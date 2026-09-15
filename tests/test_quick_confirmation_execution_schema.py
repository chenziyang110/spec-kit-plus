"""Persisted Quick audit data must fit its shipped schema, without granting authority.

Synthetic fixtures exercise JSON Schema, not Work ownership or task acceptance.
Runtime field coverage is independently checked by the Go reflection test.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "templates" / "quick-confirmation-schema.json"


def confirmation(execution: dict | None = None) -> dict:
    doc = {
        "schema": "quick-confirmation-v1",
        "confirmation_mode": "full",
        "confirmation_state": "confirmed",
        "confirmation_digest": "a" * 64,
        "source": {"kind": "prompt", "semantic_delta": False},
        "decision": {
            "goal": "Synthetic schema fixture",
            "user_visible_result": "Fixture result",
            "scope": {"include": ["fixture"], "exclude": []},
            "items": [{"id": "Q1", "deliverable": "Fixture", "depends_on": [],
                       "acceptance": "Independent fixture check", "write_scope": ["src/fixture.go"]}],
            "reconfirmation_trigger": "Changed requirements",
        },
        "delivery": {"waves": [{"id": "W1", "item_ids": ["Q1"], "parallel": False}]},
    }
    if execution is not None:
        doc["execution"] = execution
    return doc


def execution_row(**fields: object) -> dict:
    return {"work_item_status": [{"work_item_id": "Q1", "status": "in_progress", **fields}]}


class QuickConfirmationExecutionSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        cls.validator = Draft202012Validator(cls.schema)

    def assert_valid(self, value: dict) -> None:
        self.assertEqual([], [error.message for error in self.validator.iter_errors(value)])

    def assert_invalid(self, value: dict, keyword: str) -> None:
        self.assertIn(keyword, [error.validator for error in self.validator.iter_errors(value)])

    def test_schema_is_well_formed(self) -> None:
        Draft202012Validator.check_schema(self.schema)

    def test_legacy_and_pre_dispatch_states_remain_valid(self) -> None:
        for execution in (None, {}, {"work_item_status": []}, execution_row(status="pending"),
                          execution_row(status="ready"), execution_row(status="blocked"),
                          execution_row(status="accepted", acceptance_evidence=["legacy fixture"])):
            with self.subTest(execution=execution):
                self.assert_valid(confirmation(execution))

    def test_started_worker_lock_is_representable(self) -> None:
        self.assert_valid(confirmation(execution_row(requires_worker=True)))

    def test_accepted_worker_result_binding_is_representable(self) -> None:
        self.assert_valid(confirmation(execution_row(
            status="accepted", requires_worker=False, execution_mode="worker",
            worker_result_id="Q1", worker_lane_id="Q1",
            worker_result_ref=".planning/quick/fixture/worker-results/Q1.json",
            acceptance_evidence=["test:synthetic-proof"],
        )))

    def test_recorded_inline_fallback_is_representable(self) -> None:
        for status, mode in (("in_progress", None), ("accepted", "leader-inline")):
            execution = execution_row(status=status, requires_worker=False,
                                      inline_approved=True, inline_reason="spawn_failed: fixture")
            if mode is not None:
                execution["work_item_status"][0]["execution_mode"] = mode
            execution["blocked_dispatch"] = {
                "status": "recorded-fallback", "reason": "spawn_failed: fixture",
                "attempted_shape": "one-subagent", "chosen_shape": "leader-inline",
                "item_id": "Q1", "approved_at": "2026-09-15T00:00:00Z",
            }
            with self.subTest(status=status):
                self.assert_valid(confirmation(execution))

    def test_optional_fallback_pointer_can_be_absent_empty_or_null(self) -> None:
        for value in ({}, None):
            with self.subTest(value=value):
                self.assert_valid(confirmation({"blocked_dispatch": value}))

    def test_unknown_execution_fields_still_fail_closed(self) -> None:
        for execution in ({"unexpected": True}, execution_row(unexpected=True),
                          {"blocked_dispatch": {"unexpected": True}}):
            with self.subTest(execution=execution):
                self.assert_invalid(confirmation(execution), "additionalProperties")

    def test_boolean_audit_fields_are_not_truthy_strings_or_numbers(self) -> None:
        for key in ("requires_worker", "inline_approved"):
            for value in ("true", 1, None, [], {}):
                with self.subTest(key=key, value=value):
                    self.assert_invalid(confirmation(execution_row(**{key: value})), "type")

    def test_result_bindings_and_reason_are_strings(self) -> None:
        for key in ("worker_result_id", "worker_result_ref", "worker_lane_id", "inline_reason"):
            for value in (True, 1, [], {}):
                with self.subTest(key=key, value=value):
                    self.assert_invalid(confirmation(execution_row(**{key: value})), "type")

    def test_direct_execution_mode_retains_result_audit_shape(self) -> None:
        doc = confirmation(execution_row(
            status="accepted", execution_mode="leader-direct", requires_worker=False,
            worker_result_ref=".planning/quick/example/worker-results/Q1.json",
            worker_lane_id="Q1", worker_result_id="Q1",
        ))
        self.assert_valid(doc)

    def test_unknown_execution_mode_is_not_advertised_by_schema(self) -> None:
        for mode in ("unimplemented-mode", "anything", "", "WORKER"):
            with self.subTest(mode=mode):
                self.assert_invalid(confirmation(execution_row(execution_mode=mode)), "enum")

    def test_dispatch_record_fields_are_typed_and_container_is_not_array(self) -> None:
        for key in ("status", "reason", "attempted_shape", "chosen_shape", "item_id", "approved_at"):
            with self.subTest(key=key):
                self.assert_invalid(confirmation({"blocked_dispatch": {key: True}}), "type")
        self.assert_invalid(confirmation({"blocked_dispatch": []}), "type")

    def test_existing_decision_and_status_requirements_remain_required(self) -> None:
        for path in (("decision", "goal"), ("decision", "items"), ("delivery", "waves")):
            doc = confirmation(execution_row(requires_worker=True))
            del doc[path[0]][path[1]]
            with self.subTest(path=path):
                self.assert_invalid(doc, "required")
        self.assert_invalid(confirmation(execution_row(status="DONE")), "enum")

    def test_ui_continuity_requirement_is_not_waived_by_audit_fields(self) -> None:
        doc = confirmation(execution_row(requires_worker=True))
        doc["decision"]["ui_confirmation"] = {"applicable": True}
        self.assert_invalid(doc, "required")

    def test_validator_does_not_mutate_or_authorize_the_document(self) -> None:
        # A shape-valid row is not proof that the referenced result exists or
        # that a worker/inline decision is authorized. Runtime gates still own it.
        doc = confirmation(execution_row(execution_mode="worker"))
        before = copy.deepcopy(doc)
        self.assert_valid(doc)
        self.assertEqual(before, doc)


if __name__ == "__main__":
    unittest.main()
