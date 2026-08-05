import json
from collections.abc import Callable
from pathlib import Path
import re

import pytest
from jsonschema import Draft202012Validator
from specify_cli.learning_assessment import (
    ASSESSMENT_DECISIONS,
    ASSESSMENT_REDACTION_LABELS,
    DECISION_REASONS,
    VALUE_REASON_CODES,
)
from specify_cli.learnings import (
    KNOWN_COMMANDS,
    _empty_metric_bucket as _empty_runtime_metric_bucket,
    _load_learning_metrics,
    capture_learning,
)


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _schema() -> dict:
    return json.loads(
        (PROJECT_ROOT / "templates" / "project-learning-record-schema.json").read_text(
            encoding="utf-8"
        )
    )


def _policy_schema() -> dict:
    return json.loads(
        (PROJECT_ROOT / "templates" / "project-learning-policy-schema.json").read_text(
            encoding="utf-8"
        )
    )


def _metrics_schema() -> dict:
    return json.loads(
        (
            PROJECT_ROOT / "templates" / "project-learning-metrics-schema.json"
        ).read_text(encoding="utf-8")
    )


def _metric_bucket() -> dict[str, object]:
    return {
        "totals": {
            "assessed": 1,
            "captured": 1,
            "candidate_captured": 1,
            "confirmed": 0,
            "promoted": 0,
            "deferred": 0,
            "ignored": 0,
        },
        "decisions": {
            "capture-safe": 1,
            "capture-sanitized": 0,
            "defer": 0,
            "ignore": 0,
        },
        "value_tiers": {"high": 1, "medium": 0, "low": 0},
        "risk_tiers": {"none": 1, "moderate": 0, "high": 0},
        "reason_codes": {
            "explicit_capture": 1,
            "workflow_gap": 0,
            "user_correction": 0,
            "reusable_constraint": 0,
            "near_miss": 0,
            "repeated_occurrence": 0,
            "tooling_trap": 0,
            "recovery_path": 0,
            "high_signal": 0,
            "routine_outcome": 0,
        },
        "redaction_labels": {
            "credential": 0,
            "email": 0,
            "private_key": 0,
            "machine_path": 0,
            "personal_identifier": 0,
            "business_identifier": 0,
            "organization_sensitive": 0,
        },
    }


@pytest.mark.parametrize("schema_loader", [_schema, _policy_schema, _metrics_schema])
def test_project_learning_schemas_are_valid_draft_2020_12(
    schema_loader: Callable[[], dict[str, object]],
) -> None:
    Draft202012Validator.check_schema(schema_loader())


def test_project_learning_schema_enums_match_python_assessment_runtime() -> None:
    schema = _schema()
    definitions = schema["$defs"]

    assert set(definitions["learningValue"]["properties"]["reason_codes"]["items"]["enum"]) == VALUE_REASON_CODES
    assert set(definitions["assessment"]["properties"]["decision"]["enum"]) == ASSESSMENT_DECISIONS
    assert set(definitions["assessment"]["properties"]["decision_reason"]["enum"]) == DECISION_REASONS
    assert set(definitions["redactionLabels"]["items"]["enum"]) == ASSESSMENT_REDACTION_LABELS


def test_project_learning_metrics_schema_commands_match_both_runtimes() -> None:
    schema_commands = set(
        _metrics_schema()["properties"]["by_command"]["propertyNames"]["enum"]
    )
    go_source = (PROJECT_ROOT / "tools" / "specify-runtime" / "learning.go").read_text(
        encoding="utf-8"
    )
    match = re.search(
        r"var knownLearningCommands = \[\]string\{(?P<body>.*?)\n\}",
        go_source,
        flags=re.DOTALL,
    )

    assert match is not None
    go_commands = set(re.findall(r'"(sp-[a-z0-9-]+)"', match.group("body")))
    assert schema_commands == set(KNOWN_COMMANDS) == go_commands


def _assessment(
    *,
    tier: str = "high",
    sensitivity: str = "sanitized",
    risk_tier: str = "high",
    decision: str = "capture-sanitized",
) -> dict[str, object]:
    redaction_labels = (
        []
        if sensitivity == "safe"
        else [
            "personal_identifier",
            "business_identifier",
            "organization_sensitive",
        ]
    )
    return {
        "learning_value": {
            "tier": tier,
            "reason_codes": ["reusable_constraint"],
        },
        "content_safety": {
            "sensitivity": sensitivity,
            "risk_tier": risk_tier,
            "redaction_labels": redaction_labels,
        },
        "decision": decision,
        "decision_reason": {
            "capture-safe": "safe_content",
            "capture-sanitized": "valuable_after_abstraction",
            "defer": "sensitive_without_reusable_abstraction",
            "ignore": "routine_outcome",
        }[decision],
    }


