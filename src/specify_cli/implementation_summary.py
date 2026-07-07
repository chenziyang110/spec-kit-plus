"""User-facing closeout summaries for sp-implement runs."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from specify_cli.execution.implementation_review import (
    branch_review_path,
    ledger_path,
    task_review_path,
)
from specify_cli.implement_audit import _parse_tasks


SUMMARY_FILENAME = "implementation-summary.md"
COMPARISON_COMMANDS = [
    "git status --short",
    "git diff --stat HEAD",
    "git diff --name-status HEAD",
]


def build_implementation_summary(
    project_root: Path,
    feature_dir: Path,
    *,
    write_report: bool = True,
) -> dict[str, Any]:
    """Build and optionally write a stable user-facing implementation summary."""

    root = project_root.resolve()
    resolved_feature_dir = feature_dir if feature_dir.is_absolute() else (root / feature_dir).resolve()
    report_path = resolved_feature_dir / SUMMARY_FILENAME
    worker_results = _load_worker_results(resolved_feature_dir)
    tasks = _parse_tasks(resolved_feature_dir / "tasks.md")

    completed_work = _completed_work(tasks, worker_results, root, resolved_feature_dir)
    changed_from_results = _changed_paths_from_results(worker_results)
    verification_evidence = _verification_evidence(worker_results)
    git_comparison = _git_comparison(root)
    behavior_surfaces = _behavior_surfaces(changed_from_results)
    review_artifacts = _review_artifacts(resolved_feature_dir, tasks, root)

    payload: dict[str, Any] = {
        "status": "ok",
        "feature_dir": _display_path(resolved_feature_dir, root),
        "report_path": _display_path(report_path, root),
        "completed_work": completed_work,
        "changed_paths": {
            "from_worker_results": changed_from_results,
            "from_git_working_tree": git_comparison["changed_paths"],
        },
        "changed_behavior_surfaces": behavior_surfaces,
        "review_artifacts": review_artifacts,
        "verification_evidence": verification_evidence,
        "baseline_comparison": {
            "method": "working_tree_vs_head",
            "baseline": "HEAD",
            "commands": COMPARISON_COMMANDS,
            "git_available": git_comparison["git_available"],
            "status_short": git_comparison["status_short"],
            "name_status": git_comparison["name_status"],
        },
        "human_needed_checks": [],
        "unresolved_gaps": [],
    }
    if write_report:
        report_path.write_text(_render_markdown(payload), encoding="utf-8")
    return payload


def _load_worker_results(feature_dir: Path) -> list[dict[str, Any]]:
    result_dir = feature_dir / "worker-results"
    if not result_dir.exists():
        return []
    results: list[dict[str, Any]] = []
    for result_path in sorted(result_dir.glob("*.json")):
        try:
            payload = json.loads(result_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            results.append(
                {
                    "task_id": result_path.stem.upper(),
                    "status": "invalid-json",
                    "summary": "Worker result JSON could not be parsed.",
                    "path": result_path,
                    "validation_results": [],
                    "changed_files": [],
                }
            )
            continue
        if isinstance(payload, dict):
            payload["path"] = result_path
            results.append(payload)
    return results


def _completed_work(
    tasks: list[dict[str, Any]],
    worker_results: list[dict[str, Any]],
    project_root: Path,
    feature_dir: Path,
) -> list[dict[str, Any]]:
    by_task_id = {
        str(result.get("task_id") or "").upper(): result
        for result in worker_results
        if str(result.get("task_id") or "").strip()
    }
    completed: list[dict[str, Any]] = []
    for task in tasks:
        if not task.get("checked"):
            continue
        task_id = str(task.get("task_id") or "").upper()
        result = by_task_id.get(task_id, {})
        changed_files = _normalize_paths(result.get("changed_files") or result.get("changedFiles") or [])
        result_path = result.get("path")
        review_path = task_review_path(feature_dir, task_id)
        completed.append(
            {
                "task_id": task_id,
                "task": str(task.get("body") or "").strip(),
                "summary": str(result.get("summary") or task.get("body") or "").strip(),
                "result_status": str(result.get("status") or "missing-worker-result"),
                "result_path": _display_path(result_path, project_root) if isinstance(result_path, Path) else "",
                "review_artifacts": {
                    "task_review": _display_path(review_path, project_root)
                    if review_path.is_file()
                    else "",
                },
                "changed_files": changed_files,
            }
        )
    return completed


def _review_artifacts(
    feature_dir: Path,
    tasks: list[dict[str, Any]],
    project_root: Path,
) -> dict[str, Any]:
    review_ledger_path = ledger_path(feature_dir)
    review_branch_path = branch_review_path(feature_dir)
    task_reviews: dict[str, str] = {}
    for task in tasks:
        task_id = str(task.get("task_id") or "").upper()
        if not task_id:
            continue
        try:
            review_path = task_review_path(feature_dir, task_id)
        except ValueError:
            continue
        if review_path.is_file():
            task_reviews[task_id] = _display_path(review_path, project_root)
    return {
        "ledger": _display_path(review_ledger_path, project_root) if review_ledger_path.is_file() else "",
        "branch_review": _display_path(review_branch_path, project_root) if review_branch_path.is_file() else "",
        "task_reviews": task_reviews,
    }


def _changed_paths_from_results(worker_results: list[dict[str, Any]]) -> list[str]:
    paths: list[str] = []
    for result in worker_results:
        paths.extend(_normalize_paths(result.get("changed_files") or result.get("changedFiles") or []))
    return sorted(set(paths))


def _verification_evidence(worker_results: list[dict[str, Any]]) -> list[dict[str, str]]:
    evidence: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for result in worker_results:
        task_id = str(result.get("task_id") or "").upper()
        validations = result.get("validation_results") or result.get("validationResults") or []
        if not isinstance(validations, list):
            continue
        for item in validations:
            if isinstance(item, dict):
                command = str(item.get("command") or "").strip()
                status = str(item.get("status") or "").strip()
                output = str(item.get("output") or item.get("summary") or "").strip()
            else:
                command = str(item).strip()
                status = ""
                output = ""
            if not command and not output:
                continue
            key = (task_id, command, status)
            if key in seen:
                continue
            seen.add(key)
            evidence.append(
                {
                    "task_id": task_id,
                    "command": command,
                    "status": status,
                    "output": _single_line(output),
                }
            )
    return evidence


def _git_comparison(project_root: Path) -> dict[str, Any]:
    status = _run_git(project_root, ["status", "--short"])
    name_status = _run_git(project_root, ["diff", "--name-status", "HEAD"])
    changed_paths = _paths_from_git_status(status) if status is not None else []
    return {
        "git_available": status is not None and name_status is not None,
        "status_short": status.splitlines() if status else [],
        "name_status": name_status.splitlines() if name_status else [],
        "changed_paths": changed_paths,
    }


def _run_git(project_root: Path, args: list[str]) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=project_root,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
    except (OSError, ValueError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def _paths_from_git_status(status_output: str | None) -> list[str]:
    paths: list[str] = []
    for raw in (status_output or "").splitlines():
        line = raw.rstrip()
        if len(line) < 4:
            continue
        path_part = line[3:].strip()
        if " -> " in path_part:
            path_part = path_part.split(" -> ", 1)[1].strip()
        if path_part:
            paths.append(path_part.replace("\\", "/"))
    return sorted(set(paths))


def _behavior_surfaces(paths: list[str]) -> list[dict[str, str]]:
    surfaces: list[dict[str, str]] = []
    for path in paths:
        surfaces.append({"path": path, "surface": _surface_for_path(path)})
    return surfaces


def _surface_for_path(path: str) -> str:
    lowered = path.lower()
    if lowered.startswith("tests/") or "/tests/" in lowered or lowered.endswith("_test.py"):
        return "tests"
    if lowered.startswith("templates/"):
        return "generated-workflow-template"
    if lowered.startswith("docs/") or lowered.endswith(".md"):
        return "docs"
    if lowered.endswith((".toml", ".json", ".yaml", ".yml", ".ini")):
        return "config-or-state"
    if "/api/" in lowered or lowered.endswith(("route.ts", "route.py")):
        return "api-or-route"
    if "cli" in lowered or lowered.endswith("__init__.py"):
        return "cli-or-command"
    return "source"


def _normalize_paths(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    paths: list[str] = []
    for item in value:
        if not isinstance(item, str):
            continue
        normalized = item.strip().replace("\\", "/")
        if normalized:
            paths.append(normalized)
    return paths


def _display_path(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _single_line(text: str, *, limit: int = 180) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3].rstrip() + "..."


def _render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "# Implementation Summary",
        "",
        f"- Feature dir: `{payload['feature_dir']}`",
        f"- Closeout status: `{payload['status']}`",
        "",
        "## What Changed",
        "",
    ]
    completed_work = payload.get("completed_work") or []
    if completed_work:
        for item in completed_work:
            lines.append(f"- `{item['task_id']}`: {item['summary'] or item['task']}")
            changed_files = item.get("changed_files") or []
            if changed_files:
                lines.append(f"  - Files: {', '.join(f'`{path}`' for path in changed_files)}")
            if item.get("result_path"):
                lines.append(f"  - Worker result: `{item['result_path']}`")
            review_artifacts = item.get("review_artifacts") or {}
            if review_artifacts.get("task_review"):
                lines.append(f"  - Task review: `{review_artifacts['task_review']}`")
    else:
        lines.append("- No checked tasks were found in `tasks.md`.")

    lines.extend(
        [
            "",
            "## Changed Paths",
            "",
            "### From Worker Results",
            "",
        ]
    )
    changed_paths = payload.get("changed_paths", {})
    worker_paths = changed_paths.get("from_worker_results") or []
    lines.extend(_path_lines(worker_paths))
    lines.extend(["", "### From Git Working Tree", ""])
    git_paths = changed_paths.get("from_git_working_tree") or []
    lines.extend(_path_lines(git_paths))

    lines.extend(["", "## Changed Behavior Surfaces", ""])
    surfaces = payload.get("changed_behavior_surfaces") or []
    if surfaces:
        for item in surfaces:
            lines.append(f"- `{item['path']}` -> {item['surface']}")
    else:
        lines.append("- No behavior surfaces were inferred from worker changed files.")

    lines.extend(["", "## Review Artifacts", ""])
    review_artifacts = payload.get("review_artifacts") or {}
    ledger = review_artifacts.get("ledger") or ""
    branch_review = review_artifacts.get("branch_review") or ""
    task_reviews = review_artifacts.get("task_reviews") or {}
    lines.append(f"- Ledger: `{ledger}`" if ledger else "- Ledger: None recorded.")
    lines.append(f"- Branch review: `{branch_review}`" if branch_review else "- Branch review: None recorded.")
    if task_reviews:
        for task_id, path in sorted(task_reviews.items()):
            lines.append(f"- `{task_id}` task review: `{path}`")
    else:
        lines.append("- Task reviews: None recorded.")

    lines.extend(["", "## How To Verify", ""])
    evidence = payload.get("verification_evidence") or []
    if evidence:
        for item in evidence:
            command = item.get("command") or item.get("output") or "verification evidence"
            status = item.get("status") or "recorded"
            task = item.get("task_id") or "task"
            lines.append(f"- `{command}` -> {status} ({task})")
    else:
        lines.append("- No worker validation evidence was recorded.")

    comparison = payload.get("baseline_comparison") or {}
    lines.extend(
        [
            "",
            "## Version Comparison",
            "",
            f"- Baseline: `{comparison.get('baseline', 'HEAD')}`",
            "- Run these commands to inspect the current implementation diff:",
        ]
    )
    for command in comparison.get("commands") or COMPARISON_COMMANDS:
        lines.append(f"  - `{command}`")
    status_lines = comparison.get("status_short") or []
    if status_lines:
        lines.extend(["", "Current `git status --short` snapshot:", "", "```text"])
        lines.extend(status_lines)
        lines.append("```")
    else:
        lines.append("- No git working-tree changes were detected when this summary was generated.")

    lines.extend(["", "## Remaining Gaps", ""])
    gaps = payload.get("unresolved_gaps") or []
    if gaps:
        lines.extend(f"- {gap}" for gap in gaps)
    else:
        lines.append("- None recorded.")

    return "\n".join(lines) + "\n"


def _path_lines(paths: list[str]) -> list[str]:
    if not paths:
        return ["- None recorded."]
    return [f"- `{path}`" for path in paths]
