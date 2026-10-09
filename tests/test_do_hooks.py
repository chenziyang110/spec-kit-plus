"""Standalone operation hooks must consume Go state without formal-stage repair."""

from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(params=["claude", "gemini"])
def do_hook(request):
    path = ROOT / "src/specify_cli/integrations" / request.param / "hooks" / f"{request.param}-hook-dispatch.py"
    name = f"do_contract_{request.param}_hook"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
        yield request.param, module
    finally:
        sys.modules.pop(name, None)


def _project(tmp_path):
    (tmp_path / ".specify/do/sessions").mkdir(parents=True)
    return tmp_path


def test_do_hook_uses_pinned_runtime_argv_and_no_python_fallback(do_hook, tmp_path, monkeypatch):
    kind, hook = do_hook
    root = _project(tmp_path)
    executable = str(root / "path with spaces/specify-runtime")
    (root / ".specify/config.json").write_text(
        json.dumps({"runtime_launcher": {"argv": [executable]}}), encoding="utf-8"
    )
    calls = []

    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        if argv[1:3] == ["api", "ensure"]:
            return subprocess.CompletedProcess(argv, 0, json.dumps({
                "status": "ok", "data": {"requested": ["do.show"], "present": ["do.show"], "missing": []}
            }), "")
        return subprocess.CompletedProcess(argv, 0, json.dumps({
            "status": "ok", "data": {"active": True, "session": {"id": "do-exact"}}
        }), "")

    monkeypatch.setattr(hook.subprocess, "run", run)
    assert hook._active_do_context(root) == {"command_name": "do", "session_id": "do-exact"}
    assert calls[0][0] == [executable, "api", "ensure", "--capabilities", "do.show", "--format", "json"]
    assert calls[1][0] == [executable, "do", "show", "--active", "--adapter-id", kind, "--format", "json"]
    assert calls[0][1]["cwd"] == root
    assert calls[0][1]["timeout"] == hook.SHARED_HOOK_TIMEOUT_SECONDS
    assert 0 < calls[1][1]["timeout"] <= hook.SHARED_HOOK_TIMEOUT_SECONDS
    assert all(not kwargs.get("shell") for _, kwargs in calls)


@pytest.mark.parametrize("discovery,returncode", [
    ({"status": "blocked", "data": {"requested": ["do.show"], "present": [], "missing": ["do.show"]}}, 10),
    ({"status": "ok", "data": {"requested": ["do.show"], "present": [], "missing": []}}, 0),
    ({"status": "ok", "data": {"requested": ["do.validate"], "present": ["do.validate"], "missing": []}}, 0),
    ({"status": "ok", "data": {"requested": ["do.show"], "present": ["do.show"], "missing": ["do.show"]}}, 0),
])
def test_do_hook_rejects_missing_or_mismatched_capability_before_state_read(do_hook, tmp_path, monkeypatch, discovery, returncode):
    _, hook = do_hook
    calls = []
    monkeypatch.setattr(hook, "_runtime_argv_from_project_config", lambda _: ("pinned-runtime",))

    def run(argv, **_kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, returncode, json.dumps(discovery), "")

    monkeypatch.setattr(hook.subprocess, "run", run)
    assert hook._do_runtime_payload(tmp_path, "show", "--active") is None
    assert calls == [["pinned-runtime", "api", "ensure", "--capabilities", "do.show", "--format", "json"]]


def test_do_capability_and_state_read_share_the_existing_hook_deadline(do_hook, tmp_path, monkeypatch):
    _, hook = do_hook
    calls = []
    ticks = iter([0.0, hook.SHARED_HOOK_TIMEOUT_SECONDS + 0.1])
    monkeypatch.setattr(hook, "_runtime_argv_from_project_config", lambda _: ("pinned-runtime",))
    monkeypatch.setattr(hook, "time", SimpleNamespace(monotonic=lambda: next(ticks)))

    def run(argv, **_kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, json.dumps({
            "status": "ok", "data": {"requested": ["do.show"], "present": ["do.show"], "missing": []}
        }), "")

    monkeypatch.setattr(hook.subprocess, "run", run)
    assert hook._do_runtime_payload(tmp_path, "show", "--active") is None
    assert len(calls) == 1 and calls[0][1:3] == ["api", "ensure"]


