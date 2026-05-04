#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer",
#     "rich",
#     "platformdirs",
#     "readchar",
#     "json5",
# ]
# ///
"""
Specify CLI - Setup tool for Specify projects

Usage:
    uvx specify-cli.py init <project-name>
    uvx specify-cli.py init .
    uvx specify-cli.py init --here

Or install globally:
    uv tool install --from specify-cli.py specify-cli
    specify init <project-name>
    specify init .
    specify init --here
"""

import os
import re
import subprocess
import sys
import zipfile
import tempfile
import shutil
import json
import json5
import stat
import yaml
from datetime import date
from pathlib import Path
from typing import Any, Optional, Tuple

import typer
from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.align import Align
from rich.table import Table
from rich.tree import Tree
from typer.core import TyperGroup

# For cross-platform keyboard input
import readchar

from specify_cli.codex_team import (
    codex_team_doctor,
    codex_team_live_probe,
    codex_team_runtime_status,
    runtime_state_summary,
    session_ops,
    team_availability_message,
    team_help_text,
)
from specify_cli.codex_team.watch_tui import run_team_watch
from specify_cli.codex_team.auto_dispatch import (
    AutoDispatchError,
    AutoDispatchUnavailableError,
    complete_dispatched_batch,
    route_ready_parallel_batch,
)
from specify_cli.codex_team.result_template import (
    build_request_result_template,
    normalize_result_submission,
    render_schema_help,
)
from specify_cli.codex_team.sync_back import apply_sync_back, plan_sync_back
from specify_cli.codex_team.runtime_bridge import (
    RuntimeEnvironmentError,
    detect_team_runtime_backend,
    dispatch_runtime_task,
    ensure_tmux_available,
    mark_runtime_failure,
    submit_runtime_result,
)
from specify_cli.execution import (
    build_result_handoff_path,
    write_normalized_result_handoff,
)
from specify_cli.eval_runner import run_eval_suite
from specify_cli.evals import create_eval_case, eval_status_payload
from specify_cli.learning_aggregate import (
    aggregate_learning_state,
    write_learning_aggregate_report,
)
from specify_cli.learnings import (
    capture_auto_learning,
    capture_learning,
    ensure_learning_files,
    ensure_learning_memory_from_templates,
    learning_status_payload,
    promote_learning,
    start_learning_session,
)
from specify_cli.project_map_status import (
    ProjectMapStatus,
    TOPIC_FILES,
    clear_project_map_dirty,
    complete_project_map_refresh,
    git_branch_name,
    git_head_commit,
    inspect_project_map_freshness,
    legacy_project_map_status_path,
    mark_project_map_dirty,
    mark_project_map_refreshed,
    missing_canonical_project_map_paths,
    project_map_status_path,
    read_project_map_status,
    refresh_project_map_topics,
    write_project_map_status,
)
from specify_cli.lanes import (
    LaneRecord,
    assess_integration_readiness,
    append_lane_event,
    collect_integration_candidates,
    infer_lane_command_name,
    iter_lane_records,
    materialize_lane_worktree,
    mark_lane_integrated,
    read_lane_record,
    rebuild_lane_index,
    resolve_lane_for_command,
    write_lane_record,
)

def _build_agent_config() -> dict[str, dict[str, Any]]:
    """Derive AGENT_CONFIG from INTEGRATION_REGISTRY."""
    from .integrations import INTEGRATION_REGISTRY
    config: dict[str, dict[str, Any]] = {}
    for key, integration in INTEGRATION_REGISTRY.items():
        if integration.config:
            config[key] = dict(integration.config)
    return config

AGENT_CONFIG = _build_agent_config()

AI_ASSISTANT_ALIASES = {
    "kiro": "kiro-cli",
}

# Agents that use TOML command format (others use Markdown)
_TOML_AGENTS = frozenset({"gemini", "tabnine"})

def _build_ai_assistant_help() -> str:
    """Build the --ai help text from AGENT_CONFIG so it stays in sync with runtime config."""

    non_generic_agents = sorted(agent for agent in AGENT_CONFIG if agent != "generic")
    base_help = (
        f"AI assistant to use: {', '.join(non_generic_agents)}, "
        "or generic (requires --ai-commands-dir)."
    )

    if not AI_ASSISTANT_ALIASES:
        return base_help

    alias_phrases = []
    for alias, target in sorted(AI_ASSISTANT_ALIASES.items()):
        alias_phrases.append(f"'{alias}' as an alias for '{target}'")

    if len(alias_phrases) == 1:
        aliases_text = alias_phrases[0]
    else:
        aliases_text = ', '.join(alias_phrases[:-1]) + ' and ' + alias_phrases[-1]

    return base_help + " Use " + aliases_text + "."
AI_ASSISTANT_HELP = _build_ai_assistant_help()

SCRIPT_TYPE_CHOICES = {"sh": "POSIX Shell (bash/zsh)", "ps": "PowerShell"}
CONSTITUTION_PROFILE_CHOICES = {
    "product": "Balanced default for application and product repositories",
    "minimal": "Lean default for small repositories and low-ceremony teams",
    "library": "Compatibility-focused default for reusable packages and CLIs",
    "regulated": "Higher-control default for security, compliance, and auditability",
}
CONSTITUTION_PROFILE_ALIASES = {
    "default": "product",
}

CLAUDE_LOCAL_PATH = Path.home() / ".claude" / "local" / "claude"
CLAUDE_NPM_LOCAL_PATH = Path.home() / ".claude" / "local" / "node_modules" / ".bin" / "claude"

BANNER = """
███████╗██████╗ ███████╗ ██████╗██╗███████╗██╗   ██╗
██╔════╝██╔══██╗██╔════╝██╔════╝██║██╔════╝╚██╗ ██╔╝
███████╗██████╔╝█████╗  ██║     ██║█████╗   ╚████╔╝
╚════██║██╔═══╝ ██╔══╝  ██║     ██║██╔══╝    ╚██╔╝
███████║██║     ███████╗╚██████╗██║██║        ██║
╚══════╝╚═╝     ╚══════╝ ╚═════╝╚═╝╚═╝        ╚═╝
"""

APP_NAME = "Spec Kit Plus"
TAGLINE = "Spec Kit Plus - Spec-Driven Development Toolkit"


def _require_spec_kit_plus_project(project_root: Path) -> Path:
    specify_dir = project_root / ".specify"
    if not specify_dir.exists():
        console.print("[red]Error:[/red] Not a Spec Kit Plus project (no .specify/ directory)")
        console.print("Run this command from a Spec Kit Plus project root")
        raise typer.Exit(1)
    return specify_dir


class StepTracker:
    """Track and render hierarchical steps without emojis, similar to Claude Code tree output.
    Supports live auto-refresh via an attached refresh callback.
    """
    def __init__(self, title: str):
        self.title = title
        self.steps = []  # list of dicts: {key, label, status, detail}
        self.status_order = {"pending": 0, "running": 1, "done": 2, "error": 3, "skipped": 4}
        self._refresh_cb = None  # callable to trigger UI refresh

    def attach_refresh(self, cb):
        self._refresh_cb = cb

    def add(self, key: str, label: str):
        if key not in [s["key"] for s in self.steps]:
            self.steps.append({"key": key, "label": label, "status": "pending", "detail": ""})
            self._maybe_refresh()

    def start(self, key: str, detail: str = ""):
        self._update(key, status="running", detail=detail)

    def complete(self, key: str, detail: str = ""):
        self._update(key, status="done", detail=detail)

    def error(self, key: str, detail: str = ""):
        self._update(key, status="error", detail=detail)

    def skip(self, key: str, detail: str = ""):
        self._update(key, status="skipped", detail=detail)

    def _update(self, key: str, status: str, detail: str):
        for s in self.steps:
            if s["key"] == key:
                s["status"] = status
                if detail:
                    s["detail"] = detail
                self._maybe_refresh()
                return

        self.steps.append({"key": key, "label": key, "status": status, "detail": detail})
        self._maybe_refresh()

    def _maybe_refresh(self):
        if self._refresh_cb:
            try:
                self._refresh_cb()
            except Exception:
                pass

    def render(self):
        tree = Tree(f"[cyan]{self.title}[/cyan]", guide_style="grey50")
        for step in self.steps:
            label = step["label"]
            detail_text = step["detail"].strip() if step["detail"] else ""

            status = step["status"]
            if status == "done":
                symbol = "[green]●[/green]"
            elif status == "pending":
                symbol = "[green dim]○[/green dim]"
            elif status == "running":
                symbol = "[cyan]○[/cyan]"
            elif status == "error":
                symbol = "[red]●[/red]"
            elif status == "skipped":
                symbol = "[yellow]○[/yellow]"
            else:
                symbol = " "

            if status == "pending":
                # Entire line light gray (pending)
                if detail_text:
                    line = f"{symbol} [bright_black]{label} ({detail_text})[/bright_black]"
                else:
                    line = f"{symbol} [bright_black]{label}[/bright_black]"
            else:
                # Label white, detail (if any) light gray in parentheses
                if detail_text:
                    line = f"{symbol} [white]{label}[/white] [bright_black]({detail_text})[/bright_black]"
                else:
                    line = f"{symbol} [white]{label}[/white]"

            tree.add(line)
        return tree

def get_key():
    """Get a single keypress in a cross-platform way using readchar."""
    key = readchar.readkey()

    if key == readchar.key.UP or key == readchar.key.CTRL_P:
        return 'up'
    if key == readchar.key.DOWN or key == readchar.key.CTRL_N:
        return 'down'

    if key == readchar.key.ENTER:
        return 'enter'

    if key == readchar.key.ESC:
        return 'escape'

    if key == readchar.key.CTRL_C:
        raise KeyboardInterrupt

    return key

def select_with_arrows(options: dict, prompt_text: str = "Select an option", default_key: str = None) -> str:
    """
    Interactive selection using arrow keys with Rich Live display.

    Args:
        options: Dict with keys as option keys and values as descriptions
        prompt_text: Text to show above the options
        default_key: Default option key to start with

    Returns:
        Selected option key
    """
    option_keys = list(options.keys())
    if default_key and default_key in option_keys:
        selected_index = option_keys.index(default_key)
    else:
        selected_index = 0

    selected_key = None

    def create_selection_panel():
        """Create the selection panel with current selection highlighted."""
        table = Table.grid(padding=(0, 2))
        table.add_column(style="cyan", justify="left", width=3)
        table.add_column(style="white", justify="left")

        for i, key in enumerate(option_keys):
            if i == selected_index:
                table.add_row("▶", f"[cyan]{key}[/cyan] [dim]({options[key]})[/dim]")
            else:
                table.add_row(" ", f"[cyan]{key}[/cyan] [dim]({options[key]})[/dim]")

        table.add_row("", "")
        table.add_row("", "[dim]Use ↑/↓ to navigate, Enter to select, Esc to cancel[/dim]")

        return Panel(
            table,
            title=f"[bold]{prompt_text}[/bold]",
            border_style="cyan",
            padding=(1, 2)
        )

    console.print()

    def run_selection_loop():
        nonlocal selected_key, selected_index
        with Live(create_selection_panel(), console=console, transient=True, auto_refresh=False) as live:
            while True:
                try:
                    key = get_key()
                    if key == 'up':
                        selected_index = (selected_index - 1) % len(option_keys)
                    elif key == 'down':
                        selected_index = (selected_index + 1) % len(option_keys)
                    elif key == 'enter':
                        selected_key = option_keys[selected_index]
                        break
                    elif key == 'escape':
                        console.print("\n[yellow]Selection cancelled[/yellow]")
                        raise typer.Exit(1)

                    live.update(create_selection_panel(), refresh=True)

                except KeyboardInterrupt:
                    console.print("\n[yellow]Selection cancelled[/yellow]")
                    raise typer.Exit(1)

    run_selection_loop()

    if selected_key is None:
        console.print("\n[red]Selection failed.[/red]")
        raise typer.Exit(1)

    return selected_key

console = Console()


def _cli_panel(
    renderable,
    *,
    title: str,
    border_style: str,
    padding: tuple[int, int] = (0, 1),
    expand: bool = False,
) -> Panel:
    """Standardize panel hierarchy with short titles and tighter framing."""
    return Panel(
        renderable,
        title=f"[bold]{title}[/bold]",
        title_align="left",
        border_style=border_style,
        padding=padding,
        expand=expand,
    )


def _labeled_grid(rows: list[tuple[str, str]]) -> Table:
    """Render short status/detail rows with consistent label emphasis."""
    table = Table.grid(expand=False, padding=(0, 2))
    table.add_column(style="bold bright_black", justify="right", no_wrap=True)
    table.add_column(style="white")
    for label, value in rows:
        table.add_row(label, value)
    return table


def _command_grid(rows: list[tuple[str, str]]) -> Table:
    """Render command-oriented rows for next steps and enhancement surfaces."""
    table = Table.grid(expand=False, padding=(0, 2))
    table.add_column(style="bold cyan", no_wrap=True)
    table.add_column(style="white")
    for label, value in rows:
        table.add_row(label, value)
    return table

class BannerGroup(TyperGroup):
    """Custom group that shows banner before help."""

    def format_help(self, ctx, formatter):
        # Show banner before help
        show_banner()
        super().format_help(ctx, formatter)


app = typer.Typer(
    name="specify",
    help="Setup tool for Specify spec-driven development projects",
    add_completion=False,
    invoke_without_command=True,
    cls=BannerGroup,
)

teams_app = typer.Typer(
    name="sp-teams",
    help="Codex-only team/runtime surface",
    invoke_without_command=True,
    no_args_is_help=False,
)
app.add_typer(teams_app, name="sp-teams")

quick_app = typer.Typer(
    name="quick",
    help="Inspect and manage tracked quick tasks",
    add_completion=False,
)
app.add_typer(quick_app, name="quick")

implement_app = typer.Typer(
    name="implement",
    help="Inspect and finalize tracked implementation execution state",
    add_completion=False,
)
app.add_typer(implement_app, name="implement")

testing_app = typer.Typer(
    name="testing",
    help="Inspect repository testing inventory and test-system surfaces",
    add_completion=False,
)
app.add_typer(testing_app, name="testing")

project_map_app = typer.Typer(
    name="project-map",
    help="Inspect git-baseline project-map freshness and finalize or override refresh state",
    add_completion=False,
)
app.add_typer(project_map_app, name="project-map")

result_app = typer.Typer(
    name="result",
    help="Inspect and submit subagent result handoffs",
    add_completion=False,
)
app.add_typer(result_app, name="result")

hook_app = typer.Typer(
    name="hook",
    help="Run first-party workflow quality hooks, including project-map refresh finalizers",
    add_completion=False,
)
app.add_typer(hook_app, name="hook")

learning_app = typer.Typer(
    name="learning",
    help="Low-level helper surface for passive project learning files",
    add_completion=False,
)
app.add_typer(learning_app, name="learning")
eval_app = typer.Typer(
    name="eval",
    help="Durable eval case helper commands",
    add_completion=False,
)
app.add_typer(eval_app, name="eval")
lane_app = typer.Typer(
    name="lane",
    help="Inspect and manage concurrent feature lanes",
    add_completion=False,
)
app.add_typer(lane_app, name="lane")

def show_banner():
    """Display the ASCII art banner."""
    banner_lines = BANNER.strip().split('\n')
    colors = ["bright_blue", "blue", "cyan", "bright_cyan", "white", "bright_white"]

    styled_banner = Text()
    for i, line in enumerate(banner_lines):
        color = colors[i % len(colors)]
        styled_banner.append(line + "\n", style=color)

    console.print(Align.center(styled_banner))
    console.print(Align.center(Text(TAGLINE, style="italic bright_yellow")))
    console.print()


def _open_block(
    title: str,
    lines: list[str],
    *,
    accent: str = "cyan",
    subtitle: str | None = None,
) -> Group:
    """Render an open, single-side-emphasis block without a right border."""

    header = Text()
    header.append(title, style=f"bold {accent}")
    if subtitle:
        header.append(" ")
        header.append(subtitle, style="bright_black")

    renderables = [header]
    for line in lines:
        if not line:
            renderables.append(Text(""))
            continue
        row = Text("▌ ", style=accent)
        row.append_text(Text.from_markup(line))
        renderables.append(row)

    return Group(*renderables)

@app.callback()
def callback(ctx: typer.Context):
    """Show banner when no subcommand is provided."""
    if ctx.invoked_subcommand is None and "--help" not in sys.argv and "-h" not in sys.argv:
        show_banner()
        console.print(Align.center("[dim]Run 'specify --help' for usage information[/dim]"))
        console.print()

def run_command(cmd: list[str], check_return: bool = True, capture: bool = False, shell: bool = False) -> Optional[str]:
    """Run a shell command and optionally capture output."""
    try:
        if capture:
            result = subprocess.run(
                cmd,
                check=check_return,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                shell=shell,
            )
            return result.stdout.strip()
        else:
            subprocess.run(cmd, check=check_return, shell=shell)
            return None
    except subprocess.CalledProcessError as e:
        if check_return:
            console.print(f"[red]Error running command:[/red] {' '.join(cmd)}")
            console.print(f"[red]Exit code:[/red] {e.returncode}")
            if hasattr(e, 'stderr') and e.stderr:
                console.print(f"[red]Error output:[/red] {e.stderr}")
            raise
        return None


def _command_path_candidates(command_name: str) -> list[str]:
    """Return every executable candidate for a command found on PATH."""
    candidates: list[str] = []
    seen: set[str] = set()

    path_exts = [""]
    if os.name == "nt":
        raw_exts = os.environ.get("PATHEXT", ".COM;.EXE;.BAT;.CMD")
        path_exts = [ext.lower() for ext in raw_exts.split(os.pathsep) if ext]
        if "" not in path_exts:
            path_exts.insert(0, "")

    command_path = Path(command_name)
    names = [command_name]
    if os.name == "nt" and not command_path.suffix:
        names.extend(f"{command_name}{ext}" for ext in path_exts if ext)

    for path_entry in os.environ.get("PATH", "").split(os.pathsep):
        if not path_entry:
            continue
        path_dir = Path(path_entry)
        for name in names:
            candidate = path_dir / name
            try:
                resolved = str(candidate.resolve())
            except OSError:
                resolved = str(candidate)
            if resolved in seen or not candidate.is_file():
                continue
            seen.add(resolved)
            candidates.append(resolved)

    return candidates


def _current_specify_entrypoint() -> str:
    """Best-effort path for the specify executable that launched this process."""
    argv0 = Path(sys.argv[0])
    if argv0.name.lower().startswith("specify"):
        try:
            if argv0.exists():
                return str(argv0.resolve())
        except OSError:
            return str(argv0)

    first_on_path = shutil.which("specify")
    if first_on_path:
        return first_on_path

    return sys.executable


def _render_project_map_freshness(result: dict[str, Any]) -> None:
    rows = [
        ("Freshness", f"[cyan]{result['freshness']}[/cyan]"),
        ("Status File", f"[dim]{result['status_path']}[/dim]"),
    ]
    if result.get("head_commit"):
        rows.append(("HEAD", f"[dim]{result['head_commit']}[/dim]"))
    if result.get("last_mapped_commit"):
        rows.append(("Mapped Commit", f"[dim]{result['last_mapped_commit']}[/dim]"))
    if result.get("dirty"):
        rows.append(("Dirty", "[yellow]true[/yellow]"))

    console.print(_cli_panel(_labeled_grid(rows), title="Project Map", border_style="cyan"))

    reasons = result.get("reasons") or []
    if reasons:
        console.print("[bold]Reasons[/bold]")
        for reason in reasons:
            console.print(f"- {reason}")

    must_refresh_topics = result.get("must_refresh_topics") or []
    if must_refresh_topics:
        console.print("[bold]Must Refresh Topics[/bold]")
        for topic in must_refresh_topics:
            console.print(f"- {topic}")

    review_topics = result.get("review_topics") or []
    if review_topics:
        console.print("[bold]Review Topics[/bold]")
        for topic in review_topics:
            console.print(f"- {topic}")


def _project_map_preflight(
    project_root: Path,
    *,
    command_name: str,
    block_on: set[str] | None = None,
) -> dict[str, Any]:
    result = inspect_project_map_freshness(project_root)
    block_levels = block_on or {"missing", "stale"}
    freshness = result["freshness"]

    if freshness in block_levels:
        _render_project_map_freshness(result)
        console.print(
            f"[red]Error:[/red] Project-map freshness is {freshness} for [cyan]{command_name}[/cyan]."
        )
        console.print(
            "Run [cyan]/sp-map-scan[/cyan], then [cyan]/sp-map-build[/cyan] to refresh `PROJECT-HANDBOOK.md` and `.specify/project-map/`, then retry."
        )
        raise typer.Exit(1)

    if freshness == "possibly_stale":
        _render_project_map_freshness(result)
        console.print(
            f"[yellow]Warning:[/yellow] Project-map freshness is possibly_stale for [cyan]{command_name}[/cyan]."
        )
        console.print(
            "Continue only if the current task is still local; otherwise refresh the handbook/project-map first."
        )

    return result


def _require_fresh_project_map_for_execution(project_root: Path, *, command_name: str) -> dict[str, Any]:
    return _project_map_preflight(
        project_root,
        command_name=command_name,
        block_on={"missing", "stale"},
    )


def _ensure_project_map_artifacts_exist(project_root: Path) -> list[Path]:
    missing = missing_canonical_project_map_paths(project_root)
    if not missing:
        return []

    console.print("[red]Error:[/red] Cannot record a fresh project-map baseline because canonical map files are missing.")
    for path in missing:
        console.print(f"- {path}")
    console.print(
        "Run [cyan]/sp-map-scan[/cyan], then [cyan]/sp-map-build[/cyan] first so `PROJECT-HANDBOOK.md` and `.specify/project-map/*.md` exist, then retry [cyan]project-map complete-refresh[/cyan]. Use [cyan]project-map record-refresh[/cyan] only for low-level/manual recovery."
    )
    raise typer.Exit(1)


def _project_root_from_source() -> Path:
    return Path(__file__).resolve().parents[2]


def _quick_helper_script() -> tuple[list[str], Path]:
    project_root = _project_root_from_source()
    if os.name == "nt":
        script_path = project_root / "scripts" / "powershell" / "quick-state.ps1"
        if shutil.which("pwsh"):
            return ["pwsh", "-NoProfile", "-File"], script_path
        if shutil.which("powershell"):
            return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File"], script_path
        console.print("[red]Error:[/red] Neither 'pwsh' nor 'powershell' is available")
        raise typer.Exit(1)
    script_path = project_root / "scripts" / "bash" / "quick-state.sh"
    return ["bash"], script_path


