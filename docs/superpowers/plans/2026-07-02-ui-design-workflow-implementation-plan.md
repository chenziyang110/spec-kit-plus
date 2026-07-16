# UI Design Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship first-class UI design-system support through `DESIGN.md`, `sp-design`, built-in design presets, design helper commands, and cross-workflow UI quality carry-forward.
**Architecture:** Add shared generated-project assets first, then add a focused Python design helper module and Typer `specify design` subapp. Keep workflow behavior in shared command templates and passive skills so Markdown, TOML, and skills-based integrations inherit the same design contract.
**Tech Stack:** Python 3.11, Typer, Rich, PyYAML, Markdown templates, pytest, existing integration template generators.

---

## Source Spec

Implement the approved design spec at `docs/superpowers/specs/2026-07-02-ui-design-workflow-design.md`.

The worker must preserve these locks:

- `DESIGN.md` is the root project design-system contract.
- YAML front matter in `DESIGN.md` is the machine-readable lint/export boundary.
- `sp-design` owns design-system creation, synthesis, refinement, and audit.
- `sp-design` may write only `DESIGN.md`, `.specify/design/**`, and stable design rules in `.specify/memory/project-rules.md`.
- `sp-design` must not write source code, UI components, CSS/theme implementation files, tests, feature specs, plan artifacts, or task artifacts.
- Built-in design presets are Spec Kit Plus owned second-created files. Do not copy third-party `DESIGN.md` files.
- `specify design import` writes a reference summary for `sp-design`; it must not replace `DESIGN.md`.
- High-risk UI work routes to `sp-design`; small UI work may proceed with a recorded soft risk.

## File Structure

Create:

```text
src/specify_cli/design.py
templates/design-template.md
templates/design-library/workbench-precision.md
templates/design-library/developer-tool-sharp.md
templates/design-library/data-dense-ops.md
templates/design-library/consumer-mobile-polished.md
templates/commands/design.md
templates/command-partials/design/shell.md
templates/passive-skills/spec-kit-ui-design/SKILL.md
tests/test_design_cli.py
```

Modify:

```text
src/specify_cli/__init__.py
pyproject.toml
templates/passive-skills/spec-kit-workflow-routing/SKILL.md
templates/passive-skills/frontend-design/SKILL.md
templates/passive-skills/webapp-testing/SKILL.md
templates/commands/discussion.md
templates/commands/specify.md
templates/commands/plan.md
templates/commands/tasks.md
templates/commands/implement.md
templates/spec-template.md
templates/plan-template.md
templates/tasks-template.md
templates/workflow-state-template.md
templates/project-handbook-template.md
README.md
PROJECT-HANDBOOK.md
tests/test_packaging_assets.py
tests/test_passive_skill_installation.py
tests/test_alignment_templates.py
tests/test_command_surface_semantics.py
tests/test_passive_skill_guidance.py
tests/integrations/test_integration_base_markdown.py
tests/integrations/test_integration_base_toml.py
tests/integrations/test_integration_base_skills.py
tests/integrations/test_integration_claude.py
tests/integrations/test_integration_cursor_agent.py
tests/integrations/test_integration_gemini.py
tests/integrations/test_integration_codex.py
tests/integrations/test_integration_forge.py
tests/integrations/test_integration_kimi.py
```

No hook dispatch update is expected because `sp-design` has no hook-owned phase in v1. If a test proves hook command lists are explicit, update the hook list and add the matching test in the same task.

## Working Tree Discipline

- Run `git status --short` before each task.
- Several files in this repository may already be dirty from unrelated work. Read a dirty file before editing it.
- Stage only files changed for the current task.
- Do not revert unrelated user changes.

## Tasks

### Task 1: Add Failing Asset and Packaging Tests

**Files:**
- Modify: `tests/test_packaging_assets.py`
- Modify: `tests/test_passive_skill_installation.py`
- Modify: `tests/test_alignment_templates.py`

- [ ] **Step 1: Establish baseline**

Run:

```powershell
git status --short
python -m pytest tests/test_packaging_assets.py tests/test_passive_skill_installation.py tests/test_alignment_templates.py -q
```

Expected: current tests pass, or failures are unrelated to design workflow files. Record unrelated failures in the execution notes and continue.

- [ ] **Step 2: Add package-data assertions**

In `tests/test_packaging_assets.py`, add:

```python
def test_design_assets_are_packaged() -> None:
    pyproject = _read("pyproject.toml")

    assert '"templates/design-template.md" = "specify_cli/core_pack/templates/design-template.md"' in pyproject
    assert '"templates/design-library" = "specify_cli/core_pack/templates/design-library"' in pyproject
```

In `test_install_shared_infra_copies_split_core_pack_template_dirs`, add these fixtures before `_install_shared_infra(...)`:

```python
    (core_pack / "templates" / "design-template.md").write_text("# Design\n", encoding="utf-8")
    (core_pack / "templates" / "design-library").mkdir(parents=True)
    (core_pack / "templates" / "design-library" / "workbench-precision.md").write_text(
        "# Workbench Precision\n",
        encoding="utf-8",
    )
```

Add these assertions after existing `.specify/templates` assertions:

```python
    assert (project_root / ".specify" / "templates" / "design-template.md").exists()
    assert (
        project_root
        / ".specify"
        / "templates"
        / "design-library"
        / "workbench-precision.md"
    ).exists()
    assert (project_root / "DESIGN.md").exists()
```

- [ ] **Step 3: Add passive skill installation assertion**

In `tests/test_passive_skill_installation.py`, extend `test_passive_skills_are_packaged_for_skill_integrations` with:

```python
    assert "spec-kit-ui-design/SKILL.md" in passive_files
```

- [ ] **Step 4: Add semantic asset tests**

In `tests/test_alignment_templates.py`, add:

```python
def test_design_template_declares_v1_schema_and_required_guidance() -> None:
    content = _read("templates/design-template.md")

    assert "design_system:" in content
    assert "schema: spec-kit-design-v1" in content
    assert "tokens:" in content
    assert "components:" in content
    assert "accessibility:" in content
    assert "## Anti-Patterns" in content
    assert "## UI QA Checklist" in content
    assert "{color." in content


def test_design_library_contains_owned_second_created_presets() -> None:
    presets = [
        "workbench-precision",
        "developer-tool-sharp",
        "data-dense-ops",
        "consumer-mobile-polished",
    ]

    for preset in presets:
        content = _read(f"templates/design-library/{preset}.md")
        lowered = content.lower()

        assert "schema: spec-kit-design-v1" in content
        assert "spec kit plus owned" in lowered
        assert "second-created" in lowered
        assert "do not copy external brand expression" in lowered
```

- [ ] **Step 5: Run tests and verify failures**

Run:

```powershell
python -m pytest tests/test_packaging_assets.py::test_design_assets_are_packaged tests/test_passive_skill_installation.py tests/test_alignment_templates.py::test_design_template_declares_v1_schema_and_required_guidance tests/test_alignment_templates.py::test_design_library_contains_owned_second_created_presets -q
```

Expected: failures for missing package entries and missing design assets.

- [ ] **Step 6: Commit failing tests**

Run:

```powershell
git add tests/test_packaging_assets.py tests/test_passive_skill_installation.py tests/test_alignment_templates.py
git commit -m "test: cover design workflow generated assets"
```

### Task 2: Add Design Template, Built-In Presets, and Packaging Entries

**Files:**
- Create: `templates/design-template.md`
- Create: `templates/design-library/workbench-precision.md`
- Create: `templates/design-library/developer-tool-sharp.md`
- Create: `templates/design-library/data-dense-ops.md`
- Create: `templates/design-library/consumer-mobile-polished.md`
- Modify: `pyproject.toml`
- Modify: `src/specify_cli/__init__.py`

