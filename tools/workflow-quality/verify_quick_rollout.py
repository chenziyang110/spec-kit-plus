"""Run complete checkout checks; missing, skipped or empty evidence is not green.

Requires an already prepared development environment. Does not install packages,
fetch Git refs, change permissions, merge, publish, or run a paid agent evaluation.
Logs stay in a new caller-selected directory outside the checkout.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import signal
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Sequence

SCHEMA = "quick-rollout-verification-v1"
ROOT = Path(__file__).resolve().parents[2]
INSTALL_MODULE = "tests.integrations.test_quick_optimization_installation"
INSTALL_CASES = (
    *(f"test_advanced_quick_policy_survives_install[{host}-{shell}]"
      for host in ("codex", "cursor-agent") for shell in ("sh", "ps")),
    *(f"test_classic_quick_keeps_worker_default[{host}]"
      for host in ("codex", "cursor-agent")),
    "test_quick_policy_repair_preserves_user_changes",
)
GO_CASES = (
    "TestQuickOutputDiscoveryConsistency",
    "TestQuickDirectLifecyclePreservesResultGates",
    "TestQuickDirectCannotRelabelActiveWorker",
    "TestQuickDirectStaleFenceStillBlocksWithoutStateMutation",
    "TestQuickDirectResultSubmitPreservesValidationFailure",
    "TestQuickCompactConsumerLifecycle",
    *(f"TestQuickCompactConsumerLifecycle/direct={direct}/compact={compact}"
      for direct in ("false", "true") for compact in ("false", "true")),
)
SOURCE_FILES = (
    "tools/specify-runtime/go.mod", "tools/specify-runtime/go.sum",
    "tools/specify-runtime/main.go", "src/specify_cli/__init__.py",
    "tests/integrations/test_quick_optimization_installation.py",
    "templates/advanced-skills/spx-quick/references/task-contract.md",
)


class EvidenceError(ValueError):
    """The requested validation was not established by the supplied evidence."""


def inspect_go_log(path: Path, package: str, required: Sequence[str] = GO_CASES) -> dict[str, int]:
    """Require successful terminal events for the root package and named tests."""
    terminal: dict[tuple[str, str], str] = {}
    failed = False
    try:
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                if not line.strip():
                    continue
                event = json.loads(line)
                if not isinstance(event, dict):
                    raise EvidenceError("Go report contains a non-object event")
                action, owner, test = event.get("Action"), event.get("Package"), event.get("Test", "")
                if action in ("fail", "build-fail"):
                    failed = True
                if action not in ("pass", "skip", "fail"):
                    continue
                if not isinstance(owner, str) or not isinstance(test, str):
                    raise EvidenceError("Go terminal event has invalid identity")
                key = (owner, test)
                if key in terminal:
                    raise EvidenceError("Go report contains repeated terminal events")
                terminal[key] = action
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceError("Go report is missing or malformed") from exc
    if failed or terminal.get((package, "")) != "pass":
        raise EvidenceError("Go package did not pass")
    if any(terminal.get((package, test)) != "pass" for test in required):
        raise EvidenceError("Required Go lifecycle tests were missing, skipped or failed")
    return {action: sum(bool(test) and status == action for (_, test), status in terminal.items())
            for action in ("pass", "skip", "fail")}


def inspect_pytest_report(path: Path, module: str = INSTALL_MODULE,
                          required: Sequence[str] = INSTALL_CASES) -> dict[str, int]:
    """Check actual testcase rows, not just an exit code or suite summary."""
    try:
        raw = path.read_bytes()
        if len(raw) > 64 * 1024 * 1024:
            raise EvidenceError("Unsupported pytest report")
        text = raw.decode("utf-8-sig")
        if "<!DOCTYPE" in text or "<!ENTITY" in text:
            raise EvidenceError("Unsupported pytest report")
        root = ET.fromstring(text)
    except (OSError, UnicodeError, ET.ParseError) as exc:
        raise EvidenceError("Pytest report is missing or malformed") from exc
    if root.tag not in ("testsuites", "testsuite"):
        raise EvidenceError("Pytest report has an unexpected root")
    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    for suite in suites:
        for field in ("errors", "failures"):
            if suite.get(field, "0") != "0":
                raise EvidenceError("Pytest suite reports errors or failures")
    seen: dict[tuple[str, str], str] = {}
    for case in root.iter("testcase"):
        key = (case.get("classname", ""), case.get("name", ""))
        if not all(key) or key in seen:
            raise EvidenceError("Pytest testcase identity is missing or repeated")
        if case.find("failure") is not None or case.find("error") is not None:
            raise EvidenceError("Pytest testcase failed")
        seen[key] = "skip" if case.find("skipped") is not None else "pass"
    if not seen or any(seen.get((module, name)) != "pass" for name in required):
        raise EvidenceError("Required installation tests were missing, skipped or failed")
    return {status: sum(value == status for value in seen.values()) for status in ("pass", "skip")}


def execute(argv: Sequence[str], cwd: Path, output: Path, name: str,
            timeout: int, env: dict[str, str]) -> dict[str, Any]:
    """No shell, exclusive log creation, and bounded process-tree cleanup."""
    result: dict[str, Any] = {"name": name, "argv": list(argv), "status": "blocked"}
    with (output / f"{name}.stdout.log").open("xb") as stdout, \
            (output / f"{name}.stderr.log").open("xb") as stderr:
        try:
            proc = subprocess.Popen(list(argv), cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                    stdout=stdout, stderr=stderr,
                                    start_new_session=os.name == "posix")
        except OSError:
            return result | {"reason": "process-not-started"}
        try:
            code = proc.wait(timeout=timeout)
        except (subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
            if os.name == "posix":
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
            else:
                # taskkill is a Windows system command, never a shell expression.
                try:
                    subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                                   stdout=stderr, stderr=stderr, timeout=15, check=False)
                except (OSError, subprocess.TimeoutExpired):
                    pass
                proc.kill()
            proc.wait()
            if isinstance(exc, KeyboardInterrupt):
                raise
            return result | {"reason": "timeout"}
    return result | {"status": "passed" if code == 0 else "failed", "exit_code": code}


def git_value(repo: Path, *args: str) -> str:
    try:
        result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                                text=True, timeout=30, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise EvidenceError("Git checkout inspection unavailable") from exc
    if result.returncode:
        raise EvidenceError("Git checkout inspection failed")
    return result.stdout.strip()


def checkout_identity(repo: Path) -> str:
    if any(not (repo / name).is_file() for name in SOURCE_FILES):
        raise EvidenceError("Complete source checkout required; patch bundles are insufficient")
    if Path(git_value(repo, "rev-parse", "--show-toplevel")).resolve() != repo:
        raise EvidenceError("Repository root does not match the selected checkout")
    if git_value(repo, "status", "--porcelain", "--untracked-files=all"):
        raise EvidenceError("Use a clean isolated checkout; local changes are never reset")
    tracked = git_value(repo, "ls-files", "-z").split("\0")
    if any(name and not (repo / name).exists() and not (repo / name).is_symlink() for name in tracked):
        raise EvidenceError("Checkout has missing tracked files; sparse snapshots are insufficient")
    return git_value(repo, "rev-parse", "HEAD")


def verify(repo: Path, output: Path, timeout: int) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema": SCHEMA, "status": "blocked", "source_revision": None, "gates": [],
        "validation_scope": "complete Go/Python suites plus required Quick/install cases",
        "release_authorized": False, "real_agent_evaluation": "not-run",
        "python_version": sys.version.split()[0],
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    env = os.environ.copy()
    # Resolve neither a different Go workspace nor an automatic toolchain/module download.
    env.update(GOWORK="off", GOTOOLCHAIN="local", GOPROXY="off", GOFLAGS="-mod=readonly")
    env.pop("PYTEST_ADDOPTS", None)
    try:
        revision = checkout_identity(repo)
        report["source_revision"] = revision
        for dependency in ("pytest", "xdist", "ruff"):
            if importlib.util.find_spec(dependency) is None:
                raise EvidenceError(f"Prepared Python environment missing {dependency}")
        package_spec = importlib.util.find_spec("specify_cli")
        if package_spec is None or package_spec.origin is None or Path(package_spec.origin).resolve() != repo / "src/specify_cli/__init__.py":
            raise EvidenceError("The prepared Python environment must import this checkout of specify_cli")
        runtime = repo / "tools/specify-runtime"
        module = next((line.split()[1] for line in (runtime / "go.mod").read_text().splitlines()
                       if line.startswith("module ") and len(line.split()) == 2), "")
        if not module:
            raise EvidenceError("Runtime module identity missing")
        preflight = execute(["go", "list", "-deps", "-test", "./..."], runtime,
                            output, "go-preflight", timeout, env)
        report["gates"].append(preflight)
        if preflight["status"] != "passed":
            raise EvidenceError("Go dependency preflight failed; inspect its local log")
        commands = (
            ("go-tests", ["go", "test", "-json", "-count=1", "./..."], runtime),
            ("go-vet", ["go", "vet", "./..."], runtime),
            ("pytest", [sys.executable, "-m", "pytest", "-n", "auto",
                        "--junitxml", str(output / "pytest.xml")], repo),
            ("ruff", [sys.executable, "-m", "ruff", "check", "src/", "--select", "E4,E7,E9,F"], repo),
        )
        for name, argv, cwd in commands:
            gate = execute(argv, cwd, output, name, timeout, env)
            if gate["status"] == "passed":
                try:
                    if name == "go-tests":
                        gate["test_events"] = inspect_go_log(output / f"{name}.stdout.log", module)
                    elif name == "pytest":
                        gate["test_cases"] = inspect_pytest_report(output / "pytest.xml")
                except EvidenceError as exc:
                    gate.update(status="failed", reason=str(exc))
            report["gates"].append(gate)
        if checkout_identity(repo) != revision:
            raise EvidenceError("Source changed during validation; results are not a bound pass")
        states = {gate["status"] for gate in report["gates"]}
        report["status"] = "failed" if "failed" in states else "blocked" if "blocked" in states else "passed"
    except (EvidenceError, OSError, KeyboardInterrupt) as exc:
        report["reason"] = str(exc) if isinstance(exc, EvidenceError) else type(exc).__name__
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=ROOT)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=1800, help="Per-command limit; not an estimate.")
    args = parser.parse_args(argv)
    repo, output = args.repo.resolve(), args.output_dir.resolve()
    if args.timeout_seconds <= 0:
        parser.error("--timeout-seconds must be positive")
    if output.is_relative_to(repo):
        parser.error("--output-dir must be outside the checkout")
    try:
        output.mkdir(mode=0o700)  # Exclusive creation; never reuse evidence from an earlier run.
    except OSError:
        print("A new output directory with an existing parent is required.", file=sys.stderr)
        return 2
    report = verify(repo, output, args.timeout_seconds)
    text = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    (output / "summary.json").write_text(text, encoding="utf-8")
    print(text, end="")
    return {"passed": 0, "failed": 1, "blocked": 2}[report["status"]]


if __name__ == "__main__":
    raise SystemExit(main())