@pytest.mark.parametrize("do_hook", ["gemini"], indirect=True)
def test_gemini_session_start_injects_do_resume_into_agent_context(do_hook, tmp_path, monkeypatch):
    _, hook = do_hook
    monkeypatch.setattr(hook, "_infer_active_context", lambda _: {"command_name": "do", "session_id": "do-owner"})
    output = hook._handle_session_start(tmp_path, {})
    assert "DoSession do-owner" in output["hookSpecificOutput"]["additionalContext"]
    assert output["hookSpecificOutput"]["hookEventName"] == "SessionStart"


@pytest.mark.parametrize("do_hook", ["gemini"], indirect=True)
@pytest.mark.parametrize("state,blocked", [("pending", True), ("terminal", False), ("external", False), ("unavailable", True), ("ambiguous", True)])
def test_gemini_after_agent_enforces_do_terminal_or_recorded_external_exit(do_hook, tmp_path, monkeypatch, capsys, state, blocked):
    _, hook = do_hook
    context = {"command_name": "do", "session_id": "do-owner"}
    if state in {"unavailable", "ambiguous"}:
        context = {"command_name": "do", state: "true"}
    monkeypatch.setattr(hook, "_infer_active_context", lambda _: context)
    monkeypatch.setattr(hook, "_project_root", lambda _: tmp_path)
    monkeypatch.setattr(hook, "_read_stdin_payload", lambda: {"prompt": "/sp.do build", "hook_event_name": "AfterAgent"})
    calls = []

    def runtime(_root, *args):
        calls.append(args)
        assert state not in {"unavailable", "ambiguous"}
        data = {"terminal": state == "terminal", "can_stop": state in {"terminal", "external"},
                "validation": {"status": "passed" if state == "terminal" else "blocked"}, "session": {"id": "do-owner"}}
        if state == "external":
            data["session"]["blocker"] = {"owner": "external", "cause": "access unavailable"}
        return {"status": "ok" if args[0] == "show" or state == "terminal" else "blocked", "data": data}

    monkeypatch.setattr(hook, "_do_runtime_payload", runtime)
    monkeypatch.setattr(hook, "_run_shared_hook", lambda *_args, **_kw: pytest.fail("DO used a formal workflow gate"))
    asset_calls = []
    monkeypatch.setattr(hook, "_run_asset_guard", lambda *args, **_kw: asset_calls.append(args) or {})
    monkeypatch.setattr(hook.sys, "argv", ["gemini-hook-dispatch.py", "after-agent"])
    assert hook.main() == 0
    output = json.loads(capsys.readouterr().out)
    if blocked:
        assert output["decision"] == "deny"
        assert "DoSession" in output["reason"]
        assert not asset_calls
    else:
        assert output.get("decision") != "deny"
        assert len(asset_calls) == 1 and asset_calls[0][2] == "finish"
    if state == "pending":
        assert calls == [("show", "do-owner"), ("validate", "do-owner")]
    elif state == "external":
        assert calls == [("show", "do-owner")]


def test_do_context_never_picks_latest_or_a_formal_feature(do_hook, tmp_path, monkeypatch):
    _, hook = do_hook
    root = _project(tmp_path)
    (root / ".specify/do/sessions/newest-looking.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(hook, "_do_runtime_payload", lambda *_: {
        "status": "ok", "data": {"active": True, "session_id": "do-owner"}
    })
    assert hook._infer_active_context(root) == {"command_name": "do", "session_id": "do-owner"}
    monkeypatch.setattr(hook, "_do_runtime_payload", lambda *_: {
        "status": "blocked", "data": {"ambiguous": True, "sessions": ["one", "two"]}
    })
    context = hook._infer_active_context(root)
    assert context == {"command_name": "do", "ambiguous": "true"}
    assert "explicit session ID" in hook._do_resume_context(context)
    assert "session_id" not in context and "feature_dir" not in context


@pytest.mark.parametrize("prompt,command", [
    ("/sp-quick run tests", "quick"),
    ("$spx-plan create a plan", "plan"),
    ("/sp.do build", "do"),
    ("Use $spx-do to package the CLI", "do"),
    ("/skill:sp-quick resume", "quick"),
    ("Explain how /sp-do works", None),
    ("`/sp-quick` is an example", None),
])
def test_only_explicit_current_invocation_selects_workflow_context(do_hook, prompt, command):
    _, hook = do_hook
    assert hook._explicit_workflow_command({"prompt": prompt}) == command


