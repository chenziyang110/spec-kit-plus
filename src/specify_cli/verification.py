"""Shared verification helpers for execution and debug flows."""

from __future__ import annotations

import subprocess
from dataclasses import asdict, dataclass
from typing import Callable, Literal, Sequence


ValidationStatus = Literal["passed", "failed", "skipped"]
VerificationOverallStatus = Literal["passed", "failed", "skipped"]
VerificationRunner = Callable[[str], tuple[int, str]]


@dataclass(slots=True)
class ValidationResult:
    command: str
    status: ValidationStatus
    output: str = ""

    def to_payload(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True, frozen=True)
class VerificationSummary:
    total: int
    passed: int
    failed: int
    skipped: int
    overall_status: VerificationOverallStatus


def default_verification_runner(command: str) -> tuple[int, str]:
    result = subprocess.run(
        command,
        shell=True,
        capture_output=True,
        text=True,
        check=False,
    )
    parts: list[str] = []
    if result.stdout:
        parts.append(result.stdout.strip())
    if result.stderr:
        parts.append(result.stderr.strip())
    output = "\n".join(part for part in parts if part).strip()
    return result.returncode, output


def run_verification_commands(
    commands: Sequence[str],
    *,
    runner: VerificationRunner | None = None,
    stop_on_failure: bool = False,
) -> list[ValidationResult]:
    command_runner = runner or default_verification_runner
    results: list[ValidationResult] = []
    for command in commands:
        code, output = command_runner(command)
        status: ValidationStatus = "passed" if code == 0 else "failed"
        results.append(ValidationResult(command=command, status=status, output=output))
        if stop_on_failure and status == "failed":
            break
    return results


def summarize_validation_results(results: Sequence[ValidationResult]) -> VerificationSummary:
    total = len(results)
    passed = sum(1 for item in results if item.status == "passed")
    failed = sum(1 for item in results if item.status == "failed")
    skipped = sum(1 for item in results if item.status == "skipped")
    if failed:
        overall: VerificationOverallStatus = "failed"
    elif passed:
        overall = "passed"
    else:
        overall = "skipped"
    return VerificationSummary(
        total=total,
        passed=passed,
        failed=failed,
        skipped=skipped,
        overall_status=overall,
    )


def verification_passed(results: Sequence[ValidationResult]) -> bool:
    return summarize_validation_results(results).overall_status == "passed"
