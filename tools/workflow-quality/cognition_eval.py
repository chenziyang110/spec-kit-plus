"""Evaluate frozen Cognition task observations without inventing model telemetry.

The evaluator consumes evidence; it neither runs an Agent nor authenticates one.
Native runtime replay and actual Agent observations have separate denominators.
An independent, source-bound gold file is required. Missing rows remain explicit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any

SCHEMA = "cognition-eval.v1"
PROFILES = ("classic", "advanced")
CONDITIONS = ("first", "repeat", "variant", "source_changed")
FAMILIES = ("locate", "explain", "debug", "build_package", "test_entry")
KINDS = ("native_runtime_replay", "actual_agent_observation")
NEGATIVES = ("target_directory_changed", "generation_changed", "claim_revision_changed", "permissions_changed", "constraints_changed")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load(path: Path) -> Any:
    def nonfinite(value: str) -> None:
        raise ValueError(f"non-finite JSON value: {value}")

    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=_object, parse_constant=nonfinite)


def write_new(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as output:
        json.dump(value, output, ensure_ascii=False, indent=2, allow_nan=False)
        output.write("\n")


def require_hash(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{label}: expected SHA-256")
    return value


def require_navigation_digest(value: Any) -> str:
    """Runtime navigation identities have a prefix; artifact hashes never do."""
    if not isinstance(value, str) or not value.startswith("sha256:"):
        raise ValueError("original navigation snapshot: expected sha256:<64 lowercase hex>")
    require_hash(value[7:], "original navigation snapshot")
    return value


def artifact(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not isinstance(value.get("path"), str):
        raise ValueError(f"{label}: expected path/digest evidence")
    path = Path(value["path"])
    expected = require_hash(value.get("sha256"), label)
    if not path.is_file() or digest(path) != expected:
        raise ValueError(f"{label}: missing or changed evidence: {path}")
    if value.get("bytes") != path.stat().st_size:
        raise ValueError(f"{label}: byte count differs from evidence")
    return value


def binding(path: Path) -> dict[str, Any]:
    return {"path": str(path.resolve()), "sha256": digest(path), "bytes": path.stat().st_size}


def validate_task_binding(record: dict[str, Any], plan_path: Path, plan: dict[str, Any]) -> dict[str, Any]:
    """Bind observations to the real target and complete frozen task context."""
    packet_ref = artifact(record.get("task_packet"), "observation task packet")
    packet = load(Path(packet_ref["path"]))
    if packet.get("schema") != "cognition-eval-task-packet.v2" or packet.get("plan_sha256") != digest(plan_path):
        raise ValueError("observation task packet is not the current frozen contract")
    for field in ("slot", "phase", "project_root", "runtime", "source_manifest", "phase_source_manifest", "source_change", "semantic_contract", "permission_contract"):
        if field not in packet or record.get(field) != packet[field]:
            raise ValueError(f"observation changed task packet {field}")
    if packet.get("environment_sha256") != plan["environment"]["sha256"] or packet.get("gold_sha256") != plan["gold"]["sha256"]:
        raise ValueError("task packet changed the frozen environment or gold")
    semantic = record.get("semantic_contract")
    if not isinstance(semantic, dict) or set(semantic) != {"query", "intent", "scope_id", "required_facets", "negative_constraints"}:
        raise ValueError("exact query/intent/scope/facets/negative constraints are required")
    if semantic["query"] != packet.get("query") or semantic["intent"] != packet.get("intent"):
        raise ValueError("task query or intent differs from semantic context")
    target = Path(record["project_root"])
    if not target.is_dir() or str(target.resolve()) != record["project_root"]:
        raise ValueError("task target is missing, relative or redirected")
    source_manifest = artifact(record["source_manifest"], "task source manifest")
    for entry in load(Path(source_manifest["path"])):
        source_path = entry.get("source_path")
        if not isinstance(source_path, str) or Path(source_path).is_absolute() or ".." in Path(source_path).parts:
            raise ValueError("source input path escapes task target")
        expected = target / source_path
        actual = Path(entry["path"])
        if actual.resolve() != expected.resolve() or not actual.resolve().is_relative_to(target.resolve()):
            raise ValueError("source input belongs to another target or redirects outside it")
    return packet


def validate_reuse_context(previous: dict[str, Any], current: dict[str, Any]) -> None:
    for field in ("plan_sha256", "gold_sha256", "environment_sha256", "phase", "project_root", "runtime", "source_manifest", "phase_source_manifest", "semantic_contract", "permission_contract"):
        if previous.get(field) != current.get(field):
            raise ValueError(f"reused intake changed {field}")
    previous_slot = previous.get("slot", "").split("/")
    current_slot = current.get("slot", "").split("/")
    if len(previous_slot) != 4 or len(current_slot) != 4 or previous_slot[:2] != current_slot[:2] or previous_slot[-1] != current_slot[-1]:
        raise ValueError("reused intake changed profile, task family or independent round")
    if current_slot[2] not in ("repeat", "variant"):
        raise ValueError("changed task condition cannot reuse previous intake")


def runtime_payload(call: dict[str, Any]) -> dict[str, Any]:
    artifact(call.get("stdout"), "runtime owner stdout")
    artifact(call.get("stderr"), "runtime owner stderr")
    result = load(Path(call["stdout"]["path"]))
    if not isinstance(result, dict):
        raise ValueError("runtime owner did not return an object")
    return result.get("data", result)


def original_compass(record: dict[str, Any], *, seen: set[str] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Follow bound reuse evidence until a real, recorded Compass call exists."""
    visited = set() if seen is None else seen
    for call in reversed(record.get("tool_calls", [])):
        argv = call.get("argv", [])
        if len(argv) >= 3 and argv[1:3] == ["cognition", "compass"]:
            if call.get("exit_code") != 0:
                raise ValueError("original Compass call failed")
            if argv[0] != record.get("runtime", {}).get("path") or call.get("cwd") != record.get("project_root"):
                raise ValueError("original Compass call belongs to a different runtime or target")
            return runtime_payload(call), call
    reference = artifact(record.get("reuse_intake"), "original intake basis")
    if reference["sha256"] in visited or len(visited) >= 8:
        raise ValueError("cyclic or unbounded intake reuse evidence")
    visited.add(reference["sha256"])
    previous = load(Path(reference["path"]))
    validate_reuse_context(previous, record)
    payload, call = original_compass(previous, seen=visited)
    validate_runtime_guard(record, payload)
    return payload, call


