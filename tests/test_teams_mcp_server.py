from pathlib import Path
import sys
import types

from specify_cli.codex_team.installer import can_configure_specify_teams_mcp
from specify_cli.mcp.teams_server import _load_fastmcp, build_teams_mcp_server


class FakeFastMCP:
    def __init__(self, name: str):
        self.name = name
        self.tools: dict[str, object] = {}
        self.resources: dict[str, object] = {}
        self.transport: str | None = None

    def tool(self, name: str | None = None):
        def decorator(func):
            self.tools[name or func.__name__] = func
            return func

        return decorator

    def resource(self, uri: str):
        def decorator(func):
            self.resources[uri] = func
            return func

        return decorator

    def run(self, transport: str = "stdio"):
        self.transport = transport


def test_build_teams_mcp_server_registers_expected_tools(monkeypatch) -> None:
    calls: list[tuple[str, str, str]] = []

    def fake_run(project_root: Path, operation: str, **kwargs):
        calls.append((str(project_root), operation, str(kwargs.get("session_id", ""))))
        return {"operation": operation, "status": "ok", "payload": {"project_root": str(project_root)}}

    monkeypatch.setattr("specify_cli.mcp.teams_server.run_team_api_operation", fake_run)

    server = build_teams_mcp_server(fastmcp_cls=FakeFastMCP)

    assert server.name == "specify-teams"
    assert set(server.tools) >= {
        "teams_status",
        "teams_doctor",
        "teams_live_probe",
        "teams_list_tasks",
        "teams_auto_dispatch",
        "teams_complete_batch",
        "teams_submit_result",
        "teams_result_template",
    }

    payload = server.tools["teams_status"](project_root=r"F:\project", session_id="blue")
    assert payload["operation"] == "status"
    assert calls == [(r"F:\project", "status", "blue")]


def test_build_teams_mcp_server_preserves_windows_absolute_paths_on_posix(monkeypatch) -> None:
    calls: list[str] = []

    def fake_run(project_root: Path, operation: str, **kwargs):
        calls.append(str(project_root))
        return {"operation": operation, "status": "ok"}

    monkeypatch.setattr("specify_cli.mcp.teams_server.run_team_api_operation", fake_run)

    server = build_teams_mcp_server(fastmcp_cls=FakeFastMCP)
    server.tools["teams_status"](project_root=r"F:\project")

    assert calls == [r"F:\project"]


def test_teams_submit_result_forwards_inline_json(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_run(project_root: Path, operation: str, **kwargs):
        calls.append({"operation": operation, **kwargs})
        return {"operation": operation, "status": "ok"}

    monkeypatch.setattr("specify_cli.mcp.teams_server.run_team_api_operation", fake_run)
    server = build_teams_mcp_server(fastmcp_cls=FakeFastMCP)

    server.tools["teams_submit_result"](
        request_id="req-inline",
        result_json='{"task_id":"T001","status":"success"}',
        project_root=r"F:\project",
    )

    assert calls == [
        {
            "operation": "submit-result",
            "request_id": "req-inline",
            "result_json": '{"task_id":"T001","status":"success"}',
            "session_id": "default",
        }
    ]


def test_build_teams_mcp_server_registers_read_only_resources(monkeypatch) -> None:
    def fake_run(project_root: Path, operation: str, **kwargs):
        return {"operation": operation, "status": "ok", "payload": {"project_root": str(project_root)}}

    monkeypatch.setattr("specify_cli.mcp.teams_server.run_team_api_operation", fake_run)

    server = build_teams_mcp_server(fastmcp_cls=FakeFastMCP)

    assert "specify-teams://status/{session_id}" in server.resources
    assert "specify-teams://tasks" in server.resources

    status_resource = server.resources["specify-teams://status/{session_id}"]
    rendered = status_resource("default")
    assert '"operation": "status"' in rendered


def test_load_fastmcp_falls_back_to_mcpserver(monkeypatch) -> None:
    """MCP SDK v2 removed FastMCP; loader must use MCPServer instead."""

    class FakeMCPServer:
        def __init__(self, name: str):
            self.name = name

    import builtins

    orig_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):  # noqa: A002
        if name == "mcp.server.fastmcp" or (name == "mcp.server" and fromlist and "fastmcp" in fromlist):
            raise ImportError("no FastMCP in v2")
        if name == "mcp.server" and fromlist and "MCPServer" in fromlist:
            mod = types.ModuleType("mcp.server")
            mod.MCPServer = FakeMCPServer
            return mod
        if name == "mcp.server.fastmcp":
            raise ImportError("no FastMCP in v2")
        return orig_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    # Ensure a stale FastMCP module cannot short-circuit the ImportError path.
    monkeypatch.delitem(sys.modules, "mcp.server.fastmcp", raising=False)
    monkeypatch.delitem(sys.modules, "mcp.server.fastmcp.server", raising=False)

    loaded = _load_fastmcp()
    assert loaded is FakeMCPServer


def test_can_configure_specify_teams_mcp_accepts_mcpserver(monkeypatch) -> None:
    import builtins

    orig_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):  # noqa: A002
        if name == "mcp.server.fastmcp":
            raise ImportError("no FastMCP in v2")
        if name == "mcp.server" and fromlist and "MCPServer" in fromlist:
            mod = types.ModuleType("mcp.server")

            class MCPServer:  # noqa: N801
                pass

            mod.MCPServer = MCPServer
            return mod
        return orig_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    monkeypatch.delitem(sys.modules, "mcp.server.fastmcp", raising=False)
    monkeypatch.setattr(
        "specify_cli.codex_team.installer.shutil.which",
        lambda cmd: r"C:\bin\specify-teams-mcp" if cmd == "specify-teams-mcp" else None,
    )
    assert can_configure_specify_teams_mcp() is True
