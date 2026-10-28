"""Exercise real native commands through first use, reuse and method evolution.

This is a test adapter, not a production process runner. It observes subprocesses
and file reads, reports their actual results, and keeps the evidence origin
agent_tool_observation. The Go runtime never launches these build commands.
"""

from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Callable


DEMO_SOURCE = '''import argparse
import hashlib
import json
from pathlib import Path
import zipfile

parser = argparse.ArgumentParser()
parser.add_argument("--compression", choices=["stored", "deflated"], default="stored")
parser.add_argument("--verify", action="store_true")
args = parser.parse_args()
output = Path("out")
output.mkdir(exist_ok=True)
archive = output / "demo.zip"
if args.verify:
    with zipfile.ZipFile(archive) as bundle:
        assert bundle.testzip() is None
        assert bundle.read("payload.txt") == Path("payload.txt").read_bytes()
    report = {"ok": True, "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest()}
    (output / "report.json").write_text(json.dumps(report), encoding="utf-8")
    print("archive metadata verified")
else:
    mode = zipfile.ZIP_DEFLATED if args.compression == "deflated" else zipfile.ZIP_STORED
    with zipfile.ZipFile(archive, "w", compression=mode) as bundle:
        bundle.write("payload.txt")
    print("archive built with " + args.compression)
'''


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def probe(runtime: Path, project: Path, *, prepare_project: Callable[[Path], None] | None = None) -> dict:
    project.mkdir(parents=True, exist_ok=False)
    environment = os.environ.copy()
    environment["PATH"] = str(Path(sys.executable).parent) + os.pathsep + environment.get("PATH", "")
    (project / "build_demo.py").write_text(DEMO_SOURCE, encoding="utf-8")
    (project / "payload.txt").write_text("verified package payload\n" * 4096, encoding="utf-8")
    for argv in (
        ["git", "init", "-q"],
        ["git", "add", "build_demo.py", "payload.txt"],
        ["git", "-c", "user.name=Do probe", "-c", "user.email=probe@example.test", "commit", "-qm", "fixture"],
    ):
        subprocess.run(argv, cwd=project, env=environment, check=True, capture_output=True, text=True)

    if prepare_project is not None:
        prepare_project(project)

    def invoke(*args: str, payload: dict | None = None, blocked: bool = False) -> dict:
        command = [str(runtime), *args, "--project-root", str(project), "--format", "json"]
        if payload is not None:
            command += ["--input-json", "-"]
        result = subprocess.run(command, input=json.dumps(payload) if payload is not None else None,
                                cwd=project, env=environment, text=True, encoding="utf-8", capture_output=True, timeout=60)
        envelope = json.loads(result.stdout)
        if blocked:
            assert result.returncode != 0 and envelope["status"] != "ok", envelope
        else:
            assert result.returncode == 0 and envelope["status"] == "ok", (result.stderr, envelope)
        return envelope.get("data", {})

    definition = {
        "operation": "package", "target": "demo-archive", "owner": "build_demo.py", "variant": "python",
        "title": "Package and verify the demo archive", "goal": "Package and verify the demo archive",
        "aliases": ["打包项目", "build the demo package", "package demo"],
        "applicability": {}, "source_files": ["build_demo.py", "payload.txt"], "learning_refs": [],
        "steps": [{"id": "build", "purpose": "Create the actual ZIP from current source", "cwd": ".",
                   "argv": ["python", "build_demo.py"], "script_ref": "build_demo.py", "depends_on": [],
                   "required": True, "expected_result": "A ZIP containing the current payload", "side_effect": "local_write"}],
        "checks": [
            {"id": "inspect", "purpose": "Check archive integrity and exact payload", "cwd": ".",
             "argv": ["python", "build_demo.py", "--verify"], "script_ref": "build_demo.py", "depends_on": ["build"],
             "required": True, "expected_result": "Archive metadata and payload match", "kind": "json",
             "result_path": "out/report.json", "json_pointer": "/ok", "expected_json": True},
            {"id": "archive", "purpose": "Retain an actual archive hash obligation", "cwd": ".", "argv": [],
             "depends_on": ["build", "inspect"], "required": True, "expected_result": "The verified archive remains present",
             "kind": "file", "result_path": "out/demo.zip"},
        ],
    }
    attempts_executed = 0
    rounds = []

    def execute(session_id: str, method: dict | None, method_definition: dict) -> dict:
        nonlocal attempts_executed
        payload = {"session_id": session_id, "definition": method_definition, "output_scope": ["out"],
                   "agent_id": "operation-probe", "adapter_id": "native-test-adapter"}
        if method:
            payload["method_binding"] = {"id": method["id"], "revision": method["revision"],
                                         "content_digest": method["content_digest"]}
        session = invoke("do", "start", payload=payload)
        started_round = time.monotonic()
        for kind, action in [("step", s) for s in method_definition["steps"]] + [("check", c) for c in method_definition["checks"]]:
            attempt = session_id + "-" + action["id"]
            event = {"attempt_id": attempt, "target_id": action["id"], "kind": kind, "event": "started"}
            session = invoke("do", "record", session_id, payload={"expected_revision": session["revision"],
                             "request_id": attempt + "-start", "events": [event]})
            started = stamp()
            if action["argv"]:
                result = subprocess.run(action["argv"], cwd=project, env=environment, capture_output=True, text=True, timeout=60)
                assert result.returncode == 0, result.stderr
                summary = result.stdout.strip()
            else:
                assert (project / action["result_path"]).stat().st_size > 0
                result = None
                summary = "Native file inspection confirmed the archive exists"
            finished = stamp()
            attempts_executed += 1
            event.update({"event": "completed", "status": "passed", "evidence_origin": "agent_tool_observation",
                          "tool_call_id": "probe-call-" + str(attempts_executed), "argv": action["argv"], "cwd": ".",
                          "started_at": started, "finished_at": finished, "summary": summary})
            if result is not None:
                event["exit_code"] = result.returncode
            if kind == "check":
                event["result_refs"] = [{"path": action["result_path"], "kind": action["kind"]}]
            session = invoke("do", "record", session_id, payload={"expected_revision": session["revision"],
                             "request_id": attempt + "-complete", "events": [event]})
        checked = invoke("do", "validate", session_id)
        assert checked["validation"]["status"] == "passed", checked
        assert checked["runtime_execution_verified"] is False, checked
        session = invoke("do", "finish", session_id, payload={"expected_revision": session["revision"], "knowledge_status": "pending"})
        no_op = invoke("learning", "capture-auto", "--command", "sp-do", "--session-id", session_id)
        assert no_op["status"] == "no-op", no_op
        update = {"definition": method_definition, "session_id": session_id,
                  "change_summary": "Record the actual verified operation"}
        if method:
            update["base_digest"] = method["content_digest"]
        published = invoke("playbook", "update", payload=update)
        before_retry = attempts_executed
        replay = invoke("playbook", "update", payload=update)
        assert replay["status"] == "already_recorded" and attempts_executed == before_retry, replay
        session = invoke("do", "show", session_id)
        finished_state = invoke("do", "finish", session_id,
                                payload={"expected_revision": session["revision"], "knowledge_status": "saved",
                                         "knowledge": published["knowledge_receipt"]})
        assert finished_state["terminal"] is True and finished_state["session"]["execution_outcome"] == "passed", finished_state
        rounds.append({"session_id": session_id, "method_id": published["id"], "revision": published["revision"],
                       "status": published["status"], "elapsed_ms": round((time.monotonic() - started_round) * 1000),
                       "archive_bytes": (project / "out" / "demo.zip").stat().st_size})
        return published

    assert invoke("playbook", "find", "--query", "打包项目")["items"] == []
    first = execute("first-use", None, definition)
    assert first["revision"] == 1 and first["status"] == "created", first
    canonical = project / ".specify" / "playbooks" / first["id"] / "playbook.json"
    first_bytes = canonical.read_bytes()
    cards = invoke("playbook", "find", "--query", "打包项目")["items"]
    assert len(cards) == 1 and cards[0]["id"] == first["id"], cards
    assert "steps" not in cards[0] and "checks" not in cards[0], cards
    selected = invoke("playbook", "show", "--id", first["id"], "--revision", "1", "--section", "all")
    second = execute("reuse", first, selected["definition"])
    assert second["status"] == "no_change" and second["revision"] == 1, second
    assert canonical.read_bytes() == first_bytes, "unchanged reuse rewrote method authority"
    improved = copy.deepcopy(selected["definition"])
    improved["steps"][0]["argv"] += ["--compression", "deflated"]
    improved["steps"][0]["purpose"] = "Compress the current payload into a smaller verified archive"
    third = execute("improved", second, improved)
    assert third["status"] == "updated" and third["revision"] == 2, third
    assert rounds[2]["archive_bytes"] < rounds[1]["archive_bytes"], rounds
    assert (canonical.parent / "revisions" / "000001.json").read_bytes() == first_bytes
    stale_update = {"definition": definition, "base_digest": first["content_digest"], "proposal_only": True,
                    "change_summary": "Attempt an obsolete base revision"}
    invoke("playbook", "update", payload=stale_update, blocked=True)
    (project / "out" / "report.json").write_text('{"ok": false}', encoding="utf-8")
    invoke("do", "validate", "improved", blocked=True)
    return {"status": "passed", "native_observations": attempts_executed, "rounds": rounds,
            "verified": ["empty first lookup", "synonymous bounded recall", "unchanged method bytes",
                         "verified revision advancement", "immutable old revision", "idempotent knowledge replay",
                         "stale revision rejection", "tampered current report rejection"],
            "evidence_origin": "agent_tool_observation", "runtime_execution_verified": False}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--project", type=Path, required=True, help="New, nonexisting isolated fixture directory")
    args = parser.parse_args()
    print(json.dumps(probe(args.runtime.resolve(), args.project.resolve()), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
