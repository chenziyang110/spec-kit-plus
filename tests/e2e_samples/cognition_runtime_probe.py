"""Record actual Cognition CLI calls without labelling scripts as model work.

An Agent may use start/read/submit to record its own decision. The trace remains
runtime replay until a separate Agent identity and original decision artifact
are supplied. Fixture/gold construction is outside this runner.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "workflow-quality"))
from cognition_eval import CONDITIONS, artifact, binding, digest, load, original_compass, slots, validate_reuse_context, validate_task_binding, validate_runtime_guard, write_new  # noqa: E402


def invoke(runtime: Path, cwd: Path, argv: list[str], output: Path, name: str) -> dict[str, Any]:
    command = [str(runtime), *argv]
    started = time.perf_counter()
    result = subprocess.run(command, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60, check=False)
    elapsed = (time.perf_counter() - started) * 1000
    stdout, stderr = output / f"{name}.stdout", output / f"{name}.stderr"
    stdout.write_bytes(result.stdout)
    stderr.write_bytes(result.stderr)
    return {"argv": command, "cwd": str(cwd), "exit_code": result.returncode, "elapsed_ms": elapsed, "stdout": binding(stdout), "stderr": binding(stderr)}


def start(plan_path: Path, packet_path: Path, slot: str, output: Path, no_intake: bool = False, reuse_observation: Path | None = None) -> dict[str, Any]:
    if slot not in slots():
        raise ValueError("unknown required matrix slot")
    packet = load(packet_path)
    plan = load(plan_path)
    if packet.get("schema") != "cognition-eval-task-packet.v2" or packet.get("slot") != slot or packet.get("plan_sha256") != digest(plan_path):
        raise ValueError("packet slot or plan binding differs")
    artifact(packet["runtime"], "packet runtime")
    artifact(packet["source_manifest"], "packet source manifest")
    for entry in load(Path(packet["source_manifest"]["path"])):
        artifact(entry, "packet source")
    output.mkdir(exist_ok=False, parents=True)
    profile, family, condition, round_number = slot.split("/")
    runtime = Path(packet["runtime"]["path"])
    cwd = Path(packet["project_root"])
    started_at = time.time_ns()
    started = time.perf_counter()
    calls: list[dict[str, Any]] = []
    record = {"schema": "cognition-eval-observation.v1", "task_packet": binding(packet_path), "kind": "native_runtime_replay", "phase": packet["phase"], "slot": slot, "run_id": str(output.resolve()), "plan_sha256": digest(plan_path), "gold_sha256": plan["gold"]["sha256"], "environment_sha256": plan["environment"]["sha256"], "runtime": packet["runtime"], "source_manifest": packet["source_manifest"], "source_change": packet.get("source_change"), "semantic_contract": packet["semantic_contract"], "permission_contract": packet["permission_contract"], "condition_order": CONDITIONS.index(condition) + 1, "independent_round": int(round_number), "tool_calls": calls, "source_reads": [], "decision": {"owners": [], "consumers": [], "verification": [], "rejected_paths": []}, "started_at_ns": started_at, "first_confirmed_owner_ms": 0, "total_ms": (time.perf_counter() - started) * 1000, "model_tokens": {"status": "unavailable", "reason": "runtime CLI stdout has no model token telemetry"}, "observed_scope": "isolated schema5 fixture using exact source copies; no live repository graph mutation"}
    record["project_root"] = str(cwd)
    record["phase_source_manifest"] = packet["phase_source_manifest"]
    validate_task_binding(record, plan_path, plan)
    if reuse_observation is not None:
        prior = binding(reuse_observation)
        previous = load(reuse_observation)
        validate_reuse_context(previous, record)
        original, _ = original_compass(previous)
        ref = original.get("expansion_ref", {})
        record["reuse_attempt"] = {"previous": prior, "outcome": "unsupported_refreshed", "reason": "old runtime lacks same-generation snapshot contract"}
        if ref.get("expansion_contract_version") == 2:
            guard = invoke(runtime, cwd, ["cognition", "expand", "--id", ref["id"], "--section", "related_paths", "--format", "json"], output, "reuse-expand-check")
            calls.append(guard)
            record["reuse_runtime_guard"] = guard
            try:
                validate_runtime_guard(record, original)
            except ValueError as error:
                record["reuse_attempt"] = {"previous": prior, "outcome": "invalidated_refreshed", "reason": str(error)}
            else:
                record["reuse_intake"] = prior
                record["reuse_attempt"] = {"previous": prior, "outcome": "verified_reuse", "reason": "current runtime owner verified original snapshot and status"}
        if not record.get("reuse_intake"):
            no_intake = False
    if not no_intake and not record.get("reuse_intake"):
        calls.extend([invoke(runtime, cwd, ["learning", "start", "--command", "sp-ask", "--context", f"component={family}", "--format", "json"], output, "learning-start"), invoke(runtime, cwd, ["cognition", "compass", "--intent", packet["intent"], "--query", packet["query"], "--format", "json"], output, "compass")])
    elif record.get("reuse_intake"):
        # Expand verifies graph navigation only. No installed read-only owner
        # exposes a complete lesson/index/source/rules applicability digest.
        calls.append(invoke(runtime, cwd, ["learning", "start", "--command", "sp-ask", "--context", f"component={family}", "--format", "json"], output, "learning-start"))
        record["learning_reuse"] = {"outcome": "not_granted_refreshed", "reason": "graph guard cannot prove unchanged applicable lessons, index, source evidence and rules"}
    record["total_ms"] = (time.perf_counter() - started) * 1000
    write_new(output / "open-observation.json", record)
    return {"observation": str(output / "open-observation.json"), "query": packet["query"], "profile": profile, "slot": slot, "compass": load(output / "compass.stdout") if (output / "compass.stdout").exists() else None, "learning": load(output / "learning-start.stdout") if (output / "learning-start.stdout").exists() else None, "reuse_attempt": record.get("reuse_attempt"), "project_root": str(cwd), "source_manifest": packet["source_manifest"], "boundary": "Read selected live fixture source before deciding; graph does not prove source truth"}


def read_source(observation_path: Path, source_path: str, start_line: int = 1, line_count: int | None = None, reuse_from: Path | None = None) -> dict[str, Any]:
    record = load(observation_path)
    manifest = {entry["source_path"]: entry for entry in load(Path(record["source_manifest"]["path"]))}
    if source_path not in manifest:
        raise ValueError("source path is outside the frozen observation boundary")
    entry = artifact(manifest[source_path], "selected source")
    if reuse_from is not None:
        previous = load(reuse_from)
        validate_reuse_context(previous, record)
        matches = [r for r in previous.get("source_reads", []) if r["source_path"] == source_path]
        if not matches:
            raise ValueError("previous observation did not read this source")
        prior = matches[-1]
        if prior.get("source_sha256") != entry["sha256"]:
            raise ValueError("previous source evidence is stale; read current content")
        artifact(prior["evidence"], "previous read")
        read = {**prior, "mode": "reuse_verified", "reused_mode": prior.get("reused_mode", prior["mode"]), "reused_from": binding(reuse_from)}
        record["source_reads"].append(read)
        record["total_ms"] = (time.time_ns() - record["started_at_ns"]) / 1e6
        observation_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
        return {"read": read, "content": None, "current_digest_verified": True}
    complete = Path(entry["path"]).read_bytes()
    if start_line < 1 or (line_count is not None and line_count < 1):
        raise ValueError("line bounds must be positive")
    lines = complete.splitlines(keepends=True)
    data = b"".join(lines[start_line - 1:][:line_count])
    if not data:
        raise ValueError("selected source slice is empty")
    name = "source-" + hashlib.sha256(source_path.encode()).hexdigest()[:16] + f"-{len(record['source_reads']):03d}.txt"
    destination = observation_path.parent / name
    destination.write_bytes(data)
    read = {"source_path": source_path, "mode": "full" if start_line == 1 and line_count is None else "bounded", "start_line": start_line, "line_count": line_count, "source_sha256": entry["sha256"], "evidence": binding(destination)}
    record["source_reads"].append(read)
    record["total_ms"] = (time.time_ns() - record["started_at_ns"]) / 1e6
    observation_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"read": read, "content": data.decode("utf-8")}


def extra_call(observation_path: Path, argv: list[str]) -> dict[str, Any]:
    if len(argv) < 2 or argv[:2] not in (["cognition", "compass"], ["cognition", "lexicon"], ["cognition", "query"], ["cognition", "expand"], ["learning", "start"], ["learning", "list"], ["learning", "show"], ["api", "ensure"], ["api", "list"], ["api", "show"], ["api", "pack"]):
        raise ValueError("only existing read-only navigation routes are allowed")
    record = load(observation_path)
    call = invoke(Path(record["runtime"]["path"]), Path(record["project_root"]), argv, observation_path.parent, f"extra-{len(record['tool_calls']):03d}")
    record["tool_calls"].append(call)
    record["total_ms"] = (time.time_ns() - record["started_at_ns"]) / 1e6
    observation_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"call": call, "stdout": Path(call["stdout"]["path"]).read_text(encoding="utf-8"), "stderr": Path(call["stderr"]["path"]).read_text(encoding="utf-8")}


def confirm_owner(observation_path: Path, source_path: str) -> dict[str, Any]:
    record = load(observation_path)
    reads = [r for r in record["source_reads"] if r["source_path"] == source_path]
    if not reads:
        raise ValueError("owner confirmation requires a preceding actual source read or verified reuse")
    read = reads[-1]
    artifact(read["evidence"], "confirmed source read")
    elapsed = (time.time_ns() - record["started_at_ns"]) / 1e6
    event = {"run_id": record["run_id"], "slot": record["slot"], "task_packet": record["task_packet"], "started_at_ns": record["started_at_ns"], "chosen_owner": source_path, "elapsed_ms": elapsed, "source_read_evidence": read["evidence"], "source_sha256": read["source_sha256"], "meaning": "Agent explicitly confirms this path after inspecting source; independent gold still determines correctness"}
    target = observation_path.parent / f"owner-confirm-{len(record.get('owner_confirmations', [])):03d}.json"
    write_new(target, event)
    record.setdefault("owner_confirmations", []).append({**event, "event_evidence": binding(target)})
    record["first_confirmed_owner_ms"] = record["owner_confirmations"][0]["elapsed_ms"]
    record["total_ms"] = elapsed
    observation_path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    return record["owner_confirmations"][-1]


def submit(observation_path: Path, decision_path: Path, output_path: Path, agent_identity_path: Path | None) -> dict[str, Any]:
    record = load(observation_path)
    record["decision"] = load(decision_path)
    record["total_ms"] = (time.time_ns() - record["started_at_ns"]) / 1e6
    record["metric_limit"] = "first confirmed owner is an explicit model tool event evaluated against independent gold; hidden thought timing is unavailable"
    if agent_identity_path is not None:
        record["kind"] = "actual_agent_observation"
        record["agent"] = load(agent_identity_path)
        record["agent_decision_evidence"] = binding(decision_path)
    else:
        record["replay_decision_evidence"] = binding(decision_path)
    write_new(output_path, record)
    return {"output": binding(output_path), "kind": record["kind"], "slot": record["slot"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    begin = sub.add_parser("start")
    for name in ("plan", "packet", "output"):
        begin.add_argument(f"--{name}", type=Path, required=True)
    begin.add_argument("--slot", required=True)
    begin.add_argument("--no-intake", action="store_true")
    begin.add_argument("--reuse-observation", type=Path)
    read = sub.add_parser("read")
    read.add_argument("--observation", type=Path, required=True)
    read.add_argument("--path")
    read.add_argument("--batch-json", help="Agent-selected array of path/start_line/lines requests")
    read.add_argument("--start-line", type=int, default=1)
    read.add_argument("--lines", type=int)
    read.add_argument("--reuse-from", type=Path)
    call = sub.add_parser("call")
    call.add_argument("--observation", type=Path, required=True)
    call.add_argument("--argv-json", required=True)
    confirm = sub.add_parser("confirm-owner")
    confirm.add_argument("--observation", type=Path, required=True)
    confirm.add_argument("--path", required=True)
    finish = sub.add_parser("submit")
    for name in ("observation", "decision", "output"):
        finish.add_argument(f"--{name}", type=Path, required=True)
    finish.add_argument("--agent-identity", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.operation == "start":
            result = start(args.plan, args.packet, args.slot, args.output, args.no_intake, args.reuse_observation)
        elif args.operation == "read":
            if bool(args.path) == bool(args.batch_json):
                raise ValueError("select exactly one path or batch-json")
            if args.batch_json:
                requests = json.loads(args.batch_json)
                result = [read_source(args.observation, r["path"], r.get("start_line", 1), r.get("lines"), args.reuse_from) for r in requests]
            else:
                result = read_source(args.observation, args.path, args.start_line, args.lines, args.reuse_from)
        elif args.operation == "call":
            result = extra_call(args.observation, json.loads(args.argv_json))
        elif args.operation == "confirm-owner":
            result = confirm_owner(args.observation, args.path)
        else:
            result = submit(args.observation, args.decision, args.output, args.agent_identity)
        print(json.dumps(result, ensure_ascii=False))
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        print(f"cognition-probe: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
