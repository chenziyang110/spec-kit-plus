import json
from pathlib import Path

from specify_cli.hooks.engine import run_quality_hook
from specify_cli.learnings import learning_review_status


def _create_project(tmp_path: Path) -> Path:
    project = tmp_path / "hook-learning-project"
    project.mkdir()
    (project / ".specify").mkdir()
    return project


def test_learning_review_blocks_terminal_closeout_without_review(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.learning.review",
        {"command_name": "implement", "terminal_status": "resolved"},
    )

    assert result.status == "blocked"
    assert any("learning review" in message.lower() for message in result.errors)
    assert all("..." not in action for action in result.actions)
    assert all("<" not in action for action in result.actions)
    actions = " ".join(result.actions)
    assert "specify-runtime learning capture-auto" in actions
    assert "specify-runtime learning capture" in actions
    assert "do not edit Learning storage directly" in actions


def test_learning_review_allows_explicit_none_decision(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.learning.review",
        {
            "command_name": "debug",
            "terminal_status": "resolved",
            "learning_review": {
                "decision": "none",
            },
        },
    )

    assert result.status == "ok"
    assert result.data["review"]["decision"] == "none"


def test_learning_hook_deferred_uses_single_canonical_review_queue(
    tmp_path: Path,
) -> None:
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.learning.review",
        {
            "command_name": "debug",
            "terminal_status": "resolved",
            "learning_review": {
                "decision": "deferred",
                "rationale": "Wait for a reusable abstraction.",
            },
        },
    )

    assert result.status == "ok"
    assert learning_review_status(project, command_name="debug")["pending"] == 1
    review_state = json.loads(
        (project / ".planning" / "learnings" / "review-state.json").read_text(
            encoding="utf-8"
        )
    )
    assert len(review_state["items"]) == 1
    signal_path = project / ".planning" / "learnings" / "signal-state.json"
    if signal_path.exists():
        signal_state = json.loads(signal_path.read_text(encoding="utf-8"))
        assert all(
            "learning_review" not in value
            for value in signal_state.values()
            if isinstance(value, dict)
        )


def test_learning_review_blocks_none_decision_when_recent_friction_signal_exists(
    tmp_path: Path,
):
    project = _create_project(tmp_path)

    signal_result = run_quality_hook(
        project,
        "workflow.learning.signal",
        {
            "command_name": "implement",
            "retry_attempts": 2,
            "hypothesis_changes": 1,
            "validation_failures": 1,
            "false_starts": ["retried the same build path without fixing the shell"],
        },
    )
    review_result = run_quality_hook(
        project,
        "workflow.learning.review",
        {
            "command_name": "implement",
            "terminal_status": "resolved",
            "learning_review": {
                "decision": "none",
                "rationale": "The work eventually completed.",
            },
        },
    )

    assert signal_result.status == "warn"
    assert review_result.status == "blocked"
    assert any(
        "recent friction signal" in message.lower() for message in review_result.errors
    )
    assert all("..." not in action for action in review_result.actions)
    actions = " ".join(review_result.actions)
    assert "specify-runtime learning capture-auto" in actions
    assert "specify-runtime learning capture" in actions
    assert "do not edit Learning storage directly" in actions