def _run_quick_helper(
    mode: str,
    quick_id: str = "",
    status: str = "",
    include_all: bool = False,
) -> dict[str, Any]:
    interpreter, script_path = _quick_helper_script()
    if not script_path.exists():
        console.print(f"[red]Error:[/red] Quick helper script not found: {script_path}")
        raise typer.Exit(1)

    cmd = [
        *interpreter,
        str(script_path),
        str(Path.cwd()),
        mode,
        quick_id,
        status,
        "true" if include_all else "false",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        error_output = (result.stderr or result.stdout or "").strip() or "quick helper failed"
        console.print(f"[red]Error:[/red] {error_output}")
        raise typer.Exit(1)

    raw = (result.stdout or "").strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        console.print(f"[red]Error:[/red] Failed to parse quick helper output: {exc}")
        raise typer.Exit(1) from exc
    if not isinstance(payload, dict):
        console.print("[red]Error:[/red] Quick helper returned an invalid payload")
        raise typer.Exit(1)
    return payload


def _prd_helper_script() -> tuple[list[str], Path]:
    project_root = _project_root_from_source()
    core_pack = _locate_core_pack()
    if os.name == "nt":
        script_path = (
            core_pack / "scripts" / "powershell" / "prd-state.ps1"
            if core_pack is not None
            else project_root / "scripts" / "powershell" / "prd-state.ps1"
        )
        if shutil.which("pwsh"):
            return ["pwsh", "-NoProfile", "-File"], script_path
        if shutil.which("powershell"):
            return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File"], script_path
        console.print("[red]Error:[/red] Neither 'pwsh' nor 'powershell' is available")
        raise typer.Exit(1)
    script_path = (
        core_pack / "scripts" / "bash" / "prd-state.sh"
        if core_pack is not None
        else project_root / "scripts" / "bash" / "prd-state.sh"
    )
    return ["bash"], script_path


def _run_prd_helper(
    mode: str,
    run_slug: str = "",
) -> dict[str, Any]:
    interpreter, script_path = _prd_helper_script()
    if not script_path.exists():
        console.print(f"[red]Error:[/red] PRD helper script not found: {script_path}")
        raise typer.Exit(1)

    cmd = [
        *interpreter,
        str(script_path),
        str(Path.cwd()),
        mode,
        run_slug,
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode != 0:
        error_output = (result.stderr or result.stdout or "").strip() or "PRD helper failed"
        console.print(f"[red]Error:[/red] {error_output}")
        raise typer.Exit(1)

    raw = (result.stdout or "").strip()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        console.print(f"[red]Error:[/red] Failed to parse PRD helper output: {exc}")
        raise typer.Exit(1) from exc
    if not isinstance(payload, dict):
        console.print("[red]Error:[/red] PRD helper returned an invalid payload")
        raise typer.Exit(1)
    return payload


SPEC_KIT_BLOCK_START = "<!-- SPEC-KIT:BEGIN -->"
SPEC_KIT_BLOCK_END = "<!-- SPEC-KIT:END -->"


def _preferred_newline(text: str) -> str:
    if "\r\n" in text:
        return "\r\n"
    if "\n" in text:
        return "\n"
    if "\r" in text:
        return "\r"
    return "\n"


def _render_spec_kit_managed_block(*, newline: str) -> str:
    return newline.join(
        [
            SPEC_KIT_BLOCK_START,
            "## Spec Kit Plus Managed Rules",
            "",
            "- `[AGENT]` marks an action the AI must explicitly execute.",
            "- `[AGENT]` is independent from `[P]`.",
            "",
            "## Workflow Mainline",
            "",
            "- Treat `specify -> plan` as the default path.",
            "- Use `clarify` only when an existing spec needs deeper analysis before planning.",
            "- Use `deep-research` only when requirements are clear but feasibility or the implementation chain must be proven before planning; its research findings, demo evidence, and Planning Handoff become inputs to `plan`.",
            "- Use `prd-scan -> prd-build` as the canonical existing-project reverse PRD lane when the user needs repository-first current-state product documentation; keep `prd` only as a deprecated compatibility entrypoint.",
            "",
            "## Workflow Activation Discipline",
            "",
            "- If there is even a 1% chance an `sp-*` workflow or passive skill applies, route before any response or action, including a clarifying question, file read, shell command, repository inspection, code edit, test run, or summary.",
            "- Do not inspect first outside the workflow; repository inspection belongs inside the selected workflow.",
            "- Name the selected workflow or passive skill in one concise line, then continue under that contract.",
            "",
            "## Brownfield Context Gate",
            "",
            "- `PROJECT-HANDBOOK.md` is the root navigation artifact.",
            "- Deep project knowledge lives under `.specify/project-map/`.",
            "- Before planning, debugging, or implementing against existing code, read `PROJECT-HANDBOOK.md` and the smallest relevant `.specify/project-map/*.md` files.",
            "- If handbook/project-map coverage is missing, stale, or too broad, run the runtime's `map-scan` workflow entrypoint followed by `map-build` before continuing.",
            "- Treat git-baseline freshness in `.specify/project-map/index/status.json` as the truth source. If a full refresh can be completed now, do it and use `project-map complete-refresh` as the successful-refresh finalizer; otherwise use `project-map mark-dirty` as the manual override/fallback.",
            "",
            "## Project Memory",
            "",
            "- Passive project memory lives under `.specify/memory/project-rules.md` and `.specify/memory/project-learnings.md`.",
            "- Shared project memory is always available to later work in this repository, not just when a `sp-*` workflow is active.",
            "- Prefer generated project-local Spec Kit workflows, skills, and commands over ad-hoc execution when they fit the task.",
            "",
            "## Workflow Routing",
            "",
            "- Use `sp-fast` only for trivial, low-risk local changes that do not need planning artifacts.",
            "- Use `sp-quick` for bounded tasks that need lightweight tracking but not the full `specify -> plan -> tasks -> implement` flow.",
            "- Use `sp-auto` when repository state already records the recommended next step and the user wants one continue entrypoint instead of naming the exact workflow manually.",
            "- Use `sp-specify` when scope, behavior, constraints, or acceptance criteria need explicit alignment before planning.",
            "- Use `sp-prd-scan` when an existing repository needs read-only reconstruction scan outputs before final PRD synthesis, and `sp-prd-build` once that package is ready to compile final PRD exports.",
            "- Use `sp-deep-research` when a clear requirement still lacks a proven implementation chain and needs coordinated research, optional multi-agent evidence gathering, or a disposable demo before planning.",
            "- Use `sp-debug` when diagnosis or root-cause analysis is still required before a fix path is trustworthy.",
            "- Use `sp-test-scan` for project-level testing evidence and build planning, and `sp-test-build` for leader-managed testing-system construction.",
            "",
            "## Delegated Execution Defaults",
            "",
            "- Dispatch native subagents by default for independent, bounded lanes when parallel work materially improves speed, quality, or verification confidence.",
            "- Use a validated `WorkerTaskPacket` or equivalent execution contract before subagent work begins.",
            "- Do not dispatch from raw task text alone.",
            "- Wait for each subagent's structured handoff before integrating or marking work complete; idle status is not completion evidence.",
            "- Use `sp-teams` only when Codex work needs durable team state, explicit join-point tracking, result files, or lifecycle control beyond one in-session subagent burst.",
            "",
            "## Artifact Priority",
            "",
            "- `.specify/memory/constitution.md` is the principle-level source of truth when present.",
            "- `workflow-state.md` under the active feature directory is the stage/status source of truth for resumable workflow progress.",
            "- `alignment.md` and `context.md` under the active feature directory carry locked decisions from `sp-specify` into planning.",
            "- `.specify/prd-runs/<run-id>/workflow-state.md`, `prd-scan.md`, `coverage-ledger.*`, `capability-ledger.json`, `artifact-contracts.json`, `reconstruction-checklist.json`, `master/master-pack.md`, and `exports/*.md` carry current-state PRD reconstruction artifacts from `sp-prd-scan -> sp-prd-build`; they are documentation outputs, not implicit planning inputs.",
            "- `deep-research.md`, its traceable `Planning Handoff`, and `research-spikes/` under the active feature directory carry feasibility evidence IDs, recommended approach, constraints, rejected options, and demo results from `sp-deep-research` into planning.",
            "- `plan.md` under the active feature directory is the implementation design source of truth once planning begins.",
            "- `tasks.md` under the active feature directory is the execution breakdown source of truth once task generation begins.",
            "- `.specify/testing/TEST_SCAN.md`, `.specify/testing/TEST_BUILD_PLAN.md`, `.specify/testing/TEST_BUILD_PLAN.json`, `.specify/testing/TESTING_CONTRACT.md`, `.specify/testing/TESTING_PLAYBOOK.md`, `.specify/testing/UNIT_TEST_SYSTEM_REQUEST.md`, and `.specify/testing/testing-state.md` constrain testing-system construction and brownfield testing-program routing when present.",
            "- `.specify/project-map/index/status.json` determines whether handbook/project-map coverage can be trusted as fresh and records git-baseline freshness as the truth source.",
            "",
            "## Map Maintenance",
            "",
            "- If a change alters architecture boundaries, ownership, workflow names, integration contracts, or verification entry points, refresh `PROJECT-HANDBOOK.md` and the affected `.specify/project-map/*.md` files.",
            "- If a full refresh can be completed now, run `sp-map-scan` followed by `sp-map-build`, then use `project-map complete-refresh` as the successful-refresh finalizer.",
            "- Otherwise use `project-map mark-dirty` as the manual override/fallback and explicitly route the next brownfield workflow through `sp-map-scan` followed by `sp-map-build`.",
            "- Do not treat consumed handbook/project-map context as self-maintaining; the agent changing map-level truth is responsible for keeping the atlas-style handbook system current.",
            "",
            "- Preserve content outside this managed block.",
            SPEC_KIT_BLOCK_END,
        ]
    )


def _upsert_spec_kit_managed_block(target_path: Path) -> bool:
    content = target_path.read_text(encoding="utf-8") if target_path.exists() else ""
    raw_start_count = content.count(SPEC_KIT_BLOCK_START)
    raw_end_count = content.count(SPEC_KIT_BLOCK_END)
    complete_blocks = list(
        re.finditer(
            rf"{re.escape(SPEC_KIT_BLOCK_START)}.*?{re.escape(SPEC_KIT_BLOCK_END)}",
            content,
            flags=re.S,
        )
    )

    if raw_start_count == 1 and raw_end_count == 1 and len(complete_blocks) == 1:
        match = complete_blocks[0]
        newline = _preferred_newline(match.group(0) or content)
        block = _render_spec_kit_managed_block(newline=newline)
        updated = content[: match.start()] + block + content[match.end() :]
    elif content:
        newline = _preferred_newline(content)
        block = _render_spec_kit_managed_block(newline=newline)
        if block in content:
            updated = content
        else:
            if content.endswith(newline + newline):
                separator = ""
            elif content.endswith(newline):
                separator = newline
            else:
                separator = newline + newline
            updated = content + separator + block
    else:
        updated = _render_spec_kit_managed_block(newline="\n")

    if updated == content and target_path.exists():
        return False

    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(updated.encode("utf-8"))
    return True


def _render_bootstrap_context_content(project_root: Path, context_path: Path) -> str:
    template_path = project_root / ".specify" / "templates" / "agent-file-template.md"
    if template_path.exists():
        content = template_path.read_text(encoding="utf-8")
    else:
        content = (
            "# [PROJECT NAME] Development Guidelines\n\n"
            "Auto-generated from Spec Kit Plus. Last updated: [DATE]\n\n"
            "## Active Technologies\n\n"
            "[EXTRACTED FROM ALL PLAN.MD FILES]\n\n"
            "## Project Structure\n\n"
            "```text\n"
            "[ACTUAL STRUCTURE FROM PLANS]\n"
            "```\n\n"
            "## Commands\n\n"
            "[ONLY COMMANDS FOR ACTIVE TECHNOLOGIES]\n\n"
            "## Code Style\n\n"
            "[LANGUAGE-SPECIFIC, ONLY FOR LANGUAGES IN USE]\n\n"
            "## Recent Changes\n\n"
            "[LAST 3 FEATURES AND WHAT THEY ADDED]\n"
        )

    replacements = {
        "[PROJECT NAME]": project_root.resolve().name,
        "[DATE]": date.today().isoformat(),
        "[EXTRACTED FROM ALL PLAN.MD FILES]": "- Bootstrap context only; run specify -> plan to capture active technologies",
        "[ACTUAL STRUCTURE FROM PLANS]": ".specify/\nspecs/",
        "[ONLY COMMANDS FOR ACTIVE TECHNOLOGIES]": "specify check\nspecify --help",
        "[LANGUAGE-SPECIFIC, ONLY FOR LANGUAGES IN USE]": "General: Follow existing repository conventions and refresh this file after the first plan.",
        "[LAST 3 FEATURES AND WHAT THEY ADDED]": "- Initial Spec Kit Plus scaffolding",
    }
    for token, value in replacements.items():
        content = content.replace(token, value)

    if context_path.suffix == ".mdc":
        frontmatter = (
            "---\n"
            "description: Project Development Guidelines\n"
            'globs: ["**/*"]\n'
            "alwaysApply: true\n"
            "---\n\n"
        )
        content = frontmatter + content

    return content


def _bootstrap_integration_context_file(
    project_root: Path,
    integration: Any,
    manifest: Any,
) -> Path | None:
    context_file = getattr(integration, "context_file", None)
    if not context_file:
        return None

    project_root_resolved = project_root.resolve()
    target_path = (project_root / context_file).resolve()
    try:
        rel = target_path.relative_to(project_root_resolved)
    except ValueError as exc:
        raise ValueError(
            f"context file {target_path} escapes project root {project_root_resolved}"
        ) from exc

    existed = target_path.exists()

    if not existed:
        content = _render_bootstrap_context_content(project_root, target_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(content.encode("utf-8"))

    _upsert_spec_kit_managed_block(target_path)
    if not existed:
        manifest.record_existing(rel)
    return target_path


def _render_quick_task_table(tasks: list[dict[str, Any]]) -> None:
    table = Table(title="Quick Tasks")
    table.add_column("ID", style="cyan")
    table.add_column("Title")
    table.add_column("Status", style="yellow")
    table.add_column("Next Action")
    for task in tasks:
        table.add_row(
            str(task.get("id", "")),
            str(task.get("title", "")),
            str(task.get("status", "")),
            str(task.get("next_action", "")),
        )
    console.print(table)


def _normalize_prd_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    mode = str(payload.get("mode") or "")
    surfaces = payload.get("surfaces") if isinstance(payload.get("surfaces"), dict) else {}
    if mode in {"init-scan", "status", "status-scan", "init"}:
        relevant_surfaces = {
            "workflow_state",
            "prd_scan",
            "coverage_ledger",
            "coverage_ledger_json",
            "capability_ledger_json",
            "artifact_contracts_json",
            "reconstruction_checklist_json",
            "scan_packets",
            "evidence",
            "worker_results",
        }
    elif mode == "status-build":
        relevant_surfaces = {
            "workflow_state",
            "prd_scan",
            "coverage_ledger_json",
            "capability_ledger_json",
            "artifact_contracts_json",
            "reconstruction_checklist_json",
            "scan_packets",
            "evidence",
            "worker_results",
            "master_pack",
            "prd_export",
            "reconstruction_appendix",
            "data_model",
            "integration_contracts",
            "runtime_behaviors",
        }
    else:
        relevant_surfaces = set(surfaces)

    relevant_present = {name: bool(present) for name, present in surfaces.items() if name in relevant_surfaces}
    normalized["complete"] = bool(relevant_present) and all(relevant_present.values())
    normalized["missing"] = sorted(name for name, present in relevant_present.items() if not present)
    return normalized


def _render_prd_payload(payload: dict[str, Any], *, json_output: bool = False) -> None:
    normalized = _normalize_prd_payload(payload)
    if json_output:
        print(json.dumps(normalized, ensure_ascii=False))
        return

    mode = str(normalized.get("mode") or "")
    if mode in {"status-build"}:
        title = "PRD Build Status"
    elif mode in {"status", "status-scan"}:
        title = "PRD Scan Status"
    elif mode == "init-scan":
        title = "PRD Scan Initialized"
    else:
        title = "PRD Run Status"

    rows = [
        ("Workspace", str(normalized.get("workspace", ""))),
        ("Path", str(normalized.get("workspace_path", ""))),
        ("Complete", "yes" if normalized.get("complete") else "no"),
    ]
    missing = normalized.get("missing")
    if isinstance(missing, list) and missing:
        rows.append(("Missing", ", ".join(str(item) for item in missing)))
    console.print(_cli_panel(_labeled_grid(rows), title=title, border_style="cyan"))


@app.command("prd-scan")
def prd_scan_command(
    run_slug: str = typer.Argument(
        "prd-run",
        help="Run slug to initialize, or run ID when using --status",
    ),
    status: bool = typer.Option(False, "--status", help="Show an existing PRD scan run surface status"),
    json_output: bool = typer.Option(False, "--json", help="Print the helper payload as JSON"),
):
    """Initialize or inspect a reconstruction-grade PRD scan run."""
    _require_spec_kit_plus_project(Path.cwd())
    payload = _run_prd_helper("status-scan" if status else "init-scan", run_slug=run_slug)
    _render_prd_payload(payload, json_output=json_output)


@app.command("prd-build")
def prd_build_command(
    run_slug: str = typer.Argument(
        ...,
        help="Run ID for an existing PRD scan/build workspace",
    ),
    json_output: bool = typer.Option(False, "--json", help="Print the helper payload as JSON"),
):
    """Inspect a validated PRD build workspace before or during final export compilation."""
    _require_spec_kit_plus_project(Path.cwd())
    payload = _run_prd_helper("status-build", run_slug=run_slug)
    _render_prd_payload(payload, json_output=json_output)


@app.command("prd")
def prd_command(
    run_slug: str = typer.Argument(
        "prd-run",
        help="Compatibility entrypoint: run slug to initialize, or run ID when using --status",
    ),
    status: bool = typer.Option(False, "--status", help="Show the compatibility PRD scan surface status"),
    json_output: bool = typer.Option(False, "--json", help="Print the helper payload as JSON"),
):
    """Deprecated compatibility entrypoint for reverse-PRD work; prefer `prd-scan` then `prd-build`."""
    _require_spec_kit_plus_project(Path.cwd())
    payload = _run_prd_helper("status" if status else "init", run_slug=run_slug)
    _render_prd_payload(payload, json_output=json_output)


@quick_app.command("list")
def quick_list(
    all_tasks: bool = typer.Option(False, "--all", help="Include closed and archived quick tasks"),
):
    """List tracked quick tasks."""
    _require_spec_kit_plus_project(Path.cwd())
    payload = _run_quick_helper("list", include_all=all_tasks)
    tasks = payload.get("tasks", [])
    if not tasks:
        console.print("No quick tasks found.")
        return
    _render_quick_task_table(tasks)


@quick_app.command("status")
def quick_status(
    quick_id: str = typer.Argument(..., help="Quick task ID or workspace directory name"),
):
    """Show STATUS.md-backed details for a quick task."""
    _require_spec_kit_plus_project(Path.cwd())
    payload = _run_quick_helper("status", quick_id=quick_id)
    task = payload.get("task")
    if not isinstance(task, dict):
        console.print("[red]Error:[/red] Quick task not found")
        raise typer.Exit(1)

    details = _labeled_grid(
        [
            ("ID", str(task.get("id", ""))),
            ("Title", str(task.get("title", ""))),
            ("Status", str(task.get("status", ""))),
            ("Current Focus", str(task.get("current_focus", ""))),
            ("Next Action", str(task.get("next_action", ""))),
            ("Workspace", str(task.get("workspace_path", ""))),
        ]
    )
    console.print(_cli_panel(details, title="Quick Status", border_style="cyan"))


@quick_app.command("resume")
def quick_resume(
    quick_id: str = typer.Argument(..., help="Quick task ID or workspace directory name"),
):
    """Print the current next action for a quick task."""
    _require_spec_kit_plus_project(Path.cwd())
    payload = _run_quick_helper("status", quick_id=quick_id)
    task = payload.get("task")
    if not isinstance(task, dict):
        console.print("[red]Error:[/red] Quick task not found")
        raise typer.Exit(1)

    console.print(f"Resume quick task {task.get('id')}: {task.get('next_action')}")
    console.print(f"Workspace: {task.get('workspace_path')}")


@quick_app.command("close")
def quick_close(
    quick_id: str = typer.Argument(..., help="Quick task ID or workspace directory name"),
    status: str = typer.Option(
        ...,
        "--status",
        help="Terminal quick task status (resolved or blocked)",
    ),
):
    """Mark a quick task as closed in STATUS.md."""
    status_value = status.strip().lower()
    if status_value not in {"resolved", "blocked"}:
        console.print("[red]Error:[/red] --status must be 'resolved' or 'blocked'")
        raise typer.Exit(1)

    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    payload = _run_quick_helper("close", quick_id=quick_id, status=status_value)
    task = payload.get("task", {})
    workspace_path = str(task.get("workspace_path", "")).strip()
    if workspace_path:
        auto_payload = capture_auto_learning(
            project_root,
            command_name="quick",
            workspace=Path(workspace_path),
        )
        if auto_payload["status"] == "captured":
            console.print(f"Auto-captured {len(auto_payload['captured'])} quick-task learning candidate(s).")
    console.print(f"Closed quick task {task.get('id')} with status {task.get('status')}.")


@quick_app.command("archive")
def quick_archive(
    quick_id: str = typer.Argument(..., help="Quick task ID or workspace directory name"),
):
    """Archive a closed quick task workspace."""
    _require_spec_kit_plus_project(Path.cwd())
    payload = _run_quick_helper("archive", quick_id=quick_id)
    task = payload.get("task", {})
    console.print(f"Archived quick task {task.get('id')} to {task.get('workspace_path')}.")


@implement_app.command("closeout")
def implement_closeout(
    feature_dir: str = typer.Option(..., "--feature-dir", help="Feature directory containing workflow-state.md and implement-tracker.md"),
    output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
):
    """Validate implementation closeout state and auto-capture learnings."""
    from .hooks.engine import run_quality_hook

    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    resolved_feature_dir = Path(feature_dir)
    if not resolved_feature_dir.is_absolute():
        resolved_feature_dir = (project_root / resolved_feature_dir).resolve()

    hook_result = run_quality_hook(
        project_root,
        "workflow.session_state.validate",
        {"command_name": "implement", "feature_dir": str(resolved_feature_dir)},
    )
    if hook_result.status == "blocked":
        payload = {"status": "blocked", "hook_result": hook_result.to_dict(), "feature_dir": str(resolved_feature_dir)}
        if output_format.lower() == "json":
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            console.print("[red]Error:[/red] Implement closeout blocked by invalid session state.")
            for error in hook_result.errors:
                console.print(f"- {error}")
        raise typer.Exit(1)

    auto_payload = capture_auto_learning(
        project_root,
        command_name="implement",
        feature_dir=resolved_feature_dir,
    )
    payload = {
        "status": "ok",
        "feature_dir": str(resolved_feature_dir),
        "hook_result": hook_result.to_dict(),
        "auto_capture": auto_payload,
    }
    if output_format.lower() == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    rows = [
        ("Feature Dir", str(resolved_feature_dir)),
        ("Session State", hook_result.status),
        ("Auto-Capture", auto_payload["status"]),
        ("Captured", str(len(auto_payload.get("captured", [])))),
    ]
    if auto_payload.get("reason"):
        rows.append(("Reason", str(auto_payload["reason"])))
    console.print(_cli_panel(_labeled_grid(rows), title="Implement Closeout", border_style="cyan"))


@testing_app.command("inventory")
def testing_inventory_command(
    output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
):
    """Scan the current repository and summarize test-system modules and frameworks."""
    from .testing_inventory import build_testing_inventory

    project_root = Path.cwd()
    payload = build_testing_inventory(project_root)
    if output_format.lower() == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    rows = [
        ("Project Root", payload["project_root"]),
        ("Module Count", str(payload["module_count"])),
        ("Languages", ", ".join(payload["languages"]) if payload["languages"] else "none"),
    ]
    console.print(_cli_panel(_labeled_grid(rows), title="Testing Inventory", border_style="cyan"))

    table = Table(title="Modules")
    table.add_column("Module", style="cyan")
    table.add_column("Language")
    table.add_column("Kind")
    table.add_column("Framework")
    table.add_column("State")
    table.add_column("Skill")
    for module in payload["modules"]:
        table.add_row(
            str(module.get("module_root", "")),
            str(module.get("language", "")),
            str(module.get("module_kind", "")),
            str(module.get("framework", "")),
            str(module.get("state", "")),
            str(module.get("selected_skill", "") or ""),
        )
    console.print(table)


@project_map_app.command("check")
def project_map_check(
    output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
):
    """Inspect git-baseline project-map freshness for the working tree."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    result = inspect_project_map_freshness(project_root)
    if output_format.lower() == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    _render_project_map_freshness(result)


@project_map_app.command("mark-dirty")
def project_map_mark_dirty(
    reason: str = typer.Argument(..., help="Why the current work needs a manual dirty override/fallback"),
    output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
):
    """Mark the project map dirty as a manual override/fallback when refresh cannot complete now."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    mark_project_map_dirty(project_root, reason)
    result = inspect_project_map_freshness(project_root)
    if output_format.lower() == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    _render_project_map_freshness(result)


@project_map_app.command("clear-dirty")
def project_map_clear_dirty(
    output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
):
    """Clear the dirty bit without changing the recorded map baseline."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    clear_project_map_dirty(project_root)
    result = inspect_project_map_freshness(project_root)
    if output_format.lower() == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    _render_project_map_freshness(result)


@project_map_app.command("record-refresh")
def project_map_record_refresh(
    reason: str = typer.Option("manual", "--reason", help="Why the map was refreshed"),
    output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
):
    """Low-level/manual recovery path to record a fresh project-map baseline at the current HEAD."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    _ensure_project_map_artifacts_exist(project_root)
    mark_project_map_refreshed(
        project_root,
        head_commit=git_head_commit(project_root),
        branch=git_branch_name(project_root),
        reason=reason,
    )
    result = inspect_project_map_freshness(project_root)
    if output_format.lower() == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    _render_project_map_freshness(result)


@project_map_app.command("complete-refresh")
def project_map_complete_refresh(
    output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
):
    """Finalize a successful full map refresh by recording a fresh git baseline."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    _ensure_project_map_artifacts_exist(project_root)
    complete_project_map_refresh(project_root)
    result = inspect_project_map_freshness(project_root)
    if output_format.lower() == "json":
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    _render_project_map_freshness(result)


@project_map_app.command("refresh-topics")
def project_map_refresh_topics_command(
    topics: list[str] = typer.Argument(..., help="One or more canonical topic files to record as refreshed"),
    reason: str = typer.Option("topic-refresh", "--reason", help="Why these topics were refreshed"),
    output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
):
    """Record a partial project-map refresh for specific topic files."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    unknown = [topic for topic in topics if topic not in TOPIC_FILES]
    if unknown:
        console.print(f"[red]Error:[/red] Unknown topic(s): {', '.join(unknown)}")
        console.print(f"Valid topics: {', '.join(TOPIC_FILES)}")
        raise typer.Exit(1)
    _ensure_project_map_artifacts_exist(project_root)
    status = refresh_project_map_topics(
        project_root,
        topics=topics,
        reason=reason,
    )
    payload = status.to_dict()
    payload["status_path"] = str(project_map_status_path(project_root))
    if output_format.lower() == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    rows = [
        ("Refresh Scope", f"[cyan]{payload['last_refresh_scope']}[/cyan]"),
        ("Reason", f"[dim]{payload['last_refresh_reason']}[/dim]"),
        ("Basis", f"[dim]{payload['last_refresh_basis'] or '-'}[/dim]"),
        ("Topics", f"[dim]{', '.join(payload['last_refresh_topics']) or '-'}[/dim]"),
    ]
    console.print(_cli_panel(_labeled_grid(rows), title="Project Map Partial Refresh", border_style="cyan"))


@project_map_app.command("status")
def project_map_status_command(
    output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
):
    """Read the stored project-map status file without recomputing git freshness."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    status = read_project_map_status(project_root).to_dict()
    status["status_path"] = str(project_map_status_path(project_root))
    if output_format.lower() == "json":
        print(json.dumps(status, ensure_ascii=False, indent=2))
        return
    rows = [
        ("Freshness", f"[cyan]{status['freshness']}[/cyan]"),
        ("Dirty", "[yellow]true[/yellow]" if status["dirty"] else "false"),
        ("Status File", f"[dim]{status['status_path']}[/dim]"),
        ("Last Commit", f"[dim]{status['last_mapped_commit'] or '-'}[/dim]"),
        ("Last Branch", f"[dim]{status['last_mapped_branch'] or '-'}[/dim]"),
        ("Last Refresh", f"[dim]{status['last_mapped_at'] or '-'}[/dim]"),
        ("Refresh Scope", f"[dim]{status.get('last_refresh_scope') or '-'}[/dim]"),
        ("Refresh Basis", f"[dim]{status.get('last_refresh_basis') or '-'}[/dim]"),
    ]
    console.print(_cli_panel(_labeled_grid(rows), title="Project Map Status", border_style="cyan"))
    if status.get("last_refresh_topics"):
        console.print("[bold]Last Refresh Topics[/bold]")
        for topic in status["last_refresh_topics"]:
            console.print(f"- {topic}")
    if status["dirty_reasons"]:
        console.print("[bold]Dirty Reasons[/bold]")
        for reason in status["dirty_reasons"]:
            console.print(f"- {reason}")


@learning_app.command("ensure")
def learning_ensure_command(
    output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    include_runtime: bool = typer.Option(True, "--runtime/--no-runtime", help="Also create runtime learning files under .planning/learnings/"),
):
    """Ensure passive project learning files exist."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    paths = ensure_learning_files(project_root, include_runtime=include_runtime)
    payload = learning_status_payload(project_root, include_runtime=include_runtime)
    payload["paths"] = paths.to_dict()
    if output_format.lower() == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    rows = [
        ("Project Rules", f"[dim]{payload['paths']['project_rules']}[/dim]"),
        ("Project Learnings", f"[dim]{payload['paths']['project_learnings']}[/dim]"),
    ]
    if include_runtime:
        rows.extend(
            [
                ("Candidates", f"[dim]{payload['paths']['candidates']}[/dim]"),
                ("Review", f"[dim]{payload['paths']['review']}[/dim]"),
            ]
        )
    console.print(_cli_panel(_labeled_grid(rows), title="Project Learning Files", border_style="cyan"))


@learning_app.command("status")
def learning_status_command(
    output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
):
    """Inspect passive project learning file state without mutating it."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    payload = learning_status_payload(project_root)
    if output_format.lower() == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    rows = [
        ("Project Rules", "present" if payload["exists"]["project_rules"] else "missing"),
        ("Project Learnings", "present" if payload["exists"]["project_learnings"] else "missing"),
        ("Candidates", "present" if payload["exists"]["candidates"] else "missing"),
        ("Review", "present" if payload["exists"]["review"] else "missing"),
    ]
    console.print(_cli_panel(_labeled_grid(rows), title="Project Learning Status", border_style="cyan"))


@learning_app.command("start")
def learning_start_command(
    command_name: str = typer.Option(..., "--command", help="Workflow command name, for example specify or sp-implement"),
    output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
):
    """Prepare passive learning context for a workflow start."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    payload = start_learning_session(project_root, command_name=command_name)
    if output_format.lower() == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    rows = [
        ("Command", payload["command"]),
        ("Relevant Rules", str(len(payload["relevant_rules"]))),
        ("Relevant Learnings", str(len(payload["relevant_learnings"]))),
        ("Relevant Candidates", str(len(payload["relevant_candidates"]))),
        ("Preflight Warnings", str(len(payload["preflight_warnings"]))),
        ("Auto Promoted", str(len(payload["auto_promoted"]))),
        ("Promotable", str(len(payload["promotable_candidates"]))),
        ("Needs Confirmation", str(len(payload["confirmation_candidates"]))),
    ]
    console.print(_cli_panel(_labeled_grid(rows), title="Project Learning Start", border_style="cyan"))


@learning_app.command("capture")
def learning_capture_command(
    command_name: str = typer.Option(..., "--command", help="Workflow command name, for example specify or sp-implement"),
    learning_type: str = typer.Option(..., "--type", help="Learning type"),
    summary: str = typer.Option(..., "--summary", help="One-line learning summary"),
    evidence: str = typer.Option(..., "--evidence", help="Supporting evidence or context"),
    recurrence_key: str | None = typer.Option(None, "--recurrence-key", help="Stable deduplication key"),
    signal_strength: str = typer.Option("medium", "--signal", help="Signal strength: low, medium, or high"),
    applies_to: list[str] | None = typer.Option(None, "--applies-to", help="Commands this learning should influence"),
    default_scope: str | None = typer.Option(None, "--scope", help="Default sharing scope label"),
    confirm: bool = typer.Option(False, "--confirm", help="Promote directly into project learnings instead of leaving as a candidate"),
    pain_score: int | None = typer.Option(None, "--pain-score", help="Workflow friction score that triggered capture"),
    false_starts: list[str] | None = typer.Option(None, "--false-start", help="Misleading first attempts or false leads"),
    rejected_paths: list[str] | None = typer.Option(None, "--rejected-path", help="Rejected diagnosis or implementation paths"),
    decisive_signal: str | None = typer.Option(None, "--decisive-signal", help="Evidence that made the learning clear"),
    root_cause_family: str | None = typer.Option(None, "--root-cause-family", help="Stable root-cause family label"),
    injection_targets: list[str] | None = typer.Option(None, "--injection-target", help="Workflow, document, or rule surface that should receive the learning"),
    promotion_hint: str | None = typer.Option(None, "--promotion-hint", help="When or how this candidate should be promoted"),
    output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
):
    """Capture a passive learning observation for the current workflow."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    payload = capture_learning(
        project_root,
        command_name=command_name,
        learning_type=learning_type,
        summary=summary,
        evidence=evidence,
        recurrence_key=recurrence_key,
        signal_strength=signal_strength,
        applies_to=applies_to,
        default_scope=default_scope,
        confirm=confirm,
        pain_score=pain_score,
        false_starts=false_starts,
        rejected_paths=rejected_paths,
        decisive_signal=decisive_signal,
        root_cause_family=root_cause_family,
        injection_targets=injection_targets,
        promotion_hint=promotion_hint,
    )
    if output_format.lower() == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    entry = payload["entry"]
    rows = [
        ("Status", payload["status"]),
        ("Summary", entry["summary"]),
        ("Recurrence Key", entry["recurrence_key"]),
        ("Signal", entry["signal_strength"]),
        ("Needs Confirmation", "true" if payload["needs_confirmation"] else "false"),
    ]
    console.print(_cli_panel(_labeled_grid(rows), title="Project Learning Capture", border_style="cyan"))


def _run_learning_capture_auto(
    *,
    command_name: str,
    feature_dir: str | None,
    workspace: str | None,
    session_file: str | None,
    output_format: str,
) -> None:
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    payload = capture_auto_learning(
        project_root,
        command_name=command_name,
        feature_dir=Path(feature_dir) if feature_dir else None,
        workspace=Path(workspace) if workspace else None,
        session_file=Path(session_file) if session_file else None,
    )
    if output_format.lower() == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    rows = [
        ("Status", payload["status"]),
        ("Command", payload["command"]),
        ("Captured", str(len(payload.get("captured", [])))),
        ("Source", str(payload.get("source_path", ""))),
    ]
    if payload.get("reason"):
        rows.append(("Reason", str(payload["reason"])))
    console.print(_cli_panel(_labeled_grid(rows), title="Project Learning Auto-Capture", border_style="cyan"))


def learning_capture_auto_cli_command(
    command_name: str = typer.Option(..., "--command", help="Workflow command name, for example plan, test, implement, quick, or debug"),
    feature_dir: str | None = typer.Option(None, "--feature-dir", help="Feature directory containing workflow-state.md and/or implement-tracker.md"),
    workspace: str | None = typer.Option(None, "--workspace", help="Quick-task workspace containing STATUS.md"),
    session_file: str | None = typer.Option(None, "--session-file", help="Debug session markdown file"),
    output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
):
    """Auto-capture learning candidates from workflow state files."""
    _run_learning_capture_auto(
        command_name=command_name,
        feature_dir=feature_dir,
        workspace=workspace,
        session_file=session_file,
        output_format=output_format,
    )


learning_app.command(name="capture-auto")(learning_capture_auto_cli_command)


@learning_app.command("promote")
def learning_promote_command(
    recurrence_key: str = typer.Option(..., "--recurrence-key", help="Stable learning recurrence key"),
    target: str = typer.Option(..., "--target", help="Promotion target: learning or rule"),
    output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
):
    """Promote a passive learning into shared project memory."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    payload = promote_learning(
        project_root,
        recurrence_key=recurrence_key,
        target=target,
    )
    if output_format.lower() == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    entry = payload["entry"]
    rows = [
        ("Status", payload["status"]),
        ("Summary", entry["summary"]),
        ("Recurrence Key", entry["recurrence_key"]),
        ("Applies To", ", ".join(entry["applies_to"])),
    ]
    console.print(_cli_panel(_labeled_grid(rows), title="Project Learning Promotion", border_style="cyan"))


@learning_app.command("aggregate")
def learning_aggregate_command(
    command_name: str | None = typer.Option(None, "--command", help="Optional workflow command filter, for example plan or sp-implement"),
    output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
    write_report: bool = typer.Option(False, "--write-report", help="Also write a markdown report under .planning/learnings/reports/"),
    stale_after_days: int = typer.Option(90, "--stale-after-days", help="Mark inactive patterns as stale after this many days"),
):
    """Aggregate passive project learnings into a promotion-oriented report."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    payload = aggregate_learning_state(
        project_root,
        command_name=command_name,
        stale_after_days=stale_after_days,
    )
    if write_report:
        payload["report_path"] = str(write_learning_aggregate_report(project_root, payload))
    if output_format.lower() == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return

    rows = [
        ("Patterns", str(payload["counts"]["patterns"])),
        ("Promotion Ready", str(payload["counts"]["promotion_ready"])),
        ("Approaching", str(payload["counts"]["approaching_threshold"])),
        ("Stale", str(payload["counts"]["stale"])),
    ]
    if "report_path" in payload:
        rows.append(("Report", f"[dim]{payload['report_path']}[/dim]"))
    console.print(_cli_panel(_labeled_grid(rows), title="Project Learning Aggregate", border_style="cyan"))


@eval_app.command("create")
def eval_create_command(
    recurrence_key: str = typer.Option(..., "--recurrence-key", help="Stable recurrence key or eval subject id"),
    summary: str | None = typer.Option(None, "--summary", help="One-line eval summary"),
    verification_method: str | None = typer.Option(None, "--verification-method", help="Verification method: file-check, rule-check, grep-check, or command-check"),
    target: str | None = typer.Option(None, "--target", help="Target file path or glob"),
    contains: str | None = typer.Option(None, "--contains", help="String that must exist for rule-check"),
    pattern: str | None = typer.Option(None, "--pattern", help="Regex pattern for grep-check"),
    command: str | None = typer.Option(None, "--command", help="Command for command-check"),
    expect: str | None = typer.Option(None, "--expect", help="Expected result such as found, exists, pass, or fail"),
    recovery_action: str = typer.Option("", "--recovery-action", help="What to do if the eval fails"),
    output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
):
    """Create a durable eval case under .specify/evals/."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    payload = create_eval_case(
        project_root,
        recurrence_key=recurrence_key,
        summary=summary,
        verification_method=verification_method,
        target=target,
        contains=contains,
        pattern=pattern,
        command=command,
        expect=expect,
        recovery_action=recovery_action,
    )
    response = {
        "case": payload["case"].to_payload(),
        "case_path": str(payload["case_path"]),
        "paths": payload["paths"].to_dict(),
    }
    if output_format.lower() == "json":
        print(json.dumps(response, ensure_ascii=False, indent=2))
        return
    rows = [
        ("Eval Id", response["case"]["id"]),
        ("Recurrence Key", response["case"]["recurrence_key"]),
        ("Method", response["case"]["verification_method"]),
        ("Case File", f"[dim]{response['case_path']}[/dim]"),
    ]
    console.print(_cli_panel(_labeled_grid(rows), title="Eval Created", border_style="cyan"))


@eval_app.command("status")
def eval_status_command(
    output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
):
    """Inspect the durable eval store without mutating it."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    payload = eval_status_payload(project_root)
    if output_format.lower() == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    rows = [
        ("Cases", str(payload["counts"]["cases"])),
        ("Passed", str(payload["counts"]["passed"])),
        ("Failed", str(payload["counts"]["failed"])),
        ("Skipped", str(payload["counts"]["skipped"])),
        ("Pending", str(payload["counts"]["pending"])),
    ]
    console.print(_cli_panel(_labeled_grid(rows), title="Eval Status", border_style="cyan"))


@eval_app.command("run")
def eval_run_command(
    recurrence_key: str | None = typer.Option(None, "--recurrence-key", help="Optional recurrence key filter"),
    output_format: str = typer.Option("text", "--format", help="Output format: text or json"),
):
    """Run durable eval cases and update their last_result state."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    payload = run_eval_suite(project_root, recurrence_key=recurrence_key)
    if output_format.lower() == "json":
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    rows = [
        ("Total", str(payload["counts"]["total"])),
        ("Passed", str(payload["counts"]["passed"])),
        ("Failed", str(payload["counts"]["failed"])),
        ("Skipped", str(payload["counts"]["skipped"])),
    ]
    console.print(_cli_panel(_labeled_grid(rows), title="Eval Run", border_style="cyan"))

def check_tool(tool: str, tracker: StepTracker = None) -> bool:
    """Check if a tool is installed. Optionally update tracker.

    Args:
        tool: Name of the tool to check
        tracker: Optional StepTracker to update with results

    Returns:
        True if tool is found, False otherwise
    """
    # Special handling for Claude CLI local installs
    # See: https://github.com/github/spec-kit/issues/123
    # See: https://github.com/github/spec-kit/issues/550
    # Claude Code can be installed in two local paths:
    #   1. ~/.claude/local/claude          (after `claude migrate-installer`)
    #   2. ~/.claude/local/node_modules/.bin/claude  (npm-local install, e.g. via nvm)
    # Neither path may be on the system PATH, so we check them explicitly.
    if tool == "claude":
        if CLAUDE_LOCAL_PATH.is_file() or CLAUDE_NPM_LOCAL_PATH.is_file():
            if tracker:
                tracker.complete(tool, "available")
            return True

    if tool == "kiro-cli":
        # Kiro currently supports both executable names. Prefer kiro-cli and
        # accept kiro as a compatibility fallback.
        found = shutil.which("kiro-cli") is not None or shutil.which("kiro") is not None
    else:
        found = shutil.which(tool) is not None

    if tracker:
        if found:
            tracker.complete(tool, "available")
        else:
            tracker.error(tool, "not found")

    return found

def is_git_repo(path: Path = None) -> bool:
    """Check if the specified path is inside a git repository."""
    if path is None:
        path = Path.cwd()

    if not path.is_dir():
        return False

    try:
        # Use git command to check if inside a work tree
        subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            check=True,
            capture_output=True,
            cwd=path,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def init_git_repo(project_path: Path, quiet: bool = False) -> Tuple[bool, Optional[str]]:
    """Initialize a git repository in the specified path.

    Args:
        project_path: Path to initialize git repository in
        quiet: if True suppress console output (tracker handles status)

    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    try:
        original_cwd = Path.cwd()
        os.chdir(project_path)
        if not quiet:
            console.print("[cyan]Initializing git repository...[/cyan]")
        subprocess.run(
            ["git", "init"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        subprocess.run(
            ["git", "add", "."],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit from Specify template"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if not quiet:
            console.print("[green]✓[/green] Git repository initialized")
        return True, None

    except subprocess.CalledProcessError as e:
        error_msg = f"Command: {' '.join(e.cmd)}\nExit code: {e.returncode}"
        if e.stderr:
            error_msg += f"\nError: {e.stderr.strip()}"
        elif e.stdout:
            error_msg += f"\nOutput: {e.stdout.strip()}"

        if not quiet:
            console.print(f"[red]Error initializing git repository:[/red] {e}")
        return False, error_msg
    finally:
        os.chdir(original_cwd)

def handle_vscode_settings(sub_item, dest_file, rel_path, verbose=False, tracker=None) -> None:
    """Handle merging or copying of .vscode/settings.json files.

    Note: when merge produces changes, rewritten output is normalized JSON and
    existing JSONC comments/trailing commas are not preserved.
    """
    def log(message, color="green"):
        if verbose and not tracker:
            console.print(f"[{color}]{message}[/] {rel_path}")

    def atomic_write_json(target_file: Path, payload: dict[str, Any]) -> None:
        """Atomically write JSON while preserving existing mode bits when possible."""
        temp_path: Optional[Path] = None
        try:
            with tempfile.NamedTemporaryFile(
                mode='w',
                encoding='utf-8',
                dir=target_file.parent,
                prefix=f"{target_file.name}.",
                suffix=".tmp",
                delete=False,
            ) as f:
                temp_path = Path(f.name)
                json.dump(payload, f, indent=4)
                f.write('\n')

            if target_file.exists():
                try:
                    existing_stat = target_file.stat()
                    os.chmod(temp_path, stat.S_IMODE(existing_stat.st_mode))
                    if hasattr(os, "chown"):
                        try:
                            os.chown(temp_path, existing_stat.st_uid, existing_stat.st_gid)
                        except PermissionError:
                            # Best-effort owner/group preservation without requiring elevated privileges.
                            pass
                except OSError:
                    # Best-effort metadata preservation; data safety is prioritized.
                    pass

            os.replace(temp_path, target_file)
        except Exception:
            if temp_path and temp_path.exists():
                temp_path.unlink()
            raise

    try:
        with open(sub_item, 'r', encoding='utf-8') as f:
            # json5 natively supports comments and trailing commas (JSONC)
            new_settings = json5.load(f)

        if dest_file.exists():
            merged = merge_json_files(dest_file, new_settings, verbose=verbose and not tracker)
            if merged is not None:
                atomic_write_json(dest_file, merged)
                log("Merged:", "green")
                log("Note: comments/trailing commas are normalized when rewritten", "yellow")
            else:
                log("Skipped merge (preserved existing settings)", "yellow")
        else:
            shutil.copy2(sub_item, dest_file)
            log("Copied (no existing settings.json):", "blue")

    except Exception as e:
        log(f"Warning: Could not merge settings: {e}", "yellow")
        if not dest_file.exists():
            shutil.copy2(sub_item, dest_file)


def merge_json_files(existing_path: Path, new_content: Any, verbose: bool = False) -> Optional[dict[str, Any]]:
    """Merge new JSON content into existing JSON file.

    Performs a polite deep merge where:
    - New keys are added
    - Existing keys are preserved (not overwritten) unless both values are dictionaries
    - Nested dictionaries are merged recursively only when both sides are dictionaries
    - Lists and other values are preserved from base if they exist

    Args:
        existing_path: Path to existing JSON file
        new_content: New JSON content to merge in
        verbose: Whether to print merge details

    Returns:
        Merged JSON content as dict, or None if the existing file should be left untouched.
    """
    # Load existing content first to have a safe fallback
    existing_content = None
    exists = existing_path.exists()

    if exists:
        try:
            with open(existing_path, 'r', encoding='utf-8') as f:
                # Handle comments (JSONC) natively with json5
                # Note: json5 handles BOM automatically
                existing_content = json5.load(f)
        except FileNotFoundError:
            # Handle race condition where file is deleted after exists() check
            exists = False
        except Exception as e:
            if verbose:
                console.print(f"[yellow]Warning: Could not read or parse existing JSON in {existing_path.name} ({e}).[/yellow]")
            # Skip merge to preserve existing file if unparseable or inaccessible (e.g. PermissionError)
            return None

    # Validate template content
    if not isinstance(new_content, dict):
        if verbose:
            console.print(f"[yellow]Warning: Template content for {existing_path.name} is not a dictionary. Preserving existing settings.[/yellow]")
        return None

    if not exists:
        return new_content

    # If existing content parsed but is not a dict, skip merge to avoid data loss
    if not isinstance(existing_content, dict):
        if verbose:
            console.print(f"[yellow]Warning: Existing JSON in {existing_path.name} is not an object. Skipping merge to avoid data loss.[/yellow]")
        return None

    def deep_merge_polite(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
        """Recursively merge update dict into base dict, preserving base values."""
        result = base.copy()
        for key, value in update.items():
            if key not in result:
                # Add new key
                result[key] = value
            elif isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                result[key] = deep_merge_polite(result[key], value)
            else:
                # Key already exists and values are not both dicts; preserve existing value.
                # This ensures user settings aren't overwritten by template defaults.
                pass
        return result

    merged = deep_merge_polite(existing_content, new_content)

    # Detect if anything actually changed. If not, return None so the caller
    # can skip rewriting the file (preserving user's comments/formatting).
    if merged == existing_content:
        return None

    if verbose:
        console.print(f"[cyan]Merged JSON file:[/cyan] {existing_path.name}")

    return merged

def _locate_core_pack() -> Path | None:
    """Return the filesystem path to the bundled core_pack directory, or None.

    Only present in wheel installs: hatchling's force-include copies
    templates/, scripts/ etc. into specify_cli/core_pack/ at build time.

    Source-checkout and editable installs do NOT have this directory.
    Callers that need to work in both environments must check the repo-root
    trees (templates/, scripts/) as a fallback when this returns None.
    """
    # Wheel install: core_pack is a sibling directory of this file
    candidate = Path(__file__).parent / "core_pack"
    if candidate.is_dir():
        return candidate
    return None


def _bundled_extension_roots() -> list[Path]:
    """Return candidate directories that may contain bundled extensions."""
    roots: list[Path] = []
    seen: set[Path] = set()

    core = _locate_core_pack()
    if core:
        bundled_root = (core / "extensions").resolve()
        if bundled_root.is_dir() and bundled_root not in seen:
            roots.append(bundled_root)
            seen.add(bundled_root)

    repo_root = _project_root_from_source()
    source_root = (repo_root / "extensions").resolve()
    if source_root.is_dir() and source_root not in seen:
        roots.append(source_root)
        seen.add(source_root)

    return roots


def _locate_bundled_extension_source(extension: str) -> Path | None:
    """Return a bundled extension source directory by ID or display name."""
    normalized = extension.strip()
    if not normalized:
        return None

    from .extensions import ExtensionManifest, ValidationError

    for root in _bundled_extension_roots():
        direct = root / normalized
        if (direct / "extension.yml").is_file():
            return direct

    normalized_folded = normalized.casefold()
    for root in _bundled_extension_roots():
        for child in root.iterdir():
            if not child.is_dir():
                continue
            manifest_path = child / "extension.yml"
            if not manifest_path.is_file():
                continue
            try:
                manifest = ExtensionManifest(manifest_path)
            except ValidationError:
                continue
            if manifest.id == normalized or manifest.name.casefold() == normalized_folded:
                return child
    return None


def _install_bundled_extension(
    project_root: Path,
    extension: str,
    *,
    priority: int = 10,
    skip_if_installed: bool = False,
):
    """Install a bundled extension into the current project when available."""
    from .extensions import ExtensionManager, ExtensionManifest

    source_dir = _locate_bundled_extension_source(extension)
    if source_dir is None:
        return None

    manager = ExtensionManager(project_root)
    manifest = ExtensionManifest(source_dir / "extension.yml")
    if skip_if_installed and manager.registry.is_installed(manifest.id):
        return manifest

    installed_manifest = manager.install_from_directory(
        source_dir,
        get_speckit_version(),
        priority=priority,
    )
    manager.registry.update(installed_manifest.id, {"source": "bundled"})
    return installed_manifest


WINDOWS_PSMUX_WINGET_ID = "marlocarlo.psmux"
WINDOWS_PSMUX_INSTALL_CMD = [
    "winget",
    "install",
    "--id",
    WINDOWS_PSMUX_WINGET_ID,
    "--exact",
    "--accept-package-agreements",
    "--accept-source-agreements",
]
CODEX_TEAMS_INITIAL_COMMIT_MESSAGE = "chore: bootstrap codex teams workspace"


def _install_psmux_for_codex_teams() -> tuple[bool, str]:
    """Attempt to install psmux via winget on native Windows."""
    if detect_team_runtime_backend().get("name") == "psmux":
        return True, "psmux is already installed"

    if not shutil.which("winget"):
        return False, "winget is not available in this shell"

    result = subprocess.run(
        WINDOWS_PSMUX_INSTALL_CMD,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode == 0:
        return True, "Installed psmux via winget"

    detail = (result.stderr or result.stdout or "").strip() or "winget install failed"
    return False, detail


def _git_identity_configured(project_root: Path) -> bool:
    """Return whether git user identity is configured for the repository."""
    for key in ("user.name", "user.email"):
        probe = subprocess.run(
            ["git", "config", "--get", key],
            cwd=project_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if probe.returncode != 0 or not probe.stdout.strip():
            return False
    return True


def _ensure_codex_teams_bootstrap_excludes(project_root: Path) -> None:
    """Write local git excludes for files that should not block a bootstrap commit."""
    exclude_path = project_root / ".git" / "info" / "exclude"
    exclude_path.parent.mkdir(parents=True, exist_ok=True)

    existing = exclude_path.read_text(encoding="utf-8") if exclude_path.exists() else ""
    existing_lines = {line.strip() for line in existing.splitlines() if line.strip()}
    required = [
        ".vs/",
        ".svn/",
    ]
    missing = [entry for entry in required if entry not in existing_lines]
    if not missing:
        return

    prefix = "" if not existing or existing.endswith(("\n", "\r")) else "\n"
    payload = prefix + "\n".join(missing) + "\n"
    with open(exclude_path, "a", encoding="utf-8") as handle:
        handle.write(payload)


def _create_codex_teams_initial_commit(project_root: Path) -> tuple[bool, str]:
    """Create the first git commit so teams worktrees can be based on HEAD."""
    if not _git_identity_configured(project_root):
        return False, "git user.name and user.email must be configured before an automatic bootstrap commit can be created"

    _ensure_codex_teams_bootstrap_excludes(project_root)

    add_result = subprocess.run(
        ["git", "add", "-A"],
        cwd=project_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if add_result.returncode != 0:
        detail = (add_result.stderr or add_result.stdout or "").strip() or "git add failed"
        return False, detail

    commit_result = subprocess.run(
        ["git", "commit", "-m", CODEX_TEAMS_INITIAL_COMMIT_MESSAGE],
        cwd=project_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if commit_result.returncode == 0:
        return True, "Created an initial git commit for Codex teams"

    detail = (commit_result.stderr or commit_result.stdout or "").strip() or "git commit failed"
    return False, detail


def _maybe_bootstrap_codex_teams_environment(
    project_root: Path,
    *,
    team_status: dict[str, Any],
) -> dict[str, Any]:
    """Offer best-effort Codex teams bootstrap steps in interactive sessions."""
    if not sys.stdin.isatty():
        return team_status

    status = team_status

    if (
        status["native_windows"]
        and not status["runtime_backend_available"]
        and shutil.which("winget")
    ):
        if typer.confirm("Install psmux now so Codex teams can run on Windows?", default=True):
            ok, detail = _install_psmux_for_codex_teams()
            if ok:
                console.print(f"[green]✓[/green] {detail}")
            else:
                console.print(f"[yellow]Warning:[/yellow] {detail}")
            status = codex_team_runtime_status(project_root, integration_key="codex")

    if (
        status["git_repo_detected"]
        and not status["git_head_available"]
    ):
        prompt = (
            "Create an initial git commit now so Codex teams can create worker worktrees? "
            "This stages and commits the current working tree."
        )
        if typer.confirm(prompt, default=True):
            ok, detail = _create_codex_teams_initial_commit(project_root)
            if ok:
                console.print(f"[green]✓[/green] {detail}")
            else:
                console.print(f"[yellow]Warning:[/yellow] {detail}")
            status = codex_team_runtime_status(project_root, integration_key="codex")

    return status


def _install_shared_infra(
    project_path: Path,
    script_type: str,
    tracker: StepTracker | None = None,
    *,
    overwrite_existing: bool = False,
) -> bool:
    """Install shared infrastructure files into *project_path*.

    Copies ``.specify/scripts/`` and ``.specify/templates/`` from the
    bundled core_pack or source checkout.  Tracks all installed files
    in ``speckit.manifest.json``.
    Returns ``True`` on success.
    """
    from .integrations.manifest import IntegrationManifest
    from .launcher import write_project_specify_launcher_config

    core = _locate_core_pack()
    manifest = IntegrationManifest("speckit", project_path, version=get_speckit_version())
    preexisting_config = project_path / ".specify" / "config.json"
    config_existed = preexisting_config.exists()

    # Scripts
    if core and (core / "scripts").is_dir():
        scripts_src = core / "scripts"
    else:
        repo_root = Path(__file__).parent.parent.parent
        scripts_src = repo_root / "scripts"

    skipped_files: list[str] = []

    if scripts_src.is_dir():
        dest_scripts = project_path / ".specify" / "scripts"
        dest_scripts.mkdir(parents=True, exist_ok=True)
        variant_dir = "bash" if script_type == "sh" else "powershell"
        variant_src = scripts_src / variant_dir
        if variant_src.is_dir():
            dest_variant = dest_scripts / variant_dir
            dest_variant.mkdir(parents=True, exist_ok=True)
            # Merge without overwriting — only add files that don't exist yet
            for src_path in variant_src.rglob("*"):
                if src_path.is_file():
                    rel_path = src_path.relative_to(variant_src)
                    dst_path = dest_variant / rel_path
                    if dst_path.exists() and not overwrite_existing:
                        skipped_files.append(str(dst_path.relative_to(project_path)))
                    else:
                        dst_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src_path, dst_path)
                        rel = dst_path.relative_to(project_path).as_posix()
                        manifest.record_existing(rel)

    # Page templates (not command templates, not vscode-settings.json)
    if core and (core / "templates").is_dir():
        templates_src = core / "templates"
    else:
        repo_root = Path(__file__).parent.parent.parent
        templates_src = repo_root / "templates"

    if templates_src.is_dir():
        dest_templates = project_path / ".specify" / "templates"
        dest_templates.mkdir(parents=True, exist_ok=True)
        for src_path in templates_src.rglob("*"):
            if src_path.is_dir():
                continue
            if src_path.name == "vscode-settings.json":
                continue

            rel_path = src_path.relative_to(templates_src)
            dst = dest_templates / rel_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            if dst.exists() and not overwrite_existing:
                skipped_files.append(str(dst.relative_to(project_path)))
                continue

            shutil.copy2(src_path, dst)
            rel = dst.relative_to(project_path).as_posix()
            manifest.record_existing(rel)

        # Wheel installs split several template directories out of
        # ``core_pack/templates`` into sibling directories. Mirror them back
        # into ``.specify/templates`` so runtime behavior matches source checkouts.
        if core:
            extra_template_dirs = (
                "command-partials",
                "passive-skills",
                "project-map",
                "worker-prompts",
            )
            for extra_name in extra_template_dirs:
                extra_src = core / extra_name
                if not extra_src.is_dir():
                    continue

                extra_dest = dest_templates / extra_name
                extra_dest.mkdir(parents=True, exist_ok=True)
                for src_path in extra_src.rglob("*"):
                    if src_path.is_dir():
                        continue
                    rel_path = src_path.relative_to(extra_src)
                    dst = extra_dest / rel_path
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    if dst.exists() and not overwrite_existing:
                        skipped_files.append(str(dst.relative_to(project_path)))
                        continue

                    shutil.copy2(src_path, dst)
                    rel = dst.relative_to(project_path).as_posix()
                    manifest.record_existing(rel)

    # Seed the live project-map status file so downstream workflows share a
    # stable freshness surface even before the first real map refresh.
    status_path = project_map_status_path(project_path)
    if not status_path.exists():
        write_project_map_status(project_path, ProjectMapStatus())
        manifest.record_existing(status_path.relative_to(project_path).as_posix())
        legacy_status_path = legacy_project_map_status_path(project_path)
        if legacy_status_path.exists():
            manifest.record_existing(legacy_status_path.relative_to(project_path).as_posix())

    if skipped_files:
        import logging
        logging.getLogger(__name__).warning(
            "The following shared files already exist and were not overwritten:\n%s",
            "\n".join(f"  {f}" for f in skipped_files),
        )

    launcher_config = write_project_specify_launcher_config(project_path)
    if launcher_config is not None and not config_existed:
        manifest.record_existing(launcher_config.relative_to(project_path).as_posix())

    manifest.save()
    return True


def ensure_executable_scripts(project_path: Path, tracker: StepTracker | None = None) -> None:
    """Ensure POSIX .sh scripts under .specify/scripts (recursively) have execute bits (no-op on Windows)."""
    if os.name == "nt":
        return  # Windows: skip silently
    scripts_root = project_path / ".specify" / "scripts"
    if not scripts_root.is_dir():
        return
    failures: list[str] = []
    updated = 0
    for script in scripts_root.rglob("*.sh"):
        try:
            if script.is_symlink() or not script.is_file():
                continue
            try:
                with script.open("rb") as f:
                    if f.read(2) != b"#!":
                        continue
            except Exception:
                continue
            st = script.stat()
            mode = st.st_mode
            if mode & 0o111:
                continue
            new_mode = mode
            if mode & 0o400:
                new_mode |= 0o100
            if mode & 0o040:
                new_mode |= 0o010
            if mode & 0o004:
                new_mode |= 0o001
            if not (new_mode & 0o100):
                new_mode |= 0o100
            os.chmod(script, new_mode)
            updated += 1
        except Exception as e:
            failures.append(f"{script.relative_to(scripts_root)}: {e}")
    if tracker:
        detail = f"{updated} updated" + (f", {len(failures)} failed" if failures else "")
        tracker.add("chmod", "Set script permissions recursively")
        (tracker.error if failures else tracker.complete)("chmod", detail)
    else:
        if updated:
            console.print(f"[cyan]Updated execute permissions on {updated} script(s) recursively[/cyan]")
        if failures:
            console.print("[yellow]Some scripts could not be updated:[/yellow]")
            for f in failures:
                console.print(f"  - {f}")

def _materialize_constitution_template(template_text: str, project_path: Path) -> str:
    """Replace basic constitution template tokens with init-time defaults."""
    replacements = {
        "[PROJECT_NAME]": project_path.resolve().name,
    }

    for token, value in replacements.items():
        template_text = template_text.replace(token, value)

    return template_text


def _normalize_constitution_profile(profile: str | None) -> str:
    normalized = (profile or "product").strip().lower()
    normalized = CONSTITUTION_PROFILE_ALIASES.get(normalized, normalized)
    if normalized not in CONSTITUTION_PROFILE_CHOICES:
        raise ValueError(
            f"Invalid constitution profile '{profile}'. Expected one of: "
            f"{', '.join(sorted(CONSTITUTION_PROFILE_CHOICES))}."
        )
    return normalized


def _constitution_asset_root(project_path: Path | None = None) -> Path:
    candidates: list[Path] = []
    if project_path is not None:
        candidates.append(project_path / ".specify" / "templates" / "constitution")

    core = _locate_core_pack()
    if core:
        candidates.append(core / "templates" / "constitution")

    repo_root = Path(__file__).parent.parent.parent
    candidates.append(repo_root / "templates" / "constitution")

    for candidate in candidates:
        if candidate.is_dir():
            return candidate

    raise FileNotFoundError("Built-in constitution assets are missing")


def _load_constitution_profile_definition(
    constitution_profile: str,
    project_path: Path | None = None,
) -> dict[str, Any]:
    profile_id = _normalize_constitution_profile(constitution_profile)
    assets_root = _constitution_asset_root(project_path)
    profile_path = assets_root / "profiles" / f"{profile_id}.yml"
    profile_data = yaml.safe_load(profile_path.read_text(encoding="utf-8")) or {}
    if not isinstance(profile_data, dict):
        raise ValueError(f"Invalid constitution profile data in {profile_path}")
    return profile_data


def build_constitution_template_for_profile(
    constitution_profile: str,
    project_path: Path | None = None,
) -> tuple[str, dict[str, Any]]:
    profile_id = _normalize_constitution_profile(constitution_profile)
    assets_root = _constitution_asset_root(project_path)
    base_template = (assets_root / "base.md").read_text(encoding="utf-8")
    profile_data = _load_constitution_profile_definition(profile_id, project_path)

    replacements = {
        "{{CORE_PRINCIPLES}}": str(profile_data.get("core_principles", "")).strip(),
        "{{CONDITIONAL_GUIDANCE}}": str(profile_data.get("conditional_guidance", "")).strip(),
        "{{ENGINEERING_STANDARDS}}": str(profile_data.get("engineering_standards", "")).strip(),
        "{{WORKFLOW_AND_QUALITY_GATES}}": str(profile_data.get("workflow_and_quality_gates", "")).strip(),
    }

    rendered = base_template
    for token, value in replacements.items():
        rendered = rendered.replace(token, value)

    rendered = re.sub(r"\n{3,}", "\n\n", rendered).strip() + "\n"
    return rendered, profile_data


def _is_builtin_constitution_template(
    template_text: str,
    project_path: Path | None = None,
) -> bool:
    for profile_id in CONSTITUTION_PROFILE_CHOICES:
        built_text, _ = build_constitution_template_for_profile(profile_id, project_path)
        if template_text == built_text:
            return True
    return False


def ensure_constitution_template_for_profile(
    project_path: Path,
    constitution_profile: str = "product",
) -> dict[str, Any]:
    target_template = project_path / ".specify" / "templates" / "constitution-template.md"
    built_text, profile_data = build_constitution_template_for_profile(
        constitution_profile,
        project_path,
    )

    if target_template.exists():
        existing_text = target_template.read_text(encoding="utf-8")
        if existing_text == built_text:
            return {"applied": False, "reason": "already_selected", "profile": profile_data}
        if not _is_builtin_constitution_template(existing_text, project_path):
            return {"applied": False, "reason": "custom_template_preserved", "profile": profile_data}

    target_template.parent.mkdir(parents=True, exist_ok=True)
    target_template.write_text(built_text, encoding="utf-8")
    return {"applied": True, "reason": "profile_applied", "profile": profile_data}


def ensure_constitution_from_template(
    project_path: Path,
    tracker: StepTracker | None = None,
    constitution_profile: str = "product",
) -> None:
    """Copy constitution template to memory if it doesn't exist (preserves existing constitution on reinitialization)."""
    memory_constitution = project_path / ".specify" / "memory" / "constitution.md"
    template_constitution = project_path / ".specify" / "templates" / "constitution-template.md"

    profile_result = ensure_constitution_template_for_profile(
        project_path,
        constitution_profile=constitution_profile,
    )
    profile_data = profile_result["profile"]

    # If constitution already exists in memory, preserve it
    if memory_constitution.exists():
        if tracker:
            tracker.add("constitution", "Constitution setup")
            tracker.skip("constitution", "existing file preserved")
        return

    # If template doesn't exist, something went wrong with extraction
    if not template_constitution.exists():
        if tracker:
            tracker.add("constitution", "Constitution setup")
            tracker.error("constitution", "template not found")
        return

    # Copy a materialized version of the template to memory directory
    try:
        memory_constitution.parent.mkdir(parents=True, exist_ok=True)
        template_text = template_constitution.read_text(encoding="utf-8")
        today = date.today().isoformat()
        template_text = template_text.replace(
            "[CONSTITUTION_VERSION]",
            str(profile_data.get("version", "1.0.0")),
        )
        template_text = template_text.replace("[RATIFICATION_DATE]", today)
        template_text = template_text.replace("[LAST_AMENDED_DATE]", today)
        memory_constitution.write_text(
            _materialize_constitution_template(template_text, project_path),
            encoding="utf-8",
        )
        if tracker:
            tracker.add("constitution", "Constitution setup")
            tracker.complete("constitution", "initialized from template defaults")
        else:
            console.print("[cyan]Initialized constitution from template defaults[/cyan]")
    except Exception as e:
        if tracker:
            tracker.add("constitution", "Constitution setup")
            tracker.error("constitution", str(e))
        else:
            console.print(f"[yellow]Warning: Could not initialize constitution: {e}[/yellow]")


INIT_OPTIONS_FILE = ".specify/init-options.json"


def save_init_options(project_path: Path, options: dict[str, Any]) -> None:
    """Persist the CLI options used during ``specify init``.

    Writes a small JSON file to ``.specify/init-options.json`` so that
    later operations (e.g. preset install) can adapt their behaviour
    without scanning the filesystem.
    """
    dest = project_path / INIT_OPTIONS_FILE
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(options, indent=2, sort_keys=True))


