from specify_cli.verification import (
    ValidationResult,
    run_verification_commands,
    summarize_validation_results,
    verification_passed,
)


def test_run_verification_commands_records_pass_and_fail_results() -> None:
    commands = ["pytest -q", "ruff check src"]
    seen: list[str] = []

    def runner(command: str) -> tuple[int, str]:
        seen.append(command)
        if command == "pytest -q":
            return 0, "1 passed"
        return 1, "F401 unused import"

    results = run_verification_commands(commands, runner=runner)

    assert seen == commands
    assert results == [
        ValidationResult(command="pytest -q", status="passed", output="1 passed"),
        ValidationResult(command="ruff check src", status="failed", output="F401 unused import"),
    ]


def test_run_verification_commands_stops_after_failure_when_requested() -> None:
    seen: list[str] = []

    def runner(command: str) -> tuple[int, str]:
        seen.append(command)
        return (1, "boom") if command == "pytest -q" else (0, "ok")

    results = run_verification_commands(
        ["pytest -q", "ruff check src"],
        runner=runner,
        stop_on_failure=True,
    )

    assert seen == ["pytest -q"]
    assert len(results) == 1
    assert results[0].status == "failed"


def test_summarize_validation_results_counts_statuses() -> None:
    results = [
        ValidationResult(command="pytest -q", status="passed", output="1 passed"),
        ValidationResult(command="ruff check src", status="failed", output="F401"),
        ValidationResult(command="mypy src", status="skipped", output="not configured"),
    ]

    summary = summarize_validation_results(results)

    assert summary.total == 3
    assert summary.passed == 1
    assert summary.failed == 1
    assert summary.skipped == 1
    assert summary.overall_status == "failed"
    assert verification_passed(results) is False