def _summary_card(**overrides: object) -> dict[str, object]:
    card: dict[str, object] = {
        "ref": "verification.generated-entrypoint",
        "summary": "Verify generated entrypoints after template changes",
        "action": "Regenerate the integration and verify its real entrypoint.",
        "type": "verification_gap",
        "status": "candidate",
        "signal": "high",
        "occurrences": 1,
        "applies_to": ["implement"],
        "trigger_signals": ["validation_gap"],
        "source_layer": "candidate",
        "show_argv": [
            "specify-runtime",
            "learning",
            "show",
            "--ref",
            "verification.generated-entrypoint",
            "--format",
            "json",
        ],
    }
    card.update(overrides)
    return card


def _summary_list_payload(assessment: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": 1,
        "record_schema": ".specify/templates/project-learning-record-schema.json#/$defs/summaryList",
        "command": "sp-implement",
        "policy": "consume-capture",
        "filters": {"type": None, "status": None, "query": None},
        "pagination": {
            "cursor": 0,
            "limit": 10,
            "returned": 1,
            "total": 1,
            "next_cursor": None,
            "next_argv": None,
        },
        "items": [_summary_card(assessment=assessment)],
        "warnings": [],
    }


def test_project_learning_schema_accepts_optional_safety_projection_fields() -> None:
    validator = Draft202012Validator(_schema())
    payload = {
        "schema_version": 1,
        "record_schema": ".specify/templates/project-learning-record-schema.json#/$defs/startSummary",
        "command": "sp-implement",
        "policy": "consume-capture",
        "read_only": True,
        "items": [
            _summary_card(
                sensitivity="sanitized",
                redaction_labels=[
                    "credential",
                    "email",
                    "private_key",
                    "machine_path",
                    "personal_identifier",
                    "business_identifier",
                    "organization_sensitive",
                ],
                assessment=_assessment(),
            )
        ],
        "pagination": {
            "cursor": 0,
            "limit": 10,
            "returned": 1,
            "total": 1,
            "next_cursor": None,
            "next_argv": None,
        },
        "promotion_ready": [],
        "needs_confirmation": [],
        "warnings": [],
    }

    assert list(validator.iter_errors(payload)) == []


def test_project_learning_schema_accepts_optional_detail_content_safety() -> None:
    validator = Draft202012Validator(_schema())
    payload = {
        "schema_version": 1,
        "record_schema": ".specify/templates/project-learning-record-schema.json#/$defs/detailRecord",
        "ref": "verification.generated-entrypoint",
        "id": "verification.generated-entrypoint",
        "summary": "Verify generated entrypoints after template changes",
        "type": "verification_gap",
        "status": "confirmed",
        "guidance": {
            "problem": "Source checks can pass while generated integrations are stale.",
            "action": "Regenerate the integration and verify the installed entrypoint.",
            "avoid": ["Claiming completion from source-only checks"],
            "success_criteria": ["Installed output matches the template source"],
            "exceptions": ["No generated consumer exists"],
        },
        "applicability": {
            "commands": ["implement"],
            "trigger_signals": ["validation_gap"],
            "scope": "Generated integration surfaces",
        },
        "evidence": {
            "observation": "A prior source-only fix left installed commands stale.",
            "decisive_signal": "Generated output diverged from template source.",
            "false_starts": ["Running only source tests"],
            "rejected_paths": ["Skipping regeneration"],
            "root_cause_family": "generated-surface drift",
        },
        "provenance": {
            "source_command": "implement",
            "first_seen": "2026-08-04",
            "last_seen": "2026-08-04",
            "occurrences": 1,
            "source_layer": "confirmed-learning",
        },
        "lifecycle": {
            "signal": "high",
            "pain_score": 3,
            "injection_targets": ["implement"],
            "promotion_hint": "Confirm before project-rule promotion.",
        },
        "content_safety": {
            "sensitivity": "sanitized",
            "risk_tier": "moderate",
            "redaction_labels": ["machine_path"],
        },
        "assessment": _assessment(),
        "detail_path": None,
        "warnings": [],
    }

    assert list(validator.iter_errors(payload)) == []


def test_project_learning_schema_keeps_legacy_payloads_valid_without_safety_fields() -> None:
    validator = Draft202012Validator(_schema())
    payload = {
        "schema_version": 1,
        "record_schema": ".specify/templates/project-learning-record-schema.json#/$defs/summaryList",
        "command": "sp-specify",
        "policy": "consume-capture",
        "filters": {"type": None, "status": None, "query": None},
        "pagination": {
            "cursor": 0,
            "limit": 10,
            "returned": 1,
            "total": 1,
            "next_cursor": None,
            "next_argv": None,
        },
        "items": [_summary_card(trigger_signals=["ArchiveFlow"])],
        "warnings": [],
    }

    assert list(validator.iter_errors(payload)) == []


