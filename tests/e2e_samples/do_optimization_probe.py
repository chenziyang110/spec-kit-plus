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


def workspace_probe(runtime: Path, project: Path, *, source_write: bool, timings: bool,
                    tracked_files: int = 1500, output_mib: int = 32) -> dict:
    """Use a large Git workspace, a tiny declared scope, and actual child tools."""
    project.mkdir(parents=True, exist_ok=False)
    (project / "src").mkdir()
    (project / "corpus").mkdir()
    (project / "src/retained.txt").write_text("before\n", encoding="utf-8")
    (project / "src/unchanged.txt").write_text("unchanged\n", encoding="utf-8")
    for index in range(tracked_files):
        (project / "corpus" / f"fixture-{index}.txt").write_text(f"tracked fixture {index}\n", encoding="utf-8")
    source_effect = 'Path("src/retained.txt").write_text("after\\n", encoding="utf-8")\n' if source_write else ""
    (project / "build.py").write_text(
        'from pathlib import Path\n'
        'Path("out").mkdir(exist_ok=True)\n'
        f'Path("out/package.bin").write_bytes(b"d" * ({output_mib} * 1024 * 1024))\n'
        + source_effect,
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment["PATH"] = str(Path(sys.executable).parent) + os.pathsep + environment.get("PATH", "")
    for args in (["git", "init", "-q"], ["git", "add", "."],
                 ["git", "-c", "user.name=Do probe", "-c", "user.email=probe@example.test", "commit", "-qm", "fixture"]):
        subprocess.run(args, cwd=project, env=environment, check=True, capture_output=True)
    # Local pre-existing edits exercise baseline/delta hashing independently of
    # the small declared write and output scopes.
    for index in range(min(64, tracked_files)):
        (project / "corpus" / f"fixture-{index}.txt").write_bytes(b"local edit\n" * 4096)
    (project / ".specify").mkdir()
    measurements: dict = {}

    def invoke(phase, *args, payload=None, status="ok"):
        argv = [str(runtime), "do", *args, "--format", "json"]
        if payload is not None:
            argv += ["--input-json", "-"]
        if phase and timings and args[0] in {"start", "resume", "validate", "finish"}:
            argv += ["--timings"]
        started = time.perf_counter()
        result = subprocess.run(argv, cwd=project, env=environment, encoding="utf-8", capture_output=True,
                                input=json.dumps(payload) if payload is not None else None, timeout=90)
        envelope = json.loads(result.stdout)
        assert envelope["status"] == status and (result.returncode == 0) == (status == "ok"), envelope
        if phase:
            measurements[phase] = {"elapsed_ms": round(1000 * (time.perf_counter() - started), 1)}
            if "timings" in envelope["data"]:
                measurements[phase]["runtime"] = envelope["data"]["timings"]
        return envelope["data"]

    step = {"id": "build", "purpose": "Write actual package bytes", "cwd": ".", "argv": ["python", "build.py"],
            "script_ref": "build.py", "depends_on": [], "required": True, "expected_result": "Package written",
            "side_effect": "local_write"}
    if source_write:
        step["source_writes"] = ["src/retained.txt"]
    definition = {
        "operation": "package", "target": "workspace-fixture", "owner": "build.py", "variant": "python",
        "task_family": "workspace-fixture", "title": "Build a small scoped package", "goal": "Verify the current package",
        "aliases": ["local fixture"], "applicability": {}, "source_files": ["build.py"], "learning_refs": [],
        "steps": [step],
        "checks": [{"id": "archive", "purpose": "Inspect written package", "cwd": ".", "argv": [],
                    "depends_on": ["build"], "required": True, "expected_result": "Verify package bytes",
                    "kind": "file", "result_path": "out/package.bin"}],
    }
    session_id = "workspace-probe"
    episode_start = time.perf_counter()
    prepared = invoke("prepare", "prepare", payload={
        "session_id": session_id, "definition": definition, "write_scope": ["src"] if source_write else [],
        "output_scope": ["out"], "agent_id": "workspace-probe", "adapter_id": "subprocess",
    })
    state = invoke("start", "start", payload=prepared["start_input"])
    replacement = copy.deepcopy(definition)
    replacement["title"] += " and inspect the output"
    state = invoke("replan", "resume", session_id, payload={"expected_revision": state["revision"], "replan": {
        "request_id": "adjust-title", "mode": "unstarted", "definition": replacement}})
    native_ms = 0.0
    for name in ("build", "archive"):
        packet = invoke(None, "next", session_id)
        action = packet["ready"][0]
        assert action["target_id"] == name, packet
        state = invoke(None, "record", session_id, payload=action["started_input"])
        event = action["completion_event"]
        event["started_at"] = stamp()
        native_start = time.perf_counter()
        if name == "build":
            process = subprocess.run(action["action"]["argv"], cwd=project, env=environment, check=True,
                                     capture_output=True, timeout=60)
            event["exit_code"] = process.returncode
        else:
            file = project / action["action"]["result_path"]
            assert file.stat().st_size == output_mib * 1024 * 1024
            with file.open("rb") as handle:
                assert handle.read(1) == b"d"
            event["result_refs"] = [{"path": action["action"]["result_path"], "kind": "file"}]
        native_ms += 1000 * (time.perf_counter() - native_start)
        event.update({"finished_at": stamp(), "status": "passed", "tool_call_id": f"native-{name}"})
        state = invoke(None, "record", session_id, payload={"expected_revision": state["revision"],
                       "request_id": f"finish-{name}", "events": [event]})
    expected = "blocked" if source_write else "ok"
    validation = invoke("validate", "validate", session_id, status=expected)["validation"]
    assert validation["changed_source_paths"] == (["src/retained.txt"] if source_write else [])
    if source_write:
        assert validation["cognition_closeout"] == "required"
        packet = invoke("next", "next", session_id)
        if timings:
            assert packet["source_closeout"]["binding"]["changed_paths"] == ["src/retained.txt"]
    invoke("finish", "finish", session_id, payload={"expected_revision": state["revision"],
           "knowledge_status": "not_applicable"}, status=expected)
    measurement = {
        "scope": "retained-source" if source_write else "output-only",
        "tracked_files": tracked_files, "output_mib": output_mib, "cli": measurements,
        "native_ms": round(native_ms, 1), "total_ms": round(1000 * (time.perf_counter() - episode_start), 1),
        "validation_status": validation["status"],
    }
    # Recheck through real public validation, using a same-size replacement.
    # This happens after timing so the two runtimes have the same measured work.
    (project / "out/package.bin").write_bytes(b"x" * (output_mib * 1024 * 1024))
    tampered = invoke(None, "validate", session_id, status="blocked")["validation"]
    assert any("artifact" in cause and "changed" in cause for cause in tampered["blockers"]), tampered
    return measurement
