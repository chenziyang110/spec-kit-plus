import typer
import asyncio
from typing import Optional
from pathlib import Path
from rich.console import Console

from .schema import DebugGraphState
from .persistence import MarkdownPersistenceHandler
from .utils import generate_slug, get_debug_dir
from .graph import run_debug_session

console = Console()
debug_app = typer.Typer(help="Systematic debugging engine for Spec Kit Plus.")

@debug_app.callback(invoke_without_command=True)
def debug_command(
    ctx: typer.Context,
    description: Optional[str] = typer.Argument(None, help="Brief description of the bug to start a new investigation.")
):
    """
    Start a new debug investigation or resume the most recent one.
    """
    if ctx.invoked_subcommand is not None:
        return

    asyncio.run(_run_debug(description))

async def _run_debug(description: Optional[str]):
    debug_dir = get_debug_dir()
    handler = MarkdownPersistenceHandler(debug_dir)
    
    state: Optional[DebugGraphState] = None
    
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
            console.print(f"[cyan]Resuming debug session:[/cyan] {state.slug}")
        else:
            console.print("[red]Error:[/red] No description provided and no recent session found to resume.")
            console.print("Usage: specify debug \"description of the bug\"")
            raise typer.Exit(1)
            
    try:
        await run_debug_session(state, handler)
    except Exception as e:
        console.print(f"[red]Error during debug session:[/red] {e}")
        raise typer.Exit(1)

if __name__ == "__main__":
    debug_app()
