#!/usr/bin/env python3
"""Execute a local E2E runner, reconcile native results, then audit coverage.

Only explicit CLI argv is executed, without a shell. No installation, workflow
state mutation, acceptance, or product repair is performed. Exit codes are
0 complete against frozen scope, 1 incomplete, 2 invalid evidence or execution.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import signal
import subprocess
import sys
import uuid

import e2e_coverage as coverage

CASE_ID = re.compile(r"(?<![A-Za-z0-9-])E2E-[a-f0-9]{24}(?![A-Za-z0-9-])")
MAX_REPORT_BYTES = 32 * 1024 * 1024


def relative_name(value: str) -> str:
    coverage.text(value, "path")
    path = PurePosixPath(value)
    coverage.require(
        not path.is_absolute() and not PureWindowsPath(value).drive
        and "\\" not in value and ":" not in value
        and all(part not in {"", ".", ".."} for part in value.split("/")),
        f"expected a normalized project-relative POSIX path: {value}",
    )
    return value


def file_record(root: Path, name: str) -> dict:
    path = coverage.safe_file(root, relative_name(name))
    return {"path": name, "sha256": sha256_file(path)}


def sha256_file(path: Path) -> str:
    """Hash the on-disk bytes without loading large run inputs into memory."""
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def verify_frozen_inputs(inputs: list[tuple[Path, Path, str]], label: str) -> None:
    for path, original_path, original_digest in inputs:
        coverage.require(path.resolve(strict=True) == original_path and
                         sha256_file(path) == original_digest,
                         f"{label} frozen input changed: {path}")


def write_json(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


def case_id(title: str) -> str:
    matches = CASE_ID.findall(coverage.text(title, "native test selector"))
    coverage.require(len(matches) == 1, f"test must carry exactly one E2E case ID: {title}")
    return matches[0]


def validate_bindings(value: dict, planned: dict, root: Path, runner: str) -> dict:
    coverage.require(isinstance(value, dict), "bindings must be an object")
    coverage.known_fields(value, "schema_version manifest_sha256 test_sources cases", "bindings")
    coverage.require(type(value.get("schema_version")) is int and value["schema_version"] == 1,
                     "unsupported bindings schema")
    coverage.require(value.get("manifest_sha256") == planned["manifest_sha256"], "stale bindings")
    files = coverage.verify_files(root, value.get("test_sources"), "binding test_sources")
    for name in files:
        relative_name(name)
    bindings = coverage.records(value.get("cases"), "bindings.cases")
    expected = {case["id"]: case for case in planned["cases"]}
    coverage.require(bindings.keys() == expected.keys(), "bindings must equal the full planned case set")
    selectors = set()
    for identity, binding in bindings.items():
        coverage.known_fields(binding, "id test_ref selector project asserted_requirements", identity)
        coverage.require(binding.get("test_ref") in files, f"{identity}: unbound test source")
        selector = coverage.text(binding.get("selector"), f"{identity}.selector")
        coverage.require(case_id(selector) == identity, f"{identity}: selector case ID mismatch")
        refs = coverage.unique_strings(binding.get("asserted_requirements"), identity)
        coverage.require(set(refs) == set(expected[identity]["requirements"]), f"{identity}: assertion mapping mismatch")
        project = binding.get("project", "")
        coverage.require(isinstance(project, str), f"{identity}: project must be a string")
        coverage.require(runner != "pytest" or project == "", "pytest bindings cannot select a Playwright project")
        key = (binding["test_ref"], selector, project)
        coverage.require(key not in selectors, "duplicate native test binding")
        selectors.add(key)
    return bindings


def match_binding(bindings: dict, title: str, source: str, project: str = "") -> str:
    identity = case_id(title)
    coverage.require(identity in bindings, f"unplanned native test: {identity}")
    binding = bindings[identity]
    coverage.require((title, source, project) ==
                     (binding["selector"], binding["test_ref"], binding.get("project", "")),
                     f"{identity}: native selector, source, or project differs from frozen binding")
    return identity


def pytest_outcomes(report: dict, bindings: dict, run_id: str, exit_code: int) -> dict:
    coverage.require(report.get("runner") == "pytest" and type(report.get("schema_version")) is int and report["schema_version"] == 1,
                     "unsupported pytest report")
    coverage.require(report.get("run_id") == run_id, "pytest report belongs to another run")
    coverage.require(type(report.get("exit_code")) is int and report["exit_code"] == exit_code,
                     "pytest report/process exit mismatch")
    coverage.require(report.get("errors") == [], "pytest collection or internal error; see runner.log")
    collected = coverage.array(report.get("collected"), "pytest collection", nonempty=False)
    if collected:
        collected = coverage.unique_strings(collected, "pytest collection")
    else:
        # No selected tests is a real outcome, not malformed native evidence.
        # Keep every planned case not_run in the coverage audit, including when
        # a harness normalizes pytest's NO_TESTS_COLLECTED (5) to success (0).
        # Usage, interruption and internal-error exits must still fail closed.
        coverage.require(exit_code in {0, 5}, "pytest empty collection has an error exit; see runner.log")
    collected_ids = {match_binding(bindings, title, title.split("::", 1)[0]) for title in collected}
    grouped = defaultdict(list)
    for event in coverage.array(report.get("events"), "pytest events", nonempty=False):
        coverage.require(isinstance(event, dict), "invalid pytest event")
        identity = match_binding(bindings, event.get("nodeid"), relative_name(event.get("file")))
        coverage.require(identity in collected_ids, "event was not collected")
        coverage.require(event.get("phase") in {"setup", "call", "teardown"}, "unknown pytest phase")
        coverage.require(event.get("outcome") in {"passed", "failed", "skipped", "rerun"}, "unknown pytest outcome")
        coverage.require(type(event.get("wasxfail")) is bool, "missing pytest xfail disposition")
        grouped[identity].append(event)
    outcomes = {}
    for identity in collected_ids:
        events = grouped[identity]
        counts = Counter(event["phase"] for event in events)
        statuses = [event["outcome"] for event in events]
        if "rerun" in statuses or any(count > 1 for count in counts.values()):
            last = {event["phase"]: event["outcome"] for event in events}
            status = "flaky" if last == {"setup": "passed", "call": "passed", "teardown": "passed"} else "failed"
        elif "failed" in statuses:
            status = "failed"
        elif "skipped" in statuses or any(event["wasxfail"] for event in events):
            status = "skipped"
        elif counts == {"setup": 1, "call": 1, "teardown": 1}:
            status = "passed"
        else:
            status = "not_run"
        outcomes[identity] = status
    return outcomes


def playwright_outcomes(report: dict, bindings: dict, root: Path) -> dict:
    coverage.require(report.get("errors") == [], "Playwright reported a global error")
    config = report.get("config")
    coverage.require(isinstance(config, dict), "missing Playwright config")
    native_root = Path(coverage.text(config.get("rootDir"), "Playwright rootDir")).resolve()
    coverage.require(native_root.is_relative_to(root), "Playwright rootDir escapes project")
    outcomes = {}
    suites = list(coverage.array(report.get("suites"), "Playwright suites", nonempty=False))
    while suites:
        suite = suites.pop()
        coverage.require(isinstance(suite, dict), "invalid Playwright suite")
        suites.extend(coverage.array(suite.get("suites", []), "nested suites", nonempty=False))
        for spec in coverage.array(suite.get("specs"), "Playwright specs", nonempty=False):
            coverage.require(isinstance(spec, dict), "invalid Playwright spec")
            native_file = coverage.safe_file(native_root, relative_name(spec.get("file")))
            source = native_file.relative_to(root).as_posix()
            for test in coverage.array(spec.get("tests"), "Playwright tests"):
                coverage.require(isinstance(test, dict), "invalid Playwright test")
                identity = match_binding(bindings, spec.get("title"), source, test.get("projectName"))
                coverage.require(identity not in outcomes, f"duplicate test/project/repeat/shard: {identity}")
                attempts = coverage.array(test.get("results"), "Playwright attempts", nonempty=False)
                statuses = []
                for attempt in attempts:
                    coverage.require(isinstance(attempt, dict), "invalid Playwright attempt")
                    status = attempt.get("status")
                    coverage.require(status in {"passed", "failed", "timedOut", "skipped", "interrupted"},
                                     "unknown Playwright attempt status")
                    coverage.require(type(attempt.get("retry")) is int and attempt["retry"] >= 0,
                                     "invalid Playwright retry")
                    statuses.append(status)
                if test.get("expectedStatus") != "passed":
                    status = "skipped"  # Expected failure is not a successful obligation.
                elif test.get("status") == "flaky" or len(attempts) > 1 or any(a["retry"] for a in attempts):
                    status = "flaky" if statuses and statuses[-1] == "passed" else "failed"
                elif statuses == ["passed"] and test.get("status") == "expected" and not any(
                        a.get("error") or a.get("errors") for a in attempts):
                    status = "passed"
                elif any(s in {"failed", "timedOut", "interrupted"} for s in statuses):
                    status = "failed"
                elif "skipped" in statuses:
                    status = "skipped"
                else:
                    status = "not_run"
                outcomes[identity] = status
    coverage.require(bool(outcomes), "Playwright report contains zero mapped tests")
    return outcomes


def stop_process(process: subprocess.Popen) -> None:
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    elif process.poll() is None:
        # Direct executable invocation; never interpolate a shell command.
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, check=True)
    process.wait(timeout=10)


def execute(manifest: Path, binding_path: Path, root: Path, output: str,
            runner: str, target: str, arguments: list[str], timeout: float = 300,
            max_cases: int = 1000) -> dict:
    root = root.resolve(strict=True)
    coverage.require(runner in {"pytest", "playwright"}, "unsupported runner")
    coverage.require(math.isfinite(timeout) and 0 < timeout <= 86400, "timeout must be in (0, 86400]")
    coverage.text(target, "target (use a sanitized label, never credentials)")
    for arg in arguments:
        coverage.text(arg, "runner argument")
    output_path = root / relative_name(output)
    coverage.require(output_path.parts[len(root.parts)] == "test-results",
                     "run output must be inside test-results/, not workflow or source directories")
    coverage.require(output_path.resolve().is_relative_to(root), "output escapes project")
    coverage.require(output_path.resolve().relative_to(root).parts[0] == "test-results",
                     "output symlink resolves into a non-test directory")
    coverage.require(runner != "playwright" or bool(arguments), "Playwright requires an explicit local runner argv")
    manifest = manifest if manifest.is_absolute() else root / manifest
    binding_path = binding_path if binding_path.is_absolute() else root / binding_path
    # The copies in test-results freeze *parsed* input values, but cannot prove
    # that the original manifest or bindings stayed unchanged during execution.
    # Keep exact byte digests plus resolved paths, including when inputs are
    # passed as absolute paths outside root (supported by the existing CLI).
    frozen_inputs = [(path, path.resolve(strict=True), sha256_file(path))
                     for path in (manifest, binding_path)]
    model = coverage.load(manifest)
    planned = coverage.plan(model, root, max_cases)
    binding_value = coverage.load(binding_path)
    bindings = validate_bindings(binding_value, planned, root, runner)
    for entry in model["sources"]:
        relative_name(entry["path"])
    # Freeze all files before invoking the runner; do not rehash changed tests
    # and quietly certify them as the inputs that were originally executed.
    source_basis = model["sources"]
    test_basis = binding_value["test_sources"]
    verify_frozen_inputs(frozen_inputs, "pre-run")
    output_path.mkdir(parents=True, exist_ok=False)
    run_id = str(uuid.uuid4())
    native = output_path / "native-report.json"
    environment = os.environ.copy()
    environment["SPECIFY_E2E_RUN_ID"] = run_id
    environment["SPECIFY_E2E_REPORT"] = str(native)
    if runner == "pytest":
        helper_dir = str(Path(__file__).resolve().parent)
        environment["PYTHONPATH"] = helper_dir + os.pathsep + environment.get("PYTHONPATH", "")
        # xdist collection and phase evidence require a distributed reporter;
        # this adapter is deliberately serial and refuses incomplete evidence.
        command = [sys.executable, "-m", "pytest", "-p", "e2e_pytest_reporter", *arguments]
    else:
        command = [*arguments, "--reporter=json"]
        environment["PLAYWRIGHT_JSON_OUTPUT_FILE"] = str(native)
    started = datetime.now(timezone.utc).isoformat()
    receipt = {"schema_version": 1, "run_id": run_id, "runner": runner,
               "command": command, "target": target, "started_at": started,
               "manifest_sha256": planned["manifest_sha256"],
               "bindings_sha256": coverage.digest(binding_value)}
    write_json(output_path / "plan.json", planned)
    write_json(output_path / "bindings.json", binding_value)
    write_json(output_path / "manifest.json", model)
    snapshots = [file_record(root, (output_path / name).relative_to(root).as_posix())
                 for name in ("plan.json", "bindings.json", "manifest.json")]
    try:
        with (output_path / "runner.log").open("xb") as log:
            process = subprocess.Popen(command, cwd=root, env=environment, shell=False,
                                       stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=os.name == "posix")
            try:
                exit_code = process.wait(timeout=timeout)
            except (subprocess.TimeoutExpired, KeyboardInterrupt):
                stop_process(process)
                receipt.update(exit_code=process.returncode, interrupted=True)
                raise coverage.CoverageError("runner interrupted or timed out; no completion claim") from None
        receipt.update(finished_at=datetime.now(timezone.utc).isoformat(), exit_code=exit_code)
        coverage.verify_files(root, snapshots, "frozen run inputs")
        verify_frozen_inputs(frozen_inputs, "post-run")
        coverage.verify_files(root, source_basis, "post-run sources")
        coverage.verify_files(root, test_basis, "post-run tests")
        coverage.require(native.is_file() and not native.is_symlink(), "runner did not create a fresh native report")
        coverage.require(0 < native.stat().st_size <= MAX_REPORT_BYTES, "native report empty or exceeds 32 MiB")
        report = coverage.load(native)
        coverage.require(isinstance(report, dict), "native report must be an object")
        if runner == "playwright":
            stats = report.get("stats")
            coverage.require(isinstance(stats, dict), "missing Playwright run timestamps")
            native_started = datetime.fromisoformat(coverage.text(stats.get("startTime"), "Playwright startTime").replace("Z", "+00:00"))
            coverage.require(native_started.tzinfo is not None, "Playwright timestamp needs timezone")
            elapsed = (native_started - datetime.fromisoformat(started)).total_seconds()
            wall = (datetime.fromisoformat(receipt["finished_at"]) - datetime.fromisoformat(started)).total_seconds()
            duration = stats.get("duration")
            coverage.require(-2 <= elapsed <= wall + 2, "Playwright report is stale or from a future run")
            coverage.require(type(duration) in (int, float) and math.isfinite(duration) and
                             0 <= duration <= (wall + 4) * 1000, "invalid Playwright run duration")
        outcomes = (pytest_outcomes(report, bindings, run_id, exit_code) if runner == "pytest"
                    else playwright_outcomes(report, bindings, root))
        receipt["native_report"] = file_record(root, native.relative_to(root).as_posix())
        write_json(output_path / "execution.json", receipt)
        evidence = [file_record(root, (output_path / name).relative_to(root).as_posix())
                    for name in ("native-report.json", "runner.log", "execution.json", "bindings.json", "manifest.json", "plan.json")]
        results = dict(schema_version=1, manifest_sha256=planned["manifest_sha256"],
                       source_revision=model["source_revision"], run_id=run_id, target=target,
                       started_at=started, finished_at=receipt["finished_at"], command=command,
                       exit_code=exit_code, test_sources=test_basis, evidence=evidence, cases=[
                           dict(id=identity, status=status, test_ref=bindings[identity]["test_ref"],
                                asserted_requirements=bindings[identity]["asserted_requirements"], evidence=evidence)
                           for identity, status in sorted(outcomes.items())])
        write_json(output_path / "results.json", results)
        audit = coverage.audit(model, results, root, max_cases)
        verify_frozen_inputs(frozen_inputs, "post-audit")
        write_json(output_path / "coverage.json", audit)
        return audit
    except (OSError, ValueError, TypeError, RecursionError, subprocess.SubprocessError) as exc:
        receipt.update(claim="invalid", error=str(exc), finished_at=datetime.now(timezone.utc).isoformat())
        write_json(output_path / "error.json", receipt)
        raise


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    head, separator, tail = argv, [], []
    if "--" in argv:
        index = argv.index("--")
        head, separator, tail = argv[:index], ["--"], argv[index + 1:]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--bindings", type=Path, required=True)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--runner", choices=("pytest", "playwright"), required=True)
    parser.add_argument("--target", required=True)
    parser.add_argument("--timeout", type=float, default=300)
    parser.add_argument("--max-cases", type=int, default=1000)
    args = parser.parse_args(head)
    try:
        coverage.require(bool(separator), "separate runner arguments with --")
        audit = execute(args.manifest, args.bindings, args.root, args.output_dir,
                        args.runner, args.target, tail, args.timeout, args.max_cases)
        print(json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False))
        return 0 if audit["claim"] == "complete_against_frozen_scope" else 1
    except (OSError, ValueError, TypeError, RecursionError, subprocess.SubprocessError) as exc:
        print(json.dumps({"claim": "invalid", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
