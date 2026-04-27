"""Environment validation and runtime status helpers for Codex team."""

from __future__ import annotations

import os
import platform
from specify_cli.codex_team.packet_executor import resolve_packet_executor_command
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from .baseline_check import classify_baseline_build_status, detect_native_build_shell
from specify_cli.orchestration.backends.detect import detect_available_backends
from specify_cli.orchestration.state_store import write_json
from specify_cli.execution import (
    normalize_worker_task_result_payload,
    summarize_validation_results,
    validate_worker_task_result,
    worker_task_packet_from_json,
    worker_task_result_payload,
)

from . import task_ops
from .manifests import (
    DispatchRecord,
    RuntimeSession,
    dispatch_record_from_json,
    runtime_session_from_json,
    runtime_state_payload,
)
from .state_paths import codex_team_state_root, dispatch_record_path, runtime_session_path


class RuntimeEnvironmentError(RuntimeError):
    """Raised when the runtime cannot be used in the current environment."""


NATIVE_WINDOWS_REQUIRED_TOOLS = ("codex", "node", "npm", "cargo", "git")
LEGACY_HEARTBEAT_EXECUTOR = "legacy-heartbeat-runtime"
AGENT_TEAMS_EXECUTOR = "agent-teams-runtime"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def is_wsl() -> bool:
    """Return whether the current process is running inside WSL."""
    return bool(
        os.environ.get("WSL_INTEROP")
        or os.environ.get("WSL_DISTRO_NAME")
        or "microsoft" in platform.uname().release.lower()
    )


def is_msys_or_git_bash() -> bool:
    """Return whether the shell is an MSYS/Git Bash environment on Windows."""
    return bool(os.environ.get("MSYSTEM"))


def is_native_windows() -> bool:
    """Return whether the current process is running on native Windows."""
    return sys.platform == "win32" and not is_wsl() and not is_msys_or_git_bash()


def _winget_links_binary(name: str) -> str | None:
    """Return a WinGet Links binary path when available on native Windows."""
    if not is_native_windows():
        return None
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        return None
    candidate = Path(local_app_data) / "Microsoft" / "WinGet" / "Links" / f"{name}.exe"
    return str(candidate) if candidate.is_file() else None


def _winget_package_binary(package_fragment: str, binary_names: tuple[str, ...]) -> str | None:
    """Return a binary path from a WinGet package install directory when present."""
    if not is_native_windows():
        return None
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        return None
    packages_root = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
    if not packages_root.is_dir():
        return None

    fragment = package_fragment.casefold()
    for package_dir in packages_root.iterdir():
        if not package_dir.is_dir() or fragment not in package_dir.name.casefold():
            continue
        for binary_name in binary_names:
            candidate = package_dir / binary_name
            if candidate.is_file():
                return str(candidate)
    return None


def detect_team_runtime_backend() -> dict[str, object]:
    """Detect the available runtime backend for team-mode coordination."""
    backend_descriptors = detect_available_backends()

    if is_native_windows():
        psmux = backend_descriptors.get("psmux")
        psmux_binary = shutil.which("psmux")
        source = "path"
        if not psmux_binary:
            psmux_binary = _winget_links_binary("psmux")
            source = "winget_links"
        if not psmux_binary:
            psmux_binary = _winget_package_binary("psmux", ("psmux.exe", "tmux.exe"))
            source = "winget_package"
        if not psmux_binary and psmux and psmux.available:
            psmux_binary = psmux.binary
            source = "backend_descriptor"
        if psmux_binary:
            return {"available": True, "name": "psmux", "binary": psmux_binary, "source": source}

    tmux = backend_descriptors.get("tmux")
    tmux_binary = shutil.which("tmux")
    source = "path"
    if not tmux_binary:
        tmux_binary = _winget_links_binary("tmux")
        source = "winget_links"
    if not tmux_binary and tmux and tmux.available:
        tmux_binary = tmux.binary
        source = "backend_descriptor"
    if tmux_binary:
        return {"available": True, "name": "tmux", "binary": tmux_binary, "source": source}

    return {"available": False, "name": None, "binary": None, "source": "unavailable"}