- [ ] **Step 1: Add package-data entries**

In `pyproject.toml`, add these force includes near the existing template entries:

```toml
"templates/design-template.md" = "specify_cli/core_pack/templates/design-template.md"
"templates/design-library" = "specify_cli/core_pack/templates/design-library"
```

- [ ] **Step 2: Create the root design template**

Create `templates/design-template.md` with this complete content:

````markdown
---
design_system:
  schema: spec-kit-design-v1
  name: project-design-system
  version: 1
  platforms:
    - web
    - mobile
    - desktop
    - tui
    - cli
  tokens:
    color:
      surface.canvas:
        value: "#ffffff"
        usage: primary application background
      surface.panel:
        value: "#f8fafc"
        usage: raised panels, grouped controls, secondary surfaces
      surface.inverse:
        value: "#111827"
        usage: inverse headers, terminal panels, high-emphasis surfaces
      text.primary:
        value: "#111827"
        usage: primary readable text
      text.secondary:
        value: "#4b5563"
        usage: secondary text, helper copy, metadata
      text.inverse:
        value: "#ffffff"
        usage: text on inverse surfaces
      border.subtle:
        value: "#d1d5db"
        usage: controls, dividers, quiet card boundaries
      accent.primary:
        value: "#2563eb"
        usage: primary action, selected states, active navigation
      accent.danger:
        value: "#dc2626"
        usage: destructive actions and error states
      accent.success:
        value: "#16a34a"
        usage: success states and positive confirmations
    spacing:
      scale.1:
        value: "4px"
        usage: icon and label gaps
      scale.2:
        value: "8px"
        usage: compact control padding and tight stack gaps
      scale.3:
        value: "12px"
        usage: form row gaps and compact panel padding
      scale.4:
        value: "16px"
        usage: default section gap and card padding
      scale.6:
        value: "24px"
        usage: page sections and major groups
      scale.8:
        value: "32px"
        usage: screen-level spacing
    radius:
      control:
        value: "6px"
        usage: buttons, inputs, tabs, compact cards
      panel:
        value: "8px"
        usage: repeated cards, panels, dialogs
    typography:
      body.family:
        value: "system-ui"
        usage: default interface text
      body.size:
        value: "14px"
        usage: dense application copy
      heading.family:
        value: "system-ui"
        usage: page and section headings
      heading.weight:
        value: "650"
        usage: hierarchy without oversized type
    shadow:
      panel:
        value: "0 1px 2px rgba(15, 23, 42, 0.08)"
        usage: restrained elevation for overlays and active panels
  components:
    button:
      required_states:
        - default
        - hover
        - focus
        - disabled
        - loading
      token_refs:
        background: "{color.accent.primary}"
        text: "{color.text.inverse}"
        radius: "{radius.control}"
    input:
      required_states:
        - default
        - hover
        - focus
        - disabled
        - error
      token_refs:
        background: "{color.surface.canvas}"
        text: "{color.text.primary}"
        border: "{color.border.subtle}"
        radius: "{radius.control}"
    card:
      required_states:
        - default
        - hover
        - selected
        - loading
        - empty
      token_refs:
        background: "{color.surface.panel}"
        border: "{color.border.subtle}"
        radius: "{radius.panel}"
  accessibility:
    contrast_intent: WCAG AA for ordinary text where platform rendering allows
    focus_visible: required
    keyboard_navigation: required
---

# Project Design System

This file is the project design-system contract. Read it before creating or changing user-facing UI, including web, mobile, desktop, TUI, and CLI output.

## Product Feel

Use a clear, task-focused interface with restrained visual treatment. Prefer strong information hierarchy, consistent spacing, stable controls, and readable states over decorative styling.

## Platforms

- Web: responsive layouts, keyboard access, visible focus, stable control sizes, and screenshots for key viewports.
- Mobile: thumb-friendly controls, native-feeling density, readable empty and error states.
- Desktop: efficient layouts, command discoverability, and stateful controls that do not jump.
- TUI: readable narrow-width output, no-color mode, clear selected and error states.
- CLI: concise output, scan-friendly tables, predictable success and error messages, no reliance on color alone.

## Component Rules

- Buttons must have default, hover, focus, disabled, and loading states.
- Inputs must have default, hover, focus, disabled, and error states.
- Repeated cards may use `radius.panel`; controls should use `radius.control`.
- Prefer existing component patterns before adding variants.
- Do not invent styling outside the token set without updating this file.

## Anti-Patterns

- Do not ship generic gradient-heavy screens that ignore product context.
- Do not mix unrelated radius, spacing, shadow, or typography systems.
- Do not hide loading, empty, error, disabled, or permission states.
- Do not rely on color alone for status.
- Do not create UI evidence that proves behavior while ignoring visual layout.

## UI QA Checklist

- Tokens are used for colors, spacing, radius, typography, and elevation.
- Required component states are implemented or explicitly out of scope for the surface.
- Text fits inside controls and panels at mobile and desktop widths.
- Keyboard and focus behavior are visible where the platform supports them.
- Evidence captures the platform: screenshots for graphical UI, representative output for TUI/CLI.

## Design Change Policy

Update this file through `sp-design` when a change affects product-wide style, brand, density, component rules, token values, or platform-specific interface expectations.
````

- [ ] **Step 3: Create owned design presets**

For each file below, create a full `DESIGN.md`-compatible preset with YAML front matter using `schema: spec-kit-design-v1`, at least `color`, `spacing`, `radius`, and `typography` token categories, `button`, `input`, and `card` component state coverage, and this body sentence:

```markdown
This is a Spec Kit Plus owned, second-created preset. It abstracts reusable product design principles and does not copy external brand expression.
```

Use these preset-specific directions:

```text
templates/design-library/workbench-precision.md
- platforms: web, desktop, cli
- visual direction: dense professional tools, CRM, admin panels
- colors: white canvas, zinc text, blue action, amber warning, green success
- radius: 4px controls, 6px panels

templates/design-library/developer-tool-sharp.md
- platforms: web, desktop, tui, cli
- visual direction: developer products, IDE-like tools, infra consoles
- colors: near-black inverse panels, slate canvas, cyan action, red danger
- radius: 3px controls, 4px panels

templates/design-library/data-dense-ops.md
- platforms: web, desktop, tui
- visual direction: observability, logistics, analytics, monitoring, operations
- colors: cool gray surfaces, blue information, orange incident, green healthy
- radius: 4px controls, 6px panels

templates/design-library/consumer-mobile-polished.md
- platforms: mobile, web
- visual direction: consumer mobile apps and cross-platform app shells
- colors: warm white canvas, charcoal text, coral action, teal success
- radius: 10px controls, 12px panels
```

- [ ] **Step 4: Install root DESIGN.md during init**

In `src/specify_cli/__init__.py`, inside `_install_shared_infra(...)` after `templates_src` resolution and before the template-copy loop ends, add a copy from `templates_src / "design-template.md"` to `project_path / "DESIGN.md"`.

Use this exact behavior:

```python
        design_template_src = templates_src / "design-template.md"
        design_file_dst = project_path / "DESIGN.md"
        if design_template_src.exists():
            if design_file_dst.exists() and not overwrite_existing:
                skipped_files.append(str(design_file_dst.relative_to(project_path)))
            else:
                shutil.copy2(design_template_src, design_file_dst)
                manifest.record_existing("DESIGN.md")
```

Place it so `templates_src` is defined. Do not remove the existing `.specify/templates/design-template.md` copy; generated projects need both the root design contract and the template copy.

- [ ] **Step 5: Run asset tests**

Run:

```powershell
python -m pytest tests/test_packaging_assets.py::test_design_assets_are_packaged tests/test_packaging_assets.py::test_install_shared_infra_copies_split_core_pack_template_dirs tests/test_passive_skill_installation.py tests/test_alignment_templates.py::test_design_template_declares_v1_schema_and_required_guidance tests/test_alignment_templates.py::test_design_library_contains_owned_second_created_presets -q
```

Expected: all selected tests pass.

- [ ] **Step 6: Commit assets**

Run:

```powershell
git add pyproject.toml src/specify_cli/__init__.py templates/design-template.md templates/design-library tests/test_packaging_assets.py tests/test_passive_skill_installation.py tests/test_alignment_templates.py
git commit -m "feat: add design system generated assets"
```

### Task 3: Add Design Parser, Lint, Export, and Import Core

**Files:**
- Create: `src/specify_cli/design.py`
- Create: `tests/test_design_cli.py`

- [ ] **Step 1: Add failing parser and lint tests**

Create `tests/test_design_cli.py` with:

```python
from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.design import (
    DesignLintError,
    export_design_system,
    import_design_reference,
    lint_design_file,
    parse_design_markdown,
)


VALID_DESIGN = """---
design_system:
  schema: spec-kit-design-v1
  name: test-system
  version: 1
  platforms:
    - web
  tokens:
    color:
      surface.canvas:
        value: "#ffffff"
        usage: app background
      text.primary:
        value: "#111827"
        usage: primary text
    spacing:
      scale.4:
        value: "16px"
        usage: default gap
    radius:
      control:
        value: "6px"
        usage: controls
    typography:
      body.family:
        value: "system-ui"
        usage: body text
  components:
    button:
      required_states:
        - default
        - hover
        - focus
        - disabled
        - loading
      token_refs:
        background: "{color.surface.canvas}"
        text: "{color.text.primary}"
  accessibility:
    contrast_intent: WCAG AA
    focus_visible: required
    keyboard_navigation: required
---

# Design

## Platforms

Web only.

## Component Rules

Use the tokens.

## Anti-Patterns

No unrelated styling.

## UI QA Checklist

Capture screenshots.
"""


def test_parse_design_markdown_reads_yaml_front_matter() -> None:
    document = parse_design_markdown(VALID_DESIGN, source="DESIGN.md")

    assert document.design_system["schema"] == "spec-kit-design-v1"
    assert document.design_system["name"] == "test-system"
    assert document.body.startswith("# Design")


def test_lint_design_file_accepts_valid_design(tmp_path: Path) -> None:
    design_file = tmp_path / "DESIGN.md"
    design_file.write_text(VALID_DESIGN, encoding="utf-8")

    diagnostics = lint_design_file(design_file)

    assert diagnostics == []


def test_lint_design_file_reports_missing_required_markdown_section(tmp_path: Path) -> None:
    design_file = tmp_path / "DESIGN.md"
    design_file.write_text(VALID_DESIGN.replace("## Anti-Patterns\n\nNo unrelated styling.\n\n", ""), encoding="utf-8")

    diagnostics = lint_design_file(design_file)

    assert any(d.code == "missing-section" and "Anti-Patterns" in d.message for d in diagnostics)


def test_lint_design_file_reports_unknown_token_reference(tmp_path: Path) -> None:
    design_file = tmp_path / "DESIGN.md"
    design_file.write_text(VALID_DESIGN.replace("{color.text.primary}", "{color.text.missing}"), encoding="utf-8")

    diagnostics = lint_design_file(design_file)

    assert any(d.code == "unknown-token-reference" for d in diagnostics)


def test_export_design_system_json_returns_normalized_tokens(tmp_path: Path) -> None:
    design_file = tmp_path / "DESIGN.md"
    design_file.write_text(VALID_DESIGN, encoding="utf-8")

    exported = export_design_system(design_file, export_format="json")
    payload = json.loads(exported)

    assert payload["schema"] == "spec-kit-design-v1"
    assert payload["tokens"]["color"]["surface.canvas"]["value"] == "#ffffff"
    assert payload["components"]["button"]["token_refs"]["text"] == "{color.text.primary}"


def test_export_design_system_tailwind_maps_supported_token_categories(tmp_path: Path) -> None:
    design_file = tmp_path / "DESIGN.md"
    design_file.write_text(VALID_DESIGN, encoding="utf-8")

    exported = export_design_system(design_file, export_format="tailwind")
    payload = json.loads(exported)

    assert payload["theme"]["extend"]["colors"]["surface-canvas"] == "#ffffff"
    assert payload["theme"]["extend"]["spacing"]["scale-4"] == "16px"
    assert payload["theme"]["extend"]["borderRadius"]["control"] == "6px"
    assert payload["theme"]["extend"]["fontFamily"]["body-family"] == "system-ui"


def test_export_design_system_rejects_unknown_format(tmp_path: Path) -> None:
    design_file = tmp_path / "DESIGN.md"
    design_file.write_text(VALID_DESIGN, encoding="utf-8")

    with pytest.raises(DesignLintError):
        export_design_system(design_file, export_format="css")


def test_import_design_reference_writes_reference_summary(tmp_path: Path) -> None:
    out_dir = tmp_path / ".specify" / "design"

    result = import_design_reference(
        source="https://example.com/style",
        out_dir=out_dir,
        notes="Dense admin UI with compact tables.",
    )

    content = result.read_text(encoding="utf-8")
    assert result == out_dir / "references.md"
    assert "https://example.com/style" in content
    assert "Dense admin UI with compact tables." in content
    assert not (tmp_path / "DESIGN.md").exists()
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m pytest tests/test_design_cli.py -q
```

Expected: import failure because `specify_cli.design` does not exist.

- [ ] **Step 3: Implement `src/specify_cli/design.py`**

Create `src/specify_cli/design.py` with these public names and behavior:

```python
from __future__ import annotations

from dataclasses import dataclass
import json
import re
from pathlib import Path
from typing import Any

import yaml


FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)
TOKEN_NAME_RE = re.compile(r"^[a-z][a-z0-9]*(?:\.[a-z0-9]+)*$")
TOKEN_REF_RE = re.compile(r"\{([a-z][a-z0-9]*)\.([a-z][a-z0-9]*(?:\.[a-z0-9]+)*)\}")
REQUIRED_SECTIONS = ("Product Feel", "Platforms", "Component Rules", "Anti-Patterns", "UI QA Checklist")
REQUIRED_TOKEN_CATEGORIES = ("color", "spacing", "radius", "typography")
SUPPORTED_EXPORT_FORMATS = {"json", "tailwind"}


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
```

Implement these functions:

```python
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


def lint_design_file(path: Path) -> list[DesignDiagnostic]:
    if not path.exists():
        return [DesignDiagnostic("missing-file", f"{path} does not exist", str(path))]

    try:
        document = parse_design_markdown(path.read_text(encoding="utf-8"), source=str(path))
    except DesignLintError as exc:
        return [DesignDiagnostic("parse-error", str(exc), str(path))]

    diagnostics: list[DesignDiagnostic] = []
    _validate_design_system(document, diagnostics)
    _validate_markdown_sections(document, diagnostics)
    _validate_token_references(document, diagnostics)
    return diagnostics


def export_design_system(path: Path, *, export_format: str) -> str:
    export_format = export_format.lower()
    if export_format not in SUPPORTED_EXPORT_FORMATS:
        raise DesignLintError(f"unsupported export format: {export_format}")

    diagnostics = lint_design_file(path)
    if diagnostics:
        messages = "; ".join(f"{d.code}: {d.message}" for d in diagnostics)
        raise DesignLintError(messages)

    document = parse_design_markdown(path.read_text(encoding="utf-8"), source=str(path))
    if export_format == "json":
        payload = {
            "schema": document.design_system["schema"],
            "name": document.design_system.get("name"),
            "version": document.design_system.get("version"),
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
```