def test_gemini_history_does_not_reactivate_an_old_do_invocation(do_hook):
    _, hook = do_hook
    payload = {"llm_request": {"messages": [
        {"role": "user", "content": "/sp.do earlier build"},
        {"role": "assistant", "content": "/sp.do is still active"},
        {"role": "user", "parts": [{"text": "/sp.plan the next feature"}]},
    ]}}
    assert hook._explicit_workflow_command(payload) == "plan"


@pytest.mark.parametrize("prompt,selected", [
    ("/sp-do resume Exact-123", "Exact-123"),
    ("Use $spx-do resume exact_123 inspect", "exact_123"),
    ("/skill:spx-do resume exact", "exact"),
    ("/sp.do resume exact", "exact"),
    ("/sp-do resume", ""),
    ("/sp-do resume ../other", ""),
    ("/sp-do resume " + "x" * 97, ""),
    ("Explain /sp-do resume old", None),
    ("/sp-quick resume old", None),
    ("/sp-do inspect", None),
])
def test_exact_do_selector_requires_current_explicit_resume(do_hook, prompt, selected):
    _, hook = do_hook
    assert hook._explicit_do_session({"prompt": prompt, "session_id": "native-chat"}) == selected
    assert hook._explicit_do_session({"session_id": "native-chat"}) is None
    assert hook._explicit_do_session({"llm_request": {"messages": [
        {"role": "user", "content": "/sp-do resume stale"},
        {"role": "user", "content": prompt},
    ]}}) == selected


@pytest.mark.parametrize("response", [
    None,
    {"status": "blocked", "data": {"session": {"id": "exact"}}},
    {"status": "ok", "data": {"active": False}},
    {"status": "ok", "data": {"session": {"id": "unrelated"}}},
    {"status": "ok", "data": {"session_id": "unrelated", "session": {"id": "exact"}}},
])
def test_exact_do_lookup_refuses_missing_or_wrong_identity_without_fallback(do_hook, tmp_path, monkeypatch, response):
    _, hook = do_hook
    root = _project(tmp_path)
    calls = []

    def runtime(_root, *args):
        calls.append(args)
        return response

    monkeypatch.setattr(hook, "_do_runtime_payload", runtime)

    @hook._with_explicit_workflow_context
    def selected(_root, _payload):
        return hook._infer_active_context(root)

    context = selected(root, {"prompt": "/sp-do resume exact"})
    assert context == {"command_name": "do", "unavailable": "true", "session_id": "exact"}
    assert calls == [("show", "exact")]
    assert "do show exact" in hook._do_resume_context(context)
    assert hook._EXPLICIT_DO_SESSION.get() is None


def test_exact_do_resume_selects_terminal_owner_and_invalid_resume_never_queries_active(do_hook, tmp_path, monkeypatch):
    _, hook = do_hook
    calls = []

    def runtime(_root, *args):
        calls.append(args)
        return {"status": "ok", "data": {"terminal": True, "session": {"id": "exact"}}}

    monkeypatch.setattr(hook, "_do_runtime_payload", runtime)

    @hook._with_explicit_workflow_context
    def selected(_root, _payload):
        return hook._infer_active_context(tmp_path)

    assert selected(tmp_path, {"prompt": "/sp-do resume exact"}) == {"command_name": "do", "session_id": "exact"}
    assert calls == [("show", "exact")]
    calls.clear()
    context = selected(tmp_path, {"prompt": "/sp-do resume"})
    assert context == {"command_name": "do", "unavailable": "true", "invalid_resume": "true"}
    assert "valid exact session ID" in hook._do_resume_context(context)
    assert calls == []


@pytest.mark.parametrize("mismatch", ["show", "validate"])
def test_exact_do_stop_rechecks_show_and_validation_identity(do_hook, tmp_path, monkeypatch, mismatch):
    kind, hook = do_hook
    calls = []

    def runtime(_root, *args):
        calls.append(args)
        identity = "other" if args[0] == mismatch and len(calls) > 1 else "exact"
        return {"status": "ok", "data": {
            "session": {"id": identity}, "terminal": True, "validation": {"status": "passed"},
        }}

    monkeypatch.setattr(hook, "_do_runtime_payload", runtime)
    handler = hook._handle_stop_monitor if kind == "claude" else hook._handle_after_agent
    assert handler(tmp_path, {"prompt": "/sp-do resume exact"})["decision"] in {"block", "deny"}
    assert all(args[1] == "exact" for args in calls)


