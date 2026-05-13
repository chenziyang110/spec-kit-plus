"""Status contract for the project cognition runtime baseline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path

from .paths import cognition_status_path


@dataclass(slots=True)
class CognitionStatus:
    version: int = 1
    baseline_state: str = "missing"
    baseline_commit: str = ""
    baseline_branch: str = ""
    baseline_built_at: str = ""
    last_update_id: str = ""
    graph_ready: bool = False
    graph_store_path: str = ""
    active_generation_id: str = ""
    query_contract_version: int = 0
    update_contract_version: int = 0
    stale_paths: list[str] = field(default_factory=list)
    stale_reasons: list[str] = field(default_factory=list)
    freshness: str = ""
    last_refresh_reason: str = ""
    last_refresh_topics: list[str] = field(default_factory=list)
    last_refresh_scope: str = ""
    last_refresh_basis: str = ""
    last_refresh_changed_files_basis: list[str] = field(default_factory=list)
    manual_force_stale: bool = False
    manual_force_stale_reasons: list[str] = field(default_factory=list)
    dirty: bool = False
    dirty_reasons: list[str] = field(default_factory=list)
    dirty_origin_command: str = ""
    dirty_origin_feature_dir: str = ""
    dirty_origin_lane_id: str = ""
    dirty_scope_paths: list[str] = field(default_factory=list)


def _coerce_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def write_cognition_status(project_root: Path, status: CognitionStatus) -> Path:
    path = cognition_status_path(project_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(status), indent=2) + "\n", encoding="utf-8")
    return path


def read_cognition_status(project_root: Path) -> CognitionStatus:
    path = cognition_status_path(project_root)
    if not path.exists() or not path.is_file():
        return CognitionStatus()
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return CognitionStatus()
    raw_graph_ready = payload.get("graph_ready", False)
    return CognitionStatus(
        version=int(payload.get("version", 1)),
        baseline_state=str(payload.get("baseline_state", "missing")),
        baseline_commit=str(payload.get("baseline_commit", "")),
        baseline_branch=str(payload.get("baseline_branch", "")),
        baseline_built_at=str(payload.get("baseline_built_at", "")),
        last_update_id=str(payload.get("last_update_id", "")),
        graph_ready=raw_graph_ready if isinstance(raw_graph_ready, bool) else False,
        graph_store_path=str(payload.get("graph_store_path", "")),
        active_generation_id=str(payload.get("active_generation_id", "")),
        query_contract_version=int(payload.get("query_contract_version", 0)),
        update_contract_version=int(payload.get("update_contract_version", 0)),
        stale_paths=_coerce_string_list(payload.get("stale_paths", [])),
        stale_reasons=_coerce_string_list(payload.get("stale_reasons", [])),
        freshness=str(payload.get("freshness", "")),
        last_refresh_reason=str(payload.get("last_refresh_reason", "")),
        last_refresh_topics=_coerce_string_list(payload.get("last_refresh_topics", [])),
        last_refresh_scope=str(payload.get("last_refresh_scope", "")),
        last_refresh_basis=str(payload.get("last_refresh_basis", "")),
        last_refresh_changed_files_basis=_coerce_string_list(payload.get("last_refresh_changed_files_basis", [])),
        manual_force_stale=bool(payload.get("manual_force_stale", payload.get("dirty", False))),
        manual_force_stale_reasons=_coerce_string_list(
            payload.get("manual_force_stale_reasons", payload.get("dirty_reasons", payload.get("stale_reasons", [])))
        ),
        dirty=bool(payload.get("dirty", payload.get("manual_force_stale", False))),
        dirty_reasons=_coerce_string_list(
            payload.get("dirty_reasons", payload.get("manual_force_stale_reasons", payload.get("stale_reasons", [])))
        ),
        dirty_origin_command=str(payload.get("dirty_origin_command", "")),
        dirty_origin_feature_dir=str(payload.get("dirty_origin_feature_dir", "")),
        dirty_origin_lane_id=str(payload.get("dirty_origin_lane_id", "")),
        dirty_scope_paths=_coerce_string_list(payload.get("dirty_scope_paths", [])),
    )
