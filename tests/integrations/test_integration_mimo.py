"""Tests for the MiMo Code integration."""


def test_mimo_init_installs_official_command_surface_and_agents_rules(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "mimo-runtime"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "mimo", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai mimo failed: {result.output}"
    assert (target / ".mimocode" / "commands" / "sp.plan.md").exists()
    assert (target / ".mimocode" / "commands" / "sp.specify.md").exists()
    assert (target / "AGENTS.md").exists()
    assert (target / ".specify" / "integrations" / "mimo" / "scripts" / "update-context.sh").exists()
    assert (target / ".specify" / "integrations" / "mimo" / "scripts" / "update-context.ps1").exists()


def test_mimo_update_context_wrappers_route_to_mimo_agent_key():
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    bash_wrapper = (
        repo_root / "src" / "specify_cli" / "integrations" / "mimo" / "scripts" / "update-context.sh"
    ).read_text(encoding="utf-8")
    pwsh_wrapper = (
        repo_root / "src" / "specify_cli" / "integrations" / "mimo" / "scripts" / "update-context.ps1"
    ).read_text(encoding="utf-8")

    assert "update-agent-context.sh\" mimo" in bash_wrapper
    assert "-AgentType mimo" in pwsh_wrapper
