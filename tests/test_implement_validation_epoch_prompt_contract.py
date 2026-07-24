from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _flat(*relative_paths: str) -> str:
    content = "\n".join(_read(path) for path in relative_paths).lower()
    return " ".join(content.replace("`", "").split())


CLASSIC_IMPLEMENT = (
    "templates/commands/implement.md",
    "templates/command-partials/implement/shell.md",
    "templates/command-references/implement/red-first-and-validation.md",
    "templates/command-references/implement/branch-review-and-closeout.md",
    "templates/command-references/implement/subagent-worker-contract.md",
    "templates/worker-prompts/implementer.md",
)

ADVANCED_IMPLEMENT = (
    "templates/advanced-skills/spx-implement/SKILL.md",
    "templates/advanced-skills/spx-implement/references/execution-contract.md",
    "templates/advanced-skills/spx-implement/references/worker-contract.md",
)

CLASSIC_REVIEW = (
    "templates/commands/review.md",
    "templates/command-partials/review/shell.md",
    "templates/command-references/review/subagent-review-contract.md",
    "templates/command-references/review/repair-and-revalidation.md",
    "templates/command-references/review/final-claim-and-handoff.md",
)

ADVANCED_REVIEW = (
    "templates/advanced-skills/spx-review/SKILL.md",
    "templates/advanced-skills/spx-review/references/review-contract.md",
    "templates/advanced-skills/spx-review/references/worker-contract.md",
)


def test_implement_profiles_define_three_logical_gates_with_retryable_attempts() -> None:
    for paths in (CLASSIC_IMPLEMENT, ADVANCED_IMPLEMENT):
        content = _flat(*paths)

        assert "task-index.validation_policy" in content
        assert "mode: feature_epochs" in content
        assert "max_epochs: 3" in content
        assert "budget_scope: implement-review" in content
        assert "implementation-review/validation-runs.json" in content
        assert "heavy_gate_owner: leader" in content
        assert "implement validation-status --feature-dir <feature-dir> --format json" in content
        assert "implement validation-start --feature-dir <feature-dir> --stage implement" in content
        assert "--purpose <baseline|convergence>" in content
        assert "implement validation-finish --feature-dir <feature-dir> --run-id <vn>" in content
        assert "--status <passed|failed|interrupted>" in content
        assert "logical gates" in content
        assert "attempts inside" in content or "attempts against" in content
        assert "at most three" in content or "three logical gates" in content
        assert "shared across implement and review" in content
        assert "source fingerprint" in content
        assert "expected pre-change failure" in content
        assert "runner_timeout" in content
        assert "rerun the full command" in content
        assert "open-handle" in content and "process-exit" in content
        assert "deterministic bounded shards" in content
        assert "agent-owned" in content
        assert "human" in content and "skip them" in content
        assert "interrupted" in content and (
            "not failed" in content or "never a test failure" in content
        )
        assert "real assertion or verification failure" in content
        assert "new fingerprint" in content
        assert "never open a fourth" in content or "never start a fourth" in content
        assert "deferral-propose" in content and "deferral-confirm" in content
        assert "never means passed" in content or "never accepted" in content
        assert "expires at review" in content


def test_review_profiles_continue_the_ledger_and_resolve_transferred_scope() -> None:
    for paths in (CLASSIC_REVIEW, ADVANCED_REVIEW):
        content = _flat(*paths)

        assert "implementation-review/validation-runs.json" in content
        assert "implement validation-status --feature-dir <feature-dir> --format json" in content
        assert "implement validation-start --feature-dir <feature-dir> --stage review" in content
        assert "--purpose delivery" in content
        assert "implement validation-finish --feature-dir <feature-dir> --run-id <vn>" in content
        assert "--status <passed|failed|interrupted>" in content
        assert "delivery gate" in content
        assert "attempt" in content
        assert "shared across implement and review" in content
        assert "do not reset" in content
        assert "interrupted" in content and "not failed" in content
        assert "open-handle" in content and "process-exit" in content
        assert "deterministic bounded shards" in content
        assert "new fingerprint" in content
        assert "never open a fourth" in content
        assert "official real entrypoint" in content
        assert "implementation_deferrals" in content
        assert "status: resolved" in content
        assert "--restart-stale" in content
        assert "malformed" in content
        assert "exact old bytes" in content


def test_task_workers_only_run_cheap_checks_and_leader_owns_heavy_gates() -> None:
    for paths in (CLASSIC_IMPLEMENT, ADVANCED_IMPLEMENT):
        content = _flat(*paths)

        assert "task checks" in content
        assert "cheap" in content
        assert "heavyweight" in content
        assert "leader" in content and "validation attempt" in content
        assert "must not run" in content and "per txx" in content
        assert "test impact" in content
        assert "created but not wired" in content
        assert "dependency-safe work" in content
        assert "feature verification remains pending" in content

    classic_packet = _flat(
        "templates/command-references/implement/subagent-worker-contract.md"
    )
    assert "epoch_validation" not in classic_packet
    assert "task_checks" in classic_packet
    assert "validation_gates" in classic_packet
    assert "verify_commands" in classic_packet
    assert "required_validation" in classic_packet
    assert "remain inputs to the leader-owned gate attempt" in classic_packet


def test_ui_capture_is_integrated_in_an_attempt_not_repeated_per_microtask() -> None:
    for paths in (CLASSIC_IMPLEMENT + CLASSIC_REVIEW, ADVANCED_IMPLEMENT + ADVANCED_REVIEW):
        content = _flat(*paths)

        assert "do not run the full viewport/state capture loop per txx" in content
        assert "evidence_scope: integrated" in content
        assert "real-entrypoint" in content or "real entrypoint" in content
        assert "visual_capture" in content
        assert "runtime_diagnostics" in content


def test_review_batches_repairs_before_opening_another_attempt() -> None:
    for paths in (CLASSIC_REVIEW, ADVANCED_REVIEW):
        content = _flat(*paths)

        assert "complete repair batch" in content
        assert "do not open an attempt per finding or per repair" in content


def test_passive_testing_guidance_defers_to_workflow_gate_ownership() -> None:
    passive_paths = (
        "templates/passive-skills/tdd-workflow/SKILL.md",
        "templates/passive-skills/test-driven-development/SKILL.md",
        "templates/passive-skills/verification-before-completion/SKILL.md",
        "templates/passive-skills/subagent-driven-development/SKILL.md",
        "templates/passive-skills/subagent-driven-development/implementer-prompt.md",
        "templates/passive-skills/webapp-testing/SKILL.md",
    )

    for path in passive_paths:
        content = _flat(path)

        assert "workflow-owned validation" in content, path
        assert "validation" in content and "attempt" in content, path
        assert (
            "must not start an extra gate or" in content
            or "must not start an extra logical gate or" in content
        ), path

    verification = _flat(
        "templates/passive-skills/verification-before-completion/SKILL.md"
    )
    assert "moving to the next txx does not require" in verification
