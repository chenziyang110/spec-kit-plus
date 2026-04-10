import json

from specify_cli.codex_team.manifests import runtime_session_from_json
from specify_cli.codex_team.runtime_bridge import bootstrap_runtime_session, cleanup_runtime_session
from specify_cli.codex_team.state_paths import runtime_session_path


def test_bootstrap_runtime_session_writes_ready_session(monkeypatch, codex_team_project_root):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")

    session = bootstrap_runtime_session(codex_team_project_root, "session-1")
    stored = runtime_session_path(codex_team_project_root, "session-1").read_text(encoding="utf-8")
    restored = runtime_session_from_json(stored)

    assert session.status == "ready"
    assert restored.environment_check == "pass"


def test_cleanup_runtime_session_marks_cleaned(monkeypatch, codex_team_project_root):
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.shutil.which", lambda name: r"C:\tmux.exe")

    bootstrap_runtime_session(codex_team_project_root, "session-2")
    cleaned = cleanup_runtime_session(codex_team_project_root, "session-2")
    payload = json.loads(runtime_session_path(codex_team_project_root, "session-2").read_text(encoding="utf-8"))

    assert cleaned.status == "cleaned"
    assert payload["status"] == "cleaned"
    assert payload["finished_at"]
