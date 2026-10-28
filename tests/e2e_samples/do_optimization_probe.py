"""Real packaging adapter for parameter reuse and verified incremental handoffs.

Measures public runtime calls and actual native operations, not model thinking.
No browser/desktop/connector service is simulated as a real client integration.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time


BUILD_SOURCE = '''import argparse, hashlib, json, zipfile
from pathlib import Path
p = argparse.ArgumentParser()
p.add_argument("--output", required=True)
p.add_argument("--verify", action="store_true")
a = p.parse_args()
out = Path(a.output)
out.mkdir(parents=True, exist_ok=True)
archive = out / "demo.zip"
if not a.verify:
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.write("payload.txt")
else:
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert z.read("payload.txt") == Path("payload.txt").read_bytes()
    (out / "report.json").write_text(json.dumps({"ok": True, "sha256": hashlib.sha256(archive.read_bytes()).hexdigest()}), encoding="utf-8")
'''


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def probe(runtime: Path, project: Path) -> dict:
    project.mkdir(parents=True, exist_ok=False)
    (project / "build.py").write_text(BUILD_SOURCE, encoding="utf-8")
    (project / "payload.txt").write_text("real package payload\n" * 2048, encoding="utf-8")
    environment = os.environ.copy()
    environment["PATH"] = str(Path(sys.executable).parent) + os.pathsep + environment.get("PATH", "")
    for args in (["git", "init", "-q"], ["git", "add", "build.py", "payload.txt"],
                 ["git", "-c", "user.name=Do probe", "-c", "user.email=probe@example.test", "commit", "-qm", "fixture"]):
        subprocess.run(args, cwd=project, env=environment, check=True, capture_output=True)
    calls = 0
    observations = 0

    def invoke(*args: str, payload: dict | None = None) -> dict:
        nonlocal calls
        calls += 1
        command = [str(runtime), *args, "--project-root", str(project), "--format", "json"]
        if payload is not None:
            command += ["--input-json", "-"]
        completed = subprocess.run(command, input=json.dumps(payload, ensure_ascii=False) if payload else None,
                                   cwd=project, env=environment, encoding="utf-8", capture_output=True, timeout=60)
        envelope = json.loads(completed.stdout)
        assert completed.returncode == 0 and envelope["status"] == "ok", envelope
        return envelope["data"]

    definition = {
        "operation": "package", "target": "parameter-demo", "owner": "build.py", "variant": "python",
        "task_family": "python-zip-package", "title": "Package the current payload", "goal": "Package and verify the current payload",
        "aliases": ["打包项目"], "applicability": {}, "source_files": ["build.py", "payload.txt"], "learning_refs": [],
        "parameters": {"output": {"kind": "path", "required": True, "example": "out/example"}},
        "steps": [{"id": "build", "purpose": "Create the actual archive", "cwd": ".", "argv": ["python", "build.py", "--output", "{{param:output}}"],
                   "script_ref": "build.py", "depends_on": [], "required": True, "expected_result": "Current payload archive", "side_effect": "local_write"}],
        "checks": [
            {"id": "inspect", "purpose": "Inspect archive contents", "cwd": ".", "argv": ["python", "build.py", "--output", "{{param:output}}", "--verify"],
             "script_ref": "build.py", "depends_on": ["build"], "required": True, "expected_result": "Archive matches payload", "kind": "json",
             "result_path": "{{param:output}}/report.json", "json_pointer": "/ok", "expected_json": True},
            {"id": "archive", "purpose": "Check actual archive presence", "cwd": ".", "argv": [], "depends_on": ["build", "inspect"],
             "required": True, "expected_result": "Archive retains exact hash", "kind": "file", "result_path": "{{param:output}}/demo.zip"},
        ],
    }
    rounds = []
    canonical = None
    method = None
    baseline_definition = copy.deepcopy(definition)
    for index, output in enumerate(["out/first", "out/中文目录", "out/third", "out/baseline"]):
        session_id = f"optimized-{index}"
        start_calls, start_observations, started_round = calls, observations, time.perf_counter()
        round_definition = baseline_definition if index == 3 else definition
        payload = {"session_id": session_id, "definition": round_definition, "parameters": {"output": output}, "output_scope": [output],
                   "context": {"shell": "native-adapter", "toolchain.python": sys.version.split()[0]}, "agent_id": "optimization-probe", "adapter_id": "real-subprocess"}
        if method:
            payload["method_binding"] = {key: method[key] for key in ("id", "revision", "content_digest")}
        prepared = invoke("do", "prepare", payload=payload)
        state = invoke("do", "start", payload=prepared["start_input"])
        adjusted = False
        retained_count = 0
        observations_after_adjustment = 0
        while True:
            packet = invoke("do", "next", session_id)
            if packet["complete_ready"]:
                if index in (0, 3) and not adjusted:
                    # Add a real extra outcome check before closeout. Existing
                    # outputs stay bound to original attempts rather than rerun.
                    replacement = copy.deepcopy(round_definition)
                    extra = copy.deepcopy(replacement["checks"][0])
                    extra["id"] = "confirm"
                    replacement["checks"].append(extra)
                    state = invoke("do", "resume", session_id, payload={"expected_revision": state["revision"],
                        "replan": {"request_id": "add-confirm", "mode": "unstarted", "retain_verified": index == 0, "definition": replacement}})
                    epoch = invoke("do", "show", session_id, "--section", "definition:2")["definition_snapshot"]
                    retained_count = len(epoch.get("retained_attempts", []))
                    assert retained_count == (3 if index == 0 else 0)
                    observations_after_adjustment = observations
                    if index == 0:
                        definition = replacement
                    adjusted = True
                    continue
                break
            assert packet["ready"] and not packet["running"], packet
            ready = packet["ready"][0]
            state = invoke("do", "record", session_id, payload=ready["started_input"])
            event = ready["completion_event"]
            action = ready["action"]
            event["started_at"] = stamp()
            if action["argv"]:
                actual = subprocess.run(action["argv"], cwd=project, env=environment, encoding="utf-8", capture_output=True, timeout=60)
                assert actual.returncode == 0, actual.stderr
                event["exit_code"] = actual.returncode
            else:
                (project / action["result_path"]).read_bytes()
            event.update({"finished_at": stamp(), "status": "passed", "tool_call_id": f"actual-{session_id}-{observations}"})
            observations += 1
            if ready["kind"] == "check":
                event["result_refs"] = [{"path": action["result_path"], "kind": action["kind"]}]
            else:
                event["result_refs"] = [{"path": f"{output}/demo.zip", "kind": "file"}]
            state = invoke("do", "record", session_id, payload={"expected_revision": state["revision"], "request_id": f"complete-{event['attempt_id']}", "events": [event]})
        closeout_start = calls
        extra_closeout_reads = 0
        summary = "Verified packaging with parameterized output and retained local evidence"
        if index == 3:
            # Execute the retained legacy owner protocol too; the comparison
            # counts real public invocations, not an assumed baseline.
            state = invoke("do", "finish", session_id, payload={"expected_revision": state["revision"], "knowledge_status": "pending"})
            method_input = invoke("do", "show", session_id, "--section", "method")
            extra_closeout_reads += 1
            published = invoke("playbook", "update", payload={"id": method["id"], "base_digest": method["content_digest"],
                               "definition": method_input["method_definition"], "session_id": session_id, "change_summary": summary})
            state = invoke("do", "show", session_id)
            extra_closeout_reads += 1
            state = invoke("do", "finish", session_id, payload={"expected_revision": state["revision"], "knowledge_status": "saved", "knowledge": published["knowledge_receipt"]})
        else:
            state = invoke("do", "complete", session_id, payload={"expected_revision": state["revision"], "change_summary": summary})
        assert state["session"]["knowledge_status"] == "saved"
        actual_closeout_calls = calls - closeout_start
        owner_closeout_calls = actual_closeout_calls - extra_closeout_reads
        assert actual_closeout_calls == (5 if index == 3 else 1)
        assert owner_closeout_calls == (3 if index == 3 else 1)
        method = invoke("playbook", "show", "--id", state["session"]["knowledge"]["method_id"])
        path = project / ".specify/playbooks" / method["id"] / "playbook.json"
        if canonical is None:
            canonical = path.read_bytes()
        else:
            assert path.read_bytes() == canonical
        metrics = invoke("do", "show", session_id, "--section", "metrics")["metrics"]
        rounds.append({"revision": method["revision"], "initial_method_digest": prepared["method_digest"], "initial_instance_digest": prepared["definition_digest"],
                       "method_digest": method["content_digest"], "instance_digest": state["definition_digest"],
                       "public_runtime_calls": calls - start_calls, "native_observations": observations - start_observations,
                       "retained_attempts": retained_count, "metrics": metrics, "adapter_episode_ms": round((time.perf_counter() - started_round) * 1000)})
        rounds[-1]["closeout_public_calls"] = actual_closeout_calls
        rounds[-1]["closeout_owner_calls"] = owner_closeout_calls
        rounds[-1]["new_epoch_native_observations"] = observations - observations_after_adjustment if adjusted else None
    baseline = rounds.pop()
    return {"status": "passed", "rounds": rounds, "baseline": baseline, "native_observations": observations,
            "closeout_public_calls": {"legacy_finish_update_finish": baseline["closeout_public_calls"], "complete": rounds[0]["closeout_public_calls"]},
            "closeout_owner_calls": {"legacy_finish_update_finish": baseline["closeout_owner_calls"], "complete": rounds[0]["closeout_owner_calls"]},
            "incremental_required_actions": {"full_replan": baseline["new_epoch_native_observations"], "verified_retention": rounds[0]["new_epoch_native_observations"]}, "runtime_execution_verified": False,
            "measurement_scope": "actual local adapter episode; excludes model reasoning and remote client integrations"}
