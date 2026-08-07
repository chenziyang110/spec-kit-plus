"""Design Evidence v1 schema loader and semantic validator.

Formalizes measured / inferred / assumption claims so agents cannot label
unknown claims as evidence-backed without source or rationale.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

EVIDENCE_TYPE_MEASURED = "measured"
EVIDENCE_TYPE_INFERRED = "inferred"
EVIDENCE_TYPE_ASSUMPTION = "assumption"
# Prose alias retained for existing briefs/prompts.
EVIDENCE_TYPE_INFERENCE_ALIAS = "evidence-backed-inference"

CANONICAL_EVIDENCE_TYPES = frozenset(
    {
        EVIDENCE_TYPE_MEASURED,
        EVIDENCE_TYPE_INFERRED,
        EVIDENCE_TYPE_ASSUMPTION,
    }
)

_SCHEMA_RELATIVE = Path("design-intelligence") / "schema" / "design-evidence.schema.json"


def _schema_candidates() -> tuple[Path, ...]:
    here = Path(__file__).resolve()
    return (
        here.parents[3] / "templates" / _SCHEMA_RELATIVE,
        here.parents[1] / "core_pack" / "templates" / _SCHEMA_RELATIVE,
    )


def load_design_evidence_schema() -> dict[str, Any]:
    """Load the packaged Design Evidence v1 JSON Schema."""

    for candidate in _schema_candidates():
        if candidate.is_file():
            payload = json.loads(candidate.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise RuntimeError(
                    f"Design Evidence schema is not an object: {candidate}"
                )
            return payload
    raise RuntimeError(
        "packaged Design Evidence schema is missing "
        f"(looked in: {', '.join(str(path) for path in _schema_candidates())})"
    )


def normalize_evidence_type(raw: Any) -> str | None:
    """Map raw type labels onto the canonical evidence vocabulary."""

    if not isinstance(raw, str):
        return None
    value = raw.strip().lower().replace("_", "-")
    if value in {EVIDENCE_TYPE_MEASURED, "measure"}:
        return EVIDENCE_TYPE_MEASURED
    if value in {
        EVIDENCE_TYPE_INFERRED,
        EVIDENCE_TYPE_INFERENCE_ALIAS,
        "inference",
        "evidence-backed",
    }:
        return EVIDENCE_TYPE_INFERRED
    if value in {EVIDENCE_TYPE_ASSUMPTION, "assumed", "guess"}:
        return EVIDENCE_TYPE_ASSUMPTION
    return None


def _has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


@dataclass(frozen=True, slots=True)
class DesignEvidenceValidationError:
    """One structural or semantic evidence violation."""

    message: str
    path: str


@dataclass(frozen=True, slots=True)
class DesignEvidenceValidationResult:
    """Result of validating one or more Evidence objects."""

    valid: bool
    errors: tuple[DesignEvidenceValidationError, ...]
    normalized_type: str | None = None

    @property
    def ok(self) -> bool:
        return self.valid


def _schema_errors(payload: Any) -> list[DesignEvidenceValidationError]:
    schema = load_design_evidence_schema()
    validator = Draft202012Validator(schema)
    schema_errors = sorted(
        validator.iter_errors(payload),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    errors: list[DesignEvidenceValidationError] = []
    for error in schema_errors:
        path = "$" + "".join(
            f"[{part}]" if isinstance(part, int) else f".{part}"
            for part in error.absolute_path
        )
        errors.append(DesignEvidenceValidationError(error.message, path))
    return errors


def _semantic_errors(
    payload: dict[str, Any],
    *,
    path_prefix: str = "$",
) -> tuple[list[DesignEvidenceValidationError], str | None]:
    errors: list[DesignEvidenceValidationError] = []
    canonical = normalize_evidence_type(payload.get("type"))
    if payload.get("type") is not None and canonical is None:
        errors.append(
            DesignEvidenceValidationError(
                "type must be measured, inferred, or assumption "
                "(evidence-backed-inference is accepted as inferred)",
                f"{path_prefix}.type",
            )
        )
        return errors, None

    if canonical is None:
        return errors, None

    if canonical != EVIDENCE_TYPE_MEASURED and not _has_text(payload.get("rationale")):
        errors.append(
            DesignEvidenceValidationError(
                "non-measured evidence requires a non-empty rationale",
                f"{path_prefix}.rationale",
            )
        )

    if canonical == EVIDENCE_TYPE_INFERRED:
        has_source = _has_text(payload.get("source"))
        has_gap = _has_text(payload.get("source_gap"))
        if not has_source and not has_gap:
            errors.append(
                DesignEvidenceValidationError(
                    "inferred evidence requires source or explicit source_gap",
                    f"{path_prefix}.source",
                )
            )

    return errors, canonical


def validate_design_evidence(payload: Any) -> DesignEvidenceValidationResult:
    """Validate a single Design Evidence object (schema + semantic rules)."""

    if not isinstance(payload, dict):
        return DesignEvidenceValidationResult(
            valid=False,
            errors=(
                DesignEvidenceValidationError(
                    "Design Evidence payload must be a JSON object",
                    "$",
                ),
            ),
        )

    errors = _schema_errors(payload)
    semantic, normalized = _semantic_errors(payload)
    # Avoid duplicate type enum noise when semantic already explains aliases.
    if normalized is not None:
        errors = [err for err in errors if err.path != "$.type"]
    errors.extend(semantic)
    return DesignEvidenceValidationResult(
        valid=not errors,
        errors=tuple(errors),
        normalized_type=normalized,
    )


def validate_design_evidence_list(
    payloads: Any,
) -> DesignEvidenceValidationResult:
    """Validate a list of Evidence objects; index paths as ``$[i]``."""

    if not isinstance(payloads, list):
        return DesignEvidenceValidationResult(
            valid=False,
            errors=(
                DesignEvidenceValidationError(
                    "Design Evidence list must be a JSON array",
                    "$",
                ),
            ),
        )

    errors: list[DesignEvidenceValidationError] = []
    for index, item in enumerate(payloads):
        result = validate_design_evidence(item)
        if result.valid:
            continue
        prefix = f"$[{index}]"
        for error in result.errors:
            path = error.path
            if path == "$":
                remapped = prefix
            elif path.startswith("$."):
                remapped = prefix + path[1:]
            elif path.startswith("$["):
                remapped = prefix + path[1:]
            else:
                remapped = f"{prefix}.{path}"
            errors.append(DesignEvidenceValidationError(error.message, remapped))

    return DesignEvidenceValidationResult(
        valid=not errors,
        errors=tuple(errors),
    )
