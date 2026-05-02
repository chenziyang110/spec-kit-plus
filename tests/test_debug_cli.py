import pytest
from typer.testing import CliRunner
from specify_cli import app
import re
from specify_cli.debug.schema import DebugStatus
from specify_cli.debug.persistence import MarkdownPersistenceHandler
from specify_cli.debug.schema import DebugGraphState, ObserverCauseCandidate, SuggestedEvidenceLane

runner = CliRunner()

@pytest.fixture
def clean_debug_dir(tmp_path, monkeypatch):
    project_root = tmp_path / "debug-cli-project"
    project_root.mkdir()
    monkeypatch.chdir(project_root)
    debug_dir = project_root / ".planning" / "debug"
    debug_dir.mkdir(parents=True, exist_ok=True)
    yield debug_dir


@pytest.fixture(autouse=True)
def bypass_debug_project_map_preflight(monkeypatch):
    try:
        import specify_cli.debug.cli as cli_module
    except ModuleNotFoundError:
        return
    monkeypatch.setattr(cli_module, "_project_map_preflight_for_debug", lambda: None)

def test_debug_no_session(clean_debug_dir):
    # Running without description and no session should show error
    result = runner.invoke(app, ["debug"])
    assert result.exit_code == 1
    assert "no recent session found" in result.stdout.lower()

def test_debug_new_session(clean_debug_dir):
    import specify_cli.debug.cli as cli_module

    async def fake_run_debug_session(state, handler, *, resumed=False):
        handler.save(state)

    cli_module.generate_slug = lambda _: "new-session"
    cli_module.run_debug_session = fake_run_debug_session

    result = runner.invoke(app, ["debug", "parser bug"])

    assert result.exit_code == 0
    assert "starting new debug session: new-session" in result.stdout.lower()
    assert (clean_debug_dir / "new-session.md").exists()

def test_debug_resumes_most_recent_session(clean_debug_dir, monkeypatch):
    import specify_cli.debug.cli as cli_module

    MarkdownPersistenceHandler(clean_debug_dir).save(
        DebugGraphState(slug="resume-me", trigger="parser bug")
    )
    seen = {}

    async def fake_run_debug_session(state, handler, *, resumed=False):
        seen["slug"] = state.slug
        seen["resumed"] = resumed
        handler.save(state)

    monkeypatch.setattr(cli_module, "run_debug_session", fake_run_debug_session)

    result = runner.invoke(app, ["debug"])

    assert result.exit_code == 0
    assert "resuming debug session: resume-me" in result.stdout.lower()
    assert seen["slug"] == "resume-me"
    assert seen["resumed"] is True


def test_debug_new_issue_from_awaiting_human_links_child_session(clean_debug_dir, monkeypatch):
    pytest.importorskip("pydantic_graph")
    import specify_cli.debug.cli as cli_module

    handler = MarkdownPersistenceHandler(clean_debug_dir)
    parent = DebugGraphState(slug="parent-session", trigger="original issue")
    parent.status = DebugStatus.AWAITING_HUMAN
    parent.current_node_id = "AwaitingHumanNode"
    handler.save(parent)

    async def fake_run_debug_session(state, handler, *, resumed=False):
        handler.save(state)

    monkeypatch.setattr(cli_module, "generate_slug", lambda _: "follow-up-session")
    monkeypatch.setattr(cli_module, "run_debug_session", fake_run_debug_session)
    monkeypatch.setattr(cli_module, "_project_map_preflight_for_debug", lambda: None)

    result = runner.invoke(app, ["debug", "new follow-up issue"])

    assert result.exit_code == 0
    assert "linked follow-up debug session" in result.stdout.lower()
    child = handler.load(clean_debug_dir / "follow-up-session.md")
    updated_parent = handler.load(clean_debug_dir / "parent-session.md")
    assert child.parent_slug == "parent-session"
    assert updated_parent.child_slugs == ["follow-up-session"]
    assert updated_parent.resume_after_child is True
    assert "follow-up-session" in (updated_parent.current_focus.next_action or "")