def test_learning_review_sanitizes_legacy_recent_signal_state_before_blocking(
    tmp_path: Path,
):
    project = _create_project(tmp_path)
    state_path = project / ".planning" / "learnings" / "signal-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(
            {
                "implement": {
                    "command": "sp-implement",
                    "pain_score": 9,
                    "factors": {
                        "retry_attempts": 4,
                        "token=bad-factor": "secret-factor",
                    },
                    "false_starts": ["retried with token=legacy-secret"],
                    "hidden_dependencies": [r"C:\Users\alice\repo ops@example.com"],
                    "trigger_signals": [
                        "user_correction: raw detail should not persist"
                    ],
                    "learning_review": {
                        "decision": "deferred",
                        "rationale": "wait for token=review-secret",
                        "deferred_at": "bad time token=time-secret",
                    },
                    "content_safety": {
                        "sensitivity": "sanitized",
                        "redaction_labels": ["credential", "token=bad-label"],
                    },
                    "unknown": "drop token=unknown-secret",
                    "observed_at": "bad time token=observed-secret",
                },
                "debug": {
                    "command": "sp-debug",
                    "false_starts": ["email ops@example.com"],
                    "unknown": "drop token=other-secret",
                    "observed_at": "2026-01-01",
                },
                "token=bad-command": {
                    "command": "sp-token=bad-command",
                    "false_starts": ["token=command-secret"],
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.learning.review",
        {
            "command_name": "implement",
            "terminal_status": "resolved",
            "learning_review": {
                "decision": "none",
                "rationale": "No learning remains.",
            },
        },
    )
    migrated = state_path.read_text(encoding="utf-8")
    serialized = json.dumps(result.data) + migrated

    assert result.status == "blocked"
    for raw in [
        "legacy-secret",
        "review-secret",
        "unknown-secret",
        "other-secret",
        "bad-factor",
        "secret-factor",
        "time-secret",
        "observed-secret",
        "bad-label",
        "bad-command",
        "command-secret",
        "ops@example.com",
        "alice",
        "raw detail should not persist",
    ]:
        assert raw not in serialized
    migrated_payload = json.loads(migrated)
    assert "token=bad-command" not in migrated_payload
    assert "unknown" not in migrated_payload["implement"]
    assert "unknown" not in migrated_payload["debug"]
    assert "token=bad-factor" not in migrated_payload["implement"]["factors"]
    assert migrated_payload["implement"]["observed_at"] == ""
    assert migrated_payload["implement"]["learning_review"]["deferred_at"] == ""
    assert migrated_payload["debug"]["observed_at"] == ""
    assert migrated_payload["implement"]["trigger_signals"] == ["user_correction"]
    assert migrated_payload["implement"]["content_safety"]["redaction_labels"] == [
        "credential",
        "email",
        "machine_path",
    ]


def test_learning_review_clears_recent_signal_after_non_none_decision(tmp_path: Path):
    project = _create_project(tmp_path)

    run_quality_hook(
        project,
        "workflow.learning.signal",
        {
            "command_name": "implement",
            "retry_attempts": 2,
            "hypothesis_changes": 1,
            "validation_failures": 1,
        },
    )
    capture = run_quality_hook(
        project,
        "workflow.learning.capture",
        {
            "command_name": "implement",
            "learning_type": "pitfall",
            "summary": "Capture repeated implementation friction before closeout",
            "evidence": "Retries and hypothesis changes crossed the learning threshold.",
        },
    )
    captured_review = run_quality_hook(
        project,
        "workflow.learning.review",
        {
            "command_name": "implement",
            "terminal_status": "resolved",
            "learning_review": {
                "decision": "captured",
                "rationale": "Captured the reusable lesson before closeout.",
            },
        },
    )
    followup_none = run_quality_hook(
        project,
        "workflow.learning.review",
        {
            "command_name": "implement",
            "terminal_status": "resolved",
            "learning_review": {
                "decision": "none",
                "rationale": "No new reusable learning remains after the previous capture.",
            },
        },
    )

    assert capture.status == "repaired"
    assert captured_review.status == "ok"
    assert followup_none.status == "ok"


def test_learning_review_deferred_and_manual_capture_needed_preserve_recent_signal(
    tmp_path: Path,
):
    project = _create_project(tmp_path)

    run_quality_hook(
        project,
        "workflow.learning.signal",
        {
            "command_name": "implement",
            "retry_attempts": 2,
            "hypothesis_changes": 1,
            "validation_failures": 1,
        },
    )
    deferred = run_quality_hook(
        project,
        "workflow.learning.review",
        {
            "command_name": "implement",
            "terminal_status": "resolved",
            "learning_review": {
                "decision": "deferred",
                "rationale": "Capture needs the owner workflow state first.",
            },
        },
    )
    manual = run_quality_hook(
        project,
        "workflow.learning.review",
        {
            "command_name": "implement",
            "terminal_status": "resolved",
            "learning_review": {
                "decision": "manual-capture-needed",
                "rationale": "Manual capture needs concise evidence.",
            },
        },
    )
    followup_none = run_quality_hook(
        project,
        "workflow.learning.review",
        {
            "command_name": "implement",
            "terminal_status": "resolved",
            "learning_review": {
                "decision": "none",
                "rationale": "No new reusable learning remains.",
            },
        },
    )

    assert deferred.status == "ok"
    assert manual.status == "ok"
    assert followup_none.status == "blocked"


def test_learning_review_deferred_requires_rationale_and_survives_ttl_until_capture(
    tmp_path: Path,
):
    project = _create_project(tmp_path)

    run_quality_hook(
        project,
        "workflow.learning.signal",
        {
            "command_name": "plan",
            "trigger_signals": ["user_correction: keep the planning boundary"],
        },
    )
    missing_rationale = run_quality_hook(
        project,
        "workflow.learning.review",
        {
            "command_name": "plan",
            "terminal_status": "resolved",
            "learning_review": {"decision": "deferred"},
        },
    )
    deferred = run_quality_hook(
        project,
        "workflow.learning.review",
        {
            "command_name": "plan",
            "terminal_status": "resolved",
            "learning_review": {
                "decision": "deferred",
                "rationale": (
                    r"Capture after token=defer-secret for ops@example.com in "
                    r"C:\Users\alice\repo."
                ),
            },
        },
    )
    state_path = project / ".planning" / "learnings" / "signal-state.json"
    deferred_serialized = json.dumps(deferred.data) + state_path.read_text(
        encoding="utf-8"
    )
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["plan"]["observed_at"] = "2000-01-01T00:00:00Z"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    expired_none = run_quality_hook(
        project,
        "workflow.learning.review",
        {
            "command_name": "plan",
            "terminal_status": "resolved",
            "learning_review": {
                "decision": "none",
                "rationale": "Old signal should have expired.",
            },
        },
    )
    capture = run_quality_hook(
        project,
        "workflow.learning.capture",
        {
            "command_name": "plan",
            "learning_type": "user_preference",
            "summary": "Planning boundary correction must persist",
            "evidence": "Deferred learning signal was captured after review.",
            "trigger_signals": ["user_correction"],
        },
    )
    captured = run_quality_hook(
        project,
        "workflow.learning.review",
        {
            "command_name": "plan",
            "terminal_status": "resolved",
            "learning_review": {
                "decision": "captured",
                "rationale": "Captured matching deferred signal.",
            },
        },
    )
    followup_none = run_quality_hook(
        project,
        "workflow.learning.review",
        {
            "command_name": "plan",
            "terminal_status": "resolved",
            "learning_review": {
                "decision": "none",
                "rationale": "No recent signal remains.",
            },
        },
    )

    assert missing_rationale.status == "blocked"
    assert deferred.status == "ok"
    assert "defer-secret" not in deferred_serialized
    assert "ops@example.com" not in deferred_serialized
    assert "alice" not in deferred_serialized
    assert deferred.data["content_safety"]["redaction_labels"] == [
        "credential",
        "email",
        "machine_path",
    ]
    assert expired_none.status == "blocked"
    assert capture.status == "repaired"
    assert captured.status == "ok"
    assert followup_none.status == "ok"


def test_learning_review_deferred_without_prior_signal_creates_durable_state(
    tmp_path: Path,
):
    project = _create_project(tmp_path)

    deferred = run_quality_hook(
        project,
        "workflow.learning.review",
        {
            "command_name": "debug",
            "terminal_status": "resolved",
            "learning_review": {
                "decision": "manual-capture-needed",
                "rationale": "Capture manually after owner review.",
            },
        },
    )
    state = json.loads(
        (project / ".planning" / "learnings" / "review-state.json").read_text(
            encoding="utf-8"
        )
    )
    none = run_quality_hook(
        project,
        "workflow.learning.review",
        {
            "command_name": "debug",
            "terminal_status": "resolved",
            "learning_review": {
                "decision": "none",
                "rationale": "No recent learning remains.",
            },
        },
    )
    capture = run_quality_hook(
        project,
        "workflow.learning.capture",
        {
            "command_name": "debug",
            "learning_type": "pitfall",
            "summary": "Manual capture request must persist",
            "evidence": "The deferred manual capture was written.",
        },
    )
    captured = run_quality_hook(
        project,
        "workflow.learning.review",
        {
            "command_name": "debug",
            "terminal_status": "resolved",
            "learning_review": {
                "decision": "captured",
                "rationale": "Captured matching manual request.",
            },
        },
    )

    assert deferred.status == "ok"
    assert state["items"][0]["decision"] == "manual-capture-needed"
    assert state["items"][0]["command"] == "sp-debug"
    assert none.status == "blocked"
    assert capture.status == "repaired"
    assert captured.status == "ok"


def test_learning_signal_merges_with_pending_deferred_review_without_overwrite(
    tmp_path: Path,
):
    project = _create_project(tmp_path)

    deferred = run_quality_hook(
        project,
        "workflow.learning.review",
        {
            "command_name": "plan",
            "terminal_status": "resolved",
            "learning_review": {
                "decision": "deferred",
                "rationale": "Keep original rationale until capture.",
            },
        },
    )
    first_state = json.loads(
        (project / ".planning" / "learnings" / "review-state.json").read_text(
            encoding="utf-8"
        )
    )
    signal = run_quality_hook(
        project,
        "workflow.learning.signal",
        {
            "command_name": "plan",
            "retry_attempts": 2,
            "false_starts": ["retried with token=merge-secret"],
            "hidden_dependencies": ["ops@example.com must sign off"],
            "trigger_signals": ["user_correction: preserve the boundary"],
        },
    )
    merged_state = json.loads(
        (project / ".planning" / "learnings" / "signal-state.json").read_text(
            encoding="utf-8"
        )
    )
    pending_state = json.loads(
        (project / ".planning" / "learnings" / "review-state.json").read_text(
            encoding="utf-8"
        )
    )
    serialized = json.dumps(merged_state)

    assert deferred.status == "ok"
    assert signal.status == "warn"
    assert pending_state == first_state
    assert "learning_review" not in merged_state["plan"]
    assert merged_state["plan"]["trigger_signals"] == ["user_correction"]
    assert "merge-secret" not in serialized
    assert "ops@example.com" not in serialized
    assert merged_state["plan"]["content_safety"]["redaction_labels"] == [
        "credential",
        "email",
    ]


def test_learning_review_requires_matching_durable_capture_before_clearing_signal(
    tmp_path: Path,
):
    project = _create_project(tmp_path)

    run_quality_hook(
        project,
        "workflow.learning.signal",
        {
            "command_name": "plan",
            "trigger_signals": [
                "user_correction: plan must not create tasks.md before sp-tasks"
            ],
        },
    )
    missing_capture = run_quality_hook(
        project,
        "workflow.learning.review",
        {
            "command_name": "plan",
            "terminal_status": "resolved",
            "learning_review": {
                "decision": "captured",
                "rationale": "Claimed capture without durable storage.",
            },
        },
    )
    signal_state = json.loads(
        (project / ".planning" / "learnings" / "signal-state.json").read_text(
            encoding="utf-8"
        )
    )
    signal_state["plan"]["trigger_signals"] = ["user_correction"]
    (project / ".planning" / "learnings" / "signal-state.json").write_text(
        json.dumps(signal_state),
        encoding="utf-8",
    )
    capture = run_quality_hook(
        project,
        "workflow.learning.capture",
        {
            "command_name": "plan",
            "learning_type": "user_preference",
            "summary": "Plan must not create tasks before the task workflow",
            "evidence": "The user corrected the workflow boundary.",
            "trigger_signals": ["user_correction"],
        },
    )
    durable_capture = run_quality_hook(
        project,
        "workflow.learning.review",
        {
            "command_name": "plan",
            "terminal_status": "resolved",
            "learning_review": {
                "decision": "captured",
                "rationale": "Captured matching semantic trigger.",
            },
        },
    )
    followup_none = run_quality_hook(
        project,
        "workflow.learning.review",
        {
            "command_name": "plan",
            "terminal_status": "resolved",
            "learning_review": {
                "decision": "none",
                "rationale": "No recent signal remains.",
            },
        },
    )

    assert missing_capture.status == "blocked"
    assert capture.status == "repaired"
    assert durable_capture.status == "ok"
    assert followup_none.status == "ok"


def test_learning_signal_warns_when_pain_score_crosses_threshold(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.learning.signal",
        {
            "command_name": "quick",
            "retry_attempts": 2,
            "hypothesis_changes": 1,
            "validation_failures": 1,
            "false_starts": ["treated runtime issue as code issue"],
        },
    )

    assert result.status == "warn"
    assert result.data["pain_score"] >= 5
    assert "record a learning review decision" in result.actions[0]
    assert "specify-runtime learning capture-auto" in " ".join(result.actions)
    assert "do not edit Learning storage directly" in " ".join(result.actions)
    assert "specify hook" not in " ".join(result.actions)


def test_learning_signal_sanitizes_persisted_false_starts_and_hidden_dependencies(
    tmp_path: Path,
):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.learning.signal",
        {
            "command_name": "quick",
            "retry_attempts": 2,
            "false_starts": ["retried with password=raw-secret"],
            "hidden_dependencies": [r"C:\Users\alice\repo needs ops@example.com"],
        },
    )
    state_text = (
        project / ".planning" / "learnings" / "signal-state.json"
    ).read_text(encoding="utf-8")
    serialized = json.dumps(result.data) + state_text

    assert result.status == "warn"
    assert "raw-secret" not in serialized
    assert "ops@example.com" not in serialized
    assert "alice" not in serialized
    assert result.data["content_safety"] == {
        "sensitivity": "sanitized",
        "redaction_labels": ["credential", "email", "machine_path"],
    }


