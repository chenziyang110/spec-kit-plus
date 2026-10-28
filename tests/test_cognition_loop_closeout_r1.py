"""R1 exercises installed contracts, rather than treating template presence as proof."""

from pathlib import Path

import pytest

from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest


@pytest.mark.parametrize("integration_key", ["codex", "claude"])
def test_r1_installed_profiles_share_order_and_preserve_map_companions(
    tmp_path: Path, integration_key: str
) -> None:
    integration = get_integration(integration_key)
    roots = {}
    for profile in ("classic", "advanced"):
        project = tmp_path / profile
        manifest = IntegrationManifest(integration_key, project)
        integration.setup(
            project,
            manifest,
            parsed_options={"workflow_profile": profile},
            script_type="ps",
        )
        roots[profile] = integration.skills_dest(project)

    classic = roots["classic"]
    quick = (classic / "sp-quick" / "SKILL.md").read_text(encoding="utf-8")
    quick_ref = (
        classic / "sp-quick" / "references" / "validation-and-closeout.md"
    ).read_text(encoding="utf-8")
    implement_ref = (
        classic / "sp-implement" / "references" / "branch-review-and-closeout.md"
    ).read_text(encoding="utf-8")
    assert "Only failed apply uses mark-dirty" not in quick
    assert "Only when no trustworthy intent can be formed" in quick
    assert "do not stamp a second receipt" in quick_ref
    assert "3. Durable receipt:" not in quick_ref
    assert "--result-state ready|no_op|mark-dirty|partial" not in quick_ref
    assert "Inspect/repair/replay an existing durable intent" in implement_ref
    terminal = implement_ref.index("- only after the cognition receipt allows close")
    assert implement_ref.index("- update project cognition once") < terminal

    advanced = roots["advanced"]
    implement = (advanced / "spx-implement" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    advanced_quick = (advanced / "spx-quick" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    planner = implement.index("After verified repository changes, require")
    terminal = implement.index("Once the receipt allows close, run", planner)
    assert planner < terminal
    assert "After verified repository changes, call" not in implement
    assert "only an update failure uses mark-dirty" not in implement
    assert "persisted intent must follow returned inspect/repair/replay actions" in implement
    assert "An existing durable intent requires returned inspect/repair/replay" in advanced_quick
    assert "For an update failure only" not in advanced_quick
    assert "do not stamp a second receipt" in advanced_quick
    for content in (quick, quick_ref, implement_ref, implement, advanced_quick):
        assert "cognition.closeout.recovery.v1" in content

    for companion in ("sp-map-scan", "sp-map-build", "sp-map-update"):
        classic_files = {
            file.relative_to(classic / companion): file.read_bytes()
            for file in (classic / companion).rglob("*")
            if file.is_file()
        }
        advanced_files = {
            file.relative_to(advanced / companion): file.read_bytes()
            for file in (advanced / companion).rglob("*")
            if file.is_file()
        }
        assert classic_files == advanced_files
    assert not (advanced / "spec-kit-project-cognition-gate").exists()
    assert len(list(advanced.glob("spx-*/SKILL.md"))) == 30
    # Claude's normal setup intentionally excludes the Codex-only sp-teams
    # entry; this integration-specific inventory is not the source denominator.
    classic_count = 29 if integration_key == "codex" else 28
    assert len(list(classic.glob("sp-*/SKILL.md"))) == classic_count
