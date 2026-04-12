import pytest
from typer.testing import CliRunner
from specify_cli import app
from pathlib import Path
import shutil
import os

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
    # Mocking run_debug_session to avoid long running asyncio
    # Actually, the cli.py calls asyncio.run(_run_debug(description))
    # And _run_debug calls await run_debug_session(state, handler)
    
    # Let's just check if it generates a slug and starts a session
    # We might need to mock run_debug_session because it might try to do real AI calls or wait for input
    pass

def test_debug_alias_present():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "debug" in result.stdout
    assert "sp-debug" in result.stdout