def test_debug_resume_prefers_parent_session_after_resolved_child(clean_debug_dir, monkeypatch):
    pytest.importorskip("pydantic_graph")
    import specify_cli.debug.cli as cli_module

    handler = MarkdownPersistenceHandler(clean_debug_dir)
    parent = DebugGraphState(slug="parent-session", trigger="original issue")
    parent.status = DebugStatus.AWAITING_HUMAN
    parent.current_node_id = "AwaitingHumanNode"
    parent.child_slugs = ["follow-up-session"]
    parent.resume_after_child = True
    handler.save(parent)

    child = DebugGraphState(
        slug="follow-up-session",
        trigger="derived issue",
        parent_slug="parent-session",
    )
    child.status = DebugStatus.RESOLVED
    child.current_node_id = "ResolvedNode"
    handler.save(child)

    seen = {}

    async def fake_run_debug_session(state, handler, *, resumed=False):
        seen["slug"] = state.slug
        seen["resumed"] = resumed
        handler.save(state)

    monkeypatch.setattr(cli_module, "run_debug_session", fake_run_debug_session)
    monkeypatch.setattr(cli_module, "_project_map_preflight_for_debug", lambda: None)

    result = runner.invoke(app, ["debug"])

    assert result.exit_code == 0
    assert seen["slug"] == "parent-session"
    assert seen["resumed"] is True
    assert "returning to parent debug session" in result.stdout.lower()


def test_debug_same_issue_feedback_reopens_parent_session(clean_debug_dir, monkeypatch):
    import specify_cli.debug.cli as cli_module

    handler = MarkdownPersistenceHandler(clean_debug_dir)
    state = DebugGraphState(slug="parent-session", trigger="original issue")
    state.status = DebugStatus.AWAITING_HUMAN
    state.current_node_id = "AwaitingHumanNode"
    state.resolution.human_verification_outcome = "same_issue"
    handler.save(state)

    seen = {}

    async def fake_run_debug_session(state, handler, *, resumed=False):
        seen["slug"] = state.slug
        seen["resumed"] = resumed
        state.status = DebugStatus.INVESTIGATING
        handler.save(state)

    monkeypatch.setattr(cli_module, "run_debug_session", fake_run_debug_session)

    result = runner.invoke(app, ["debug"])

    assert result.exit_code == 0
    assert "resuming debug session: parent-session" in result.stdout.lower()
    assert seen["slug"] == "parent-session"
    assert seen["resumed"] is True

def test_debug_awaiting_human_status(clean_debug_dir, monkeypatch):
    import specify_cli.debug.cli as cli_module

    async def fake_run_debug_session(state, handler, *, resumed=False):
        state.status = DebugStatus.AWAITING_HUMAN
        state.resolution.report = (
            "## Awaiting Human Review\n\n"
            "- Root cause: parser boundary issue\n"
            "- Attempted fix: adjusted boundary condition\n"
        )
        handler.save(state)

    monkeypatch.setattr(cli_module, "generate_slug", lambda _: "hitl-test")
    monkeypatch.setattr(cli_module, "run_debug_session", fake_run_debug_session)

    result = runner.invoke(app, ["debug", "parser bug"])

    assert result.exit_code == 0
    assert "awaiting human review" in result.stdout.lower()
    assert "paused" in result.stdout.lower()
    assert "hitl-test.md" in result.stdout


def test_debug_awaiting_human_report_mentions_child_wait_state(clean_debug_dir, monkeypatch):
    import specify_cli.debug.cli as cli_module

    async def fake_run_debug_session(state, handler, *, resumed=False):
        state.status = DebugStatus.AWAITING_HUMAN
        state.waiting_on_child_human_followup = True
        state.child_slugs = ["child-session"]
        state.resolution.human_verification_outcome = "derived_issue"
        state.resolution.report = "## Awaiting Human Review\n\n- Waiting on child follow-up"
        handler.save(state)

    monkeypatch.setattr(cli_module, "generate_slug", lambda _: "parent-session")
    monkeypatch.setattr(cli_module, "run_debug_session", fake_run_debug_session)

    result = runner.invoke(app, ["debug", "parser bug"])

    assert result.exit_code == 0
    assert "awaiting human review" in result.stdout.lower()
    assert "child-session" in result.stdout.lower()