def load_init_options(project_path: Path) -> dict[str, Any]:
    """Load the init options previously saved by ``specify init``.

    Returns an empty dict if the file does not exist or cannot be parsed.
    """
    path = project_path / INIT_OPTIONS_FILE
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _get_skills_dir(project_path: Path, selected_ai: str) -> Path:
    """Resolve the agent-specific skills directory.

    Returns ``project_path / <agent_folder> / "skills"``, falling back
    to ``project_path / ".agents/skills"`` for unknown agents.
    """
    agent_config = AGENT_CONFIG.get(selected_ai, {})
    agent_folder = agent_config.get("folder", "")
    if agent_folder:
        preferred = project_path / agent_folder.rstrip("/") / "skills"
        if selected_ai == "codex":
            legacy = project_path / ".agents" / "skills"
            if not preferred.exists() and legacy.exists():
                return legacy
        return preferred
    return project_path / ".agents" / "skills"


# Constants kept for backward compatibility with presets and extensions.
DEFAULT_SKILLS_DIR = ".agents/skills"
NATIVE_SKILLS_AGENTS = {"codex", "kimi"}
SKILL_DESCRIPTIONS = {
    "specify": "Use when a new or changed feature request needs guided requirement discovery and a planning-ready specification package.",
    "prd-scan": "Use when an existing repository needs read-only reconstruction scan outputs before final PRD synthesis.",
    "prd-build": "Use when a validated PRD scan package exists and the final PRD suite must be compiled from it.",
    "prd": "Deprecated compatibility entrypoint for reverse-PRD work; prefer prd-scan followed by prd-build.",
    "clarify": "Use when an existing specification package has planning-critical gaps, weak analysis, or new constraints that should be absorbed before planning.",
    "deep-research": "Use when a planning-ready spec still has feasibility risk and needs coordinated research, evidence packets, a Planning Handoff, or a disposable demo before implementation planning.",
    "research": "Use when a compatibility alias is needed for deep-research; route to the canonical feasibility research gate without creating separate sp-research artifacts.",
    "explain": "Use when the user needs the current stage artifact or handbook/project-map atlas artifact explained in plain language without changing the underlying files.",
    "fast": "Use when the requested change is truly trivial, local, low risk, and can be completed without entering the full specify-plan workflow.",
    "quick": "Use when a task is small but non-trivial and needs lightweight tracked planning, validation, or resumable execution outside the full workflow.",
    "plan": "Use when the current specification package is ready for implementation planning and you need design artifacts before task breakdown or coding.",
    "tasks": "Use when plan artifacts exist and execution needs dependency-aware tasks, guardrails, and parallelization guidance before implementation.",
    "implement": "Use when tasks.md exists and the planned work should be executed through the tracked implementation workflow.",
    "analyze": "Use when tasks.md exists and you need a non-destructive cross-artifact consistency and boundary-guardrail analysis before or during execution.",
    "constitution": "Use when project principles or development rules need to be created, revised, or realigned before further specification or planning work.",
    "checklist": "Use when you need a feature-specific checklist to validate requirements quality or planning completeness before implementation.",
    "test-scan": "Use when you need a deep, read-only scan that turns a repository's testing gaps into a build-ready unit-test system plan.",
    "test-build": "Use when a completed test-system scan exists and you need to build or refresh the repository's unit testing system through leader-managed execution waves.",
    "map-scan": "Use when handbook/project-map coverage is missing, stale, or insufficient and you need a complete project scan package before atlas construction.",
    "map-build": "Use when map-scan has produced complete coverage ledgers and scan packets, and you need to generate or refresh the atlas-style codebase handbook system from live code evidence.",
    "taskstoissues": "Use when tasks.md is ready and you want actionable, dependency-aware GitHub issues generated from it.",
}


def _install_codex_team_assets_if_needed(
    project_root: Path,
    manifest: Any,
    integration_key: str,
) -> list[Path]:
    """Install Codex-only helper assets when the active integration is codex."""
    from .codex_team import install_codex_team_assets

    return install_codex_team_assets(
        project_root,
        manifest,
        integration_key=integration_key,
    )


