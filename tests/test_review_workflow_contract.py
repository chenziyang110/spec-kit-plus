from pathlib import Path
import json

import pytest


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8").lower()


def _read_tree(relative: str) -> str:
    directory = ROOT / relative
    assert directory.is_dir(), f"missing review contract directory: {relative}"
    files = sorted(directory.rglob("*.md"))
    assert files, f"review contract directory is empty: {relative}"
    return "\n".join(path.read_text(encoding="utf-8").lower() for path in files)


def _flat(content: str) -> str:
    return " ".join(content.split())


def _review_profile_contracts() -> tuple[tuple[str, str], ...]:
    return (
        (
            "classic",
            "\n".join(
                (
                    _read("templates/commands/review.md"),
                    _read_tree("templates/command-partials/review"),
                    _read_tree("templates/command-references/review"),
                )
            ),
        ),
        (
            "advanced",
            "\n".join(
                (
                    _read("templates/advanced-skills/spx-review/SKILL.md"),
                    _read_tree("templates/advanced-skills/spx-review/references"),
                )
            ),
        ),
    )


@pytest.mark.parametrize(
    "relative",
    (
        "templates/commands/review.md",
        "templates/advanced-skills/spx-review/SKILL.md",
    ),
)
def test_review_workflow_surfaces_exist(relative: str) -> None:
    assert (ROOT / relative).is_file(), f"missing required review surface: {relative}"


def test_classic_review_proves_real_product_paths_and_repairs_findings() -> None:
    combined = "\n".join(
        (
            _read("templates/commands/review.md"),
            _read_tree("templates/command-partials/review"),
            _read_tree("templates/command-references/review"),
        )
    )

    # A review is a system-level usability gate, not another source-only audit.
    assert "real entrypoint" in combined or "real entry point" in combined
    assert "user journey" in combined
    for wiring_term in ("button", "route", "handler", "provider"):
        assert wiring_term in combined
    for evidence_kind in (
        "structure_snapshot",
        "visual_capture",
        "runtime_diagnostics",
    ):
        assert evidence_kind in combined

    # An understood defect is repaired in this stage and its exact path is rerun.
    assert "finding" in combined
    assert "repair" in combined
    assert "revalid" in combined or "rerun" in combined or "re-run" in combined
    assert "diagnos" in combined


def test_classic_review_uses_jit_subagent_packets_but_keeps_final_authority() -> None:
    combined = "\n".join(
        (
            _read("templates/commands/review.md"),
            _read_tree("templates/command-references/review"),
        )
    )

    assert "systemreviewpacket" in combined or "system review packet" in combined
    assert "just in time" in combined or "just-in-time" in combined
    assert "subagent" in combined or "worker" in combined
    assert "leader" in combined
    assert "final verdict" in combined
    assert "worker" in combined and (
        "must not declare" in combined
        or "cannot declare" in combined
        or "never authority" in combined
    )


def test_classic_review_final_claim_requires_fresh_integrated_evidence() -> None:
    combined = "\n".join(
        (
            _read("templates/commands/review.md"),
            _read_tree("templates/command-references/review"),
        )
    )

    assert "fingerprint" in combined or "source revision" in combined
    assert "stale" in combined
    assert "blocking finding" in combined or "blocking findings" in combined
    assert "mandatory scenario" in combined or "required scenario" in combined
    assert "{{invoke:accept}}" in combined
    assert "do not claim" in combined or "never claim" in combined


def test_spx_review_preserves_the_system_review_and_repair_contract() -> None:
    combined = "\n".join(
        (
            _read("templates/advanced-skills/spx-review/SKILL.md"),
            _read_tree("templates/advanced-skills/spx-review/references"),
        )
    )

    assert "real entrypoint" in combined or "real entry point" in combined
    assert "user journey" in combined
    for wiring_term in ("button", "route", "handler", "provider"):
        assert wiring_term in combined
    assert "finding" in combined and "repair" in combined
    assert "revalid" in combined or "rerun" in combined or "re-run" in combined
    assert "systemreviewpacket" in combined or "system review packet" in combined
    assert "leader" in combined and "final verdict" in combined
    assert "blocking finding" in combined or "blocking findings" in combined
    assert "fingerprint" in combined or "source revision" in combined
    assert "$spx-accept" in combined


@pytest.mark.parametrize(("profile", "combined"), _review_profile_contracts())
def test_review_has_independent_audit_fix_and_revalidation_waves(
    profile: str,
    combined: str,
) -> None:
    del profile
    flat = _flat(combined)

    assert "review/audit wave" in flat
    assert "read-only" in flat and "audit worker" in flat
    assert "fix wave" in flat and "fix worker" in flat
    assert "independent revalidation wave" in flat
    assert "repair author" in flat and (
        "must not verify" in flat or "cannot verify" in flat
    )
    assert "leader orchestrates" in flat and "subagent" in flat


@pytest.mark.parametrize(("profile", "combined"), _review_profile_contracts())
def test_review_leader_owns_zero_uncovered_coverage_and_all_joins(
    profile: str,
    combined: str,
) -> None:
    del profile
    flat = _flat(combined)

    assert "review universe" in flat
    assert "independent coverage discovery" in flat
    assert "zero uncovered" in flat
    assert "all packets joined" in flat
    assert "leader" in flat and "coverage" in flat
    assert "leader" in flat and "final verdict" in flat
    assert "worker" in flat and (
        "cannot declare coverage complete" in flat
        or "must not declare coverage complete" in flat
    )


