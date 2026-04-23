import json
import sys

from specify_cli.codex_team.state_paths import result_record_path, shutdown_path
from specify_cli.codex_team.worker_runtime import main


def test_worker_runtime_seeds_pending_result_envelope(monkeypatch, codex_team_project_root):
    result_path = result_record_path(codex_team_project_root, "req-runtime")
    result_path.parent.mkdir(parents=True, exist_ok=True)
    shutdown = shutdown_path(codex_team_project_root, "session-runtime")
    shutdown.parent.mkdir(parents=True, exist_ok=True)
    shutdown.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "worker-runtime",
            "--project-root",
            str(codex_team_project_root),
            "--session-id",
            "session-runtime",
            "--worker-id",
            "worker-runtime-1",
            "--task-id",
            "T123",
            "--request-id",
            "req-runtime",
            "--worktree",
            str(codex_team_project_root / ".specify" / "codex-team" / "worktrees" / "session-runtime" / "worker-runtime-1"),
            "--result-path",
            str(result_path),
            "--heartbeat-interval",
            "1",
        ],
    )

    exit_code = main()

    assert exit_code == 0
    stored = json.loads(result_path.read_text(encoding="utf-8"))
    assert stored["task_id"] == "T123"
    assert stored["status"] == "pending"
    assert "placeholder" in stored["summary"].lower()