def test_explicit_non_do_invocation_keeps_its_context_and_never_queries_do(do_hook, tmp_path, monkeypatch):
    kind, hook = do_hook
    root = _project(tmp_path)
    quick = root / ".planning/quick/current/STATUS.md"
    quick.parent.mkdir(parents=True)
    quick.write_text("---\nstatus: active\n---\n", encoding="utf-8")
    implement = root / ".specify/features/other/implement-tracker.md"
    implement.parent.mkdir(parents=True)
    implement.write_text("---\nstatus: executing\n---\n", encoding="utf-8")
    monkeypatch.setattr(hook, "_do_runtime_payload", lambda *_: pytest.fail("DO intercepted an explicit Quick request"))
    calls = []

    def shared(_root, args, **_kwargs):
        calls.append(args)
        return {"status": "ok", "data": {"statusline": "Quick current"}}

    monkeypatch.setattr(hook, "_run_shared_hook", shared)
    if kind == "claude":
        hook._handle_user_prompt_submit(root, {"prompt": "/sp-quick run tests"})
    else:
        hook._handle_before_agent(root, {"prompt": "/sp.quick run tests"})
    policies = [args for args in calls if args[0] == "workflow-policy"]
    assert policies and all(args[args.index("--command") + 1] == "quick" for args in policies)
    assert all("--feature-dir" not in args for args in policies)
    assert hook._EXPLICIT_WORKFLOW.get() is None


def test_new_explicit_workflow_does_not_inherit_an_unrelated_do_owner(do_hook, tmp_path, monkeypatch):
    kind, hook = do_hook
    root = _project(tmp_path)
    monkeypatch.setattr(hook, "_do_runtime_payload", lambda *_: pytest.fail("unrelated DO lookup"))
    if kind == "claude":
        monkeypatch.setattr(hook, "_claude_personal_skill_shadow_advisory", lambda _: "")
    output = hook._handle_session_start(root, {"prompt": "/sp-plan new feature"})
    assert not output
    assert hook._EXPLICIT_WORKFLOW.get() is None


def test_explicit_context_is_cleared_after_a_hook_error(do_hook, tmp_path):
    _, hook = do_hook

    @hook._with_explicit_workflow_context
    def fail(_root, _payload):
        assert hook._EXPLICIT_WORKFLOW.get() == "quick"
        raise ValueError("native hook fixture error")

    with pytest.raises(ValueError, match="native hook fixture"):
        fail(tmp_path, {"prompt": "/sp-quick fixture"})
    assert hook._EXPLICIT_WORKFLOW.get() is None
    assert hook._EXPLICIT_DO_SESSION.get() is None

    @hook._with_explicit_workflow_context
    def fail_resume(_root, _payload):
        assert hook._EXPLICIT_DO_SESSION.get() == "exact"
        raise ValueError("native resume fixture error")

    with pytest.raises(ValueError, match="native resume fixture"):
        fail_resume(tmp_path, {"prompt": "/sp-do resume exact"})
    assert hook._EXPLICIT_DO_SESSION.get() is None


def _claude_transcript(root: Path, prompts: list[str]) -> Path:
    path = root / ".claude/transcripts/current.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(
        json.dumps({"type": "message", "message": {
            "role": "user", "content": [{"type": "text", "text": prompt}]
        }}) for prompt in prompts
    ) + "\n", encoding="utf-8")
    return path


