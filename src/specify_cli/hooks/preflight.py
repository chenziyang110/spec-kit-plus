"""Preflight hooks for workflow entry integrity."""

from __future__ import annotations

from pathlib import Path

from specify_cli.execution import worker_task_packet_from_json
from specify_cli.lanes.state_store import iter_lane_records

from .checkpoint_serializers import normalize_command_name, serialize_workflow_state
from .events import WORKFLOW_PREFLIGHT
from .project_map import project_map_freshness_result
from .types import HookResult, QualityHookError


def workflow_preflight_hook(project_root: Path, payload: dict[str, object]) -> HookResult:
    command_name = normalize_command_name(str(payload.get("command_name") or ""))
    freshness = project_map_freshness_result(project_root, command_name=command_name)
    freshness_payload = freshness.data.get("freshness", {})

    errors = list(freshness.errors)
    warnings = list(freshness.warnings)

    if command_name == "implement":
        raw_feature_dir = str(payload.get("feature_dir") or "").strip()
        if not raw_feature_dir:
            raise QualityHookError("feature_dir is required for implement preflight")
        feature_dir = Path(raw_feature_dir)
        if not feature_dir.is_absolute():
            feature_dir = (project_root / feature_dir).resolve()
        current_scope_paths = _packet_scope_paths(project_root, payload)
        relative_feature_dir = feature_dir.relative_to(project_root).as_posix()
        state_path = feature_dir / "workflow-state.md"
        current_lane_id = ""
        if state_path.exists():
            preview_checkpoint = serialize_workflow_state(state_path)
            current_lane_id = str(preview_checkpoint.get("lane_id") or "").strip()
        if (
            freshness.status == "blocked"
            and str(freshness_payload.get("freshness", "")).strip().lower() == "stale"
            and str(freshness_payload.get("dirty_origin_command", "")).strip().lower() == "implement"
            and (
                (
                    current_lane_id
                    and str(freshness_payload.get("dirty_origin_lane_id", "")).strip()
                    and current_lane_id == str(freshness_payload.get("dirty_origin_lane_id", "")).strip()
                )
                or (
                    (not current_lane_id or not str(freshness_payload.get("dirty_origin_lane_id", "")).strip())
                    and str(freshness_payload.get("dirty_origin_feature_dir", "")).strip() == relative_feature_dir
                )
            )
        ):
            dirty_scope_paths = [str(path).strip() for path in freshness_payload.get("dirty_scope_paths", []) if str(path).strip()]
            if dirty_scope_paths and current_scope_paths:
                if _scope_paths_overlap(dirty_scope_paths, current_scope_paths):
                    warnings.append(
                        "project-map freshness is stale from the current lane's prior implement fallback and overlaps the current packet scope; resume may continue but atlas refresh is still required before other brownfield entrypoints."
                    )
                    warnings.extend(freshness.errors)
                    errors.clear()
                else:
                    errors.append(
                        "project-map freshness is stale from the current lane's prior implement fallback, but the recorded dirty scope does not overlap the current packet scope"
                    )
            else:
                warnings.append(
                    "project-map freshness is stale from the current lane's prior implement fallback; resume may continue but atlas refresh is still required before other brownfield entrypoints."
                )
                warnings.extend(freshness.errors)
                errors.clear()
        if not state_path.exists():
            errors.append(f"workflow-state.md is missing at {state_path}")
        else:
            checkpoint = preview_checkpoint if current_lane_id else serialize_workflow_state(state_path)
            next_command = str(checkpoint.get("next_command") or "").strip()
            if next_command and next_command != "/sp.implement":
                errors.append(
                    f"workflow-state requires {next_command} before /sp.implement may continue"
                )
            if checkpoint.get("active_command") == "sp-analyze" and checkpoint.get("status") != "completed":
                errors.append("analyze gate is still active and has not been cleared")

    if command_name == "integrate":
        from specify_cli.lanes.integration import assess_integration_readiness

        raw_feature_dir = str(payload.get("feature_dir") or "").strip()
        if not raw_feature_dir:
            raise QualityHookError("feature_dir is required for integrate preflight")
        feature_dir = Path(raw_feature_dir)
        if not feature_dir.is_absolute():
            feature_dir = (project_root / feature_dir).resolve()

        lane = next(
            (
                record
                for record in iter_lane_records(project_root)
                if (project_root / record.feature_dir).resolve() == feature_dir.resolve()
            ),
            None,
        )
        if lane is None:
            errors.append(f"no lane record found for feature dir {feature_dir}")
        else:
            readiness = assess_integration_readiness(project_root, lane)
            if not readiness.ready:
                for check in readiness.checks:
                    if check["status"] != "pass":
                        errors.append(f"integrate precheck failed: {check['name']} ({check['detail']})")

    if errors:
        return HookResult(
            event=WORKFLOW_PREFLIGHT,
            status="blocked",
            severity="critical",
            errors=errors,
            warnings=warnings,
            data={"project_map": freshness.to_dict()},
        )
    if warnings:
        return HookResult(
            event=WORKFLOW_PREFLIGHT,
            status="warn",
            severity="warning",
            warnings=warnings,
            data={"project_map": freshness.to_dict()},
        )
    return HookResult(
        event=WORKFLOW_PREFLIGHT,
        status="ok",
        severity="info",
        data={"project_map": freshness.to_dict()},
    )


