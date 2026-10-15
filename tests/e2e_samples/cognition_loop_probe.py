"""Record real work/verification/runtime calls in an isolated loop fixture.

The adapter records an episode; it does not impersonate a model, score its own
facts, or write cognition/Learning stores. Agents choose edits, commands and
semantic inputs. Product owners retain workflow state and publication authority.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys
import time
import uuid
import unittest
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "workflow-quality"))
from cognition_eval import artifact, binding, digest, load, write_new  # noqa: E402
from cognition_loop_eval import STAGES, source_manifest, slots, validate_plan  # noqa: E402

FIXTURE_SCHEMA = "cognition-loop-isolated-fixture.v1"
FIXTURE_FILES = {
    "src/__init__.py": "",
    "src/service.py": "def charge(amount, rate=0.1):\n    return round(amount * rate, 2)\n",
    "src/consumer.py": "import json\nfrom pathlib import Path\nfrom src.service import charge\nfrom src.legacy import old_charge\n\ndef invoice(amount):\n    config = json.loads(Path(__file__).with_name('config.json').read_text(encoding='utf-8'))\n    return {'amount': amount, 'charge': charge(amount, config['rate'])}\n\ndef legacy_invoice(amount):\n    return {'amount': amount, 'charge': old_charge(amount)}\n",
    "src/legacy.py": "from src.service import charge\n\ndef old_charge(amount):\n    return charge(amount)\n",
    "src/config.json": '{"rate":0.1,"currency":"CNY"}\n',
    "templates/service.txt": "charge(amount, rate) returns a rounded fee.\n",
    "tools/generate.py": "from pathlib import Path\n\nsource = Path('templates/service.txt').read_bytes()\nPath('src/generated.txt').write_bytes(source)\n",
    "src/generated.txt": "charge(amount, rate) returns a rounded fee.\n",
    "tests/test_service.py": "import unittest\nfrom src.service import charge\nfrom src.consumer import invoice, legacy_invoice\n\nclass ServiceTest(unittest.TestCase):\n    def test_charge(self):\n        self.assertEqual(charge(100), 10)\n    def test_invoice(self):\n        self.assertEqual(invoice(20)['charge'], 2)\n    def test_legacy_invoice(self):\n        self.assertEqual(legacy_invoice(20)['charge'], 2)\n\nif __name__ == '__main__':\n    unittest.main()\n",
    "build.py": "import json\nfrom pathlib import Path\nfrom zipfile import ZipFile\n\nout = Path('out')\nout.mkdir(exist_ok=True)\nwith ZipFile(out / 'service.zip', 'w') as archive:\n    for path in sorted(Path('src').glob('*')):\n        if path.is_file():\n            archive.write(path)\nwith ZipFile(out / 'service.zip') as archive:\n    assert archive.testzip() is None\nprint(json.dumps({'ok': True, 'archive': 'out/service.zip'}))\n",
}
PROTECTED = (".specify", ".planning", ".git", ".cognition-loop-fixture.json", ".asset-policy.json")


def inside(root: Path, value: str) -> Path:
    if not isinstance(value, str) or not value or value.startswith("/") or "\\" in value or ":" in value or Path(value).is_absolute() or ".." in Path(value).parts:
        raise ValueError("path must be exact fixture-relative POSIX syntax")
    path = root / value
    if not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("path redirects outside isolated fixture")
    return path


def fixture_guard(root: Path) -> dict[str, Any]:
    root = root.resolve()
    if not root.name.startswith("loop-fixture-"):
        raise ValueError("only explicitly named isolated loop-fixture targets are allowed")
    marker = load(root / ".cognition-loop-fixture.json")
    if marker.get("schema") != FIXTURE_SCHEMA or marker.get("root") != str(root) or len(marker.get("nonce", "")) != 32:
        raise ValueError("fixture marker identity does not match target")
    if root == ROOT.resolve():
        raise ValueError("source repository cannot be a fixture target")
    return marker


def snapshot(root: Path, paths: list[str], destination: Path) -> dict[str, Any]:
    fixture_guard(root)
    destination.mkdir(parents=True, exist_ok=False)
    rows = []
    for name in sorted(set(paths)):
        if any(name == prefix or name.startswith(prefix + "/") for prefix in PROTECTED):
            raise ValueError("snapshot cannot read protected runtime-owned storage")
        source = inside(root, name)
        if source.is_symlink():
            raise ValueError("source snapshot refuses redirected fixture files")
        if not source.exists():
            rows.append({"source_path": name, "state": "deleted", "sha256": None, "bytes": 0})
            continue
        if not source.is_file():
            raise ValueError("source snapshot only accepts files")
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(source.read_bytes())
        rows.append({"source_path": name, **binding(target)})
    manifest = destination / "manifest.json"
    write_new(manifest, rows)
    return binding(manifest)


def create_fixture(root: Path) -> dict[str, Any]:
    root = root.resolve()
    if not root.name.startswith("loop-fixture-") or root.exists() or root == ROOT.resolve():
        raise ValueError("fixture must be a new dedicated loop-fixture directory")
    root.mkdir(parents=True, exist_ok=False)
    marker = {"schema": FIXTURE_SCHEMA, "root": str(root), "nonce": uuid.uuid4().hex,
              "managed_sources": sorted(FIXTURE_FILES),
              "original_sources": {name: {"sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(), "bytes": len(content.encode("utf-8"))} for name, content in sorted(FIXTURE_FILES.items())},
              "scope": "isolated native fixture; not the source repository or a user's existing cognition store"}
    write_new(root / ".cognition-loop-fixture.json", marker)
    for name, content in FIXTURE_FILES.items():
        path = inside(root, name)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
    # Initialize a separate fixture Git repository. No parent checkout mutation.
    calls = []
    for argv in (["git", "init", "-q"], ["git", "config", "--local", "core.autocrlf", "false"],
                 ["git", "config", "--local", "core.eol", "lf"], ["git", "add", *sorted(FIXTURE_FILES)],
                 ["git", "-c", "user.name=Cognition loop fixture", "-c", "user.email=loop-fixture@example.test", "commit", "-qm", "frozen loop fixture"]):
        result = subprocess.run(argv, cwd=root, capture_output=True, check=False, timeout=30)
        calls.append({"argv": argv, "cwd": str(root), "exit_code": result.returncode,
                      "stdout": result.stdout.decode("utf-8", errors="replace"), "stderr": result.stderr.decode("utf-8", errors="replace")})
        if result.returncode:
            raise ValueError("fixture Git initialization failed; preserve directory for recovery")
    return {"fixture": str(root), "marker": binding(root / ".cognition-loop-fixture.json"), "git_initialization": calls,
            "next_action": "seed through approved native import/scan owner, then independently accept the exact task/gold/protocol before observations"}


def business_dependency_check(root: Path, case_id: str) -> dict[str, Any]:
    """Execute behavior and real call routes, allowing equivalent source code.

    Run this in a fresh checker process, separate from the task agent. A source
    substring or merely adding a helper file is not dependency evidence.
    """
    root = root.resolve()
    fixture_guard(root)
    sys.path.insert(0, str(root))
    service = importlib.import_module("src.service")
    consumer = importlib.import_module("src.consumer")
    target = root / ("src/discount.py" if case_id == "L04" else "src/rounding.py")
    parent = root / ("src/consumer.py" if case_id == "L04" else "src/service.py")
    calls = []

    def trace(frame, event, arg):
        if event == "call" and Path(frame.f_code.co_filename).resolve() == target:
            caller = frame.f_back
            while caller:
                if Path(caller.f_code.co_filename).resolve() == parent:
                    calls.append({"callee": str(target), "function": frame.f_code.co_name,
                                  "caller": str(parent), "caller_function": caller.f_code.co_name})
                    break
                caller = caller.f_back

    def equal(actual, expected):
        if actual != expected:
            raise AssertionError((actual, expected))

    def rejects(operation):
        try:
            operation()
        except ValueError:
            return
        raise AssertionError("expected ValueError for percentage outside 0..100")

    previous = sys.getprofile()
    try:
        sys.setprofile(trace)
        if case_id == "L04":
            discount = importlib.import_module("src.discount").discount
            for amount, percent in ((100, 25), (80, 10), (123, 0), (123, 100)):
                expected = amount * (1 - percent / 100)
                equal(discount(amount, percent), expected)
                count = len(calls)
                equal(consumer.discounted_invoice(amount, percent)["amount"], expected)
                if len(calls) == count:
                    raise AssertionError("discounted_invoice did not actually execute its discount dependency")
            for percent in (-1, 101):
                rejects(lambda: discount(100, percent))
                count = len(calls)
                rejects(lambda: consumer.discounted_invoice(100, percent))
                if len(calls) == count:
                    raise AssertionError("consumer did not use discount component for range rejection")
        elif case_id == "L10":
            for amount, rate in ((100, 0.1), (20, 0.1), (10.05, 0.3), (0, 0.1), (12.345, 0.17)):
                count = len(calls)
                equal(service.charge(amount, rate), round(amount * rate, 2))
                if len(calls) == count:
                    raise AssertionError("charge did not actually execute the new rounding dependency")
            count = len(calls)
            equal(consumer.invoice(20)["charge"], 2)
            if len(calls) == count:
                raise AssertionError("invoice did not reach service's rounding dependency")
        else:
            raise ValueError("dependency checker only owns L04 and L10")
    finally:
        sys.setprofile(previous)
    return {"case_id": case_id, "status": "passed", "actual_dependency_calls": calls,
            "source": [binding(target), binding(parent)], "oracle_code_required": False}


def negative_regression_run(root: Path, *, control: bool = False) -> dict[str, Any]:
    """Run the retained regression and record its actual assertRaises cause.

    The inner execution remains failed. The outer business checker can accept
    the truthful failure report only when the specified test really exposes the
    missing negative rejection, never for unrelated import/setup/assert errors.
    """
    root = root.resolve()
    fixture_guard(root)
    sys.path.insert(0, str(root))
    harness = load(root / "tests/e2e-harness.json")
    if harness.get("pattern") != "test_negative_e2e.py" or not isinstance(harness.get("test_id"), str) or not harness["test_id"].startswith("test_negative_e2e."):
        raise ValueError("harness must specify the actual negative-regression test_id and exact pattern")
    service = importlib.import_module("src.service")
    original_charge = service.charge
    original_enter = unittest.case._AssertRaisesContext.__enter__
    original_exit = unittest.case._AssertRaisesContext.__exit__
    contexts = []
    causal_events = []
    test_events = []
    current = {"id": None, "test": None}

    def enter(context):
        test = current["test"]
        method = getattr(test, test._testMethodName, None) if test else None
        code = getattr(method, "__code__", None)
        frame = sys._getframe(1)
        in_body = False
        while frame:
            if frame.f_code is code and frame.f_locals.get("self") is test:
                in_body = True
                break
            frame = frame.f_back
        record = {"test_id": current["id"], "expects_value_error": context.expected is ValueError,
                  "test_body_active": in_body, "negative_calls": [], "actual_missing_rejection_failure": False}
        contexts.append((context, record))
        return original_enter(context)

    def charge(*args, **kwargs):
        amount = args[0] if args else kwargs.get("amount")
        record = contexts[-1][1] if contexts else None
        call = {"amount": amount, "returned_without_value_error": False}
        if record is not None and amount == -20:
            record["negative_calls"].append(call)
        try:
            if control and amount == -20:
                raise ValueError("checker-only counterfactual negative rejection")
            result = original_charge(*args, **kwargs)
            call["returned_without_value_error"] = True
            return result
        except Exception as error:
            call["exception"] = type(error).__name__
            raise

    def leave(context, exc_type, exc_value, tb):
        pair = next((pair for pair in reversed(contexts) if pair[0] is context), None)
        try:
            return original_exit(context, exc_type, exc_value, tb)
        except AssertionError as error:
            if pair:
                record = pair[1]
                record["actual_missing_rejection_failure"] = (
                    exc_type is None and record["expects_value_error"]
                    and any(row["returned_without_value_error"] for row in record["negative_calls"])
                    and str(error).startswith("ValueError not raised"))
                record["assert_raises_failure"] = str(error)
            raise
        finally:
            if pair:
                causal_events.append(pair[1])
                contexts.remove(pair)

    class RecordedResult(unittest.TextTestResult):
        def startTest(self, test):
            current["id"] = test.id()
            current["test"] = test
            super().startTest(test)

        def addFailure(self, test, error):
            test_events.append({"test_id": test.id(), "status": "failure", "exception": error[0].__name__,
                                "traceback": self._exc_info_to_string(error, test)})
            super().addFailure(test, error)

        def addError(self, test, error):
            test_events.append({"test_id": test.id(), "status": "error", "exception": error[0].__name__,
                                "traceback": self._exc_info_to_string(error, test)})
            super().addError(test, error)

        def addSuccess(self, test):
            test_events.append({"test_id": test.id(), "status": "passed"})
            super().addSuccess(test)

    original_sources = {name: digest(root / name) for name in FIXTURE_FILES}
    try:
        service.charge = charge
        unittest.case._AssertRaisesContext.__enter__ = enter
        unittest.case._AssertRaisesContext.__exit__ = leave
        suite = unittest.TestLoader().discover(str(root / "tests"), pattern=harness["pattern"])
        result = unittest.TextTestRunner(stream=sys.stderr, verbosity=2, resultclass=RecordedResult).run(suite)
    finally:
        service.charge = original_charge
        unittest.case._AssertRaisesContext.__enter__ = original_enter
        unittest.case._AssertRaisesContext.__exit__ = original_exit
    specified = harness["test_id"]
    failures = [row for row in test_events if row["status"] == "failure"]
    cause = [row for row in causal_events if row["test_id"] == specified and row["test_body_active"] and row["actual_missing_rejection_failure"]]
    unchanged = original_sources == {name: digest(root / name) for name in FIXTURE_FILES}
    accepted = (result.testsRun > 0 and len(result.errors) == 0 and len(result.failures) == 1
                and len(failures) == 1 and failures[0]["test_id"] == specified
                and failures[0]["exception"] == "AssertionError" and len(cause) == 1 and unchanged)
    return {"schema": "cognition-loop-negative-regression.v3", "project_root": str(root),
            "specified_test_id": specified, "tests_run": result.testsRun, "failures": len(result.failures),
            "errors": len(result.errors), "test_events": test_events, "causal_events": causal_events,
            "control": "counterfactual_negative_rejection_without_source_edit" if control else "actual_original_behavior",
            "original_sources_unchanged": unchanged, "inner_exit_code": 0 if result.wasSuccessful() else 1,
            "truthful_business_failure": accepted, "execution_prerequisite": "failed"}


def negative_regression_check(root: Path) -> dict[str, Any]:
    """Keep full inner failure output and its native command in the report."""
    argv = [sys.executable, str(Path(__file__).resolve()), "negative-regression", "--project", str(root.resolve())]
    def invoke(command):
        started = time.time_ns()
        result = subprocess.run(command, cwd=root, capture_output=True, timeout=30)
        proof = {"argv": command, "cwd": str(root.resolve()), "started_at_ns": started,
                 "ended_at_ns": time.time_ns(), "exit_code": result.returncode,
                 "stdout": result.stdout.decode("utf-8", errors="replace"),
                 "stderr": result.stderr.decode("utf-8", errors="replace")}
        try:
            report = json.loads(proof["stdout"])
        except (ValueError, TypeError):
            report = None
        return proof, report

    proof, report = invoke(argv)
    control_proof, control = invoke(argv + ["--control-negative-rejection"])
    passed = (proof["exit_code"] == 1 and isinstance(report, dict)
              and report.get("truthful_business_failure") is True
              and report.get("execution_prerequisite") == "failed"
              and control_proof["exit_code"] == 0 and isinstance(control, dict)
              and control.get("original_sources_unchanged") is True
              and control.get("tests_run") == report["tests_run"]
              and control.get("failures") == control.get("errors") == 0
              and any(row["test_id"] == report["specified_test_id"] and row["status"] == "passed" for row in control["test_events"]))
    return {"status": "passed" if passed else "failed", "native_call": proof, "regression": report,
            "counterfactual_control_call": control_proof, "counterfactual_control": control,
            "control_limit": "checker-only injected rejection tests failure specificity; never a product repair or actual work observation"}


def save_open(path: Path, record: dict[str, Any]) -> None:
    # Mutable trace draft is probe-owned. Final submissions are exclusive files.
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def start(plan_path: Path, packet_path: Path, output: Path, actor_path: Path | None = None) -> dict[str, Any]:
    plan, _ = validate_plan(plan_path)
    packet = load(packet_path)
    kind = packet.get("kind")
    if packet.get("schema") != "cognition-loop-packet.v1" or kind not in plan["required_slots"] or packet.get("slot") not in slots(kind) or packet.get("plan_sha256") != digest(plan_path) or packet.get("phase") != plan["phase"]:
        raise ValueError("packet changed fixed plan, phase, kind or slot")
    if packet.get("runtime") != plan["runtime"]:
        raise ValueError("packet runtime is not current frozen phase runtime")
    artifact(packet["runtime"], "frozen phase runtime")
    root = Path(packet["project_root"])
    fixture_guard(root)
    source_manifest(packet["source_before"], "packet source inputs")
    artifact(packet["installed_entry"], "actual installed workflow entry")
    if not isinstance(packet.get("allowed_commands"), list) or not packet["allowed_commands"]:
        raise ValueError("packet must freeze actual approved executable bindings/prefixes")
    for command in packet["allowed_commands"]:
        artifact(command["executable"], "approved executable")
        if not isinstance(command.get("argv_prefix"), list):
            raise ValueError("approved native argv prefixes must be explicit")
    output.mkdir(exist_ok=False, parents=True)
    actual_before = snapshot(root, [row["source_path"] for row in source_manifest(packet["source_before"], "initial source denominator")], output / "source-before")
    # Input source snapshots have different paths, so compare original byte facts.
    expected = [(row["source_path"], row.get("sha256"), row["bytes"]) for row in source_manifest(packet["source_before"], "packet sources")]
    actual = [(row["source_path"], row.get("sha256"), row["bytes"]) for row in source_manifest(actual_before, "actual initial sources")]
    if expected != actual:
        raise ValueError("live fixture changed after frozen packet; preserve output and reopen input acceptance")
    start_ns = time.time_ns()
    record = {key: packet[key] for key in ("slot", "kind", "phase", "case_id", "project_root", "runtime", "source_before", "installed_entry", "plan_sha256", "owned_paths", "producer_id")}
    record.update({"schema": "cognition-loop-observation.v1", "packet": binding(packet_path),
                   "run_id": str(output.resolve()), "started_at_ns": start_ns, "attempts": [],
                   "actual_initial_snapshot": actual_before, "business_result": "pending", "fact_decisions": [],
                   "model_tokens": {"status": "unavailable", "reason": "native probe has no model telemetry API"},
                   "memory": {"status": "unavailable"}, "io": {"status": "unavailable"}, "lock_wait": {"status": "unavailable"}})
    if actor_path:
        record["actor"] = binding(actor_path)
    path = output / "open-observation.json"
    save_open(path, record)
    return {"observation": str(path), "task": packet.get("request"), "boundary": "Agent chooses authorized work. Runtime graph is advisory and its stores are not direct edit targets."}


def edit(observation_path: Path, source_path: str, content: str | None, *, rename_to: str | None = None) -> dict[str, Any]:
    record = load(observation_path)
    root = Path(record["project_root"])
    fixture_guard(root)
    owned = set(record["owned_paths"])
    names = [source_path] + ([rename_to] if rename_to else [])
    if any(name not in owned or any(name == prefix or name.startswith(prefix + "/") for prefix in PROTECTED) for name in names):
        raise ValueError("edit is outside accepted task source ownership or targets a protected runtime owner")
    source = inside(root, source_path)
    if source.is_symlink():
        raise ValueError("edit refuses redirected source")
    start_ns = time.time_ns()
    old = binding(source) if source.is_file() else None
    if rename_to:
        target = inside(root, rename_to)
        if target.exists():
            raise ValueError("rename target already exists")
        target.parent.mkdir(parents=True, exist_ok=True)
        source.rename(target)
    elif content is None:
        if not source.is_file():
            raise ValueError("delete requires one existing owned source file")
        source.unlink()
    else:
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(content, encoding="utf-8", newline="\n")
    end_ns = time.time_ns()
    change = {"source_path": source_path, "rename_to": rename_to, "old": old,
              "content_sha256": hashlib.sha256(content.encode()).hexdigest() if content is not None else None,
              "source_write_bytes": len(content.encode("utf-8")) if content is not None else 0,
              "started_at_ns": start_ns, "ended_at_ns": end_ns}
    proof = observation_path.parent / f"edit-{len(record['attempts']):03d}.json"
    write_new(proof, change)
    record.setdefault("source_edits", []).append(binding(proof))
    record["attempts"].append({"id": f"edit-{len(record['attempts'])}", "stage": "work", "result": "passed",
                               "started_at_ns": start_ns, "ended_at_ns": end_ns, "calls": [], "evidence": [binding(proof)]})
    save_open(observation_path, record)
    return {"change": binding(proof)}


def call(observation_path: Path, argv: list[str], stage: str, *, input_value: Any = None, timeout: float = 60) -> dict[str, Any]:
    record = load(observation_path)
    root = Path(record["project_root"])
    fixture_guard(root)
    if stage not in STAGES or not isinstance(argv, list) or not argv or any(not isinstance(value, str) for value in argv):
        raise ValueError("exact native argv and known stage required")
    packet = load(Path(artifact(record["packet"], "current episode packet")["path"]))
    approved = False
    for candidate in packet["allowed_commands"]:
        executable = artifact(candidate["executable"], "current approved executable")
        prefix = [executable["path"], *candidate["argv_prefix"]]
        if argv[:len(prefix)] == prefix:
            approved = True
            break
    if not approved:
        raise ValueError("native command executable/prefix is outside frozen episode authority")
    for index, argument in enumerate(argv[:-1]):
        if argument == "--project-root" and Path(argv[index + 1]).resolve() != root.resolve():
            raise ValueError("runtime native command targets another project")
    if not 0 < timeout <= 60:
        raise ValueError("native per-call timeout must stay within 60 seconds")
    stem = f"call-{len(record['attempts']):03d}"
    start_ns = time.time_ns()
    kwargs: dict[str, Any] = {"cwd": root, "stdout": subprocess.PIPE, "stderr": subprocess.PIPE, "timeout": timeout, "check": False}
    if input_value is not None:
        kwargs["input"] = json.dumps(input_value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    interrupted = False
    try:
        result = subprocess.run(argv, **kwargs)
        exit_code, stdout, stderr = result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired as error:
        exit_code, stdout, stderr = -1, error.stdout or b"", error.stderr or b""
        interrupted = True
    except OSError as error:
        exit_code, stdout, stderr = -1, b"", repr(error).encode("utf-8")
    end_ns = time.time_ns()
    stdout_path, stderr_path = observation_path.parent / (stem + ".stdout"), observation_path.parent / (stem + ".stderr")
    with stdout_path.open("xb") as stream:
        stream.write(stdout)
    with stderr_path.open("xb") as stream:
        stream.write(stderr)
    native = {"argv": argv, "cwd": str(root.resolve()), "exit_code": exit_code,
              "started_at_ns": start_ns, "ended_at_ns": end_ns,
              "stdout": binding(stdout_path), "stderr": binding(stderr_path)}
    if input_value is not None:
        stdin_path = observation_path.parent / (stem + ".stdin")
        with stdin_path.open("xb") as stream:
            stream.write(kwargs["input"])
        native["stdin"] = binding(stdin_path)
    result_state = "interrupted" if interrupted else "passed" if exit_code == 0 else "blocked" if exit_code == 10 else "failed"
    record["attempts"].append({"id": stem, "stage": stage, "result": result_state,
                               "started_at_ns": start_ns, "ended_at_ns": end_ns, "calls": [native], "evidence": []})
    save_open(observation_path, record)
    return {"call": native, "result": result_state, "stdout": stdout.decode("utf-8", errors="replace"), "stderr": stderr.decode("utf-8", errors="replace")}


def read(observation_path: Path, source_path: str) -> dict[str, Any]:
    record = load(observation_path)
    root = Path(record["project_root"])
    fixture_guard(root)
    packet = load(Path(record["packet"]["path"]))
    allowed = set(packet.get("read_paths", [])) | set(packet["owned_paths"])
    if source_path not in allowed:
        raise ValueError("source read outside frozen evidence boundary")
    if any(source_path == prefix or source_path.startswith(prefix + "/") for prefix in PROTECTED):
        raise ValueError("source read cannot bypass protected runtime owner")
    path = inside(root, source_path)
    if not path.is_file() or path.is_symlink():
        raise ValueError("source read missing or redirected")
    data = path.read_bytes()
    target = observation_path.parent / f"read-{len(record.get('source_reads', [])):03d}.txt"
    with target.open("xb") as stream:
        stream.write(data)
    proof = {"source_path": source_path, "source_sha256": digest(path), "evidence": binding(target)}
    record.setdefault("source_reads", []).append(proof)
    save_open(observation_path, record)
    return {"read": proof, "content": data.decode("utf-8")}


def submit(observation_path: Path, decision_path: Path, output_path: Path) -> dict[str, Any]:
    submit_start = time.time_ns()
    record = load(observation_path)
    decision = load(decision_path)
    allowed = {"business_result", "business_verification", "fact_decisions", "semantic_review", "consumer", "closeout", "learning", "actor", "memory", "io", "lock_wait", "model_tokens"}
    if set(decision) - allowed:
        raise ValueError("submission cannot overwrite original clock, packet, attempts, scope or phase")
    record.update(decision)
    root = Path(record["project_root"])
    names = sorted({row["source_path"] for row in source_manifest(record["source_before"], "original source scope")} | set(record["owned_paths"]))
    if record.get("source_after"):
        sequence = len(list(observation_path.parent.glob("source-final-check-*")))
        current = snapshot(root, names, observation_path.parent / f"source-final-check-{sequence:03d}")
        expected = [(row["source_path"], row.get("sha256"), row["bytes"]) for row in source_manifest(record["source_after"], "accepted candidate version")]
        observed = [(row["source_path"], row.get("sha256"), row["bytes"]) for row in source_manifest(current, "final source check")]
        if expected != observed:
            refused = observation_path.parent / f"version-rejection-{sequence:03d}.json"
            write_new(refused, {"reason": "source_changed_after_checkpoint", "expected": record["source_after"], "observed": current})
            record["attempts"].append({"id": f"version-rejection-{sequence:03d}", "stage": "verification", "result": "failed",
                                       "started_at_ns": submit_start, "ended_at_ns": time.time_ns(), "calls": [], "evidence": [binding(refused)]})
            save_open(observation_path, record)
            raise ValueError("source changed after semantic checkpoint; reopen owning task and affected acceptance")
        record["final_source_check"] = current
        frozen_decisions = load(Path(artifact(record["decisions_artifact"], "candidate original facts")["path"]))
        if frozen_decisions != record.get("fact_decisions", []):
            raise ValueError("fact decisions changed after semantic checkpoint")
    else:
        record["source_after"] = snapshot(root, names, observation_path.parent / "source-after")
        decisions = observation_path.parent / "fact-decisions.json"
        write_new(decisions, record.get("fact_decisions", []))
        record["decisions_artifact"] = binding(decisions)
    record["submission_artifact"] = binding(decision_path)
    record["ended_at_ns"] = time.time_ns()
    record["total_ms"] = (record["ended_at_ns"] - record["started_at_ns"]) / 1e6
    write_new(output_path, record)
    return {"output": binding(output_path), "kind": record["kind"], "slot": record["slot"],
            "acceptance": "submitted claim; independent semantic review and new consumer still determine success"}


def checkpoint(observation_path: Path, decision_path: Path) -> dict[str, Any]:
    """Freeze proposed source/facts before independent review and new consumption."""
    record = load(observation_path)
    decision = load(decision_path)
    if set(decision) - {"business_result", "business_verification", "fact_decisions", "closeout", "learning", "actor"}:
        raise ValueError("candidate checkpoint cannot rewrite provenance or grant independent acceptance")
    revision = len(record.get("candidate_history", [])) + 1
    if record.get("source_after"):
        prior = {"source_after": record["source_after"], "decisions_artifact": record["decisions_artifact"],
                 "checkpoint_at_ns": record["candidate_checkpoint_at_ns"], "status": "superseded_pending_revalidation"}
        for key in ("semantic_review", "consumer"):
            if key in record:
                prior[key] = record.pop(key)
        record.setdefault("candidate_history", []).append(prior)
        revision += 1
    record.update(decision)
    root = Path(record["project_root"])
    names = sorted({row["source_path"] for row in source_manifest(record["source_before"], "original source scope")} | set(record["owned_paths"]))
    record["source_after"] = snapshot(root, names, observation_path.parent / f"source-after-v{revision:03d}")
    facts = observation_path.parent / f"fact-decisions-v{revision:03d}.json"
    write_new(facts, record.get("fact_decisions", []))
    record["decisions_artifact"] = binding(facts)
    record["candidate_checkpoint_at_ns"] = time.time_ns()
    save_open(observation_path, record)
    checkpoint_path = observation_path.parent / f"candidate-checkpoint-v{revision:03d}.json"
    write_new(checkpoint_path, {"schema": "cognition-loop-candidate-checkpoint.v1", "case_id": record["case_id"],
                               "source_after": record["source_after"], "decisions_artifact": record["decisions_artifact"],
                               "producer_id": record["producer_id"], "checkpoint_at_ns": record["candidate_checkpoint_at_ns"],
                               "acceptance": "candidate only; independent semantic validation and a separate new consumer required"})
    return {"checkpoint": binding(checkpoint_path), "source_after": record["source_after"], "decisions_artifact": record["decisions_artifact"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    new = sub.add_parser("fixture")
    new.add_argument("--project", type=Path, required=True)
    regression = sub.add_parser("negative-regression")
    regression.add_argument("--project", type=Path, required=True)
    regression.add_argument("--control-negative-rejection", action="store_true")
    begin = sub.add_parser("start")
    for name in ("plan", "packet", "output"):
        begin.add_argument("--" + name, type=Path, required=True)
    begin.add_argument("--actor", type=Path)
    change = sub.add_parser("edit")
    change.add_argument("--observation", type=Path, required=True)
    change.add_argument("--path", required=True)
    choose = change.add_mutually_exclusive_group(required=True)
    choose.add_argument("--content-json")
    choose.add_argument("--delete", action="store_true")
    choose.add_argument("--rename-to")
    invoke = sub.add_parser("call")
    invoke.add_argument("--observation", type=Path, required=True)
    invoke.add_argument("--argv-json", required=True)
    invoke.add_argument("--stage", choices=STAGES, required=True)
    invoke.add_argument("--input-json")
    invoke.add_argument("--timeout", type=float, default=60)
    reading = sub.add_parser("read")
    reading.add_argument("--observation", type=Path, required=True)
    reading.add_argument("--path", required=True)
    finish = sub.add_parser("submit")
    for name in ("observation", "decision", "output"):
        finish.add_argument("--" + name, type=Path, required=True)
    proposed = sub.add_parser("checkpoint")
    for name in ("observation", "decision"):
        proposed.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.operation == "fixture":
            result = create_fixture(args.project)
        elif args.operation == "negative-regression":
            result = negative_regression_run(args.project, control=args.control_negative_rejection)
            print(json.dumps(result, ensure_ascii=False, allow_nan=False))
            return result["inner_exit_code"]
        elif args.operation == "start":
            result = start(args.plan, args.packet, args.output, args.actor)
        elif args.operation == "edit":
            content = json.loads(args.content_json) if args.content_json is not None else None
            result = edit(args.observation, args.path, content, rename_to=args.rename_to)
        elif args.operation == "call":
            result = call(args.observation, json.loads(args.argv_json), args.stage, input_value=json.loads(args.input_json) if args.input_json else None, timeout=args.timeout)
        elif args.operation == "read":
            result = read(args.observation, args.path)
        elif args.operation == "checkpoint":
            result = checkpoint(args.observation, args.decision)
        else:
            result = submit(args.observation, args.decision, args.output)
        print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    except (OSError, UnicodeError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        print(f"cognition-loop-probe: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    raise SystemExit(main())