@pytest.mark.parametrize("do_hook", ["claude"], indirect=True)
def test_claude_stop_uses_current_transcript_workflow_before_unrelated_do(do_hook, tmp_path, monkeypatch):
    _, hook = do_hook
    root = _project(tmp_path)
    quick = root / ".planning/quick/current/STATUS.md"
    quick.parent.mkdir(parents=True)
    quick.write_text("---\nstatus: active\n---\n", encoding="utf-8")
    transcript = _claude_transcript(root, ["/sp-do old build", "/sp-quick current fix"])
    monkeypatch.setattr(hook, "_do_runtime_payload", lambda *_: pytest.fail("DO intercepted the current native transcript"))
    calls = []

    def shared(_root, args, **_kwargs):
        calls.append(args)
        return {"status": "blocked", "errors": ["current Quick gate"]}

    monkeypatch.setattr(hook, "_run_shared_hook", shared)
    output = hook._handle_stop_monitor(root, {"transcript_path": str(transcript)})
    assert output == {"decision": "block", "reason": "current Quick gate"}
    assert calls[0][:3] == ["monitor-context", "--command", "quick"]
    assert "--workspace" in calls[0] and "--feature-dir" not in calls[0]
    assert hook._EXPLICIT_WORKFLOW.get() is None


@pytest.mark.parametrize("do_hook", ["claude"], indirect=True)
def test_claude_transcript_uses_latest_user_and_direct_prompt_wins(do_hook, tmp_path):
    _, hook = do_hook
    transcript = _claude_transcript(tmp_path, ["/sp-do earlier", "/sp-plan current"])

    @hook._with_explicit_workflow_context
    def selected(_root, _payload):
        return hook._EXPLICIT_WORKFLOW.get()

    payload = {"transcript_path": str(transcript)}
    assert selected(tmp_path, payload) == "plan"
    assert selected(tmp_path, {**payload, "prompt": "/sp-quick new"}) == "quick"
    assert selected(tmp_path, {**payload, "prompt": "A new ordinary request"}) is None
    _claude_transcript(tmp_path, ["/sp-do earlier", "A new ordinary request"])
    assert selected(tmp_path, payload) is None


@pytest.mark.parametrize("do_hook", ["claude"], indirect=True)
def test_claude_exact_resume_uses_only_latest_allowed_transcript_or_current_prompt(do_hook, tmp_path):
    _, hook = do_hook
    transcript = _claude_transcript(tmp_path, ["/sp-do resume stale", "/sp-do resume exact"])

    @hook._with_explicit_workflow_context
    def selected(_root, _payload):
        return hook._EXPLICIT_DO_SESSION.get()

    payload = {"transcript_path": str(transcript)}
    assert selected(tmp_path, payload) == "exact"
    assert selected(tmp_path, {**payload, "prompt": "/sp-do resume current"}) == "current"
    assert selected(tmp_path, {**payload, "prompt": "A new ordinary request"}) is None
    _claude_transcript(tmp_path, ["/sp-do resume stale", "A new ordinary request"])
    assert selected(tmp_path, payload) is None
    assert hook._EXPLICIT_DO_SESSION.get() is None


@pytest.mark.parametrize("do_hook", ["claude"], indirect=True)
def test_claude_current_map_transcript_keeps_its_existing_scope_before_do(do_hook, tmp_path, monkeypatch):
    _, hook = do_hook
    root = _project(tmp_path)
    transcript = _claude_transcript(root, ["现在继续 $sp-map-build"])
    monkeypatch.setattr(hook, "_do_runtime_payload", lambda *_: pytest.fail("DO intercepted explicit map work"))
    calls = []

    def shared(_root, args, **_kwargs):
        calls.append(args)
        return {"status": "blocked", "errors": ["map build gate"]}

    monkeypatch.setattr(hook, "_run_shared_hook", shared)
    output = hook._handle_stop_monitor(root, {"transcript_path": str(transcript)})
    assert output["reason"] == "map build gate"
    assert calls[0] == ["validate-artifacts", "--command", "map-build", "--feature-dir",
                        str(root / ".specify/project-cognition")]


def test_no_do_store_does_not_spawn_runtime(do_hook, tmp_path, monkeypatch):
    _, hook = do_hook
    monkeypatch.setattr(hook, "_do_runtime_payload", lambda *_: pytest.fail("unexpected runtime call"))
    assert hook._active_do_context(tmp_path) is None


def test_runtime_confirms_no_active_do_session(do_hook, tmp_path, monkeypatch):
    _, hook = do_hook
    root = _project(tmp_path)
    monkeypatch.setattr(hook, "_do_runtime_payload", lambda *_: {
        "status": "ok", "data": {"active": False}
    })
    assert hook._active_do_context(root) is None


