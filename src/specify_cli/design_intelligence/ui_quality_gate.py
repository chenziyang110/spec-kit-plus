"""Executable UI quality gate helpers (structured rules only).

Prompt-based UI quality gate remains the default until this engine expands.
Does not score taste, parse screenshots, or replace design approve.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .evidence import validate_design_evidence_list

GATE_REPORT_VERSION = "1.0"
_SCHEMA_RELATIVE = (
    Path("design-intelligence") / "schema" / "ui-quality-gate-report.schema.json"
)


def _schema_candidates() -> tuple[Path, ...]:
    here = Path(__file__).resolve()
    return (
        here.parents[3] / "templates" / _SCHEMA_RELATIVE,
        here.parents[1] / "core_pack" / "templates" / _SCHEMA_RELATIVE,
    )


def load_ui_quality_gate_report_schema() -> dict[str, Any]:
    """Load the packaged UI quality gate report schema."""

    for candidate in _schema_candidates():
        if candidate.is_file():
            payload = json.loads(candidate.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise RuntimeError(
                    f"UI quality gate report schema is not an object: {candidate}"
                )
            return payload
    raise RuntimeError(
        "packaged UI quality gate report schema is missing "
        f"(looked in: {', '.join(str(path) for path in _schema_candidates())})"
    )


@dataclass(frozen=True, slots=True)
class UiQualityGateIssue:
    """One structured gate finding."""

    id: str
    category: str
    severity: str
    message: str
    path: str | None = None
    rule_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category,
            "severity": self.severity,
            "message": self.message,
            "path": self.path,
            "rule_id": self.rule_id,
        }


@dataclass(frozen=True, slots=True)
class UiQualityGateReport:
    """Machine-readable gate result."""

    status: str
    issues: tuple[UiQualityGateIssue, ...]
    scope: str | None = None
    version: str = GATE_REPORT_VERSION

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "status": self.status,
            "scope": self.scope,
            "checked_at": None,
            "issues": [issue.as_dict() for issue in self.issues],
        }


@dataclass(frozen=True, slots=True)
class UiQualityGateReportValidationResult:
    valid: bool
    errors: tuple[str, ...]

    @property
    def ok(self) -> bool:
        return self.valid


def validate_ui_quality_gate_report(
    payload: Any,
) -> UiQualityGateReportValidationResult:
    """Structural validation for a gate report object."""

    if not isinstance(payload, dict):
        return UiQualityGateReportValidationResult(
            valid=False,
            errors=("UI quality gate report must be a JSON object",),
        )
    schema = load_ui_quality_gate_report_schema()
    validator = Draft202012Validator(schema)
    errors = sorted(
        (error.message for error in validator.iter_errors(payload)),
        key=str,
    )
    return UiQualityGateReportValidationResult(
        valid=not errors,
        errors=tuple(errors),
    )


def run_ui_quality_gate_rules(
    *,
    evidence: list[dict[str, Any]] | None = None,
    required_states: list[str] | None = None,
    observed_states: list[str] | None = None,
    scope: str | None = None,
) -> UiQualityGateReport:
    """Run the initial deterministic rule pack on structured inputs.

    Current rules:
    - evidence semantic validity (missing rationale / inferred without source)
    - required state coverage when both required and observed lists are provided

    Future rules (typography, spacing, responsive, a11y, motion) may append
    issues without changing the report envelope.
    """

    issues: list[UiQualityGateIssue] = []
    counter = 0

    def _add(
        category: str,
        severity: str,
        message: str,
        *,
        path: str | None = None,
        rule_id: str | None = None,
    ) -> None:
        nonlocal counter
        counter += 1
        issues.append(
            UiQualityGateIssue(
                id=f"UQ-{counter:03d}",
                category=category,
                severity=severity,
                message=message,
                path=path,
                rule_id=rule_id,
            )
        )

    if evidence is not None:
        result = validate_design_evidence_list(evidence)
        for error in result.errors:
            _add(
                "evidence",
                "error",
                error.message,
                path=error.path,
                rule_id="evidence.semantic",
            )

    if required_states is not None and observed_states is not None:
        required = {item.strip() for item in required_states if isinstance(item, str)}
        observed = {item.strip() for item in observed_states if isinstance(item, str)}
        missing = sorted(state for state in required if state and state not in observed)
        for state in missing:
            _add(
                "consistency",
                "error",
                f"required UI state not observed: {state}",
                path="$.states",
                rule_id="states.required_coverage",
            )

    status = "pass" if not any(issue.severity == "error" for issue in issues) else "fail"
    if not issues and evidence is None and required_states is None:
        status = "not-run"

    return UiQualityGateReport(
        status=status,
        issues=tuple(issues),
        scope=scope,
    )
