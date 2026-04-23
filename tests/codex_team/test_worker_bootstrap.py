from specify_cli.codex_team.tmux_backend import WorkerPaneSpec
from specify_cli.codex_team.worker_bootstrap import build_worker_bootstrap_payload


def test_build_worker_bootstrap_payload_includes_packet_metadata() -> None:
    pane_spec = WorkerPaneSpec(
        backend="tmux",
        binary=r"C:\tmux.exe",
        session="codex-team-default",
        worker_id="worker-1",
        pane_title="worker-worker-1",
        launch_command="python -m worker",
        worktree="C:/tmp/worktree",
        env={"WORKER_ID": "worker-1"},
    )

    payload = build_worker_bootstrap_payload(
        pane_spec,
        role="implementer",
        additional_metadata={
            "packet_summary": "task_id: T002",
            "required_references": "src/contracts/auth.py",
            "forbidden_drift": "Do not create a parallel auth stack",
            "validation_gates": "pytest tests/unit/test_auth_service.py -q",
        },
    )

    assert "packet_summary: task_id: T002" in payload.instructions
    assert "required_references: src/contracts/auth.py" in payload.instructions
    assert "forbidden_drift: Do not create a parallel auth stack" in payload.instructions
    assert "validation_gates: pytest tests/unit/test_auth_service.py -q" in payload.instructions
    assert "hard rule: do not execute from raw task text alone" in payload.instructions
