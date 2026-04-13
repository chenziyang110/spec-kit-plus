import pytest
from typer.testing import CliRunner
from specify_cli import app
from pathlib import Path
import shutil
import os
from specify_cli.debug.schema import DebugStatus
from specify_cli.debug.persistence import MarkdownPersistenceHandler
from specify_cli.debug.schema import DebugGraphState

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

def test_debug_alias_present():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "debug" in result.stdout
    assert "sp-debug" in result.stdout