def validate_runtime_reuse(record: dict[str, Any], previous: dict[str, Any]) -> None:
    validate_reuse_context(previous, record)
    payload, _ = original_compass(previous)
    validate_runtime_guard(record, payload)


def validate_runtime_guard(record: dict[str, Any], payload: dict[str, Any]) -> None:
    ref = payload.get("expansion_ref", {})
    if ref.get("expansion_contract_version") != 2:
        raise ValueError("original runtime lacks same-generation snapshot reuse support")
    require_navigation_digest(ref.get("navigation_digest"))
    if any(not isinstance(ref.get(field), str) or not ref[field] for field in ("id", "active_generation_id", "query_fingerprint")):
        raise ValueError("original snapshot lacks a complete navigation identity")
    guard = record.get("reuse_runtime_guard")
    if not isinstance(guard, dict) or guard not in record.get("tool_calls", []):
        raise ValueError("reuse requires a recorded current runtime-owner Expand check")
    expected = [record["runtime"]["path"], "cognition", "expand", "--id", ref.get("id"), "--section", "related_paths", "--format", "json"]
    if guard.get("argv") != expected or guard.get("cwd") != record["project_root"] or guard.get("exit_code") != 0:
        raise ValueError("runtime reuse check changed its exact target/reference")
    current = runtime_payload(guard)
    if current.get("status") != "ok" or current.get("readiness") not in ("query_ready", "review") or current.get("expansion_contract_version") != 2:
        raise ValueError("runtime refused snapshot/status freshness for reused intake")
    epistemic = current.get("epistemic_contract", {})
    for field, expected_value in {"contract_version": 1, "graph_role": "route_candidate_only", "fact_source_of_truth": "live_repository", "live_verification_required": True, "graph_only_claims_allowed": False, "unverified_claim_action": "withhold"}.items():
        if (epistemic.get(field) is not expected_value) if isinstance(expected_value, bool) else (epistemic.get(field) != expected_value):
            raise ValueError("runtime reuse check lost its advisory epistemic contract")
    for field in ("id", "active_generation_id", "query_fingerprint"):
        if current.get(field) != ref.get(field):
            raise ValueError(f"runtime reuse check changed {field}")


def slots() -> list[str]:
    return [f"{profile}/{family}/{condition}/{round_number}" for profile in PROFILES for family in FAMILIES for condition in CONDITIONS for round_number in (1, 2, 3)]


def validate_gold(gold: Any, tasks_path: Path) -> dict[str, Any]:
    if not isinstance(gold, dict) or gold.get("schema") != "cognition-eval-gold.v1" or gold.get("status") != "accepted":
        raise ValueError("independent gold is not accepted")
    tasks = load(tasks_path)
    if not gold.get("reviewer") or gold["reviewer"] == tasks.get("author"):
        raise ValueError("gold reviewer must be separate from task author")
    if gold.get("tasks_sha256") != digest(tasks_path):
        raise ValueError("gold refers to a different task packet")
    by_family = {task["family"]: task for task in gold.get("tasks", [])}
    if len(gold.get("tasks", [])) != 5 or set(by_family) != set(FAMILIES):
        raise ValueError("gold must cover exactly the five requested task families")
    for family, task in by_family.items():
        for field in ("owners", "consumers", "verification", "negative_paths", "evidence"):
            if not isinstance(task.get(field), list) or not task[field]:
                raise ValueError(f"gold {family}: missing {field}")
        evidence_paths = set()
        for index, entry in enumerate(task["evidence"]):
            artifact(entry, f"gold {family} evidence {index}")
            evidence_paths.add(entry.get("source_path"))
        expected_paths = set(task["owners"] + task["consumers"] + task["verification"] + task["negative_paths"])
        if not expected_paths.issubset(evidence_paths):
            raise ValueError(f"gold {family}: facts lack live source bindings")
    return by_family


