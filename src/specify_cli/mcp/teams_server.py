"""Agent-facing MCP facade for the Codex teams control plane."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from specify_cli.codex_team.api_surface import run_team_api_operation

MCP_IMPORT_HINT = (
    "specify-teams-mcp requires the optional MCP dependency. "
    "Install it with: pip install 'specify-cli[mcp]'"
)


def _load_fastmcp():
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:  # pragma: no cover - exercised via runtime/manual path
        raise RuntimeError(MCP_IMPORT_HINT) from exc
    return FastMCP


def _resolve_project_root(project_root: str | None) -> Path:
    return Path(project_root).resolve() if project_root else Path.cwd().resolve()


def build_teams_mcp_server(*, fastmcp_cls: type | None = None):
    """Build the agent-facing MCP server for teams control operations."""

    FastMCP = fastmcp_cls or _load_fastmcp()
    mcp = FastMCP("specify-teams")

    def _run(project_root: str | None, operation: str, **kwargs: Any) -> dict[str, Any]:
        return run_team_api_operation(_resolve_project_root(project_root), operation, **kwargs)

    @mcp.tool(name="teams_status")
    def teams_status(project_root: str | None = None, session_id: str = "default") -> dict[str, Any]:
        return _run(project_root, "status", session_id=session_id)

    @mcp.tool(name="teams_doctor")
    def teams_doctor(project_root: str | None = None, session_id: str = "default") -> dict[str, Any]:
        return _run(project_root, "doctor", session_id=session_id)

    @mcp.tool(name="teams_live_probe")
    def teams_live_probe(project_root: str | None = None, session_id: str = "default") -> dict[str, Any]:
        return _run(project_root, "live-probe", session_id=session_id)

    @mcp.tool(name="teams_list_tasks")
    def teams_list_tasks(project_root: str | None = None) -> dict[str, Any]:
        return _run(project_root, "tasks")

    @mcp.tool(name="teams_auto_dispatch")
    def teams_auto_dispatch(
        feature_dir: str,
        project_root: str | None = None,
        session_id: str = "default",
    ) -> dict[str, Any]:
        return _run(project_root, "auto-dispatch", feature_dir=feature_dir, session_id=session_id)

    @mcp.tool(name="teams_complete_batch")
    def teams_complete_batch(
        batch_id: str,
        project_root: str | None = None,
        session_id: str = "default",
    ) -> dict[str, Any]:
        return _run(project_root, "complete-batch", batch_id=batch_id, session_id=session_id)

    @mcp.tool(name="teams_submit_result")
    def teams_submit_result(
        request_id: str,
        result_file: str,
        project_root: str | None = None,
        session_id: str = "default",
    ) -> dict[str, Any]:
        return _run(
            project_root,
            "submit-result",
            request_id=request_id,
            result_file=result_file,
            session_id=session_id,
        )

    @mcp.tool(name="teams_result_template")
    def teams_result_template(
        request_id: str,
        project_root: str | None = None,
    ) -> dict[str, Any]:
        return _run(project_root, "result-template", request_id=request_id)

    @mcp.resource("specify-teams://status/{session_id}")
    def teams_status_resource(session_id: str = "default") -> str:
        return json.dumps(_run(None, "status", session_id=session_id), ensure_ascii=False, default=str, indent=2)

    @mcp.resource("specify-teams://tasks")
    def teams_tasks_resource() -> str:
        return json.dumps(_run(None, "tasks"), ensure_ascii=False, default=str, indent=2)

    return mcp


def main() -> None:
    """Run the teams MCP server over stdio for agent clients."""

    try:
        server = build_teams_mcp_server()
    except RuntimeError as exc:  # pragma: no cover - exercised via runtime/manual path
        print(str(exc), file=sys.stderr)
        raise SystemExit(1) from exc
    server.run()


__all__ = ["build_teams_mcp_server", "main"]
