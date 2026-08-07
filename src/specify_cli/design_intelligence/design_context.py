"""DesignContext v1 schema loader and structural validator.

Validates required fields and version only. When an ``evidence`` array is
present, also applies Design Evidence semantic rules. Does not score taste,
reverse-engineer screenshots, or enforce design approve authority.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .evidence import validate_design_evidence_list

DESIGN_CONTEXT_VERSION = "1.0"
_SCHEMA_RELATIVE = Path("design-intelligence") / "schema" / "design-context.schema.json"


def _schema_candidates() -> tuple[Path, ...]:
    here = Path(__file__).resolve()
    return (
        here.parents[3] / "templates" / _SCHEMA_RELATIVE,
        here.parents[1] / "core_pack" / "templates" / _SCHEMA_RELATIVE,
    )


def load_design_context_schema() -> dict[str, Any]:
    """Load the packaged DesignContext v1 JSON Schema."""

    for candidate in _schema_candidates():
        if candidate.is_file():
            payload = json.loads(candidate.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise RuntimeError(
                    f"DesignContext schema is not an object: {candidate}"
                )
            return payload
    raise RuntimeError(
        "packaged DesignContext schema is missing "
        f"(looked in: {', '.join(str(path) for path in _schema_candidates())})"
    )


@dataclass(frozen=True, slots=True)
class DesignContextValidationError:
    """One structural schema violation."""

    message: str
    path: str


@dataclass(frozen=True, slots=True)
class DesignContextValidationResult:
    """Result of validating a DesignContext payload."""

    valid: bool
    errors: tuple[DesignContextValidationError, ...]

    @property
    def ok(self) -> bool:
        return self.valid


def validate_design_context(payload: Any) -> DesignContextValidationResult:
    """Validate *payload* against DesignContext v1.

    Rules:
    - payload must be a mapping
    - JSON Schema validity (required: version, intent.user_goal)
    - version must equal ``1.0``
    """

    if not isinstance(payload, dict):
        return DesignContextValidationResult(
            valid=False,
            errors=(
                DesignContextValidationError(
                    "DesignContext payload must be a JSON object",
                    "$",
                ),
            ),
        )

    schema = load_design_context_schema()
    validator = Draft202012Validator(schema)
    schema_errors = sorted(
        validator.iter_errors(payload),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    errors: list[DesignContextValidationError] = []
    for error in schema_errors:
        path = "$" + "".join(
            f"[{part}]" if isinstance(part, int) else f".{part}"
            for part in error.absolute_path
        )
        errors.append(DesignContextValidationError(error.message, path))

    version = payload.get("version")
    if version is not None and version != DESIGN_CONTEXT_VERSION and not any(
        err.path == "$.version" for err in errors
    ):
        errors.append(
            DesignContextValidationError(
                f"version must equal {DESIGN_CONTEXT_VERSION!r}",
                "$.version",
            )
        )

    evidence = payload.get("evidence")
    if evidence is not None:
        evidence_result = validate_design_evidence_list(evidence)
        for error in evidence_result.errors:
            path = error.path
            if path == "$":
                remapped = "$.evidence"
            elif path.startswith("$["):
                remapped = "$.evidence" + path[1:]
            elif path.startswith("$."):
                remapped = "$.evidence" + path[1:]
            else:
                remapped = f"$.evidence.{path}"
            errors.append(DesignContextValidationError(error.message, remapped))

    return DesignContextValidationResult(
        valid=not errors,
        errors=tuple(errors),
    )
