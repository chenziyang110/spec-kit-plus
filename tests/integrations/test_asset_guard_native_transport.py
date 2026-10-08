"""Exercise installed native JSON hooks without activating a workflow."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]


def _git(project, *args):
    return subprocess.run(["git", *args], cwd=project, check=True, capture_output=True, text=True).stdout.strip()


@pytest.fixture(params=["claude", "gemini"])
def native(tmp_path, request):
    integration = request.param
    project = tmp_path / "project with spaces"
    project.mkdir()
    _git(project, "init", "-q")
    _git(project, "config", "user.name", "Hook Test")
    _git(project, "config", "user.email", "hook@example.invalid")
    (project / "app.py").write_text("value = 1\n", encoding="utf-8")
    _git(project, "add", "app.py")
    _git(project, "commit", "-qm", "fixture")
    dispatcher = project / f".{integration}/hooks/{integration}-hook-dispatch.py"
    dispatcher.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / f"src/specify_cli/integrations/{integration}/hooks/{integration}-hook-dispatch.py", dispatcher)
    helper = project / ".specify/bin/specify-asset-guard.py"
    helper.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / "src/specify_cli/shared_hooks/specify-asset-guard.py", helper)
    runtime = helper.parent / "fixture-runtime.py"
    runtime.write_text(
        "import json,sys\n"
        "args=sys.argv[1:]\n"
        "paths=[args[i+1] for i,x in enumerate(args[:-1]) if x=='--path']\n"
        "deleted=[args[i+1] for i,x in enumerate(args[:-1]) if x=='--deleted-path']\n"
        "bad=[p for p in paths if 'Wrong Name' in p or p.startswith('.specify/features/')]\n"
        "path_only='--path-only' in args\n"
        "payload={'status':'blocked' if bad else 'ok','data':{'checked':len(set(paths)),'path_only':path_only,'scope':'paths' if path_only else 'worktree','deleted_paths':deleted,'violation_count':len(bad)},'items':[{'path':p,'message':'choose the governed path'} for p in bad]}\n"
        "print(json.dumps(payload))\n"
        "sys.exit(10 if bad else 0)\n",
        encoding="utf-8",
    )
    (project / ".specify/config.json").write_text(json.dumps({"runtime_launcher": {"argv": [sys.executable, str(runtime)]}}), encoding="utf-8")
    return integration, project, dispatcher


def invoke(native, route, payload):
    integration, project, dispatcher = native
    env = dict(os.environ)
    env[f"{integration.upper()}_PROJECT_DIR"] = str(project)
    result = subprocess.run([sys.executable, str(dispatcher), route], cwd=project, input=json.dumps(payload), capture_output=True, text=True, timeout=10, env=env)
    assert result.returncode == 0, result.stderr
    assert result.stderr == ""
    return json.loads(result.stdout) if result.stdout.strip() else {}


def before_route(native, *, shell=False):
    return ("pre-tool-bash" if shell else "pre-tool-write") if native[0] == "claude" else "before-tool"


def finish_route(native):
    return "stop-monitor" if native[0] == "claude" else "after-agent"


def write_payload(native, path):
    return {"session_id": "same-session", "tool_name": "Write" if native[0] == "claude" else "write_file", "tool_input": {"file_path": path}}


def assert_denied(native, output, *, finish=False):
    if native[0] == "claude" and not finish:
        assert output["hookSpecificOutput"]["permissionDecision"] == "deny"
    else:
        assert output["decision"] in {"deny", "block"}


def test_native_write_before_check_blocks_bad_path_without_workflow(native):
    output = invoke(native, before_route(native), write_payload(native, "Wrong Name.md"))
    assert_denied(native, output)
    assert "governed path" in json.dumps(output)
    project = native[1]
    assert not (project / "Wrong Name.md").exists()
    assert not (project / ".specify/runtime/asset-observations").exists()
    assert not (project / ".specify/features").exists()


@pytest.mark.parametrize("path", [".asset-policy.json", ".github/workflows/ci.yml", "AGENTS.md"])
def test_native_write_before_allows_authorized_configuration_maintenance(native, path):
    output = invoke(native, before_route(native), write_payload(native, path))
    assert output.get("decision") not in {"deny", "block"}
    assert output.get("hookSpecificOutput", {}).get("permissionDecision") != "deny"
    assert "unavailable" not in json.dumps(output).lower()
    assert invoke(native, finish_route(native), {"session_id": "same-session"}) == {}
    assert not (native[1] / ".specify/runtime/asset-observations").exists()


def test_native_write_before_preserves_canonical_owner_boundary(native):
    output = invoke(native, before_route(native), write_payload(native, ".specify/features/demo/spec.md"))
    assert_denied(native, output)
    assert not (native[1] / ".specify/runtime/asset-observations").exists()


def test_native_end_of_turn_checks_shell_created_files_and_cleanup_after_repair(native):
    project = native[1]
    payload = {"session_id": "same-session", "tool_name": "Bash" if native[0] == "claude" else "run_shell_command", "tool_input": {"command": "python create_report.py"}}
    assert invoke(native, before_route(native, shell=True), payload) == {}
    target = project / "Wrong Name.md"
    target.write_text("# Report\n", encoding="utf-8")
    output = invoke(native, finish_route(native), {"session_id": "same-session"})
    assert_denied(native, output, finish=True)
    assert "ownership before changing another actor's files" in json.dumps(output)
    assert target.read_text() == "# Report\n"
    destination = project / "docs/reports/report.md"
    destination.parent.mkdir(parents=True)
    target.rename(destination)
    assert invoke(native, finish_route(native), {"session_id": "same-session"}) == {}
    assert not (project / ".specify/runtime/asset-observations").exists()
    assert not (project / ".specify/bin/__pycache__").exists()


def test_native_chat_and_read_shell_create_no_observation(native):
    project = native[1]
    payload = {"session_id": "same-session", "tool_name": "Bash" if native[0] == "claude" else "run_shell_command", "tool_input": {"command": "git status --short"}}
    assert invoke(native, before_route(native, shell=True), payload) == {}
    assert invoke(native, finish_route(native), {"session_id": "same-session"}) == {}
    assert not (project / ".specify/runtime").exists()
    assert not (project / ".specify/bin/__pycache__").exists()


def test_native_old_runtime_is_explicitly_unverified(native):
    project = native[1]
    runtime = project / ".specify/bin/fixture-runtime.py"
    runtime.write_text("import json,sys\nprint(json.dumps({'status':'usage-error','message':'unknown command assets'}))\nsys.exit(2)\n", encoding="utf-8")
    output = invoke(native, before_route(native), write_payload(native, "docs/guide.md"))
    assert "unavailable" in json.dumps(output).lower()
    assert "do not claim" in json.dumps(output).lower()
    assert "permissionDecision" not in json.dumps(output)


def test_native_gate_denial_is_preserved_without_observation(native):
    if native[0] != "claude":
        pytest.skip("the existing Claude cognition owner gate has a direct native denial")
    output = invoke(native, before_route(native), write_payload(native, ".specify/project-cognition/project-cognition.db"))
    assert_denied(native, output)
    assert not (native[1] / ".specify/runtime/asset-observations").exists()


@pytest.fixture(scope="session")
def real_asset_runtime(request):
    if shutil.which("go") is None:
        pytest.skip("Go is required for the native hook/runtime integration contract")
    return request.getfixturevalue("built_unified_runtime")


def test_native_hooks_use_real_go_rules_and_recheck_shell_outputs(native, real_asset_runtime):
    """Prove the transport fixture agrees with the real pinned command surface."""
    project = native[1]
    (project / ".specify/config.json").write_text(
        json.dumps({"runtime_launcher": {"argv": [str(real_asset_runtime)]}}),
        encoding="utf-8",
    )
    for path in (".asset-policy.json", ".github/workflows/ci.yml", "AGENTS.md", "src/app.py"):
        output = invoke(native, before_route(native), write_payload(native, path))
        assert output.get("decision") not in {"deny", "block"}, output
        assert output.get("hookSpecificOutput", {}).get("permissionDecision") != "deny", output
        assert "unavailable" not in json.dumps(output).lower(), output
        assert invoke(native, finish_route(native), {"session_id": "same-session"}) == {}
    output = invoke(native, before_route(native), write_payload(native, ".specify/features/demo/spec.md"))
    assert_denied(native, output)

    existing = project / "untouched-legacy-report.md"
    existing.write_text("Existing report outside this task.\n", encoding="utf-8")
    payload = {
        "session_id": "same-session",
        "tool_name": "Bash" if native[0] == "claude" else "run_shell_command",
        "tool_input": {"command": "python generate.py"},
    }
    assert invoke(native, before_route(native, shell=True), payload) == {}
    target = project / "Wrong Name.md"
    target.write_text("# Integration report\n", encoding="utf-8")
    output = invoke(native, finish_route(native), {"session_id": "same-session"})
    assert_denied(native, output, finish=True)
    assert "untouched-legacy-report.md" not in json.dumps(output)

    routed = subprocess.run(
        [str(real_asset_runtime), "assets", "route", "--purpose", "report", "--slug", "integration-smoke", "--format", "json"],
        cwd=project,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert routed.returncode == 0, routed.stdout + routed.stderr
    destination = project / json.loads(routed.stdout)["data"]["path"]
    destination.parent.mkdir(parents=True, exist_ok=True)
    target.rename(destination)
    assert invoke(native, finish_route(native), {"session_id": "same-session"}) == {}
    assert existing.read_text(encoding="utf-8") == "Existing report outside this task.\n"
    assert not (project / ".specify/runtime/asset-observations").exists()
    assert not (project / ".specify/features").exists()
