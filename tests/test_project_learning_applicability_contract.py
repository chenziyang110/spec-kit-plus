"""Real native Learning wire records and installed profile consumer contracts."""

import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import shutil

import jsonschema
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "templates/project-learning-record-schema.json"


@pytest.fixture(scope="module")
def runtime(tmp_path_factory):
    supplied = os.environ.get("SPECIFY_LEARNING_APPLICABILITY_TEST_BIN")
    if supplied:
        return Path(supplied)
    target = tmp_path_factory.mktemp("learning-native") / "specify-runtime.exe"
    result = subprocess.run(["go", "build", "-o", str(target), "."], cwd=ROOT / "tools/specify-runtime", capture_output=True, text=True, timeout=180)
    assert result.returncode == 0, result.stdout + result.stderr
    return target


@pytest.fixture(scope="module")
def records(runtime, tmp_path_factory):
    root = tmp_path_factory.mktemp("learning-wire")
    (root / "src/owner").mkdir(parents=True)
    source = root / "src/owner/entry.go"
    source.write_text("package owner\nconst Retry = true\n", encoding="utf-8")
    (root / "constraints.json").write_text('{"retry":"bounded"}', encoding="utf-8")
    (root / "counterexample.txt").write_text("Current reproduced counterexample", encoding="utf-8")

    def call(*args):
        result = subprocess.run([str(runtime), "learning", *args, "--project-root", str(root), "--format", "json"], capture_output=True, text=True, encoding="utf-8", timeout=30)
        assert result.returncode == 0, result.stdout + result.stderr
        return json.loads(result.stdout)["data"]

    capture = ("capture", "--command", "debug", "--type", "tooling_trap", "--summary", "Preserve diagnostics after watcher recovery", "--evidence", "Repeated watcher failure recovered with retained diagnostics", "--recurrence-key", "debug.wire", "--component", "src/owner", "--source-file", "src/owner/entry.go", "--constraint-file", "constraints.json", "--evidence-kind", "recovery", "--signal", "high")
    call(*capture)
    call(*capture)
    context = ("--context", "component=src/owner", "--context", "constraint_file=constraints.json")
    result = {
        "start": call("start", "--command", "debug", *context),
        "list": call("list", "--command", "debug", *context),
        "show": call("show", "--ref", "debug.wire", *context),
        "wrong-component": call("show", "--ref", "debug.wire", "--context", "component=src/other"),
        "counterevidence": call("show", "--ref", "debug.wire", *context, "--context", "counterevidence_file=counterexample.txt"),
        "missing-context": call("show", "--ref", "debug.wire"),
    }
    source.write_text("package owner\nconst Retry = null\n", encoding="utf-8")
    result["changed-source"] = call("show", "--ref", "debug.wire", *context)
    call("capture", "--command", "debug", "--type", "tooling_trap", "--summary", "Legacy diagnostic lesson", "--evidence", "Observed recovery", "--recurrence-key", "debug.legacy")
    result["legacy"] = call("show", "--ref", "debug.legacy")
    output = os.environ.get("SPECIFY_LEARNING_APPLICABILITY_TEST_RECORDS")
    if output:
        Path(output).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def test_actual_native_read_records_preserve_strict_schema(records):
    schema = json.loads(SCHEMA.read_text(encoding="utf-8-sig"))
    jsonschema.Draft202012Validator.check_schema(schema)
    validator = jsonschema.Draft202012Validator(schema)
    for name, record in records.items():
        errors = list(validator.iter_errors(record))
        assert not errors, (name, [e.message for e in errors])
    assert records["start"]["needs_confirmation"][0]["applicability"]["applicable"] is True
    assert records["show"]["applicability"]["state"] == "applicable"
    for name in ("wrong-component", "counterevidence", "changed-source"):
        assert records[name]["applicability"]["state"] == "rejected"
    assert records["legacy"]["applicability"]["state"] == "degraded"


@pytest.mark.parametrize("mutation", ["unknown", "wrong-type", "unknown-version", "unknown-state", "nested-unknown", "safety-unknown", "context-unknown"])
def test_applicability_schema_refuses_invalid_wire_values(records, mutation):
    record = copy.deepcopy(records["start"])
    proof = record["items"][0]["applicability"]
    if mutation == "unknown":
        record["caller_claim"] = True
    elif mutation == "wrong-type":
        proof["applicable"] = "true"
    elif mutation == "unknown-version":
        proof["version"] = "learning-applicability.v999"
    elif mutation == "unknown-state":
        proof["state"] = "verified"
    elif mutation == "nested-unknown":
        proof["caller_sha256"] = "a" * 64
    elif mutation == "safety-unknown":
        record["items"][0]["assessment"]["content_safety"]["raw_token"] = "unsafe"
    else:
        record["task_context"]["arbitrary"] = ["owner"]
    validator = jsonschema.Draft202012Validator(json.loads(SCHEMA.read_text(encoding="utf-8-sig")))
    assert list(validator.iter_errors(record))


@pytest.mark.parametrize("profile", ["classic", "advanced"])
def test_real_installed_profiles_preserve_bound_learning_contract(tmp_path, profile, runtime):
    from specify_cli.integrations.codex import CodexIntegration
    from specify_cli.integrations.manifest import IntegrationManifest
    from specify_cli.specify_runtime import project_runtime_launcher_arg, project_runtime_entrypoint_path

    target = tmp_path / profile
    binary = project_runtime_entrypoint_path(target)
    binary.parent.mkdir(parents=True)
    shutil.copy2(runtime, binary)
    relative = project_runtime_launcher_arg()
    (target / ".specify/config.json").write_text(json.dumps({"runtime_launcher": {"argv": [relative]}, "runtime_launcher_binding": {"runtime_entrypoint": relative, "runtime_binary_sha256": hashlib.sha256(binary.read_bytes()).hexdigest()}}), encoding="utf-8")
    integration = CodexIntegration()
    integration.setup(target, IntegrationManifest("codex", target), {"workflow_profile": profile})
    skills = target / ".codex/skills"
    if profile == "classic":
        path = skills / "sp-implement/SKILL.md"
        passive = skills / "spec-kit-project-learning/SKILL.md"
        assert passive.exists()
        text = path.read_text(encoding="utf-8") + passive.read_text(encoding="utf-8")
    else:
        path = skills / "spx-implement/SKILL.md"
        shared = skills / "spx-implement/references/project-learning.md"
        assert shared.exists()
        assert not (skills / "spec-kit-project-learning").exists()
        text = path.read_text(encoding="utf-8") + shared.read_text(encoding="utf-8")
    for value in ("learning.applicability.v1", "component=src/owner", "constraint_file=constraints.json", "counterevidence_file=tests/current-counterexample.txt", "reason_codes", "--source-file", "--evidence-kind", "Do-before-Learning", "Gold/scoring"):
        assert value in text
    assert "{{specify-subcmd:" not in text
    assert ".specify/bin/specify-runtime" in text.replace("\\", "/")


def test_both_profile_intake_exceptions_and_lifecycle_preserved():
    for path in (ROOT / "templates/command-partials/common/learning-layer.md", ROOT / "templates/advanced-skills/_shared/project-learning.md", ROOT / "templates/passive-skills/spec-kit-project-learning/SKILL.md"):
        text = path.read_text(encoding="utf-8")
        assert "context-direct" in text
        assert "read-only" in text
        assert "candidate cannot become a rule directly" in text.lower()
        assert "graph freshness" in text.lower()
        assert "ordinary success" in text.lower() or "ordinary-success" in text.lower()
