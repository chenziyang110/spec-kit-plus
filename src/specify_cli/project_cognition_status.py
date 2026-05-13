"""Project cognition freshness status helpers.

This module centralizes the freshness contract that bridges the legacy
project-map status metadata with the graph-native project cognition baseline.
Python call sites use it to reason about graph readiness and staleness without
shelling out.

This module now supports atlas hard-gate routing and minimum read-set checks in
addition to freshness status.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import subprocess
from typing import Any

from specify_cli.cognition import (
    CognitionStatus,
    cognition_db_path,
    cognition_status_path,
    read_cognition_status,
    write_cognition_status,
)
from specify_cli.scan_freshness import (
    collect_git_changed_files,
    read_scan_status,
    write_scan_payload,
)


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
    "capabilities.json",
    "symptoms.json",
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

SCAN_SCOPE_RUNTIME_LIVE_PREFIXES = (
    "src/",
    "templates/",
    "scripts/",
    "tests/",
    ".github/workflows/",
    ".specify/memory/",
    ".specify/templates/",
)

SCAN_SCOPE_RUNTIME_LIVE_FILES = {
    "pyproject.toml",
    "readme.md",
    "agents.md",
}

SCAN_SCOPE_HIGH_IMPACT_TOP_LEVEL_FILES = {
    ".specify/extensions.yml",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
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

SCAN_SCOPE_REFERENCE_ONLY_PREFIXES = (
    ".specify/project-cognition/",
    ".specify/project-map/",
    ".specify/prd-runs/",
    ".specify/testing/worker-results/",
)

SCAN_SCOPE_REFERENCE_ONLY_FILES = {
    "project-handbook.md",
}

SCAN_SCOPE_HARD_EXCLUDED_PREFIXES = (
    ".git/",
    ".venv/",
    ".pytest_cache/",
    ".ruff_cache/",
    "dist/",
    "build/",
)

MISSING_COGNITION_BASELINE_GUIDANCE = (
    "Run /sp-map-scan, then /sp-map-build to create the initial project cognition baseline."
)
STALE_COGNITION_BASELINE_GUIDANCE = (
    "Use /sp-map-update when the project cognition runtime is stale or too weak for the touched area. "
    "If no usable baseline remains, rebuild it with /sp-map-scan followed by /sp-map-build."
)
SUPPORT_DRIFT_COGNITION_BASELINE_GUIDANCE = (
    "Resolve or intentionally ignore project cognition support-surface drift before retrying; "
    "support drift is not refreshed through /sp-map-update."
)
PARTIAL_REFRESH_COGNITION_BASELINE_GUIDANCE = (
    "Project cognition refresh data was recorded, but runtime readiness is still blocked for the touched area."
)

FRESHNESS_READY_STATE = "fresh"
FRESHNESS_RUNTIME_STALE_STATE = "stale"
FRESHNESS_POSSIBLY_STALE_STATE = "possibly_stale"
FRESHNESS_SUPPORT_DRIFT_STATE = "support_drift"
FRESHNESS_MISSING_STATE = "missing"
FRESHNESS_PARTIAL_REFRESH_STATE = "partial_refresh"

STATE_READY = "fresh"
STATE_RUNTIME_STALE = "runtime_stale"
STATE_SUPPORT_DRIFT = "support_drift"
STATE_MISSING_BASELINE = "missing_baseline"
STATE_PARTIAL_REFRESH = "partial_refresh"

READINESS_READY = "ready"
READINESS_BLOCKED = "blocked"
READINESS_REVIEW = "review"

NEXT_ACTION_RETRY = "retry_current_workflow"
NEXT_ACTION_MAP_UPDATE = "run_map_update"
NEXT_ACTION_MAP_SCAN_BUILD = "run_map_scan_build"
NEXT_ACTION_SUPPORT = "commit_or_ignore_support_files"
NEXT_ACTION_POLICY = "review_policy_configuration"

TEAM_EXECUTION_PREFIXES = (
    "team ",
    "sp-teams",
)

FRESHNESS_SEVERITY_ORDER = {
    FRESHNESS_READY_STATE: 0,
    FRESHNESS_POSSIBLY_STALE_STATE: 1,
    FRESHNESS_SUPPORT_DRIFT_STATE: 2,
    FRESHNESS_RUNTIME_STALE_STATE: 3,
    FRESHNESS_PARTIAL_REFRESH_STATE: 4,
    FRESHNESS_MISSING_STATE: 5,
}


def classify_scan_scope_path(path: str) -> str:
    lower = str(path or "").strip().replace("\\", "/").lower().strip("/")
    if not lower:
        return "hard_excluded"
    if lower in SCAN_SCOPE_REFERENCE_ONLY_FILES or lower.startswith(SCAN_SCOPE_REFERENCE_ONLY_PREFIXES):
        return "reference_only"
    if lower.startswith(SCAN_SCOPE_HARD_EXCLUDED_PREFIXES):
        return "hard_excluded"
    if (
        lower in SCAN_SCOPE_RUNTIME_LIVE_FILES
        or lower in SCAN_SCOPE_HIGH_IMPACT_TOP_LEVEL_FILES
        or lower.startswith(SCAN_SCOPE_RUNTIME_LIVE_PREFIXES)
    ):
        return "live_surface"
    return "hard_excluded"


def filter_scan_scope_candidates(paths: list[str]) -> dict[str, list[str]]:
    live_candidates: list[str] = []
    reference_only: list[str] = []
    hard_excluded: list[str] = []

    for path in paths:
        classification = classify_scan_scope_path(path)
        if classification == "live_surface":
            live_candidates.append(path)
        elif classification == "reference_only":
            reference_only.append(path)
        else:
            hard_excluded.append(path)

    return {
        "live_candidates": live_candidates,
        "reference_only": reference_only,
        "hard_excluded": hard_excluded,
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


def project_cognition_status_metadata_path(project_root: Path) -> Path:
    return cognition_status_path(project_root)


def legacy_project_map_status_paths(project_root: Path) -> tuple[Path, Path]:
    return (
        project_map_status_path(project_root),
        legacy_project_map_status_path(project_root),
    )


def canonical_cognition_runtime_paths(project_root: Path) -> list[Path]:
    return [
        cognition_status_path(project_root),
        cognition_db_path(project_root),
    ]


def canonical_project_map_paths(project_root: Path) -> list[Path]:
    return canonical_cognition_runtime_paths(project_root)


def atlas_minimum_read_set(project_root: Path) -> list[Path]:
    return [
        cognition_status_path(project_root),
        cognition_db_path(project_root),
    ]


def atlas_root_topic_path(project_root: Path, topic_filename: str) -> Path:
    return project_map_root_dir(project_root) / topic_filename


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


def classify_changed_path_details(path: str) -> dict[str, str]:
    lower = str(path or "").strip().replace("\\", "/").lower().strip("/")
    scan_scope_class = classify_scan_scope_path(path)
    if scan_scope_class in {"reference_only", "hard_excluded"}:
        return {"layer": scan_scope_class, "severity": "ignore"}

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
        ".specify/project-map/map-state.md",
    }:
        return {"layer": "reference", "severity": "ignore"}
    if lower.startswith(".specify/project-map/worker-results/"):
        return {"layer": "reference", "severity": "ignore"}

    support_exact = {
        ".specify/templates/runtime-config.template.json",
    }
    support_prefixes = (
        ".specify/templates/testing/support/",
    )
    if lower in support_exact or lower.startswith(support_prefixes):
        return {"layer": "support", "severity": FRESHNESS_SUPPORT_DRIFT_STATE}
    if lower.startswith(".specify/templates/project-map/"):
        return {"layer": "runtime_truth", "severity": FRESHNESS_RUNTIME_STALE_STATE}

    if lower in high_impact_exact:
        return {"layer": "runtime_truth", "severity": FRESHNESS_RUNTIME_STALE_STATE}

    high_impact_prefixes = (
        ".specify/memory/",
        ".github/workflows/",
    )
    if lower.startswith(high_impact_prefixes):
        return {"layer": "runtime_truth", "severity": FRESHNESS_RUNTIME_STALE_STATE}

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
            return {"layer": "runtime_truth", "severity": FRESHNESS_RUNTIME_STALE_STATE}

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
        return {"layer": "broader_code", "severity": FRESHNESS_POSSIBLY_STALE_STATE}

    return {"layer": "reference", "severity": "ignore"}


def classify_changed_path(path: str) -> str:
    return classify_changed_path_details(path)["severity"]


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


def recommended_next_action_for_freshness(*, freshness: str, reasons: list[str]) -> str:
    normalized = str(freshness or "").strip().lower()
    reason_text = " ".join(reasons).lower()
    if normalized == FRESHNESS_MISSING_STATE:
        return NEXT_ACTION_MAP_SCAN_BUILD
    if normalized == FRESHNESS_RUNTIME_STALE_STATE:
        return NEXT_ACTION_MAP_UPDATE
    if normalized == FRESHNESS_SUPPORT_DRIFT_STATE:
        if "policy" in reason_text:
            return NEXT_ACTION_POLICY
        return NEXT_ACTION_SUPPORT
    if normalized == FRESHNESS_PARTIAL_REFRESH_STATE:
        return NEXT_ACTION_MAP_UPDATE
    if normalized == FRESHNESS_POSSIBLY_STALE_STATE:
        return NEXT_ACTION_MAP_UPDATE
    return NEXT_ACTION_RETRY


def public_state_for_freshness(freshness: str) -> str:
    normalized = str(freshness or "").strip().lower()
    if normalized == FRESHNESS_MISSING_STATE:
        return STATE_MISSING_BASELINE
    if normalized == FRESHNESS_SUPPORT_DRIFT_STATE:
        return STATE_SUPPORT_DRIFT
    if normalized == FRESHNESS_PARTIAL_REFRESH_STATE:
        return STATE_PARTIAL_REFRESH
    if normalized in {FRESHNESS_RUNTIME_STALE_STATE, FRESHNESS_POSSIBLY_STALE_STATE}:
        return STATE_RUNTIME_STALE
    return STATE_READY


def readiness_for_freshness(freshness: str) -> str:
    normalized = str(freshness or "").strip().lower()
    if normalized == FRESHNESS_READY_STATE:
        return READINESS_READY
    if normalized == FRESHNESS_POSSIBLY_STALE_STATE:
        return READINESS_REVIEW
    return READINESS_BLOCKED


def _freshness_payload(
    *,
    project_root: Path,
    freshness: str,
    status: ProjectMapStatus,
    head_commit: str,
    manual_force_stale: bool,
    manual_force_stale_reasons: list[str],
    dirty: bool,
    dirty_reasons: list[str],
    reasons: list[str],
    changed_files: list[str],
    must_refresh_topics: list[str],
    review_topics: list[str],
    suggested_topics: list[str],
    missing_runtime_paths: list[str],
    dirty_origin_command: str = "",
    dirty_origin_feature_dir: str = "",
    dirty_origin_lane_id: str = "",
    dirty_scope_paths: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "freshness": freshness,
        "state": public_state_for_freshness(freshness),
        "readiness": readiness_for_freshness(freshness),
        "recommended_next_action": recommended_next_action_for_freshness(
            freshness=freshness,
            reasons=reasons,
        ),
        "status_path": str(project_cognition_status_metadata_path(project_root)),
        "head_commit": head_commit,
        "last_mapped_commit": status.last_mapped_commit,
        "manual_force_stale": manual_force_stale,
        "manual_force_stale_reasons": manual_force_stale_reasons,
        "dirty": dirty,
        "dirty_reasons": dirty_reasons,
        "dirty_origin_command": dirty_origin_command,
        "dirty_origin_feature_dir": dirty_origin_feature_dir,
        "dirty_origin_lane_id": dirty_origin_lane_id,
        "dirty_scope_paths": list(dirty_scope_paths or []),
        "reasons": reasons,
        "changed_files": changed_files,
        "must_refresh_topics": must_refresh_topics,
        "review_topics": review_topics,
        "suggested_topics": suggested_topics,
        "missing_runtime_paths": missing_runtime_paths,
        "global": status.to_dict().get("global", {}),
        "modules": dict(status.modules or {}),
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
    global_dirty_origin_command: str
    global_dirty_origin_feature_dir: str
    global_dirty_origin_lane_id: str
    global_dirty_scope_paths: list[str] | None
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
        global_dirty_origin_command: str = "",
        global_dirty_origin_feature_dir: str = "",
        global_dirty_origin_lane_id: str = "",
        global_dirty_scope_paths: list[str] | None = None,
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
        dirty_origin_command: str | None = None,
        dirty_origin_feature_dir: str | None = None,
        dirty_origin_lane_id: str | None = None,
        dirty_scope_paths: list[str] | None = None,
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
        self.global_dirty_origin_command = (
            dirty_origin_command if dirty_origin_command is not None else global_dirty_origin_command
        )
        self.global_dirty_origin_feature_dir = (
            dirty_origin_feature_dir if dirty_origin_feature_dir is not None else global_dirty_origin_feature_dir
        )
        self.global_dirty_origin_lane_id = (
            dirty_origin_lane_id if dirty_origin_lane_id is not None else global_dirty_origin_lane_id
        )
        self.global_dirty_scope_paths = list(
            dirty_scope_paths if dirty_scope_paths is not None else (global_dirty_scope_paths or [])
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

    @property
    def manual_force_stale(self) -> bool:
        return self.global_dirty

    @manual_force_stale.setter
    def manual_force_stale(self, value: bool) -> None:
        self.global_dirty = value

    @property
    def manual_force_stale_reasons(self) -> list[str]:
        return list(self.global_dirty_reasons or [])

    @manual_force_stale_reasons.setter
    def manual_force_stale_reasons(self, value: list[str] | None) -> None:
        self.global_dirty_reasons = list(value or [])
        self.global_stale_reasons = list(value or [])

    @property
    def dirty_origin_command(self) -> str:
        return self.global_dirty_origin_command

    @dirty_origin_command.setter
    def dirty_origin_command(self, value: str) -> None:
        self.global_dirty_origin_command = value

    @property
    def dirty_origin_feature_dir(self) -> str:
        return self.global_dirty_origin_feature_dir

    @dirty_origin_feature_dir.setter
    def dirty_origin_feature_dir(self, value: str) -> None:
        self.global_dirty_origin_feature_dir = value

    @property
    def dirty_origin_lane_id(self) -> str:
        return self.global_dirty_origin_lane_id

    @dirty_origin_lane_id.setter
    def dirty_origin_lane_id(self, value: str) -> None:
        self.global_dirty_origin_lane_id = value

    @property
    def dirty_scope_paths(self) -> list[str]:
        return list(self.global_dirty_scope_paths or [])

    @dirty_scope_paths.setter
    def dirty_scope_paths(self, value: list[str] | None) -> None:
        self.global_dirty_scope_paths = list(value or [])

    @property
    def last_refresh_commit(self) -> str:
        return self.global_last_refresh_commit

    @last_refresh_commit.setter
    def last_refresh_commit(self, value: str) -> None:
        self.global_last_refresh_commit = value

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
                "manual_force_stale": self.global_dirty,
                "manual_force_stale_reasons": list(self.global_dirty_reasons or []),
                "dirty": self.global_dirty,
                "dirty_reasons": list(self.global_dirty_reasons or []),
                "dirty_origin_command": self.global_dirty_origin_command,
                "dirty_origin_feature_dir": self.global_dirty_origin_feature_dir,
                "dirty_origin_lane_id": self.global_dirty_origin_lane_id,
                "dirty_scope_paths": list(self.global_dirty_scope_paths or []),
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
            "manual_force_stale": self.manual_force_stale,
            "manual_force_stale_reasons": self.manual_force_stale_reasons,
            "dirty": self.dirty,
            "dirty_reasons": self.dirty_reasons,
            "dirty_origin_command": self.dirty_origin_command,
            "dirty_origin_feature_dir": self.dirty_origin_feature_dir,
            "dirty_origin_lane_id": self.dirty_origin_lane_id,
            "dirty_scope_paths": self.dirty_scope_paths,
            "stale_reasons": self.dirty_reasons,
            "affected_root_docs": list(self.global_affected_root_docs or []),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectMapStatus":
        global_payload = data.get("global")
        if isinstance(global_payload, dict):
            manual_force_stale = global_payload.get("manual_force_stale", global_payload.get("dirty", False))
            manual_force_stale_reasons = global_payload.get(
                "manual_force_stale_reasons",
                global_payload.get("dirty_reasons", global_payload.get("stale_reasons", [])),
            )
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
                global_dirty=bool(manual_force_stale),
                global_dirty_reasons=list(manual_force_stale_reasons or []),
                global_dirty_origin_command=str(global_payload.get("dirty_origin_command", "")),
                global_dirty_origin_feature_dir=str(global_payload.get("dirty_origin_feature_dir", "")),
                global_dirty_origin_lane_id=str(global_payload.get("dirty_origin_lane_id", "")),
                global_dirty_scope_paths=list(global_payload.get("dirty_scope_paths", []) or []),
                global_stale_reasons=list(global_payload.get("stale_reasons", []) or []),
                global_affected_root_docs=list(global_payload.get("affected_root_docs", []) or []),
                modules=dict(data.get("modules", {}) or {}),
            )

        manual_force_stale = data.get("manual_force_stale", data.get("dirty", False))
        manual_force_stale_reasons = data.get(
            "manual_force_stale_reasons",
            data.get("dirty_reasons", data.get("stale_reasons", [])),
        )
        return cls(
            version=int(data.get("version", 1)),
            last_mapped_commit=str(data.get("last_mapped_commit", data.get("global_last_refresh_commit", ""))),
            last_mapped_at=str(data.get("last_mapped_at", data.get("global_last_refresh_at", ""))),
            last_mapped_branch=str(data.get("last_mapped_branch", data.get("global_last_refresh_branch", ""))),
            freshness=str(data.get("freshness", data.get("global_freshness", "missing"))),
            last_refresh_reason=str(data.get("last_refresh_reason", data.get("global_last_refresh_reason", ""))),
            last_refresh_topics=list(data.get("last_refresh_topics", data.get("global_last_refresh_topics", [])) or []),
            last_refresh_scope=str(data.get("last_refresh_scope", data.get("global_last_refresh_scope", "full"))),
            last_refresh_basis=str(data.get("last_refresh_basis", data.get("global_last_refresh_basis", ""))),
            last_refresh_changed_files_basis=list(
                data.get("last_refresh_changed_files_basis", data.get("global_last_refresh_changed_files_basis", [])) or []
            ),
            dirty=bool(manual_force_stale),
            dirty_reasons=list(manual_force_stale_reasons or []),
            dirty_origin_command=str(data.get("dirty_origin_command", "")),
            dirty_origin_feature_dir=str(data.get("dirty_origin_feature_dir", "")),
            dirty_origin_lane_id=str(data.get("dirty_origin_lane_id", "")),
            dirty_scope_paths=list(data.get("dirty_scope_paths", []) or []),
            modules=dict(data.get("modules", {}) or {}),
        )


def read_project_map_status(project_root: Path) -> ProjectMapStatus:
    canonical_path = project_cognition_status_metadata_path(project_root)
    if canonical_path.exists():
        shared_status = read_scan_status(canonical_path, status_family="project-cognition")
        if shared_status.raw_payload:
            return ProjectMapStatus.from_dict(shared_status.raw_payload)
    for status_path in legacy_project_map_status_paths(project_root):
        if not status_path.exists():
            continue
        shared_status = read_scan_status(status_path, status_family="project-map")
        if not shared_status.raw_payload:
            continue
        return ProjectMapStatus.from_dict(shared_status.raw_payload)
    return ProjectMapStatus()


def write_project_map_status(project_root: Path, status: ProjectMapStatus) -> Path:
    status_path = project_cognition_status_metadata_path(project_root)
    payload = status.to_dict()
    write_scan_payload(status_path, payload)
    _write_cognition_freshness_metadata(project_root, status, legacy_status_payload=payload)
    return status_path


def _write_cognition_freshness_metadata(
    project_root: Path,
    status: ProjectMapStatus,
    *,
    legacy_status_payload: dict[str, Any] | None = None,
) -> Path:
    cognition_status = read_cognition_status(project_root)
    merged = CognitionStatus(
        version=max(int(cognition_status.version or 1), 2),
        baseline_state=cognition_status.baseline_state,
        baseline_commit=status.last_refresh_commit or cognition_status.baseline_commit,
        baseline_branch=status.last_mapped_branch or cognition_status.baseline_branch,
        baseline_built_at=status.last_mapped_at or cognition_status.baseline_built_at,
        last_update_id=cognition_status.last_update_id,
        graph_ready=cognition_status.graph_ready,
        graph_store_path=cognition_status.graph_store_path,
        active_generation_id=cognition_status.active_generation_id,
        query_contract_version=cognition_status.query_contract_version,
        update_contract_version=cognition_status.update_contract_version,
        stale_paths=list(cognition_status.stale_paths or []),
        stale_reasons=list(cognition_status.stale_reasons or []),
        freshness=status.freshness,
        last_refresh_reason=status.last_refresh_reason,
        last_refresh_topics=list(status.last_refresh_topics or []),
        last_refresh_scope=status.last_refresh_scope,
        last_refresh_basis=status.last_refresh_basis,
        last_refresh_changed_files_basis=list(status.last_refresh_changed_files_basis or []),
        manual_force_stale=status.manual_force_stale,
        manual_force_stale_reasons=list(status.manual_force_stale_reasons or []),
        dirty=status.dirty,
        dirty_reasons=list(status.dirty_reasons or []),
        dirty_origin_command=status.dirty_origin_command,
        dirty_origin_feature_dir=status.dirty_origin_feature_dir,
        dirty_origin_lane_id=status.dirty_origin_lane_id,
        dirty_scope_paths=list(status.dirty_scope_paths or []),
    )
    if merged.graph_ready and merged.baseline_state == "missing":
        merged.baseline_state = "ready"
    if legacy_status_payload is None:
        return write_cognition_status(project_root, merged)
    merged_payload = dict(legacy_status_payload)
    merged_payload.update(asdict(merged))
    return write_scan_payload(cognition_status_path(project_root), merged_payload)


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
        global_dirty_origin_command="",
        global_dirty_origin_feature_dir="",
        global_dirty_origin_lane_id="",
        global_dirty_scope_paths=[],
    )
    write_project_map_status(project_root, status)
    return status


def complete_project_map_refresh(project_root: Path) -> ProjectMapStatus:
    return mark_project_map_refreshed(
        project_root,
        head_commit=git_head_commit(project_root),
        branch=git_branch_name(project_root),
        reason="map-build",
        refresh_topics=list(TOPIC_FILES),
        refresh_scope="full",
        refresh_basis="map-build",
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


def mark_project_map_dirty(
    project_root: Path,
    reason: str,
    *,
    origin_command: str = "",
    origin_feature_dir: str = "",
    origin_lane_id: str = "",
    scope_paths: list[str] | None = None,
) -> ProjectMapStatus:
    status = read_project_map_status(project_root)
    reasons = list(status.manual_force_stale_reasons or [])
    canonical_reason = normalize_dirty_reason(reason)
    if canonical_reason and canonical_reason not in reasons:
        reasons.append(canonical_reason)
    status.manual_force_stale = True
    status.manual_force_stale_reasons = reasons
    status.freshness = "stale"
    if origin_command:
        status.dirty_origin_command = origin_command
    if origin_feature_dir:
        status.dirty_origin_feature_dir = origin_feature_dir
    if origin_lane_id:
        status.dirty_origin_lane_id = origin_lane_id
    if scope_paths is not None:
        status.dirty_scope_paths = scope_paths
    if not status.last_mapped_at:
        status.last_mapped_at = iso_now()
    if not status.last_refresh_reason:
        status.last_refresh_reason = "manual"
    write_project_map_status(project_root, status)
    return status


def clear_project_map_dirty(project_root: Path) -> ProjectMapStatus:
    status = read_project_map_status(project_root)
    status.manual_force_stale = False
    status.manual_force_stale_reasons = []
    status.dirty_origin_command = ""
    status.dirty_origin_feature_dir = ""
    status.dirty_origin_lane_id = ""
    status.dirty_scope_paths = []
    status.freshness = "fresh"
    write_project_map_status(project_root, status)
    return status


def assess_project_map_freshness(
    project_root: Path,
    *,
    head_commit: str,
    changed_files: list[str],
    has_git: bool,
    allow_legacy_status_only: bool = False,
) -> dict[str, Any]:
    cognition_status = read_cognition_status(project_root)
    status = _effective_project_map_status(project_root, cognition_status)
    missing_runtime_paths = missing_canonical_project_map_paths(project_root)
    has_status_metadata = bool(
        cognition_status.freshness
        or project_cognition_status_metadata_path(project_root).exists()
        or any(status_path.exists() for status_path in legacy_project_map_status_paths(project_root))
    )

    if missing_runtime_paths and not allow_legacy_status_only and not has_status_metadata:
        return _freshness_payload(
            project_root=project_root,
            freshness=FRESHNESS_MISSING_STATE,
            status=status,
            head_commit=head_commit,
            manual_force_stale=False,
            manual_force_stale_reasons=[],
            dirty=False,
            dirty_reasons=[],
            reasons=[MISSING_COGNITION_BASELINE_GUIDANCE],
            changed_files=[],
            must_refresh_topics=[],
            review_topics=[],
            suggested_topics=[],
            missing_runtime_paths=[str(path) for path in missing_runtime_paths],
        )

    if not cognition_status.graph_ready and not allow_legacy_status_only and not has_status_metadata:
        return _freshness_payload(
            project_root=project_root,
            freshness=FRESHNESS_MISSING_STATE,
            status=status,
            head_commit=head_commit,
            manual_force_stale=False,
            manual_force_stale_reasons=[],
            dirty=False,
            dirty_reasons=[],
            reasons=[MISSING_COGNITION_BASELINE_GUIDANCE],
            changed_files=[],
            must_refresh_topics=[],
            review_topics=[],
            suggested_topics=[],
            missing_runtime_paths=[],
        )

    if not has_status_metadata:
        return _freshness_payload(
            project_root=project_root,
            freshness=FRESHNESS_MISSING_STATE,
            status=status,
            head_commit=head_commit,
            manual_force_stale=False,
            manual_force_stale_reasons=[],
            dirty=False,
            dirty_reasons=[],
            reasons=["project cognition freshness metadata is missing; re-establish the baseline before brownfield work resumes."],
            changed_files=[],
            must_refresh_topics=[],
            review_topics=[],
            suggested_topics=[],
            missing_runtime_paths=[],
        )

    if status.dirty:
        dirty_topic_plan = _merged_dirty_reason_topics(list(status.dirty_reasons or []))
        return _freshness_payload(
            project_root=project_root,
            freshness=FRESHNESS_RUNTIME_STALE_STATE,
            status=status,
            head_commit=head_commit,
            manual_force_stale=True,
            manual_force_stale_reasons=list(status.manual_force_stale_reasons or []),
            dirty=True,
            dirty_reasons=list(status.dirty_reasons or []),
            dirty_origin_command=status.dirty_origin_command,
            dirty_origin_feature_dir=status.dirty_origin_feature_dir,
            dirty_origin_lane_id=status.dirty_origin_lane_id,
            dirty_scope_paths=status.dirty_scope_paths,
            reasons=list(status.dirty_reasons or []),
            changed_files=[],
            must_refresh_topics=dirty_topic_plan["must_refresh_topics"],
            review_topics=dirty_topic_plan["review_topics"],
            suggested_topics=[topic for topic in TOPIC_FILES if topic in (*dirty_topic_plan["must_refresh_topics"], *dirty_topic_plan["review_topics"])],
            missing_runtime_paths=[],
        )

    if has_status_metadata and (not has_git or not status.last_mapped_commit or not head_commit):
        return _freshness_payload(
            project_root=project_root,
            freshness=FRESHNESS_POSSIBLY_STALE_STATE,
            status=status,
            head_commit=head_commit,
            manual_force_stale=False,
            manual_force_stale_reasons=[],
            dirty=False,
            dirty_reasons=[],
            reasons=["git baseline unavailable for project cognition freshness"],
            changed_files=[],
            must_refresh_topics=[],
            review_topics=[],
            suggested_topics=[],
            missing_runtime_paths=[],
        )

    worst = FRESHNESS_READY_STATE
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
        if classification == FRESHNESS_RUNTIME_STALE_STATE:
            if status.last_refresh_scope == "partial":
                candidate = FRESHNESS_PARTIAL_REFRESH_STATE
                reasons.append(f"partial cognition refresh is recorded but runtime-truth drift remains: {changed}")
            else:
                candidate = FRESHNESS_RUNTIME_STALE_STATE
                reasons.append(f"high-impact project cognition input changed: {changed}")
            if FRESHNESS_SEVERITY_ORDER[candidate] > FRESHNESS_SEVERITY_ORDER[worst]:
                worst = candidate
        elif classification == FRESHNESS_SUPPORT_DRIFT_STATE:
            if FRESHNESS_SEVERITY_ORDER[classification] > FRESHNESS_SEVERITY_ORDER[worst]:
                worst = FRESHNESS_SUPPORT_DRIFT_STATE
            reasons.append(f"tool-managed support surface changed: {changed}")
        elif (
            classification == FRESHNESS_POSSIBLY_STALE_STATE
            and FRESHNESS_SEVERITY_ORDER[worst] < FRESHNESS_SEVERITY_ORDER[FRESHNESS_RUNTIME_STALE_STATE]
        ):
            if FRESHNESS_SEVERITY_ORDER[classification] > FRESHNESS_SEVERITY_ORDER[worst]:
                worst = FRESHNESS_POSSIBLY_STALE_STATE
            if covered_by_last_refresh:
                reasons.append(f"covered topic changed since last partial cognition refresh: {changed}")
            else:
                reasons.append(f"codebase surface changed since last cognition baseline: {changed}")

    if worst == FRESHNESS_READY_STATE:
        reasons = []
    elif worst in {FRESHNESS_RUNTIME_STALE_STATE, FRESHNESS_POSSIBLY_STALE_STATE}:
        reasons.append(STALE_COGNITION_BASELINE_GUIDANCE)
    elif worst == FRESHNESS_SUPPORT_DRIFT_STATE:
        reasons.append(SUPPORT_DRIFT_COGNITION_BASELINE_GUIDANCE)
    elif worst == FRESHNESS_PARTIAL_REFRESH_STATE:
        reasons.append(PARTIAL_REFRESH_COGNITION_BASELINE_GUIDANCE)

    return _freshness_payload(
        project_root=project_root,
        freshness=worst,
        status=status,
        head_commit=head_commit,
        manual_force_stale=False,
        manual_force_stale_reasons=[],
        dirty=False,
        dirty_reasons=[],
        dirty_origin_command="",
        dirty_origin_feature_dir="",
        dirty_origin_lane_id="",
        dirty_scope_paths=[],
        reasons=reasons,
        changed_files=considered,
        must_refresh_topics=must_refresh_topics,
        review_topics=review_topics,
        suggested_topics=suggested_topics,
        missing_runtime_paths=[],
    )


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
    return collect_git_changed_files(
        project_root,
        baseline_commit=last_mapped_commit,
        head_commit=head_commit,
    )


def inspect_project_cognition_freshness(project_root: Path) -> dict[str, Any]:
    cognition_status = read_cognition_status(project_root)
    status = _effective_project_map_status(project_root, cognition_status)
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


def inspect_project_cognition_freshness_for_command(
    project_root: Path,
    *,
    command_name: str = "",
) -> dict[str, Any]:
    lowered = str(command_name or "").strip().lower()
    allow_legacy_status_only = any(
        lowered.startswith(prefix) for prefix in TEAM_EXECUTION_PREFIXES
    )

    cognition_status = read_cognition_status(project_root)
    status = _effective_project_map_status(project_root, cognition_status)
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
        allow_legacy_status_only=allow_legacy_status_only,
    )


def inspect_project_map_freshness(project_root: Path) -> dict[str, Any]:
    return inspect_project_cognition_freshness(project_root)


def inspect_project_map_freshness_for_command(
    project_root: Path,
    *,
    command_name: str = "",
) -> dict[str, Any]:
    return inspect_project_cognition_freshness_for_command(
        project_root,
        command_name=command_name,
    )


def _effective_project_map_status(project_root: Path, cognition_status: CognitionStatus | None = None) -> ProjectMapStatus:
    status = read_project_map_status(project_root)
    cognition_status = cognition_status or read_cognition_status(project_root)

    if not cognition_status.freshness:
        return status

    status.last_mapped_commit = cognition_status.baseline_commit or status.last_mapped_commit
    status.last_mapped_branch = cognition_status.baseline_branch or status.last_mapped_branch
    status.last_mapped_at = cognition_status.baseline_built_at or status.last_mapped_at
    status.freshness = cognition_status.freshness
    status.last_refresh_reason = cognition_status.last_refresh_reason or status.last_refresh_reason
    status.last_refresh_topics = list(cognition_status.last_refresh_topics or status.last_refresh_topics)
    status.last_refresh_scope = cognition_status.last_refresh_scope or status.last_refresh_scope
    status.last_refresh_basis = cognition_status.last_refresh_basis or status.last_refresh_basis
    status.last_refresh_changed_files_basis = list(
        cognition_status.last_refresh_changed_files_basis or status.last_refresh_changed_files_basis
    )
    status.manual_force_stale = cognition_status.manual_force_stale
    status.manual_force_stale_reasons = list(cognition_status.manual_force_stale_reasons or [])
    status.dirty = cognition_status.dirty
    status.dirty_reasons = list(cognition_status.dirty_reasons or [])
    status.dirty_origin_command = cognition_status.dirty_origin_command
    status.dirty_origin_feature_dir = cognition_status.dirty_origin_feature_dir
    status.dirty_origin_lane_id = cognition_status.dirty_origin_lane_id
    status.dirty_scope_paths = list(cognition_status.dirty_scope_paths or [])
    return status
