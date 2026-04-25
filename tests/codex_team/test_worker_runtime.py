import json
import sys

from specify_cli.codex_team.state_paths import shutdown_path, worker_heartbeat_path
from specify_cli.codex_team.worker_runtime import main


def test_worker_runtime_reports_executor_missing_without_placeholder_result(
    monkeypatch,
    codex_team_project_root,
):
    result_path = codex_team_project_root / ".specify" / "codex-team" / "state" / "results" / "req-runtime.json"
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
    assert result_path.exists() is False
    heartbeat = json.loads(
        worker_heartbeat_path(codex_team_project_root, "worker-runtime-1").read_text(encoding="utf-8")
    )
    assert heartbeat["status"] == "executor_missing"
    assert "no packet executor" in heartbeat["details"]["reason"].lower()
