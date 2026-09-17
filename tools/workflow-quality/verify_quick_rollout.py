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
from typing import Any, Mapping, Sequence

SCHEMA = "quick-rollout-verification-v2"
ROOT = Path(__file__).resolve().parents[2]
INSTALL_MODULE = "tests.integrations.test_quick_optimization_installation"
INSTALL_CASES = (
    *(f"test_advanced_quick_policy_survives_install[{host}-{shell}]"
      for host in ("codex", "cursor-agent") for shell in ("sh", "ps")),
    *(f"test_classic_quick_keeps_worker_default[{host}]"
      for host in ("codex", "cursor-agent")),
    "test_quick_policy_repair_preserves_user_changes",
)
SHADOW_ENTRYPOINT_CASES = (
    "TestQuickShadowCLIEntrypointReadsRealOwnerWithoutWrites",
    "TestQuickShadowCLIEntrypointBlocksDependenciesWithoutRepair",
    "TestQuickShadowCLIEntrypointHelpBeforeRepositoryAccess",
    "TestQuickShadowCLIEntrypointFreshStateOnEveryInvocation",
    "TestQuickShadowCLIEntrypointDiscoveryAgrees",
    "TestQuickShadowCLIEntrypointUsesQueryTimeout",
    "TestQuickShadowCLIEntrypointCancelledBeforeProjectAccess",
    "TestQuickShadowCLIEntrypointCancellationReachesGit",
    "TestQuickShadowCLIEntrypointPreservesLegacyDescriptors",
    "TestQuickShadowCLIEntrypointShowSelectorsAndMixedPack",
    "TestQuickShadowCLIStateReadyAfterAcceptedPrerequisite",
    "TestQuickShadowCLIStateExactNumbersReachOutput",
    "TestQuickShadowCLIStateAliasesCannotClearBlockers",
)
CONTEXT_CASES = (
    "TestBoundContextPreservesEveryInput",
    "TestDecodeDoesNotAuthorizeFreshness",
    "TestQuickShadowRetainsWholeOwnerContract",
)
GO_TEST_PACKAGE_TEMPLATE = "{{if or .TestGoFiles .XTestGoFiles}}{{.ImportPath}}{{end}}"
GO_CASES = (
    *SHADOW_ENTRYPOINT_CASES,
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


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceError("Go report contains a duplicate JSON key")
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise EvidenceError(f"Go report contains a non-finite JSON number: {value}")


def required_go_groups(module: str) -> dict[str, Sequence[str]]:
    return {module: GO_CASES, module + "/context": CONTEXT_CASES}


def read_go_packages(path: Path, module: str) -> tuple[str, ...]:
    """Read the host's actual test-package inventory, generated before testing."""
    try:
        with path.open("rb") as stream:
            raw = stream.read(2 * 1024 * 1024 + 1)
        if len(raw) > 2 * 1024 * 1024:
            raise EvidenceError("Go package inventory exceeds its read limit")
        packages = tuple(line for line in raw.decode("utf-8").splitlines() if line)
    except (OSError, UnicodeError) as exc:
        raise EvidenceError("Go package inventory is missing or malformed") from exc
    if (not packages or not module or module not in packages or
            len(set(packages)) != len(packages) or
            any(any(char.isspace() or ord(char) < 32 for char in name) or
                not (name == module or name.startswith(module + "/")) for name in packages)):
        raise EvidenceError("Go package inventory must contain unique module-local package names")
    return packages


def inspect_go_log(path: Path, package: str, required: Sequence[str] = GO_CASES, *,
                   expected_packages: Sequence[str] = (),
                   required_groups: Mapping[str, Sequence[str]] | None = None) -> dict[str, int]:
    """Reject unfinished streams as well as missing/skipped required cases.

    Optional platform-test skips remain visible. Every observed package/test
    must terminate; every inventoried test package must pass. This checks log
    completeness, not authenticity against a hostile writer or source identity.
    """
    terminal: dict[tuple[str, str], str] = {}
    observed: set[tuple[str, str]] = set()
    failed = False
    total = 0
    try:
        with path.open("rb") as stream:
            while line := stream.readline(4 * 1024 * 1024 + 1):
                total += len(line)
                if len(line) > 4 * 1024 * 1024 or total > 256 * 1024 * 1024:
                    raise EvidenceError("Go report exceeds its bounded read limit")
                if not line.strip():
                    continue
                event = json.loads(line.decode("utf-8"), object_pairs_hook=_unique_object,
                                   parse_constant=_invalid_constant)
                if not isinstance(event, dict):
                    raise EvidenceError("Go report contains a non-object event")
                action = event.get("Action")
                if not isinstance(action, str) or not action:
                    raise EvidenceError("Go event action is missing or invalid")
                if action in ("fail", "build-fail"):
                    failed = True
                # Newer Go versions emit build events using ImportPath, not Package.
                if action in ("build-output", "build-fail"):
                    continue
                owner, test = event.get("Package"), event.get("Test", "")
                if not isinstance(owner, str) or not owner or not isinstance(test, str):
                    raise EvidenceError("Go event has invalid package/test identity")
                observed.add((owner, ""))
                if test:
                    observed.add((owner, test))
                if action not in ("pass", "skip", "fail", "bench"):
                    continue
                key = (owner, test)
                if key in terminal:
                    raise EvidenceError("Go report contains repeated terminal events")
                terminal[key] = action
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceError("Go report is missing or malformed") from exc
    if failed or terminal.get((package, "")) != "pass":
        raise EvidenceError("Go package did not pass")
    if observed - terminal.keys():
        raise EvidenceError("Go report contains unfinished packages or tests")
    if any(terminal.get((name, "")) != "pass" for name in expected_packages):
        raise EvidenceError("An inventoried Go test package was missing, skipped or failed")
    groups = {package: required, **(required_groups or {})}
    for owner, cases in groups.items():
        if terminal.get((owner, "")) != "pass" or any(
                terminal.get((owner, test)) != "pass" for test in cases):
            raise EvidenceError(f"Required Go tests in {owner} were missing, skipped or failed")
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


def checkout_environment() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items()
           if not key.upper().startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_TERMINAL_PROMPT="0", GIT_NO_LAZY_FETCH="1")
    return env


