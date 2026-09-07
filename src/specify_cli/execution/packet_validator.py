"""Validation helpers for worker task packets."""

from __future__ import annotations

import re
from dataclasses import dataclass

from specify_cli.design_intelligence import validate_ui_source_continuity
from specify_cli.design_intelligence.ui_migration import migration_component_binding_errors

from .packet_schema import UI_CONTRACT_FIELDS, UIContract, WorkerTaskPacket


MP_ID_RE = re.compile(r"^MP-\d{3}$")
DESIGN_DECISION_ID_RE = re.compile(r"^DS-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
DESIGN_HANDOFF_ID_RE = re.compile(r"^DH-[A-Z0-9]+(?:-[A-Z0-9]+)+$")
DESIGN_CHANGE_ID_RE = re.compile(r"^UD-\d{4}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
APPROVED_PREVIEW_REF_RE = re.compile(
    r"round-\d+\.(?:html|png|jpe?g|webp)#direction-[a-z0-9-]+$", re.IGNORECASE
)
CHANGE_LOCAL_PREVIEW_PREFIX_RE = re.compile(
    r"^\.specify/design/changes/UD-\d{4}/previews/"
)
CHANGE_LOCAL_PREVIEW_SUFFIX_RE = re.compile(
    r"^(?P<stem>round-\d+)\.(?:html|png|jpe?g|webp)#direction-[a-z0-9][a-z0-9-]*$"
)
UI_WORK_TYPES = {"existing-pattern", "feature-extension", "reference-implementation"}
UI_SURFACE_TYPES = {
    "landing",
    "product-workspace",
    "hybrid",
    "existing-pattern-maintenance",
}
UI_PLATFORMS = {"web", "mobile", "desktop", "tui", "cli"}
UI_REFERENCE_INTENTS = {
    "exact",
    "preserve-structure",
    "inspiration",
    "extract-tokens",
    "do-not-copy",
}
UI_REQUIRED_EVIDENCE = {
    "structure_snapshot",
    "visual_capture",
    "runtime_diagnostics",
    "visual_comparison_or_human_review",
}
OBSOLETE_UI_EVIDENCE_LABELS = {
    "real_entrypoint_ui_evidence",
    "reference_source_evidence",
    "ui_fidelity_criteria",
    "deviation_log",
    "visual_comparison_evidence",
}
SURFACE_LIMIT_ANTI_GOAL_RE = re.compile(
    r"\b(do not|don't|must not)\b.*\b(add|introduce|modify|change|expand)\b.*\b(public\s+)?(command|commands|api|apis|route|routes|surface|surfaces|lifecycle)\b",
    re.IGNORECASE,
)
WRITE_SCOPE_PATTERN_CHARS_RE = re.compile(r"[\?\[\]]")
WINDOWS_ABSOLUTE_SCOPE_RE = re.compile(r"^[A-Za-z]:")


@dataclass(slots=True)
class PacketValidationError(ValueError):
    code: str
    message: str

    def __post_init__(self) -> None:
        ValueError.__init__(self, self.message)


def _has_blank_entry(values: list[str]) -> bool:
    return any(not item.strip() for item in values)


def _valid_write_scope_entry(value: str) -> bool:
    normalized = value.strip().replace("\\", "/").strip("`'\"")
    if not normalized or WRITE_SCOPE_PATTERN_CHARS_RE.search(normalized):
        return False
    path_without_subtree = normalized.removesuffix("/**")
    if (
        normalized.startswith("/")
        or WINDOWS_ABSOLUTE_SCOPE_RE.match(normalized)
        or any(part == ".." for part in path_without_subtree.split("/"))
        or path_without_subtree in {"", "."}
    ):
        return False
    if "*" not in normalized:
        return True
    return (
        normalized.endswith("/**")
        and normalized.count("*") == 2
        and "*" not in normalized.removesuffix("/**")
    )


def _valid_comparison_tolerance(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    if any(
        value.get(field) != "exact"
        for field in ("structure", "content", "tokens", "text_wrap")
    ):
        return False
    if value.get("platform_variance") != "approved-deviation-only":
        return False

    geometry = value.get("geometry")
    color = value.get("color")
    motion = value.get("motion")
    if not all(isinstance(item, dict) for item in (geometry, color, motion)):
        return False
    assert isinstance(geometry, dict)
    assert isinstance(color, dict)
    assert isinstance(motion, dict)
    if geometry.get("unit") not in {"px", "cell", "point"}:
        return False
    if color.get("method") != "delta-e-2000" or motion.get("unit") != "ms":
        return False
    for item in (geometry, color, motion):
        maximum = item.get("max_delta")
        if isinstance(maximum, bool) or not isinstance(maximum, (int, float)):
            return False
        if maximum < 0:
            return False
    return set(value) == {
        "structure",
        "content",
        "tokens",
        "geometry",
        "color",
        "text_wrap",
        "motion",
        "platform_variance",
    }


def _nonblank_string_list(value: object) -> bool:
    return (
        isinstance(value, list)
        and bool(value)
        and all(isinstance(item, str) and item.strip() for item in value)
    )


def _valid_contract_row_refs(
    item: object,
    design_decision_ids: set[str],
    handoff_contract_ids: set[str],
) -> bool:
    if not isinstance(item, dict):
        return False
    row_id = str(item.get("id") or "").strip()
    decision_ids = item.get("decision_ids")
    if not row_id or not _nonblank_string_list(decision_ids):
        return False
    assert isinstance(decision_ids, list)
    if any(decision_id not in design_decision_ids for decision_id in decision_ids):
        return False
    if handoff_contract_ids:
        return row_id in handoff_contract_ids
    return not DESIGN_HANDOFF_ID_RE.fullmatch(row_id)


def _valid_surface_contract(
    item: object,
    design_decision_ids: set[str],
    handoff_contract_ids: set[str],
    component_ids: set[str],
) -> bool:
    return (
        isinstance(item, dict)
        and _valid_contract_row_refs(
            item, design_decision_ids, handoff_contract_ids
        )
        and bool(str(item.get("profile_id") or "").strip())
        and bool(str(item.get("name") or "").strip())
        and bool(str(item.get("kind") or "").strip())
        and bool(str(item.get("entrypoint_id") or "").strip())
        and _nonblank_string_list(item.get("source_refs"))
        and _nonblank_string_list(item.get("specimen_ids"))
        and _nonblank_string_list(item.get("component_ids"))
        and set(item.get("component_ids") or []) <= component_ids
    )


def _valid_interaction_script(
    value: object,
    data_state_ids: set[str],
) -> bool:
    required_fields = {
        "preconditions",
        "start_state_id",
        "steps",
        "branches",
        "focus_checkpoint",
        "announcement_checkpoint",
        "completion_checkpoint",
        "recovery_checkpoint",
    }
    if not isinstance(value, dict) or set(value) != required_fields:
        return False
    steps = value.get("steps")
    branches = value.get("branches")
    allowed_conditions = {
        "success",
        "failure",
        "timeout",
        "cancel",
        "retry",
        "duplicate",
        "out_of_order",
    }
    seen_conditions: set[str] = set()
    valid_branches = isinstance(branches, list) and bool(branches)
    for branch in branches if isinstance(branches, list) else []:
        if (
            not isinstance(branch, dict)
            or set(branch)
            != {
                "conditions",
                "setup",
                "expected_state_id",
                "expected_feedback",
                "focus_behavior",
                "announcement",
                "continuation",
            }
            or not _nonblank_string_list(branch.get("conditions"))
        ):
            valid_branches = False
            continue
        conditions = set(branch.get("conditions") or [])
        if (
            not conditions <= allowed_conditions
            or conditions & seen_conditions
            or str(branch.get("expected_state_id") or "").strip()
            not in data_state_ids
            or any(
                not str(branch.get(field) or "").strip()
                for field in (
                    "setup",
                    "expected_feedback",
                    "focus_behavior",
                    "announcement",
                    "continuation",
                )
            )
        ):
            valid_branches = False
        seen_conditions.update(conditions)
    valid_branches = (
        valid_branches
        and "success" in seen_conditions
        and bool(seen_conditions & {"failure", "timeout", "cancel"})
        and bool(seen_conditions & {"retry", "duplicate", "out_of_order"})
    )
    return (
        _nonblank_string_list(value.get("preconditions"))
        and str(value.get("start_state_id") or "").strip() in data_state_ids
        and isinstance(steps, list)
        and bool(steps)
        and all(
            isinstance(step, dict)
            and set(step) == {"input", "action", "expected_feedback"}
            and all(
                str(step.get(field) or "").strip()
                for field in ("input", "action", "expected_feedback")
            )
            for step in steps
        )
        and valid_branches
        and all(
            str(value.get(field) or "").strip()
            for field in (
                "focus_checkpoint",
                "announcement_checkpoint",
                "completion_checkpoint",
                "recovery_checkpoint",
            )
        )
    )


def _valid_scenario_contract(
    item: object,
    design_decision_ids: set[str],
    handoff_contract_ids: set[str],
    surface_ids: set[str],
    rows_by_field: dict[str, dict[str, dict[str, object]]],
) -> bool:
    if (
        not isinstance(item, dict)
        or not _valid_contract_row_refs(
            item, design_decision_ids, handoff_contract_ids
        )
        or str(item.get("surface_id") or "").strip() not in surface_ids
        or not str(item.get("name") or "").strip()
        or item.get("risk") not in {"low", "medium", "high"}
        or item.get("required") is not True
        or not _valid_interaction_script(
            item.get("interaction_script"),
            {
                str(state_id).strip()
                for state_id in item.get("data_state_ids") or []
                if isinstance(state_id, str) and state_id.strip()
            },
        )
    ):
        return False
    referenced_decisions: set[str] = set()
    for field, rows_by_id in rows_by_field.items():
        refs = item.get(field)
        if not _nonblank_string_list(refs):
            return False
        assert isinstance(refs, list)
        if any(ref not in rows_by_id for ref in refs):
            return False
        referenced_decisions.update(
            decision_id
            for row_id in refs
            for decision_id in rows_by_id[row_id].get("decision_ids") or []
            if isinstance(decision_id, str) and decision_id.strip()
        )
    return set(item.get("decision_ids") or []) == referenced_decisions


def _valid_responsive_contract(
    item: object,
    design_decision_ids: set[str],
    handoff_contract_ids: set[str],
) -> bool:
    if (
        not isinstance(item, dict)
        or not _valid_contract_row_refs(
            item, design_decision_ids, handoff_contract_ids
        )
        or not str(item.get("state") or "").strip()
        or not str(item.get("adaptation") or "").strip()
        or not str(item.get("stretch_behavior") or "").strip()
        or not str(item.get("overflow_behavior") or "").strip()
    ):
        return False
    if str(item.get("viewport") or "").strip():
        return True
    target = item.get("target")
    if not isinstance(target, dict):
        return False
    width = target.get("width")
    height = target.get("height")
    return (
        isinstance(width, (int, float))
        and not isinstance(width, bool)
        and width > 0
        and isinstance(height, (int, float))
        and not isinstance(height, bool)
        and height > 0
        and target.get("unit") in {"px", "cell", "point"}
    )


def _valid_visual_acceptance_contract(
    item: object,
    design_decision_ids: set[str],
    handoff_contract_ids: set[str],
) -> bool:
    if not isinstance(item, dict) or not _valid_contract_row_refs(
        item, design_decision_ids, handoff_contract_ids
    ):
        return False
    if (
        str(item.get("viewport") or "").strip()
        and str(item.get("state") or "").strip()
        and str(item.get("evidence") or "").strip()
    ):
        return True
    return bool(str(item.get("target_id") or "").strip()) and all(
        isinstance(item.get(field), list) and bool(item.get(field))
        for field in (
            "states",
            "color_modes",
            "motion_modes",
            "decision_ids",
            "must_match",
            "evidence",
        )
    )


def _valid_data_scenario(item: object) -> bool:
    return isinstance(item, dict) and all(
        str(item.get(field) or "").strip()
        for field in ("state", "data_condition", "expectation")
    )


def _valid_component_adoption(value: object) -> bool:
    if not isinstance(value, dict):
        return False
    if not str(value.get("resource_id") or "").strip():
        return False
    if value.get("action") not in {"reuse", "extend", "add", "custom"}:
        return False
    if any(
        not isinstance(value.get(field), str)
        or not str(value.get(field) or "").strip()
        for field in ("package", "version", "license", "source_ref")
    ):
        return False
    if any(
        not _nonblank_string_list(value.get(field))
        for field in ("component_refs", "reason_codes", "selection_basis_refs")
    ):
        return False
    permission_gate = value.get("permission_gate")
    permission_status = value.get("permission_status")
    if permission_gate not in {"required", "not-required"}:
        return False
    if permission_status not in {"authorized", "not-authorized"}:
        return False
    if value.get("action") == "add" and permission_gate != "required":
        return False
    if permission_gate == "not-required" and permission_status != "authorized":
        return False
    return True


def _valid_component_contract(
    item: object,
    design_decision_ids: set[str],
    handoff_contract_ids: set[str],
) -> bool:
    if (
        not isinstance(item, dict)
        or not _valid_contract_row_refs(
            item, design_decision_ids, handoff_contract_ids
        )
        or not str(item.get("component") or "").strip()
        or not _nonblank_string_list(item.get("anatomy"))
        or not _nonblank_string_list(item.get("variants"))
        or not _nonblank_string_list(item.get("content_constraints"))
        or not _nonblank_string_list(item.get("semantic_token_refs"))
        or item.get("governance") not in {"reuse", "extend", "new"}
        or not str(item.get("iconography") or "").strip()
    ):
        return False
    adoption = item.get("adoption")
    if adoption is not None and not _valid_component_adoption(adoption):
        return False
    required_states = item.get("required_states")
    interaction_modes = item.get("interaction_modes")
    data_scenarios = item.get("data_scenarios")
    if (
        not isinstance(required_states, list)
        or not required_states
        or _has_blank_entry(required_states)
    ):
        return False
    if (
        not isinstance(interaction_modes, list)
        or not interaction_modes
        or _has_blank_entry(interaction_modes)
    ):
        return False
    if (
        not isinstance(data_scenarios, list)
        or not data_scenarios
        or any(not _valid_data_scenario(scenario) for scenario in data_scenarios)
    ):
        return False
    return True


def _valid_interaction_contract(
    item: object,
    design_decision_ids: set[str],
    handoff_contract_ids: set[str],
) -> bool:
    required_fields = {
        "id",
        "surface",
        "input",
        "trigger",
        "event_sequence",
        "immediate_feedback",
        "focus_behavior",
        "repeat_behavior",
        "cancellation_behavior",
        "pending_behavior",
        "decision_ids",
    }
    return (
        isinstance(item, dict)
        and set(item) == required_fields
        and _valid_contract_row_refs(
            item, design_decision_ids, handoff_contract_ids
        )
        and all(
            str(item.get(field) or "").strip()
            for field in required_fields - {"decision_ids"}
        )
    )


def _valid_editing_contract(
    item: object,
    design_decision_ids: set[str],
    handoff_contract_ids: set[str],
) -> bool:
    required_fields = {
        "id",
        "surface",
        "input_methods",
        "composition_behavior",
        "paste_autofill_behavior",
        "selection_caret_behavior",
        "formatting_behavior",
        "validation_timing",
        "validation_feedback",
        "dirty_state_behavior",
        "persistence_behavior",
        "undo_redo_behavior",
        "conflict_behavior",
        "read_only_disabled_behavior",
        "submission_behavior",
        "decision_ids",
    }
    return (
        isinstance(item, dict)
        and set(item) == required_fields
        and _valid_contract_row_refs(
            item, design_decision_ids, handoff_contract_ids
        )
        and _nonblank_string_list(item.get("input_methods"))
        and all(
            str(item.get(field) or "").strip()
            for field in required_fields
            - {"input_methods", "decision_ids"}
        )
    )


def _valid_data_state_contract(
    item: object,
    design_decision_ids: set[str],
    handoff_contract_ids: set[str],
) -> bool:
    return (
        isinstance(item, dict)
        and _valid_contract_row_refs(
            item, design_decision_ids, handoff_contract_ids
        )
        and bool(str(item.get("surface") or "").strip())
        and bool(str(item.get("state") or "").strip())
        and bool(str(item.get("data_condition") or "").strip())
        and bool(str(item.get("expectation") or "").strip())
    )


def _valid_accessibility_contract(
    item: object,
    design_decision_ids: set[str],
    handoff_contract_ids: set[str],
) -> bool:
    return (
        isinstance(item, dict)
        and _valid_contract_row_refs(
            item, design_decision_ids, handoff_contract_ids
        )
        and bool(str(item.get("surface") or "").strip())
        and _nonblank_string_list(item.get("semantics"))
        and bool(str(item.get("reading_order") or "").strip())
        and bool(str(item.get("focus_order") or "").strip())
        and _nonblank_string_list(item.get("keyboard"))
        and _nonblank_string_list(item.get("announcements"))
        and bool(str(item.get("target_size") or "").strip())
        and bool(str(item.get("contrast") or "").strip())
        and bool(str(item.get("zoom_reflow") or "").strip())
        and _nonblank_string_list(item.get("alternatives"))
    )


def _valid_navigation_contract(
    item: object,
    design_decision_ids: set[str],
    handoff_contract_ids: set[str],
) -> bool:
    return (
        isinstance(item, dict)
        and _valid_contract_row_refs(
            item, design_decision_ids, handoff_contract_ids
        )
        and all(
            str(item.get(field) or "").strip()
            for field in (
                "surface",
                "entry",
                "destination",
                "trigger",
                "back_behavior",
                "deep_link_behavior",
                "interruption_recovery",
            )
        )
    )


def _valid_content_contract(
    item: object,
    design_decision_ids: set[str],
    handoff_contract_ids: set[str],
) -> bool:
    return (
        isinstance(item, dict)
        and _valid_contract_row_refs(
            item, design_decision_ids, handoff_contract_ids
        )
        and all(
            str(item.get(field) or "").strip()
            for field in (
                "surface",
                "state",
                "purpose",
                "copy",
                "primary_action",
                "trust_requirement",
                "localization",
            )
        )
        and _nonblank_string_list(item.get("content_limits"))
    )


def _valid_motion_contract(
    value: object,
    design_decision_ids: set[str],
    handoff_contract_ids: set[str],
) -> bool:
    if not isinstance(value, dict):
        return False
    if not str(value.get("purpose") or "").strip() or not str(
        value.get("reduced_motion") or ""
    ).strip():
        return False
    transitions = value.get("transitions")
    if not isinstance(transitions, list) or not transitions:
        return False
    for item in transitions:
        if (
            not isinstance(item, dict)
            or not _valid_contract_row_refs(
                item, design_decision_ids, handoff_contract_ids
            )
            or not all(
                str(item.get(field) or "").strip()
                for field in (
                    "surface",
                    "trigger",
                    "response",
                    "easing",
                    "interrupt_behavior",
                )
            )
        ):
            return False
        duration = item.get("duration_ms")
        if isinstance(duration, bool) or not isinstance(duration, (int, float)):
            return False
        if duration < 0:
            return False
    timing = value.get("feedback_timing")
    if not isinstance(timing, dict):
        return False
    values: list[float] = []
    for field in ("immediate_ms", "progress_ms", "timeout_ms"):
        raw = timing.get(field)
        if isinstance(raw, bool) or not isinstance(raw, (int, float)) or raw < 0:
            return False
        values.append(float(raw))
    return values == sorted(values)


def _valid_usability_validation(value: object) -> bool:
    if not isinstance(value, dict) or value.get("risk_level") not in {
        "low",
        "medium",
        "high",
    }:
        return False
    if not all(
        _nonblank_string_list(value.get(field))
        for field in ("methods", "critical_tasks", "success_criteria")
    ):
        return False
    human_review_required = value.get("human_review_required")
    if not isinstance(human_review_required, bool):
        return False
    smoothness_ids = value.get("smoothness_acceptance_ids")
    if smoothness_ids is not None:
        if not isinstance(smoothness_ids, list) or any(
            not isinstance(item, str) or not item.strip()
            for item in smoothness_ids
        ):
            return False
        normalized_ids = [str(item).strip() for item in smoothness_ids]
        if len(normalized_ids) != len(set(normalized_ids)):
            return False
    performance_budgets = value.get("performance_budgets")
    if performance_budgets is not None:
        if not isinstance(performance_budgets, dict):
            return False
        expected_budget_fields = {
            "inp_ms",
            "long_task_ms",
            "cls",
            "animation_dropped_frame_pct",
            "bundle_delta_kb",
        }
        if set(performance_budgets) != expected_budget_fields:
            return False
        if any(
            isinstance(performance_budgets.get(field), bool)
            or not isinstance(performance_budgets.get(field), (int, float))
            or performance_budgets.get(field, -1) < 0
            for field in expected_budget_fields
        ):
            return False
    return value.get("risk_level") != "high" or human_review_required


def _ui_contract_applies(packet: WorkerTaskPacket) -> bool:
    contract = packet.ui_contract
    return (
        any(
            getattr(contract, field_name)
            for field_name in UI_CONTRACT_FIELDS
            if field_name != "fidelity_level"
        )
        or contract.fidelity_level != "none"
    )


def _validate_style_authority(value: object) -> None:
    expected_fields = {
        "mode",
        "scope_level",
        "source_refs",
        "protected_surfaces",
        "allowed_style_delta_surfaces",
        "authorization_source",
    }
    if not isinstance(value, dict) or set(value) != expected_fields:
        raise PacketValidationError(
            "DP1",
            "UI contract style_authority must contain the current exact fields",
        )
    mode = str(value.get("mode") or "").strip()
    scope_level = str(value.get("scope_level") or "").strip()
    source_refs = value.get("source_refs")
    protected = value.get("protected_surfaces")
    allowed = value.get("allowed_style_delta_surfaces")
    authorization = value.get("authorization_source")
    if mode not in {
        "greenfield",
        "inherit-existing",
        "page-overhaul-authorized",
    }:
        raise PacketValidationError(
            "DP1", "UI contract style_authority.mode is not resolved"
        )
    if scope_level not in {"feature-partial", "page"}:
        raise PacketValidationError(
            "DP1", "UI contract style_authority.scope_level is invalid"
        )
    for field_name, items in (
        ("source_refs", source_refs),
        ("protected_surfaces", protected),
        ("allowed_style_delta_surfaces", allowed),
    ):
        if not isinstance(items, list) or any(
            not isinstance(item, str) or not item.strip() for item in items
        ) or len(items) != len(set(items)):
            raise PacketValidationError(
                "DP1",
                f"UI contract style_authority.{field_name} must be a string list",
            )
    assert isinstance(source_refs, list)
    assert isinstance(protected, list)
    assert isinstance(allowed, list)
    protected_set = {item.strip() for item in protected}
    allowed_set = {item.strip() for item in allowed}
    baseline_guards = {"global-shell", "shared-components"}
    authorization_claimed = authorization is not None and authorization != ""
    if mode == "greenfield":
        if authorization_claimed:
            raise PacketValidationError(
                "DP1",
                "UI contract greenfield style_authority cannot claim overhaul authorization",
            )
        return
    if not source_refs or not baseline_guards <= protected_set:
        raise PacketValidationError(
            "DP1",
            "UI contract existing-UI style_authority requires live sources plus global-shell and shared-components protection",
        )
    if mode == "inherit-existing":
        if scope_level != "feature-partial" or allowed_set or authorization_claimed:
            raise PacketValidationError(
                "DP1",
                "UI contract inherit-existing style_authority cannot authorize a style delta",
            )
        return
    if (
        scope_level != "page"
        or not allowed_set
        or allowed_set & baseline_guards
        or not isinstance(authorization, str)
        or not authorization.strip()
    ):
        raise PacketValidationError(
            "DP1",
            "UI contract page-overhaul-authorized style_authority requires one exact page delta and explicit authorization while protecting shared UI",
        )


def validate_ui_contract(contract: UIContract) -> None:
    """Validate the one current UI contract shape and values."""
    if contract.fidelity_level not in {"approximate", "high", "inspiration"}:
        raise PacketValidationError(
            "DP1",
            "active UI contract fidelity_level must be approximate, high, or inspiration",
        )
    design_change_values = (
        contract.design_change_id.strip(),
        contract.design_change_ref.strip(),
        contract.design_change_sha256.strip(),
        contract.design_contract_ref.strip(),
    )
    has_design_change_binding = any(design_change_values)
    if has_design_change_binding and not all(design_change_values):
        raise PacketValidationError(
            "DP1",
            "UI contract design change ID, ref, SHA-256, and machine contract ref must be present together",
        )
    if has_design_change_binding:
        if not DESIGN_CHANGE_ID_RE.fullmatch(contract.design_change_id):
            raise PacketValidationError(
                "DP1", "UI contract design_change_id must be a canonical UD-#### ID"
            )
        expected_workspace = f".specify/design/changes/{contract.design_change_id}"
        expected_design_ref = f"{expected_workspace}/design-change.md"
        expected_contract_ref = f"{expected_workspace}/design-contract.json"
        if contract.design_change_ref != expected_design_ref:
            raise PacketValidationError(
                "DP1",
                "UI contract design_change_ref must match its UD-* workspace",
            )
        if contract.design_contract_ref != expected_contract_ref:
            raise PacketValidationError(
                "DP1",
                "UI contract design_contract_ref must match its UD-* workspace",
            )
        if not SHA256_RE.fullmatch(contract.design_change_sha256):
            raise PacketValidationError(
                "DP1", "UI contract design_change_sha256 must be a SHA-256 digest"
            )
        for required_source in (expected_design_ref, expected_contract_ref):
            if required_source not in contract.design_sources:
                raise PacketValidationError(
                    "DP1",
                    f"UI contract design_sources must include {required_source}",
                )
        for bound_ref in (
            contract.approved_visual_ref,
            contract.approved_handoff_ref,
        ):
            if bound_ref.startswith(".specify/design/changes/") and not bound_ref.startswith(
                f"{expected_workspace}/"
            ):
                raise PacketValidationError(
                    "DP1",
                    "UI contract change-local approval refs must match design_change_id",
                )
    elif any(
        source.startswith(".specify/design/changes/")
        for source in contract.design_sources
    ):
        raise PacketValidationError(
            "DP1",
            "UI contract change-local design_sources require an exact design change binding",
        )
    if contract.ui_work_type not in UI_WORK_TYPES:
        raise PacketValidationError("DP1", "UI contract requires a valid ui_work_type")
    if contract.surface_type not in UI_SURFACE_TYPES:
        raise PacketValidationError("DP1", "UI contract requires a valid surface_type")
    if not contract.platforms or any(
        item not in UI_PLATFORMS for item in contract.platforms
    ):
        raise PacketValidationError("DP1", "UI contract requires supported platforms")
    _validate_style_authority(contract.style_authority)
    for field_name in (
        "subject",
        "audience",
        "single_job",
        "visual_thesis",
        "content_thesis",
        "interaction_thesis",
        "signature_element",
        "approved_visual_ref",
    ):
        if not str(getattr(contract, field_name)).strip():
            raise PacketValidationError(
                "DP1", f"UI contract requires nonblank {field_name}"
            )
    if not contract.design_sources or _has_blank_entry(contract.design_sources):
        raise PacketValidationError("DP1", "UI contract requires design_sources")
    if not contract.design_decision_ids or any(
        not DESIGN_DECISION_ID_RE.fullmatch(item)
        for item in contract.design_decision_ids
    ):
        raise PacketValidationError(
            "DP1", "UI contract requires canonical design_decision_ids"
        )
    if any(
        not isinstance(item, str) or not DESIGN_HANDOFF_ID_RE.fullmatch(item)
        for item in contract.handoff_contract_ids
    ):
        raise PacketValidationError(
            "DP1", "UI contract handoff_contract_ids must contain canonical DH-* IDs"
        )
    for field_name in (
        "approved_preview_sha256",
        "approved_manifest_sha256",
        "approved_handoff_sha256",
    ):
        value = str(getattr(contract, field_name) or "").strip()
        if value and not SHA256_RE.fullmatch(value):
            raise PacketValidationError(
                "DP1", f"UI contract {field_name} must be a SHA-256 digest"
            )
    has_handoff_ref = bool(contract.approved_handoff_ref.strip())
    has_handoff_digest = bool(contract.approved_handoff_sha256.strip())
    has_handoff_ids = bool(contract.handoff_contract_ids)
    if any((has_handoff_ref, has_handoff_digest, has_handoff_ids)) and not (
        has_handoff_ref and has_handoff_digest and has_handoff_ids
    ):
        raise PacketValidationError(
            "DP1",
            "UI contract immutable handoff ref, SHA-256, and DH-* IDs must be present together",
        )
    if has_handoff_ref and not contract.approved_handoff_ref.strip().lower().endswith(
        ".handoff.json"
    ):
        raise PacketValidationError(
            "DP1", "UI contract approved_handoff_ref must identify a .handoff.json file"
        )
    approved_visual_ref = contract.approved_visual_ref.strip()
    has_change_local_prefix = bool(
        CHANGE_LOCAL_PREVIEW_PREFIX_RE.match(approved_visual_ref)
    )
    if has_change_local_prefix and not has_design_change_binding:
        raise PacketValidationError(
            "DP1",
            "UI contract change-local visual round requires an exact design change binding",
        )
    change_local_preview = False
    if has_design_change_binding:
        expected_workspace_prefix = (
            f".specify/design/changes/{contract.design_change_id}/"
        )
        expected_preview_prefix = f"{expected_workspace_prefix}previews/"
        approved_handoff_ref = contract.approved_handoff_ref.strip()
        uses_change_workspace = approved_visual_ref.startswith(
            expected_workspace_prefix
        ) or approved_handoff_ref.startswith(expected_workspace_prefix)
        if uses_change_workspace:
            if not approved_visual_ref.startswith(
                expected_preview_prefix
            ) or not approved_handoff_ref.startswith(expected_preview_prefix):
                raise PacketValidationError(
                    "DP1",
                    "UI contract change-local visual round and immutable handoff must stay in the design change previews workspace",
                )
            preview_suffix = approved_visual_ref.removeprefix(
                expected_preview_prefix
            )
            preview_match = CHANGE_LOCAL_PREVIEW_SUFFIX_RE.fullmatch(preview_suffix)
            if not preview_match:
                raise PacketValidationError(
                    "DP1",
                    "UI contract change-local visual round must match round-<number>.<html|png|jpg|jpeg|webp>#direction-<slug>",
                )
            change_local_preview = True
            expected_handoff_ref = (
                f"{expected_preview_prefix}{preview_match.group('stem')}.handoff.json"
            )
            if approved_handoff_ref != expected_handoff_ref:
                raise PacketValidationError(
                    "DP1",
                    "UI contract change-local visual round requires the same-stem immutable handoff sidecar",
                )
    if (
        change_local_preview
        or APPROVED_PREVIEW_REF_RE.search(contract.approved_visual_ref)
    ) and (
        not SHA256_RE.fullmatch(contract.approved_preview_sha256)
        or not SHA256_RE.fullmatch(contract.approved_manifest_sha256)
        or not contract.approved_handoff_ref.strip().lower().endswith(".handoff.json")
        or not SHA256_RE.fullmatch(contract.approved_handoff_sha256)
        or not contract.handoff_contract_ids
        or any(
            not DESIGN_HANDOFF_ID_RE.fullmatch(item)
            for item in contract.handoff_contract_ids
        )
    ):
        raise PacketValidationError(
            "DP1",
            "approved visual round requires preview, manifest, and immutable handoff bindings",
        )
    if not contract.required_states or _has_blank_entry(contract.required_states):
        raise PacketValidationError("DP1", "UI contract requires required_states")
    if not contract.real_content_plan:
        raise PacketValidationError("DP1", "UI contract requires a real_content_plan")
    for item in contract.real_content_plan:
        if not isinstance(item, dict) or not str(item.get("source_ref") or "").strip():
            raise PacketValidationError(
                "DP1", "UI contract real_content_plan entries require source_ref"
            )
    for item in contract.reference_intents:
        if (
            not isinstance(item, dict)
            or not str(item.get("ref") or "").strip()
            or str(item.get("intent") or "").strip() not in UI_REFERENCE_INTENTS
            or str(item.get("fidelity") or "").strip()
            not in {"exact", "high", "approximate", "inspiration"}
            or not isinstance(item.get("surface_ids"), list)
            or not item.get("surface_ids")
            or any(
                not isinstance(surface_id, str) or not surface_id.strip()
                for surface_id in item.get("surface_ids", [])
            )
        ):
            raise PacketValidationError(
                "DP1",
                "UI contract reference_intents entries require ref, intent, fidelity, and governed surface_ids",
            )
    for item in contract.image_plan:
        if (
            not isinstance(item, dict)
            or not str(item.get("ref") or "").strip()
            or not str(item.get("role") or "").strip()
        ):
            raise PacketValidationError(
                "DP1", "UI contract image_plan entries require ref and role"
            )
    continuity_result = validate_ui_source_continuity(
        contract.source_continuity,
        require_ready=True,
    )
    if not continuity_result.valid:
        details = "; ".join(
            f"{error.path}: {error.message}" for error in continuity_result.errors
        )
        raise PacketValidationError(
            "DP1",
            "UI contract source_continuity is invalid: " + details,
        )
    decision_id_set = set(contract.design_decision_ids)
    handoff_id_set = set(contract.handoff_contract_ids)
    if not contract.interaction_matrix or any(
        not _valid_interaction_contract(item, decision_id_set, handoff_id_set)
        for item in contract.interaction_matrix
    ):
        raise PacketValidationError(
            "DP1",
            "UI contract interaction_matrix entries require the complete event, feedback, focus, repeat, cancellation, pending, and known-reference lifecycle",
        )
    if not contract.editing_matrix or any(
        not _valid_editing_contract(item, decision_id_set, handoff_id_set)
        for item in contract.editing_matrix
    ):
        raise PacketValidationError(
            "DP1",
            "UI contract editing_matrix entries require the complete input, composition, validation, persistence, history, conflict, state, submission, and known-reference contract",
        )
    if not contract.data_state_matrix or any(
        not _valid_data_state_contract(item, decision_id_set, handoff_id_set)
        for item in contract.data_state_matrix
    ):
        raise PacketValidationError(
            "DP1",
            "UI contract data_state_matrix entries require id, surface, state, data_condition, expectation, and known decision/DH references",
        )
    if not contract.accessibility_matrix or any(
        not _valid_accessibility_contract(item, decision_id_set, handoff_id_set)
        for item in contract.accessibility_matrix
    ):
        raise PacketValidationError(
            "DP1",
            "UI contract accessibility_matrix entries require the full semantic, focus, keyboard, announcement, target, contrast, zoom, alternative, and known-reference contract",
        )
    if not contract.navigation_matrix or any(
        not _valid_navigation_contract(item, decision_id_set, handoff_id_set)
        for item in contract.navigation_matrix
    ):
        raise PacketValidationError(
            "DP1",
            "UI contract navigation_matrix entries require entry/destination, trigger, back/deep-link/interruption behavior, and known references",
        )
    if not contract.content_matrix or any(
        not _valid_content_contract(item, decision_id_set, handoff_id_set)
        for item in contract.content_matrix
    ):
        raise PacketValidationError(
            "DP1",
            "UI contract content_matrix entries require state-specific copy, action, trust, localization, limits, and known references",
        )
    if not contract.color_modes or _has_blank_entry(contract.color_modes):
        raise PacketValidationError("DP1", "UI contract requires color_modes")
    if not contract.component_contracts:
        raise PacketValidationError("DP1", "UI contract requires component_contracts")
    for item in contract.component_contracts:
        if not _valid_component_contract(item, decision_id_set, handoff_id_set):
            raise PacketValidationError(
                "DP1",
                "UI contract component_contracts require immutable identity, anatomy, states, modes, data, variants, content/token governance, iconography, and known references",
            )
    component_ids = {
        str(item.get("id") or "").strip()
        for item in contract.component_contracts
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    if not contract.surface_catalog or any(
        not _valid_surface_contract(
            item, decision_id_set, handoff_id_set, component_ids
        )
        for item in contract.surface_catalog
    ):
        raise PacketValidationError(
            "DP1",
            "UI contract surface_catalog entries require stable identity, profile, source/specimen/component coverage, and known references",
        )
    if contract.source_continuity.get("applicability") == "required":
        migration_errors = migration_component_binding_errors(
            contract.source_continuity, contract.component_contracts
        )
        if migration_errors:
            raise PacketValidationError("DP1", "; ".join(migration_errors))
        surface_ids = {
            str(item.get("id") or "").strip()
            for item in contract.surface_catalog
            if isinstance(item, dict)
        }
        interaction_ids = {
            str(item.get("id") or "").strip()
            for item in contract.interaction_matrix
            if isinstance(item, dict)
        }
        coverage = contract.source_continuity.get("coverage")
        if not isinstance(coverage, dict):
            raise PacketValidationError(
                "DP1",
                "UI contract source_continuity requires a coverage object",
            )
        declared_coverage = {
            "surface_ids": {
                str(item).strip()
                for item in coverage.get("surface_ids") or []
                if isinstance(item, str) and item.strip()
            },
            "interaction_ids": {
                str(item).strip()
                for item in coverage.get("interaction_ids") or []
                if isinstance(item, str) and item.strip()
            },
            "component_ids": {
                str(item).strip()
                for item in coverage.get("component_ids") or []
                if isinstance(item, str) and item.strip()
            },
        }
        actual_coverage = {
            "surface_ids": surface_ids,
            "interaction_ids": interaction_ids,
            "component_ids": component_ids,
        }
        for field, actual_ids in actual_coverage.items():
            if declared_coverage[field] != actual_ids:
                raise PacketValidationError(
                    "DP1",
                    "UI contract source_continuity coverage."
                    f"{field} must exactly cover the selected UI contract IDs",
                )
        for row in contract.source_continuity.get("surface_bindings") or []:
            if not isinstance(row, dict) or str(row.get("surface_id") or "").strip() not in surface_ids:
                raise PacketValidationError(
                    "DP1",
                    "UI contract source_continuity surface_bindings must reference selected surface_catalog IDs",
                )
        if contract.style_authority.get("mode") == "inherit-existing":
            disallowed = {
                str(row.get("disposition") or "").strip()
                for row in contract.source_continuity.get("surface_bindings") or []
                if isinstance(row, dict)
            } & {"replace", "merge", "split", "retire"}
            if disallowed:
                raise PacketValidationError(
                    "DP1",
                    "UI contract inherit-existing style_authority requires source_continuity surface_bindings to preserve or adapt existing surfaces",
                )
        for row in contract.source_continuity.get("action_bindings") or []:
            if not isinstance(row, dict) or str(row.get("interaction_id") or "").strip() not in interaction_ids:
                raise PacketValidationError(
                    "DP1",
                    "UI contract source_continuity action_bindings must reference selected interaction_matrix IDs",
                )
        for row in contract.source_continuity.get("asset_bindings") or []:
            if not isinstance(row, dict) or str(row.get("component_id") or "").strip() not in component_ids:
                raise PacketValidationError(
                    "DP1",
                    "UI contract source_continuity asset_bindings must reference selected component_contracts IDs",
                )
    if not contract.responsive_matrix or any(
        not _valid_responsive_contract(item, decision_id_set, handoff_id_set)
        for item in contract.responsive_matrix
    ):
        raise PacketValidationError(
            "DP1",
            "UI contract responsive_matrix entries require state, stretch/overflow behavior, decision_ids, and a viewport or immutable target plus adaptation",
        )
    if not _valid_motion_contract(
        contract.motion_contract, decision_id_set, handoff_id_set
    ):
        raise PacketValidationError(
            "DP1",
            "UI contract motion_contract requires transitions, reduced motion, ordered feedback timing, and known references",
        )
    if not _valid_usability_validation(contract.usability_validation):
        raise PacketValidationError(
            "DP1",
            "UI contract usability_validation requires risk, methods, critical tasks, success criteria, and a human-review decision",
        )
    surface_ids = {
        str(item.get("id") or "").strip()
        for item in contract.surface_catalog
        if isinstance(item, dict) and str(item.get("id") or "").strip()
    }
    scenario_rows_by_field = {
        field: {
            str(item.get("id") or "").strip(): item
            for item in collection
            if isinstance(item, dict) and str(item.get("id") or "").strip()
        }
        for field, collection in {
            "interaction_ids": contract.interaction_matrix,
            "editing_ids": contract.editing_matrix,
            "data_state_ids": contract.data_state_matrix,
            "accessibility_ids": contract.accessibility_matrix,
            "navigation_ids": contract.navigation_matrix,
            "content_ids": contract.content_matrix,
            "responsive_ids": contract.responsive_matrix,
            "motion_transition_ids": (
                contract.motion_contract.get("transitions") or []
                if isinstance(contract.motion_contract, dict)
                else []
            ),
        }.items()
    }
    if not contract.scenario_matrix or any(
        not _valid_scenario_contract(
            item,
            decision_id_set,
            handoff_id_set,
            surface_ids,
            scenario_rows_by_field,
        )
        for item in contract.scenario_matrix
    ):
        raise PacketValidationError(
            "DP1",
            "UI contract scenario_matrix entries must bind one stable surface to known interaction/editing/data/accessibility/navigation/content/responsive/motion rows, an executable interaction_script, and exact decision coverage",
        )
    if not contract.visual_acceptance_matrix or any(
        not _valid_visual_acceptance_contract(item, decision_id_set, handoff_id_set)
        for item in contract.visual_acceptance_matrix
    ):
        raise PacketValidationError(
            "DP1",
            "UI contract visual_acceptance_matrix entries require a viewport/state/evidence row or an immutable target contract",
        )
    if not _valid_comparison_tolerance(contract.comparison_tolerance):
        raise PacketValidationError(
            "DP1",
            "UI contract comparison_tolerance must preserve the structured exact-reproduction rules",
        )
    if any(
        not isinstance(item, dict)
        or not str(item.get("decision_id") or "").strip()
        or not str(item.get("reason") or "").strip()
        for item in contract.accepted_deviations
    ):
        raise PacketValidationError(
            "DP1",
            "UI contract accepted_deviations entries require decision_id and reason",
        )
    evidence = {item.strip() for item in contract.required_evidence}
    if evidence != UI_REQUIRED_EVIDENCE:
        raise PacketValidationError(
            "DP1",
            "UI contract required_evidence must be exactly: "
            + ", ".join(sorted(UI_REQUIRED_EVIDENCE)),
        )


def validate_ui_context_nav(
    context_nav: list[dict[str, str]], *, require_handoff: bool = False
) -> None:
    """Validate packet-only compact navigation derived for UI execution."""

    context_kinds = {
        str(item.get("kind") or "").strip()
        for item in context_nav
        if isinstance(item, dict)
    }
    missing_context = {"ui_entrypoint", "design_source"} - context_kinds
    if require_handoff:
        missing_context |= {"design_handoff"} - context_kinds
    if missing_context:
        raise PacketValidationError(
            "DP2",
            "UI contract is missing compact context_nav kinds: "
            + ", ".join(sorted(missing_context)),
        )


def validate_worker_task_packet(packet: WorkerTaskPacket) -> WorkerTaskPacket:
    """Return the packet when its hard-fail execution contract is complete."""

    if (
        not packet.intent.outcome
        or not packet.intent.constraints
        or not packet.intent.success_signals
    ):
        raise PacketValidationError(
            "DP1", "execution intent contract must be present in the packet"
        )
    if not packet.scope.write_scope:
        raise PacketValidationError(
            "DP1", "write_scope is required for delegated execution"
        )
    if any(not _valid_write_scope_entry(item) for item in packet.scope.write_scope):
        raise PacketValidationError(
            "DP1",
            "write_scope entries must be an exact future file path or bounded directory subtree; exact directory paths without globbing are also allowed, but filename globs such as *_test.go, ?, [], /*, or middle ** are not",
        )
    if not packet.context_bundle:
        raise PacketValidationError(
            "DP2", "context_bundle must be compiled into the packet"
        )
    if not packet.required_references:
        raise PacketValidationError(
            "DP2", "required_references must be compiled into the packet"
        )
    if not packet.hard_rules:
        raise PacketValidationError("DP1", "hard_rules must be present in the packet")
    policy = packet.validation_policy
    if policy.mode not in {"task", "feature_epochs"}:
        raise PacketValidationError("DP1", "validation_policy mode is invalid")
    if policy.mode == "feature_epochs":
        if (
            isinstance(policy.max_epochs, bool)
            or not isinstance(policy.max_epochs, int)
            or policy.max_epochs != 3
        ):
            raise PacketValidationError(
                "DP1",
                "feature_epochs validation_policy max_epochs must equal 3 so "
                "Review retains its delivery gate",
            )
        if policy.budget_scope != "implement-review":
            raise PacketValidationError(
                "DP1",
                "feature_epochs validation_policy budget_scope must be implement-review",
            )
        if not policy.budget_ref.strip():
            raise PacketValidationError(
                "DP1", "feature_epochs validation_policy requires budget_ref"
            )
        if policy.heavy_gate_owner != "leader":
            raise PacketValidationError(
                "DP1",
                "feature_epochs validation_policy heavy_gate_owner must be leader",
            )
    elif not packet.validation_gates:
        raise PacketValidationError(
            "DP1", "validation_gates must be present in the packet"
        )
    if not packet.done_criteria:
        raise PacketValidationError(
            "DP1", "done_criteria must be present in the packet"
        )
    if not packet.handoff_requirements:
        raise PacketValidationError(
            "DP1", "handoff_requirements must be present in the packet"
        )
    if not packet.platform_guardrails:
        raise PacketValidationError(
            "DP2", "platform_guardrails must be compiled into the packet"
        )
    if _has_blank_entry(packet.user_confirmed_deferral_refs):
        raise PacketValidationError(
            "DP1", "user_confirmed_deferral_refs cannot contain blank entries"
        )
    if any(SURFACE_LIMIT_ANTI_GOAL_RE.search(goal) for goal in packet.anti_goals):
        if not packet.does_not_remove:
            raise PacketValidationError(
                "DP1",
                "surface-limiting anti-goals require a does-not-remove guard",
            )
    obsolete_evidence = sorted(
        {
            item.strip().lower().replace("-", "_").replace(" ", "_")
            for item in packet.required_evidence
        }
        & OBSOLETE_UI_EVIDENCE_LABELS
    )
    if obsolete_evidence:
        raise PacketValidationError(
            "DP1",
            "worker packet contains obsolete UI evidence labels: "
            + ", ".join(obsolete_evidence),
        )
    if packet.ui_contract.fidelity_level not in {
        "none",
        "approximate",
        "high",
        "inspiration",
    }:
        raise PacketValidationError(
            "DP1",
            "UI contract fidelity_level must be none, approximate, high, or inspiration",
        )
    if _ui_contract_applies(packet):
        validate_ui_contract(packet.ui_contract)
        validate_ui_context_nav(
            packet.context_nav,
            require_handoff=bool(packet.ui_contract.approved_handoff_ref),
        )
    if _has_blank_entry(packet.controller_checks_required):
        raise PacketValidationError(
            "DP1", "controller checks required cannot contain blank entries"
        )
    for obligation in packet.must_preserve_obligations:
        if not MP_ID_RE.match(obligation.id):
            raise PacketValidationError(
                "DP1", "must-preserve obligation id must use MP-### format"
            )
        if (
            not obligation.type
            or not obligation.claim
            or not obligation.source
            or not obligation.downstream_requirement
        ):
            raise PacketValidationError(
                "DP1", "must-preserve obligation is missing required fields"
            )
    for obligation in packet.consequence_obligations:
        if not obligation.obligation_id.strip():
            raise PacketValidationError(
                "DP2", "consequence obligation is missing obligation_id"
            )
        if not obligation.claim.strip():
            raise PacketValidationError(
                "DP2",
                f"consequence obligation {obligation.obligation_id} is missing claim",
            )
        if not obligation.affected_objects:
            raise PacketValidationError(
                "DP2",
                f"consequence obligation {obligation.obligation_id} is missing affected_objects",
            )
        if not obligation.stop_and_reopen_condition.strip():
            raise PacketValidationError(
                "DP2",
                f"consequence obligation {obligation.obligation_id} is missing stop_and_reopen_condition",
            )
    return packet
