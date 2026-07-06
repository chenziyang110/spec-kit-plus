import json
import os
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from specify_cli.artifacts.registry import _validate_allowed_output_path_pattern
from specify_cli.artifacts import (
    ARTIFACT_REGISTRY,
    ArtifactScaffoldError,
    audit_fixed_cost,
    get_artifact_kind,
    scaffold_artifact,
    validate_registry,
)
from specify_cli.artifacts.scaffold import _reject_symlink_escape


def test_registry_contains_first_rollout_kinds():
    assert set(ARTIFACT_REGISTRY) == {"quick-status", "plan-contract"}

    quick_status = get_artifact_kind("quick-status")
    assert quick_status.workflow == "sp-quick"
    assert quick_status.allowed_output_paths == (".planning/quick/*/STATUS.md",)
    assert "current_focus" in quick_status.agent_fill_required
    assert quick_status.fill_targets["current_focus"]["anchor"] == (
        "agent-fill:current_focus"
    )

    plan_contract = get_artifact_kind("plan-contract")
    assert plan_contract.workflow == "sp-plan"
    assert plan_contract.allowed_output_paths == (
        "specs/*/plan-contract.json",
        "specs/*/plan/plan-contract.json",
        ".specify/features/*/plan-contract.json",
        ".specify/features/*/plan/plan-contract.json",
    )
    assert plan_contract.validator == "json"
    assert "allowed_optimization_scope" in plan_contract.agent_fill_required
    assert plan_contract.fill_targets["allowed_optimization_scope"]["pointer"] == (
        "/allowed_optimization_scope"
    )


def test_validate_registry_reports_no_errors_for_first_rollout():
    assert validate_registry() == []


def test_allowed_output_path_patterns_are_relative_posix_artifact_paths():
    artifact_kind = get_artifact_kind("plan-contract")
    invalid_patterns = (
        "",
        "/specs/*/plan-contract.json",
        "C:/specs/*/plan-contract.json",
        "specs/../plan-contract.json",
        r"specs\*\plan-contract.json",
        "specs/*/plan.json",
    )

    for pattern in invalid_patterns:
        copied = replace(artifact_kind, allowed_output_paths=(pattern,))
        assert _validate_allowed_output_path_pattern(
            "plan-contract", copied, pattern
        ), pattern


def test_audit_reports_fixed_savings_and_registry_metadata():
    audit = audit_fixed_cost()

    assert audit["status"] == "ok"
    assert audit["candidate_count"] == 2

    candidates = {candidate["kind"]: candidate for candidate in audit["candidates"]}

    quick_status = candidates["quick-status"]
    assert quick_status["recommendation"] == "scaffold"
    assert quick_status["fixed_bytes"] > 1000
    assert quick_status["estimated_token_savings"] == quick_status["fixed_bytes"] // 4
    assert quick_status["quality_risk"] == "low"
    assert quick_status["fill_targets"]["current_focus"]["type"] == "markdown_anchor"

    plan_contract = candidates["plan-contract"]
    assert plan_contract["recommendation"] == "builder"
    assert plan_contract["fixed_bytes"] > 500
    assert plan_contract["downstream_consumers"] == ["sp-tasks", "sp-analyze"]


def test_scaffold_rejects_absolute_output_path(tmp_path: Path):
    with pytest.raises(ArtifactScaffoldError, match="unsafe_path"):
        scaffold_artifact(
            tmp_path,
            kind="quick-status",
            out_path=str(tmp_path / ".planning" / "quick" / "001-demo" / "STATUS.md"),
        )


def test_scaffold_rejects_traversal_output_path(tmp_path: Path):
    with pytest.raises(ArtifactScaffoldError, match="unsafe_path"):
        scaffold_artifact(
            tmp_path,
            kind="quick-status",
            out_path=".planning/quick/001-demo/../../escape.md",
        )


def test_scaffold_rejects_disallowed_kind_path(tmp_path: Path):
    with pytest.raises(ArtifactScaffoldError, match="unsafe_path"):
        scaffold_artifact(
            tmp_path,
            kind="quick-status",
            out_path="specs/001-demo/STATUS.md",
        )