def test_legacy_feature_state_cannot_impersonate_a_do_session(do_hook, tmp_path, monkeypatch):
    _, hook = do_hook
    root = _project(tmp_path)
    legacy = root / ".specify/features/unrelated/workflow-state.md"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("---\nactive_command: sp-do\nstatus: active\n---\n", encoding="utf-8")
    monkeypatch.setattr(hook, "_do_runtime_payload", lambda *_: {
        "status": "ok", "data": {"active": False}
    })
    assert hook._infer_active_context(root) is None


@pytest.mark.parametrize("payload", [
    None,
    {"status": "blocked", "data": {"active": False}},
    {"status": "ok", "data": []},
    {"status": "ok", "data": {}},
    {"status": "ok", "data": {"active": True, "session": {}}},
])
def test_failed_lookup_does_not_fall_back_to_a_formal_feature(do_hook, tmp_path, monkeypatch, payload):
    kind, hook = do_hook
    root = _project(tmp_path)
    monkeypatch.setattr(hook, "_do_runtime_payload", lambda *_: payload)
    context = hook._infer_active_context(root)
    assert context == {"command_name": "do", "unavailable": "true"}
    assert "could not be read" in hook._do_resume_context(context)
    assert "session_id" not in context and "feature_dir" not in context
    monkeypatch.setattr(hook, "_run_shared_hook", lambda *_args, **_kw: pytest.fail("formal fallback hid DO failure"))
    if kind == "claude":
        output = hook._handle_stop_monitor(root, {})
        assert output["decision"] == "block"
        assert "could not be read" in output["reason"]
    else:
        output = hook._handle_before_agent(root, {})
        assert "could not be read" in output["hookSpecificOutput"]["additionalContext"]
        assert "decision" not in output


@pytest.mark.parametrize("stdout,returncode", [("invalid json", 0), ("[]", 0), ('{"status":"ok"}', 1)])
def test_invalid_do_context_is_not_execution_evidence(do_hook, tmp_path, monkeypatch, stdout, returncode):
    _, hook = do_hook
    monkeypatch.setattr(hook, "_runtime_argv_from_project_config", lambda _: ("pinned-runtime",))
    def run(argv, **_kwargs):
        if argv[1:3] == ["api", "ensure"]:
            return subprocess.CompletedProcess(argv, 0, json.dumps({
                "status": "ok", "data": {"requested": ["do.show"], "present": ["do.show"], "missing": []}
            }), "")
        return subprocess.CompletedProcess(argv, returncode, stdout, "")

    monkeypatch.setattr(hook.subprocess, "run", run)
    assert hook._do_runtime_payload(tmp_path, "show", "--active") is None


def test_claude_stop_requires_terminal_and_fresh_validation(do_hook, tmp_path, monkeypatch):
    kind, hook = do_hook
    if kind != "claude":
        pytest.skip("Claude has the native Stop hook")
    context = {"command_name": "do", "session_id": "do-owner"}
    monkeypatch.setattr(hook, "_infer_active_context", lambda _: context)
    monkeypatch.setattr(hook, "_map_context_from_transcript", lambda *_: pytest.fail("stale transcript took ownership"))
    monkeypatch.setattr(hook, "_run_shared_hook", lambda *_args, **_kw: pytest.fail("formal hook invoked for DO"))

    for status, terminal in [("passed", False), ("blocked", True)]:
        monkeypatch.setattr(hook, "_do_runtime_payload", lambda *_: {
            "status": "ok", "data": {"ready_to_finish": True, "terminal": terminal, "validation": {"status": status}}
        })
        output = hook._handle_stop_monitor(tmp_path, {})
        assert output["decision"] == "block"
        assert "DoSession do-owner" in output["reason"]

    monkeypatch.setattr(hook, "_do_runtime_payload", lambda *_: {
        "status": "ok", "data": {"terminal": True, "validation": {"status": "passed"}}
    })
    assert hook._handle_stop_monitor(tmp_path, {}) is None

    monkeypatch.setattr(hook, "_do_runtime_payload", lambda *_: None)
    assert hook._handle_stop_monitor(tmp_path, {})["decision"] == "block"


