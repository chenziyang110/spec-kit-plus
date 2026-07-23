from __future__ import annotations

import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli import app
from specify_cli.design import (
    DesignLintError,
    approve_design_preview,
    design_preview_approval_path,
    lint_design_preview_file,
    scaffold_design_preview,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PREVIEW_TEMPLATE = REPO_ROOT / "templates" / "design-preview-template.html"
runner = CliRunner()


def _candidate_preview() -> str:
    content = PREVIEW_TEMPLATE.read_text(encoding="utf-8")
    content = content.replace(
        'data-preview-status="scaffold"',
        'data-preview-status="candidate"',
    )
    content = content.replace('"configured": false', '"configured": true')
    content = content.replace(
        '"status": "scaffold",\n    "approved_direction": null',
        '"status": "candidate",\n    "approved_direction": null',
    )
    return re.sub(r"__[A-Z0-9_]+__", "Configured design content", content)


def test_design_preview_template_is_a_modern_three_direction_board() -> None:
    content = PREVIEW_TEMPLATE.read_text(encoding="utf-8")

    assert lint_design_preview_file(PREVIEW_TEMPLATE) == []
    assert content.count("data-direction-id=") == 3
    assert 'data-design-preview-schema="spec-kit-design-preview-v1"' in content
    assert 'data-preview-section="foundations"' in content
    assert 'data-preview-section="components"' in content
    assert 'data-preview-section="states"' in content
    assert 'data-preview-section="motion"' in content
    assert 'data-preview-section="responsive"' in content
    assert 'data-preview-section="handoff"' in content
    assert "@layer" in content
    assert "@container" in content
    assert "color-mix(" in content
    assert "clamp(" in content
    assert "prefers-reduced-motion: reduce" in content
    assert "document.startViewTransition" in content
    assert "--motion-duration-fast" in content
    assert "--motion-easing-emphasized" in content
    assert 'data-active-direction="direction-a"' in content
    assert "document.body.dataset.activeDirection = directionId" in content
    assert 'id="design-preview-manifest"' in content
    assert '"modes": {' in content
    assert '"high-contrast": {' in content
    assert 'id="direction-a"' in content
    assert "location.hash" in content
    assert "hashchange" in content
    assert 'id="direction-comparison"' in content
    assert 'id="simulated-viewport"' in content
    assert "https://" not in content
    assert "http://" not in content
    assert "<script src=" not in content


def test_design_preview_ready_lint_rejects_unconfigured_scaffold() -> None:
    diagnostics = lint_design_preview_file(PREVIEW_TEMPLATE, level="ready")

    assert any(item.code == "preview-not-candidate" for item in diagnostics)
    assert any(item.code == "preview-unresolved-placeholder" for item in diagnostics)


def test_design_preview_ready_lint_accepts_configured_candidate(tmp_path: Path) -> None:
    preview = tmp_path / "round-01.html"
    preview.write_text(_candidate_preview(), encoding="utf-8")

    assert lint_design_preview_file(preview, level="ready") == []


def test_design_preview_lint_rejects_remote_runtime_dependency(
    tmp_path: Path,
) -> None:
    preview = tmp_path / "remote.html"
    preview.write_text(
        _candidate_preview().replace(
            "</head>",
            '<script src="https://cdn.example.com/runtime.js"></script></head>',
        ),
        encoding="utf-8",
    )

    diagnostics = lint_design_preview_file(preview)

    assert any(item.code == "preview-remote-dependency" for item in diagnostics)


def test_design_preview_lint_requires_exactly_three_unique_directions(
    tmp_path: Path,
) -> None:
    preview = tmp_path / "directions.html"
    preview.write_text(
        _candidate_preview().replace('data-direction-id="direction-c"', ""),
        encoding="utf-8",
    )

    diagnostics = lint_design_preview_file(preview)

    assert any(item.code == "preview-direction-count" for item in diagnostics)


def test_design_preview_lint_requires_reduced_motion_fallback(
    tmp_path: Path,
) -> None:
    preview = tmp_path / "motion.html"
    preview.write_text(
        _candidate_preview().replace(
            "prefers-reduced-motion: reduce",
            "prefers-reduced-motion: no-preference",
        ),
        encoding="utf-8",
    )

    diagnostics = lint_design_preview_file(preview)

    assert any(item.code == "preview-missing-reduced-motion" for item in diagnostics)


def test_scaffold_design_preview_copies_template_without_overwriting(
    tmp_path: Path,
) -> None:
    output = tmp_path / ".specify" / "design" / "previews" / "round-01.html"

    written = scaffold_design_preview(output, template_path=PREVIEW_TEMPLATE)

    assert written == output
    output_content = output.read_text(encoding="utf-8")
    assert 'data-review-round="1"' in output_content
    assert '"round": "1"' in output_content
    with pytest.raises(DesignLintError, match="already exists"):
        scaffold_design_preview(output, template_path=PREVIEW_TEMPLATE)


def test_scaffold_design_preview_never_overwrites_an_approved_round(
    tmp_path: Path,
) -> None:
    output = tmp_path / ".specify" / "design" / "previews" / "round-01.html"
    output.parent.mkdir(parents=True)
    output.write_text(_candidate_preview(), encoding="utf-8")
    approve_design_preview(output, direction_id="direction-a")
    approved = output.read_text(encoding="utf-8")

    with pytest.raises(DesignLintError, match="approved"):
        scaffold_design_preview(
            output,
            force=True,
            template_path=PREVIEW_TEMPLATE,
        )

    assert output.read_text(encoding="utf-8") == approved


def test_approve_design_preview_freezes_direction_and_binds_sidecar(
    tmp_path: Path,
) -> None:
    preview = tmp_path / "round-03.html"
    preview.write_text(_candidate_preview(), encoding="utf-8")

    payload = approve_design_preview(preview, direction_id="direction-b")
    content = preview.read_text(encoding="utf-8")
    approval_path = design_preview_approval_path(preview)

    assert payload["direction_id"] == "direction-b"
    assert payload["decision_ids"]
    assert 'data-preview-status="approved"' in content
    assert 'data-approved-direction="direction-b"' in content
    assert '"status": "approved"' in content
    assert '"approved_direction": "direction-b"' in content
    assert approval_path.is_file()
    assert lint_design_preview_file(preview, level="ready") == []

    preview.write_text(content.replace("Compare all", "Compare directions"), encoding="utf-8")
    diagnostics = lint_design_preview_file(preview, level="ready")

    assert any(item.code == "preview-stale-approval-sidecar" for item in diagnostics)


def test_design_preview_approve_cli_writes_immutable_approval(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    preview = Path(".specify/design/previews/round-02.html")
    preview.parent.mkdir(parents=True)
    preview.write_text(_candidate_preview(), encoding="utf-8")

    result = runner.invoke(
        app,
        ["design", "approve", str(preview), "--direction", "direction-c", "--format", "json"],
    )

    assert result.exit_code == 0
    assert design_preview_approval_path(preview).is_file()
    assert '"direction_id": "direction-c"' in result.output


def test_design_preview_cli_scaffolds_and_lints_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    output = Path(".specify/design/previews/round-01.html")

    scaffold_result = runner.invoke(app, ["design", "preview", "--out", str(output)])

    assert scaffold_result.exit_code == 0
    assert output.exists()
    output.write_text(_candidate_preview(), encoding="utf-8")

    lint_result = runner.invoke(
        app,
        ["design", "preview-lint", str(output), "--level", "ready"],
    )

    assert lint_result.exit_code == 0
    assert "valid at ready level" in lint_result.output


def test_design_preview_asset_is_packaged_and_installed_by_shared_template_copy() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert (
        '"templates/design-preview-template.html" = '
        '"specify_cli/core_pack/templates/design-preview-template.html"'
    ) in pyproject
    assert PREVIEW_TEMPLATE.exists()


def test_design_workflows_require_question_driven_three_option_iteration() -> None:
    classic = (
        REPO_ROOT / "templates" / "command-partials" / "design" / "shell.md"
    ).read_text(encoding="utf-8")
    advanced = (
        REPO_ROOT / "templates" / "advanced-skills" / "spx-design" / "SKILL.md"
    ).read_text(encoding="utf-8")
    combined = f"{classic}\n{advanced}".lower()

    assert "one high-impact design question at a time" in combined
    assert "exactly three" in combined
    assert "design-preview-template.html" in combined
    assert "round-" in combined
    assert "until the user approves" in combined
    assert "do not overwrite" in combined
    assert "approved_visual_ref" in combined
    assert "motion" in combined
    assert "prefers-reduced-motion" in combined
    assert "feature-level `ui-target.html`" in combined