def test_scaffold_rejects_symlink_escape(tmp_path: Path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    quick_root = project_root / ".planning" / "quick"
    quick_root.mkdir(parents=True)
    link = quick_root / "001-demo"
    if not _create_directory_link(link, outside):
        pytest.skip("directory symlink or junction creation is not available")

    with pytest.raises(ArtifactScaffoldError, match="unsafe_path"):
        scaffold_artifact(
            project_root,
            kind="quick-status",
            out_path=".planning/quick/001-demo/STATUS.md",
        )

    assert not (outside / "STATUS.md").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows junction race coverage")
def test_scaffold_rejects_ancestor_swap_before_parent_mkdir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    project_root = tmp_path / "project"
    project_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    quick_root = project_root / ".planning" / "quick"
    quick_root.mkdir(parents=True)
    target_parent = quick_root / "001-demo"
    original_mkdir = Path.mkdir
    attempted_swap = False

    def racing_mkdir(self: Path, *args: object, **kwargs: object) -> None:
        nonlocal attempted_swap
        if self == target_parent and not attempted_swap:
            attempted_swap = True
            try:
                quick_root.rmdir()
            except OSError:
                pass
            if not quick_root.exists() and not _create_directory_link(quick_root, outside):
                pytest.skip("directory junction creation is not available")
        return original_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", racing_mkdir)

    try:
        scaffold_artifact(
            project_root,
            kind="quick-status",
            out_path=".planning/quick/001-demo/STATUS.md",
        )
    except ArtifactScaffoldError as exc:
        assert "unsafe_path" in str(exc)

    assert attempted_swap
    assert not (outside / "001-demo").exists()
    assert not (outside / "STATUS.md").exists()


@pytest.mark.skipif(os.name != "nt", reason="Windows junction race coverage")
def test_scaffold_blocks_parent_swap_before_create_only_open(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    project_root = tmp_path / "project"
    project_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    target = project_root / ".planning" / "quick" / "001-demo" / "STATUS.md"
    target_parent = target.parent
    original_open = Path.open
    attempted_swap = False

    def racing_open(self: Path, *args: object, **kwargs: object):
        nonlocal attempted_swap
        if self == target and not attempted_swap:
            attempted_swap = True
            try:
                target_parent.rmdir()
            except OSError:
                pass
            if not target_parent.exists() and not _create_directory_link(
                target_parent, outside
            ):
                pytest.skip("directory junction creation is not available")
        return original_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "open", racing_open)

    try:
        scaffold_artifact(
            project_root,
            kind="quick-status",
            out_path=".planning/quick/001-demo/STATUS.md",
        )
    except ArtifactScaffoldError as exc:
        assert "unsafe_path" in str(exc)

    assert attempted_swap
    assert not (outside / "STATUS.md").exists()
    assert not (project_root / ".planning" / "quick" / "STATUS.md").exists()


def _create_directory_link(link: Path, target: Path) -> bool:
    try:
        link.symlink_to(target, target_is_directory=True)
        return True
    except OSError:
        if os.name != "nt":
            return False

    completed = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(link), str(target)],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return completed.returncode == 0


def test_reject_symlink_escape_rejects_resolved_parent_outside_root(tmp_path: Path):
    project_root = tmp_path / "project"
    project_root.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()

    with pytest.raises(ArtifactScaffoldError, match="unsafe_path"):
        _reject_symlink_escape(
            project_root.resolve(),
            outside / "STATUS.md",
            [project_root / ".planning" / "quick"],
        )


def test_quick_status_scaffold_writes_create_only_compact_payload(tmp_path: Path):
    payload = scaffold_artifact(
        tmp_path,
        kind="quick-status",
        out_path=".planning/quick/001-demo/STATUS.md",
        variables={
            "id": "001",
            "slug": "001-demo",
            "title": "Demo",
            "trigger": "manual",
        },
    )

    output = tmp_path / ".planning" / "quick" / "001-demo" / "STATUS.md"
    text = output.read_text(encoding="utf-8")

    assert payload["status"] == "created"
    assert payload["kind"] == "quick-status"
    assert payload["path"] == ".planning/quick/001-demo/STATUS.md"
    assert payload["estimated_token_savings"] > 0
    assert payload["agent_fill_required"]
    assert payload["fill_targets"]["current_focus"]["anchor"] == "agent-fill:current_focus"
    assert "understanding_confirmed: false" in text
    assert "status: gathering" in text
    assert "<!-- agent-fill:current_focus -->" in text

    with pytest.raises(ArtifactScaffoldError, match="blocked_existing_file"):
        scaffold_artifact(
            tmp_path,
            kind="quick-status",
            out_path=".planning/quick/001-demo/STATUS.md",
        )