def test_ambiguous_do_owner_requires_explicit_session_without_validating_latest(do_hook, tmp_path, monkeypatch):
    kind, hook = do_hook
    context = {"command_name": "do", "ambiguous": "true"}
    monkeypatch.setattr(hook, "_infer_active_context", lambda _: context)
    monkeypatch.setattr(hook, "_do_runtime_payload", lambda *_: pytest.fail("an arbitrary session was validated"))
    if kind == "claude":
        output = hook._handle_stop_monitor(tmp_path, {})
        assert output["decision"] == "block"
        assert "explicit session ID" in output["reason"]
    else:
        output = hook._handle_before_agent(tmp_path, {})
        assert "explicit session ID" in output["hookSpecificOutput"]["additionalContext"]


def test_runtime_accepted_external_blocker_permits_honest_blocked_exit(do_hook, tmp_path, monkeypatch):
    kind, hook = do_hook
    monkeypatch.setattr(hook, "_infer_active_context", lambda _: {"command_name": "do", "session_id": "do-blocked"})
    calls = []

    def runtime(_root, *args):
        calls.append(args)
        return {
            "status": "ok" if args[0] == "show" else "blocked",
            "data": {
                "terminal": False, "can_stop": True,
                "session": {"id": "do-blocked", "blocker": {"owner": "external", "cause": "access unavailable"}},
                "validation": {"status": "blocked"},
            },
        }

    monkeypatch.setattr(hook, "_do_runtime_payload", runtime)
    if kind == "claude":
        assert hook._handle_stop_monitor(tmp_path, {}) is None
        assert calls == [("show", "do-blocked")]
    else:
        output = hook._handle_before_agent(tmp_path, {})
        assert "permits a blocked exit" in output["hookSpecificOutput"]["additionalContext"]
        assert "decision" not in output


def test_gemini_pending_do_can_continue_without_formal_phase_block(do_hook, tmp_path, monkeypatch):
    kind, hook = do_hook
    if kind != "gemini":
        pytest.skip("Gemini uses its existing BeforeAgent surface")
    context = {"command_name": "do", "session_id": "do-owner"}
    monkeypatch.setattr(hook, "_infer_active_context", lambda _: context)
    calls = []

    def runtime(_root, *args):
        calls.append(args)
        return {"status": "blocked", "data": {"terminal": False, "validation": {"status": "blocked"}}}

    monkeypatch.setattr(hook, "_do_runtime_payload", runtime)
    monkeypatch.setattr(hook, "_run_shared_hook", lambda *_args, **_kw: pytest.fail("formal context hook invoked for DO"))
    output = hook._handle_before_agent(tmp_path, {})
    assert "decision" not in output
    assert output["hookSpecificOutput"]["hookEventName"] == "BeforeAgent"
    assert "not yet terminal" in output["hookSpecificOutput"]["additionalContext"]
    assert calls == [("validate", "do-owner")]
    assert hook._workflow_policy_shared(tmp_path, trigger="pre_tool", context=context) is None


