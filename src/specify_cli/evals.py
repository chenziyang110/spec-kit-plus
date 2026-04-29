from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

import yaml

from specify_cli.learnings import build_learning_paths, read_learning_entries


EVAL_SCHEMA_VERSION = "1"


@dataclass(frozen=True)
class EvalPaths:
    root: Path
    index: Path
    cases_dir: Path

    def to_dict(self) -> dict[str, str]:
        return {
            "root": str(self.root),
            "index": str(self.index),
            "cases_dir": str(self.cases_dir),
        }


@dataclass
class EvalCase:
    id: str
    recurrence_key: str
    summary: str
    verification_method: str
    target: str = ""
    contains: str = ""
    pattern: str = ""
    command: str = ""
    expect: str = ""
    source_layer: str = "manual"
    recovery_action: str = ""
    created_at: str = ""
    last_run: str = ""
    last_result: str = "pending"

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = now_iso()

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "EvalCase":
        values = {name: payload.get(name, "") for name in cls.__dataclass_fields__}
        return cls(**values)


def now_iso() -> str:
    return datetime.now(tz=UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def build_eval_id() -> str:
    return datetime.now(tz=UTC).strftime("eval-%Y%m%d-%H%M%S-%f")


def build_eval_paths(project_root: Path) -> EvalPaths:
    root = project_root / ".specify" / "evals"
    return EvalPaths(
        root=root,
        index=root / "index.json",
        cases_dir=root / "cases",
    )


def ensure_eval_store(project_root: Path) -> EvalPaths:
    paths = build_eval_paths(project_root)
    paths.cases_dir.mkdir(parents=True, exist_ok=True)
    if not paths.index.exists():
        paths.index.write_text(
            json.dumps(
                {
                    "schema_version": EVAL_SCHEMA_VERSION,
                    "updated_at": now_iso(),
                    "cases": [],
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    return paths


def eval_case_path(paths: EvalPaths, case_id: str) -> Path:
    return paths.cases_dir / f"{case_id}.md"


def render_eval_case(case: EvalCase) -> str:
    frontmatter = yaml.safe_dump(case.to_payload(), sort_keys=False).strip()
    return (
        f"---\n{frontmatter}\n---\n\n"
        "# Eval Case\n\n"
        f"## Summary\n{case.summary}\n\n"
        "## Recovery Action\n"
        f"{case.recovery_action or 'Review the failing assertion and refresh the owning rule or implementation.'}\n"
    )


def split_eval_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        raise ValueError("eval case is missing YAML frontmatter")
    _start, rest = text.split("---\n", 1)
    frontmatter_text, body = rest.split("\n---\n", 1)
    payload = yaml.safe_load(frontmatter_text) or {}
    if not isinstance(payload, dict):
        raise ValueError("eval frontmatter must be a mapping")
    return payload, body


def read_eval_case(path: Path) -> EvalCase:
    payload, _body = split_eval_frontmatter(path.read_text(encoding="utf-8"))
    return EvalCase.from_payload(payload)


def load_eval_cases(project_root: Path) -> list[EvalCase]:
    paths = build_eval_paths(project_root)
    if not paths.cases_dir.exists():
        return []
    return [read_eval_case(path) for path in sorted(paths.cases_dir.glob("*.md"))]


def sync_eval_index(project_root: Path) -> dict[str, Any]:
    paths = ensure_eval_store(project_root)
    cases = load_eval_cases(project_root)
    payload = {
        "schema_version": EVAL_SCHEMA_VERSION,
        "updated_at": now_iso(),
        "cases": [
            {
                "id": case.id,
                "recurrence_key": case.recurrence_key,
                "summary": case.summary,
                "verification_method": case.verification_method,
                "path": str(eval_case_path(paths, case.id)),
                "last_run": case.last_run,
                "last_result": case.last_result,
                "source_layer": case.source_layer,
            }
            for case in cases
        ],
    }
    paths.index.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def write_eval_case(project_root: Path, case: EvalCase) -> Path:
    paths = ensure_eval_store(project_root)
    path = eval_case_path(paths, case.id)
    path.write_text(render_eval_case(case), encoding="utf-8")
    sync_eval_index(project_root)
    return path


def find_learning_source(project_root: Path, recurrence_key: str) -> tuple[str, Any] | None:
    paths = build_learning_paths(project_root)
    for source_layer, path in (
        ("project_rules", paths.project_rules),
        ("project_learnings", paths.project_learnings),
        ("candidates", paths.candidates),
    ):
        if not path.exists():
            continue
        _preamble, entries = read_learning_entries(path)
        for entry in entries:
            if entry.recurrence_key == recurrence_key:
                return source_layer, entry
    return None


def create_eval_case(
    project_root: Path,
    *,
    recurrence_key: str,
    summary: str | None = None,
    verification_method: str | None = None,
    target: str | None = None,
    contains: str | None = None,
    pattern: str | None = None,
    command: str | None = None,
    expect: str | None = None,
    recovery_action: str = "",
) -> dict[str, Any]:
    paths = ensure_eval_store(project_root)
    source_layer = "manual"
    source = find_learning_source(project_root, recurrence_key)
    if source is not None:
        source_layer, entry = source
        if not summary:
            summary = entry.summary
        if verification_method is None and source_layer in {"project_rules", "project_learnings"}:
            verification_method = "rule-check"
            target = target or (
                ".specify/memory/project-rules.md"
                if source_layer == "project_rules"
                else ".specify/memory/project-learnings.md"
            )
            contains = contains or entry.summary
            expect = expect or "found"

    if not summary:
        raise ValueError("summary is required when the recurrence key cannot be inferred from project learning memory")
    if not verification_method:
        raise ValueError("verification_method is required when it cannot be inferred")

    if expect is None:
        expect = {
            "rule-check": "found",
            "file-check": "exists",
            "grep-check": "found",
            "command-check": "pass",
        }.get(verification_method, "")

    case = EvalCase(
        id=build_eval_id(),
        recurrence_key=recurrence_key.strip().lower(),
        summary=summary,
        verification_method=verification_method,
        target=target or "",
        contains=contains or "",
        pattern=pattern or "",
        command=command or "",
        expect=expect or "",
        source_layer=source_layer,
        recovery_action=recovery_action,
    )
    case_path = write_eval_case(project_root, case)
    return {"case": case, "case_path": case_path, "paths": paths}


def eval_status_payload(project_root: Path) -> dict[str, Any]:
    paths = build_eval_paths(project_root)
    cases = load_eval_cases(project_root)
    return {
        "paths": paths.to_dict(),
        "exists": {
            "root": paths.root.exists(),
            "index": paths.index.exists(),
            "cases_dir": paths.cases_dir.exists(),
        },
        "counts": {
            "cases": len(cases),
            "passed": sum(1 for case in cases if case.last_result == "pass"),
            "failed": sum(1 for case in cases if case.last_result == "fail"),
            "skipped": sum(1 for case in cases if case.last_result == "skip"),
            "pending": sum(1 for case in cases if case.last_result == "pending"),
        },
        "cases": [case.to_payload() for case in cases],
    }