@app.command()
def init(
    project_name: str = typer.Argument(None, help="Name for your new project directory (optional if using --here, or use '.' for current directory)"),
    ai_assistant: str = typer.Option(None, "--ai", help=AI_ASSISTANT_HELP),
    ai_commands_dir: str = typer.Option(None, "--ai-commands-dir", help="Directory for agent command files (required with --ai generic, e.g. .myagent/commands/)"),
    script_type: str = typer.Option(None, "--script", help="Script type to use: sh or ps"),
    constitution_profile: str = typer.Option("product", "--constitution-profile", help="Built-in constitution profile: product, minimal, library, or regulated"),
    ignore_agent_tools: bool = typer.Option(False, "--ignore-agent-tools", help="Skip checks for AI agent tools like Claude Code"),
    no_git: bool = typer.Option(False, "--no-git", help="Skip git repository initialization"),
    here: bool = typer.Option(False, "--here", help="Initialize project in the current directory instead of creating a new one"),
    force: bool = typer.Option(False, "--force", help="Force merge/overwrite when using --here (skip confirmation)"),
    skip_tls: bool = typer.Option(False, "--skip-tls", help="Deprecated (no-op). Previously: skip SSL/TLS verification.", hidden=True),
    debug: bool = typer.Option(False, "--debug", help="Deprecated (no-op). Previously: show verbose diagnostic output.", hidden=True),
    github_token: str = typer.Option(None, "--github-token", help="Deprecated (no-op). Previously: GitHub token for API requests.", hidden=True),
    ai_skills: bool = typer.Option(False, "--ai-skills", help="Install Prompt.MD templates as agent skills (requires --ai)"),
    offline: bool = typer.Option(False, "--offline", help="Deprecated (no-op). All scaffolding now uses bundled assets.", hidden=True),
    preset: str = typer.Option(None, "--preset", help="Install a preset during initialization (by preset ID)"),
    branch_numbering: str = typer.Option(None, "--branch-numbering", help="Branch numbering strategy: 'sequential' (001, 002, …, 1000, … — expands past 999 automatically) or 'timestamp' (YYYYMMDD-HHMMSS)"),
    integration: str = typer.Option(None, "--integration", help="Use the new integration system (e.g. --integration copilot). Mutually exclusive with --ai."),
    integration_options: str = typer.Option(None, "--integration-options", help='Options for the integration (e.g. --integration-options="--commands-dir .myagent/cmds")'),
):
    """
    Initialize a new Specify project.

    By default, project files are downloaded from the latest GitHub release.
    Use --offline to scaffold from assets bundled inside the specify-cli
    package instead (no internet access required, ideal for air-gapped or
    enterprise environments).

    NOTE: Starting with v0.6.0, bundled assets will be used by default and
    the --offline flag will be removed. The GitHub download path will be
    retired because bundled assets eliminate the need for network access,
    avoid proxy/firewall issues, and guarantee that templates always match
    the installed CLI version.

    This command will:
    1. Check that required tools are installed (git is optional)
    2. Let you choose your AI assistant
    3. Download template from GitHub (or use bundled assets with --offline)
    4. Initialize a fresh git repository (if not --no-git and no existing repo)
    5. Optionally set up AI assistant commands

    Examples:
        specify init my-project
        specify init my-project --ai claude
        specify init my-project --ai copilot --no-git
        specify init --ignore-agent-tools my-project
        specify init . --ai claude         # Initialize in current directory
        specify init .                     # Initialize in current directory (interactive AI selection)
        specify init --here --ai claude    # Alternative syntax for current directory
        specify init --here --ai codex --ai-skills
        specify init --here --ai codebuddy
        specify init --here --ai vibe      # Initialize with Mistral Vibe support
        specify init --here
        specify init --here --force  # Skip confirmation when current directory not empty
        specify init my-project --ai claude   # Claude installs skills by default
        specify init my-project --constitution-profile library
        specify init --here --ai gemini --ai-skills
        specify init my-project --ai generic --ai-commands-dir .myagent/commands/  # Unsupported agent
        specify init my-project --offline  # Use bundled assets (no network access)
        specify init my-project --ai claude --preset healthcare-compliance  # With preset
    """

    show_banner()

    # Detect when option values are likely misinterpreted flags (parameter ordering issue)
    if ai_assistant and ai_assistant.startswith("--"):
        console.print(f"[red]Error:[/red] Invalid value for --ai: '{ai_assistant}'")
        console.print("[yellow]Hint:[/yellow] Did you forget to provide a value for --ai?")
        console.print("[yellow]Example:[/yellow] specify init --ai claude --here")
        console.print(f"[yellow]Available agents:[/yellow] {', '.join(AGENT_CONFIG.keys())}")
        raise typer.Exit(1)

    if ai_commands_dir and ai_commands_dir.startswith("--"):
        console.print(f"[red]Error:[/red] Invalid value for --ai-commands-dir: '{ai_commands_dir}'")
        console.print("[yellow]Hint:[/yellow] Did you forget to provide a value for --ai-commands-dir?")
        console.print("[yellow]Example:[/yellow] specify init --ai generic --ai-commands-dir .myagent/commands/")
        raise typer.Exit(1)

    try:
        constitution_profile = _normalize_constitution_profile(constitution_profile)
    except ValueError:
        console.print(
            f"[red]Error:[/red] Invalid --constitution-profile value '{constitution_profile}'. "
            f"Choose from: {', '.join(sorted(CONSTITUTION_PROFILE_CHOICES))}"
        )
        raise typer.Exit(1)

    if ai_assistant:
        ai_assistant = AI_ASSISTANT_ALIASES.get(ai_assistant, ai_assistant)

    # --integration and --ai are mutually exclusive
    if integration and ai_assistant:
        console.print("[red]Error:[/red] --integration and --ai are mutually exclusive")
        raise typer.Exit(1)

    # Resolve the integration — either from --integration or --ai
    from .integrations import INTEGRATION_REGISTRY, get_integration
    if integration:
        resolved_integration = get_integration(integration)
        if not resolved_integration:
            console.print(f"[red]Error:[/red] Unknown integration: '{integration}'")
            available = ", ".join(sorted(INTEGRATION_REGISTRY))
            console.print(f"[yellow]Available integrations:[/yellow] {available}")
            raise typer.Exit(1)
        ai_assistant = integration
    elif ai_assistant:
        resolved_integration = get_integration(ai_assistant)
        if not resolved_integration:
            console.print(f"[red]Error:[/red] Unknown agent '{ai_assistant}'. Choose from: {', '.join(sorted(INTEGRATION_REGISTRY))}")
            raise typer.Exit(1)

    # Deprecation warnings for --ai-skills and --ai-commands-dir (only when
    # an integration has been resolved from --ai or --integration)
    if ai_assistant or integration:
        if ai_skills:
            from .integrations.base import SkillsIntegration as _SkillsCheck
            if isinstance(resolved_integration, _SkillsCheck):
                console.print(
                    "[dim]Note: --ai-skills is not needed; "
                    "skills are the default for this integration.[/dim]"
                )
            else:
                console.print(
                    "[dim]Note: --ai-skills has no effect with "
                    f"{resolved_integration.key}; this integration uses commands, not skills.[/dim]"
                )
        if ai_commands_dir and resolved_integration.key != "generic":
            console.print(
                "[dim]Note: --ai-commands-dir is deprecated; "
                'use [bold]--integration generic --integration-options="--commands-dir <dir>"[/bold] instead.[/dim]'
            )

    if project_name == ".":
        here = True
        project_name = None  # Clear project_name to use existing validation logic

    if here and project_name:
        console.print("[red]Error:[/red] Cannot specify both project name and --here flag")
        raise typer.Exit(1)

    if not here and not project_name:
        console.print("[red]Error:[/red] Must specify either a project name, use '.' for current directory, or use --here flag")
        raise typer.Exit(1)

    if ai_skills and not ai_assistant:
        console.print("[red]Error:[/red] --ai-skills requires --ai to be specified")
        console.print("[yellow]Usage:[/yellow] specify init <project> --ai <agent> --ai-skills")
        raise typer.Exit(1)

    BRANCH_NUMBERING_CHOICES = {"sequential", "timestamp"}
    if branch_numbering and branch_numbering not in BRANCH_NUMBERING_CHOICES:
        console.print(f"[red]Error:[/red] Invalid --branch-numbering value '{branch_numbering}'. Choose from: {', '.join(sorted(BRANCH_NUMBERING_CHOICES))}")
        raise typer.Exit(1)

    if here:
        project_name = Path.cwd().name
        project_path = Path.cwd()

        existing_items = list(project_path.iterdir())
        if existing_items:
            console.print(f"[yellow]Warning:[/yellow] Current directory is not empty ({len(existing_items)} items)")
            console.print("[yellow]Template files will be merged with existing content and may overwrite existing files[/yellow]")
            if force:
                console.print("[cyan]--force supplied: skipping confirmation and proceeding with merge[/cyan]")
            else:
                response = typer.confirm("Do you want to continue?")
                if not response:
                    console.print("[yellow]Operation cancelled[/yellow]")
                    raise typer.Exit(0)
    else:
        project_path = Path(project_name).resolve()
        if project_path.exists():
            console.print()
            console.print(_open_block(
                "Directory conflict",
                [
                    f"Directory '[cyan]{project_name}[/cyan]' already exists",
                    "Please choose a different project name or remove the existing directory.",
                    "",
                    "Next: choose a different project name or remove the existing directory.",
                ],
                accent="red",
            ))
            raise typer.Exit(1)

    if ai_assistant:
        if ai_assistant not in AGENT_CONFIG:
            console.print(f"[red]Error:[/red] Invalid AI assistant '{ai_assistant}'. Choose from: {', '.join(AGENT_CONFIG.keys())}")
            raise typer.Exit(1)
        selected_ai = ai_assistant
    else:
        # Create options dict for selection (agent_key: display_name)
        ai_choices = {key: config["name"] for key, config in AGENT_CONFIG.items()}
        selected_ai = select_with_arrows(
            ai_choices,
            "Choose your AI assistant:",
            "copilot"
        )

    # Auto-promote interactively selected agents to the integration path
    if not ai_assistant:
        resolved_integration = get_integration(selected_ai)
        if not resolved_integration:
            console.print(f"[red]Error:[/red] Unknown agent '{selected_ai}'")
            raise typer.Exit(1)

    # Validate --ai-commands-dir usage.
    # Skip validation when --integration-options is provided — the integration
    # will validate its own options in setup().
    if selected_ai == "generic" and not integration_options:
        if not ai_commands_dir:
            console.print("[red]Error:[/red] --ai-commands-dir is required when using --ai generic or --integration generic")
            console.print('[dim]Example: specify init my-project --integration generic --integration-options="--commands-dir .myagent/commands/"[/dim]')
            raise typer.Exit(1)

    current_dir = Path.cwd()

    setup_lines = [
        f"{'Project':<15} [green]{project_path.name}[/green]",
        f"{'Working Path':<15} [dim]{current_dir}[/dim]",
        f"{'Constitution':<15} [cyan]{constitution_profile}[/cyan]",
    ]

    if not here:
        setup_lines.append(f"{'Target Path':<15} [dim]{project_path}[/dim]")

    console.print(_open_block("Initialize Spec Kit Plus Project", setup_lines, accent="cyan"))

    should_init_git = False
    if not no_git:
        should_init_git = check_tool("git")
        if not should_init_git:
            console.print("[yellow]Git not found - will skip repository initialization[/yellow]")

    if not ignore_agent_tools:
        agent_config = AGENT_CONFIG.get(selected_ai)
        if agent_config and agent_config["requires_cli"]:
            install_url = agent_config["install_url"]
            if not check_tool(selected_ai):
                console.print()
                console.print(_open_block(
                    "Agent Detection Error",
                    [
                        f"[cyan]{selected_ai}[/cyan] not found",
                        f"Install from: [cyan]{install_url}[/cyan]",
                        f"{agent_config['name']} is required to continue with this project type.",
                        "",
                        "Tip: Use [cyan]--ignore-agent-tools[/cyan] to skip this check",
                    ],
                    accent="red",
                ))
                raise typer.Exit(1)

    if script_type:
        if script_type not in SCRIPT_TYPE_CHOICES:
            console.print(f"[red]Error:[/red] Invalid script type '{script_type}'. Choose from: {', '.join(SCRIPT_TYPE_CHOICES.keys())}")
            raise typer.Exit(1)
        selected_script = script_type
    else:
        default_script = "ps" if os.name == "nt" else "sh"

        if sys.stdin.isatty():
            selected_script = select_with_arrows(SCRIPT_TYPE_CHOICES, "Choose script type (or press Enter)", default_script)
        else:
            selected_script = default_script

    console.print(f"[cyan]Selected AI assistant:[/cyan] {selected_ai}")
    console.print(f"[cyan]Selected script type:[/cyan] {selected_script}")

    tracker = StepTracker("Initialize Spec Kit Plus Project")

    sys._specify_tracker_active = True

    tracker.add("precheck", "Check required tools")
    tracker.complete("precheck", "ok")
    tracker.add("ai-select", "Select AI assistant")
    tracker.complete("ai-select", f"{selected_ai}")
    tracker.add("script-select", "Select script type")
    tracker.complete("script-select", selected_script)

    tracker.add("integration", "Install integration")
    tracker.add("shared-infra", "Install shared infrastructure")

    for key, label in [
        ("chmod", "Ensure scripts executable"),
        ("constitution", "Constitution setup"),
        ("learning-memory", "Project learning memory"),
        ("git", "Initialize git repository"),
        ("final", "Finalize"),
    ]:
        tracker.add(key, label)

    # Track git error message outside Live context so it persists
    git_error_message = None
    with Live(tracker.render(), console=console, refresh_per_second=8, transient=True) as live:
        tracker.attach_refresh(lambda: live.update(tracker.render()))
        try:
            # Integration-based scaffolding
            from .integrations.manifest import IntegrationManifest
            tracker.start("integration")
            manifest = IntegrationManifest(
                resolved_integration.key, project_path, version=get_speckit_version()
            )

            # Forward all legacy CLI flags to the integration as parsed_options.
            # Integrations receive every option and decide what to use;
            # irrelevant keys are simply ignored by the integration's setup().
            integration_parsed_options: dict[str, Any] = {}
            if ai_commands_dir:
                integration_parsed_options["commands_dir"] = ai_commands_dir
            if ai_skills:
                integration_parsed_options["skills"] = True

            resolved_integration.setup(
                project_path, manifest,
                parsed_options=integration_parsed_options or None,
                script_type=selected_script,
                raw_options=integration_options,
            )
            _install_codex_team_assets_if_needed(
                project_path,
                manifest,
                resolved_integration.key,
            )

            _write_integration_json(
                project_path,
                resolved_integration.key,
                selected_script,
            )

            tracker.complete("integration", resolved_integration.config.get("name", resolved_integration.key))

            # Install shared infrastructure (scripts, templates)
            tracker.start("shared-infra")
            _install_shared_infra(project_path, selected_script, tracker=tracker)
            _bootstrap_integration_context_file(
                project_path,
                resolved_integration,
                manifest,
            )
            manifest.save()
            tracker.complete("shared-infra", f"scripts ({selected_script}) + templates")

            ensure_executable_scripts(project_path, tracker=tracker)

            ensure_constitution_from_template(
                project_path,
                tracker=tracker,
                constitution_profile=constitution_profile,
            )
            ensure_learning_memory_from_templates(project_path, tracker=tracker)

            if not no_git:
                tracker.start("git")
                if is_git_repo(project_path):
                    tracker.complete("git", "existing repo detected")
                elif should_init_git:
                    success, error_msg = init_git_repo(project_path, quiet=True)
                    if success:
                        tracker.complete("git", "initialized")
                    else:
                        tracker.error("git", "init failed")
                        git_error_message = error_msg
                else:
                    tracker.skip("git", "git not available")
            else:
                tracker.skip("git", "--no-git flag")

            # Persist the CLI options so later operations (e.g. preset add)
            # can adapt their behaviour without re-scanning the filesystem.
            # Must be saved BEFORE preset install so _get_skills_dir() works.
            init_opts = {
                "ai": selected_ai,
                "integration": resolved_integration.key,
                "branch_numbering": branch_numbering or "sequential",
                "here": here,
                "preset": preset,
                "script": selected_script,
                "speckit_version": get_speckit_version(),
                "constitution_profile": constitution_profile,
            }
            # Ensure ai_skills is set for SkillsIntegration so downstream
            # tools (extensions, presets) emit SKILL.md overrides correctly.
            from .integrations.base import SkillsIntegration as _SkillsPersist
            if isinstance(resolved_integration, _SkillsPersist):
                init_opts["ai_skills"] = True
            save_init_options(project_path, init_opts)

            # Install preset if specified
            if preset:
                try:
                    from .presets import PresetManager, PresetCatalog, PresetError
                    preset_manager = PresetManager(project_path)
                    speckit_ver = get_speckit_version()

                    # Try local directory first, then catalog
                    local_path = Path(preset).resolve()
                    if local_path.is_dir() and (local_path / "preset.yml").exists():
                        preset_manager.install_from_directory(local_path, speckit_ver)
                    else:
                        preset_catalog = PresetCatalog(project_path)
                        pack_info = preset_catalog.get_pack_info(preset)
                        if not pack_info:
                            console.print(f"[yellow]Warning:[/yellow] Preset '{preset}' not found in catalog. Skipping.")
                        else:
                            try:
                                zip_path = preset_catalog.download_pack(preset)
                                preset_manager.install_from_zip(zip_path, speckit_ver)
                                # Clean up downloaded ZIP to avoid cache accumulation
                                try:
                                    zip_path.unlink(missing_ok=True)
                                except OSError:
                                    # Best-effort cleanup; failure to delete is non-fatal
                                    pass
                            except PresetError as preset_err:
                                console.print(f"[yellow]Warning:[/yellow] Failed to install preset '{preset}': {preset_err}")
                except Exception as preset_err:
                    console.print(f"[yellow]Warning:[/yellow] Failed to install preset: {preset_err}")

            tracker.complete("final", "project ready")
        except (typer.Exit, SystemExit):
            raise
        except Exception as e:
            tracker.error("final", str(e))
            console.print(_open_block("Failure", [f"Initialization failed: {e}"], accent="red"))
            if debug:
                _env_pairs = [
                    ("Python", sys.version.split()[0]),
                    ("Platform", sys.platform),
                    ("CWD", str(Path.cwd())),
                ]
                _label_width = max(len(k) for k, _ in _env_pairs)
                env_lines = [f"{k.ljust(_label_width)} → [bright_black]{v}[/bright_black]" for k, v in _env_pairs]
                console.print(_open_block("Debug Environment", env_lines, accent="magenta"))
            if not here and project_path.exists():
                shutil.rmtree(project_path)
            raise typer.Exit(1)
        finally:
            pass

    console.print(tracker.render())
    console.print("\n[bold green]Spec Kit Plus project ready.[/bold green]")

    # Pre-fetch spec-lint binary in the background so `specify lint` works
    # immediately without a download pause on first use.  Non-fatal.
    try:
        from specify_cli.lint import ensure_binary as _ensure_lint
        _ensure_lint()
    except Exception:
        pass  # spec-lint download is best-effort during init

    # Show git error details if initialization failed
    if git_error_message:
        console.print()
        console.print(_open_block(
            "Git Initialization Failed",
            [
                "[yellow]Warning:[/yellow] Git repository initialization failed",
                "",
                git_error_message,
                "",
                "[dim]You can initialize git manually later with:[/dim]",
                f"[cyan]cd {project_path if not here else '.'}[/cyan]",
                "[cyan]git init[/cyan]",
                "[cyan]git add .[/cyan]",
                "[cyan]git commit -m \"Initial commit\"[/cyan]",
            ],
            accent="red",
        ))

    # Agent folder security notice
    agent_config = AGENT_CONFIG.get(selected_ai)
    if agent_config:
        agent_folder = ai_commands_dir if selected_ai == "generic" else agent_config["folder"]
        if agent_folder:
            console.print()
            console.print(_open_block(
                "Security note",
                [
                    "Some agents may store credentials, auth tokens, or other identifying and private artifacts in the agent folder within your project.",
                    f"Consider adding [cyan]{agent_folder}[/cyan] (or parts of it) to [cyan].gitignore[/cyan] to prevent accidental credential leakage.",
                ],
                accent="yellow",
            ))

    steps_lines = []
    if not here:
        steps_lines.append(f"1. Go to the project folder: [cyan]cd {project_name}[/cyan]")
        step_num = 2
    else:
        steps_lines.append("1. You're already in the project directory!")
        step_num = 2

    # Determine skill display mode for the next-steps panel.
    # Skills integrations (codex, kimi, agy) should show skill invocation syntax.
    from .integrations.base import SkillsIntegration as _SkillsInt
    _is_skills_integration = isinstance(resolved_integration, _SkillsInt)

    codex_skill_mode = selected_ai == "codex" and (ai_skills or _is_skills_integration)
    claude_skill_mode = selected_ai == "claude" and (ai_skills or _is_skills_integration)
    kimi_skill_mode = selected_ai == "kimi"
    agy_skill_mode = selected_ai == "agy" and _is_skills_integration
    native_skill_mode = codex_skill_mode or claude_skill_mode or kimi_skill_mode or agy_skill_mode

    if native_skill_mode and not ai_skills:
        agent_start_labels = {
            "codex": "Codex",
            "claude": "Claude",
            "kimi": "Kimi",
            "agy": "Antigravity",
        }
        agent_label = agent_start_labels.get(
            selected_ai,
            resolved_integration.config.get("name", selected_ai).strip(),
        )
        skill_folder = resolved_integration.config.get("folder", "").rstrip("/")
        skill_subdir = resolved_integration.config.get("commands_subdir", "skills").strip("/")
        skills_path = f"{skill_folder}/{skill_subdir}" if skill_folder else skill_subdir
        steps_lines.append(
            f"{step_num}. Start {agent_label} in this project directory; Spec Kit Plus skills were installed to [cyan]{skills_path}[/cyan]"
        )
        step_num += 1

    if codex_skill_mode:
        team_status = codex_team_runtime_status(project_path, integration_key="codex")
        team_status = _maybe_bootstrap_codex_teams_environment(
            project_path,
            team_status=team_status,
        )
        readiness_lines = [
            f"runtime backend available: [cyan]{team_status['runtime_backend_available']}[/cyan]",
            f"git repo detected: [cyan]{team_status['git_repo_detected']}[/cyan]",
            f"git HEAD available: [cyan]{team_status['git_head_available']}[/cyan]",
            f"leader workspace clean: [cyan]{team_status['leader_workspace_clean']}[/cyan]",
            f"worktree-ready: [cyan]{team_status['worktree_ready']}[/cyan]",
        ]
        if team_status["next_steps"]:
            readiness_lines.append("")
            readiness_lines.append("Next steps")
            readiness_lines.extend(f"- {step}" for step in team_status["next_steps"])
        console.print()
        console.print(_open_block("Codex Teams Readiness", readiness_lines, accent="cyan"))

    usage_label = "skills" if native_skill_mode else "slash commands"

    def _display_cmd(name: str) -> str:
        if codex_skill_mode or agy_skill_mode:
            return f"$sp-{name}"
        if claude_skill_mode:
            return f"/sp-{name}"
        if kimi_skill_mode:
            return f"/skill:sp-{name}"
        return f"/sp.{name}"

    steps_lines.append(f"{step_num}. Start using {usage_label} with your AI agent:")
    steps_lines.append("   ")
    steps_lines.append("   Core workflow skills")
    constitution_review_text = "Review the seeded default constitution and apply project-specific changes when needed"
    if constitution_profile != "product":
        constitution_review_text = (
            f"Review the seeded {constitution_profile} constitution profile and apply project-specific changes when needed"
        )
    steps_lines.append(f"   {step_num}.1 [cyan]{_display_cmd('constitution')}[/] - {constitution_review_text}")
    steps_lines.append(f"   {step_num}.2 [cyan]{_display_cmd('specify')}[/] - Create the aligned requirement package")
    steps_lines.append(f"   {step_num}.3 [cyan]{_display_cmd('plan')}[/] - Generate the implementation design artifacts")
    steps_lines.append(f"   {step_num}.4 [cyan]{_display_cmd('tasks')}[/] - Generate actionable tasks")
    steps_lines.append(f"   {step_num}.5 [cyan]{_display_cmd('implement')}[/] - Execute implementation")
    steps_lines.append("   ")
    steps_lines.append("   Support skills")
    steps_lines.append(f"   - [cyan]{_display_cmd('map-scan')}[/] - Scan the complete project tree and produce the coverage ledger plus scan packets for existing-code mapping")
    steps_lines.append(f"   - [cyan]{_display_cmd('map-build')}[/] - Build or refresh `PROJECT-HANDBOOK.md` and `.specify/project-map/` from a complete map-scan package before specification or planning")
    steps_lines.append(f"   - [cyan]{_display_cmd('test-scan')}[/] - Deep-scan the testing surface and produce build-ready lanes")
    steps_lines.append(f"   - [cyan]{_display_cmd('test-build')}[/] - Build the unit testing system from scan-approved lanes with leader/subagent coordination")
    steps_lines.append(f"   - [cyan]{_display_cmd('auto')}[/] - Resume the recommended next workflow step from current repository state without naming the exact command manually")
    steps_lines.append(f"   - [cyan]{_display_cmd('prd-scan')}[/] - Produce reconstruction-grade PRD scan outputs for an existing repository before final synthesis")
    steps_lines.append(f"   - [cyan]{_display_cmd('prd-build')}[/] - Compile the final PRD suite from a validated PRD scan package")
    steps_lines.append(f"   - [cyan]{_display_cmd('prd')}[/] - Deprecated compatibility entrypoint; routes older reverse-PRD habits to the scan/build flow")
    steps_lines.append(f"   - [cyan]{_display_cmd('clarify')}[/] - Deepen an existing spec before planning when analysis or references still need work")
    steps_lines.append(f"   - [cyan]{_display_cmd('deep-research')}[/] - Coordinate research, evidence packets, and disposable demos into a traceable Planning Handoff before planning")
    steps_lines.append(f"   - [cyan]{_display_cmd('checklist')}[/] - Generate requirement-quality checklists after [cyan]{_display_cmd('plan')}[/]")
    steps_lines.append(f"   - [cyan]{_display_cmd('analyze')}[/] - Audit spec, context, plan, and tasks for drift before [cyan]{_display_cmd('implement')}[/], including boundary guardrail gaps")
    steps_lines.append(f"   - [cyan]{_display_cmd('explain')}[/] - Explain the current spec, plan, tasks, implement, or handbook/project-map atlas state in plain language")
    steps_lines.append(f"   - [cyan]{_display_cmd('integrate')}[/] - Inspect lane closeout readiness and complete independent feature integration")
    if codex_skill_mode:
        steps_lines.append("   ")
        steps_lines.append("   Codex-only runtime")
        steps_lines.append("   - [cyan]sp-teams[/] - Inspect the official Codex team/runtime surface and environment status")
        steps_lines.append("   - [cyan]$sp-teams[/] - Reach the same Codex-only runtime surface from the skills layer")
        steps_lines.append("   - [cyan]$sp-implement-teams[/] - Run implementation through the Codex-only teams execution surface")
    if claude_skill_mode:
        steps_lines.append("   ")
        steps_lines.append("   Claude Agent Teams")
        steps_lines.append("   - [cyan]/sp-implement-teams[/] - Run implementation through Claude Code's native Agent Teams surface")

    console.print()
    console.print(_open_block("Start Here", steps_lines, accent="cyan"))

    enhancement_intro = (
        "Support and gate skills that improve safety and confidence around your specs"
        if native_skill_mode
        else "Support and gate commands that improve safety and confidence around your specs"
    )
    enhancement_lines = [enhancement_intro, ""]
    if codex_skill_mode:
        enhancement_lines.append(
            "○ [cyan]sp-teams[/] [bright_black](codex-only)[/bright_black] - Inspect the official Codex team/runtime surface and environment status"
        )
    enhancement_lines.extend(
        [
            f"○ [cyan]{_display_cmd('map-scan')}[/] [bright_black](required for existing code)[/bright_black] - Produce a complete scan package before deeper brownfield specification, planning, task generation, or implementation resumes",
            f"○ [cyan]{_display_cmd('map-build')}[/] [bright_black](after map-scan)[/bright_black] - Generate or refresh the handbook/project-map atlas-style encyclopedia from the complete scan package",
            f"○ [cyan]{_display_cmd('auto')}[/] [bright_black](state-driven resume)[/bright_black] - Continue from the recommended next workflow step already recorded in repository state without renaming the canonical downstream command",
            f"○ [cyan]{_display_cmd('prd-scan')}[/] [bright_black](existing-project PRD scan)[/bright_black] - Produce the reconstruction-grade scan package for reverse-PRD work before final synthesis",
            f"○ [cyan]{_display_cmd('prd-build')}[/] [bright_black](after prd-scan)[/bright_black] - Compile the final PRD suite from a validated scan package without turning build back into an ad hoc scan",
            f"○ [cyan]{_display_cmd('prd')}[/] [bright_black](deprecated compatibility)[/bright_black] - Compatibility entrypoint only; prefer the canonical [cyan]{_display_cmd('prd-scan')}[/] -> [cyan]{_display_cmd('prd-build')}[/] flow",
            f"○ [cyan]{_display_cmd('clarify')}[/] [bright_black](optional)[/bright_black] - Strengthen the current spec package before planning when requirements, references, or analysis need deeper work",
            f"○ [cyan]{_display_cmd('deep-research')}[/] [bright_black](optional feasibility and research gate)[/bright_black] - Prove whether a clear requirement can be implemented and hand [cyan]{_display_cmd('plan')}[/] the research findings, demo evidence, constraints, and recommended approach",
            f"○ [cyan]{_display_cmd('analyze')}[/] [bright_black](default gate before implement)[/bright_black] - Cross-artifact consistency & alignment report, including boundary guardrail drift (after [cyan]{_display_cmd('tasks')}[/], before [cyan]{_display_cmd('implement')}[/])",
            f"○ [cyan]{_display_cmd('explain')}[/] [bright_black](optional)[/bright_black] - Explain the current spec, plan, task, implement, or handbook/project-map atlas artifact in plain language before moving forward",
            f"○ [cyan]{_display_cmd('checklist')}[/] [bright_black](optional)[/bright_black] - Generate quality checklists to validate requirements completeness, clarity, and consistency (after [cyan]{_display_cmd('plan')}[/])"
            ,
            f"○ [cyan]{_display_cmd('integrate')}[/] [bright_black](post-implement closeout)[/bright_black] - Inspect lane readiness, surface precheck failures, and close completed independent feature lanes before merge"
        ]
    )
    enhancements_title = "Support and gate skills" if native_skill_mode else "Support and gate commands"
    console.print()
    console.print(_open_block(enhancements_title, enhancement_lines, accent="cyan"))


def _require_codex_team_project(project_root: Path) -> str:
    _require_spec_kit_plus_project(project_root)
    current = _read_integration_json(project_root)
    integration_key = current.get("integration")
    if integration_key != "codex":
        console.print("[red]Error:[/red] Codex team runtime is only available for Codex integration projects.")
        raise typer.Exit(1)
    return integration_key


def _require_result_project(project_root: Path) -> str:
    _require_spec_kit_plus_project(project_root)
    current = _read_integration_json(project_root)
    integration_key = str(current.get("integration") or "").strip()
    if not integration_key:
        console.print(f"[red]Error:[/red] {INTEGRATION_JSON} is missing the integration key.")
        raise typer.Exit(1)
    return integration_key


def _run_hook_and_print(project_root: Path, event_name: str, payload: dict[str, Any]) -> None:
    from .hooks.engine import run_quality_hook

    result = run_quality_hook(project_root, event_name, payload)
    print(json.dumps(result.to_dict(), ensure_ascii=False))


def _normalize_optional_repo_path(project_root: Path, raw_value: str | None) -> str | None:
    if not raw_value:
        return None
    path = Path(raw_value)
    if not path.is_absolute():
        path = (project_root / path).resolve()
    return str(path)


def _resolve_feature_dir_for_command(
    project_root: Path,
    *,
    command_name: str,
    feature_dir: str | None,
) -> Path | None:
    if feature_dir:
        resolved = Path(feature_dir)
        return resolved if resolved.is_absolute() else (project_root / resolved).resolve()

    lane_result = resolve_lane_for_command(project_root, command_name=command_name)
    if lane_result.mode == "resume" and lane_result.selected_lane_id:
        lane = read_lane_record(project_root, lane_result.selected_lane_id)
        if lane is not None:
            return (project_root / lane.feature_dir).resolve()
    return None


def _print_lane_resolution_json(result: Any) -> None:
    lane_records = {record.lane_id: record for record in iter_lane_records(Path.cwd())}
    payload = {
        "mode": result.mode,
        "selected_lane_id": result.selected_lane_id,
        "reason": result.reason,
        "candidates": [
            {
                "lane_id": candidate.lane_id,
                "feature_id": candidate.feature_id,
                "feature_dir": candidate.feature_dir,
                "last_command": candidate.last_command,
                "inferred_command": candidate.last_command,
                "recovery_state": candidate.recovery_state,
                "last_stable_checkpoint": candidate.last_stable_checkpoint,
                "recovery_reason": candidate.recovery_reason,
                "verification_status": lane_records[candidate.lane_id].verification_status
                if candidate.lane_id in lane_records
                else "unknown",
                "worktree_path": lane_records[candidate.lane_id].worktree_path
                if candidate.lane_id in lane_records
                else "",
                "worktree_exists": (Path.cwd() / lane_records[candidate.lane_id].worktree_path).exists()
                if candidate.lane_id in lane_records
                else False,
            }
            for candidate in result.candidates
        ],
    }
    print(json.dumps(payload, ensure_ascii=False))


def _find_lane_by_feature_dir(project_root: Path, feature_dir: Path) -> LaneRecord | None:
    resolved_feature_dir = feature_dir.resolve()
    for lane in iter_lane_records(project_root):
        if (project_root / lane.feature_dir).resolve() == resolved_feature_dir:
            return lane
    return None


def _infer_lane_record(
    project_root: Path,
    *,
    lane_id: str,
    feature_dir: Path,
    branch: str,
    worktree: Path,
    command_name: str,
) -> LaneRecord:
    from specify_cli.hooks.checkpoint_serializers import serialize_implement_tracker, serialize_workflow_state
    from specify_cli.lanes.models import utc_now

    normalized_command = command_name.strip().lower()
    existing = read_lane_record(project_root, lane_id)

    lifecycle_map = {
        "specify": "specified",
        "plan": "planned",
        "tasks": "tasked",
        "implement": "implementing",
        "integrate": "integrating",
    }
    lifecycle_state = lifecycle_map.get(normalized_command, existing.lifecycle_state if existing else "draft")
    recovery_state = existing.recovery_state if existing is not None else "blocked"
    verification_status = existing.verification_status if existing is not None else "unknown"
    last_stable_checkpoint = existing.last_stable_checkpoint if existing is not None else ""

    workflow_path = feature_dir / "workflow-state.md"
    tracker_path = feature_dir / "implement-tracker.md"

    if normalized_command == "implement" and tracker_path.exists():
        tracker = serialize_implement_tracker(tracker_path)
        tracker_status = str(tracker.get("status") or "")
        last_stable_checkpoint = str(tracker.get("current_batch") or tracker.get("next_action") or last_stable_checkpoint)
        if tracker_status == "resolved":
            recovery_state = "completed"
            verification_status = "passed"
        elif tracker_status == "blocked":
            recovery_state = "blocked"
            verification_status = "failed"
        else:
            recovery_state = "resumable"
            verification_status = "unknown"
    elif workflow_path.exists():
        workflow = serialize_workflow_state(workflow_path)
        last_stable_checkpoint = str(workflow.get("next_action") or last_stable_checkpoint)
        recovery_state = "resumable"
    elif normalized_command == "integrate":
        recovery_state = "completed"
        verification_status = "passed"
    else:
        recovery_state = "resumable"

    return LaneRecord(
        lane_id=lane_id,
        feature_id=feature_dir.name,
        feature_dir=feature_dir.relative_to(project_root).as_posix(),
        branch_name=branch,
        worktree_path=worktree.relative_to(project_root).as_posix() if worktree.is_absolute() else worktree.as_posix(),
        lifecycle_state=lifecycle_state,
        recovery_state=recovery_state,
        last_command=normalized_command,
        last_stable_checkpoint=last_stable_checkpoint,
        verification_status=verification_status,
        created_at=existing.created_at if existing is not None else utc_now(),
        updated_at=utc_now(),
    )


def _resolve_result_context(
    project_root: Path,
    *,
    command_name: str,
    integration_key: str,
    request_id: str | None,
    feature_dir: str | None,
    task_id: str | None,
    workspace: str | None,
    session_slug: str | None,
    lane_id: str | None,
) -> dict[str, Any]:
    normalized_command = command_name.strip().lower()

    resolved_feature_dir: Path | None = None
    resolved_workspace: Path | None = None
    resolved_lane_id = lane_id

    if feature_dir:
        resolved_feature_dir = Path(feature_dir)
        if not resolved_feature_dir.is_absolute():
            resolved_feature_dir = (project_root / resolved_feature_dir).resolve()
    if workspace:
        resolved_workspace = Path(workspace)
        if not resolved_workspace.is_absolute():
            resolved_workspace = (project_root / resolved_workspace).resolve()

    if normalized_command == "implement":
        if integration_key == "codex" and request_id:
            return {
                "request_id": request_id,
                "feature_dir": None,
                "task_id": None,
                "quick_workspace": None,
                "debug_session_slug": None,
                "lane_id": None,
            }
        if resolved_feature_dir is None or not task_id:
            console.print("[red]Error:[/red] --feature-dir and --task-id are required for implement result handoff.")
            raise typer.Exit(1)
        return {
            "request_id": None,
            "feature_dir": resolved_feature_dir,
            "task_id": task_id,
            "quick_workspace": None,
            "debug_session_slug": None,
            "lane_id": None,
        }

    if normalized_command == "quick":
        if resolved_workspace is None or not resolved_lane_id:
            console.print("[red]Error:[/red] --workspace and --lane-id are required for quick result handoff.")
            raise typer.Exit(1)
        return {
            "request_id": None,
            "feature_dir": None,
            "task_id": None,
            "quick_workspace": resolved_workspace,
            "debug_session_slug": None,
            "lane_id": resolved_lane_id,
        }

    if normalized_command == "debug":
        if not session_slug or not resolved_lane_id:
            console.print("[red]Error:[/red] --session-slug and --lane-id are required for debug result handoff.")
            raise typer.Exit(1)
        return {
            "request_id": None,
            "feature_dir": None,
            "task_id": None,
            "quick_workspace": None,
            "debug_session_slug": session_slug,
            "lane_id": resolved_lane_id,
        }

    console.print(f"[red]Error:[/red] Unsupported result command '{command_name}'.")
    raise typer.Exit(1)


@lane_app.command("register")
def lane_register(
    feature_dir: str = typer.Option(..., "--feature-dir", help="Feature directory for this lane"),
    branch: str = typer.Option(..., "--branch", help="Git branch bound to the lane"),
    worktree: str = typer.Option(..., "--worktree", help="Worktree path bound to the lane"),
    command_name: str = typer.Option(..., "--command", help="Workflow command updating the lane"),
    lane_id: str = typer.Option(..., "--lane-id", help="Stable lane identifier"),
):
    """Register or update a concurrent feature lane."""

    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    resolved_feature_dir = _normalize_optional_repo_path(project_root, feature_dir)
    resolved_worktree = _normalize_optional_repo_path(project_root, worktree)
    if resolved_feature_dir is None or resolved_worktree is None:
        console.print("[red]Error:[/red] --feature-dir and --worktree are required.")
        raise typer.Exit(1)

    record = _infer_lane_record(
        project_root,
        lane_id=lane_id,
        feature_dir=Path(resolved_feature_dir),
        branch=branch,
        worktree=Path(resolved_worktree),
        command_name=command_name,
    )
    write_lane_record(project_root, record)
    worktree_result = materialize_lane_worktree(project_root, record)
    append_lane_event(
        project_root,
        lane_id,
        {
            "event": "lane_registered",
            "lane_id": lane_id,
            "feature_dir": record.feature_dir,
            "branch_name": record.branch_name,
            "worktree_path": record.worktree_path,
            "lifecycle_state": record.lifecycle_state,
            "recovery_state": record.recovery_state,
            "verification_status": record.verification_status,
            "command_name": record.last_command,
            "worktree_status": worktree_result.status,
            "worktree_reason": worktree_result.reason,
        },
    )
    payload = rebuild_lane_index(project_root)
    print(
        json.dumps(
            {
                "status": "ok",
                "lane_id": lane_id,
                "feature_dir": record.feature_dir,
                "branch_name": record.branch_name,
                "worktree_path": record.worktree_path,
                "lifecycle_state": record.lifecycle_state,
                "recovery_state": record.recovery_state,
                "verification_status": record.verification_status,
                "materialize_status": worktree_result.status,
                "checkout_mode": worktree_result.checkout_mode,
                "materialize_reason": worktree_result.reason,
                "index_lane_count": len(payload.get("lanes", [])),
            },
            ensure_ascii=False,
        )
    )


@lane_app.command("resolve")
def lane_resolve(
    command_name: str = typer.Option(..., "--command", help="Workflow command name"),
    feature_dir: str | None = typer.Option(None, "--feature-dir", help="Explicit feature directory override"),
    ensure_worktree: bool = typer.Option(False, "--ensure-worktree", help="Materialize the selected lane worktree when resolution is unique"),
):
    """Resolve the lane for a resumable workflow command."""

    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    if feature_dir:
        resolved = _normalize_optional_repo_path(project_root, feature_dir)
        lane = _find_lane_by_feature_dir(project_root, Path(str(resolved)))
        payload: dict[str, object]
        if lane is None:
            payload = {
                "mode": "blocked",
                "selected_lane_id": "",
                "reason": "feature-dir-has-no-registered-lane",
                "feature_dir": resolved,
                "candidates": [],
            }
            print(json.dumps(payload, ensure_ascii=False))
            return

        payload = {
            "mode": "resume",
            "selected_lane_id": lane.lane_id,
            "reason": "explicit-feature-dir",
            "feature_dir": resolved,
            "candidates": [],
        }
        payload["candidates"] = [
            {
                "lane_id": lane.lane_id,
                "feature_id": lane.feature_id,
                "feature_dir": lane.feature_dir,
                "last_command": lane.last_command,
                "inferred_command": infer_lane_command_name(project_root, lane),
                "recovery_state": lane.recovery_state,
                "last_stable_checkpoint": lane.last_stable_checkpoint,
                "recovery_reason": lane.recovery_reason,
                "verification_status": lane.verification_status,
                "worktree_path": lane.worktree_path,
                "worktree_exists": (project_root / lane.worktree_path).exists(),
            }
        ]
        if ensure_worktree:
            worktree_result = materialize_lane_worktree(project_root, lane)
            payload["worktree"] = {
                "status": worktree_result.status,
                "checkout_mode": worktree_result.checkout_mode,
                "path": worktree_result.worktree_path,
                "reason": worktree_result.reason,
            }
        print(
            json.dumps(payload, ensure_ascii=False)
        )
        return

    result = resolve_lane_for_command(project_root, command_name=command_name)
    if ensure_worktree and result.mode == "resume" and result.selected_lane_id:
        lane = read_lane_record(project_root, result.selected_lane_id)
        if lane is not None:
            worktree_result = materialize_lane_worktree(project_root, lane)
            payload = {
                "mode": result.mode,
                "selected_lane_id": result.selected_lane_id,
                "reason": result.reason,
                "worktree": {
                    "status": worktree_result.status,
                    "checkout_mode": worktree_result.checkout_mode,
                    "path": worktree_result.worktree_path,
                    "reason": worktree_result.reason,
                },
                "candidates": [
                    {
                        "lane_id": candidate.lane_id,
                        "feature_id": candidate.feature_id,
                        "feature_dir": candidate.feature_dir,
                        "last_command": candidate.last_command,
                        "recovery_state": candidate.recovery_state,
                        "last_stable_checkpoint": candidate.last_stable_checkpoint,
                        "recovery_reason": candidate.recovery_reason,
                        "verification_status": lane.verification_status if candidate.lane_id == lane.lane_id else "unknown",
                        "worktree_path": lane.worktree_path if candidate.lane_id == lane.lane_id else "",
                        "worktree_exists": (project_root / lane.worktree_path).exists()
                        if candidate.lane_id == lane.lane_id
                        else False,
                    }
                    for candidate in result.candidates
                ],
            }
            print(json.dumps(payload, ensure_ascii=False))
            return

    _print_lane_resolution_json(result)


@lane_app.command("status")
def lane_status():
    """List all registered lanes with their current recovery and worktree status."""

    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    lanes = iter_lane_records(project_root)
    print(
        json.dumps(
            {
                "status": "ok",
                "lane_count": len(lanes),
                "lanes": [
                    {
                        "lane_id": lane.lane_id,
                        "feature_id": lane.feature_id,
                        "feature_dir": lane.feature_dir,
                        "branch_name": lane.branch_name,
                        "lifecycle_state": lane.lifecycle_state,
                        "recovery_state": lane.recovery_state,
                        "verification_status": lane.verification_status,
                        "last_command": lane.last_command,
                        "inferred_command": infer_lane_command_name(project_root, lane),
                        "last_stable_checkpoint": lane.last_stable_checkpoint,
                        "worktree_path": lane.worktree_path,
                        "worktree_exists": (project_root / lane.worktree_path).exists(),
                        "ready_for_integrate": (
                            assess_integration_readiness(project_root, lane).ready
                            if lane.last_command in {"implement", "integrate"}
                            or lane.lifecycle_state in {"implementing", "integrating", "completed"}
                            else None
                        ),
                        "suggested_next_command": (
                            "integrate"
                            if lane.verification_status == "passed"
                            and lane.last_command in {"implement", "integrate"}
                            and lane.recovery_state in {"resumable", "completed"}
                            else (
                                lane.last_command or "specify"
                                if lane.recovery_state == "resumable"
                                else "manual-attention"
                            )
                        ),
                    }
                    for lane in lanes
                ],
            },
            ensure_ascii=False,
        )
    )