Private helpers must validate:

```text
_validate_design_system:
- schema equals spec-kit-design-v1
- platforms is a non-empty list
- tokens is a mapping
- required token categories exist
- token categories are mappings of token name to mapping with value and usage
- token names match TOKEN_NAME_RE
- components is a mapping
- each component has required_states as a non-empty list
- accessibility has contrast_intent, focus_visible, keyboard_navigation

_validate_markdown_sections:
- each REQUIRED_SECTIONS entry appears as a Markdown heading, for example `## Product Feel`

_validate_token_references:
- collect existing token references as (category, token_name)
- inspect components.*.token_refs string values
- every "{category.token.name}" exists

_to_tailwind_theme:
- map color -> theme.extend.colors using token names with "." replaced by "-"
- map spacing -> theme.extend.spacing
- map radius -> theme.extend.borderRadius
- map typography keys ending ".family" -> theme.extend.fontFamily
- map typography keys ending ".size" -> theme.extend.fontSize
- map shadow -> theme.extend.boxShadow
- map animation -> theme.extend.animation
- include skipped_token_categories for categories not mapped
```

- [ ] **Step 4: Run design core tests**

Run:

```powershell
python -m pytest tests/test_design_cli.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Commit parser core**

Run:

```powershell
git add src/specify_cli/design.py tests/test_design_cli.py
git commit -m "feat: add design system parser and exports"
```

### Task 4: Add `specify design` CLI Commands

**Files:**
- Modify: `src/specify_cli/__init__.py`
- Modify: `tests/test_design_cli.py`

- [ ] **Step 1: Add failing CLI tests**

Append these tests to `tests/test_design_cli.py`:

```python
from typer.testing import CliRunner
from specify_cli import app


def test_specify_design_lint_reports_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "DESIGN.md").write_text(VALID_DESIGN, encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(app, ["design", "lint"])

    assert result.exit_code == 0
    assert "DESIGN.md is valid" in result.output


def test_specify_design_lint_reports_json_diagnostics(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "DESIGN.md").write_text(VALID_DESIGN.replace("schema: spec-kit-design-v1", "schema: wrong"), encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(app, ["design", "lint", "--format", "json"])

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert payload["diagnostics"][0]["code"] == "invalid-schema"


def test_specify_design_export_prints_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "DESIGN.md").write_text(VALID_DESIGN, encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(app, ["design", "export", "--format", "json"])

    assert result.exit_code == 0
    assert json.loads(result.output)["schema"] == "spec-kit-design-v1"


def test_specify_design_import_writes_references(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        app,
        ["design", "import", "https://example.com/design", "--notes", "Compact SaaS interface"],
    )

    assert result.exit_code == 0
    assert ".specify/design/references.md" in result.output
    assert (tmp_path / ".specify" / "design" / "references.md").exists()
    assert not (tmp_path / "DESIGN.md").exists()
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m pytest tests/test_design_cli.py -q
```

Expected: failures because `design` subcommands are not registered.

- [ ] **Step 3: Register `design_app`**

In `src/specify_cli/__init__.py`, add imports near the existing local module imports:

```python
from specify_cli.design import (
    DesignDiagnostic,
    DesignLintError,
    export_design_system,
    import_design_reference,
    lint_design_file,
)
```

Add this Typer app next to the other subapps:

```python
design_app = typer.Typer(
    name="design",
    help="Lint, export, and import Spec Kit Plus DESIGN.md assets",
    add_completion=False,
)
app.add_typer(design_app, name="design")
```

- [ ] **Step 4: Add command implementations**

Add helper and commands after the subapp definitions:

```python
def _diagnostics_payload(diagnostics: list[DesignDiagnostic]) -> dict[str, Any]:
    return {
        "ok": not diagnostics,
        "diagnostics": [
            {"level": d.level, "code": d.code, "message": d.message, "path": d.path}
            for d in diagnostics
        ],
    }


@design_app.command("lint")
def design_lint(
    path: Path = typer.Argument(Path("DESIGN.md"), help="Path to DESIGN.md"),
    output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
) -> None:
    diagnostics = lint_design_file(path)

    if output_format == "json":
        print_json(_diagnostics_payload(diagnostics))
    elif output_format == "text":
        if diagnostics:
            for diagnostic in diagnostics:
                console.print(f"[red]{diagnostic.code}[/red]: {diagnostic.message}")
        else:
            console.print(f"[green]{path} is valid[/green]")
    else:
        console.print("[red]Error:[/red] --format must be text or json")
        raise typer.Exit(2)

    if diagnostics:
        raise typer.Exit(1)


@design_app.command("export")
def design_export(
    path: Path = typer.Argument(Path("DESIGN.md"), help="Path to DESIGN.md"),
    export_format: str = typer.Option("json", "--format", help="Export format: json or tailwind"),
    out: Optional[Path] = typer.Option(None, "--out", help="Write export to a file instead of stdout"),
) -> None:
    try:
        rendered = export_design_system(path, export_format=export_format)
    except DesignLintError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1)

    if out is None:
        console.print(rendered, end="")
        return

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(rendered, encoding="utf-8")
    console.print(f"[green]Wrote[/green] {out}")


@design_app.command("import")
def design_import(
    source: str = typer.Argument(..., help="URL, file path, screenshot note, or textual design reference"),
    notes: str = typer.Option("", "--notes", help="Short note describing useful traits to synthesize"),
    out_dir: Path = typer.Option(Path(".specify/design"), "--out-dir", help="Design workflow directory"),
) -> None:
    out_path = import_design_reference(source, out_dir=out_dir, notes=notes)
    console.print(f"[green]Wrote[/green] {out_path}")
```

- [ ] **Step 5: Run CLI tests**

Run:

```powershell
python -m pytest tests/test_design_cli.py -q
```

Expected: all tests pass.

- [ ] **Step 6: Commit CLI commands**

Run:

```powershell
git add src/specify_cli/__init__.py tests/test_design_cli.py
git commit -m "feat: add specify design commands"
```

### Task 5: Add `sp-design` Generated Workflow

**Files:**
- Create: `templates/commands/design.md`
- Create: `templates/command-partials/design/shell.md`
- Modify: `src/specify_cli/__init__.py`
- Modify: integration tests listed in the file structure
- Modify: `tests/test_command_surface_semantics.py`
- Modify: `tests/test_alignment_templates.py`

- [ ] **Step 1: Add failing command surface tests**

In `tests/test_command_surface_semantics.py`, add:

```python
def test_design_command_declares_design_system_workflow_contract() -> None:
    content = _read("templates/commands/design.md")

    assert "description: Use when a project needs a DESIGN.md design-system contract" in content
    assert "primary_outputs" in content
    assert "DESIGN.md" in content
    assert ".specify/design/design-state.md" in content
    assert "{{spec-kit-include: ../command-partials/design/shell.md}}" in content
```

In `tests/test_alignment_templates.py`, add:

```python
def test_design_workflow_is_not_an_implementation_workflow() -> None:
    content = _read("templates/commands/design.md") + "\n" + _read("templates/command-partials/design/shell.md")
    lowered = content.lower()

    assert "active_command: sp-design" in content
    assert "phase_mode: design-only" in content
    assert "allowed writes" in lowered
    assert "forbidden writes" in lowered
    assert "source code" in lowered
    assert "css or theme implementation files" in lowered
    assert "ask the user to approve a direction" in lowered
    assert "specify design lint" in lowered
    assert "write the project's own `design.md`" in lowered
```