def ensure_tmux_available() -> None:
    """Fail visibly when no supported team runtime backend is available."""
    backend = detect_team_runtime_backend()
    if backend["available"]:
        return

    if is_native_windows():
        raise RuntimeEnvironmentError(
            "A tmux-compatible team runtime backend is required on native Windows. "
            "Install psmux with: winget install psmux"
        )

    raise RuntimeEnvironmentError(
        "tmux is required for the Codex team runtime in first-release environments."
    )


def native_windows_toolchain_readiness() -> dict[str, object]:
    """Return native Windows toolchain readiness for the Codex team runtime."""
    if not is_native_windows():
        return {"required": [], "missing": [], "ready": True}

    missing = [tool for tool in NATIVE_WINDOWS_REQUIRED_TOOLS if not shutil.which(tool)]
    return {
        "required": list(NATIVE_WINDOWS_REQUIRED_TOOLS),
        "missing": missing,
        "ready": not missing,
    }


def ensure_native_windows_toolchain_available() -> None:
    """Fail visibly when the native Windows Codex team toolchain is incomplete."""
    readiness = native_windows_toolchain_readiness()
    if readiness["ready"]:
        return

    missing = ", ".join(str(tool) for tool in readiness["missing"])
    raise RuntimeEnvironmentError(
        "The native Windows Codex team runtime must run from a single native shell with "
        f"psmux, codex, node, npm, cargo, and git available. Missing: {missing}"
    )


def ensure_codex_team_runtime_prerequisites() -> None:
    """Validate the runtime backend plus the Windows-native toolchain contract."""
    ensure_tmux_available()
    if is_native_windows():
        ensure_native_windows_toolchain_available()


def _candidate_agent_teams_engine_roots(project_root: Path) -> list[Path]:
    package_root = Path(__file__).resolve().parents[1]
    repo_root = Path(__file__).resolve().parents[3]
    candidates = [
        project_root / ".specify" / "extensions" / "agent-teams" / "engine",
        project_root / "extensions" / "agent-teams" / "engine",
        package_root / "core_pack" / "extensions" / "agent-teams" / "engine",
        repo_root / "extensions" / "agent-teams" / "engine",
    ]
    unique: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve(strict=False)
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(candidate)
    return unique


def _detect_agent_teams_runtime_cli(project_root: Path) -> str | None:
    override = os.environ.get("SPECIFY_CODEX_TEAM_RUNTIME_CLI", "").strip()
    if override:
        candidate = Path(override)
        if not candidate.is_absolute():
            candidate = (project_root / candidate).resolve()
        return str(candidate) if candidate.is_file() else None

    for engine_root in _candidate_agent_teams_engine_roots(project_root):
        candidate = engine_root / "dist" / "team" / "runtime-cli.js"
        if candidate.is_file():
            return str(candidate)
    return None