@lane_app.command("materialize-worktree")
def lane_materialize_worktree(
    lane_id: str = typer.Option(..., "--lane-id", help="Stable lane identifier"),
):
    """Materialize the git worktree for one registered lane when possible."""

    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    lane = read_lane_record(project_root, lane_id)
    if lane is None:
        console.print(f"[red]Error:[/red] lane '{lane_id}' not found.")
        raise typer.Exit(1)

    result = materialize_lane_worktree(project_root, lane)
    print(
        json.dumps(
            {
                "lane_id": result.lane_id,
                "worktree_path": result.worktree_path,
                "status": result.status,
                "checkout_mode": result.checkout_mode,
                "reason": result.reason,
            },
            ensure_ascii=False,
        )
    )


@teams_app.callback(invoke_without_command=True)
def _team_root(
    ctx: typer.Context,
    session_id: str = typer.Option("default", "--session-id", help="Runtime session identifier"),
    bootstrap: bool = typer.Option(False, "--bootstrap", help="Bootstrap a runtime session"),
    dispatch: str | None = typer.Option(None, "--dispatch", help="Dispatch request identifier"),
    worker: str = typer.Option("worker-1", "--worker", help="Target worker name for dispatched work"),
    fail: bool = typer.Option(False, "--fail", help="Mark a dispatched request as failed"),
    reason: str = typer.Option("synthetic failure", "--reason", help="Failure reason for --fail"),
    cleanup: bool = typer.Option(False, "--cleanup", help="Clean up the runtime session"),
):
    if ctx.invoked_subcommand is None:
        if bootstrap or dispatch or fail or cleanup:
            _handle_legacy_team_flags(
                session_id=session_id,
                bootstrap=bootstrap,
                dispatch=dispatch,
                worker=worker,
                fail=fail,
                reason=reason,
                cleanup=cleanup,
            )
            return
        ctx.invoke(team_status, session_id=session_id)


def _handle_legacy_team_flags(
    *,
    session_id: str,
    bootstrap: bool,
    dispatch: str | None,
    worker: str,
    fail: bool,
    reason: str,
    cleanup: bool,
) -> None:
    project_root = Path.cwd()
    _require_codex_team_project(project_root)

    if bootstrap:
        session = session_ops.bootstrap_session(project_root, session_id=session_id)
        console.print(f"Bootstrapped session [cyan]{session.session_id}[/cyan] with status [green]{session.status}[/green].")
        return

    if dispatch:
        _require_fresh_project_map_for_execution(project_root, command_name="team dispatch")
        record = dispatch_runtime_task(
            project_root,
            session_id=session_id,
            request_id=dispatch,
            target_worker=worker,
        )
        console.print(f"Dispatched [cyan]{record.request_id}[/cyan] to [cyan]{record.target_worker}[/cyan].")
        if fail:
            session, failed_record = mark_runtime_failure(
                project_root,
                session_id=session_id,
                request_id=dispatch,
                reason=reason,
            )
            console.print(f"Marked request [cyan]{failed_record.request_id}[/cyan] failed; session is now [yellow]{session.status}[/yellow].")
        return

    if cleanup:
        session = session_ops.cleanup_session(project_root, session_id=session_id)
        console.print(f"Cleaned session [cyan]{session.session_id}[/cyan].")
        return

    if fail:
        console.print("[red]Error:[/red] --fail requires --dispatch <request-id>.")
        raise typer.Exit(1)


@teams_app.command("status")
def team_status(
    session_id: str = typer.Option("default", "--session-id", help="Runtime session identifier"),
):
    """Inspect the Codex-only team/runtime surface for the current project."""
    project_root = Path.cwd()
    integration_key = _require_codex_team_project(project_root)

    console.print(team_help_text())
    console.print(team_availability_message(integration_key))

    status = codex_team_runtime_status(project_root, integration_key=integration_key, session_id=session_id)
    console.print(runtime_state_summary(project_root))
    console.print(f"runtime backend: {status['runtime_backend'] or 'unavailable'}")
    console.print(f"runtime backend available: {status['runtime_backend_available']}")
    console.print(f"runtime backend source: {status['runtime_backend_source']}")
    console.print(f"executor available: {status['executor_available']}")
    console.print(f"executor mode: {status['executor_mode']}")
    console.print(f"native build shell: {status['native_build_shell']['source']} (ready={status['native_build_shell']['ready']})")
    if status["native_build_shell"].get("target_arch"):
        console.print(f"native build target arch: {status['native_build_shell']['target_arch']}")
    console.print(f"baseline build: {status['baseline_build']['status']}")
    if status["baseline_build"].get("reason"):
        console.print(f"baseline build reason: {status['baseline_build']['reason']}")
    console.print(f"git repo detected: {status['git_repo_detected']}")
    console.print(f"git HEAD available: {status['git_head_available']}")
    console.print(f"leader workspace clean: {status['leader_workspace_clean']}")
    console.print(f"worktree-ready: {status['worktree_ready']}")
    console.print(f"teams ready: {status['teams_ready']}")
    if status["runtime_state"] is not None:
        console.print(
            f"live session: {status['runtime_state']['session']['session_id']} "
            f"({status['runtime_state']['session']['status']})"
        )
    else:
        console.print("live session: none")
    console.print("runtime config: [cyan].specify/teams/runtime.json[/cyan]")
    if not status["runtime_backend_available"]:
        try:
            ensure_tmux_available()
        except RuntimeEnvironmentError as exc:
            console.print(f"[yellow]Warning:[/yellow] {exc}")
    if status["next_steps"]:
        console.print("[bold]Next steps[/bold]")
        for step in status["next_steps"]:
            console.print(f"- {step}")


@teams_app.command("watch")
def team_watch(
    session_id: str = typer.Option("default", "--session-id", help="Runtime session identifier"),
    refresh_interval: float = typer.Option(1.0, "--refresh-interval", help="Refresh interval in seconds"),
    focus: str = typer.Option("", "--focus", help="Initial focused worker or leader"),
    view: str = typer.Option("split", "--view", help="Initial watch view: members, flow, or split"),
):
    """Open the full-screen observer over team members and flow."""
    project_root = Path.cwd()
    _require_codex_team_project(project_root)

    normalized_view = view.strip().lower()
    if normalized_view not in {"members", "flow", "split"}:
        console.print("[red]Error:[/red] --view must be one of: members, flow, split.")
        raise typer.Exit(1)
    if refresh_interval <= 0:
        console.print("[red]Error:[/red] --refresh-interval must be greater than 0.")
        raise typer.Exit(1)

    run_team_watch(
        project_root,
        session_id=session_id,
        refresh_interval=refresh_interval,
        focus=focus.strip(),
        view=normalized_view,
    )


@teams_app.command("await")
def team_await(
    session_id: str = typer.Option("default", "--session-id", help="Runtime session identifier"),
):
    project_root = Path.cwd()
    _require_codex_team_project(project_root)
    snapshot = session_ops.monitor_summary(project_root, session_id=session_id)
    console.print(f"Monitor snapshot: {snapshot.snapshot_id}")
    console.print(f"Task count: {snapshot.task_count}")
    console.print(f"Worker count: {snapshot.worker_count}")


@teams_app.command("doctor")
def team_doctor_command(
    session_id: str = typer.Option("default", "--session-id", help="Runtime session identifier"),
):
    project_root = Path.cwd()
    integration_key = _require_codex_team_project(project_root)
    report = codex_team_doctor(project_root, session_id=session_id, integration_key=integration_key)

    status = report["status"]
    transcript = report["transcript"]
    console.print(f"executor available: {status['executor_available']}")
    console.print(f"executor mode: {status['executor_mode']}")
    console.print(f"teams ready: {status['teams_ready']}")
    console.print(
        f"native build shell: {report['native_build_shell']['source']} "
        f"(ready={report['native_build_shell']['ready']})"
    )
    if report["native_build_shell"].get("target_arch"):
        console.print(f"native build target arch: {report['native_build_shell']['target_arch']}")
    console.print(f"baseline build: {report['baseline_build']['status']}")
    if report["baseline_build"].get("reason"):
        console.print(f"baseline build reason: {report['baseline_build']['reason']}")
    if status["runtime_state"] is not None:
        console.print(
            f"live session: {status['runtime_state']['session']['session_id']} "
            f"({status['runtime_state']['session']['status']})"
        )
    else:
        console.print("live session: none")

    console.print("[bold]Latest Transcript[/bold]")
    if transcript is None:
        console.print("- none")
    else:
        console.print(f"- path: {transcript.get('path', '')}")
        console.print(f"- returncode: {transcript.get('returncode', 'unknown')}")
        if transcript.get("state_probe"):
            probe = transcript["state_probe"]
            console.print(f"- team: {probe.get('team_name', '')}")
            console.print(f"- phase: {probe.get('phase', 'unknown')}")
        if transcript.get("stderr_tail"):
            console.print(f"- stderr: {transcript['stderr_tail']}")

    console.print("[bold]Failed Dispatches[/bold]")
    failed_dispatches = report["failed_dispatches"]
    if not failed_dispatches:
        console.print("- none")
    else:
        for item in failed_dispatches:
            console.print(f"- {item['request_id']} -> {item['target_worker']}: {item['reason']}")

    console.print("[bold]Recent Batches[/bold]")
    recent_batches = report["recent_batches"]
    if not recent_batches:
        console.print("- none")
    else:
        for item in recent_batches:
            console.print(
                f"- {item['batch_name']} ({item['batch_id']}): lane={item['lane_status']} "
                f"repo={item['repo_verification_status']}"
            )


@teams_app.command("live-probe")
def team_live_probe_command(
    session_id: str = typer.Option("default", "--session-id", help="Runtime session identifier"),
):
    project_root = Path.cwd()
    integration_key = _require_codex_team_project(project_root)
    try:
        payload = codex_team_live_probe(project_root, session_id=session_id, integration_key=integration_key)
    except RuntimeEnvironmentError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    console.print(f"probe status: {'passed' if payload['ok'] else 'failed'}")
    console.print(f"probe request: {payload['request_id']}")
    console.print(f"transcript path: {payload['transcript_path']}")
    dispatch = payload.get("dispatch") or {}
    if dispatch.get("reason"):
        console.print(f"dispatch reason: {dispatch['reason']}")


@teams_app.command("sync-back")
def team_sync_back(
    session_id: str = typer.Option("default", "--session-id", help="Runtime session identifier"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show candidate files without copying them"),
    allow_dirty: bool = typer.Option(False, "--allow-dirty", help="Allow sync-back when the main workspace is dirty"),
):
    project_root = Path.cwd()
    _require_codex_team_project(project_root)
    if dry_run:
        plan = plan_sync_back(project_root, session_id=session_id, allow_dirty=allow_dirty)
        console.print("[bold]Sync-back candidates[/bold]")
        if not plan["candidates"]:
            console.print("- none")
            return
        for candidate in plan["candidates"]:
            console.print(f"- {candidate['relative_path']} ({candidate['worker_id']})")
        return

    try:
        result = apply_sync_back(project_root, session_id=session_id, allow_dirty=allow_dirty)
    except RuntimeError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    console.print(f"Copied {result['copied_count']} file(s) from worker worktrees.")
    for candidate in result["copied"]:
        console.print(f"- {candidate['relative_path']} ({candidate['worker_id']})")


@teams_app.command("resume")
def team_resume(
    session_id: str = typer.Option("default", "--session-id", help="Runtime session identifier"),
):
    project_root = Path.cwd()
    _require_codex_team_project(project_root)
    session, resumed_existing = session_ops.resume_session(project_root, session_id=session_id)
    if resumed_existing:
        console.print(
            f"Resumed existing session [cyan]{session.session_id}[/cyan] with status [green]{session.status}[/green]."
        )
    else:
        console.print(
            f"Bootstrapped session [cyan]{session.session_id}[/cyan] with status [green]{session.status}[/green]."
        )


@teams_app.command("shutdown")
def team_shutdown(
    session_id: str = typer.Option("default", "--session-id", help="Runtime session identifier"),
    reason: str | None = typer.Option(None, "--reason", help="Failure reason for shutdown"),
    requested_by: str | None = typer.Option(None, "--requested-by", help="Identity requesting shutdown"),
    acknowledge: bool = typer.Option(False, "--acknowledge", help="Acknowledge a pending shutdown"),
    acknowledged_by: str | None = typer.Option(None, "--acknowledged-by", help="Identity acknowledging shutdown"),
):
    project_root = Path.cwd()
    _require_codex_team_project(project_root)
    if acknowledge:
        if not acknowledged_by:
            console.print("[red]Error:[/red] --acknowledge requires --acknowledged-by.")
            raise typer.Exit(1)
        session_ops.acknowledge_shutdown(project_root, session_id=session_id, acknowledged_by=acknowledged_by)
        console.print(f"Shutdown acknowledged for session [cyan]{session_id}[/cyan].")
        return
    if not reason or not requested_by:
        console.print("[red]Error:[/red] --reason and --requested-by are required to request a shutdown.")
        raise typer.Exit(1)
    session_ops.request_shutdown(
        project_root,
        session_id=session_id,
        reason=reason,
        requested_by=requested_by,
    )
    console.print(f"Shutdown requested for session [cyan]{session_id}[/cyan].")


@teams_app.command("cleanup")
def team_cleanup(
    session_id: str = typer.Option("default", "--session-id", help="Runtime session identifier"),
):
    project_root = Path.cwd()
    _require_codex_team_project(project_root)
    session = session_ops.cleanup_session(project_root, session_id=session_id)
    console.print(f"Cleaned session [cyan]{session.session_id}[/cyan].")


@teams_app.command("notify-hook", hidden=True)
def team_notify_hook(
    payload_json: str = typer.Argument(..., help="JSON payload from Codex CLI"),
):
    """Internal hook for Codex turn notifications."""
    try:
        payload = json.loads(payload_json)
    except json.JSONDecodeError:
        # Silently ignore invalid JSON
        return

    from .codex_team.auto_dispatch import run_notify_hook
    run_notify_hook(payload)


@teams_app.command("auto-dispatch")
def team_auto_dispatch(
    feature_dir: str = typer.Option(..., "--feature-dir", help="Feature directory that contains the active implementation state artifacts"),
    session_id: str = typer.Option("default", "--session-id", help="Runtime session identifier"),
):
    project_root = Path.cwd()
    _require_codex_team_project(project_root)
    _require_fresh_project_map_for_execution(project_root, command_name="team auto-dispatch")
    try:
        result = route_ready_parallel_batch(
            project_root,
            feature_dir=(project_root / feature_dir).resolve(),
            session_id=session_id,
        )
    except AutoDispatchUnavailableError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    except AutoDispatchError as exc:
        console.print(f"[yellow]No auto-dispatch:[/yellow] {exc}")
        raise typer.Exit(1) from exc

    console.print(
        f"Auto-dispatched [cyan]{result.batch_name}[/cyan] from [cyan]{result.feature_dir}[/cyan]: "
        f"{', '.join(result.dispatched_task_ids)}"
    )


@teams_app.command("complete-batch")
def team_complete_batch(
    batch_id: str = typer.Option(..., "--batch-id", help="Dispatched batch identifier"),
    session_id: str = typer.Option("default", "--session-id", help="Runtime session identifier"),
):
    project_root = Path.cwd()
    _require_codex_team_project(project_root)
    try:
        result = complete_dispatched_batch(
            project_root,
            batch_id=batch_id,
            session_id=session_id,
        )
    except AutoDispatchError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    console.print(
        f"Completed batch [cyan]{result.batch_name}[/cyan] ({result.batch_id}) with status "
        f"[green]{result.status}[/green]."
    )
    if result.next_batch_id:
        console.print(
            f"Auto-dispatched next batch [cyan]{result.next_batch_name}[/cyan] ({result.next_batch_id}): "
            f"{', '.join(result.next_dispatched_task_ids or [])}"
        )


@teams_app.command("submit-result")
def team_submit_result(
    request_id: str | None = typer.Option(None, "--request-id", help="Dispatch request identifier"),
    result_file: str | None = typer.Option(None, "--result-file", help="Path to worker result JSON"),
    session_id: str = typer.Option("default", "--session-id", help="Runtime session identifier"),
    print_schema: bool = typer.Option(False, "--print-schema", help="Print the worker result schema and exit"),
):
    project_root = Path.cwd()
    _require_codex_team_project(project_root)

    if print_schema:
        console.print(render_schema_help())
        return
    if not request_id:
        console.print("[red]Error:[/red] --request-id is required unless --print-schema is used.")
        raise typer.Exit(1)
    if not result_file:
        console.print("[red]Error:[/red] --result-file is required unless --print-schema is used.")
        raise typer.Exit(1)

    result_path = Path(result_file)
    if not result_path.is_absolute():
        result_path = (project_root / result_path).resolve()
    if not result_path.exists():
        console.print(f"[red]Error:[/red] Result file not found: {result_path}")
        raise typer.Exit(1)

    try:
        result = normalize_result_submission(
            project_root,
            request_id,
            result_path.read_text(encoding="utf-8"),
        )
        record = submit_runtime_result(
            project_root,
            session_id=session_id,
            request_id=request_id,
            result=result,
        )
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    console.print(
        f"Submitted result for [cyan]{record.request_id}[/cyan] with status "
        f"[green]{record.status}[/green]."
    )


@teams_app.command("result-template")
def team_result_template(
    request_id: str = typer.Option(..., "--request-id", help="Dispatch request identifier"),
    output: str | None = typer.Option(None, "--output", help="Optional file path to write the template to"),
):
    project_root = Path.cwd()
    _require_codex_team_project(project_root)

    try:
        payload = build_request_result_template(project_root, request_id)
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc

    rendered = json.dumps(payload, ensure_ascii=False, indent=2)
    if not output:
        print(rendered)
        return

    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = (project_root / output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    console.print(f"Wrote result template for [cyan]{request_id}[/cyan] to [cyan]{output_path}[/cyan].")


@teams_app.command("api")
def team_api(
    operation: str = typer.Argument(..., help="API operation (status|doctor|live-probe|tasks|auto-dispatch|complete-batch|submit-result)"),
    feature_dir: str | None = typer.Option(None, "--feature-dir", help="Feature directory for auto-dispatch"),
    batch_id: str | None = typer.Option(None, "--batch-id", help="Batch identifier for completion"),
    request_id: str | None = typer.Option(None, "--request-id", help="Dispatch request identifier for result submission"),
    result_file: str | None = typer.Option(None, "--result-file", help="Path to worker result JSON for result submission"),
    session_id: str = typer.Option("default", "--session-id", help="Runtime session identifier"),
):
    from specify_cli.codex_team.api_surface import TeamApiError, run_team_api_operation

    project_root = Path.cwd()
    try:
        envelope = run_team_api_operation(
            project_root,
            operation,
            feature_dir=feature_dir,
            batch_id=batch_id,
            request_id=request_id,
            result_file=result_file,
            session_id=session_id,
        )
    except TeamApiError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    print(json.dumps(envelope, ensure_ascii=False, default=str))


@result_app.command("path")
def result_path_command(
    command_name: str = typer.Option(..., "--command", help="Workflow command (implement|quick|debug)"),
    request_id: str | None = typer.Option(None, "--request-id", help="Dispatch request id (Codex/runtime-managed paths)"),
    feature_dir: str | None = typer.Option(None, "--feature-dir", help="Feature directory for implement result handoff"),
    task_id: str | None = typer.Option(None, "--task-id", help="Task id for implement result handoff"),
    workspace: str | None = typer.Option(None, "--workspace", help="Quick-task workspace path"),
    session_slug: str | None = typer.Option(None, "--session-slug", help="Debug session slug"),
    lane_id: str | None = typer.Option(None, "--lane-id", help="Delegated lane id"),
):
    """Print the canonical delegated-result handoff path."""
    project_root = Path.cwd()
    integration_key = _require_result_project(project_root)
    context = _resolve_result_context(
        project_root,
        command_name=command_name,
        integration_key=integration_key,
        request_id=request_id,
        feature_dir=feature_dir,
        task_id=task_id,
        workspace=workspace,
        session_slug=session_slug,
        lane_id=lane_id,
    )
    path = build_result_handoff_path(
        project_root,
        command_name=command_name,
        integration_key=integration_key,
        request_id=context["request_id"],
        feature_dir=context["feature_dir"],
        task_id=context["task_id"],
        quick_workspace=context["quick_workspace"],
        debug_session_slug=context["debug_session_slug"],
        lane_id=context["lane_id"],
    )
    print(
        json.dumps(
            {
                "command": command_name,
                "integration": integration_key,
                "path": str(path),
            },
            ensure_ascii=False,
        )
    )


@result_app.command("submit")
def result_submit_command(
    command_name: str = typer.Option(..., "--command", help="Workflow command (implement|quick|debug)"),
    result_file: str = typer.Option(..., "--result-file", help="Path to subagent result JSON"),
    request_id: str | None = typer.Option(None, "--request-id", help="Dispatch request id (Codex/runtime-managed paths)"),
    feature_dir: str | None = typer.Option(None, "--feature-dir", help="Feature directory for implement result handoff"),
    task_id: str | None = typer.Option(None, "--task-id", help="Task id for implement result handoff"),
    workspace: str | None = typer.Option(None, "--workspace", help="Quick-task workspace path"),
    session_slug: str | None = typer.Option(None, "--session-slug", help="Debug session slug"),
    lane_id: str | None = typer.Option(None, "--lane-id", help="Delegated lane id"),
):
    """Normalize and write a subagent result to the canonical handoff path."""
    project_root = Path.cwd()
    integration_key = _require_result_project(project_root)
    if integration_key == "codex":
        console.print("[red]Error:[/red] Codex projects must use `sp-teams submit-result` for runtime-managed result channels.")
        raise typer.Exit(1)

    source_path = Path(result_file)
    if not source_path.is_absolute():
        source_path = (project_root / source_path).resolve()
    if not source_path.exists():
        console.print(f"[red]Error:[/red] Result file not found: {source_path}")
        raise typer.Exit(1)

    context = _resolve_result_context(
        project_root,
        command_name=command_name,
        integration_key=integration_key,
        request_id=request_id,
        feature_dir=feature_dir,
        task_id=task_id,
        workspace=workspace,
        session_slug=session_slug,
        lane_id=lane_id,
    )
    try:
        path, normalized = write_normalized_result_handoff(
            project_root,
            command_name=command_name,
            integration_key=integration_key,
            raw_result=source_path.read_text(encoding="utf-8"),
            request_id=context["request_id"],
            feature_dir=context["feature_dir"],
            task_id=context["task_id"],
            quick_workspace=context["quick_workspace"],
            debug_session_slug=context["debug_session_slug"],
            lane_id=context["lane_id"],
        )
    except Exception as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    print(
        json.dumps(
            {
                "status": "ok",
                "command": command_name,
                "integration": integration_key,
                "path": str(path),
                "worker_status": normalized.status,
                "reported_status": normalized.reported_status,
            },
            ensure_ascii=False,
        )
    )


@hook_app.command("preflight")
def hook_preflight_command(
    command_name: str = typer.Option(..., "--command", help="Workflow command name"),
    feature_dir: str | None = typer.Option(None, "--feature-dir", help="Feature directory path"),
    workspace: str | None = typer.Option(None, "--workspace", help="Quick-task workspace path"),
    session_file: str | None = typer.Option(None, "--session-file", help="Debug session file path"),
):
    """Run the shared workflow preflight hook and return JSON."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    _run_hook_and_print(
        project_root,
        "workflow.preflight",
        {
            "command_name": command_name,
            "feature_dir": _normalize_optional_repo_path(project_root, feature_dir),
            "workspace": _normalize_optional_repo_path(project_root, workspace),
            "session_file": _normalize_optional_repo_path(project_root, session_file),
        },
    )


@hook_app.command("validate-state")
def hook_validate_state_command(
    command_name: str = typer.Option(..., "--command", help="Workflow command name"),
    feature_dir: str | None = typer.Option(None, "--feature-dir", help="Feature directory path"),
    workspace: str | None = typer.Option(None, "--workspace", help="Quick-task workspace path"),
    session_file: str | None = typer.Option(None, "--session-file", help="Debug session file path"),
):
    """Validate the current workflow source-of-truth state and return JSON."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    _run_hook_and_print(
        project_root,
        "workflow.state.validate",
        {
            "command_name": command_name,
            "feature_dir": _normalize_optional_repo_path(project_root, feature_dir),
            "workspace": _normalize_optional_repo_path(project_root, workspace),
            "session_file": _normalize_optional_repo_path(project_root, session_file),
        },
    )


@hook_app.command("validate-artifacts")
def hook_validate_artifacts_command(
    command_name: str = typer.Option(..., "--command", help="Workflow command name"),
    feature_dir: str = typer.Option(..., "--feature-dir", help="Feature directory path"),
):
    """Validate required workflow artifacts and return JSON."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    _run_hook_and_print(
        project_root,
        "workflow.artifacts.validate",
        {
            "command_name": command_name,
            "feature_dir": _normalize_optional_repo_path(project_root, feature_dir),
        },
    )


@hook_app.command("checkpoint")
def hook_checkpoint_command(
    command_name: str = typer.Option(..., "--command", help="Workflow command name"),
    feature_dir: str | None = typer.Option(None, "--feature-dir", help="Feature directory path"),
    workspace: str | None = typer.Option(None, "--workspace", help="Quick-task workspace path"),
    session_file: str | None = typer.Option(None, "--session-file", help="Debug session file path"),
):
    """Build a recovery checkpoint payload from the workflow source of truth."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    _run_hook_and_print(
        project_root,
        "workflow.checkpoint",
        {
            "command_name": command_name,
            "feature_dir": _normalize_optional_repo_path(project_root, feature_dir),
            "workspace": _normalize_optional_repo_path(project_root, workspace),
            "session_file": _normalize_optional_repo_path(project_root, session_file),
        },
    )


@hook_app.command("validate-packet")
def hook_validate_packet_command(
    packet_file: str = typer.Option(..., "--packet-file", help="Path to WorkerTaskPacket JSON"),
):
    """Validate a subagent execution packet and return JSON."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    _run_hook_and_print(
        project_root,
        "delegation.packet.validate",
        {"packet_file": _normalize_optional_repo_path(project_root, packet_file)},
    )


@hook_app.command("validate-result")
def hook_validate_result_command(
    packet_file: str = typer.Option(..., "--packet-file", help="Path to WorkerTaskPacket JSON"),
    result_file: str = typer.Option(..., "--result-file", help="Path to subagent result JSON"),
):
    """Validate a subagent result against its packet and return JSON."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    _run_hook_and_print(
        project_root,
        "delegation.join.validate",
        {
            "packet_file": _normalize_optional_repo_path(project_root, packet_file),
            "result_file": _normalize_optional_repo_path(project_root, result_file),
        },
    )


@hook_app.command("monitor-context")
def hook_monitor_context_command(
    command_name: str = typer.Option(..., "--command", help="Workflow command name"),
    feature_dir: str | None = typer.Option(None, "--feature-dir", help="Feature directory path"),
    workspace: str | None = typer.Option(None, "--workspace", help="Quick-task workspace path"),
    session_file: str | None = typer.Option(None, "--session-file", help="Debug session file path"),
    trigger: str = typer.Option("turn-progress", "--trigger", help="Structural context-monitor trigger"),
    context_usage: int | None = typer.Option(None, "--context-usage", help="Optional context usage percentage"),
):
    """Monitor context pressure and emit checkpoint recommendations as JSON."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    _run_hook_and_print(
        project_root,
        "workflow.context.monitor",
        {
            "command_name": command_name,
            "feature_dir": _normalize_optional_repo_path(project_root, feature_dir),
            "workspace": _normalize_optional_repo_path(project_root, workspace),
            "session_file": _normalize_optional_repo_path(project_root, session_file),
            "trigger": trigger,
            "context_usage_percent": context_usage,
        },
    )


@hook_app.command("validate-session-state")
def hook_validate_session_state_command(
    command_name: str = typer.Option(..., "--command", help="Workflow command name"),
    feature_dir: str | None = typer.Option(None, "--feature-dir", help="Feature directory path"),
    workspace: str | None = typer.Option(None, "--workspace", help="Quick-task workspace path"),
    session_file: str | None = typer.Option(None, "--session-file", help="Debug session file path"),
):
    """Validate cross-file session state consistency and return JSON."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    _run_hook_and_print(
        project_root,
        "workflow.session_state.validate",
        {
            "command_name": command_name,
            "feature_dir": _normalize_optional_repo_path(project_root, feature_dir),
            "workspace": _normalize_optional_repo_path(project_root, workspace),
            "session_file": _normalize_optional_repo_path(project_root, session_file),
        },
    )


@hook_app.command("render-statusline")
def hook_render_statusline_command(
    command_name: str = typer.Option(..., "--command", help="Workflow command name"),
    feature_dir: str | None = typer.Option(None, "--feature-dir", help="Feature directory path"),
    workspace: str | None = typer.Option(None, "--workspace", help="Quick-task workspace path"),
    session_file: str | None = typer.Option(None, "--session-file", help="Debug session file path"),
):
    """Render a compact workflow statusline summary and return JSON."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    _run_hook_and_print(
        project_root,
        "workflow.statusline.render",
        {
            "command_name": command_name,
            "feature_dir": _normalize_optional_repo_path(project_root, feature_dir),
            "workspace": _normalize_optional_repo_path(project_root, workspace),
            "session_file": _normalize_optional_repo_path(project_root, session_file),
        },
    )


@hook_app.command("validate-read-path")
def hook_validate_read_path_command(
    target_path: str = typer.Option(..., "--target-path", help="Path the workflow wants to read"),
):
    """Validate whether a read target stays inside workflow-safe path boundaries."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    _run_hook_and_print(
        project_root,
        "workflow.read_guard.validate",
        {"target_path": _normalize_optional_repo_path(project_root, target_path)},
    )


@hook_app.command("validate-prompt")
def hook_validate_prompt_command(
    prompt_text: str = typer.Option(..., "--prompt-text", help="Prompt text to validate"),
):
    """Validate prompt text for explicit workflow-bypass or override language."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    _run_hook_and_print(
        project_root,
        "workflow.prompt_guard.validate",
        {"prompt_text": prompt_text},
    )


@hook_app.command("validate-boundary")
def hook_validate_boundary_command(
    from_command: str = typer.Option(..., "--from-command", help="Current workflow command"),
    to_command: str = typer.Option(..., "--to-command", help="Requested next workflow command"),
):
    """Validate whether a workflow command transition is allowed."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    _run_hook_and_print(
        project_root,
        "workflow.boundary.validate",
        {"from_command": from_command, "to_command": to_command},
    )


@hook_app.command("validate-phase-boundary")
def hook_validate_phase_boundary_command(
    from_phase_mode: str = typer.Option(..., "--from-phase-mode", help="Current phase mode"),
    to_phase_mode: str = typer.Option(..., "--to-phase-mode", help="Requested next phase mode"),
):
    """Validate whether a workflow phase transition is allowed."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    _run_hook_and_print(
        project_root,
        "workflow.phase_boundary.validate",
        {"from_phase_mode": from_phase_mode, "to_phase_mode": to_phase_mode},
    )


@hook_app.command("validate-commit")
def hook_validate_commit_command(
    commit_message: str = typer.Option(..., "--commit-message", help="Commit message to validate"),
    feature_dir: str | None = typer.Option(None, "--feature-dir", help="Optional feature directory for tracker validation"),
):
    """Validate commit message and workflow terminal state before commit finalization."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    _run_hook_and_print(
        project_root,
        "workflow.commit.validate",
        {
            "commit_message": commit_message,
            "feature_dir": _normalize_optional_repo_path(project_root, feature_dir),
        },
    )


@hook_app.command("workflow-policy")
def hook_workflow_policy_command(
    command_name: str = typer.Option(..., "--command", help="Workflow command name"),
    feature_dir: str | None = typer.Option(None, "--feature-dir", help="Feature directory path"),
    workspace: str | None = typer.Option(None, "--workspace", help="Quick-task workspace path"),
    session_file: str | None = typer.Option(None, "--session-file", help="Debug session file path"),
    trigger: str = typer.Option("manual", "--trigger", help="Native or workflow trigger name"),
    requested_action: str | None = typer.Option(None, "--requested-action", help="Requested high-level action"),
    prior_redirect_count: int | None = typer.Option(None, "--prior-redirect-count", help="Number of prior redirect outcomes for this active workflow"),
):
    """Evaluate workflow policy and return normalized enforcement JSON."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    payload = {
        "command_name": command_name,
        "feature_dir": _normalize_optional_repo_path(project_root, feature_dir),
        "workspace": _normalize_optional_repo_path(project_root, workspace),
        "session_file": _normalize_optional_repo_path(project_root, session_file),
        "trigger": trigger,
        "requested_action": requested_action or "",
    }
    if prior_redirect_count is not None:
        payload["prior_redirect_count"] = prior_redirect_count
    _run_hook_and_print(
        project_root,
        "workflow.policy.evaluate",
        payload,
    )


@hook_app.command("build-compaction")
def hook_build_compaction_command(
    command_name: str = typer.Option(..., "--command", help="Workflow command name"),
    feature_dir: str | None = typer.Option(None, "--feature-dir", help="Feature directory path"),
    workspace: str | None = typer.Option(None, "--workspace", help="Quick-task workspace path"),
    session_file: str | None = typer.Option(None, "--session-file", help="Debug session file path"),
    trigger: str = typer.Option("manual", "--trigger", help="Compaction trigger name"),
):
    """Build a structured compaction artifact for resumable workflow recovery."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    _run_hook_and_print(
        project_root,
        "workflow.compaction.build",
        {
            "command_name": command_name,
            "feature_dir": _normalize_optional_repo_path(project_root, feature_dir),
            "workspace": _normalize_optional_repo_path(project_root, workspace),
            "session_file": _normalize_optional_repo_path(project_root, session_file),
            "trigger": trigger,
        },
    )


@hook_app.command("read-compaction")
def hook_read_compaction_command(
    command_name: str = typer.Option(..., "--command", help="Workflow command name"),
    feature_dir: str | None = typer.Option(None, "--feature-dir", help="Feature directory path"),
    workspace: str | None = typer.Option(None, "--workspace", help="Quick-task workspace path"),
    session_file: str | None = typer.Option(None, "--session-file", help="Debug session file path"),
):
    """Read the latest structured compaction artifact for a workflow scope."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    _run_hook_and_print(
        project_root,
        "workflow.compaction.read",
        {
            "command_name": command_name,
            "feature_dir": _normalize_optional_repo_path(project_root, feature_dir),
            "workspace": _normalize_optional_repo_path(project_root, workspace),
            "session_file": _normalize_optional_repo_path(project_root, session_file),
        },
    )


@hook_app.command("signal-learning")
def hook_signal_learning_command(
    command_name: str = typer.Option(..., "--command", help="Workflow command name"),
    retry_attempts: int = typer.Option(0, "--retry-attempts", help="Retry or recovery attempts observed"),
    hypothesis_changes: int = typer.Option(0, "--hypothesis-changes", help="Major hypothesis changes observed"),
    validation_failures: int = typer.Option(0, "--validation-failures", help="Validation failures observed"),
    artifact_rewrites: int = typer.Option(0, "--artifact-rewrites", help="Artifact rewrites observed"),
    command_failures: int = typer.Option(0, "--command-failures", help="Failed command attempts observed"),
    user_corrections: int = typer.Option(0, "--user-corrections", help="User corrections observed"),
    route_changes: int = typer.Option(0, "--route-changes", help="Workflow routing changes observed"),
    scope_changes: int = typer.Option(0, "--scope-changes", help="Scope changes observed"),
    false_starts: list[str] | None = typer.Option(None, "--false-start", help="Misleading first attempts or false leads"),
    hidden_dependencies: list[str] | None = typer.Option(None, "--hidden-dependency", help="Hidden dependencies discovered"),
):
    """Detect workflow friction that should trigger a learning review."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    _run_hook_and_print(
        project_root,
        "workflow.learning.signal",
        {
            "command_name": command_name,
            "retry_attempts": retry_attempts,
            "hypothesis_changes": hypothesis_changes,
            "validation_failures": validation_failures,
            "artifact_rewrites": artifact_rewrites,
            "command_failures": command_failures,
            "user_corrections": user_corrections,
            "route_changes": route_changes,
            "scope_changes": scope_changes,
            "false_starts": false_starts or [],
            "hidden_dependencies": hidden_dependencies or [],
        },
    )


