"""UI source-continuity schema loader and semantic validator.

The contract keeps reconstructed and adapted interfaces connected to the
sources that establish their visible surfaces, business actions, and assets.
Schema validation covers the row shapes; semantic validation covers lifecycle
state, ready-to-consume completeness, globally unique row IDs, and placeholder
or character-based asset substitutions.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import unicodedata
from typing import Any

from jsonschema import Draft202012Validator

from .ui_migration import migration_contract_errors

UI_SOURCE_CONTINUITY_SCHEMA = "spec-kit-ui-source-continuity-v1"

APPLICABILITY_NOT_ASSESSED = "not-assessed"
APPLICABILITY_NOT_APPLICABLE = "not-applicable"
APPLICABILITY_REQUIRED = "required"

MODE_NONE = "none"
READY_MODES = frozenset(
    {
        "reference-grounded",
        "live-product",
        "implementation-backed",
        "mixed",
    }
)

PLACEHOLDER_POLICY_FORBID = "forbid-character-substitution"
PLACEHOLDER_POLICY_APPROVED_TEXT = "approved-text-symbol"
TARGET_STRATEGY_APPROVED_EXCEPTION = "approved-exception"

_BINDING_FIELDS = ("surface_bindings", "action_bindings", "asset_bindings")
_NON_APPLICABLE_EMPTY_FIELDS = (
    "authority_refs",
    *_BINDING_FIELDS,
    "unresolved_gaps",
)
_COVERAGE_FIELDS = ("surface_ids", "interaction_ids", "component_ids")
_SCHEMA_RELATIVE = (
    Path("design-intelligence") / "schema" / "ui-source-continuity.schema.json"
)

_CHARACTER_REF_PREFIX = re.compile(
    r"^(?:char(?:acter)?|emoji|glyph|symbol|text|unicode)\s*:",
    re.IGNORECASE,
)
_HTML_CHARACTER_REF = re.compile(r"^&#(?:x[0-9a-f]+|[0-9]+);?$", re.IGNORECASE)
_UNICODE_CHARACTER_REF = re.compile(
    r"^(?:u\+|\\u)[0-9a-f]{4,8}$",
    re.IGNORECASE,
)
_TEMPLATE_PLACEHOLDER_REF = re.compile(
    r"(?:\{\{[^{}]+\}\}|\$\{[^{}]+\}|<[^<>]+>)"
)
_PLACEHOLDER_TOKENS = frozenset(
    {
        "dummy",
        "example",
        "fake",
        "mock",
        "pending",
        "placeholder",
        "replace",
        "sample",
        "tbd",
        "temp",
        "temporary",
        "todo",
        "unresolved",
    }
)


def _schema_candidates() -> tuple[Path, ...]:
    here = Path(__file__).resolve()
    return (
        here.parents[3] / "templates" / _SCHEMA_RELATIVE,
        here.parents[1] / "core_pack" / "templates" / _SCHEMA_RELATIVE,
    )


def load_ui_source_continuity_schema() -> dict[str, Any]:
    """Load the packaged UI source-continuity v1 JSON Schema."""

    for candidate in _schema_candidates():
        if candidate.is_file():
            payload = json.loads(candidate.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                raise RuntimeError(
                    f"UI source-continuity schema is not an object: {candidate}"
                )
            return payload
    raise RuntimeError(
        "packaged UI source-continuity schema is missing "
        f"(looked in: {', '.join(str(path) for path in _schema_candidates())})"
    )


@dataclass(frozen=True, slots=True)
class UiSourceContinuityValidationError:
    """One structural or semantic source-continuity violation."""

    message: str
    path: str


@dataclass(frozen=True, slots=True)
class UiSourceContinuityValidationResult:
    """Result of validating one UI source-continuity contract."""

    valid: bool
    errors: tuple[UiSourceContinuityValidationError, ...]

    @property
    def ok(self) -> bool:
        return self.valid


def _json_path(parts: Any) -> str:
    return "$" + "".join(
        f"[{part}]" if isinstance(part, int) else f".{part}" for part in parts
    )


def _schema_errors(payload: Any) -> list[UiSourceContinuityValidationError]:
    schema = load_ui_source_continuity_schema()
    validator = Draft202012Validator(schema)
    violations = sorted(
        validator.iter_errors(payload),
        key=lambda item: tuple(str(part) for part in item.absolute_path),
    )
    return [
        UiSourceContinuityValidationError(
            message=violation.message,
            path=_json_path(violation.absolute_path),
        )
        for violation in violations
    ]


def _has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _nonempty_list(value: Any) -> bool:
    return isinstance(value, list) and bool(value)


def _is_placeholder_ref(value: str) -> bool:
    normalized = value.strip().casefold()
    if normalized in {"?", "n/a", "none", "null", "unknown"}:
        return True
    if _TEMPLATE_PLACEHOLDER_REF.search(normalized):
        return True
    tokens = {token for token in re.split(r"[^a-z0-9]+", normalized) if token}
    if tokens & _PLACEHOLDER_TOKENS:
        return True
    return "replace-me" in normalized or "replace_me" in normalized


def _is_character_ref(value: str) -> bool:
    normalized = value.strip()
    if _CHARACTER_REF_PREFIX.match(normalized):
        return True
    if _HTML_CHARACTER_REF.fullmatch(normalized):
        return True
    if _UNICODE_CHARACTER_REF.fullmatch(normalized):
        return True
    contains_path_marker = any(character in "/\\." for character in normalized)
    if len(normalized) <= 4 and not contains_path_marker:
        return any(
            unicodedata.category(character).startswith(("S", "P"))
            for character in normalized
            if not character.isspace()
        )
    return False


def _append_lifecycle_errors(
    payload: dict[str, Any],
    errors: list[UiSourceContinuityValidationError],
    *,
    require_ready: bool,
) -> None:
    applicability = payload.get("applicability")
    mode = payload.get("mode")

    if applicability == APPLICABILITY_NOT_ASSESSED:
        if mode != MODE_NONE:
            errors.append(
                UiSourceContinuityValidationError(
                    "not-assessed source continuity must use mode 'none'",
                    "$.mode",
                )
            )
        for field in _NON_APPLICABLE_EMPTY_FIELDS:
            if _nonempty_list(payload.get(field)):
                errors.append(
                    UiSourceContinuityValidationError(
                        f"not-assessed source continuity must keep {field} empty",
                        f"$.{field}",
                    )
                )
        _append_empty_coverage_errors(payload, errors, applicability)
        if require_ready:
            errors.append(
                UiSourceContinuityValidationError(
                    "source continuity applicability must be assessed before ready",
                    "$.applicability",
                )
            )
        return

    if applicability == APPLICABILITY_NOT_APPLICABLE:
        if mode != MODE_NONE:
            errors.append(
                UiSourceContinuityValidationError(
                    "not-applicable source continuity must use mode 'none'",
                    "$.mode",
                )
            )
        if not _has_text(payload.get("reason")):
            errors.append(
                UiSourceContinuityValidationError(
                    "not-applicable source continuity requires a non-empty reason",
                    "$.reason",
                )
            )
        for field in _NON_APPLICABLE_EMPTY_FIELDS:
            if _nonempty_list(payload.get(field)):
                errors.append(
                    UiSourceContinuityValidationError(
                        f"not-applicable source continuity must keep {field} empty",
                        f"$.{field}",
                    )
                )
        _append_empty_coverage_errors(payload, errors, applicability)
        return

    if applicability != APPLICABILITY_REQUIRED:
        return

    if mode not in READY_MODES:
        errors.append(
            UiSourceContinuityValidationError(
                "required source continuity must select a source-backed mode",
                "$.mode",
            )
        )

    if not require_ready:
        return

    if not _has_text(payload.get("reason")):
        errors.append(
            UiSourceContinuityValidationError(
                "required source continuity requires a non-empty reason",
                "$.reason",
            )
        )
    if not _nonempty_list(payload.get("authority_refs")):
        errors.append(
            UiSourceContinuityValidationError(
                "required source continuity needs at least one authority reference",
                "$.authority_refs",
            )
        )
    for field, label in (
        ("surface_bindings", "surface"),
        ("action_bindings", "action"),
        ("asset_bindings", "asset"),
    ):
        if not _nonempty_list(payload.get(field)):
            errors.append(
                UiSourceContinuityValidationError(
                    f"required source continuity needs at least one {label} binding",
                    f"$.{field}",
                )
            )


def _append_empty_coverage_errors(
    payload: dict[str, Any],
    errors: list[UiSourceContinuityValidationError],
    applicability: str,
) -> None:
    coverage = payload.get("coverage")
    if not isinstance(coverage, dict):
        return
    for field in _COVERAGE_FIELDS:
        if _nonempty_list(coverage.get(field)):
            errors.append(
                UiSourceContinuityValidationError(
                    f"{applicability} source continuity must keep coverage.{field} empty",
                    f"$.coverage.{field}",
                )
            )


def _append_coverage_errors(
    payload: dict[str, Any],
    errors: list[UiSourceContinuityValidationError],
    *,
    require_ready: bool,
) -> None:
    if not require_ready or payload.get("applicability") != APPLICABILITY_REQUIRED:
        return
    coverage = payload.get("coverage")
    if not isinstance(coverage, dict):
        return
    expected = {
        "surface_ids": {
            str(row.get("surface_id") or "").strip()
            for row in payload.get("surface_bindings") or []
            if isinstance(row, dict) and str(row.get("surface_id") or "").strip()
        },
        "interaction_ids": {
            str(row.get("interaction_id") or "").strip()
            for row in payload.get("action_bindings") or []
            if isinstance(row, dict) and str(row.get("interaction_id") or "").strip()
        },
        "component_ids": {
            str(row.get("component_id") or "").strip()
            for row in payload.get("asset_bindings") or []
            if isinstance(row, dict) and str(row.get("component_id") or "").strip()
        },
    }
    for field in _COVERAGE_FIELDS:
        declared = {
            str(value).strip()
            for value in coverage.get(field) or []
            if isinstance(value, str) and value.strip()
        }
        if not declared:
            errors.append(
                UiSourceContinuityValidationError(
                    f"ready source continuity coverage.{field} must be non-empty",
                    f"$.coverage.{field}",
                )
            )
            continue
        if declared != expected[field]:
            missing = sorted(declared - expected[field])
            unknown = sorted(expected[field] - declared)
            detail = []
            if missing:
                detail.append("unbound declared IDs: " + ", ".join(missing))
            if unknown:
                detail.append("bindings outside coverage: " + ", ".join(unknown))
            errors.append(
                UiSourceContinuityValidationError(
                    f"coverage {field} must exactly match its binding targets; "
                    + "; ".join(detail),
                    f"$.coverage.{field}",
                )
            )


def _append_duplicate_id_errors(
    payload: dict[str, Any],
    errors: list[UiSourceContinuityValidationError],
) -> None:
    seen: dict[str, str] = {}
    for field in _BINDING_FIELDS:
        rows = payload.get(field)
        if not isinstance(rows, list):
            continue
        for index, row in enumerate(rows):
            if not isinstance(row, dict) or not _has_text(row.get("id")):
                continue
            identifier = row["id"].strip()
            path = f"$.{field}[{index}].id"
            first_path = seen.get(identifier)
            if first_path is None:
                seen[identifier] = path
                continue
            errors.append(
                UiSourceContinuityValidationError(
                    f"binding id {identifier!r} duplicates {first_path}; IDs must be "
                    "unique across surface, action, and asset bindings",
                    path,
                )
            )


def _append_ready_asset_errors(
    payload: dict[str, Any],
    errors: list[UiSourceContinuityValidationError],
    *,
    require_ready: bool,
) -> None:
    rows = payload.get("asset_bindings")
    if not isinstance(rows, list):
        return

    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        path = f"$.asset_bindings[{index}]"
        policy = row.get("placeholder_policy")
        strategy = row.get("target_strategy")
        target_ref = row.get("target_ref")
        approved_text_symbol = (
            policy == PLACEHOLDER_POLICY_APPROVED_TEXT
            and strategy == TARGET_STRATEGY_APPROVED_EXCEPTION
        )

        if policy == PLACEHOLDER_POLICY_APPROVED_TEXT and not approved_text_symbol:
            errors.append(
                UiSourceContinuityValidationError(
                    "approved-text-symbol requires target_strategy "
                    "'approved-exception'",
                    f"{path}.target_strategy",
                )
            )
        if (
            strategy == TARGET_STRATEGY_APPROVED_EXCEPTION
            and policy != PLACEHOLDER_POLICY_APPROVED_TEXT
        ):
            errors.append(
                UiSourceContinuityValidationError(
                    "approved-exception requires placeholder_policy "
                    "'approved-text-symbol'",
                    f"{path}.placeholder_policy",
                )
            )

        if not require_ready or not _has_text(target_ref):
            continue

        placeholder = _is_placeholder_ref(target_ref)
        character_ref = _is_character_ref(target_ref)
        if placeholder:
            errors.append(
                UiSourceContinuityValidationError(
                    "ready asset target_ref cannot be a placeholder or temporary "
                    "reference",
                    f"{path}.target_ref",
                )
            )
        if approved_text_symbol:
            if not character_ref:
                errors.append(
                    UiSourceContinuityValidationError(
                        "approved-text-symbol must identify an intentional character "
                        "or text symbol target_ref",
                        f"{path}.target_ref",
                    )
                )
        elif character_ref:
            errors.append(
                UiSourceContinuityValidationError(
                    "ready asset target_ref cannot use character, emoji, glyph, or "
                    "text substitution",
                    f"{path}.target_ref",
                )
            )


def validate_ui_source_continuity(
    payload: Any,
    *,
    require_ready: bool = False,
) -> UiSourceContinuityValidationResult:
    """Validate a UI source-continuity contract.

    ``require_ready=False`` accepts the explicit ``not-assessed`` draft state
    and incomplete rows still being gathered. Ready validation requires either
    a well-formed ``not-applicable`` declaration or complete source, surface,
    action, and asset coverage with no unresolved gaps.
    """

    if not isinstance(payload, dict):
        return UiSourceContinuityValidationResult(
            valid=False,
            errors=(
                UiSourceContinuityValidationError(
                    "UI source-continuity payload must be a JSON object",
                    "$",
                ),
            ),
        )

    errors = _schema_errors(payload)
    _append_lifecycle_errors(payload, errors, require_ready=require_ready)
    _append_duplicate_id_errors(payload, errors)
    _append_coverage_errors(payload, errors, require_ready=require_ready)
    _append_ready_asset_errors(payload, errors, require_ready=require_ready)
    if not errors:
        errors.extend(
            UiSourceContinuityValidationError(message, path)
            for path, message in migration_contract_errors(
                payload,
                character_ref=_is_character_ref,
                placeholder_ref=_is_placeholder_ref,
            )
        )

    gaps = payload.get("unresolved_gaps")
    if require_ready and _nonempty_list(gaps):
        errors.append(
            UiSourceContinuityValidationError(
                "ready source continuity cannot contain unresolved gaps",
                "$.unresolved_gaps",
            )
        )

    return UiSourceContinuityValidationResult(
        valid=not errors,
        errors=tuple(errors),
    )