def test_debug_prints_checkpoint_for_incomplete_session(clean_debug_dir, monkeypatch):
    import specify_cli.debug.cli as cli_module

    async def fake_run_debug_session(state, handler, *, resumed=False):
        state.status = DebugStatus.INVESTIGATING
        state.diagnostic_profile = "scheduler-admission"
        state.observer_mode = "full"
        state.observer_framing_completed = True
        state.observer_framing.summary = "Observer framing points to scheduler ownership drift."
        state.observer_framing.primary_suspected_loop = "scheduler-admission"
        state.observer_framing.suspected_owning_layer = "scheduler"
        state.observer_framing.recommended_first_probe = "Compare queue and running sets before reading code."
        state.observer_framing.alternative_cause_candidates = [
            ObserverCauseCandidate(candidate="ownership set never released")
        ]
        state.transition_memo.first_candidate_to_test = "ownership set never released"
        state.transition_memo.why_first = "Best fits the outsider framing."
        state.transition_memo.evidence_unlock = ["reproduction", "logs", "code"]
        state.suggested_evidence_lanes = [
            SuggestedEvidenceLane(
                name="queue-snapshot",
                focus="waiting and promotion flow",
                evidence_to_collect=["queue contents before the decision"],
            )
        ]
        state.current_focus.next_action = "Fill in truth ownership map and control state inventory."
        handler.save(state)

    monkeypatch.setattr(cli_module, "generate_slug", lambda _: "checkpoint-test")
    monkeypatch.setattr(cli_module, "run_debug_session", fake_run_debug_session)

    result = runner.invoke(app, ["debug", "parser bug"])

    assert result.exit_code == 0
    assert "current stage" in result.stdout.lower()
    assert "diagnostic profile" in result.stdout.lower()
    assert "scheduler-admission" in result.stdout.lower()
    assert "observer framing" in result.stdout.lower()
    assert "primary suspected loop" in result.stdout.lower()
    assert "transition memo" in result.stdout.lower()
    assert "first candidate to test" in result.stdout.lower()
    assert "suggested evidence lanes" in result.stdout.lower()
    assert "suggested codex dispatch" in result.stdout.lower()
    assert "suggested codex spawn payloads" in result.stdout.lower()
    assert "queue-snapshot" in result.stdout.lower()
    assert "investigating" in result.stdout.lower()
    assert "next action" in result.stdout.lower()
    assert "truth ownership map" in result.stdout.lower()
    assert "checkpoint-test.md" in result.stdout


def test_debug_prints_missing_root_cause_fields(clean_debug_dir, monkeypatch):
    import specify_cli.debug.cli as cli_module

    async def fake_run_debug_session(state, handler, *, resumed=False):
        state.status = DebugStatus.FIXING
        state.resolution.root_cause = {"summary": "Parser boundary issue"}
        state.current_focus.next_action = "Add owning layer and broken control state before fixing."
        handler.save(state)

    monkeypatch.setattr(cli_module, "generate_slug", lambda _: "root-cause-test")
    monkeypatch.setattr(cli_module, "run_debug_session", fake_run_debug_session)

    result = runner.invoke(app, ["debug", "parser bug"])

    assert result.exit_code == 0
    assert "root cause draft" in result.stdout.lower()
    assert "summary: parser boundary issue" in result.stdout.lower()
    assert "missing root cause fields" in result.stdout.lower()
    assert "owning layer" in result.stdout.lower()
    assert "broken control state" in result.stdout.lower()
    assert "failure mechanism" in result.stdout.lower()
    assert "next action" in result.stdout.lower()


def test_debug_prints_missing_causal_gate_fields(clean_debug_dir, monkeypatch):
    import specify_cli.debug.cli as cli_module

    async def fake_run_debug_session(state, handler, *, resumed=False):
        state.status = DebugStatus.FIXING
        state.resolution.root_cause = {
            "summary": "Parser boundary issue",
            "owning_layer": "parser",
            "broken_control_state": "token boundary decisions",
            "failure_mechanism": "upper bound truncates the final token",
            "loop_break": "control decision -> state transition",
            "decisive_signal": "caller loses the final token while source parse request is unchanged",
        }
        state.resolution.fix = "Normalize display status"
        handler.save(state)

    monkeypatch.setattr(cli_module, "generate_slug", lambda _: "causal-gates-test")
    monkeypatch.setattr(cli_module, "run_debug_session", fake_run_debug_session)

    result = runner.invoke(app, ["debug", "parser bug"])

    assert result.exit_code == 0
    lowered = result.stdout.lower()
    assert "missing causal gate fields" in lowered
    assert "fix scope classification" in lowered