@hook_app.command("review-learning")
def hook_review_learning_command(
    command_name: str = typer.Option(..., "--command", help="Workflow command name"),
    terminal_status: str = typer.Option(..., "--terminal-status", help="Terminal workflow status, for example resolved or blocked"),
    decision: str | None = typer.Option(None, "--decision", help="Learning review decision: none, captured, deferred, auto-captured, or manual-capture-needed"),
    rationale: str | None = typer.Option(None, "--rationale", help="Why no reusable learning exists or why capture was deferred"),
):
    """Enforce a learning review before terminal workflow closeout."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    learning_review = None
    if decision is not None or rationale is not None:
        learning_review = {"decision": decision or "", "rationale": rationale or ""}
    _run_hook_and_print(
        project_root,
        "workflow.learning.review",
        {
            "command_name": command_name,
            "terminal_status": terminal_status,
            "learning_review": learning_review,
        },
    )


@hook_app.command("capture-learning")
def hook_capture_learning_command(
    command_name: str = typer.Option(..., "--command", help="Workflow command name"),
    learning_type: str = typer.Option(..., "--type", help="Learning type"),
    summary: str = typer.Option(..., "--summary", help="One-line learning summary"),
    evidence: str = typer.Option(..., "--evidence", help="Supporting evidence or context"),
    recurrence_key: str | None = typer.Option(None, "--recurrence-key", help="Stable deduplication key"),
    signal_strength: str = typer.Option("medium", "--signal", help="Signal strength: low, medium, or high"),
    applies_to: list[str] | None = typer.Option(None, "--applies-to", help="Commands this learning should influence"),
    default_scope: str | None = typer.Option(None, "--scope", help="Default sharing scope label"),
    confirm: bool = typer.Option(False, "--confirm", help="Promote directly into project learnings instead of leaving as a candidate"),
    pain_score: int | None = typer.Option(None, "--pain-score", help="Workflow friction score that triggered capture"),
    false_starts: list[str] | None = typer.Option(None, "--false-start", help="Misleading first attempts or false leads"),
    rejected_paths: list[str] | None = typer.Option(None, "--rejected-path", help="Rejected diagnosis or implementation paths"),
    decisive_signal: str | None = typer.Option(None, "--decisive-signal", help="Evidence that made the learning clear"),
    root_cause_family: str | None = typer.Option(None, "--root-cause-family", help="Stable root-cause family label"),
    injection_targets: list[str] | None = typer.Option(None, "--injection-target", help="Workflow, document, or rule surface that should receive the learning"),
    promotion_hint: str | None = typer.Option(None, "--promotion-hint", help="When or how this candidate should be promoted"),
):
    """Capture a structured learning candidate through the hook surface."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    _run_hook_and_print(
        project_root,
        "workflow.learning.capture",
        {
            "command_name": command_name,
            "learning_type": learning_type,
            "summary": summary,
            "evidence": evidence,
            "recurrence_key": recurrence_key,
            "signal_strength": signal_strength,
            "applies_to": applies_to or [],
            "default_scope": default_scope,
            "confirm": confirm,
            "pain_score": pain_score,
            "false_starts": false_starts or [],
            "rejected_paths": rejected_paths or [],
            "decisive_signal": decisive_signal,
            "root_cause_family": root_cause_family,
            "injection_targets": injection_targets or [],
            "promotion_hint": promotion_hint,
        },
    )


@hook_app.command("inject-learning")
def hook_inject_learning_command(
    command_name: str = typer.Option(..., "--command", help="Workflow command name"),
    learning_type: str = typer.Option(..., "--type", help="Learning type"),
    summary: str = typer.Option("", "--summary", help="One-line learning summary"),
):
    """Derive prevention targets for a captured learning."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    _run_hook_and_print(
        project_root,
        "workflow.learning.inject",
        {
            "command_name": command_name,
            "learning_type": learning_type,
            "summary": summary,
        },
    )


@hook_app.command("mark-dirty")
def hook_mark_dirty_command(
    reason: str = typer.Option(..., "--reason", help="Why the current work needs a manual dirty override/fallback"),
):
    """Mark the project map dirty as the shared manual override/fallback."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    _run_hook_and_print(
        project_root,
        "project_map.mark_dirty",
        {"reason": reason},
    )