def test_project_learning_schema_accepts_safe_assessment_without_redaction_labels() -> None:
    validator = Draft202012Validator(_schema())
    payload = _summary_list_payload(
        _assessment(
            sensitivity="safe",
            risk_tier="none",
            decision="capture-safe",
        )
    )

    assert list(validator.iter_errors(payload)) == []


@pytest.mark.parametrize(
    "assessment",
    [
        _assessment(
            sensitivity="safe", risk_tier="none", decision="capture-safe"
        ),
        _assessment(decision="capture-sanitized"),
        _assessment(decision="defer"),
        _assessment(
            tier="low", sensitivity="safe", risk_tier="none", decision="ignore"
        ),
    ],
    ids=["capture_safe", "capture_sanitized", "defer", "ignore"],
)
def test_project_learning_schema_accepts_every_consistent_assessment_decision(
    assessment: dict[str, object],
) -> None:
    validator = Draft202012Validator(_schema())

    assert list(validator.iter_errors(_summary_list_payload(assessment))) == []


def test_project_learning_schema_rejects_unknown_redaction_labels() -> None:
    validator = Draft202012Validator(_schema())
    payload = {
        "schema_version": 1,
        "record_schema": ".specify/templates/project-learning-record-schema.json#/$defs/startSummary",
        "command": "sp-implement",
        "policy": "consume-capture",
        "read_only": True,
        "items": [
            _summary_card(
                sensitivity="sanitized",
                redaction_labels=["phone_number"],
            )
        ],
        "pagination": {
            "cursor": 0,
            "limit": 10,
            "returned": 1,
            "total": 1,
            "next_cursor": None,
            "next_argv": None,
        },
        "promotion_ready": [],
        "needs_confirmation": [],
        "warnings": [],
    }

    assert list(validator.iter_errors(payload)) != []


@pytest.mark.parametrize(
    "assessment",
    [
        {
            "learning_value": {
                "tier": "high",
                "reason_codes": ["user_correction"],
            },
            "content_safety": {
                "sensitivity": "sanitized",
                "risk_tier": "high",
                "redaction_labels": ["credential"],
            },
            "decision": "ignore",
            "decision_reason": "routine_outcome",
        },
        _assessment(sensitivity="safe", risk_tier="none"),
        {
            "learning_value": {"tier": "medium", "reason_codes": []},
            "content_safety": {
                "sensitivity": "safe",
                "risk_tier": "none",
                "redaction_labels": [],
            },
            "decision": "capture-safe",
            "decision_reason": "reusable",
        },
        {
            "learning_value": {
                "tier": "medium",
                "reason_codes": ["verbatim incident details"],
            },
            "content_safety": {
                "sensitivity": "safe",
                "risk_tier": "none",
                "redaction_labels": [],
            },
            "decision": "capture-safe",
            "decision_reason": "safe_content",
        },
        {
            "learning_value": {
                "tier": "medium",
                "reason_codes": ["reusable_constraint"],
            },
            "content_safety": {
                "sensitivity": "safe",
                "risk_tier": "none",
                "redaction_labels": [],
            },
            "decision": "capture-safe",
            "decision_reason": "raw token was abc123",
        },
        {
            "learning_value": {
                "tier": "medium",
                "reason_codes": ["reusable_constraint"],
            },
            "content_safety": {
                "sensitivity": "safe",
                "risk_tier": "none",
                "redaction_labels": [],
            },
            "decision": "capture-safe",
            "decision_reason": "valuable_after_abstraction",
        },
        {
            "learning_value": {
                "tier": "low",
                "reason_codes": ["routine_outcome"],
            },
            "content_safety": {
                "sensitivity": "safe",
                "risk_tier": "none",
                "redaction_labels": [],
            },
            "decision": "capture-safe",
            "decision_reason": "safe_content",
        },
        {
            "learning_value": {
                "tier": "high",
                "reason_codes": ["user_correction"],
            },
            "content_safety": {
                "sensitivity": "safe",
                "risk_tier": "none",
                "redaction_labels": [],
            },
            "decision": "defer",
            "decision_reason": "sensitive_without_reusable_abstraction",
        },
    ],
    ids=[
        "high_value_cannot_be_ignored",
        "sanitized_capture_requires_sanitized_content",
        "reason_codes_must_not_be_empty",
        "reason_codes_are_canonical",
        "decision_reason_is_canonical",
        "decision_reason_must_match_decision",
        "low_value_must_be_ignored",
        "defer_requires_sanitized_content",
    ],
)
def test_project_learning_schema_rejects_inconsistent_assessment(
    assessment: dict[str, object],
) -> None:
    validator = Draft202012Validator(_schema())
    payload = _summary_list_payload(assessment)

    assert list(validator.iter_errors(payload)) != []


