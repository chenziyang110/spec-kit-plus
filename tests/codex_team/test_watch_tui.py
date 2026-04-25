from __future__ import annotations

import io

from rich.console import Console

from specify_cli.codex_team.watch_state import (
    FailedDispatchSummary,
    WatchFlowSummary,
    WatchMemberSummary,
    WatchSnapshot,
)
from specify_cli.codex_team.watch_tui import WatchUiState, handle_watch_input, render_watch_dashboard, run_team_watch


def _sample_snapshot() -> WatchSnapshot:
    return WatchSnapshot(
        session_id="default",
        session_status="running",
        member_count=2,
        task_count=2,
        members=[
            WatchMemberSummary(
                worker_id="worker-1",
                status="executing",
                task_id="T001",
                task_summary="Implement watch snapshot aggregation",
                freshness="fresh",
                activity_age_seconds=4,
            ),
            WatchMemberSummary(
                worker_id="worker-2",
                status="blocked",
                task_id="T002",
                task_summary="Fix blocked dispatch",
                freshness="stale",
                activity_age_seconds=95,
            ),
        ],
        flow=WatchFlowSummary(
            task_status_counts={"in_progress": 1, "pending": 1},
            blocked_batch_ids=["batch-1"],
            awaiting_review_batch_ids=["batch-1"],
            failed_dispatches=[
                FailedDispatchSummary(
                    request_id="req-1",
                    target_worker="worker-2",
                    reason="leader pane missing",
                    status="failed",
                )
            ],
        ),
        problems=[],
    )


def _render_text(state: WatchUiState) -> str:
    console = Console(width=120, record=True)
    console.print(render_watch_dashboard(_sample_snapshot(), state))
    return console.export_text()


def test_render_watch_dashboard_shows_split_stage_layout() -> None:
    output = _render_text(WatchUiState(view="split", focus_index=0, expanded=False))

    assert "Member Stage" in output
    assert "Flow Stage" in output
    assert "worker-1" in output
    assert "worker-2" in output
    assert "batch-1" in output


def test_handle_watch_input_cycles_focus_view_and_expansion() -> None:
    snapshot = _sample_snapshot()
    state = WatchUiState(view="split", focus_index=0, expanded=False)

    state = handle_watch_input(state, "tab", snapshot)
    assert state.focus_index == 1

    state = handle_watch_input(state, "f", snapshot)
    assert state.view == "members"

    state = handle_watch_input(state, "enter", snapshot)
    assert state.expanded is True

    output = _render_text(state)
    assert "Focused Detail" in output
    assert "Fix blocked dispatch" in output


def test_handle_watch_input_marks_exit_on_q() -> None:
    snapshot = _sample_snapshot()
    state = WatchUiState(view="split", focus_index=0, expanded=False)

    next_state = handle_watch_input(state, "q", snapshot)

    assert next_state.should_exit is True


def test_run_team_watch_exits_cleanly_on_mocked_q(monkeypatch) -> None:
    monkeypatch.setattr("specify_cli.codex_team.watch_tui.build_watch_snapshot", lambda *args, **kwargs: _sample_snapshot())
    monkeypatch.setattr("specify_cli.codex_team.watch_tui._poll_watch_key", lambda timeout_seconds: "q")

    output = io.StringIO()
    console = Console(file=output, width=120, force_terminal=False)

    run_team_watch(
        ".",
        session_id="default",
        refresh_interval=0.1,
        focus="worker-1",
        view="split",
        console=console,
    )
