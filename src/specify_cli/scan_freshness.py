"""Shared scan freshness status helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import subprocess
from typing import Any

import pathspec


COGNITIONIGNORE_FILENAMES = (
    ".cognitionignore",
    ".specify/project-cognition/.cognitionignore",
)


@dataclass(slots=True)
class ScanFreshnessStatus:
    status_family: str
    version: int = 1
    freshness: str = "missing"
    last_refresh_commit: str = ""
    last_refresh_branch: str = ""
    last_refresh_at: str = ""
    last_refresh_scope: str = "full"
    last_refresh_basis: str = ""
    last_refresh_changed_files_basis: list[str] = field(default_factory=list)
    manual_force_stale: bool = False
    manual_force_stale_reasons: list[str] = field(default_factory=list)
    raw_payload: dict[str, Any] = field(default_factory=dict, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "status_family": self.status_family,
            "freshness": self.freshness,
            "last_refresh_commit": self.last_refresh_commit,
            "last_refresh_branch": self.last_refresh_branch,
            "last_refresh_at": self.last_refresh_at,
            "last_refresh_scope": self.last_refresh_scope,
            "last_refresh_basis": self.last_refresh_basis,
            "last_refresh_changed_files_basis": list(self.last_refresh_changed_files_basis),
            "manual_force_stale": self.manual_force_stale,
            "manual_force_stale_reasons": list(self.manual_force_stale_reasons),
        }


def write_scan_status(status_path: Path, status: ScanFreshnessStatus) -> Path:
    return write_scan_payload(status_path, status.to_dict())


def write_scan_payload(status_path: Path, payload: dict[str, Any]) -> Path:
    status_path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, indent=2) + "\n"
    status_path.write_text(serialized, encoding="utf-8")
    return status_path


def read_scan_status(status_path: Path, *, status_family: str) -> ScanFreshnessStatus:
    try:
        payload = json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ScanFreshnessStatus(status_family=status_family)
    if not isinstance(payload, dict):
        return ScanFreshnessStatus(status_family=status_family)
    return _status_from_payload(payload, status_family=status_family)


def _status_from_payload(payload: dict[str, Any], *, status_family: str) -> ScanFreshnessStatus:
    global_payload = payload.get("global")
    if isinstance(global_payload, dict):
        dirty_reasons = list(
            global_payload.get("dirty_reasons")
            or global_payload.get("stale_reasons")
            or []
        )
        return ScanFreshnessStatus(
            status_family=status_family,
            version=int(payload.get("version", 1)),
            freshness=str(global_payload.get("freshness", "missing")),
            last_refresh_commit=str(global_payload.get("last_refresh_commit", "")),
            last_refresh_branch=str(global_payload.get("last_refresh_branch", "")),
            last_refresh_at=str(global_payload.get("last_refresh_at", "")),
            last_refresh_scope=str(global_payload.get("last_refresh_scope", "full")),
            last_refresh_basis=str(global_payload.get("last_refresh_basis", "")),
            last_refresh_changed_files_basis=list(global_payload.get("last_refresh_changed_files_basis", []) or []),
            manual_force_stale=bool(global_payload.get("dirty", False)),
            manual_force_stale_reasons=dirty_reasons,
            raw_payload=dict(payload),
        )

    manual_reasons = list(
        payload.get("manual_force_stale_reasons")
        or payload.get("dirty_reasons")
        or payload.get("stale_reasons")
        or []
    )
    return ScanFreshnessStatus(
        status_family=str(payload.get("status_family", status_family)),
        version=int(payload.get("version", 1)),
        freshness=str(payload.get("freshness", "missing")),
        last_refresh_commit=str(payload.get("last_refresh_commit", payload.get("last_mapped_commit", ""))),
        last_refresh_branch=str(payload.get("last_refresh_branch", payload.get("last_mapped_branch", ""))),
        last_refresh_at=str(payload.get("last_refresh_at", payload.get("last_mapped_at", ""))),
        last_refresh_scope=str(payload.get("last_refresh_scope", "full")),
        last_refresh_basis=str(payload.get("last_refresh_basis", "")),
        last_refresh_changed_files_basis=list(payload.get("last_refresh_changed_files_basis", []) or []),
        manual_force_stale=bool(payload.get("manual_force_stale", payload.get("dirty", False))),
        manual_force_stale_reasons=manual_reasons,
        raw_payload=dict(payload),
    )


def collect_git_changed_files(
    project_root: Path,
    *,
    baseline_commit: str,
    head_commit: str = "HEAD",
    use_cognitionignore: bool = False,
) -> list[str]:
    if not baseline_commit or not head_commit:
        return []

    commands = [
        ["git", "-C", str(project_root), "diff", "--name-status", "--find-renames", f"{baseline_commit}..{head_commit}"],
        ["git", "-C", str(project_root), "diff", "--name-status", "--find-renames", "--cached"],
        ["git", "-C", str(project_root), "diff", "--name-status", "--find-renames"],
        ["git", "-C", str(project_root), "ls-files", "--others", "--exclude-standard"],
    ]

    changed: list[str] = []
    seen: set[str] = set()
    for index, command in enumerate(commands):
        try:
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue

        for raw_line in result.stdout.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            if index == 3:
                candidate = line
            else:
                parts = line.split("\t")
                if len(parts) < 2:
                    continue
                status_code = parts[0]
                candidate = parts[2] if status_code.startswith("R") and len(parts) >= 3 else parts[1]

            normalized = candidate.replace("\\", "/")
            if normalized not in seen:
                seen.add(normalized)
                changed.append(normalized)

    if use_cognitionignore:
        return filter_cognition_ignored_paths(project_root, changed)
    return changed


def filter_cognition_ignored_paths(project_root: Path, paths: list[str]) -> list[str]:
    """Return paths not excluded by project cognition ignore rules."""

    ignore_spec = load_cognition_ignore_spec(project_root)
    if ignore_spec is None:
        return list(paths)

    filtered: list[str] = []
    for path in paths:
        normalized = _normalize_cognition_path(path)
        if not normalized:
            continue
        if not ignore_spec.match_file(normalized):
            filtered.append(normalized)
    return filtered


def cognition_ignored_paths(project_root: Path, paths: list[str]) -> list[str]:
    """Return paths excluded by project cognition ignore rules."""

    ignore_spec = load_cognition_ignore_spec(project_root)
    if ignore_spec is None:
        return []
    ignored: list[str] = []
    for path in paths:
        normalized = _normalize_cognition_path(path)
        if normalized and ignore_spec.match_file(normalized):
            ignored.append(normalized)
    return ignored


def load_cognition_ignore_spec(project_root: Path) -> pathspec.GitIgnoreSpec | None:
    """Load gitignore-compatible project cognition ignore patterns."""

    lines: list[str] = []
    for relative_ignore_path in COGNITIONIGNORE_FILENAMES:
        ignore_path = project_root / relative_ignore_path
        if not ignore_path.exists() or not ignore_path.is_file():
            continue
        for line in ignore_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                lines.append(stripped.replace("\\", "/"))
            else:
                lines.append(line)

    if not lines:
        return None
    return pathspec.GitIgnoreSpec.from_lines(lines)


def _normalize_cognition_path(path: str) -> str:
    return str(path or "").strip().replace("\\", "/").strip("/")
