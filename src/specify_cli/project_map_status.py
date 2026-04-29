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
INDEX_DIRNAME = "index"
ROOT_DIRNAME = "root"
MODULES_DIRNAME = "modules"
TOPIC_FILES = (
    "ARCHITECTURE.md",
    "STRUCTURE.md",
    "CONVENTIONS.md",
    "INTEGRATIONS.md",
    "OPERATIONS.md",
    "WORKFLOWS.md",
    "TESTING.md",
)
INDEX_FILES = (
    "atlas-index.json",
    "modules.json",
    "relations.json",
    STATUS_FILENAME,
)
DIRTY_REASON_ALIASES = {
    "shared surface changed": "shared_surface_changed",
    "shared_surface_changed": "shared_surface_changed",
    "architecture surface changed": "architecture_surface_changed",
    "architecture_surface_changed": "architecture_surface_changed",
    "integration boundary changed": "integration_boundary_changed",
    "integration_boundary_changed": "integration_boundary_changed",
    "workflow contract changed": "workflow_contract_changed",
    "workflow_contract_changed": "workflow_contract_changed",
    "verification surface changed": "verification_surface_changed",
    "verification_surface_changed": "verification_surface_changed",
    "runtime invariant changed": "runtime_invariant_changed",
    "runtime_invariant_changed": "runtime_invariant_changed",
}


def project_map_dir(project_root: Path) -> Path:
    return project_root / ".specify" / "project-map"


def project_map_index_dir(project_root: Path) -> Path:
    return project_map_dir(project_root) / INDEX_DIRNAME


def project_map_root_dir(project_root: Path) -> Path:
    return project_map_dir(project_root) / ROOT_DIRNAME


def project_map_modules_dir(project_root: Path) -> Path:
    return project_map_dir(project_root) / MODULES_DIRNAME


def project_map_status_path(project_root: Path) -> Path:
    return project_map_index_dir(project_root) / STATUS_FILENAME


def legacy_project_map_status_path(project_root: Path) -> Path:
    return project_map_dir(project_root) / STATUS_FILENAME


