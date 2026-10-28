from __future__ import annotations

import json
import re
from pathlib import Path

from specify_cli.integrations.base import IntegrationBase


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ("fast", "quick", "implement", "debug")
CLASSIC_INCLUDE = (
    "{{spec-kit-include: "
    "../command-partials/common/autonomous-blocker-recovery.md}}"
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _compact(relative: str) -> str:
    return re.sub(r"\s+", " ", _read(relative)).lower()


def test_shared_recovery_contract_owns_project_control_plane_failures() -> None:
    contracts = (
        _compact(
            "templates/command-partials/common/autonomous-blocker-recovery.md"
        ),
        _compact("templates/advanced-skills/_shared/autonomous-blocker-recovery.md"),
    )

    for contract in contracts:
        for required in (
            "blocker category does not define the repair boundary",
            "launcher",
            "test harness",
            "dependency restoration",
            "build or startup tooling",
            "local service",
            "initial write scope",
            "expand the owned scope before editing",
            "same invocation",
            "resume the exact interrupted gate",
            "retry count alone",
            "do not invoke another user-invoked workflow",
        ):
            assert required in contract

        assert "credentials" in contract
        assert "protected external system" in contract
        assert "human decision" in contract


def test_four_classic_workflows_include_autonomous_recovery() -> None:
    for workflow in WORKFLOWS:
        command = _read(f"templates/commands/{workflow}.md")
        assert CLASSIC_INCLUDE in command, workflow


def test_every_classic_workflow_renders_recovery_once_before_its_body() -> None:
    templates = sorted((ROOT / "templates/commands").glob("*.md"))
    assert len(templates) == 29
    for template in templates:
        rendered = IntegrationBase.render_template_content(
            template.read_text(encoding="utf-8"), template_path=template
        )
        assert rendered.count("## Autonomous Blocker Recovery") == 1, template.name
        assert "every `sp-*` workflow" in rendered, template.name
        assert "{{spec-kit-include:" not in rendered, template.name


def test_recovery_contracts_preserve_gates_and_minimal_verification() -> None:
    for relative in (
        "templates/command-partials/common/autonomous-blocker-recovery.md",
        "templates/advanced-skills/_shared/autonomous-blocker-recovery.md",
    ):
        contract = _compact(relative)
        for guard in (
            "failed gate closed" if "advanced-skills" in relative else "failed gate remains closed",
            "independent acceptance",
            "read-only/review workflows",
            "verification budget",
            "narrowest meaningful repair check",
            "never edit runtime storage",
            "no new stage authority",
            "never successful completion",
        ):
            assert guard in contract, (relative, guard)


def test_four_spx_workflows_route_to_the_shared_recovery_reference() -> None:
    surface_map = json.loads(
        _read("templates/advanced-skills/_shared/surface-map.json")
    )
    assert (
        "_shared/autonomous-blocker-recovery.md"
        in surface_map["shared_references"]
    )

    for workflow in WORKFLOWS:
        skill = _compact(f"templates/advanced-skills/spx-{workflow}/SKILL.md")
        assert "read `references/autonomous-blocker-recovery.md`" in skill, workflow


def test_recovery_routes_preserve_parent_state_and_resume_the_failed_gate() -> None:
    expected = {
        "fast": (
            "enter autonomous recovery mode",
            "continue in the same invocation",
        ),
        "quick": (
            "preserve the quick workspace",
            "resume the blocked q item or verification point",
        ),
        "implement": (
            "preserve the task lifecycle",
            "resume the interrupted validation gate",
        ),
        "debug": (
            "preserve the debug session",
            "resume the original reproduction and verification path",
        ),
    }

    for profile_root in ("templates/commands", "templates/advanced-skills"):
        for workflow, phrases in expected.items():
            relative = (
                f"{profile_root}/{workflow}.md"
                if profile_root == "templates/commands"
                else f"{profile_root}/spx-{workflow}/SKILL.md"
            )
            contract = _compact(relative)
            for phrase in phrases:
                assert phrase in contract, (relative, phrase)


def test_recovery_routing_is_not_a_terminal_user_handoff() -> None:
    forbidden = {
        "templates/commands/fast.md": (
            "stop and redirect to the right workflow",
        ),
        "templates/advanced-skills/spx-fast/SKILL.md": (
            "report any escalation as a handoff and do not invoke another workflow",
        ),
        "templates/advanced-skills/spx-implement/SKILL.md": (
            "hand off unknown root causes to `$spx-debug` and stop",
        ),
        "templates/advanced-skills/spx-debug/references/investigation-contract.md": (
            "hand off to `$spx-quick` and stop",
        ),
    }

    for relative, phrases in forbidden.items():
        contract = _compact(relative)
        for phrase in phrases:
            assert phrase not in contract, (relative, phrase)
def test_recovery_preserves_explicit_cross_workflow_handoff_boundaries() -> None:
    expected = {
        "templates/commands/implement.md": (
            "stop and route to the owning upstream phase",
        ),
        "templates/command-references/debug/fix-gate.md": (
            "approved registered causal scope",
            "without invoking another user-invoked workflow",
            "use `/sp-specify` only when the user explicitly chooses",
        ),
        "templates/advanced-skills/spx-fast/SKILL.md": (
            "this invocation authorizes only this workflow stage",
            "do not invoke another workflow in this run",
        ),
        "templates/advanced-skills/spx-implement/references/execution-contract.md": (
            "every cross-workflow route is a handoff-and-stop boundary",
        ),
    }

    for relative, phrases in expected.items():
        contract = _compact(relative)
        for phrase in phrases:
            assert phrase in contract, (relative, phrase)