def detect_codex_team_executor(project_root: Path) -> dict[str, object]:
    """Return whether a packet executor is wired into ``specify team``."""

    configured = os.environ.get("SPECIFY_CODEX_TEAM_EXECUTOR", "").strip().lower()
    runtime_cli_path = _detect_agent_teams_runtime_cli(project_root)
    node_binary = shutil.which("node")
    packet_executor_command = resolve_packet_executor_command()

    if configured == LEGACY_HEARTBEAT_EXECUTOR:
        return {
            "available": True,
            "mode": LEGACY_HEARTBEAT_EXECUTOR,
            "reason": (
                "Legacy worker runtime enabled. "
                "Workers will consume packets and write structured results directly."
            ),
            "configured_value": configured,
            "bundled_runtime_binary": None,
            "runtime_cli_path": None,
            "packet_executor_command": packet_executor_command or [],
            "next_steps": (
                []
                if packet_executor_command
                else [
                    "Configure SPECIFY_CODEX_TEAM_PACKET_EXECUTOR for delegated packet execution, or use agent-teams-runtime when a runtime-cli-backed executor is available."
                ]
            ),
        }

    prefer_agent_teams = configured == AGENT_TEAMS_EXECUTOR or (
        not configured and runtime_cli_path is not None
    )
    if prefer_agent_teams and runtime_cli_path and node_binary:
        return {
            "available": True,
            "mode": AGENT_TEAMS_EXECUTOR,
            "reason": "Bundled agent-teams runtime-cli is available for delegated batch execution.",
            "configured_value": configured,
            "bundled_runtime_binary": None,
            "runtime_cli_path": runtime_cli_path,
            "packet_executor_command": packet_executor_command or [],
            "next_steps": [],
        }

    next_steps: list[str] = []
    if runtime_cli_path is None:
        next_steps.append("Bundled teams runtime assets are missing from this checkout. Restore or rebuild the internal runtime before enabling teams execution.")
    elif not node_binary:
        next_steps.append("Install Node.js or make `node` available on PATH before enabling teams execution.")
    next_steps.append(
        "Use sp-implement for implementation work until a packet executor is wired into specify team."
    )

    return {
        "available": False,
        "mode": "none",
        "reason": (
            "No packet executor is configured for specify team auto-dispatch. "
            "The current runtime can report state and accept submitted results, "
            "but it cannot truthfully execute worker packets."
        ),
        "configured_value": configured,
        "bundled_runtime_binary": None,
        "runtime_cli_path": runtime_cli_path,
        "packet_executor_command": packet_executor_command or [],
        "next_steps": next_steps,
    }


def ensure_codex_team_executor_available(project_root: Path) -> dict[str, object]:
    """Fail visibly when ``specify team`` has no packet executor configured."""

    executor = detect_codex_team_executor(project_root)
    if executor["available"]:
        return executor
    raise RuntimeEnvironmentError(str(executor["reason"]))