def freeze(tasks_path: Path, gold_path: Path, environment_path: Path, runtime_path: Path, source_manifest_path: Path) -> dict[str, Any]:
    validate_gold(load(gold_path), tasks_path)
    manifest = load(source_manifest_path)
    if not isinstance(manifest, list) or not manifest:
        raise ValueError("source manifest must contain bound source inputs")
    for index, entry in enumerate(manifest):
        artifact(entry, f"source input {index}")
    environment = load(environment_path)
    for field in ("platform", "hardware", "model", "model_config", "permissions", "cold_warm_policy"):
        if field not in environment:
            raise ValueError(f"environment missing {field}")
    return {"schema": "cognition-eval-plan.v1", "observation_contract_version": 2, "reuse_contract_version": 2, "tasks": binding(tasks_path), "gold": binding(gold_path), "environment": binding(environment_path), "baseline_runtime": binding(runtime_path), "baseline_source_manifest": binding(source_manifest_path), "required_slots": slots(), "required_actual_observations": 120, "per_profile": 60, "negative_conditions": list(NEGATIVES), "model_tokens": {"status": "unavailable", "reason": "Only real native telemetry can supply model tokens"}, "boundaries": ["Graph contents are advisory; gold facts come from live source reviewed independently", "Each repeat round is independent; first/repeat/variant ordering is recorded", "OS caches are not cleared; first means task-session cold, never hardware-cache cold", "Native replay cannot count as actual Agent observations", "Three rounds do not support P95", "Evidence IDs and hashes establish consistency, not process authentication", "Reuse needs exact target/query/intent/scope/constraints plus a current runtime-owner snapshot check; old runtimes refresh instead"]}


def validate_phase_mapping(before: dict[str, Any], after: dict[str, Any]) -> None:
    if after.get("phase") != "after" or after.get("tasks_sha256") != before.get("tasks_sha256"):
        raise ValueError("after gold must preserve the original logical tasks and declare its phase")
    before_tasks = {task["family"]: task for task in before["tasks"]}
    after_tasks = {task["family"]: task for task in after["tasks"]}
    rows = after.get("logical_role_mapping", [])
    expected = {(family, role) for family in FAMILIES for role in ("owners", "consumers", "verification", "negative_paths")}
    if len(rows) != 20 or {(row.get("family"), row.get("role")) for row in rows} != expected:
        raise ValueError("after gold requires all original twenty logical role mappings")
    for row in rows:
        family, role = row["family"], row["role"]
        if set(row.get("before_paths", [])) != set(before_tasks[family][role]) or set(row.get("after_paths", [])) != set(after_tasks[family][role]) or not row.get("criterion"):
            raise ValueError("after gold silently changes or drops a logical role mapping")


def freeze_after(before_plan_path: Path, gold_path: Path, runtime_path: Path, source_manifest_path: Path) -> dict[str, Any]:
    before_plan = load(before_plan_path)
    if before_plan.get("schema") != "cognition-eval-plan.v1" or before_plan.get("required_slots") != slots() or before_plan.get("phase", "before") != "before":
        raise ValueError("before plan is not the original complete phase contract")
    for field in ("tasks", "gold", "environment", "baseline_runtime", "baseline_source_manifest"):
        artifact(before_plan[field], f"before plan {field}")
    before_gold = load(Path(before_plan["gold"]["path"]))
    after_gold = load(gold_path)
    if artifact(after_gold.get("before_gold"), "after gold original binding") != before_plan["gold"]:
        raise ValueError("after gold refers to a different original ground truth")
    validate_phase_mapping(before_gold, after_gold)
    result = freeze(Path(before_plan["tasks"]["path"]), gold_path, Path(before_plan["environment"]["path"]), runtime_path, source_manifest_path)
    originals = {entry["source_path"] for entry in load(Path(before_plan["baseline_source_manifest"]["path"]))}
    current = {entry["source_path"] for entry in load(source_manifest_path)}
    if not originals.issubset(current):
        raise ValueError("after source boundary dropped original task paths")
    required = {entry["source_path"] for task in after_gold["tasks"] for entry in task["evidence"]}
    if not required.issubset(current):
        raise ValueError("after source boundary misses necessary current gold dependencies")
    result.update(phase="after", before_plan=binding(before_plan_path), comparison_contract="same120slots_same20logicalroles_phase_specific_source_facts")
    result["boundaries"].extend(["After ground truth follows current physical owners; original logical tasks/roles and BEFORE artifacts remain unchanged", "Learning applicability is separate from the graph snapshot; owning intake repeats when unchanged lesson/index/source/rules cannot be proven", "Separate source_changed project retains the original target-directory confound; no pure source-change causal claim"])
    return result


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{label}: expected finite non-negative number")
    return float(value)


