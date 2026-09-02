from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from functools import wraps
from itertools import combinations
import hashlib
from html.parser import HTMLParser
import json
import re
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import yaml
from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateError
from jsonschema import Draft202012Validator

from .atomic_io import atomic_write_text, interprocess_lock
from .design_intelligence import validate_ui_source_continuity
from .workflow_transaction import WorkflowTransactionError, apply_workflow_transaction


FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)
TOKEN_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(?:\.[a-z0-9]+)*$")
TOKEN_REF_RE = re.compile(r"\{([a-z][a-z0-9]*)\.([a-z][a-z0-9]*(?:\.[a-z0-9]+)*)\}")
REQUIRED_SECTIONS = (
    "Product Feel",
    "Platforms",
    "Component Rules",
    "Anti-Patterns",
    "Design Change Policy",
    "UI QA Checklist",
)
READY_REQUIRED_SECTIONS = (
    "Design Direction",
    "Visual And Interaction Signature",
    "Foundations",
    "Motion Rules",
    "Responsive Behavior",
    "Content And Imagery",
    "Reference Fidelity",
    "Planned Gaps and Exceptions",
)
REQUIRED_TOKEN_CATEGORIES = ("color", "spacing", "radius", "typography", "motion")
REQUIRED_ACCESSIBILITY_KEYS = (
    "contrast_intent",
    "focus_visible",
    "keyboard_navigation",
    "reduced_motion",
)
SUPPORTED_EXPORT_FORMATS = {"json", "tailwind"}
SUPPORTED_LINT_LEVELS = {"structural", "ready"}
SUPPORTED_PREVIEW_LINT_LEVELS = {"structural", "concept", "ready"}
DESIGN_PREVIEW_SCHEMA = "spec-kit-design-preview-v1"
DESIGN_PREVIEW_MANIFEST_SCHEMA = "spec-kit-design-preview-manifest-v1"
DESIGN_PREVIEW_APPROVAL_SCHEMA = "spec-kit-design-preview-approval-v1"
DESIGN_IMAGE_APPROVAL_SCHEMA = "spec-kit-design-image-approval-v1"
DESIGN_DIRECTION_CHECKPOINT_SCHEMA = "spec-kit-design-direction-checkpoint-v1"
DESIGN_HANDOFF_SCHEMA = "spec-kit-design-handoff-v1"
DESIGN_CHANGE_SCHEMA = "spec-kit-ui-design-change-v1"
DESIGN_CHANGE_INDEX_SCHEMA = "spec-kit-ui-design-index-v1"
UI_PROFESSIONAL_SKILL_CATALOG = "spec-kit-ui-professional-v1"
DESIGN_CAPABILITY_PROFILES_SCHEMA = "spec-kit-design-capability-profiles-v1"
DESIGN_CAPABILITY_MODEL_SCHEMA = "spec-kit-design-capability-model-v1"
DESIGN_PREVIEW_MANIFEST_ID = "design-preview-manifest"
DESIGN_PREVIEW_DIRECTION_RE = re.compile(r"^direction-[a-z0-9][a-z0-9-]*$")
DESIGN_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
DESIGN_IMAGE_CAPABILITY_VALUES = {"available", "unavailable"}
MAX_DESIGN_IMAGE_IMPORT_BYTES = 32 * 1024 * 1024
DESIGN_VISUAL_COLLABORATION_FIELDS = (
    "image_generation",
    "image_inspection",
    "image_editing",
    "inspection_owner",
    "prompt_strategy",
)
DESIGN_SPECIMEN_ID_RE = re.compile(r"^SP-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
# Freeform boards do not require fixed specimen sections (foundations/components/...).
# Direction canvases carry creative layout; governance lives in the embedded manifest.
DESIGN_PREVIEW_REQUIRED_SECTIONS: tuple[str, ...] = ()
DESIGN_PREVIEW_PLACEHOLDER_RE = re.compile(r"__[A-Z0-9_]+__")
DESIGN_PREVIEW_SEED_RE = re.compile(
    r"(?i)(?:freeform-seed|unfinished prototype seed|replace this seed)"
)
DESIGN_PREVIEW_REMOTE_RE = re.compile(r"(?i)(?:https?:)?//")
DESIGN_PREVIEW_NETWORK_SCRIPT_RE = re.compile(
    r"(?i)\b(?:fetch|XMLHttpRequest|WebSocket|EventSource)\s*\("
)
DESIGN_DECISION_ID_RE = re.compile(r"^DS-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
DESIGN_HANDOFF_ID_RE = re.compile(r"^DH-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
DESIGN_HANDOFF_REQUIRED_EVIDENCE = {
    "structure_snapshot",
    "visual_capture",
    "runtime_diagnostics",
    "visual_comparison_or_human_review",
}
DESIGN_DIRECTION_CONFIRMATION_MARKER = "explicit-user-direction-confirmation"
DESIGN_PROFESSIONAL_MATRIX_FIELDS = (
    "interaction_matrix",
    "editing_matrix",
    "data_state_matrix",
    "accessibility_matrix",
    "navigation_matrix",
    "content_matrix",
)
DESIGN_EXPERIENCE_GRAPH_FIELDS = ("surface_catalog", "scenario_matrix")
DESIGN_PROFESSIONAL_FIELDS = (
    "source_continuity",
    *DESIGN_EXPERIENCE_GRAPH_FIELDS,
    *DESIGN_PROFESSIONAL_MATRIX_FIELDS,
    "motion_contract",
    "usability_validation",
)
DESIGN_DECISION_KINDS_BY_CONTRACT = {
    "component_contracts": (
        "color",
        "typography",
        "spacing",
        "component",
        "motion",
    ),
    "interaction_matrix": ("component", "motion", "responsive"),
    "editing_matrix": (
        "typography",
        "spacing",
        "component",
        "motion",
        "responsive",
        "content",
    ),
    "data_state_matrix": ("color", "component", "content"),
    "accessibility_matrix": (
        "color",
        "typography",
        "spacing",
        "component",
        "motion",
        "responsive",
        "content",
    ),
    "navigation_matrix": ("component", "responsive", "content"),
    "content_matrix": ("color", "typography", "spacing", "content"),
    "responsive_matrix": ("typography", "spacing", "component", "responsive"),
    "motion_contract": ("component", "motion"),
}
UI_TARGET_SCHEMA = "spec-kit-ui-target-v1"
UI_TARGET_MANIFEST_SCHEMA = "spec-kit-ui-target-manifest-v1"
UI_TARGET_MANIFEST_ID = "ui-target-manifest"
UI_TARGET_NETWORK_OR_PERSISTENCE_RE = re.compile(
    r"(?i)\b(?:fetch|XMLHttpRequest|WebSocket|EventSource)\s*\("
    r"|\b(?:localStorage|sessionStorage|indexedDB|document\.cookie)\b"
)
UI_TARGET_APPROVED_PREVIEW_REF_RE = re.compile(
    r"round-\d+\.(?:html|png|jpe?g|webp)#direction-[a-z0-9-]+$", re.IGNORECASE
)
DESIGN_CHANGE_ID_RE = re.compile(r"^UD-[0-9]{4,}$")
DESIGN_CHANGE_SCOPE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")
SUPPORTED_DESIGN_CHANGE_TYPES = {"greenfield", "preserve", "overhaul", "extension"}


@dataclass(frozen=True)
class DesignDocument:
    source: str
    front_matter: dict[str, Any]
    design_system: dict[str, Any]
    body: str


@dataclass(frozen=True)
class DesignDiagnostic:
    code: str
    message: str
    path: str
    level: str = "error"
    # Recovery contract (layer/severity/recovery/agent_action). Optional so
    # existing constructors remain valid; lint enriches from the contract file.
    layer: str | None = None
    recovery: tuple[str, ...] = ()
    agent_action: tuple[str, ...] = ()
    why: str | None = None


class DesignLintError(ValueError):
    pass


def _design_index_transaction(function: Any) -> Any:
    """Serialize design-index mutations across Python and runtime processes."""

    @wraps(function)
    def locked(project_root: Path, *args: Any, **kwargs: Any) -> Any:
        root = project_root.resolve()
        lock_path = root / ".specify" / "design" / ".index.lock"
        transaction = interprocess_lock(lock_path)
        try:
            transaction.__enter__()
        except (OSError, TimeoutError, ValueError) as exc:
            raise DesignLintError(
                f"cannot acquire UI design index transaction: {exc}"
            ) from exc
        try:
            return function(root, *args, **kwargs)
        finally:
            transaction.__exit__(None, None, None)

    return locked


class _DesignPreviewHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.html_lang = ""
        self.preview_attrs: dict[str, str] = {}
        self.direction_ids: list[str] = []
        self.direction_anchor_ids: list[str] = []
        self.element_ids: set[str] = set()
        self.fragment_references: list[str] = []
        self.sections: set[str] = set()
        self.external_dependencies: list[str] = []
        self.style_parts: list[str] = []
        self.script_parts: list[str] = []
        self.manifest_parts: list[str] = []
        self._style_depth = 0
        self._script_depth = 0
        self._manifest_depth = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        normalized_tag = tag.lower()
        normalized_attrs = {
            str(name).lower(): "" if value is None else str(value)
            for name, value in attrs
        }
        if normalized_tag == "html":
            self.html_lang = normalized_attrs.get("lang", "").strip()
        if "data-design-preview-schema" in normalized_attrs:
            self.preview_attrs = normalized_attrs

        element_id = normalized_attrs.get("id", "").strip()
        if element_id:
            self.element_ids.add(element_id)
        href = normalized_attrs.get("href", "").strip()
        if href.startswith("#") and len(href) > 1:
            self.fragment_references.append(href[1:])

        direction_id = normalized_attrs.get("data-direction-id", "").strip()
        if direction_id:
            self.direction_ids.append(direction_id)
            self.direction_anchor_ids.append(normalized_attrs.get("id", "").strip())
        section = normalized_attrs.get("data-preview-section", "").strip()
        if section:
            self.sections.add(section)

        if normalized_tag == "style":
            self._style_depth += 1
        if normalized_tag == "script":
            self._script_depth += 1
            if normalized_attrs.get("id") == DESIGN_PREVIEW_MANIFEST_ID:
                self._manifest_depth += 1
            source = normalized_attrs.get("src", "").strip()
            if source:
                self.external_dependencies.append(source)
        if normalized_tag == "link" and normalized_attrs.get("href", "").strip():
            self.external_dependencies.append(normalized_attrs["href"].strip())

        for attribute_name in ("src", "poster"):
            reference = normalized_attrs.get(attribute_name, "").strip()
            if reference and not reference.lower().startswith("data:"):
                self.external_dependencies.append(reference)

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()
        if normalized_tag == "style" and self._style_depth:
            self._style_depth -= 1
        if normalized_tag == "script" and self._script_depth:
            self._script_depth -= 1
            if self._manifest_depth:
                self._manifest_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._style_depth:
            self.style_parts.append(data)
        if self._script_depth:
            self.script_parts.append(data)
        if self._manifest_depth:
            self.manifest_parts.append(data)


class _UITargetHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.html_lang = ""
        self.target_attrs: dict[str, str] = {}
        self.external_dependencies: list[str] = []
        self.inline_event_handlers: list[str] = []
        self.widths: set[str] = set()
        self.states: set[str] = set()
        self.style_parts: list[str] = []
        self.script_parts: list[str] = []
        self.manifest_parts: list[str] = []
        self._style_depth = 0
        self._script_depth = 0
        self._manifest_depth = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        normalized_tag = tag.lower()
        normalized_attrs = {
            str(name).lower(): "" if value is None else str(value)
            for name, value in attrs
        }
        if normalized_tag == "html":
            self.html_lang = normalized_attrs.get("lang", "").strip()
        if "data-ui-target-schema" in normalized_attrs:
            self.target_attrs = normalized_attrs
        width = normalized_attrs.get("data-width", "").strip()
        if width:
            self.widths.add(width)
        state = normalized_attrs.get("data-state", "").strip()
        if normalized_tag == "button" and state:
            self.states.add(state)

        self.inline_event_handlers.extend(
            name for name in normalized_attrs if name.startswith("on")
        )
        if normalized_tag == "style":
            self._style_depth += 1
        if normalized_tag == "script":
            self._script_depth += 1
            if normalized_attrs.get("id") == UI_TARGET_MANIFEST_ID:
                self._manifest_depth += 1
            source = normalized_attrs.get("src", "").strip()
            if source:
                self.external_dependencies.append(source)
        if normalized_tag == "link" and normalized_attrs.get("href", "").strip():
            self.external_dependencies.append(normalized_attrs["href"].strip())
        for attribute_name in ("src", "poster"):
            reference = normalized_attrs.get(attribute_name, "").strip()
            if reference and not reference.lower().startswith("data:"):
                self.external_dependencies.append(reference)

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.lower()
        if normalized_tag == "style" and self._style_depth:
            self._style_depth -= 1
        if normalized_tag == "script" and self._script_depth:
            self._script_depth -= 1
            if self._manifest_depth:
                self._manifest_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._style_depth:
            self.style_parts.append(data)
        if self._script_depth:
            self.script_parts.append(data)
        if self._manifest_depth:
            self.manifest_parts.append(data)


def parse_design_markdown(
    text: str, *, source: str = "design-change.md"
) -> DesignDocument:
    match = FRONT_MATTER_RE.match(text)
    if not match:
        raise DesignLintError(f"{source}: missing YAML front matter")

    front_matter = yaml.safe_load(match.group(1)) or {}
    if not isinstance(front_matter, dict):
        raise DesignLintError(f"{source}: YAML front matter must be a mapping")

    legacy_design_system = front_matter.get("design_system")
    design_change = front_matter.get("design_change")
    if isinstance(legacy_design_system, dict) and isinstance(design_change, dict):
        raise DesignLintError(
            f"{source}: define exactly one of design_change or design_system"
        )
    design_system = (
        design_change if isinstance(design_change, dict) else legacy_design_system
    )
    if not isinstance(design_system, dict):
        raise DesignLintError(
            f"{source}: missing design_change or legacy design_system mapping"
        )

    return DesignDocument(
        source=source,
        front_matter=front_matter,
        design_system=design_system,
        body=match.group(2),
    )


def _normalize_design_change_values(
    values: list[str] | None,
    *,
    field: str,
    required: bool = False,
) -> list[str]:
    normalized: list[str] = []
    for raw in values or []:
        value = str(raw).strip()
        if not value:
            continue
        if value in normalized:
            raise DesignLintError(f"{field} values must be unique")
        normalized.append(value)
    if required and not normalized:
        raise DesignLintError(f"at least one {field} value is required")
    return normalized


def _render_design_change_template(
    template: str,
    *,
    change_id: str,
    title: str,
    change_type: str,
    scopes: list[str],
    profile_ids: list[str],
    baseline_refs: list[str],
    supersedes: list[str],
    iteration_of: str | None,
) -> str:
    replacements = {
        "__DESIGN_CHANGE_ID__": json.dumps(change_id, ensure_ascii=False),
        "__DESIGN_CHANGE_TITLE__": json.dumps(title, ensure_ascii=False),
        "__DESIGN_CHANGE_TYPE__": json.dumps(change_type, ensure_ascii=False),
        "__DESIGN_CHANGE_SCOPES__": json.dumps(scopes, ensure_ascii=False),
        "__DESIGN_CHANGE_PROFILES__": json.dumps(profile_ids, ensure_ascii=False),
        "__DESIGN_CHANGE_BASELINE_REFS__": json.dumps(
            baseline_refs, ensure_ascii=False
        ),
        "__DESIGN_CHANGE_SUPERSEDES__": json.dumps(
            supersedes, ensure_ascii=False
        ),
        "__DESIGN_CHANGE_ITERATION_OF__": json.dumps(
            iteration_of, ensure_ascii=False
        ),
    }
    rendered = template
    for placeholder, value in replacements.items():
        rendered = rendered.replace(placeholder, value)
    return rendered


@_design_index_transaction
def scaffold_design_change(
    project_root: Path,
    *,
    change_id: str,
    title: str,
    change_type: str,
    scopes: list[str],
    profile_ids: list[str],
    baseline_refs: list[str] | None = None,
    supersedes: list[str] | None = None,
    iteration_of: str | None = None,
    basis_sha256: str | None = None,
) -> Path:
    """Create one bounded UI design-change workspace and register its metadata."""

    normalized_id = change_id.strip().upper()
    if not DESIGN_CHANGE_ID_RE.fullmatch(normalized_id):
        raise DesignLintError("change_id must use UD- followed by at least four digits")
    normalized_title = title.strip()
    if not normalized_title:
        raise DesignLintError("design change title is required")
    normalized_type = change_type.strip().lower()
    if normalized_type not in SUPPORTED_DESIGN_CHANGE_TYPES:
        raise DesignLintError(
            "design change type must be one of "
            + ", ".join(sorted(SUPPORTED_DESIGN_CHANGE_TYPES))
        )
    normalized_scopes = _normalize_design_change_values(
        scopes,
        field="scope",
        required=True,
    )
    invalid_scopes = [
        scope
        for scope in normalized_scopes
        if not DESIGN_CHANGE_SCOPE_RE.fullmatch(scope)
    ]
    if invalid_scopes:
        raise DesignLintError(
            "design change scopes must be stable path-like identifiers: "
            + ", ".join(invalid_scopes)
        )
    normalized_profiles = _normalize_design_change_values(
        profile_ids,
        field="profile",
        required=True,
    )
    _selected_design_capability_profiles(normalized_profiles)
    normalized_baselines = _normalize_design_change_values(
        baseline_refs,
        field="baseline_ref",
    )
    normalized_supersedes = _normalize_design_change_values(
        supersedes,
        field="supersedes",
    )
    for superseded_id in normalized_supersedes:
        if not DESIGN_CHANGE_ID_RE.fullmatch(superseded_id):
            raise DesignLintError(
                "supersedes values must use UD- followed by at least four digits"
            )
        if superseded_id == normalized_id:
            raise DesignLintError("a design change cannot supersede itself")

    project_root = project_root.resolve()
    design_root = project_root / ".specify" / "design"
    workspace = design_root / "changes" / normalized_id
    design_path = workspace / "design-change.md"
    if design_path.exists():
        raise DesignLintError(f"design change already exists: {normalized_id}")

    index_path = design_root / "index.json"
    if index_path.exists():
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DesignLintError(f"cannot read design change index: {exc}") from exc
        if not isinstance(index, dict) or index.get("schema") != DESIGN_CHANGE_INDEX_SCHEMA:
            raise DesignLintError("design change index has an invalid schema")
        changes = index.get("changes")
        if not isinstance(changes, list):
            raise DesignLintError("design change index changes must be a list")
    else:
        index = {"schema": DESIGN_CHANGE_INDEX_SCHEMA, "changes": []}
        changes = index["changes"]

    if any(
        isinstance(change, dict) and change.get("id") == normalized_id
        for change in changes
    ):
        raise DesignLintError(f"design change already exists: {normalized_id}")

    template_path = _locate_design_schema("design-change-template.md")
    try:
        template = template_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise DesignLintError(f"cannot read design change template: {exc}") from exc
    rendered = _render_design_change_template(
        template,
        change_id=normalized_id,
        title=normalized_title,
        change_type=normalized_type,
        scopes=normalized_scopes,
        profile_ids=normalized_profiles,
        baseline_refs=normalized_baselines,
        supersedes=normalized_supersedes,
        iteration_of=iteration_of,
    )
    try:
        parsed = parse_design_markdown(rendered, source=str(template_path))
    except (DesignLintError, yaml.YAMLError) as exc:
        raise DesignLintError(f"rendered design change template is invalid: {exc}") from exc
    if parsed.design_system.get("schema") != DESIGN_CHANGE_SCHEMA:
        raise DesignLintError("rendered design change template has an invalid schema")

    relative_design_path = design_path.relative_to(project_root).as_posix()
    record: dict[str, Any] = {
        "id": normalized_id,
        "title": normalized_title,
        "design_ref": relative_design_path,
        "status": "draft",
        "change_type": normalized_type,
        "scope": normalized_scopes,
        "supersedes": normalized_supersedes,
        "approval_sha256": None,
        "consumers": [],
    }
    if iteration_of is not None:
        record["iteration_of"] = iteration_of
        record["basis_sha256"] = basis_sha256
    changes.append(record)
    brief_template = _locate_design_schema("design-brief-template.md")
    try:
        brief = brief_template.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise DesignLintError(f"cannot read design brief template: {exc}") from exc

    atomic_write_text(design_path, rendered)
    atomic_write_text(workspace / "brief.md", brief)
    (workspace / "previews").mkdir(parents=True, exist_ok=True)
    atomic_write_text(
        index_path,
        json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    return design_path


def _load_design_change_index(
    project_root: Path,
) -> tuple[dict[str, Any], Path, dict[str, dict[str, Any]]]:
    index_path = project_root / ".specify" / "design" / "index.json"
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DesignLintError(f"cannot read design change index: {exc}") from exc
    if not isinstance(index, dict) or index.get("schema") != DESIGN_CHANGE_INDEX_SCHEMA:
        raise DesignLintError("design change index has an invalid schema")
    changes = index.get("changes")
    if not isinstance(changes, list):
        raise DesignLintError("design change index changes must be a list")
    records = {
        str(record.get("id") or "").strip(): record
        for record in changes
        if isinstance(record, dict)
    }
    return index, index_path, records


def _design_record_is_registered(record: dict[str, Any]) -> bool:
    return record.get("status") in {"approved", "superseded"} and bool(
        re.fullmatch(r"[0-9a-f]{64}", str(record.get("approval_sha256") or ""))
    )


def _load_registered_design_change(
    project_root: Path,
    change_id: str,
) -> tuple[Path, str, DesignDocument, dict[str, Any]]:
    project_root = project_root.resolve()
    _, _, records = _load_design_change_index(project_root)
    normalized_id = change_id.strip().upper()
    record = records.get(normalized_id)
    if record is None or not _design_record_is_registered(record):
        raise DesignLintError(f"design change {normalized_id} is not registered")
    design_ref = str(record.get("design_ref") or "")
    path = (project_root / design_ref).resolve()
    try:
        path.relative_to(project_root)
        content = path.read_bytes()
    except (ValueError, OSError) as exc:
        raise DesignLintError(f"cannot read registered design change: {exc}") from exc
    digest = hashlib.sha256(content).hexdigest()
    if digest != record.get("approval_sha256"):
        raise DesignLintError(
            f"registered design change {normalized_id} digest does not match its contract"
        )
    document = parse_design_markdown(content.decode("utf-8"), source=str(path))
    return path, digest, document, record


def _design_scope_within(scope: str, root: str) -> bool:
    return scope == root or scope.startswith(f"{root}/")


def _design_scope_intersection(left: str, right: str) -> str | None:
    if _design_scope_within(left, right):
        return left
    if _design_scope_within(right, left):
        return right
    return None


def _superseded_scope_rows(record: dict[str, Any]) -> list[dict[str, str]]:
    raw_rows = record.get("superseded_scopes")
    if not isinstance(raw_rows, list):
        return []
    rows: list[dict[str, str]] = []
    for raw in raw_rows:
        if not isinstance(raw, dict):
            continue
        scope = str(raw.get("scope") or "").strip()
        by = str(raw.get("by") or "").strip()
        if scope and by:
            rows.append({"scope": scope, "by": by})
    return rows


def _design_scope_excluded(record: dict[str, Any], scope: str) -> bool:
    return any(
        _design_scope_within(scope, row["scope"])
        for row in _superseded_scope_rows(record)
    )


def _active_design_intersections(
    record: dict[str, Any],
    scopes: list[str],
) -> list[str]:
    if record.get("status") != "approved":
        return []
    intersections = {
        intersection
        for own_scope in record.get("scope", [])
        if isinstance(own_scope, str)
        for scope in scopes
        if (
            intersection := _design_scope_intersection(own_scope, scope)
        ) is not None
        and not _design_scope_excluded(record, intersection)
    }
    return sorted(intersections)


def _add_superseded_scopes(
    record: dict[str, Any],
    scopes: list[str],
    *,
    by: str,
) -> None:
    rows = _superseded_scope_rows(record)
    for scope in scopes:
        if any(_design_scope_within(scope, row["scope"]) for row in rows):
            continue
        rows = [
            row
            for row in rows
            if not _design_scope_within(row["scope"], scope)
        ]
        rows.append({"scope": scope, "by": by})
    rows.sort(key=lambda row: row["scope"])
    record["superseded_scopes"] = rows
    if all(
        _design_scope_excluded(record, str(scope))
        for scope in record.get("scope", [])
    ):
        record["status"] = "superseded"
        record["superseded_by"] = by


def scaffold_design_iteration(
    project_root: Path,
    *,
    source_id: str,
    change_id: str,
    title: str,
    scopes: list[str] | None = None,
    change_type: str = "preserve",
    profile_ids: list[str] | None = None,
) -> Path:
    """Create a successor draft pinned to one exact registered design change."""

    project_root = project_root.resolve()
    normalized_source = source_id.strip().upper()
    _, source_digest, source_document, source_record = (
        _load_registered_design_change(project_root, normalized_source)
    )
    selected_scopes = list(scopes or [])
    if not selected_scopes:
        if _superseded_scope_rows(source_record):
            raise DesignLintError(
                f"design iteration source {normalized_source} is partially superseded; "
                "pass explicit scopes"
            )
        selected_scopes = [str(value) for value in source_record.get("scope", [])]
    source_scopes = [str(value) for value in source_record.get("scope", [])]
    for scope in selected_scopes:
        if not any(_design_scope_within(scope, root) for root in source_scopes):
            raise DesignLintError(
                f"iteration scope {scope} must stay within source change "
                f"{normalized_source}"
            )
        superseded_overlap = next(
            (
                row
                for row in _superseded_scope_rows(source_record)
                if _design_scope_intersection(scope, row["scope"]) is not None
            ),
            None,
        )
        if superseded_overlap is not None:
            raise DesignLintError(
                f"iteration scope {scope} is no longer active on source "
                f"{normalized_source}; it was superseded by "
                f"{superseded_overlap['by']} for {superseded_overlap['scope']}"
            )
    selected_profiles = list(
        profile_ids or source_document.design_system.get("capability_profiles") or ["web"]
    )
    baseline = (
        f"{source_record['design_ref']}#sha256={source_digest}"
    )
    return scaffold_design_change(
        project_root,
        change_id=change_id,
        title=title,
        change_type=change_type,
        scopes=selected_scopes,
        profile_ids=[str(value) for value in selected_profiles],
        baseline_refs=[baseline],
        supersedes=[normalized_source],
        iteration_of=normalized_source,
        basis_sha256=source_digest,
    )


@_design_index_transaction
def register_design_change(project_root: Path, design_path: Path) -> dict[str, Any]:
    """Register one ready immutable design change and resolve explicit supersedes."""

    project_root = project_root.resolve()
    target = design_path.resolve() if design_path.is_absolute() else (
        project_root / design_path
    ).resolve()
    changes_root = project_root / ".specify" / "design" / "changes"
    try:
        relative_workspace_path = target.relative_to(changes_root)
    except ValueError as exc:
        raise DesignLintError(
            "design change must be inside "
            ".specify/design/changes/<UD-ID>/design-change.md"
        ) from exc
    if (
        len(relative_workspace_path.parts) != 2
        or relative_workspace_path.name != "design-change.md"
    ):
        raise DesignLintError(
            "design change must be inside "
            ".specify/design/changes/<UD-ID>/design-change.md"
        )

    diagnostics = lint_design_file(target, level="ready")
    if diagnostics:
        raise DesignLintError(
            "; ".join(
                f"{diagnostic.code}: {diagnostic.message}"
                for diagnostic in diagnostics
            )
        )
    try:
        content = target.read_bytes()
        document = parse_design_markdown(content.decode("utf-8"), source=str(target))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise DesignLintError(f"cannot read design change: {exc}") from exc
    design_change = document.design_system
    if design_change.get("schema") != DESIGN_CHANGE_SCHEMA:
        raise DesignLintError("only change-scoped design contracts can be registered")
    change_id = str(design_change.get("id") or "").strip()
    if relative_workspace_path.parts[0] != change_id:
        raise DesignLintError("design_change.id must match its workspace directory")

    index, index_path, records = _load_design_change_index(project_root)
    changes = index["changes"]
    record = records.get(change_id)
    if record is None:
        raise DesignLintError(f"design change {change_id} is not registered in index.json")

    digest = hashlib.sha256(content).hexdigest()
    if record.get("status") in {"approved", "superseded"}:
        if record.get("approval_sha256") == digest:
            return deepcopy(record)
        raise DesignLintError(
            f"registered design change {change_id} is immutable; create a new UD-* change"
        )

    scope = design_change.get("scope")
    assert isinstance(scope, dict)
    scopes = [str(value) for value in scope["surfaces"]]
    relationships = design_change.get("relationships")
    assert isinstance(relationships, dict)
    supersedes = [str(value) for value in relationships["supersedes"]]
    iteration_of = str(relationships.get("iteration_of") or "").strip()
    unknown_supersedes = [value for value in supersedes if value not in records]
    if unknown_supersedes:
        raise DesignLintError(
            "design change supersedes unknown IDs: " + ", ".join(unknown_supersedes)
        )

    if iteration_of:
        source = records.get(iteration_of)
        if source is None or not _design_record_is_registered(source):
            raise DesignLintError(
                f"design iteration source {iteration_of} must be registered"
            )
        basis_sha256 = str(record.get("basis_sha256") or "")
        expected_baseline = (
            f"{source['design_ref']}#sha256={basis_sha256}"
        )
        if (
            record.get("iteration_of") != iteration_of
            or basis_sha256 != source.get("approval_sha256")
            or expected_baseline not in design_change.get("baseline_refs", [])
            or iteration_of not in supersedes
        ):
            raise DesignLintError(
                "design iteration must preserve its exact source baseline and "
                "supersedes relationship"
            )

    superseded_records: list[tuple[dict[str, Any], list[str]]] = []
    for other in changes:
        if not isinstance(other, dict) or other.get("id") == change_id:
            continue
        if other.get("status") != "approved":
            continue
        intersections = _active_design_intersections(other, scopes)
        if not intersections:
            continue
        other_id = str(other.get("id") or "")
        if other_id not in supersedes:
            raise DesignLintError(
                f"design change {change_id} overlaps approved design change "
                f"{other_id}; declare supersedes or narrow the scope"
            )
        superseded_records.append((other, intersections))

    relative_design_path = target.relative_to(project_root).as_posix()
    if record.get("design_ref") != relative_design_path:
        raise DesignLintError("design change path does not match index design_ref")
    if record.get("scope") != scopes:
        raise DesignLintError("design change scope does not match its index record")
    if record.get("supersedes") != supersedes:
        raise DesignLintError(
            "design change supersedes relationships do not match its index record"
        )

    for prior, intersections in superseded_records:
        _add_superseded_scopes(prior, intersections, by=change_id)
    record["status"] = "approved"
    record["approval_sha256"] = digest
    atomic_write_text(
        index_path,
        json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    return deepcopy(record)


def _scope_specificity(scope: str) -> int:
    return scope.count("/") * 10_000 + len(scope)


def resolve_design_changes(
    project_root: Path,
    scope: str,
) -> list[dict[str, Any]]:
    """Return active registered candidates for a scope without adopting one."""

    normalized_scope = scope.strip()
    if not DESIGN_CHANGE_SCOPE_RE.fullmatch(normalized_scope):
        raise DesignLintError(
            "design resolve scope must be a stable path-like identifier"
        )
    _, _, records = _load_design_change_index(project_root.resolve())
    candidates: list[tuple[int, dict[str, Any]]] = []
    for record in records.values():
        intersections = _active_design_intersections(record, [normalized_scope])
        if not intersections:
            continue
        matched = max(intersections, key=_scope_specificity)
        candidates.append(
            (
                _scope_specificity(matched),
                {
                    "id": record.get("id"),
                    "design_ref": record.get("design_ref"),
                    "approval_sha256": record.get("approval_sha256"),
                    "matched_scope": matched,
                    "scope": deepcopy(record.get("scope", [])),
                },
            )
        )
    candidates.sort(key=lambda item: (-item[0], str(item[1]["id"])))
    return [item for _, item in candidates]


def _diff_string_sets(before: list[str], after: list[str]) -> dict[str, list[str]]:
    before_set = set(before)
    after_set = set(after)
    return {
        "added": sorted(after_set - before_set),
        "removed": sorted(before_set - after_set),
        "retained": sorted(before_set & after_set),
    }


def _design_rows_by_id(rows: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list):
        return {}
    return {
        str(row["id"]): row
        for row in rows
        if isinstance(row, dict) and str(row.get("id") or "").strip()
    }


def _diff_design_rows(before: Any, after: Any) -> dict[str, list[str]]:
    before_rows = _design_rows_by_id(before)
    after_rows = _design_rows_by_id(after)
    shared = set(before_rows) & set(after_rows)
    return {
        "added": sorted(set(after_rows) - set(before_rows)),
        "removed": sorted(set(before_rows) - set(after_rows)),
        "changed": sorted(
            row_id
            for row_id in shared
            if before_rows[row_id] != after_rows[row_id]
        ),
        "retained": sorted(
            row_id
            for row_id in shared
            if before_rows[row_id] == after_rows[row_id]
        ),
    }


def diff_design_changes(
    project_root: Path,
    from_id: str,
    to_id: str,
) -> dict[str, Any]:
    """Compare two exact registered design contracts semantically."""

    project_root = project_root.resolve()
    from_path, from_digest, before, _ = _load_registered_design_change(
        project_root, from_id
    )
    to_path, to_digest, after, _ = _load_registered_design_change(
        project_root, to_id
    )
    normalized_from = from_id.strip().upper()
    normalized_to = to_id.strip().upper()
    before_design = before.design_system
    after_design = after.design_system
    relationships = after_design.get("relationships")
    if not isinstance(relationships, dict):
        relationships = {}
    sections = (
        "product_context",
        "direction_contract",
        "scope",
        "constraints",
        "platforms",
        "capability_profiles",
        "specimens",
        "tokens",
        "color_modes",
        "components",
        "responsive",
        "content",
        "decisions",
        "verification",
        "accessibility",
    )
    changed_sections = sorted(
        section
        for section in sections
        if before_design.get(section) != after_design.get(section)
    )
    before_scope = before_design.get("scope")
    after_scope = after_design.get("scope")
    before_surfaces = (
        [str(value) for value in before_scope.get("surfaces", [])]
        if isinstance(before_scope, dict)
        else []
    )
    after_surfaces = (
        [str(value) for value in after_scope.get("surfaces", [])]
        if isinstance(after_scope, dict)
        else []
    )
    before_approval = before_design.get("approval")
    after_approval = after_design.get("approval")
    before_handoffs = (
        [str(value) for value in before_approval.get("handoff_contract_ids", [])]
        if isinstance(before_approval, dict)
        else []
    )
    after_handoffs = (
        [str(value) for value in after_approval.get("handoff_contract_ids", [])]
        if isinstance(after_approval, dict)
        else []
    )
    return {
        "schema": "spec-kit-ui-design-diff-v1",
        "from": {
            "id": normalized_from,
            "design_ref": from_path.relative_to(project_root).as_posix(),
            "sha256": from_digest,
        },
        "to": {
            "id": normalized_to,
            "design_ref": to_path.relative_to(project_root).as_posix(),
            "sha256": to_digest,
        },
        "lineage": {
            "direct_iteration": relationships.get("iteration_of")
            == normalized_from,
            "supersedes_source": normalized_from
            in relationships.get("supersedes", []),
        },
        "scope": _diff_string_sets(before_surfaces, after_surfaces),
        "decisions": _diff_design_rows(
            before_design.get("decisions"), after_design.get("decisions")
        ),
        "handoff_contracts": _diff_string_sets(
            before_handoffs, after_handoffs
        ),
        "changed_sections": changed_sections,
    }


def _design_delta_ids(
    delta: Any,
    *,
    include_changed: bool,
) -> list[str]:
    if not isinstance(delta, dict):
        return []
    fields = ("added", "removed", "changed") if include_changed else (
        "added",
        "removed",
    )
    return sorted(
        {
            str(value).strip()
            for field in fields
            for value in delta.get(field, [])
            if isinstance(value, str) and value.strip()
        }
    )


def _design_impact_classes(diff: dict[str, Any]) -> list[str]:
    """Classify one semantic design delta into stable UI impact dimensions."""

    sections = {
        str(value).strip()
        for value in diff.get("changed_sections", [])
        if isinstance(value, str) and value.strip()
    }
    decisions = _design_delta_ids(
        diff.get("decisions"), include_changed=True
    )
    handoffs = _design_delta_ids(
        diff.get("handoff_contracts"), include_changed=False
    )
    predicates = {
        "scope": "scope" in sections,
        "visual": bool(
            sections
            & {
                "direction_contract",
                "specimens",
                "tokens",
                "color_modes",
                "components",
                "decisions",
            }
        )
        or bool(decisions),
        "interaction": bool(
            sections
            & {
                "direction_contract",
                "constraints",
                "components",
                "verification",
                "decisions",
            }
        )
        or bool(decisions)
        or bool(handoffs),
        "component": bool(
            sections & {"capability_profiles", "components"}
        ),
        "responsive": bool(sections & {"platforms", "responsive"}),
        "content": bool(sections & {"product_context", "content"}),
        "accessibility": "accessibility" in sections,
        "verification": "verification" in sections,
        "design-decision": bool(decisions),
        "handoff-contract": bool(handoffs),
    }
    order = (
        "scope",
        "visual",
        "interaction",
        "component",
        "responsive",
        "content",
        "accessibility",
        "verification",
        "design-decision",
        "handoff-contract",
    )
    return [impact_class for impact_class in order if predicates[impact_class]]


def _design_reconciliation_contract(
    *,
    mode: str,
    current_change_id: str | None,
    changed_sections: list[str],
    affected_decision_ids: list[str],
    affected_handoff_contract_ids: list[str],
) -> dict[str, Any]:
    if current_change_id is None:
        if mode == "formal":
            return {
                "preserved_bindings": [],
                "invalidated_bindings": [],
                "reconcile_from": "specify",
                "reconciliation_actions": [
                    "bind_feature_ui_brief",
                    "compile_plan_ui_design_contract",
                    "compile_task_ui_contracts",
                ],
            }
        if mode == "formal-post-specify":
            return {
                "preserved_bindings": [
                    "feature.spec_contract",
                    "feature.requirements",
                    "feature.acceptance_criteria",
                ],
                "invalidated_bindings": [],
                "reconcile_from": "plan",
                "reconciliation_actions": [
                    "compile_plan_ui_design_contract",
                    "compile_task_ui_contracts",
                ],
            }
        return {
            "preserved_bindings": [],
            "invalidated_bindings": [],
            "reconcile_from": "quick-checkpoint",
            "reconciliation_actions": [
                "confirm_quick_design_binding",
                "compile_quick_ui_work_items",
            ],
        }

    material_change = bool(
        changed_sections
        or affected_decision_ids
        or affected_handoff_contract_ids
    )
    if not material_change:
        if mode in {"formal", "formal-post-specify"}:
            preserved = [
                "feature.ui_brief",
                "plan.ui_design_contract",
                "tasks.ui_contracts",
                "implementation.completed_work",
                "review.scope_evidence",
            ]
            if mode == "formal-post-specify":
                preserved = [
                    "feature.spec_contract",
                    "feature.requirements",
                    "feature.acceptance_criteria",
                    *preserved,
                ]
        else:
            preserved = [
                "quick.completed_work_items",
                "quick.pending_worker_packets",
                "review.scope_evidence",
            ]
        return {
            "preserved_bindings": preserved,
            "invalidated_bindings": [],
            "reconcile_from": "none",
            "reconciliation_actions": [],
        }

    if mode == "quick":
        return {
            "preserved_bindings": [
                "quick.completed_work_items",
                "review.unaffected_scope_evidence",
            ],
            "invalidated_bindings": [
                "quick.pending_worker_packets",
                "quick.in_progress_worker_packets",
                "review.affected_scope_evidence",
            ],
            "reconcile_from": "quick-work-items",
            "reconciliation_actions": [
                "retire_unstarted_worker_packets",
                "stop_in_progress_worker_packets_at_safe_boundary",
                "create_corrective_work_item_for_completed_work",
                "recapture_affected_review_evidence",
            ],
        }

    if mode == "formal-post-specify":
        if set(changed_sections).issubset({"verification"}) and not (
            affected_decision_ids or affected_handoff_contract_ids
        ):
            return {
                "preserved_bindings": [
                    "feature.spec_contract",
                    "feature.requirements",
                    "feature.acceptance_criteria",
                    "feature.ui_brief",
                    "plan.ui_design_contract",
                    "tasks.ui_contracts",
                    "implementation.completed_work",
                    "review.unaffected_scope_evidence",
                ],
                "invalidated_bindings": ["review.affected_scope_evidence"],
                "reconcile_from": "review",
                "reconciliation_actions": [
                    "recapture_affected_review_evidence"
                ],
            }
        return {
            "preserved_bindings": [
                "feature.spec_contract",
                "feature.requirements",
                "feature.acceptance_criteria",
                "implementation.completed_work",
                "review.unaffected_scope_evidence",
            ],
            "invalidated_bindings": [
                "plan.ui_design_contract",
                "tasks.ui_contracts",
                "review.affected_scope_evidence",
            ] if current_change_id is not None else [],
            "reconcile_from": "plan",
            "reconciliation_actions": [
                "recompile_plan_ui_design_contract",
                "recompile_task_ui_contracts",
                "recapture_affected_review_evidence",
            ],
        }

    specify_sections = {
        "product_context",
        "direction_contract",
        "scope",
        "constraints",
        "platforms",
        "content",
        "accessibility",
    }
    if specify_sections.intersection(changed_sections):
        return {
            "preserved_bindings": [
                "implementation.completed_work",
                "review.unaffected_scope_evidence",
            ],
            "invalidated_bindings": [
                "feature.ui_brief",
                "plan.ui_design_contract",
                "tasks.ui_contracts",
                "review.affected_scope_evidence",
            ],
            "reconcile_from": "specify",
            "reconciliation_actions": [
                "rebind_feature_ui_brief",
                "recompile_plan_ui_design_contract",
                "recompile_task_ui_contracts",
                "recapture_affected_review_evidence",
            ],
        }
    if set(changed_sections).issubset({"verification"}) and not (
        affected_decision_ids or affected_handoff_contract_ids
    ):
        return {
            "preserved_bindings": [
                "feature.ui_brief",
                "plan.ui_design_contract",
                "tasks.ui_contracts",
                "implementation.completed_work",
                "review.unaffected_scope_evidence",
            ],
            "invalidated_bindings": ["review.affected_scope_evidence"],
            "reconcile_from": "review",
            "reconciliation_actions": [
                "recapture_affected_review_evidence"
            ],
        }
    return {
        "preserved_bindings": [
            "feature.ui_brief",
            "implementation.completed_work",
            "review.unaffected_scope_evidence",
        ],
        "invalidated_bindings": [
            "plan.ui_design_contract",
            "tasks.ui_contracts",
            "review.affected_scope_evidence",
        ],
        "reconcile_from": "plan",
        "reconciliation_actions": [
            "recompile_plan_ui_design_contract",
            "recompile_task_ui_contracts",
            "recapture_affected_review_evidence",
        ],
    }


def _normalize_design_adoption_identity(
    *,
    consumer_ref: str,
    change_id: str,
    scope: str,
    mode: str,
    expected_change: str,
) -> tuple[str, str, str, str, str]:
    consumer = consumer_ref.strip()
    change = change_id.strip().upper()
    exact_scope = scope.strip()
    adoption_mode = mode.strip().lower()
    expected = expected_change.strip().upper()
    if not DESIGN_CHANGE_SCOPE_RE.fullmatch(consumer):
        raise DesignLintError(
            "design adoption consumer reference must be a stable identifier"
        )
    if not DESIGN_CHANGE_ID_RE.fullmatch(change):
        raise DesignLintError("design adoption requires a UD-* change")
    if not DESIGN_CHANGE_SCOPE_RE.fullmatch(exact_scope):
        raise DesignLintError(
            "design adoption scope must be a stable path-like identifier"
        )
    if adoption_mode not in {"formal", "formal-post-specify", "quick"}:
        raise DesignLintError(
            "design adoption mode must be formal, formal-post-specify, or quick"
        )
    if expected != "NONE" and not DESIGN_CHANGE_ID_RE.fullmatch(expected):
        raise DesignLintError("expected current change must be a UD-* ID or none")
    if adoption_mode in {"formal", "formal-post-specify"} and not consumer.startswith("feature:"):
        raise DesignLintError(
            "formal design adoption consumer must use feature:<id>"
        )
    if adoption_mode == "quick" and not consumer.startswith("quick:"):
        raise DesignLintError(
            "quick design adoption consumer must use quick:<id>"
        )
    return consumer, change, exact_scope, adoption_mode, expected


def _active_design_adoption_record(
    records: dict[str, dict[str, Any]],
    *,
    change_id: str,
    scope: str,
) -> dict[str, Any]:
    record = records.get(change_id)
    if (
        record is None
        or not _design_record_is_registered(record)
        or not _active_design_intersections(record, [scope])
    ):
        raise DesignLintError(
            f"design change {change_id} is not active for scope {scope}"
        )
    roots = [str(value) for value in record.get("scope", [])]
    if not any(_design_scope_within(scope, root) for root in roots):
        raise DesignLintError(
            f"design change {change_id} cannot be the singular binding "
            f"for scope {scope}"
        )
    return record


def _current_design_adoption(
    index: dict[str, Any],
    *,
    consumer_ref: str,
    scope: str,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    raw_adoptions = index.get("adoptions", [])
    if not isinstance(raw_adoptions, list):
        raise DesignLintError("design change index adoptions must be a list")
    matching = [
        row
        for row in raw_adoptions
        if isinstance(row, dict)
        and row.get("consumer_ref") == consumer_ref
        and row.get("scope") == scope
    ]
    current_rows = [
        row for row in matching if row.get("status") == "current"
    ]
    if len(current_rows) > 1:
        raise DesignLintError(
            "design change index has multiple current adoptions for one scope"
        )
    return matching, current_rows[0] if current_rows else None


def _build_design_adoption_impact(
    project_root: Path,
    *,
    index: dict[str, Any],
    records: dict[str, dict[str, Any]],
    consumer_ref: str,
    change_id: str,
    scope: str,
    mode: str,
    expected_change: str,
) -> dict[str, Any]:
    _active_design_adoption_record(records, change_id=change_id, scope=scope)
    _, current = _current_design_adoption(
        index, consumer_ref=consumer_ref, scope=scope
    )
    current_id = str(current.get("change_id") or "").upper() if current else "NONE"
    if current_id != expected_change:
        raise DesignLintError(
            f"expected current change {expected_change} but found {current_id}"
        )

    _, candidate_digest, _, _ = _load_registered_design_change(
        project_root, change_id
    )
    current_digest: str | None = None
    changed_sections: list[str] = []
    affected_decisions: list[str] = []
    affected_handoffs: list[str] = []
    semantic_diff: dict[str, Any] = {
        "changed_sections": [],
        "decisions": {},
        "handoff_contracts": {},
    }
    if current is not None:
        raw_diff = diff_design_changes(project_root, current_id, change_id)
        from_binding = raw_diff.get("from")
        current_digest = (
            str(from_binding.get("sha256") or "")
            if isinstance(from_binding, dict)
            else None
        )
        # Both immutable changes are validated to cover this exact consumer
        # scope. Contract-root narrowing elsewhere must not invalidate this
        # consumer merely because the change-level scope arrays differ.
        changed_sections = [
            section
            for section in raw_diff.get("changed_sections", [])
            if isinstance(section, str) and section != "scope"
        ]
        affected_decisions = _design_delta_ids(
            raw_diff.get("decisions"), include_changed=True
        )
        affected_handoffs = _design_delta_ids(
            raw_diff.get("handoff_contracts"), include_changed=False
        )
        semantic_diff = deepcopy(raw_diff)
        semantic_diff["changed_sections"] = changed_sections

    reconciliation = _design_reconciliation_contract(
        mode=mode,
        current_change_id=current_id if current is not None else None,
        changed_sections=changed_sections,
        affected_decision_ids=affected_decisions,
        affected_handoff_contract_ids=affected_handoffs,
    )
    impact: dict[str, Any] = {
        "schema": "spec-kit-ui-design-impact-v1",
        "consumer_ref": consumer_ref,
        "scope": scope,
        "mode": mode,
        "current_change_id": current_id if current is not None else None,
        "candidate_change_id": change_id,
        "current_design_sha256": current_digest,
        "candidate_design_sha256": candidate_digest,
        "impact_classes": _design_impact_classes(semantic_diff),
        "changed_sections": changed_sections,
        "affected_decision_ids": affected_decisions,
        "affected_handoff_contract_ids": affected_handoffs,
        **reconciliation,
    }
    impact["impact_sha256"] = _canonical_json_sha256(impact)
    return impact


def impact_design_adoption(
    project_root: Path,
    *,
    consumer_ref: str,
    change_id: str,
    scope: str,
    mode: str,
    expected_change: str,
) -> dict[str, Any]:
    """Preview scope-bounded consumer reconciliation without changing state."""

    project_root = project_root.resolve()
    (
        normalized_consumer,
        normalized_change,
        normalized_scope,
        normalized_mode,
        normalized_expected,
    ) = _normalize_design_adoption_identity(
        consumer_ref=consumer_ref,
        change_id=change_id,
        scope=scope,
        mode=mode,
        expected_change=expected_change,
    )
    index, _, records = _load_design_change_index(project_root)
    return _build_design_adoption_impact(
        project_root,
        index=index,
        records=records,
        consumer_ref=normalized_consumer,
        change_id=normalized_change,
        scope=normalized_scope,
        mode=normalized_mode,
        expected_change=normalized_expected,
    )


def _json_contains_design_field(value: Any, key: str, expected: str) -> bool:
    if isinstance(value, dict):
        if key in value and str(value[key]).strip() == expected:
            return True
        return any(
            _json_contains_design_field(child, key, expected)
            for child in value.values()
        )
    if isinstance(value, list):
        return any(
            _json_contains_design_field(child, key, expected) for child in value
        )
    return False


def _binding_contains_design_fields(
    content: bytes,
    fields: dict[str, str],
) -> bool:
    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError):
        text = content.decode("utf-8", errors="replace").replace("\r\n", "\n").replace(
            "\r", "\n"
        )
        return all(
            re.search(
                rf"(?m)^[ \t]*(?:[-*][ \t]+)?{re.escape(key)}[ \t]*:[ \t]*"
                rf"(?:{re.escape(value)}|\"{re.escape(value)}\"|'{re.escape(value)}')"
                r"[ \t]*$",
                text,
            )
            is not None
            for key, value in fields.items()
        )
    return all(
        _json_contains_design_field(payload, key, value)
        for key, value in fields.items()
    )


def _planning_ready_spec_binding(content: bytes) -> bool:
    try:
        payload = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False
    return (
        isinstance(payload, dict)
        and str(payload.get("status") or "").strip().lower() == "planning-ready"
    )


class _UniqueKeySafeLoader(yaml.SafeLoader):
    pass


def _construct_unique_yaml_mapping(
    loader: _UniqueKeySafeLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[Any, Any]:
    loader.flatten_mapping(node)
    mapping: dict[Any, Any] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            duplicate = key in mapping
        except TypeError as exc:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                "found an unhashable mapping key",
                key_node.start_mark,
            ) from exc
        if duplicate:
            raise yaml.constructor.ConstructorError(
                "while constructing a mapping",
                node.start_mark,
                f"found duplicate mapping key {key!r}",
                key_node.start_mark,
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeySafeLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_yaml_mapping,
)


def _quick_confirmation_string_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(
        not isinstance(item, str) for item in value
    ):
        raise DesignLintError(
            f"quick design adoption confirmation is invalid: "
            f"{field} must be an array of strings"
        )
    return list(value)


def _quick_confirmation_required_text(
    value: Any,
    field: str,
) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DesignLintError(
            f"quick design adoption confirmation is invalid: {field} is required"
        )
    return value


def _quick_confirmation_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    if isinstance(value, (int, float)):
        return value != 0
    return False


def _validate_quick_confirmation_document(
    confirmation: dict[str, Any],
) -> dict[str, Any]:
    decision = confirmation.get("decision")
    if not isinstance(decision, dict):
        decision = {}
    _quick_confirmation_required_text(decision.get("goal"), "decision.goal")
    _quick_confirmation_required_text(
        decision.get("user_visible_result"),
        "decision.user_visible_result",
    )
    scope = decision.get("scope")
    if not isinstance(scope, dict):
        scope = {}
    included = _quick_confirmation_string_list(
        scope.get("include"), "decision.scope.include"
    )
    _quick_confirmation_string_list(
        scope.get("exclude"), "decision.scope.exclude"
    )
    _quick_confirmation_string_list(scope.get("defer"), "decision.scope.defer")
    if not included:
        raise DesignLintError(
            "quick design adoption confirmation is invalid: "
            "decision.scope.include must not be empty"
        )
    _quick_confirmation_required_text(
        decision.get("reconfirmation_trigger"),
        "decision.reconfirmation_trigger",
    )
    recommended_approach = decision.get("recommended_approach")
    if recommended_approach is not None and not isinstance(
        recommended_approach, str
    ):
        raise DesignLintError(
            "quick design adoption confirmation is invalid: "
            "decision.recommended_approach must be a string"
        )
    _quick_confirmation_string_list(
        decision.get("assumptions_and_risks"),
        "decision.assumptions_and_risks",
    )
    _quick_confirmation_string_list(
        decision.get("completion_evidence"),
        "decision.completion_evidence",
    )
    _quick_confirmation_string_list(
        decision.get("user_corrections"),
        "decision.user_corrections",
    )

    items = decision.get("items")
    if not isinstance(items, list) or not items:
        raise DesignLintError(
            "quick design adoption confirmation is invalid: "
            "decision.items must not be empty"
        )
    seen: set[str] = set()
    item_by_id: dict[str, dict[str, Any]] = {}
    dependencies: dict[str, list[str]] = {}
    for raw_item in items:
        if not isinstance(raw_item, dict):
            raise DesignLintError(
                "quick design adoption confirmation is invalid: "
                "work item id must match Q1, Q2, ..."
            )
        raw_id = raw_item.get("id")
        item_id = raw_id.strip() if isinstance(raw_id, str) else ""
        if re.fullmatch(r"Q[1-9][0-9]*", item_id) is None:
            raise DesignLintError(
                "quick design adoption confirmation is invalid: "
                f"work item id {raw_id!r} must match Q1, Q2, ..."
            )
        if item_id in seen:
            raise DesignLintError(
                "quick design adoption confirmation is invalid: "
                f"duplicate work item id {item_id}"
            )
        seen.add(item_id)
        _quick_confirmation_required_text(
            raw_item.get("deliverable"), f"{item_id} deliverable"
        )
        _quick_confirmation_required_text(
            raw_item.get("acceptance"), f"{item_id} acceptance"
        )
        dependencies[item_id] = _quick_confirmation_string_list(
            raw_item.get("depends_on"), f"{item_id}.depends_on"
        )
        _quick_confirmation_string_list(
            raw_item.get("write_scope"), f"{item_id}.write_scope"
        )
        item_by_id[item_id] = raw_item
    for item_id, item_dependencies in dependencies.items():
        for dependency in item_dependencies:
            if dependency not in seen:
                raise DesignLintError(
                    "quick design adoption confirmation is invalid: "
                    f"{item_id} depends on missing item {dependency}"
                )
            if dependency == item_id:
                raise DesignLintError(
                    "quick design adoption confirmation is invalid: "
                    f"{item_id} cannot depend on itself"
                )

    visit_state: dict[str, int] = {}

    def visit(item_id: str) -> None:
        if visit_state.get(item_id) == 1:
            raise DesignLintError(
                "quick design adoption confirmation is invalid: "
                f"dependency cycle detected at {item_id}"
            )
        if visit_state.get(item_id) == 2:
            return
        visit_state[item_id] = 1
        for dependency in dependencies[item_id]:
            visit(dependency)
        visit_state[item_id] = 2

    for item_id in sorted(seen):
        visit(item_id)

    delivery = confirmation.get("delivery")
    if not isinstance(delivery, dict):
        delivery = {}
    waves = delivery.get("waves")
    if not isinstance(waves, list) or not waves:
        raise DesignLintError(
            "quick design adoption confirmation is invalid: "
            "delivery.waves must not be empty"
        )
    covered: dict[str, str] = {}
    for raw_wave in waves:
        if not isinstance(raw_wave, dict):
            raise DesignLintError(
                "quick design adoption confirmation is invalid: "
                "delivery wave id is required"
            )
        wave_id = _quick_confirmation_required_text(
            raw_wave.get("id"), "delivery wave id"
        ).strip()
        item_ids = _quick_confirmation_string_list(
            raw_wave.get("item_ids"), f"delivery wave {wave_id}.item_ids"
        )
        if not item_ids:
            raise DesignLintError(
                "quick design adoption confirmation is invalid: "
                f"delivery wave {wave_id} has no items"
            )
        parallel = raw_wave.get("parallel", False)
        if not isinstance(parallel, bool):
            raise DesignLintError(
                "quick design adoption confirmation is invalid: "
                f"delivery wave {wave_id}.parallel must be a boolean"
            )
        for item_id in item_ids:
            if item_id not in seen:
                raise DesignLintError(
                    "quick design adoption confirmation is invalid: "
                    f"delivery wave {wave_id} references unknown item {item_id}"
                )
            if item_id in covered:
                raise DesignLintError(
                    "quick design adoption confirmation is invalid: "
                    f"item {item_id} appears in multiple waves "
                    f"({covered[item_id]} and {wave_id})"
                )
            covered[item_id] = wave_id
        if parallel or len(item_ids) > 1:
            seen_paths: dict[str, str] = {}
            for item_id in item_ids:
                for path in _quick_confirmation_string_list(
                    item_by_id[item_id].get("write_scope"),
                    f"{item_id}.write_scope",
                ):
                    normalized_path = path.strip().replace("\\", "/")
                    if not normalized_path:
                        continue
                    owner = seen_paths.get(normalized_path)
                    if owner is not None and owner != item_id:
                        raise DesignLintError(
                            "quick design adoption confirmation is invalid: "
                            f"parallel wave {wave_id} has write-scope conflict "
                            f"on {normalized_path} between {owner} and {item_id}"
                        )
                    seen_paths[normalized_path] = item_id
    for item_id in seen:
        if item_id not in covered:
            raise DesignLintError(
                "quick design adoption confirmation is invalid: "
                f"item {item_id} is not assigned to any delivery wave"
            )

    ui_confirmation = decision.get("ui_confirmation")
    if ui_confirmation is not None:
        if not isinstance(ui_confirmation, dict):
            raise DesignLintError(
                "quick design adoption confirmation is invalid: "
                "decision.ui_confirmation must be an object"
            )
        if not (
            "applicable" in ui_confirmation
            and not _quick_confirmation_bool(ui_confirmation.get("applicable"))
        ):
            for field in (
                "confirmation_purpose",
                "user_and_primary_job",
                "target_experience",
            ):
                _quick_confirmation_required_text(
                    ui_confirmation.get(field), f"ui_confirmation.{field}"
                )
            evidence = ui_confirmation.get("acceptance_evidence")
            evidence_values = (
                evidence if isinstance(evidence, list) else [evidence]
            )
            if not any(
                value is not None and str(value).strip()
                for value in evidence_values
            ):
                raise DesignLintError(
                    "quick design adoption confirmation is invalid: "
                    "ui_confirmation.acceptance_evidence is required when "
                    "UI confirmation is present"
                )
            continuity_result = validate_ui_source_continuity(
                ui_confirmation.get("source_continuity"),
                require_ready=True,
            )
            if not continuity_result.valid:
                details = "; ".join(
                    f"{error.path}: {error.message}"
                    for error in continuity_result.errors
                )
                raise DesignLintError(
                    "quick design adoption confirmation is invalid: "
                    "ui_confirmation.source_continuity is required and must "
                    "be ready: "
                    + details
                )
    return decision


def _stable_go_json(value: Any) -> str:
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise DesignLintError(
                "quick design adoption confirmation digest contains a "
                "non-string object key"
            )
        return "{" + ",".join(
            f"{_stable_go_json(key)}:{_stable_go_json(value[key])}"
            for key in sorted(value)
        ) + "}"
    if isinstance(value, list):
        return "[" + ",".join(_stable_go_json(item) for item in value) + "]"
    if isinstance(value, str):
        return (
            json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            .replace("<", r"\u003c")
            .replace(">", r"\u003e")
            .replace("&", r"\u0026")
            .replace("\u2028", r"\u2028")
            .replace("\u2029", r"\u2029")
        )
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise DesignLintError(
            f"quick design adoption cannot canonicalize confirmation digest: {exc}"
        ) from exc


def _quick_confirmation_digest(decision: dict[str, Any]) -> str:
    scope = decision.get("scope")
    if not isinstance(scope, dict):
        scope = {}
    items = decision.get("items")
    if not isinstance(items, list):
        items = []
    normalized_items: list[dict[str, Any]] = []
    for item in sorted(items, key=lambda row: str(row.get("id") or "")):
        dependencies = item.get("depends_on")
        if not isinstance(dependencies, list):
            dependencies = []
        normalized_items.append(
            {
                "id": item.get("id") or "",
                "deliverable": item.get("deliverable") or "",
                "depends_on": sorted(dependencies),
                "acceptance": item.get("acceptance") or "",
            }
        )
    protected = {
        "schema": "quick-confirmation-v1",
        "goal": decision.get("goal") or "",
        "user_visible_result": decision.get("user_visible_result") or "",
        "scope": {
            "include": list(scope.get("include") or []),
            "exclude": list(scope.get("exclude") or []),
            "defer": list(scope.get("defer") or []),
        },
        "items": normalized_items,
        "recommended_approach": decision.get("recommended_approach") or "",
        "assumptions_and_risks": list(
            decision.get("assumptions_and_risks") or []
        ),
        "completion_evidence": list(decision.get("completion_evidence") or []),
        "reconfirmation_trigger": decision.get("reconfirmation_trigger") or "",
        "ui_confirmation": decision.get("ui_confirmation"),
    }
    return hashlib.sha256(_stable_go_json(protected).encode("utf-8")).hexdigest()


def _quick_status_design_binding(text: str) -> dict[str, str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    headings = list(
        re.finditer(r"(?mi)^##[ \t]+UI Design Binding[ \t]*$", normalized)
    )
    structural_error = (
        "quick design adoption STATUS.md must contain exactly one "
        "## UI Design Binding section with one ui_design_binding mapping"
    )
    if len(headings) != 1:
        raise DesignLintError(structural_error)
    section = normalized[headings[0].end() :]
    next_heading = re.search(r"(?m)^##(?:[ \t]+|$)", section)
    if next_heading is not None:
        section = section[: next_heading.start()]
    section = re.sub(r"(?s)<!--.*?-->", "", section)
    if len(re.findall(r"(?m)^ui_design_binding[ \t]*:", section)) != 1:
        raise DesignLintError(structural_error)
    try:
        payload = yaml.load(section, Loader=_UniqueKeySafeLoader)
    except yaml.YAMLError as exc:
        raise DesignLintError(f"{structural_error}: {exc}") from exc
    binding = payload.get("ui_design_binding") if isinstance(payload, dict) else None
    if not isinstance(binding, dict):
        raise DesignLintError(structural_error)
    return {
        str(key).strip(): str(value or "").strip()
        for key, value in binding.items()
    }


@_design_index_transaction
def adopt_design_change(
    project_root: Path,
    *,
    consumer_ref: str,
    change_id: str,
    scope: str,
    mode: str,
    binding_ref: Path,
    binding_sha256: str,
    expected_change: str,
) -> dict[str, Any]:
    """Append a CAS-guarded consumer adoption receipt for an exact binding."""

    project_root = project_root.resolve()
    (
        normalized_consumer,
        normalized_change,
        normalized_scope,
        normalized_mode,
        normalized_expected,
    ) = _normalize_design_adoption_identity(
        consumer_ref=consumer_ref,
        change_id=change_id,
        scope=scope,
        mode=mode,
        expected_change=expected_change,
    )
    normalized_binding_digest = binding_sha256.strip().lower()
    if not re.fullmatch(r"[0-9a-f]{64}", normalized_binding_digest):
        raise DesignLintError("design adoption requires a binding SHA-256")

    index, index_path, records = _load_design_change_index(project_root)
    record = _active_design_adoption_record(
        records, change_id=normalized_change, scope=normalized_scope
    )

    design_path, design_digest, _, _ = _load_registered_design_change(
        project_root, normalized_change
    )
    design_ref = str(record["design_ref"])
    design_contract_ref = (
        Path(design_ref).parent / "design-contract.json"
    ).as_posix()
    contract_path = (project_root / design_contract_ref).resolve()
    try:
        contract_path.relative_to(project_root)
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except (ValueError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DesignLintError(
            f"cannot read design contract export {design_contract_ref}: {exc}"
        ) from exc
    if not isinstance(contract, dict) or contract.get("id") != normalized_change:
        raise DesignLintError(
            f"design contract export does not match {normalized_change}"
        )
    try:
        expected_contract = json.loads(
            export_design_system(design_path, export_format="json")
        )
    except (DesignLintError, json.JSONDecodeError) as exc:
        raise DesignLintError(
            f"cannot verify design contract export for {normalized_change}: {exc}"
        ) from exc
    if contract != expected_contract:
        raise DesignLintError(
            f"design contract export does not match the registered design "
            f"{normalized_change}"
        )

    binding_path = (
        binding_ref.resolve()
        if binding_ref.is_absolute()
        else (project_root / binding_ref).resolve()
    )
    try:
        relative_binding = binding_path.relative_to(project_root).as_posix()
        binding_content = binding_path.read_bytes()
    except (ValueError, OSError) as exc:
        raise DesignLintError(f"cannot read design adoption binding: {exc}") from exc
    if normalized_mode in {"formal", "formal-post-specify"}:
        if not normalized_consumer.startswith("feature:"):
            raise DesignLintError(
                "formal design adoption consumer must use feature:<id>"
            )
        if not (
            relative_binding.endswith("/spec-contract.json")
            and (
                relative_binding.startswith("specs/")
                or relative_binding.startswith(".specify/features/")
            )
        ):
            raise DesignLintError(
                "formal design adoption binding must be a feature spec-contract.json"
            )
        if (
            normalized_mode == "formal-post-specify"
            and not _planning_ready_spec_binding(binding_content)
        ):
            raise DesignLintError(
                "formal-post-specify design adoption requires an unchanged "
                "planning-ready source spec-contract.json"
            )
    else:
        if not normalized_consumer.startswith("quick:"):
            raise DesignLintError(
                "quick design adoption consumer must use quick:<id>"
            )
        if not (
            relative_binding.startswith(".planning/quick/")
            and relative_binding.endswith("/STATUS.md")
        ):
            raise DesignLintError(
                "quick design adoption binding must be .planning/quick/<id>/STATUS.md"
            )
        text = binding_content.decode("utf-8", errors="replace")
        frontmatter_match = FRONT_MATTER_RE.match(text)
        try:
            frontmatter = (
                yaml.safe_load(frontmatter_match.group(1))
                if frontmatter_match is not None
                else None
            )
        except yaml.YAMLError as exc:
            raise DesignLintError(
                f"quick design adoption STATUS.md frontmatter is invalid: {exc}"
            ) from exc
        if not isinstance(frontmatter, dict) or frontmatter.get(
            "understanding_confirmed"
        ) is not True:
            raise DesignLintError(
                "quick design adoption checkpoint must be confirmed in STATUS.md"
            )
        status_binding = _quick_status_design_binding(text)
        confirmation_path = binding_path.parent / "confirmation.json"
        try:
            confirmation = json.loads(
                confirmation_path.read_text(encoding="utf-8")
            )
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise DesignLintError(
                "quick design adoption checkpoint must be confirmed through "
                f"confirmation.json: {exc}"
            ) from exc
        if (
            not isinstance(confirmation, dict)
            or confirmation.get("schema") != "quick-confirmation-v1"
            or confirmation.get("confirmation_state")
            not in {"confirmed", "inherited"}
        ):
            raise DesignLintError(
                "quick design adoption checkpoint must be confirmed or inherited"
            )
        decision = _validate_quick_confirmation_document(confirmation)
        confirmation_digest = str(
            confirmation.get("confirmation_digest") or ""
        ).strip()
        expected_confirmation_digest = _quick_confirmation_digest(decision)
        if confirmation_digest != expected_confirmation_digest:
            raise DesignLintError(
                "quick design adoption confirmation digest does not match "
                "the protected decision"
            )
        ui_confirmation = (
            decision.get("ui_confirmation")
            if isinstance(decision, dict)
            else None
        )
        confirmed_binding = (
            ui_confirmation.get("design_binding")
            if isinstance(ui_confirmation, dict)
            else None
        )
        expected_confirmation_binding = {
            "scope": normalized_scope,
            "design_change_id": normalized_change,
            "design_change_ref": design_ref,
            "design_change_sha256": design_digest,
            "design_contract_ref": design_contract_ref,
        }
        if (
            not re.fullmatch(r"[0-9a-f]{64}", confirmation_digest)
            or not isinstance(ui_confirmation, dict)
            or ui_confirmation.get("applicable") is not True
            or not isinstance(confirmed_binding, dict)
            or set(confirmed_binding) != set(expected_confirmation_binding)
            or any(
                str(confirmed_binding.get(key) or "").strip() != value
                for key, value in expected_confirmation_binding.items()
            )
        ):
            raise DesignLintError(
                "quick design adoption requires the confirmed UI design binding "
                "to match the exact scope and registered change"
            )
    actual_binding_digest = hashlib.sha256(binding_content).hexdigest()
    if actual_binding_digest != normalized_binding_digest:
        raise DesignLintError(
            f"design adoption binding SHA-256 does not match {relative_binding}"
        )
    expected_fields = {
        "design_change_id": normalized_change,
        "design_change_ref": design_ref,
        "design_change_sha256": design_digest,
        "design_contract_ref": design_contract_ref,
    }
    if normalized_mode == "quick":
        expected_fields["scope"] = normalized_scope
    if (
        normalized_mode != "formal-post-specify"
        and not _binding_contains_design_fields(binding_content, expected_fields)
    ):
        raise DesignLintError(
            "design adoption binding does not contain the exact registered "
            "change fields"
        )
    if normalized_mode == "quick":
        normalized_confirmed_binding = {
            str(key).strip(): str(value or "").strip()
            for key, value in confirmed_binding.items()
        }
        if (
            status_binding != expected_confirmation_binding
            or status_binding != normalized_confirmed_binding
        ):
            raise DesignLintError(
                "quick design adoption STATUS.md ui_design_binding must "
                "exact-match confirmation.json design binding"
            )

    adoptions = index.setdefault("adoptions", [])
    if not isinstance(adoptions, list):
        raise DesignLintError("design change index adoptions must be a list")
    matching, current = _current_design_adoption(
        index,
        consumer_ref=normalized_consumer,
        scope=normalized_scope,
    )
    current_id = str(current.get("change_id")) if current else "NONE"
    if current_id != normalized_expected:
        raise DesignLintError(
            f"expected current change {normalized_expected} but found {current_id}"
        )
    if (
        current is not None
        and current_id == normalized_change
        and current.get("mode") == normalized_mode
        and current.get("binding_sha256") == actual_binding_digest
    ):
        return deepcopy(current)

    impact = _build_design_adoption_impact(
        project_root,
        index=index,
        records=records,
        consumer_ref=normalized_consumer,
        change_id=normalized_change,
        scope=normalized_scope,
        mode=normalized_mode,
        expected_change=normalized_expected,
    )

    revision = max(
        [int(row.get("revision") or 0) for row in matching] or [0]
    ) + 1
    if current is not None:
        current["status"] = "superseded"
        current["superseded_by_revision"] = revision
    receipt: dict[str, Any] = {
        "consumer_ref": normalized_consumer,
        "scope": normalized_scope,
        "mode": normalized_mode,
        "revision": revision,
        "status": "current",
        "change_id": normalized_change,
        "design_change_id": normalized_change,
        "design_ref": design_ref,
        "design_sha256": design_digest,
        "design_change_ref": design_ref,
        "design_change_sha256": design_digest,
        "design_contract_ref": design_contract_ref,
        "binding_ref": relative_binding,
        "binding_sha256": actual_binding_digest,
        "previous_change_id": current_id if current else None,
    }
    for field in (
        "impact_sha256",
        "impact_classes",
        "preserved_bindings",
        "invalidated_bindings",
        "reconcile_from",
        "reconciliation_actions",
        "changed_sections",
        "affected_decision_ids",
        "affected_handoff_contract_ids",
    ):
        receipt[field] = deepcopy(impact[field])
    adoptions.append(receipt)
    for change_record in records.values():
        consumers = change_record.get("consumers")
        if not isinstance(consumers, list):
            consumers = []
        change_record["consumers"] = [
            row
            for row in consumers
            if not (
                isinstance(row, dict)
                and row.get("consumer_ref") == normalized_consumer
                and row.get("scope") == normalized_scope
            )
        ]
    record["consumers"].append(
        {
            "consumer_ref": normalized_consumer,
            "scope": normalized_scope,
            "mode": normalized_mode,
            "revision": revision,
        }
    )
    atomic_write_text(
        index_path,
        json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    return deepcopy(receipt)


def resolve_design_adoption(
    project_root: Path,
    *,
    consumer_ref: str,
    scope: str,
    binding_ref: Path,
    binding_sha256: str,
    expected_change: str | None = None,
) -> dict[str, Any]:
    """Verify the current post-Specify design overlay without mutating state."""

    project_root = project_root.resolve()
    normalized_consumer = consumer_ref.strip()
    normalized_scope = scope.strip()
    normalized_digest = binding_sha256.strip().lower()
    if not DESIGN_CHANGE_SCOPE_RE.fullmatch(normalized_consumer):
        raise DesignLintError(
            "design adoption consumer reference must be a stable identifier"
        )
    if not normalized_consumer.startswith("feature:"):
        raise DesignLintError(
            "formal-post-specify adoption consumer must use feature:<id>"
        )
    if not DESIGN_CHANGE_SCOPE_RE.fullmatch(normalized_scope):
        raise DesignLintError(
            "design adoption scope must be a stable path-like identifier"
        )
    if not re.fullmatch(r"[0-9a-f]{64}", normalized_digest):
        raise DesignLintError("design adoption requires a binding SHA-256")

    index, _, records = _load_design_change_index(project_root)
    _, current = _current_design_adoption(
        index,
        consumer_ref=normalized_consumer,
        scope=normalized_scope,
    )
    if current is None:
        raise DesignLintError(
            "no current design adoption exists for the feature and scope"
        )
    if current.get("mode") != "formal-post-specify":
        raise DesignLintError(
            "current design adoption is not a formal-post-specify overlay"
        )
    change_id = str(current.get("change_id") or "").strip().upper()
    if expected_change is not None:
        normalized_expected = expected_change.strip().upper()
        if not DESIGN_CHANGE_ID_RE.fullmatch(normalized_expected):
            raise DesignLintError("expected current change must be a UD-* ID")
        if change_id != normalized_expected:
            raise DesignLintError(
                f"expected current change {normalized_expected} but found {change_id}"
            )

    binding_path = (
        binding_ref.resolve()
        if binding_ref.is_absolute()
        else (project_root / binding_ref).resolve()
    )
    try:
        relative_binding = binding_path.relative_to(project_root).as_posix()
        binding_content = binding_path.read_bytes()
    except (ValueError, OSError) as exc:
        raise DesignLintError(f"cannot read design adoption binding: {exc}") from exc
    actual_digest = hashlib.sha256(binding_content).hexdigest()
    if (
        relative_binding != current.get("binding_ref")
        or normalized_digest != current.get("binding_sha256")
        or actual_digest != normalized_digest
    ):
        raise DesignLintError(
            "source spec binding does not match the current design adoption receipt"
        )
    if not _planning_ready_spec_binding(binding_content):
        raise DesignLintError(
            "formal-post-specify adoption requires the unchanged planning-ready source spec"
        )

    record = _active_design_adoption_record(
        records,
        change_id=change_id,
        scope=normalized_scope,
    )
    _, registered_digest, _, _ = _load_registered_design_change(
        project_root, change_id
    )
    if (
        registered_digest != current.get("design_change_sha256")
        or record.get("design_ref") != current.get("design_change_ref")
    ):
        raise DesignLintError(
            "current design adoption does not match the active registered design"
        )

    verified = deepcopy(current)
    verified["verified"] = True
    verified["source_spec_ref"] = relative_binding
    verified["source_spec_sha256"] = actual_digest
    return verified


def design_preview_approval_path(path: Path) -> Path:
    """Return the deterministic sidecar path for one preview round."""

    return path.with_suffix(".approval.json")


def design_preview_handoff_path(path: Path) -> Path:
    """Return the immutable implementation handoff path for one preview round."""

    return path.with_suffix(".handoff.json")


def design_preview_direction_checkpoint_path(path: Path) -> Path:
    """Return the non-consumable direction checkpoint sidecar path."""

    return path.with_suffix(".direction.json")


def _sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _canonical_json_sha256(payload: Any) -> str:
    content = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return _sha256_bytes(content)


def _locate_design_schema(name: str) -> Path:
    package_schema = Path(__file__).parent / "core_pack" / "templates" / name
    if package_schema.is_file():
        return package_schema
    return Path(__file__).parents[2] / "templates" / name


def _load_design_capability_registry() -> dict[str, Any]:
    path = _locate_design_schema("design-capability-profiles.json")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DesignLintError(
            f"cannot load design capability profiles {path}: {exc}"
        ) from exc
    if not isinstance(payload, dict) or payload.get("schema") != (
        DESIGN_CAPABILITY_PROFILES_SCHEMA
    ):
        raise DesignLintError(
            "design capability profile registry has an invalid schema"
        )
    profiles = payload.get("profiles")
    if not isinstance(profiles, list) or not profiles:
        raise DesignLintError("design capability profile registry has no profiles")
    return payload


def design_capability_profiles() -> list[dict[str, Any]]:
    """Return the deterministic project-surface profile catalog."""

    registry = _load_design_capability_registry()
    return [
        deepcopy(profile)
        for profile in registry["profiles"]
        if isinstance(profile, dict)
    ]


def parse_design_capability_profile_ids(value: str) -> list[str]:
    """Normalize a comma-separated profile selection without hiding duplicates."""

    profile_ids = [part.strip().lower() for part in value.split(",") if part.strip()]
    if not profile_ids:
        raise DesignLintError("at least one design capability profile is required")
    if len(profile_ids) != len(set(profile_ids)):
        raise DesignLintError("design capability profiles must be unique")
    return profile_ids


def _ordered_union(*collections: Any) -> list[str]:
    values: list[str] = []
    seen: set[str] = set()
    for collection in collections:
        if not isinstance(collection, list):
            continue
        for raw in collection:
            value = str(raw).strip()
            if value and value not in seen:
                values.append(value)
                seen.add(value)
    return values


def _selected_design_capability_profiles(
    profile_ids: list[str],
) -> list[dict[str, Any]]:
    registry = _load_design_capability_registry()
    profiles_by_id = {
        str(profile.get("id") or "").strip(): profile
        for profile in registry["profiles"]
        if isinstance(profile, dict)
    }
    unknown = [profile_id for profile_id in profile_ids if profile_id not in profiles_by_id]
    if unknown:
        raise DesignLintError(
            "unknown design capability profiles: "
            + ", ".join(unknown)
            + "; choose from "
            + ", ".join(profiles_by_id)
        )
    selected = [profiles_by_id[profile_id] for profile_id in profile_ids]
    nonvisual = [
        str(profile.get("id") or "")
        for profile in selected
        if profile.get("preview_required") is not True
    ]
    if nonvisual:
        if len(selected) > 1:
            raise DesignLintError(
                "no-ui cannot be combined with visual design capability profiles"
            )
        exit_contract = str(selected[0].get("exit_contract") or "").strip()
        raise DesignLintError(
            "profile no-ui has no visual design surface; " + exit_contract
        )
    return selected


def _apply_design_capability_profiles(
    manifest: dict[str, Any],
    profile_ids: list[str],
) -> None:
    """Project deterministic capability, specimen, and evidence contracts."""

    profiles = _selected_design_capability_profiles(profile_ids)
    specimens: list[dict[str, Any]] = []
    for profile in profiles:
        profile_id = str(profile["id"])
        for raw in profile.get("specimens") or []:
            specimen = deepcopy(raw)
            specimen["profile_id"] = profile_id
            specimens.append(specimen)

    capability_ids = _ordered_union(
        *(profile.get("capability_ids") for profile in profiles)
    )
    input_modes = _ordered_union(*(profile.get("input_modes") for profile in profiles))
    measurement_units = _ordered_union(
        *(profile.get("measurement_units") for profile in profiles)
    )
    manifest["capability_model"] = {
        "schema": DESIGN_CAPABILITY_MODEL_SCHEMA,
        "profile_ids": profile_ids,
        "profiles": [
            {
                "id": str(profile["id"]),
                "label": str(profile["label"]),
                "summary": str(profile["summary"]),
                "input_modes": deepcopy(profile.get("input_modes")),
                "measurement_units": deepcopy(profile.get("measurement_units")),
            }
            for profile in profiles
        ],
        "capability_ids": capability_ids,
        "input_modes": input_modes,
        "measurement_units": measurement_units,
        "specimens": specimens,
    }

    project = manifest.get("project")
    if isinstance(project, dict):
        project["platforms"] = profile_ids

    specimen_ids = [str(specimen["id"]) for specimen in specimens]
    for direction in manifest.get("directions") or []:
        if isinstance(direction, dict):
            direction["specimen_ids"] = specimen_ids

    decisions = [
        decision
        for decision in manifest.get("decisions") or []
        if isinstance(decision, dict) and str(decision.get("id") or "").strip()
    ]
    decision_ids = [str(decision.get("id") or "").strip() for decision in decisions]

    def decision_ids_for(
        contract_kind: str,
        source: dict[str, Any] | None = None,
    ) -> list[str]:
        requested = source.get("decision_kinds") if isinstance(source, dict) else None
        if not isinstance(requested, list) or not requested:
            requested = DESIGN_DECISION_KINDS_BY_CONTRACT[contract_kind]
        requested_kinds = {
            str(kind).strip() for kind in requested if str(kind).strip()
        }
        return [
            str(decision.get("id") or "").strip()
            for decision in decisions
            if str(decision.get("kind") or "").strip() in requested_kinds
        ]
    handoff = manifest.get("handoff")
    if not isinstance(handoff, dict):
        handoff = {}
        manifest["handoff"] = handoff
    handoff["reproduction_mode"] = (
        "exact" if profile_ids == ["web"] else "platform-adapted"
    )

    component_contracts: list[dict[str, Any]] = []
    professional_matrices: dict[str, list[dict[str, Any]]] = {
        field: [] for field in DESIGN_PROFESSIONAL_MATRIX_FIELDS
    }
    motion_purposes: list[str] = []
    motion_transitions: list[dict[str, Any]] = []
    reduced_motion_rules: list[str] = []
    feedback_timings: list[dict[str, int]] = []
    responsive_matrix: list[dict[str, Any]] = []
    acceptance_matrix: list[dict[str, Any]] = []
    surface_catalog: list[dict[str, Any]] = []
    scenario_matrix: list[dict[str, Any]] = []
    project_payload = manifest.get("project")
    project_source_refs = [
        str(value).strip()
        for value in (
            project_payload.get("modules")
            if isinstance(project_payload, dict)
            else []
        )
        if isinstance(value, str) and value.strip()
    ]
    for profile in profiles:
        profile_id = str(profile["id"])
        profile_specimens = [
            specimen for specimen in specimens if specimen["profile_id"] == profile_id
        ]
        profile_specimen_ids = [str(specimen["id"]) for specimen in profile_specimens]
        required_states = _ordered_union(
            *(specimen.get("required_states") for specimen in profile_specimens)
        )
        profile_component_rows: list[dict[str, Any]] = []
        profile_matrix_rows: dict[str, list[dict[str, Any]]] = {
            field: [] for field in professional_matrices
        }
        profile_motion_rows: list[dict[str, Any]] = []
        profile_responsive_rows: list[dict[str, Any]] = []
        contract = deepcopy(profile.get("component_contract"))
        if isinstance(contract, dict):
            contract["required_states"] = required_states
            contract["interaction_modes"] = deepcopy(profile.get("input_modes"))
            contract["decision_ids"] = decision_ids_for(
                "component_contracts", contract
            )
            contract.pop("decision_kinds", None)
            component_contracts.append(contract)
            profile_component_rows.append(contract)

        for field, projected_rows in professional_matrices.items():
            for raw in profile.get(field) or []:
                if not isinstance(raw, dict):
                    continue
                row = deepcopy(raw)
                row["decision_ids"] = decision_ids_for(field, raw)
                row.pop("decision_kinds", None)
                projected_rows.append(row)
                profile_matrix_rows[field].append(row)

        profile_motion = profile.get("motion_contract")
        if isinstance(profile_motion, dict):
            purpose = str(profile_motion.get("purpose") or "").strip()
            if purpose:
                motion_purposes.append(f"{profile_id}: {purpose}")
            reduced_motion = str(profile_motion.get("reduced_motion") or "").strip()
            if reduced_motion:
                reduced_motion_rules.append(f"{profile_id}: {reduced_motion}")
            for raw in profile_motion.get("transitions") or []:
                if not isinstance(raw, dict):
                    continue
                transition = deepcopy(raw)
                transition["decision_ids"] = decision_ids_for(
                    "motion_contract", raw
                )
                transition.pop("decision_kinds", None)
                motion_transitions.append(transition)
                profile_motion_rows.append(transition)
            timing = profile_motion.get("feedback_timing")
            if isinstance(timing, dict) and all(
                isinstance(timing.get(field), int)
                for field in ("immediate_ms", "progress_ms", "timeout_ms")
            ):
                feedback_timings.append(deepcopy(timing))

        for target in profile.get("targets") or []:
            if not isinstance(target, dict):
                continue
            target_id = str(target.get("id") or "").strip()
            responsive_row = {
                "id": target_id,
                "profile_id": profile_id,
                "label": str(target.get("label") or "").strip(),
                "target": deepcopy(target.get("target")),
                "review_width_px": target.get("review_width_px"),
                "state": "default",
                "adaptation": str(target.get("adaptation") or "").strip(),
                "stretch_behavior": str(
                    target.get("stretch_behavior") or ""
                ).strip(),
                "overflow_behavior": str(
                    target.get("overflow_behavior") or ""
                ).strip(),
                "decision_ids": decision_ids_for("responsive_matrix", target),
            }
            responsive_matrix.append(responsive_row)
            profile_responsive_rows.append(responsive_row)
            acceptance_matrix.append(
                {
                    "id": str(target.get("acceptance_id") or "").strip(),
                    "target_id": target_id,
                    "specimen_ids": profile_specimen_ids,
                    "states": required_states,
                    "color_modes": deepcopy(profile.get("color_modes")),
                    "motion_modes": deepcopy(profile.get("motion_modes")),
                    "decision_ids": decision_ids,
                    "must_match": [
                        "structure",
                        "geometry",
                        "tokens",
                        "content",
                        "state",
                        "motion",
                    ],
                    "evidence": [
                        "structure_snapshot",
                        "visual_capture",
                        "runtime_diagnostics",
                        "visual_comparison_or_human_review",
                    ],
                }
            )
        profile_key = re.sub(r"[^A-Z0-9]+", "-", profile_id.upper())
        surface_id = f"DH-SURFACE-{profile_key}-001"
        graph_rows = [
            *profile_component_rows,
            *(
                row
                for field in DESIGN_PROFESSIONAL_MATRIX_FIELDS
                for row in profile_matrix_rows[field]
            ),
            *profile_responsive_rows,
            *profile_motion_rows,
        ]
        surface_catalog.append(
            {
                "id": surface_id,
                "profile_id": profile_id,
                "name": str(profile.get("label") or "").strip(),
                "kind": profile_id,
                "entrypoint_id": f"EP-{profile_key}-001",
                "source_refs": deepcopy(project_source_refs),
                "specimen_ids": profile_specimen_ids,
                "component_ids": [
                    str(row.get("id") or "").strip()
                    for row in profile_component_rows
                    if str(row.get("id") or "").strip()
                ],
                "decision_ids": _ordered_union(
                    *(row.get("decision_ids") for row in graph_rows)
                ),
            }
        )
        scenario_sources = {
            "interaction_ids": profile_matrix_rows["interaction_matrix"],
            "editing_ids": profile_matrix_rows["editing_matrix"],
            "data_state_ids": profile_matrix_rows["data_state_matrix"],
            "accessibility_ids": profile_matrix_rows["accessibility_matrix"],
            "navigation_ids": profile_matrix_rows["navigation_matrix"],
            "content_ids": profile_matrix_rows["content_matrix"],
            "responsive_ids": profile_responsive_rows,
            "motion_transition_ids": profile_motion_rows,
        }
        scenario_count = max(len(rows) for rows in scenario_sources.values())
        for index in range(scenario_count):
            selected_rows = {
                field: [rows[index % len(rows)]]
                for field, rows in scenario_sources.items()
            }
            data_state = selected_rows["data_state_ids"][0]

            def state_row(name: str) -> dict[str, Any]:
                return next(
                    (
                        row
                        for row in scenario_sources["data_state_ids"]
                        if str(row.get("state") or "").strip().lower() == name
                    ),
                    data_state,
                )

            success_state = state_row("populated")
            transient_state = state_row("partial")
            unavailable_state = state_row("unavailable")
            branch_state_rows: list[dict[str, Any]] = []
            branch_state_ids: set[str] = set()
            for row in (
                data_state,
                success_state,
                transient_state,
                unavailable_state,
            ):
                row_id = str(row.get("id") or "").strip()
                if row_id and row_id not in branch_state_ids:
                    branch_state_ids.add(row_id)
                    branch_state_rows.append(row)
            selected_rows["data_state_ids"] = branch_state_rows
            scenario_text = json.dumps(
                selected_rows,
                ensure_ascii=False,
                sort_keys=True,
            ).lower()
            if any(
                marker in scenario_text
                for marker in (
                    "error",
                    "offline",
                    "permission",
                    "destructive",
                    "timeout",
                    "failure",
                    "recovery",
                )
            ):
                risk = "high"
            elif any(
                marker in scenario_text
                for marker in (
                    "keyboard",
                    "focus",
                    "loading",
                    "empty",
                    "partial",
                    "reduced",
                    "overflow",
                    "touch",
                )
            ):
                risk = "medium"
            else:
                risk = "low"
            interaction = selected_rows["interaction_ids"][0]
            accessibility = selected_rows["accessibility_ids"][0]
            navigation = selected_rows["navigation_ids"][0]
            responsive = selected_rows["responsive_ids"][0]
            focus_checkpoint = str(
                accessibility.get("focus_order") or ""
            ).strip()
            announcement_checkpoint = " ".join(
                str(item).strip()
                for item in accessibility.get("announcements") or []
                if str(item).strip()
            )
            recovery_checkpoint = str(
                navigation.get("interruption_recovery") or ""
            ).strip()
            scenario_matrix.append(
                {
                    "id": f"DH-SCENARIO-{profile_key}-{index + 1:03d}",
                    "surface_id": surface_id,
                    "name": (
                        f"{str(profile.get('label') or '').strip()}: "
                        f"{str(data_state.get('state') or '').strip()} via "
                        f"{str(interaction.get('input') or '').strip()} at "
                        f"{str(responsive.get('label') or '').strip()}"
                    ),
                    "risk": risk,
                    "required": True,
                    "interaction_script": {
                        "preconditions": [
                            (
                                f"Render {surface_id} at "
                                f"{str(responsive.get('label') or '').strip()} "
                                f"with {str(data_state.get('data_condition') or '').strip().rstrip(' .!?')}."
                            ),
                            (
                                f"Begin in the {str(data_state.get('state') or '').strip()} "
                                f"state before {str(interaction.get('trigger') or '').strip().rstrip(' .!?')}."
                            ),
                        ],
                        "start_state_id": str(
                            data_state.get("id") or ""
                        ).strip(),
                        "steps": [
                            {
                                "input": str(interaction.get("input") or "").strip(),
                                "action": str(
                                    interaction.get("trigger") or ""
                                ).strip(),
                                "expected_feedback": str(
                                    interaction.get("immediate_feedback") or ""
                                ).strip(),
                            }
                        ],
                        "branches": [
                            {
                                "conditions": ["success"],
                                "setup": (
                                    "Complete the action once without interruption: "
                                    f"{str(interaction.get('trigger') or '').strip()}"
                                ),
                                "expected_state_id": str(
                                    success_state.get("id") or ""
                                ).strip(),
                                "expected_feedback": str(
                                    success_state.get("expectation") or ""
                                ).strip(),
                                "focus_behavior": focus_checkpoint,
                                "announcement": (
                                    f"Success: {announcement_checkpoint}"
                                ),
                                "continuation": str(
                                    navigation.get("destination") or ""
                                ).strip(),
                            },
                            {
                                "conditions": ["failure", "timeout"],
                                "setup": (
                                    "Force the action to fail or exceed its timeout: "
                                    f"{str(interaction.get('trigger') or '').strip()}"
                                ),
                                "expected_state_id": str(
                                    unavailable_state.get("id") or ""
                                ).strip(),
                                "expected_feedback": str(
                                    unavailable_state.get("expectation") or ""
                                ).strip(),
                                "focus_behavior": focus_checkpoint,
                                "announcement": (
                                    f"Failure or timeout: {announcement_checkpoint}"
                                ),
                                "continuation": recovery_checkpoint,
                            },
                            {
                                "conditions": ["cancel"],
                                "setup": (
                                    "Cancel the action before completion: "
                                    f"{str(interaction.get('trigger') or '').strip()}"
                                ),
                                "expected_state_id": str(
                                    data_state.get("id") or ""
                                ).strip(),
                                "expected_feedback": str(
                                    data_state.get("expectation") or ""
                                ).strip(),
                                "focus_behavior": focus_checkpoint,
                                "announcement": (
                                    f"Cancellation: {announcement_checkpoint}"
                                ),
                                "continuation": str(
                                    navigation.get("back_behavior") or ""
                                ).strip(),
                            },
                            {
                                "conditions": [
                                    "retry",
                                    "duplicate",
                                    "out_of_order",
                                ],
                                "setup": (
                                    "Retry or repeat the action and resolve completions "
                                    "out of order: "
                                    f"{str(interaction.get('trigger') or '').strip()}"
                                ),
                                "expected_state_id": str(
                                    transient_state.get("id") or ""
                                ).strip(),
                                "expected_feedback": str(
                                    transient_state.get("expectation") or ""
                                ).strip(),
                                "focus_behavior": focus_checkpoint,
                                "announcement": (
                                    "Retry, duplicate, or out-of-order completion: "
                                    f"{announcement_checkpoint}"
                                ),
                                "continuation": recovery_checkpoint,
                            },
                        ],
                        "focus_checkpoint": focus_checkpoint,
                        "announcement_checkpoint": announcement_checkpoint,
                        "completion_checkpoint": str(
                            success_state.get("expectation") or ""
                        ).strip(),
                        "recovery_checkpoint": recovery_checkpoint,
                    },
                    **{
                        field: [str(row.get("id") or "").strip() for row in rows]
                        for field, rows in selected_rows.items()
                    },
                    "decision_ids": _ordered_union(
                        *(
                            row.get("decision_ids")
                            for rows in selected_rows.values()
                            for row in rows
                        )
                    ),
                }
            )
    handoff["component_contracts"] = component_contracts
    handoff["surface_catalog"] = surface_catalog
    handoff["scenario_matrix"] = scenario_matrix
    handoff.update(professional_matrices)
    handoff["responsive_matrix"] = responsive_matrix
    handoff["motion_contract"] = {
        "purpose": " ".join(motion_purposes),
        "transitions": motion_transitions,
        "reduced_motion": " ".join(reduced_motion_rules),
        "feedback_timing": {
            "immediate_ms": min(
                timing["immediate_ms"] for timing in feedback_timings
            ),
            "progress_ms": min(timing["progress_ms"] for timing in feedback_timings),
            "timeout_ms": max(timing["timeout_ms"] for timing in feedback_timings),
        },
    }
    risk_rank = {"low": 0, "medium": 1, "high": 2}
    risk_level = max(
        (
            str(profile.get("usability_validation", {}).get("risk_level") or "")
            for profile in profiles
            if isinstance(profile.get("usability_validation"), dict)
        ),
        key=lambda value: risk_rank.get(value, -1),
    )
    handoff["usability_validation"] = {
        "risk_level": risk_level,
        "methods": _ordered_union(
            *(
                profile.get("usability_validation", {}).get("methods")
                for profile in profiles
                if isinstance(profile.get("usability_validation"), dict)
            )
        ),
        "critical_tasks": _ordered_union(
            *(
                profile.get("usability_validation", {}).get("critical_tasks")
                for profile in profiles
                if isinstance(profile.get("usability_validation"), dict)
            )
        ),
        "success_criteria": _ordered_union(
            *(
                profile.get("usability_validation", {}).get("success_criteria")
                for profile in profiles
                if isinstance(profile.get("usability_validation"), dict)
            )
        ),
        "human_review_required": any(
            profile.get("usability_validation", {}).get("human_review_required")
            is True
            for profile in profiles
            if isinstance(profile.get("usability_validation"), dict)
        ),
    }
    smoothness_acceptance_ids = _ordered_union(
        *(
            profile.get("usability_validation", {}).get(
                "smoothness_acceptance_ids"
            )
            for profile in profiles
            if isinstance(profile.get("usability_validation"), dict)
        )
    )
    if smoothness_acceptance_ids:
        handoff["usability_validation"]["smoothness_acceptance_ids"] = (
            smoothness_acceptance_ids
        )
    budget_fields = (
        "inp_ms",
        "long_task_ms",
        "cls",
        "animation_dropped_frame_pct",
        "bundle_delta_kb",
    )
    budget_rows = [
        profile["usability_validation"]["performance_budgets"]
        for profile in profiles
        if isinstance(profile.get("usability_validation"), dict)
        and isinstance(
            profile["usability_validation"].get("performance_budgets"), dict
        )
    ]
    if budget_rows and all(
        all(
            isinstance(row.get(field), (int, float))
            and not isinstance(row.get(field), bool)
            and row.get(field, -1) >= 0
            for field in budget_fields
        )
        for row in budget_rows
    ):
        handoff["usability_validation"]["performance_budgets"] = {
            field: min(row[field] for row in budget_rows)
            for field in budget_fields
        }
    handoff["visual_acceptance_matrix"] = acceptance_matrix


def _json_schema_diagnostics(
    payload: Any,
    *,
    schema_name: str,
    code: str,
    root_path: str,
) -> list[DesignDiagnostic]:
    """Return stable field-addressed diagnostics from a bundled JSON Schema."""

    diagnostics: list[DesignDiagnostic] = []
    schema_path = _locate_design_schema(schema_name)
    try:
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError) as exc:
        return [
            DesignDiagnostic(
                code,
                f"cannot load {schema_name}: {exc}",
                str(schema_path),
            )
        ]

    errors = sorted(
        validator.iter_errors(payload),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    for error in errors:
        suffix = "".join(
            f"[{part}]" if isinstance(part, int) else f".{part}"
            for part in error.absolute_path
        )
        diagnostics.append(
            DesignDiagnostic(code, error.message, f"{root_path}{suffix}")
        )
    return diagnostics


def _parse_preview_manifest(
    parser: _DesignPreviewHTMLParser,
) -> dict[str, Any] | None:
    raw = "".join(parser.manifest_parts).strip()
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DesignLintError(
            f"embedded {DESIGN_PREVIEW_MANIFEST_ID} is not valid JSON: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise DesignLintError(
            f"embedded {DESIGN_PREVIEW_MANIFEST_ID} must be a JSON object"
        )
    return payload


def _preview_project_root(path: Path) -> Path:
    resolved = path.resolve()
    _design_preview_round_number(resolved)
    if (
        resolved.parent.name != "previews"
        or resolved.parent.parent.name == ""
        or not DESIGN_CHANGE_ID_RE.fullmatch(resolved.parent.parent.name)
        or resolved.parent.parent.parent.name != "changes"
        or resolved.parent.parent.parent.parent.name != "design"
        or resolved.parent.parent.parent.parent.parent.name != ".specify"
    ):
        raise DesignLintError(
            "design preview must be inside .specify/design/changes/<UD-ID>/previews/"
        )
    return resolved.parent.parent.parent.parent.parent.parent


def _preview_change_context(
    path: Path,
) -> tuple[Path, Path, str, dict[str, Any], str, DesignDocument]:
    resolved = path.resolve()
    project_root = _preview_project_root(resolved)
    change_id = resolved.parent.parent.name
    _index, _index_path, records = _load_design_change_index(project_root)
    record = records.get(change_id)
    if record is None:
        raise DesignLintError(f"design change {change_id} is not registered in index.json")
    if (
        str(record.get("status") or "").strip() != "draft"
        or _design_record_is_registered(record)
        or bool(str(record.get("approval_sha256") or "").strip())
    ):
        raise DesignLintError(
            f"design preview direction checkpoint requires a draft change workspace: {change_id}"
        )
    design_path = (project_root / str(record.get("design_ref") or "")).resolve()
    expected_design_ref = f".specify/design/changes/{change_id}/design-change.md"
    if str(record.get("design_ref") or "").strip() != expected_design_ref or not design_path.is_file():
        raise DesignLintError(f"design change {change_id} workspace is not canonical")
    try:
        design_bytes = design_path.read_bytes()
        document = parse_design_markdown(
            design_bytes.decode("utf-8"),
            source=str(design_path),
        )
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        raise DesignLintError(f"cannot read draft design change {change_id}: {exc}") from exc
    design_change = document.design_system
    if (
        design_change.get("schema") != DESIGN_CHANGE_SCHEMA
        or str(design_change.get("id") or "").strip() != change_id
    ):
        raise DesignLintError(
            "draft design change identity does not match its canonical workspace"
        )
    scope = design_change.get("scope")
    surfaces = scope.get("surfaces") if isinstance(scope, dict) else None
    document_scopes = (
        [str(value) for value in surfaces]
        if isinstance(surfaces, list)
        else []
    )
    record_scopes = (
        [str(value) for value in record.get("scope", [])]
        if isinstance(record.get("scope"), list)
        else []
    )
    if not document_scopes or record_scopes != document_scopes:
        raise DesignLintError("draft design change scope does not match index.json")
    for formal_path in (
        design_preview_approval_path(resolved),
        design_preview_handoff_path(resolved),
    ):
        if formal_path.exists():
            raise DesignLintError(
                "cannot direction-confirm a round that already has formal approval or handoff artifacts"
            )
    expected_preview_ref = resolved.relative_to(project_root).as_posix()
    return (
        project_root,
        design_path,
        change_id,
        record,
        expected_preview_ref,
        document,
    )


def _design_preview_round_number(path: Path) -> str:
    match = re.fullmatch(r"round-(\d+)", path.stem, re.IGNORECASE)
    if match is None:
        raise DesignLintError(
            "design direction checkpoints require a round-NN preview filename"
        )
    return str(int(match.group(1)))


def _concept_preview_manifest_diagnostics(
    manifest: dict[str, Any] | None,
    *,
    direction_ids: list[str],
    expected_primary_medium: str,
) -> list[DesignDiagnostic]:
    diagnostics: list[DesignDiagnostic] = []
    if manifest is None:
        _add_diagnostic(
            diagnostics,
            "preview-missing-manifest",
            "design preview must embed one machine-readable design-preview-manifest",
            f"script#{DESIGN_PREVIEW_MANIFEST_ID}",
        )
        return diagnostics
    if manifest.get("schema") != DESIGN_PREVIEW_MANIFEST_SCHEMA:
        _add_diagnostic(
            diagnostics,
            "preview-invalid-manifest-schema",
            f"preview manifest schema must equal {DESIGN_PREVIEW_MANIFEST_SCHEMA}",
            "manifest.schema",
        )
    diagnostics.extend(
        _visual_collaboration_diagnostics(
            manifest, expected_primary_medium=expected_primary_medium
        )
    )
    if manifest.get("configured") is not True:
        _add_diagnostic(
            diagnostics,
            "preview-manifest-not-configured",
            "concept preview manifest must set configured to true",
            "manifest.configured",
        )
    project = manifest.get("project")
    if not isinstance(project, dict):
        _add_diagnostic(
            diagnostics,
            "preview-invalid-project-context",
            "preview manifest project must be an object",
            "manifest.project",
        )
    else:
        for field in ("name", "short_name", "subject", "audience", "single_job"):
            if not isinstance(project.get(field), str) or not str(project.get(field)).strip():
                _add_diagnostic(
                    diagnostics,
                    "preview-incomplete-project-context",
                    f"concept preview manifest project.{field} must be non-empty",
                    f"manifest.project.{field}",
                )
    directions = manifest.get("directions")
    if not isinstance(directions, list) or len(directions) != 1:
        _add_diagnostic(
            diagnostics,
            "preview-manifest-direction-count",
            "preview manifest must define exactly one current concept",
            "manifest.directions",
        )
        directions = []
    manifest_direction_ids = [
        str(item.get("id") or "").strip()
        for item in directions
        if isinstance(item, dict)
    ]
    if manifest_direction_ids != direction_ids:
        _add_diagnostic(
            diagnostics,
            "preview-manifest-direction-mismatch",
            "preview manifest direction ID must match the rendered current concept",
            "manifest.directions",
        )
    for index, direction in enumerate(directions):
        if not isinstance(direction, dict):
            continue
        dials = direction.get("dials")
        if not isinstance(dials, dict) or any(
            key not in dials or not str(dials.get(key) or "").strip()
            for key in ("variance", "motion", "density", "inference_reason")
        ):
            _add_diagnostic(
                diagnostics,
                "preview-incomplete-direction",
                "concept preview direction must define dials and inference reason",
                f"manifest.directions[{index}].dials",
            )
        if not isinstance(direction.get("aesthetic_family"), str) or not str(
            direction.get("aesthetic_family") or ""
        ).strip():
            _add_diagnostic(
                diagnostics,
                "preview-incomplete-direction",
                "concept preview direction must define aesthetic_family",
                f"manifest.directions[{index}].aesthetic_family",
            )
    boundaries = manifest.get("boundaries")
    if not isinstance(boundaries, dict) or not boundaries:
        _add_diagnostic(
            diagnostics,
            "preview-invalid-boundaries",
            "concept preview manifest must define boundaries",
            "manifest.boundaries",
        )
    diagnostics.extend(_concept_capability_model_diagnostics(manifest))
    handoff = manifest.get("handoff")
    handoff = handoff if isinstance(handoff, dict) else {}
    responsive_matrix = handoff.get("responsive_matrix")
    selected_profiles = set(_design_capability_profile_ids(manifest))
    found_target = False
    if isinstance(responsive_matrix, list):
        for index, row in enumerate(responsive_matrix):
            if not isinstance(row, dict):
                continue
            target = row.get("target")
            if (
                isinstance(row.get("id"), str)
                and row.get("id").strip()
                and isinstance(row.get("profile_id"), str)
                and row.get("profile_id").strip() in selected_profiles
                and isinstance(target, dict)
                and target.get("width") is not None
                and target.get("height") is not None
                and str(target.get("unit") or "").strip()
            ):
                found_target = True
                break
    if not found_target:
        _add_diagnostic(
            diagnostics,
            "preview-missing-concept-target",
            "concept preview must define at least one selected-profile review target",
            "manifest.handoff.responsive_matrix",
        )
    review = manifest.get("review")
    if not isinstance(review, dict):
        _add_diagnostic(
            diagnostics,
            "preview-invalid-review",
            "preview manifest must define review state",
            "manifest.review",
        )
    else:
        if not str(review.get("round") or "").strip():
            _add_diagnostic(
                diagnostics,
                "preview-invalid-review",
                "preview manifest review.round must be non-empty",
                "manifest.review.round",
            )
        if str(review.get("status") or "").strip().lower() != "candidate":
            _add_diagnostic(
                diagnostics,
                "preview-manifest-candidate-mismatch",
                "concept preview manifest must record candidate status",
                "manifest.review.status",
            )
        if review.get("approved_direction") not in {None, ""}:
            _add_diagnostic(
                diagnostics,
                "preview-manifest-candidate-mismatch",
                "concept preview manifest must not record an approved direction",
                "manifest.review.approved_direction",
            )
    return diagnostics


def _concept_capability_model_diagnostics(
    manifest: dict[str, Any],
) -> list[DesignDiagnostic]:
    diagnostics: list[DesignDiagnostic] = []
    model = manifest.get("capability_model")
    if not isinstance(model, dict):
        _add_diagnostic(
            diagnostics,
            "preview-missing-capability-model",
            "preview manifest must define a platform capability model",
            "manifest.capability_model",
        )
        return diagnostics
    if model.get("schema") != DESIGN_CAPABILITY_MODEL_SCHEMA:
        _add_diagnostic(
            diagnostics,
            "preview-invalid-capability-model-schema",
            f"capability model schema must equal {DESIGN_CAPABILITY_MODEL_SCHEMA}",
            "manifest.capability_model.schema",
        )
    try:
        registry_profiles = design_capability_profiles()
    except DesignLintError as exc:
        _add_diagnostic(
            diagnostics,
            "preview-capability-registry-error",
            str(exc),
            "manifest.capability_model",
        )
        return diagnostics
    profiles_by_id = {
        str(profile.get("id") or "").strip(): profile
        for profile in registry_profiles
        if isinstance(profile, dict)
    }
    profile_ids = _design_capability_profile_ids(manifest)
    if not profile_ids:
        _add_diagnostic(
            diagnostics,
            "preview-missing-capability-profile",
            "capability model must select at least one profile",
            "manifest.capability_model.profile_ids",
        )
        return diagnostics
    if "no-ui" in profile_ids:
        _add_diagnostic(
            diagnostics,
            "preview-nonvisual-profile",
            "no-ui cannot be combined with concept preview confirmation",
            "manifest.capability_model.profile_ids",
        )
        return diagnostics
    profile_rows = model.get("profiles")
    if not isinstance(profile_rows, list):
        _add_diagnostic(
            diagnostics,
            "preview-profile-contract-mismatch",
            "capability model profiles must be a list",
            "manifest.capability_model.profiles",
        )
        return diagnostics
    rows_by_id = {
        str(profile.get("id") or "").strip(): profile
        for profile in profile_rows
        if isinstance(profile, dict) and str(profile.get("id") or "").strip()
    }
    unknown_profiles = [profile_id for profile_id in profile_ids if profile_id not in profiles_by_id]
    if unknown_profiles:
        _add_diagnostic(
            diagnostics,
            "preview-unknown-capability-profile",
            "unknown capability profiles: " + ", ".join(unknown_profiles),
            "manifest.capability_model.profile_ids",
        )
    if list(rows_by_id) != profile_ids:
        _add_diagnostic(
            diagnostics,
            "preview-profile-contract-mismatch",
            "capability profile contracts must match profile_ids in order",
            "manifest.capability_model.profiles",
        )
    declared_capabilities = {
        str(value).strip()
        for value in model.get("capability_ids") or []
        if str(value).strip()
    }
    declared_inputs = {
        str(value).strip()
        for value in model.get("input_modes") or []
        if str(value).strip()
    }
    declared_units = {
        str(value).strip()
        for value in model.get("measurement_units") or []
        if str(value).strip()
    }
    required_capabilities: set[str] = set()
    required_inputs: set[str] = set()
    required_units: set[str] = set()
    specimens = model.get("specimens")
    specimen_rows = specimens if isinstance(specimens, list) else []
    for profile_id in profile_ids:
        registry_profile = profiles_by_id.get(profile_id, {})
        required_capabilities.update(
            str(value).strip()
            for value in registry_profile.get("capability_ids") or []
            if str(value).strip()
        )
        required_inputs.update(
            str(value).strip()
            for value in registry_profile.get("input_modes") or []
            if str(value).strip()
        )
        required_units.update(
            str(value).strip()
            for value in registry_profile.get("measurement_units") or []
            if str(value).strip()
        )
        row = rows_by_id.get(profile_id)
        if not isinstance(row, dict):
            continue
        profile_specimens = [
            specimen
            for specimen in specimen_rows
            if isinstance(specimen, dict)
            and str(specimen.get("profile_id") or "").strip() == profile_id
        ]
        if not profile_specimens:
            _add_diagnostic(
                diagnostics,
                "preview-missing-profile-specimen",
                f"concept preview profile {profile_id} must define at least one specimen",
                "manifest.capability_model.specimens",
            )
        else:
            valid_specimen = False
            for specimen in profile_specimens:
                if (
                    isinstance(specimen.get("id"), str)
                    and specimen.get("id").strip()
                    and isinstance(specimen.get("required_states"), list)
                    and specimen.get("required_states")
                ):
                    valid_specimen = True
                    break
            if not valid_specimen:
                _add_diagnostic(
                    diagnostics,
                    "preview-missing-profile-specimen",
                    f"concept preview profile {profile_id} must define one reviewable specimen with required_states",
                    "manifest.capability_model.specimens",
                )
    for code, label, missing, path in (
        (
            "preview-missing-profile-capability",
            "capabilities",
            required_capabilities - declared_capabilities,
            "manifest.capability_model.capability_ids",
        ),
        (
            "preview-missing-profile-input",
            "input modes",
            required_inputs - declared_inputs,
            "manifest.capability_model.input_modes",
        ),
        (
            "preview-missing-profile-unit",
            "measurement units",
            required_units - declared_units,
            "manifest.capability_model.measurement_units",
        ),
    ):
        if missing:
            _add_diagnostic(
                diagnostics,
                code,
                f"selected profiles require {label}: " + ", ".join(sorted(missing)),
                path,
            )
    return diagnostics


def _hex_luminance(value: str) -> float | None:
    match = re.fullmatch(r"#([0-9a-fA-F]{6})", value.strip())
    if not match:
        return None
    channels = [
        int(match.group(1)[index : index + 2], 16) / 255
        for index in (0, 2, 4)
    ]
    linear = [
        channel / 12.92
        if channel <= 0.04045
        else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast_ratio(foreground: str, background: str) -> float | None:
    foreground_luminance = _hex_luminance(foreground)
    background_luminance = _hex_luminance(background)
    if foreground_luminance is None or background_luminance is None:
        return None
    lighter = max(foreground_luminance, background_luminance)
    darker = min(foreground_luminance, background_luminance)
    return (lighter + 0.05) / (darker + 0.05)


def _capability_model_diagnostics(
    manifest: dict[str, Any],
    *,
    directions: list[Any],
    ready: bool,
) -> list[DesignDiagnostic]:
    diagnostics: list[DesignDiagnostic] = []
    model = manifest.get("capability_model")
    if not isinstance(model, dict):
        _add_diagnostic(
            diagnostics,
            "preview-missing-capability-model",
            "preview manifest must define a platform capability model",
            "manifest.capability_model",
        )
        return diagnostics

    if model.get("schema") != DESIGN_CAPABILITY_MODEL_SCHEMA:
        _add_diagnostic(
            diagnostics,
            "preview-invalid-capability-model-schema",
            f"capability model schema must equal {DESIGN_CAPABILITY_MODEL_SCHEMA}",
            "manifest.capability_model.schema",
        )

    try:
        registry_profiles = design_capability_profiles()
    except DesignLintError as exc:
        _add_diagnostic(
            diagnostics,
            "preview-capability-registry-error",
            str(exc),
            "manifest.capability_model",
        )
        return diagnostics
    profiles_by_id = {
        str(profile.get("id") or "").strip(): profile
        for profile in registry_profiles
    }
    profile_ids = [
        str(profile_id).strip()
        for profile_id in model.get("profile_ids") or []
        if str(profile_id).strip()
    ]
    if not profile_ids:
        _add_diagnostic(
            diagnostics,
            "preview-missing-capability-profile",
            "capability model must select at least one profile",
            "manifest.capability_model.profile_ids",
        )
        return diagnostics
    profile_contract_ids = [
        str(profile.get("id") or "").strip()
        for profile in model.get("profiles") or []
        if isinstance(profile, dict)
    ]
    if profile_contract_ids != profile_ids:
        _add_diagnostic(
            diagnostics,
            "preview-profile-contract-mismatch",
            "capability profile contracts must match profile_ids in order",
            "manifest.capability_model.profiles",
        )
    unknown_profiles = [
        profile_id for profile_id in profile_ids if profile_id not in profiles_by_id
    ]
    if unknown_profiles:
        _add_diagnostic(
            diagnostics,
            "preview-unknown-capability-profile",
            "unknown capability profiles: " + ", ".join(unknown_profiles),
            "manifest.capability_model.profile_ids",
        )
    if "no-ui" in profile_ids:
        message = (
            "no-ui cannot be combined with visual profiles"
            if len(profile_ids) > 1
            else (
                "no-ui work must record design_system_status not-applicable with "
                "current evidence and skip preview, approval, handoff, ui-target, "
                "and visual comparison"
            )
        )
        _add_diagnostic(
            diagnostics,
            "preview-nonvisual-profile",
            message,
            "manifest.capability_model.profile_ids",
        )
        return diagnostics
    selected_profiles = [
        profiles_by_id[profile_id]
        for profile_id in profile_ids
        if profile_id in profiles_by_id
    ]

    declared_capabilities = {
        str(value).strip()
        for value in model.get("capability_ids") or []
        if str(value).strip()
    }
    declared_inputs = {
        str(value).strip()
        for value in model.get("input_modes") or []
        if str(value).strip()
    }
    declared_units = {
        str(value).strip()
        for value in model.get("measurement_units") or []
        if str(value).strip()
    }
    required_capabilities = {
        str(value).strip()
        for profile in selected_profiles
        for value in profile.get("capability_ids") or []
        if str(value).strip()
    }
    required_inputs = {
        str(value).strip()
        for profile in selected_profiles
        for value in profile.get("input_modes") or []
        if str(value).strip()
    }
    required_units = {
        str(value).strip()
        for profile in selected_profiles
        for value in profile.get("measurement_units") or []
        if str(value).strip()
    }
    for code, label, missing, path in (
        (
            "preview-missing-profile-capability",
            "capabilities",
            required_capabilities - declared_capabilities,
            "manifest.capability_model.capability_ids",
        ),
        (
            "preview-missing-profile-input",
            "input modes",
            required_inputs - declared_inputs,
            "manifest.capability_model.input_modes",
        ),
        (
            "preview-missing-profile-unit",
            "measurement units",
            required_units - declared_units,
            "manifest.capability_model.measurement_units",
        ),
    ):
        if missing:
            _add_diagnostic(
                diagnostics,
                code,
                f"selected profiles require {label}: " + ", ".join(sorted(missing)),
                path,
            )

    content = manifest.get("content")
    content = content if isinstance(content, dict) else {}
    specimens = model.get("specimens")
    if not isinstance(specimens, list) or not specimens:
        _add_diagnostic(
            diagnostics,
            "preview-missing-capability-specimens",
            "visual capability profiles require concrete specimens",
            "manifest.capability_model.specimens",
        )
        return diagnostics
    specimen_ids: list[str] = []
    specimen_capabilities: set[str] = set()
    specimen_ids_by_profile: dict[str, list[str]] = {
        profile_id: [] for profile_id in profile_ids
    }
    specimen_kinds_by_profile: dict[str, set[str]] = {
        profile_id: set() for profile_id in profile_ids
    }
    for index, specimen in enumerate(specimens):
        if not isinstance(specimen, dict):
            continue
        specimen_id = str(specimen.get("id") or "").strip()
        specimen_ids.append(specimen_id)
        if not DESIGN_SPECIMEN_ID_RE.fullmatch(specimen_id):
            _add_diagnostic(
                diagnostics,
                "preview-invalid-specimen-id",
                "specimen IDs must use the stable SP-<PROFILE>-<KIND>-<NUMBER> form",
                f"manifest.capability_model.specimens[{index}].id",
            )
        profile_id = str(specimen.get("profile_id") or "").strip()
        if profile_id not in profile_ids:
            _add_diagnostic(
                diagnostics,
                "preview-specimen-profile-mismatch",
                "specimen profile_id must reference a selected capability profile",
                f"manifest.capability_model.specimens[{index}].profile_id",
            )
        else:
            specimen_ids_by_profile[profile_id].append(specimen_id)
            specimen_kinds_by_profile[profile_id].add(
                str(specimen.get("kind") or "").strip()
            )
        capabilities = {
            str(value).strip()
            for value in specimen.get("capability_ids") or []
            if str(value).strip()
        }
        specimen_capabilities.update(capabilities)
        unknown_capabilities = capabilities - declared_capabilities
        if unknown_capabilities:
            _add_diagnostic(
                diagnostics,
                "preview-unknown-specimen-capability",
                "specimen references undeclared capabilities: "
                + ", ".join(sorted(unknown_capabilities)),
                f"manifest.capability_model.specimens[{index}].capability_ids",
            )
        if ready:
            missing_content = [
                str(key).strip()
                for key in specimen.get("content_keys") or []
                if not isinstance(content.get(str(key).strip()), str)
                or not str(content.get(str(key).strip()) or "").strip()
            ]
            if missing_content:
                _add_diagnostic(
                    diagnostics,
                    "preview-missing-specimen-content",
                    "ready specimen requires representative content keys: "
                    + ", ".join(missing_content),
                    f"manifest.capability_model.specimens[{index}].content_keys",
                )
    if len(specimen_ids) != len(set(specimen_ids)):
        _add_diagnostic(
            diagnostics,
            "preview-duplicate-specimen-id",
            "capability specimen IDs must be unique",
            "manifest.capability_model.specimens",
        )
    uncovered_capabilities = declared_capabilities - specimen_capabilities
    if uncovered_capabilities:
        _add_diagnostic(
            diagnostics,
            "preview-uncovered-capability",
            "every declared capability must be demonstrated by a specimen: "
            + ", ".join(sorted(uncovered_capabilities)),
            "manifest.capability_model.specimens",
        )
    for profile in selected_profiles:
        profile_id = str(profile.get("id") or "")
        required_kinds = {
            str(specimen.get("kind") or "").strip()
            for specimen in profile.get("specimens") or []
            if isinstance(specimen, dict)
        }
        missing_kinds = required_kinds - specimen_kinds_by_profile.get(
            profile_id, set()
        )
        if missing_kinds:
            _add_diagnostic(
                diagnostics,
                "preview-missing-profile-specimen",
                f"profile {profile_id} requires specimen kinds: "
                + ", ".join(sorted(missing_kinds)),
                "manifest.capability_model.specimens",
            )

    for index, direction in enumerate(directions):
        if not isinstance(direction, dict):
            continue
        direction_specimens = direction.get("specimen_ids")
        if direction_specimens != specimen_ids:
            _add_diagnostic(
                diagnostics,
                "preview-direction-specimen-mismatch",
                "all directions must cover the same ordered capability specimens",
                f"manifest.directions[{index}].specimen_ids",
            )

    handoff = manifest.get("handoff")
    handoff = handoff if isinstance(handoff, dict) else {}
    targets = handoff.get("responsive_matrix")
    acceptance = handoff.get("visual_acceptance_matrix")
    target_profiles: dict[str, str] = {}
    covered_target_profiles: set[str] = set()
    for index, target in enumerate(targets or []):
        if not isinstance(target, dict):
            continue
        target_id = str(target.get("id") or "").strip()
        profile_id = str(target.get("profile_id") or "").strip()
        target_profiles[target_id] = profile_id
        if profile_id not in profile_ids:
            _add_diagnostic(
                diagnostics,
                "preview-target-profile-mismatch",
                "presentation target profile_id must reference a selected profile",
                f"manifest.handoff.responsive_matrix[{index}].profile_id",
            )
        else:
            covered_target_profiles.add(profile_id)
    missing_target_profiles = set(profile_ids) - covered_target_profiles
    if missing_target_profiles:
        _add_diagnostic(
            diagnostics,
            "preview-missing-profile-target",
            "every selected profile requires a presentation target: "
            + ", ".join(sorted(missing_target_profiles)),
            "manifest.handoff.responsive_matrix",
        )

    accepted_specimens: set[str] = set()
    for index, row in enumerate(acceptance or []):
        if not isinstance(row, dict):
            continue
        target_id = str(row.get("target_id") or "").strip()
        profile_id = target_profiles.get(target_id, "")
        expected_specimens = specimen_ids_by_profile.get(profile_id, [])
        actual_specimens = row.get("specimen_ids")
        if actual_specimens != expected_specimens:
            _add_diagnostic(
                diagnostics,
                "preview-acceptance-specimen-mismatch",
                "visual acceptance row must exactly bind its profile specimens",
                f"manifest.handoff.visual_acceptance_matrix[{index}].specimen_ids",
            )
        if isinstance(actual_specimens, list):
            accepted_specimens.update(str(value).strip() for value in actual_specimens)
    missing_accepted_specimens = set(specimen_ids) - accepted_specimens
    if missing_accepted_specimens:
        _add_diagnostic(
            diagnostics,
            "preview-incomplete-specimen-acceptance",
            "visual acceptance must cover every capability specimen: "
            + ", ".join(sorted(missing_accepted_specimens)),
            "manifest.handoff.visual_acceptance_matrix",
        )
    return diagnostics


# Ready-level taste gates: min pairwise axis changes and Manhattan distance.
_DIAL_MIN_CHANGED_AXES = 2
_DIAL_MIN_MANHATTAN_DISTANCE = 4
_SCAFFOLD_TASTE_REASON_PREFIXES = (
    "scaffold baseline:",
    "scaffold default:",
    "template baseline:",
)


def _direction_dial_vector(dials: dict[str, Any]) -> tuple[int, int, int] | None:
    """Return a normalized variance/motion/density triple when all axes are valid."""

    values: list[int] = []
    for key in ("variance", "motion", "density"):
        raw = dials.get(key)
        if isinstance(raw, bool) or not isinstance(raw, int) or not 1 <= raw <= 10:
            return None
        values.append(raw)
    return values[0], values[1], values[2]


def _dial_manhattan_distance(
    left: tuple[int, int, int],
    right: tuple[int, int, int],
) -> int:
    return sum(abs(a - b) for a, b in zip(left, right, strict=True))


def _dial_changed_axes(
    left: tuple[int, int, int],
    right: tuple[int, int, int],
) -> int:
    return sum(a != b for a, b in zip(left, right, strict=True))


def _normalize_signature_for_divergence(value: str) -> str:
    """Collapse whitespace and trailing punctuation so near-duplicates collide."""

    normalized = re.sub(r"\s+", " ", value.strip().casefold())
    return re.sub(r"[\W_]+$", "", normalized)


def _is_scaffold_taste_reason(reason: str) -> bool:
    lowered = reason.strip().casefold()
    return any(lowered.startswith(prefix) for prefix in _SCAFFOLD_TASTE_REASON_PREFIXES)


_VISUAL_FINGERPRINT_RULE_CACHE: dict[str, Any] | None = None
_DIAGNOSTIC_CONTRACT_CACHE: dict[str, Any] | None = None
_DEFAULT_FINGERPRINT_DIMENSIONS = (
    "typography",
    "geometry",
    "density",
    "elevation",
    "motion",
    "modes",
)


def _load_visual_fingerprint_rule() -> dict[str, Any]:
    """Load the versioned visual fingerprint rule (v1 dimensions + version)."""

    global _VISUAL_FINGERPRINT_RULE_CACHE
    if _VISUAL_FINGERPRINT_RULE_CACHE is not None:
        return _VISUAL_FINGERPRINT_RULE_CACHE
    path = _locate_design_schema("visual-fingerprint-rule.json")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError):
        payload = {
            "schema": "spec-kit-visual-fingerprint-rule-v1",
            "version": "1",
            "dimensions": list(_DEFAULT_FINGERPRINT_DIMENSIONS),
        }
    if not isinstance(payload, dict):
        payload = {
            "version": "1",
            "dimensions": list(_DEFAULT_FINGERPRINT_DIMENSIONS),
        }
    version = str(payload.get("version") or "1").strip() or "1"
    dimensions = payload.get("dimensions")
    if not isinstance(dimensions, list) or not dimensions:
        dimensions = list(_DEFAULT_FINGERPRINT_DIMENSIONS)
    else:
        dimensions = [str(item).strip() for item in dimensions if str(item).strip()]
    rule = {
        "schema": str(payload.get("schema") or "spec-kit-visual-fingerprint-rule-v1"),
        "version": version,
        "dimensions": dimensions,
    }
    _VISUAL_FINGERPRINT_RULE_CACHE = rule
    return rule


def _load_design_diagnostic_contract() -> dict[str, Any]:
    """Load diagnostic recovery contract for agent-facing lint enrichment."""

    global _DIAGNOSTIC_CONTRACT_CACHE
    if _DIAGNOSTIC_CONTRACT_CACHE is not None:
        return _DIAGNOSTIC_CONTRACT_CACHE
    path = _locate_design_schema("design-diagnostic-contract.json")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError):
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    _DIAGNOSTIC_CONTRACT_CACHE = payload
    return payload


def _normalize_fingerprint_value(value: Any) -> Any:
    """Recursively normalize values for stable fingerprint hashing."""

    if isinstance(value, dict):
        return {
            str(key): _normalize_fingerprint_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, list):
        return [_normalize_fingerprint_value(item) for item in value]
    if isinstance(value, str):
        return re.sub(r"\s+", " ", value.strip())
    return value


def _direction_visual_fingerprint(direction: dict[str, Any]) -> dict[str, Any]:
    """Return a versioned visual fingerprint for one direction.

    Fingerprints are comparable only when version and dimensions match.
    """

    rule = _load_visual_fingerprint_rule()
    dimensions = list(rule["dimensions"])
    payload = {
        dimension: _normalize_fingerprint_value(direction.get(dimension))
        for dimension in dimensions
    }
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    digest = hashlib.sha256(encoded.encode("utf-8")).hexdigest()
    return {
        "version": str(rule["version"]),
        "dimensions": dimensions,
        "hash": digest,
    }


def _visual_fingerprints_comparable(
    left: dict[str, Any],
    right: dict[str, Any],
) -> bool:
    return (
        str(left.get("version") or "") == str(right.get("version") or "")
        and list(left.get("dimensions") or []) == list(right.get("dimensions") or [])
    )


def _enrich_design_diagnostic(diagnostic: DesignDiagnostic) -> DesignDiagnostic:
    """Attach layer/recovery/agent_action from the diagnostic contract."""

    contract = _load_design_diagnostic_contract()
    codes = contract.get("codes") if isinstance(contract.get("codes"), dict) else {}
    default = contract.get("default") if isinstance(contract.get("default"), dict) else {}
    entry = codes.get(diagnostic.code) if isinstance(codes, dict) else None
    if not isinstance(entry, dict):
        entry = default

    layer = entry.get("layer") if isinstance(entry, dict) else None
    if not isinstance(layer, str) or not layer.strip():
        layer = str(default.get("layer") or "structural")
    severity = entry.get("severity") if isinstance(entry, dict) else None
    if not isinstance(severity, str) or not severity.strip():
        severity = diagnostic.level or str(default.get("severity") or "error")
    why = entry.get("why") if isinstance(entry, dict) else None
    if not isinstance(why, str) or not why.strip():
        why = default.get("why") if isinstance(default.get("why"), str) else None
    recovery_raw = (
        entry.get("recovery")
        if isinstance(entry, dict) and isinstance(entry.get("recovery"), list)
        else default.get("recovery")
    )
    actions_raw = (
        entry.get("agent_action")
        if isinstance(entry, dict) and isinstance(entry.get("agent_action"), list)
        else default.get("agent_action")
    )
    recovery = tuple(
        str(item).strip()
        for item in (recovery_raw or ())
        if str(item).strip()
    )
    agent_action = tuple(
        str(item).strip()
        for item in (actions_raw or ())
        if str(item).strip()
    )
    return DesignDiagnostic(
        code=diagnostic.code,
        message=diagnostic.message,
        path=diagnostic.path,
        level=severity,
        layer=layer.strip(),
        recovery=recovery,
        agent_action=agent_action,
        why=why.strip() if isinstance(why, str) and why.strip() else None,
    )


def enrich_design_diagnostics(
    diagnostics: list[DesignDiagnostic],
) -> list[DesignDiagnostic]:
    """Public helper: enrich diagnostics with recovery contract fields."""

    return [_enrich_design_diagnostic(item) for item in diagnostics]


def _direction_divergence_diagnostics(
    directions: list[Any],
) -> list[DesignDiagnostic]:
    """Validate concept taste fields and legacy multi-direction divergence."""

    diagnostics: list[DesignDiagnostic] = []
    dial_vectors: list[tuple[int, int, int]] = []
    signatures: list[str] = []
    visual_fingerprints: list[dict[str, Any]] = []

    for index, direction in enumerate(directions):
        if not isinstance(direction, dict):
            continue
        direction_id = str(direction.get("id") or "").strip() or f"direction-{index + 1}"
        dials = direction.get("dials")
        if not isinstance(dials, dict):
            _add_diagnostic(
                diagnostics,
                "preview-missing-direction-dials",
                f"ready direction {direction_id} must define dials.variance/motion/density",
                f"manifest.directions[{index}].dials",
            )
            continue
        vector = _direction_dial_vector(dials)
        if vector is None:
            _add_diagnostic(
                diagnostics,
                "preview-invalid-direction-dials",
                (
                    f"ready direction {direction_id} dials must be integers 1-10 "
                    "for variance, motion, and density"
                ),
                f"manifest.directions[{index}].dials",
            )
        else:
            dial_vectors.append(vector)
            reason = dials.get("inference_reason")
            if not isinstance(reason, str) or not reason.strip():
                _add_diagnostic(
                    diagnostics,
                    "preview-missing-dial-inference",
                    f"ready direction {direction_id} must explain dial inference_reason",
                    f"manifest.directions[{index}].dials.inference_reason",
                )
            elif DESIGN_PREVIEW_PLACEHOLDER_RE.search(reason):
                _add_diagnostic(
                    diagnostics,
                    "preview-unresolved-dial-inference",
                    (
                        f"ready direction {direction_id} inference_reason must replace "
                        "scaffold placeholders with project-specific reasoning"
                    ),
                    f"manifest.directions[{index}].dials.inference_reason",
                )
            elif _is_scaffold_taste_reason(reason):
                _add_diagnostic(
                    diagnostics,
                    "preview-scaffold-taste-reason",
                    (
                        f"ready direction {direction_id} inference_reason still uses "
                        "scaffold baseline wording; replace with project intake"
                    ),
                    f"manifest.directions[{index}].dials.inference_reason",
                )

        family = direction.get("aesthetic_family")
        if not isinstance(family, str) or not family.strip():
            _add_diagnostic(
                diagnostics,
                "preview-missing-aesthetic-family",
                f"ready direction {direction_id} must define aesthetic_family",
                f"manifest.directions[{index}].aesthetic_family",
            )
        elif DESIGN_PREVIEW_PLACEHOLDER_RE.search(family):
            _add_diagnostic(
                diagnostics,
                "preview-unresolved-aesthetic-family",
                (
                    f"ready direction {direction_id} aesthetic_family must replace "
                    "scaffold placeholders with a project-selected family"
                ),
                f"manifest.directions[{index}].aesthetic_family",
            )

        signature = _normalize_signature_for_divergence(
            str(direction.get("signature_element") or "")
        )
        if signature:
            signatures.append(signature)

        visual_fingerprints.append(_direction_visual_fingerprint(direction))

    if len(dial_vectors) == 3:
        if len(set(dial_vectors)) < 3:
            _add_diagnostic(
                diagnostics,
                "preview-undifferentiated-direction-dials",
                (
                    "ready directions must diverge on dial vectors "
                    "(variance, motion, density); identical triples are not comparable options"
                ),
                "manifest.directions",
            )
        else:
            for left_index, right_index in combinations(range(3), 2):
                left = dial_vectors[left_index]
                right = dial_vectors[right_index]
                changed = _dial_changed_axes(left, right)
                distance = _dial_manhattan_distance(left, right)
                if (
                    changed < _DIAL_MIN_CHANGED_AXES
                    or distance < _DIAL_MIN_MANHATTAN_DISTANCE
                ):
                    _add_diagnostic(
                        diagnostics,
                        "preview-insufficient-direction-divergence",
                        (
                            "ready directions must differ on at least "
                            f"{_DIAL_MIN_CHANGED_AXES} dial axes and have Manhattan "
                            f"distance >= {_DIAL_MIN_MANHATTAN_DISTANCE}; "
                            f"directions[{left_index}]={left} and "
                            f"directions[{right_index}]={right} only change "
                            f"{changed} axis/axes with distance {distance}"
                        ),
                        "manifest.directions",
                    )
                    break

    if len(signatures) == 3 and len(set(signatures)) < 3:
        _add_diagnostic(
            diagnostics,
            "preview-undifferentiated-direction-signatures",
            (
                "ready directions must each declare a unique signature_element "
                "so the user can tell them apart (ignoring case, spacing, and "
                "trailing punctuation)"
            ),
            "manifest.directions",
        )

    if len(visual_fingerprints) == 3:
        comparable = all(
            _visual_fingerprints_comparable(visual_fingerprints[0], item)
            for item in visual_fingerprints[1:]
        )
        if comparable:
            hashes = [str(item.get("hash") or "") for item in visual_fingerprints]
            if len(set(hashes)) < 3:
                rule = _load_visual_fingerprint_rule()
                _add_diagnostic(
                    diagnostics,
                    "preview-undifferentiated-direction-visuals",
                    (
                        "ready directions must differ in render-driving visual systems "
                        f"(fingerprint rule v{rule['version']}: "
                        + ", ".join(rule["dimensions"])
                        + "); distinct dials/signatures alone are not enough when "
                        "visual payloads match"
                    ),
                    "manifest.directions",
                )

    return diagnostics


def _visual_collaboration_diagnostics(
    manifest: dict[str, Any],
    *,
    expected_primary_medium: str | None,
) -> list[DesignDiagnostic]:
    diagnostics: list[DesignDiagnostic] = []
    collaboration = manifest.get("visual_collaboration")
    if not isinstance(collaboration, dict):
        _add_diagnostic(
            diagnostics,
            "preview-invalid-visual-collaboration",
            "preview manifest must freeze the live visual capability route",
            "manifest.visual_collaboration",
        )
        return diagnostics

    primary_medium = str(collaboration.get("primary_medium") or "").strip()
    image_generation = str(collaboration.get("image_generation") or "").strip()
    image_inspection = str(collaboration.get("image_inspection") or "").strip()
    image_editing = str(collaboration.get("image_editing") or "").strip()
    inspection_owner = str(collaboration.get("inspection_owner") or "").strip()
    prompt_strategy = str(collaboration.get("prompt_strategy") or "").strip()
    expected_owner = (
        "agent-and-user" if image_inspection == "available" else "user"
    )
    valid_route = (
        image_inspection in DESIGN_IMAGE_CAPABILITY_VALUES
        and image_editing in DESIGN_IMAGE_CAPABILITY_VALUES
        and inspection_owner == expected_owner
        and (
            (
                primary_medium == "image-primary"
                and image_generation == "available"
                and prompt_strategy == "image-generation"
            )
            or (
                primary_medium == "html-primary"
                and image_generation == "unavailable"
                and prompt_strategy == "html-authoring"
            )
        )
    )
    if expected_primary_medium and primary_medium != expected_primary_medium:
        valid_route = False
    if not valid_route:
        _add_diagnostic(
            diagnostics,
            "preview-invalid-visual-collaboration",
            (
                "visual_collaboration must truthfully bind the selected medium, "
                "independent image capabilities, prompt strategy, and inspection owner"
            ),
            "manifest.visual_collaboration",
        )
    return diagnostics


def _preview_manifest_diagnostics(
    manifest: dict[str, Any] | None,
    *,
    direction_ids: list[str],
    ready: bool,
    expected_primary_medium: str | None = None,
) -> list[DesignDiagnostic]:
    diagnostics: list[DesignDiagnostic] = []
    if manifest is None:
        _add_diagnostic(
            diagnostics,
            "preview-missing-manifest",
            "design preview must embed one machine-readable design-preview-manifest",
            f"script#{DESIGN_PREVIEW_MANIFEST_ID}",
        )
        return diagnostics

    if manifest.get("schema") != DESIGN_PREVIEW_MANIFEST_SCHEMA:
        _add_diagnostic(
            diagnostics,
            "preview-invalid-manifest-schema",
            f"preview manifest schema must equal {DESIGN_PREVIEW_MANIFEST_SCHEMA}",
            "manifest.schema",
        )
    diagnostics.extend(
        _json_schema_diagnostics(
            manifest,
            schema_name="design-preview-manifest.schema.json",
            code="preview-manifest-schema-error",
            root_path="manifest",
        )
    )
    diagnostics.extend(
        _visual_collaboration_diagnostics(
            manifest,
            expected_primary_medium=expected_primary_medium,
        )
    )

    configured = manifest.get("configured")
    if ready and configured is not True:
        _add_diagnostic(
            diagnostics,
            "preview-manifest-not-configured",
            "ready preview manifest must set configured to true",
            "manifest.configured",
        )

    project = manifest.get("project")
    if not isinstance(project, dict):
        _add_diagnostic(
            diagnostics,
            "preview-invalid-project-context",
            "preview manifest project must be an object",
            "manifest.project",
        )
    elif ready:
        for field in ("name", "short_name", "subject", "audience", "single_job"):
            value = project.get(field)
            if not isinstance(value, str) or not value.strip():
                _add_diagnostic(
                    diagnostics,
                    "preview-incomplete-project-context",
                    f"ready preview manifest project.{field} must be non-empty",
                    f"manifest.project.{field}",
                )

    directions = manifest.get("directions")
    if not isinstance(directions, list) or len(directions) != 1:
        _add_diagnostic(
            diagnostics,
            "preview-manifest-direction-count",
            "preview manifest must define exactly one current concept",
            "manifest.directions",
        )
        directions = []
    manifest_direction_ids = [
        str(item.get("id") or "").strip()
        for item in directions
        if isinstance(item, dict)
    ]
    if manifest_direction_ids != direction_ids:
        _add_diagnostic(
            diagnostics,
            "preview-manifest-direction-mismatch",
            "preview manifest direction ID must match the rendered current concept",
            "manifest.directions",
        )

    required_motion = {
        "duration_fast",
        "duration_base",
        "duration_slow",
        "easing_standard",
        "easing_emphasized",
        "distance_enter",
        "reduced_motion",
    }
    required_palette = {
        "canvas",
        "canvas_deep",
        "surface",
        "surface_raised",
        "ink",
        "ink_muted",
        "line",
        "accent",
        "accent_ink",
        "support",
        "warning",
        "danger",
    }
    for index, direction in enumerate(directions):
        if not isinstance(direction, dict):
            _add_diagnostic(
                diagnostics,
                "preview-invalid-direction",
                "each preview manifest direction must be an object",
                f"manifest.directions[{index}]",
            )
            continue
        direction_id = str(direction.get("id") or "").strip()
        if not DESIGN_PREVIEW_DIRECTION_RE.fullmatch(direction_id):
            _add_diagnostic(
                diagnostics,
                "preview-invalid-direction-id",
                "direction IDs must use the direction-<slug> form",
                f"manifest.directions[{index}].id",
            )
        if ready:
            for field in (
                "name",
                "visual_thesis",
                "content_thesis",
                "interaction_thesis",
                "signature_element",
                "gain",
                "cost",
            ):
                value = direction.get(field)
                if not isinstance(value, str) or not value.strip():
                    _add_diagnostic(
                        diagnostics,
                        "preview-incomplete-direction",
                        f"ready direction {direction_id or index + 1} must define {field}",
                        f"manifest.directions[{index}].{field}",
                    )

        motion = direction.get("motion")
        if not isinstance(motion, dict) or not required_motion <= set(motion):
            _add_diagnostic(
                diagnostics,
                "preview-incomplete-motion-system",
                f"direction {direction_id or index + 1} must define a complete motion system",
                f"manifest.directions[{index}].motion",
            )

        density = direction.get("density")
        density_scale = density.get("scale") if isinstance(density, dict) else None
        if (
            not isinstance(density, dict)
            or not str(density.get("space_unit") or "").strip()
            or not str(density.get("label") or "").strip()
            or isinstance(density_scale, bool)
            or not isinstance(density_scale, (int, float))
            or density_scale <= 0
        ):
            _add_diagnostic(
                diagnostics,
                "preview-invalid-density-system",
                (
                    f"direction {direction_id or index + 1} must define density "
                    "space_unit, label, and a positive numeric scale"
                ),
                f"manifest.directions[{index}].density",
            )

        modes = direction.get("modes")
        if not isinstance(modes, dict):
            _add_diagnostic(
                diagnostics,
                "preview-missing-color-modes",
                f"direction {direction_id or index + 1} must define color modes",
                f"manifest.directions[{index}].modes",
            )
            continue
        for mode_name in ("light", "dark", "high-contrast"):
            palette = modes.get(mode_name)
            if not isinstance(palette, dict) or not required_palette <= set(palette):
                _add_diagnostic(
                    diagnostics,
                    "preview-incomplete-color-mode",
                    f"direction {direction_id or index + 1} must define a complete {mode_name} palette",
                    f"manifest.directions[{index}].modes.{mode_name}",
                )
                continue
            if not ready:
                continue
            for foreground_key, background_key, label in (
                ("ink", "canvas", "primary text"),
                ("ink_muted", "canvas", "secondary text"),
                ("accent_ink", "accent", "primary action"),
            ):
                ratio = _contrast_ratio(
                    str(palette.get(foreground_key) or ""),
                    str(palette.get(background_key) or ""),
                )
                if ratio is None or ratio < 4.5:
                    ratio_text = "invalid colors" if ratio is None else f"{ratio:.2f}:1"
                    _add_diagnostic(
                        diagnostics,
                        "preview-insufficient-contrast",
                        (
                            f"{direction_id} {mode_name} {label} contrast must be "
                            f"at least 4.5:1; found {ratio_text}"
                        ),
                        (
                            f"manifest.directions[{index}].modes."
                            f"{mode_name}.{foreground_key}"
                        ),
                    )

    if ready and isinstance(directions, list) and len(directions) == 1:
        diagnostics.extend(_direction_divergence_diagnostics(directions))

    diagnostics.extend(
        _capability_model_diagnostics(
            manifest,
            directions=directions,
            ready=ready,
        )
    )

    review = manifest.get("review")
    if not isinstance(review, dict):
        _add_diagnostic(
            diagnostics,
            "preview-invalid-review-metadata",
            "preview manifest review must be an object",
            "manifest.review",
        )
    content = manifest.get("content")
    if not isinstance(content, dict):
        _add_diagnostic(
            diagnostics,
            "preview-invalid-content-fixture",
            "preview manifest content must be an object",
            "manifest.content",
        )
    elif ready and any(
        not isinstance(value, str) or not value.strip() for value in content.values()
    ):
        _add_diagnostic(
            diagnostics,
            "preview-incomplete-content-fixture",
            "ready preview content values must all be non-empty representative content",
            "manifest.content",
        )

    boundaries = manifest.get("boundaries")
    if not isinstance(boundaries, dict):
        _add_diagnostic(
            diagnostics,
            "preview-invalid-boundaries",
            "preview manifest boundaries must be an object",
            "manifest.boundaries",
        )
    else:
        for field in ("must_preserve", "may_adapt", "must_not"):
            values = boundaries.get(field)
            if not isinstance(values, list) or not values or not all(
                isinstance(item, str) and item.strip() for item in values
            ):
                _add_diagnostic(
                    diagnostics,
                    "preview-incomplete-boundaries",
                    f"preview manifest boundaries.{field} must be a non-empty string list",
                    f"manifest.boundaries.{field}",
                )

    decisions = manifest.get("decisions")
    if not isinstance(decisions, list) or not decisions:
        _add_diagnostic(
            diagnostics,
            "preview-missing-decisions",
            "preview manifest must define stable design decisions",
            "manifest.decisions",
        )
        decisions = []
    decision_ids: list[str] = []
    for index, decision in enumerate(decisions):
        if not isinstance(decision, dict):
            _add_diagnostic(
                diagnostics,
                "preview-invalid-decision",
                "each design decision must be an object",
                f"manifest.decisions[{index}]",
            )
            continue
        decision_id = str(decision.get("id") or "").strip()
        decision_ids.append(decision_id)
        if "{{" not in decision_id and not re.fullmatch(
            r"DS-[A-Z0-9]+(?:-[A-Z0-9]+)+",
            decision_id,
        ):
            _add_diagnostic(
                diagnostics,
                "preview-invalid-decision-id",
                "design decision IDs must use a stable DS-<KIND>-<NUMBER> form",
                f"manifest.decisions[{index}].id",
            )
        for field in ("kind", "title", "statement", "source_ref", "verification"):
            if not str(decision.get(field) or "").strip():
                _add_diagnostic(
                    diagnostics,
                    "preview-incomplete-decision",
                    f"design decision {decision_id or index + 1} must define {field}",
                    f"manifest.decisions[{index}].{field}",
                )
        affected_surfaces = decision.get("affected_surfaces")
        if not isinstance(affected_surfaces, list) or not affected_surfaces or any(
            not isinstance(item, str) or not item.strip()
            for item in affected_surfaces
        ):
            _add_diagnostic(
                diagnostics,
                "preview-incomplete-decision",
                f"design decision {decision_id or index + 1} must define affected_surfaces",
                f"manifest.decisions[{index}].affected_surfaces",
            )
    if len(set(decision_ids)) != len(decision_ids):
        _add_diagnostic(
            diagnostics,
            "preview-duplicate-decision-id",
            "design decision IDs must be unique",
            "manifest.decisions",
        )

    token_map = manifest.get("token_map")
    mapped_decision_ids: set[str] = set()
    if not isinstance(token_map, list) or not token_map:
        _add_diagnostic(
            diagnostics,
            "preview-missing-token-map",
            "preview manifest must map design decisions to implementation owners",
            "manifest.token_map",
        )
    else:
        for index, entry in enumerate(token_map):
            if not isinstance(entry, dict):
                _add_diagnostic(
                    diagnostics,
                    "preview-invalid-token-map",
                    "token map entries must be objects",
                    f"manifest.token_map[{index}]",
                )
                continue
            mapped_decision_id = str(entry.get("decision_id") or "").strip()
            if mapped_decision_id not in decision_ids:
                _add_diagnostic(
                    diagnostics,
                    "preview-unknown-token-map-decision",
                    "token map decision_id must reference manifest.decisions",
                    f"manifest.token_map[{index}].decision_id",
                )
            else:
                mapped_decision_ids.add(mapped_decision_id)
            binding_id = str(entry.get("id") or "").strip()
            if not DESIGN_HANDOFF_ID_RE.fullmatch(binding_id):
                _add_diagnostic(
                    diagnostics,
                    "preview-invalid-handoff-id",
                    "implementation binding IDs must use a stable DH-<KIND>-<NUMBER> form",
                    f"manifest.token_map[{index}].id",
                )
            for field in (
                "source_path",
                "preview_token",
                "production_owner",
                "production_target",
                "verification",
            ):
                if not str(entry.get(field) or "").strip():
                    _add_diagnostic(
                        diagnostics,
                        "preview-incomplete-token-map",
                        f"token map entry must define {field}",
                        f"manifest.token_map[{index}].{field}",
                    )
    if ready:
        unmapped_decision_ids = [
            decision_id
            for decision_id in decision_ids
            if decision_id and decision_id not in mapped_decision_ids
        ]
        if unmapped_decision_ids:
            _add_diagnostic(
                diagnostics,
                "preview-unmapped-decision",
                (
                    "ready preview must map every design decision to an "
                    "implementation owner; missing " + ", ".join(unmapped_decision_ids)
                ),
                "manifest.token_map",
            )

    handoff = manifest.get("handoff")
    if not isinstance(handoff, dict):
        _add_diagnostic(
            diagnostics,
            "preview-missing-handoff-contract",
            "preview manifest must define an implementation-grade handoff contract",
            "manifest.handoff",
        )
        return diagnostics

    continuity_result = validate_ui_source_continuity(
        handoff.get("source_continuity"),
        require_ready=ready,
    )
    for error in continuity_result.errors:
        _add_diagnostic(
            diagnostics,
            "preview-source-continuity-invalid",
            error.message,
            "manifest.handoff.source_continuity" + error.path.removeprefix("$"),
        )

    component_contracts = handoff.get("component_contracts")
    surface_catalog = handoff.get("surface_catalog")
    scenario_matrix = handoff.get("scenario_matrix")
    responsive_matrix = handoff.get("responsive_matrix")
    acceptance_matrix = handoff.get("visual_acceptance_matrix")
    professional_matrices = {
        field: handoff.get(field) for field in DESIGN_PROFESSIONAL_MATRIX_FIELDS
    }
    continuity = handoff.get("source_continuity")
    if (
        ready
        and isinstance(continuity, dict)
        and continuity.get("applicability") == "required"
    ):
        coverage = continuity.get("coverage")
        coverage = coverage if isinstance(coverage, dict) else {}
        actual_coverage = {
            "surface_ids": {
                str(row.get("id") or "").strip()
                for row in surface_catalog or []
                if isinstance(row, dict) and str(row.get("id") or "").strip()
            },
            "interaction_ids": {
                str(row.get("id") or "").strip()
                for row in handoff.get("interaction_matrix") or []
                if isinstance(row, dict) and str(row.get("id") or "").strip()
            },
            "component_ids": {
                str(row.get("id") or "").strip()
                for row in component_contracts or []
                if isinstance(row, dict) and str(row.get("id") or "").strip()
            },
        }
        for field, actual_ids in actual_coverage.items():
            declared_ids = {
                str(value).strip()
                for value in coverage.get(field) or []
                if isinstance(value, str) and value.strip()
            }
            if declared_ids != actual_ids:
                _add_diagnostic(
                    diagnostics,
                    "preview-source-continuity-coverage-mismatch",
                    f"source_continuity.coverage.{field} must exactly cover the handoff IDs",
                    f"manifest.handoff.source_continuity.coverage.{field}",
                )
    for field, entries in (
        ("surface_catalog", surface_catalog),
        ("scenario_matrix", scenario_matrix),
    ):
        if not isinstance(entries, list) or not entries:
            _add_diagnostic(
                diagnostics,
                f"preview-missing-{field.replace('_', '-')}",
                f"preview handoff must define a non-empty {field}",
                f"manifest.handoff.{field}",
            )
    for field, entries in professional_matrices.items():
        if not isinstance(entries, list) or not entries:
            _add_diagnostic(
                diagnostics,
                f"preview-missing-{field.replace('_', '-')}",
                f"preview handoff must define a non-empty {field}",
                f"manifest.handoff.{field}",
            )
    contract_collections = (
        ("surface_catalog", surface_catalog),
        ("scenario_matrix", scenario_matrix),
        ("component_contracts", component_contracts),
        *professional_matrices.items(),
        ("responsive_matrix", responsive_matrix),
        ("visual_acceptance_matrix", acceptance_matrix),
    )
    handoff_ids = [
        str(entry.get("id") or "").strip()
        for entry in token_map or []
        if isinstance(entry, dict)
    ]
    for field, entries in contract_collections:
        if not isinstance(entries, list) or not entries:
            _add_diagnostic(
                diagnostics,
                "preview-incomplete-handoff-contract",
                f"preview handoff {field} must be a non-empty list",
                f"manifest.handoff.{field}",
            )
            continue
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                continue
            contract_id = str(entry.get("id") or "").strip()
            handoff_ids.append(contract_id)
            if (
                ready
                and field == "interaction_matrix"
                and not _valid_design_interaction_contract(entry)
            ):
                _add_diagnostic(
                    diagnostics,
                    "preview-incomplete-handoff-contract",
                    "interaction_matrix rows must define the complete event, feedback, focus, repeat, cancellation, and pending lifecycle",
                    f"manifest.handoff.{field}[{index}]",
                )
            if (
                ready
                and field == "editing_matrix"
                and not _valid_design_editing_contract(entry)
            ):
                _add_diagnostic(
                    diagnostics,
                    "preview-incomplete-handoff-contract",
                    "editing_matrix rows must define the complete input and editing lifecycle",
                    f"manifest.handoff.{field}[{index}]",
                )
            if not DESIGN_HANDOFF_ID_RE.fullmatch(contract_id):
                _add_diagnostic(
                    diagnostics,
                    "preview-invalid-handoff-id",
                    "handoff contract IDs must use a stable DH-<KIND>-<NUMBER> form",
                    f"manifest.handoff.{field}[{index}].id",
                )
            referenced_decisions = entry.get("decision_ids")
            if not isinstance(referenced_decisions, list) or not referenced_decisions:
                _add_diagnostic(
                    diagnostics,
                    "preview-unbound-handoff-contract",
                    "handoff contract entries must reference approved DS-* decisions",
                    f"manifest.handoff.{field}[{index}].decision_ids",
                )
            elif any(item not in decision_ids for item in referenced_decisions):
                _add_diagnostic(
                    diagnostics,
                    "preview-unknown-handoff-decision",
                    "handoff contract decision_ids must reference manifest.decisions",
                    f"manifest.handoff.{field}[{index}].decision_ids",
                )

    motion_contract = handoff.get("motion_contract")
    if not isinstance(motion_contract, dict):
        _add_diagnostic(
            diagnostics,
            "preview-missing-motion-contract",
            "preview handoff must define a structured motion_contract",
            "manifest.handoff.motion_contract",
        )
    else:
        transitions = motion_contract.get("transitions")
        if not isinstance(transitions, list) or not transitions:
            _add_diagnostic(
                diagnostics,
                "preview-incomplete-motion-contract",
                "motion_contract.transitions must be a non-empty list",
                "manifest.handoff.motion_contract.transitions",
            )
            transitions = []
        for index, transition in enumerate(transitions):
            if not isinstance(transition, dict):
                continue
            transition_id = str(transition.get("id") or "").strip()
            handoff_ids.append(transition_id)
            if not DESIGN_HANDOFF_ID_RE.fullmatch(transition_id):
                _add_diagnostic(
                    diagnostics,
                    "preview-invalid-handoff-id",
                    "motion transition IDs must use a stable DH-<KIND>-<NUMBER> form",
                    f"manifest.handoff.motion_contract.transitions[{index}].id",
                )
            referenced_decisions = transition.get("decision_ids")
            if not isinstance(referenced_decisions, list) or not referenced_decisions:
                _add_diagnostic(
                    diagnostics,
                    "preview-unbound-handoff-contract",
                    "motion transitions must reference approved DS-* decisions",
                    f"manifest.handoff.motion_contract.transitions[{index}].decision_ids",
                )
            elif any(item not in decision_ids for item in referenced_decisions):
                _add_diagnostic(
                    diagnostics,
                    "preview-unknown-handoff-decision",
                    "motion transition decision_ids must reference manifest.decisions",
                    f"manifest.handoff.motion_contract.transitions[{index}].decision_ids",
                )
        timing = motion_contract.get("feedback_timing")
        if ready and (
            not str(motion_contract.get("purpose") or "").strip()
            or not str(motion_contract.get("reduced_motion") or "").strip()
            or not isinstance(timing, dict)
            or isinstance(timing.get("immediate_ms"), bool)
            or not isinstance(timing.get("immediate_ms"), int)
            or timing.get("immediate_ms", -1) < 0
            or isinstance(timing.get("progress_ms"), bool)
            or not isinstance(timing.get("progress_ms"), int)
            or timing.get("progress_ms", 0) <= 0
            or isinstance(timing.get("timeout_ms"), bool)
            or not isinstance(timing.get("timeout_ms"), int)
            or timing.get("timeout_ms", 0) <= timing.get("progress_ms", 0)
        ):
            _add_diagnostic(
                diagnostics,
                "preview-incomplete-motion-contract",
                "motion_contract requires purpose, reduced-motion behavior, transitions, and ordered immediate/progress/timeout timing",
                "manifest.handoff.motion_contract",
            )

    component_ids = {
        str(row.get("id") or "").strip()
        for row in component_contracts or []
        if isinstance(row, dict) and str(row.get("id") or "").strip()
    }
    specimen_ids = set(_design_specimen_ids(manifest))
    surface_ids: set[str] = set()
    for index, surface in enumerate(surface_catalog or []):
        if not isinstance(surface, dict):
            continue
        surface_id = str(surface.get("id") or "").strip()
        surface_ids.add(surface_id)
        if ready and (
            any(
                not str(surface.get(field) or "").strip()
                for field in ("profile_id", "name", "kind", "entrypoint_id")
            )
            or not _is_nonempty_string_list(surface.get("source_refs"))
            or not _is_nonempty_string_list(surface.get("specimen_ids"))
            or not set(surface.get("specimen_ids") or []) <= specimen_ids
            or not _is_nonempty_string_list(surface.get("component_ids"))
            or not set(surface.get("component_ids") or []) <= component_ids
        ):
            _add_diagnostic(
                diagnostics,
                "preview-incomplete-surface-catalog",
                "surface_catalog rows require profile, official entrypoint, source, specimen, component, and decision bindings",
                f"manifest.handoff.surface_catalog[{index}]",
            )

    motion_rows = (
        motion_contract.get("transitions") or []
        if isinstance(motion_contract, dict)
        else []
    )
    scenario_sources = {
        "interaction_ids": professional_matrices["interaction_matrix"] or [],
        "editing_ids": professional_matrices["editing_matrix"] or [],
        "data_state_ids": professional_matrices["data_state_matrix"] or [],
        "accessibility_ids": professional_matrices["accessibility_matrix"] or [],
        "navigation_ids": professional_matrices["navigation_matrix"] or [],
        "content_ids": professional_matrices["content_matrix"] or [],
        "responsive_ids": responsive_matrix or [],
        "motion_transition_ids": motion_rows,
    }
    scenario_rows_by_id = {
        str(row.get("id") or "").strip(): row
        for rows in scenario_sources.values()
        if isinstance(rows, list)
        for row in rows
        if isinstance(row, dict) and str(row.get("id") or "").strip()
    }
    known_scenario_refs = {
        field: {
            str(row.get("id") or "").strip()
            for row in rows
            if isinstance(row, dict) and str(row.get("id") or "").strip()
        }
        for field, rows in scenario_sources.items()
        if isinstance(rows, list)
    }
    covered_scenario_refs = {field: set() for field in scenario_sources}
    for index, scenario in enumerate(scenario_matrix or []):
        if not isinstance(scenario, dict):
            continue
        path = f"manifest.handoff.scenario_matrix[{index}]"
        valid = (
            str(scenario.get("surface_id") or "").strip() in surface_ids
            and bool(str(scenario.get("name") or "").strip())
            and scenario.get("risk") in {"low", "medium", "high"}
            and scenario.get("required") is True
            and _valid_design_interaction_script(
                scenario.get("interaction_script"),
                {
                    str(item).strip()
                    for item in scenario.get("data_state_ids") or []
                    if isinstance(item, str) and item.strip()
                },
            )
        )
        referenced_ids: set[str] = set()
        for field in scenario_sources:
            refs = scenario.get(field)
            if (
                not _is_nonempty_string_list(refs)
                or not set(refs or []) <= known_scenario_refs.get(field, set())
            ):
                valid = False
                continue
            covered_scenario_refs[field].update(refs)
            referenced_ids.update(refs)
        referenced_decisions = {
            decision_id
            for row_id in referenced_ids
            for decision_id in scenario_rows_by_id[row_id].get("decision_ids") or []
            if isinstance(decision_id, str) and decision_id.strip()
        }
        if set(scenario.get("decision_ids") or []) != referenced_decisions:
            valid = False
        if ready and not valid:
            _add_diagnostic(
                diagnostics,
                "preview-invalid-scenario-contract",
                "scenario_matrix rows must bind one known surface to known matrix rows with exact decision coverage",
                path,
            )
    for field, expected_refs in known_scenario_refs.items():
        if covered_scenario_refs[field] != expected_refs:
            _add_diagnostic(
                diagnostics,
                "preview-incomplete-scenario-coverage",
                f"scenario_matrix must cover every {field} contract without a Cartesian expansion",
                "manifest.handoff.scenario_matrix",
            )

    usability = handoff.get("usability_validation")
    if not isinstance(usability, dict):
        _add_diagnostic(
            diagnostics,
            "preview-missing-usability-validation",
            "preview handoff must define usability_validation",
            "manifest.handoff.usability_validation",
        )
    elif ready and (
        usability.get("risk_level") not in {"low", "medium", "high"}
        or any(
            not isinstance(usability.get(field), list)
            or not usability.get(field)
            or any(
                not isinstance(item, str) or not item.strip()
                for item in usability.get(field) or []
            )
            for field in ("methods", "critical_tasks", "success_criteria")
        )
        or not isinstance(usability.get("human_review_required"), bool)
        or (
            usability.get("smoothness_acceptance_ids") is not None
            and (
                not isinstance(usability.get("smoothness_acceptance_ids"), list)
                or any(
                    not isinstance(item, str) or not item.strip()
                    for item in usability.get("smoothness_acceptance_ids") or []
                )
                or len(usability.get("smoothness_acceptance_ids") or [])
                != len(set(usability.get("smoothness_acceptance_ids") or []))
            )
        )
        or (
            usability.get("performance_budgets") is not None
            and (
                not isinstance(usability.get("performance_budgets"), dict)
                or set(usability.get("performance_budgets") or {})
                != {
                    "inp_ms",
                    "long_task_ms",
                    "cls",
                    "animation_dropped_frame_pct",
                    "bundle_delta_kb",
                }
                or any(
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or value < 0
                    for value in (
                        usability.get("performance_budgets") or {}
                    ).values()
                )
            )
        )
        or (
            usability.get("risk_level") == "high"
            and usability.get("human_review_required") is not True
        )
    ):
        _add_diagnostic(
            diagnostics,
            "preview-incomplete-usability-validation",
            "usability_validation requires risk, methods, critical tasks, success criteria, and an explicit human-review decision",
            "manifest.handoff.usability_validation",
        )
        if (
            usability.get("risk_level") == "high"
            and usability.get("human_review_required") is not True
        ):
            _add_diagnostic(
                diagnostics,
                "preview-high-risk-human-review-required",
                "high-risk usability validation must require human review",
                "manifest.handoff.usability_validation.human_review_required",
            )

    for index, entry in enumerate(handoff.get("accepted_deviations") or []):
        if not isinstance(entry, dict):
            continue
        deviation_id = str(entry.get("id") or "").strip()
        handoff_ids.append(deviation_id)
        if entry.get("decision_id") not in decision_ids:
            _add_diagnostic(
                diagnostics,
                "preview-unknown-handoff-decision",
                "accepted deviation decision_id must reference manifest.decisions",
                f"manifest.handoff.accepted_deviations[{index}].decision_id",
            )

    nonempty_handoff_ids = [item for item in handoff_ids if item]
    if len(nonempty_handoff_ids) != len(set(nonempty_handoff_ids)):
        _add_diagnostic(
            diagnostics,
            "preview-duplicate-handoff-id",
            "all implementation binding and handoff contract IDs must be unique",
            "manifest.handoff",
        )

    responsive_ids = {
        str(entry.get("id") or "").strip()
        for entry in responsive_matrix or []
        if isinstance(entry, dict)
    }
    acceptance_target_ids = {
        str(entry.get("target_id") or "").strip()
        for entry in acceptance_matrix or []
        if isinstance(entry, dict)
    }
    missing_acceptance_targets = sorted(responsive_ids - acceptance_target_ids)
    unknown_acceptance_targets = sorted(acceptance_target_ids - responsive_ids)
    if missing_acceptance_targets or unknown_acceptance_targets:
        details = []
        if missing_acceptance_targets:
            details.append("uncovered " + ", ".join(missing_acceptance_targets))
        if unknown_acceptance_targets:
            details.append("unknown " + ", ".join(unknown_acceptance_targets))
        _add_diagnostic(
            diagnostics,
            "preview-invalid-handoff-target-coverage",
            "visual acceptance targets must exactly cover responsive targets: "
            + "; ".join(details),
            "manifest.handoff.visual_acceptance_matrix",
        )

    required_states = {
        str(state).strip()
        for entry in component_contracts or []
        if isinstance(entry, dict)
        for state in entry.get("required_states") or []
        if isinstance(state, str) and state.strip()
    }
    accepted_states = {
        str(state).strip()
        for entry in acceptance_matrix or []
        if isinstance(entry, dict)
        for state in entry.get("states") or []
        if isinstance(state, str) and state.strip()
    }
    missing_states = sorted(required_states - accepted_states)
    if missing_states:
        _add_diagnostic(
            diagnostics,
            "preview-incomplete-handoff-state-coverage",
            "visual acceptance matrix does not cover required component states: "
            + ", ".join(missing_states),
            "manifest.handoff.visual_acceptance_matrix",
        )

    accepted_decisions = {
        str(decision_id).strip()
        for entry in acceptance_matrix or []
        if isinstance(entry, dict)
        for decision_id in entry.get("decision_ids") or []
        if isinstance(decision_id, str) and decision_id.strip()
    }
    missing_accepted_decisions = [
        decision_id
        for decision_id in decision_ids
        if decision_id and decision_id not in accepted_decisions
    ]
    if missing_accepted_decisions:
        _add_diagnostic(
            diagnostics,
            "preview-incomplete-handoff-decision-coverage",
            "visual acceptance matrix must cover every approved design decision: "
            + ", ".join(missing_accepted_decisions),
            "manifest.handoff.visual_acceptance_matrix",
        )

    for index, entry in enumerate(acceptance_matrix or []):
        if not isinstance(entry, dict):
            continue
        evidence = {
            str(item).strip()
            for item in entry.get("evidence") or []
            if isinstance(item, str) and item.strip()
        }
        if evidence != DESIGN_HANDOFF_REQUIRED_EVIDENCE:
            _add_diagnostic(
                diagnostics,
                "preview-incomplete-handoff-evidence",
                "each visual acceptance row must require structure, visual, runtime, and comparison evidence",
                f"manifest.handoff.visual_acceptance_matrix[{index}].evidence",
            )
    return diagnostics


def _design_handoff_contract_ids(manifest: dict[str, Any]) -> list[str]:
    handoff = manifest.get("handoff")
    handoff = handoff if isinstance(handoff, dict) else {}
    collections = (
        manifest.get("token_map"),
        *(handoff.get(field) for field in DESIGN_EXPERIENCE_GRAPH_FIELDS),
        handoff.get("component_contracts"),
        *(handoff.get(field) for field in DESIGN_PROFESSIONAL_MATRIX_FIELDS),
        handoff.get("responsive_matrix"),
        handoff.get("visual_acceptance_matrix"),
        handoff.get("accepted_deviations"),
        (
            handoff.get("motion_contract", {}).get("transitions")
            if isinstance(handoff.get("motion_contract"), dict)
            else None
        ),
    )
    return [
        str(entry.get("id") or "").strip()
        for entries in collections
        if isinstance(entries, list)
        for entry in entries
        if isinstance(entry, dict) and str(entry.get("id") or "").strip()
    ]


def _design_capability_profile_ids(manifest: dict[str, Any]) -> list[str]:
    model = manifest.get("capability_model")
    model = model if isinstance(model, dict) else {}
    return [
        str(value).strip()
        for value in model.get("profile_ids") or []
        if isinstance(value, str) and value.strip()
    ]


def _design_specimen_ids(manifest: dict[str, Any]) -> list[str]:
    model = manifest.get("capability_model")
    model = model if isinstance(model, dict) else {}
    return [
        str(specimen.get("id") or "").strip()
        for specimen in model.get("specimens") or []
        if isinstance(specimen, dict) and str(specimen.get("id") or "").strip()
    ]


def _build_design_handoff_payload(
    path: Path,
    *,
    content: str | bytes,
    direction_id: str,
    manifest: dict[str, Any],
    visual_medium: str = "html",
    prompt_sha256: str | None = None,
    inspection_owner: str | None = None,
) -> dict[str, Any]:
    """Select one direction and resolve its immutable implementation contract."""

    directions = manifest.get("directions")
    selected = next(
        (
            direction
            for direction in directions or []
            if isinstance(direction, dict) and direction.get("id") == direction_id
        ),
        None,
    )
    if not isinstance(selected, dict):
        raise DesignLintError(
            f"cannot build handoff for missing approved direction {direction_id}"
        )
    handoff = manifest.get("handoff")
    if not isinstance(handoff, dict):
        raise DesignLintError("design preview manifest has no handoff contract")

    reproduction = deepcopy(handoff)
    reproduction["capability_model"] = deepcopy(manifest.get("capability_model"))
    # The selected direction owns review-board motion tokens. The reproduction
    # contract already contains profile-adapted implementation transitions and
    # reduced-motion behavior; keep those per-platform values intact.
    responsive_by_id = {
        str(entry.get("id") or "").strip(): entry
        for entry in reproduction.get("responsive_matrix") or []
        if isinstance(entry, dict)
    }
    resolved_acceptance: list[dict[str, Any]] = []
    for entry in reproduction.get("visual_acceptance_matrix") or []:
        if not isinstance(entry, dict):
            continue
        resolved = deepcopy(entry)
        target = responsive_by_id.get(str(entry.get("target_id") or "").strip())
        target = target if isinstance(target, dict) else {}
        approved_targets: list[dict[str, str]] = []
        for color_mode in entry.get("color_modes") or []:
            for motion_mode in entry.get("motion_modes") or []:
                if visual_medium == "html":
                    query: dict[str, str | int] = {
                        "mode": str(color_mode),
                        "motion": str(motion_mode),
                        "capture": 1,
                    }
                    profile_id = str(target.get("profile_id") or "").strip()
                    if profile_id:
                        query["profile"] = profile_id
                    target_id = str(target.get("id") or "").strip()
                    if target_id:
                        query["target"] = target_id
                    review_width = target.get("review_width_px")
                    if isinstance(review_width, int):
                        query["viewport"] = review_width
                    approved_ref = f"{path.name}?{urlencode(query)}#{direction_id}"
                else:
                    approved_ref = f"{path.name}#{direction_id}"
                approved_targets.append(
                    {
                        "ref": approved_ref,
                        "color_mode": str(color_mode),
                        "motion_mode": str(motion_mode),
                    }
                )
        resolved["approved_targets"] = approved_targets
        resolved_acceptance.append(resolved)
    reproduction["visual_acceptance_matrix"] = resolved_acceptance
    reproduction["contract_ids"] = _design_handoff_contract_ids(manifest)

    review = manifest.get("review")
    review = review if isinstance(review, dict) else {}
    decision_ids = [
        str(item.get("id") or "").strip()
        for item in manifest.get("decisions") or []
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    ]
    content_bytes = content if isinstance(content, bytes) else content.encode("utf-8")
    approval: dict[str, Any] = {
        "preview_file": path.name,
        "preview_ref": f"{path.name}#{direction_id}",
        "direction_id": direction_id,
        "review_round": str(review.get("round") or "").strip(),
        "preview_sha256": _sha256_bytes(content_bytes),
        "manifest_sha256": _canonical_json_sha256(manifest),
        "decision_ids": decision_ids,
        "visual_medium": visual_medium,
    }
    collaboration = manifest.get("visual_collaboration")
    if isinstance(collaboration, dict):
        for field in DESIGN_VISUAL_COLLABORATION_FIELDS:
            value = str(collaboration.get(field) or "").strip()
            if value:
                approval[field] = value
    if prompt_sha256 is not None:
        approval["prompt_ref"] = f"{path.stem}.prompt.md"
        approval["prompt_sha256"] = prompt_sha256
    if inspection_owner is not None:
        approval["inspection_owner"] = inspection_owner
    return {
        "schema": DESIGN_HANDOFF_SCHEMA,
        "approval": approval,
        "project": deepcopy(manifest.get("project")),
        "direction": deepcopy(selected),
        "content": deepcopy(manifest.get("content")),
        "boundaries": deepcopy(manifest.get("boundaries")),
        "decisions": deepcopy(manifest.get("decisions")),
        "implementation_bindings": deepcopy(manifest.get("token_map")),
        "reproduction": reproduction,
    }


def _validate_preview_handoff_sidecar(
    path: Path,
    *,
    content: str,
    approved_direction: str,
    manifest: dict[str, Any],
    approval_payload: dict[str, Any],
) -> list[DesignDiagnostic]:
    diagnostics: list[DesignDiagnostic] = []
    handoff_path = design_preview_handoff_path(path)
    if not handoff_path.is_file():
        return [
            DesignDiagnostic(
                "preview-missing-handoff-sidecar",
                f"approved preview requires {handoff_path.name}",
                str(handoff_path),
            )
        ]
    try:
        handoff_bytes = handoff_path.read_bytes()
        handoff_payload = json.loads(handoff_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return [
            DesignDiagnostic(
                "preview-invalid-handoff-sidecar",
                f"cannot read handoff sidecar: {exc}",
                str(handoff_path),
            )
        ]
    if not isinstance(handoff_payload, dict):
        return [
            DesignDiagnostic(
                "preview-invalid-handoff-sidecar",
                "handoff sidecar must be a JSON object",
                str(handoff_path),
            )
        ]

    diagnostics.extend(
        _json_schema_diagnostics(
            handoff_payload,
            schema_name="design-handoff-schema.json",
            code="preview-handoff-schema-error",
            root_path="handoff",
        )
    )
    expected_digest = _sha256_bytes(handoff_bytes)
    expected_sidecar = {
        "handoff_file": handoff_path.name,
        "handoff_ref": handoff_path.name,
        "handoff_sha256": expected_digest,
        "handoff_contract_ids": _design_handoff_contract_ids(manifest),
        "capability_profile_ids": _design_capability_profile_ids(manifest),
        "specimen_ids": _design_specimen_ids(manifest),
    }
    for field, expected_value in expected_sidecar.items():
        if approval_payload.get(field) != expected_value:
            _add_diagnostic(
                diagnostics,
                "preview-stale-handoff-binding",
                f"approval sidecar {field} does not bind the immutable handoff",
                f"{design_preview_approval_path(path).name}.{field}",
            )

    expected_payload = _build_design_handoff_payload(
        path,
        content=content,
        direction_id=approved_direction,
        manifest=manifest,
    )
    if handoff_payload != expected_payload:
        _add_diagnostic(
            diagnostics,
            "preview-stale-handoff-sidecar",
            "handoff sidecar must be the exact deterministic projection of the approved direction",
            str(handoff_path),
        )
    return diagnostics


def _validate_preview_approval_sidecar(
    path: Path,
    *,
    content: str,
    approved_direction: str,
    manifest: dict[str, Any] | None,
) -> list[DesignDiagnostic]:
    diagnostics: list[DesignDiagnostic] = []
    approval_path = design_preview_approval_path(path)
    if not approval_path.is_file():
        _add_diagnostic(
            diagnostics,
            "preview-missing-approval-sidecar",
            f"approved preview requires {approval_path.name}",
            str(approval_path),
        )
        return diagnostics
    try:
        payload = json.loads(approval_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        _add_diagnostic(
            diagnostics,
            "preview-invalid-approval-sidecar",
            f"cannot read approval sidecar: {exc}",
            str(approval_path),
        )
        return diagnostics
    if not isinstance(payload, dict):
        _add_diagnostic(
            diagnostics,
            "preview-invalid-approval-sidecar",
            "approval sidecar must be a JSON object",
            str(approval_path),
        )
        return diagnostics

    expected_manifest_sha256 = (
        _canonical_json_sha256(manifest) if isinstance(manifest, dict) else ""
    )
    expected = {
        "schema": DESIGN_PREVIEW_APPROVAL_SCHEMA,
        "visual_medium": "html",
        "preview_file": path.name,
        "direction_id": approved_direction,
        "preview_ref": f"{path.name}#{approved_direction}",
        "html_sha256": _sha256_bytes(content.encode("utf-8")),
        "manifest_sha256": expected_manifest_sha256,
    }
    collaboration = (
        manifest.get("visual_collaboration") if isinstance(manifest, dict) else None
    )
    if isinstance(collaboration, dict):
        expected.update(
            {
                field: str(collaboration.get(field) or "").strip()
                for field in DESIGN_VISUAL_COLLABORATION_FIELDS
            }
        )
    for field, expected_value in expected.items():
        if payload.get(field) != expected_value:
            _add_diagnostic(
                diagnostics,
                "preview-stale-approval-sidecar",
                f"approval sidecar {field} does not bind the current approved preview",
                f"{approval_path.name}.{field}",
            )
    decision_ids = payload.get("decision_ids")
    if not isinstance(decision_ids, list) or not decision_ids or not all(
        isinstance(item, str) and item.strip() for item in decision_ids
    ):
        _add_diagnostic(
            diagnostics,
            "preview-invalid-approval-decisions",
            "approval sidecar decision_ids must be a list of stable non-empty IDs",
            f"{approval_path.name}.decision_ids",
        )
    if isinstance(manifest, dict):
        diagnostics.extend(
            _validate_preview_handoff_sidecar(
                path,
                content=content,
                approved_direction=approved_direction,
                manifest=manifest,
                approval_payload=payload,
            )
        )
    return diagnostics


def _build_direction_checkpoint_payload(
    path: Path,
    *,
    direction_id: str,
    manifest: dict[str, Any],
    visual_medium: str,
    prompt_path: Path | None = None,
) -> dict[str, Any]:
    project_root, design_path, change_id, record, preview_ref, document = (
        _preview_change_context(path)
    )
    contract_profile_ids = [
        str(value)
        for value in document.design_system.get("capability_profiles", [])
        if str(value).strip()
    ]
    manifest_profile_ids = _design_capability_profile_ids(manifest)
    if manifest_profile_ids != contract_profile_ids:
        raise DesignLintError(
            "direction checkpoint capability profiles do not match the draft design change"
        )
    review = manifest.get("review")
    review = review if isinstance(review, dict) else {}
    review_round = str(review.get("round") or "").strip()
    expected_round = _design_preview_round_number(path)
    if review_round != expected_round:
        raise DesignLintError(
            "design preview review.round must match its round-NN filename"
        )
    payload: dict[str, Any] = {
        "schema": DESIGN_DIRECTION_CHECKPOINT_SCHEMA,
        "status": "confirmed",
        "authority": "non-consumable",
        "approved": False,
        "registered": False,
        "consumer_eligible": False,
        "confirmed_by": DESIGN_DIRECTION_CONFIRMATION_MARKER,
        "design_change_id": change_id,
        "design_change_ref": str(record.get("design_ref") or "").strip(),
        "design_change_sha256": _sha256_bytes(design_path.read_bytes()),
        "scope": deepcopy(record.get("scope", [])),
        "capability_profile_ids": manifest_profile_ids,
        "visual_medium": visual_medium,
        "preview_file": path.name,
        "preview_ref": f"{preview_ref}#{direction_id}",
        "preview_sha256": _sha256_bytes(path.read_bytes()),
        "direction_id": direction_id,
        "review_round": review_round,
        "manifest_ref": path.with_suffix(".manifest.json").resolve(strict=False)
        .relative_to(project_root)
        .as_posix(),
        "manifest_sha256": _sha256_bytes(path.with_suffix(".manifest.json").read_bytes()),
    }
    if prompt_path is not None:
        collaboration = manifest.get("visual_collaboration")
        collaboration = collaboration if isinstance(collaboration, dict) else {}
        payload.update(
            {
                "prompt_ref": prompt_path.resolve(strict=False)
                .relative_to(project_root)
                .as_posix(),
                "prompt_sha256": _sha256_bytes(prompt_path.read_bytes()),
                "image_generation": str(collaboration.get("image_generation") or "").strip(),
                "image_inspection": str(collaboration.get("image_inspection") or "").strip(),
                "image_editing": str(collaboration.get("image_editing") or "").strip(),
                "inspection_owner": str(collaboration.get("inspection_owner") or "").strip(),
                "prompt_strategy": str(collaboration.get("prompt_strategy") or "").strip(),
            }
        )
    return payload


def _write_or_verify_direction_checkpoint(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    checkpoint_path = design_preview_direction_checkpoint_path(path)
    diagnostics = _json_schema_diagnostics(
        payload,
        schema_name="design-direction-checkpoint.schema.json",
        code="direction-checkpoint-schema-error",
        root_path="direction_checkpoint",
    )
    if diagnostics:
        raise DesignLintError(
            "; ".join(
                f"{diagnostic.code}: {diagnostic.message}" for diagnostic in diagnostics
            )
        )
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if checkpoint_path.exists():
        existing = checkpoint_path.read_text(encoding="utf-8")
        if existing == rendered:
            return payload
        raise DesignLintError(
            f"direction checkpoint already exists with different bytes: {checkpoint_path}"
        )
    atomic_write_text(checkpoint_path, rendered)
    return payload


def _replace_preview_attribute(content: str, name: str, value: str) -> str:
    pattern = re.compile(
        rf'(<[a-z][^<>]*\b{re.escape(name)}\s*=\s*")[^"]*(")',
        re.IGNORECASE,
    )
    updated, count = pattern.subn(rf"\g<1>{value}\g<2>", content)
    if count == 0:
        raise DesignLintError(f"design preview is missing required attribute {name}")
    return updated


def _replace_preview_manifest(
    content: str,
    manifest: dict[str, Any],
) -> str:
    pattern = re.compile(
        (
            r"(<script\b(?=[^>]*\bid=[\"']"
            + re.escape(DESIGN_PREVIEW_MANIFEST_ID)
            + r"[\"'])[^>]*>)(.*?)(</script>)"
        ),
        re.DOTALL | re.IGNORECASE,
    )
    rendered = (
        json.dumps(manifest, ensure_ascii=False, indent=2)
        .replace("&", r"\u0026")
        .replace("<", r"\u003c")
        .replace(">", r"\u003e")
    )
    updated, count = pattern.subn(
        lambda match: f"{match.group(1)}\n{rendered}\n  {match.group(3)}",
        content,
        count=1,
    )
    if count != 1:
        raise DesignLintError(
            f"design preview must contain exactly one {DESIGN_PREVIEW_MANIFEST_ID}"
        )
    return updated


def _ensure_preview_output_writable(out_path: Path, *, force: bool) -> None:
    if not out_path.exists():
        return
    if not force:
        raise DesignLintError(f"design preview already exists: {out_path}")
    try:
        existing_content = out_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise DesignLintError(
            f"cannot inspect existing design preview {out_path}: {exc}"
        ) from exc
    existing_parser = _DesignPreviewHTMLParser()
    existing_parser.feed(existing_content)
    existing_parser.close()
    existing_status = (
        existing_parser.preview_attrs.get("data-preview-status", "").strip().lower()
    )
    if existing_status == "approved":
        raise DesignLintError(
            f"approved design preview cannot be overwritten: {out_path}"
        )


def _render_preview_direction_ids(
    content: str,
    direction_ids: list[str],
) -> str:
    source_ids = ("direction-main",)
    sentinels = ("__SPECIFY_DIRECTION_SLOT_MAIN__",)
    for source_id, sentinel in zip(source_ids, sentinels, strict=True):
        token_pattern = re.compile(
            rf"(?<![a-z0-9-]){re.escape(source_id)}(?![a-z0-9-])"
        )
        content = token_pattern.sub(sentinel, content)
    for sentinel, direction_id in zip(sentinels, direction_ids, strict=True):
        content = content.replace(sentinel, direction_id)
    return content


def approve_design_preview(
    path: Path,
    *,
    direction_id: str,
    approval_path: Path | None = None,
) -> dict[str, Any]:
    """Freeze one configured preview direction and write its byte-bound approval."""

    if not path.is_file():
        raise DesignLintError(f"design preview does not exist: {path}")
    content = path.read_text(encoding="utf-8")
    parser = _DesignPreviewHTMLParser()
    parser.feed(content)
    parser.close()
    status = parser.preview_attrs.get("data-preview-status", "").strip().lower()
    if status == "approved":
        raise DesignLintError(
            f"design preview is already approved and immutable: {path}"
        )
    if status != "candidate":
        raise DesignLintError(
            "design preview must be a configured candidate before approval"
        )
    if design_preview_direction_checkpoint_path(path).exists():
        raise DesignLintError(
            "design preview has a non-consumable direction checkpoint; approve a new round instead"
        )
    if direction_id not in parser.direction_ids:
        raise DesignLintError(
            f"unknown design direction {direction_id}; choose one of "
            + ", ".join(parser.direction_ids)
        )
    diagnostics = lint_design_preview_file(path, level="ready")
    if diagnostics:
        messages = "; ".join(
            f"{diagnostic.code}: {diagnostic.message}" for diagnostic in diagnostics
        )
        raise DesignLintError(
            f"design preview is not ready for approval: {messages}"
        )
    manifest = _parse_preview_manifest(parser)
    if manifest is None:
        raise DesignLintError("design preview has no embedded manifest")
    review = manifest.setdefault("review", {})
    if not isinstance(review, dict):
        raise DesignLintError("design preview manifest review must be an object")
    review["status"] = "approved"
    review["approved_direction"] = direction_id
    collaboration = manifest.get("visual_collaboration")
    if not isinstance(collaboration, dict):
        raise DesignLintError(
            "design preview manifest must freeze the live visual capability route"
        )

    updated = _replace_preview_manifest(content, manifest)
    updated = _replace_preview_attribute(
        updated,
        "data-preview-status",
        "approved",
    )
    updated = _replace_preview_attribute(
        updated,
        "data-approved-direction",
        direction_id,
    )
    updated = _replace_preview_attribute(
        updated,
        "data-active-direction",
        direction_id,
    )
    resolved_approval_path = approval_path or design_preview_approval_path(path)
    decision_ids = [
        str(item.get("id") or "").strip()
        for item in manifest.get("decisions", [])
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    ]
    if not decision_ids:
        raise DesignLintError(
            "design preview manifest must define stable decisions before approval"
        )
    handoff_path = design_preview_handoff_path(path)
    handoff_payload = _build_design_handoff_payload(
        path,
        content=updated,
        direction_id=direction_id,
        manifest=manifest,
    )
    handoff_diagnostics = _json_schema_diagnostics(
        handoff_payload,
        schema_name="design-handoff-schema.json",
        code="preview-handoff-schema-error",
        root_path="handoff",
    )
    if handoff_diagnostics:
        messages = "; ".join(
            f"{diagnostic.path}: {diagnostic.message}"
            for diagnostic in handoff_diagnostics
        )
        raise DesignLintError(f"cannot approve invalid design handoff: {messages}")
    handoff_text = json.dumps(
        handoff_payload,
        ensure_ascii=False,
        indent=2,
    ) + "\n"
    payload = {
        "schema": DESIGN_PREVIEW_APPROVAL_SCHEMA,
        "visual_medium": "html",
        "preview_file": path.name,
        "direction_id": direction_id,
        "preview_ref": f"{path.name}#{direction_id}",
        "review_round": str(review.get("round") or "").strip(),
        "html_sha256": _sha256_bytes(updated.encode("utf-8")),
        "manifest_sha256": _canonical_json_sha256(manifest),
        "decision_ids": decision_ids,
        "handoff_file": handoff_path.name,
        "handoff_ref": handoff_path.name,
        "handoff_sha256": _sha256_bytes(handoff_text.encode("utf-8")),
        "handoff_contract_ids": _design_handoff_contract_ids(manifest),
        "capability_profile_ids": _design_capability_profile_ids(manifest),
        "specimen_ids": _design_specimen_ids(manifest),
        **{
            field: str(collaboration.get(field) or "").strip()
            for field in DESIGN_VISUAL_COLLABORATION_FIELDS
        },
    }

    atomic_write_text(path, updated)
    atomic_write_text(handoff_path, handoff_text)
    atomic_write_text(
        resolved_approval_path,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )
    post_diagnostics = lint_design_preview_file(path, level="ready")
    if post_diagnostics:
        messages = "; ".join(
            f"{diagnostic.code}: {diagnostic.message}"
            for diagnostic in post_diagnostics
        )
        raise DesignLintError(
            f"approved design preview failed deterministic validation: {messages}"
        )
    return payload


def _design_image_artifact_diagnostics(path: Path) -> tuple[bytes, list[DesignDiagnostic]]:
    try:
        image_bytes = path.read_bytes()
    except OSError as exc:
        return b"", [
            DesignDiagnostic(
                "image-missing-file",
                f"cannot read design image: {exc}",
                str(path),
            )
        ]
    return image_bytes, _design_image_bytes_diagnostics(path, image_bytes)


def _design_image_bytes_diagnostics(
    path: Path, image_bytes: bytes
) -> list[DesignDiagnostic]:
    diagnostics: list[DesignDiagnostic] = []
    suffix = path.suffix.lower()
    if suffix not in DESIGN_IMAGE_SUFFIXES:
        _add_diagnostic(
            diagnostics,
            "image-unsupported-format",
            "design image must be PNG, JPEG, or WEBP",
            str(path),
        )
        return diagnostics
    signatures = {
        ".png": image_bytes.startswith(b"\x89PNG\r\n\x1a\n"),
        ".jpg": image_bytes.startswith(b"\xff\xd8\xff"),
        ".jpeg": image_bytes.startswith(b"\xff\xd8\xff"),
        ".webp": (
            len(image_bytes) >= 12
            and image_bytes.startswith(b"RIFF")
            and image_bytes[8:12] == b"WEBP"
        ),
    }
    if not signatures[suffix]:
        _add_diagnostic(
            diagnostics,
            "image-format-mismatch",
            "design image bytes do not match the PNG, JPEG, or WEBP extension",
            str(path),
        )
    return diagnostics


def _design_image_bundle_path(
    image_path: Path,
    candidate: Path,
    *,
    expected_name: str,
    label: str,
) -> Path:
    if candidate.name != expected_name or candidate.parent.resolve() != image_path.parent.resolve():
        raise DesignLintError(
            f"design image {label} must be the adjacent {expected_name}"
        )
    return candidate


def approve_design_image(
    path: Path,
    *,
    manifest_path: Path,
    prompt_path: Path,
    direction_id: str,
    image_inspection: str,
    image_editing: str,
    approval_path: Path | None = None,
) -> dict[str, Any]:
    """Freeze one image-primary concept with its manifest and generation prompt."""

    image_bytes, image_diagnostics = _design_image_artifact_diagnostics(path)
    if image_diagnostics:
        raise DesignLintError(
            "; ".join(
                f"{diagnostic.code}: {diagnostic.message}"
                for diagnostic in image_diagnostics
            )
        )
    normalized_inspection = image_inspection.strip().lower()
    normalized_editing = image_editing.strip().lower()
    for label, value in (
        ("image inspection", normalized_inspection),
        ("image editing", normalized_editing),
    ):
        if value not in DESIGN_IMAGE_CAPABILITY_VALUES:
            raise DesignLintError(f"{label} must be available or unavailable")
    manifest_path = _design_image_bundle_path(
        path,
        manifest_path,
        expected_name=f"{path.stem}.manifest.json",
        label="manifest",
    )
    prompt_path = _design_image_bundle_path(
        path,
        prompt_path,
        expected_name=f"{path.stem}.prompt.md",
        label="prompt",
    )
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DesignLintError(f"cannot read design image manifest: {exc}") from exc
    if not isinstance(manifest, dict):
        raise DesignLintError("design image manifest must be a JSON object")
    review = manifest.get("review")
    if not isinstance(review, dict):
        raise DesignLintError("design image manifest review must be an object")
    status = str(review.get("status") or "").strip().lower()
    if status == "approved" or design_preview_approval_path(path).exists():
        raise DesignLintError(f"design image round is already approved and immutable: {path}")
    if design_preview_direction_checkpoint_path(path).exists():
        raise DesignLintError(
            "design image has a non-consumable direction checkpoint; approve a new round instead"
        )
    if status != "candidate":
        raise DesignLintError("design image manifest must be a configured candidate before approval")
    directions = manifest.get("directions")
    direction_ids = [
        str(item.get("id") or "").strip()
        for item in directions or []
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    ]
    if direction_id not in direction_ids:
        raise DesignLintError(
            f"unknown design direction {direction_id}; choose one of "
            + ", ".join(direction_ids)
        )
    try:
        prompt_bytes = prompt_path.read_bytes()
        prompt_text = prompt_bytes.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise DesignLintError(f"cannot read image generation prompt: {exc}") from exc
    if len(prompt_text.strip()) < 40 or DESIGN_PREVIEW_PLACEHOLDER_RE.search(prompt_text):
        raise DesignLintError(
            "image generation prompt must be project-specific, non-placeholder Markdown"
        )

    inspection_owner = (
        "agent-and-user" if normalized_inspection == "available" else "user"
    )
    manifest["visual_collaboration"] = {
        "primary_medium": "image-primary",
        "image_generation": "available",
        "image_inspection": normalized_inspection,
        "image_editing": normalized_editing,
        "inspection_owner": inspection_owner,
        "prompt_strategy": "image-generation",
    }
    review["status"] = "approved"
    review["approved_direction"] = direction_id
    diagnostics = _preview_manifest_diagnostics(
        manifest,
        direction_ids=direction_ids,
        ready=True,
        expected_primary_medium="image-primary",
    )
    if diagnostics:
        raise DesignLintError(
            "design image manifest is not ready for approval: "
            + "; ".join(
                f"{diagnostic.code}: {diagnostic.message}"
                for diagnostic in diagnostics
            )
        )

    decision_ids = [
        str(item.get("id") or "").strip()
        for item in manifest.get("decisions") or []
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    ]
    if not decision_ids:
        raise DesignLintError(
            "design image manifest must define stable decisions before approval"
        )
    prompt_sha256 = _sha256_bytes(prompt_bytes)
    image_sha256 = _sha256_bytes(image_bytes)
    handoff_path = design_preview_handoff_path(path)
    handoff_payload = _build_design_handoff_payload(
        path,
        content=image_bytes,
        direction_id=direction_id,
        manifest=manifest,
        visual_medium="image",
        prompt_sha256=prompt_sha256,
        inspection_owner=inspection_owner,
    )
    handoff_diagnostics = _json_schema_diagnostics(
        handoff_payload,
        schema_name="design-handoff-schema.json",
        code="image-handoff-schema-error",
        root_path="handoff",
    )
    if handoff_diagnostics:
        raise DesignLintError(
            "cannot approve invalid design image handoff: "
            + "; ".join(
                f"{diagnostic.path}: {diagnostic.message}"
                for diagnostic in handoff_diagnostics
            )
        )
    handoff_text = json.dumps(
        handoff_payload,
        ensure_ascii=False,
        indent=2,
    ) + "\n"
    payload = {
        "schema": DESIGN_IMAGE_APPROVAL_SCHEMA,
        "visual_medium": "image",
        "preview_file": path.name,
        "direction_id": direction_id,
        "preview_ref": f"{path.name}#{direction_id}",
        "review_round": str(review.get("round") or "").strip(),
        "image_sha256": image_sha256,
        "preview_sha256": image_sha256,
        "manifest_file": manifest_path.name,
        "manifest_ref": manifest_path.name,
        "manifest_sha256": _canonical_json_sha256(manifest),
        "prompt_file": prompt_path.name,
        "prompt_ref": prompt_path.name,
        "prompt_sha256": prompt_sha256,
        "image_generation": "available",
        "prompt_strategy": "image-generation",
        "image_inspection": normalized_inspection,
        "image_editing": normalized_editing,
        "inspection_owner": inspection_owner,
        "decision_ids": decision_ids,
        "handoff_file": handoff_path.name,
        "handoff_ref": handoff_path.name,
        "handoff_sha256": _sha256_bytes(handoff_text.encode("utf-8")),
        "handoff_contract_ids": _design_handoff_contract_ids(manifest),
        "capability_profile_ids": _design_capability_profile_ids(manifest),
        "specimen_ids": _design_specimen_ids(manifest),
    }
    resolved_approval_path = approval_path or design_preview_approval_path(path)
    atomic_write_text(
        manifest_path,
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
    )
    atomic_write_text(handoff_path, handoff_text)
    atomic_write_text(
        resolved_approval_path,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )
    post_diagnostics = lint_design_image_bundle(path, level="ready")
    if post_diagnostics:
        raise DesignLintError(
            "approved design image failed deterministic validation: "
            + "; ".join(
                f"{diagnostic.code}: {diagnostic.message}"
                for diagnostic in post_diagnostics
            )
        )
    return payload


@_design_index_transaction
def _confirm_design_preview_direction_locked(
    project_root: Path,
    path: Path,
    *,
    direction_id: str,
) -> dict[str, Any]:
    if _preview_project_root(path) != project_root:
        raise DesignLintError("design preview project root changed during confirmation")
    if not path.is_file():
        raise DesignLintError(f"design preview does not exist: {path}")
    content = path.read_text(encoding="utf-8")
    parser = _DesignPreviewHTMLParser()
    parser.feed(content)
    parser.close()
    if parser.preview_attrs.get("data-preview-status", "").strip().lower() != "candidate":
        raise DesignLintError("design preview must be a configured candidate before direction confirmation")
    if direction_id not in parser.direction_ids:
        raise DesignLintError(
            f"unknown design direction {direction_id}; choose one of "
            + ", ".join(parser.direction_ids)
        )
    diagnostics = lint_design_preview_file(path, level="concept")
    if diagnostics:
        raise DesignLintError(
            "design preview is not ready for direction confirmation: "
            + "; ".join(f"{diagnostic.code}: {diagnostic.message}" for diagnostic in diagnostics)
        )
    manifest = _parse_preview_manifest(parser)
    if manifest is None:
        raise DesignLintError("design preview has no embedded manifest")
    adjacent_manifest_path = path.with_suffix(".manifest.json")
    try:
        adjacent_manifest = json.loads(adjacent_manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DesignLintError(f"cannot read adjacent design preview manifest: {exc}") from exc
    if not isinstance(adjacent_manifest, dict):
        raise DesignLintError("adjacent design preview manifest must be a JSON object")
    if _canonical_json_sha256(adjacent_manifest) != _canonical_json_sha256(manifest):
        raise DesignLintError(
            "adjacent design preview manifest must exactly match the embedded manifest before direction confirmation"
        )
    payload = _build_direction_checkpoint_payload(
        path,
        direction_id=direction_id,
        manifest=manifest,
        visual_medium="html",
    )
    return _write_or_verify_direction_checkpoint(path, payload)


def confirm_design_preview_direction(
    path: Path,
    *,
    direction_id: str,
) -> dict[str, Any]:
    return _confirm_design_preview_direction_locked(
        _preview_project_root(path),
        path,
        direction_id=direction_id,
    )


@_design_index_transaction
def _confirm_design_image_direction_locked(
    project_root: Path,
    path: Path,
    *,
    manifest_path: Path,
    prompt_path: Path,
    direction_id: str,
    image_inspection: str,
    image_editing: str,
) -> dict[str, Any]:
    if _preview_project_root(path) != project_root:
        raise DesignLintError("design preview project root changed during confirmation")
    _image_bytes, diagnostics = _design_image_artifact_diagnostics(path)
    if diagnostics:
        raise DesignLintError("; ".join(f"{d.code}: {d.message}" for d in diagnostics))
    manifest_path = _design_image_bundle_path(
        path,
        manifest_path,
        expected_name=f"{path.stem}.manifest.json",
        label="manifest",
    )
    prompt_path = _design_image_bundle_path(
        path,
        prompt_path,
        expected_name=f"{path.stem}.prompt.md",
        label="prompt",
    )
    if not manifest_path.is_file():
        raise DesignLintError("image direction confirmation requires --manifest")
    if not prompt_path.is_file():
        raise DesignLintError("image direction confirmation requires --prompt")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DesignLintError(f"cannot read design image manifest: {exc}") from exc
    if not isinstance(manifest, dict):
        raise DesignLintError("design image manifest must be a JSON object")
    review = manifest.get("review")
    if not isinstance(review, dict) or str(review.get("status") or "").strip().lower() != "candidate":
        raise DesignLintError("design image manifest must be a configured candidate before direction confirmation")
    direction_ids = [
        str(item.get("id") or "").strip()
        for item in manifest.get("directions") or []
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    ]
    if direction_id not in direction_ids:
        raise DesignLintError(
            f"unknown design direction {direction_id}; choose one of "
            + ", ".join(direction_ids)
        )
    try:
        prompt_text = prompt_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise DesignLintError(f"cannot read image generation prompt: {exc}") from exc
    if len(prompt_text.strip()) < 40 or DESIGN_PREVIEW_PLACEHOLDER_RE.search(prompt_text):
        raise DesignLintError("image generation prompt must be project-specific, non-placeholder Markdown")
    collaboration = manifest.get("visual_collaboration")
    if not isinstance(collaboration, dict):
        raise DesignLintError("design image manifest must freeze the live visual capability route")
    normalized_inspection = image_inspection.strip().lower()
    normalized_editing = image_editing.strip().lower()
    for label, value in (
        ("image inspection", normalized_inspection),
        ("image editing", normalized_editing),
    ):
        if value not in DESIGN_IMAGE_CAPABILITY_VALUES:
            raise DesignLintError(f"{label} must be available or unavailable")
    expected = {
        "primary_medium": "image-primary",
        "image_generation": "available",
        "image_inspection": normalized_inspection,
        "image_editing": normalized_editing,
        "inspection_owner": "agent-and-user"
        if normalized_inspection == "available"
        else "user",
        "prompt_strategy": "image-generation",
    }
    if collaboration != expected:
        raise DesignLintError(
            "image direction confirmation requires the manifest "
            "visual_collaboration to exactly match the provided capability route"
        )
    diagnostics = lint_design_image_bundle(path, level="concept")
    if diagnostics:
        raise DesignLintError(
            "design image is not ready for direction confirmation: "
            + "; ".join(f"{diagnostic.code}: {diagnostic.message}" for diagnostic in diagnostics)
        )
    payload = _build_direction_checkpoint_payload(
        path,
        direction_id=direction_id,
        manifest=manifest,
        visual_medium="image",
        prompt_path=prompt_path,
    )
    return _write_or_verify_direction_checkpoint(path, payload)


def confirm_design_image_direction(
    path: Path,
    *,
    manifest_path: Path,
    prompt_path: Path,
    direction_id: str,
    image_inspection: str,
    image_editing: str,
) -> dict[str, Any]:
    return _confirm_design_image_direction_locked(
        _preview_project_root(path),
        path,
        manifest_path=manifest_path,
        prompt_path=prompt_path,
        direction_id=direction_id,
        image_inspection=image_inspection,
        image_editing=image_editing,
    )


def lint_design_image_bundle(
    path: Path,
    *,
    level: str = "ready",
) -> list[DesignDiagnostic]:
    """Validate an image-primary round and its immutable approval bundle."""

    normalized_level = level.lower()
    if normalized_level not in SUPPORTED_PREVIEW_LINT_LEVELS:
        raise DesignLintError(f"unsupported design image lint level: {level}")
    image_bytes, diagnostics = _design_image_artifact_diagnostics(path)
    if diagnostics or normalized_level == "structural":
        return enrich_design_diagnostics(diagnostics)
    if normalized_level == "concept":
        try:
            _preview_change_context(path)
        except DesignLintError as exc:
            _add_diagnostic(
                diagnostics,
                "image-noncanonical-workspace",
                str(exc),
                str(path),
            )

    manifest_path = path.with_suffix(".manifest.json")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        _add_diagnostic(
            diagnostics,
            "image-invalid-manifest",
            f"cannot read design image manifest: {exc}",
            str(manifest_path),
        )
        return enrich_design_diagnostics(diagnostics)
    if not isinstance(manifest, dict):
        _add_diagnostic(
            diagnostics,
            "image-invalid-manifest",
            "design image manifest must be a JSON object",
            str(manifest_path),
        )
        return enrich_design_diagnostics(diagnostics)
    direction_ids = [
        str(item.get("id") or "").strip()
        for item in manifest.get("directions") or []
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    ]
    prompt_path = path.with_suffix(".prompt.md")
    try:
        prompt_bytes = prompt_path.read_bytes()
        prompt_text = prompt_bytes.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        _add_diagnostic(
            diagnostics,
            "image-invalid-generation-prompt",
            f"cannot read image generation prompt: {exc}",
            str(prompt_path),
        )
        return enrich_design_diagnostics(diagnostics)
    if (
        len(prompt_text.strip()) < 40
        or DESIGN_PREVIEW_PLACEHOLDER_RE.search(prompt_text)
    ):
        _add_diagnostic(
            diagnostics,
            "image-invalid-generation-prompt",
            "concept image preview requires a project-specific adjacent generation prompt",
            str(prompt_path),
        )
    if normalized_level == "concept":
        diagnostics.extend(
            _concept_preview_manifest_diagnostics(
                manifest,
                direction_ids=direction_ids,
                expected_primary_medium="image-primary",
            )
        )
        return enrich_design_diagnostics(diagnostics)

    approval_path = design_preview_approval_path(path)
    try:
        approval = json.loads(approval_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        _add_diagnostic(
            diagnostics,
            "image-missing-approval-sidecar",
            f"cannot read approved image sidecar: {exc}",
            str(approval_path),
        )
        return enrich_design_diagnostics(diagnostics)
    if not isinstance(approval, dict):
        _add_diagnostic(
            diagnostics,
            "image-invalid-approval-sidecar",
            "approved image sidecar must be a JSON object",
            str(approval_path),
        )
        return enrich_design_diagnostics(diagnostics)

    direction_id = str(approval.get("direction_id") or "").strip()
    image_sha256 = _sha256_bytes(image_bytes)
    expected_approval = {
        "schema": DESIGN_IMAGE_APPROVAL_SCHEMA,
        "visual_medium": "image",
        "preview_file": path.name,
        "preview_ref": f"{path.name}#{direction_id}",
        "image_sha256": image_sha256,
        "preview_sha256": image_sha256,
        "manifest_file": f"{path.stem}.manifest.json",
        "manifest_ref": f"{path.stem}.manifest.json",
        "prompt_file": f"{path.stem}.prompt.md",
        "prompt_ref": f"{path.stem}.prompt.md",
        "handoff_file": design_preview_handoff_path(path).name,
        "handoff_ref": design_preview_handoff_path(path).name,
        "image_generation": "available",
        "prompt_strategy": "image-generation",
    }
    for field, expected_value in expected_approval.items():
        if approval.get(field) != expected_value:
            _add_diagnostic(
                diagnostics,
                "image-stale-approval-sidecar",
                f"image approval sidecar {field} does not bind the immutable round",
                f"{approval_path.name}.{field}",
            )
    image_inspection = str(approval.get("image_inspection") or "").strip()
    image_editing = str(approval.get("image_editing") or "").strip()
    inspection_owner = str(approval.get("inspection_owner") or "").strip()
    expected_owner = "agent-and-user" if image_inspection == "available" else "user"
    if (
        image_inspection not in DESIGN_IMAGE_CAPABILITY_VALUES
        or image_editing not in DESIGN_IMAGE_CAPABILITY_VALUES
        or inspection_owner != expected_owner
    ):
        _add_diagnostic(
            diagnostics,
            "image-invalid-capability-binding",
            "image approval must bind inspection/editing availability and the truthful inspection owner",
            str(approval_path),
        )

    if approval.get("manifest_sha256") != _canonical_json_sha256(manifest):
        _add_diagnostic(
            diagnostics,
            "image-stale-manifest-binding",
            "image approval sidecar does not bind the immutable manifest",
            str(manifest_path),
        )
    diagnostics.extend(
        _preview_manifest_diagnostics(
            manifest,
            direction_ids=direction_ids,
            ready=True,
            expected_primary_medium="image-primary",
        )
    )
    review = manifest.get("review")
    review = review if isinstance(review, dict) else {}
    if (
        str(review.get("status") or "").strip() != "approved"
        or str(review.get("approved_direction") or "").strip() != direction_id
    ):
        _add_diagnostic(
            diagnostics,
            "image-unapproved-manifest",
            "design image manifest must freeze the approved direction",
            "manifest.review",
        )
    expected_collaboration = {
        "primary_medium": "image-primary",
        "image_generation": "available",
        "image_inspection": image_inspection,
        "image_editing": image_editing,
        "inspection_owner": inspection_owner,
        "prompt_strategy": "image-generation",
    }
    if manifest.get("visual_collaboration") != expected_collaboration:
        _add_diagnostic(
            diagnostics,
            "image-capability-manifest-drift",
            "manifest visual_collaboration must match the approved live capability route",
            "manifest.visual_collaboration",
        )

    if approval.get("prompt_sha256") != _sha256_bytes(prompt_bytes):
        _add_diagnostic(
            diagnostics,
            "image-stale-prompt-binding",
            "approved image must bind its project-specific generation/edit prompt",
            str(prompt_path),
        )

    handoff_path = design_preview_handoff_path(path)
    try:
        handoff_bytes = handoff_path.read_bytes()
        handoff = json.loads(handoff_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        _add_diagnostic(
            diagnostics,
            "image-invalid-handoff-sidecar",
            f"cannot read design image handoff: {exc}",
            str(handoff_path),
        )
        return enrich_design_diagnostics(diagnostics)
    diagnostics.extend(
        _json_schema_diagnostics(
            handoff,
            schema_name="design-handoff-schema.json",
            code="image-handoff-schema-error",
            root_path="handoff",
        )
    )
    if approval.get("handoff_sha256") != _sha256_bytes(handoff_bytes):
        _add_diagnostic(
            diagnostics,
            "image-stale-handoff-binding",
            "image approval sidecar does not bind the immutable handoff",
            str(handoff_path),
        )
    expected_handoff = _build_design_handoff_payload(
        path,
        content=image_bytes,
        direction_id=direction_id,
        manifest=manifest,
        visual_medium="image",
        prompt_sha256=_sha256_bytes(prompt_bytes),
        inspection_owner=inspection_owner,
    )
    if handoff != expected_handoff:
        _add_diagnostic(
            diagnostics,
            "image-stale-handoff-sidecar",
            "image handoff must be the exact deterministic projection of the approved concept",
            str(handoff_path),
        )
    return enrich_design_diagnostics(diagnostics)


def lint_design_preview_file(
    path: Path,
    *,
    level: str = "structural",
) -> list[DesignDiagnostic]:
    """Validate a project-level, single-concept HTML design preview round."""

    normalized_level = level.lower()
    if normalized_level not in SUPPORTED_PREVIEW_LINT_LEVELS:
        raise DesignLintError(f"unsupported design preview lint level: {level}")
    if not path.exists():
        return enrich_design_diagnostics(
            [
                DesignDiagnostic(
                    "preview-missing-file",
                    f"{path} does not exist",
                    str(path),
                )
            ]
        )
    if not path.is_file():
        return enrich_design_diagnostics(
            [
                DesignDiagnostic(
                    "preview-read-error",
                    f"{path} is not a file",
                    str(path),
                )
            ]
        )

    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return enrich_design_diagnostics(
            [
                DesignDiagnostic(
                    "preview-read-error",
                    f"cannot read {path}: {exc}",
                    str(path),
                )
            ]
        )

    parser = _DesignPreviewHTMLParser()
    try:
        parser.feed(content)
        parser.close()
    except Exception as exc:
        return enrich_design_diagnostics(
            [
                DesignDiagnostic(
                    "preview-parse-error",
                    f"cannot parse {path}: {exc}",
                    str(path),
                )
            ]
        )

    diagnostics: list[DesignDiagnostic] = []
    if not re.search(r"(?i)<!doctype\s+html\s*>", content):
        _add_diagnostic(
            diagnostics,
            "preview-missing-doctype",
            "design preview must declare <!doctype html>",
            "html",
        )
    if not parser.html_lang:
        _add_diagnostic(
            diagnostics,
            "preview-missing-language",
            "design preview must declare a document language",
            "html.lang",
        )

    schema = parser.preview_attrs.get("data-design-preview-schema", "").strip()
    if schema != DESIGN_PREVIEW_SCHEMA:
        _add_diagnostic(
            diagnostics,
            "preview-invalid-schema",
            f"data-design-preview-schema must equal {DESIGN_PREVIEW_SCHEMA}",
            "data-design-preview-schema",
        )

    direction_ids = parser.direction_ids
    if len(direction_ids) != 1:
        _add_diagnostic(
            diagnostics,
            "preview-direction-count",
            "design preview must contain exactly one current concept",
            "data-direction-id",
        )
    if len(set(direction_ids)) != len(direction_ids):
        _add_diagnostic(
            diagnostics,
            "preview-duplicate-direction",
            "design direction IDs must be unique",
            "data-direction-id",
        )
    if parser.direction_anchor_ids != direction_ids:
        _add_diagnostic(
            diagnostics,
            "preview-direction-anchor-mismatch",
            "every direction control must expose an id equal to its data-direction-id",
            "data-direction-id.id",
        )

    for fragment in sorted(set(parser.fragment_references)):
        if fragment not in parser.element_ids:
            _add_diagnostic(
                diagnostics,
                "preview-unresolved-fragment",
                f"local fragment #{fragment} does not resolve to an element id",
                f"href.#{fragment}",
            )

    for section in DESIGN_PREVIEW_REQUIRED_SECTIONS:
        if section not in parser.sections:
            _add_diagnostic(
                diagnostics,
                "preview-missing-section",
                f"design preview is missing required section: {section}",
                f"data-preview-section.{section}",
            )

    style_text = "\n".join(parser.style_parts)
    script_text = "\n".join(parser.script_parts)
    for direction_id in dict.fromkeys(direction_ids):
        selector = re.compile(
            r"body\s*\[\s*data-active-direction\s*=\s*[\"']"
            + re.escape(direction_id)
            + r"[\"']\s*\]"
        )
        if not selector.search(style_text):
            _add_diagnostic(
                diagnostics,
                "preview-missing-direction-style",
                (
                    f"direction {direction_id} must have a body "
                    "data-active-direction style scope"
                ),
                f"style.{direction_id}",
            )
    try:
        manifest = _parse_preview_manifest(parser)
    except DesignLintError as exc:
        manifest = None
        _add_diagnostic(
            diagnostics,
            "preview-invalid-manifest",
            str(exc),
            f"script#{DESIGN_PREVIEW_MANIFEST_ID}",
        )
    if normalized_level == "concept":
        try:
            _preview_change_context(path)
        except DesignLintError as exc:
            _add_diagnostic(
                diagnostics,
                "preview-noncanonical-workspace",
                str(exc),
                str(path),
            )
    if normalized_level == "concept":
        diagnostics.extend(
            _concept_preview_manifest_diagnostics(
                manifest,
                direction_ids=direction_ids,
                expected_primary_medium="html-primary",
            )
        )
    else:
        diagnostics.extend(
            _preview_manifest_diagnostics(
                manifest,
                direction_ids=direction_ids,
                ready=normalized_level == "ready",
                expected_primary_medium="html-primary",
            )
        )
    for token_name in (
        "--motion-duration-fast",
        "--motion-duration-base",
        "--motion-easing-standard",
        "--motion-easing-emphasized",
    ):
        if token_name not in style_text:
            _add_diagnostic(
                diagnostics,
                "preview-missing-motion-token",
                f"design preview must define {token_name}",
                f"style.{token_name}",
            )
    if "prefers-reduced-motion: reduce" not in style_text:
        _add_diagnostic(
            diagnostics,
            "preview-missing-reduced-motion",
            "design preview must provide a prefers-reduced-motion fallback",
            "style.prefers-reduced-motion",
        )
    for routing_signal in ("location.hash", "hashchange"):
        if routing_signal not in script_text:
            _add_diagnostic(
                diagnostics,
                "preview-missing-direction-routing",
                "design preview must open and track the selected direction from the URL fragment",
                f"script.{routing_signal}",
            )

    dependency_evidence = list(parser.external_dependencies)
    if (
        DESIGN_PREVIEW_REMOTE_RE.search(content)
        or re.search(r"(?i)@import\b", style_text)
        or re.search(r"(?i)url\s*\(\s*(?![\"']?data:)", style_text)
        or DESIGN_PREVIEW_NETWORK_SCRIPT_RE.search(script_text)
    ):
        dependency_evidence.append("remote or runtime-loaded content")
    if dependency_evidence:
        _add_diagnostic(
            diagnostics,
            "preview-remote-dependency",
            "design preview must be a self-contained HTML file without external or network runtime dependencies",
            "html.dependencies",
        )

    if normalized_level in {"concept", "ready"}:
        prototype_status = (
            parser.preview_attrs.get("data-prototype-status", "").strip().lower()
        )
        if prototype_status != "authored" or DESIGN_PREVIEW_SEED_RE.search(content):
            _add_diagnostic(
                diagnostics,
                "preview-unfinished-prototype",
                (
                    f"{normalized_level} preview must replace the prototype seed and set "
                    'data-prototype-status="authored" after visual inspection'
                ),
                "data-prototype-status",
            )
        status = parser.preview_attrs.get("data-preview-status", "").strip().lower()
        if normalized_level == "concept" and status != "candidate":
            _add_diagnostic(
                diagnostics,
                "preview-not-candidate",
                "concept preview status must be candidate",
                "data-preview-status",
            )
        elif normalized_level == "ready" and status not in {"candidate", "approved"}:
            _add_diagnostic(
                diagnostics,
                "preview-not-candidate",
                "ready preview status must be candidate or approved",
                "data-preview-status",
            )
        if DESIGN_PREVIEW_PLACEHOLDER_RE.search(content):
            _add_diagnostic(
                diagnostics,
                "preview-unresolved-placeholder",
                f"{normalized_level} preview must not contain unresolved __PLACEHOLDER__ values",
                "html",
            )
        if ":focus-visible" not in style_text:
            _add_diagnostic(
                diagnostics,
                "preview-missing-focus-visible",
                "concept preview must style visible focus states",
                "style.focus-visible",
            )
    if normalized_level == "ready":
        review = manifest.get("review") if isinstance(manifest, dict) else None
        if status == "candidate" and (
            not isinstance(review, dict)
            or str(review.get("status") or "").strip().lower() != "candidate"
            or review.get("approved_direction") not in {None, ""}
        ):
            _add_diagnostic(
                diagnostics,
                "preview-manifest-candidate-mismatch",
                "candidate preview manifest must record candidate status without an approved direction",
                "manifest.review",
            )
        if status == "approved":
            approved_direction = parser.preview_attrs.get(
                "data-approved-direction",
                "",
            ).strip()
            if approved_direction not in set(direction_ids):
                _add_diagnostic(
                    diagnostics,
                    "preview-invalid-approval",
                    "approved preview must name one existing data-direction-id",
                    "data-approved-direction",
                )
            if not isinstance(review, dict) or (
                str(review.get("status") or "").strip().lower() != "approved"
                or str(review.get("approved_direction") or "").strip()
                != approved_direction
            ):
                _add_diagnostic(
                    diagnostics,
                    "preview-manifest-approval-mismatch",
                    "approved preview manifest must record the same approved direction",
                    "manifest.review",
                )
            diagnostics.extend(
                _validate_preview_approval_sidecar(
                    path,
                    content=content,
                    approved_direction=approved_direction,
                    manifest=manifest,
                )
            )

    return enrich_design_diagnostics(diagnostics)


def scaffold_design_preview_manifest(
    out_path: Path,
    *,
    force: bool = False,
    template_path: Path | None = None,
    profile_ids: list[str] | None = None,
) -> Path:
    """Extract the editable preview manifest from the canonical HTML template."""

    _source, content = _load_design_preview_template(template_path)
    manifest_suffix = ".manifest.json"
    if out_path.name.lower().endswith(manifest_suffix):
        preview_path = out_path.with_name(
            out_path.name[: -len(manifest_suffix)] + ".html"
        )
        if preview_path.exists():
            _ensure_preview_output_writable(preview_path, force=True)
    if out_path.exists() and not force:
        raise DesignLintError(f"design preview manifest already exists: {out_path}")
    parser = _DesignPreviewHTMLParser()
    parser.feed(content)
    parser.close()
    manifest = _parse_preview_manifest(parser)
    if manifest is None:
        raise DesignLintError(
            f"design preview template has no {DESIGN_PREVIEW_MANIFEST_ID}"
        )
    _apply_design_capability_profiles(manifest, profile_ids or ["web"])

    round_match = re.fullmatch(
        r"round-(\d+)\.manifest",
        out_path.stem,
        re.IGNORECASE,
    )
    review = manifest.get("review")
    if not isinstance(review, dict):
        review = {}
        manifest["review"] = review
    if round_match:
        review["round"] = str(int(round_match.group(1)))
    review["status"] = "scaffold"
    review["approved_direction"] = None
    manifest["configured"] = False

    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(
            out_path,
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        )
    except OSError as exc:
        raise DesignLintError(
            f"cannot write design preview manifest {out_path}: {exc}"
        ) from exc
    return out_path


def render_design_preview(
    manifest_path: Path,
    out_path: Path,
    *,
    force: bool = False,
    template_path: Path | None = None,
) -> Path:
    """Render an unfinished structural preview draft from a compact manifest."""

    _source, content = _load_design_preview_template(template_path)
    if not manifest_path.is_file():
        raise DesignLintError(
            f"design preview manifest does not exist: {manifest_path}"
        )
    _ensure_preview_output_writable(out_path, force=force)

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DesignLintError(
            f"cannot read design preview manifest {manifest_path}: {exc}"
        ) from exc
    if not isinstance(manifest, dict):
        raise DesignLintError("design preview manifest must be a JSON object")

    round_match = re.fullmatch(r"round-(\d+)", out_path.stem, re.IGNORECASE)
    review = manifest.get("review")
    if not isinstance(review, dict):
        review = {}
        manifest["review"] = review
    round_number = (
        str(int(round_match.group(1)))
        if round_match
        else str(review.get("round") or "").strip()
    )
    if not round_number:
        raise DesignLintError(
            "design preview review.round is required when --out is not round-NN.html"
        )
    manifest["configured"] = True
    review.update(
        {
            "round": round_number,
            "status": "candidate",
            "approved_direction": None,
        }
    )

    directions = manifest.get("directions")
    direction_ids = (
        [
            str(direction.get("id") or "").strip()
            for direction in directions
            if isinstance(direction, dict)
        ]
        if isinstance(directions, list)
        else []
    )
    manifest_diagnostics = _preview_manifest_diagnostics(
        manifest,
        direction_ids=direction_ids,
        ready=True,
        expected_primary_medium="html-primary",
    )
    if manifest_diagnostics:
        messages = "; ".join(
            f"{diagnostic.code}: {diagnostic.message}"
            for diagnostic in manifest_diagnostics
        )
        raise DesignLintError(f"design preview manifest is not ready: {messages}")

    content = _render_preview_direction_ids(content, direction_ids)
    content = _replace_preview_manifest(content, manifest)
    content = _replace_preview_attribute(content, "data-preview-status", "candidate")
    content = _replace_preview_attribute(content, "data-review-round", round_number)
    content = _replace_preview_attribute(content, "data-approved-direction", "")
    content = _replace_preview_attribute(
        content,
        "data-active-direction",
        direction_ids[0],
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    validation_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".html",
            prefix=f".{out_path.stem}-render-check-",
            dir=out_path.parent,
            delete=False,
        ) as validation_file:
            validation_file.write(content)
            validation_path = Path(validation_file.name)
        diagnostics = lint_design_preview_file(validation_path, level="structural")
    finally:
        if validation_path is not None:
            validation_path.unlink(missing_ok=True)
    if diagnostics:
        messages = "; ".join(
            f"{diagnostic.code}: {diagnostic.message}"
            for diagnostic in diagnostics
        )
        raise DesignLintError(f"rendered design preview is not ready: {messages}")

    try:
        atomic_write_text(out_path, content)
    except OSError as exc:
        raise DesignLintError(f"cannot write design preview {out_path}: {exc}") from exc
    return out_path


def scaffold_design_preview(
    out_path: Path,
    *,
    force: bool = False,
    template_path: Path | None = None,
) -> Path:
    """Copy the bundled single-concept design preview scaffold."""

    source, content = _load_design_preview_template(template_path)
    _ensure_preview_output_writable(out_path, force=force)

    validation_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".html",
            prefix=".design-preview-template-check-",
            delete=False,
        ) as validation_file:
            validation_file.write(content)
            validation_path = Path(validation_file.name)
        diagnostics = lint_design_preview_file(validation_path, level="structural")
        if diagnostics:
            messages = "; ".join(
                f"{diagnostic.code}: {diagnostic.message}"
                for diagnostic in diagnostics
            )
            raise DesignLintError(
                f"design preview template {source} is invalid: {messages}"
            )
        round_match = re.fullmatch(r"round-(\d+)", out_path.stem, re.IGNORECASE)
        if round_match:
            round_number = str(int(round_match.group(1)))
            content = content.replace("__ROUND_NUMBER__", round_number)
            content = re.sub(
                r'(data-review-round=")[^"]*(")',
                rf"\g<1>{round_number}\g<2>",
                content,
                count=1,
            )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(out_path, content)
    except OSError as exc:
        raise DesignLintError(f"cannot write design preview {out_path}: {exc}") from exc
    finally:
        if validation_path is not None:
            validation_path.unlink(missing_ok=True)
    return out_path


def _load_design_preview_template(template_path: Path | None) -> tuple[Path, str]:
    """Load a custom HTML template or compose the bundled Jinja source parts."""

    if template_path is not None:
        if not template_path.is_file():
            raise DesignLintError(
                f"design preview template does not exist: {template_path}"
            )
        try:
            return template_path, template_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise DesignLintError(
                f"cannot read design preview template {template_path}: {exc}"
            ) from exc

    template_dir = _locate_design_preview_template_dir()
    template_file = template_dir / "template.html.j2"
    if not template_file.is_file():
        raise DesignLintError(
            f"design preview Jinja template does not exist: {template_file}"
        )
    try:
        environment = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=False,
            undefined=StrictUndefined,
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
            newline_sequence="\n",
        )
        return template_file, environment.get_template(template_file.name).render()
    except (OSError, UnicodeDecodeError, TemplateError) as exc:
        raise DesignLintError(
            f"cannot render design preview Jinja template {template_file}: {exc}"
        ) from exc


def _locate_design_preview_template_dir() -> Path:
    package_template = Path(__file__).parent / "design_preview_source"
    if package_template.is_dir():
        return package_template
    return Path(__file__).parents[2] / "src" / "specify_cli" / "design_preview_source"


def _locate_design_preview_template() -> Path:
    """Locate the generated compatibility artifact, not the Jinja source."""

    package_template = (
        Path(__file__).parent
        / "core_pack"
        / "templates"
        / "design-preview-template.html"
    )
    if package_template.is_file():
        return package_template
    return Path(__file__).parents[2] / "templates" / "design-preview-template.html"


def _parse_ui_target_manifest(
    parser: _UITargetHTMLParser,
) -> dict[str, Any] | None:
    raw = "".join(parser.manifest_parts).strip()
    if not raw:
        return None
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DesignLintError(
            f"embedded {UI_TARGET_MANIFEST_ID} is not valid JSON: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise DesignLintError(
            f"embedded {UI_TARGET_MANIFEST_ID} must be a JSON object"
        )
    return payload


def lint_ui_target_file(
    path: Path,
    *,
    level: str = "structural",
) -> list[DesignDiagnostic]:
    """Validate a feature-level, single-file UI target review artifact."""

    normalized_level = level.lower()
    if normalized_level not in SUPPORTED_LINT_LEVELS:
        raise DesignLintError(f"unsupported UI target lint level: {level}")
    if not path.exists():
        return [
            DesignDiagnostic(
                "ui-target-missing-file",
                f"{path} does not exist",
                str(path),
            )
        ]
    if not path.is_file():
        return [
            DesignDiagnostic(
                "ui-target-read-error",
                f"{path} is not a file",
                str(path),
            )
        ]
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [
            DesignDiagnostic(
                "ui-target-read-error",
                f"cannot read {path}: {exc}",
                str(path),
            )
        ]

    parser = _UITargetHTMLParser()
    try:
        parser.feed(content)
        parser.close()
    except Exception as exc:
        return [
            DesignDiagnostic(
                "ui-target-parse-error",
                f"cannot parse {path}: {exc}",
                str(path),
            )
        ]

    diagnostics: list[DesignDiagnostic] = []
    if not re.search(r"(?i)<!doctype\s+html\s*>", content):
        _add_diagnostic(
            diagnostics,
            "ui-target-missing-doctype",
            "UI target must declare <!doctype html>",
            "html",
        )
    if not parser.html_lang:
        _add_diagnostic(
            diagnostics,
            "ui-target-missing-language",
            "UI target must declare a document language",
            "html.lang",
        )
    if (
        parser.target_attrs.get("data-ui-target-schema", "").strip()
        != UI_TARGET_SCHEMA
    ):
        _add_diagnostic(
            diagnostics,
            "ui-target-invalid-schema",
            f"data-ui-target-schema must equal {UI_TARGET_SCHEMA}",
            "data-ui-target-schema",
        )

    style_text = "\n".join(parser.style_parts)
    script_text = "\n".join(parser.script_parts)
    try:
        manifest = _parse_ui_target_manifest(parser)
    except DesignLintError as exc:
        manifest = None
        _add_diagnostic(
            diagnostics,
            "ui-target-invalid-manifest",
            str(exc),
            f"script#{UI_TARGET_MANIFEST_ID}",
        )
    if manifest is None:
        _add_diagnostic(
            diagnostics,
            "ui-target-missing-manifest",
            "UI target must embed one machine-readable manifest",
            f"script#{UI_TARGET_MANIFEST_ID}",
        )
        manifest = {}
    elif manifest.get("schema") != UI_TARGET_MANIFEST_SCHEMA:
        _add_diagnostic(
            diagnostics,
            "ui-target-invalid-manifest-schema",
            f"UI target manifest schema must equal {UI_TARGET_MANIFEST_SCHEMA}",
            "manifest.schema",
        )

    if parser.inline_event_handlers:
        _add_diagnostic(
            diagnostics,
            "ui-target-inline-event-handler",
            "UI target must use bounded event listeners, not inline event-handler attributes",
            "html.events",
        )
    dependency_evidence = list(parser.external_dependencies)
    if (
        DESIGN_PREVIEW_REMOTE_RE.search(content)
        or re.search(r"(?i)@import\b", style_text)
        or re.search(r"(?i)url\s*\(\s*(?![\"']?data:)", style_text)
        or UI_TARGET_NETWORK_OR_PERSISTENCE_RE.search(content)
    ):
        dependency_evidence.append("remote, network, or persistence behavior")
    if dependency_evidence:
        _add_diagnostic(
            diagnostics,
            "ui-target-forbidden-runtime",
            "UI target must be self-contained and must not load remote assets, call a network, or persist data",
            "html.dependencies",
        )
    for required_css in (
        "@container",
        "prefers-reduced-motion: reduce",
        "--target-width",
    ):
        if required_css not in style_text:
            _add_diagnostic(
                diagnostics,
                "ui-target-missing-responsive-contract",
                f"UI target must include {required_css}",
                f"style.{required_css}",
            )
    for required_runtime in (
        "URLSearchParams",
        "location.hash",
        "hashchange",
        "addEventListener",
    ):
        if required_runtime not in script_text:
            _add_diagnostic(
                diagnostics,
                "ui-target-missing-review-control",
                f"UI target review runtime must include {required_runtime}",
                f"script.{required_runtime}",
            )

    viewports = manifest.get("viewports")
    normalized_viewports = (
        {
            str(item).strip()
            for item in viewports
            if isinstance(item, (str, int)) and str(item).strip()
        }
        if isinstance(viewports, list)
        else set()
    )
    if len(normalized_viewports) < 2 or normalized_viewports != parser.widths:
        _add_diagnostic(
            diagnostics,
            "ui-target-viewport-mismatch",
            "manifest viewports must match at least two rendered viewport controls",
            "manifest.viewports",
        )
    required_states = manifest.get("required_states")
    normalized_states = (
        {
            str(item).strip()
            for item in required_states
            if isinstance(item, str) and item.strip()
        }
        if isinstance(required_states, list)
        else set()
    )
    baseline_states = {"default", "loading", "empty", "error"}
    if (
        not baseline_states <= normalized_states
        or normalized_states != parser.states
    ):
        _add_diagnostic(
            diagnostics,
            "ui-target-state-mismatch",
            "manifest required_states must match rendered controls and include default/loading/empty/error",
            "manifest.required_states",
        )

    if normalized_level == "ready":
        if manifest.get("configured") is not True:
            _add_diagnostic(
                diagnostics,
                "ui-target-not-configured",
                "ready UI target manifest must set configured to true",
                "manifest.configured",
            )
        if DESIGN_PREVIEW_PLACEHOLDER_RE.search(content):
            _add_diagnostic(
                diagnostics,
                "ui-target-unresolved-placeholder",
                "ready UI target must not contain unresolved __PLACEHOLDER__ values",
                "html",
            )
        if (
            parser.target_attrs.get("data-status", "").strip().lower()
            not in {"candidate", "locked"}
        ):
            _add_diagnostic(
                diagnostics,
                "ui-target-invalid-status",
                "ready UI target status must be candidate or locked",
                "data-status",
            )
        if (
            parser.target_attrs.get("data-fidelity", "").strip().lower()
            not in {"approximate", "high", "inspiration"}
        ):
            _add_diagnostic(
                diagnostics,
                "ui-target-invalid-fidelity",
                "ready UI target must name approximate, high, or inspiration fidelity",
                "data-fidelity",
            )
        feature = manifest.get("feature")
        if not isinstance(feature, dict) or any(
            not isinstance(feature.get(field), str)
            or not str(feature.get(field) or "").strip()
            for field in ("name", "short_name", "title", "job")
        ):
            _add_diagnostic(
                diagnostics,
                "ui-target-incomplete-feature",
                "ready UI target must define feature name, short name, title, and job",
                "manifest.feature",
            )
        approval = manifest.get("approval")
        if not isinstance(approval, dict):
            _add_diagnostic(
                diagnostics,
                "ui-target-missing-approval",
                "ready UI target must bind its approved design source",
                "manifest.approval",
            )
        else:
            approved_ref = str(approval.get("ref") or "").strip()
            direction_id = str(approval.get("direction_id") or "").strip()
            if not approved_ref or not direction_id:
                _add_diagnostic(
                    diagnostics,
                    "ui-target-incomplete-approval",
                    "ready UI target approval requires ref and direction_id",
                    "manifest.approval",
                )
            if UI_TARGET_APPROVED_PREVIEW_REF_RE.search(approved_ref):
                for field in (
                    "preview_sha256",
                    "manifest_sha256",
                    "handoff_sha256",
                ):
                    if not re.fullmatch(
                        r"[0-9a-f]{64}",
                        str(approval.get(field) or "").strip(),
                    ):
                        _add_diagnostic(
                            diagnostics,
                            "ui-target-invalid-approval-digest",
                            f"approved visual round requires a valid {field}",
                            f"manifest.approval.{field}",
                        )
                if not str(approval.get("handoff_ref") or "").strip().lower().endswith(
                    ".handoff.json"
                ):
                    _add_diagnostic(
                        diagnostics,
                        "ui-target-invalid-handoff-ref",
                        "approved visual round requires its immutable handoff reference",
                        "manifest.approval.handoff_ref",
                    )
        content_fixture = manifest.get("content")
        if not isinstance(content_fixture, dict) or any(
            not isinstance(value, str) or not value.strip()
            for value in content_fixture.values()
        ):
            _add_diagnostic(
                diagnostics,
                "ui-target-incomplete-content",
                "ready UI target content must be representative and non-empty",
                "manifest.content",
            )
        decision_ids = manifest.get("decision_ids")
        if (
            not isinstance(decision_ids, list)
            or not decision_ids
            or any(
                not isinstance(item, str)
                or not DESIGN_DECISION_ID_RE.fullmatch(item.strip())
                for item in decision_ids
            )
        ):
            _add_diagnostic(
                diagnostics,
                "ui-target-invalid-decisions",
                "ready UI target must carry canonical DS-* decision IDs",
                "manifest.decision_ids",
            )
        handoff_contract_ids = manifest.get("handoff_contract_ids")
        if (
            not isinstance(handoff_contract_ids, list)
            or not handoff_contract_ids
            or any(
                not isinstance(item, str)
                or not DESIGN_HANDOFF_ID_RE.fullmatch(item.strip())
                for item in handoff_contract_ids
            )
        ):
            _add_diagnostic(
                diagnostics,
                "ui-target-invalid-handoff-contracts",
                "ready UI target must carry canonical DH-* handoff contract IDs",
                "manifest.handoff_contract_ids",
            )
    return diagnostics


def scaffold_ui_target(
    out_path: Path,
    *,
    force: bool = False,
    template_path: Path | None = None,
) -> Path:
    """Copy the bundled feature-level UI target scaffold."""

    source = template_path or _locate_ui_target_template()
    if not source.is_file():
        raise DesignLintError(f"UI target template does not exist: {source}")
    if out_path.exists() and not force:
        raise DesignLintError(f"UI target already exists: {out_path}")
    diagnostics = lint_ui_target_file(source, level="structural")
    if diagnostics:
        messages = "; ".join(
            f"{diagnostic.code}: {diagnostic.message}"
            for diagnostic in diagnostics
        )
        raise DesignLintError(f"bundled UI target template is invalid: {messages}")
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(out_path, source.read_text(encoding="utf-8"))
    except OSError as exc:
        raise DesignLintError(f"cannot write UI target {out_path}: {exc}") from exc
    return out_path


def _locate_ui_target_template() -> Path:
    package_template = (
        Path(__file__).parent / "core_pack" / "templates" / "ui-target-template.html"
    )
    if package_template.is_file():
        return package_template
    return Path(__file__).parents[2] / "templates" / "ui-target-template.html"


def lint_design_file(path: Path, *, level: str = "structural") -> list[DesignDiagnostic]:
    level = level.lower()
    if level not in SUPPORTED_LINT_LEVELS:
        raise DesignLintError(f"unsupported design lint level: {level}")
    if not path.exists():
        return [DesignDiagnostic("missing-file", f"{path} does not exist", str(path))]
    if not path.is_file():
        return [DesignDiagnostic("read-error", f"{path} is not a file", str(path))]

    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [DesignDiagnostic("read-error", f"cannot read {path}: {exc}", str(path))]

    try:
        document = parse_design_markdown(text, source=str(path))
    except DesignLintError as exc:
        return [DesignDiagnostic("parse-error", str(exc), str(path))]
    except yaml.YAMLError as exc:
        return [DesignDiagnostic("parse-error", f"{path}: invalid YAML front matter: {exc}", str(path))]

    diagnostics: list[DesignDiagnostic] = []
    _validate_design_system(document, diagnostics)
    _validate_markdown_sections(document, diagnostics)
    _validate_token_references(document, diagnostics)
    if level == "ready":
        _validate_design_readiness(document, diagnostics)
    return diagnostics


def export_design_system(
    path: Path,
    *,
    export_format: str = "json",
    require_ready: bool = True,
) -> str:
    export_format = export_format.lower()
    if export_format not in SUPPORTED_EXPORT_FORMATS:
        raise DesignLintError(f"unsupported export format: {export_format}")

    diagnostics = lint_design_file(path, level="ready" if require_ready else "structural")
    if diagnostics:
        messages = "; ".join(f"{diagnostic.code}: {diagnostic.message}" for diagnostic in diagnostics)
        raise DesignLintError(messages)

    document = parse_design_markdown(path.read_text(encoding="utf-8"), source=str(path))
    if export_format == "json":
        payload = {
            "schema": document.design_system["schema"],
            "name": document.design_system.get("name"),
            "version": document.design_system.get("version"),
            "status": document.design_system.get("status"),
            "approval": document.design_system.get("approval", {}),
            "product_context": document.design_system.get("product_context", {}),
            "professional_skill_route": document.design_system.get(
                "professional_skill_route", {}
            ),
            "style_authority": document.design_system.get(
                "style_authority", {}
            ),
            "direction_contract": document.design_system.get("direction_contract", {}),
            "platforms": document.design_system.get("platforms", []),
            "capability_profiles": document.design_system.get(
                "capability_profiles", []
            ),
            "specimens": document.design_system.get("specimens", []),
            "tokens": document.design_system.get("tokens", {}),
            "color_modes": document.design_system.get("color_modes", {}),
            "components": document.design_system.get("components", {}),
            "responsive": document.design_system.get("responsive", {}),
            "content": document.design_system.get("content", {}),
            "decisions": document.design_system.get("decisions", []),
            "verification": document.design_system.get("verification", {}),
            "accessibility": document.design_system.get("accessibility", {}),
        }
        if "design_change" in document.front_matter:
            for key in (
                "id",
                "title",
                "change_type",
                "scope",
                "baseline_refs",
                "relationships",
                "constraints",
            ):
                payload[key] = document.design_system.get(key)
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"

    return json.dumps(_to_tailwind_theme(document.design_system), indent=2, sort_keys=True) + "\n"


def import_design_reference(
    source: str,
    *,
    out_dir: Path,
    notes: str = "",
    change_id: str | None = None,
    round_id: str | None = None,
) -> Path:
    if (change_id is None) != (round_id is None):
        raise DesignLintError(
            "design image import requires both change_id and round_id"
        )
    if change_id is not None and round_id is not None:
        return _import_design_image_round(
            source,
            design_root=out_dir,
            notes=notes,
            change_id=change_id,
            round_id=round_id,
        )

    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "references.md"
    source_line = source.strip()
    notes_line = notes.strip() or "No notes supplied."
    content = (
        "# Design References\n\n"
        "This file is input for `sp-design`. It is not an approved UI design change.\n\n"
        "## Imported Reference\n\n"
        f"- Source: {source_line}\n"
        f"- Notes: {notes_line}\n\n"
        "## Synthesis Instructions\n\n"
        "- Extract reusable design principles.\n"
        "- Remove brand-specific expression.\n"
        "- Write original scoped guidance into the change-local "
        "`design-change.md` only after user approval in `sp-design`.\n"
    )
    atomic_write_text(out_path, content)
    return out_path


def _import_design_image_round(
    source: str,
    *,
    design_root: Path,
    notes: str,
    change_id: str,
    round_id: str,
) -> Path:
    normalized_change = change_id.strip().upper()
    if not DESIGN_CHANGE_ID_RE.fullmatch(normalized_change):
        raise DesignLintError(
            "design image import change_id must use UD- followed by at least four digits"
        )
    normalized_round = _normalize_design_round(round_id)
    design_root = design_root.resolve()
    if design_root.name != "design" or design_root.parent.name != ".specify":
        raise DesignLintError(
            "design image import out_dir must be the project .specify/design directory"
        )
    project_root = design_root.parent.parent

    source_path = Path(source).expanduser().resolve()
    if not source_path.is_file():
        raise DesignLintError(
            f"design image import requires a regular source file: {source_path}"
        )
    try:
        if source_path.stat().st_size > MAX_DESIGN_IMAGE_IMPORT_BYTES:
            raise DesignLintError(
                "design image source exceeds the "
                f"{MAX_DESIGN_IMAGE_IMPORT_BYTES // (1024 * 1024)} MiB import limit"
            )
        with source_path.open("rb") as handle:
            image_bytes = handle.read(MAX_DESIGN_IMAGE_IMPORT_BYTES + 1)
    except DesignLintError:
        raise
    except OSError as exc:
        raise DesignLintError(f"cannot read design image source: {exc}") from exc
    if len(image_bytes) > MAX_DESIGN_IMAGE_IMPORT_BYTES:
        raise DesignLintError(
            "design image source exceeds the "
            f"{MAX_DESIGN_IMAGE_IMPORT_BYTES // (1024 * 1024)} MiB import limit"
        )
    diagnostics = _design_image_bytes_diagnostics(source_path, image_bytes)
    if diagnostics:
        messages = "; ".join(
            f"{diagnostic.code}: {diagnostic.message}" for diagnostic in diagnostics
        )
        raise DesignLintError(f"design image source is invalid: {messages}")

    index_path = design_root / "index.json"
    try:
        index = json.loads(index_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DesignLintError(f"cannot read design change index: {exc}") from exc
    if not isinstance(index, dict) or index.get("schema") != DESIGN_CHANGE_INDEX_SCHEMA:
        raise DesignLintError("design change index has an invalid schema")
    changes = index.get("changes")
    if not isinstance(changes, list):
        raise DesignLintError("design change index changes must be a list")
    record = next(
        (
            item
            for item in changes
            if isinstance(item, dict) and item.get("id") == normalized_change
        ),
        None,
    )
    if record is None:
        raise DesignLintError(f"design change {normalized_change} does not exist")
    if record.get("status") != "draft":
        raise DesignLintError(
            f"design change {normalized_change} is immutable; import into a new draft UD-* change"
        )

    workspace = design_root / "changes" / normalized_change
    design_path = workspace / "design-change.md"
    expected_design_ref = design_path.relative_to(project_root).as_posix()
    if record.get("design_ref") != expected_design_ref or not design_path.is_file():
        raise DesignLintError(
            f"design change {normalized_change} workspace is not canonical"
        )

    target = workspace / "previews" / (
        f"round-{normalized_round}{source_path.suffix.lower()}"
    )
    imported_ref = target.relative_to(project_root).as_posix()
    digest = hashlib.sha256(image_bytes).hexdigest()
    references_path = workspace / "references.md"
    notes_line = notes.strip() or "No notes supplied."
    references = (
        "# Design References\n\n"
        "This file is input for `sp-design`. It is not an approved UI design change.\n\n"
        "## Imported Reference\n\n"
        f"- Source: {source_path}\n"
        f"- Imported asset: {imported_ref}\n"
        f"- SHA-256: {digest}\n"
        f"- Notes: {notes_line}\n\n"
        "## Synthesis Instructions\n\n"
        "- Preserve the imported bytes as one immutable candidate round.\n"
        "- Bind the adjacent manifest and exact prompt only through `design approve` after explicit user approval.\n"
        "- Write original scoped guidance into the change-local `design-change.md` only after user approval in `sp-design`.\n"
    )

    expected_before: dict[Path, bytes | None] = {}
    updates: dict[Path, bytes] = {references_path: references.encode("utf-8")}
    try:
        existing = target.read_bytes()
    except FileNotFoundError:
        existing = None
        updates[target] = image_bytes
        expected_before[target] = None
    except OSError as exc:
        raise DesignLintError(f"cannot inspect design image target: {exc}") from exc
    else:
        if existing != image_bytes:
            raise DesignLintError(
                f"design image round already exists with different bytes: {imported_ref}"
            )
        if references_path.is_file():
            return target
        if references_path.exists():
            raise DesignLintError(
                "design reference target is not a regular file: "
                f"{references_path}"
            )
        expected_before[target] = existing

    try:
        apply_workflow_transaction(
            project_root,
            kind="design.import-image",
            updates=updates,
            expected_before=expected_before,
        )
    except WorkflowTransactionError as exc:
        raise DesignLintError(f"cannot import design image: {exc}") from exc
    return target


def _normalize_design_round(value: str) -> str:
    normalized = value.strip()
    if not re.fullmatch(r"[0-9]{1,4}", normalized):
        raise DesignLintError(
            "design image import round_id must be a positive integer with at most four digits"
        )
    round_number = int(normalized)
    if round_number < 1:
        raise DesignLintError("design image import round_id must be greater than zero")
    return f"{round_number:02d}"


def _load_professional_skill_catalog_refs() -> dict[str, str] | None:
    path = _locate_design_schema("ui-professional-skills/catalog.json")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if (
        not isinstance(payload, dict)
        or payload.get("catalog_id") != UI_PROFESSIONAL_SKILL_CATALOG
        or not isinstance(payload.get("skills"), list)
    ):
        return None
    refs: dict[str, str] = {}
    for raw_skill in payload["skills"]:
        if not isinstance(raw_skill, dict):
            return None
        skill_id = raw_skill.get("id")
        reference = raw_skill.get("ref")
        if (
            not isinstance(skill_id, str)
            or not skill_id
            or skill_id in refs
            or not isinstance(reference, str)
            or not reference
        ):
            return None
        refs[skill_id] = reference
    return refs


def _validate_professional_skill_route(
    design_system: dict[str, Any],
    diagnostics: list[DesignDiagnostic],
    *,
    ready: bool,
) -> None:
    route = design_system.get("professional_skill_route")
    if route is None:
        # Compatibility for already-approved contracts created before the
        # professional router existed. New scaffolds always include the field.
        return
    path = "design_system.professional_skill_route"
    if not isinstance(route, dict):
        _add_diagnostic(
            diagnostics,
            "invalid-professional-skill-route",
            "professional_skill_route must be a mapping",
            path,
        )
        return

    problems: list[str] = []
    if route.get("catalog_version") != UI_PROFESSIONAL_SKILL_CATALOG:
        problems.append(
            f"catalog_version must equal {UI_PROFESSIONAL_SKILL_CATALOG}"
        )
    status = str(route.get("status") or "").strip()
    if status not in {"unresolved", "question-required", "resolved"}:
        problems.append("status must be unresolved, question-required, or resolved")

    domain_id = route.get("domain_skill_id")
    if domain_id is not None and not (
        isinstance(domain_id, str) and domain_id.startswith("domain-")
    ):
        problems.append("domain_skill_id must be null or a domain-* ID")
    style_id = route.get("style_skill_id")
    if style_id is not None and not (
        isinstance(style_id, str) and style_id.startswith("style-")
    ):
        problems.append("style_skill_id must be null or a style-* ID")

    specialist_ids = route.get("specialist_skill_ids")
    if not (
        isinstance(specialist_ids, list)
        and len(specialist_ids) <= 2
        and len(specialist_ids) == len(set(specialist_ids))
        and all(
            isinstance(item, str) and item.startswith("specialist-")
            for item in specialist_ids
        )
    ):
        problems.append("specialist_skill_ids must contain zero to two unique specialist-* IDs")

    matched_signals = route.get("matched_signals")
    if not (
        isinstance(matched_signals, dict)
        and all(
            isinstance(skill_id, str)
            and isinstance(signals, list)
            and all(isinstance(signal, str) and signal.strip() for signal in signals)
            for skill_id, signals in matched_signals.items()
        )
    ):
        problems.append("matched_signals must map skill IDs to non-empty signal strings")

    loaded_refs = route.get("loaded_refs")
    if not (
        isinstance(loaded_refs, list)
        and len(loaded_refs) <= 4
        and len(loaded_refs) == len(set(loaded_refs))
        and all(isinstance(item, str) and item.strip() for item in loaded_refs)
    ):
        problems.append("loaded_refs must contain at most four unique references")

    unresolved = route.get("unresolved_candidates")
    if not (
        isinstance(unresolved, list)
        and len(unresolved) == len(set(unresolved))
        and all(isinstance(item, str) and item.strip() for item in unresolved)
    ):
        problems.append("unresolved_candidates must contain unique skill IDs")

    catalog_refs = _load_professional_skill_catalog_refs()
    if catalog_refs is None:
        problems.append("the UI professional skill catalog is unavailable or invalid")
    elif not problems:
        referenced_ids = [
            skill_id
            for skill_id in [domain_id, style_id, *specialist_ids, *unresolved]
            if isinstance(skill_id, str)
        ]
        referenced_ids.extend(matched_signals)
        unknown_ids = sorted(set(referenced_ids).difference(catalog_refs))
        if unknown_ids:
            problems.append(
                "route references unknown skill IDs: " + ", ".join(unknown_ids)
            )

    if problems:
        _add_diagnostic(
            diagnostics,
            "invalid-professional-skill-route",
            "; ".join(problems),
            path,
        )
        return

    if not ready:
        return
    expected_refs = 1 + (1 if style_id else 0) + len(specialist_ids)
    if isinstance(domain_id, str):
        selected_ids = [domain_id]
        if style_id:
            selected_ids.append(style_id)
        selected_ids.extend(specialist_ids)
        expected_loaded_refs = [catalog_refs[skill_id] for skill_id in selected_ids]
        if loaded_refs != expected_loaded_refs:
            _add_diagnostic(
                diagnostics,
                "professional-skill-route-ref-mismatch",
                "loaded_refs must exactly match the selected domain, style, "
                "and specialists",
                path + ".loaded_refs",
            )
    if (
        status != "resolved"
        or not isinstance(domain_id, str)
        or len(loaded_refs) != expected_refs
        or unresolved
    ):
        _add_diagnostic(
            diagnostics,
            "unresolved-professional-skill-route",
            "ready design must resolve one domain, optional one style, "
            "zero to two specialists, and the exact selected references",
            path,
        )


def _validate_style_authority(
    design_system: dict[str, Any],
    diagnostics: list[DesignDiagnostic],
    *,
    ready: bool,
) -> None:
    authority = design_system.get("style_authority")
    schema = design_system.get("schema")
    path = "design_system.style_authority"
    if authority is None:
        if schema == DESIGN_CHANGE_SCHEMA:
            _add_diagnostic(
                diagnostics,
                "invalid-style-authority",
                "current design changes require style_authority",
                path,
            )
        return
    expected_fields = {
        "mode",
        "scope_level",
        "source_refs",
        "protected_surfaces",
        "allowed_style_delta_surfaces",
        "authorization_source",
    }
    if not isinstance(authority, dict) or set(authority) != expected_fields:
        _add_diagnostic(
            diagnostics,
            "invalid-style-authority",
            "style_authority must contain the current exact fields",
            path,
        )
        return
    mode = str(authority.get("mode") or "").strip()
    scope_level_raw = authority.get("scope_level")
    scope_level = (
        str(scope_level_raw).strip() if scope_level_raw is not None else ""
    )
    problems: list[str] = []
    if mode not in {
        "unresolved",
        "greenfield",
        "inherit-existing",
        "page-overhaul-authorized",
    }:
        problems.append("mode is invalid")
    if scope_level not in {"", "feature-partial", "page"}:
        problems.append("scope_level must be null, feature-partial, or page")
    lists: dict[str, list[str]] = {}
    for field in (
        "source_refs",
        "protected_surfaces",
        "allowed_style_delta_surfaces",
    ):
        raw = authority.get(field)
        if not (
            isinstance(raw, list)
            and all(isinstance(item, str) and item.strip() for item in raw)
            and len(raw) == len(set(raw))
        ):
            problems.append(f"{field} must contain unique nonblank strings")
            lists[field] = []
        else:
            lists[field] = [item.strip() for item in raw]
    authorization = authority.get("authorization_source")
    if authorization is not None and not (
        isinstance(authorization, str) and authorization.strip()
    ):
        problems.append("authorization_source must be null or a nonblank string")
    if problems:
        _add_diagnostic(
            diagnostics,
            "invalid-style-authority",
            "; ".join(problems),
            path,
        )
        return
    if not ready:
        return

    violations: list[str] = []
    protected = set(lists["protected_surfaces"])
    allowed = set(lists["allowed_style_delta_surfaces"])
    baseline_guards = {"global-shell", "shared-components"}
    route = design_system.get("professional_skill_route")
    style_skill_id = route.get("style_skill_id") if isinstance(route, dict) else None
    change_type = str(design_system.get("change_type") or "").strip()
    scope = design_system.get("scope")
    declared_surfaces = {
        item.strip()
        for item in (scope.get("surfaces") if isinstance(scope, dict) else []) or []
        if isinstance(item, str) and item.strip()
    }
    if mode == "unresolved":
        violations.append("ready design must resolve style authority")
    elif mode == "greenfield":
        if schema == DESIGN_CHANGE_SCHEMA and change_type != "greenfield":
            violations.append("greenfield style authority requires change_type greenfield")
        if authorization is not None:
            violations.append("greenfield cannot claim overhaul authorization")
    elif mode == "inherit-existing":
        if scope_level != "feature-partial":
            violations.append("inherit-existing requires feature-partial scope")
        if not lists["source_refs"]:
            violations.append("inherit-existing requires live UI source_refs")
        if not baseline_guards <= protected:
            violations.append("inherit-existing must protect global-shell and shared-components")
        if allowed:
            violations.append("inherit-existing cannot allow a style delta")
        if authorization is not None:
            violations.append("inherit-existing cannot claim overhaul authorization")
        if style_skill_id is not None:
            violations.append("inherit-existing requires style_skill_id null")
    elif mode == "page-overhaul-authorized":
        if change_type != "overhaul":
            violations.append("page overhaul style authority requires change_type overhaul")
        if scope_level != "page":
            violations.append("page overhaul style authority requires page scope")
        if not lists["source_refs"]:
            violations.append("page overhaul requires live UI source_refs")
        if not baseline_guards <= protected:
            violations.append("page overhaul must protect global-shell and shared-components")
        if not allowed or not allowed <= declared_surfaces:
            violations.append("allowed style delta surfaces must be exact declared page surfaces")
        if allowed & baseline_guards:
            violations.append("global shell and shared components cannot be style delta surfaces")
        if not isinstance(authorization, str) or not authorization.strip():
            violations.append("page overhaul requires explicit authorization_source")
    if violations:
        _add_diagnostic(
            diagnostics,
            "style-authority-violation",
            "; ".join(violations),
            path,
        )


def _validate_design_system(document: DesignDocument, diagnostics: list[DesignDiagnostic]) -> None:
    design_system = document.design_system
    schema = design_system.get("schema")
    if schema not in {"spec-kit-design-v1", DESIGN_CHANGE_SCHEMA}:
        _add_diagnostic(
            diagnostics,
            "invalid-schema",
            "schema must equal spec-kit-ui-design-change-v1 or legacy spec-kit-design-v1",
            "design_change.schema",
        )
    if schema == DESIGN_CHANGE_SCHEMA:
        _validate_design_change_metadata(design_system, diagnostics)
        verification = design_system.get("verification")
        if not isinstance(verification, dict):
            _add_diagnostic(
                diagnostics,
                "missing-source-continuity",
                "design_change.verification must contain source_continuity",
                "design_change.verification.source_continuity",
            )
        else:
            continuity_result = validate_ui_source_continuity(
                verification.get("source_continuity"),
                require_ready=False,
            )
            for error in continuity_result.errors:
                _add_diagnostic(
                    diagnostics,
                    "invalid-source-continuity",
                    error.message,
                    "design_change.verification.source_continuity"
                    + error.path.removeprefix("$"),
                )

    _validate_professional_skill_route(design_system, diagnostics, ready=False)
    _validate_style_authority(design_system, diagnostics, ready=False)

    platforms = design_system.get("platforms")
    if not isinstance(platforms, list) or not platforms:
        _add_diagnostic(diagnostics, "invalid-platforms", "platforms must be a non-empty list", "design_system.platforms")

    tokens = design_system.get("tokens")
    if not isinstance(tokens, dict):
        _add_diagnostic(diagnostics, "invalid-tokens", "tokens must be a mapping", "design_system.tokens")
        tokens = {}

    for category in REQUIRED_TOKEN_CATEGORIES:
        if category not in tokens:
            _add_diagnostic(
                diagnostics,
                "missing-token-category",
                f"tokens must include {category}",
                f"design_system.tokens.{category}",
            )

    for category, entries in tokens.items():
        if not isinstance(category, str):
            _add_diagnostic(diagnostics, "invalid-token-category", "token category names must be strings", "design_system.tokens")
            continue
        if not isinstance(entries, dict):
            _add_diagnostic(
                diagnostics,
                "invalid-token-category",
                f"token category {category} must be a mapping",
                f"design_system.tokens.{category}",
            )
            continue
        for token_name, token_value in entries.items():
            token_path = f"design_system.tokens.{category}.{token_name}"
            if not isinstance(token_name, str) or not TOKEN_NAME_RE.match(token_name):
                _add_diagnostic(diagnostics, "invalid-token-name", f"invalid token name {token_name}", token_path)
            if not isinstance(token_value, dict):
                _add_diagnostic(diagnostics, "invalid-token", f"{category}.{token_name} must be a mapping", token_path)
                continue
            for key in ("value", "usage"):
                if key not in token_value:
                    _add_diagnostic(diagnostics, "invalid-token", f"{category}.{token_name} must include {key}", token_path)

    components = design_system.get("components")
    if not isinstance(components, dict):
        _add_diagnostic(diagnostics, "invalid-components", "components must be a mapping", "design_system.components")
        components = {}

    for component_name, component in components.items():
        component_path = f"design_system.components.{component_name}"
        if not isinstance(component, dict):
            _add_diagnostic(diagnostics, "invalid-component", f"{component_name} must be a mapping", component_path)
            continue
        states = component.get("required_states")
        if not isinstance(states, list) or not states:
            _add_diagnostic(
                diagnostics,
                "invalid-component-states",
                f"{component_name} required_states must be a non-empty list",
                f"{component_path}.required_states",
            )
        decision_refs = component.get("decision_refs")
        if decision_refs is not None and (
            not isinstance(decision_refs, list)
            or not all(isinstance(item, str) and item.strip() for item in decision_refs)
        ):
            _add_diagnostic(
                diagnostics,
                "invalid-component-decision-refs",
                f"{component_name} decision_refs must be a string list",
                f"{component_path}.decision_refs",
            )

    decisions = design_system.get("decisions")
    if decisions is not None and not isinstance(decisions, list):
        _add_diagnostic(
            diagnostics,
            "invalid-design-decisions",
            "decisions must be a list",
            "design_system.decisions",
        )
        decisions = []
    decision_ids: list[str] = []
    for index, decision in enumerate(decisions or []):
        path = f"design_system.decisions[{index}]"
        if not isinstance(decision, dict):
            _add_diagnostic(
                diagnostics,
                "invalid-design-decision",
                "each design decision must be a mapping",
                path,
            )
            continue
        decision_id = str(decision.get("id") or "").strip()
        decision_ids.append(decision_id)
        if "{{" not in decision_id and not re.fullmatch(
            r"DS-[A-Z0-9]+(?:-[A-Z0-9]+)+",
            decision_id,
        ):
            _add_diagnostic(
                diagnostics,
                "invalid-design-decision-id",
                "design decision IDs must use a stable DS-<KIND>-<NUMBER> form",
                f"{path}.id",
            )
        for field in ("kind", "statement", "source_ref", "verification"):
            if not str(decision.get(field) or "").strip():
                _add_diagnostic(
                    diagnostics,
                    "incomplete-design-decision",
                    f"design decision {decision_id or index + 1} must include {field}",
                    f"{path}.{field}",
                )
    if len(set(decision_ids)) != len(decision_ids):
        _add_diagnostic(
            diagnostics,
            "duplicate-design-decision-id",
            "design decision IDs must be unique",
            "design_system.decisions",
        )

    for field in ("color_modes", "responsive", "content", "verification"):
        value = design_system.get(field)
        if value is not None and not isinstance(value, dict):
            _add_diagnostic(
                diagnostics,
                f"invalid-{field.replace('_', '-')}",
                f"{field} must be a mapping",
                f"design_system.{field}",
            )

    accessibility = design_system.get("accessibility")
    if not isinstance(accessibility, dict):
        _add_diagnostic(
            diagnostics,
            "invalid-accessibility",
            "accessibility must be a mapping",
            "design_system.accessibility",
        )
        accessibility = {}

    for key in REQUIRED_ACCESSIBILITY_KEYS:
        if key not in accessibility:
            _add_diagnostic(
                diagnostics,
                "missing-accessibility-key",
                f"accessibility must include {key}",
                f"design_system.accessibility.{key}",
            )


def _validate_design_change_metadata(
    design_change: dict[str, Any],
    diagnostics: list[DesignDiagnostic],
) -> None:
    change_id = str(design_change.get("id") or "").strip()
    if not DESIGN_CHANGE_ID_RE.fullmatch(change_id):
        _add_diagnostic(
            diagnostics,
            "invalid-design-change-id",
            "design_change.id must use UD- followed by at least four digits",
            "design_change.id",
        )
    if not str(design_change.get("title") or "").strip():
        _add_diagnostic(
            diagnostics,
            "missing-design-change-title",
            "design_change.title must be non-empty",
            "design_change.title",
        )
    change_type = str(design_change.get("change_type") or "").strip().lower()
    if change_type not in SUPPORTED_DESIGN_CHANGE_TYPES:
        _add_diagnostic(
            diagnostics,
            "invalid-design-change-type",
            "design_change.change_type must be greenfield, preserve, overhaul, or extension",
            "design_change.change_type",
        )

    scope = design_change.get("scope")
    if not isinstance(scope, dict):
        _add_diagnostic(
            diagnostics,
            "invalid-design-change-scope",
            "design_change.scope must be a mapping",
            "design_change.scope",
        )
    else:
        surfaces = scope.get("surfaces")
        if (
            not isinstance(surfaces, list)
            or not surfaces
            or any(
                not isinstance(surface, str)
                or not DESIGN_CHANGE_SCOPE_RE.fullmatch(surface)
                for surface in surfaces
            )
        ):
            _add_diagnostic(
                diagnostics,
                "invalid-design-change-surfaces",
                "design_change.scope.surfaces must contain stable path-like identifiers",
                "design_change.scope.surfaces",
            )
        for field in ("entrypoints", "states", "platforms"):
            if not isinstance(scope.get(field), list):
                _add_diagnostic(
                    diagnostics,
                    "invalid-design-change-scope",
                    f"design_change.scope.{field} must be a list",
                    f"design_change.scope.{field}",
                )

    if not isinstance(design_change.get("baseline_refs"), list):
        _add_diagnostic(
            diagnostics,
            "invalid-design-change-baselines",
            "design_change.baseline_refs must be a list",
            "design_change.baseline_refs",
        )
    relationships = design_change.get("relationships")
    if not isinstance(relationships, dict):
        _add_diagnostic(
            diagnostics,
            "invalid-design-change-relationships",
            "design_change.relationships must be a mapping",
            "design_change.relationships",
        )
    else:
        for field in ("supersedes", "depends_on", "conflicts_with"):
            values = relationships.get(field)
            if not isinstance(values, list):
                _add_diagnostic(
                    diagnostics,
                    "invalid-design-change-relationships",
                    f"design_change.relationships.{field} must be a list",
                    f"design_change.relationships.{field}",
                )
        iteration_of = relationships.get("iteration_of")
        if iteration_of is not None and (
            not isinstance(iteration_of, str)
            or not DESIGN_CHANGE_ID_RE.fullmatch(iteration_of)
            or iteration_of == design_change.get("id")
        ):
            _add_diagnostic(
                diagnostics,
                "invalid-design-change-iteration",
                (
                    "design_change.relationships.iteration_of must be null or "
                    "a different canonical UD-* ID"
                ),
                "design_change.relationships.iteration_of",
            )
        elif isinstance(iteration_of, str) and iteration_of not in (
            relationships.get("supersedes") or []
        ):
            _add_diagnostic(
                diagnostics,
                "invalid-design-change-iteration",
                "an iteration source must also appear in relationships.supersedes",
                "design_change.relationships.iteration_of",
            )
    constraints = design_change.get("constraints")
    if not isinstance(constraints, dict):
        _add_diagnostic(
            diagnostics,
            "invalid-design-change-constraints",
            "design_change.constraints must be a mapping",
            "design_change.constraints",
        )
    else:
        for field in ("must_preserve", "may_adapt", "must_not"):
            if not isinstance(constraints.get(field), list):
                _add_diagnostic(
                    diagnostics,
                    "invalid-design-change-constraints",
                    f"design_change.constraints.{field} must be a list",
                    f"design_change.constraints.{field}",
                )


def _validate_markdown_sections(document: DesignDocument, diagnostics: list[DesignDiagnostic]) -> None:
    for section in REQUIRED_SECTIONS:
        if not re.search(rf"^##+\s+{re.escape(section)}\s*$", document.body, re.MULTILINE):
            _add_diagnostic(
                diagnostics,
                "missing-section",
                f"missing required Markdown section: {section}",
                section,
            )


def _validate_token_references(document: DesignDocument, diagnostics: list[DesignDiagnostic]) -> None:
    tokens = document.design_system.get("tokens", {})
    if not isinstance(tokens, dict):
        return

    known_refs = {
        (category, token_name)
        for category, entries in tokens.items()
        if isinstance(category, str) and isinstance(entries, dict)
        for token_name in entries
        if isinstance(token_name, str)
    }

    components = document.design_system.get("components", {})
    if not isinstance(components, dict):
        return

    for component_name, component in components.items():
        if not isinstance(component, dict):
            continue
        token_refs = component.get("token_refs", {})
        if not isinstance(token_refs, dict):
            _add_diagnostic(
                diagnostics,
                "invalid-token-reference",
                f"{component_name} token_refs must be a mapping of string token references",
                f"design_system.components.{component_name}.token_refs",
            )
            continue
        for ref_name, ref_value in token_refs.items():
            ref_path = f"design_system.components.{component_name}.token_refs.{ref_name}"
            if not isinstance(ref_value, str):
                _add_diagnostic(
                    diagnostics,
                    "invalid-token-reference",
                    f"token reference must be a string: {ref_name}",
                    ref_path,
                )
                continue
            match = TOKEN_REF_RE.fullmatch(ref_value)
            if not match:
                _add_diagnostic(
                    diagnostics,
                    "invalid-token-reference",
                    f"token reference must use {{category.token.name}} syntax: {ref_value}",
                    ref_path,
                )
                continue
            category, token_name = match.groups()
            if (category, token_name) not in known_refs:
                _add_diagnostic(
                    diagnostics,
                    "unknown-token-reference",
                    f"unknown token reference {{{category}.{token_name}}}",
                    ref_path,
                )


def _is_nonempty_string_list(value: Any) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and item.strip() for item in value)
    )


def _valid_design_interaction_script(
    value: Any,
    data_state_ids: set[str],
) -> bool:
    required_fields = {
        "preconditions",
        "start_state_id",
        "steps",
        "branches",
        "focus_checkpoint",
        "announcement_checkpoint",
        "completion_checkpoint",
        "recovery_checkpoint",
    }
    if not isinstance(value, dict) or set(value) != required_fields:
        return False
    steps = value.get("steps")
    branches = value.get("branches")
    allowed_conditions = {
        "success",
        "failure",
        "timeout",
        "cancel",
        "retry",
        "duplicate",
        "out_of_order",
    }
    seen_conditions: set[str] = set()
    valid_branches = isinstance(branches, list) and bool(branches)
    for branch in branches if isinstance(branches, list) else []:
        if (
            not isinstance(branch, dict)
            or set(branch)
            != {
                "conditions",
                "setup",
                "expected_state_id",
                "expected_feedback",
                "focus_behavior",
                "announcement",
                "continuation",
            }
            or not _is_nonempty_string_list(branch.get("conditions"))
        ):
            valid_branches = False
            continue
        conditions = set(branch.get("conditions") or [])
        if (
            not conditions <= allowed_conditions
            or conditions & seen_conditions
            or str(branch.get("expected_state_id") or "").strip()
            not in data_state_ids
            or any(
                not str(branch.get(field) or "").strip()
                for field in (
                    "setup",
                    "expected_feedback",
                    "focus_behavior",
                    "announcement",
                    "continuation",
                )
            )
        ):
            valid_branches = False
        seen_conditions.update(conditions)
    valid_branches = (
        valid_branches
        and "success" in seen_conditions
        and bool(seen_conditions & {"failure", "timeout", "cancel"})
        and bool(seen_conditions & {"retry", "duplicate", "out_of_order"})
    )
    return (
        _is_nonempty_string_list(value.get("preconditions"))
        and str(value.get("start_state_id") or "").strip() in data_state_ids
        and isinstance(steps, list)
        and bool(steps)
        and all(
            isinstance(step, dict)
            and set(step) == {"input", "action", "expected_feedback"}
            and all(
                str(step.get(field) or "").strip()
                for field in ("input", "action", "expected_feedback")
            )
            for step in steps
        )
        and valid_branches
        and all(
            str(value.get(field) or "").strip()
            for field in (
                "focus_checkpoint",
                "announcement_checkpoint",
                "completion_checkpoint",
                "recovery_checkpoint",
            )
        )
    )


DESIGN_INTERACTION_CONTRACT_FIELDS = {
    "id",
    "surface",
    "input",
    "trigger",
    "event_sequence",
    "immediate_feedback",
    "focus_behavior",
    "repeat_behavior",
    "cancellation_behavior",
    "pending_behavior",
    "decision_ids",
}


def _valid_design_interaction_contract(value: object) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == DESIGN_INTERACTION_CONTRACT_FIELDS
        and all(
            str(value.get(field) or "").strip()
            for field in DESIGN_INTERACTION_CONTRACT_FIELDS - {"decision_ids"}
        )
        and _is_nonempty_string_list(value.get("decision_ids"))
    )


DESIGN_EDITING_CONTRACT_FIELDS = {
    "id",
    "surface",
    "input_methods",
    "composition_behavior",
    "paste_autofill_behavior",
    "selection_caret_behavior",
    "formatting_behavior",
    "validation_timing",
    "validation_feedback",
    "dirty_state_behavior",
    "persistence_behavior",
    "undo_redo_behavior",
    "conflict_behavior",
    "read_only_disabled_behavior",
    "submission_behavior",
    "decision_ids",
}


def _valid_design_editing_contract(value: object) -> bool:
    return (
        isinstance(value, dict)
        and set(value) == DESIGN_EDITING_CONTRACT_FIELDS
        and _is_nonempty_string_list(value.get("input_methods"))
        and all(
            str(value.get(field) or "").strip()
            for field in DESIGN_EDITING_CONTRACT_FIELDS
            - {"input_methods", "decision_ids"}
        )
        and _is_nonempty_string_list(value.get("decision_ids"))
    )


def _validate_design_professional_verification(
    verification: dict[str, Any],
    *,
    decision_ids: list[str],
    handoff_contract_ids: list[str],
    immutable_handoff: dict[str, Any] | None,
    diagnostics: list[DesignDiagnostic],
) -> None:
    """Validate and, when available, byte-projection-bind professional UI rows."""

    known_decisions = set(decision_ids)
    frozen_contract_ids = set(handoff_contract_ids)
    seen_contract_ids: set[str] = set()
    required_strings = {
        "interaction_matrix": tuple(
            sorted(DESIGN_INTERACTION_CONTRACT_FIELDS - {"id", "decision_ids"})
        ),
        "editing_matrix": tuple(
            sorted(
                DESIGN_EDITING_CONTRACT_FIELDS
                - {"id", "input_methods", "decision_ids"}
            )
        ),
        "data_state_matrix": (
            "surface",
            "state",
            "data_condition",
            "expectation",
        ),
        "accessibility_matrix": (
            "surface",
            "reading_order",
            "focus_order",
            "target_size",
            "contrast",
            "zoom_reflow",
        ),
        "navigation_matrix": (
            "surface",
            "entry",
            "destination",
            "trigger",
            "back_behavior",
            "deep_link_behavior",
            "interruption_recovery",
        ),
        "content_matrix": (
            "surface",
            "state",
            "purpose",
            "copy",
            "primary_action",
            "trust_requirement",
            "localization",
        ),
    }
    required_lists = {
        "editing_matrix": ("input_methods",),
        "accessibility_matrix": (
            "semantics",
            "keyboard",
            "announcements",
            "alternatives",
        ),
        "content_matrix": ("content_limits",),
    }
    for field in DESIGN_EXPERIENCE_GRAPH_FIELDS:
        rows = verification.get(field)
        if not isinstance(rows, list) or not rows:
            _add_diagnostic(
                diagnostics,
                "missing-design-professional-contract",
                f"verification.{field} must be a non-empty list",
                f"design_change.verification.{field}",
            )
            continue
        for index, row in enumerate(rows):
            path = f"design_change.verification.{field}[{index}]"
            if not isinstance(row, dict):
                _add_diagnostic(
                    diagnostics,
                    "invalid-design-professional-contract",
                    f"verification.{field} rows must be mappings",
                    path,
                )
                continue
            contract_id = str(row.get("id") or "").strip()
            referenced_decisions = row.get("decision_ids")
            if (
                not DESIGN_HANDOFF_ID_RE.fullmatch(contract_id)
                or contract_id in seen_contract_ids
                or (frozen_contract_ids and contract_id not in frozen_contract_ids)
            ):
                _add_diagnostic(
                    diagnostics,
                    "invalid-design-professional-contract-id",
                    "surface/scenario IDs must be unique frozen DH-* contracts",
                    f"{path}.id",
                )
            seen_contract_ids.add(contract_id)
            valid = _is_nonempty_string_list(referenced_decisions) and set(
                referenced_decisions or []
            ) <= known_decisions
            if field == "surface_catalog":
                valid = valid and all(
                    str(row.get(name) or "").strip()
                    for name in ("profile_id", "name", "kind", "entrypoint_id")
                ) and all(
                    _is_nonempty_string_list(row.get(name))
                    for name in ("source_refs", "specimen_ids", "component_ids")
                )
            else:
                valid = (
                    valid
                    and bool(str(row.get("surface_id") or "").strip())
                    and bool(str(row.get("name") or "").strip())
                    and row.get("risk") in {"low", "medium", "high"}
                    and row.get("required") is True
                    and _valid_design_interaction_script(
                        row.get("interaction_script"),
                        {
                            str(item).strip()
                            for item in row.get("data_state_ids") or []
                            if isinstance(item, str) and item.strip()
                        },
                    )
                    and all(
                        _is_nonempty_string_list(row.get(name))
                        for name in (
                            "interaction_ids",
                            "editing_ids",
                            "data_state_ids",
                            "accessibility_ids",
                            "navigation_ids",
                            "content_ids",
                            "responsive_ids",
                            "motion_transition_ids",
                        )
                    )
                )
            if not valid:
                _add_diagnostic(
                    diagnostics,
                    "incomplete-design-professional-contract",
                    f"verification.{field} row is missing executable graph fields",
                    path,
                )
    for field in DESIGN_PROFESSIONAL_MATRIX_FIELDS:
        rows = verification.get(field)
        if not isinstance(rows, list) or not rows:
            _add_diagnostic(
                diagnostics,
                "missing-design-professional-contract",
                f"verification.{field} must be a non-empty list",
                f"design_change.verification.{field}",
            )
            continue
        for index, row in enumerate(rows):
            path = f"design_change.verification.{field}[{index}]"
            if not isinstance(row, dict):
                _add_diagnostic(
                    diagnostics,
                    "invalid-design-professional-contract",
                    f"verification.{field} rows must be mappings",
                    path,
                )
                continue
            contract_id = str(row.get("id") or "").strip()
            if (
                not DESIGN_HANDOFF_ID_RE.fullmatch(contract_id)
                or contract_id in seen_contract_ids
                or (frozen_contract_ids and contract_id not in frozen_contract_ids)
            ):
                _add_diagnostic(
                    diagnostics,
                    "invalid-design-professional-contract-id",
                    "professional matrix IDs must be unique frozen DH-* contracts",
                    f"{path}.id",
                )
            seen_contract_ids.add(contract_id)
            referenced_decisions = row.get("decision_ids")
            if not _is_nonempty_string_list(referenced_decisions) or not set(
                referenced_decisions or []
            ) <= known_decisions:
                _add_diagnostic(
                    diagnostics,
                    "invalid-design-professional-decision-binding",
                    "professional matrix decision_ids must reference approved DS-* decisions",
                    f"{path}.decision_ids",
                )
            if any(
                not str(row.get(name) or "").strip()
                for name in required_strings[field]
            ) or any(
                not _is_nonempty_string_list(row.get(name))
                for name in required_lists.get(field, ())
            ) or (
                field == "interaction_matrix"
                and not _valid_design_interaction_contract(row)
            ) or (
                field == "editing_matrix"
                and not _valid_design_editing_contract(row)
            ):
                _add_diagnostic(
                    diagnostics,
                    "incomplete-design-professional-contract",
                    f"verification.{field} row is missing executable fields",
                    path,
                )

    motion = verification.get("motion_contract")
    if not isinstance(motion, dict):
        _add_diagnostic(
            diagnostics,
            "missing-design-professional-contract",
            "verification.motion_contract must be a mapping",
            "design_change.verification.motion_contract",
        )
    else:
        transitions = motion.get("transitions")
        transitions = transitions if isinstance(transitions, list) else []
        timing = motion.get("feedback_timing")
        timing = timing if isinstance(timing, dict) else {}
        immediate = timing.get("immediate_ms")
        progress = timing.get("progress_ms")
        timeout = timing.get("timeout_ms")
        if (
            not str(motion.get("purpose") or "").strip()
            or not str(motion.get("reduced_motion") or "").strip()
            or not transitions
            or isinstance(immediate, bool)
            or not isinstance(immediate, int)
            or immediate < 0
            or isinstance(progress, bool)
            or not isinstance(progress, int)
            or progress <= 0
            or isinstance(timeout, bool)
            or not isinstance(timeout, int)
            or timeout <= progress
        ):
            _add_diagnostic(
                diagnostics,
                "incomplete-design-professional-contract",
                "verification.motion_contract requires purpose, transitions, reduced motion, and ordered feedback timing",
                "design_change.verification.motion_contract",
            )
        for index, transition in enumerate(transitions):
            path = f"design_change.verification.motion_contract.transitions[{index}]"
            if not isinstance(transition, dict):
                _add_diagnostic(
                    diagnostics,
                    "invalid-design-professional-contract",
                    "motion transitions must be mappings",
                    path,
                )
                continue
            contract_id = str(transition.get("id") or "").strip()
            referenced_decisions = transition.get("decision_ids")
            duration = transition.get("duration_ms")
            if (
                not DESIGN_HANDOFF_ID_RE.fullmatch(contract_id)
                or contract_id in seen_contract_ids
                or (frozen_contract_ids and contract_id not in frozen_contract_ids)
            ):
                _add_diagnostic(
                    diagnostics,
                    "invalid-design-professional-contract-id",
                    "motion transition IDs must be unique frozen DH-* contracts",
                    f"{path}.id",
                )
            seen_contract_ids.add(contract_id)
            if not _is_nonempty_string_list(referenced_decisions) or not set(
                referenced_decisions or []
            ) <= known_decisions:
                _add_diagnostic(
                    diagnostics,
                    "invalid-design-professional-decision-binding",
                    "motion transition decision_ids must reference approved DS-* decisions",
                    f"{path}.decision_ids",
                )
            if (
                any(
                    not str(transition.get(name) or "").strip()
                    for name in (
                        "surface",
                        "trigger",
                        "response",
                        "easing",
                        "interrupt_behavior",
                    )
                )
                or isinstance(duration, bool)
                or not isinstance(duration, int)
                or duration < 0
            ):
                _add_diagnostic(
                    diagnostics,
                    "incomplete-design-professional-contract",
                    "motion transition is missing executable timing or interruption fields",
                    path,
                )

    usability = verification.get("usability_validation")
    if not isinstance(usability, dict):
        _add_diagnostic(
            diagnostics,
            "missing-design-professional-contract",
            "verification.usability_validation must be a mapping",
            "design_change.verification.usability_validation",
        )
    else:
        risk = usability.get("risk_level")
        human_review = usability.get("human_review_required")
        if (
            risk not in {"low", "medium", "high"}
            or any(
                not _is_nonempty_string_list(usability.get(field))
                for field in ("methods", "critical_tasks", "success_criteria")
            )
            or not isinstance(human_review, bool)
        ):
            _add_diagnostic(
                diagnostics,
                "incomplete-design-professional-contract",
                "verification.usability_validation requires risk, methods, tasks, success criteria, and human-review decision",
                "design_change.verification.usability_validation",
            )
        if risk == "high" and human_review is not True:
            _add_diagnostic(
                diagnostics,
                "design-high-risk-human-review-required",
                "high-risk usability validation must require human review",
                "design_change.verification.usability_validation.human_review_required",
            )

    if immutable_handoff is not None:
        for field in DESIGN_PROFESSIONAL_FIELDS:
            if verification.get(field) != immutable_handoff.get(field):
                _add_diagnostic(
                    diagnostics,
                    "design-professional-contract-drift",
                    f"verification.{field} must exactly match the immutable approved handoff",
                    f"design_change.verification.{field}",
                )


def _validate_approved_visual_reference(
    document: DesignDocument,
    approval: dict[str, Any],
    diagnostics: list[DesignDiagnostic],
) -> None:
    visual_refs = approval.get("visual_refs")
    if not isinstance(visual_refs, list):
        return
    local_refs = [
        item.strip()
        for item in visual_refs
        if isinstance(item, str)
        and item.strip()
        and "://" not in item
        and "#" in item
    ]
    if not local_refs:
        _add_diagnostic(
            diagnostics,
            "missing-local-approved-preview",
            "approved UI design requires a local immutable HTML or image round reference",
            "design_system.approval.visual_refs",
        )
        return

    source_path = Path(document.source)
    source_root = source_path.parent
    resolved = False
    for visual_ref in local_refs:
        preview_ref, _, direction_id = visual_ref.partition("#")
        suffix = Path(preview_ref).suffix.lower()
        if suffix not in ({".html"} | DESIGN_IMAGE_SUFFIXES) or not direction_id:
            continue
        preview_path = (source_root / preview_ref).resolve(strict=False)
        if not preview_path.is_file():
            _add_diagnostic(
                diagnostics,
                "approved-preview-missing",
                f"approved visual reference does not exist: {visual_ref}",
                "design_system.approval.visual_refs",
            )
            continue
        preview_diagnostics = (
            lint_design_preview_file(preview_path, level="ready")
            if suffix == ".html"
            else lint_design_image_bundle(preview_path, level="ready")
        )
        if preview_diagnostics:
            _add_diagnostic(
                diagnostics,
                "approved-preview-invalid",
                (
                    f"approved visual reference is not a valid immutable preview: "
                    f"{preview_diagnostics[0].code}: {preview_diagnostics[0].message}"
                ),
                visual_ref,
            )
            continue
        sidecar_path = design_preview_approval_path(preview_path)
        try:
            sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            _add_diagnostic(
                diagnostics,
                "approved-preview-sidecar-invalid",
                f"cannot read approved preview sidecar: {exc}",
                str(sidecar_path),
            )
            continue
        expected = {
            "direction": direction_id,
            "preview_sha256": (
                sidecar.get("html_sha256")
                if suffix == ".html"
                else sidecar.get("image_sha256")
            ),
            "manifest_sha256": sidecar.get("manifest_sha256"),
            "review_round": str(sidecar.get("review_round") or "").strip(),
            "handoff_sha256": sidecar.get("handoff_sha256"),
        }
        if str(sidecar.get("direction_id") or "").strip() != direction_id:
            _add_diagnostic(
                diagnostics,
                "approved-direction-reference-mismatch",
                "approved visual reference fragment must equal the preview sidecar direction",
                "design_system.approval.visual_refs",
            )
        if str(approval.get("direction") or "").strip() != expected["direction"]:
            _add_diagnostic(
                diagnostics,
                "approved-direction-reference-mismatch",
                "approval.direction must equal the approved visual reference fragment",
                "design_system.approval.direction",
            )
        for field in ("preview_sha256", "manifest_sha256"):
            value = str(approval.get(field) or "").strip()
            if value != expected[field]:
                _add_diagnostic(
                    diagnostics,
                    "approved-preview-digest-mismatch",
                    f"approval.{field} must match the immutable preview sidecar",
                    f"design_system.approval.{field}",
                )
        if suffix != ".html":
            for field in ("visual_medium", "prompt_sha256", "inspection_owner"):
                value = str(approval.get(field) or "").strip()
                if value != str(sidecar.get(field) or "").strip():
                    _add_diagnostic(
                        diagnostics,
                        "approved-image-provenance-mismatch",
                        f"approval.{field} must match the immutable image approval sidecar",
                        f"design_system.approval.{field}",
                    )
            prompt_ref = str(approval.get("prompt_ref") or "").strip()
            expected_prompt_path = preview_path.with_suffix(".prompt.md").resolve(
                strict=False
            )
            resolved_prompt_path = (
                (source_root / prompt_ref).resolve(strict=False)
                if prompt_ref
                else None
            )
            if resolved_prompt_path != expected_prompt_path:
                _add_diagnostic(
                    diagnostics,
                    "approved-image-prompt-reference-mismatch",
                    "approval.prompt_ref must identify the exact adjacent image-generation prompt",
                    "design_system.approval.prompt_ref",
                )
        handoff_ref = str(approval.get("handoff_ref") or "").strip()
        if not handoff_ref or not handoff_ref.lower().endswith(".handoff.json"):
            _add_diagnostic(
                diagnostics,
                "missing-approved-handoff-reference",
                "design_system.approval.handoff_ref must identify the immutable design handoff",
                "design_system.approval.handoff_ref",
            )
        handoff_sha256 = str(approval.get("handoff_sha256") or "").strip()
        if not re.fullmatch(r"[0-9a-f]{64}", handoff_sha256):
            _add_diagnostic(
                diagnostics,
                "missing-approved-handoff-digest",
                "design_system.approval.handoff_sha256 must be a SHA-256 digest",
                "design_system.approval.handoff_sha256",
            )
        if str(approval.get("review_round") or "").strip() != expected["review_round"]:
            _add_diagnostic(
                diagnostics,
                "approved-review-round-mismatch",
                "approval.review_round must match the immutable preview sidecar",
                "design_system.approval.review_round",
            )
        approval_decisions = approval.get("decision_ids")
        if approval_decisions != sidecar.get("decision_ids"):
            _add_diagnostic(
                diagnostics,
                "approved-decision-set-mismatch",
                "approval.decision_ids must exactly match the approved preview sidecar",
                "design_system.approval.decision_ids",
            )
        if approval.get("handoff_contract_ids") != sidecar.get(
            "handoff_contract_ids"
        ):
            _add_diagnostic(
                diagnostics,
                "approved-handoff-contract-set-mismatch",
                "approval.handoff_contract_ids must exactly match the approved preview sidecar",
                "design_system.approval.handoff_contract_ids",
            )
        for field in ("capability_profile_ids", "specimen_ids"):
            if approval.get(field) != sidecar.get(field):
                _add_diagnostic(
                    diagnostics,
                    "approved-capability-set-mismatch",
                    f"approval.{field} must exactly match the approved preview sidecar",
                    f"design_system.approval.{field}",
                )
        handoff_ref = str(approval.get("handoff_ref") or "").strip()
        expected_handoff_path = design_preview_handoff_path(preview_path).resolve(
            strict=False
        )
        resolved_handoff_path = (
            (source_root / handoff_ref).resolve(strict=False)
            if handoff_ref
            else None
        )
        if resolved_handoff_path != expected_handoff_path:
            _add_diagnostic(
                diagnostics,
                "approved-handoff-reference-mismatch",
                "approval.handoff_ref must identify the handoff frozen beside the approved preview",
                "design_system.approval.handoff_ref",
            )
        elif not expected_handoff_path.is_file():
            _add_diagnostic(
                diagnostics,
                "approved-handoff-missing",
                f"approved handoff does not exist: {handoff_ref}",
                "design_system.approval.handoff_ref",
            )
        else:
            try:
                handoff_bytes = expected_handoff_path.read_bytes()
                actual_handoff_sha256 = _sha256_bytes(handoff_bytes)
            except OSError as exc:
                _add_diagnostic(
                    diagnostics,
                    "approved-handoff-unreadable",
                    f"cannot read approved handoff: {exc}",
                    "design_system.approval.handoff_ref",
                )
            else:
                if str(approval.get("handoff_sha256") or "").strip() != str(
                    expected["handoff_sha256"] or ""
                ) or actual_handoff_sha256 != str(
                    expected["handoff_sha256"] or ""
                ):
                    _add_diagnostic(
                        diagnostics,
                        "approved-handoff-digest-mismatch",
                        "approval.handoff_sha256 and handoff bytes must match the immutable preview sidecar",
                        "design_system.approval.handoff_sha256",
                    )
                if document.design_system.get("schema") == DESIGN_CHANGE_SCHEMA:
                    try:
                        handoff_payload = json.loads(handoff_bytes.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                        _add_diagnostic(
                            diagnostics,
                            "approved-handoff-unreadable",
                            f"cannot parse approved handoff: {exc}",
                            "design_system.approval.handoff_ref",
                        )
                    else:
                        reproduction = (
                            handoff_payload.get("reproduction")
                            if isinstance(handoff_payload, dict)
                            else None
                        )
                        verification = document.design_system.get("verification")
                        if isinstance(reproduction, dict) and isinstance(
                            verification, dict
                        ):
                            _validate_design_professional_verification(
                                verification,
                                decision_ids=[
                                    str(item)
                                    for item in approval.get("decision_ids") or []
                                    if isinstance(item, str) and item.strip()
                                ],
                                handoff_contract_ids=[
                                    str(item)
                                    for item in approval.get("handoff_contract_ids")
                                    or []
                                    if isinstance(item, str) and item.strip()
                                ],
                                immutable_handoff=reproduction,
                                diagnostics=diagnostics,
                            )
        resolved = True
        break
    if not resolved and not any(
        item.code.startswith("approved-preview") for item in diagnostics
    ):
        _add_diagnostic(
            diagnostics,
            "approved-preview-unresolved",
            "no approved visual reference resolves to an immutable preview direction",
            "design_system.approval.visual_refs",
        )


def _validate_design_readiness(document: DesignDocument, diagnostics: list[DesignDiagnostic]) -> None:
    design_system = document.design_system
    _validate_professional_skill_route(design_system, diagnostics, ready=True)
    _validate_style_authority(design_system, diagnostics, ready=True)
    status = str(design_system.get("status") or "").strip().lower()
    if status != "approved":
        _add_diagnostic(
            diagnostics,
            "design-not-approved",
            "design_system.status must equal approved for downstream UI work",
            "design_system.status",
        )

    approval = design_system.get("approval")
    if not isinstance(approval, dict):
        _add_diagnostic(
            diagnostics,
            "missing-design-approval",
            "design_system.approval must record the approved direction and source references",
            "design_system.approval",
        )
    else:
        if str(approval.get("status") or "").strip().lower() != "approved":
            _add_diagnostic(
                diagnostics,
                "missing-design-approval",
                "design_system.approval.status must equal approved",
                "design_system.approval.status",
            )
        direction = str(approval.get("direction") or "").strip()
        if not direction or "{{" in direction or "}}" in direction:
            _add_diagnostic(
                diagnostics,
                "missing-approved-direction",
                "design_system.approval.direction must name the selected project-specific direction",
                "design_system.approval.direction",
            )
        source_refs = approval.get("source_refs")
        if (
            not isinstance(source_refs, list)
            or not source_refs
            or not all(isinstance(item, str) and item.strip() for item in source_refs)
        ):
            _add_diagnostic(
                diagnostics,
                "missing-design-provenance",
                "design_system.approval.source_refs must identify product or repository evidence",
                "design_system.approval.source_refs",
            )
        visual_refs = approval.get("visual_refs")
        if (
            not isinstance(visual_refs, list)
            or not visual_refs
            or not all(isinstance(item, str) and item.strip() for item in visual_refs)
        ):
            _add_diagnostic(
                diagnostics,
                "missing-approved-visual-reference",
                "design_system.approval.visual_refs must identify the exact inspectable artifact approved by the user",
                "design_system.approval.visual_refs",
            )
        for field in ("preview_sha256", "manifest_sha256"):
            value = str(approval.get(field) or "").strip()
            if not re.fullmatch(r"[0-9a-f]{64}", value):
                _add_diagnostic(
                    diagnostics,
                    "missing-approved-preview-digest",
                    f"design_system.approval.{field} must be a SHA-256 digest",
                    f"design_system.approval.{field}",
                )
        review_round = approval.get("review_round")
        if review_round in {None, ""}:
            _add_diagnostic(
                diagnostics,
                "missing-approved-review-round",
                "design_system.approval.review_round must identify the approved round",
                "design_system.approval.review_round",
            )
        decision_ids = approval.get("decision_ids")
        if not isinstance(decision_ids, list) or not decision_ids or not all(
            isinstance(item, str) and item.strip() for item in decision_ids
        ):
            _add_diagnostic(
                diagnostics,
                "missing-approved-decision-ids",
                "design_system.approval.decision_ids must freeze the approved DS-* set",
                "design_system.approval.decision_ids",
            )
        handoff_contract_ids = approval.get("handoff_contract_ids")
        if (
            not isinstance(handoff_contract_ids, list)
            or not handoff_contract_ids
            or any(
                not isinstance(item, str)
                or not DESIGN_HANDOFF_ID_RE.fullmatch(item.strip())
                for item in handoff_contract_ids
            )
        ):
            _add_diagnostic(
                diagnostics,
                "missing-approved-handoff-contract-ids",
                "design_system.approval.handoff_contract_ids must freeze the approved DH-* set",
                "design_system.approval.handoff_contract_ids",
            )
        capability_profile_ids = approval.get("capability_profile_ids")
        if (
            not isinstance(capability_profile_ids, list)
            or not capability_profile_ids
            or any(
                not isinstance(item, str)
                or not re.fullmatch(r"[a-z][a-z0-9-]*", item.strip())
                for item in capability_profile_ids
            )
        ):
            _add_diagnostic(
                diagnostics,
                "missing-approved-capability-profiles",
                "design_system.approval.capability_profile_ids must freeze the approved profile set",
                "design_system.approval.capability_profile_ids",
            )
        specimen_ids = approval.get("specimen_ids")
        if (
            not isinstance(specimen_ids, list)
            or not specimen_ids
            or any(
                not isinstance(item, str)
                or not DESIGN_SPECIMEN_ID_RE.fullmatch(item.strip())
                for item in specimen_ids
            )
        ):
            _add_diagnostic(
                diagnostics,
                "missing-approved-specimens",
                "design_system.approval.specimen_ids must freeze the approved specimen set",
                "design_system.approval.specimen_ids",
            )
        if design_system.get("capability_profiles") != capability_profile_ids:
            _add_diagnostic(
                diagnostics,
                "design-capability-profile-drift",
                "design_system.capability_profiles must exactly match approval.capability_profile_ids",
                "design_system.capability_profiles",
            )
        if design_system.get("specimens") != specimen_ids:
            _add_diagnostic(
                diagnostics,
                "design-specimen-drift",
                "design_system.specimens must exactly match approval.specimen_ids",
                "design_system.specimens",
            )
        _validate_approved_visual_reference(document, approval, diagnostics)

    product_context = design_system.get("product_context")
    if not isinstance(product_context, dict):
        _add_diagnostic(
            diagnostics,
            "missing-product-context",
            "approved design system must define product_context",
            "design_system.product_context",
        )
    else:
        for field in ("subject", "audience", "single_job"):
            if not str(product_context.get(field) or "").strip():
                _add_diagnostic(
                    diagnostics,
                    "incomplete-product-context",
                    f"product_context.{field} must be non-empty",
                    f"design_system.product_context.{field}",
                )

    direction_contract = design_system.get("direction_contract")
    if not isinstance(direction_contract, dict):
        _add_diagnostic(
            diagnostics,
            "missing-direction-contract",
            "approved design system must define direction_contract",
            "design_system.direction_contract",
        )
    else:
        for field in (
            "visual_thesis",
            "content_thesis",
            "interaction_thesis",
            "signature_element",
        ):
            if not str(direction_contract.get(field) or "").strip():
                _add_diagnostic(
                    diagnostics,
                    "incomplete-direction-contract",
                    f"direction_contract.{field} must be non-empty",
                    f"design_system.direction_contract.{field}",
                )
        for field in ("safe_system_choices", "creative_risks"):
            if not isinstance(direction_contract.get(field), list):
                _add_diagnostic(
                    diagnostics,
                    "invalid-direction-contract-list",
                    f"direction_contract.{field} must be a list",
                    f"design_system.direction_contract.{field}",
                )

    name = str(design_system.get("name") or "").strip().lower()
    if not name or name in {"project-design-system", "bootstrap-design-seed"} or "{{" in name:
        _add_diagnostic(
            diagnostics,
            "generic-design-name",
            "design_system.name must be project-specific before downstream UI work",
            "design_system.name",
        )

    components = design_system.get("components")
    if not isinstance(components, dict) or not components:
        _add_diagnostic(
            diagnostics,
            "missing-ready-components",
            "an approved design system must define at least one applicable component contract",
            "design_system.components",
        )

    tokens = design_system.get("tokens")
    if isinstance(tokens, dict):
        for category in REQUIRED_TOKEN_CATEGORIES:
            values = tokens.get(category)
            if not isinstance(values, dict) or not values:
                _add_diagnostic(
                    diagnostics,
                    "missing-ready-token-values",
                    f"approved design system must define {category} tokens",
                    f"design_system.tokens.{category}",
                )

    decisions = design_system.get("decisions")
    canonical_decision_ids = [
        str(item.get("id") or "").strip()
        for item in decisions or []
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    ] if isinstance(decisions, list) else []
    if not canonical_decision_ids:
        _add_diagnostic(
            diagnostics,
            "missing-ready-decisions",
            "approved design system must define stable DS-* decisions",
            "design_system.decisions",
        )
    elif isinstance(approval, dict) and approval.get("decision_ids") != canonical_decision_ids:
        _add_diagnostic(
            diagnostics,
            "design-decision-approval-mismatch",
            "design_system decisions must exactly match approval.decision_ids in order",
            "design_system.decisions",
        )

    for component_name, component in (
        components.items() if isinstance(components, dict) else []
    ):
        if not isinstance(component, dict):
            continue
        decision_refs = component.get("decision_refs")
        if not isinstance(decision_refs, list) or not decision_refs:
            _add_diagnostic(
                diagnostics,
                "missing-component-decision-refs",
                f"component {component_name} must map to approved DS-* decisions",
                f"design_system.components.{component_name}.decision_refs",
            )
        elif not set(decision_refs) <= set(canonical_decision_ids):
            _add_diagnostic(
                diagnostics,
                "unknown-component-decision-ref",
                f"component {component_name} decision_refs must exist in design_system.decisions",
                f"design_system.components.{component_name}.decision_refs",
            )

    color_modes = design_system.get("color_modes")
    if not isinstance(color_modes, dict) or not color_modes:
        _add_diagnostic(
            diagnostics,
            "missing-color-modes",
            "approved design system must define applicable color_modes",
            "design_system.color_modes",
        )

    responsive = design_system.get("responsive")
    if not isinstance(responsive, dict):
        _add_diagnostic(
            diagnostics,
            "missing-responsive-contract",
            "approved design system must define responsive rules",
            "design_system.responsive",
        )
    else:
        if not isinstance(responsive.get("breakpoints"), dict):
            _add_diagnostic(
                diagnostics,
                "invalid-responsive-breakpoints",
                "responsive.breakpoints must be a mapping",
                "design_system.responsive.breakpoints",
            )
        if not isinstance(responsive.get("adaptations"), list):
            _add_diagnostic(
                diagnostics,
                "invalid-responsive-adaptations",
                "responsive.adaptations must be a list",
                "design_system.responsive.adaptations",
            )

    content_contract = design_system.get("content")
    if not isinstance(content_contract, dict):
        _add_diagnostic(
            diagnostics,
            "missing-content-contract",
            "approved design system must define content and imagery rules",
            "design_system.content",
        )
    else:
        for field in ("voice_rules", "real_content_sources", "imagery_rules"):
            if not isinstance(content_contract.get(field), list):
                _add_diagnostic(
                    diagnostics,
                    "invalid-content-contract",
                    f"content.{field} must be a list",
                    f"design_system.content.{field}",
                )

    verification = design_system.get("verification")
    if not isinstance(verification, dict):
        _add_diagnostic(
            diagnostics,
            "missing-design-verification",
            "approved design system must define verification requirements",
            "design_system.verification",
        )
    else:
        continuity_result = validate_ui_source_continuity(
            verification.get("source_continuity"),
            require_ready=True,
        )
        for error in continuity_result.errors:
            _add_diagnostic(
                diagnostics,
                "invalid-source-continuity",
                error.message,
                "design_system.verification.source_continuity"
                + error.path.removeprefix("$"),
            )
        for field in ("required_viewports", "required_states"):
            values = verification.get(field)
            if not isinstance(values, list) or not values:
                _add_diagnostic(
                    diagnostics,
                    "incomplete-design-verification",
                    f"verification.{field} must be a non-empty list",
                    f"design_system.verification.{field}",
                )
        if not str(verification.get("visual_tolerance") or "").strip():
            _add_diagnostic(
                diagnostics,
                "missing-visual-tolerance",
                "verification.visual_tolerance must define comparison boundaries",
                "design_system.verification.visual_tolerance",
            )
        if design_system.get("schema") == DESIGN_CHANGE_SCHEMA:
            _validate_design_professional_verification(
                verification,
                decision_ids=canonical_decision_ids,
                handoff_contract_ids=(
                    approval.get("handoff_contract_ids", [])
                    if isinstance(approval, dict)
                    else []
                ),
                immutable_handoff=None,
                diagnostics=diagnostics,
            )

    for section in READY_REQUIRED_SECTIONS:
        if not re.search(
            rf"^##+\s+{re.escape(section)}\s*$",
            document.body,
            re.MULTILINE,
        ):
            _add_diagnostic(
                diagnostics,
                "missing-ready-section",
                f"approved design system is missing Markdown section: {section}",
                section,
            )

    if _contains_template_placeholder(design_system):
        _add_diagnostic(
            diagnostics,
            "unresolved-design-placeholder",
            "approved design-system metadata and tokens must not contain unresolved template placeholders",
            "design_system",
        )


def _contains_template_placeholder(value: Any) -> bool:
    if isinstance(value, str):
        return bool(re.search(r"\{\{[^{}]+\}\}", value))
    if isinstance(value, dict):
        return any(
            _contains_template_placeholder(key) or _contains_template_placeholder(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_contains_template_placeholder(item) for item in value)
    return False


def _to_tailwind_theme(design_system: dict[str, Any]) -> dict[str, Any]:
    extend: dict[str, dict[str, Any]] = {
        "colors": {},
        "spacing": {},
        "borderRadius": {},
        "fontFamily": {},
        "fontSize": {},
        "boxShadow": {},
        "animation": {},
        "transitionDuration": {},
        "transitionTimingFunction": {},
    }
    skipped_token_categories: list[str] = []
    tokens = design_system.get("tokens", {})
    if not isinstance(tokens, dict):
        tokens = {}

    for category, entries in tokens.items():
        if not isinstance(entries, dict):
            skipped_token_categories.append(str(category))
            continue

        if category == "color":
            _copy_tokens(entries, extend["colors"])
        elif category == "spacing":
            _copy_tokens(entries, extend["spacing"])
        elif category == "radius":
            _copy_tokens(entries, extend["borderRadius"])
        elif category == "typography":
            for token_name, token_value in entries.items():
                value = _token_export_value(token_value)
                if value is None:
                    continue
                export_name = token_name.replace(".", "-")
                if token_name.endswith(".family"):
                    extend["fontFamily"][export_name] = value
                elif token_name.endswith(".size"):
                    extend["fontSize"][export_name] = value
                else:
                    skipped_token_categories.append(f"{category}.{token_name}")
        elif category == "shadow":
            _copy_tokens(entries, extend["boxShadow"])
        elif category == "animation":
            _copy_tokens(entries, extend["animation"])
        elif category == "motion":
            for token_name, token_value in entries.items():
                value = _token_export_value(token_value)
                if value is None:
                    continue
                export_name = str(token_name).replace(".", "-")
                if str(token_name).startswith("duration."):
                    extend["transitionDuration"][export_name] = value
                elif str(token_name).startswith("easing."):
                    extend["transitionTimingFunction"][export_name] = value
                else:
                    skipped_token_categories.append(
                        f"{category}.{token_name}"
                    )
        else:
            skipped_token_categories.append(str(category))

    return {
        "theme": {"extend": extend},
        "skipped_token_categories": skipped_token_categories,
    }


def _copy_tokens(entries: dict[Any, Any], output: dict[str, Any]) -> None:
    for token_name, token_value in entries.items():
        value = _token_export_value(token_value)
        if value is not None:
            output[str(token_name).replace(".", "-")] = value


def _token_export_value(token_value: Any) -> Any | None:
    if not isinstance(token_value, dict) or "value" not in token_value:
        return None
    return token_value["value"]


def _add_diagnostic(diagnostics: list[DesignDiagnostic], code: str, message: str, path: str) -> None:
    diagnostics.append(DesignDiagnostic(code=code, message=message, path=path))
