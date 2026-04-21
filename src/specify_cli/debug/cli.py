import typer
import asyncio
import json
from typing import Optional
from pathlib import Path
from rich.console import Console

from .schema import DebugGraphState, DebugStatus
from .persistence import MarkdownPersistenceHandler
from .dispatch import (
    build_codex_dispatch_plan,
    build_codex_spawn_plan,
    format_dispatch_plan,
    format_spawn_plan,
)
from .utils import generate_slug, get_debug_dir
from .graph import run_debug_session
from ..project_map_status import inspect_project_map_freshness

console = Console()
debug_app = typer.Typer(help="Systematic debugging engine for Spec Kit Plus.")


def _project_map_preflight_for_debug() -> None:
    project_root = Path.cwd()
    if not (project_root / ".specify").exists():
        return

    result = inspect_project_map_freshness(project_root)
    freshness = result["freshness"]
    if freshness in {"missing", "stale"}:
        console.print(
            f"[red]Error:[/red] Project-map freshness is {freshness}. Refresh `PROJECT-HANDBOOK.md` and `.specify/project-map/` before debug."
        )
        for reason in result.get("reasons", []):
            console.print(f"- {reason}")
        raise typer.Exit(1)

    if freshness == "possibly_stale":
        console.print(
            "[yellow]Warning:[/yellow] Project-map freshness is possibly_stale. Continue only if the investigation is still local."
        )
        for reason in result.get("reasons", []):
            console.print(f"- {reason}")


def _print_root_cause_summary(state: DebugGraphState) -> None:
    root_cause = state.resolution.root_cause
    if not root_cause:
        return

    console.print("[bold]Root Cause Draft[/bold]")
    if root_cause.summary:
        console.print(f"- Summary: {root_cause.summary}")
    if root_cause.owning_layer:
        console.print(f"- Owning layer: {root_cause.owning_layer}")
    if root_cause.broken_control_state:
        console.print(f"- Broken control state: {root_cause.broken_control_state}")
    if root_cause.failure_mechanism:
        console.print(f"- Failure mechanism: {root_cause.failure_mechanism}")
    if root_cause.loop_break:
        console.print(f"- Closed-loop break: {root_cause.loop_break}")
    if root_cause.decisive_signal:
        console.print(f"- Primary decisive signal: {root_cause.decisive_signal}")


def _missing_root_cause_fields(state: DebugGraphState) -> list[str]:
    root_cause = state.resolution.root_cause
    if not root_cause:
        return [
            "root cause summary",
            "owning layer",
            "broken control state",
            "failure mechanism",
            "closed-loop break",
            "primary decisive signal",
        ]

    missing: list[str] = []
    if not root_cause.summary:
        missing.append("root cause summary")
    if not root_cause.owning_layer:
        missing.append("owning layer")
    if not root_cause.broken_control_state:
        missing.append("broken control state")
    if not root_cause.failure_mechanism:
        missing.append("failure mechanism")
    if not root_cause.loop_break:
        missing.append("closed-loop break")
    if not root_cause.decisive_signal:
        missing.append("primary decisive signal")
    return missing


def _print_session_checkpoint(state: DebugGraphState, handler: MarkdownPersistenceHandler) -> None:
    session_path = handler.debug_dir / f"{state.slug}.md"
    console.print(f"[cyan]Current stage:[/cyan] {state.status.value}")
    if state.diagnostic_profile:
        console.print(f"[cyan]Diagnostic profile:[/cyan] {state.diagnostic_profile}")
    if state.suggested_evidence_lanes:
        console.print("[bold]Suggested Evidence Lanes[/bold]")
        for lane in state.suggested_evidence_lanes:
            console.print(f"- {lane.name}: {lane.focus}")
        dispatch_plan = build_codex_dispatch_plan(state)
        if dispatch_plan:
            console.print("[bold]Suggested Codex Dispatch[/bold]")
            for task in dispatch_plan:
                console.print(f"- {task.lane_name}: {task.task_summary}")
        spawn_plan = build_codex_spawn_plan(state)
        if spawn_plan:
            console.print("[bold]Suggested Codex Spawn Payloads[/bold]")
            for task in spawn_plan:
                console.print(f"- {task.lane_name}: {task.agent_type} ({task.reasoning_effort})")
    _print_root_cause_summary(state)

    missing_root_fields = _missing_root_cause_fields(state)
    if missing_root_fields and state.resolution.root_cause:
        console.print("[bold]Missing Root Cause Fields[/bold]")
        for field in missing_root_fields:
            console.print(f"- {field}")

    if state.current_focus.next_action:
        console.print("[bold]Next Action[/bold]")
        console.print(state.current_focus.next_action)

    console.print(f"[cyan]Session file:[/cyan] {session_path}")

