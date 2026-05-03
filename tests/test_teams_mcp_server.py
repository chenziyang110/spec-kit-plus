from pathlib import Path

from specify_cli.mcp.teams_server import build_teams_mcp_server


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