def validate_record(record: Any, plan_path: Path, plan: dict[str, Any], gold: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(record, dict) or record.get("schema") != "cognition-eval-observation.v1":
        raise ValueError("invalid observation schema")
    if record.get("kind") not in KINDS or record.get("phase") not in ("before", "after"):
        raise ValueError("observation requires explicit kind and phase")
    if record.get("slot") not in plan["required_slots"] or not record.get("run_id"):
        raise ValueError("invalid matrix slot or missing run ID")
    if record.get("plan_sha256") != digest(plan_path) or record.get("gold_sha256") != plan["gold"]["sha256"]:
        raise ValueError("observation belongs to a different frozen contract")
    if record.get("environment_sha256") != plan["environment"]["sha256"]:
        raise ValueError("model/config/permission/environment differs from packet")
    if record["phase"] != plan.get("phase", "before"):
        raise ValueError("observation belongs to a different phase plan")
    validate_task_binding(record, plan_path, plan)
    artifact(record.get("runtime"), "observation runtime")
    artifact(record.get("source_manifest"), "observation source manifest")
    source_inputs = load(Path(record["source_manifest"]["path"]))
    source_by_path = {entry.get("source_path"): entry for entry in source_inputs}
    if len(source_by_path) != len(source_inputs) or None in source_by_path:
        raise ValueError("source input paths must be explicit and unique")
    for index, entry in enumerate(source_inputs):
        artifact(entry, f"observation source {index}")
    phase_manifest = artifact(record.get("phase_source_manifest"), "phase original source inputs")
    if phase_manifest["sha256"] != plan["baseline_source_manifest"]["sha256"]:
        raise ValueError("phase changed its frozen original source")
    phase_inputs = load(Path(phase_manifest["path"]))
    phase_by_path = {entry.get("source_path"): entry for entry in phase_inputs}
    if len(phase_by_path) != len(phase_inputs) or set(phase_by_path) != set(source_by_path):
        raise ValueError("observation dropped or added undeclared phase source inputs")
    for entry in phase_inputs:
        artifact(entry, "phase original source")
    if record["runtime"]["sha256"] != plan["baseline_runtime"]["sha256"]:
        raise ValueError("phase observation changed baseline runtime")
    profile, family, condition, round_number = record["slot"].split("/")
    if record.get("condition_order") != CONDITIONS.index(condition) + 1:
        raise ValueError("condition ordering must remain explicit")
    if record.get("independent_round") != int(round_number):
        raise ValueError("observation round binding differs")
    if condition == "source_changed":
        change = record.get("source_change")
        if not isinstance(change, dict) or change.get("before_sha256") == change.get("after_sha256"):
            raise ValueError("source change requires exact different content digests")
        require_hash(change.get("before_sha256"), "source change before")
        require_hash(change.get("after_sha256"), "source change after")
        before = artifact(change.get("before"), "source change original basis")
        after = artifact(change.get("after"), "source change current basis")
        changed_path = change.get("path")
        current = source_by_path.get(changed_path)
        original = phase_by_path.get(changed_path)
        if current is None or original is None or change["after_sha256"] != current["sha256"] or after["sha256"] != current["sha256"] or change["before_sha256"] != original["sha256"] or before["sha256"] != original["sha256"] or Path(after["path"]).resolve() != Path(current["path"]).resolve() or Path(before["path"]).resolve() != Path(original["path"]).resolve():
            raise ValueError("declared source change does not match exact original/current source inputs")
    elif record.get("source_change") is not None:
        raise ValueError("unchanged condition cannot silently change source")
    declared_change = record.get("source_change", {}).get("path") if record.get("source_change") else None
    actual_changes = {path for path, entry in source_by_path.items() if entry["sha256"] != phase_by_path[path]["sha256"]}
    if actual_changes != ({declared_change} if declared_change else set()):
        raise ValueError("condition source changes differ from exact frozen phase inputs")
    traces = record.get("tool_calls")
    if not isinstance(traces, list):
        raise ValueError("tool-call records must be explicit")
    if not traces:
        raise ValueError("zero-call intake reuse cannot prove current runtime snapshot/status")
    if record.get("reuse_intake"):
        previous = load(Path(artifact(record["reuse_intake"], "reused intake")["path"]))
        validate_runtime_reuse(record, previous)
        if record["phase"] == "after":
            family = record["slot"].split("/")[1]
            expected_learning = [record["runtime"]["path"], "learning", "start", "--command", "sp-ask", "--context", f"component={family}", "--format", "json"]
            learning_calls = [call for call in traces if call.get("argv") == expected_learning and call.get("cwd") == record["project_root"] and call.get("exit_code") == 0]
            if record.get("learning_reuse", {}).get("outcome") != "not_granted_refreshed" or not learning_calls:
                raise ValueError("graph snapshot does not prove Learning applicability; current owning intake required")
            learning = runtime_payload(learning_calls[-1])
            if learning.get("read_only") is not True or learning.get("command") != "sp-ask" or learning.get("schema_version") != 1 or learning.get("task_context", {}).get("components") != [family]:
                raise ValueError("current Learning owner did not return the required read-only task intake")
    for index, call in enumerate(traces):
        if not isinstance(call.get("argv"), list) or not call["argv"] or not call.get("cwd") or not isinstance(call.get("exit_code"), int):
            raise ValueError(f"tool call {index}: missing native invocation")
        artifact(call.get("stdout"), f"tool call {index} stdout")
        artifact(call.get("stderr"), f"tool call {index} stderr")
        _number(call.get("elapsed_ms"), f"tool call {index} time")
    reads = record.get("source_reads")
    if not isinstance(reads, list):
        raise ValueError("source reads must be explicit")
    for index, read in enumerate(reads):
        artifact(read.get("evidence"), f"source read {index}")
        if not read.get("source_path") or read.get("mode") not in ("full", "bounded", "reuse_verified"):
            raise ValueError("source read requires path and full/bounded/reused classification")
        source = source_by_path.get(read["source_path"])
        if source is None:
            raise ValueError("source read names a path outside the actual input manifest")
        content = Path(source["path"]).read_bytes()
        content_mode = read["mode"]
        if read["mode"] == "reuse_verified":
            prior_evidence = artifact(read.get("reused_from"), "source reuse basis")
            previous = load(Path(prior_evidence["path"]))
            validate_reuse_context(previous, record)
            if not any(r["source_path"] == read["source_path"] and r["evidence"] == read["evidence"] and r.get("source_sha256") == source["sha256"] for r in previous.get("source_reads", [])):
                raise ValueError("source reuse has no current matching read basis")
            content_mode = read.get("reused_mode")
            if content_mode not in ("full", "bounded"):
                raise ValueError("source reuse requires its original full/bounded mode")
        if content_mode == "bounded":
            line_number, line_count = read.get("start_line"), read.get("line_count")
            if not isinstance(line_number, int) or line_number < 1 or not isinstance(line_count, int) or line_count < 1:
                raise ValueError("bounded source read needs exact positive line range")
            content = b"".join(content.splitlines(keepends=True)[line_number - 1:][:line_count])
        if not content or hashlib.sha256(content).hexdigest() != read["evidence"]["sha256"]:
            raise ValueError("source read artifact does not match the claimed current source")
    decision = record.get("decision")
    if not isinstance(decision, dict):
        raise ValueError("observation needs an inspectable decision")
    for field in ("owners", "consumers", "verification", "rejected_paths"):
        if not isinstance(decision.get(field), list) or any(not isinstance(p, str) for p in decision[field]):
            raise ValueError(f"decision missing {field}")
    if record["kind"] == "actual_agent_observation":
        identity = record.get("agent")
        if not isinstance(identity, dict) or not identity.get("task_id") or not identity.get("turn_id") or not identity.get("model_config"):
            raise ValueError("actual Agent observation needs a real task/turn/model configuration identity")
        artifact(record.get("agent_decision_evidence"), "agent decision evidence")
        if load(Path(record["agent_decision_evidence"]["path"])) != decision:
            raise ValueError("Agent decision differs from original recorded decision artifact")
    elif record.get("replay_decision_evidence"):
        replay = artifact(record["replay_decision_evidence"], "native replay decision evidence")
        if load(Path(replay["path"])) != decision:
            raise ValueError("native replay decision differs from its original artifact")
    for field in ("first_confirmed_owner_ms", "total_ms"):
        _number(record.get(field), field)
    tokens = record.get("model_tokens")
    if not isinstance(tokens, dict) or tokens.get("status") not in ("unavailable", "native_telemetry"):
        raise ValueError("model token availability must be explicit")
    if tokens["status"] == "native_telemetry":
        artifact(tokens.get("evidence"), "native token telemetry")
        for field in ("input", "output"):
            _number(tokens.get(field), f"native tokens {field}")
    if record["kind"] == "native_runtime_replay" and tokens["status"] != "unavailable":
        raise ValueError("runtime replay cannot provide model tokens")
    expected = gold[family]
    confirmations = record.get("owner_confirmations", [])
    for confirmation in confirmations:
        artifact(confirmation.get("event_evidence"), "owner confirmation event")
        original = load(Path(confirmation["event_evidence"]["path"]))
        if {k: v for k, v in confirmation.items() if k != "event_evidence"} != original:
            raise ValueError("owner confirmation changed after recording")
        for field in ("run_id", "slot", "task_packet", "started_at_ns"):
            if confirmation.get(field) != record.get(field):
                raise ValueError(f"owner confirmation belongs to another episode: {field}")
        _number(confirmation.get("elapsed_ms"), "owner confirmation time")
        if confirmation["elapsed_ms"] > record["total_ms"] or not any(r["source_path"] == confirmation["chosen_owner"] and r["evidence"] == confirmation["source_read_evidence"] for r in reads):
            raise ValueError("owner confirmation lacks a preceding inspected source basis")
    correct_confirmations = [c for c in confirmations if c["chosen_owner"] in expected["owners"]]
    first_confirmed = min(c["elapsed_ms"] for c in correct_confirmations) if correct_confirmations else None
    missing_confirm = record["kind"] == "actual_agent_observation" and first_confirmed is None
    covered = {field: sorted(set(decision[field]) & set(expected[field])) for field in ("owners", "consumers", "verification")}
    missing = {field: sorted(set(expected[field]) - set(decision[field])) for field in covered}
    unread = sorted(set(expected["owners"] + expected["consumers"] + expected["verification"] + expected["negative_paths"]) - {read["source_path"] for read in reads})
    wrong = sorted(set(decision["owners"]) & set(expected["negative_paths"]))
    rejected = sorted(set(decision["rejected_paths"]) & set(expected["negative_paths"]))
    actual_reads = [r for r in reads if r["mode"] != "reuse_verified"]
    return {"run_id": record["run_id"], "slot": record["slot"], "profile": profile, "family": family, "kind": record["kind"], "phase": record["phase"], "covered": covered, "missing": missing, "required_live_read_gaps": unread, "wrong_owner_paths": wrong, "negative_routes_rejected": rejected, "missing_confirmed_owner_event": missing_confirm, "fact_acceptance": "pass" if not any(missing.values()) and not unread and not wrong and not missing_confirm and set(rejected) == set(expected["negative_paths"]) else "fail", "metrics": {"first_confirmed_owner_ms": first_confirmed, "total_ms": record["total_ms"], "tool_calls": len(traces), "compass_calls": sum(call["argv"].count("compass") > 0 for call in traces), "learning_calls": sum("learning" in call["argv"] for call in traces), "catalog_calls": sum("catalog" in call["argv"] for call in traces), "query_calls": sum("query" in call["argv"] for call in traces), "expand_calls": sum("expand" in call["argv"] for call in traces), "source_reads": len(actual_reads), "source_revalidations": len(reads) - len(actual_reads), "repeated_source_reads": len(actual_reads) - len({r["source_path"] for r in actual_reads}), "cli_argv_utf8_bytes": sum(len(json.dumps(call["argv"], ensure_ascii=False).encode("utf-8")) for call in traces), "stdout_bytes": sum(call["stdout"]["bytes"] for call in traces), "stderr_bytes": sum(call["stderr"]["bytes"] for call in traces), "source_read_bytes": sum(read["evidence"]["bytes"] for read in actual_reads), "model_tokens": tokens}}


def evaluate(plan_path: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    plan = load(plan_path)
    if plan.get("schema") != "cognition-eval-plan.v1" or plan.get("required_slots") != slots():
        raise ValueError("plan changes the original 120-row denominator")
    if plan.get("observation_contract_version") != 2 or plan.get("reuse_contract_version") != 2:
        raise ValueError("old evaluation plan lacks exact target/change/reuse bindings")
    for field in ("tasks", "gold", "environment", "baseline_runtime", "baseline_source_manifest"):
        artifact(plan[field], f"plan {field}")
    gold = validate_gold(load(Path(plan["gold"]["path"])), Path(plan["tasks"]["path"]))
    results, seen, ids = [], set(), set()
    for record in records:
        row = validate_record(record, plan_path, plan, gold)
        key = (row["phase"], row["kind"], row["slot"])
        if key in seen or row["run_id"] in ids:
            raise ValueError("duplicate observation cannot fill another required row")
        seen.add(key)
        ids.add(row["run_id"])
        results.append(row)
    matrices = []
    for phase in ("before", "after"):
        for kind in KINDS:
            selected = [row for row in results if row["phase"] == phase and row["kind"] == kind]
            by_slot = {row["slot"]: row for row in selected}
            missing = [slot for slot in slots() if slot not in by_slot]
            matrices.append({"phase": phase, "kind": kind, "required": 120, "observed": len(selected), "passing": sum(row["fact_acceptance"] == "pass" for row in selected), "failing": sum(row["fact_acceptance"] == "fail" for row in selected), "unexecuted_slots": missing, "status": "complete" if not missing else "pending", "per_profile": {profile: {"required": 60, "observed": sum(row["profile"] == profile for row in selected)} for profile in PROFILES}})
    paired = []
    for kind in KINDS:
        selected = [r for r in results if r["kind"] == kind]
        before = {r["slot"]: r for r in selected if r["phase"] == "before"}
        after = {r["slot"]: r for r in selected if r["phase"] == "after"}
        common = sorted(set(before) & set(after))
        paired.append({"kind": kind, "required_pairs": 120, "available_pairs": len(common), "correctness_before": sum(before[s]["fact_acceptance"] == "pass" for s in common), "correctness_after": sum(after[s]["fact_acceptance"] == "pass" for s in common), "median_total_ms_before": statistics.median(before[s]["metrics"]["total_ms"] for s in common) if common else None, "median_total_ms_after": statistics.median(after[s]["metrics"]["total_ms"] for s in common) if common else None, "claim": "insufficient_complete_matrix" if len(common) != 120 else "observed_sample_only", "p95": {"status": "unavailable", "reason": "three rounds are not a stable tail-latency sample"}})
    actual = [m for m in matrices if m["kind"] == "actual_agent_observation"]
    status = "pending_actual_agent_evidence" if any(m["status"] != "complete" for m in actual) else "observed_fact_failures" if any(m["failing"] for m in actual) else "pending_independent_negative_evidence"
    return {"schema": SCHEMA, "plan": binding(plan_path), "matrices": matrices, "paired": paired, "observations": results, "negative_conditions": {condition: {"status": "pending_independent_evidence", "required": True} for condition in NEGATIVES}, "boundaries": plan["boundaries"], "status": status}


def compare(before_plan_path: Path, after_plan_path: Path, before_records: list[dict[str, Any]], after_records: list[dict[str, Any]], negative_path: Path | None = None) -> dict[str, Any]:
    before_plan, after_plan = load(before_plan_path), load(after_plan_path)
    if artifact(after_plan.get("before_plan"), "comparison original plan") != binding(before_plan_path) or after_plan.get("phase") != "after":
        raise ValueError("comparison lost exact original phase plan")
    for field in ("tasks", "environment", "required_slots"):
        if before_plan[field] != after_plan[field]:
            raise ValueError(f"comparison changes original paired {field}")
    validate_phase_mapping(load(Path(before_plan["gold"]["path"])), load(Path(after_plan["gold"]["path"])))
    before = evaluate(before_plan_path, before_records)
    after = evaluate(after_plan_path, after_records)
    actual_before = {row["slot"]: row for row in before["observations"] if row["kind"] == "actual_agent_observation"}
    actual_after = {row["slot"]: row for row in after["observations"] if row["kind"] == "actual_agent_observation"}
    common = sorted(set(actual_before) & set(actual_after))
    pairs = [{"slot": slot, "before": actual_before[slot], "after": actual_after[slot]} for slot in common]
    costs = []
    for profile in PROFILES:
        for condition in CONDITIONS:
            selected = [pair for pair in pairs if pair["slot"].split("/")[0] == profile and pair["slot"].split("/")[2] == condition]
            costs.append({"profile": profile, "condition": condition, "required_pairs": 15, "observed_pairs": len(selected), "medians": {metric: {phase: statistics.median(pair[phase]["metrics"][metric] for pair in selected) if selected else None for phase in ("before", "after")} for metric in ("total_ms", "tool_calls", "compass_calls", "learning_calls", "source_read_bytes", "stdout_bytes")}})
    negatives = {condition: {"required": True, "status": "pending_independent_evidence"} for condition in NEGATIVES}
    negative_reference = None
    if negative_path is not None:
        receipt = load(negative_path)
        if receipt.get("schema") != "cognition-eval-negative-acceptance.v1" or receipt.get("status") != "accepted" or not receipt.get("validator") or receipt.get("validator") == receipt.get("author") or receipt.get("after_plan_sha256") != digest(after_plan_path):
            raise ValueError("negative controls need independent, exact after-plan acceptance")
        rows = receipt.get("rows", [])
        if len(rows) != 5 or {row.get("condition") for row in rows} != set(NEGATIVES):
            raise ValueError("negative receipt dropped an original required condition")
        for row in rows:
            if row.get("status") != "accepted" or not row.get("evidence"):
                raise ValueError("negative receipt has an unaccepted or unevidenced condition")
            for ref in row["evidence"]:
                artifact(ref, "independent negative evidence")
            negatives[row["condition"]] = row
        negative_reference = binding(negative_path)
    complete = len(common) == 120
    before_correct = sum(pair["before"]["fact_acceptance"] == "pass" for pair in pairs)
    after_correct = sum(pair["after"]["fact_acceptance"] == "pass" for pair in pairs)
    repeat_pairs = []
    for phase, rows in (("before", actual_before), ("after", actual_after)):
        for profile in PROFILES:
            for family in FAMILIES:
                for round_number in (1, 2, 3):
                    first_slot, repeat_slot = f"{profile}/{family}/first/{round_number}", f"{profile}/{family}/repeat/{round_number}"
                    if first_slot in rows and repeat_slot in rows:
                        repeat_pairs.append({"phase": phase, "profile": profile, "family": family, "round": round_number, "first": rows[first_slot]["metrics"], "repeat": rows[repeat_slot]["metrics"]})
    source_sets = {phase: {entry["source_path"] for entry in load(Path(plan["baseline_source_manifest"]["path"]))} for phase, plan in (("before", before_plan), ("after", after_plan))}
    phase_gold = {phase: load(Path(plan["gold"]["path"])) for phase, plan in (("before", before_plan), ("after", after_plan))}
    fact_deltas = [{"family": family, "role": role, "before_paths": next(task for task in phase_gold["before"]["tasks"] if task["family"] == family)[role], "after_paths": next(task for task in phase_gold["after"]["tasks"] if task["family"] == family)[role]} for family in FAMILIES for role in ("owners", "consumers", "verification", "negative_paths")]
    return {"schema": "cognition-eval-comparison.v1", "before_plan": binding(before_plan_path), "after_plan": binding(after_plan_path), "required_actual_pairs": 120, "observed_actual_pairs": len(common), "before_correct": before_correct, "after_correct": after_correct, "correctness_nonregression_observed": after_correct >= before_correct if complete else None, "per_slot_regressions": [pair["slot"] for pair in pairs if pair["before"]["fact_acceptance"] == "pass" and pair["after"]["fact_acceptance"] == "fail"], "condition_costs": costs, "within_phase_first_repeat": repeat_pairs, "source_scope_delta": {"before_paths": len(source_sets["before"]), "after_paths": len(source_sets["after"]), "added_paths": sorted(source_sets["after"] - source_sets["before"]), "removed_paths": sorted(source_sets["before"] - source_sets["after"])}, "phase_fact_path_delta": fact_deltas, "pairs": pairs, "missing_before": sorted(set(slots()) - set(actual_before)), "missing_after": sorted(set(slots()) - set(actual_after)), "negative_conditions": negatives, "negative_acceptance": negative_reference, "status": "pending_actual_after_evidence" if not complete else "pending_independent_negative_evidence" if negative_path is None else "observed_complete_sample", "boundaries": after_plan["boundaries"] + ["Accuracy and cost are observed model samples; model thoughts are not deterministically replayable", "Phase source and physical fact denominators changed explicitly; cross-phase results are not pure runtime causal effects", "Full source reads count all raw bytes even when the display wrapper shows excerpts", "No source-read reuse saving is attributed to AFTER when BEFORE already reused those bytes", "Separate Learning intervention does not alter paired task inputs; P95 and model tokens remain unavailable"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    prepare = sub.add_parser("freeze")
    for flag in ("tasks", "gold", "environment", "runtime", "source-manifest", "output"):
        prepare.add_argument(f"--{flag}", type=Path, required=True)
    review = sub.add_parser("evaluate")
    review.add_argument("--plan", type=Path, required=True)
    review.add_argument("--observations", type=Path, nargs="+", required=True)
    review.add_argument("--output", type=Path, required=True)
    after = sub.add_parser("freeze-after")
    for flag in ("before-plan", "gold", "runtime", "source-manifest", "output"):
        after.add_argument(f"--{flag}", type=Path, required=True)
    paired = sub.add_parser("compare")
    for flag in ("before-plan", "after-plan", "output"):
        paired.add_argument(f"--{flag}", type=Path, required=True)
    paired.add_argument("--before-observations", type=Path, nargs="+", required=True)
    paired.add_argument("--after-observations", type=Path, nargs="+", required=True)
    paired.add_argument("--negative-evidence", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.operation == "freeze":
            report = freeze(args.tasks, args.gold, args.environment, args.runtime, args.source_manifest)
        elif args.operation == "freeze-after":
            report = freeze_after(args.before_plan, args.gold, args.runtime, args.source_manifest)
        elif args.operation == "compare":
            def records_from(paths: list[Path]) -> list[dict[str, Any]]:
                rows = []
                for path in paths:
                    value = load(path)
                    rows.extend(value if isinstance(value, list) else [value])
                return rows
            report = compare(args.before_plan, args.after_plan, records_from(args.before_observations), records_from(args.after_observations), args.negative_evidence)
        else:
            records = []
            for path in args.observations:
                value = load(path)
                records.extend(value if isinstance(value, list) else [value])
            report = evaluate(args.plan, records)
        write_new(args.output, report)
    except (KeyError, TypeError, ValueError, OSError, UnicodeError) as exc:
        print(f"cognition-eval: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
