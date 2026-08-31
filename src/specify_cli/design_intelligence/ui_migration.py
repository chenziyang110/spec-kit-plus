"""Exact state, asset-variant, and native-effect requirements within UI continuity.

These are optional for static sources. Once discovered and bound, their complete
denominator travels with the existing source-continuity manifest and report.
Evidence authenticity remains owned by the caller's normal Lab evidence gate.
"""

from __future__ import annotations

from collections.abc import Callable
import math
from typing import Any


def _rows(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        return []
    return value


def _name(value: object) -> str:
    return value if isinstance(value, str) else ""


def _size(value: object) -> tuple[int | float, int | float] | None:
    if not isinstance(value, list) or len(value) != 2:
        return None
    if any(
        isinstance(item, bool)
        or not isinstance(item, (int, float))
        or item > 2147483647
        or item < 1
        or not math.isfinite(item)
        or int(item) != item
        for item in value
    ):
        return None
    return value[0], value[1]


def _scalar(value: object) -> tuple[str, object] | None:
    if value is None:
        return "null", None
    if isinstance(value, bool):
        return "boolean", value
    if isinstance(value, str):
        return "string", value
    if isinstance(value, (int, float)):
        try:
            number = float(value)
        except (OverflowError, ValueError):
            return None
        return ("number", number) if math.isfinite(number) else None
    return None


def _effect_satisfied(before: object, after: object, native: dict[str, Any]) -> bool:
    fields = native.get("effect_fields")
    mode = native.get("effect_requirement")
    if (
        not isinstance(before, dict)
        or not isinstance(after, dict)
        or not fields
        or not _exact(fields, fields)
        or mode not in {"state-change", "observation"}
    ):
        return False
    changed = False
    for field in fields:
        if field not in before or field not in after:
            return False
        left, right = _scalar(before[field]), _scalar(after[field])
        if left is None or right is None:
            return False
        changed = changed or left != right
    return changed or mode == "observation"


def _exact(values: object, expected: object) -> bool:
    return (
        isinstance(values, list)
        and isinstance(expected, list)
        and all(isinstance(item, str) and item.strip() for item in values + expected)
        and len(values) == len(set(values))
        and len(expected) == len(set(expected))
        and set(values) == set(expected)
    )


def _variant_denominator_errors(
    continuity: dict[str, Any], asset: dict[str, Any]
) -> list[str]:
    variants = asset.get("state_variants")
    if not isinstance(variants, dict):
        return []
    component_id = _name(asset.get("component_id"))
    sources = [_name(row.get("source_ref")) for row in _rows(variants.get("variants"))]
    inventory = asset.get("source_refs", [])
    errors = []
    if not sources or set(sources) != set(inventory):
        errors.append(f"asset-state-source-coverage-mismatch:{component_id}")
    for surface in _rows(continuity.get("surface_bindings")):
        for component in _rows(surface.get("component_states")):
            if component.get("component_id") == component_id and not _exact(
                variants.get("required_states"), component.get("required_states")
            ):
                errors.append(f"asset-state-component-coverage-mismatch:{component_id}")
    return errors


def migration_contract_errors(
    continuity: dict[str, Any],
    *,
    character_ref: Callable[[str], bool],
    placeholder_ref: Callable[[str], bool],
) -> list[tuple[str, str]]:
    """Supplement the JSON schema with exact coverage and preservation checks."""
    errors: list[tuple[str, str]] = []
    components = continuity.get("coverage", {}).get("component_ids", [])
    for index, surface in enumerate(_rows(continuity.get("surface_bindings"))):
        declarations = _rows(surface.get("component_states"))
        seen: set[str] = set()
        for offset, component in enumerate(declarations):
            path = f"$.surface_bindings[{index}].component_states[{offset}]"
            component_id = component.get("component_id")
            if component_id not in components or component_id in seen:
                errors.append(
                    (
                        path,
                        "component state binding must identify one covered component",
                    )
                )
            seen.add(component_id)
            states = _rows(component.get("states"))
            if not _exact(
                [row.get("state") for row in states], component.get("required_states")
            ):
                errors.append(
                    (path, "component states must exactly cover required_states")
                )
            for state in states:
                if not _exact(
                    [row.get("part") for row in _rows(state.get("visuals"))],
                    component.get("parts"),
                ):
                    errors.append(
                        (
                            path,
                            "each component state must preserve every visual part separately",
                        )
                    )
    for index, asset in enumerate(_rows(continuity.get("asset_bindings"))):
        variants = asset.get("state_variants")
        if not isinstance(variants, dict):
            continue
        path = f"$.asset_bindings[{index}].state_variants"
        errors.extend(
            (path, error) for error in _variant_denominator_errors(continuity, asset)
        )
        rows = _rows(variants.get("variants"))
        if not _exact(
            [row.get("state") for row in rows], variants.get("required_states")
        ):
            errors.append((path, "asset variants must exactly cover required_states"))
        for row in rows:
            if row.get("source_ref") not in asset.get("source_refs", []):
                errors.append(
                    (
                        path,
                        "asset variant source_ref must belong to the source inventory",
                    )
                )
            for field in ("source_ref", "target_ref"):
                value = row.get(field)
                if isinstance(value, str) and (
                    character_ref(value) or placeholder_ref(value)
                ):
                    errors.append(
                        (
                            path,
                            "state variants require real assets, never character or placeholder substitution",
                        )
                    )
            if asset.get("target_strategy") == "preserve" and row.get(
                "source_size"
            ) != row.get("target_size"):
                errors.append(
                    (path, "preserved asset variant dimensions must match the source")
                )
    for index, action in enumerate(_rows(continuity.get("action_bindings"))):
        native = action.get("native_operation")
        if (
            isinstance(native, dict)
            and native.get("effect_requirement") == "observation"
            and action.get("side_effects")
        ):
            errors.append(
                (
                    f"$.action_bindings[{index}].native_operation",
                    "observation mode cannot replace a native action with promised side effects",
                )
            )
        if isinstance(native, dict) and isinstance(
            native.get("permission_required"), bool
        ):
            refs = native.get("permission_refs")
            if isinstance(refs, list) and bool(refs) != native["permission_required"]:
                errors.append(
                    (
                        f"$.action_bindings[{index}].native_operation",
                        "native permission_refs must match permission_required",
                    )
                )
    return errors


def migration_component_binding_errors(
    continuity: dict[str, Any], components: list[dict[str, Any]]
) -> list[str]:
    """Keep the source-state denominator tied to the selected component contract."""
    by_id = {_name(row.get("id")): row for row in _rows(components)}
    errors: list[str] = []
    for surface in _rows(continuity.get("surface_bindings")):
        for component in _rows(surface.get("component_states")):
            target = by_id.get(component.get("component_id"), {})
            if not _exact(component.get("parts"), target.get("anatomy")):
                errors.append(
                    "source component state parts must exactly match component anatomy"
                )
            if not _exact(
                component.get("required_states"), target.get("required_states")
            ):
                errors.append(
                    "source component states must exactly match component required_states"
                )
    for asset in _rows(continuity.get("asset_bindings")):
        variants = asset.get("state_variants")
        if isinstance(variants, dict) and not _exact(
            variants.get("required_states"),
            by_id.get(_name(asset.get("component_id")), {}).get("required_states"),
        ):
            errors.append(
                "source asset states must exactly match component required_states"
            )
    return errors


def migration_adapter_targets(
    capabilities: set[str], continuity: dict[str, Any]
) -> dict[str, list[dict[str, Any]]]:
    """Compile bounded state targets for each capable adapter; omit static noise."""
    checks = []
    if "surface-enumeration" in capabilities:
        checks.append("inventory")
    if capabilities & {"action-execution", "side-effect-observation"}:
        checks.append("behavior")
    if capabilities & {"asset-inspection", "visual-capture"}:
        checks.append("visual")
    result = {}
    states = [
        {
            "surface_binding_id": surface["id"],
            "component_id": component["component_id"],
            "state": state,
            "parts": component["parts"],
            "checks": checks,
        }
        for surface in _rows(continuity.get("surface_bindings"))
        for component in _rows(surface.get("component_states"))
        for state in component.get("required_states", [])
    ]
    if states and checks:
        result["component_states"] = states
    if capabilities & {"asset-inspection", "visual-capture"}:
        variants = [
            {"asset_binding_id": asset["id"], "state": state}
            for asset in _rows(continuity.get("asset_bindings"))
            for state in asset.get("state_variants", {}).get("required_states", [])
        ]
        if variants:
            result["asset_variants"] = variants
    return result


def migration_observation_errors(
    continuity: dict[str, Any], report: dict[str, Any]
) -> list[str]:
    """Reject partial or contradictory detailed observations even with top-level PASS."""
    evidence = {
        _name(row.get("ref")): (row.get("side"), row.get("kind"))
        for row in _rows(report.get("evidence_refs"))
    }
    errors: list[str] = []

    def bound(ref: object, side: str, kind: str) -> bool:
        return isinstance(ref, str) and evidence.get(ref) == (side, kind)

    def fields(row: dict, expected: set[str]) -> bool:
        return set(row) == expected

    def observed(value: object) -> bool:
        return isinstance(value, str) and bool(value.strip())

    surface_results = {
        _name(row.get("surface_id")): row
        for row in _rows(report.get("surface_results"))
    }
    for surface in _rows(continuity.get("surface_bindings")):
        if "component_states" not in surface:
            continue
        surface_id = surface.get("surface_id", "")
        rows = _rows(surface_results.get(surface_id, {}).get("component_states"))
        expected = {
            (component["component_id"], state)
            for component in _rows(surface.get("component_states"))
            for state in component.get("required_states", [])
        }
        keys = [
            (_name(row.get("component_id")), _name(row.get("state"))) for row in rows
        ]
        if len(keys) != len(set(keys)) or set(keys) != expected:
            errors.append(f"component-state-coverage-mismatch:{surface_id}")
        declarations = {
            row["component_id"]: row for row in _rows(surface.get("component_states"))
        }
        for row in rows:
            key = f"{row.get('component_id')}:{row.get('state')}"
            if not fields(
                row,
                {
                    "component_id",
                    "state",
                    "behavior_matches",
                    "behavior_observation",
                    "behavior_evidence_ref",
                    "visuals",
                },
            ):
                errors.append(f"component-state-result-invalid:{key}")
            if row.get("behavior_matches") is not True or not observed(
                row.get("behavior_observation")
            ):
                errors.append(f"component-state-behavior-mismatch:{key}")
            if not bound(
                row.get("behavior_evidence_ref"), "target", "runtime_diagnostics"
            ):
                errors.append(f"component-state-evidence-kind-mismatch:{key}")
            visuals = _rows(row.get("visuals"))
            parts = declarations.get(_name(row.get("component_id")), {}).get(
                "parts", []
            )
            if not _exact([visual.get("part") for visual in visuals], parts):
                errors.append(f"component-state-visual-coverage-mismatch:{key}")
            for visual in visuals:
                if (
                    not fields(
                        visual,
                        {
                            "part",
                            "matches",
                            "observation",
                            "source_evidence_ref",
                            "target_evidence_ref",
                        },
                    )
                    or visual.get("matches") is not True
                    or not observed(visual.get("observation"))
                ):
                    errors.append(
                        f"component-state-visual-mismatch:{key}:{visual.get('part')}"
                    )
                if not bound(
                    visual.get("source_evidence_ref"), "source", "visual_capture"
                ) or not bound(
                    visual.get("target_evidence_ref"), "target", "visual_capture"
                ):
                    errors.append(f"component-state-evidence-kind-mismatch:{key}")

    asset_results = {
        _name(row.get("component_id")): row
        for row in _rows(report.get("asset_results"))
    }
    for asset in _rows(continuity.get("asset_bindings")):
        variants = asset.get("state_variants")
        if not isinstance(variants, dict):
            continue
        errors.extend(_variant_denominator_errors(continuity, asset))
        component_id = asset.get("component_id", "")
        rows = _rows(asset_results.get(component_id, {}).get("state_variants"))
        if not _exact(
            [row.get("state") for row in rows], variants.get("required_states")
        ):
            errors.append(f"asset-state-coverage-mismatch:{component_id}")
        expected = {row.get("state"): row for row in _rows(variants.get("variants"))}
        for row in rows:
            key = f"{component_id}:{row.get('state')}"
            target = expected.get(_name(row.get("state")), {})
            if not fields(
                row,
                {
                    "state",
                    "source_ref",
                    "target_ref",
                    "source_size",
                    "target_size",
                    "source_evidence_ref",
                    "target_evidence_ref",
                    "render_match",
                    "character_substitution",
                },
            ):
                errors.append(f"asset-state-result-invalid:{key}")
            if any(
                row.get(field) != target.get(field)
                for field in ("source_ref", "target_ref")
            ):
                errors.append(f"asset-state-reference-mismatch:{key}")
            if any(
                _size(row.get(field)) is None
                or _size(row.get(field)) != _size(target.get(field))
                for field in ("source_size", "target_size")
            ):
                errors.append(f"asset-state-size-mismatch:{key}")
            if row.get("character_substitution") is not False:
                errors.append(f"asset-state-character-substitution:{key}")
            if row.get("render_match") is not True:
                errors.append(f"asset-state-render-mismatch:{key}")
            if not bound(
                row.get("source_evidence_ref"), "source", "visual_capture"
            ) or not bound(row.get("target_evidence_ref"), "target", "visual_capture"):
                errors.append(f"asset-state-evidence-kind-mismatch:{key}")

    action_results = {
        _name(row.get("interaction_id")): row
        for row in _rows(report.get("action_results"))
    }
    for action in _rows(continuity.get("action_bindings")):
        native = action.get("native_operation")
        if not isinstance(native, dict):
            continue
        interaction_id = action.get("interaction_id", "")
        if native.get("effect_requirement") == "observation" and action.get(
            "side_effects"
        ):
            errors.append(f"native-operation-mode-mismatch:{interaction_id}")
        result = action_results.get(interaction_id, {}).get("native_operation")
        if not isinstance(result, dict):
            errors.append(f"native-operation-result-missing:{interaction_id}")
            continue
        if not fields(
            result,
            {
                "api_ref",
                "verified_permission_refs",
                "permission_evidence_ref",
                "effect_evidence_ref",
                "before",
                "after",
                "effect_matches",
            },
        ) or result.get("api_ref") != native.get("api_ref"):
            errors.append(f"native-operation-api-mismatch:{interaction_id}")
        if not _exact(
            result.get("verified_permission_refs"), native.get("permission_refs")
        ):
            errors.append(f"native-operation-permission-mismatch:{interaction_id}")
        if any(
            not bound(result.get(field), "target", "runtime_diagnostics")
            for field in ("permission_evidence_ref", "effect_evidence_ref")
        ):
            errors.append(f"native-operation-evidence-kind-mismatch:{interaction_id}")
        before, after = result.get("before"), result.get("after")
        if (
            not _effect_satisfied(before, after, native)
            or result.get("effect_matches") is not True
        ):
            errors.append(f"native-operation-effect-mismatch:{interaction_id}")
    return sorted(set(errors))