@hook_app.command("complete-refresh")
def hook_complete_refresh_command():
    """Finalize a successful project-map refresh through the shared hook surface."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    _run_hook_and_print(
        project_root,
        "project_map.complete_refresh",
        {},
    )


@app.command()
def check():
    """Check that all required tools are installed."""
    show_banner()
    console.print("[bold]Checking for installed tools...[/bold]\n")

    tracker = StepTracker("Check Available Tools")

    tracker.add("git", "Git version control")
    git_ok = check_tool("git", tracker=tracker)

    agent_results = {}
    for agent_key, agent_config in AGENT_CONFIG.items():
        if agent_key == "generic":
            continue  # Generic is not a real agent to check
        agent_name = agent_config["name"]
        requires_cli = agent_config["requires_cli"]

        tracker.add(agent_key, agent_name)

        if requires_cli:
            agent_results[agent_key] = check_tool(agent_key, tracker=tracker)
        else:
            # IDE-based agent - skip CLI check and mark as optional
            tracker.skip(agent_key, "IDE-based, no CLI check")
            agent_results[agent_key] = False  # Don't count IDE agents as "found"

    # Check VS Code variants (not in agent config)
    tracker.add("code", "Visual Studio Code")
    check_tool("code", tracker=tracker)

    tracker.add("code-insiders", "Visual Studio Code Insiders")
    check_tool("code-insiders", tracker=tracker)

    console.print(tracker.render())

    specify_candidates = _command_path_candidates("specify")
    if specify_candidates:
        console.print()
        rows = [("Active", f"[dim]{_current_specify_entrypoint()}[/dim]")]
        rows.append(("Module", f"[dim]{Path(__file__).resolve()}[/dim]"))
        if len(specify_candidates) > 1:
            rows.append(("PATH Entries", f"[yellow]{len(specify_candidates)} found[/yellow]"))
        else:
            rows.append(("PATH Entries", "1 found"))
        console.print(_cli_panel(_labeled_grid(rows), title="Specify CLI Path", border_style="cyan"))

        if len(specify_candidates) > 1:
            console.print("[yellow]Warning:[/yellow] Multiple `specify` executables are on PATH. A stale copy can shadow the latest install.")
            for candidate in specify_candidates:
                console.print(f"- [dim]{candidate}[/dim]")
            console.print(
                "[dim]Clean old pip/conda installs or reorder PATH, then verify `specify --help` shows the expected commands.[/dim]"
            )

    project_root = Path.cwd()
    project_config = project_root / ".specify" / "config.json"
    if project_config.exists():
        try:
            loaded = json.loads(project_config.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            loaded = None

        console.print()
        if isinstance(loaded, dict) and isinstance(loaded.get("specify_launcher"), dict):
            launcher = loaded["specify_launcher"]
            argv = launcher.get("argv")
            command = launcher.get("command")
            rows = [
                ("Project", f"[dim]{project_root}[/dim]"),
                ("Launcher", "[green]configured[/green]"),
            ]
            if isinstance(command, str) and command.strip():
                rows.append(("Command", f"[dim]{command}[/dim]"))
            elif isinstance(argv, list) and argv:
                rows.append(("Command", f"[dim]{' '.join(str(item) for item in argv)}[/dim]"))
            console.print(_cli_panel(_labeled_grid(rows), title="Project Launcher", border_style="green"))
        else:
            rows = [
                ("Project", f"[dim]{project_root}[/dim]"),
                ("Launcher", "[yellow]missing[/yellow]"),
                ("Mode", "[yellow]compatibility mode[/yellow]"),
            ]
            console.print(_cli_panel(_labeled_grid(rows), title="Project Launcher", border_style="yellow"))
            console.print(
                "[yellow]Warning:[/yellow] This project has Spec Kit state but no persisted project launcher. "
                "Runtime helper commands may fall back to PATH `specify` compatibility mode."
            )
            console.print(
                "[dim]Re-run `uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify init --here --force --ai <agent>` from the project root to persist a trusted launcher.[/dim]"
            )

    if (project_root / ".specify").exists():
        from .launcher import diagnose_project_runtime_compatibility

        compatibility_issues = diagnose_project_runtime_compatibility(project_root)
        if compatibility_issues:
            console.print()
            rows = [
                ("Project", f"[dim]{project_root}[/dim]"),
                ("Issues", f"[yellow]{len(compatibility_issues)} detected[/yellow]"),
            ]
            console.print(_cli_panel(_labeled_grid(rows), title="Project Compatibility", border_style="yellow"))
            for issue in compatibility_issues:
                console.print(f"- [yellow]{issue['summary']}[/yellow]")
                console.print(f"  [dim]{issue['repair']}[/dim]")

    console.print("\n[bold green]Specify CLI is ready to use![/bold green]")

    if not git_ok:
        console.print("[dim]Tip: Install git for repository management[/dim]")

    if not any(agent_results.values()):
        console.print("[dim]Tip: Install an AI assistant for the best experience[/dim]")

@app.command()
def version():
    """Display version and system information."""
    import platform
    import importlib.metadata

    show_banner()

    # Get CLI version from package metadata
    cli_version = "unknown"
    try:
        cli_version = importlib.metadata.version("specify-cli")
    except Exception:
        # Fallback: try reading from pyproject.toml if running from source
        try:
            import tomllib
            pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
            if pyproject_path.exists():
                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)
                    cli_version = data.get("project", {}).get("version", "unknown")
        except Exception:
            pass

    info_table = Table(show_header=False, box=None, padding=(0, 2))
    info_table.add_column("Key", style="cyan", justify="right")
    info_table.add_column("Value", style="white")

    info_table.add_row("CLI Version", cli_version)
    info_table.add_row("", "")
    info_table.add_row("Python", platform.python_version())
    info_table.add_row("Platform", platform.system())
    info_table.add_row("Architecture", platform.machine())
    info_table.add_row("OS Version", platform.version())
    info_table.add_row("", "")
    info_table.add_row("Executable", _current_specify_entrypoint())
    info_table.add_row("Module Path", str(Path(__file__).resolve()))

    specify_candidates = _command_path_candidates("specify")
    if specify_candidates:
        info_table.add_row("PATH Entries", str(len(specify_candidates)))

    panel = Panel(
        info_table,
        title="[bold cyan]Specify CLI Information[/bold cyan]",
        border_style="cyan",
        padding=(1, 2)
    )

    console.print(panel)
    if len(specify_candidates) > 1:
        console.print("[yellow]Warning:[/yellow] Multiple `specify` executables are on PATH:")
        for candidate in specify_candidates:
            console.print(f"- [dim]{candidate}[/dim]")
        console.print(
            "[dim]If a new workflow command is missing, remove stale pip/conda/uv tool installs or move the latest entry earlier on PATH.[/dim]"
        )
    console.print()


@app.command("integrate")
def integrate(
    feature_dir: str | None = typer.Option(None, "--feature-dir", help="Feature directory to close out"),
    close: bool = typer.Option(False, "--close", help="Mark the targeted lane integrated after readiness passes"),
):
    """Inspect candidate lanes for closeout through the integrate workflow."""

    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)

    if feature_dir:
        resolved = _resolve_feature_dir_for_command(
            project_root,
            command_name="integrate",
            feature_dir=feature_dir,
        )
        readiness = None
        lane_payload = None
        lane_record = None
        if resolved is not None:
            relative_feature_dir = Path(resolved).relative_to(project_root).as_posix()
            lane_record = next(
                (
                    record
                    for record in collect_integration_candidates(project_root)
                    if record.feature_dir == relative_feature_dir
                ),
                None,
            )
            if lane_record is None:
                for record in rebuild_lane_index(project_root).get("lanes", []):
                    if isinstance(record, dict) and record.get("feature_dir") == relative_feature_dir:
                        lane_record = read_lane_record(project_root, str(record["lane_id"]))
                        if lane_record is not None:
                            break
            if lane_record is not None:
                readiness = assess_integration_readiness(project_root, lane_record)
                lane_payload = readiness.lane
                if close and readiness.ready:
                    lane_payload = mark_lane_integrated(project_root, readiness.lane)

        print(
            json.dumps(
                {
                    "status": "ok"
                    if lane_record is not None and (readiness is None or readiness.ready or not close)
                    else "blocked",
                    "mode": "targeted",
                    "feature_dir": str(resolved) if resolved is not None else None,
                    "closed": bool(close and readiness is not None and readiness.ready),
                    "ready": readiness.ready if readiness is not None else None,
                    "lane_id": lane_payload.lane_id if lane_payload is not None else None,
                    "checks": readiness.checks if readiness is not None else [],
                },
                ensure_ascii=False,
            )
        )
        return

    candidates = collect_integration_candidates(project_root)
    print(
        json.dumps(
            {
                "status": "ok",
                "mode": "discovery",
                "candidates": [
                    (
                        lambda readiness: {
                            "lane_id": readiness.lane.lane_id,
                            "feature_id": readiness.lane.feature_id,
                            "feature_dir": readiness.lane.feature_dir,
                            "branch_name": readiness.lane.branch_name,
                            "recovery_state": readiness.lane.recovery_state,
                            "verification_status": readiness.lane.verification_status,
                            "ready": readiness.ready,
                            "recommended_action": "close" if readiness.ready else "fix-prechecks",
                            "checks": readiness.checks,
                        }
                    )(assess_integration_readiness(project_root, lane))
                    for lane in candidates
                ],
            },
            ensure_ascii=False,
        )
    )


@app.command()
def lint(
    dir: str = typer.Option(".", "--dir", help="Feature directory path (containing spec.md, alignment.md, etc.)"),
    tier: str = typer.Option("standard", "--tier", help="Check tier: light, standard, deep"),
    show_version: bool = typer.Option(False, "--version", help="Print spec-lint version and exit"),
    force_download: bool = typer.Option(False, "--force-download", help="Re-download spec-lint binary even if cached"),
):
    """Run spec quality gate checks on a feature directory.

    Downloads the spec-lint binary on first run (cached at ~/.specify/bin/).
    """
    from specify_cli.lint import run as run_lint

    args = []
    if show_version:
        args.append("--version")
    else:
        args.extend(["-dir", dir, "-tier", tier])

    ec = run_lint(args, force=force_download)
    raise typer.Exit(code=ec)


# ===== Extension Commands =====

extension_app = typer.Typer(
    name="extension",
    help="Manage spec-kit extensions",
    add_completion=False,
)
app.add_typer(extension_app, name="extension")

catalog_app = typer.Typer(
    name="catalog",
    help="Manage extension catalogs",
    add_completion=False,
)
extension_app.add_typer(catalog_app, name="catalog")

preset_app = typer.Typer(
    name="preset",
    help="Manage spec-kit presets",
    add_completion=False,
)
app.add_typer(preset_app, name="preset")

preset_catalog_app = typer.Typer(
    name="catalog",
    help="Manage preset catalogs",
    add_completion=False,
)
preset_app.add_typer(preset_catalog_app, name="catalog")


def get_speckit_version() -> str:
    """Get current spec-kit version."""
    import importlib.metadata
    try:
        return importlib.metadata.version("specify-cli")
    except Exception:
        # Fallback: try reading from pyproject.toml
        try:
            import tomllib
            pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
            if pyproject_path.exists():
                with open(pyproject_path, "rb") as f:
                    data = tomllib.load(f)
                    return data.get("project", {}).get("version", "unknown")
        except Exception:
            # Intentionally ignore any errors while reading/parsing pyproject.toml.
            # If this lookup fails for any reason, we fall back to returning "unknown" below.
            pass
    return "unknown"


# ===== Integration Commands =====

integration_app = typer.Typer(
    name="integration",
    help="Manage AI agent integrations",
    add_completion=False,
)
app.add_typer(integration_app, name="integration")

# ===== Debug Commands =====

try:
    from .debug.cli import debug_app
except ModuleNotFoundError as exc:
    missing_debug_dependency = exc.name or "required debug dependency"
    debug_app = typer.Typer(
        name="debug",
        help="Systematic and resumable bug investigation and fixing (debug runtime dependency missing)",
        add_completion=False,
    )

    @debug_app.callback(invoke_without_command=True)
    def _debug_unavailable_callback(ctx: typer.Context) -> None:
        if ctx.invoked_subcommand is not None:
            return
        console.print(
            f"[red]Error:[/red] Debug command is unavailable because '{missing_debug_dependency}' is not installed."
        )
        console.print(
            "Install the missing dependency and retry, or use a non-debug workflow command."
        )
        raise typer.Exit(1)

app.add_typer(debug_app, name="debug")
# Register sp-debug as an alias per TOL-03
app.add_typer(debug_app, name="sp-debug")


INTEGRATION_JSON = ".specify/integration.json"


def _read_integration_json(project_root: Path) -> dict[str, Any]:
    """Load ``.specify/integration.json``.  Returns ``{}`` when missing."""
    path = project_root / INTEGRATION_JSON
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        console.print(f"[red]Error:[/red] {path} contains invalid JSON.")
        console.print(f"Please fix or delete {INTEGRATION_JSON} and retry.")
        console.print(f"[dim]Details:[/dim] {exc}")
        raise typer.Exit(1)
    except OSError as exc:
        console.print(f"[red]Error:[/red] Could not read {path}.")
        console.print(f"Please fix file permissions or delete {INTEGRATION_JSON} and retry.")
        console.print(f"[dim]Details:[/dim] {exc}")
        raise typer.Exit(1)
    if not isinstance(data, dict):
        console.print(f"[red]Error:[/red] {path} must contain a JSON object, got {type(data).__name__}.")
        console.print(f"Please fix or delete {INTEGRATION_JSON} and retry.")
        raise typer.Exit(1)
    return data


def _write_integration_json(
    project_root: Path,
    integration_key: str,
    script_type: str,
) -> None:
    """Write ``.specify/integration.json`` for *integration_key*."""
    script_ext = "sh" if script_type == "sh" else "ps1"
    dest = project_root / INTEGRATION_JSON
    dest.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "integration": integration_key,
        "version": get_speckit_version(),
        "scripts": {
            "update-context": f".specify/integrations/{integration_key}/scripts/update-context.{script_ext}",
        },
    }
    if integration_key == "codex":
        payload["team"] = {
            "surface": "sp-teams",
            "runtime_config": ".specify/teams/runtime.json",
        }
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _remove_integration_json(project_root: Path) -> None:
    """Remove ``.specify/integration.json`` if it exists."""
    path = project_root / INTEGRATION_JSON
    if path.exists():
        path.unlink()


def _normalize_script_type(script_type: str, source: str) -> str:
    """Normalize and validate a script type from CLI/config sources."""
    normalized = script_type.strip().lower()
    if normalized in SCRIPT_TYPE_CHOICES:
        return normalized
    console.print(
        f"[red]Error:[/red] Invalid script type {script_type!r} from {source}. "
        f"Expected one of: {', '.join(sorted(SCRIPT_TYPE_CHOICES.keys()))}."
    )
    raise typer.Exit(1)


def _resolve_script_type(project_root: Path, script_type: str | None) -> str:
    """Resolve the script type from the CLI flag or init-options.json."""
    if script_type:
        return _normalize_script_type(script_type, "--script")
    opts = load_init_options(project_root)
    saved = opts.get("script")
    if isinstance(saved, str) and saved.strip():
        return _normalize_script_type(saved, ".specify/init-options.json")
    return "ps" if os.name == "nt" else "sh"


@integration_app.command("list")
def integration_list():
    """List available integrations and installed status."""
    from .integrations import INTEGRATION_REGISTRY

    project_root = Path.cwd()

    _require_spec_kit_plus_project(project_root)

    current = _read_integration_json(project_root)
    installed_key = current.get("integration")

    table = Table(title="AI Agent Integrations")
    table.add_column("Key", style="cyan")
    table.add_column("Name")
    table.add_column("Status")
    table.add_column("CLI Required")

    for key in sorted(INTEGRATION_REGISTRY.keys()):
        integration = INTEGRATION_REGISTRY[key]
        cfg = integration.config or {}
        name = cfg.get("name", key)
        requires_cli = cfg.get("requires_cli", False)

        if key == installed_key:
            status = "[green]installed[/green]"
        else:
            status = ""

        cli_req = "yes" if requires_cli else "no (IDE)"
        table.add_row(key, name, status, cli_req)

    console.print(table)

    if installed_key:
        console.print(f"\n[dim]Current integration:[/dim] [cyan]{installed_key}[/cyan]")
    else:
        console.print("\n[yellow]No integration currently installed.[/yellow]")
        console.print("Install one with: [cyan]specify integration install <key>[/cyan]")


@integration_app.command("install")
def integration_install(
    key: str = typer.Argument(help="Integration key to install (e.g. claude, copilot)"),
    script: str | None = typer.Option(None, "--script", help="Script type: sh or ps (default: from init-options.json or platform default)"),
    integration_options: str | None = typer.Option(None, "--integration-options", help='Options for the integration (e.g. --integration-options="--commands-dir .myagent/cmds")'),
):
    """Install an integration into an existing project."""
    from .integrations import INTEGRATION_REGISTRY, get_integration
    from .integrations.manifest import IntegrationManifest

    project_root = Path.cwd()

    _require_spec_kit_plus_project(project_root)

    integration = get_integration(key)
    if integration is None:
        console.print(f"[red]Error:[/red] Unknown integration '{key}'")
        available = ", ".join(sorted(INTEGRATION_REGISTRY.keys()))
        console.print(f"Available integrations: {available}")
        raise typer.Exit(1)

    current = _read_integration_json(project_root)
    installed_key = current.get("integration")

    if installed_key and installed_key == key:
        console.print(f"[yellow]Integration '{key}' is already installed.[/yellow]")
        console.print("Run [cyan]specify integration uninstall[/cyan] first, then reinstall.")
        raise typer.Exit(0)

    if installed_key:
        console.print(f"[red]Error:[/red] Integration '{installed_key}' is already installed.")
        console.print(f"Run [cyan]specify integration uninstall[/cyan] first, or use [cyan]specify integration switch {key}[/cyan].")
        raise typer.Exit(1)

    selected_script = _resolve_script_type(project_root, script)

    # Ensure shared infrastructure is present (safe to run unconditionally;
    # _install_shared_infra merges missing files without overwriting).
    _install_shared_infra(project_root, selected_script)
    if os.name != "nt":
        ensure_executable_scripts(project_root)

    manifest = IntegrationManifest(
        integration.key, project_root, version=get_speckit_version()
    )

    # Build parsed options from --integration-options
    parsed_options: dict[str, Any] | None = None
    if integration_options:
        parsed_options = _parse_integration_options(integration, integration_options)

    try:
        integration.setup(
            project_root, manifest,
            parsed_options=parsed_options,
            script_type=selected_script,
            raw_options=integration_options,
        )
        _install_codex_team_assets_if_needed(
            project_root,
            manifest,
            integration.key,
        )
        _bootstrap_integration_context_file(
            project_root,
            integration,
            manifest,
        )
        manifest.save()
        _write_integration_json(project_root, integration.key, selected_script)
        _update_init_options_for_integration(project_root, integration, script_type=selected_script)

    except Exception as e:
        # Attempt rollback of any files written by setup
        try:
            integration.teardown(project_root, manifest, force=True)
        except Exception as rollback_err:
            # Suppress so the original setup error remains the primary failure
            console.print(f"[yellow]Warning:[/yellow] Failed to roll back integration changes: {rollback_err}")
        _remove_integration_json(project_root)
        console.print(f"[red]Error:[/red] Failed to install integration: {e}")
        raise typer.Exit(1)

    name = (integration.config or {}).get("name", key)
    console.print(f"\n[green]✓[/green] Integration '{name}' installed successfully")


def _parse_integration_options(integration: Any, raw_options: str) -> dict[str, Any] | None:
    """Parse --integration-options string into a dict matching the integration's declared options.

    Returns ``None`` when no options are provided.
    """
    import shlex
    parsed: dict[str, Any] = {}
    tokens = shlex.split(raw_options)
    declared_options = list(integration.options())
    declared = {opt.name.lstrip("-"): opt for opt in declared_options}
    allowed = ", ".join(sorted(opt.name for opt in declared_options))
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if not token.startswith("-"):
            console.print(f"[red]Error:[/red] Unexpected integration option value '{token}'.")
            if allowed:
                console.print(f"Allowed options: {allowed}")
            raise typer.Exit(1)
        name = token.lstrip("-")
        value: str | None = None
        # Handle --name=value syntax
        if "=" in name:
            name, value = name.split("=", 1)
        opt = declared.get(name)
        if not opt:
            console.print(f"[red]Error:[/red] Unknown integration option '{token}'.")
            if allowed:
                console.print(f"Allowed options: {allowed}")
            raise typer.Exit(1)
        key = name.replace("-", "_")
        if opt.is_flag:
            if value is not None:
                console.print(f"[red]Error:[/red] Option '{opt.name}' is a flag and does not accept a value.")
                raise typer.Exit(1)
            parsed[key] = True
            i += 1
        elif value is not None:
            parsed[key] = value
            i += 1
        elif i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
            parsed[key] = tokens[i + 1]
            i += 2
        else:
            console.print(f"[red]Error:[/red] Option '{opt.name}' requires a value.")
            raise typer.Exit(1)
    return parsed or None


def _update_init_options_for_integration(
    project_root: Path,
    integration: Any,
    script_type: str | None = None,
) -> None:
    """Update ``init-options.json`` to reflect *integration* as the active one."""
    from .integrations.base import SkillsIntegration
    opts = load_init_options(project_root)
    opts["integration"] = integration.key
    opts["ai"] = integration.key
    if script_type:
        opts["script"] = script_type
    if isinstance(integration, SkillsIntegration):
        opts["ai_skills"] = True
    else:
        opts.pop("ai_skills", None)
    save_init_options(project_root, opts)


def _repair_active_integration_runtime_assets(
    project_root: Path,
    *,
    script_type: str,
) -> tuple[str | None, int]:
    """Refresh shared infra and the active integration's managed runtime assets.

    This path is intentionally conservative: it refreshes shared/runtime-managed
    assets while leaving user-modified workflow and skill content alone.
    """
    from .integrations import get_integration
    from .integrations.manifest import IntegrationManifest

    current = _read_integration_json(project_root)
    installed_key = current.get("integration")

    _install_shared_infra(project_root, script_type, overwrite_existing=True)
    if os.name != "nt":
        ensure_executable_scripts(project_root)

    if not installed_key:
        return None, 0

    integration = get_integration(installed_key)
    if integration is None:
        raise ValueError(f"Unknown active integration '{installed_key}'")

    try:
        manifest = IntegrationManifest.load(integration.key, project_root)
        manifest.version = get_speckit_version()
    except (ValueError, FileNotFoundError):
        manifest = IntegrationManifest(
            integration.key, project_root, version=get_speckit_version()
        )

    integration.repair_runtime_assets(
        project_root,
        manifest,
        script_type=script_type,
    )
    _install_codex_team_assets_if_needed(
        project_root,
        manifest,
        integration.key,
    )
    manifest.save()
    _write_integration_json(project_root, integration.key, script_type)
    _update_init_options_for_integration(project_root, integration, script_type=script_type)
    return integration.key, len(manifest.files)


@integration_app.command("uninstall")
def integration_uninstall(
    key: str = typer.Argument(None, help="Integration key to uninstall (default: current integration)"),
    force: bool = typer.Option(False, "--force", help="Remove files even if modified"),
):
    """Uninstall an integration, safely preserving modified files."""
    from .integrations import get_integration
    from .integrations.manifest import IntegrationManifest

    project_root = Path.cwd()

    _require_spec_kit_plus_project(project_root)

    current = _read_integration_json(project_root)
    installed_key = current.get("integration")

    if key is None:
        if not installed_key:
            console.print("[yellow]No integration is currently installed.[/yellow]")
            raise typer.Exit(0)
        key = installed_key

    if installed_key and installed_key != key:
        console.print(f"[red]Error:[/red] Integration '{key}' is not the currently installed integration ('{installed_key}').")
        raise typer.Exit(1)

    integration = get_integration(key)

    manifest_path = project_root / ".specify" / "integrations" / f"{key}.manifest.json"
    if not manifest_path.exists():
        console.print(f"[yellow]No manifest found for integration '{key}'. Nothing to uninstall.[/yellow]")
        _remove_integration_json(project_root)
        # Clear integration-related keys from init-options.json
        opts = load_init_options(project_root)
        if opts.get("integration") == key or opts.get("ai") == key:
            opts.pop("integration", None)
            opts.pop("ai", None)
            opts.pop("ai_skills", None)
            save_init_options(project_root, opts)
        raise typer.Exit(0)

    try:
        manifest = IntegrationManifest.load(key, project_root)
    except (ValueError, FileNotFoundError) as exc:
        console.print(f"[red]Error:[/red] Integration manifest for '{key}' is unreadable.")
        console.print(f"Manifest: {manifest_path}")
        console.print(
            f"To recover, delete the unreadable manifest, run "
            f"[cyan]specify integration uninstall {key}[/cyan] to clear stale metadata, "
            f"then run [cyan]specify integration install {key}[/cyan] to regenerate."
        )
        console.print(f"[dim]Details:[/dim] {exc}")
        raise typer.Exit(1)

    if integration is not None:
        removed, skipped = integration.uninstall(project_root, manifest, force=force)
    else:
        removed, skipped = manifest.uninstall(project_root, force=force)

    _remove_integration_json(project_root)

    # Update init-options.json to clear the integration
    opts = load_init_options(project_root)
    if opts.get("integration") == key or opts.get("ai") == key:
        opts.pop("integration", None)
        opts.pop("ai", None)
        opts.pop("ai_skills", None)
        save_init_options(project_root, opts)

    name = (integration.config or {}).get("name", key) if integration else key
    console.print(f"\n[green]✓[/green] Integration '{name}' uninstalled")
    if removed:
        console.print(f"  Removed {len(removed)} file(s)")
    if skipped:
        console.print(f"\n[yellow]⚠[/yellow]  {len(skipped)} modified file(s) were preserved:")
        for path in skipped:
            rel = path.relative_to(project_root) if path.is_absolute() else path
            console.print(f"    {rel}")


@integration_app.command("switch")
def integration_switch(
    target: str = typer.Argument(help="Integration key to switch to"),
    script: str | None = typer.Option(None, "--script", help="Script type: sh or ps (default: from init-options.json or platform default)"),
    force: bool = typer.Option(False, "--force", help="Force removal of modified files during uninstall"),
    integration_options: str | None = typer.Option(None, "--integration-options", help='Options for the target integration'),
):
    """Switch from the current integration to a different one."""
    from .integrations import INTEGRATION_REGISTRY, get_integration
    from .integrations.manifest import IntegrationManifest

    project_root = Path.cwd()

    _require_spec_kit_plus_project(project_root)

    target_integration = get_integration(target)
    if target_integration is None:
        console.print(f"[red]Error:[/red] Unknown integration '{target}'")
        available = ", ".join(sorted(INTEGRATION_REGISTRY.keys()))
        console.print(f"Available integrations: {available}")
        raise typer.Exit(1)

    current = _read_integration_json(project_root)
    installed_key = current.get("integration")

    if installed_key == target:
        console.print(f"[yellow]Integration '{target}' is already installed. Nothing to switch.[/yellow]")
        raise typer.Exit(0)

    selected_script = _resolve_script_type(project_root, script)

    # Phase 1: Uninstall current integration (if any)
    if installed_key:
        current_integration = get_integration(installed_key)
        manifest_path = project_root / ".specify" / "integrations" / f"{installed_key}.manifest.json"

        if current_integration and manifest_path.exists():
            console.print(f"Uninstalling current integration: [cyan]{installed_key}[/cyan]")
            try:
                old_manifest = IntegrationManifest.load(installed_key, project_root)
            except (ValueError, FileNotFoundError) as exc:
                console.print(f"[red]Error:[/red] Could not read integration manifest for '{installed_key}': {manifest_path}")
                console.print(f"[dim]{exc}[/dim]")
                console.print(
                    f"To recover, delete the unreadable manifest at {manifest_path}, "
                    f"run [cyan]specify integration uninstall {installed_key}[/cyan], then retry."
                )
                raise typer.Exit(1)
            removed, skipped = current_integration.uninstall(project_root, old_manifest, force=force)
            if removed:
                console.print(f"  Removed {len(removed)} file(s)")
            if skipped:
                console.print(f"  [yellow]⚠[/yellow]  {len(skipped)} modified file(s) preserved")
        elif not current_integration and manifest_path.exists():
            # Integration removed from registry but manifest exists — use manifest-only uninstall
            console.print(f"Uninstalling unknown integration '{installed_key}' via manifest")
            try:
                old_manifest = IntegrationManifest.load(installed_key, project_root)
                removed, skipped = old_manifest.uninstall(project_root, force=force)
                if removed:
                    console.print(f"  Removed {len(removed)} file(s)")
                if skipped:
                    console.print(f"  [yellow]⚠[/yellow]  {len(skipped)} modified file(s) preserved")
            except (ValueError, FileNotFoundError) as exc:
                console.print(f"[yellow]Warning:[/yellow] Could not read manifest for '{installed_key}': {exc}")
        else:
            console.print(f"[red]Error:[/red] Integration '{installed_key}' is installed but has no manifest.")
            console.print(
                f"Run [cyan]specify integration uninstall {installed_key}[/cyan] to clear metadata, "
                f"then retry [cyan]specify integration switch {target}[/cyan]."
            )
            raise typer.Exit(1)

        # Clear metadata so a failed Phase 2 doesn't leave stale references
        _remove_integration_json(project_root)
        opts = load_init_options(project_root)
        opts.pop("integration", None)
        opts.pop("ai", None)
        opts.pop("ai_skills", None)
        save_init_options(project_root, opts)

    # Ensure shared infrastructure is present (safe to run unconditionally;
    # _install_shared_infra merges missing files without overwriting).
    _install_shared_infra(project_root, selected_script)
    if os.name != "nt":
        ensure_executable_scripts(project_root)

    # Phase 2: Install target integration
    console.print(f"Installing integration: [cyan]{target}[/cyan]")
    manifest = IntegrationManifest(
        target_integration.key, project_root, version=get_speckit_version()
    )

    parsed_options: dict[str, Any] | None = None
    if integration_options:
        parsed_options = _parse_integration_options(target_integration, integration_options)

    try:
        target_integration.setup(
            project_root, manifest,
            parsed_options=parsed_options,
            script_type=selected_script,
            raw_options=integration_options,
        )
        _install_codex_team_assets_if_needed(
            project_root,
            manifest,
            target_integration.key,
        )
        _bootstrap_integration_context_file(
            project_root,
            target_integration,
            manifest,
        )
        manifest.save()
        _write_integration_json(project_root, target_integration.key, selected_script)
        _update_init_options_for_integration(project_root, target_integration, script_type=selected_script)

    except Exception as e:
        # Attempt rollback of any files written by setup
        try:
            target_integration.teardown(project_root, manifest, force=True)
        except Exception as rollback_err:
            # Suppress so the original setup error remains the primary failure
            console.print(f"[yellow]Warning:[/yellow] Failed to roll back integration '{target}': {rollback_err}")
        _remove_integration_json(project_root)
        console.print(f"[red]Error:[/red] Failed to install integration '{target}': {e}")
        raise typer.Exit(1)

    name = (target_integration.config or {}).get("name", target)
    console.print(f"\n[green]✓[/green] Switched to integration '{name}'")


@integration_app.command("repair")
def integration_repair(
    script: str | None = typer.Option(None, "--script", help="Script type: sh or ps (default: from init-options.json or platform default)"),
):
    """Refresh shared/runtime integration assets for the current project."""
    project_root = Path.cwd()

    _require_spec_kit_plus_project(project_root)

    selected_script = _resolve_script_type(project_root, script)
    active_key, tracked_files = _repair_active_integration_runtime_assets(
        project_root,
        script_type=selected_script,
    )

    if active_key:
        console.print(
            f"[green]✓[/green] Refreshed shared assets and repaired runtime-managed surfaces for integration "
            f"[cyan]{active_key}[/cyan]."
        )
        console.print(f"[dim]Tracked files refreshed: {tracked_files}[/dim]")
    else:
        console.print("[green]✓[/green] Refreshed shared project assets. No active integration was installed.")


# ===== Preset Commands =====


@preset_app.command("list")
def preset_list():
    """List installed presets."""
    from .presets import PresetManager

    project_root = Path.cwd()

    _require_spec_kit_plus_project(project_root)

    manager = PresetManager(project_root)
    installed = manager.list_installed()

    if not installed:
        console.print("[yellow]No presets installed.[/yellow]")
        console.print("\nInstall a preset with:")
        console.print("  [cyan]specify preset add <pack-name>[/cyan]")
        return

    console.print("\n[bold cyan]Installed Presets:[/bold cyan]\n")
    for pack in installed:
        status = "[green]enabled[/green]" if pack.get("enabled", True) else "[red]disabled[/red]"
        pri = pack.get('priority', 10)
        console.print(f"  [bold]{pack['name']}[/bold] ({pack['id']}) v{pack['version']} — {status} — priority {pri}")
        console.print(f"    {pack['description']}")
        if pack.get("tags"):
            tags_str = ", ".join(pack["tags"])
            console.print(f"    [dim]Tags: {tags_str}[/dim]")
        console.print(f"    [dim]Templates: {pack['template_count']}[/dim]")
        console.print()


@preset_app.command("add")
def preset_add(
    pack_id: str = typer.Argument(None, help="Preset ID to install from catalog"),
    from_url: str = typer.Option(None, "--from", help="Install from a URL (ZIP file)"),
    dev: str = typer.Option(None, "--dev", help="Install from local directory (development mode)"),
    priority: int = typer.Option(10, "--priority", help="Resolution priority (lower = higher precedence, default 10)"),
):
    """Install a preset."""
    from .presets import (
        PresetManager,
        PresetCatalog,
        PresetError,
        PresetValidationError,
        PresetCompatibilityError,
    )

    project_root = Path.cwd()

    specify_dir = _require_spec_kit_plus_project(project_root)

    # Validate priority
    if priority < 1:
        console.print("[red]Error:[/red] Priority must be a positive integer (1 or higher)")
        raise typer.Exit(1)

    manager = PresetManager(project_root)
    speckit_version = get_speckit_version()

    try:
        if dev:
            dev_path = Path(dev).resolve()
            if not dev_path.exists():
                console.print(f"[red]Error:[/red] Directory not found: {dev}")
                raise typer.Exit(1)

            console.print(f"Installing preset from [cyan]{dev_path}[/cyan]...")
            manifest = manager.install_from_directory(dev_path, speckit_version, priority)
            console.print(f"[green]✓[/green] Preset '{manifest.name}' v{manifest.version} installed (priority {priority})")

        elif from_url:
            # Validate URL scheme before downloading
            from urllib.parse import urlparse as _urlparse
            _parsed = _urlparse(from_url)
            _is_localhost = _parsed.hostname in ("localhost", "127.0.0.1", "::1")
            if _parsed.scheme != "https" and not (_parsed.scheme == "http" and _is_localhost):
                console.print(f"[red]Error:[/red] URL must use HTTPS (got {_parsed.scheme}://). HTTP is only allowed for localhost.")
                raise typer.Exit(1)

            console.print(f"Installing preset from [cyan]{from_url}[/cyan]...")
            import urllib.request
            import urllib.error
            import tempfile

            with tempfile.TemporaryDirectory() as tmpdir:
                zip_path = Path(tmpdir) / "preset.zip"
                try:
                    with urllib.request.urlopen(from_url, timeout=60) as response:
                        zip_path.write_bytes(response.read())
                except urllib.error.URLError as e:
                    console.print(f"[red]Error:[/red] Failed to download: {e}")
                    raise typer.Exit(1)

                manifest = manager.install_from_zip(zip_path, speckit_version, priority)

            console.print(f"[green]✓[/green] Preset '{manifest.name}' v{manifest.version} installed (priority {priority})")

        elif pack_id:
            catalog = PresetCatalog(project_root)
            pack_info = catalog.get_pack_info(pack_id)

            if not pack_info:
                console.print(f"[red]Error:[/red] Preset '{pack_id}' not found in catalog")
                raise typer.Exit(1)

            if not pack_info.get("_install_allowed", True):
                catalog_name = pack_info.get("_catalog_name", "unknown")
                console.print(f"[red]Error:[/red] Preset '{pack_id}' is from the '{catalog_name}' catalog which is discovery-only (install not allowed).")
                console.print("Add the catalog with --install-allowed or install from the preset's repository directly with --from.")
                raise typer.Exit(1)

            console.print(f"Installing preset [cyan]{pack_info.get('name', pack_id)}[/cyan]...")

            try:
                zip_path = catalog.download_pack(pack_id)
                manifest = manager.install_from_zip(zip_path, speckit_version, priority)
                console.print(f"[green]✓[/green] Preset '{manifest.name}' v{manifest.version} installed (priority {priority})")
            finally:
                if 'zip_path' in locals() and zip_path.exists():
                    zip_path.unlink(missing_ok=True)
        else:
            console.print("[red]Error:[/red] Specify a preset ID, --from URL, or --dev path")
            raise typer.Exit(1)

    except PresetCompatibilityError as e:
        console.print(f"[red]Compatibility Error:[/red] {e}")
        raise typer.Exit(1)
    except PresetValidationError as e:
        console.print(f"[red]Validation Error:[/red] {e}")
        raise typer.Exit(1)
    except PresetError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)


@preset_app.command("remove")
def preset_remove(
    pack_id: str = typer.Argument(..., help="Preset ID to remove"),
):
    """Remove an installed preset."""
    from .presets import PresetManager

    project_root = Path.cwd()

    _require_spec_kit_plus_project(project_root)

    manager = PresetManager(project_root)

    if not manager.registry.is_installed(pack_id):
        console.print(f"[red]Error:[/red] Preset '{pack_id}' is not installed")
        raise typer.Exit(1)

    if manager.remove(pack_id):
        console.print(f"[green]✓[/green] Preset '{pack_id}' removed successfully")
    else:
        console.print(f"[red]Error:[/red] Failed to remove preset '{pack_id}'")
        raise typer.Exit(1)


@preset_app.command("search")
def preset_search(
    query: str = typer.Argument(None, help="Search query"),
    tag: str = typer.Option(None, "--tag", help="Filter by tag"),
    author: str = typer.Option(None, "--author", help="Filter by author"),
):
    """Search for presets in the catalog."""
    from .presets import PresetCatalog, PresetError

    project_root = Path.cwd()

    _require_spec_kit_plus_project(project_root)

    catalog = PresetCatalog(project_root)

    try:
        results = catalog.search(query=query, tag=tag, author=author)
    except PresetError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    if not results:
        console.print("[yellow]No presets found matching your criteria.[/yellow]")
        return

    console.print(f"\n[bold cyan]Presets ({len(results)} found):[/bold cyan]\n")
    for pack in results:
        console.print(f"  [bold]{pack.get('name', pack['id'])}[/bold] ({pack['id']}) v{pack.get('version', '?')}")
        console.print(f"    {pack.get('description', '')}")
        if pack.get("tags"):
            tags_str = ", ".join(pack["tags"])
            console.print(f"    [dim]Tags: {tags_str}[/dim]")
        console.print()


@preset_app.command("resolve")
def preset_resolve(
    template_name: str = typer.Argument(..., help="Template name to resolve (e.g., spec-template)"),
):
    """Show which template will be resolved for a given name."""
    from .presets import PresetResolver

    project_root = Path.cwd()

    _require_spec_kit_plus_project(project_root)

    resolver = PresetResolver(project_root)
    result = resolver.resolve_with_source(template_name)

    if result:
        console.print(f"  [bold]{template_name}[/bold]: {result['path']}")
        console.print(f"    [dim](from: {result['source']})[/dim]")
    else:
        console.print(f"  [yellow]{template_name}[/yellow]: not found")
        console.print("    [dim]No template with this name exists in the resolution stack[/dim]")


@preset_app.command("info")
def preset_info(
    pack_id: str = typer.Argument(..., help="Preset ID to get info about"),
):
    """Show detailed information about a preset."""
    from .extensions import normalize_priority
    from .presets import PresetCatalog, PresetManager, PresetError

    project_root = Path.cwd()

    _require_spec_kit_plus_project(project_root)

    # Check if installed locally first
    manager = PresetManager(project_root)
    local_pack = manager.get_pack(pack_id)

    if local_pack:
        console.print(f"\n[bold cyan]Preset: {local_pack.name}[/bold cyan]\n")
        console.print(f"  ID:          {local_pack.id}")
        console.print(f"  Version:     {local_pack.version}")
        console.print(f"  Description: {local_pack.description}")
        if local_pack.author:
            console.print(f"  Author:      {local_pack.author}")
        if local_pack.tags:
            console.print(f"  Tags:        {', '.join(local_pack.tags)}")
        console.print(f"  Templates:   {len(local_pack.templates)}")
        for tmpl in local_pack.templates:
            console.print(f"    - {tmpl['name']} ({tmpl['type']}): {tmpl.get('description', '')}")
        repo = local_pack.data.get("preset", {}).get("repository")
        if repo:
            console.print(f"  Repository:  {repo}")
        license_val = local_pack.data.get("preset", {}).get("license")
        if license_val:
            console.print(f"  License:     {license_val}")
        console.print("\n  [green]Status: installed[/green]")
        # Get priority from registry
        pack_metadata = manager.registry.get(pack_id)
        priority = normalize_priority(pack_metadata.get("priority") if isinstance(pack_metadata, dict) else None)
        console.print(f"  [dim]Priority:[/dim] {priority}")
        console.print()
        return

    # Fall back to catalog
    catalog = PresetCatalog(project_root)
    try:
        pack_info = catalog.get_pack_info(pack_id)
    except PresetError:
        pack_info = None

    if not pack_info:
        console.print(f"[red]Error:[/red] Preset '{pack_id}' not found (not installed and not in catalog)")
        raise typer.Exit(1)

    console.print(f"\n[bold cyan]Preset: {pack_info.get('name', pack_id)}[/bold cyan]\n")
    console.print(f"  ID:          {pack_info['id']}")
    console.print(f"  Version:     {pack_info.get('version', '?')}")
    console.print(f"  Description: {pack_info.get('description', '')}")
    if pack_info.get("author"):
        console.print(f"  Author:      {pack_info['author']}")
    if pack_info.get("tags"):
        console.print(f"  Tags:        {', '.join(pack_info['tags'])}")
    if pack_info.get("repository"):
        console.print(f"  Repository:  {pack_info['repository']}")
    if pack_info.get("license"):
        console.print(f"  License:     {pack_info['license']}")
    console.print("\n  [yellow]Status: not installed[/yellow]")
    console.print(f"  Install with: [cyan]specify preset add {pack_id}[/cyan]")
    console.print()


@preset_app.command("set-priority")
def preset_set_priority(
    pack_id: str = typer.Argument(help="Preset ID"),
    priority: int = typer.Argument(help="New priority (lower = higher precedence)"),
):
    """Set the resolution priority of an installed preset."""
    from .presets import PresetManager

    project_root = Path.cwd()

    # Check if we're in a spec-kit project
    _require_spec_kit_plus_project(project_root)

    # Validate priority
    if priority < 1:
        console.print("[red]Error:[/red] Priority must be a positive integer (1 or higher)")
        raise typer.Exit(1)

    manager = PresetManager(project_root)

    # Check if preset is installed
    if not manager.registry.is_installed(pack_id):
        console.print(f"[red]Error:[/red] Preset '{pack_id}' is not installed")
        raise typer.Exit(1)

    # Get current metadata
    metadata = manager.registry.get(pack_id)
    if metadata is None or not isinstance(metadata, dict):
        console.print(f"[red]Error:[/red] Preset '{pack_id}' not found in registry (corrupted state)")
        raise typer.Exit(1)

    from .extensions import normalize_priority
    raw_priority = metadata.get("priority")
    # Only skip if the stored value is already a valid int equal to requested priority
    # This ensures corrupted values (e.g., "high") get repaired even when setting to default (10)
    if isinstance(raw_priority, int) and raw_priority == priority:
        console.print(f"[yellow]Preset '{pack_id}' already has priority {priority}[/yellow]")
        raise typer.Exit(0)

    old_priority = normalize_priority(raw_priority)

    # Update priority
    manager.registry.update(pack_id, {"priority": priority})

    console.print(f"[green]✓[/green] Preset '{pack_id}' priority changed: {old_priority} → {priority}")
    console.print("\n[dim]Lower priority = higher precedence in template resolution[/dim]")


@preset_app.command("enable")
def preset_enable(
    pack_id: str = typer.Argument(help="Preset ID to enable"),
):
    """Enable a disabled preset."""
    from .presets import PresetManager

    project_root = Path.cwd()

    # Check if we're in a spec-kit project
    _require_spec_kit_plus_project(project_root)

    manager = PresetManager(project_root)

    # Check if preset is installed
    if not manager.registry.is_installed(pack_id):
        console.print(f"[red]Error:[/red] Preset '{pack_id}' is not installed")
        raise typer.Exit(1)

    # Get current metadata
    metadata = manager.registry.get(pack_id)
    if metadata is None or not isinstance(metadata, dict):
        console.print(f"[red]Error:[/red] Preset '{pack_id}' not found in registry (corrupted state)")
        raise typer.Exit(1)

    if metadata.get("enabled", True):
        console.print(f"[yellow]Preset '{pack_id}' is already enabled[/yellow]")
        raise typer.Exit(0)

    # Enable the preset
    manager.registry.update(pack_id, {"enabled": True})

    console.print(f"[green]✓[/green] Preset '{pack_id}' enabled")
    console.print("\nTemplates from this preset will now be included in resolution.")
    console.print("[dim]Note: Previously registered commands/skills remain active.[/dim]")


@preset_app.command("disable")
def preset_disable(
    pack_id: str = typer.Argument(help="Preset ID to disable"),
):
    """Disable a preset without removing it."""
    from .presets import PresetManager

    project_root = Path.cwd()

    # Check if we're in a spec-kit project
    _require_spec_kit_plus_project(project_root)

    manager = PresetManager(project_root)

    # Check if preset is installed
    if not manager.registry.is_installed(pack_id):
        console.print(f"[red]Error:[/red] Preset '{pack_id}' is not installed")
        raise typer.Exit(1)

    # Get current metadata
    metadata = manager.registry.get(pack_id)
    if metadata is None or not isinstance(metadata, dict):
        console.print(f"[red]Error:[/red] Preset '{pack_id}' not found in registry (corrupted state)")
        raise typer.Exit(1)

    if not metadata.get("enabled", True):
        console.print(f"[yellow]Preset '{pack_id}' is already disabled[/yellow]")
        raise typer.Exit(0)

    # Disable the preset
    manager.registry.update(pack_id, {"enabled": False})

    console.print(f"[green]✓[/green] Preset '{pack_id}' disabled")
    console.print("\nTemplates from this preset will be skipped during resolution.")
    console.print("[dim]Note: Previously registered commands/skills remain active until preset removal.[/dim]")
    console.print(f"To re-enable: specify preset enable {pack_id}")


# ===== Preset Catalog Commands =====


@preset_catalog_app.command("list")
def preset_catalog_list():
    """List all active preset catalogs."""
    from .presets import PresetCatalog, PresetValidationError

    project_root = Path.cwd()

    _require_spec_kit_plus_project(project_root)

    catalog = PresetCatalog(project_root)

    try:
        active_catalogs = catalog.get_active_catalogs()
    except PresetValidationError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    console.print("\n[bold cyan]Active Preset Catalogs:[/bold cyan]\n")
    for entry in active_catalogs:
        install_str = (
            "[green]install allowed[/green]"
            if entry.install_allowed
            else "[yellow]discovery only[/yellow]"
        )
        console.print(f"  [bold]{entry.name}[/bold] (priority {entry.priority})")
        if entry.description:
            console.print(f"     {entry.description}")
        console.print(f"     URL: {entry.url}")
        console.print(f"     Install: {install_str}")
        console.print()

    config_path = project_root / ".specify" / "preset-catalogs.yml"
    user_config_path = Path.home() / ".specify" / "preset-catalogs.yml"
    if os.environ.get("SPECKIT_PRESET_CATALOG_URL"):
        console.print("[dim]Catalog configured via SPECKIT_PRESET_CATALOG_URL environment variable.[/dim]")
    else:
        try:
            proj_loaded = config_path.exists() and catalog._load_catalog_config(config_path) is not None
        except PresetValidationError:
            proj_loaded = False
        if proj_loaded:
            console.print(f"[dim]Config: {config_path.relative_to(project_root)}[/dim]")
        else:
            try:
                user_loaded = user_config_path.exists() and catalog._load_catalog_config(user_config_path) is not None
            except PresetValidationError:
                user_loaded = False
            if user_loaded:
                console.print("[dim]Config: ~/.specify/preset-catalogs.yml[/dim]")
            else:
                console.print("[dim]Using built-in default catalog stack.[/dim]")
                console.print(
                    "[dim]Add .specify/preset-catalogs.yml to customize.[/dim]"
                )


@preset_catalog_app.command("add")
def preset_catalog_add(
    url: str = typer.Argument(help="Catalog URL (must use HTTPS)"),
    name: str = typer.Option(..., "--name", help="Catalog name"),
    priority: int = typer.Option(10, "--priority", help="Priority (lower = higher priority)"),
    install_allowed: bool = typer.Option(
        False, "--install-allowed/--no-install-allowed",
        help="Allow presets from this catalog to be installed",
    ),
    description: str = typer.Option("", "--description", help="Description of the catalog"),
):
    """Add a catalog to .specify/preset-catalogs.yml."""
    from .presets import PresetCatalog, PresetValidationError

    project_root = Path.cwd()

    specify_dir = _require_spec_kit_plus_project(project_root)

    # Validate URL
    tmp_catalog = PresetCatalog(project_root)
    try:
        tmp_catalog._validate_catalog_url(url)
    except PresetValidationError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    config_path = specify_dir / "preset-catalogs.yml"

    # Load existing config
    if config_path.exists():
        try:
            config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        except Exception as e:
            console.print(f"[red]Error:[/red] Failed to read {config_path}: {e}")
            raise typer.Exit(1)
    else:
        config = {}

    catalogs = config.get("catalogs", [])
    if not isinstance(catalogs, list):
        console.print("[red]Error:[/red] Invalid catalog config: 'catalogs' must be a list.")
        raise typer.Exit(1)

    # Check for duplicate name
    for existing in catalogs:
        if isinstance(existing, dict) and existing.get("name") == name:
            console.print(f"[yellow]Warning:[/yellow] A catalog named '{name}' already exists.")
            console.print("Use 'specify preset catalog remove' first, or choose a different name.")
            raise typer.Exit(1)

    catalogs.append({
        "name": name,
        "url": url,
        "priority": priority,
        "install_allowed": install_allowed,
        "description": description,
    })

    config["catalogs"] = catalogs
    config_path.write_text(yaml.dump(config, default_flow_style=False, sort_keys=False, allow_unicode=True), encoding="utf-8")

    install_label = "install allowed" if install_allowed else "discovery only"
    console.print(f"\n[green]✓[/green] Added catalog '[bold]{name}[/bold]' ({install_label})")
    console.print(f"  URL: {url}")
    console.print(f"  Priority: {priority}")
    console.print(f"\nConfig saved to {config_path.relative_to(project_root)}")


@preset_catalog_app.command("remove")
def preset_catalog_remove(
    name: str = typer.Argument(help="Catalog name to remove"),
):
    """Remove a catalog from .specify/preset-catalogs.yml."""
    project_root = Path.cwd()

    specify_dir = _require_spec_kit_plus_project(project_root)

    config_path = specify_dir / "preset-catalogs.yml"
    if not config_path.exists():
        console.print("[red]Error:[/red] No preset catalog config found. Nothing to remove.")
        raise typer.Exit(1)

    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception:
        console.print("[red]Error:[/red] Failed to read preset catalog config.")
        raise typer.Exit(1)

    catalogs = config.get("catalogs", [])
    if not isinstance(catalogs, list):
        console.print("[red]Error:[/red] Invalid catalog config: 'catalogs' must be a list.")
        raise typer.Exit(1)
    original_count = len(catalogs)
    catalogs = [c for c in catalogs if isinstance(c, dict) and c.get("name") != name]

    if len(catalogs) == original_count:
        console.print(f"[red]Error:[/red] Catalog '{name}' not found.")
        raise typer.Exit(1)

    config["catalogs"] = catalogs
    config_path.write_text(yaml.dump(config, default_flow_style=False, sort_keys=False, allow_unicode=True), encoding="utf-8")

    console.print(f"[green]✓[/green] Removed catalog '{name}'")
    if not catalogs:
        console.print("\n[dim]No catalogs remain in config. Built-in defaults will be used.[/dim]")


# ===== Extension Commands =====


def _resolve_installed_extension(
    argument: str,
    installed_extensions: list,
    command_name: str = "command",
    allow_not_found: bool = False,
) -> tuple[Optional[str], Optional[str]]:
    """Resolve an extension argument (ID or display name) to an installed extension.

    Args:
        argument: Extension ID or display name provided by user
        installed_extensions: List of installed extension dicts from manager.list_installed()
        command_name: Name of the command for error messages (e.g., "enable", "disable")
        allow_not_found: If True, return (None, None) when not found instead of raising

    Returns:
        Tuple of (extension_id, display_name), or (None, None) if allow_not_found=True and not found

    Raises:
        typer.Exit: If extension not found (and allow_not_found=False) or name is ambiguous
    """
    from rich.table import Table

    # First, try exact ID match
    for ext in installed_extensions:
        if ext["id"] == argument:
            return (ext["id"], ext["name"])

    # If not found by ID, try display name match
    name_matches = [ext for ext in installed_extensions if ext["name"].lower() == argument.lower()]

    if len(name_matches) == 1:
        # Unique display-name match
        return (name_matches[0]["id"], name_matches[0]["name"])
    elif len(name_matches) > 1:
        # Ambiguous display-name match
        console.print(
            f"[red]Error:[/red] Extension name '{argument}' is ambiguous. "
            "Multiple installed extensions share this name:"
        )
        table = Table(title="Matching extensions")
        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="white")
        table.add_column("Version", style="green")
        for ext in name_matches:
            table.add_row(ext.get("id", ""), ext.get("name", ""), str(ext.get("version", "")))
        console.print(table)
        console.print("\nPlease rerun using the extension ID:")
        console.print(f"  [bold]specify extension {command_name} <extension-id>[/bold]")
        raise typer.Exit(1)
    else:
        # No match by ID or display name
        if allow_not_found:
            return (None, None)
        console.print(f"[red]Error:[/red] Extension '{argument}' is not installed")
        raise typer.Exit(1)


def _resolve_catalog_extension(
    argument: str,
    catalog,
    command_name: str = "info",
) -> tuple[Optional[dict], Optional[Exception]]:
    """Resolve an extension argument (ID or display name) from the catalog.

    Args:
        argument: Extension ID or display name provided by user
        catalog: ExtensionCatalog instance
        command_name: Name of the command for error messages

    Returns:
        Tuple of (extension_info, catalog_error)
        - If found: (ext_info_dict, None)
        - If catalog error: (None, error)
        - If not found: (None, None)
    """
    from rich.table import Table
    from .extensions import ExtensionError

    try:
        # First try by ID
        ext_info = catalog.get_extension_info(argument)
        if ext_info:
            return (ext_info, None)

        # Try by display name - search using argument as query, then filter for exact match
        search_results = catalog.search(query=argument)
        name_matches = [ext for ext in search_results if ext["name"].lower() == argument.lower()]

        if len(name_matches) == 1:
            return (name_matches[0], None)
        elif len(name_matches) > 1:
            # Ambiguous display-name match in catalog
            console.print(
                f"[red]Error:[/red] Extension name '{argument}' is ambiguous. "
                "Multiple catalog extensions share this name:"
            )
            table = Table(title="Matching extensions")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Name", style="white")
            table.add_column("Version", style="green")
            table.add_column("Catalog", style="dim")
            for ext in name_matches:
                table.add_row(
                    ext.get("id", ""),
                    ext.get("name", ""),
                    str(ext.get("version", "")),
                    ext.get("_catalog_name", ""),
                )
            console.print(table)
            console.print("\nPlease rerun using the extension ID:")
            console.print(f"  [bold]specify extension {command_name} <extension-id>[/bold]")
            raise typer.Exit(1)

        # Not found
        return (None, None)

    except ExtensionError as e:
        return (None, e)


@extension_app.command("list")
def extension_list(
    available: bool = typer.Option(False, "--available", help="Show available extensions from catalog"),
    all_extensions: bool = typer.Option(False, "--all", help="Show both installed and available"),
):
    """List installed extensions."""
    from .extensions import ExtensionManager

    project_root = Path.cwd()

    # Check if we're in a spec-kit project
    _require_spec_kit_plus_project(project_root)

    manager = ExtensionManager(project_root)
    installed = manager.list_installed()

    if not installed and not (available or all_extensions):
        console.print("[yellow]No extensions installed.[/yellow]")
        console.print("\nInstall an extension with:")
        console.print("  specify extension add <extension-name>")
        return

    if installed:
        console.print("\n[bold cyan]Installed Extensions:[/bold cyan]\n")

        for ext in installed:
            status_icon = "✓" if ext["enabled"] else "✗"
            status_color = "green" if ext["enabled"] else "red"

            console.print(f"  [{status_color}]{status_icon}[/{status_color}] [bold]{ext['name']}[/bold] (v{ext['version']})")
            console.print(f"     [dim]{ext['id']}[/dim]")
            console.print(f"     {ext['description']}")
            console.print(f"     Commands: {ext['command_count']} | Hooks: {ext['hook_count']} | Priority: {ext['priority']} | Status: {'Enabled' if ext['enabled'] else 'Disabled'}")
            console.print()

    if available or all_extensions:
        console.print("\nInstall an extension:")
        console.print("  [cyan]specify extension add <name>[/cyan]")


@catalog_app.command("list")
def catalog_list():
    """List all active extension catalogs."""
    from .extensions import ExtensionCatalog, ValidationError

    project_root = Path.cwd()

    _require_spec_kit_plus_project(project_root)

    catalog = ExtensionCatalog(project_root)

    try:
        active_catalogs = catalog.get_active_catalogs()
    except ValidationError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    console.print("\n[bold cyan]Active Extension Catalogs:[/bold cyan]\n")
    for entry in active_catalogs:
        install_str = (
            "[green]install allowed[/green]"
            if entry.install_allowed
            else "[yellow]discovery only[/yellow]"
        )
        console.print(f"  [bold]{entry.name}[/bold] (priority {entry.priority})")
        if entry.description:
            console.print(f"     {entry.description}")
        console.print(f"     URL: {entry.url}")
        console.print(f"     Install: {install_str}")
        console.print()

    config_path = project_root / ".specify" / "extension-catalogs.yml"
    user_config_path = Path.home() / ".specify" / "extension-catalogs.yml"
    if os.environ.get("SPECKIT_CATALOG_URL"):
        console.print("[dim]Catalog configured via SPECKIT_CATALOG_URL environment variable.[/dim]")
    else:
        try:
            proj_loaded = config_path.exists() and catalog._load_catalog_config(config_path) is not None
        except ValidationError:
            proj_loaded = False
        if proj_loaded:
            console.print(f"[dim]Config: {config_path.relative_to(project_root)}[/dim]")
        else:
            try:
                user_loaded = user_config_path.exists() and catalog._load_catalog_config(user_config_path) is not None
            except ValidationError:
                user_loaded = False
            if user_loaded:
                console.print("[dim]Config: ~/.specify/extension-catalogs.yml[/dim]")
            else:
                console.print("[dim]Using built-in default catalog stack.[/dim]")
                console.print(
                    "[dim]Add .specify/extension-catalogs.yml to customize.[/dim]"
                )


@catalog_app.command("add")
def catalog_add(
    url: str = typer.Argument(help="Catalog URL (must use HTTPS)"),
    name: str = typer.Option(..., "--name", help="Catalog name"),
    priority: int = typer.Option(10, "--priority", help="Priority (lower = higher priority)"),
    install_allowed: bool = typer.Option(
        False, "--install-allowed/--no-install-allowed",
        help="Allow extensions from this catalog to be installed",
    ),
    description: str = typer.Option("", "--description", help="Description of the catalog"),
):
    """Add a catalog to .specify/extension-catalogs.yml."""
    from .extensions import ExtensionCatalog, ValidationError

    project_root = Path.cwd()

    specify_dir = _require_spec_kit_plus_project(project_root)

    # Validate URL
    tmp_catalog = ExtensionCatalog(project_root)
    try:
        tmp_catalog._validate_catalog_url(url)
    except ValidationError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    config_path = specify_dir / "extension-catalogs.yml"

    # Load existing config
    if config_path.exists():
        try:
            config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        except Exception as e:
            console.print(f"[red]Error:[/red] Failed to read {config_path}: {e}")
            raise typer.Exit(1)
    else:
        config = {}

    catalogs = config.get("catalogs", [])
    if not isinstance(catalogs, list):
        console.print("[red]Error:[/red] Invalid catalog config: 'catalogs' must be a list.")
        raise typer.Exit(1)

    # Check for duplicate name
    for existing in catalogs:
        if isinstance(existing, dict) and existing.get("name") == name:
            console.print(f"[yellow]Warning:[/yellow] A catalog named '{name}' already exists.")
            console.print("Use 'specify extension catalog remove' first, or choose a different name.")
            raise typer.Exit(1)

    catalogs.append({
        "name": name,
        "url": url,
        "priority": priority,
        "install_allowed": install_allowed,
        "description": description,
    })

    config["catalogs"] = catalogs
    config_path.write_text(yaml.dump(config, default_flow_style=False, sort_keys=False, allow_unicode=True), encoding="utf-8")

    install_label = "install allowed" if install_allowed else "discovery only"
    console.print(f"\n[green]✓[/green] Added catalog '[bold]{name}[/bold]' ({install_label})")
    console.print(f"  URL: {url}")
    console.print(f"  Priority: {priority}")
    console.print(f"\nConfig saved to {config_path.relative_to(project_root)}")


@catalog_app.command("remove")
def catalog_remove(
    name: str = typer.Argument(help="Catalog name to remove"),
):
    """Remove a catalog from .specify/extension-catalogs.yml."""
    project_root = Path.cwd()

    specify_dir = _require_spec_kit_plus_project(project_root)

    config_path = specify_dir / "extension-catalogs.yml"
    if not config_path.exists():
        console.print("[red]Error:[/red] No catalog config found. Nothing to remove.")
        raise typer.Exit(1)

    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except Exception:
        console.print("[red]Error:[/red] Failed to read catalog config.")
        raise typer.Exit(1)

    catalogs = config.get("catalogs", [])
    if not isinstance(catalogs, list):
        console.print("[red]Error:[/red] Invalid catalog config: 'catalogs' must be a list.")
        raise typer.Exit(1)
    original_count = len(catalogs)
    catalogs = [c for c in catalogs if isinstance(c, dict) and c.get("name") != name]

    if len(catalogs) == original_count:
        console.print(f"[red]Error:[/red] Catalog '{name}' not found.")
        raise typer.Exit(1)

    config["catalogs"] = catalogs
    config_path.write_text(yaml.dump(config, default_flow_style=False, sort_keys=False, allow_unicode=True), encoding="utf-8")

    console.print(f"[green]✓[/green] Removed catalog '{name}'")
    if not catalogs:
        console.print("\n[dim]No catalogs remain in config. Built-in defaults will be used.[/dim]")


@extension_app.command("add")
def extension_add(
    extension: str = typer.Argument(help="Extension name or path"),
    dev: bool = typer.Option(False, "--dev", help="Install from local directory"),
    from_url: Optional[str] = typer.Option(None, "--from", help="Install from custom URL"),
    priority: int = typer.Option(10, "--priority", help="Resolution priority (lower = higher precedence, default 10)"),
):
    """Install an extension."""
    from .extensions import ExtensionManager, ExtensionCatalog, ExtensionError, ValidationError, CompatibilityError

    project_root = Path.cwd()

    # Check if we're in a spec-kit project
    _require_spec_kit_plus_project(project_root)

    # Validate priority
    if priority < 1:
        console.print("[red]Error:[/red] Priority must be a positive integer (1 or higher)")
        raise typer.Exit(1)

    manager = ExtensionManager(project_root)
    speckit_version = get_speckit_version()

    try:
        with console.status(f"[cyan]Installing extension: {extension}[/cyan]"):
            if dev:
                # Install from local directory
                source_path = Path(extension).expanduser().resolve()
                if not source_path.exists():
                    console.print(f"[red]Error:[/red] Directory not found: {source_path}")
                    raise typer.Exit(1)

                if not (source_path / "extension.yml").exists():
                    console.print(f"[red]Error:[/red] No extension.yml found in {source_path}")
                    raise typer.Exit(1)

                manifest = manager.install_from_directory(source_path, speckit_version, priority=priority)

            elif from_url:
                # Install from URL (ZIP file)
                import urllib.request
                import urllib.error
                from urllib.parse import urlparse

                # Validate URL
                parsed = urlparse(from_url)
                is_localhost = parsed.hostname in ("localhost", "127.0.0.1", "::1")

                if parsed.scheme != "https" and not (parsed.scheme == "http" and is_localhost):
                    console.print("[red]Error:[/red] URL must use HTTPS for security.")
                    console.print("HTTP is only allowed for localhost URLs.")
                    raise typer.Exit(1)

                # Warn about untrusted sources
                console.print("[yellow]Warning:[/yellow] Installing from external URL.")
                console.print("Only install extensions from sources you trust.\n")
                console.print(f"Downloading from {from_url}...")

                # Download ZIP to temp location
                download_dir = project_root / ".specify" / "extensions" / ".cache" / "downloads"
                download_dir.mkdir(parents=True, exist_ok=True)
                zip_path = download_dir / f"{extension}-url-download.zip"

                try:
                    with urllib.request.urlopen(from_url, timeout=60) as response:
                        zip_data = response.read()
                    zip_path.write_bytes(zip_data)

                    # Install from downloaded ZIP
                    manifest = manager.install_from_zip(zip_path, speckit_version, priority=priority)
                except urllib.error.URLError as e:
                    console.print(f"[red]Error:[/red] Failed to download from {from_url}: {e}")
                    raise typer.Exit(1)
                finally:
                    # Clean up downloaded ZIP
                    if zip_path.exists():
                        zip_path.unlink()

            else:
                # Prefer extensions bundled with this Spec Kit installation before catalog lookup.
                manifest = _install_bundled_extension(
                    project_root,
                    extension,
                    priority=priority,
                )
                if manifest is None:
                    # Install from catalog
                    catalog = ExtensionCatalog(project_root)

                    # Check if extension exists in catalog (supports both ID and display name)
                    ext_info, catalog_error = _resolve_catalog_extension(extension, catalog, "add")
                    if catalog_error:
                        console.print(f"[red]Error:[/red] Could not query extension catalog: {catalog_error}")
                        raise typer.Exit(1)
                    if not ext_info:
                        console.print(f"[red]Error:[/red] Extension '{extension}' not found in catalog")
                        console.print("\nSearch available extensions:")
                        console.print("  specify extension search")
                        raise typer.Exit(1)

                    # Enforce install_allowed policy
                    if not ext_info.get("_install_allowed", True):
                        catalog_name = ext_info.get("_catalog_name", "community")
                        console.print(
                            f"[red]Error:[/red] '{extension}' is available in the "
                            f"'{catalog_name}' catalog but installation is not allowed from that catalog."
                        )
                        console.print(
                            f"\nTo enable installation, add '{extension}' to an approved catalog "
                            f"(install_allowed: true) in .specify/extension-catalogs.yml."
                        )
                        raise typer.Exit(1)

                    # Download extension ZIP (use resolved ID, not original argument which may be display name)
                    extension_id = ext_info['id']
                    console.print(f"Downloading {ext_info['name']} v{ext_info.get('version', 'unknown')}...")
                    zip_path = catalog.download_extension(extension_id)

                    try:
                        # Install from downloaded ZIP
                        manifest = manager.install_from_zip(zip_path, speckit_version, priority=priority)
                    finally:
                        # Clean up downloaded ZIP
                        if zip_path.exists():
                            zip_path.unlink()

        console.print("\n[green]✓[/green] Extension installed successfully!")
        console.print(f"\n[bold]{manifest.name}[/bold] (v{manifest.version})")
        console.print(f"  {manifest.description}")
        console.print("\n[bold cyan]Provided commands:[/bold cyan]")
        for cmd in manifest.commands:
            console.print(f"  • {cmd['name']} - {cmd.get('description', '')}")

        # Report agent skills registration
        reg_meta = manager.registry.get(manifest.id)
        reg_skills = reg_meta.get("registered_skills", []) if reg_meta else []
        # Normalize to guard against corrupted registry entries
        if not isinstance(reg_skills, list):
            reg_skills = []
        if reg_skills:
            console.print(f"\n[green]✓[/green] {len(reg_skills)} agent skill(s) auto-registered")

        console.print("\n[yellow]⚠[/yellow]  Configuration may be required")
        console.print(f"   Check: .specify/extensions/{manifest.id}/")

    except ValidationError as e:
        console.print(f"\n[red]Validation Error:[/red] {e}")
        raise typer.Exit(1)
    except CompatibilityError as e:
        console.print(f"\n[red]Compatibility Error:[/red] {e}")
        raise typer.Exit(1)
    except ExtensionError as e:
        console.print(f"\n[red]Error:[/red] {e}")
        raise typer.Exit(1)


@extension_app.command("remove")
def extension_remove(
    extension: str = typer.Argument(help="Extension ID or name to remove"),
    keep_config: bool = typer.Option(False, "--keep-config", help="Don't remove config files"),
    force: bool = typer.Option(False, "--force", help="Skip confirmation"),
):
    """Uninstall an extension."""
    from .extensions import ExtensionManager

    project_root = Path.cwd()

    # Check if we're in a spec-kit project
    _require_spec_kit_plus_project(project_root)

    manager = ExtensionManager(project_root)

    # Resolve extension ID from argument (handles ambiguous names)
    installed = manager.list_installed()
    extension_id, display_name = _resolve_installed_extension(extension, installed, "remove")

    # Get extension info for command and skill counts
    ext_manifest = manager.get_extension(extension_id)
    cmd_count = len(ext_manifest.commands) if ext_manifest else 0
    reg_meta = manager.registry.get(extension_id)
    raw_skills = reg_meta.get("registered_skills") if reg_meta else None
    skill_count = len(raw_skills) if isinstance(raw_skills, list) else 0

    # Confirm removal
    if not force:
        console.print("\n[yellow]⚠  This will remove:[/yellow]")
        console.print(f"   • {cmd_count} commands from AI agent")
        if skill_count:
            console.print(f"   • {skill_count} agent skill(s)")
        console.print(f"   • Extension directory: .specify/extensions/{extension_id}/")
        if not keep_config:
            console.print("   • Config files (will be backed up)")
        console.print()

        confirm = typer.confirm("Continue?")
        if not confirm:
            console.print("Cancelled")
            raise typer.Exit(0)

    # Remove extension
    success = manager.remove(extension_id, keep_config=keep_config)

    if success:
        console.print(f"\n[green]✓[/green] Extension '{display_name}' removed successfully")
        if keep_config:
            console.print(f"\nConfig files preserved in .specify/extensions/{extension_id}/")
        else:
            console.print(f"\nConfig files backed up to .specify/extensions/.backup/{extension_id}/")
        console.print(f"\nTo reinstall: specify extension add {extension_id}")
    else:
        console.print("[red]Error:[/red] Failed to remove extension")
        raise typer.Exit(1)


@extension_app.command("search")
def extension_search(
    query: str = typer.Argument(None, help="Search query (optional)"),
    tag: Optional[str] = typer.Option(None, "--tag", help="Filter by tag"),
    author: Optional[str] = typer.Option(None, "--author", help="Filter by author"),
    verified: bool = typer.Option(False, "--verified", help="Show only verified extensions"),
):
    """Search for available extensions in catalog."""
    from .extensions import ExtensionCatalog, ExtensionError

    project_root = Path.cwd()

    # Check if we're in a spec-kit project
    _require_spec_kit_plus_project(project_root)

    catalog = ExtensionCatalog(project_root)

    try:
        console.print("🔍 Searching extension catalog...")
        results = catalog.search(query=query, tag=tag, author=author, verified_only=verified)

        if not results:
            console.print("\n[yellow]No extensions found matching criteria[/yellow]")
            if query or tag or author or verified:
                console.print("\nTry:")
                console.print("  • Broader search terms")
                console.print("  • Remove filters")
                console.print("  • specify extension search (show all)")
            raise typer.Exit(0)

        console.print(f"\n[green]Found {len(results)} extension(s):[/green]\n")

        for ext in results:
            # Extension header
            verified_badge = " [green]✓ Verified[/green]" if ext.get("verified") else ""
            console.print(f"[bold]{ext['name']}[/bold] (v{ext['version']}){verified_badge}")
            console.print(f"  {ext['description']}")

            # Metadata
            console.print(f"\n  [dim]Author:[/dim] {ext.get('author', 'Unknown')}")
            if ext.get('tags'):
                tags_str = ", ".join(ext['tags'])
                console.print(f"  [dim]Tags:[/dim] {tags_str}")

            # Source catalog
            catalog_name = ext.get("_catalog_name", "")
            install_allowed = ext.get("_install_allowed", True)
            if catalog_name:
                if install_allowed:
                    console.print(f"  [dim]Catalog:[/dim] {catalog_name}")
                else:
                    console.print(f"  [dim]Catalog:[/dim] {catalog_name} [yellow](discovery only — not installable)[/yellow]")

            # Stats
            stats = []
            if ext.get('downloads') is not None:
                stats.append(f"Downloads: {ext['downloads']:,}")
            if ext.get('stars') is not None:
                stats.append(f"Stars: {ext['stars']}")
            if stats:
                console.print(f"  [dim]{' | '.join(stats)}[/dim]")

            # Links
            if ext.get('repository'):
                console.print(f"  [dim]Repository:[/dim] {ext['repository']}")

            # Install command (show warning if not installable)
            if install_allowed:
                console.print(f"\n  [cyan]Install:[/cyan] specify extension add {ext['id']}")
            else:
                console.print(f"\n  [yellow]⚠[/yellow]  Not directly installable from '{catalog_name}'.")
                console.print(
                    f"  Add to an approved catalog with install_allowed: true, "
                    f"or install from a ZIP URL: specify extension add {ext['id']} --from <zip-url>"
                )
            console.print()

    except ExtensionError as e:
        console.print(f"\n[red]Error:[/red] {e}")
        console.print("\nTip: The catalog may be temporarily unavailable. Try again later.")
        raise typer.Exit(1)


@extension_app.command("info")
def extension_info(
    extension: str = typer.Argument(help="Extension ID or name"),
):
    """Show detailed information about an extension."""
    from .extensions import ExtensionCatalog, ExtensionManager, normalize_priority

    project_root = Path.cwd()

    # Check if we're in a spec-kit project
    _require_spec_kit_plus_project(project_root)

    catalog = ExtensionCatalog(project_root)
    manager = ExtensionManager(project_root)
    installed = manager.list_installed()

    # Try to resolve from installed extensions first (by ID or name)
    # Use allow_not_found=True since the extension may be catalog-only
    resolved_installed_id, resolved_installed_name = _resolve_installed_extension(
        extension, installed, "info", allow_not_found=True
    )

    # Try catalog lookup (with error handling)
    # If we resolved an installed extension by display name, use its ID for catalog lookup
    # to ensure we get the correct catalog entry (not a different extension with same name)
    lookup_key = resolved_installed_id if resolved_installed_id else extension
    ext_info, catalog_error = _resolve_catalog_extension(lookup_key, catalog, "info")

    # Case 1: Found in catalog - show full catalog info
    if ext_info:
        _print_extension_info(ext_info, manager)
        return

    # Case 2: Installed locally but catalog lookup failed or not in catalog
    if resolved_installed_id:
        # Get local manifest info
        ext_manifest = manager.get_extension(resolved_installed_id)
        metadata = manager.registry.get(resolved_installed_id)
        metadata_is_dict = isinstance(metadata, dict)
        if not metadata_is_dict:
            console.print(
                "[yellow]Warning:[/yellow] Extension metadata appears to be corrupted; "
                "some information may be unavailable."
            )
        version = metadata.get("version", "unknown") if metadata_is_dict else "unknown"

        console.print(f"\n[bold]{resolved_installed_name}[/bold] (v{version})")
        console.print(f"ID: {resolved_installed_id}")
        console.print()

        if ext_manifest:
            console.print(f"{ext_manifest.description}")
            console.print()
            # Author is optional in extension.yml, safely retrieve it
            author = ext_manifest.data.get("extension", {}).get("author")
            if author:
                console.print(f"[dim]Author:[/dim] {author}")
                console.print()

            if ext_manifest.commands:
                console.print("[bold]Commands:[/bold]")
                for cmd in ext_manifest.commands:
                    console.print(f"  • {cmd['name']}: {cmd.get('description', '')}")
                console.print()

        # Show catalog status
        if catalog_error:
            console.print(f"[yellow]Catalog unavailable:[/yellow] {catalog_error}")
            console.print("[dim]Note: Using locally installed extension; catalog info could not be verified.[/dim]")
        else:
            console.print("[yellow]Note:[/yellow] Not found in catalog (custom/local extension)")

        console.print()
        console.print("[green]✓ Installed[/green]")
        priority = normalize_priority(metadata.get("priority") if metadata_is_dict else None)
        console.print(f"[dim]Priority:[/dim] {priority}")
        console.print(f"\nTo remove: specify extension remove {resolved_installed_id}")
        return

    # Case 3: Not found anywhere
    if catalog_error:
        console.print(f"[red]Error:[/red] Could not query extension catalog: {catalog_error}")
        console.print("\nTry again when online, or use the extension ID directly.")
    else:
        console.print(f"[red]Error:[/red] Extension '{extension}' not found")
        console.print("\nTry: specify extension search")
    raise typer.Exit(1)


def _print_extension_info(ext_info: dict, manager):
    """Print formatted extension info from catalog data."""
    from .extensions import normalize_priority

    # Header
    verified_badge = " [green]✓ Verified[/green]" if ext_info.get("verified") else ""
    console.print(f"\n[bold]{ext_info['name']}[/bold] (v{ext_info['version']}){verified_badge}")
    console.print(f"ID: {ext_info['id']}")
    console.print()

    # Description
    console.print(f"{ext_info['description']}")
    console.print()

    # Author and License
    console.print(f"[dim]Author:[/dim] {ext_info.get('author', 'Unknown')}")
    console.print(f"[dim]License:[/dim] {ext_info.get('license', 'Unknown')}")

    # Source catalog
    if ext_info.get("_catalog_name"):
        install_allowed = ext_info.get("_install_allowed", True)
        install_note = "" if install_allowed else " [yellow](discovery only)[/yellow]"
        console.print(f"[dim]Source catalog:[/dim] {ext_info['_catalog_name']}{install_note}")
    console.print()

    # Requirements
    if ext_info.get('requires'):
        console.print("[bold]Requirements:[/bold]")
        reqs = ext_info['requires']
        if reqs.get('speckit_version'):
            console.print(f"  • Spec Kit: {reqs['speckit_version']}")
        if reqs.get('tools'):
            for tool in reqs['tools']:
                tool_name = tool['name']
                tool_version = tool.get('version', 'any')
                required = " (required)" if tool.get('required') else " (optional)"
                console.print(f"  • {tool_name}: {tool_version}{required}")
        console.print()

    # Provides
    if ext_info.get('provides'):
        console.print("[bold]Provides:[/bold]")
        provides = ext_info['provides']
        if provides.get('commands'):
            console.print(f"  • Commands: {provides['commands']}")
        if provides.get('hooks'):
            console.print(f"  • Hooks: {provides['hooks']}")
        console.print()

    # Tags
    if ext_info.get('tags'):
        tags_str = ", ".join(ext_info['tags'])
        console.print(f"[bold]Tags:[/bold] {tags_str}")
        console.print()

    # Statistics
    stats = []
    if ext_info.get('downloads') is not None:
        stats.append(f"Downloads: {ext_info['downloads']:,}")
    if ext_info.get('stars') is not None:
        stats.append(f"Stars: {ext_info['stars']}")
    if stats:
        console.print(f"[bold]Statistics:[/bold] {' | '.join(stats)}")
        console.print()

    # Links
    console.print("[bold]Links:[/bold]")
    if ext_info.get('repository'):
        console.print(f"  • Repository: {ext_info['repository']}")
    if ext_info.get('homepage'):
        console.print(f"  • Homepage: {ext_info['homepage']}")
    if ext_info.get('documentation'):
        console.print(f"  • Documentation: {ext_info['documentation']}")
    if ext_info.get('changelog'):
        console.print(f"  • Changelog: {ext_info['changelog']}")
    console.print()

    # Installation status and command
    is_installed = manager.registry.is_installed(ext_info['id'])
    install_allowed = ext_info.get("_install_allowed", True)
    if is_installed:
        console.print("[green]✓ Installed[/green]")
        metadata = manager.registry.get(ext_info['id'])
        priority = normalize_priority(metadata.get("priority") if isinstance(metadata, dict) else None)
        console.print(f"[dim]Priority:[/dim] {priority}")
        console.print(f"\nTo remove: specify extension remove {ext_info['id']}")
    elif install_allowed:
        console.print("[yellow]Not installed[/yellow]")
        console.print(f"\n[cyan]Install:[/cyan] specify extension add {ext_info['id']}")
    else:
        catalog_name = ext_info.get("_catalog_name", "community")
        console.print("[yellow]Not installed[/yellow]")
        console.print(
            f"\n[yellow]⚠[/yellow]  '{ext_info['id']}' is available in the '{catalog_name}' catalog "
            f"but not in your approved catalog. Add it to .specify/extension-catalogs.yml "
            f"with install_allowed: true to enable installation."
        )


@extension_app.command("update")
def extension_update(
    extension: str = typer.Argument(None, help="Extension ID or name to update (or all)"),
):
    """Update extension(s) to latest version."""
    from .extensions import (
        ExtensionManager,
        ExtensionCatalog,
        ExtensionError,
        ValidationError,
        CommandRegistrar,
        HookExecutor,
        normalize_priority,
    )
    from packaging import version as pkg_version
    import shutil

    project_root = Path.cwd()

    # Check if we're in a spec-kit project
    _require_spec_kit_plus_project(project_root)

    manager = ExtensionManager(project_root)
    catalog = ExtensionCatalog(project_root)
    speckit_version = get_speckit_version()

    try:
        # Get list of extensions to update
        installed = manager.list_installed()
        if extension:
            # Update specific extension - resolve ID from argument (handles ambiguous names)
            extension_id, _ = _resolve_installed_extension(extension, installed, "update")
            extensions_to_update = [extension_id]
        else:
            # Update all extensions
            extensions_to_update = [ext["id"] for ext in installed]

        if not extensions_to_update:
            console.print("[yellow]No extensions installed[/yellow]")
            raise typer.Exit(0)

        console.print("🔄 Checking for updates...\n")

        updates_available = []

        for ext_id in extensions_to_update:
            # Get installed version
            metadata = manager.registry.get(ext_id)
            if metadata is None or not isinstance(metadata, dict) or "version" not in metadata:
                console.print(f"⚠  {ext_id}: Registry entry corrupted or missing (skipping)")
                continue
            try:
                installed_version = pkg_version.Version(metadata["version"])
            except pkg_version.InvalidVersion:
                console.print(
                    f"⚠  {ext_id}: Invalid installed version '{metadata.get('version')}' in registry (skipping)"
                )
                continue

            # Get catalog info
            ext_info = catalog.get_extension_info(ext_id)
            if not ext_info:
                console.print(f"⚠  {ext_id}: Not found in catalog (skipping)")
                continue

            # Check if installation is allowed from this catalog
            if not ext_info.get("_install_allowed", True):
                console.print(f"⚠  {ext_id}: Updates not allowed from '{ext_info.get('_catalog_name', 'catalog')}' (skipping)")
                continue

            try:
                catalog_version = pkg_version.Version(ext_info["version"])
            except pkg_version.InvalidVersion:
                console.print(
                    f"⚠  {ext_id}: Invalid catalog version '{ext_info.get('version')}' (skipping)"
                )
                continue

            if catalog_version > installed_version:
                updates_available.append(
                    {
                        "id": ext_id,
                        "name": ext_info.get("name", ext_id),  # Display name for status messages
                        "installed": str(installed_version),
                        "available": str(catalog_version),
                        "download_url": ext_info.get("download_url"),
                    }
                )
            else:
                console.print(f"✓ {ext_id}: Up to date (v{installed_version})")

        if not updates_available:
            console.print("\n[green]All extensions are up to date![/green]")
            raise typer.Exit(0)

        # Show available updates
        console.print("\n[bold]Updates available:[/bold]\n")
        for update in updates_available:
            console.print(
                f"  • {update['id']}: {update['installed']} → {update['available']}"
            )

        console.print()
        confirm = typer.confirm("Update these extensions?")
        if not confirm:
            console.print("Cancelled")
            raise typer.Exit(0)

        # Perform updates with atomic backup/restore
        console.print()
        updated_extensions = []
        failed_updates = []
        registrar = CommandRegistrar()
        hook_executor = HookExecutor(project_root)

        for update in updates_available:
            extension_id = update["id"]
            ext_name = update["name"]  # Use display name for user-facing messages
            console.print(f"📦 Updating {ext_name}...")

            # Backup paths
            backup_base = manager.extensions_dir / ".backup" / f"{extension_id}-update"
            backup_ext_dir = backup_base / "extension"
            backup_commands_dir = backup_base / "commands"
            backup_config_dir = backup_base / "config"

            # Store backup state
            backup_registry_entry = None
            backup_hooks = None  # None means no hooks key in config; {} means hooks key existed
            backed_up_command_files = {}

            try:
                # 1. Backup registry entry (always, even if extension dir doesn't exist)
                backup_registry_entry = manager.registry.get(extension_id)

                # 2. Backup extension directory
                extension_dir = manager.extensions_dir / extension_id
                if extension_dir.exists():
                    backup_base.mkdir(parents=True, exist_ok=True)
                    if backup_ext_dir.exists():
                        shutil.rmtree(backup_ext_dir)
                    shutil.copytree(extension_dir, backup_ext_dir)

                    # Backup config files separately so they can be restored
                    # after a successful install (install_from_directory clears dest dir).
                    config_files = list(extension_dir.glob("*-config.yml")) + list(
                        extension_dir.glob("*-config.local.yml")
                    )
                    for cfg_file in config_files:
                        backup_config_dir.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(cfg_file, backup_config_dir / cfg_file.name)

                # 3. Backup command files for all agents
                from .agents import CommandRegistrar as _AgentReg
                registered_commands = backup_registry_entry.get("registered_commands", {})
                for agent_name, cmd_names in registered_commands.items():
                    if agent_name not in registrar.AGENT_CONFIGS:
                        continue
                    agent_config = registrar.AGENT_CONFIGS[agent_name]
                    commands_dir = project_root / agent_config["dir"]

                    for cmd_name in cmd_names:
                        output_name = _AgentReg._compute_output_name(agent_name, cmd_name, agent_config)
                        cmd_file = commands_dir / f"{output_name}{agent_config['extension']}"
                        if cmd_file.exists():
                            backup_cmd_path = backup_commands_dir / agent_name / cmd_file.name
                            backup_cmd_path.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(cmd_file, backup_cmd_path)
                            backed_up_command_files[str(cmd_file)] = str(backup_cmd_path)

                        # Also backup copilot prompt files
                        if agent_name == "copilot":
                            prompt_file = project_root / ".github" / "prompts" / f"{cmd_name}.prompt.md"
                            if prompt_file.exists():
                                backup_prompt_path = backup_commands_dir / "copilot-prompts" / prompt_file.name
                                backup_prompt_path.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(prompt_file, backup_prompt_path)
                                backed_up_command_files[str(prompt_file)] = str(backup_prompt_path)

                # 4. Backup hooks from extensions.yml
                # Use backup_hooks=None to indicate config had no "hooks" key (don't create on restore)
                # Use backup_hooks={} to indicate config had "hooks" key with no hooks for this extension
                config = hook_executor.get_project_config()
                if "hooks" in config:
                    backup_hooks = {}  # Config has hooks key - preserve this fact
                    for hook_name, hook_list in config["hooks"].items():
                        ext_hooks = [h for h in hook_list if h.get("extension") == extension_id]
                        if ext_hooks:
                            backup_hooks[hook_name] = ext_hooks

                # 5. Download new version
                zip_path = catalog.download_extension(extension_id)
                try:
                    # 6. Validate extension ID from ZIP BEFORE modifying installation
                    # Handle both root-level and nested extension.yml (GitHub auto-generated ZIPs)
                    with zipfile.ZipFile(zip_path, "r") as zf:
                        import yaml
                        manifest_data = None
                        namelist = zf.namelist()

                        # First try root-level extension.yml
                        if "extension.yml" in namelist:
                            with zf.open("extension.yml") as f:
                                manifest_data = yaml.safe_load(f) or {}
                        else:
                            # Look for extension.yml in a single top-level subdirectory
                            # (e.g., "repo-name-branch/extension.yml")
                            manifest_paths = [n for n in namelist if n.endswith("/extension.yml") and n.count("/") == 1]
                            if len(manifest_paths) == 1:
                                with zf.open(manifest_paths[0]) as f:
                                    manifest_data = yaml.safe_load(f) or {}

                        if manifest_data is None:
                            raise ValueError("Downloaded extension archive is missing 'extension.yml'")

                    zip_extension_id = manifest_data.get("extension", {}).get("id")
                    if zip_extension_id != extension_id:
                        raise ValueError(
                            f"Extension ID mismatch: expected '{extension_id}', got '{zip_extension_id}'"
                        )

                    # 7. Remove old extension (handles command file cleanup and registry removal)
                    manager.remove(extension_id, keep_config=True)

                    # 8. Install new version
                    _ = manager.install_from_zip(zip_path, speckit_version)

                    # Restore user config files from backup after successful install.
                    new_extension_dir = manager.extensions_dir / extension_id
                    if backup_config_dir.exists() and new_extension_dir.exists():
                        for cfg_file in backup_config_dir.iterdir():
                            if cfg_file.is_file():
                                shutil.copy2(cfg_file, new_extension_dir / cfg_file.name)

                    # 9. Restore metadata from backup (installed_at, enabled state)
                    if backup_registry_entry and isinstance(backup_registry_entry, dict):
                        # Copy current registry entry to avoid mutating internal
                        # registry state before explicit restore().
                        current_metadata = manager.registry.get(extension_id)
                        if current_metadata is None or not isinstance(current_metadata, dict):
                            raise RuntimeError(
                                f"Registry entry for '{extension_id}' missing or corrupted after install — update incomplete"
                            )
                        new_metadata = dict(current_metadata)

                        # Preserve the original installation timestamp
                        if "installed_at" in backup_registry_entry:
                            new_metadata["installed_at"] = backup_registry_entry["installed_at"]

                        # Preserve the original priority (normalized to handle corruption)
                        if "priority" in backup_registry_entry:
                            new_metadata["priority"] = normalize_priority(backup_registry_entry["priority"])

                        # If extension was disabled before update, disable it again
                        if not backup_registry_entry.get("enabled", True):
                            new_metadata["enabled"] = False

                        # Use restore() instead of update() because update() always
                        # preserves the existing installed_at, ignoring our override
                        manager.registry.restore(extension_id, new_metadata)

                        # Also disable hooks in extensions.yml if extension was disabled
                        if not backup_registry_entry.get("enabled", True):
                            config = hook_executor.get_project_config()
                            if "hooks" in config:
                                for hook_name in config["hooks"]:
                                    for hook in config["hooks"][hook_name]:
                                        if hook.get("extension") == extension_id:
                                            hook["enabled"] = False
                                hook_executor.save_project_config(config)
                finally:
                    # Clean up downloaded ZIP
                    if zip_path.exists():
                        zip_path.unlink()

                # 10. Clean up backup on success
                if backup_base.exists():
                    shutil.rmtree(backup_base)

                console.print(f"   [green]✓[/green] Updated to v{update['available']}")
                updated_extensions.append(ext_name)

            except KeyboardInterrupt:
                raise
            except Exception as e:
                console.print(f"   [red]✗[/red] Failed: {e}")
                failed_updates.append((ext_name, str(e)))

                # Rollback on failure
                console.print(f"   [yellow]↩[/yellow] Rolling back {ext_name}...")

                try:
                    # Restore extension directory
                    # Only perform destructive rollback if backup exists (meaning we
                    # actually modified the extension). This avoids deleting a valid
                    # installation when failure happened before changes were made.
                    extension_dir = manager.extensions_dir / extension_id
                    if backup_ext_dir.exists():
                        if extension_dir.exists():
                            shutil.rmtree(extension_dir)
                        shutil.copytree(backup_ext_dir, extension_dir)

                    # Remove any NEW command files created by failed install
                    # (files that weren't in the original backup)
                    try:
                        new_registry_entry = manager.registry.get(extension_id)
                        if new_registry_entry is None or not isinstance(new_registry_entry, dict):
                            new_registered_commands = {}
                        else:
                            new_registered_commands = new_registry_entry.get("registered_commands", {})
                        for agent_name, cmd_names in new_registered_commands.items():
                            if agent_name not in registrar.AGENT_CONFIGS:
                                continue
                            agent_config = registrar.AGENT_CONFIGS[agent_name]
                            commands_dir = project_root / agent_config["dir"]

                            for cmd_name in cmd_names:
                                output_name = _AgentReg._compute_output_name(agent_name, cmd_name, agent_config)
                                cmd_file = commands_dir / f"{output_name}{agent_config['extension']}"
                                # Delete if it exists and wasn't in our backup
                                if cmd_file.exists() and str(cmd_file) not in backed_up_command_files:
                                    cmd_file.unlink()

                                # Also handle copilot prompt files
                                if agent_name == "copilot":
                                    prompt_file = project_root / ".github" / "prompts" / f"{cmd_name}.prompt.md"
                                    if prompt_file.exists() and str(prompt_file) not in backed_up_command_files:
                                        prompt_file.unlink()
                    except KeyError:
                        pass  # No new registry entry exists, nothing to clean up

                    # Restore backed up command files
                    for original_path, backup_path in backed_up_command_files.items():
                        backup_file = Path(backup_path)
                        if backup_file.exists():
                            original_file = Path(original_path)
                            original_file.parent.mkdir(parents=True, exist_ok=True)
                            shutil.copy2(backup_file, original_file)

                    # Restore hooks in extensions.yml
                    # - backup_hooks=None means original config had no "hooks" key
                    # - backup_hooks={} or {...} means config had hooks key
                    config = hook_executor.get_project_config()
                    if "hooks" in config:
                        modified = False

                        if backup_hooks is None:
                            # Original config had no "hooks" key; remove it entirely
                            del config["hooks"]
                            modified = True
                        else:
                            # Remove any hooks for this extension added by failed install
                            for hook_name, hooks_list in config["hooks"].items():
                                original_len = len(hooks_list)
                                config["hooks"][hook_name] = [
                                    h for h in hooks_list
                                    if h.get("extension") != extension_id
                                ]
                                if len(config["hooks"][hook_name]) != original_len:
                                    modified = True

                            # Add back the backed up hooks if any
                            if backup_hooks:
                                for hook_name, hooks in backup_hooks.items():
                                    if hook_name not in config["hooks"]:
                                        config["hooks"][hook_name] = []
                                    config["hooks"][hook_name].extend(hooks)
                                    modified = True

                        if modified:
                            hook_executor.save_project_config(config)

                    # Restore registry entry (use restore() since entry was removed)
                    if backup_registry_entry:
                        manager.registry.restore(extension_id, backup_registry_entry)

                    console.print("   [green]✓[/green] Rollback successful")
                    # Clean up backup directory only on successful rollback
                    if backup_base.exists():
                        shutil.rmtree(backup_base)
                except Exception as rollback_error:
                    console.print(f"   [red]✗[/red] Rollback failed: {rollback_error}")
                    console.print(f"   [dim]Backup preserved at: {backup_base}[/dim]")

        # Summary
        console.print()
        if updated_extensions:
            console.print(f"[green]✓[/green] Successfully updated {len(updated_extensions)} extension(s)")
        if failed_updates:
            console.print(f"[red]✗[/red] Failed to update {len(failed_updates)} extension(s):")
            for ext_name, error in failed_updates:
                console.print(f"   • {ext_name}: {error}")
            raise typer.Exit(1)

    except ValidationError as e:
        console.print(f"\n[red]Validation Error:[/red] {e}")
        raise typer.Exit(1)
    except ExtensionError as e:
        console.print(f"\n[red]Error:[/red] {e}")
        raise typer.Exit(1)


@extension_app.command("enable")
def extension_enable(
    extension: str = typer.Argument(help="Extension ID or name to enable"),
):
    """Enable a disabled extension."""
    from .extensions import ExtensionManager, HookExecutor

    project_root = Path.cwd()

    # Check if we're in a spec-kit project
    _require_spec_kit_plus_project(project_root)

    manager = ExtensionManager(project_root)
    hook_executor = HookExecutor(project_root)

    # Resolve extension ID from argument (handles ambiguous names)
    installed = manager.list_installed()
    extension_id, display_name = _resolve_installed_extension(extension, installed, "enable")

    # Update registry
    metadata = manager.registry.get(extension_id)
    if metadata is None or not isinstance(metadata, dict):
        console.print(f"[red]Error:[/red] Extension '{extension_id}' not found in registry (corrupted state)")
        raise typer.Exit(1)

    if metadata.get("enabled", True):
        console.print(f"[yellow]Extension '{display_name}' is already enabled[/yellow]")
        raise typer.Exit(0)

    manager.registry.update(extension_id, {"enabled": True})

    # Enable hooks in extensions.yml
    config = hook_executor.get_project_config()
    if "hooks" in config:
        for hook_name in config["hooks"]:
            for hook in config["hooks"][hook_name]:
                if hook.get("extension") == extension_id:
                    hook["enabled"] = True
        hook_executor.save_project_config(config)

    console.print(f"[green]✓[/green] Extension '{display_name}' enabled")


@extension_app.command("disable")
def extension_disable(
    extension: str = typer.Argument(help="Extension ID or name to disable"),
):
    """Disable an extension without removing it."""
    from .extensions import ExtensionManager, HookExecutor

    project_root = Path.cwd()

    # Check if we're in a spec-kit project
    _require_spec_kit_plus_project(project_root)

    manager = ExtensionManager(project_root)
    hook_executor = HookExecutor(project_root)

    # Resolve extension ID from argument (handles ambiguous names)
    installed = manager.list_installed()
    extension_id, display_name = _resolve_installed_extension(extension, installed, "disable")

    # Update registry
    metadata = manager.registry.get(extension_id)
    if metadata is None or not isinstance(metadata, dict):
        console.print(f"[red]Error:[/red] Extension '{extension_id}' not found in registry (corrupted state)")
        raise typer.Exit(1)

    if not metadata.get("enabled", True):
        console.print(f"[yellow]Extension '{display_name}' is already disabled[/yellow]")
        raise typer.Exit(0)

    manager.registry.update(extension_id, {"enabled": False})

    # Disable hooks in extensions.yml
    config = hook_executor.get_project_config()
    if "hooks" in config:
        for hook_name in config["hooks"]:
            for hook in config["hooks"][hook_name]:
                if hook.get("extension") == extension_id:
                    hook["enabled"] = False
        hook_executor.save_project_config(config)

    console.print(f"[green]✓[/green] Extension '{display_name}' disabled")
    console.print("\nCommands will no longer be available. Hooks will not execute.")
    console.print(f"To re-enable: specify extension enable {extension_id}")


@extension_app.command("set-priority")
def extension_set_priority(
    extension: str = typer.Argument(help="Extension ID or name"),
    priority: int = typer.Argument(help="New priority (lower = higher precedence)"),
):
    """Set the resolution priority of an installed extension."""
    from .extensions import ExtensionManager

    project_root = Path.cwd()

    # Check if we're in a spec-kit project
    _require_spec_kit_plus_project(project_root)

    # Validate priority
    if priority < 1:
        console.print("[red]Error:[/red] Priority must be a positive integer (1 or higher)")
        raise typer.Exit(1)

    manager = ExtensionManager(project_root)

    # Resolve extension ID from argument (handles ambiguous names)
    installed = manager.list_installed()
    extension_id, display_name = _resolve_installed_extension(extension, installed, "set-priority")

    # Get current metadata
    metadata = manager.registry.get(extension_id)
    if metadata is None or not isinstance(metadata, dict):
        console.print(f"[red]Error:[/red] Extension '{extension_id}' not found in registry (corrupted state)")
        raise typer.Exit(1)

    from .extensions import normalize_priority
    raw_priority = metadata.get("priority")
    # Only skip if the stored value is already a valid int equal to requested priority
    # This ensures corrupted values (e.g., "high") get repaired even when setting to default (10)
    if isinstance(raw_priority, int) and raw_priority == priority:
        console.print(f"[yellow]Extension '{display_name}' already has priority {priority}[/yellow]")
        raise typer.Exit(0)

    old_priority = normalize_priority(raw_priority)

    # Update priority
    manager.registry.update(extension_id, {"priority": priority})

    console.print(f"[green]✓[/green] Extension '{display_name}' priority changed: {old_priority} → {priority}")
    console.print("\n[dim]Lower priority = higher precedence in template resolution[/dim]")


def main():
    app()

if __name__ == "__main__":
    main()
