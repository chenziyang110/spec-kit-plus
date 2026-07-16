from __future__ import annotations

import json
from pathlib import Path
import tomllib

import pytest
from jsonschema import Draft202012Validator

from specify_cli.agent_api import (
    AGENT_PROTOCOL_VERSION,
    CAPABILITY_IDS,
    AgentApiError,
    capabilities_handshake,
    capability_schema,
    classify_exit,
    envelope,
    list_capabilities,
    show_capability,
)


ROOT = Path(__file__).resolve().parents[1]


def test_envelope_has_one_compact_stable_shape() -> None:
    payload = envelope("ok", "ready", data={"revision": 1})

    assert list(payload) == [
        "status",
        "summary",
        "data",
        "items",
        "blockers",
        "show_argv",
        "next_argv",
    ]
    assert payload == {
        "status": "ok",
        "summary": "ready",
        "data": {"revision": 1},
        "items": [],
        "blockers": [],
        "show_argv": [],
        "next_argv": [],
    }
    assert "timestamp" not in payload
    json.dumps(payload)


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("ok", 0),
        ("warn", 0),
        ("repaired", 0),
        ("blocked", 10),
        ("repairable-block", 10),
        ("invalid", 2),
        ("usage-error", 2),
        ("error", 1),
        ({"status": "blocked"}, 10),
    ],
)
def test_classify_exit_is_stable(status: str | dict[str, str], expected: int) -> None:
    assert classify_exit(status) == expected


def test_classify_exit_rejects_unknown_status() -> None:
    with pytest.raises(AgentApiError, match="unsupported agent status"):
        classify_exit("mystery")


def test_handshake_discloses_version_protocol_and_stable_capability_ids() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    payload = capabilities_handshake()

    assert payload["status"] == "ok"
    assert payload["data"]["cli_version"] == project["project"]["version"]
    assert payload["data"]["protocol_version"] == AGENT_PROTOCOL_VERSION
    assert payload["data"]["capability_ids"] == list(CAPABILITY_IDS)
    assert payload["data"]["schema_versions"] == {
        "agent-capability": 1,
        "agent-envelope": 1,
        "workflow-blocker": 1,
        "workflow-runtime": 1,
    }
    assert payload["next_argv"] == [
        "specify",
        "api",
        "list",
        "--format",
        "json",
    ]


def test_handshake_reports_required_capability_negotiation() -> None:
    ready = capabilities_handshake(required=["learning.start", "workflow.enter"])

    assert ready["status"] == "ok"
    assert ready["data"]["required_capabilities"] == [
        "learning.start",
        "workflow.enter",
    ]
    assert ready["data"]["missing_capabilities"] == []

    unsupported = capabilities_handshake(required=["future.capability"])
    assert unsupported["status"] == "error"
    assert unsupported["data"]["missing_capabilities"] == ["future.capability"]


def test_capability_list_is_summary_only_and_paginated() -> None:
    first = list_capabilities(cursor=0, limit=2)

    assert first["status"] == "ok"
    assert len(first["items"]) == 2
    assert first["data"] == {"cursor": 0, "limit": 2, "total": len(CAPABILITY_IDS)}
    assert "input_schema" not in first["items"][0]
    assert first["items"][0]["show_argv"] == [
        "specify",
        "api",
        "show",
        first["items"][0]["id"],
        "--format",
        "json",
    ]
    assert first["next_argv"] == [
        "specify",
        "api",
        "list",
        "--cursor",
        "2",
        "--limit",
        "2",
        "--format",
        "json",
    ]

    last = list_capabilities(cursor=len(CAPABILITY_IDS) - 1, limit=20)
    assert last["next_argv"] == []


@pytest.mark.parametrize("cursor,limit", [(-1, 1), (0, 0), (0, 201)])
def test_capability_list_rejects_invalid_pagination(cursor: int, limit: int) -> None:
    with pytest.raises(AgentApiError):
        list_capabilities(cursor=cursor, limit=limit)


