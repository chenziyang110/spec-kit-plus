from __future__ import annotations

import json
import re
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
            target.is_dir()
            and any(
                item.is_file()
                and item.suffix != ".pyc"
                and "__pycache__" not in item.parts
                for item in target.rglob("*")
            )
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


def test_task_results_product_review_and_execution_survive_run_retirement() -> None:
    assert (REPO_ROOT / "templates/artifacts/lane-manifest.json").is_file()

    artifact_registry = (
        REPO_ROOT / "tools/specify-runtime/artifact_registry.go"
    ).read_text(encoding="utf-8")
    assert "planning-lane-manifest" in artifact_registry
    assert "task-generation-lane-manifest" in artifact_registry

    runtime_main = (REPO_ROOT / "tools/specify-runtime/main.go").read_text(
        encoding="utf-8"
    )
    for capability in (
        "result.path",
        "result.submit",
        "review.target-bind",
        "accept.closeout",
        "execution.control",
        "board.feature-bootstrap",
    ):
        assert f'"{capability}"' in runtime_main
    for capability in ("run.launch", "run.supervise", "candidate.build", "cas.publish", "sync.safe"):
        assert f'"{capability}"' not in runtime_main
    for command in ("run", "snapshot", "candidate", "cas", "sync"):
        assert f'case "{command}":' not in runtime_main


def test_active_workflow_surfaces_emit_work_execution_without_retired_run_commands() -> None:
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
        "run-bootstrap.md",
    )
    retired_command = re.compile(
        r"\bspecify-runtime(?:\.exe)?\s+(?:(?:run|snapshot|candidate|cas|sync)\b|accept\s+receipt\b)"
    )
    violations: list[str] = []
    for root in active_roots:
        for path in root.rglob("*"):
            if not path.is_file() or path.suffix not in {".go", ".json", ".md", ".py"}:
                continue
            content = path.read_text(encoding="utf-8")
            # Runtime adapters may strip inherited retired environment keys;
            # prompt/artifact sources must never teach them as live bindings.
            if path.suffix in {".md", ".json"} and "SPECIFY_RUN_" in content:
                violations.append(f"{path.relative_to(REPO_ROOT)}: retired environment binding")
            if retired_command.search(" ".join(content.lower().split())):
                violations.append(f"{path.relative_to(REPO_ROOT)}: retired CLI emission")
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
    assert not retired_command.search(" ".join(docs.lower().split()))
    assert "Work Board + execution" in docs
    assert "execution announce" in docs
    assert "execution guard" in docs
    assert "execution complete" in docs
    assert "implement -> review -> accept" in docs
    assert "WorkerTaskResult" in docs
    assert "structure_snapshot" in docs


def test_retirement_preserves_historical_data_without_turning_it_into_active_work() -> None:
    for relative in (
        "README.md",
        "PROJECT-HANDBOOK.md",
        "templates/project-handbook-template.md",
        "docs/quickstart.md",
    ):
        content = " ".join((REPO_ROOT / relative).read_text(encoding="utf-8").lower().split())
        assert "inert preserved history" in content, relative
        assert "historical" in content and "worktrees" in content, relative
        assert "delete" in content and "rewrite historical records" in content, relative
        assert "safe additive metadata schema evolution is allowed" in content, relative
        assert "recovery-held work remains active" in content, relative
    archive = (REPO_ROOT / "docs/superpowers/specs/2026-08-03-sp-run-control-design.md").read_text(encoding="utf-8")
    assert "Retired historical design" in archive
    assert "not the current implementation contract" in archive