def test_project_learning_policy_schema_accepts_only_bounded_literal_detectors() -> None:
    validator = Draft202012Validator(_policy_schema())
    policy = {
        "detectors": {
            "secret_prefixes": ["acme_live_"],
            "sensitive_key_names": ["customer_secret"],
            "business_id_prefixes": ["CUST-"],
            "sensitive_terms": ["Project Zephyr"],
        },
        "deferred_review_days": 30,
    }

    assert list(validator.iter_errors(policy)) == []


@pytest.mark.parametrize(
    "policy",
    [
        {"detectors": {"regex": ["(?s).*"]}},
        {"detectors": {"secret_prefixes": [f"prefix-{index}" for index in range(65)]}},
        {"detectors": {"sensitive_terms": ["x" * 129]}},
        {"deferred_review_days": 0},
        {"deferred_review_days": 366},
        {"detectors": {"sensitive_terms": ["   "]}},
        {"detectors": {"sensitive_terms": ["safe\nunsafe"]}},
        {"detectors": {"sensitive_terms": ["safe\u0085unsafe"]}},
    ],
    ids=[
        "arbitrary_regex",
        "too_many_literals",
        "literal_too_long",
        "review_days_too_low",
        "review_days_too_high",
        "whitespace_only_literal",
        "control_character_literal",
        "c1_control_character_literal",
    ],
)
def test_project_learning_policy_schema_rejects_unbounded_configuration(
    policy: dict[str, object],
) -> None:
    validator = Draft202012Validator(_policy_schema())

    assert list(validator.iter_errors(policy)) != []


def test_project_learning_metrics_schema_accepts_only_aggregate_canonical_counts() -> None:
    validator = Draft202012Validator(_metrics_schema())
    assert _metrics_schema()["properties"]["by_command"]["maxProperties"] == 64
    payload = {
        "schema_version": 1,
        "global": _metric_bucket(),
        "by_command": {"sp-implement": _metric_bucket()},
    }

    assert list(validator.iter_errors(payload)) == []


def test_python_learning_metrics_runtime_emits_schema_valid_empty_and_event_states(
    tmp_path: Path,
) -> None:
    validator = Draft202012Validator(_metrics_schema())
    empty = _load_learning_metrics(tmp_path)

    assert list(validator.iter_errors(empty)) == []
    assert empty == {
        "schema_version": 1,
        "global": _empty_runtime_metric_bucket(),
        "by_command": {},
    }

    capture_learning(
        tmp_path,
        command_name="debug",
        learning_type="workflow_gap",
        summary="Preserve the re-entry reason before handoff",
        evidence="The route changed and the next stage could not resume safely",
        recommended_action="Record the route reason in durable workflow state",
    )
    metrics_path = tmp_path / ".planning" / "learnings" / "metrics.json"
    one_event = json.loads(metrics_path.read_text(encoding="utf-8"))

    assert list(validator.iter_errors(one_event)) == []
    assert one_event["global"]["totals"]["assessed"] == 1
    assert one_event["global"]["totals"]["candidate_captured"] == 1
    assert one_event["by_command"]["sp-debug"]["decisions"]["capture-safe"] == 1


@pytest.mark.parametrize(
    "forbidden_field",
    [
        "summary",
        "evidence",
        "ref",
        "path",
        "rationale",
        "timestamp",
        "age_buckets",
    ],
)
def test_project_learning_metrics_schema_rejects_agent_content_and_references(
    forbidden_field: str,
) -> None:
    validator = Draft202012Validator(_metrics_schema())
    global_bucket = _metric_bucket()
    global_bucket[forbidden_field] = "must not persist"
    payload = {
        "schema_version": 1,
        "global": global_bucket,
        "by_command": {},
    }

    assert list(validator.iter_errors(payload)) != []


@pytest.mark.parametrize(
    "payload",
    [
        {
            "schema_version": 1,
            "global": _metric_bucket(),
            "by_command": {"../../private": _metric_bucket()},
        },
        {
            "schema_version": 1,
            "global": {
                **_metric_bucket(),
                "totals": {**_metric_bucket()["totals"], "assessed": -1},
            },
            "by_command": {},
        },
        {
            "schema_version": 1,
            "global": _metric_bucket(),
            "by_command": {
                f"sp-command-{index}": _metric_bucket() for index in range(65)
            },
        },
    ],
    ids=["unsafe_command_key", "negative_count", "too_many_commands"],
)
def test_project_learning_metrics_schema_rejects_noncanonical_dimensions(
    payload: dict[str, object],
) -> None:
    validator = Draft202012Validator(_metrics_schema())

    assert list(validator.iter_errors(payload)) != []