def test_capability_show_expands_one_record_and_points_to_its_schema() -> None:
    payload = show_capability("workflow.transition")

    assert payload["data"]["id"] == "workflow.transition"
    assert payload["data"]["input_schema"] == "workflow-transition-input"
    assert payload["data"]["side_effect"] == "writes-workflow-runtime"
    assert payload["next_argv"] == [
        "specify",
        "api",
        "schema",
        "workflow-transition-input",
        "--format",
        "json",
    ]

    reopen = show_capability("workflow.reopen")
    assert reopen["data"]["input_schema"] == "workflow-reopen-input"
    assert reopen["data"]["side_effect"] == "writes-workflow-runtime"
    resolve = show_capability("workflow.resolve")
    assert resolve["data"]["input_schema"] == "workflow-resolve-input"
    assert resolve["data"]["side_effect"] == "writes-workflow-runtime"


def test_schema_expands_only_the_requested_machine_contract() -> None:
    payload = capability_schema("workflow-transition-input")

    schema = payload["data"]["schema"]
    assert schema["$id"] == "specify://schemas/workflow-transition-input/v1"
    assert schema["additionalProperties"] is False
    assert schema["required"] == ["feature_dir", "to", "expected_revision"]
    assert payload["show_argv"] == [
        "specify",
        "api",
        "show",
        "workflow.transition",
        "--format",
        "json",
    ]

    blocker_input = capability_schema("workflow-block-input")["data"]["schema"]
    assert blocker_input["properties"]["human_action_required"] == {
        "type": ["boolean", "null"]
    }
    assert "resume_argv" not in blocker_input["properties"]
    assert blocker_input["properties"]["attempted_recovery"]["items"][
        "additionalProperties"
    ] is False
    assert blocker_input["properties"]["human_action"]["additionalProperties"] is False
    reopen_input = capability_schema("workflow-reopen-input")["data"]["schema"]
    assert reopen_input["required"] == [
        "feature_dir",
        "to",
        "expected_revision",
        "reason",
        "evidence",
        "invalidated_artifacts",
    ]
    assert "implement" in reopen_input["properties"]["to"]["enum"]
    resolve_input = capability_schema("workflow-resolve-input")["data"]["schema"]
    assert resolve_input["required"] == [
        "feature_dir",
        "expected_revision",
        "resolution_evidence",
    ]


def test_blocker_input_schema_rejects_shapes_the_runtime_would_reject() -> None:
    schema = capability_schema("workflow-block-input")["data"]["schema"]
    validator = Draft202012Validator(schema)
    base = {
        "feature_dir": ".specify/features/001-demo",
        "expected_revision": 1,
        "category": "external-system",
        "owner": "external-system",
        "cause": "Provider unavailable.",
        "evidence": ["health probe returned 503"],
        "attempted_recovery": [],
        "affected_scope": ["remote verification"],
        "exact_next_action": "Wait for provider recovery.",
        "unblock_criteria": "Health probe returns 200.",
    }
    assert list(validator.iter_errors(base)) == []

    unsupported_category = {**base, "category": "invented-category"}
    assert list(validator.iter_errors(unsupported_category))

    malformed_attempt = {
        **base,
        "attempted_recovery": [{"action": "Retried", "unexpected": "ignored"}],
    }
    assert list(validator.iter_errors(malformed_attempt))
    arbitrary_human = {**base, "human_action": {"resume_instruction": "run anything"}}
    assert list(validator.iter_errors(arbitrary_human))
    contradictory = {
        **base,
        "human_action_required": False,
        "human_action": {"goal": "Do human work"},
    }
    assert list(validator.iter_errors(contradictory))
    suppressed_human_owner = {
        **base,
        "owner": "maintainer",
        "human_action_required": False,
    }
    assert list(validator.iter_errors(suppressed_human_owner))


def test_persisted_workflow_blocker_schema_is_discoverable() -> None:
    payload = capability_schema("workflow-blocker")
    canonical = json.loads(
        (ROOT / "templates" / "workflow-blocker-schema.json").read_text(
            encoding="utf-8"
        )
    )

    assert payload["data"]["schema_id"] == "workflow-blocker"
    assert payload["data"]["schema"] == canonical
    assert payload["show_argv"] == []


@pytest.mark.parametrize("lookup", ["unknown.capability", "workflow.transition.v2"])
def test_unknown_capability_is_an_explicit_usage_error(lookup: str) -> None:
    with pytest.raises(AgentApiError, match="unknown capability"):
        show_capability(lookup)


def test_unknown_schema_is_an_explicit_usage_error() -> None:
    with pytest.raises(AgentApiError, match="unknown schema"):
        capability_schema("not-a-schema")