def test_quick_status_scaffold_escapes_markdown_yaml_quotes(tmp_path: Path):
    scaffold_artifact(
        tmp_path,
        kind="quick-status",
        out_path=".planning/quick/001-demo/STATUS.md",
        variables={
            "id": "001",
            "slug": "001-demo",
            "title": 'Demo "quoted"',
            "trigger": 'manual "trigger"',
        },
    )

    output = tmp_path / ".planning" / "quick" / "001-demo" / "STATUS.md"
    text = output.read_text(encoding="utf-8")

    assert 'title: "Demo \\"quoted\\""' in text
    assert 'trigger: "manual \\"trigger\\""' in text


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("title", 'Demo"\nunderstanding_confirmed: true\nx: "'),
        ("trigger", 'manual"\nstatus: resolved\nx: "'),
        ("title", "Demo --- injected"),
        ("trigger", "manual ... injected"),
    ],
)
def test_quick_status_scaffold_rejects_unsafe_markdown_variables(
    tmp_path: Path, key: str, value: str
):
    output = tmp_path / ".planning" / "quick" / "001-demo" / "STATUS.md"

    with pytest.raises(ArtifactScaffoldError, match="unsafe_variable"):
        scaffold_artifact(
            tmp_path,
            kind="quick-status",
            out_path=".planning/quick/001-demo/STATUS.md",
            variables={
                "id": "001",
                "slug": "001-demo",
                "title": "Demo",
                "trigger": "manual",
                key: value,
            },
        )

    assert not output.exists()


@pytest.mark.parametrize(
    "variables",
    [
        {"status": "ready"},
        {"handoff_to_tasks_ready": True},
        {"ready": True},
        {"approved": True},
        {"user_confirmed": True},
        {"understanding_confirmed": True},
        {"planning_gate_status": "approved"},
    ],
)
def test_plan_contract_scaffold_rejects_unsafe_status_variables(
    tmp_path: Path, variables: dict[str, object]
):
    output = tmp_path / "specs" / "001-demo" / "plan-contract.json"

    with pytest.raises(ArtifactScaffoldError, match="unsafe_status"):
        scaffold_artifact(
            tmp_path,
            kind="plan-contract",
            out_path="specs/001-demo/plan-contract.json",
            variables=variables,
        )

    assert not output.exists()

@pytest.mark.parametrize(
    "variables",
    [
        {"status": "pending"},
        {"handoff_to_tasks_ready": False},
        {"implementation_target": {"target_root": "src"}},
    ],
)
def test_plan_contract_scaffold_rejects_existing_non_fill_target_variables(
    tmp_path: Path, variables: dict[str, object]
):
    output = tmp_path / "specs" / "001-demo" / "plan-contract.json"

    with pytest.raises(ArtifactScaffoldError, match="unsafe_variable"):
        scaffold_artifact(
            tmp_path,
            kind="plan-contract",
            out_path="specs/001-demo/plan-contract.json",
            variables=variables,
        )

    assert not output.exists()


@pytest.mark.parametrize(
    "variables",
    [
        {"consequence_gate": {"status": "ready"}},
        {"implementation_target": {"approved": True}},
        {"status": {"ready": True}},
        {"must_preserve": [[{"status": "ready"}]]},
    ],
)
def test_plan_contract_scaffold_rejects_nested_readiness_overrides(
    tmp_path: Path, variables: dict[str, object]
):
    output = tmp_path / "specs" / "001-demo" / "plan-contract.json"

    with pytest.raises(ArtifactScaffoldError, match="unsafe_status"):
        scaffold_artifact(
            tmp_path,
            kind="plan-contract",
            out_path="specs/001-demo/plan-contract.json",
            variables=variables,
        )

    assert not output.exists()


def test_quick_status_scaffold_does_not_replace_status_like_markdown_variables(
    tmp_path: Path,
):
    scaffold_artifact(
        tmp_path,
        kind="quick-status",
        out_path=".planning/quick/001-demo/STATUS.md",
        variables={"understanding_confirmed": False},
    )

    output = tmp_path / ".planning" / "quick" / "001-demo" / "STATUS.md"
    text = output.read_text(encoding="utf-8")

    assert "understanding_confirmed: false" in text


def test_plan_contract_scaffold_writes_safe_json_skeleton(tmp_path: Path):
    payload = scaffold_artifact(
        tmp_path,
        kind="plan-contract",
        out_path="specs/001-demo/plan-contract.json",
        variables={"route": "quick", "ignored": "value"},
    )

    output = tmp_path / "specs" / "001-demo" / "plan-contract.json"
    data = json.loads(output.read_text(encoding="utf-8"))

    assert payload["status"] == "created"
    assert payload["path"] == "specs/001-demo/plan-contract.json"
    assert data["status"] == "pending"
    assert data["route"] == "quick"
    assert "ignored" not in data
    assert data["handoff_to_tasks_ready"] is False
    assert payload["fill_targets"]["route"]["pointer"] == "/route"


def test_plan_contract_scaffold_supports_nested_allowed_specs_plan_path(tmp_path: Path):
    scaffold_artifact(
        tmp_path,
        kind="plan-contract",
        out_path="specs/001-demo/plan/plan-contract.json",
    )

    output = tmp_path / "specs" / "001-demo" / "plan" / "plan-contract.json"
    data = json.loads(output.read_text(encoding="utf-8"))

    assert data["status"] == "pending"
    assert data["handoff_to_tasks_ready"] is False
