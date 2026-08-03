from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_feature_lane_runtime_and_workflow_surfaces_are_retired() -> None:
    retired_paths = (
        "src/specify_cli/lanes",
        "tests/lanes",
        "tools/specify-runtime/lane.go",
        "tools/specify-runtime/lane_test.go",
        "tools/specify-runtime/integrate.go",
        "tools/specify-runtime/integrate_test.go",
        "templates/commands/integrate.md",
        "templates/advanced-skills/spx-integrate",
    )
    remaining = [path for path in retired_paths if (REPO_ROOT / path).exists()]
    assert remaining == []

    python_cli = (REPO_ROOT / "src/specify_cli/__init__.py").read_text()
    assert "from specify_cli.lanes import" not in python_cli
    assert 'app.add_typer(lane_app, name="lane")' not in python_cli
    assert '@app.command("integrate")' not in python_cli

    runtime_main = (REPO_ROOT / "tools/specify-runtime/main.go").read_text()
    assert 'case "lane":' not in runtime_main
    assert "return runLane(" not in runtime_main
    assert "return runIntegrate(" not in runtime_main
    assert '"lane.resolve"' not in runtime_main
    assert '"integrate.discover"' not in runtime_main
    assert '"integrate.close"' not in runtime_main

    surface_map = json.loads(
        (REPO_ROOT / "templates/advanced-skills/_shared/surface-map.json").read_text()
    )
    assert "spx-integrate" not in surface_map["skills"]

    artifact_registry = json.loads(
        (REPO_ROOT / "templates/workflow-artifact-registry.json").read_text()
    )
    registry_text = json.dumps(artifact_registry)
    assert "lane_runtime_artifacts" not in registry_text
    assert ".specify/lanes/**" not in registry_text

    for script in (
        "scripts/bash/create-new-feature.sh",
        "scripts/powershell/create-new-feature.ps1",
        "scripts/bash/common.sh",
        "scripts/powershell/common.ps1",
    ):
        content = (REPO_ROOT / script).read_text()
        assert ".specify/lanes" not in content
        assert "LANE_WORKTREE" not in content


def test_task_and_evidence_lane_artifacts_remain_supported() -> None:
    assert (REPO_ROOT / "templates/artifacts/lane-manifest.json").is_file()

    artifact_registry = (
        REPO_ROOT / "tools/specify-runtime/artifact_registry.go"
    ).read_text()
    assert "planning-lane-manifest" in artifact_registry
    assert "task-generation-lane-manifest" in artifact_registry

    run_cli = (REPO_ROOT / "tools/specify-runtime/run.go").read_text()
    assert 'case "integrate":' in run_cli
    assert "runIntegrateCandidate" in run_cli