@pytest.mark.parametrize("kind", ["claude", "gemini"])
def test_native_do_finish_hook_rejects_unfinished_then_allows_completed_operation(kind, built_unified_runtime, tmp_path):
    project = tmp_path / "project with spaces"
    project.mkdir()
    source = project / "native_check.py"
    source.write_text("print('native operation verified')\n", encoding="utf-8")
    for argv in (
        ["git", "init", "-q"], ["git", "add", source.name],
        ["git", "-c", "user.name=Do Hook Test", "-c", "user.email=hook@example.invalid", "commit", "-qm", "fixture"],
    ):
        subprocess.run(argv, cwd=project, check=True, capture_output=True, text=True)
    original = source.read_bytes()
    bin_dir = project / ".specify/bin"
    bin_dir.mkdir(parents=True)
    (project / ".specify/config.json").write_text(json.dumps({
        "runtime_launcher": {"argv": [str(built_unified_runtime)]}
    }), encoding="utf-8")
    shutil.copyfile(ROOT / "src/specify_cli/shared_hooks/specify-asset-guard.py", bin_dir / "specify-asset-guard.py")
    dispatcher = project / f".{kind}/hooks/{kind}-hook-dispatch.py"
    dispatcher.parent.mkdir(parents=True)
    shutil.copyfile(ROOT / f"src/specify_cli/integrations/{kind}/hooks/{kind}-hook-dispatch.py", dispatcher)
    env = dict(os.environ)
    env[f"{kind.upper()}_PROJECT_DIR"] = str(project)
    session_id = "native-do-" + kind
    native_payload = {"cwd": str(project), "session_id": "native-chat"}
    if kind == "claude":
        transcript = _claude_transcript(project, ["/sp-do resume stale", f"/sp-do resume {session_id}"])
        native_payload["transcript_path"] = str(transcript)
    else:
        native_payload["prompt"] = f"/sp-do resume {session_id}"
    argv = [sys.executable, source.name]
    definition = {
        "operation": "check", "target": "native-hook", "owner": source.name, "variant": kind,
        "title": "Inspect the actual native operation", "goal": "Inspect the actual native operation",
        "aliases": [], "applicability": {}, "source_files": [source.name], "learning_refs": [],
        "steps": [{"id": "inspect", "purpose": "Run the real native check", "cwd": ".", "argv": argv,
                   "depends_on": [], "required": True, "expected_result": "Native check passes", "side_effect": "read"}],
        "checks": [{"id": "verify", "purpose": "Verify the real native check", "cwd": ".", "argv": argv,
                    "depends_on": ["inspect"], "required": True, "expected_result": "Native check passes", "kind": "exit_code"}],
    }

    def runtime(*args, payload=None):
        command = [str(built_unified_runtime), *args, "--format", "json"]
        if payload is not None:
            command += ["--input-json", "-"]
        result = subprocess.run(command, cwd=project, input=json.dumps(payload) if payload is not None else None,
                                text=True, capture_output=True, timeout=30, env=env)
        envelope = json.loads(result.stdout)
        assert result.returncode == 0 and envelope["status"] == "ok", (result.stderr, envelope)
        return envelope["data"]

    def finish_hook():
        route = "stop-monitor" if kind == "claude" else "after-agent"
        result = subprocess.run([sys.executable, str(dispatcher), route], cwd=project, env=env,
                                input=json.dumps(native_payload),
                                capture_output=True, text=True, timeout=20)
        assert result.returncode == 0 and result.stderr == "", (result.returncode, result.stderr)
        return json.loads(result.stdout) if result.stdout.strip() else {}

    session = runtime("do", "start", payload={"session_id": session_id, "definition": definition,
                      "adapter_id": kind, "agent_id": "native-hook-validator"})
    other_id = "unrelated-" + kind
    runtime("do", "start", payload={"session_id": other_id, "definition": definition,
            "adapter_id": kind, "agent_id": "other-validator"})
    other_file = project / ".specify/do/sessions" / other_id / "session.json"
    other_before = other_file.read_bytes()
    assert finish_hook()["decision"] in {"deny", "block"}
    for attempt_kind, target in [("step", "inspect"), ("check", "verify")]:
        event = {"attempt_id": target + "-attempt", "target_id": target, "kind": attempt_kind, "event": "started"}
        session = runtime("do", "record", session_id, payload={"expected_revision": session["revision"],
                          "request_id": target + "-start", "events": [event]})
        started = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        result = subprocess.run(argv, cwd=project, check=True, capture_output=True, text=True)
        finished = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        event |= {"event": "completed", "status": "passed", "evidence_origin": "agent_tool_observation",
                  "tool_call_id": kind + "-native-" + target, "argv": argv, "cwd": ".", "started_at": started,
                  "finished_at": finished, "exit_code": result.returncode, "summary": result.stdout.strip()}
        session = runtime("do", "record", session_id, payload={"expected_revision": session["revision"],
                          "request_id": target + "-complete", "events": [event]})
    checked = runtime("do", "validate", session_id)
    assert checked["validation"]["status"] == "passed" and checked["terminal"] is False
    assert finish_hook()["decision"] in {"deny", "block"}
    session = runtime("do", "finish", session_id, payload={"expected_revision": session["revision"], "knowledge_status": "pending"})
    assert session["terminal"] is False
    assert finish_hook()["decision"] in {"deny", "block"}
    session = runtime("do", "finish", session_id, payload={"expected_revision": session["revision"], "knowledge_status": "not_applicable"})
    assert session["terminal"] is True and finish_hook() == {}
    assert runtime("do", "show", "--active", "--adapter-id", kind)["session_id"] == other_id
    assert other_file.read_bytes() == other_before
    assert source.read_bytes() == original
    assert not (project / ".specify/features").exists()
    assert not (project / ".planning/quick").exists()
