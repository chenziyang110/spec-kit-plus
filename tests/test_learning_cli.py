import json
import hashlib
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from specify_cli import app
from tests.conftest import seed_existing_workflow_state, strip_ansi
from specify_cli.debug.persistence import MarkdownPersistenceHandler
from specify_cli.debug.schema import (
    DebugGraphState,
    DebugStatus,
    RootCause,
    ValidationCheck,
)
from specify_cli.learnings import (
    AutoCaptureSuggestion,
    assess_learning_candidate,
    build_learning_paths,
    capture_auto_learning,
    capture_learning,
    learning_metrics_payload,
    learning_review_status,
    list_learning_summaries,
    normalize_command_name,
    read_learning_entries,
    sanitize_agent_text,
    show_learning_detail,
    start_learning_session,
    promote_learning,
    review_learning,
)
from specify_cli.learning_policy import (
    LearningPolicyError,
    learning_policy_digest,
    parse_learning_policy,
)
from specify_cli.launcher import SpecifyLauncherSpec, render_command, write_project_specify_launcher_config
from specify_cli.workflow_runtime import (
    complete_workflow_stage,
    enter_workflow,
    transition_workflow,
)


pytestmark = pytest.mark.usefixtures("unified_runtime_env")


runner = CliRunner()


def test_project_learning_assessment_fixture_matches_python_compatibility() -> None:
    fixture = json.loads(
        (Path(__file__).parent / "fixtures" / "project_learning_assessment_v1.json").read_text(
            encoding="utf-8"
        )
    )
    for case in fixture["text_cases"]:
        policy = parse_learning_policy(case.get("policy"))
        sanitized, labels = sanitize_agent_text(case["input"], policy=policy)
        assert labels == case["expected_labels"], case["id"]
        if "expected_output" in case:
            assert sanitized == case["expected_output"], case["id"]
        assert all(value in sanitized for value in case["expected_contains"]), case[
            "id"
        ]
        assert not any(
            value in sanitized for value in case["forbidden_contains"]
        ), case["id"]

    for case in fixture["assessment_cases"]:
        assessment = assess_learning_candidate(
            source=case["source"],
            learning_type=case["learning_type"],
            signal_strength=case["signal_strength"],
            occurrences=case["occurrences"],
            summary=case["summary"],
            evidence=case["evidence"],
            recommended_action=case["recommended_action"],
            trigger_signals=case["trigger_signals"],
            policy=parse_learning_policy(case.get("policy")),
        )
        assert assessment.learning_value_tier == case["expected_value_tier"], case[
            "id"
        ]
        assert list(assessment.learning_value_reason_codes) == case[
            "expected_reason_codes"
        ], case["id"]
        assert assessment.assessment_decision == case["expected_decision"], case[
            "id"
        ]


def test_project_learning_fingerprint_matches_cross_runtime_golden() -> None:
    from specify_cli.learning_policy import default_learning_policy
    from specify_cli.learnings import _snapshot_fingerprint

    suggestion = AutoCaptureSuggestion(
        learning_type="tooling_trap",
        recurrence_key="sp-plan.runtime-boundary",
        signal_strength="medium",
        summary="Verify the runtime boundary first.",
        evidence="The runner mismatch caused the failure.",
    )

    assert _snapshot_fingerprint(
        "sp-plan",
        "specs/demo/workflow-state.md",
        [suggestion],
        policy=default_learning_policy(),
    ) == "47ba691a336c90c16cc5dc83101eea72bc29152ede042211b44158777200644e"


def test_project_learning_policy_digest_matches_cross_runtime_golden() -> None:
    policy = parse_learning_policy(
        {
            "detectors": {
                "secret_prefixes": ["Acme_"],
                "sensitive_key_names": ["customer_secret"],
                "business_id_prefixes": ["CUST-"],
                "sensitive_terms": ["Project Zephyr"],
            },
            "deferred_review_days": 14,
        }
    )

    assert learning_policy_digest(policy) == (
        "bca349b678b400f54197abc387a0b0441ab3087fc7fb75c63c936753f4da98d1"
    )


def test_learning_policy_detector_order_is_overlap_safe_and_order_independent() -> None:
    forward = parse_learning_policy(
        {"detectors": {"sensitive_terms": ["Project", "Project Zephyr"]}}
    )
    reverse = parse_learning_policy(
        {"detectors": {"sensitive_terms": ["Project Zephyr", "Project"]}}
    )

    assert forward.detectors.sensitive_terms == ("Project Zephyr", "Project")
    assert forward == reverse
    assert learning_policy_digest(forward) == learning_policy_digest(reverse)
    assert sanitize_agent_text(
        "Project Zephyr requires review.", policy=forward
    ) == (
        "[REDACTED_ORG_TERM] requires review.",
        ["organization_sensitive"],
    )


