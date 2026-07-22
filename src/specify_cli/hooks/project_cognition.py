"""Project cognition gate hooks backed by the unified Specify runtime."""

from __future__ import annotations

from pathlib import Path

from specify_cli.execution import worker_task_packet_from_json
from specify_cli.specify_runtime import SpecifyRuntimeError, run_specify_runtime

from .events import (
    PROJECT_COGNITION_COMPLETE_REFRESH,
    PROJECT_COGNITION_MARK_DIRTY,
)
from .types import HookResult, QualityHookError


SCAN_BUILD_ALLOWED_REASON_TOKENS = frozenset(
    {
        "missing_baseline",
        "active_generation_has_no_path_index_rows",
        "path_not_safely_adoptable_by_project_cognition_index",
        "explicit_rebuild_requested",
        "baseline_identity_invalid",
        "unsupported_runtime",
    }
)
STALE_BLOCK_COMMANDS = {"implement", "quick", "fast", "specify", "plan", "tasks", "debug"}
STALE_FALLBACK_GUIDANCE = (
    "project cognition runtime freshness is stale; refresh through /sp-map-update, "
    "and rebuild through /sp-map-scan -> /sp-map-build only for first/missing/unusable baseline, "
    "active_generation_has_no_path_index_rows, path_not_safely_adoptable_by_project_cognition_index, "
    "explicit_rebuild_requested, or baseline_identity_invalid"
)
PATH_INDEX_STALE_FALLBACK_GUIDANCE = (
    "project cognition runtime freshness is stale because changed paths are missing from path_index; "
    "run /sp-map-update first so ordinary gaps can receive provisional coverage, review state, known unknowns, "
    "and minimal live reads; rebuild through /sp-map-scan -> /sp-map-build only for first/missing/unusable baseline, "
    "active_generation_has_no_path_index_rows, path_not_safely_adoptable_by_project_cognition_index, "
    "explicit_rebuild_requested, or baseline_identity_invalid"
)
SCAN_BUILD_FALLBACK_GUIDANCE = (
    "project cognition runtime freshness requires rebuild through /sp-map-scan -> /sp-map-build because the "
    "baseline is missing or unusable, active_generation_has_no_path_index_rows, "
    "path_not_safely_adoptable_by_project_cognition_index, explicit_rebuild_requested, or baseline_identity_invalid"
)
SUPPORT_DRIFT_FALLBACK_GUIDANCE = (
    "project cognition runtime freshness has support-surface drift; resolve, commit, or intentionally ignore "
    "the support files before retrying"
)
PARTIAL_REFRESH_FALLBACK_GUIDANCE = (
    "project cognition refresh data was recorded, but runtime readiness is still blocked; follow recommended_next_action "
    "before retrying"
)
NON_STALE_FALLBACK_GUIDANCE = (
    "project cognition runtime freshness is {state}; create the initial baseline through "
    "/sp-map-scan -> /sp-map-build when missing, or refresh through /sp-map-update when stale"
)
MISSING_BASELINE_FALLBACK_GUIDANCE = (
    "project cognition runtime freshness is missing; create the initial baseline through /sp-map-scan -> /sp-map-build before retrying"
)
HUMAN_FALLBACK_GUIDANCE = {
    STALE_FALLBACK_GUIDANCE,
    PATH_INDEX_STALE_FALLBACK_GUIDANCE,
    SCAN_BUILD_FALLBACK_GUIDANCE,
    SUPPORT_DRIFT_FALLBACK_GUIDANCE,
    PARTIAL_REFRESH_FALLBACK_GUIDANCE,
    MISSING_BASELINE_FALLBACK_GUIDANCE,
}