def canonical_project_map_paths(project_root: Path) -> list[Path]:
    project_map_index_root = project_map_index_dir(project_root)
    project_map_root = project_map_root_dir(project_root)
    return [
        project_root / "PROJECT-HANDBOOK.md",
        project_map_index_root / "atlas-index.json",
        project_map_index_root / "modules.json",
        project_map_index_root / "relations.json",
        project_map_index_root / STATUS_FILENAME,
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


def normalize_dirty_reason(reason: str) -> str:
    normalized = " ".join((reason or "").strip().lower().replace("-", " ").replace("_", " ").split())
    if not normalized:
        return "project_map_dirty"
    return DIRTY_REASON_ALIASES.get(normalized, normalized.replace(" ", "_"))


def refresh_plan_for_dirty_reason(reason: str) -> dict[str, list[str]]:
    canonical = normalize_dirty_reason(reason)
    mapping = {
        "shared_surface_changed": {
            "must_refresh_topics": ["ARCHITECTURE.md", "STRUCTURE.md"],
            "review_topics": ["INTEGRATIONS.md", "WORKFLOWS.md", "TESTING.md"],
        },
        "architecture_surface_changed": {
            "must_refresh_topics": ["ARCHITECTURE.md"],
            "review_topics": ["STRUCTURE.md", "WORKFLOWS.md", "TESTING.md"],
        },
        "integration_boundary_changed": {
            "must_refresh_topics": ["INTEGRATIONS.md"],
            "review_topics": ["ARCHITECTURE.md", "OPERATIONS.md", "TESTING.md"],
        },
        "workflow_contract_changed": {
            "must_refresh_topics": ["WORKFLOWS.md"],
            "review_topics": ["ARCHITECTURE.md", "INTEGRATIONS.md", "TESTING.md"],
        },
        "verification_surface_changed": {
            "must_refresh_topics": ["TESTING.md"],
            "review_topics": ["ARCHITECTURE.md", "WORKFLOWS.md"],
        },
        "runtime_invariant_changed": {
            "must_refresh_topics": ["OPERATIONS.md"],
            "review_topics": ["INTEGRATIONS.md", "TESTING.md"],
        },
    }
    return mapping.get(
        canonical,
        {
            "must_refresh_topics": ["ARCHITECTURE.md"],
            "review_topics": ["TESTING.md"],
        },
    )


def _merged_dirty_reason_topics(reasons: list[str]) -> dict[str, list[str]]:
    must_refresh: list[str] = []
    review: list[str] = []
    for reason in reasons:
        plan = refresh_plan_for_dirty_reason(reason)
        for topic in plan["must_refresh_topics"]:
            if topic not in must_refresh:
                must_refresh.append(topic)
        for topic in plan["review_topics"]:
            if topic not in review:
                review.append(topic)
    return {
        "must_refresh_topics": [topic for topic in TOPIC_FILES if topic in must_refresh],
        "review_topics": [topic for topic in TOPIC_FILES if topic in review],
    }


def classify_changed_path(path: str) -> str:
    lower = path.lower().replace("\\", "/")

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
    if lower in {
        ".specify/project-map/status.json",
        ".specify/project-map/index/status.json",
    }:
        return "ignore"
    if lower in high_impact_exact:
        return "stale"

    high_impact_prefixes = (
        ".specify/project-map/root/",
        ".specify/project-map/modules/",
        ".specify/project-map/index/",
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
    path_parts = [part for part in lower.split("/") if part]
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


def suggested_topics_for_changed_path(path: str) -> list[str]:
    plan = refresh_plan_for_changed_path(path)
    return [topic for topic in TOPIC_FILES if topic in (*plan["must_refresh_topics"], *plan["review_topics"])]


def refresh_plan_for_changed_path(path: str) -> dict[str, list[str]]:
    lower = path.lower().replace("\\", "/")
    classification = classify_changed_path(path)
    if classification == "ignore":
        return {"must_refresh_topics": [], "review_topics": []}

    must_refresh: list[str] = []
    review: list[str] = []
    specific_boundary_hit = False

    def add(target: list[str], *names: str) -> None:
        for name in names:
            if name not in target:
                target.append(name)

    if lower in {
        "project-handbook.md",
        ".specify/project-map/root/architecture.md",
        ".specify/project-map/architecture.md",
    }:
        add(must_refresh, "ARCHITECTURE.md")
    if lower in {".specify/project-map/root/structure.md", ".specify/project-map/structure.md"}:
        add(must_refresh, "STRUCTURE.md")
    if lower in {".specify/project-map/root/conventions.md", ".specify/project-map/conventions.md"}:
        add(must_refresh, "CONVENTIONS.md")
    if lower in {".specify/project-map/root/integrations.md", ".specify/project-map/integrations.md"}:
        add(must_refresh, "INTEGRATIONS.md")
    if lower in {".specify/project-map/root/workflows.md", ".specify/project-map/workflows.md"}:
        add(must_refresh, "WORKFLOWS.md")
    if lower in {".specify/project-map/root/testing.md", ".specify/project-map/testing.md"}:
        add(must_refresh, "TESTING.md")
    if lower in {".specify/project-map/root/operations.md", ".specify/project-map/operations.md"}:
        add(must_refresh, "OPERATIONS.md")

    path_parts = [part for part in lower.split("/") if part]
    filename = path_parts[-1] if path_parts else lower

    if any(term in path_parts for term in ("route", "routes", "router", "routing", "api", "endpoint", "endpoints", "workflow", "workflows", "command", "commands")):
        specific_boundary_hit = True
        add(must_refresh, "INTEGRATIONS.md", "WORKFLOWS.md")
        add(review, "ARCHITECTURE.md", "TESTING.md")
    if any(term in path_parts for term in ("schema", "schemas", "contract", "contracts", "type", "types", "interface", "interfaces", "manifest", "manifests", "adapter", "adapters", "middleware", "export", "exports")):
        specific_boundary_hit = True
        add(must_refresh, "INTEGRATIONS.md")
        add(review, "ARCHITECTURE.md", "TESTING.md")
    if any(term in path_parts for term in ("config", "configs", "settings")) or filename in {
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
    }:
        add(must_refresh, "CONVENTIONS.md", "INTEGRATIONS.md", "OPERATIONS.md")
        add(review, "TESTING.md")
    if filename in {"dockerfile", "docker-compose.yml", "docker-compose.yaml", "makefile"}:
        add(must_refresh, "INTEGRATIONS.md", "OPERATIONS.md")
        add(review, "TESTING.md")
    if not specific_boundary_hit and any(term in path_parts for term in ("src", "app", "apps", "server", "client", "web", "ui", "frontend", "backend", "lib", "libs")):
        add(must_refresh, "STRUCTURE.md")
        add(review, "ARCHITECTURE.md", "TESTING.md")
    if any(term in path_parts for term in ("scripts",)):
        add(must_refresh, "OPERATIONS.md")
        add(review, "STRUCTURE.md", "TESTING.md")
    if any(term in path_parts for term in ("tests",)):
        add(must_refresh, "TESTING.md")
        add(review, "ARCHITECTURE.md")
    if any(term in path_parts for term in ("docs", "specs")):
        add(must_refresh, "WORKFLOWS.md")
        add(review, "ARCHITECTURE.md")

    if classification == "stale" and not must_refresh and not review:
        add(must_refresh, "ARCHITECTURE.md")
        add(review, "TESTING.md")
    elif classification == "possibly_stale" and not must_refresh and not review:
        add(must_refresh, "STRUCTURE.md")
        add(review, "ARCHITECTURE.md", "TESTING.md")

    return {
        "must_refresh_topics": [topic for topic in TOPIC_FILES if topic in must_refresh],
        "review_topics": [topic for topic in TOPIC_FILES if topic in review],
    }


@dataclass(init=False, slots=True)
class ProjectMapStatus:
    version: int
    global_freshness: str
    global_last_refresh_commit: str
    global_last_refresh_at: str
    global_last_refresh_branch: str
    global_last_refresh_reason: str
    global_last_refresh_topics: list[str] | None
    global_last_refresh_scope: str
    global_last_refresh_basis: str
    global_last_refresh_changed_files_basis: list[str] | None
    global_dirty: bool
    global_dirty_reasons: list[str] | None
    global_stale_reasons: list[str] | None
    global_affected_root_docs: list[str] | None
    modules: dict[str, dict[str, Any]] | None

    def __init__(
        self,
        *,
        version: int = 2,
        global_freshness: str = "missing",
        global_last_refresh_commit: str = "",
        global_last_refresh_at: str = "",
        global_last_refresh_branch: str = "",
        global_last_refresh_reason: str = "",
        global_last_refresh_topics: list[str] | None = None,
        global_last_refresh_scope: str = "full",
        global_last_refresh_basis: str = "",
        global_last_refresh_changed_files_basis: list[str] | None = None,
        global_dirty: bool = False,
        global_dirty_reasons: list[str] | None = None,
        global_stale_reasons: list[str] | None = None,
        global_affected_root_docs: list[str] | None = None,
        modules: dict[str, dict[str, Any]] | None = None,
        last_mapped_commit: str | None = None,
        last_mapped_at: str | None = None,
        last_mapped_branch: str | None = None,
        freshness: str | None = None,
        last_refresh_reason: str | None = None,
        last_refresh_topics: list[str] | None = None,
        last_refresh_scope: str | None = None,
        last_refresh_basis: str | None = None,
        last_refresh_changed_files_basis: list[str] | None = None,
        dirty: bool | None = None,
        dirty_reasons: list[str] | None = None,
    ) -> None:
        self.version = int(version)
        self.global_freshness = freshness if freshness is not None else global_freshness
        self.global_last_refresh_commit = (
            last_mapped_commit if last_mapped_commit is not None else global_last_refresh_commit
        )
        self.global_last_refresh_at = (
            last_mapped_at if last_mapped_at is not None else global_last_refresh_at
        )
        self.global_last_refresh_branch = (
            last_mapped_branch if last_mapped_branch is not None else global_last_refresh_branch
        )
        self.global_last_refresh_reason = (
            last_refresh_reason if last_refresh_reason is not None else global_last_refresh_reason
        )
        self.global_last_refresh_topics = list(
            last_refresh_topics if last_refresh_topics is not None else (global_last_refresh_topics or [])
        )
        self.global_last_refresh_scope = (
            last_refresh_scope if last_refresh_scope is not None else global_last_refresh_scope
        )
        self.global_last_refresh_basis = (
            last_refresh_basis if last_refresh_basis is not None else global_last_refresh_basis
        )
        self.global_last_refresh_changed_files_basis = list(
            last_refresh_changed_files_basis
            if last_refresh_changed_files_basis is not None
            else (global_last_refresh_changed_files_basis or [])
        )
        self.global_dirty = dirty if dirty is not None else global_dirty
        resolved_global_reasons = (
            dirty_reasons
            if dirty_reasons is not None
            else (
                global_dirty_reasons
                if global_dirty_reasons is not None
                else global_stale_reasons
            )
        )
        self.global_dirty_reasons = list(
            resolved_global_reasons or []
        )
        self.global_stale_reasons = list(self.global_dirty_reasons)
        self.global_affected_root_docs = list(global_affected_root_docs or [])
        self.modules = dict(modules or {})

    @property
    def last_mapped_commit(self) -> str:
        return self.global_last_refresh_commit

    @last_mapped_commit.setter
    def last_mapped_commit(self, value: str) -> None:
        self.global_last_refresh_commit = value

    @property
    def last_mapped_at(self) -> str:
        return self.global_last_refresh_at

    @last_mapped_at.setter
    def last_mapped_at(self, value: str) -> None:
        self.global_last_refresh_at = value

    @property
    def last_mapped_branch(self) -> str:
        return self.global_last_refresh_branch

    @last_mapped_branch.setter
    def last_mapped_branch(self, value: str) -> None:
        self.global_last_refresh_branch = value

    @property
    def freshness(self) -> str:
        return self.global_freshness

    @freshness.setter
    def freshness(self, value: str) -> None:
        self.global_freshness = value

    @property
    def last_refresh_reason(self) -> str:
        return self.global_last_refresh_reason

    @last_refresh_reason.setter
    def last_refresh_reason(self, value: str) -> None:
        self.global_last_refresh_reason = value

    @property
    def last_refresh_topics(self) -> list[str]:
        return list(self.global_last_refresh_topics or [])

    @last_refresh_topics.setter
    def last_refresh_topics(self, value: list[str] | None) -> None:
        self.global_last_refresh_topics = list(value or [])

    @property
    def last_refresh_scope(self) -> str:
        return self.global_last_refresh_scope

    @last_refresh_scope.setter
    def last_refresh_scope(self, value: str) -> None:
        self.global_last_refresh_scope = value

    @property
    def last_refresh_basis(self) -> str:
        return self.global_last_refresh_basis

    @last_refresh_basis.setter
    def last_refresh_basis(self, value: str) -> None:
        self.global_last_refresh_basis = value

    @property
    def last_refresh_changed_files_basis(self) -> list[str]:
        return list(self.global_last_refresh_changed_files_basis or [])

    @last_refresh_changed_files_basis.setter
    def last_refresh_changed_files_basis(self, value: list[str] | None) -> None:
        self.global_last_refresh_changed_files_basis = list(value or [])

    @property
    def dirty(self) -> bool:
        return self.global_dirty

    @dirty.setter
    def dirty(self, value: bool) -> None:
        self.global_dirty = value

    @property
    def dirty_reasons(self) -> list[str]:
        return list(self.global_dirty_reasons or [])

    @dirty_reasons.setter
    def dirty_reasons(self, value: list[str] | None) -> None:
        self.global_dirty_reasons = list(value or [])

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "global": {
                "freshness": self.global_freshness,
                "last_refresh_commit": self.global_last_refresh_commit,
                "last_refresh_at": self.global_last_refresh_at,
                "last_refresh_branch": self.global_last_refresh_branch,
                "last_refresh_reason": self.global_last_refresh_reason,
                "last_refresh_topics": list(self.global_last_refresh_topics or []),
                "last_refresh_scope": self.global_last_refresh_scope,
                "last_refresh_basis": self.global_last_refresh_basis,
                "last_refresh_changed_files_basis": list(self.global_last_refresh_changed_files_basis or []),
                "dirty": self.global_dirty,
                "dirty_reasons": list(self.global_dirty_reasons or []),
                "stale_reasons": list(self.global_dirty_reasons or []),
                "affected_root_docs": list(self.global_affected_root_docs or []),
            },
            "modules": dict(self.modules or {}),
            # Legacy flat compatibility keys:
            "last_mapped_commit": self.last_mapped_commit,
            "last_mapped_at": self.last_mapped_at,
            "last_mapped_branch": self.last_mapped_branch,
            "freshness": self.freshness,
            "last_refresh_reason": self.last_refresh_reason,
            "last_refresh_topics": self.last_refresh_topics,
            "last_refresh_scope": self.last_refresh_scope,
            "last_refresh_basis": self.last_refresh_basis,
            "last_refresh_changed_files_basis": self.last_refresh_changed_files_basis,
            "dirty": self.dirty,
            "dirty_reasons": self.dirty_reasons,
            "stale_reasons": self.dirty_reasons,
            "affected_root_docs": list(self.global_affected_root_docs or []),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectMapStatus":
        global_payload = data.get("global")
        if isinstance(global_payload, dict):
            return cls(
                version=int(data.get("version", 2)),
                global_freshness=str(global_payload.get("freshness", "missing")),
                global_last_refresh_commit=str(global_payload.get("last_refresh_commit", "")),
                global_last_refresh_at=str(global_payload.get("last_refresh_at", "")),
                global_last_refresh_branch=str(global_payload.get("last_refresh_branch", "")),
                global_last_refresh_reason=str(global_payload.get("last_refresh_reason", "")),
                global_last_refresh_topics=list(global_payload.get("last_refresh_topics", []) or []),
                global_last_refresh_scope=str(global_payload.get("last_refresh_scope", "full")),
                global_last_refresh_basis=str(global_payload.get("last_refresh_basis", "")),
                global_last_refresh_changed_files_basis=list(global_payload.get("last_refresh_changed_files_basis", []) or []),
                global_dirty=bool(global_payload.get("dirty", False)),
                global_dirty_reasons=list(global_payload.get("dirty_reasons", []) or []),
                global_stale_reasons=list(global_payload.get("stale_reasons", []) or []),
                global_affected_root_docs=list(global_payload.get("affected_root_docs", []) or []),
                modules=dict(data.get("modules", {}) or {}),
            )

        return cls(
            version=int(data.get("version", 1)),
            last_mapped_commit=str(data.get("last_mapped_commit", "")),
            last_mapped_at=str(data.get("last_mapped_at", "")),
            last_mapped_branch=str(data.get("last_mapped_branch", "")),
            freshness=str(data.get("freshness", "missing")),
            last_refresh_reason=str(data.get("last_refresh_reason", "")),
            last_refresh_topics=list(data.get("last_refresh_topics", []) or []),
            last_refresh_scope=str(data.get("last_refresh_scope", "full")),
            last_refresh_basis=str(data.get("last_refresh_basis", "")),
            last_refresh_changed_files_basis=list(data.get("last_refresh_changed_files_basis", []) or []),
            dirty=bool(data.get("dirty", False)),
            dirty_reasons=list(data.get("dirty_reasons", []) or []),
            modules=dict(data.get("modules", {}) or {}),
        )


def read_project_map_status(project_root: Path) -> ProjectMapStatus:
    for status_path in (project_map_status_path(project_root), legacy_project_map_status_path(project_root)):
        if not status_path.exists():
            continue
        try:
            payload = json.loads(status_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue
        return ProjectMapStatus.from_dict(payload)
    return ProjectMapStatus()


def write_project_map_status(project_root: Path, status: ProjectMapStatus) -> Path:
    status_path = project_map_status_path(project_root)
    status_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(status.to_dict(), indent=2) + "\n"
    status_path.write_text(payload, encoding="utf-8")
    legacy_path = legacy_project_map_status_path(project_root)
    if legacy_path != status_path:
        legacy_path.parent.mkdir(parents=True, exist_ok=True)
        legacy_path.write_text(payload, encoding="utf-8")
    return status_path


def mark_project_map_refreshed(
    project_root: Path,
    *,
    head_commit: str,
    branch: str,
    reason: str,
    mapped_at: str | None = None,
    refresh_topics: list[str] | None = None,
    refresh_scope: str = "full",
    refresh_basis: str | None = None,
    changed_files_basis: list[str] | None = None,
) -> ProjectMapStatus:
    status = ProjectMapStatus(
        version=2,
        global_last_refresh_commit=head_commit,
        global_last_refresh_at=mapped_at or iso_now(),
        global_last_refresh_branch=branch,
        global_freshness="fresh",
        global_last_refresh_reason=reason,
        global_last_refresh_topics=list(refresh_topics or TOPIC_FILES),
        global_last_refresh_scope=refresh_scope,
        global_last_refresh_basis=refresh_basis or reason,
        global_last_refresh_changed_files_basis=list(changed_files_basis or []),
        global_dirty=False,
        global_dirty_reasons=[],
    )
    write_project_map_status(project_root, status)
    return status


def complete_project_map_refresh(project_root: Path) -> ProjectMapStatus:
    return mark_project_map_refreshed(
        project_root,
        head_commit=git_head_commit(project_root),
        branch=git_branch_name(project_root),
        reason="map-codebase",
        refresh_topics=list(TOPIC_FILES),
        refresh_scope="full",
        refresh_basis="map-codebase",
        changed_files_basis=[],
    )


def refresh_project_map_topics(
    project_root: Path,
    *,
    topics: list[str],
    reason: str,
    changed_files_basis: list[str] | None = None,
) -> ProjectMapStatus:
    ordered_topics = [topic for topic in TOPIC_FILES if topic in topics]
    return mark_project_map_refreshed(
        project_root,
        head_commit=git_head_commit(project_root),
        branch=git_branch_name(project_root),
        reason=reason,
        refresh_topics=ordered_topics,
        refresh_scope="partial",
        refresh_basis=reason,
        changed_files_basis=changed_files_basis or [],
    )


def mark_project_map_dirty(project_root: Path, reason: str) -> ProjectMapStatus:
    status = read_project_map_status(project_root)
    reasons = list(status.dirty_reasons or [])
    canonical_reason = normalize_dirty_reason(reason)
    if canonical_reason and canonical_reason not in reasons:
        reasons.append(canonical_reason)
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

    if not project_map_status_path(project_root).exists() and not legacy_project_map_status_path(project_root).exists():
        return {
            "freshness": "missing",
            "status_path": str(project_map_status_path(project_root)),
            "head_commit": head_commit,
            "last_mapped_commit": "",
            "dirty": False,
            "dirty_reasons": [],
            "reasons": ["project-map status missing"],
            "changed_files": [],
            "must_refresh_topics": [],
            "review_topics": [],
            "suggested_topics": [],
            "global": status.to_dict().get("global", {}),
            "modules": dict(status.modules or {}),
        }

    if status.dirty:
        dirty_topic_plan = _merged_dirty_reason_topics(list(status.dirty_reasons or []))
        return {
            "freshness": "stale",
            "status_path": str(project_map_status_path(project_root)),
            "head_commit": head_commit,
            "last_mapped_commit": status.last_mapped_commit,
            "dirty": True,
            "dirty_reasons": list(status.dirty_reasons or []),
            "reasons": list(status.dirty_reasons or []),
            "changed_files": [],
            "must_refresh_topics": dirty_topic_plan["must_refresh_topics"],
            "review_topics": dirty_topic_plan["review_topics"],
            "suggested_topics": [topic for topic in TOPIC_FILES if topic in (*dirty_topic_plan["must_refresh_topics"], *dirty_topic_plan["review_topics"])],
            "global": status.to_dict().get("global", {}),
            "modules": dict(status.modules or {}),
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
            "must_refresh_topics": [],
            "review_topics": [],
            "suggested_topics": [],
            "global": status.to_dict().get("global", {}),
            "modules": dict(status.modules or {}),
        }

    worst = "fresh"
    reasons: list[str] = []
    considered: list[str] = []
    suggested_topics: list[str] = []
    must_refresh_topics: list[str] = []
    review_topics: list[str] = []

    for changed in changed_files:
        classification = classify_changed_path(changed)
        considered.append(changed)
        plan = refresh_plan_for_changed_path(changed)
        covered_by_last_refresh = (
            status.last_refresh_scope == "partial"
            and set(plan["must_refresh_topics"] + plan["review_topics"]).issubset(set(status.last_refresh_topics or []))
        )
        if classification == "possibly_stale" and covered_by_last_refresh:
            plan = {
                "must_refresh_topics": [],
                "review_topics": [topic for topic in TOPIC_FILES if topic in set(plan["must_refresh_topics"] + plan["review_topics"])],
            }
        for topic in plan["must_refresh_topics"]:
            if topic not in must_refresh_topics:
                must_refresh_topics.append(topic)
        for topic in plan["review_topics"]:
            if topic not in review_topics:
                review_topics.append(topic)
        for topic in suggested_topics_for_changed_path(changed):
            if topic not in suggested_topics:
                suggested_topics.append(topic)
        if classification == "stale":
            worst = "stale"
            reasons.append(f"high-impact project-map change: {changed}")
        elif classification == "possibly_stale" and worst != "stale":
            worst = "possibly_stale"
            if covered_by_last_refresh:
                reasons.append(f"covered topic changed since last partial map: {changed}")
            else:
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
        "must_refresh_topics": must_refresh_topics,
        "review_topics": review_topics,
        "suggested_topics": suggested_topics,
        "global": status.to_dict().get("global", {}),
        "modules": dict(status.modules or {}),
    }


def git_head_commit(project_root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(project_root), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
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
            encoding="utf-8",
            errors="replace",
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
            encoding="utf-8",
            errors="replace",
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
