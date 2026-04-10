"""Contract tests for the Codex team CLI surface."""

from specify_cli.codex_team.commands import TEAM_COMMAND_NAME, team_availability_message, team_help_text


def test_team_command_uses_specify_owned_surface():
    assert TEAM_COMMAND_NAME == "specify team"
    assert "specify team" in team_help_text()
    assert "omx" in team_help_text()


def test_team_availability_message_is_codex_only():
    assert "available" in team_availability_message("codex")
    assert "only available for Codex" in team_availability_message("claude")
