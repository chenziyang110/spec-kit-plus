import pytest
from typer.testing import CliRunner
from specify_cli import app
from pathlib import Path
import shutil
import os
from specify_cli.debug.schema import DebugStatus
from specify_cli.debug.persistence import MarkdownPersistenceHandler
from specify_cli.debug.schema import DebugGraphState, SuggestedEvidenceLane

runner = CliRunner()

@pytest.fixture
def clean_debug_dir():
    debug_dir = Path.cwd() / ".planning" / "debug"
    if debug_dir.exists():
        shutil.rmtree(debug_dir)
    debug_dir.mkdir(parents=True, exist_ok=True)
    yield debug_dir
    # Clean up after test if needed
    # shutil.rmtree(debug_dir)

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


def test_debug_prints_checkpoint_for_incomplete_session(clean_debug_dir, monkeypatch):
    import specify_cli.debug.cli as cli_module

    async def fake_run_debug_session(state, handler, *, resumed=False):
        state.status = DebugStatus.INVESTIGATING
        state.diagnostic_profile = "scheduler-admission"
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
    assert "--dispatch" in result.stdout


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