def git_value(repo: Path, *args: str) -> str:
    try:
        result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                                text=True, timeout=30, check=False, env=checkout_environment())
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise EvidenceError("Git checkout inspection unavailable") from exc
    if result.returncode:
        raise EvidenceError("Git checkout inspection failed")
    return result.stdout.rstrip("\n")


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
        "validation_scope": "complete Go/Python suites plus required Quick/shadow/context/install cases",
        "release_authorized": False, "real_agent_evaluation": "not-run",
        "python_version": sys.version.split()[0],
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    env = checkout_environment()
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
        inventory = execute(["go", "list", "-f", GO_TEST_PACKAGE_TEMPLATE, "./..."], runtime,
                            output, "go-packages", timeout, env)
        report["gates"].append(inventory)
        if inventory["status"] != "passed":
            raise EvidenceError("Go test-package inventory failed; inspect its local log")
        packages = read_go_packages(output / "go-packages.stdout.log", module)
        report["expected_go_test_packages"] = list(packages)
        report["required_go_cases"] = required_go_groups(module)
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
                        gate["test_events"] = inspect_go_log(
                            output / f"{name}.stdout.log", module, expected_packages=packages,
                            required_groups=required_go_groups(module))
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


def inspect_go_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Inspect existing Go evidence; do not execute tests.")
    parser.add_argument("--inspect-go-log", type=Path, required=True)
    parser.add_argument("--go-packages", type=Path, required=True)
    parser.add_argument("--module", required=True)
    args = parser.parse_args(argv)
    result: dict[str, Any] = {
        "schema": "quick-go-evidence-v1", "status": "failed",
        "validation_scope": "existing Go log and host test-package inventory only",
        "tests_executed_by_inspector": False, "release_authorized": False,
    }
    try:
        packages = read_go_packages(args.go_packages, args.module)
        result["test_events"] = inspect_go_log(
            args.inspect_go_log, args.module, expected_packages=packages,
            required_groups=required_go_groups(args.module))
        result.update(status="passed", expected_test_packages=list(packages))
    except EvidenceError as exc:
        result["reason"] = str(exc)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["status"] == "passed" else 1


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if any(arg == "--inspect-go-log" or arg.startswith("--inspect-go-log=") for arg in argv):
        return inspect_go_main(argv)
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
