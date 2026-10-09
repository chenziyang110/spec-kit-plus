"""Native hooks delegate policy to Go and retain only bounded observations."""

import importlib.util
import json
import shlex
from pathlib import Path
import subprocess
import sys

import pytest


@pytest.fixture
def guard():
    source = Path(__file__).resolve().parents[1] / "src/specify_cli/shared_hooks/specify-asset-guard.py"
    spec = importlib.util.spec_from_file_location("asset_guard_adapter_test", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(project: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=project, check=True, capture_output=True, text=True)
    return result.stdout.strip()


@pytest.fixture
def project(tmp_path):
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.name", "Asset Test")
    git(tmp_path, "config", "user.email", "assets@example.invalid")
    (tmp_path / "app.py").write_text("original = True\n", encoding="utf-8")
    git(tmp_path, "add", "app.py")
    git(tmp_path, "commit", "-qm", "fixture")
    return tmp_path


def event(tool="Write", path="docs/guides/new-guide.md", session="one"):
    return {"session_id": session, "tool_name": tool, "tool_input": {"file_path": path}}


def checker(monkeypatch, guard, *, blocked=False):
    calls = []

    def check(_root, paths, *, path_only, deleted_paths=None):
        calls.append((sorted(paths), path_only))
        return {"status": "blocked" if blocked else "ok", "message": "repair placement", "path_only": path_only}

    monkeypatch.setattr(guard, "check_paths", check)
    return calls


def runtime_program(check_payload: dict, exit_code: int = 0) -> str:
    discovery = {"status": "ok", "data": {"requested": ["assets.check"], "present": ["assets.check"], "missing": []}}
    return (
        "import json,sys\n"
        "if sys.argv[1:3] == ['api','ensure']:\n"
        " print(" + repr(json.dumps(discovery)) + ");sys.exit(0)\n"
        "print(" + repr(json.dumps(check_payload)) + ")\n"
        f"sys.exit({exit_code})\n"
    )


@pytest.mark.parametrize("payload", [
    {},
    {"session_id": "one", "tool_name": "Read", "tool_input": {"file_path": "README.md"}},
    {"session_id": "one", "tool_name": "Bash", "tool_input": {"command": "git rev-parse --show-toplevel"}},
    {"session_id": "one", "tool_name": "Bash", "tool_input": {"command": "rg --files docs && cat README.md"}},
    {"session_id": "one", "tool_name": "Bash", "tool_input": {"command": "sed -n 1,60p README.md"}},
])
def test_chat_and_read_only_tools_leave_no_observation(guard, tmp_path, monkeypatch, payload):
    monkeypatch.setattr(guard, "_status_paths", lambda *_: pytest.fail("read-only task inspected Git"))
    assert guard.before_tool(tmp_path, payload, "claude") == {}
    assert guard.finish_turn(tmp_path, payload, "claude") == {}
    assert list(tmp_path.iterdir()) == []


def test_structured_write_is_checked_without_active_workflow_and_cleans_cache(guard, project, monkeypatch):
    calls = checker(monkeypatch, guard)
    payload = event()
    assert guard.before_tool(project, payload, "claude") == {}
    target = project / "docs/guides/new-guide.md"
    target.parent.mkdir(parents=True)
    target.write_text("# Guide\n", encoding="utf-8")
    assert guard.finish_turn(project, payload, "claude") == {}
    assert calls == [(["docs/guides/new-guide.md"], True), (["docs/guides/new-guide.md"], False)]
    assert not (project / guard.CACHE_ROOT).exists()
    assert not list(project.rglob("workflow*"))


def test_blocked_write_does_not_create_checkpoint(guard, project, monkeypatch):
    checker(monkeypatch, guard, blocked=True)
    result = guard.before_tool(project, event(path="Report Final.md"), "claude")
    assert result["status"] == "blocked"
    assert not (project / ".specify").exists()


def test_initial_dirty_paths_are_not_blanket_exempted(guard, project, monkeypatch):
    calls = checker(monkeypatch, guard)
    (project / "old-report.md").write_text("old report", encoding="utf-8")
    (project / "app.py").write_text("initial dirty", encoding="utf-8")
    payload = {"session_id": "one", "tool_name": "Bash", "tool_input": {"command": "python generate.py"}}
    assert guard.before_tool(project, payload, "claude") == {}
    (project / "app.py").write_text("changed again", encoding="utf-8")
    (project / "new-report.md").write_text("new report", encoding="utf-8")
    assert guard.finish_turn(project, payload, "claude") == {}
    assert calls == [(["app.py", "new-report.md"], False)]
    assert (project / "old-report.md").read_text() == "old report"


def test_shell_deletion_of_initial_untracked_asset_is_checked(guard, project, monkeypatch):
    calls = []
    monkeypatch.setattr(guard, "check_paths", lambda _root, paths, *, path_only, deleted_paths=None: calls.append((paths, deleted_paths or [], path_only)) or {"status": "ok"})
    target = project / "docs/guides/untracked-guide.md"
    target.parent.mkdir(parents=True)
    target.write_text("Existing guide.\n", encoding="utf-8")
    payload = {"session_id": "one", "tool_name": "Bash", "tool_input": {"command": "python cleanup.py"}}
    assert guard.before_tool(project, payload, "claude") == {}
    target.unlink()
    assert guard.finish_turn(project, payload, "claude") == {}
    assert calls == [([], ["docs/guides/untracked-guide.md"], False)]


def test_shell_restoration_of_initial_dirty_asset_is_checked(guard, project, monkeypatch):
    calls = checker(monkeypatch, guard)
    (project / "app.py").write_text("initial_dirty = True\n", encoding="utf-8")
    payload = {"session_id": "one", "tool_name": "Bash", "tool_input": {"command": "git restore app.py"}}
    assert guard.before_tool(project, payload, "claude") == {}
    git(project, "restore", "app.py")
    assert guard.finish_turn(project, payload, "claude") == {}
    assert calls == [(["app.py"], False)]


def test_explicit_tool_target_is_checked_even_if_already_dirty(guard, project, monkeypatch):
    calls = checker(monkeypatch, guard)
    (project / "app.py").write_text("already dirty", encoding="utf-8")
    payload = event(path="app.py")
    guard.before_tool(project, payload, "gemini")
    guard.finish_turn(project, payload, "gemini")
    assert calls == [(["app.py"], True), (["app.py"], False)]


def test_finish_includes_changes_committed_during_the_turn(guard, project, monkeypatch):
    calls = checker(monkeypatch, guard)
    payload = {"session_id": "one", "tool_name": "Bash", "tool_input": {"command": "python change.py"}}
    guard.before_tool(project, payload, "claude")
    (project / "app.py").write_text("committed = True\n", encoding="utf-8")
    git(project, "add", "app.py")
    git(project, "commit", "-qm", "change")
    guard.finish_turn(project, payload, "claude")
    assert calls == [(["app.py"], False)]


def test_actual_deletions_are_distinct_from_failed_new_writes(guard, project, monkeypatch):
    calls = []
    monkeypatch.setattr(guard, "check_paths", lambda _root, paths, *, path_only, deleted_paths=None: calls.append((paths, deleted_paths or [], path_only)) or {"status": "ok"})
    payload = event(path="app.py")
    guard.before_tool(project, payload, "claude")
    (project / "app.py").unlink()
    guard.finish_turn(project, payload, "claude")
    assert calls[-1] == ([], ["app.py"], False)
    calls.clear()
    payload = event(path="never-created.md")
    guard.before_tool(project, payload, "claude")
    guard.finish_turn(project, payload, "claude")
    assert calls[-1] == ([], [], False)


def test_missing_git_for_shell_is_unverified_and_cleans_observation(guard, tmp_path, monkeypatch):
    checker(monkeypatch, guard)
    payload = {"session_id": "one", "tool_name": "Bash", "tool_input": {"command": "python generate.py"}}
    guard.before_tool(tmp_path, payload, "claude")
    result = guard.finish_turn(tmp_path, payload, "claude")
    assert result["status"] == "unavailable"
    assert "do not claim" in result["message"]
    assert not (tmp_path / guard.CACHE_ROOT).exists()


def test_missing_session_identity_is_unverified_without_cache(guard, project, monkeypatch):
    checker(monkeypatch, guard)
    payload = event()
    del payload["session_id"]
    result = guard.before_tool(project, payload, "claude")
    assert result["status"] == "unavailable"
    assert not (project / ".specify").exists()


def test_parallel_sessions_do_not_share_checkpoints(guard, project, monkeypatch):
    checker(monkeypatch, guard)
    guard.before_tool(project, event(path="app.py", session="one"), "claude")
    guard.before_tool(project, event(path="app.py", session="two"), "claude")
    cache = project / guard.CACHE_ROOT
    assert len(list(cache.glob("*.json"))) == 2
    guard.finish_turn(project, event(session="one"), "claude")
    assert len(list(cache.glob("*.json"))) == 1
    guard.finish_turn(project, event(session="two"), "claude")
    assert not cache.exists()


def test_inferred_violation_never_authorizes_other_actor_edits(guard, project, monkeypatch):
    payload = {"session_id": "one", "tool_name": "Bash", "tool_input": {"command": "python generate.py"}}
    guard.before_tool(project, payload, "claude")
    other = project / "other-actor-report.md"
    other.write_text("preserve me", encoding="utf-8")
    checker(monkeypatch, guard, blocked=True)
    result = guard.finish_turn(project, payload, "claude")
    assert result["status"] == "blocked"
    assert "ownership before changing another actor's files" in result["message"]
    assert other.read_text() == "preserve me"


def test_cache_symlink_is_not_followed(guard, project, monkeypatch, tmp_path_factory):
    checker(monkeypatch, guard)
    outside = tmp_path_factory.mktemp("outside-observation")
    (project / ".specify/runtime").mkdir(parents=True)
    cache = project / guard.CACHE_ROOT
    try:
        cache.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(str(exc))
    result = guard.before_tool(project, event(path="app.py"), "claude")
    assert result["status"] == "unavailable"
    assert list(outside.iterdir()) == []


@pytest.mark.parametrize("command", [
    "ls & python generate.py",
    "file -C -m custom-magic",
    "sed -n 1p -i old-report.md",
    "sed -n 1p -e 'w extra-report.md' old-report.md",
    "Get-Content (New-Item -ItemType File 'Wrong Name.md')",
    "Get-ChildItem | Measure-Object -Property { New-Item 'Wrong Name.md' }",
])
def test_possibly_mutating_shell_is_observed(guard, project, monkeypatch, command):
    checker(monkeypatch, guard)
    payload = {"session_id": "one", "tool_name": "Bash", "tool_input": {"command": command}}
    assert guard.before_tool(project, payload, "claude") == {}
    assert list((project / guard.CACHE_ROOT).glob("*.json"))
    guard.finish_turn(project, payload, "claude")
    assert not (project / guard.CACHE_ROOT).exists()


def test_fingerprinting_does_not_follow_parent_links(guard, project, tmp_path_factory):
    outside = tmp_path_factory.mktemp("outside-fingerprint")
    (outside / "asset.md").write_text("outside", encoding="utf-8")
    try:
        (project / "linked").symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(str(exc))
    assert guard._fingerprint(project, "linked/asset.md") == "unknown"


@pytest.mark.parametrize("initial_git", [False, True])
def test_first_commit_during_shell_task_cannot_hide_missing_baseline(guard, tmp_path, monkeypatch, initial_git):
    checker(monkeypatch, guard)
    if initial_git:
        git(tmp_path, "init", "-q")
    payload = {"session_id": "one", "tool_name": "Bash", "tool_input": {"command": "python generate.py"}}
    guard.before_tool(tmp_path, payload, "claude")
    if not initial_git:
        git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.name", "Asset Test")
    git(tmp_path, "config", "user.email", "assets@example.invalid")
    (tmp_path / "new-report.md").write_text("Created and committed during this turn.\n", encoding="utf-8")
    git(tmp_path, "add", "new-report.md")
    git(tmp_path, "commit", "-qm", "first commit")
    result = guard.finish_turn(tmp_path, payload, "claude")
    assert result["status"] == "unavailable"
    assert "starting Git baseline" in result["message"]
    assert not (tmp_path / guard.CACHE_ROOT).exists()


@pytest.mark.parametrize("key,value", [("head", "not-a-commit"), ("shell", "false"), ("git_available", 0), ("baseline", {"app.py": "not-a-fingerprint"}), ("initial", {})])
def test_corrupt_observation_never_claims_a_clean_result(guard, project, monkeypatch, key, value):
    checker(monkeypatch, guard)
    payload = event(path="app.py")
    guard.before_tool(project, payload, "claude")
    path = next((project / guard.CACHE_ROOT).glob("*.json"))
    state = json.loads(path.read_text(encoding="utf-8"))
    state[key] = value
    path.write_text(json.dumps(state), encoding="utf-8")
    result = guard.finish_turn(project, payload, "claude")
    assert result["status"] == "unavailable"
    assert "invalid or unsafe" in result["message"]


@pytest.mark.parametrize("status,exit_code,data,expected", [
    ("ok", 0, {"checked": 1, "path_only": True}, "ok"),
    ("ok", 0, {"checked": 1, "path_only": False}, "unavailable"),
    ("ok", 0, {"checked": 0, "path_only": True}, "unavailable"),
    ("ok", 0, {"checked": True, "path_only": True}, "unavailable"),
    ("ok", 0, {"checked": 1, "path_only": True, "scope": "tree"}, "unavailable"),
    ("ok", 0, {"checked": 1, "path_only": True, "violation_count": 1}, "unavailable"),
    ("blocked", 10, {"checked": 1, "path_only": True}, "blocked"),
    ("usage-error", 2, {}, "unavailable"),
])
def test_real_pinned_runtime_contract_and_compatibility(guard, tmp_path, status, exit_code, data, expected):
    runtime = tmp_path / "fake_runtime.py"
    data = {"scope": "paths", "deleted_paths": [], "violation_count": 0, **data}
    payload = {"status": status, "data": data, "items": [] if status == "ok" else [{"path": "Wrong Name.md", "message": "use the policy path"}]}
    runtime.write_text(runtime_program(payload, exit_code), encoding="utf-8")
    config = tmp_path / ".specify/config.json"
    config.parent.mkdir()
    config.write_text(json.dumps({"runtime_launcher": {"argv": [sys.executable, str(runtime)]}}), encoding="utf-8")
    result = guard.check_paths(tmp_path, ["Wrong Name.md"], path_only=True)
    assert result["status"] == expected
    if expected == "unavailable":
        assert "do not claim this check passed" in result["message"]


def test_unpinned_path_command_is_not_executed(guard, tmp_path):
    config = tmp_path / ".specify/config.json"
    config.parent.mkdir()
    config.write_text(json.dumps({"runtime_launcher": {"argv": ["specify-runtime"]}}), encoding="utf-8")
    assert guard.check_paths(tmp_path, ["docs/guide.md"], path_only=True)["status"] == "unavailable"


@pytest.mark.parametrize("discovery,exit_code", [
    ({"status": "blocked", "data": {"requested": ["assets.check"], "present": [], "missing": ["assets.check"]}}, 10),
    ({"status": "ok", "data": {"requested": ["assets.check"], "present": ["assets.route"], "missing": []}}, 0),
    ({"status": "ok", "data": {"requested": ["assets.check"], "present": ["assets.check"], "missing": ["assets.check"]}}, 0),
    ({"status": "ok", "data": {"present": ["assets.check"], "missing": []}}, 0),
    ([], 0),
])
def test_capability_discovery_refuses_before_running_asset_check(guard, tmp_path, discovery, exit_code):
    marker = tmp_path / "check-ran"
    runtime = tmp_path / "runtime.py"
    runtime.write_text(
        "import sys\nfrom pathlib import Path\n"
        "if sys.argv[1:3] == ['api','ensure']:\n"
        " print(" + repr(json.dumps(discovery)) + f");sys.exit({exit_code})\n"
        "Path(" + repr(str(marker)) + ").write_text('unexpected check')\n",
        encoding="utf-8",
    )
    config = tmp_path / ".specify/config.json"
    config.parent.mkdir()
    config.write_text(json.dumps({"runtime_launcher": {"argv": [sys.executable, str(runtime)]}}), encoding="utf-8")
    result = guard.check_paths(tmp_path, ["docs/guide.md"], path_only=True)
    assert result["status"] == "unavailable"
    assert "required assets.check capability" in result["message"]
    assert not marker.exists()


def test_git_environment_cannot_redirect_observation(guard, project, monkeypatch, tmp_path_factory):
    other = tmp_path_factory.mktemp("other-git-root")
    git(other, "init", "-q")
    monkeypatch.setenv("GIT_DIR", str(other / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(other))
    calls = checker(monkeypatch, guard)
    payload = {"session_id": "one", "tool_name": "Bash", "tool_input": {"command": "python generate.py"}}
    assert guard.before_tool(project, payload, "claude") == {}
    (project / "Wrong Name.md").write_text("new report", encoding="utf-8")
    assert guard.finish_turn(project, payload, "claude") == {}
    assert calls == [(["Wrong Name.md"], False)]


def test_unused_filter_registration_does_not_disable_delta(guard, project, monkeypatch):
    git(project, "config", "filter.unused.clean", "must-not-run-this-driver")
    calls = checker(monkeypatch, guard)
    payload = {"session_id": "one", "tool_name": "Bash", "tool_input": {"command": "python generate.py"}}
    assert guard.before_tool(project, payload, "claude") == {}
    (project / "new-report.md").write_text("new report", encoding="utf-8")
    assert guard.finish_turn(project, payload, "claude") == {}
    assert calls == [(["new-report.md"], False)]


@pytest.mark.parametrize("flag", ["--assume-unchanged", "--skip-worktree"])
@pytest.mark.parametrize("when", ["before", "after"])
def test_shell_hidden_index_flags_cannot_claim_a_complete_delta(guard, project, monkeypatch, flag, when):
    checker(monkeypatch, guard)
    payload = {"session_id": "one", "tool_name": "Bash", "tool_input": {"command": "python generate.py"}}
    if when == "before":
        git(project, "update-index", flag, "app.py")
    assert guard.before_tool(project, payload, "claude") == {}
    if when == "after":
        git(project, "update-index", flag, "app.py")
    (project / "app.py").write_text("hidden = True\n", encoding="utf-8")
    inventory = git(project, "ls-files", "-v", "app.py")
    result = guard.finish_turn(project, payload, "claude")
    assert result["status"] == "unavailable"
    assert "exact output paths" in result["message"]
    assert git(project, "ls-files", "-v", "app.py") == inventory
    assert (project / "app.py").read_text() == "hidden = True\n"
    assert not (project / guard.CACHE_ROOT).exists()


@pytest.mark.parametrize("flag", ["--assume-unchanged", "--skip-worktree"])
def test_explicit_targets_remain_checkable_with_hidden_index_flags(guard, project, monkeypatch, flag):
    calls = checker(monkeypatch, guard)
    git(project, "update-index", flag, "app.py")
    payload = event(path="app.py")
    assert guard.before_tool(project, payload, "claude") == {}
    (project / "app.py").write_text("explicit = True\n", encoding="utf-8")
    assert guard.finish_turn(project, payload, "claude") == {}
    assert calls == [(["app.py"], True), (["app.py"], False)]


@pytest.mark.parametrize("setting", ["core.fsmonitor", "filter.observer.clean", "filter.observer.process"])
def test_observation_never_executes_configured_git_programs(guard, project, monkeypatch, tmp_path, setting):
    checker(monkeypatch, guard)
    marker = tmp_path / "Observer Junk.md"
    program = tmp_path / "git-program.py"
    program.write_text("from pathlib import Path\nimport sys\nPath(" + repr(str(marker)) + ").write_text('unexpected execution')\nsys.stdout.write(sys.stdin.read())\n", encoding="utf-8")
    command = shlex.join([sys.executable.replace("\\", "/"), str(program).replace("\\", "/")])
    git(project, "config", setting, command)
    (project / ".gitattributes").write_text("app.py filter=observer\n", encoding="utf-8")
    (project / "app.py").write_text("modified = True\n", encoding="utf-8")
    payload = {"session_id": "one", "tool_name": "Bash", "tool_input": {"command": "python generate.py"}}
    assert guard.before_tool(project, payload, "claude") == {}
    result = guard.finish_turn(project, payload, "claude")
    if setting.startswith("filter."):
        assert result["status"] == "unavailable"
        assert "exact output paths" in result["message"]
    else:
        assert result == {}
    assert not marker.exists()
    assert not (project / guard.CACHE_ROOT).exists()


def test_user_git_status_with_fsmonitor_is_observed(guard, project, monkeypatch):
    marker = project / "Wrong Name.md"
    program = project / "git-program.py"
    program.write_text(
        "from pathlib import Path\nimport sys\n"
        "Path(" + repr(str(marker)) + ").write_text('user shell output')\n"
        "sys.stdout.write('token\\0')\n",
        encoding="utf-8",
    )
    command = shlex.join([sys.executable.replace("\\", "/"), str(program).replace("\\", "/")])
    git(project, "config", "core.fsmonitor", command)
    payload = {"session_id": "one", "tool_name": "Bash", "tool_input": {"command": "git status --short"}}
    calls = checker(monkeypatch, guard, blocked=True)
    assert guard.before_tool(project, payload, "claude") == {}
    assert not marker.exists()
    git(project, "status", "--short")
    assert marker.exists()
    result = guard.finish_turn(project, payload, "claude")
    assert result["status"] == "blocked"
    assert calls == [(["Wrong Name.md"], False)]
    assert marker.read_text() == "user shell output"


def test_exact_raw_path_is_never_trimmed_before_validation(guard, project, monkeypatch):
    calls = checker(monkeypatch, guard, blocked=True)
    path = "docs/guides/valid.md "
    result = guard.before_tool(project, event(path=path), "claude")
    assert result["status"] == "blocked"
    assert calls == [([path], True)]
    assert not (project / guard.CACHE_ROOT).exists()


def test_observation_does_not_enter_submodule_filters(guard, project, monkeypatch):
    child = project / "vendor/child"
    child.mkdir(parents=True)
    git(child, "init", "-q")
    git(child, "config", "user.name", "Asset Test")
    git(child, "config", "user.email", "assets@example.invalid")
    (child / "app.py").write_text("original = True\n", encoding="utf-8")
    (child / ".gitattributes").write_text("app.py filter=observer\n", encoding="utf-8")
    git(child, "add", "app.py", ".gitattributes")
    git(child, "commit", "-qm", "child fixture")
    revision = git(child, "rev-parse", "HEAD")
    git(project, "update-index", "--add", "--cacheinfo", f"160000,{revision},vendor/child")
    git(project, "commit", "-qm", "gitlink fixture")
    marker = project / "Observer Submodule.md"
    program = project / "submodule-filter.py"
    program.write_text("from pathlib import Path\nimport sys\nPath(" + repr(str(marker)) + ").write_text('unexpected')\nsys.stdout.write(sys.stdin.read())\n", encoding="utf-8")
    git(child, "config", "filter.observer.clean", shlex.join([sys.executable.replace("\\", "/"), str(program).replace("\\", "/")]))
    (child / "app.py").write_text("changed = True\n", encoding="utf-8")
    checker(monkeypatch, guard)
    payload = {"session_id": "one", "tool_name": "Bash", "tool_input": {"command": "python generate.py"}}
    assert guard.before_tool(project, payload, "claude") == {}
    assert guard.finish_turn(project, payload, "claude") == {}
    assert not marker.exists()


def test_owner_repair_exception_is_exact_and_not_payload_controlled(guard, project, monkeypatch):
    calls = checker(monkeypatch, guard, blocked=True)
    owned = "specs/001-demo/implement-tracker.md"
    payload = event(tool="MultiEdit", path=owned)
    payload["owner_paths"] = ["Wrong Name.md"]
    payload["tool_input"]["edits"] = [{"file_path": "Wrong Name.md"}]
    result = guard.before_tool(project, payload, "claude", owner_paths={owned})
    assert result["status"] == "blocked"
    assert calls == [(["Wrong Name.md"], True)]


@pytest.mark.parametrize("reported,expected", [([], "unavailable"), (["gone.md"], "ok")])
def test_runtime_must_acknowledge_the_exact_deleted_set(guard, tmp_path, reported, expected):
    runtime = tmp_path / "runtime.py"
    payload = {"status": "ok", "data": {"checked": 0, "path_only": False, "scope": "worktree", "violation_count": 0, "deleted_paths": reported}}
    runtime.write_text(runtime_program(payload), encoding="utf-8")
    config = tmp_path / ".specify/config.json"
    config.parent.mkdir()
    config.write_text(json.dumps({"runtime_launcher": {"argv": [sys.executable, str(runtime)]}}), encoding="utf-8")
    assert guard.check_paths(tmp_path, [], path_only=False, deleted_paths=["gone.md"])["status"] == expected
