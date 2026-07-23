from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
import json
import re
from pathlib import Path
from typing import Any

import yaml


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
REQUIRED_TOKEN_CATEGORIES = ("color", "spacing", "radius", "typography")
REQUIRED_ACCESSIBILITY_KEYS = ("contrast_intent", "focus_visible", "keyboard_navigation")
SUPPORTED_EXPORT_FORMATS = {"json", "tailwind"}
SUPPORTED_LINT_LEVELS = {"structural", "ready"}
DESIGN_PREVIEW_SCHEMA = "spec-kit-design-preview-v1"
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
        self.sections: set[str] = set()
        self.external_dependencies: list[str] = []
        self.style_parts: list[str] = []
        self.script_parts: list[str] = []
        self._style_depth = 0
        self._script_depth = 0

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
        section = normalized_attrs.get("data-preview-section", "").strip()
        if section:
            self.sections.add(section)

        if normalized_tag == "style":
            self._style_depth += 1
        if normalized_tag == "script":
            self._script_depth += 1
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

    def handle_data(self, data: str) -> None:
        if self._style_depth:
            self.style_parts.append(data)
        if self._script_depth:
            self.script_parts.append(data)


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
    if out_path.exists() and not force:
        raise DesignLintError(f"design preview already exists: {out_path}")

    diagnostics = lint_design_preview_file(source, level="structural")
    if diagnostics:
        messages = "; ".join(
            f"{diagnostic.code}: {diagnostic.message}"
            for diagnostic in diagnostics
        )
        raise DesignLintError(f"bundled design preview template is invalid: {messages}")

    try:
        content = source.read_text(encoding="utf-8")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")
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
            "components": document.design_system.get("components", {}),
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