def test_debug_awaiting_human_status_prints_diagnostic_profile(clean_debug_dir, monkeypatch):
    import specify_cli.debug.cli as cli_module

    async def fake_run_debug_session(state, handler, *, resumed=False):
        state.status = DebugStatus.AWAITING_HUMAN
        state.diagnostic_profile = "cache-snapshot"
        state.resolution.report = (
            "## Awaiting Human Review\n\n"
            "- Diagnostic profile: cache-snapshot\n"
            "- Root cause: stale cache projection\n"
        )
        handler.save(state)

    monkeypatch.setattr(cli_module, "generate_slug", lambda _: "hitl-profile")
    monkeypatch.setattr(cli_module, "run_debug_session", fake_run_debug_session)

    result = runner.invoke(app, ["debug", "stale cache bug"])

    assert result.exit_code == 0
    assert "awaiting human review" in result.stdout.lower()
    assert "diagnostic profile: cache-snapshot" in result.stdout.lower()

def test_debug_alias_present():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "debug" in result.stdout
    assert "sp-debug" in result.stdout


def test_debug_help_lists_dispatch_option():
    result = runner.invoke(app, ["debug", "--help"])
    assert result.exit_code == 0
    normalized = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
    assert "--dispatch" in normalized or "-dispatch" in normalized


def test_debug_dispatch_prints_text_plan(clean_debug_dir, monkeypatch):
    import specify_cli.debug.cli as cli_module
    from specify_cli.debug.schema import SuggestedEvidenceLane

    async def fake_run_debug_session(state, handler, *, resumed=False):
        state.diagnostic_profile = "scheduler-admission"
        state.suggested_evidence_lanes = [
            SuggestedEvidenceLane(
                name="queue-snapshot",
                focus="waiting and promotion flow",
                evidence_to_collect=["queue contents before the decision"],
            )
        ]
        handler.save(state)

    monkeypatch.setattr(cli_module, "generate_slug", lambda _: "dispatch-test")
    monkeypatch.setattr(cli_module, "run_debug_session", fake_run_debug_session)

    result = runner.invoke(app, ["debug", "--dispatch", "queue stuck"])

    assert result.exit_code == 0
    assert "suggested codex dispatch" in result.stdout.lower()
    assert "queue-snapshot" in result.stdout.lower()
    assert "evidence-collector" in result.stdout.lower()


def test_debug_dispatch_prints_json_plan(clean_debug_dir, monkeypatch):
    import specify_cli.debug.cli as cli_module
    from specify_cli.debug.schema import SuggestedEvidenceLane

    async def fake_run_debug_session(state, handler, *, resumed=False):
        state.diagnostic_profile = "cache-snapshot"
        state.suggested_evidence_lanes = [
            SuggestedEvidenceLane(
                name="snapshot-drift-trace",
                focus="cache or snapshot divergence",
                evidence_to_collect=["cached state", "snapshot write timestamp"],
            )
        ]
        handler.save(state)

    monkeypatch.setattr(cli_module, "generate_slug", lambda _: "dispatch-json")
    monkeypatch.setattr(cli_module, "run_debug_session", fake_run_debug_session)

    result = runner.invoke(app, ["debug", "--dispatch", "--format", "json", "stale cache"])

    assert result.exit_code == 0
    assert '"slug": "dispatch-json"' in result.stdout
    assert '"diagnostic_profile": "cache-snapshot"' in result.stdout
    assert '"lane_name": "snapshot-drift-trace"' in result.stdout


def test_debug_dispatch_prints_spawn_json_plan(clean_debug_dir, monkeypatch):
    import specify_cli.debug.cli as cli_module
    from specify_cli.debug.schema import SuggestedEvidenceLane

    async def fake_run_debug_session(state, handler, *, resumed=False):
        state.diagnostic_profile = "ui-projection"
        state.suggested_evidence_lanes = [
            SuggestedEvidenceLane(
                name="source-truth-trace",
                focus="publish-time source state",
                evidence_to_collect=["source-of-truth state at publish time"],
            )
        ]
        handler.save(state)

    monkeypatch.setattr(cli_module, "generate_slug", lambda _: "dispatch-spawn")
    monkeypatch.setattr(cli_module, "run_debug_session", fake_run_debug_session)

    result = runner.invoke(app, ["debug", "--dispatch", "--format", "spawn-json", "ui mismatch"])

    assert result.exit_code == 0
    assert '"slug": "dispatch-spawn"' in result.stdout
    assert '"diagnostic_profile": "ui-projection"' in result.stdout
    assert '"agent_type": "explorer"' in result.stdout
    assert '"lane_name": "source-truth-trace"' in result.stdout
