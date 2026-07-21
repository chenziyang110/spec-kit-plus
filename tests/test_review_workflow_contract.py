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


def _implement_profile_contracts() -> tuple[tuple[str, str], ...]:
    return (
        (
            "classic",
            "\n".join(
                (
                    _read("templates/commands/implement.md"),
                    _read_tree("templates/command-partials/implement"),
                    _read_tree("templates/command-references/implement"),
                )
            ),
        ),
        (
            "advanced",
            "\n".join(
                (
                    _read("templates/advanced-skills/spx-implement/SKILL.md"),
                    _read_tree("templates/advanced-skills/spx-implement/references"),
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


@pytest.mark.parametrize(
    ("profile", "combined"), _review_profile_contracts(), ids=("classic", "advanced")
)
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


@pytest.mark.parametrize(
    ("profile", "combined"), _review_profile_contracts(), ids=("classic", "advanced")
)
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


@pytest.mark.parametrize(
    ("profile", "combined"), _review_profile_contracts(), ids=("classic", "advanced")
)
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


@pytest.mark.parametrize(
    ("profile", "combined"), _review_profile_contracts(), ids=("classic", "advanced")
)
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


def test_accept_requires_a_fresh_passed_review_and_routes_repairs_back_to_review() -> (
    None
):
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
        assert "review" in content and ("passed" in content or "approved" in content)
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
        assert "test data" in content or "acceptance data" in content
        assert "agent" in content and "official entrypoint" in content
        assert "human performs" in content
        assert "do not repeat system review" in content
        assert "every failed observation first goes to the review leader" in content
        assert "accept does not diagnose" in content
        assert "repair_history" in content
        assert "cli alone" in content
        assert "resolved" in content


def test_review_hands_off_the_frozen_human_acceptance_universe() -> None:
    for _profile, content in _review_profile_contracts():
        flat = _flat(content)
        assert "human acceptance universe" in flat
        assert "human_acceptance_obligations" in flat
        assert "human_acceptance_scenarios" in flat
        assert "reviewed_runtime_targets" in flat
        assert "immutable" in flat
        assert (
            ("does not prefill" in flat or "never prefills" in flat)
            and "human" in flat
            and "pass" in flat
        )


@pytest.mark.parametrize("profile", ("classic", "advanced"))
def test_review_targets_are_bound_to_identity_and_artifact_bytes(profile: str) -> None:
    flat = _flat(dict(_review_profile_contracts())[profile])

    assert "identity_evidence_ref" in flat
    assert "identity_evidence_sha256" in flat
    assert "review-evidence/cycle-<n>/" in flat
    assert "top-level `version`" in flat and "status" in flat and "ready" in flat
    for field in (
        "environment_ref",
        "instance_ref",
        "configuration_ref",
        "reviewed_snapshot_sha256",
        "review_scenario_ids",
        "ready_evidence_refs",
    ):
        assert field in flat
    assert "artifact_ref" in flat and "artifact_sha256" in flat
    assert "build" in flat and "deployment" in flat
    assert "current bytes" in flat
    assert "implementation snapshot" in flat
    assert "review-evidence/" in flat and "review-results/" in flat


def test_accept_preserves_review_identity_evidence_fields_read_only() -> None:
    surfaces = (
        "\n".join(
            (
                _read("templates/commands/accept.md"),
                _read_tree("templates/command-partials/accept"),
            )
        ),
        "\n".join(
            (
                _read("templates/advanced-skills/spx-accept/SKILL.md"),
                _read_tree("templates/advanced-skills/spx-accept/references"),
            )
        ),
    )

    for content in surfaces:
        flat = _flat(content)
        assert "identity_evidence_ref" in flat
        assert "identity_evidence_sha256" in flat
        assert "read-only" in flat
        assert "exact immutable projection" in flat


def test_spx_plan_always_loads_and_restates_the_exact_acceptance_denominator() -> None:
    skill = _flat(_read("templates/advanced-skills/spx-plan/SKILL.md"))

    assert "always read `references/planning-contract.md`" in skill
    assert (
        "`references/planning-contract.md` and `references/consequence-gate.md` "
        "only on its triggers"
    ) not in skill
    assert "acceptance_refs" in skill
    assert "spec-contract.json#/acceptance_criteria/0..n-1" in skill
    assert "complete" in skill
    assert "unique ordered" in skill
    assert "exactly once" in skill


@pytest.mark.parametrize("profile", ("classic", "advanced"))
def test_implement_preserves_the_live_acceptance_contract_for_review(
    profile: str,
) -> None:
    flat = _flat(dict(_implement_profile_contracts())[profile])

    assert "live spec, plan, and tasks" in flat
    assert "exact complete `acceptance_refs` denominator" in flat
    assert "acceptance_refs" in flat
    assert "acceptance_denominator_sha256" in flat
    assert "frozen human acceptance universe" in flat
    assert "human_acceptance_obligations" in flat
    assert "human_acceptance_scenarios" in flat
    assert "human_acceptance_contract_sha256" in flat
    assert "unchanged" in flat
    assert "reviewed_runtime_targets" in flat
    assert (
        "only review creates" in flat
        or "only `sp-review` creates" in flat
        or "only `$spx-review` creates" in flat
        or "review exclusively owns" in flat
    )


@pytest.mark.parametrize("profile", ("classic", "advanced"))
def test_any_fix_requires_fresh_evidence_for_the_full_review_matrix(
    profile: str,
) -> None:
    flat = _flat(dict(_review_profile_contracts())[profile])

    assert "after any fix" in flat
    assert (
        "all required review scenarios" in flat
        or "every required review scenario" in flat
    )
    assert "final reviewed snapshot" in flat
    assert (
        "recapture all required evidence" in flat
        or "recapture every required evidence" in flat
    )
    assert "no pre-fix scenario evidence can satisfy approval" in flat
    assert "fix_assignments_sha256" in flat
    assert "evidence_manifest_ref" in flat
    assert "scenario_evidence" in flat
    assert "cycle 1" in flat
    assert "byte" in flat and "digest" in flat


def test_classic_routing_summarizes_the_acceptance_repair_cycle_contract() -> None:
    routing = _flat(
        _read("templates/passive-skills/spec-kit-workflow-routing/SKILL.md")
    )

    assert "new review cycle" in routing
    assert "reviewed_runtime_targets" in routing and "immutable" in routing
    assert "structured human confirmation" in routing
    assert (
        "reset every frozen human acceptance scenario" in routing
        or "invalidates every prior human pass and confirmation" in routing
        or "invalidate every human result" in routing
    )
    assert "full frozen human acceptance universe" in routing


def test_diagnostic_packets_map_to_the_review_state_scenario_kind() -> None:
    contracts = (
        _flat(_read("templates/command-references/review/subagent-review-contract.md")),
        _flat(
            _read("templates/advanced-skills/spx-review/references/worker-contract.md")
        ),
    )
    schema = json.loads(_read("templates/review-state-schema.json"))
    kinds = schema["properties"]["review_assignments"]["items"]["properties"]["kind"][
        "enum"
    ]

    for contract in contracts:
        assert "diagnostic" in contract and "packet" in contract
        assert "scenario_review" in contract
        assert "review_assignments" in contract or "review-state" in contract
    assert "scenario_review" in kinds
    assert "diagnostic" not in kinds


def test_spx_accept_is_discoverable_as_the_post_review_stage() -> None:
    frontmatter = (
        (ROOT / "templates/advanced-skills/spx-accept/SKILL.md")
        .read_text(encoding="utf-8")
        .split("---", 2)[1]
        .lower()
    )

    assert "post-review" in frontmatter
    assert "post-implementation" not in frontmatter


def test_spx_implement_does_not_split_the_system_review_acceptance_sentence() -> None:
    skill = _flat(_read("templates/advanced-skills/spx-implement/SKILL.md"))

    assert "system review. acceptance." not in skill
    assert "task completion is not system review. never claim completion" in skill
