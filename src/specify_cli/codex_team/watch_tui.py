"""Rich renderers and lightweight interaction state for `specify team watch`."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, replace
import os
import sys
import time

from rich.console import Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .watch_state import WatchFlowSummary, WatchSnapshot, build_watch_snapshot


WATCH_VIEWS = ("split", "members", "flow")


@dataclass(slots=True)
class WatchUiState:
    view: str = "split"
    focus_index: int = 0
    expanded: bool = False
    should_exit: bool = False


def _bounded_focus_index(state: WatchUiState, snapshot: WatchSnapshot) -> int:
    if not snapshot.members:
        return 0
    return max(0, min(state.focus_index, len(snapshot.members) - 1))


def handle_watch_input(state: WatchUiState, key: str, snapshot: WatchSnapshot) -> WatchUiState:
    focus_index = _bounded_focus_index(state, snapshot)
    normalized = key.lower()

    if normalized in {"q", "quit"}:
        return replace(state, focus_index=focus_index, should_exit=True)

    if normalized in {"tab", "right", "down"} and snapshot.members:
        return replace(state, focus_index=(focus_index + 1) % len(snapshot.members))

    if normalized in {"shift-tab", "left", "up"} and snapshot.members:
        return replace(state, focus_index=(focus_index - 1) % len(snapshot.members))

    if normalized == "f":
        current_index = WATCH_VIEWS.index(state.view) if state.view in WATCH_VIEWS else 0
        return replace(state, view=WATCH_VIEWS[(current_index + 1) % len(WATCH_VIEWS)])

    if normalized == "enter":
        return replace(state, expanded=not state.expanded, focus_index=focus_index)

    return replace(state, focus_index=focus_index)


def _member_stage(snapshot: WatchSnapshot, state: WatchUiState):
    table = Table(expand=True, box=None, padding=(0, 1))
    table.add_column("Member", ratio=2)
    table.add_column("State", ratio=1)
    table.add_column("Task", ratio=3)
    table.add_column("Freshness", ratio=1)

    focus_index = _bounded_focus_index(state, snapshot)
    for index, member in enumerate(snapshot.members):
        name = f"> {member.worker_id}" if index == focus_index else f"  {member.worker_id}"
        status_style = "bold cyan" if index == focus_index else "white"
        table.add_row(
            Text(name, style=status_style),
            Text(member.status, style=status_style),
            Text(member.task_summary or "-", style="white"),
            Text(member.freshness, style="yellow" if member.freshness != "fresh" else "green"),
        )

    title = f"Member Stage  [{snapshot.member_count} active]"
    return Panel(table, title=title, border_style="cyan")


def _flow_stage(flow: WatchFlowSummary):
    summary = Table(expand=True, box=None, padding=(0, 1))
    summary.add_column("Metric", ratio=2)
    summary.add_column("Value", ratio=4)

    counts = ", ".join(f"{status}:{count}" for status, count in sorted(flow.task_status_counts.items())) or "none"
    blocked = ", ".join(flow.blocked_batch_ids) or "none"
    review = ", ".join(flow.awaiting_review_batch_ids) or "none"
    failed = ", ".join(f"{item.request_id} -> {item.target_worker}" for item in flow.failed_dispatches) or "none"

    summary.add_row("Task Status", counts)
    summary.add_row("Blocked Batches", blocked)
    summary.add_row("Review Queue", review)
    summary.add_row("Failed Dispatches", failed)

    return Panel(summary, title="Flow Stage", border_style="bright_blue")


def _focused_detail(snapshot: WatchSnapshot, state: WatchUiState):
    if not snapshot.members:
        return None
    member = snapshot.members[_bounded_focus_index(state, snapshot)]
    rows = Table(expand=True, box=None, padding=(0, 1))
    rows.add_column("Field", ratio=1)
    rows.add_column("Value", ratio=4)
    rows.add_row("Member", member.worker_id)
    rows.add_row("State", member.status)
    rows.add_row("Task", member.task_id or "-")
    rows.add_row("Summary", member.task_summary or "-")
    rows.add_row("Freshness", member.freshness)
    rows.add_row("Age", "-" if member.activity_age_seconds is None else f"{member.activity_age_seconds}s")
    return Panel(rows, title="Focused Detail", border_style="magenta")


def _watch_footer(snapshot: WatchSnapshot):
    text = Text()
    text.append(f"session {snapshot.session_id} ", style="bold white")
    text.append(f"({snapshot.session_status})", style="cyan")
    text.append("  - keys: Tab focus  Enter detail  F view  Q quit", style="bright_black")
    return Panel(text, border_style="bright_black")


def _problem_panel(snapshot: WatchSnapshot):
    if not snapshot.problems:
        return None
    table = Table(expand=True, box=None, padding=(0, 1))
    table.add_column("Problem", ratio=1)
    table.add_column("Detail", ratio=4)
    for problem in snapshot.problems[:5]:
        table.add_row(problem.kind, problem.message)
    return Panel(table, title="State Warnings", border_style="yellow")


def render_watch_dashboard(snapshot: WatchSnapshot, state: WatchUiState):
    panels: list[object] = []
    if state.view == "split":
        layout = Layout()
        layout.split_row(
            Layout(_member_stage(snapshot, state), name="members"),
            Layout(_flow_stage(snapshot.flow), name="flow"),
        )
        panels.append(layout)
    elif state.view == "members":
        panels.append(_member_stage(snapshot, state))
    elif state.view == "flow":
        panels.append(_flow_stage(snapshot.flow))

    if state.expanded:
        detail = _focused_detail(snapshot, state)
        if detail is not None:
            panels.append(detail)

    problems = _problem_panel(snapshot)
    if problems is not None:
        panels.append(problems)

    panels.append(_watch_footer(snapshot))
    return Group(*panels)


def _initial_watch_ui_state(snapshot: WatchSnapshot, *, focus: str, view: str) -> WatchUiState:
    normalized_view = view if view in WATCH_VIEWS else "split"
    focus_index = 0
    if focus:
        for index, member in enumerate(snapshot.members):
            if member.worker_id == focus:
                focus_index = index
                break
    return WatchUiState(view=normalized_view, focus_index=focus_index)


@contextmanager
def _raw_terminal_mode():
    if os.name == "nt" or not sys.stdin.isatty():
        yield
        return

    import termios
    import tty

    fd = sys.stdin.fileno()
    previous = termios.tcgetattr(fd)
    try:
        tty.setcbreak(fd)
        yield
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, previous)


def _read_windows_key(timeout_seconds: float) -> str | None:
    import msvcrt

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if msvcrt.kbhit():
            char = msvcrt.getwch()
            if char in {"\x00", "\xe0"} and msvcrt.kbhit():
                arrow = msvcrt.getwch()
                return {
                    "H": "up",
                    "P": "down",
                    "K": "left",
                    "M": "right",
                }.get(arrow)
            return {
                "\t": "tab",
                "\r": "enter",
            }.get(char, char)
        time.sleep(0.05)
    return None


def _read_posix_key(timeout_seconds: float) -> str | None:
    import select

    ready, _, _ = select.select([sys.stdin], [], [], timeout_seconds)
    if not ready:
        return None

    char = sys.stdin.read(1)
    if char == "\t":
        return "tab"
    if char in {"\n", "\r"}:
        return "enter"
    if char != "\x1b":
        return char

    ready, _, _ = select.select([sys.stdin], [], [], 0.02)
    if not ready:
        return "escape"
    remainder = sys.stdin.read(2)
    return {
        "[A": "up",
        "[B": "down",
        "[C": "right",
        "[D": "left",
        "[Z": "shift-tab",
    }.get(remainder, "escape")


def _poll_watch_key(timeout_seconds: float) -> str | None:
    if timeout_seconds <= 0:
        return None
    if os.name == "nt":
        return _read_windows_key(timeout_seconds)
    return _read_posix_key(timeout_seconds)


def run_team_watch(
    project_root,
    *,
    session_id: str,
    refresh_interval: float,
    focus: str,
    view: str,
    console=None,
) -> None:
    from specify_cli import console as default_console

    render_console = console or default_console
    snapshot = build_watch_snapshot(project_root, session_id=session_id)
    state = _initial_watch_ui_state(snapshot, focus=focus, view=view)

    with _raw_terminal_mode():
        with Live(
            render_watch_dashboard(snapshot, state),
            console=render_console,
            screen=True,
            auto_refresh=False,
            transient=True,
        ) as live:
            while not state.should_exit:
                snapshot = build_watch_snapshot(project_root, session_id=session_id)
                state = replace(state, focus_index=_bounded_focus_index(state, snapshot))
                live.update(render_watch_dashboard(snapshot, state), refresh=True)
                key = _poll_watch_key(refresh_interval)
                if key is None:
                    continue
                state = handle_watch_input(state, key, snapshot)