def _packet_scope_paths(project_root: Path, payload: dict[str, object]) -> list[str]:
    raw = str(payload.get("packet_file") or "").strip()
    if not raw:
        return []
    packet_path = Path(raw)
    if not packet_path.is_absolute():
        packet_path = (project_root / packet_path).resolve()
    if not packet_path.exists():
        return []
    packet = worker_task_packet_from_json(packet_path.read_text(encoding="utf-8"))
    return list(dict.fromkeys([*packet.scope.write_scope, *packet.scope.read_scope]))


def _scope_paths_overlap(left: list[str], right: list[str]) -> bool:
    normalized_left = {_normalize_scope_path(path) for path in left if path}
    normalized_right = {_normalize_scope_path(path) for path in right if path}
    for left_path in normalized_left:
        for right_path in normalized_right:
            left_family = _scope_family(left_path)
            right_family = _scope_family(right_path)
            if (
                left_path == right_path
                or left_path.startswith(f"{right_path}/")
                or right_path.startswith(f"{left_path}/")
                or left_family & right_family
                or ("shared-config" in left_family and _is_runtime_code_path(right_path))
                or ("shared-config" in right_family and _is_runtime_code_path(left_path))
            ):
                return True
    return False


def _normalize_scope_path(path: str) -> str:
    return str(path or "").strip().replace("\\", "/").strip("/")


def _scope_family(path: str) -> set[str]:
    normalized = _normalize_scope_path(path)
    family: set[str] = set()
    parts = [part for part in normalized.split("/") if part]
    filename = parts[-1] if parts else normalized

    if filename in {
        "package.json",
        "package-lock.json",
        "pnpm-lock.yaml",
        "yarn.lock",
        "pyproject.toml",
        "poetry.lock",
        "go.mod",
        "go.sum",
        "cargo.toml",
        "cargo.lock",
        "composer.json",
        "composer.lock",
        "gemfile",
        "gemfile.lock",
        "dockerfile",
        "docker-compose.yml",
        "docker-compose.yaml",
        "makefile",
    } or any(part in {"config", "configs", "settings"} for part in parts):
        family.add("shared-config")

    if any(part in {"workflow", "workflows", "command", "commands", "integration", "integrations", "hook", "hooks"} for part in parts):
        family.add("workflow-surface")

    if normalized.startswith(".github/workflows/") or normalized.startswith("templates/commands/") or normalized.startswith("src/specify_cli/hooks/"):
        family.add("workflow-surface")

    return family


def _is_runtime_code_path(path: str) -> bool:
    parts = [part for part in _normalize_scope_path(path).split("/") if part]
    return bool(parts) and parts[0] in {
        "src",
        "app",
        "apps",
        "server",
        "client",
        "web",
        "ui",
        "frontend",
        "backend",
        "lib",
        "libs",
        "tests",
        "scripts",
        "templates",
        "tools",
        "extensions",
        "presets",
    }