- [ ] **Step 2: Add generated integration expectations**

Update complete-file inventory tests for the new command output. Use existing helpers in these files rather than hardcoding every command list manually:

```text
tests/integrations/test_integration_base_markdown.py
tests/integrations/test_integration_base_toml.py
tests/integrations/test_integration_base_skills.py
tests/integrations/test_integration_claude.py
tests/integrations/test_integration_cursor_agent.py
tests/integrations/test_integration_gemini.py
tests/integrations/test_integration_codex.py
tests/integrations/test_integration_forge.py
tests/integrations/test_integration_kimi.py
```

Expected new outputs:

```text
Markdown command integrations: design command file with projected invocation for that integration
TOML integrations: design TOML command file
Skills integrations: sp-design/SKILL.md
Claude integration: .claude/commands/sp.design.md
Codex integration: .codex/skills/sp-design/SKILL.md
Cursor Agent integration: .cursor/skills/sp-design/SKILL.md
Gemini integration: .gemini/commands/sp.design.toml
Forge integration: .forge/commands/sp.design.md using {{parameters}}
Kimi integration: .kimi/skills/sp-design/SKILL.md
```

- [ ] **Step 3: Run tests and verify failures**

Run:

```powershell
python -m pytest tests/test_command_surface_semantics.py::test_design_command_declares_design_system_workflow_contract tests/test_alignment_templates.py::test_design_workflow_is_not_an_implementation_workflow tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py -q
```

Expected: failures because `templates/commands/design.md` and partial are absent.

- [ ] **Step 4: Create command template**

Create `templates/commands/design.md`:

```markdown
---
description: Use when a project needs a DESIGN.md design-system contract, design-system synthesis, UI style refinement, or design readiness audit before UI work proceeds.
workflow_contract:
  when_to_use: A project needs product-wide interface style, design-system tokens, platform UI rules, or design readiness review before specification, planning, tasks, or implementation.
  primary_objective: Produce, refine, synthesize, or audit the root `DESIGN.md` design-system contract without implementing UI code.
  primary_outputs: '`DESIGN.md`, `.specify/design/design-state.md`, `.specify/design/references.md`, `.specify/design/options.md`, and `.specify/design/review.md`; stable design rules in `.specify/memory/project-rules.md` only when they should become shared project defaults.'
  default_handoff: 'After user review, recommend exactly one next command: `/sp.discussion`, `/sp.specify`, `/sp.plan`, or the originally blocked workflow.'
scripts:
  sh: scripts/bash/update-agent-context.sh __AGENT__
  ps: scripts/powershell/update-agent-context.ps1 -AgentType __AGENT__
---

{{spec-kit-include: ../command-partials/design/shell.md}}

{{spec-kit-include: ../command-partials/common/semantic-work-contract.md}}

{{spec-kit-include: ../command-partials/common/adaptive-execution.md}}
```

- [ ] **Step 5: Create shell partial**

Create `templates/command-partials/design/shell.md` with:

```markdown
# sp-design: Design System Workflow

You are running `sp-design`. This is a design-system workflow, not an implementation workflow.

## Workflow Phase Lock

- Create or resume `.specify/design/design-state.md` before substantial design synthesis.
- Set durable state with:
  - `active_command: sp-design`
  - `phase_mode: design-only`
  - `current_stage: context-intake`
  - `allowed_writes: DESIGN.md, .specify/design/design-state.md, .specify/design/references.md, .specify/design/options.md, .specify/design/review.md, .specify/memory/project-rules.md`
  - `forbidden_actions: edit source code, edit tests, write CSS/theme implementation files, create UI components, create feature specs, create plan artifacts, create task artifacts`
- When resuming after compaction, read `.specify/design/design-state.md` before continuing.

## Allowed Writes

- `DESIGN.md`
- `.specify/design/design-state.md`
- `.specify/design/references.md`
- `.specify/design/options.md`
- `.specify/design/review.md`
- stable design rules in `.specify/memory/project-rules.md` when they should become shared project defaults

## Forbidden Writes

- source code
- UI components
- CSS or theme implementation files
- tests
- business feature specs
- plan or task artifacts outside the active design workflow

## Modes

Infer the mode from the user's request:

- `create`: generate a new project design system from product context.
- `synthesize`: transform references into an original design system.
- `refine`: update an existing `DESIGN.md`.
- `audit`: inspect whether the current design system is enough for upcoming UI work.

If the mode is ambiguous, choose the smallest safe mode and state the assumption.

## Intake

1. Read `DESIGN.md` if it exists.
2. Read `.specify/design/references.md`, `.specify/design/options.md`, and `.specify/design/review.md` if they exist.
3. Read `README.md`, project handbook files, existing UI surfaces, existing design files, `.specify/memory/project-rules.md`, and relevant `.specify/memory/learnings/INDEX.md` entries when present.
4. Identify declared or implied platforms: web, mobile, desktop, TUI, CLI.
5. If references are supplied as URLs, screenshots, text notes, existing design files, or imported summaries, extract reusable design principles rather than copying their expression.
6. When built-in presets help, read one of the shipped preset files such as `.specify/templates/design-library/workbench-precision.md` or `templates/design-library/workbench-precision.md` and treat it as inspiration, not as a forced brand.

## Synthesis Rules

- The final output is the project's own `DESIGN.md`.
- Present two or three project-specific design directions when creating or synthesizing a design system.
- Each direction must name product feel, platform fit, density, typography intent, color strategy, component state strategy, accessibility stance, and trade-offs.
- Ask the user to approve a direction before writing or replacing `DESIGN.md`.
- Preserve existing project rules unless the user approves a design-system change that supersedes them.
- Do not copy external brand names, protected visual identity, proprietary token names, or third-party file text into the final design system.
- Normalize approved direction into `spec-kit-design-v1` YAML front matter plus readable Markdown guidance.

## Required DESIGN.md Shape

`DESIGN.md` must contain:

- YAML front matter with `design_system.schema: spec-kit-design-v1`
- `design_system.name`
- `design_system.version`
- `design_system.platforms`
- token categories for `color`, `spacing`, `radius`, and `typography`
- component required states and token references
- accessibility intent
- Markdown sections for `Product Feel`, `Platforms`, `Component Rules`, `Anti-Patterns`, `UI QA Checklist`, and `Design Change Policy`

## Review

Before closeout:

1. Run `specify design lint` when the CLI helper is available.
2. Write `.specify/design/review.md` with:
   - selected mode
   - inputs read
   - approved direction
   - platforms covered
   - design-system risks
   - lint result
   - recommended next workflow
3. Ask the user to review the written design before downstream workflows consume it as locked input.

## Closeout

Close with the design-system status, changed files, lint result, and exactly one recommended next command.
```

- [ ] **Step 6: Add CLI skill description**

In `src/specify_cli/__init__.py`, add to `SKILL_DESCRIPTIONS`:

```python
    "design": "Use when a project needs a DESIGN.md design-system contract, design-system synthesis, UI style refinement, or design readiness audit before UI work proceeds.",
```

- [ ] **Step 7: Run command and integration tests**

Run:

```powershell
python -m pytest tests/test_command_surface_semantics.py::test_design_command_declares_design_system_workflow_contract tests/test_alignment_templates.py::test_design_workflow_is_not_an_implementation_workflow tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_cursor_agent.py tests/integrations/test_integration_gemini.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_forge.py tests/integrations/test_integration_kimi.py -q
```

Expected: all selected tests pass.

- [ ] **Step 8: Commit workflow command**

Run:

```powershell
git add src/specify_cli/__init__.py templates/commands/design.md templates/command-partials/design/shell.md tests/test_command_surface_semantics.py tests/test_alignment_templates.py tests/integrations
git commit -m "feat: add sp-design workflow"
```