@pytest.mark.parametrize(("profile", "combined"), _review_profile_contracts())
def test_approved_scope_defects_stay_inside_review_fix(
    profile: str,
    combined: str,
) -> None:
    flat = _flat(combined)

    assert "approved-scope defect" in flat
    assert "regardless of repair size" in flat
    assert "task omission" in flat
    assert "unknown root cause" in flat
    assert "review remains the stage owner" in flat
    assert "diagnostic packet" in flat

    if profile == "classic":
        assert "hand off to `{{invoke:debug}}`" not in flat
        assert "reopen `sp-implement`" not in flat
        assert "reopen `sp-tasks`" not in flat
    else:
        assert "hand off an unknown mechanism to `$spx-debug`" not in flat
        assert "reopen `$spx-implement`" not in flat
        assert "reopen `$spx-tasks`" not in flat


@pytest.mark.parametrize(("profile", "combined"), _review_profile_contracts())
def test_review_only_hands_off_for_upstream_truth_changes(
    profile: str,
    combined: str,
) -> None:
    del profile
    flat = _flat(combined)

    assert "only" in flat and "upstream truth" in flat
    assert "requirement truth" in flat
    assert "design truth" in flat
    assert "architecture truth" in flat
    assert "missing code" in flat and "not an upstream truth gap" in flat


def test_implement_hands_off_to_review_instead_of_acceptance() -> None:
    classic = _read("templates/commands/implement.md")
    advanced = _read("templates/advanced-skills/spx-implement/SKILL.md")

    assert "{{invoke:review}}" in classic
    assert "{{invoke:accept}}" not in classic
    assert "$spx-review" in advanced
    assert "recommend `$spx-accept`" not in advanced
    assert "stop" in classic and "stop" in advanced


def test_tasks_compile_review_obligations_before_implementation_handoff() -> None:
    task_index = json.loads(_read("templates/task-index-template.json"))
    classic = _read("templates/commands/tasks.md")
    advanced = _read("templates/advanced-skills/spx-tasks/SKILL.md")

    assert "review_obligations" in task_index
    for content in (classic, advanced):
        assert "review obligations" in content or "review_obligations" in content
        assert "acceptance" in content
        assert "consumer" in content
        assert "official entrypoint" in content


def test_tasks_freeze_the_requirement_delta_human_acceptance_universe() -> None:
    task_index = json.loads(_read("templates/task-index-template.json"))
    classic = _flat(_read("templates/commands/tasks.md"))
    advanced = _flat(_read("templates/advanced-skills/spx-tasks/SKILL.md"))

    assert "human_acceptance_obligations" in task_index
    assert "human_acceptance_scenarios" in task_index
    for content in (classic, advanced):
        assert "human acceptance universe" in content
        assert "new or changed requirement" in content
        assert "zero uncovered" in content
        assert "human_acceptance_obligations" in content
        assert "human_acceptance_scenarios" in content


def test_accept_requires_a_fresh_passed_review_and_routes_repairs_back_to_review() -> None:
    classic = "\n".join(
        (
            _read("templates/commands/accept.md"),
            _read_tree("templates/command-partials/accept"),
        )
    )
    advanced = "\n".join(
        (
            _read("templates/advanced-skills/spx-accept/SKILL.md"),
            _read_tree("templates/advanced-skills/spx-accept/references"),
        )
    )

    for content, review_route in (
        (classic, "{{invoke:review}}"),
        (advanced, "$spx-review"),
    ):
        assert "review" in content and "passed" in content
        assert "fingerprint" in content or "fresh" in content
        assert review_route in content

    assert "transition from `review`" in classic
    assert "transition from the validated\n`review`" in advanced or (
        "transition from the validated `review`" in advanced
    )
    assert "{{invoke:debug}}" not in classic
    assert "$spx-debug" not in advanced
    for content in (classic, advanced):
        assert "unknown mechanism" in content
        assert "review" in content and "diagnostic packet" in content


def test_accept_is_agent_assisted_human_e2e_for_the_frozen_requirement_delta() -> None:
    classic = _flat(
        "\n".join(
            (
                _read("templates/commands/accept.md"),
                _read_tree("templates/command-partials/accept"),
            )
        )
    )
    advanced = _flat(
        "\n".join(
            (
                _read("templates/advanced-skills/spx-accept/SKILL.md"),
                _read_tree("templates/advanced-skills/spx-accept/references"),
            )
        )
    )

    for content in (classic, advanced):
        assert "human acceptance universe" in content
        assert "new or changed requirement" in content
        assert "zero uncovered" in content
        assert "runtime identity" in content
        assert "test data" in content
        assert "agent" in content and "official entrypoint" in content
        assert "human performs" in content
        assert "do not repeat system review" in content
        assert "every failed observation first goes to the review leader" in content
        assert "accept does not diagnose" in content


def test_review_hands_off_the_frozen_human_acceptance_universe() -> None:
    for _profile, content in _review_profile_contracts():
        flat = _flat(content)
        assert "human acceptance universe" in flat
        assert "human_acceptance_obligations" in flat
        assert "human_acceptance_scenarios" in flat
        assert "runtime identity" in flat
        assert "does not prefill" in flat and "human" in flat and "pass" in flat
