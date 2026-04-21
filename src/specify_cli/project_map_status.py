"""Project-map freshness status helpers.

This module centralizes the status-file contract used by the handbook/project-map
freshness helpers so Python call sites can reason about the same state without
shelling out.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
from typing import Any


STATUS_FILENAME = "status.json"


def project_map_dir(project_root: Path) -> Path:
    return project_root / ".specify" / "project-map"


def project_map_status_path(project_root: Path) -> Path:
    return project_map_dir(project_root) / STATUS_FILENAME


def canonical_project_map_paths(project_root: Path) -> list[Path]:
    project_map_root = project_map_dir(project_root)
    return [
        project_root / "PROJECT-HANDBOOK.md",
        project_map_root / "ARCHITECTURE.md",
        project_map_root / "STRUCTURE.md",
        project_map_root / "CONVENTIONS.md",
        project_map_root / "INTEGRATIONS.md",
        project_map_root / "WORKFLOWS.md",
        project_map_root / "TESTING.md",
        project_map_root / "OPERATIONS.md",
    ]


def missing_canonical_project_map_paths(project_root: Path) -> list[Path]:
    return [path for path in canonical_project_map_paths(project_root) if not path.exists()]


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def classify_changed_path(path: str) -> str:
    lower = path.lower()

    high_impact_exact = {
        "project-handbook.md",
        ".specify/templates/project-handbook-template.md",
        ".specify/memory/constitution.md",
        ".specify/extensions.yml",
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
    }
    if lower == ".specify/project-map/status.json":
        return "ignore"
    if lower in high_impact_exact:
        return "stale"

    high_impact_prefixes = (
        ".specify/project-map/",
        ".specify/templates/project-map/",
        ".github/workflows/",
    )
    if lower.startswith(high_impact_prefixes):
        return "stale"

    high_impact_terms = (
        "route",
        "routes",
        "router",
        "routing",
        "url",
        "urls",
        "endpoint",
        "endpoints",
        "api",
        "schema",
        "schemas",
        "contract",
        "contracts",
        "type",
        "types",
        "interface",
        "interfaces",
        "registry",
        "registries",
        "manifest",
        "manifests",
        "config",
        "configs",
        "settings",
        "workflow",
        "workflows",
        "command",
        "commands",
        "integration",
        "integrations",
        "adapter",
        "adapters",
        "middleware",
        "export",
        "exports",
        "index",
    )
    path_parts = [part for part in lower.replace("\\", "/").split("/") if part]
    for part in path_parts:
        stem = part.split(".", 1)[0]
        if stem in high_impact_terms:
            return "stale"

    medium_terms = (
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
        "scripts",
        "tests",
        "docs",
        "specs",
    )
    if any(part in medium_terms for part in path_parts):
        return "possibly_stale"

    return "ignore"


@dataclass(slots=True)
class ProjectMapStatus:
    version: int = 1
    last_mapped_commit: str = ""
    last_mapped_at: str = ""
    last_mapped_branch: str = ""
    freshness: str = "missing"
    last_refresh_reason: str = ""
    dirty: bool = False
    dirty_reasons: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "last_mapped_commit": self.last_mapped_commit,
            "last_mapped_at": self.last_mapped_at,
            "last_mapped_branch": self.last_mapped_branch,
            "freshness": self.freshness,
            "last_refresh_reason": self.last_refresh_reason,
            "dirty": self.dirty,
            "dirty_reasons": list(self.dirty_reasons or []),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectMapStatus":
        return cls(
            version=int(data.get("version", 1)),
            last_mapped_commit=str(data.get("last_mapped_commit", "")),
            last_mapped_at=str(data.get("last_mapped_at", "")),
            last_mapped_branch=str(data.get("last_mapped_branch", "")),
            freshness=str(data.get("freshness", "missing")),
            last_refresh_reason=str(data.get("last_refresh_reason", "")),
            dirty=bool(data.get("dirty", False)),
            dirty_reasons=list(data.get("dirty_reasons", []) or []),
        )


def read_project_map_status(project_root: Path) -> ProjectMapStatus:
    status_path = project_map_status_path(project_root)
    if not status_path.exists():
        return ProjectMapStatus()
    try:
        payload = json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ProjectMapStatus()
    if not isinstance(payload, dict):
        return ProjectMapStatus()
    return ProjectMapStatus.from_dict(payload)


def write_project_map_status(project_root: Path, status: ProjectMapStatus) -> Path:
    status_path = project_map_status_path(project_root)
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps(status.to_dict(), indent=2) + "\n", encoding="utf-8")
    return status_path


def mark_project_map_refreshed(
    project_root: Path,
    *,
    head_commit: str,
    branch: str,
    reason: str,
    mapped_at: str | None = None,
) -> ProjectMapStatus:
    status = ProjectMapStatus(
        last_mapped_commit=head_commit,
        last_mapped_at=mapped_at or iso_now(),
        last_mapped_branch=branch,
        freshness="fresh",
        last_refresh_reason=reason,
        dirty=False,
        dirty_reasons=[],
    )
    write_project_map_status(project_root, status)
    return status


def complete_project_map_refresh(project_root: Path) -> ProjectMapStatus:
    return mark_project_map_refreshed(
        project_root,
        head_commit=git_head_commit(project_root),
        branch=git_branch_name(project_root),
        reason="map-codebase",
    )


def mark_project_map_dirty(project_root: Path, reason: str) -> ProjectMapStatus:
    status = read_project_map_status(project_root)
    reasons = list(status.dirty_reasons or [])
    if reason and reason not in reasons:
        reasons.append(reason)
    status.dirty = True
    status.freshness = "stale"
    status.dirty_reasons = reasons
    if not status.last_mapped_at:
        status.last_mapped_at = iso_now()
    if not status.last_refresh_reason:
        status.last_refresh_reason = "manual"
    write_project_map_status(project_root, status)
    return status


def clear_project_map_dirty(project_root: Path) -> ProjectMapStatus:
    status = read_project_map_status(project_root)
    status.dirty = False
    status.freshness = "fresh"
    status.dirty_reasons = []
    write_project_map_status(project_root, status)
    return status


def assess_project_map_freshness(
    project_root: Path,
    *,
    head_commit: str,
    changed_files: list[str],
    has_git: bool,
) -> dict[str, Any]:
    status = read_project_map_status(project_root)

    if not project_map_status_path(project_root).exists():
        return {
            "freshness": "missing",
            "status_path": str(project_map_status_path(project_root)),
            "head_commit": head_commit,
            "last_mapped_commit": "",
            "dirty": False,
            "dirty_reasons": [],
            "reasons": ["project-map status missing"],
            "changed_files": [],
        }

    if status.dirty:
        return {
            "freshness": "stale",
            "status_path": str(project_map_status_path(project_root)),
            "head_commit": head_commit,
            "last_mapped_commit": status.last_mapped_commit,
            "dirty": True,
            "dirty_reasons": list(status.dirty_reasons or []),
            "reasons": list(status.dirty_reasons or []),
            "changed_files": [],
        }

    if not has_git or not status.last_mapped_commit or not head_commit:
        return {
            "freshness": "possibly_stale",
            "status_path": str(project_map_status_path(project_root)),
            "head_commit": head_commit,
            "last_mapped_commit": status.last_mapped_commit,
            "dirty": False,
            "dirty_reasons": [],
            "reasons": ["git baseline unavailable for project-map freshness"],
            "changed_files": [],
        }

    worst = "fresh"
    reasons: list[str] = []
    considered: list[str] = []

    for changed in changed_files:
        classification = classify_changed_path(changed)
        considered.append(changed)
        if classification == "stale":
            worst = "stale"
            reasons.append(f"high-impact project-map change: {changed}")
        elif classification == "possibly_stale" and worst != "stale":
            worst = "possibly_stale"
            reasons.append(f"codebase surface changed since last map: {changed}")

    if worst == "fresh":
        reasons = []

    return {
        "freshness": worst,
        "status_path": str(project_map_status_path(project_root)),
        "head_commit": head_commit,
        "last_mapped_commit": status.last_mapped_commit,
        "dirty": False,
        "dirty_reasons": [],
        "reasons": reasons,
        "changed_files": considered,
    }


def git_head_commit(project_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(project_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""
    return result.stdout.strip()


def git_branch_name(project_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(project_root), "rev-parse", "--abbrev-ref", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return ""
    return result.stdout.strip()


def has_git_repo(project_root: Path) -> bool:
    try:
        subprocess.run(
            ["git", "-C", str(project_root), "rev-parse", "--is-inside-work-tree"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False
    return True


def collect_changed_files(project_root: Path, *, last_mapped_commit: str, head_commit: str) -> list[str]:
    if not last_mapped_commit or not head_commit:
        return []

    commands = [
        ["git", "-C", str(project_root), "diff", "--name-status", "--find-renames", f"{last_mapped_commit}..{head_commit}"],
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

    return changed


def inspect_project_map_freshness(project_root: Path) -> dict[str, Any]:
    status = read_project_map_status(project_root)
    has_git = has_git_repo(project_root)
    head_commit = git_head_commit(project_root) if has_git else ""
    changed_files = collect_changed_files(
        project_root,
        last_mapped_commit=status.last_mapped_commit,
        head_commit=head_commit,
    ) if has_git else []
    return assess_project_map_freshness(
        project_root,
        head_commit=head_commit,
        changed_files=changed_files,
        has_git=has_git,
    )