### Task 6: Add UI Design Passive Skill and Align Existing UI Skills

**Files:**
- Create: `templates/passive-skills/spec-kit-ui-design/SKILL.md`
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Modify: `templates/passive-skills/frontend-design/SKILL.md`
- Modify: `templates/passive-skills/webapp-testing/SKILL.md`
- Modify: `tests/test_passive_skill_guidance.py`
- Modify: `tests/test_alignment_templates.py`

- [ ] **Step 1: Add failing passive guidance tests**

In `tests/test_passive_skill_guidance.py`, add:

```python
def test_ui_design_passive_skill_requires_design_md_before_ui_work() -> None:
    content = _read("templates/passive-skills/spec-kit-ui-design/SKILL.md")
    lowered = content.lower()

    assert "design.md" in lowered
    assert "sp-design" in content
    assert "web" in lowered
    assert "mobile" in lowered
    assert "desktop" in lowered
    assert "tui" in lowered
    assert "cli" in lowered
    assert "platform-appropriate evidence" in lowered
    assert "generic one-off styling" in lowered


def test_workflow_routing_recommends_design_for_high_risk_ui() -> None:
    content = _read("templates/passive-skills/spec-kit-workflow-routing/SKILL.md")
    lowered = content.lower()

    assert "sp-design" in content
    assert "{{invoke:design}}" in content
    assert "high-risk ui" in lowered
    assert "new product ui" in lowered
    assert "redesign or rebrand" in lowered
    assert "small ui work" in lowered
    assert "soft risk" in lowered


def test_frontend_design_is_subordinate_to_design_md() -> None:
    content = _read("templates/passive-skills/frontend-design/SKILL.md")
    lowered = content.lower()

    assert "design.md" in lowered
    assert "subordinate" in lowered
    assert "sp-design" in content
    assert "do not invent unrelated bold aesthetics" in lowered


def test_webapp_testing_requires_visual_evidence() -> None:
    content = _read("templates/passive-skills/webapp-testing/SKILL.md")
    lowered = content.lower()

    assert "viewport screenshot" in lowered
    assert "layout overflow" in lowered
    assert "visual regression-friendly" in lowered
    assert "sp-implement" in content
```

- [ ] **Step 2: Run tests and verify failures**

Run:

```powershell
python -m pytest tests/test_passive_skill_guidance.py::test_ui_design_passive_skill_requires_design_md_before_ui_work tests/test_passive_skill_guidance.py::test_workflow_routing_recommends_design_for_high_risk_ui tests/test_passive_skill_guidance.py::test_frontend_design_is_subordinate_to_design_md tests/test_passive_skill_guidance.py::test_webapp_testing_requires_visual_evidence -q
```

Expected: failures for missing passive skill and missing guidance phrases.

- [ ] **Step 3: Create `spec-kit-ui-design` passive skill**

Create `templates/passive-skills/spec-kit-ui-design/SKILL.md`:

```markdown
---
name: "spec-kit-ui-design"
description: "Use when UI, UX, visual design, design-system, accessibility, component, platform interface, TUI, or CLI output quality matters in a Spec Kit Plus project."
origin: spec-kit-plus
---

# Spec Kit UI Design

UI quality is product scope. Before creating or changing user-facing interface work, read `DESIGN.md` when it exists.

## Design System Gate

- If `DESIGN.md` exists, treat it as the binding design-system contract.
- If `DESIGN.md` is missing and the work is new product UI, redesign or rebrand, core workflow experience, multi-platform interface work, or a high-visibility customer-facing surface, recommend `sp-design` with `{{invoke:design}}`.
- If `DESIGN.md` is missing and the work is a small internal form, narrow copy/state improvement, already-covered component variant, or low-risk CLI/TUI wording refinement, proceed only after recording the missing design system as a soft risk.
- If `DESIGN.md` contradicts the requested UI change, stop and route to `sp-design`, `sp-specify`, or `sp-plan` according to ownership.

## Platform Rules

- Web: require responsive layout checks, visible focus, keyboard access, stable control sizing, and viewport screenshots.
- Mobile: require thumb-friendly controls, native-feeling density, readable empty/error states, and small-screen evidence.
- Desktop: require efficient layout, discoverable commands, and stateful controls that do not shift unexpectedly.
- TUI: require readable narrow-width output, no-color output, selected/error states, and keyboard readability.
- CLI: require scan-friendly output, predictable success/error text, no reliance on color alone, and representative terminal samples.

## Component Coverage

For relevant surfaces, account for default, hover, focus, disabled, loading, empty, error, success, selected, permission, and offline states. If a state does not apply, name the reason in the spec, plan, task, or implementation evidence.

## Evidence

UI implementation closeout needs platform-appropriate evidence:

- Web: Playwright screenshots, viewport checks, accessibility checks when available, console checks, and layout overflow checks.
- Mobile or desktop: screenshots or recordings, platform state coverage, and accessibility checks when available.
- TUI or CLI: representative output, narrow-width output, no-color output, error and empty states, and readability checks.

Reject generic one-off styling when a project design system exists. Reuse tokens, component rules, platform rules, and anti-patterns from `DESIGN.md`.
```

- [ ] **Step 4: Update workflow routing**

In `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`, add a recommendation rule after `sp-discussion` guidance:

```markdown
- Use `sp-design` when the request is high-risk UI or design-system work: new product UI, redesign or rebrand, core workflow experience, multi-platform design decisions, high-visibility customer-facing surfaces, or missing/contradictory `DESIGN.md` for a UI-heavy request. Recommend `{{invoke:design}}` rather than letting implementation invent styling. Small UI work can proceed with a recorded soft risk when it is a narrow internal form change, copy or state improvement, already-covered component variant, or low-risk CLI/TUI wording refinement.
```

- [ ] **Step 5: Update `frontend-design`**

Near the top of `templates/passive-skills/frontend-design/SKILL.md`, after the opening description paragraph, add:

```markdown
## Spec Kit Plus Design-System Priority

When this skill runs inside a Spec Kit Plus project, read `DESIGN.md` before designing or styling UI. `frontend-design` is subordinate to `DESIGN.md`.

- If `DESIGN.md` exists, use its tokens, component rules, anti-patterns, platform guidance, and UI QA checklist.
- Do not invent unrelated bold aesthetics when `DESIGN.md` already defines the product direction.
- If no design system exists and the work is high-visibility, new product UI, redesign or rebrand, or a core experience surface, recommend `sp-design` before implementation.
- If no design system exists and the work is narrow and low-risk, record the missing design system as a soft risk and keep styling conservative.
```

- [ ] **Step 6: Update `webapp-testing`**

Add this section after the decision tree:

```markdown
## Spec Kit Plus UI Evidence

When testing UI work from `sp-implement`, capture visual evidence that can be referenced in closeout:

- viewport screenshots for the required desktop and mobile widths
- visual regression-friendly screenshot paths under an evidence directory named by the active task or surface
- accessibility checks where the project tooling supports them
- console error checks after page load and after key interactions
- layout overflow checks for body width, clipped controls, and text that escapes buttons, cards, tables, dialogs, or navigation

Evidence should prove that the implemented UI follows `DESIGN.md`, not only that the underlying behavior works.
```

- [ ] **Step 7: Run passive skill tests**

Run:

```powershell
python -m pytest tests/test_passive_skill_installation.py tests/test_passive_skill_guidance.py -q
```

Expected: all selected tests pass.

- [ ] **Step 8: Commit passive skill alignment**

Run:

