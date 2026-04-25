from pathlib import Path

from specify_cli.codex_team.commands import runtime_state_summary, team_help_text


def test_runtime_state_summary_mentions_join_points_retry_and_blockers(tmp_path: Path):
    summary = runtime_state_summary(tmp_path)

    lowered = summary.lower()
    assert "join points" in lowered
    assert "retry-pending" in lowered or "retry pending" in lowered
    assert "blockers" in lowered


def test_team_help_text_mentions_submit_result_surface() -> None:
    help_text = team_help_text().lower()

    assert "submit-result" in help_text
    assert "structured worker results" in help_text
    assert "result-template" in help_text
    assert "print-schema" in help_text
