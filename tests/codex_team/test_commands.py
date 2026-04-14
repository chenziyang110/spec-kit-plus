from pathlib import Path

from specify_cli.codex_team.commands import runtime_state_summary


def test_runtime_state_summary_mentions_join_points_retry_and_blockers(tmp_path: Path):
    summary = runtime_state_summary(tmp_path)

    lowered = summary.lower()
    assert "join points" in lowered
    assert "retry-pending" in lowered or "retry pending" in lowered
    assert "blockers" in lowered
