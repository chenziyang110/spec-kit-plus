from pathlib import Path


def _write_fake_runtime_cli(path: Path) -> None:
    path.write_text(
        "\n".join(
            [
                "import json",
                "import os",
                "import sys",
                "from pathlib import Path",
                "",
                "payload = json.loads(sys.stdin.read())",
                "state_root = Path(os.environ['SPECIFY_TEAM_STATE_ROOT'])",
                "tasks_dir = state_root / 'team' / payload['teamName'] / 'tasks'",
                "tasks_dir.mkdir(parents=True, exist_ok=True)",
                "for index, task in enumerate(payload['tasks'], start=1):",
                "    description = task['description']",
                "    marker_start = 'BEGIN_WORKER_TASK_RESULT_JSON'",
                "    marker_end = 'END_WORKER_TASK_RESULT_JSON'",
                "    start = description.index(marker_start) + len(marker_start)",
                "    end = description.index(marker_end)",
                "    payload_text = description[start:end].strip()",
                "    result_payload = json.loads(payload_text)",
                "    result_text = marker_start + '\\n' + json.dumps(result_payload, ensure_ascii=False, indent=2) + '\\n' + marker_end",
                "    task_payload = {",
                "        'id': str(index),",
                "        'subject': task['subject'],",
                "        'description': description,",
                "        'status': 'completed',",
                "        'result': result_text,",
                "        'created_at': '2026-04-26T00:00:00Z',",
                "    }",
                "    (tasks_dir / f'task-{index}.json').write_text(json.dumps(task_payload, ensure_ascii=False, indent=2), encoding='utf-8')",
                "(tasks_dir.parent / 'phase.json').write_text(json.dumps({'current_phase': 'complete', 'updated_at': '2026-04-26T00:00:00Z'}, ensure_ascii=False, indent=2), encoding='utf-8')",
                "(tasks_dir.parent / 'monitor-snapshot.json').write_text(json.dumps({'taskStatusById': {'1': 'completed'}, 'workerAliveByName': {'worker-1': True}, 'workerStateByName': {'worker-1': 'done'}, 'workerTurnCountByName': {'worker-1': 1}, 'workerTaskIdByName': {'worker-1': '1'}, 'mailboxNotifiedByMessageId': {}, 'completedEventTaskIds': {'1': True}}, ensure_ascii=False, indent=2), encoding='utf-8')",
                "json.dump({'status': 'completed', 'teamName': payload['teamName'], 'taskResults': [], 'duration': 0, 'workerCount': len(payload['tasks'])}, sys.stdout)",
            ]
        ),
        encoding="utf-8",
    )


def test_codex_team_live_probe_returns_success_with_fake_runtime(
    monkeypatch,
    codex_team_project_root: Path,
):
    from specify_cli.codex_team.live_probe import codex_team_live_probe

    runtime_cli = codex_team_project_root / "fake-runtime-cli.py"
    _write_fake_runtime_cli(runtime_cli)

    monkeypatch.setenv("SPECIFY_CODEX_TEAM_RUNTIME_CLI", str(runtime_cli))
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.is_native_windows", lambda: False)
    monkeypatch.setattr(
        "specify_cli.codex_team.runtime_bridge.shutil.which",
        lambda name: r"C:\tool.exe" if name == "node" else None,
    )
    monkeypatch.setattr("specify_cli.codex_team.runtime_bridge.detect_available_backends", lambda: {})

    payload = codex_team_live_probe(codex_team_project_root, session_id="default")

    assert payload["ok"] is True
    assert payload["dispatch"]["status"] == "completed"
    assert payload["result"]["status"] == "success"
    assert payload["doctor"]["transcript"]["returncode"] == 0