def test_learning_signal_warns_on_one_explicit_semantic_trigger(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.learning.signal",
        {
            "command_name": "plan",
            "trigger_signals": [
                "user_correction: plan must not create tasks.md before sp-tasks"
            ],
        },
    )

    assert result.status == "warn"
    assert result.data["pain_score"] >= result.data["threshold"]
    assert result.data["trigger_signals"] == ["user_correction"]
    assert result.data["command"] == "sp-plan"
    assert "sp-sp-" not in " ".join(result.actions)


def test_learning_inject_derives_targets_from_learning_type(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.learning.inject",
        {
            "command_name": "map-build",
            "learning_type": "map_coverage_gap",
            "summary": "Atlas omitted runtime watcher dependencies",
        },
    )

    assert result.status == "ok"
    assert "sp-map-scan" in result.data["injection_targets"]
    assert "sp-map-build" in result.data["injection_targets"]
    assert "PROJECT-HANDBOOK.md" in result.data["injection_targets"]


def test_learning_inject_sanitizes_summary_output(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.learning.inject",
        {
            "command_name": "debug",
            "learning_type": "pitfall",
            "summary": "Debug summary leaked token=inject-secret for ops@example.com",
        },
    )

    serialized = json.dumps(result.data)
    assert result.status == "ok"
    assert "inject-secret" not in serialized
    assert "ops@example.com" not in serialized
    assert result.data["content_safety"]["redaction_labels"] == [
        "credential",
        "email",
    ]


