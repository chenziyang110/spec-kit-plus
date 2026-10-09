"""Consume real E2E runtime packets through the shared Python worker contract.

This is a CLI/contract integration fixture, not product E2E acceptance or native
subagent execution. The Go behavior suite covers the full dependency lifecycle.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from specify_cli.execution.packet_schema import worker_task_packet_from_json
from specify_cli.execution.packet_validator import validate_worker_task_packet


def invoke(binary: Path, *args: str) -> dict:
    result = subprocess.run(
        [str(binary), *args, "--format", "json"],
        capture_output=True, text=True, timeout=20, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def consume_bound_packet(project: Path, data: dict):
    binding = data["worker_task_packet_binding"]
    raw = (project / binding["artifact_ref"]).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == binding["artifact_sha256"]
    assert binding["json_pointer"] == "/worker_task_packet"
    assert json.loads(raw)["worker_task_packet"] == data["worker_task_packet"]
    return worker_task_packet_from_json(json.dumps(data["worker_task_packet"]))


@pytest.mark.parametrize("with_file_input", [True, False])
def test_real_worker_and_review_packets_use_existing_consumer(built_unified_runtime: Path, tmp_path: Path, with_file_input: bool):
    binary, project = built_unified_runtime, tmp_path
    (project / "request.md").write_text("Compile and consume the complete E2E worker contract.\n")
    packed = invoke(binary, "api", "pack", "--capabilities", "e2e.init", "--include-schema")
    plan = packed["items"][0]["schema"]["examples"][0]
    plan["scope"][0]["operation"] = "Compile the shared worker packet"
    plan["tasks"][0]["acceptance"][0]["criterion"] = "The stage fixture records all packet inputs."
    if not with_file_input:
        plan["tasks"][0]["inputs"] = []
    common = ("--project-root", str(project), "--run-id", "packet-consumer")
    initialized = invoke(binary, "e2e", "init", *common, "--leader-id", "leader",
                         "--input-json", json.dumps(plan))["data"]
    started = invoke(binary, "e2e", "task-start", *common, "--task-id", "S1",
                     "--worker-id", "worker", "--expected-revision", str(initialized["revision"]))["data"]
    packet = consume_bound_packet(project, started)
    assert validate_worker_task_packet(packet) is packet
    assert packet.task_id == "S1"
    assert packet.feature_id == packet.story_id == ""
    assert "packet-consumer" in packet.objective
    assert packet.scope.read_scope == packet.interfaces.consumes
    assert ("request.md" in packet.scope.read_scope) is with_file_input
    assert any("/snapshots/" in path for path in packet.scope.read_scope)
    assert packet.scope.write_scope == packet.interfaces.produces == plan["tasks"][0]["outputs"]
    assert packet.context_bundle and packet.required_references
    assert packet.hard_rules and packet.done_criteria and packet.handoff_requirements
    assert packet.dispatch_policy.mode == "hard_fail"

    output = project / packet.scope.write_scope[0]
    output.parent.mkdir(parents=True)
    output.write_text("Stage fixture records the complete declared packet contract.\n")
    evidence = project / "fixture-evidence.txt"
    evidence.write_text("Inspected the stage fixture and its request input.\n")
    submitted = started["submission_template"]
    submitted["outcome"] = "pass"
    submitted["worker_result"] = {
        "task_id": "S1", "packet_id": started["packet_sha256"],
        "status": "success", "summary": "The synthetic stage fixture is available.",
    }
    for row in submitted["checks"]:
        row.update(status="passed", actual="The stage fixture identifies its complete declared contract.",
                   reproduction="Read the frozen task contract and tests/e2e/stage-1.md.",
                   preconditions="An isolated CLI contract fixture, with no product or external side effects.",
                   evidence_refs=["fixture-evidence.txt"])
    result = invoke(binary, "e2e", "task-submit", *common, "--task-id", "S1", "--worker-id", "worker",
                    "--expected-revision", str(started["revision"]), "--result-json", json.dumps(submitted))["data"]
    review = invoke(binary, "e2e", "review-start", *common, "--task-id", "S1", "--validator-id", "reviewer",
                    "--expected-revision", str(result["revision"]))["data"]
    reviewer = consume_bound_packet(project, review)
    assert validate_worker_task_packet(reviewer, read_only_review=True) is reviewer
    assert reviewer.task_id == "S1"
    assert reviewer.agent_role == "independent-validator"
    assert reviewer.scope.write_scope == reviewer.interfaces.produces == []
    assert result["submission_ref"] in reviewer.scope.read_scope
    assert started["packet_ref"] in reviewer.scope.read_scope
    assert any("/blobs/" in path for path in reviewer.scope.read_scope)
    assert reviewer.done_criteria == packet.done_criteria
    assert reviewer.scope.read_scope == reviewer.interfaces.consumes