```powershell
git add templates/passive-skills/spec-kit-ui-design templates/passive-skills/spec-kit-workflow-routing/SKILL.md templates/passive-skills/frontend-design/SKILL.md templates/passive-skills/webapp-testing/SKILL.md tests/test_passive_skill_installation.py tests/test_passive_skill_guidance.py
git commit -m "feat: add ui design passive guidance"
```

### Task 7: Propagate Design Carry-Forward Through Core Workflows

**Files:**
- Modify: `templates/commands/discussion.md`
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/commands/implement.md`
- Modify: `templates/spec-template.md`
- Modify: `templates/plan-template.md`
- Modify: `templates/tasks-template.md`
- Modify: `templates/workflow-state-template.md`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_command_surface_semantics.py`

- [ ] **Step 1: Add failing workflow semantic tests**

In `tests/test_alignment_templates.py`, add:

```python
def test_discussion_carries_ui_design_intent_to_handoff() -> None:
    content = _read("templates/commands/discussion.md")

    assert "experience_commitments" in content
    assert "design_system_requirements" in content
    assert "design_system_status" in content
    assert "design_risk_level" in content
    assert "sp-design" in content


def test_specify_reads_design_md_for_ui_features() -> None:
    content = _read("templates/commands/specify.md")

    assert "DESIGN.md" in content
    assert "Experience Requirements" in content
    assert "design-system readiness" in content
    assert "design_system_status" in content
    assert "strong blocker" in content.lower()
    assert "soft risk" in content.lower()


def test_plan_tasks_implement_preserve_design_quality_chain() -> None:
    plan = _read("templates/commands/plan.md")
    tasks = _read("templates/commands/tasks.md")
    implement = _read("templates/commands/implement.md")

    assert "Design System Adoption" in plan
    assert "token strategy" in plan.lower()
    assert "Design Quality Coverage" in tasks
    assert "required states" in tasks.lower()
    assert "DESIGN.md" in implement
    assert "Playwright screenshots" in implement
    assert "representative output" in implement
    assert "tests passed" in implement
    assert "sp-design" in implement
```

In `tests/test_command_surface_semantics.py`, add:

```python
def test_templates_include_design_quality_sections() -> None:
    assert "## Experience Requirements" in _read("templates/spec-template.md")
    assert "## Design System Adoption" in _read("templates/plan-template.md")
    assert "Design Quality Coverage" in _read("templates/tasks-template.md")
    assert "design-system" in _read("templates/workflow-state-template.md").lower()
```

- [ ] **Step 2: Run tests and verify failures**

Run:

```powershell
python -m pytest tests/test_alignment_templates.py::test_discussion_carries_ui_design_intent_to_handoff tests/test_alignment_templates.py::test_specify_reads_design_md_for_ui_features tests/test_alignment_templates.py::test_plan_tasks_implement_preserve_design_quality_chain tests/test_command_surface_semantics.py::test_templates_include_design_quality_sections -q
```

Expected: failures for missing phrases or incomplete carry-forward.

- [ ] **Step 3: Update `discussion.md`**

Add guidance near existing UI discussion guidance:

```markdown
When UI-facing signals appear, record design intent and experience commitments in durable discussion state and handoff material:

- `experience_commitments`
- `design_system_requirements`
- `design_system_status`
- `design_risk_level`

For new product UI, redesign or rebrand, core workflow experience, multi-platform design decisions, and high-visibility customer-facing surfaces, recommend `sp-design`. For small UI work, continue only when the design-system gap is recorded as a soft risk.
```

- [ ] **Step 4: Update `specify.md`**

Add a UI design intake subsection in the context/spec writing area:

```markdown
**UI Design System Intake**:
- If the feature has user-interface scope, read `DESIGN.md` when present.
- Capture Experience Requirements in `spec.md`.
- Capture design-system readiness in `alignment.md` with `design_system_status`.
- Capture relevant design references and gaps in `context.md`.
- Treat missing or insufficient design system as a strong blocker for new product UI, redesign or rebrand, core workflow experience, multi-platform design decisions, and high-visibility customer-facing surfaces.
- Treat missing design system as a soft risk for small internal form changes, narrow copy or state improvements, already-covered component variants, and low-risk CLI/TUI wording refinements.
```

- [ ] **Step 5: Update `plan.md`**

Add a required design planning subsection:

```markdown
## Design System Adoption

For UI-facing features, convert `DESIGN.md` into implementation constraints:

- design-system source and status
- token strategy
- component reuse and extension policy
- platform adaptation strategy
- accessibility requirements
- screenshot or output evidence strategy
- forbidden styling drift

Name where implementers may use judgment and where the design system is binding.
```

- [ ] **Step 6: Update `tasks.md`**

Add a task-generation requirement:

```markdown
## Design Quality Coverage

For user-visible surfaces, include a coverage row with:

- surface name
- design source
- required states
- platform coverage
- evidence required
- task IDs that implement and verify the surface

UI tasks should cover default, hover, focus, disabled, loading, empty, error, and success states when relevant, responsive layout or platform adaptation, accessibility checks, screenshots, terminal samples, recordings, or manual review artifacts, and no-color or narrow-terminal modes for TUI/CLI.
```

- [ ] **Step 7: Update `implement.md`**

Add an implementation closeout rule:

```markdown
Before closing UI tasks, read `DESIGN.md`, `Design System Adoption`, and `Design Quality Coverage`.

Do not close UI tasks with only `tests passed` unless the accepted task package explicitly says tests are sufficient evidence. Usual evidence:

- Web: Playwright screenshots, viewport checks, accessibility checks, and visual review notes.
- Mobile or desktop: screenshots or recordings, platform-state coverage, and accessibility checks where available.
- TUI or CLI: representative output, narrow-width output, no-color output, error and empty states, and readability checks.

If `DESIGN.md` is missing, contradictory, or insufficient, record a blocker and route back to `sp-design`, `sp-plan`, or `sp-specify` according to ownership.
```

- [ ] **Step 8: Update artifact templates**

Add these headings to the templates:

```markdown
templates/spec-template.md:
## Experience Requirements

- Design-system source:
- Design-system status:
- Required platforms:
- Experience commitments:
- Design risks:

templates/plan-template.md:
## Design System Adoption

- Source and status:
- Token strategy:
- Component reuse and extension policy:
- Platform adaptation strategy:
- Accessibility requirements:
- Evidence strategy:
- Forbidden styling drift:

templates/tasks-template.md:
## Design Quality Coverage

| Surface | Design Source | Required States | Platform Coverage | Evidence Required | Task IDs |
|---------|---------------|-----------------|-------------------|-------------------|----------|

templates/workflow-state-template.md:
- design_system_status: [not-applicable | ready | soft-risk | blocked]
- design_risk_level: [none | low | medium | high]
```

- [ ] **Step 9: Run workflow semantic tests**

Run:

```powershell
python -m pytest tests/test_alignment_templates.py tests/test_command_surface_semantics.py -q
```

Expected: all selected tests pass, except unrelated pre-existing failures recorded at baseline.

- [ ] **Step 10: Commit workflow propagation**

Run:

```powershell
git add templates/commands/discussion.md templates/commands/specify.md templates/commands/plan.md templates/commands/tasks.md templates/commands/implement.md templates/spec-template.md templates/plan-template.md templates/tasks-template.md templates/workflow-state-template.md tests/test_alignment_templates.py tests/test_command_surface_semantics.py
git commit -m "feat: carry design quality through workflows"
```

### Task 8: Update Documentation and Project Handbook

**Files:**
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `templates/project-handbook-template.md`
- Modify: `tests/test_specify_guidance_docs.py`
- Modify: `tests/test_agents_guidance.py`

- [ ] **Step 1: Add failing docs tests**

In `tests/test_specify_guidance_docs.py`, add:

