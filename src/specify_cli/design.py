from __future__ import annotations

from dataclasses import dataclass
import hashlib
from html.parser import HTMLParser
import json
import re
from pathlib import Path
from typing import Any

import yaml

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
DESIGN_PREVIEW_MANIFEST_ID = "design-preview-manifest"
DESIGN_PREVIEW_DIRECTION_RE = re.compile(r"^direction-[a-z0-9][a-z0-9-]*$")
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
        for field in ("kind", "title", "verification"):
            if not str(decision.get(field) or "").strip():
                _add_diagnostic(
                    diagnostics,
                    "preview-incomplete-decision",
                    f"design decision {decision_id or index + 1} must define {field}",
                    f"manifest.decisions[{index}].{field}",
                )
    if len(set(decision_ids)) != len(decision_ids):
        _add_diagnostic(
            diagnostics,
            "preview-duplicate-decision-id",
            "design decision IDs must be unique",
            "manifest.decisions",
        )

    token_map = manifest.get("token_map")
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
            if str(entry.get("decision_id") or "").strip() not in decision_ids:
                _add_diagnostic(
                    diagnostics,
                    "preview-unknown-token-map-decision",
                    "token map decision_id must reference manifest.decisions",
                    f"manifest.token_map[{index}].decision_id",
                )
            for field in ("preview_token", "production_owner", "verification"):
                if not str(entry.get(field) or "").strip():
                    _add_diagnostic(
                        diagnostics,
                        "preview-incomplete-token-map",
                        f"token map entry must define {field}",
                        f"manifest.token_map[{index}].{field}",
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
    return diagnostics


def _replace_preview_attribute(content: str, name: str, value: str) -> str:
    pattern = re.compile(rf'({re.escape(name)}\s*=\s*")[^"]*(")')
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
    rendered = json.dumps(manifest, ensure_ascii=False, indent=2)
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
    payload = {
        "schema": DESIGN_PREVIEW_APPROVAL_SCHEMA,
        "preview_file": path.name,
        "direction_id": direction_id,
        "preview_ref": f"{path.name}#{direction_id}",
        "review_round": str(review.get("round") or "").strip(),
        "html_sha256": _sha256_bytes(updated.encode("utf-8")),
        "manifest_sha256": _canonical_json_sha256(manifest),
        "decision_ids": decision_ids,
    }

    atomic_write_text(path, updated)
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


def scaffold_design_preview(
    out_path: Path,
    *,
    force: bool = False,
    template_path: Path | None = None,
) -> Path:
    """Copy the bundled three-direction design preview scaffold."""

    source = template_path or _locate_design_preview_template()
    if not source.exists() or not source.is_file():
        raise DesignLintError(f"design preview template does not exist: {source}")
    if out_path.exists():
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
            existing_parser.preview_attrs.get("data-preview-status", "")
            .strip()
            .lower()
        )
        if existing_status == "approved":
            raise DesignLintError(
                f"approved design preview cannot be overwritten: {out_path}"
            )

    diagnostics = lint_design_preview_file(source, level="structural")
    if diagnostics:
        messages = "; ".join(
            f"{diagnostic.code}: {diagnostic.message}"
            for diagnostic in diagnostics
        )
        raise DesignLintError(f"bundled design preview template is invalid: {messages}")

    try:
        content = source.read_text(encoding="utf-8")
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
    return out_path


def _locate_design_preview_template() -> Path:
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
                for field in ("preview_sha256", "manifest_sha256"):
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
