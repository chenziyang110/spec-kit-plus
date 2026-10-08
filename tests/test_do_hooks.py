"""Standalone operation hooks must consume Go state without formal-stage repair."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys

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
        return subprocess.CompletedProcess(argv, 0, json.dumps({
            "status": "ok", "data": {"active": True, "session": {"id": "do-exact"}}
        }), "")

    monkeypatch.setattr(hook.subprocess, "run", run)
    assert hook._active_do_context(root) == {"command_name": "do", "session_id": "do-exact"}
    assert calls[0][0] == [executable, "do", "show", "--active", "--adapter-id", kind, "--format", "json"]
    assert calls[0][1]["cwd"] == root
    assert calls[0][1]["timeout"] == hook.SHARED_HOOK_TIMEOUT_SECONDS
    assert not calls[0][1].get("shell")


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
    monkeypatch.setattr(hook.subprocess, "run", lambda argv, **_: subprocess.CompletedProcess(argv, returncode, stdout, ""))
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
