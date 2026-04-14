from specify_cli.codex_team.auto_dispatch import (
    PassiveParallelismLane,
    PassiveParallelismRequest,
    assess_passive_parallelism,
)


def test_assess_passive_parallelism_triggers_for_multi_reference_analysis():
    decision = assess_passive_parallelism(
        PassiveParallelismRequest(
            stage="analysis",
            lanes=[
                PassiveParallelismLane(
                    lane_id="refs-api",
                    summary="Inspect the API contract",
                    references=("docs/api.md",),
                ),
                PassiveParallelismLane(
                    lane_id="refs-db",
                    summary="Inspect the schema notes",
                    references=("docs/schema.md",),
                ),
            ],
        )
    )

    assert decision.should_trigger is True
    assert decision.reason == "multi_reference_analysis"
    assert decision.dispatch_payload == {
        "stage": "analysis",
        "lanes": [
            {
                "lane_id": "refs-api",
                "summary": "Inspect the API contract",
                "references": ["docs/api.md"],
                "write_scopes": [],
                "low_risk_preparation": False,
            },
            {
                "lane_id": "refs-db",
                "summary": "Inspect the schema notes",
                "references": ["docs/schema.md"],
                "write_scopes": [],
                "low_risk_preparation": False,
            },
        ],
    }


def test_assess_passive_parallelism_does_not_trigger_for_unclear_or_tightly_coupled_work():
    unclear = assess_passive_parallelism(
        PassiveParallelismRequest(
            stage="analysis",
            scope_clear=False,
            lanes=[
                PassiveParallelismLane(
                    lane_id="refs-api",
                    summary="Inspect the API contract",
                    references=("docs/api.md",),
                ),
                PassiveParallelismLane(
                    lane_id="refs-db",
                    summary="Inspect the schema notes",
                    references=("docs/schema.md",),
                ),
            ],
        )
    )
    coupled = assess_passive_parallelism(
        PassiveParallelismRequest(
            stage="analysis",
            tightly_coupled=True,
            lanes=[
                PassiveParallelismLane(
                    lane_id="refs-api",
                    summary="Inspect the API contract",
                    references=("docs/api.md",),
                ),
                PassiveParallelismLane(
                    lane_id="refs-db",
                    summary="Inspect the schema notes",
                    references=("docs/schema.md",),
                ),
            ],
        )
    )

    assert unclear.should_trigger is False
    assert unclear.reason == "unclear_scope"
    assert unclear.dispatch_payload is None
    assert coupled.should_trigger is False
    assert coupled.reason == "tightly_coupled"
    assert coupled.dispatch_payload is None


def test_assess_passive_parallelism_does_not_trigger_for_duplicate_reference_sets():
    decision = assess_passive_parallelism(
        PassiveParallelismRequest(
            stage="analysis",
            lanes=[
                PassiveParallelismLane(
                    lane_id="refs-a",
                    summary="Inspect overlapping reference set A",
                    references=("docs/api.md", "docs/schema.md"),
                ),
                PassiveParallelismLane(
                    lane_id="refs-b",
                    summary="Inspect overlapping reference set B",
                    references=("docs/schema.md", "docs/api.md"),
                ),
            ],
        )
    )

    assert decision.should_trigger is False
    assert decision.reason == "duplicated_reference_sets"
    assert decision.dispatch_payload is None


def test_assess_passive_parallelism_triggers_for_independent_capability_planning():
    decision = assess_passive_parallelism(
        PassiveParallelismRequest(
            stage="enhancement",
            lanes=[
                PassiveParallelismLane(
                    lane_id="cap-auth",
                    summary="Plan auth enhancement",
                    write_scopes=("src/auth",),
                    low_risk_preparation=True,
                ),
                PassiveParallelismLane(
                    lane_id="cap-billing",
                    summary="Plan billing enhancement",
                    write_scopes=("src/billing",),
                    low_risk_preparation=True,
                ),
            ],
        )
    )

    assert decision.should_trigger is True
    assert decision.reason == "independent_capability_planning"
    assert decision.dispatch_payload == {
        "stage": "enhancement",
        "lanes": [
            {
                "lane_id": "cap-auth",
                "summary": "Plan auth enhancement",
                "references": [],
                "write_scopes": ["src/auth"],
                "low_risk_preparation": True,
            },
            {
                "lane_id": "cap-billing",
                "summary": "Plan billing enhancement",
                "references": [],
                "write_scopes": ["src/billing"],
                "low_risk_preparation": True,
            },
        ],
    }


def test_assess_passive_parallelism_does_not_trigger_when_write_scopes_overlap():
    decision = assess_passive_parallelism(
        PassiveParallelismRequest(
            stage="enhancement",
            lanes=[
                PassiveParallelismLane(
                    lane_id="cap-auth-ui",
                    summary="Plan auth UI enhancement",
                    write_scopes=("src/auth/ui",),
                    low_risk_preparation=True,
                ),
                PassiveParallelismLane(
                    lane_id="cap-auth-api",
                    summary="Plan auth API enhancement",
                    write_scopes=("src/auth",),
                    low_risk_preparation=True,
                ),
            ],
        )
    )

    assert decision.should_trigger is False
    assert decision.reason == "overlapping_write_scopes"
    assert decision.dispatch_payload is None


def test_assess_passive_parallelism_rejects_broad_later_phase_implementation_lanes():
    decision = assess_passive_parallelism(
        PassiveParallelismRequest(
            stage="enhancement",
            lanes=[
                PassiveParallelismLane(
                    lane_id="impl-api",
                    summary="Implement later-phase API flow",
                    write_scopes=("src/api",),
                    low_risk_preparation=False,
                ),
                PassiveParallelismLane(
                    lane_id="impl-ui",
                    summary="Implement later-phase UI flow",
                    write_scopes=("src/ui",),
                    low_risk_preparation=False,
                ),
            ],
        )
    )

    assert decision.should_trigger is False
    assert decision.reason == "unsafe_preparation"
    assert decision.dispatch_payload is None