def resolve_agent_teams_runtime_binary(engine_root: Path) -> Path | None:
    """Return the first available bundled runtime binary for the given engine root."""
    candidates = [
        engine_root / "target" / "release" / "omx-runtime",
        engine_root / "target" / "release" / "omx-runtime.exe",
        engine_root / "target" / "debug" / "omx-runtime",
        engine_root / "target" / "debug" / "omx-runtime.exe",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None

def _git_probe(project_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a git probe command without raising on failure."""
    return subprocess.run(
        ["git", *args],
        cwd=project_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def codex_team_git_readiness(project_root: Path) -> dict[str, object]:
    """Return git/worktree readiness information for team-mode execution."""
    repo_probe = _git_probe(project_root, "rev-parse", "--is-inside-work-tree")
    git_repo_detected = repo_probe.returncode == 0 and repo_probe.stdout.strip().lower() == "true"

    if not git_repo_detected:
        return {
            "git_repo_detected": False,
            "git_head_available": False,
            "leader_workspace_clean": False,
            "worktree_ready": False,
            "git_next_steps": [
                "Initialize git before teams execution: git init",
                'Create an initial commit before teams execution: git add . && git commit -m "Initial commit"',
            ],
        }

    head_probe = _git_probe(project_root, "rev-parse", "--verify", "HEAD")
    git_head_available = head_probe.returncode == 0
    status_probe = _git_probe(project_root, "status", "--short")
    leader_workspace_clean = status_probe.returncode == 0 and not status_probe.stdout.strip()
    worktree_ready = git_head_available and leader_workspace_clean

    git_next_steps: list[str] = []
    if not git_head_available:
        git_next_steps.append(
            'Create an initial commit before teams execution: git add . && git commit -m "Initial commit"'
        )
    elif not leader_workspace_clean:
        git_next_steps.append(
            "Commit or stash leader workspace changes before teams execution."
        )

    return {
        "git_repo_detected": True,
        "git_head_available": git_head_available,
        "leader_workspace_clean": leader_workspace_clean,
        "worktree_ready": worktree_ready,
        "git_next_steps": git_next_steps,
    }


def _load_runtime_session(project_root: Path, session_id: str) -> RuntimeSession:
    path = runtime_session_path(project_root, session_id)
    return runtime_session_from_json(path.read_text(encoding="utf-8"))


def _load_dispatch_record(project_root: Path, request_id: str) -> DispatchRecord:
    path = dispatch_record_path(project_root, request_id)
    return dispatch_record_from_json(path.read_text(encoding="utf-8"))


def bootstrap_runtime_session(project_root: Path, session_id: str) -> RuntimeSession:
    """Validate the environment and persist a ready runtime session."""
    ensure_codex_team_runtime_prerequisites()
    session = RuntimeSession(
        session_id=session_id,
        status="ready",
        environment_check="pass",
    )
    write_json(runtime_session_path(project_root, session_id), runtime_state_payload(session)["session"])
    return session


def dispatch_runtime_task(
    project_root: Path,
    *,
    session_id: str,
    request_id: str,
    target_worker: str,
    packet_path: str = "",
    packet_summary: dict[str, object] | None = None,
    delegation_metadata: dict[str, object] | None = None,
    result_path: str = "",
) -> DispatchRecord:
    """Persist a dispatched task and advance the session to running."""
    session = _load_runtime_session(project_root, session_id)
    session.status = "running"
    record = DispatchRecord(
        request_id=request_id,
        target_worker=target_worker,
        status="dispatched",
        packet_path=packet_path,
        packet_summary=packet_summary,
        delegation_metadata=delegation_metadata,
        result_path=result_path,
    )
    write_json(runtime_session_path(project_root, session_id), runtime_state_payload(session)["session"])
    write_json(dispatch_record_path(project_root, request_id), runtime_state_payload(session, [record])["dispatches"][0])
    return record


def submit_runtime_result(
    project_root: Path,
    *,
    session_id: str,
    request_id: str,
    result: object,
) -> DispatchRecord:
    """Validate and persist a worker result for an existing dispatch."""

    session = _load_runtime_session(project_root, session_id)
    record = _load_dispatch_record(project_root, request_id)
    if record.status in {"completed", "failed", "blocked"}:
        raise RuntimeEnvironmentError(f"request {request_id} already has a terminal result")
    packet_path = Path(record.packet_path) if record.packet_path else None
    if packet_path is None or not packet_path.exists():
        raise RuntimeEnvironmentError(f"packet for request {request_id} is unavailable")

    packet = worker_task_packet_from_json(packet_path.read_text(encoding="utf-8"))
    normalized = normalize_worker_task_result_payload(result)
    validated = validate_worker_task_result(normalized, packet)

    result_path = Path(record.result_path) if record.result_path else (codex_team_state_root(project_root) / "results" / f"{request_id}.json")
    record.result_path = str(result_path)
    write_json(result_path, worker_task_result_payload(validated))

    if validated.status == "success":
        record.status = "completed"
    elif validated.status == "blocked":
        record.status = "blocked"
    else:
        record.status = "failed"
    record.updated_at = _utc_now()

    _sync_task_state_from_result(
        project_root,
        packet_task_id=packet.task_id,
        request_id=request_id,
        target_worker=record.target_worker or packet.task_id.lower(),
        validated=validated,
    )

    write_json(runtime_session_path(project_root, session_id), runtime_state_payload(session)["session"])
    write_json(dispatch_record_path(project_root, request_id), runtime_state_payload(session, [record])["dispatches"][0])
    return record


def _sync_task_state_from_result(
    project_root: Path,
    *,
    packet_task_id: str,
    request_id: str,
    target_worker: str,
    validated,
) -> None:
    try:
        task_record = task_ops.get_task(project_root, packet_task_id)
    except task_ops.TaskOpsError:
        task_record = task_ops.create_task(
            project_root,
            task_id=packet_task_id,
            summary=validated.summary or packet_task_id,
            metadata={"source": "submit_runtime_result"},
        )

    current_claim = (task_record.metadata or {}).get("current_claim")
    claim_token = current_claim.get("claim_id") if isinstance(current_claim, dict) else None

    if task_record.status == task_ops.TASK_STATUS_PENDING:
        claim_token = task_ops.claim_task(
            project_root,
            task_id=packet_task_id,
            worker_id=target_worker,
            expected_version=task_record.version,
        )
        task_record = task_ops.transition_task_status(
            project_root,
            task_id=packet_task_id,
            new_status=task_ops.TASK_STATUS_IN_PROGRESS,
            owner=target_worker,
            expected_version=task_record.version + 1,
            claim_token=claim_token,
        )
    elif task_record.status == task_ops.TASK_STATUS_IN_PROGRESS:
        if not current_claim or current_claim.get("worker_id") != target_worker or not claim_token:
            raise RuntimeEnvironmentError(
                f"task {packet_task_id} is in progress but has no matching claim for worker {target_worker}"
            )
    elif task_record.status in task_ops.TERMINAL_STATUSES:
        raise RuntimeEnvironmentError(f"task {packet_task_id} already reached terminal status {task_record.status}")

    final_status = (
        task_ops.TASK_STATUS_COMPLETED
        if validated.status == "success"
        else task_ops.TASK_STATUS_FAILED
    )
    failure_class = "blocked" if validated.status == "blocked" else ""
    terminal_record = task_ops.transition_task_status(
        project_root,
        task_id=packet_task_id,
        new_status=final_status,
        owner=target_worker,
        expected_version=task_record.version,
        claim_token=claim_token,
        failure_class=failure_class,
    )
    latest_record = task_ops.get_task(project_root, packet_task_id)

    validation_summary = summarize_validation_results(validated.validation_results)
    task_ops.update_task_metadata(
        project_root,
        packet_task_id,
        expected_version=latest_record.version,
        metadata={
            "result_request_id": request_id,
            "reported_status": validated.reported_status or validated.status,
            "concerns_present": bool(validated.concerns),
            "last_validation_summary": {
                "total": validation_summary.total,
                "passed": validation_summary.passed,
                "failed": validation_summary.failed,
                "skipped": validation_summary.skipped,
                "overall_status": validation_summary.overall_status,
            },
            "worker_result": {
                "status": validated.status,
                "summary": validated.summary,
                "changed_files": validated.changed_files,
                "concerns": validated.concerns,
                "validation_results": [
                    {
                        "command": item.command,
                        "status": item.status,
                        "output": item.output,
                    }
                    for item in validated.validation_results
                ],
            },
        },
    )


def mark_runtime_failure(
    project_root: Path,
    *,
    session_id: str,
    request_id: str,
    reason: str,
    failure_class: str = "critical",
    blocker_id: str = "",
    retry_count: int = 0,
    retry_budget: int = 0,
) -> tuple[RuntimeSession, DispatchRecord]:
    """Persist a visible failure state for the session and dispatch."""
    session = _load_runtime_session(project_root, session_id)
    record = _load_dispatch_record(project_root, request_id)
    record.failure_class = failure_class
    record.retry_count = retry_count
    record.retry_budget = retry_budget

    retryable = (
        failure_class == "transient"
        and retry_budget > 0
        and retry_count < retry_budget
    )

    if retryable:
        session.status = "retry_pending"
        record.status = "retry_pending"
    else:
        session.status = "failed"
        session.blocker_id = blocker_id
        session.finished_at = record.updated_at
        record.status = "failed"
    record.reason = reason
    write_json(runtime_session_path(project_root, session_id), runtime_state_payload(session)["session"])
    write_json(dispatch_record_path(project_root, request_id), runtime_state_payload(session, [record])["dispatches"][0])
    return session, record


def cleanup_runtime_session(project_root: Path, session_id: str) -> RuntimeSession:
    """Persist a cleaned terminal state for the runtime session."""
    session = _load_runtime_session(project_root, session_id)
    session.status = "cleaned"
    session.finished_at = session.finished_at or session.created_at
    write_json(runtime_session_path(project_root, session_id), runtime_state_payload(session)["session"])
    return session


def _load_live_runtime_state(project_root: Path, session_id: str) -> dict[str, object] | None:
    path = runtime_session_path(project_root, session_id)
    if not path.exists():
        return None
    session = runtime_session_from_json(path.read_text(encoding="utf-8"))
    return runtime_state_payload(session, [])


def codex_team_runtime_status(
    project_root: Path,
    *,
    integration_key: str | None,
    session_id: str = "default",
) -> dict[str, object]:
    """Return a compact runtime status payload for help text and tests."""
    available = integration_key == "codex"
    backend = detect_team_runtime_backend()
    git_status = codex_team_git_readiness(project_root)
    toolchain_status = native_windows_toolchain_readiness()
    executor_status = detect_codex_team_executor(project_root)
    native_build_shell = detect_native_build_shell(project_root)
    baseline_build = classify_baseline_build_status(project_root)
    state_root = codex_team_state_root(project_root)
    live_runtime_state = _load_live_runtime_state(project_root, session_id)
    session = RuntimeSession(
        session_id="preview",
        status=(
            "ready"
            if available
            and backend["available"]
            and git_status["worktree_ready"]
            and toolchain_status["ready"]
            and executor_status["available"]
            else "created"
        ),
        environment_check="pass" if backend["available"] else "fail",
    )
    dispatch = DispatchRecord(
        request_id="preview-request",
        target_worker="preview-worker",
        status="pending",
    )
    next_steps: list[str] = []
    if available and not backend["available"]:
        if is_native_windows():
            next_steps.append("Install a Windows team runtime backend: winget install psmux")
        else:
            next_steps.append("Install tmux before teams execution.")
    if available and is_native_windows() and not toolchain_status["ready"]:
        missing_text = ", ".join(str(tool) for tool in toolchain_status["missing"])
        next_steps.append(
            "Use a single native Windows shell for teams execution so psmux, codex, node, npm, cargo, and git resolve together. "
            f"Missing: {missing_text}"
        )
    next_steps.extend(str(step) for step in executor_status["next_steps"])
    next_steps.extend(git_status["git_next_steps"])
    return {
        "available": available,
        "runtime_backend_available": backend["available"],
        "runtime_backend": backend["name"],
        "runtime_backend_binary": backend["binary"],
        "runtime_backend_source": backend["source"],
        "tmux_available": backend["name"] == "tmux",
        "native_windows": is_native_windows(),
        "native_toolchain_ready": toolchain_status["ready"],
        "native_toolchain_required": toolchain_status["required"],
        "native_toolchain_missing": toolchain_status["missing"],
        "native_build_shell": native_build_shell,
        "baseline_build": baseline_build,
        "git_repo_detected": git_status["git_repo_detected"],
        "git_head_available": git_status["git_head_available"],
        "leader_workspace_clean": git_status["leader_workspace_clean"],
        "worktree_ready": git_status["worktree_ready"],
        "executor_available": executor_status["available"],
        "executor_mode": executor_status["mode"],
        "executor_reason": executor_status["reason"],
        "executor_bundled_runtime_binary": executor_status["bundled_runtime_binary"],
        "executor_runtime_cli_path": executor_status["runtime_cli_path"],
        "executor_packet_executor_command": executor_status.get("packet_executor_command", []),
        "teams_ready": (
            available
            and backend["available"]
            and toolchain_status["ready"]
            and git_status["worktree_ready"]
            and executor_status["available"]
        ),
        "next_steps": next_steps,
        "state_root": state_root,
        "runtime_state": live_runtime_state,
        "runtime_state_source": "live" if live_runtime_state is not None else "none",
        "preview_runtime_state": runtime_state_payload(session, [dispatch]),
        "runtime_state_summary": (
            "Runtime state surfaces worker outcomes, join points, retry-pending work, and blockers."
        ),
    }
