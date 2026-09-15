"""Verification-runner tests; these do not claim the target workflow passed."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_quick_rollout", ROOT / "tools/workflow-quality/verify_quick_rollout.py"
)
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class RolloutVerificationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.log = self.root / "go.jsonl"
        self.xml = self.root / "pytest.xml"
        self.package = "example.invalid/fixture"

    def go_events(self):
        return [{"Action": "pass", "Package": self.package, "Test": test}
                for test in runner.GO_CASES] + [{"Action": "pass", "Package": self.package}]

    def write_go(self, events):
        self.log.write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")

    def xml_tree(self):
        root = ET.Element("testsuites")
        suite = ET.SubElement(root, "testsuite", errors="0", failures="0")
        for name in runner.INSTALL_CASES:
            ET.SubElement(suite, "testcase", classname=runner.INSTALL_MODULE, name=name)
        return root

    def write_xml(self, root):
        self.xml.write_bytes(ET.tostring(root))

    def test_go_requires_package_and_all_lifecycle_cases(self):
        self.write_go(self.go_events())
        self.assertEqual(runner.inspect_go_log(self.log, self.package)["pass"], len(runner.GO_CASES))
        for index in (0, -1, -2):
            with self.subTest(missing=index):
                events = self.go_events()
                del events[index]
                self.write_go(events)
                with self.assertRaises(runner.EvidenceError):
                    runner.inspect_go_log(self.log, self.package)

    def test_go_skip_failure_or_duplicate_is_not_pass(self):
        for action in ("skip", "fail"):
            events = self.go_events()
            events[0]["Action"] = action
            self.write_go(events)
            with self.subTest(action=action), self.assertRaises(runner.EvidenceError):
                runner.inspect_go_log(self.log, self.package)
        for extra in (self.go_events()[0], {"Action": "build-fail", "Package": "other"},
                      {"Action": "fail", "Package": "other", "Test": "TestUnrelated"}):
            self.write_go(self.go_events() + [extra])
            with self.subTest(extra=extra), self.assertRaises(runner.EvidenceError):
                runner.inspect_go_log(self.log, self.package)

    def test_go_malformed_or_wrong_package_is_rejected(self):
        for raw in ("", "not-json", "[]\n"):
            self.log.write_text(raw, encoding="utf-8")
            with self.subTest(raw=raw), self.assertRaises(runner.EvidenceError):
                runner.inspect_go_log(self.log, self.package)
        self.write_go(self.go_events())
        with self.assertRaises(runner.EvidenceError):
            runner.inspect_go_log(self.log, "other-module")

    def test_pytest_requires_exact_installed_cases(self):
        self.write_xml(self.xml_tree())
        self.assertEqual(runner.inspect_pytest_report(self.xml)["pass"], len(runner.INSTALL_CASES))
        for missing in runner.INSTALL_CASES:
            root = self.xml_tree()
            suite = root.find("testsuite")
            suite.remove(next(case for case in suite if case.get("name") == missing))
            self.write_xml(root)
            with self.subTest(missing=missing), self.assertRaises(runner.EvidenceError):
                runner.inspect_pytest_report(self.xml)

    def test_pytest_skip_failure_summary_or_duplicates_rejected(self):
        for change in ("skip", "failure", "error", "summary", "duplicate", "wrong-module"):
            root = self.xml_tree()
            suite = root.find("testsuite")
            case = suite[0]
            if change == "skip":
                ET.SubElement(case, "skipped")
            elif change in ("failure", "error"):
                ET.SubElement(case, change)
            elif change == "summary":
                suite.set("errors", "1")
            elif change == "duplicate":
                ET.SubElement(suite, "testcase", case.attrib)
            else:
                case.set("classname", "unrelated.module")
            self.write_xml(root)
            with self.subTest(change=change), self.assertRaises(runner.EvidenceError):
                runner.inspect_pytest_report(self.xml)

    def test_pytest_empty_malformed_and_dtd_rejected(self):
        for raw in (b"", b"<bad>", b"<testsuites/>", b"<not-tests/>",
                    b'<!DOCTYPE test [<!ENTITY x "unsafe">]><testsuites/>'):
            self.xml.write_bytes(raw)
            with self.subTest(raw=raw), self.assertRaises(runner.EvidenceError):
                runner.inspect_pytest_report(self.xml)

    def test_nonrequired_platform_skip_is_reported_not_hidden(self):
        events = self.go_events() + [{"Action": "skip", "Package": self.package, "Test": "TestOtherOS"}]
        self.write_go(events)
        self.assertEqual(runner.inspect_go_log(self.log, self.package)["skip"], 1)
        root = self.xml_tree()
        case = ET.SubElement(root.find("testsuite"), "testcase", classname="other", name="other_os")
        ET.SubElement(case, "skipped")
        self.write_xml(root)
        self.assertEqual(runner.inspect_pytest_report(self.xml)["skip"], 1)

    def test_process_exit_and_log_preservation(self):
        result = runner.execute([sys.executable, "-c", "print('observed'); raise SystemExit(3)"],
                                self.root, self.root, "child", 10, os.environ.copy())
        self.assertEqual(result["status"], "failed")
        self.assertEqual(result["exit_code"], 3)
        path = self.root / "child.stdout.log"
        before = path.read_bytes()
        self.assertIn(b"observed", before)
        with self.assertRaises(FileExistsError):
            runner.execute([sys.executable, "-c", "print('overwrite')"],
                           self.root, self.root, "child", 10, os.environ.copy())
        self.assertEqual(path.read_bytes(), before)

    def test_process_missing_and_timeout_are_not_pass(self):
        result = runner.execute([str(self.root / "missing-executable")], self.root, self.root,
                                "missing", 10, os.environ.copy())
        self.assertEqual(result["status"], "blocked")
        result = runner.execute([sys.executable, "-c", "import time; time.sleep(60)"],
                                self.root, self.root, "timeout", 1, os.environ.copy())
        self.assertEqual(result["reason"], "timeout")
        self.assertNotEqual(result["status"], "passed")

    def test_partial_snapshot_returns_blocked_without_test_execution(self):
        repo = self.root / "partial"
        repo.mkdir()
        output = self.root / "evidence"
        with contextlib.redirect_stdout(io.StringIO()):
            code = runner.main(["--repo", str(repo), "--output-dir", str(output)])
        self.assertEqual(code, 2)
        report = json.loads((output / "summary.json").read_text())
        self.assertEqual(report["status"], "blocked")
        self.assertEqual(report["gates"], [])
        self.assertFalse(report["release_authorized"])
        self.assertEqual(report["real_agent_evaluation"], "not-run")
        before = (output / "summary.json").read_bytes()
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(runner.main(["--repo", str(repo), "--output-dir", str(output)]), 2)
        self.assertEqual((output / "summary.json").read_bytes(), before)

    def test_output_inside_checkout_is_rejected(self):
        repo = self.root / "checkout"
        repo.mkdir()
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            runner.main(["--repo", str(repo), "--output-dir", str(repo / "evidence")])
        self.assertFalse((repo / "evidence").exists())

    def test_real_pytest_skipped_case_cannot_satisfy_gate(self):
        fixture = self.root / "test_fixture.py"
        fixture.write_text(
            'import pytest\ndef test_ok(): pass\n'
            '@pytest.mark.skip(reason="fixture")\ndef test_missing(): pass\n'
        )
        env = os.environ.copy()
        env["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        env.pop("PYTEST_ADDOPTS", None)
        result = runner.execute([sys.executable, "-m", "pytest", "-q", str(fixture),
                                 "--junitxml", str(self.xml)],
                                self.root, self.root, "pytest-fixture", 60, env)
        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(runner.inspect_pytest_report(self.xml, "test_fixture", ("test_ok",)),
                         {"pass": 1, "skip": 1})
        with self.assertRaises(runner.EvidenceError):
            runner.inspect_pytest_report(self.xml, "test_fixture", ("test_ok", "test_missing"))

    def test_aggregate_requires_reports_and_stable_source(self):
        # Synthetic orchestration test, not execution of the repository suites.
        runtime = self.root / "tools/specify-runtime"
        runtime.mkdir(parents=True)
        (runtime / "go.mod").write_text(f"module {self.package}\n")
        spec = SimpleNamespace(origin=str(self.root / "src/specify_cli/__init__.py"))
        observed = []

        def fake_execute(argv, cwd, output, name, timeout, env):
            observed.append((name, argv, env))
            if name == "go-tests":
                (output / "go-tests.stdout.log").write_text(
                    "".join(json.dumps(event) + "\n" for event in self.go_events())
                )
            elif name == "pytest":
                self.write_xml(self.xml_tree())
            return {"name": name, "status": "passed", "exit_code": 0}

        for end_revision, expected in (("a" * 40, "passed"), ("b" * 40, "blocked")):
            observed.clear()
            with patch.object(runner, "checkout_identity", side_effect=["a" * 40, end_revision]), \
                    patch.object(runner.importlib.util, "find_spec", return_value=spec), \
                    patch.object(runner, "execute", side_effect=fake_execute):
                report = runner.verify(self.root, self.root, 60)
            self.assertEqual(report["status"], expected)
            self.assertEqual([name for name, _, _ in observed],
                             ["go-preflight", "go-tests", "go-vet", "pytest", "ruff"])
            self.assertEqual(observed[1][1], ["go", "test", "-json", "-count=1", "./..."])
            self.assertEqual(observed[1][2]["GOPROXY"], "off")
            self.assertFalse(report["release_authorized"])

    def test_python_environment_from_other_checkout_is_blocked(self):
        spec = SimpleNamespace(origin=str(self.root / "wrong/specify_cli/__init__.py"))
        with patch.object(runner, "checkout_identity", return_value="a" * 40), \
                patch.object(runner.importlib.util, "find_spec", return_value=spec), \
                patch.object(runner, "execute") as execute:
            report = runner.verify(self.root, self.root, 60)
        self.assertEqual(report["status"], "blocked")
        execute.assert_not_called()

    @unittest.skipUnless(shutil.which("go"), "requires a local Go toolchain")
    def test_real_go_zero_test_exit_cannot_satisfy_gate(self):
        # Real toolchain, tiny isolated stdlib-only module; not the product runtime.
        (self.root / "go.mod").write_text(f"module {self.package}\n\ngo 1.20\n")
        (self.root / "fixture_test.go").write_text(
            'package fixture\nimport "testing"\nfunc TestPresent(t *testing.T) {}\n'
        )
        env = os.environ.copy()
        env.update(GOPROXY="off", GOTOOLCHAIN="local", GOWORK="off", GOFLAGS="")
        for pattern, name in (("^NoSuchTest$", "empty"), ("^TestPresent$", "actual")):
            result = runner.execute(["go", "test", "-json", "-count=1", "-run", pattern, "."],
                                    self.root, self.root, name, 60, env)
            self.assertEqual(result["exit_code"], 0)
            path = self.root / f"{name}.stdout.log"
            if name == "empty":
                with self.assertRaises(runner.EvidenceError):
                    runner.inspect_go_log(path, self.package, ("TestPresent",))
            else:
                self.assertEqual(runner.inspect_go_log(path, self.package, ("TestPresent",))["pass"], 1)


if __name__ == "__main__":
    unittest.main()