```python
def test_docs_describe_design_workflow_and_design_md() -> None:
    readme = _read("README.md")
    handbook = _read("PROJECT-HANDBOOK.md")
    template = _read("templates/project-handbook-template.md")

    for content in (readme, handbook, template):
        assert "sp-design" in content
        assert "DESIGN.md" in content
        assert "design-system" in content.lower()
        assert "specify design lint" in content
```

If `tests/test_agents_guidance.py` checks generated AGENTS guidance, add:

```python
def test_agent_guidance_mentions_design_system_contract() -> None:
    content = _read("AGENTS.md")

    assert "DESIGN.md" in content
    assert "sp-design" in content
```

If `AGENTS.md` is intentionally local and not generated in the current branch, skip the second test and record the reason in execution notes.

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
python -m pytest tests/test_specify_guidance_docs.py tests/test_agents_guidance.py -q
```

Expected: docs guidance test fails until docs are updated. Existing unrelated AGENTS failures may already exist; record them.

- [ ] **Step 3: Update README**

Add `sp-design` to the workflow list and explain:

```markdown
- `design` / `sp-design` creates, synthesizes, refines, or audits the root `DESIGN.md` design-system contract before UI work proceeds. Use it for new product UI, redesigns, rebrands, core workflow experience, multi-platform interface decisions, and high-visibility customer-facing surfaces.
```

Add helper command documentation:

```markdown
### Design System Helpers

- `specify design lint` checks whether `DESIGN.md` is complete enough for agents to use.
- `specify design export --format json` exports normalized design tokens and component token references.
- `specify design export --format tailwind` exports supported token categories into Tailwind theme fields.
- `specify design import SOURCE_REFERENCE` writes `.specify/design/references.md` as input for `sp-design`; it does not overwrite `DESIGN.md`.
```

- [ ] **Step 4: Update project handbook files**

In both `PROJECT-HANDBOOK.md` and `templates/project-handbook-template.md`, add:

```markdown
- **UI design system**: Generated projects include a root `DESIGN.md` as the design-system contract. UI-facing workflows read it before specification, planning, task generation, and implementation. Use `sp-design` to create, synthesize, refine, or audit the design system; use `specify design lint` to check structural readiness; use `specify design export --format json|tailwind` when implementation needs token exports; use `specify design import SOURCE_REFERENCE` to create reference summaries for synthesis without overwriting `DESIGN.md`.
```

- [ ] **Step 5: Run docs tests**

Run:

```powershell
python -m pytest tests/test_specify_guidance_docs.py tests/test_agents_guidance.py -q
```

Expected: docs tests pass, except any unrelated failures recorded at baseline.

- [ ] **Step 6: Commit docs**

Run:

```powershell
git add README.md PROJECT-HANDBOOK.md templates/project-handbook-template.md tests/test_specify_guidance_docs.py tests/test_agents_guidance.py
git commit -m "docs: document design workflow"
```

### Task 9: Full Verification and Drift Check

**Files:**
- No planned source edits unless verification exposes a design workflow regression.

- [ ] **Step 1: Run format and whitespace checks**

Run:

```powershell
git diff --check
```

Expected: no whitespace errors.

- [ ] **Step 2: Run targeted regression suite**

Run:

```powershell
python -m pytest tests/test_design_cli.py tests/test_packaging_assets.py tests/test_passive_skill_installation.py tests/test_passive_skill_guidance.py tests/test_alignment_templates.py tests/test_command_surface_semantics.py tests/test_specify_guidance_docs.py -q
```

Expected: all targeted tests pass, except unrelated failures already present before Task 1.

- [ ] **Step 3: Run integration generation suite**

Run:

```powershell
python -m pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_cursor_agent.py tests/integrations/test_integration_gemini.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_forge.py tests/integrations/test_integration_kimi.py -q
```

Expected: all selected integration tests pass, except unrelated failures recorded at baseline.

- [ ] **Step 4: Exercise CLI manually**

Use a temporary project directory:

```powershell
$tmp = New-Item -ItemType Directory -Path ([System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "speckit-design-check-" + [System.Guid]::NewGuid().ToString("N")))
python -m specify_cli init $tmp.FullName --ai codex --script ps --ignore-agent-tools
Push-Location $tmp.FullName
python -m specify_cli design lint
python -m specify_cli design export --format json | ConvertFrom-Json | Select-Object -ExpandProperty schema
python -m specify_cli design export --format tailwind | ConvertFrom-Json | Out-Null
python -m specify_cli design import https://example.com/design --notes "Compact admin UI"
Test-Path DESIGN.md
Test-Path .specify/design/references.md
Pop-Location
```

Expected:

```text
python -m specify_cli design lint -> exit 0 and reports DESIGN.md is valid
json export schema -> spec-kit-design-v1
tailwind export parses as JSON
design import writes .specify/design/references.md
DESIGN.md remains present and is not replaced by import
```

- [ ] **Step 5: Inspect generated Codex assets**

In the temp project from Step 4, run:

```powershell
Test-Path .codex/skills/sp-design/SKILL.md
Select-String -Path .codex/skills/sp-design/SKILL.md -Pattern "DESIGN.md","specify design lint","Forbidden Writes"
Test-Path .specify/templates/design-library/workbench-precision.md
```

Expected: all paths exist and selected strings are present.

- [ ] **Step 6: Final source scan**

Run:

```powershell
$scanPatterns = @(
  ("TB" + "D"),
  ("TO" + "DO"),
  ("fill in " + "details"),
  ("implement" + " later"),
  "Google Labs",
  "VoltAgent",
  "Cursor Designer",
  "UI Design Brain",
  "Anthropic frontend design"
)
rg -n ($scanPatterns -join "|") templates src tests README.md PROJECT-HANDBOOK.md pyproject.toml
```

Expected: no new unresolved markers in changed files. Third-party names should appear only in the approved design spec or historical docs, not in built-in presets.

- [ ] **Step 7: Final commit**

If verification required fixes, return to the task that owns the changed file, apply that task's test command, and use that task's commit command. Do not create a catch-all verification commit.

If no fixes were required, do not create an empty commit.

- [ ] **Step 8: Final status**

Run:

```powershell
git status --short
git log --oneline -5
```

Expected: only unrelated pre-existing dirty files remain, or the working tree is clean. Report the commit list and any pre-existing unrelated dirty files in the closeout.

## Acceptance Checklist

- `DESIGN.md` installs at generated project root without overwriting an existing root design file unless overwrite mode is active.
- `.specify/templates/design-template.md` and `.specify/templates/design-library/**` install for generated projects.
- `templates/design-library/**` contains original Spec Kit Plus owned second-created presets.
- `specify design lint` validates front matter schema, token categories, token names, token references, required component states, accessibility fields, and required Markdown sections.
- `specify design export --format json` emits normalized tokens and component token references.
- `specify design export --format tailwind` maps supported token categories and reports skipped categories in JSON.
- `specify design import` writes `.specify/design/references.md` and does not overwrite `DESIGN.md`.
- `sp-design` is generated across Markdown, TOML, and skills-based integrations.
- `spec-kit-ui-design` installs for skills-based integrations.
- `spec-kit-workflow-routing` recommends `sp-design` for high-risk UI and permits soft-risk continuation for low-risk UI.
- `frontend-design` reads `DESIGN.md` first and does not invent unrelated aesthetics when a design system exists.
- `webapp-testing` describes screenshot, viewport, accessibility, console, overflow, and evidence naming requirements.
- `sp-discussion`, `sp-specify`, `sp-plan`, `sp-tasks`, and `sp-implement` preserve design intent and evidence requirements.
- README and project handbook files document `sp-design`, `DESIGN.md`, and `specify design` helpers.
