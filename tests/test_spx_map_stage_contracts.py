from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ADVANCED_SKILLS = ROOT / "templates" / "advanced-skills"


def _normalized(path: Path) -> str:
    return re.sub(r"\s+", " ", path.read_text(encoding="utf-8").lower())


def test_shared_cognition_recovery_is_a_handoff_not_implicit_execution() -> None:
    content = _normalized(ADVANCED_SKILLS / "_shared" / "project-cognition.md")

    assert "recommend the matching maintenance skill" in content
    assert "do not invoke `$spx-map-rebuild` or `$spx-map-update`" in content
    assert "a recovery handoff is not authorization to execute another workflow" in content


def test_independent_map_stages_preserve_explicit_stop_boundaries() -> None:
    scan = _normalized(ADVANCED_SKILLS / "spx-map-scan" / "SKILL.md")
    build = _normalized(ADVANCED_SKILLS / "spx-map-build" / "SKILL.md")
    update = _normalized(ADVANCED_SKILLS / "spx-map-update" / "SKILL.md")

    for skill in (scan, build, update):
        assert "this invocation authorizes only this workflow stage" in skill

    assert "do not invoke `$spx-map-build`" in scan
    assert "do not invoke `$spx-map-scan`" in build
    assert "do not invoke `$spx-map-rebuild`" in update


def test_map_update_has_deterministic_validation_and_freshness_closeout() -> None:
    skill = _normalized(ADVANCED_SKILLS / "spx-map-update" / "SKILL.md")
    gates = _normalized(
        ADVANCED_SKILLS / "spx-map-update" / "references" / "update-gates.md"
    )

    for required in (
        "specify-runtime cognition validate-build --format json",
        "specify-runtime cognition complete-refresh --format json",
        "specify-runtime cognition record-refresh --reason map-update --format json",
    ):
        assert required in skill

    assert "`result_state=ready` or `result_state=no_op` requires" in gates
    assert "`status=ok` and `readiness=query_ready`" in gates
    assert "matching validation receipt" in gates
    assert "not an ordinary closeout branch" in gates
    assert "never call `complete-refresh`" in gates


def test_non_orchestrator_support_skills_stop_before_followup_workflows() -> None:
    for skill_name in (
        "spx-analyze",
        "spx-checklist",
        "spx-constitution",
        "spx-design",
        "spx-discussion",
        "spx-fast",
        "spx-prd-scan",
        "spx-quick",
        "spx-team",
    ):
        content = _normalized(ADVANCED_SKILLS / skill_name / "SKILL.md")
        assert "this invocation authorizes only this workflow stage" in content
        assert "do not invoke another workflow in this run" in content
