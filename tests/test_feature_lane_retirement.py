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
    remaining = []
    for path in retired_paths:
        target = REPO_ROOT / path
        if target.is_file() or (
            target.is_dir() and any(item.is_file() for item in target.rglob("*"))
        ):
            remaining.append(path)
    assert remaining == []

    python_cli = (REPO_ROOT / "src/specify_cli/__init__.py").read_text(
        encoding="utf-8"
    )
    assert "from specify_cli.lanes import" not in python_cli
    assert 'app.add_typer(lane_app, name="lane")' not in python_cli
    assert '@app.command("integrate")' not in python_cli
    assert "_display_cmd('integrate')" not in python_cli

    runtime_main = (REPO_ROOT / "tools/specify-runtime/main.go").read_text(
        encoding="utf-8"
    )
    assert 'case "lane":' not in runtime_main
    assert "return runLane(" not in runtime_main
    assert "return runIntegrate(" not in runtime_main
    assert '"lane.resolve"' not in runtime_main
    assert '"integrate.discover"' not in runtime_main
    assert '"integrate.close"' not in runtime_main

    surface_map = json.loads(
        (REPO_ROOT / "templates/advanced-skills/_shared/surface-map.json").read_text(
            encoding="utf-8"
        )
    )
    assert "spx-integrate" not in surface_map["skills"]

    artifact_registry = json.loads(
        (REPO_ROOT / "templates/workflow-artifact-registry.json").read_text(
            encoding="utf-8"
        )
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
        content = (REPO_ROOT / script).read_text(encoding="utf-8")
        assert ".specify/lanes" not in content
        assert "LANE_WORKTREE" not in content


def test_task_and_evidence_lane_artifacts_remain_supported_without_legacy_run_integration() -> None:
    assert (REPO_ROOT / "templates/artifacts/lane-manifest.json").is_file()

    artifact_registry = (
        REPO_ROOT / "tools/specify-runtime/artifact_registry.go"
    ).read_text(encoding="utf-8")
    assert "planning-lane-manifest" in artifact_registry
    assert "task-generation-lane-manifest" in artifact_registry

    run_cli = (REPO_ROOT / "tools/specify-runtime/run.go").read_text(
        encoding="utf-8"
    )
    assert 'case "integrate":' not in run_cli
    assert "runIntegrateCandidate" not in run_cli
    for handler in (
        "runResultCommand",
        "runCandidateCommand",
        "runAcceptCommand",
        "runCASCommand",
        "runSyncCommand",
    ):
        assert handler in run_cli


def test_active_workflow_surfaces_use_run_control_not_feature_lanes() -> None:
    active_roots = (
        REPO_ROOT / "src",
        REPO_ROOT / "templates" / "commands",
        REPO_ROOT / "templates" / "command-partials",
        REPO_ROOT / "templates" / "command-references",
        REPO_ROOT / "templates" / "advanced-skills",
    )
    forbidden = (
        ".specify/lanes",
        "specify-runtime lane resolve",
        "sp-integrate",
        "spx-integrate",
        "specify-runtime run integrate",
        "runIntegrateCandidate",
    )
    violations: list[str] = []
    for root in active_roots:
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in {".go", ".json", ".md", ".py"}:
                continue
            content = path.read_text(encoding="utf-8")
            for token in forbidden:
                if token in content:
                    violations.append(f"{path.relative_to(REPO_ROOT)}: {token}")
    assert violations == []

    docs = "\n".join(
        (REPO_ROOT / path).read_text(encoding="utf-8")
        for path in ("README.md", "PROJECT-HANDBOOK.md", "docs/quickstart.md")
    )
    for token in forbidden:
        assert token not in docs
    assert "specify-runtime run launch" in docs
    assert "run supervise" in docs
    assert "specify-runtime result show" in docs
    assert "specify-runtime candidate build" in docs
    assert "candidate review" in docs
    assert "accept receipt" in docs
    assert "cas publish" in docs
    assert "sync safe" in docs
    assert "WSLENV" in docs
