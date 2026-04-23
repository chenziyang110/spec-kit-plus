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
            "native_dispatch_hint": "Dispatch bounded lanes through `spawn_agent`.",
            "native_join_hint": "Rejoin with `wait_agent`, integrate, then `close_agent`.",
            "result_contract_hint": "WorkerTaskResult contract with validation evidence.",
        },
    )

    assert "packet_summary: task_id: T002" in payload.instructions
    assert "required_references: src/contracts/auth.py" in payload.instructions
    assert "forbidden_drift: Do not create a parallel auth stack" in payload.instructions
    assert "validation_gates: pytest tests/unit/test_auth_service.py -q" in payload.instructions
    assert "native_dispatch_hint: Dispatch bounded lanes through `spawn_agent`." in payload.instructions
    assert "native_join_hint: Rejoin with `wait_agent`, integrate, then `close_agent`." in payload.instructions
    assert "result_contract_hint: WorkerTaskResult contract with validation evidence." in payload.instructions
    assert "hard rule: do not execute from raw task text alone" in payload.instructions


def test_build_worker_bootstrap_payload_can_carry_request_and_result_targets() -> None:
    pane_spec = WorkerPaneSpec(
        backend="tmux",
        binary=r"C:\tmux.exe",
        session="codex-team-default",
        worker_id="worker-2",
        pane_title="worker-worker-2",
        launch_command="python -m worker",
        worktree="C:/tmp/worktree-2",
        env={"WORKER_ID": "worker-2"},
    )

    payload = build_worker_bootstrap_payload(
        pane_spec,
        role="implementer",
        additional_metadata={
            "request_id": "req-99",
            "result_path": "F:/tmp/results/req-99.json",
        },
    )

    assert payload.metadata["request_id"] == "req-99"
    assert payload.metadata["result_path"] == "F:/tmp/results/req-99.json"