@debug_app.callback(invoke_without_command=True)
def debug_command(
    ctx: typer.Context,
    description: Optional[str] = typer.Argument(None, help="Brief description of the bug to start a new investigation."),
    dispatch_plan: bool = typer.Option(False, "--dispatch", help="Render the suggested Codex child-agent dispatch plan instead of the standard debug checkpoint."),
    output_format: str = typer.Option("text", "--format", help="Output format for --dispatch: text, json, or spawn-json."),
):
    """
    Start a new debug investigation or resume the most recent one.
    """
    if ctx.invoked_subcommand is not None:
        return

    if dispatch_plan:
        asyncio.run(_run_debug_dispatch(description, output_format))
    else:
        asyncio.run(_run_debug(description))

async def _run_debug(description: Optional[str]):
    _project_map_preflight_for_debug()
    debug_dir = get_debug_dir()
    handler = MarkdownPersistenceHandler(debug_dir)
    
    state: Optional[DebugGraphState] = None
    resumed = False
    
    if description:
        # Start new session
        slug = generate_slug(description)
        state = DebugGraphState(
            slug=slug,
            trigger=description
        )
        console.print(f"[green]Starting new debug session:[/green] {slug}")
    else:
        # Try to resume
        state = handler.load_most_recent_session()
        if state:
            resumed = True
            console.print(f"[cyan]Resuming debug session:[/cyan] {state.slug}")
        else:
            console.print("[red]Error:[/red] No description provided and no recent session found to resume.")
            console.print("Usage: specify debug \"description of the bug\"")
            raise typer.Exit(1)
            
    try:
        await run_debug_session(state, handler, resumed=resumed)
        if state.status == DebugStatus.AWAITING_HUMAN:
            session_path = handler.debug_dir / f"{state.slug}.md"
            report = state.resolution.report or "No session summary was generated."
            console.print("[yellow]Awaiting Human Review[/yellow]")
            console.print(report)
            console.print(f"[yellow]Session paused.[/yellow] Continue from: {session_path}")
        elif state.status != DebugStatus.RESOLVED:
            _print_session_checkpoint(state, handler)
    except Exception as e:
        console.print(f"[red]Error during debug session:[/red] {e}")
        raise typer.Exit(1)


async def _load_or_create_debug_state(description: Optional[str]) -> tuple[DebugGraphState, MarkdownPersistenceHandler, bool]:
    debug_dir = get_debug_dir()
    handler = MarkdownPersistenceHandler(debug_dir)

    if description:
        slug = generate_slug(description)
        state = DebugGraphState(slug=slug, trigger=description)
        return state, handler, False

    state = handler.load_most_recent_session()
    if state:
        return state, handler, True

    console.print("[red]Error:[/red] No description provided and no recent session found to resume.")
    console.print("Usage: specify debug dispatch \"description of the bug\"")
    raise typer.Exit(1)


async def _run_debug_dispatch(description: Optional[str], output_format: str) -> None:
    _project_map_preflight_for_debug()
    state, handler, resumed = await _load_or_create_debug_state(description)
    await run_debug_session(state, handler, resumed=resumed)

    tasks = build_codex_dispatch_plan(state)
    spawn_tasks = build_codex_spawn_plan(state)
    if output_format.lower() == "json":
        payload = {
            "slug": state.slug,
            "diagnostic_profile": state.diagnostic_profile,
            "tasks": [task.model_dump(mode="json") for task in tasks],
        }
        console.print(json.dumps(payload, indent=2))
        return
    if output_format.lower() == "spawn-json":
        payload = {
            "slug": state.slug,
            "diagnostic_profile": state.diagnostic_profile,
            "spawn_tasks": [task.model_dump(mode="json") for task in spawn_tasks],
        }
        console.print(json.dumps(payload, indent=2))
        return

    console.print(format_dispatch_plan(tasks))
    if spawn_tasks:
        console.print(format_spawn_plan(spawn_tasks))

if __name__ == "__main__":
    debug_app()