def project_cognition_freshness_result(project_root: Path, *, command_name: str) -> HookResult:
    normalized = command_name.strip().lower()
    try:
        freshness = run_specify_runtime(["cognition", "check", "--format", "json"], cwd=project_root)
    except SpecifyRuntimeError as exc:
        freshness = {
            "state": "missing_baseline",
            "freshness": "missing_baseline",
            "readiness": "blocked",
            "recommended_next_action": "install_project_cognition",
            "reasons": [str(exc)],
        }
    raw_freshness = str(freshness.get("freshness", "")).strip().lower()
    state = str(freshness.get("state", freshness.get("freshness", ""))).strip().lower()
    readiness = str(freshness.get("readiness", "")).strip().lower()
    next_action = str(freshness.get("recommended_next_action", "")).strip().lower()
    reasons = [str(item) for item in freshness.get("reasons", []) if str(item).strip()]
    machine_reasons = [reason for reason in reasons if reason not in HUMAN_FALLBACK_GUIDANCE]
    has_scan_build_reason = _has_scan_build_allowed_reason(machine_reasons)
    has_ordinary_path_index_reason = next_action != "run_map_scan_build" and not has_scan_build_reason and any(
        "path_index" in reason.lower() or "path-index" in reason.lower() for reason in machine_reasons
    )

    if state == "fresh":
        return HookResult(
            event="project_cognition.refresh.validate",
            status="ok",
            severity="info",
            data={"freshness": freshness},
        )
    if state == "missing_baseline" and normalized in STALE_BLOCK_COMMANDS:
        return HookResult(
            event="project_cognition.refresh.validate",
            status="blocked",
            severity="critical",
            errors=reasons or [MISSING_BASELINE_FALLBACK_GUIDANCE],
            data={"freshness": freshness},
        )
    if (
        state == "runtime_stale"
        and readiness == "blocked"
        and raw_freshness != "possibly_stale"
        and normalized in STALE_BLOCK_COMMANDS
    ):
        if next_action == "run_map_scan_build" or has_scan_build_reason:
            errors = machine_reasons or reasons or [SCAN_BUILD_FALLBACK_GUIDANCE]
        elif has_ordinary_path_index_reason:
            errors = [PATH_INDEX_STALE_FALLBACK_GUIDANCE]
        else:
            errors = reasons or [STALE_FALLBACK_GUIDANCE]
        return HookResult(
            event="project_cognition.refresh.validate",
            status="blocked",
            severity="critical",
            errors=errors,
            data={"freshness": freshness},
        )
    if state == "support_drift" and normalized in STALE_BLOCK_COMMANDS:
        return HookResult(
            event="project_cognition.refresh.validate",
            status="blocked",
            severity="critical",
            errors=reasons or [SUPPORT_DRIFT_FALLBACK_GUIDANCE],
            data={"freshness": freshness},
        )
    if state == "partial_refresh" and normalized in STALE_BLOCK_COMMANDS:
        return HookResult(
            event="project_cognition.refresh.validate",
            status="blocked",
            severity="critical",
            errors=reasons or [PARTIAL_REFRESH_FALLBACK_GUIDANCE],
            data={"freshness": freshness},
        )
    if readiness == "blocked" and next_action == "run_map_update" and normalized in STALE_BLOCK_COMMANDS:
        return HookResult(
            event="project_cognition.refresh.validate",
            status="blocked",
            severity="critical",
            errors=reasons or [STALE_FALLBACK_GUIDANCE],
            data={"freshness": freshness},
        )
    return HookResult(
        event="project_cognition.refresh.validate",
        status="warn",
        severity="warning",
        warnings=reasons or [NON_STALE_FALLBACK_GUIDANCE.format(state=state or "unknown")],
        data={"freshness": freshness},
    )

def _has_scan_build_allowed_reason(reasons: list[str]) -> bool:
    compact_reason_text = " ".join(str(reason or "") for reason in reasons).lower()
    compact_reason_text = compact_reason_text.replace("-", "_").replace(" ", "_")
    return any(token in compact_reason_text for token in SCAN_BUILD_ALLOWED_REASON_TOKENS)


def mark_dirty_hook(project_root: Path, payload: dict[str, object]) -> HookResult:
    """Record manual dirty fallback state when a complete refresh cannot finish now."""

    reason = str(payload.get("reason") or "").strip()
    if not reason:
        raise QualityHookError("reason is required for project_cognition.mark_dirty")
    scope_paths: list[str] | None = None
    packet_file = str(payload.get("packet_file") or "").strip()
    if packet_file:
        packet_path = Path(packet_file)
        if not packet_path.is_absolute():
            packet_path = (project_root / packet_path).resolve()
        if packet_path.exists():
            packet = worker_task_packet_from_json(packet_path.read_text(encoding="utf-8"))
            scope_paths = list(dict.fromkeys([*packet.scope.write_scope, *packet.scope.read_scope]))
    args = ["mark-dirty", "--reason", reason]
    for option, key in (
        ("--origin-command", "origin_command"),
        ("--origin-feature-dir", "origin_feature_dir"),
        ("--origin-lane-id", "origin_lane_id"),
    ):
        value = str(payload.get(key) or "").strip()
        if value:
            args.extend([option, value])
    for scope_path in scope_paths or []:
        args.extend(["--scope", scope_path])
    args.extend(["--format", "json"])
    status = _run_hook_binary(project_root, args)
    return HookResult(
        event=PROJECT_COGNITION_MARK_DIRTY,
        status="ok",
        severity="info",
        writes={"status_path": str(status.get("status_path", ""))},
        data={"project_cognition_status": status},
    )


def complete_refresh_hook(project_root: Path, _payload: dict[str, object]) -> HookResult:
    """Finalize a successful full refresh against the current git baseline."""

    validation = _run_hook_binary(project_root, ["validate-build", "--format", "json"])
    if validation.get("status") != "ok":
        status = _run_hook_binary(
            project_root,
            ["record-refresh", "--reason", "acceptance-blocked", "--format", "json"],
            blocked_ok=True,
        )
        return HookResult(
            event=PROJECT_COGNITION_COMPLETE_REFRESH,
            status="blocked",
            severity="critical",
            errors=[str(message) for message in validation.get("errors", [])],
            writes={"status_path": str(status.get("status_path", ""))},
            data={
                "validation": validation,
                "freshness": "partial_refresh",
                "readiness": "blocked",
                "recommended_next_action": "run_map_scan_build",
                "project_cognition_status": status,
            },
        )
    status = _run_hook_binary(project_root, ["complete-refresh", "--format", "json"])
    return HookResult(
        event=PROJECT_COGNITION_COMPLETE_REFRESH,
        status="ok",
        severity="info",
        writes={"status_path": str(status.get("status_path", ""))},
        data={"project_cognition_status": status},
    )


def _run_hook_binary(project_root: Path, args: list[str], *, blocked_ok: bool = False) -> dict[str, object]:
    try:
        return run_specify_runtime(["cognition", *args], cwd=project_root, check=not blocked_ok)
    except SpecifyRuntimeError as exc:
        raise QualityHookError(str(exc)) from exc
