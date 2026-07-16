from pathlib import Path


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
