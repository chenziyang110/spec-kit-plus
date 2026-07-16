import json
from pathlib import Path

import pytest

from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _compact(path: str) -> str:
    return " ".join(
        (PROJECT_ROOT / path).read_text(encoding="utf-8").lower().split()
    )


def test_shared_cognition_guidance_consumes_structured_rebuild_contract() -> None:
    surfaces = {
        "advanced": _compact(
            "templates/advanced-skills/_shared/project-cognition.md"
        ),
        "classic passive": _compact(
            "templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md"
        ),
        "classic planning": _compact(
            "templates/command-partials/common/planning-context-loading-gradient.md"
        ),
        "classic execution": _compact(
            "templates/command-partials/common/context-loading-gradient.md"
        ),
    }

    for label, content in surfaces.items():
        assert "rebuild_reasons[]" in content, label
        assert "recommended_next_action.action_id" in content, label
        assert "recommended_next_action.workflow_routes" in content, label
        assert "project_cognition.rebuild" in content, label
        assert "do not treat `recommended_next_action` as a string" in content, label
        assert "project_cognition.repair_status" in content, label
        assert "recommended_next_action.argv" in content, label

    assert "workflow_routes.advanced.steps" in surfaces["advanced"]
    for label in ("classic passive", "classic planning", "classic execution"):
        assert "workflow_routes.classic.steps" in surfaces[label], label

    for path in ("PROJECT-HANDBOOK.md", "templates/project-handbook-template.md"):
        handbook = _compact(path)
        assert "`recommended_next_action`" in handbook, path
        assert "object" in handbook, path
        assert "`rebuild_reasons[]`" in handbook, path
        assert "`spx-map-rebuild`" in handbook, path
        assert "`sp-map-scan`" in handbook and "`sp-map-build`" in handbook, path


def test_every_explicit_compass_readiness_consumer_routes_by_action_id() -> None:
    roots = (
        "templates/commands",
        "templates/command-partials",
        "templates/command-references",
        "templates/passive-skills",
        "templates/advanced-skills",
    )
    consumers: list[Path] = []
    for root in roots:
        for path in (PROJECT_ROOT / root).rglob("*.md"):
            content = path.read_text(encoding="utf-8").lower()
            if "compass --intent" in content and "needs_rebuild" in content:
                consumers.append(path)
                assert "recommended_next_action.action_id" in content, path
                assert "complete_scan_packets" in content, path

    assert consumers, "expected explicit Compass readiness consumers"


@pytest.mark.parametrize("integration_key", ("codex", "gemini"))
def test_rendered_classic_runtime_gates_use_structured_actions_and_pinned_cognition(
    tmp_path: Path,
    integration_key: str,
) -> None:
    project = tmp_path / f"{integration_key}-project"
    cognition = project / ".specify" / "bin" / "project-cognition-test"
    cognition.parent.mkdir(parents=True)
    cognition.write_text("fixture", encoding="utf-8")
    config = {
        "specify_launcher": {
            "command": "uvx --from git+https://example.test/spec-kit-plus.git@abc specify",
            "argv": [
                "uvx",
                "--from",
                "git+https://example.test/spec-kit-plus.git@abc",
                "specify",
            ],
        },
        "project_cognition_launcher": {
            "command": str(cognition),
            "argv": [str(cognition)],
        },
    }
    (project / ".specify" / "config.json").write_text(
        json.dumps(config, indent=2) + "\n",
        encoding="utf-8",
    )
    integration = get_integration(integration_key)
    assert integration is not None
    manifest = IntegrationManifest(integration_key, project)
    integration.setup(
        project,
        manifest,
        parsed_options={"workflow_profile": "classic"},
        script_type="sh",
    )
    generated_root = integration.commands_dest(project)
    contents = [
        path.read_text(encoding="utf-8")
        for path in generated_root.rglob("*")
        if path.is_file() and path.suffix.lower() in {".md", ".toml"}
    ]
    runtime_gates = [
        content
        for content in contents
        if "Project Cognition Advisory Gate" in content
    ]

    assert runtime_gates
    for content in runtime_gates:
        assert "recommended_next_action.action_id" in content
        assert "complete_scan_packets" in content
        assert "project_cognition.repair_status" in content
        assert cognition.name in content
        assert "{{specify-subcmd:" not in content
