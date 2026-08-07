from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
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

from .atomic_io import atomic_write_text


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
DESIGN_PREVIEW_SCHEMA = "spec-kit-design-preview-v1"
DESIGN_PREVIEW_MANIFEST_SCHEMA = "spec-kit-design-preview-manifest-v1"
DESIGN_PREVIEW_APPROVAL_SCHEMA = "spec-kit-design-preview-approval-v1"
DESIGN_HANDOFF_SCHEMA = "spec-kit-design-handoff-v1"
DESIGN_CAPABILITY_PROFILES_SCHEMA = "spec-kit-design-capability-profiles-v1"
DESIGN_CAPABILITY_MODEL_SCHEMA = "spec-kit-design-capability-model-v1"
DESIGN_PREVIEW_MANIFEST_ID = "design-preview-manifest"
DESIGN_PREVIEW_DIRECTION_RE = re.compile(r"^direction-[a-z0-9][a-z0-9-]*$")
DESIGN_SPECIMEN_ID_RE = re.compile(r"^SP-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
DESIGN_PREVIEW_REQUIRED_SECTIONS = (
    "foundations",
    "components",
    "states",
    "motion",
    "responsive",
    "handoff",
)
DESIGN_PREVIEW_PLACEHOLDER_RE = re.compile(r"__[A-Z0-9_]+__")
DESIGN_PREVIEW_REMOTE_RE = re.compile(r"(?i)(?:https?:)?//")
DESIGN_PREVIEW_NETWORK_SCRIPT_RE = re.compile(
    r"(?i)\b(?:fetch|XMLHttpRequest|WebSocket|EventSource)\s*\("
)
DESIGN_HANDOFF_ID_RE = re.compile(r"^DH-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
DESIGN_HANDOFF_REQUIRED_EVIDENCE = {
    "structure_snapshot",
    "visual_capture",
    "runtime_diagnostics",
    "visual_comparison_or_human_review",
}
UI_TARGET_SCHEMA = "spec-kit-ui-target-v1"
UI_TARGET_MANIFEST_SCHEMA = "spec-kit-ui-target-manifest-v1"
UI_TARGET_MANIFEST_ID = "ui-target-manifest"
UI_TARGET_NETWORK_OR_PERSISTENCE_RE = re.compile(
    r"(?i)\b(?:fetch|XMLHttpRequest|WebSocket|EventSource)\s*\("
    r"|\b(?:localStorage|sessionStorage|indexedDB|document\.cookie)\b"
)
UI_TARGET_APPROVED_PREVIEW_REF_RE = re.compile(
    r"round-\d+\.html#direction-[a-z0-9-]+$", re.IGNORECASE
)


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


class DesignLintError(ValueError):
    pass


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


def parse_design_markdown(text: str, *, source: str = "DESIGN.md") -> DesignDocument:
    match = FRONT_MATTER_RE.match(text)
    if not match:
        raise DesignLintError(f"{source}: missing YAML front matter")

    front_matter = yaml.safe_load(match.group(1)) or {}
    if not isinstance(front_matter, dict):
        raise DesignLintError(f"{source}: YAML front matter must be a mapping")

    design_system = front_matter.get("design_system")
    if not isinstance(design_system, dict):
        raise DesignLintError(f"{source}: missing design_system mapping")

    return DesignDocument(
        source=source,
        front_matter=front_matter,
        design_system=design_system,
        body=match.group(2),
    )


def design_preview_approval_path(path: Path) -> Path:
    """Return the deterministic sidecar path for one preview round."""

    return path.with_suffix(".approval.json")


def design_preview_handoff_path(path: Path) -> Path:
    """Return the immutable implementation handoff path for one preview round."""

    return path.with_suffix(".handoff.json")


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

    decision_ids = [
        str(decision.get("id") or "").strip()
        for decision in manifest.get("decisions") or []
        if isinstance(decision, dict) and str(decision.get("id") or "").strip()
    ]
    handoff = manifest.get("handoff")
    if not isinstance(handoff, dict):
        handoff = {}
        manifest["handoff"] = handoff
    handoff["reproduction_mode"] = (
        "exact" if profile_ids == ["web"] else "platform-adapted"
    )

    component_contracts: list[dict[str, Any]] = []
    responsive_matrix: list[dict[str, Any]] = []
    acceptance_matrix: list[dict[str, Any]] = []
    for profile in profiles:
        profile_id = str(profile["id"])
        profile_specimens = [
            specimen for specimen in specimens if specimen["profile_id"] == profile_id
        ]
        profile_specimen_ids = [str(specimen["id"]) for specimen in profile_specimens]
        required_states = _ordered_union(
            *(specimen.get("required_states") for specimen in profile_specimens)
        )
        contract = deepcopy(profile.get("component_contract"))
        if isinstance(contract, dict):
            contract["required_states"] = required_states
            contract["decision_ids"] = decision_ids
            component_contracts.append(contract)

        for target in profile.get("targets") or []:
            if not isinstance(target, dict):
                continue
            target_id = str(target.get("id") or "").strip()
            responsive_matrix.append(
                {
                    "id": target_id,
                    "profile_id": profile_id,
                    "label": str(target.get("label") or "").strip(),
                    "target": deepcopy(target.get("target")),
                    "review_width_px": target.get("review_width_px"),
                    "state": "default",
                    "adaptation": str(target.get("adaptation") or "").strip(),
                    "decision_ids": decision_ids,
                }
            )
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
    handoff["component_contracts"] = component_contracts
    handoff["responsive_matrix"] = responsive_matrix
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


def _direction_visual_fingerprint(direction: dict[str, Any]) -> str:
    """Canonical hash of render-driving visual systems for one direction."""

    payload = {
        "typography": direction.get("typography"),
        "geometry": direction.get("geometry"),
        "density": direction.get("density"),
        "elevation": direction.get("elevation"),
        "motion": direction.get("motion"),
        "modes": direction.get("modes"),
    }
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _direction_divergence_diagnostics(
    directions: list[Any],
) -> list[DesignDiagnostic]:
    """Reject ready boards whose three directions are not meaningfully differentiated."""

    diagnostics: list[DesignDiagnostic] = []
    dial_vectors: list[tuple[int, int, int]] = []
    signatures: list[str] = []
    visual_fingerprints: list[str] = []

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

    if len(visual_fingerprints) == 3 and len(set(visual_fingerprints)) < 3:
        _add_diagnostic(
            diagnostics,
            "preview-undifferentiated-direction-visuals",
            (
                "ready directions must differ in render-driving visual systems "
                "(typography, geometry, density tokens, elevation, motion, or color modes); "
                "distinct dials/signatures alone are not enough when visual payloads match"
            ),
            "manifest.directions",
        )

    return diagnostics


def _preview_manifest_diagnostics(
    manifest: dict[str, Any] | None,
    *,
    direction_ids: list[str],
    ready: bool,
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
    if not isinstance(directions, list) or len(directions) != 3:
        _add_diagnostic(
            diagnostics,
            "preview-manifest-direction-count",
            "preview manifest must define exactly three directions",
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
            "preview manifest direction IDs must match the three rendered direction IDs in order",
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

    if ready and isinstance(directions, list) and len(directions) == 3:
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

    component_contracts = handoff.get("component_contracts")
    responsive_matrix = handoff.get("responsive_matrix")
    acceptance_matrix = handoff.get("visual_acceptance_matrix")
    contract_collections = (
        ("component_contracts", component_contracts),
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
        handoff.get("component_contracts"),
        handoff.get("responsive_matrix"),
        handoff.get("visual_acceptance_matrix"),
        handoff.get("accepted_deviations"),
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
    content: str,
    direction_id: str,
    manifest: dict[str, Any],
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
                approved_targets.append(
                    {
                        "ref": f"{path.name}?{urlencode(query)}#{direction_id}",
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
    return {
        "schema": DESIGN_HANDOFF_SCHEMA,
        "approval": {
            "preview_file": path.name,
            "preview_ref": f"{path.name}#{direction_id}",
            "direction_id": direction_id,
            "review_round": str(review.get("round") or "").strip(),
            "preview_sha256": _sha256_bytes(content.encode("utf-8")),
            "manifest_sha256": _canonical_json_sha256(manifest),
            "decision_ids": decision_ids,
        },
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
        "preview_file": path.name,
        "direction_id": approved_direction,
        "preview_ref": f"{path.name}#{approved_direction}",
        "html_sha256": _sha256_bytes(content.encode("utf-8")),
        "manifest_sha256": expected_manifest_sha256,
    }
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
    source_ids = ("direction-a", "direction-b", "direction-c")
    sentinels = (
        "__SPECIFY_DIRECTION_SLOT_A__",
        "__SPECIFY_DIRECTION_SLOT_B__",
        "__SPECIFY_DIRECTION_SLOT_C__",
    )
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


def lint_design_preview_file(
    path: Path,
    *,
    level: str = "structural",
) -> list[DesignDiagnostic]:
    """Validate a project-level, three-direction HTML design preview board."""

    normalized_level = level.lower()
    if normalized_level not in SUPPORTED_LINT_LEVELS:
        raise DesignLintError(f"unsupported design preview lint level: {level}")
    if not path.exists():
        return [
            DesignDiagnostic(
                "preview-missing-file",
                f"{path} does not exist",
                str(path),
            )
        ]
    if not path.is_file():
        return [
            DesignDiagnostic(
                "preview-read-error",
                f"{path} is not a file",
                str(path),
            )
        ]

    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return [
            DesignDiagnostic(
                "preview-read-error",
                f"cannot read {path}: {exc}",
                str(path),
            )
        ]

    parser = _DesignPreviewHTMLParser()
    try:
        parser.feed(content)
        parser.close()
    except Exception as exc:
        return [
            DesignDiagnostic(
                "preview-parse-error",
                f"cannot parse {path}: {exc}",
                str(path),
            )
        ]

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
    if len(direction_ids) != 3:
        _add_diagnostic(
            diagnostics,
            "preview-direction-count",
            "design preview must contain exactly three comparable directions",
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
    diagnostics.extend(
        _preview_manifest_diagnostics(
            manifest,
            direction_ids=direction_ids,
            ready=normalized_level == "ready",
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

    if normalized_level == "ready":
        status = parser.preview_attrs.get("data-preview-status", "").strip().lower()
        if status not in {"candidate", "approved"}:
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
                "ready preview must not contain unresolved __PLACEHOLDER__ values",
                "html",
            )
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

    return diagnostics


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
    """Render a ready candidate preview from a compact manifest."""

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
        diagnostics = lint_design_preview_file(validation_path, level="ready")
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
    """Copy the bundled three-direction design preview scaffold."""

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
                            f"approved HTML preview requires a valid {field}",
                            f"manifest.approval.{field}",
                        )
                if not str(approval.get("handoff_ref") or "").strip().lower().endswith(
                    ".handoff.json"
                ):
                    _add_diagnostic(
                        diagnostics,
                        "ui-target-invalid-handoff-ref",
                        "approved HTML preview requires its immutable handoff reference",
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
                or not re.fullmatch(r"DS-[A-Z]+-\d{3}", item.strip())
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
        return json.dumps(payload, indent=2, sort_keys=True) + "\n"

    return json.dumps(_to_tailwind_theme(document.design_system), indent=2, sort_keys=True) + "\n"


def import_design_reference(source: str, *, out_dir: Path, notes: str = "") -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "references.md"
    source_line = source.strip()
    notes_line = notes.strip() or "No notes supplied."
    content = (
        "# Design References\n\n"
        "This file is input for `sp-design`. It is not the project design system.\n\n"
        "## Imported Reference\n\n"
        f"- Source: {source_line}\n"
        f"- Notes: {notes_line}\n\n"
        "## Synthesis Instructions\n\n"
        "- Extract reusable design principles.\n"
        "- Remove brand-specific expression.\n"
        "- Write original project guidance into `DESIGN.md` only after user approval in `sp-design`.\n"
    )
    out_path.write_text(content, encoding="utf-8")
    return out_path


def _validate_design_system(document: DesignDocument, diagnostics: list[DesignDiagnostic]) -> None:
    design_system = document.design_system
    if design_system.get("schema") != "spec-kit-design-v1":
        _add_diagnostic(diagnostics, "invalid-schema", "schema must equal spec-kit-design-v1", "design_system.schema")

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
            "approved UI design requires a local round-NN.html#direction-id reference",
            "design_system.approval.visual_refs",
        )
        return

    source_path = Path(document.source)
    source_root = source_path.parent
    resolved = False
    for visual_ref in local_refs:
        preview_ref, _, direction_id = visual_ref.partition("#")
        if not preview_ref.lower().endswith(".html") or not direction_id:
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
        preview_diagnostics = lint_design_preview_file(preview_path, level="ready")
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
            "preview_sha256": sidecar.get("html_sha256"),
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
                actual_handoff_sha256 = _sha256_bytes(
                    expected_handoff_path.read_bytes()
                )
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