def test_learning_capture_hook_records_structured_candidate(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.learning.capture",
        {
            "command_name": "debug",
            "learning_type": "tooling_trap",
            "summary": "Watcher loops can masquerade as process-manager failures",
            "evidence": "Repeated process fixes failed; excluding the log directory stopped restarts.",
            "pain_score": 6,
            "false_starts": ["job object cleanup", "port conflict"],
            "rejected_paths": ["process manager root cause"],
            "decisive_signal": "restart stopped when watcher ignored generated logs",
            "root_cause_family": "dev-tooling-watch-loop",
            "injection_targets": ["sp-debug", "sp-map-scan", "sp-map-build"],
            "promotion_hint": "promote after another watcher-loop recurrence",
        },
    )

    assert result.status == "repaired"
    entry = result.data["capture"]["entry"]
    assert entry["learning_type"] == "tooling_trap"
    assert entry["pain_score"] == 6
    assert entry["false_starts"] == ["job object cleanup", "port conflict"]

    candidates = project / ".planning" / "learnings" / "candidates.md"
    assert "Watcher loops can masquerade" in candidates.read_text(encoding="utf-8")


def test_learning_capture_hook_outputs_sanitized_injection_targets(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.learning.capture",
        {
            "command_name": "debug",
            "learning_type": "tooling_trap",
            "summary": "Capture target sanitization",
            "evidence": "Safe evidence.",
            "injection_targets": [
                r"C:\Users\alice\repo",
                "owner ops@example.com",
            ],
        },
    )

    serialized = json.dumps(result.data)
    assert result.status == "repaired"
    assert "alice" not in serialized
    assert "ops@example.com" not in serialized
    assert result.data["injection_targets"] == [
        "<USER_HOME>/repo",
        "owner [REDACTED_EMAIL]",
    ]
