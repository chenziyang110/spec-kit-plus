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
    stale_paths: list[str] = field(default_factory=list)
    stale_reasons: list[str] = field(default_factory=list)


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
        stale_paths=_coerce_string_list(payload.get("stale_paths", [])),
        stale_reasons=_coerce_string_list(payload.get("stale_reasons", [])),
    )