def test_learning_policy_invalid_read_falls_back_but_writes_fail_closed(
    tmp_path: Path,
) -> None:
    _seed_learning_templates(tmp_path)
    config_path = tmp_path / ".specify" / "config.json"
    config_path.write_text('{"project_learning": null}\n', encoding="utf-8")
    before = {
        path.relative_to(tmp_path).as_posix(): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }

    payload = list_learning_summaries(tmp_path, command_name="plan")

    assert "project_learning_policy_invalid:using_builtin_policy" in payload[
        "warnings"
    ]
    assert before == {
        path.relative_to(tmp_path).as_posix(): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    with pytest.raises(LearningPolicyError, match="write was rejected"):
        capture_learning(
            tmp_path,
            command_name="plan",
            learning_type="workflow_gap",
            summary="Preserve the route.",
            evidence="The route was lost.",
        )


def test_learning_capture_auto_dry_run_is_compact_and_zero_mutation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_learning_templates(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source = workspace / "state.md"
    source.write_text("first snapshot\n", encoding="utf-8")

    def suggest(*_args, **_kwargs):
        return source, [
            AutoCaptureSuggestion(
                learning_type="tooling_trap",
                summary="Verify the runner boundary before changing code.",
                evidence="The runner boundary caused the failure.",
                recurrence_key="sp-quick.runner-boundary",
                signal_strength="medium",
                recommended_action="Check the runner boundary first.",
                trigger_signals=("tooling_trap",),
            )
        ]

    monkeypatch.setattr("specify_cli.learnings._suggest_quick_auto_capture", suggest)
    before = {
        path.relative_to(tmp_path).as_posix(): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }

    payload = capture_auto_learning(
        tmp_path,
        command_name="quick",
        workspace=Path("workspace"),
        dry_run=True,
    )

    assert payload["status"] == "dry-run"
    assert payload["captured"] == []
    assert set(payload["assessed"][0]) == {
        "type",
        "summary",
        "action",
        "recurrence_key",
        "assessment",
    }
    assert before == {
        path.relative_to(tmp_path).as_posix(): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }


def test_learning_policy_added_after_storage_redacts_read_boundary_without_write(
    tmp_path: Path,
) -> None:
    _seed_learning_templates(tmp_path)
    capture_learning(
        tmp_path,
        command_name="debug",
        learning_type="pitfall",
        summary="Project Zephyr requires the fallback route.",
        evidence="Project Zephyr failed on the primary route.",
        recurrence_key="sp-debug.project-zephyr-fallback",
    )
    config_path = tmp_path / ".specify" / "config.json"
    config_path.write_text(
        json.dumps(
            {
                "project_learning": {
                    "detectors": {"sensitive_terms": ["Project Zephyr"]}
                }
            }
        ),
        encoding="utf-8",
    )
    candidates = build_learning_paths(tmp_path).candidates
    before = candidates.read_bytes()

    card = list_learning_summaries(tmp_path, command_name="debug")["items"][0]
    detail = show_learning_detail(tmp_path, learning_ref=card["ref"])
    serialized = json.dumps({"card": card, "detail": detail})

    assert "Project Zephyr" not in serialized
    assert "redacted-org-term" in card["ref"]
    assert candidates.read_bytes() == before


def test_learning_policy_added_after_unknown_command_keeps_legacy_learning_consumable(
    tmp_path: Path,
) -> None:
    _seed_learning_templates(tmp_path)
    capture_learning(
        tmp_path,
        command_name="zephyr-flow",
        learning_type="pitfall",
        summary="Preserve the custom workflow boundary.",
        evidence="The custom workflow boundary changed future action.",
        recurrence_key="sp-zephyr-flow.custom-boundary",
    )
    (tmp_path / ".specify" / "config.json").write_text(
        json.dumps(
            {
                "project_learning": {
                    "detectors": {"sensitive_terms": ["zephyr"]}
                }
            }
        ),
        encoding="utf-8",
    )
    paths = build_learning_paths(tmp_path)
    before = {
        path: path.read_bytes()
        for path in (
            paths.candidates,
            paths.confirmed_learnings,
            paths.project_rules,
            paths.learning_index,
        )
        if path.is_file()
    }

    listed = list_learning_summaries(tmp_path, command_name="zephyr-flow")

    assert listed["command"] == "sp-other"
    assert len(listed["items"]) == 1
    assert "sp-other" in listed["items"][0]["applies_to"]
    assert "zephyr" not in json.dumps(listed).lower()
    assert before == {path: path.read_bytes() for path in before}


def test_learning_review_queue_metrics_and_status_are_aggregate_safe(
    tmp_path: Path,
) -> None:
    _seed_learning_templates(tmp_path)
    review_learning(
        tmp_path,
        command_name="debug",
        decision="deferred",
        rationale="Wait for token=private-value from ops@example.com.",
    )
    status_before = learning_review_status(tmp_path, command_name="debug")
    with pytest.raises(ValueError, match="cannot be closed"):
        review_learning(
            tmp_path,
            command_name="debug",
            decision="none",
        )
    with pytest.raises(ValueError, match="no matching durable"):
        review_learning(
            tmp_path,
            command_name="debug",
            decision="captured",
        )

    capture = capture_learning(
        tmp_path,
        command_name="debug",
        learning_type="recovery_path",
        summary="Run scoped validation after recovery.",
        evidence="The validation proved the recovery.",
        recurrence_key="sp-debug.scoped-recovery-validation",
        recommended_action="Run scoped validation before resolving.",
    )
    status_after = learning_review_status(tmp_path, command_name="debug")
    metrics = learning_metrics_payload(tmp_path, command_name="debug")
    metrics_text = (tmp_path / ".planning" / "learnings" / "metrics.json").read_text(
        encoding="utf-8"
    )

    assert status_before["pending"] == 1
    assert "items" not in status_before
    assert "private-value" not in json.dumps(status_before)
    assert status_after["pending"] == 0
    assert capture["entry"]["recurrence_key"] == "sp-debug.scoped-recovery-validation"
    assert metrics["metrics"]["totals"]["assessed"] == 1
    assert metrics["derived"]["confirmation_rate"] == 0.0
    assert set(metrics["metrics"]) == {
        "totals",
        "decisions",
        "value_tiers",
        "risk_tiers",
        "reason_codes",
        "redaction_labels",
    }
    assert "private-value" not in metrics_text
    assert "ops@example.com" not in metrics_text


def test_learning_review_write_migrates_legacy_pending_without_duplicate(
    tmp_path: Path,
) -> None:
    _seed_learning_templates(tmp_path)
    signal_path = tmp_path / ".planning" / "learnings" / "signal-state.json"
    signal_path.parent.mkdir(parents=True, exist_ok=True)
    signal_path.write_text(
        json.dumps(
            {
                "debug": {
                    "command": "sp-debug",
                    "observed_at": "2026-08-01T00:00:00Z",
                    "learning_review": {
                        "decision": "deferred",
                        "rationale": "legacy pending review",
                        "deferred_at": "2026-08-01T00:00:00Z",
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    assert learning_review_status(tmp_path, command_name="debug")["pending"] == 1
    assert not (
        tmp_path / ".planning" / "learnings" / "review-state.json"
    ).exists()

    review_learning(
        tmp_path,
        command_name="debug",
        decision="deferred",
        rationale="canonical pending review",
    )

    assert learning_review_status(tmp_path, command_name="debug")["pending"] == 1
    legacy = json.loads(signal_path.read_text(encoding="utf-8"))
    assert "learning_review" not in legacy["debug"]


def test_learning_review_cleanup_scrubs_touched_legacy_signal_state(
    tmp_path: Path,
) -> None:
    _seed_learning_templates(tmp_path)
    (tmp_path / ".specify" / "config.json").write_text(
        json.dumps(
            {
                "project_learning": {
                    "detectors": {"sensitive_terms": ["Project Zephyr"]}
                }
            }
        ),
        encoding="utf-8",
    )
    signal_path = tmp_path / ".planning" / "learnings" / "signal-state.json"
    signal_path.parent.mkdir(parents=True, exist_ok=True)
    signal_path.write_text(
        json.dumps(
            {
                "debug": {
                    "command": "sp-debug",
                    "pain_score": 8,
                    "factors": {
                        "retry_attempts": 2,
                        "token=bad-factor": "token=bad-value",
                    },
                    "false_starts": ["retried with token=legacy-secret"],
                    "hidden_dependencies": [
                        "Project Zephyr needs ops@example.com approval"
                    ],
                    "trigger_signals": [
                        "user_correction: Project Zephyr raw detail"
                    ],
                    "observed_at": "bad time token=timestamp-secret",
                    "learning_review": {
                        "decision": "deferred",
                        "rationale": "wait for token=review-secret",
                        "deferred_at": "bad time ops@example.com",
                    },
                    "unknown": "token=unknown-secret",
                },
                "plan": {
                    "command": "sp-plan",
                    "false_starts": ["email other@example.com"],
                    "observed_at": "invalid token=other-time",
                },
            }
        ),
        encoding="utf-8",
    )

    review_learning(
        tmp_path,
        command_name="debug",
        decision="deferred",
        rationale="Keep a canonical pending review.",
    )

    serialized = signal_path.read_text(encoding="utf-8")
    for raw in (
        "legacy-secret",
        "review-secret",
        "timestamp-secret",
        "unknown-secret",
        "other-time",
        "Project Zephyr",
        "ops@example.com",
        "other@example.com",
        "bad-factor",
        "bad-value",
    ):
        assert raw not in serialized
    state = json.loads(serialized)
    assert "learning_review" not in state["debug"]
    assert state["debug"]["observed_at"] == ""
    assert state["plan"]["observed_at"] == ""
    assert state["debug"]["content_safety"]["sensitivity"] == "sanitized"


@pytest.mark.parametrize(
    ("target", "confirm"),
    [("learning", False), ("rule", True)],
)
def test_learning_promotion_refreshes_durable_transition_and_clears_review(
    tmp_path: Path,
    target: str,
    confirm: bool,
) -> None:
    _seed_learning_templates(tmp_path)
    recurrence_key = f"sp-debug.promote-review-{target}"
    capture_learning(
        tmp_path,
        command_name="debug",
        learning_type="pitfall",
        summary=f"Promotion to {target} preserves the durable boundary.",
        evidence=f"Promotion to {target} proved the reusable behavior.",
        recurrence_key=recurrence_key,
        confirm=confirm,
    )
    review_learning(
        tmp_path,
        command_name="debug",
        decision="deferred",
        rationale="Wait for the durable promotion transition.",
        recurrence_key=recurrence_key,
    )

    promoted = promote_learning(
        tmp_path, recurrence_key=recurrence_key, target=target
    )

    assert promoted["status"] == (
        "confirmed" if target == "learning" else "promoted-rule"
    )
    assert learning_review_status(tmp_path, command_name="debug")["pending"] == 0


def test_learning_review_explicit_recurrence_does_not_consume_other_pending_key(
    tmp_path: Path,
) -> None:
    _seed_learning_templates(tmp_path)
    recurrence_a = "sp-debug.review-specific-a"
    recurrence_b = "sp-debug.review-specific-b"
    for recurrence in (recurrence_a, recurrence_b):
        capture_learning(
            tmp_path,
            command_name="debug",
            learning_type="pitfall",
            summary=f"Durable behavior for {recurrence} changes future action.",
            evidence=f"Evidence for {recurrence} proves the reusable boundary.",
            recurrence_key=recurrence,
        )
    review_learning(
        tmp_path,
        command_name="debug",
        decision="deferred",
        rationale="Only recurrence B remains pending.",
        recurrence_key=recurrence_b,
    )

    result = review_learning(
        tmp_path,
        command_name="debug",
        decision="captured",
        recurrence_key=recurrence_a,
    )

    assert result["recurrence_key"] == recurrence_a
    assert learning_review_status(tmp_path, command_name="debug")["pending"] == 1


def test_learning_review_rejects_malformed_durable_freshness(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_learning_templates(tmp_path)
    recurrence_key = "sp-debug.malformed-review-freshness"
    capture_learning(
        tmp_path,
        command_name="debug",
        learning_type="pitfall",
        summary="Malformed freshness cannot prove a durable transition.",
        evidence="A malformed durable timestamp must fail closed.",
        recurrence_key=recurrence_key,
    )
    review_learning(
        tmp_path,
        command_name="debug",
        decision="deferred",
        rationale="Wait for a fresh durable transition.",
        recurrence_key=recurrence_key,
    )
    entry = read_learning_entries(build_learning_paths(tmp_path).candidates)[1][0]
    entry.last_seen = "not-a-timestamp"
    monkeypatch.setattr(
        "specify_cli.learnings._durable_learning_entries", lambda _root: [entry]
    )

    with pytest.raises(ValueError, match="no matching durable"):
        review_learning(
            tmp_path,
            command_name="debug",
            decision="captured",
            recurrence_key=recurrence_key,
        )

    assert learning_review_status(tmp_path, command_name="debug")["pending"] == 1


def test_learning_review_without_key_closes_multiple_specifics_only_after_all_are_fresh(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_learning_templates(tmp_path)
    recurrences = [
        "sp-debug.batch-review-a",
        "sp-debug.batch-review-b",
    ]
    for recurrence in recurrences:
        capture_learning(
            tmp_path,
            command_name="debug",
            learning_type="pitfall",
            summary=f"Batch review behavior for {recurrence} changes future action.",
            evidence=f"Evidence for {recurrence} proves the reusable boundary.",
            recurrence_key=recurrence,
        )
        review_learning(
            tmp_path,
            command_name="debug",
            decision="deferred",
            rationale=f"Wait for a fresh transition for {recurrence}.",
            recurrence_key=recurrence,
        )
    entries = read_learning_entries(build_learning_paths(tmp_path).candidates)[1]
    for entry in entries:
        entry.last_seen = "9999-01-01T00:00:00Z"
    monkeypatch.setattr(
        "specify_cli.learnings._durable_learning_entries", lambda _root: entries
    )

    result = review_learning(
        tmp_path,
        command_name="debug",
        decision="captured",
    )

    assert result["recurrence_keys"] == recurrences
    assert learning_review_status(tmp_path, command_name="debug")["pending"] == 0


def test_learning_start_candidate_quota_prioritizes_value_and_diversity(
    tmp_path: Path,
) -> None:
    _seed_learning_templates(tmp_path)
    for index in range(15):
        capture_learning(
            tmp_path,
            command_name="debug",
            learning_type="workflow_gap",
            summary=f"Stable workflow lesson {index} preserves re-entry state.",
            evidence=f"Stable evidence {index} proved the re-entry requirement.",
            recurrence_key=f"sp-debug.stable-workflow-{index}",
            applies_to=["debug"],
            confirm=True,
        )
    candidate_types = [
        "pitfall",
        "pitfall",
        "pitfall",
        "pitfall",
        "tooling_trap",
        "recovery_path",
        "near_miss",
    ]
    for index, learning_type in enumerate(candidate_types):
        capture_learning(
            tmp_path,
            command_name="debug",
            learning_type=learning_type,
            summary=f"Candidate {learning_type} lesson {index} changes future action.",
            evidence=f"Candidate evidence {index} proved the reusable behavior.",
            recurrence_key=f"sp-debug.{learning_type}-family-{index}",
        )

    intake = start_learning_session(tmp_path, command_name="debug")
    candidates = [
        item for item in intake["items"] if item["source_layer"] == "candidate"
    ]
    counts: dict[str, int] = {}
    for item in candidates:
        counts[item["type"]] = counts.get(item["type"], 0) + 1

    assert len(intake["items"]) == 20
    assert len(candidates) == 5
    assert len(counts) >= 3
    assert max(counts.values()) <= 2


def test_learning_start_preserves_value_rank_within_candidate_layer(
    tmp_path: Path,
) -> None:
    from specify_cli.learnings import _write_entries

    _seed_learning_templates(tmp_path)
    medium_ref = "sp-debug.aaa-medium-value"
    high_ref = "sp-debug.zzz-high-value"
    for recurrence_key in (medium_ref, high_ref):
        capture_learning(
            tmp_path,
            command_name="debug",
            learning_type="pitfall",
            summary=f"Candidate {recurrence_key} changes future action.",
            evidence=f"Candidate {recurrence_key} proved the reusable boundary.",
            recurrence_key=recurrence_key,
        )
    candidates_path = build_learning_paths(tmp_path).candidates
    preamble, entries = read_learning_entries(candidates_path)
    medium = next(entry for entry in entries if entry.recurrence_key == medium_ref)
    medium.learning_value_tier = "medium"
    medium.learning_value_reason_codes = ["high_signal"]
    medium.sensitivity_risk_tier = "none"
    medium.assessment_decision = "capture-safe"
    medium.assessment_reason = "safe_content"
    _write_entries(candidates_path, preamble, entries)

    intake = start_learning_session(tmp_path, command_name="debug")
    candidate_refs = [
        item["ref"]
        for item in intake["items"]
        if item["source_layer"] == "candidate"
    ]

    assert candidate_refs == [high_ref, medium_ref]


def test_learning_capture_auto_reassesses_recurrence_with_existing_occurrence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_learning_templates(tmp_path)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    source = workspace / "state.md"
    source.write_text("first environment mismatch\n", encoding="utf-8")

    def suggest(*_args, **_kwargs):
        return source, [
            AutoCaptureSuggestion(
                learning_type="tooling_trap",
                summary="Verify the runtime boundary before changing product code.",
                evidence=source.read_text(encoding="utf-8"),
                recurrence_key="sp-quick.runtime-boundary",
                signal_strength="medium",
                recommended_action="Check the runtime boundary first.",
                trigger_signals=("tooling_trap",),
            )
        ]

    monkeypatch.setattr("specify_cli.learnings._suggest_quick_auto_capture", suggest)
    first = capture_auto_learning(
        tmp_path, command_name="quick", workspace=Path("workspace")
    )
    source.write_text("second distinct environment mismatch\n", encoding="utf-8")
    second = capture_auto_learning(
        tmp_path, command_name="quick", workspace=Path("workspace")
    )

    assert first["assessed"][0]["assessment"]["learning_value"]["tier"] == "medium"
    assert second["assessed"][0]["assessment"]["learning_value"] == {
        "tier": "high",
        "reason_codes": ["repeated_occurrence", "tooling_trap"],
    }
    assert second["captured"][0]["entry"]["occurrence_count"] == 2


def test_learning_review_status_derives_aging_without_mutation(tmp_path: Path) -> None:
    _seed_learning_templates(tmp_path)
    review_learning(
        tmp_path,
        command_name="plan",
        decision="deferred",
        rationale="Wait for a safe abstraction.",
    )
    review_path = tmp_path / ".planning" / "learnings" / "review-state.json"
    state = json.loads(review_path.read_text(encoding="utf-8"))
    state["items"][0].update(
        {
            "created_at": "2026-05-01T00:00:00Z",
            "updated_at": "2026-05-01T00:00:00Z",
            "review_after": "2026-05-08T00:00:00Z",
        }
    )
    review_path.write_text(json.dumps(state), encoding="utf-8")
    before = review_path.read_bytes()

    status = learning_review_status(
        tmp_path,
        command_name="plan",
        current_time=datetime(2026, 8, 4, tzinfo=UTC),
    )

    assert status["pending"] == 1
    assert status["overdue"] == 1
    assert status["age_buckets"]["due_over_30_days"] == 1
    assert "items" not in status
    assert review_path.read_bytes() == before


def test_learning_policy_rejects_unknown_regex_and_control_literals() -> None:
    with pytest.raises(LearningPolicyError, match="unsupported fields"):
        parse_learning_policy({"detectors": {"patterns": [".*"]}})
    with pytest.raises(LearningPolicyError, match="control characters"):
        parse_learning_policy(
            {"detectors": {"sensitive_terms": ["unsafe\u0085term"]}}
        )


def test_learning_custom_sensitive_command_is_canonicalized_to_sp_other(
    tmp_path: Path,
) -> None:
    _seed_learning_templates(tmp_path)
    (tmp_path / ".specify" / "config.json").write_text(
        json.dumps(
            {
                "project_learning": {
                    "detectors": {"sensitive_terms": ["zephyr"]}
                }
            }
        ),
        encoding="utf-8",
    )

    capture = capture_learning(
        tmp_path,
        command_name="zephyr-flow",
        learning_type="pitfall",
        summary="Preserve the custom workflow boundary.",
        evidence="The custom workflow boundary changed future action.",
        recurrence_key="sp-zephyr-flow.custom-boundary",
    )
    review = review_learning(
        tmp_path,
        command_name="zephyr-flow",
        decision="deferred",
        rationale="Wait for the owner review.",
    )
    listed = list_learning_summaries(tmp_path, command_name="zephyr-flow")
    storage = "\n".join(
        path.read_text(encoding="utf-8")
        for root in (
            tmp_path / ".planning" / "learnings",
            tmp_path / ".specify" / "memory" / "learnings",
        )
        if root.exists()
        for path in root.rglob("*")
        if path.is_file()
    ).lower()

    assert capture["entry"]["source_command"] == "sp-other"
    assert "sp-other" in capture["entry"]["applies_to"]
    assert capture["assessment"]["content_safety"] == {
        "sensitivity": "sanitized",
        "risk_tier": "high",
        "redaction_labels": ["organization_sensitive"],
    }
    assert capture["assessment"]["decision"] == "capture-sanitized"
    assert review["item"]["command"] == "sp-other"
    assert listed["command"] == "sp-other"
    assert listed["items"]
    assert "zephyr" not in storage


def test_learning_normalizes_research_alias_to_deep_research() -> None:
    assert normalize_command_name("research") == "sp-deep-research"
    assert normalize_command_name("sp-research") == "sp-deep-research"
    assert normalize_command_name("sp.research") == "sp-deep-research"
    assert normalize_command_name("/sp.plan") == "sp-plan"
    assert normalize_command_name("spx-implement") == "sp-implement"
    assert normalize_command_name("spx.research") == "sp-deep-research"


@pytest.mark.parametrize("command_name", ["", "/", "sp-", "spx-", "plan now"])
def test_learning_rejects_blank_or_malformed_command_names(command_name: str) -> None:
    with pytest.raises(ValueError):
        normalize_command_name(command_name)


@pytest.mark.parametrize(
    ("summary", "evidence", "message"),
    [("", "evidence", "summary"), ("summary", "   ", "evidence")],
)
def test_learning_capture_rejects_blank_required_fields(
    tmp_path: Path,
    summary: str,
    evidence: str,
    message: str,
) -> None:
    _seed_learning_templates(tmp_path)

    with pytest.raises(ValueError, match=message):
        capture_learning(
            tmp_path,
            command_name="plan",
            learning_type="pitfall",
            summary=summary,
            evidence=evidence,
        )


@pytest.mark.parametrize(
    ("secret", "expected"),
    [
        ("Authorization: Bearer abc.def.ghi", "Authorization: [REDACTED_SECRET]"),
        ("ghp_12345678", "[REDACTED_SECRET]"),
        ("sk-1234567890abcdef", "[REDACTED_SECRET]"),
        ("AKIA123456789012", "[REDACTED_SECRET]"),
        ("eyJhbGciOi.fake_payload.fake_signature", "[REDACTED_SECRET]"),
        ("'api_key'='opaque-value'", "'api_key'='[REDACTED_SECRET]'"),
        (
            '{"authorization":"Bearer abc.def.ghi"}',
            '{"authorization":"[REDACTED_SECRET]"}',
        ),
    ],
)
def test_learning_sanitizer_matches_go_credential_thresholds(
    secret: str, expected: str
) -> None:
    sanitized, labels = sanitize_agent_text(f"credential {secret}")

    assert labels == ["credential"]
    assert expected in sanitized
    assert sanitized.count("[REDACTED_SECRET]") == 1
    assert secret not in sanitized
    sanitized_again, labels_again = sanitize_agent_text(sanitized)
    assert sanitized_again == sanitized
    assert labels_again == ["credential"]


def test_learning_sanitizer_restores_labels_from_existing_redaction_markers() -> None:
    text = (
        "[REDACTED_SECRET] [REDACTED_EMAIL] "
        "[REDACTED_PRIVATE_KEY] <USER_HOME>/repo"
    )

    sanitized, labels = sanitize_agent_text(text)

    assert sanitized == text
    assert labels == ["credential", "email", "machine_path", "private_key"]


def test_learning_sanitizer_redacts_root_home_path_with_suffix() -> None:
    sanitized, labels = sanitize_agent_text("/root/work/project/file.txt")

    assert sanitized == "<USER_HOME>/work/project/file.txt"
    assert labels == ["machine_path"]


def test_learning_sanitizer_does_not_treat_rooted_prefix_as_home() -> None:
    sanitized, labels = sanitize_agent_text("/rooted/work/project")

    assert sanitized == "/rooted/work/project"
    assert labels == []


def test_learning_capture_sanitizes_agent_facing_fields_and_legacy_reads(
    tmp_path: Path,
) -> None:
    _seed_learning_templates(tmp_path)
    secret_text = (
        "password=hunter2 token=ghp_1234567890abcdef1234567890abcdef123456 "
        "Authorization: Bearer sk-1234567890abcdef email ops@example.com "
        r"C:\Users\alice\repo /home/bob/repo AKIAIOSFODNN7EXAMPLE"
    )

    payload = capture_learning(
        tmp_path,
        command_name="debug",
        learning_type="tooling_trap",
        summary=f"Do not leak {secret_text}",
        evidence=f"Observed {secret_text}",
        recurrence_key="debug.secret-sanitized",
        false_starts=[f"failed with {secret_text}"],
        trigger_signals=[f"user_correction: {secret_text}"],
    )

    serialized = json.dumps(payload, sort_keys=True)
    for raw in [
        "hunter2",
        "ghp_1234567890abcdef1234567890abcdef123456",
        "sk-1234567890abcdef",
        "ops@example.com",
        "alice",
        "/home/bob",
        "AKIAIOSFODNN7EXAMPLE",
    ]:
        assert raw not in serialized
    entry = payload["entry"]
    assert entry["sensitivity"] == "sanitized"
    assert entry["redaction_labels"] == ["credential", "email", "machine_path"]
    assert "[REDACTED_SECRET]" in serialized
    assert "[REDACTED_EMAIL]" in serialized
    assert "<USER_HOME>/repo" in serialized

    detail = list_learning_summaries(tmp_path, command_name="debug")["items"][0]
    shown = _invoke_in_project(
        tmp_path,
        [
            "learning",
            "show",
            "--ref",
            detail["ref"],
            "--format",
            "json",
        ],
    )
    assert shown.exit_code == 0, shown.stdout
    assert "hunter2" not in shown.stdout
    assert "ops@example.com" not in shown.stdout
    shown_payload = json.loads(shown.stdout)
    assert shown_payload["content_safety"] == {
        "sensitivity": "sanitized",
        "redaction_labels": ["credential", "email", "machine_path"],
    }
    assert shown_payload["detail_path"].startswith(".specify/memory/learnings/")

    paths = build_learning_paths(tmp_path)
    preamble, candidates = read_learning_entries(paths.candidates)
    legacy_payload = candidates[0].to_payload()
    legacy_payload.pop("sensitivity")
    legacy_payload.pop("redaction_labels")
    legacy_payload["summary"] = "legacy row leaked api_key=legacy-secret"
    paths.candidates.write_text(
        "\n".join(
            [
                preamble,
                "",
                "<!-- SPECKIT_LEARNING_DATA_BEGIN -->",
                json.dumps([legacy_payload], indent=2),
                "<!-- SPECKIT_LEARNING_DATA_END -->",
            ]
        ),
        encoding="utf-8",
    )

    _, legacy_entries = read_learning_entries(paths.candidates)
    assert legacy_entries[0].sensitivity == "sanitized"
    assert "legacy-secret" not in legacy_entries[0].summary


def test_learning_capture_sanitizes_json_credential_values(
    tmp_path: Path,
) -> None:
    _seed_learning_templates(tmp_path)
    evidence = '{"password":"hunter2","api_key":"opaque-value"}'

    payload = capture_learning(
        tmp_path,
        command_name="debug",
        learning_type="pitfall",
        summary="JSON credentials stay field-meaningful",
        evidence=evidence,
        recurrence_key="debug.json-credentials",
    )
    serialized = json.dumps(payload)
    sanitized_evidence = payload["entry"]["evidence"]

    assert '"password":"[REDACTED_SECRET]"' in sanitized_evidence
    assert '"api_key":"[REDACTED_SECRET]"' in sanitized_evidence
    assert "hunter2" not in serialized
    assert "opaque-value" not in serialized
    assert payload["entry"]["redaction_labels"] == ["credential"]


def test_learning_list_and_show_sanitize_legacy_index_only_records(
    tmp_path: Path,
) -> None:
    _seed_learning_templates(tmp_path)
    _write_learning_index_payload(
        tmp_path,
        [
            {
                "id": "learn-2026-06-03-secret-index",
                "problem": "Legacy index leaked password=raw-secret for ops@example.com",
                "lesson": r"Open C:\Users\alice\repo after using token=raw-token",
                "learning_type": "pitfall",
                "source_command": "sp-debug",
                "recurrence_key": "sp-debug.legacy-secret-index",
                "applies_to": ["sp-debug"],
                "trigger_signals": ["user@example.com", r"C:\Users\alice\repo"],
                "detail": "./learn-2026-06-03-secret-index.md",
                "first_seen": "2026-06-03T00:00:00Z",
                "last_seen": "2026-06-03T00:00:00Z",
                "occurrence_count": 1,
                "signal_strength": "medium",
                "redaction_labels": ["phone_number", "credential"],
            }
        ],
    )

    listed = list_learning_summaries(tmp_path, command_name="debug")
    card = listed["items"][0]
    shown = _invoke_in_project(
        tmp_path,
        [
            "learning",
            "show",
            "--ref",
            "sp-debug.legacy-secret-index",
            "--format",
            "json",
        ],
    )
    serialized = json.dumps(listed) + shown.stdout

    assert shown.exit_code == 0, shown.stdout
    assert "raw-secret" not in serialized
    assert "raw-token" not in serialized
    assert "ops@example.com" not in serialized
    assert "alice" not in serialized
    assert card["sensitivity"] == "sanitized"
    assert card["redaction_labels"] == ["credential", "email", "machine_path"]
    assert json.loads(shown.stdout)["content_safety"] == {
        "sensitivity": "sanitized",
        "redaction_labels": ["credential", "email", "machine_path"],
    }


def test_learning_show_sanitizes_legacy_index_identity_time_and_detail_ref(
    tmp_path: Path,
) -> None:
    _seed_learning_templates(tmp_path)
    _write_learning_index_payload(
        tmp_path,
        [
            {
                "id": "learn-token=identity-secret",
                "problem": "Legacy index identity fields may leak",
                "lesson": "Sanitize identity, time, and detail metadata.",
                "learning_type": "pitfall",
                "source_command": "sp-debug",
                "recurrence_key": "sp-debug.legacy-identity",
                "applies_to": ["sp-debug"],
                "trigger_signals": ["pitfall"],
                "detail": "./learn-token=detail-secret.md",
                "first_seen": "token=first-secret",
                "last_seen": "token=last-secret",
                "occurrence_count": 1,
                "signal_strength": "medium",
            }
        ],
    )

    shown = _invoke_in_project(
        tmp_path,
        [
            "learning",
            "show",
            "--ref",
            "sp-debug.legacy-identity",
            "--format",
            "json",
        ],
    )
    payload = json.loads(shown.stdout)
    serialized = json.dumps(payload)

    assert shown.exit_code == 0, shown.stdout
    for raw in ["identity-secret", "detail-secret", "first-secret", "last-secret"]:
        assert raw not in serialized
    assert payload["id"].startswith("learn-")
    assert payload["provenance"]["first_seen"] == "1970-01-01T00:00:00Z"
    assert payload["provenance"]["last_seen"] == "1970-01-01T00:00:00Z"
    assert payload["detail_path"] is None
    assert payload["content_safety"]["redaction_labels"] == ["credential"]


def test_learning_capture_collects_redaction_labels_from_list_fields_only(
    tmp_path: Path,
) -> None:
    _seed_learning_templates(tmp_path)

    payload = capture_learning(
        tmp_path,
        command_name="debug",
        learning_type="pitfall",
        summary="Sensitive value appears only in list fields",
        evidence="Summary and evidence are safe.",
        recurrence_key="debug.list-only-secret",
        false_starts=["retried with token=list-secret"],
        trigger_signals=["validation_gap: ops@example.com"],
    )

    assert payload["entry"]["sensitivity"] == "sanitized"
    assert payload["entry"]["redaction_labels"] == ["credential", "email"]
    serialized = json.dumps(payload)
    assert "list-secret" not in serialized
    assert "ops@example.com" not in serialized


def test_learning_capture_merge_preserves_list_only_sensitivity_labels(
    tmp_path: Path,
) -> None:
    _seed_learning_templates(tmp_path)
    capture_learning(
        tmp_path,
        command_name="debug",
        learning_type="pitfall",
        summary="Merge keeps original safe summary",
        evidence="Safe evidence.",
        recurrence_key="debug.merge-list-secret",
    )

    merged = capture_learning(
        tmp_path,
        command_name="debug",
        learning_type="pitfall",
        summary="Merge keeps original safe summary",
        evidence="Safe evidence.",
        recurrence_key="debug.merge-list-secret",
        trigger_signals=["validation_gap: ops@example.com"],
    )

    assert merged["entry"]["sensitivity"] == "sanitized"
    assert merged["entry"]["redaction_labels"] == ["email"]
    assert merged["index_entry"]["sensitivity"] == "sanitized"
    assert merged["index_entry"]["redaction_labels"] == ["email"]
    assert "ops@example.com" not in json.dumps(merged)


def test_learning_recurrence_key_canonicalizes_redactions_and_raw_lookup_refs(
    tmp_path: Path,
) -> None:
    _seed_learning_templates(tmp_path)
    raw_key = "debug.email-ops@example.com.password=raw-secret"

    payload = capture_learning(
        tmp_path,
        command_name="debug",
        learning_type="pitfall",
        summary="Canonicalize sensitive recurrence keys",
        evidence="Safe evidence.",
        recurrence_key=raw_key,
    )
    shown = _invoke_in_project(
        tmp_path,
        ["learning", "show", "--ref", raw_key, "--format", "json"],
    )
    promoted = promote_learning(tmp_path, recurrence_key=raw_key, target="learning")

    assert payload["entry"]["recurrence_key"] == (
        "redacted-email-redacted-secret"
    )
    assert "raw-secret" not in json.dumps(payload)
    assert shown.exit_code == 0, shown.stdout
    assert json.loads(shown.stdout)["ref"] == payload["entry"]["recurrence_key"]
    assert promoted["entry"]["recurrence_key"] == payload["entry"]["recurrence_key"]


def test_learning_missing_ref_errors_use_safe_canonical_recurrence_key(
    tmp_path: Path,
) -> None:
    _seed_learning_templates(tmp_path)
    raw_key = "debug.ops@example.com.password=missing-secret"

    with pytest.raises(ValueError) as show_error:
        show_learning_detail(tmp_path, learning_ref=raw_key)
    with pytest.raises(ValueError) as promote_error:
        promote_learning(tmp_path, recurrence_key=raw_key, target="learning")

    errors = f"{show_error.value} {promote_error.value}"
    assert "missing-secret" not in errors
    assert "ops@example.com" not in errors
    assert "redacted-email" in errors
    assert "redacted-secret" in errors


def test_learning_recurrence_key_matches_generic_email_redaction_parity(
    tmp_path: Path,
) -> None:
    _seed_learning_templates(tmp_path)

    payload = capture_learning(
        tmp_path,
        command_name="debug",
        learning_type="pitfall",
        summary="Collapse email-like recurrence keys",
        evidence="Safe evidence.",
        recurrence_key="legacy.email.person@example.com",
    )

    assert payload["entry"]["recurrence_key"] == "redacted-email"


def test_learning_list_sanitizes_filter_query_projection(tmp_path: Path) -> None:
    _seed_learning_templates(tmp_path)

    payload = list_learning_summaries(
        tmp_path,
        command_name="debug",
        query="token=query-secret ops@example.com",
    )

    assert payload["filters"]["query"] == (
        "token=[REDACTED_SECRET] [REDACTED_EMAIL]"
    )
    assert "query-secret" not in json.dumps(payload)
    assert "ops@example.com" not in json.dumps(payload)


def test_concurrent_learning_capture_merges_without_lost_occurrences(
    tmp_path: Path,
) -> None:
    _seed_learning_templates(tmp_path)
    recurrence_key = "sp-plan.concurrent-capture"

    def capture(index: int) -> int:
        payload = capture_learning(
            tmp_path,
            command_name="plan",
            learning_type="pitfall",
            summary="Serialize Learning mutations through the CLI",
            evidence=f"Concurrent evidence packet {index}",
            recurrence_key=recurrence_key,
        )
        return int(payload["entry"]["occurrence_count"])

    with ThreadPoolExecutor(max_workers=4) as pool:
        occurrence_counts = sorted(pool.map(capture, range(4)))

    paths = build_learning_paths(tmp_path)
    _, candidates = read_learning_entries(paths.candidates)
    matching = [entry for entry in candidates if entry.recurrence_key == recurrence_key]
    assert occurrence_counts == [1, 2, 3, 4]
    assert len(matching) == 1
    assert matching[0].occurrence_count == 4


def _seed_learning_templates(project_path: Path) -> None:
    templates_root = Path(__file__).resolve().parents[1] / "templates"
    target_root = project_path / ".specify" / "templates"
    target_root.mkdir(parents=True, exist_ok=True)
    for name in (
        "project-rules-template.md",
        "project-confirmed-learnings-template.md",
        "project-learnings-index-template.md",
        "project-learning-detail-template.md",
    ):
        (target_root / name).write_text(
            (templates_root / name).read_text(encoding="utf-8"), encoding="utf-8"
        )


def _invoke_in_project(project: Path, args: list[str]):
    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        return runner.invoke(app, args, catch_exceptions=False)
    finally:
        os.chdir(old_cwd)


def _start_in_project(project: Path, command_name: str):
    return _invoke_in_project(
        project,
        [
            "learning",
            "start",
            "--command",
            command_name,
            "--format",
            "json",
        ],
    )


def _write_learning_index_payload(project: Path, payloads: list[object]) -> None:
    index_path = project / ".specify" / "memory" / "learnings" / "INDEX.md"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        "\n".join(
            [
                "# Project Learning Index",
                "",
                "<!-- SPECKIT_LEARNING_DATA_BEGIN -->",
                json.dumps(payloads, indent=2),
                "<!-- SPECKIT_LEARNING_DATA_END -->",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _current_and_malformed_index_payloads(command_name: str) -> list[object]:
    normalized_command = normalize_command_name(command_name)
    return [
        {
            "id": "learn-2026-06-03-valid-entry",
            "problem": "Use focused preflight context before workflow execution",
            "lesson": "Read relevant learning detail docs before repeating the same workflow mistake.",
            "learning_type": "pitfall",
            "source_command": normalized_command,
            "recurrence_key": f"{normalized_command}.valid-index-entry",
            "applies_to": [normalized_command],
            "trigger_signals": ["pitfall", "medium"],
            "detail": "./learn-2026-06-03-valid-entry.md",
            "first_seen": "2026-06-03T00:00:00Z",
            "last_seen": "2026-06-03T00:00:00Z",
            "occurrence_count": 1,
            "signal_strength": "medium",
        },
        {
            "id": "learn-2026-06-03-missing-type",
            "problem": "Invalid index row omitted its learning type",
            "lesson": "Reject rows that do not satisfy the current schema.",
            "source_command": normalized_command,
            "recurrence_key": f"{normalized_command}.missing-learning-type",
            "applies_to": [normalized_command],
            "trigger_signals": ["medium"],
            "detail": "./learn-2026-06-03-missing-type.md",
            "first_seen": "2026-06-03T00:00:00Z",
            "last_seen": "2026-06-03T00:00:00Z",
            "occurrence_count": 1,
            "signal_strength": "medium",
        },
        {
            "id": "LRN-obsolete-summary-only",
            "summary": "Obsolete summary-only row",
            "evidence": "Obsolete evidence-only row.",
            "learning_type": "recovery_path",
            "recurrence_key": f"{normalized_command}.summary-only",
            "applies_to": [normalized_command],
            "signal_strength": "medium",
            "status": "confirmed",
            "first_seen": "2026-06-03T00:00:00Z",
            "last_seen": "2026-06-03T00:00:00Z",
            "occurrence_count": 1,
        },
        {
            "id": "learn-2026-06-03-malformed-entry",
            "problem": "Malformed entry has no recoverable command routing",
            "lesson": "This row should be skipped with diagnostics.",
            "learning_type": "pitfall",
            "recurrence_key": f"{normalized_command}.malformed-entry",
            "applies_to": {"not": "a-list"},
            "first_seen": "2026-06-03T00:00:00Z",
            "last_seen": "2026-06-03T00:00:00Z",
        },
    ]


def _write_implement_tracker(
    feature_dir: Path,
    *,
    status: str,
    retry_attempts: int,
    failed_tasks: list[str],
    completed_checks: list[str],
    blockers: list[dict[str, str]] | None = None,
    open_gaps: list[dict[str, str]] | None = None,
) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    blockers = blockers or []
    open_gaps = open_gaps or []
    content = [
        "---",
        f'status: "{status}"',
        'feature: "demo-feature"',
        'resume_decision: "resume-here"',
        "---",
        "",
        "## Current Focus",
        "current_batch: batch-2",
        "goal: finish validation after recovery",
        "next_action: close the feature",
        "",
        "## Execution State",
        "completed_tasks:",
        "  - T001",
        "in_progress_tasks: []",
        "failed_tasks:",
        *[f"  - {task}" for task in failed_tasks],
        f"retry_attempts: {retry_attempts}",
        "",
        "## Validation",
        "planned_checks:",
        "  - pytest -q",
        "completed_checks:",
        *[f"  - {check}" for check in completed_checks],
        "",
        "## Blockers",
        *(
            [
                f"- task: {item['task']}",
                f"  type: {item['type']}",
                f"  evidence: {item['evidence']}",
                f"  recovery_action: {item['recovery_action']}",
            ]
            for item in blockers
        ),
        "",
        "## Open Gaps",
        *(
            [
                f"- type: {item['type']}",
                f"  summary: {item['summary']}",
                f"  source: {item['source']}",
                f"  next_action: {item['next_action']}",
            ]
            for item in open_gaps
        ),
        "",
    ]
    flattened: list[str] = []
    for item in content:
        if isinstance(item, list):
            flattened.extend(item)
        else:
            flattened.append(item)
    (feature_dir / "implement-tracker.md").write_text(
        "\n".join(flattened) + "\n", encoding="utf-8"
    )


def _write_tasks_and_worker_result(feature_dir: Path) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "spec-contract.json").write_text(
        json.dumps(
            {
                "scope": {
                    "in": ["A user can refresh validation fixture evidence."],
                    "out": [],
                    "deferred": [],
                },
                "acceptance_criteria": [
                    "A user can refresh validation fixture evidence."
                ],
                "capability_operations": [],
                "acceptance_coverage": [
                    {
                        "requirement_ref": "spec-contract.json#/scope/in/0",
                        "acceptance_ref": ("spec-contract.json#/acceptance_criteria/0"),
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (feature_dir / "plan-contract.json").write_text(
        json.dumps(
            {
                "version": 2,
                "status": "ready",
                "acceptance_refs": ["spec-contract.json#/acceptance_criteria/0"],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {
                "version": 2,
                "status": "ready",
                "acceptance_refs": ["plan-contract.json#/acceptance_refs/0"],
                "official_entrypoints": [
                    {
                        "id": "fixture-cli",
                        "command": "specify implement closeout",
                        "ready_signal": "The closeout result is emitted.",
                    }
                ],
                "system_review_scenarios": [
                    {
                        "id": "SR-FIXTURE-001",
                        "kind": "interaction",
                        "title": "Refresh validation fixture evidence",
                        "required": True,
                        "entrypoint_id": "fixture-cli",
                        "preconditions": ["The fixture project is initialized."],
                        "actions": ["Run implementation closeout."],
                        "expected_results": ["The closeout result reports success."],
                        "required_evidence": ["runtime_diagnostics"],
                    }
                ],
                "review_obligations": [
                    {
                        "id": "RO-FIXTURE-001",
                        "kind": "acceptance",
                        "source_ref": "plan-contract.json#/acceptance_refs/0",
                        "surface": "Implementation closeout result",
                        "required": True,
                        "scenario_ids": ["SR-FIXTURE-001"],
                    }
                ],
                "human_acceptance_obligations": [
                    {
                        "id": "HAO-FIXTURE-001",
                        "source_ref": "plan-contract.json#/acceptance_refs/0",
                        "change_kind": "changed",
                        "user_outcome": (
                            "The user sees a successful implementation closeout."
                        ),
                        "required": True,
                        "scenario_ids": ["HA-FIXTURE-001"],
                    }
                ],
                "human_acceptance_scenarios": [
                    {
                        "id": "HA-FIXTURE-001",
                        "title": "Confirm implementation closeout",
                        "user_value": (
                            "The user can confirm the implementation is ready "
                            "for review."
                        ),
                        "actor": "human user",
                        "required": True,
                        "obligation_ids": ["HAO-FIXTURE-001"],
                        "entrypoint_id": "fixture-cli",
                        "review_scenario_ids": ["SR-FIXTURE-001"],
                        "start_state": "The fixture implementation is complete.",
                        "steps": [
                            {
                                "id": "HA-FIXTURE-001-S01",
                                "action": "Inspect the closeout result.",
                                "expected_result": (
                                    "The result reports that closeout succeeded."
                                ),
                                "evidence_requirement": (
                                    "Human-visible successful closeout output."
                                ),
                                "risk": "low",
                            }
                        ],
                    }
                ],
                "tasks": [{"id": "T001"}],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "\n".join(
            [
                "# Tasks",
                "",
                "- [X] T001 Refresh validation fixture evidence",
                "",
            ]
        ),
        encoding="utf-8",
    )
    worker_results = feature_dir / "worker-results"
    worker_results.mkdir(parents=True, exist_ok=True)
    (worker_results / "T001.json").write_text(
        json.dumps(
            {
                "task_id": "T001",
                "status": "success",
                "validation_results": [
                    {
                        "command": "pytest -q",
                        "status": "passed",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    lifecycle_dir = feature_dir / "implementation-review" / "tasks"
    lifecycle_dir.mkdir(parents=True, exist_ok=True)
    (lifecycle_dir / "T001.json").write_text(
        json.dumps(
            {
                "version": 1,
                "task_id": "T001",
                "task_ref": "task-index.json#/tasks/T001",
                "source_revision": "r1",
                "execution_mode": "leader-direct",
                "packet_ref": None,
                "status": "accepted",
                "changed_paths": [],
                "validation": [{"command": "pytest -q", "status": "passed"}],
                "review": None,
                "obligation_evidence": [],
                "blockers": [],
                "recovery": None,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _write_workflow_state(
    feature_dir: Path,
    *,
    next_command: str = "/sp.implement",
    status: str = "completed",
    route_reason: str = "",
    blocked_reason: str = "",
    false_starts: list[str] | None = None,
    hidden_dependencies: list[str] | None = None,
    reusable_constraints: list[str] | None = None,
    trigger_signals: list[str] | None = None,
) -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    false_starts = false_starts or []
    hidden_dependencies = hidden_dependencies or []
    reusable_constraints = reusable_constraints or []
    trigger_signals = trigger_signals or []
    lines = [
        "# Workflow State: Demo",
        "",
        "## Current Command",
        "",
        "- active_command: `sp-analyze`",
        f"- status: `{status}`",
        "",
        "## Phase Mode",
        "",
        "- phase_mode: `analysis-only`",
        "- summary: demo",
        "",
        "## Next Action",
        "",
        "- continue",
        "",
        "## Next Command",
        "",
        f"- `{next_command}`",
    ]
    if (
        route_reason
        or blocked_reason
        or false_starts
        or hidden_dependencies
        or reusable_constraints
        or trigger_signals
    ):
        lines.extend(
            [
                "",
                "## Learning Signals",
                "",
                f"- route_reason: {route_reason}",
                f"- blocked_reason: {blocked_reason}",
                "",
                "### Learning Triggers",
            ]
        )
        lines.extend([f"- {item}" for item in trigger_signals] or ["-"])
        lines.extend(
            [
                "",
                "### False Starts",
            ]
        )
        lines.extend([f"- {item}" for item in false_starts] or ["-"])
        lines.extend(["", "### Hidden Dependencies"])
        lines.extend([f"- {item}" for item in hidden_dependencies] or ["-"])
        lines.extend(["", "### Reusable Constraints"])
        lines.extend([f"- {item}" for item in reusable_constraints] or ["-"])
    lines.append("")
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(lines),
        encoding="utf-8",
    )


def _write_resolved_debug_session(project: Path, slug: str) -> Path:
    debug_dir = project / ".planning" / "debug"
    handler = MarkdownPersistenceHandler(debug_dir)
    state = DebugGraphState(slug=slug, trigger="Intermittent validation failure")
    state.status = DebugStatus.RESOLVED
    state.resolution.fail_count = 2
    state.resolution.fix = "Re-run validation after refreshing the fixture cache"
    state.resolution.root_cause = RootCause(
        summary="Fixture cache drifted after the first failing run",
        owning_layer="tests",
        broken_control_state="fixture cache freshness",
        failure_mechanism="stale fixture state persisted across retries",
        loop_break="verification observed stale state",
        decisive_signal="fresh cache run passed immediately",
    )
    state.resolution.validation_results = [
        ValidationCheck(
            command="pytest tests/test_cache.py -q", status="passed", output="1 passed"
        )
    ]
    state.resolution.loop_restoration_proof = [
        "Fresh cache validation passed end-to-end"
    ]
    handler.save(state)
    return debug_dir / f"{slug}.md"


def test_learning_ensure_creates_stable_and_runtime_files(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)

    result = _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["exists"]["project_rules"] is True
    assert payload["exists"]["confirmed_learnings"] is True
    assert payload["exists"]["candidates"] is True
    assert payload["exists"]["review"] is True
    assert (project / ".specify" / "memory" / "project-rules.md").exists()
    assert (project / ".specify" / "memory" / "learnings" / "confirmed.md").exists()
    assert (project / ".planning" / "learnings" / "candidates.md").exists()
    assert (project / ".planning" / "learnings" / "review.md").exists()


def test_learning_ensure_creates_learning_index(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)

    result = _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["exists"]["learning_index"] is True
    assert (
        payload["paths"]["learning_index"]
        .replace("\\", "/")
        .endswith(".specify/memory/learnings/INDEX.md")
    )
    assert (
        payload["paths"]["learning_detail_template"]
        .replace("\\", "/")
        .endswith(".specify/templates/project-learning-detail-template.md")
    )
    index_path = project / ".specify" / "memory" / "learnings" / "INDEX.md"
    assert index_path.exists()
    index_content = index_path.read_text(encoding="utf-8")
    assert "# Project Learning Index" in index_content
    assert "<!-- SPECKIT_LEARNING_DATA_BEGIN -->" in index_content
    assert "<!-- SPECKIT_LEARNING_DATA_END -->" in index_content


def test_learning_ensure_migrates_legacy_confirmed_store_without_data_loss(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify" / "memory").mkdir(parents=True)
    _seed_learning_templates(project)
    legacy_path = project / ".specify" / "memory" / "project-learnings.md"
    legacy_path.write_text(
        "\n".join(
            [
                "# Project Learnings",
                "",
                "<!-- SPECKIT_LEARNING_DATA_BEGIN -->",
                json.dumps(
                    [
                        {
                            "id": "LRN-legacy-confirmed",
                            "summary": "Preserve confirmed Learning during upgrades",
                            "learning_type": "project_constraint",
                            "source_command": "sp-plan",
                            "evidence": "Confirmed in the legacy v0.5.20 store",
                            "recurrence_key": "sp-plan.legacy-confirmed",
                            "default_scope": "project",
                            "applies_to": ["sp-plan"],
                            "signal_strength": "high",
                            "status": "confirmed",
                            "first_seen": "2026-06-01T00:00:00Z",
                            "last_seen": "2026-06-02T00:00:00Z",
                            "occurrence_count": 2,
                        }
                    ],
                    indent=2,
                ),
                "<!-- SPECKIT_LEARNING_DATA_END -->",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(project, ["learning", "ensure", "--format", "json"])
    repeated = _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    assert result.exit_code == 0, result.stdout
    assert repeated.exit_code == 0, repeated.stdout
    paths = build_learning_paths(project)
    _, confirmed = read_learning_entries(paths.confirmed_learnings)
    migrated = [
        entry
        for entry in confirmed
        if entry.recurrence_key == "sp-plan.legacy-confirmed"
    ]
    assert len(migrated) == 1
    assert migrated[0].occurrence_count == 2
    assert migrated[0].evidence == "Confirmed in the legacy v0.5.20 store"


def test_learning_status_reports_missing_runtime_files_without_mutation(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)

    result = _invoke_in_project(project, ["learning", "status", "--format", "json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["exists"]["project_rules"] is False
    assert payload["exists"]["confirmed_learnings"] is False
    assert payload["exists"]["learning_index"] is False
    assert payload["exists"]["candidates"] is False
    assert payload["exists"]["review"] is False


def test_learning_capture_merges_by_recurrence_key_and_increments_count(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    args = [
        "learning",
        "capture",
        "--command",
        "implement",
        "--type",
        "pitfall",
        "--summary",
        "Need to preserve shared boundary pattern",
        "--evidence",
        "Observed during implementation",
        "--recurrence-key",
        "shared.boundary.pattern",
        "--format",
        "json",
    ]
    first = _invoke_in_project(project, args)
    second = _invoke_in_project(project, args)

    assert first.exit_code == 0, first.stdout
    assert second.exit_code == 0, second.stdout
    first_payload = json.loads(first.stdout)
    second_payload = json.loads(second.stdout)
    assert first_payload["entry"]["occurrence_count"] == 1
    assert second_payload["entry"]["occurrence_count"] == 2
    assert second_payload["needs_confirmation"] is True


def test_learning_capture_writes_index_and_detail_doc(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    summary = "Run generated helper commands from the project launcher"
    evidence_fragment = (
        "Launcher command wiring drifted from generated helper expectations."
    )
    false_start = (
        "patched only the generated helper without updating the shared launcher surface"
    )
    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "workflow_gap",
            "--summary",
            summary,
            "--evidence",
            f"{evidence_fragment}\nShared helper tests exposed the mismatch.",
            "--recurrence-key",
            "cli.project-launcher-helper-drift",
            "--applies-to",
            "sp-implement",
            "--false-start",
            false_start,
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    index_entry = payload["index_entry"]
    assert index_entry["recurrence_key"] == "cli.project-launcher-helper-drift"
    assert (
        index_entry["problem"]
        == "Run generated helper commands from the project launcher"
    )
    assert "sp-implement" in index_entry["applies_to"]
    assert index_entry["detail"].startswith("./learn-")

    index_path = project / ".specify" / "memory" / "learnings" / "INDEX.md"
    index_content = index_path.read_text(encoding="utf-8")
    assert "cli.project-launcher-helper-drift" in index_content
    assert index_entry["detail"] in index_content

    detail_path = index_path.parent / index_entry["detail"].removeprefix("./")
    detail_content = detail_path.read_text(encoding="utf-8")
    assert summary in detail_content
    assert evidence_fragment in detail_content
    assert false_start in detail_content


def test_learning_capture_uses_unique_detail_refs_for_long_common_recurrence_prefixes(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    common_prefix = "cli." + "project-launcher-helper-drift-" * 4
    first_summary = "First long-prefix launcher learning"
    second_summary = "Second long-prefix launcher learning"
    first_evidence = "First evidence must stay in its own detail file."
    second_evidence = "Second evidence must stay in its own detail file."

    first = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "pitfall",
            "--summary",
            first_summary,
            "--evidence",
            first_evidence,
            "--recurrence-key",
            f"{common_prefix}first",
            "--format",
            "json",
        ],
    )
    second = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "pitfall",
            "--summary",
            second_summary,
            "--evidence",
            second_evidence,
            "--recurrence-key",
            f"{common_prefix}second",
            "--format",
            "json",
        ],
    )

    assert first.exit_code == 0, first.stdout
    assert second.exit_code == 0, second.stdout
    first_payload = json.loads(first.stdout)
    second_payload = json.loads(second.stdout)
    first_detail = first_payload["index_entry"]["detail"]
    second_detail = second_payload["index_entry"]["detail"]
    assert first_detail != second_detail

    learning_dir = project / ".specify" / "memory" / "learnings"
    first_detail_content = (learning_dir / first_detail.removeprefix("./")).read_text(
        encoding="utf-8"
    )
    second_detail_content = (learning_dir / second_detail.removeprefix("./")).read_text(
        encoding="utf-8"
    )
    assert first_summary in first_detail_content
    assert first_evidence in first_detail_content
    assert second_summary in second_detail_content
    assert second_evidence in second_detail_content


def test_learning_capture_repairs_existing_duplicate_valid_detail_ref(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    shared_detail_ref = "./learn-2026-05-11-shared.md"
    shared_other_summary = "Other stale detail owner"
    shared_other_evidence = "Other stale detail content must remain untouched."
    index_path = project / ".specify" / "memory" / "learnings" / "INDEX.md"
    index_path.write_text(
        "\n".join(
            [
                "# Project Learning Index",
                "",
                "<!-- SPECKIT_LEARNING_DATA_BEGIN -->",
                json.dumps(
                    [
                        {
                            "id": "learn-2026-05-11-duplicate-first",
                            "problem": "Captured duplicate detail owner",
                            "lesson": "First duplicate row should get a repaired detail ref.",
                            "learning_type": "pitfall",
                            "source_command": "sp-implement",
                            "recurrence_key": "cli.duplicate-detail.first",
                            "applies_to": ["sp-implement"],
                            "trigger_signals": ["pitfall", "medium"],
                            "detail": shared_detail_ref,
                            "first_seen": "2026-05-11T00:00:00Z",
                            "last_seen": "2026-05-11T00:00:00Z",
                            "occurrence_count": 1,
                            "signal_strength": "medium",
                        },
                        {
                            "id": "learn-2026-05-11-duplicate-other",
                            "problem": shared_other_summary,
                            "lesson": shared_other_evidence,
                            "learning_type": "pitfall",
                            "source_command": "sp-implement",
                            "recurrence_key": "cli.duplicate-detail.other",
                            "applies_to": ["sp-implement"],
                            "trigger_signals": ["pitfall", "medium"],
                            "detail": shared_detail_ref,
                            "first_seen": "2026-05-11T00:00:00Z",
                            "last_seen": "2026-05-11T00:00:00Z",
                            "occurrence_count": 1,
                            "signal_strength": "medium",
                        },
                    ],
                    indent=2,
                ),
                "<!-- SPECKIT_LEARNING_DATA_END -->",
                "",
            ]
        ),
        encoding="utf-8",
    )
    learning_dir = project / ".specify" / "memory" / "learnings"
    shared_detail_path = learning_dir / shared_detail_ref.removeprefix("./")
    shared_detail_path.write_text(
        f"# {shared_other_summary}\n\n## Evidence\n\n{shared_other_evidence}\n",
        encoding="utf-8",
    )

    summary = "Captured duplicate detail owner"
    evidence = "Captured detail content must move to a unique detail document."
    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "pitfall",
            "--summary",
            summary,
            "--evidence",
            evidence,
            "--recurrence-key",
            "cli.duplicate-detail.first",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    repaired_detail_ref = payload["index_entry"]["detail"]
    assert repaired_detail_ref != shared_detail_ref
    assert repaired_detail_ref.startswith("./learn-")

    repaired_detail_content = (
        learning_dir / repaired_detail_ref.removeprefix("./")
    ).read_text(encoding="utf-8")
    shared_detail_content = shared_detail_path.read_text(encoding="utf-8")
    assert summary in repaired_detail_content
    assert evidence in repaired_detail_content
    assert shared_other_summary in shared_detail_content
    assert shared_other_evidence in shared_detail_content
    assert evidence not in shared_detail_content


def test_learning_capture_repairs_duplicate_ref_when_canonical_is_already_taken(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    recurrence_key = "cli.duplicate-detail.canonical-first"
    stale_first_seen = "2026-05-11T00:00:00Z"
    recurrence_hash = hashlib.sha256(recurrence_key.encode("utf-8")).hexdigest()[:10]
    canonical_id = (
        f"learn-2026-05-11-cli-duplicate-detail-canonical-first-{recurrence_hash}"
    )
    shared_detail_ref = f"./{canonical_id}.md"
    other_summary = "Other canonical detail owner"
    other_evidence = "Other canonical detail content must remain untouched."
    index_path = project / ".specify" / "memory" / "learnings" / "INDEX.md"
    index_path.write_text(
        "\n".join(
            [
                "# Project Learning Index",
                "",
                "<!-- SPECKIT_LEARNING_DATA_BEGIN -->",
                json.dumps(
                    [
                        {
                            "id": canonical_id,
                            "problem": "Captured canonical duplicate owner",
                            "lesson": "Canonical duplicate should get an alternate detail ref.",
                            "learning_type": "pitfall",
                            "source_command": "sp-implement",
                            "recurrence_key": recurrence_key,
                            "applies_to": ["sp-implement"],
                            "trigger_signals": ["pitfall", "medium"],
                            "detail": shared_detail_ref,
                            "first_seen": stale_first_seen,
                            "last_seen": stale_first_seen,
                            "occurrence_count": 1,
                            "signal_strength": "medium",
                        },
                        {
                            "id": "learn-2026-05-11-other-canonical-owner",
                            "problem": other_summary,
                            "lesson": other_evidence,
                            "learning_type": "pitfall",
                            "source_command": "sp-implement",
                            "recurrence_key": "cli.duplicate-detail.canonical-other",
                            "applies_to": ["sp-implement"],
                            "trigger_signals": ["pitfall", "medium"],
                            "detail": shared_detail_ref,
                            "first_seen": stale_first_seen,
                            "last_seen": stale_first_seen,
                            "occurrence_count": 1,
                            "signal_strength": "medium",
                        },
                    ],
                    indent=2,
                ),
                "<!-- SPECKIT_LEARNING_DATA_END -->",
                "",
            ]
        ),
        encoding="utf-8",
    )
    learning_dir = project / ".specify" / "memory" / "learnings"
    shared_detail_path = learning_dir / shared_detail_ref.removeprefix("./")
    shared_detail_path.write_text(
        f"# {other_summary}\n\n## Evidence\n\n{other_evidence}\n",
        encoding="utf-8",
    )

    summary = "Captured canonical duplicate owner"
    evidence = "Captured canonical collision content must use an alternate detail file."
    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "pitfall",
            "--summary",
            summary,
            "--evidence",
            evidence,
            "--recurrence-key",
            recurrence_key,
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    repaired_detail_ref = payload["index_entry"]["detail"]
    assert repaired_detail_ref != shared_detail_ref
    assert repaired_detail_ref.startswith("./learn-")

    repaired_detail_content = (
        learning_dir / repaired_detail_ref.removeprefix("./")
    ).read_text(encoding="utf-8")
    shared_detail_content = shared_detail_path.read_text(encoding="utf-8")
    assert summary in repaired_detail_content
    assert evidence in repaired_detail_content
    assert other_summary in shared_detail_content
    assert other_evidence in shared_detail_content
    assert evidence not in shared_detail_content


def test_learning_capture_repairs_case_variant_detail_ref_collision(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    recurrence_key = "cli.duplicate-detail.case-variant"
    stale_first_seen = "2026-05-11T00:00:00Z"
    recurrence_hash = hashlib.sha256(recurrence_key.encode("utf-8")).hexdigest()[:10]
    canonical_id = (
        f"learn-2026-05-11-cli-duplicate-detail-case-variant-{recurrence_hash}"
    )
    canonical_detail_ref = f"./{canonical_id}.md"
    case_variant_ref = f"./{canonical_id.upper()}.MD"
    other_summary = "Other case-variant detail owner"
    other_evidence = "Other case-variant detail content must remain untouched."
    index_path = project / ".specify" / "memory" / "learnings" / "INDEX.md"
    index_path.write_text(
        "\n".join(
            [
                "# Project Learning Index",
                "",
                "<!-- SPECKIT_LEARNING_DATA_BEGIN -->",
                json.dumps(
                    [
                        {
                            "id": "learn-2026-05-11-other-case-owner",
                            "problem": other_summary,
                            "lesson": other_evidence,
                            "learning_type": "pitfall",
                            "source_command": "sp-implement",
                            "recurrence_key": "cli.duplicate-detail.case-other",
                            "applies_to": ["sp-implement"],
                            "trigger_signals": ["pitfall", "medium"],
                            "detail": case_variant_ref,
                            "first_seen": stale_first_seen,
                            "last_seen": stale_first_seen,
                            "occurrence_count": 1,
                            "signal_strength": "medium",
                        },
                    ],
                    indent=2,
                ),
                "<!-- SPECKIT_LEARNING_DATA_END -->",
                "",
            ]
        ),
        encoding="utf-8",
    )
    learning_dir = project / ".specify" / "memory" / "learnings"
    canonical_detail_path = learning_dir / canonical_detail_ref.removeprefix("./")
    canonical_detail_path.write_text(
        f"# {other_summary}\n\n## Evidence\n\n{other_evidence}\n",
        encoding="utf-8",
    )

    summary = "Captured case-variant detail owner"
    evidence = "Captured case-variant content must use an alternate detail file."
    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "pitfall",
            "--summary",
            summary,
            "--evidence",
            evidence,
            "--recurrence-key",
            recurrence_key,
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    repaired_detail_ref = payload["index_entry"]["detail"]
    assert repaired_detail_ref != case_variant_ref
    assert repaired_detail_ref != canonical_detail_ref
    assert repaired_detail_ref.startswith("./learn-")

    repaired_detail_content = (
        learning_dir / repaired_detail_ref.removeprefix("./")
    ).read_text(encoding="utf-8")
    canonical_detail_content = canonical_detail_path.read_text(encoding="utf-8")
    assert summary in repaired_detail_content
    assert evidence in repaired_detail_content
    assert other_summary in canonical_detail_content
    assert other_evidence in canonical_detail_content
    assert evidence not in canonical_detail_content


def test_learning_capture_sanitizes_malformed_legacy_first_seen_for_detail_ref(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    recurrence_key = "cli.malformed-first-seen.detail-ref"
    summary = "Sanitize malformed first seen for detail refs"
    evidence = "Malformed legacy timestamps must not create nested detail paths."
    legacy_payload = {
        "id": "LRN-legacy-malformed-first-seen",
        "summary": "Legacy malformed first seen",
        "learning_type": "pitfall",
        "source_command": "sp-implement",
        "evidence": "Legacy evidence",
        "recurrence_key": recurrence_key,
        "default_scope": "implementation-heavy",
        "applies_to": ["sp-implement"],
        "signal_strength": "medium",
        "status": "candidate",
        "first_seen": "../../bad",
        "last_seen": "../../bad",
        "occurrence_count": 1,
        "pain_score": 0,
        "false_starts": [],
        "rejected_paths": [],
        "decisive_signal": "",
        "root_cause_family": "",
        "injection_targets": [],
        "promotion_hint": "",
    }
    candidate_path = project / ".planning" / "learnings" / "candidates.md"
    candidate_path.write_text(
        "\n".join(
            [
                "# Candidate Learnings",
                "",
                "<!-- SPECKIT_LEARNING_DATA_BEGIN -->",
                json.dumps([legacy_payload], indent=2),
                "<!-- SPECKIT_LEARNING_DATA_END -->",
                "",
            ]
        ),
        encoding="utf-8",
    )

    index_path = project / ".specify" / "memory" / "learnings" / "INDEX.md"
    index_path.write_text(
        "\n".join(
            [
                "# Project Learning Index",
                "",
                "<!-- SPECKIT_LEARNING_DATA_BEGIN -->",
                json.dumps(
                    [
                        {
                            "id": "learn-legacy-malformed-first-seen",
                            "problem": "Legacy malformed first seen",
                            "lesson": "Legacy evidence",
                            "learning_type": "pitfall",
                            "source_command": "sp-implement",
                            "recurrence_key": recurrence_key,
                            "applies_to": ["sp-implement"],
                            "trigger_signals": ["pitfall", "medium"],
                            "detail": "../../outside.md",
                            "first_seen": "../../bad",
                            "last_seen": "../../bad",
                            "occurrence_count": 1,
                            "signal_strength": "medium",
                        }
                    ],
                    indent=2,
                ),
                "<!-- SPECKIT_LEARNING_DATA_END -->",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "pitfall",
            "--summary",
            summary,
            "--evidence",
            evidence,
            "--recurrence-key",
            recurrence_key,
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    detail_ref = payload["index_entry"]["detail"]
    detail_name = detail_ref.removeprefix("./")
    learning_dir = (project / ".specify" / "memory" / "learnings").resolve()
    assert str(project) not in payload["detail_path"]
    assert "pytest-of" not in payload["detail_path"]
    detail_path = (project / payload["detail_path"]).resolve()
    assert detail_ref.startswith("./learn-")
    assert "/" not in detail_name
    assert "\\" not in detail_name
    assert detail_path.is_relative_to(learning_dir)
    assert detail_path.exists()
    detail_content = detail_path.read_text(encoding="utf-8")
    assert summary in detail_content
    assert evidence in detail_content


def test_learning_capture_repairs_unsafe_ref_before_canonical_duplicate_check(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    recurrence_key = "cli.duplicate-detail.unsafe-current"
    stale_first_seen = "2026-05-11T00:00:00Z"
    recurrence_hash = hashlib.sha256(recurrence_key.encode("utf-8")).hexdigest()[:10]
    canonical_id = (
        f"learn-2026-05-11-cli-duplicate-detail-unsafe-current-{recurrence_hash}"
    )
    canonical_detail_ref = f"./{canonical_id}.md"
    unsafe_detail_ref = "../../outside.md"
    other_summary = "Other unsafe-canonical owner"
    other_evidence = "Other unsafe-canonical content must remain untouched."
    index_path = project / ".specify" / "memory" / "learnings" / "INDEX.md"
    index_path.write_text(
        "\n".join(
            [
                "# Project Learning Index",
                "",
                "<!-- SPECKIT_LEARNING_DATA_BEGIN -->",
                json.dumps(
                    [
                        {
                            "id": "../unsafe-current-id",
                            "problem": "Captured unsafe current detail owner",
                            "lesson": "Unsafe detail should repair before duplicate detection.",
                            "learning_type": "pitfall",
                            "source_command": "sp-implement",
                            "recurrence_key": recurrence_key,
                            "applies_to": ["sp-implement"],
                            "trigger_signals": ["pitfall", "medium"],
                            "detail": unsafe_detail_ref,
                            "first_seen": stale_first_seen,
                            "last_seen": stale_first_seen,
                            "occurrence_count": 1,
                            "signal_strength": "medium",
                        },
                        {
                            "id": "learn-2026-05-11-other-unsafe-canonical-owner",
                            "problem": other_summary,
                            "lesson": other_evidence,
                            "learning_type": "pitfall",
                            "source_command": "sp-implement",
                            "recurrence_key": "cli.duplicate-detail.unsafe-other",
                            "applies_to": ["sp-implement"],
                            "trigger_signals": ["pitfall", "medium"],
                            "detail": canonical_detail_ref,
                            "first_seen": stale_first_seen,
                            "last_seen": stale_first_seen,
                            "occurrence_count": 1,
                            "signal_strength": "medium",
                        },
                    ],
                    indent=2,
                ),
                "<!-- SPECKIT_LEARNING_DATA_END -->",
                "",
            ]
        ),
        encoding="utf-8",
    )
    learning_dir = project / ".specify" / "memory" / "learnings"
    canonical_detail_path = learning_dir / canonical_detail_ref.removeprefix("./")
    canonical_detail_path.write_text(
        f"# {other_summary}\n\n## Evidence\n\n{other_evidence}\n",
        encoding="utf-8",
    )

    summary = "Captured unsafe current detail owner"
    evidence = "Unsafe current detail content must use a unique repaired detail file."
    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "pitfall",
            "--summary",
            summary,
            "--evidence",
            evidence,
            "--recurrence-key",
            recurrence_key,
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    repaired_detail_ref = payload["index_entry"]["detail"]
    assert repaired_detail_ref != unsafe_detail_ref
    assert repaired_detail_ref != canonical_detail_ref
    assert repaired_detail_ref.startswith("./learn-")

    repaired_detail_content = (
        learning_dir / repaired_detail_ref.removeprefix("./")
    ).read_text(encoding="utf-8")
    canonical_detail_content = canonical_detail_path.read_text(encoding="utf-8")
    assert summary in repaired_detail_content
    assert evidence in repaired_detail_content
    assert other_summary in canonical_detail_content
    assert other_evidence in canonical_detail_content
    assert evidence not in canonical_detail_content


def test_learning_capture_confirm_keeps_index_occurrence_count_aligned(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    args = [
        "learning",
        "capture",
        "--command",
        "implement",
        "--type",
        "pitfall",
        "--summary",
        "Keep launcher helper recurrence counts aligned",
        "--evidence",
        "Candidate capture should not make index counts drift on confirm.",
        "--recurrence-key",
        "cli.launcher-helper.count-alignment",
        "--format",
        "json",
    ]
    candidate = _invoke_in_project(project, args)
    confirmed = _invoke_in_project(project, [*args[:-2], "--confirm", *args[-2:]])

    assert candidate.exit_code == 0, candidate.stdout
    assert confirmed.exit_code == 0, confirmed.stdout
    payload = json.loads(confirmed.stdout)
    assert payload["entry"]["occurrence_count"] == 1
    assert (
        payload["index_entry"]["occurrence_count"]
        == payload["entry"]["occurrence_count"]
    )


def test_learning_promote_refreshes_index_detail_status(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    captured = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "pitfall",
            "--summary",
            "Refresh detail docs after explicit promotion",
            "--evidence",
            "Promotion should update the linked detail machine payload.",
            "--recurrence-key",
            "cli.detail-doc.promotion-refresh",
            "--format",
            "json",
        ],
    )
    assert captured.exit_code == 0, captured.stdout
    detail_path = project / json.loads(captured.stdout)["detail_path"]

    promoted = _invoke_in_project(
        project,
        [
            "learning",
            "promote",
            "--recurrence-key",
            "cli.detail-doc.promotion-refresh",
            "--target",
            "learning",
            "--format",
            "json",
        ],
    )

    assert promoted.exit_code == 0, promoted.stdout
    detail_content = detail_path.read_text(encoding="utf-8")
    assert '"status": "confirmed"' in detail_content
    assert '"status": "candidate"' not in detail_content


def test_learning_start_is_read_only_and_does_not_promote_detail_status(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    args = [
        "learning",
        "capture",
        "--command",
        "plan",
        "--type",
        "workflow_gap",
        "--summary",
        "Refresh detail docs after auto promotion",
        "--evidence",
        "Auto-promotion should update the linked detail machine payload.",
        "--recurrence-key",
        "cli.detail-doc.auto-promotion-refresh",
        "--format",
        "json",
    ]
    captured = _invoke_in_project(project, args)
    _invoke_in_project(project, args)
    assert captured.exit_code == 0, captured.stdout
    detail_path = project / json.loads(captured.stdout)["detail_path"]

    started = _start_in_project(project, "plan")

    assert started.exit_code == 0, started.stdout
    payload = json.loads(started.stdout)
    detail_content = detail_path.read_text(encoding="utf-8")
    assert payload["read_only"] is True
    assert (
        payload["promotion_ready"][0]["ref"] == "cli.detail-doc.auto-promotion-refresh"
    )
    assert payload["items"][0]["status"] == "candidate"
    assert '"status": "candidate"' in detail_content
    assert '"status": "confirmed"' not in detail_content


def test_learning_capture_sanitizes_existing_index_detail_path(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    index_path = project / ".specify" / "memory" / "learnings" / "INDEX.md"
    index_path.write_text(
        "\n".join(
            [
                "# Project Learning Index",
                "",
                "<!-- SPECKIT_LEARNING_DATA_BEGIN -->",
                json.dumps(
                    [
                        {
                            "id": "learn-2026-05-11-cli-detail-path-escape",
                            "problem": "Existing malicious detail path must not escape",
                            "lesson": "Keep generated learning detail writes contained.",
                            "learning_type": "pitfall",
                            "source_command": "sp-implement",
                            "recurrence_key": "cli.detail-path.escape",
                            "applies_to": ["sp-implement"],
                            "trigger_signals": ["pitfall", "medium"],
                            "detail": "../../outside.md",
                            "first_seen": "2026-05-11T00:00:00Z",
                            "last_seen": "2026-05-11T00:00:00Z",
                            "occurrence_count": 1,
                            "signal_strength": "medium",
                        }
                    ],
                    indent=2,
                ),
                "<!-- SPECKIT_LEARNING_DATA_END -->",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "pitfall",
            "--summary",
            "Existing malicious detail path must not escape",
            "--evidence",
            "Capture should rewrite unsafe detail paths inside learning memory.",
            "--recurrence-key",
            "cli.detail-path.escape",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    learning_dir = (project / ".specify" / "memory" / "learnings").resolve()
    detail_path = (project / payload["detail_path"]).resolve()
    assert detail_path.is_relative_to(learning_dir)
    assert payload["index_entry"]["detail"].startswith("./learn-")
    assert not (project / ".specify" / "outside.md").exists()


def test_learning_capture_sanitizes_existing_index_detail_path_and_id(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    index_path = project / ".specify" / "memory" / "learnings" / "INDEX.md"
    index_path.write_text(
        "\n".join(
            [
                "# Project Learning Index",
                "",
                "<!-- SPECKIT_LEARNING_DATA_BEGIN -->",
                json.dumps(
                    [
                        {
                            "id": "../outside-via-id",
                            "problem": "Existing malicious detail id must not escape",
                            "lesson": "Keep fallback detail writes contained.",
                            "learning_type": "pitfall",
                            "source_command": "sp-implement",
                            "recurrence_key": "cli.detail-path.escape-via-id",
                            "applies_to": ["sp-implement"],
                            "trigger_signals": ["pitfall", "medium"],
                            "detail": "../../outside.md",
                            "first_seen": "2026-05-11T00:00:00Z",
                            "last_seen": "2026-05-11T00:00:00Z",
                            "occurrence_count": 1,
                            "signal_strength": "medium",
                        }
                    ],
                    indent=2,
                ),
                "<!-- SPECKIT_LEARNING_DATA_END -->",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "pitfall",
            "--summary",
            "Existing malicious detail id must not escape",
            "--evidence",
            "Capture should not trust an existing index id when repairing detail paths.",
            "--recurrence-key",
            "cli.detail-path.escape-via-id",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    learning_dir = (project / ".specify" / "memory" / "learnings").resolve()
    detail_path = (project / payload["detail_path"]).resolve()
    assert detail_path.is_relative_to(learning_dir)
    assert payload["index_entry"]["detail"].startswith("./learn-")
    assert not (project / ".specify" / "outside.md").exists()
    assert not (project / ".specify" / "memory" / "outside-via-id.md").exists()


def test_learning_capture_sanitizes_existing_index_detail_ref_to_index_file(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    index_path = project / ".specify" / "memory" / "learnings" / "INDEX.md"
    index_path.write_text(
        "\n".join(
            [
                "# Project Learning Index",
                "",
                "<!-- SPECKIT_LEARNING_DATA_BEGIN -->",
                json.dumps(
                    [
                        {
                            "id": "learn-2026-05-11-cli-index-ref",
                            "problem": "Existing detail ref must not target index",
                            "lesson": "Keep detail docs separate from the index file.",
                            "learning_type": "pitfall",
                            "source_command": "sp-implement",
                            "recurrence_key": "cli.detail-path.index-ref",
                            "applies_to": ["sp-implement"],
                            "trigger_signals": ["pitfall", "medium"],
                            "detail": "./INDEX.md",
                            "first_seen": "2026-05-11T00:00:00Z",
                            "last_seen": "2026-05-11T00:00:00Z",
                            "occurrence_count": 1,
                            "signal_strength": "medium",
                        }
                    ],
                    indent=2,
                ),
                "<!-- SPECKIT_LEARNING_DATA_END -->",
                "",
                "## Managed Entries",
                "",
                "Index sentinel content",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "pitfall",
            "--summary",
            "Existing detail ref must not target index",
            "--evidence",
            "Capture should not use INDEX.md as a detail document.",
            "--recurrence-key",
            "cli.detail-path.index-ref",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    learning_dir = (project / ".specify" / "memory" / "learnings").resolve()
    detail_path = (project / payload["detail_path"]).resolve()
    assert detail_path.is_relative_to(learning_dir)
    assert detail_path != index_path.resolve()
    assert payload["index_entry"]["detail"].startswith("./learn-")
    index_content = index_path.read_text(encoding="utf-8")
    assert "# Project Learning Index" in index_content
    assert "## Managed Entries" in index_content


def test_learning_start_filters_relevant_candidates_by_command(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "plan",
            "--type",
            "workflow_gap",
            "--summary",
            "Need explicit validation tasks",
            "--evidence",
            "Missed twice in planning",
            "--recurrence-key",
            "workflow.validation.tasks",
            "--format",
            "json",
        ],
    )
    _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "debug",
            "--type",
            "recovery_path",
            "--summary",
            "Re-run focused repro before widening scope",
            "--evidence",
            "Resolved repeated debug loops",
            "--recurrence-key",
            "debug.focused.repro",
            "--format",
            "json",
        ],
    )

    result = _start_in_project(project, "debug")

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    summaries = [entry["summary"] for entry in payload["items"]]
    assert "Re-run focused repro before widening scope" in summaries
    assert "Need explicit validation tasks" not in summaries


def test_learning_start_rejects_obsolete_index_shape_without_translation(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    index_path = project / ".specify" / "memory" / "learnings" / "INDEX.md"
    index_path.write_text(
        "\n".join(
            [
                "# Project Learning Index",
                "",
                "<!-- SPECKIT_LEARNING_DATA_BEGIN -->",
                json.dumps(
                    [
                        {
                            "id": "LRN-obsolete-quick-learning",
                            "summary": "Obsolete quick learning summary",
                            "learning_type": "workflow_gap",
                            "source_command": "sp-quick",
                            "evidence": "Obsolete evidence must not become the current lesson.",
                            "recurrence_key": "quick.obsolete-index-shape",
                            "default_scope": "quick-task",
                            "applies_to": ["sp-quick"],
                            "signal_strength": "medium",
                            "status": "confirmed",
                            "first_seen": "2026-05-14T00:00:00Z",
                            "last_seen": "2026-05-14T00:00:00Z",
                            "occurrence_count": 1,
                        }
                    ],
                    indent=2,
                ),
                "<!-- SPECKIT_LEARNING_DATA_END -->",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _start_in_project(project, "quick")

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["items"] == []
    assert payload["warnings"]


def test_learning_start_keeps_valid_current_rows_and_rejects_malformed_rows(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])
    _write_learning_index_payload(
        project, _current_and_malformed_index_payloads("debug")
    )

    result = _start_in_project(project, "debug")

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    recurrence_keys = {entry["ref"] for entry in payload["items"]}
    assert "sp-debug.valid-index-entry" in recurrence_keys
    assert "sp-debug.missing-learning-type" not in recurrence_keys
    assert "sp-debug.summary-only" not in recurrence_keys
    assert "sp-debug.malformed-entry" not in recurrence_keys
    assert payload["warnings"]


@pytest.mark.parametrize("command_name", ["constitution", "map-scan", "map-build"])
def test_learning_start_rejects_non_current_rows_for_all_workflows(
    tmp_path: Path,
    command_name: str,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])
    _write_learning_index_payload(
        project, _current_and_malformed_index_payloads(command_name)
    )

    result = _start_in_project(project, command_name)

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    normalized_command = normalize_command_name(command_name)
    recurrence_keys = {entry["ref"] for entry in payload["items"]}
    assert f"{normalized_command}.valid-index-entry" in recurrence_keys
    assert f"{normalized_command}.summary-only" not in recurrence_keys
    assert f"{normalized_command}.malformed-entry" not in recurrence_keys
    assert payload["warnings"]


def test_learning_start_returns_relevant_cards_with_show_argv(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "debug",
            "--type",
            "recovery_path",
            "--summary",
            "Re-run the focused repro before widening debug scope",
            "--evidence",
            "The failing behavior disappeared only after the minimal repro was restored.",
            "--recurrence-key",
            "debug.focused-repro-before-scope-widening",
            "--format",
            "json",
        ],
    )

    result = _start_in_project(project, "debug")

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert [entry["ref"] for entry in payload["items"]] == [
        "debug.focused-repro-before-scope-widening"
    ]
    assert payload["items"][0]["show_argv"][1:3] == ["learning", "show"]
    assert "evidence" not in payload["items"][0]


def test_learning_summary_argv_uses_the_persisted_project_launcher(tmp_path: Path) -> None:
    project = tmp_path / "learning project 项目"
    project.mkdir()
    _seed_learning_templates(project)
    launcher_argv = (
        "uvx",
        "--from",
        "git+https://github.com/chenziyang110/spec-kit-plus.git@aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "specify",
    )
    write_project_specify_launcher_config(
        project,
        SpecifyLauncherSpec(
            command=render_command(launcher_argv),
            argv=launcher_argv,
            source="test",
            kind="source_bound",
        ),
    )
    for index in range(2):
        capture_learning(
            project,
            command_name="implement",
            learning_type="pitfall",
            summary=f"Bound launcher learning {index}",
            evidence=f"Evidence {index}",
            recurrence_key=f"launcher.bound-{index}",
        )

    payload = list_learning_summaries(
        project,
        command_name="implement",
        limit=1,
    )

    assert payload["items"][0]["show_argv"][: len(launcher_argv)] == list(
        launcher_argv
    )
    assert payload["pagination"]["next_argv"][: len(launcher_argv)] == list(
        launcher_argv
    )


def test_learning_start_surfaces_repeated_medium_candidate_without_promoting(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    args = [
        "learning",
        "capture",
        "--command",
        "plan",
        "--type",
        "workflow_gap",
        "--summary",
        "Always preserve verification tasks in planning",
        "--evidence",
        "Repeated omission in planning",
        "--recurrence-key",
        "workflow.verify.tasks",
        "--signal",
        "medium",
        "--format",
        "json",
    ]
    _invoke_in_project(project, args)
    _invoke_in_project(project, args)

    result = _start_in_project(project, "plan")

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    promotion_ready = [entry["summary"] for entry in payload["promotion_ready"]]
    relevant_cards = [entry["summary"] for entry in payload["items"]]
    assert "Always preserve verification tasks in planning" in promotion_ready
    assert "Always preserve verification tasks in planning" in relevant_cards
    assert payload["items"][0]["source_layer"] == "candidate"


def test_learning_capture_confirm_and_promote_rule_flow(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    captured = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "specify",
            "--type",
            "project_constraint",
            "--summary",
            "Always name touched shared surfaces explicitly",
            "--evidence",
            "User confirmed this should become a default",
            "--recurrence-key",
            "shared.surfaces.must.be.named",
            "--signal",
            "high",
            "--confirm",
            "--format",
            "json",
        ],
    )
    promoted = _invoke_in_project(
        project,
        [
            "learning",
            "promote",
            "--recurrence-key",
            "shared.surfaces.must.be.named",
            "--target",
            "rule",
            "--format",
            "json",
        ],
    )
    start = _start_in_project(project, "implement")

    assert captured.exit_code == 0, captured.stdout
    assert promoted.exit_code == 0, promoted.stdout
    promoted_payload = json.loads(promoted.stdout)
    start_payload = json.loads(start.stdout)
    assert promoted_payload["status"] == "promoted-rule"
    rule_summaries = [entry["summary"] for entry in start_payload["items"]]
    assert "Always name touched shared surfaces explicitly" in rule_summaries
    assert start_payload["items"][0]["source_layer"] == "project-rule"


def test_learning_start_exposes_confirmed_project_constraint_for_all_workflows(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "project_constraint",
            "--summary",
            "Use the validated build surface before retrying native compilation",
            "--evidence",
            "Confirmed reusable build constraint",
            "--recurrence-key",
            "build.surface.must.be.validated",
            "--confirm",
            "--format",
            "json",
        ],
    )

    workflow_commands = (
        "accept",
        "analyze",
        "ask",
        "auto",
        "checklist",
        "clarify",
        "constitution",
        "debug",
        "deep-research",
        "design",
        "discussion",
        "explain",
        "fast",
        "implement",
        "implement-teams",
        "map-build",
        "map-rebuild",
        "map-scan",
        "map-update",
        "plan",
        "prd",
        "prd-build",
        "prd-scan",
        "quick",
        "specify",
        "tasks",
        "taskstoissues",
        "team",
    )

    for command_name in workflow_commands:
        result = _start_in_project(project, command_name)
        assert result.exit_code == 0, result.stdout
        payload = json.loads(result.stdout)
        relevant_learnings = [entry["summary"] for entry in payload["items"]]
        assert (
            "Use the validated build surface before retrying native compilation"
            in relevant_learnings
        )
        assert any(
            item["summary"]
            == "Use the validated build surface before retrying native compilation"
            and item["source_layer"] == "confirmed-learning"
            for item in payload["items"]
        )


def test_learning_start_surfaces_single_high_signal_candidate_for_confirmation(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "debug",
            "--type",
            "tooling_trap",
            "--summary",
            "Validate the shell and solution platform before retrying MSBuild",
            "--evidence",
            "Single high-signal build trap that should still shape the next run",
            "--recurrence-key",
            "build.shell-and-platform.must-be-validated",
            "--signal",
            "high",
            "--format",
            "json",
        ],
    )

    result = _start_in_project(project, "implement")

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    confirmation = [entry["summary"] for entry in payload["needs_confirmation"]]

    assert (
        "Validate the shell and solution platform before retrying MSBuild"
        in confirmation
    )
    assert any(
        item["summary"]
        == "Validate the shell and solution platform before retrying MSBuild"
        and item["source_layer"] == "candidate"
        and "sp-implement" in item["why_relevant"]
        for item in payload["items"]
    )


def test_learning_start_surfaces_repeated_high_signal_candidate_without_promoting(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    args = [
        "learning",
        "capture",
        "--command",
        "implement",
        "--type",
        "project_constraint",
        "--summary",
        "Always name touched shared surfaces explicitly",
        "--evidence",
        "Repeated and high-signal constraint",
        "--recurrence-key",
        "shared.surfaces.must.be.named",
        "--signal",
        "high",
        "--format",
        "json",
    ]
    _invoke_in_project(project, args)
    _invoke_in_project(project, args)

    result = _start_in_project(project, "implement")

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    promotion_ready = [entry["summary"] for entry in payload["promotion_ready"]]
    relevant_candidates = [entry["summary"] for entry in payload["items"]]
    assert "Always name touched shared surfaces explicitly" in promotion_ready
    assert "Always name touched shared surfaces explicitly" in relevant_candidates
    assert payload["items"][0]["source_layer"] == "candidate"


def test_learning_start_promotion_ready_preserves_structured_learning_fields(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    args = [
        "learning",
        "capture",
        "--command",
        "debug",
        "--type",
        "tooling_trap",
        "--summary",
        "Validate native shell before retrying the build",
        "--evidence",
        "Repeated build retries failed until the shell was corrected.",
        "--recurrence-key",
        "build.shell.must.be.validated",
        "--signal",
        "high",
        "--pain-score",
        "7",
        "--false-start",
        "retrying msbuild from the wrong shell",
        "--rejected-path",
        "source-code regression",
        "--decisive-signal",
        "the same build passed immediately after switching shells",
        "--root-cause-family",
        "native-build-shell-mismatch",
        "--injection-target",
        "sp-debug",
        "--promotion-hint",
        "promote whenever native build setup is involved",
        "--format",
        "json",
    ]
    _invoke_in_project(project, args)
    _invoke_in_project(project, args)

    result = _start_in_project(project, "debug")

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    promotion_ready = next(
        entry
        for entry in payload["promotion_ready"]
        if entry["ref"] == "build.shell.must.be.validated"
    )
    assert set(promotion_ready) == {"ref", "summary", "occurrences"}

    shown = _invoke_in_project(
        project,
        ["learning", "show", "--ref", promotion_ready["ref"], "--format", "json"],
    )
    detail = json.loads(shown.stdout)
    assert detail["lifecycle"]["pain_score"] == 7
    assert detail["evidence"]["false_starts"] == [
        "retrying msbuild from the wrong shell"
    ]
    assert detail["evidence"]["rejected_paths"] == ["source-code regression"]
    assert (
        detail["evidence"]["decisive_signal"]
        == "the same build passed immediately after switching shells"
    )
    assert detail["evidence"]["root_cause_family"] == "native-build-shell-mismatch"
    assert detail["lifecycle"]["injection_targets"] == ["sp-debug"]
    assert (
        detail["lifecycle"]["promotion_hint"]
        == "promote whenever native build setup is involved"
    )


def test_learning_aggregate_json_reports_grouped_patterns(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])
    _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "pitfall",
            "--summary",
            "Need to preserve shared boundary pattern",
            "--evidence",
            "Observed during implementation",
            "--recurrence-key",
            "shared.boundary.pattern",
            "--format",
            "json",
        ],
    )

    result = _invoke_in_project(project, ["learning", "aggregate", "--format", "json"])

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["counts"]["patterns"] == 1
    assert payload["patterns"][0]["recurrence_key"] == "shared.boundary.pattern"


def test_learning_aggregate_write_report_creates_markdown_output(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    result = _invoke_in_project(
        project,
        ["learning", "aggregate", "--format", "json", "--write-report"],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    report_path = Path(payload["report_path"])
    assert report_path.exists()
    assert "Learning Aggregate Report" in report_path.read_text(encoding="utf-8")


def test_learning_start_exposes_compact_promotion_and_confirmation_cards(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    args = [
        "learning",
        "capture",
        "--command",
        "implement",
        "--type",
        "pitfall",
        "--summary",
        "Need to preserve shared boundary pattern",
        "--evidence",
        "Observed during implementation",
        "--recurrence-key",
        "shared.boundary.pattern",
        "--signal",
        "high",
        "--format",
        "json",
    ]
    _invoke_in_project(project, args)
    _invoke_in_project(project, args)

    result = _start_in_project(project, "implement")

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["items"][0]["ref"] == "shared.boundary.pattern"
    assert payload["promotion_ready"] == [
        {
            "ref": "shared.boundary.pattern",
            "summary": "Need to preserve shared boundary pattern",
            "occurrences": 2,
        }
    ]
    assert payload["needs_confirmation"][0]["ref"] == "shared.boundary.pattern"


def test_learning_start_defaults_to_compact_read_only_intake(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])
    _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "debug",
            "--type",
            "tooling_trap",
            "--summary",
            "Use the project-pinned launcher",
            "--evidence",
            "The global executable resolved to another checkout.",
            "--recurrence-key",
            "tooling.project-pinned-launcher",
            "--format",
            "json",
        ],
    )

    result = _start_in_project(project, "spx-debug")

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert "detail_level" not in payload
    assert payload["read_only"] is True
    assert payload["command"] == "sp-debug"
    assert payload["policy"] == "consume-capture"
    assert payload["items"][0]["ref"] == "tooling.project-pinned-launcher"
    assert "evidence" not in payload["items"][0]
    assert payload["items"][0]["show_argv"][1:3] == ["learning", "show"]
    schema = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "templates"
            / "project-learning-record-schema.json"
        ).read_text(encoding="utf-8")
    )
    assert list(Draft202012Validator(schema).iter_errors(payload)) == []


def test_learning_list_and_show_use_progressive_agent_contract(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])
    captured = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "verification_gap",
            "--summary",
            "Verify the real entrypoint after generated-surface changes",
            "--problem",
            "Unit tests can pass while the generated integration remains stale.",
            "--action",
            "Regenerate the integration and verify its real entrypoint.",
            "--trigger",
            "generated surface changed",
            "--success",
            "installed output matches the source template",
            "--avoid",
            "claiming completion from source-only tests",
            "--exception",
            "no generated or mirrored consumer exists",
            "--evidence",
            "A prior source-only fix left installed commands stale.",
            "--recurrence-key",
            "verification.generated-entrypoint",
            "--format",
            "json",
        ],
    )
    assert captured.exit_code == 0, captured.stdout
    second = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "pitfall",
            "--summary",
            "Keep a second low-signal summary for pagination",
            "--evidence",
            "This record verifies deterministic continuation arguments.",
            "--recurrence-key",
            "verification.pagination-second",
            "--signal",
            "low",
            "--format",
            "json",
        ],
    )
    assert second.exit_code == 0, second.stdout

    listed = _invoke_in_project(
        project,
        [
            "learning",
            "list",
            "--command",
            "spx-implement",
            "--limit",
            "1",
            "--format",
            "json",
        ],
    )
    assert listed.exit_code == 0, listed.stdout
    list_payload = json.loads(listed.stdout)
    assert "detail_level" not in list_payload
    assert list_payload["pagination"]["returned"] == 1
    assert list_payload["pagination"]["next_argv"][1:3] == ["learning", "list"]
    assert "--cursor" in list_payload["pagination"]["next_argv"]
    assert (
        list_payload["items"][0]["action"]
        == "Regenerate the integration and verify its real entrypoint."
    )
    assert "evidence" not in list_payload["items"][0]

    all_listed = _invoke_in_project(
        project,
        ["learning", "list", "--command", "spx-implement", "--all", "--format", "json"],
    )
    assert all_listed.exit_code == 0, all_listed.stdout
    all_payload = json.loads(all_listed.stdout)
    assert (
        all_payload["pagination"]["returned"] == all_payload["pagination"]["total"] == 2
    )
    assert all_payload["pagination"]["next_argv"] is None

    shown = _invoke_in_project(
        project,
        [
            "learning",
            "show",
            "--ref",
            "verification.generated-entrypoint",
            "--format",
            "json",
        ],
    )
    assert shown.exit_code == 0, shown.stdout
    detail = json.loads(shown.stdout)
    assert "detail_level" not in detail
    assert detail["guidance"] == {
        "problem": "Unit tests can pass while the generated integration remains stale.",
        "action": "Regenerate the integration and verify its real entrypoint.",
        "avoid": ["claiming completion from source-only tests"],
        "success_criteria": ["installed output matches the source template"],
        "exceptions": ["no generated or mirrored consumer exists"],
    }
    assert "generated surface changed" in detail["applicability"]["trigger_signals"]
    assert (
        detail["evidence"]["observation"]
        == "A prior source-only fix left installed commands stale."
    )

    schema = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "templates"
            / "project-learning-record-schema.json"
        ).read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    assert list(Draft202012Validator(schema).iter_errors(list_payload)) == []
    assert list(Draft202012Validator(schema).iter_errors(all_payload)) == []
    assert list(Draft202012Validator(schema).iter_errors(detail)) == []


def test_learning_start_does_not_create_missing_learning_files(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)

    result = _start_in_project(project, "plan")

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["items"] == []
    assert payload["warnings"]
    assert not (project / ".specify" / "memory" / "learnings" / "INDEX.md").exists()
    assert not (project / ".planning" / "learnings").exists()


def test_learning_consumer_commands_do_not_mutate_existing_storage(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])
    _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "plan",
            "--type",
            "workflow_gap",
            "--summary",
            "Keep consumption read-only",
            "--evidence",
            "Read commands must not update timestamps, recurrence, or lifecycle state.",
            "--recurrence-key",
            "learning.reads-are-pure",
            "--format",
            "json",
        ],
    )

    def snapshot() -> dict[str, bytes]:
        return {
            path.relative_to(project).as_posix(): path.read_bytes()
            for root in (
                project / ".specify" / "memory",
                project / ".planning" / "learnings",
            )
            for path in root.rglob("*")
            if path.is_file()
        }

    before = snapshot()
    commands = [
        ["learning", "start", "--command", "spx-plan", "--format", "json"],
        ["learning", "list", "--command", "spx-plan", "--all", "--format", "json"],
        ["learning", "show", "--ref", "learning.reads-are-pure", "--format", "json"],
    ]
    for args in commands:
        result = _invoke_in_project(project, args)
        assert result.exit_code == 0, result.stdout

    assert snapshot() == before


def test_learning_help_surfaces_low_level_helper_commands() -> None:
    result = runner.invoke(app, ["learning", "--help"], catch_exceptions=False)

    assert result.exit_code == 0, result.stdout
    assert "ensure" in result.stdout
    assert "status" in result.stdout
    assert "start" in result.stdout
    assert "list" in result.stdout
    assert "show" in result.stdout
    assert "capture" in result.stdout
    assert "capture-auto" in result.stdout
    assert "promote" in result.stdout


def test_learning_start_exposes_only_the_current_compact_contract(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)

    help_result = runner.invoke(
        app, ["learning", "start", "--help"], catch_exceptions=False
    )
    obsolete_result = _invoke_in_project(
        project,
        [
            "learning",
            "start",
            "--command",
            "plan",
            "--detail-level",
            "full",
            "--format",
            "json",
        ],
    )

    assert help_result.exit_code == 0, help_result.stdout
    assert "--detail-level" not in strip_ansi(help_result.stdout)
    assert obsolete_result.exit_code != 0


def test_learning_capture_auto_help_mentions_broader_state_surfaces() -> None:
    result = runner.invoke(
        app, ["learning", "capture-auto", "--help"], catch_exceptions=False
    )

    assert result.exit_code == 0, result.stdout
    output = strip_ansi(result.stdout)
    assert "--command" in output
    assert "plan" in output
    assert "test" in output
    assert "implement" in output
    assert "quick" in output
    assert "debug" in output
    assert "--feature-dir" in output
    assert "--dry-run" in output
    assert "workflow-state.md" in output
    assert "implement-tracker.md" in output
    assert "STATUS.md" in output
    assert "Debug session markdown file" in output


def test_project_constraint_default_applies_to_includes_test_and_map_codebase(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "implement",
            "--type",
            "project_constraint",
            "--summary",
            "Need to preserve shared execution constraints",
            "--evidence",
            "Observed across execution workflows",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    applies_to = payload["entry"]["applies_to"]
    assert "sp-implement" in applies_to
    assert "sp-debug" in applies_to
    assert "sp-map-scan" in applies_to
    assert "sp-map-build" in applies_to


def test_learning_capture_accepts_structured_path_learning_fields(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _invoke_in_project(project, ["learning", "ensure", "--format", "json"])

    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture",
            "--command",
            "debug",
            "--type",
            "tooling_trap",
            "--summary",
            "Watcher loops can masquerade as process-manager failures",
            "--evidence",
            "Repeated process fixes failed; excluding the log directory stopped restarts.",
            "--pain-score",
            "6",
            "--false-start",
            "job object cleanup",
            "--rejected-path",
            "process manager root cause",
            "--decisive-signal",
            "watcher ignore stopped restarts",
            "--root-cause-family",
            "dev-tooling-watch-loop",
            "--injection-target",
            "sp-debug",
            "--promotion-hint",
            "promote after another watcher-loop recurrence",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    entry = payload["entry"]
    assert entry["learning_type"] == "tooling_trap"
    assert entry["pain_score"] == 6
    assert entry["false_starts"] == ["job object cleanup"]
    assert entry["rejected_paths"] == ["process manager root cause"]
    assert entry["decisive_signal"] == "watcher ignore stopped restarts"
    assert entry["root_cause_family"] == "dev-tooling-watch-loop"
    assert entry["injection_targets"] == ["sp-debug"]


def test_learning_capture_auto_implement_writes_candidates_from_tracker_state(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    feature_dir = project / "specs" / "demo-feature"
    _write_implement_tracker(
        feature_dir,
        status="resolved",
        retry_attempts=2,
        failed_tasks=["T002"],
        completed_checks=["pytest -q"],
    )

    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture-auto",
            "--command",
            "implement",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    summaries = [item["entry"]["summary"] for item in payload["captured"]]
    assert payload["status"] == "captured"
    assert (
        "Rerun planned validation after implementation recovery before resolving the feature"
        in summaries
    )
    assert (
        "Failed implementation tasks should keep execution in recovery until validation turns green"
        in summaries
    )


def test_learning_capture_auto_cli_dry_run_preserves_project_bytes(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    feature_dir = project / "specs" / "demo-feature"
    _write_implement_tracker(
        feature_dir,
        status="resolved",
        retry_attempts=2,
        failed_tasks=["T002"],
        completed_checks=["pytest -q"],
    )
    before = {
        path.relative_to(project).as_posix(): path.read_bytes()
        for path in project.rglob("*")
        if path.is_file()
    }

    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture-auto",
            "--command",
            "implement",
            "--feature-dir",
            str(feature_dir),
            "--dry-run",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "dry-run"
    assert payload["dry_run"] is True
    assert payload["captured"] == []
    assert before == {
        path.relative_to(project).as_posix(): path.read_bytes()
        for path in project.rglob("*")
        if path.is_file()
    }


def test_learning_capture_auto_registry_uses_safe_refs_without_entry_bodies(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    feature_dir = project / "specs" / "demo-feature"
    _write_implement_tracker(
        feature_dir,
        status="resolved",
        retry_attempts=1,
        failed_tasks=["T002"],
        completed_checks=["pytest -q"],
    )

    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture-auto",
            "--command",
            "implement",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    registry = json.loads(
        (project / ".planning" / "learnings" / "auto-capture.json").read_text(
            encoding="utf-8"
        )
    )
    record = next(iter(registry.values()))
    assert record["source_ref"] == "specs/demo-feature/implement-tracker.md"
    assert "source_path" not in record
    assert "captured_entries" not in record
    assert "recurrence_keys" in record


def test_learning_capture_auto_rejects_external_feature_dir(tmp_path: Path) -> None:
    project = tmp_path / "project"
    external = tmp_path / "external"
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _write_implement_tracker(
        external,
        status="resolved",
        retry_attempts=1,
        failed_tasks=["T002"],
        completed_checks=["pytest -q"],
    )

    with pytest.raises(ValueError, match="feature_dir must resolve inside"):
        capture_auto_learning(
            project,
            command_name="implement",
            feature_dir=external,
        )


def test_learning_capture_auto_resolves_relative_feature_dir_from_project_root(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    other_cwd = tmp_path / "other-cwd"
    feature_dir = project / "specs" / "demo-feature"
    other_cwd.mkdir(parents=True)
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _write_implement_tracker(
        feature_dir,
        status="resolved",
        retry_attempts=1,
        failed_tasks=["T002"],
        completed_checks=["pytest -q"],
    )
    previous = Path.cwd()
    try:
        os.chdir(other_cwd)
        payload = capture_auto_learning(
            project,
            command_name="implement",
            feature_dir=Path("specs/demo-feature"),
        )
    finally:
        os.chdir(previous)

    assert payload["status"] == "captured"
    assert payload["source_path"] == "specs/demo-feature/implement-tracker.md"


def test_learning_capture_auto_rejects_symlink_escape_feature_dir(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    external = tmp_path / "external"
    link = project / "specs" / "linked-external"
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    _write_implement_tracker(
        external,
        status="resolved",
        retry_attempts=1,
        failed_tasks=["T002"],
        completed_checks=["pytest -q"],
    )
    link.parent.mkdir(parents=True, exist_ok=True)
    try:
        link.symlink_to(external, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"symlink creation not supported: {exc}")

    with pytest.raises(ValueError, match="feature_dir must resolve inside"):
        capture_auto_learning(
            project,
            command_name="implement",
            feature_dir=link,
        )


def test_learning_capture_auto_migrates_legacy_registry_without_raw_payloads(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    feature_dir = project / "specs" / "demo-feature"
    tracker_path = feature_dir / "implement-tracker.md"
    _write_implement_tracker(
        feature_dir,
        status="resolved",
        retry_attempts=1,
        failed_tasks=["T002"],
        completed_checks=["pytest -q"],
    )
    registry_path = project / ".planning" / "learnings" / "auto-capture.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(
        json.dumps(
            {
                "unsafe fingerprint token=registry-secret": {
                    "command": "sp-implement",
                    "source_path": str(tracker_path),
                    "recurrence_keys": [
                        "legacy.ops@example.com.password=registry-secret"
                    ],
                    "captured_entries": [
                        {
                            "summary": "raw registry payload",
                            "evidence": "token=registry-secret ops@example.com",
                        }
                    ],
                    "unknown": "keep-out",
                    "captured_at": "2026-08-04T00:00:00Z",
                },
                "legacy-relative-ref": {
                    "command": "sp-implement",
                    "source_ref": ".planning/learnings/workflow-state.md",
                    "recurrence_keys": ["legacy.relative-ref"],
                    "captured_at": "2026-01-01",
                },
                "legacy-posix-home": {
                    "command": "sp-implement",
                    "source_path": "/home/alice/project/workflow-state.md",
                    "recurrence_keys": ["legacy.posix-home"],
                    "captured_at": "2026-08-04T00:00:00Z",
                },
                "legacy-unsupported-command": {
                    "command": "token=bad-command",
                    "source_path": "/home/alice/project/secret.md",
                    "recurrence_keys": ["legacy.unsupported"],
                    "captured_at": "token=bad-time",
                }
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture-auto",
            "--command",
            "implement",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    serialized = json.dumps(registry)
    assert "registry-secret" not in serialized
    assert "ops@example.com" not in serialized
    assert "/home/alice" not in serialized
    assert "bad-command" not in serialized
    assert "bad-time" not in serialized
    assert str(project) not in serialized
    assert "pytest-of" not in serialized
    assert all(re.fullmatch(r"[0-9a-f]{64}", key) for key in registry)
    source_refs = {record["source_ref"] for record in registry.values()}
    assert ".planning/learnings/workflow-state.md" in source_refs
    assert "<USER_HOME>/project/workflow-state.md" in source_refs
    assert "specs/demo-feature/implement-tracker.md" in source_refs
    for record in registry.values():
        assert sorted(record) == [
            "captured_at",
            "command",
            "recurrence_keys",
            "source_ref",
        ]
        assert "captured_entries" not in record
        assert "source_path" not in record
    assert any(record["captured_at"] == "" for record in registry.values())


def test_learning_promote_requires_candidate_confirmation_before_rule(
    tmp_path: Path,
) -> None:
    _seed_learning_templates(tmp_path)
    capture_learning(
        tmp_path,
        command_name="plan",
        learning_type="project_constraint",
        summary="Rule candidates require confirmation first",
        evidence="One occurrence is not enough for a durable project rule.",
        recurrence_key="plan.confirm-before-rule",
    )

    with pytest.raises(ValueError, match="confirm"):
        promote_learning(
            tmp_path,
            recurrence_key="plan.confirm-before-rule",
            target="rule",
        )

    confirmed = promote_learning(
        tmp_path,
        recurrence_key="plan.confirm-before-rule",
        target="learning",
    )
    promoted = promote_learning(
        tmp_path,
        recurrence_key="plan.confirm-before-rule",
        target="rule",
    )

    assert confirmed["status"] == "confirmed"
    assert promoted["status"] == "promoted-rule"
    for payload in (confirmed, promoted):
        assert payload["detail_path"].startswith(".specify/memory/learnings/")
        assert str(tmp_path) not in payload["detail_path"]
        assert "pytest-of" not in payload["detail_path"]
        assert (tmp_path / payload["detail_path"]).exists()


def test_learning_capture_auto_implement_writes_index_details(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    feature_dir = project / ".specify" / "features" / "001-demo"
    _write_implement_tracker(
        feature_dir,
        status="resolved",
        retry_attempts=1,
        failed_tasks=["T004"],
        completed_checks=["pytest tests/test_demo.py -q"],
    )

    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture-auto",
            "--command",
            "implement",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "captured"
    captured = payload["captured"][0]
    assert "index_entry" in captured
    detail_path = project / captured["detail_path"]
    assert detail_path.exists()
    assert "Observed auto-capture evidence" in detail_path.read_text(encoding="utf-8")


def test_learning_capture_auto_implement_extracts_gap_and_constraint_patterns(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    feature_dir = project / "specs" / "demo-feature"
    _write_implement_tracker(
        feature_dir,
        status="blocked",
        retry_attempts=0,
        failed_tasks=[],
        completed_checks=[],
        blockers=[
            {
                "task": "T009",
                "type": "external",
                "evidence": "API contract approval still pending",
                "recovery_action": "wait for API owner sign-off",
            }
        ],
        open_gaps=[
            {
                "type": "plan_gap",
                "summary": "Plan omitted the contract migration step",
                "source": "T009",
                "next_action": "update plan.md and tasks.md before resuming",
            }
        ],
    )

    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture-auto",
            "--command",
            "implement",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    keys = [item["entry"]["recurrence_key"] for item in payload["captured"]]
    assert "implement.execution-blockers-feed-back-into-planning" in keys
    assert "implement.external-or-human-blockers-are-project-constraints" in keys


def test_learning_capture_auto_debug_writes_candidates_from_resolved_session(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    session_file = _write_resolved_debug_session(project, "fixture-cache-drift")

    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture-auto",
            "--command",
            "debug",
            "--session-file",
            str(session_file),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "captured"
    keys = [item["entry"]["recurrence_key"] for item in payload["captured"]]
    assert "debug.return-to-investigation-after-failed-verification" in keys
    assert "debug.research-checkpoint-after-repeated-verification-failure" in keys


def test_learning_capture_auto_skips_duplicate_snapshot(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    feature_dir = project / "specs" / "demo-feature"
    _write_implement_tracker(
        feature_dir,
        status="resolved",
        retry_attempts=1,
        failed_tasks=["T002"],
        completed_checks=["pytest -q"],
    )

    first = _invoke_in_project(
        project,
        [
            "learning",
            "capture-auto",
            "--command",
            "implement",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )
    second = _invoke_in_project(
        project,
        [
            "learning",
            "capture-auto",
            "--command",
            "implement",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )

    assert first.exit_code == 0, first.stdout
    assert second.exit_code == 0, second.stdout
    second_payload = json.loads(second.stdout)
    assert second_payload["status"] == "duplicate-snapshot"


def test_learning_capture_auto_ignores_timestamp_only_tracker_changes(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    feature_dir = project / "specs" / "demo-feature"
    _write_implement_tracker(
        feature_dir,
        status="resolved",
        retry_attempts=1,
        failed_tasks=["T002"],
        completed_checks=["pytest -q"],
    )
    tracker_path = feature_dir / "implement-tracker.md"
    tracker_path.write_text(
        tracker_path.read_text(encoding="utf-8").replace(
            'resume_decision: "resume-here"',
            'resume_decision: "resume-here"\nupdated: "2026-04-27T10:00:00Z"',
        ),
        encoding="utf-8",
    )

    first = _invoke_in_project(
        project,
        [
            "learning",
            "capture-auto",
            "--command",
            "implement",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )

    tracker_path.write_text(
        tracker_path.read_text(encoding="utf-8").replace(
            'updated: "2026-04-27T10:00:00Z"',
            'updated: "2026-04-27T10:05:00Z"',
        ),
        encoding="utf-8",
    )

    second = _invoke_in_project(
        project,
        [
            "learning",
            "capture-auto",
            "--command",
            "implement",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )

    assert first.exit_code == 0, first.stdout
    assert second.exit_code == 0, second.stdout
    second_payload = json.loads(second.stdout)
    assert second_payload["status"] == "duplicate-snapshot"


def test_learning_capture_auto_quick_extracts_fallback_constraint(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    workspace = project / ".planning" / "quick" / "260417-001-demo"
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "STATUS.md").write_text(
        "\n".join(
            [
                "---",
                'id: "260417-001"',
                'title: "Demo quick task"',
                'status: "blocked"',
                "---",
                "",
                "## Current Focus",
                "goal: keep the worker result contract aligned",
                "current_focus: recover from runtime outage",
                "next_action: wait for runtime recovery",
                "",
                "## Execution",
                "active_lane: leader-inline-fallback",
                "join_point:",
                "files_or_surfaces: src/specify_cli/__init__.py",
                "execution_fallback: native worker runtime unavailable",
                "blockers: []",
                "recovery_action: retry after runtime comes back",
                "retry_attempts: 1",
                "blocker_reason: runtime unavailable",
                "",
                "## Validation",
                "planned_checks:",
                "  - pytest tests/test_learning_cli.py -q",
                "completed_checks: []",
                "",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture-auto",
            "--command",
            "quick",
            "--workspace",
            str(workspace),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    keys = [item["entry"]["recurrence_key"] for item in payload["captured"]]
    assert (
        "quick.leader-inline-fallback-preserves-runtime-unavailability-reason" in keys
    )


def test_learning_capture_auto_workflow_state_records_blocked_reason(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    feature_dir = project / ".specify" / "features" / "002-demo"
    _write_workflow_state(
        feature_dir,
        next_command="",
        status="blocked",
        blocked_reason="Generated command guidance omitted the runtime helper argument required by the CLI.",
    )

    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture-auto",
            "--command",
            "plan",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "captured"
    entries = [item["entry"] for item in payload["captured"]]
    keys = [entry["recurrence_key"] for entry in entries]
    assert "sp-plan.workflow-state-preserves-blocked-reason" in keys
    blocked = next(
        entry
        for entry in entries
        if entry["recurrence_key"] == "sp-plan.workflow-state-preserves-blocked-reason"
    )
    assert blocked["recommended_action"].startswith("Preserve the blocker")


def test_learning_capture_auto_plan_extracts_route_reason_false_starts_and_constraints(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    feature_dir = project / "specs" / "demo-feature"
    _write_workflow_state(
        feature_dir,
        next_command="/sp.tasks",
        status="blocked",
        route_reason="Planning cannot proceed until the ownership split is made explicit.",
        blocked_reason="Shared boundary ownership is still ambiguous.",
        false_starts=["assumed the adapter layer owned persistence concerns"],
        hidden_dependencies=["deployment workflow depends on the ownership split"],
        reusable_constraints=["keep persistence ownership explicit in plan artifacts"],
    )

    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture-auto",
            "--command",
            "plan",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    entries = [item["entry"] for item in payload["captured"]]
    keys = [entry["recurrence_key"] for entry in entries]
    assert payload["status"] == "captured"
    assert "sp-plan.workflow-state-preserves-reentry-reason" in keys
    assert "sp-plan.workflow-state-preserves-false-starts" in keys
    assert "sp-plan.workflow-state-promotes-discovered-constraints" in keys
    by_key = {entry["recurrence_key"]: entry for entry in entries}
    assert by_key["sp-plan.workflow-state-preserves-reentry-reason"][
        "recommended_action"
    ].startswith("Preserve the next command")
    assert by_key["sp-plan.workflow-state-preserves-false-starts"][
        "recommended_action"
    ].startswith("Check recorded false starts")
    assert by_key["sp-plan.workflow-state-promotes-discovered-constraints"][
        "recommended_action"
    ].startswith("Apply the recorded dependency")


def test_learning_capture_auto_materializes_explicit_semantic_triggers(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    feature_dir = project / "specs" / "semantic-trigger"
    long_correction = (
        "sp-plan must not create tasks.md before sp-tasks, and it must preserve the "
        "complete user rationale even when that rationale exceeds a compact summary "
        "length because the detail is durable evidence rather than display-only output"
    )
    _write_workflow_state(
        feature_dir,
        trigger_signals=[
            f"user_correction: {long_correction}",
            "cognition_gap: generated integration was absent from the path index",
        ],
    )

    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture-auto",
            "--command",
            "plan",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    entries = [item["entry"] for item in payload["captured"]]
    by_type = {entry["learning_type"]: entry for entry in entries}
    assert by_type["user_preference"]["recommended_action"].startswith(
        "Apply the corrected assumption"
    )
    assert long_correction in by_type["user_preference"]["summary"]
    assert long_correction in by_type["user_preference"]["evidence"]
    assert by_type["map_coverage_gap"]["trigger_signals"] == ["cognition_gap"]


def test_learning_capture_auto_semantic_trigger_uses_canonical_signal_and_detail_digest(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    feature_dir = project / "specs" / "semantic-trigger"
    raw_detail = "api_key=secret-value from C:/Users/alice/project"
    _write_workflow_state(
        feature_dir,
        trigger_signals=[f"user_correction: {raw_detail}"],
    )

    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture-auto",
            "--command",
            "plan",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    entry = json.loads(result.stdout)["captured"][0]["entry"]
    assert entry["trigger_signals"] == ["user_correction"]
    assert entry["recurrence_key"].startswith(
        "sp-plan.trigger.user_correction.digest-"
    )
    assert "secret-value" not in entry["recurrence_key"]
    assert "alice" not in json.dumps(entry)
    assert "- feature_dir: specs/semantic-trigger" in entry["evidence"]
    assert str(project.resolve()) not in entry["evidence"]


def test_phase_completion_and_transition_preserve_learning_capture_source(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    feature_dir = project / ".specify" / "features" / "runtime-signal"
    _write_workflow_state(
        feature_dir,
        trigger_signals=[
            "tooling_trap: invoke the project-bound launcher instead of a shadowed global CLI"
        ],
    )
    rich_before = (feature_dir / "workflow-state.md").read_bytes()

    enter_workflow(feature_dir, stage="discussion", expected_revision=0)
    completed = complete_workflow_stage(feature_dir, expected_revision=1)
    transition_workflow(
        feature_dir,
        target_stage="specify",
        expected_revision=completed["data"]["revision"],
    )

    assert (feature_dir / "workflow-state.md").read_bytes() == rich_before
    result = _invoke_in_project(
        project,
        [
            "learning",
            "capture-auto",
            "--command",
            "plan",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )
    assert result.exit_code == 0, result.stdout
    entries = [item["entry"] for item in json.loads(result.stdout)["captured"]]
    assert any(
        entry["learning_type"] == "tooling_trap"
        and "project-bound launcher" in entry["summary"]
        for entry in entries
    )


def test_implement_closeout_validates_state_and_auto_captures(tmp_path: Path) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    feature_dir = project / ".specify" / "features" / "demo-feature"
    _write_workflow_state(feature_dir)
    _write_implement_tracker(
        feature_dir,
        status="resolved",
        retry_attempts=1,
        failed_tasks=["T002"],
        completed_checks=["pytest -q"],
    )
    _write_tasks_and_worker_result(feature_dir)
    seed_existing_workflow_state(feature_dir, stage="implement", revision=7)

    result = _invoke_in_project(
        project,
        [
            "implement",
            "closeout",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["hook_result"]["status"] == "ok"
    assert payload["auto_capture"]["status"] == "captured"
    assert payload["next_command"] == "sp-review (Classic) or spx-review (Advanced)"
    handoff = json.loads(
        (feature_dir / "implementation-handoff.json").read_text(encoding="utf-8")
    )
    assert handoff["human_acceptance_contract_origin"] == "task-index-v2"


def test_implement_closeout_returns_blocked_json_when_session_state_is_missing(
    tmp_path: Path,
) -> None:
    project = tmp_path
    (project / ".specify").mkdir(parents=True, exist_ok=True)
    _seed_learning_templates(project)
    feature_dir = project / "specs" / "demo-feature"
    feature_dir.mkdir(parents=True, exist_ok=True)

    result = _invoke_in_project(
        project,
        [
            "implement",
            "closeout",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 10, result.stdout
    payload = json.loads(result.stdout)
    assert payload["status"] == "blocked"
    assert payload["hook_result"]["status"] == "blocked"
    assert payload["blockers"]
    assert any(
        "workflow-state.md" in message or "implement-tracker.md" in message
        for message in payload["hook_result"]["errors"]
    )


def test_implement_help_surfaces_closeout_command() -> None:
    result = runner.invoke(app, ["implement", "--help"], catch_exceptions=False)

    assert result.exit_code == 0, result.stdout
    assert "closeout" in result.stdout
