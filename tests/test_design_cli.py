from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli import app
from specify_cli.design import (
    DesignLintError,
    export_design_system,
    import_design_reference,
    lint_design_file,
    parse_design_markdown,
)


runner = CliRunner()


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

## Product Feel

Purposeful and compact.

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


def test_lint_design_file_reports_non_file_path(tmp_path: Path) -> None:
    diagnostics = lint_design_file(tmp_path)

    assert any(d.code == "read-error" and "not a file" in d.message for d in diagnostics)


def test_lint_design_file_reports_missing_required_markdown_section(tmp_path: Path) -> None:
    design_file = tmp_path / "DESIGN.md"
    design_file.write_text(
        VALID_DESIGN.replace("## Anti-Patterns\n\nNo unrelated styling.\n\n", ""),
        encoding="utf-8",
    )

    diagnostics = lint_design_file(design_file)

    assert any(d.code == "missing-section" and "Anti-Patterns" in d.message for d in diagnostics)


def test_lint_design_file_reports_unknown_token_reference(tmp_path: Path) -> None:
    design_file = tmp_path / "DESIGN.md"
    design_file.write_text(VALID_DESIGN.replace("{color.text.primary}", "{color.text.missing}"), encoding="utf-8")

    diagnostics = lint_design_file(design_file)

    assert any(d.code == "unknown-token-reference" for d in diagnostics)


def test_lint_design_file_reports_malformed_token_reference(tmp_path: Path) -> None:
    design_file = tmp_path / "DESIGN.md"
    design_file.write_text(VALID_DESIGN.replace("{color.text.primary}", "color.text.primary"), encoding="utf-8")

    diagnostics = lint_design_file(design_file)

    assert any(d.code == "invalid-token-reference" for d in diagnostics)


def test_lint_design_file_reports_unclosed_token_reference(tmp_path: Path) -> None:
    design_file = tmp_path / "DESIGN.md"
    design_file.write_text(VALID_DESIGN.replace("{color.text.primary}", "{color.text.primary"), encoding="utf-8")

    diagnostics = lint_design_file(design_file)

    assert any(d.code == "invalid-token-reference" for d in diagnostics)


def test_lint_design_file_reports_non_string_token_reference(tmp_path: Path) -> None:
    design_file = tmp_path / "DESIGN.md"
    design_file.write_text(VALID_DESIGN.replace('text: "{color.text.primary}"', "text: 123"), encoding="utf-8")

    diagnostics = lint_design_file(design_file)

    assert any(d.code == "invalid-token-reference" for d in diagnostics)


def test_lint_design_file_reports_non_mapping_token_refs(tmp_path: Path) -> None:
    design_file = tmp_path / "DESIGN.md"
    design_file.write_text(
        VALID_DESIGN.replace(
            '      token_refs:\n        background: "{color.surface.canvas}"\n        text: "{color.text.primary}"',
            "      token_refs: 123",
        ),
        encoding="utf-8",
    )

    diagnostics = lint_design_file(design_file)

    assert any(d.code == "invalid-token-reference" for d in diagnostics)


def test_export_design_system_json_returns_normalized_tokens(tmp_path: Path) -> None:
    design_file = tmp_path / "DESIGN.md"
    design_file.write_text(VALID_DESIGN, encoding="utf-8")

    exported = export_design_system(design_file, export_format="json")
    payload = json.loads(exported)

    assert payload["schema"] == "spec-kit-design-v1"
    assert payload["tokens"]["color"]["surface.canvas"]["value"] == "#ffffff"
    assert payload["components"]["button"]["token_refs"]["text"] == "{color.text.primary}"
    assert payload["accessibility"]["focus_visible"] == "required"


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


def test_design_lint_cli_reports_success_by_default_against_cwd_design(tmp_path: Path) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("DESIGN.md").write_text(VALID_DESIGN, encoding="utf-8")
        result = runner.invoke(app, ["design", "lint"])

    assert result.exit_code == 0
    assert "DESIGN.md is valid" in result.output


def test_design_lint_cli_json_reports_diagnostics_for_invalid_schema(tmp_path: Path) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("DESIGN.md").write_text(
            VALID_DESIGN.replace("schema: spec-kit-design-v1", "schema: wrong-schema"),
            encoding="utf-8",
        )
        result = runner.invoke(app, ["design", "lint", "--format", "json"])

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["ok"] is False
    assert any(diagnostic["code"] == "invalid-schema" for diagnostic in payload["diagnostics"])


def test_design_export_cli_json_prints_design_schema(tmp_path: Path) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        Path("DESIGN.md").write_text(VALID_DESIGN, encoding="utf-8")
        result = runner.invoke(app, ["design", "export", "--format", "json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["schema"] == "spec-kit-design-v1"


def test_specify_design_export_rejects_unknown_format_as_usage_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "DESIGN.md").write_text(VALID_DESIGN, encoding="utf-8")
    runner = CliRunner()

    result = runner.invoke(app, ["design", "export", "--format", "css"])

    assert result.exit_code == 2
    assert "--format must be json or tailwind" in result.output


def test_design_import_cli_writes_reference_without_root_design(tmp_path: Path) -> None:
    with runner.isolated_filesystem(temp_dir=tmp_path):
        result = runner.invoke(
            app,
            [
                "design",
                "import",
                "https://example.com/style",
                "--notes",
                "Dense admin UI with compact tables.",
            ],
        )
        references_path = Path(".specify/design/references.md")
        references_content = references_path.read_text(encoding="utf-8")
        root_design_exists = Path("DESIGN.md").exists()

    assert result.exit_code == 0
    assert "Wrote .specify/design/references.md" in result.output
    assert "https://example.com/style" in references_content
    assert "Dense admin UI with compact tables." in references_content
    assert not root_design_exists
