from __future__ import annotations

import json
from pathlib import Path
import re

from typer.testing import CliRunner

from specify_cli import app
from specify_cli.design import lint_ui_target_file, scaffold_ui_target


REPO_ROOT = Path(__file__).resolve().parents[1]
UI_TARGET_TEMPLATE = REPO_ROOT / "templates" / "ui-target-template.html"
runner = CliRunner()


def _ready_ui_target() -> str:
    content = UI_TARGET_TEMPLATE.read_text(encoding="utf-8")
    content = content.replace('data-status="draft"', 'data-status="candidate"')
    content = content.replace("__FIDELITY_MODE__", "high")
    content = content.replace('"configured": false', '"configured": true')
    content = content.replace(
        "__APPROVED_VISUAL_REF__",
        ".specify/design/previews/round-01.html#direction-a",
    )
    content = content.replace("__APPROVED_DIRECTION_ID__", "direction-a")
    content = content.replace("__APPROVED_PREVIEW_SHA256__", "a" * 64)
    content = content.replace("__APPROVED_MANIFEST_SHA256__", "b" * 64)
    content = content.replace(
        "__DESIGN_DECISION_IDS__",
        'DS-COMP-001", "DS-RESP-001',
    )
    return re.sub(r"__[A-Z0-9_]+__", "Configured content", content)


def test_bundled_ui_target_is_a_valid_structural_scaffold() -> None:
    assert lint_ui_target_file(UI_TARGET_TEMPLATE) == []
    content = UI_TARGET_TEMPLATE.read_text(encoding="utf-8")
    assert "spec-kit-ui-target-manifest-v1" in content
    assert "@container" in content
    assert "prefers-reduced-motion: reduce" in content
    assert "location.hash" in content


def test_ready_ui_target_binds_approval_decisions_states_and_viewports(
    tmp_path: Path,
) -> None:
    target = tmp_path / "ui-target.html"
    target.write_text(_ready_ui_target(), encoding="utf-8")

    assert lint_ui_target_file(target, level="ready") == []


def test_ui_target_lint_rejects_remote_runtime_and_inline_handlers(
    tmp_path: Path,
) -> None:
    target = tmp_path / "ui-target.html"
    content = _ready_ui_target().replace(
        '<button type="button" data-width="390"',
        '<button type="button" onclick="fetch(\'/api\')" data-width="390"',
        1,
    )
    target.write_text(content, encoding="utf-8")

    diagnostics = lint_ui_target_file(target, level="ready")

    assert any(item.code == "ui-target-inline-event-handler" for item in diagnostics)
    assert any(item.code == "ui-target-forbidden-runtime" for item in diagnostics)


def test_scaffold_and_cli_lint_use_the_shared_ui_target_template(
    tmp_path: Path,
) -> None:
    target = tmp_path / "ui-target.html"

    assert scaffold_ui_target(target) == target
    result = runner.invoke(
        app,
        ["design", "ui-target-lint", str(target), "--format", "json"],
    )

    assert result.exit_code == 0
    assert json.loads(result.output)["ok"] is True


def test_ui_target_cli_scaffolds_to_requested_path(tmp_path: Path) -> None:
    target = tmp_path / "feature" / "ui-target.html"

    result = runner.invoke(
        app,
        ["design", "ui-target", "--out", str(target)],
    )

    assert result.exit_code == 0
    assert target.read_text(encoding="utf-8") == UI_TARGET_TEMPLATE.read_text(
        encoding="utf-8"
    )
