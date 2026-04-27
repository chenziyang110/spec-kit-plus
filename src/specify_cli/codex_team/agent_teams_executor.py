"""Batch executor that bridges ``specify team`` dispatches into agent-teams runtime-cli."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from specify_cli.codex_team.runtime_bridge import mark_runtime_failure, submit_runtime_result


RESULT_START_MARKER = "BEGIN_WORKER_TASK_RESULT_JSON"
RESULT_END_MARKER = "END_WORKER_TASK_RESULT_JSON"
SUPPORTED_AGENT_TYPES = {"codex", "claude", "gemini"}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Codex team batch executor via agent-teams runtime-cli")
    parser.add_argument("--project-root", required=True)
    parser.add_argument("--manifest-path", required=True)
    return parser


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_runtime_transcript(
    manifest_path: Path,
    *,
    runtime_command: list[str],
    runtime_payload: dict[str, object],
    state_root: Path,
    completed: subprocess.CompletedProcess[str],
) -> Path:
    transcript_path = manifest_path.with_suffix(".runtime.json")
    transcript_path.write_text(
        json.dumps(
            {
                "runtime_command": runtime_command,
                "runtime_payload": runtime_payload,
                "state_root": str(state_root),
                "returncode": completed.returncode,
                "stdout": completed.stdout,
                "stderr": completed.stderr,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return transcript_path


def _resolve_agent_types(worker_count: int) -> list[str]:
    raw_map = (
        os.environ.get("SP_TEAMS_WORKER_CLI_MAP", "").strip()
        or os.environ.get("OMX_TEAM_WORKER_CLI_MAP", "").strip()
    )
    if raw_map:
        values = [value.strip().lower() for value in raw_map.split(",") if value.strip()]
        if values and all(value in SUPPORTED_AGENT_TYPES for value in values):
            return values

    raw_single = (
        os.environ.get("SP_TEAMS_WORKER_CLI", "").strip()
        or os.environ.get("OMX_TEAM_WORKER_CLI", "").strip()
    ).lower()
    if raw_single in SUPPORTED_AGENT_TYPES:
        return [raw_single] * max(1, worker_count)

    return ["codex"] * max(1, worker_count)


def _build_runtime_tasks(task_specs: list[dict[str, str]], worker_count: int) -> list[dict[str, str]]:
    effective_worker_count = max(1, worker_count)
    tasks: list[dict[str, str]] = []
    for index, task_spec in enumerate(task_specs, start=1):
        worker_index = ((index - 1) % effective_worker_count) + 1
        tasks.append(
            {
                "subject": task_spec["subject"],
                "description": task_spec["description"],
                "owner": f"worker-{worker_index}",
                "role": "executor",
            }
        )
    return tasks


def _extract_worker_task_result(raw_text: str) -> object | None:
    start = raw_text.find(RESULT_START_MARKER)
    if start < 0:
        return None
    start += len(RESULT_START_MARKER)
    end = raw_text.find(RESULT_END_MARKER, start)
    if end < 0:
        return None
    payload = raw_text[start:end].strip()
    if not payload:
        return None
    return payload


def _load_team_task_payloads(state_root: Path, team_name: str) -> dict[str, dict[str, Any]]:
    tasks_dir = state_root / "team" / team_name / "tasks"
    if not tasks_dir.is_dir():
        return {}

    payloads: dict[str, dict[str, Any]] = {}
    for task_file in sorted(tasks_dir.glob("*.json")):
        payload = _load_json(task_file)
        subject = str(payload.get("subject", "")).strip()
        if subject:
            payloads[subject] = payload
    return payloads


def _finalize_runtime_results(
    project_root: Path,
    session_id: str,
    state_root: Path,
    team_name: str,
    task_specs: list[dict[str, str]],
    *,
    fallback_reason: str,
) -> int:
    exit_code = 0
    team_tasks = _load_team_task_payloads(state_root, team_name)

    for task_spec in task_specs:
        task_id = str(task_spec["task_id"])
        request_id = str(task_spec["request_id"])
        subject = str(task_spec["subject"])
        task_payload = team_tasks.get(subject)
        if task_payload is None:
            mark_runtime_failure(
                project_root,
                session_id=session_id,
                request_id=request_id,
                reason=f"{fallback_reason}; runtime task state for {task_id} is missing",
            )
            exit_code = 1
            continue

        result_source = str(task_payload.get("result") or task_payload.get("error") or "")
        structured = _extract_worker_task_result(result_source)
        if structured is None:
            mark_runtime_failure(
                project_root,
                session_id=session_id,
                request_id=request_id,
                reason=f"{fallback_reason}; structured worker result for {task_id} is missing",
            )
            exit_code = 1
            continue

        try:
            submit_runtime_result(
                project_root,
                session_id=session_id,
                request_id=request_id,
                result=structured,
            )
        except Exception as exc:  # pragma: no cover - exercised by contract tests
            mark_runtime_failure(
                project_root,
                session_id=session_id,
                request_id=request_id,
                reason=f"{fallback_reason}; failed to normalize structured worker result for {task_id}: {exc}",
            )
            exit_code = 1

    return exit_code


def main() -> int:
    args = _build_parser().parse_args()
    return run_manifest(Path(args.project_root), Path(args.manifest_path))


def run_manifest(project_root: Path, manifest_path: Path) -> int:
    manifest = _load_json(manifest_path)

    runtime_cli_path = Path(str(manifest["runtime_cli_path"]))
    state_root = Path(str(manifest["state_root"]))
    session_id = str(manifest["session_id"])
    team_name = str(manifest["team_name"])
    task_specs = [
        {
            "task_id": str(task["task_id"]),
            "request_id": str(task["request_id"]),
            "subject": str(task["subject"]),
            "description": str(task["description"]),
        }
        for task in manifest.get("tasks", [])
    ]

    runtime_payload = {
        "teamName": team_name,
        "workerCount": int(manifest["worker_count"]),
        "agentTypes": _resolve_agent_types(int(manifest["worker_count"])),
        "tasks": _build_runtime_tasks(task_specs, int(manifest["worker_count"])),
        "cwd": str(manifest["cwd"]),
        "pollIntervalMs": 1000,
    }

    env = {
        **os.environ,
        "OMX_TEAM_STATE_ROOT": str(state_root),
        "SP_TEAMS_STATE_ROOT": str(state_root),
    }
    if os.name == "nt":
        env["Path"] = env.get("PATH") or env.get("Path") or ""
        env["PATH"] = env.get("PATH") or env.get("Path") or ""

    runtime_command = (
        [sys.executable, str(runtime_cli_path)]
        if runtime_cli_path.suffix.lower() == ".py"
        else ["node", str(runtime_cli_path)]
    )

    completed = subprocess.run(
        runtime_command,
        cwd=str(project_root),
        input=json.dumps(runtime_payload),
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
        env=env,
    )
    _write_runtime_transcript(
        manifest_path,
        runtime_command=runtime_command,
        runtime_payload=runtime_payload,
        state_root=state_root,
        completed=completed,
    )

    stderr = completed.stderr.strip()
    stdout = completed.stdout.strip()
    fallback_reason = stderr or stdout or "agent-teams runtime-cli exited without structured worker results"

    if completed.returncode != 0 and not task_specs:
        return 1

    exit_code = _finalize_runtime_results(
        project_root,
        session_id,
        state_root,
        team_name,
        task_specs,
        fallback_reason=fallback_reason,
    )
    if completed.returncode != 0:
        return 1
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
