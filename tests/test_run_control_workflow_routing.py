from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from pathlib import Path

import pytest

from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest

from .template_utils import read_command_with_references, read_skill_with_references


ROOT = Path(__file__).resolve().parents[1]
TMP_ROOT = ROOT / ".tmp" / "test_execution_workflow_routing"
CLASSIC_EXECUTION_BOOTSTRAP = (
    ROOT / "templates" / "command-partials" / "common" / "execution-bootstrap.md"
)
ADVANCED_EXECUTION_BOOTSTRAP = (
    ROOT / "templates" / "advanced-skills" / "_shared" / "execution-bootstrap.md"
)
SKILLS_INTEGRATION_SAMPLE_KEYS = ("codex", "agy", "vibe", "zcode")
ACTIVITY_WORKFLOWS = ("fast", "debug", "implement", "quick")
ARTIFACT_WORKFLOWS = ("specify", "plan", "tasks", "review", "accept")
CLASSIC_MODIFYING_WORKFLOWS = ACTIVITY_WORKFLOWS + ARTIFACT_WORKFLOWS
ADVANCED_MODIFYING_WORKFLOWS = tuple(f"spx-{name}" for name in CLASSIC_MODIFYING_WORKFLOWS)

RETIRED_COMMAND = re.compile(
    r"\bspecify-runtime(?:\.exe)?\s+(?:"
    r"(?:run|snapshot|candidate|cas|sync)\b|"
    r"accept\s+receipt\b|result\s+(?:list|show|depend|reopen)\b)"
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _normalized(content: str) -> str:
    return " ".join(content.lower().replace(chr(96), "").split())


def _assert_no_retired_run_surface(content: str) -> None:
    lowered = _normalized(content)
    assert not RETIRED_COMMAND.search(lowered)
    for token in (
        "run-bootstrap.md",
        "specify_run_",
        "run.launch",
        "run supervise",
        "pre-launch snapshot",
        "sealed result",
        "immutable candidate",
        "frozen candidate",
        "unhosted",
    ):
        assert token not in lowered, token


def _assert_commands_in_order(content: str, commands: tuple[str, ...]) -> None:
    lowered = _normalized(content)
    cursor = 0
    for command in commands:
        position = lowered.find(f"specify-runtime {command}", cursor)
        assert position >= 0, (command, commands)
        cursor = position + len(f"specify-runtime {command}")


def _assert_shared_execution_contract(content: str) -> None:
    _assert_no_retired_run_surface(content)
    lowered = _normalized(content)
    _assert_commands_in_order(
        content,
        (
            "execution overview",
            "execution announce",
            "execution checkpoint",
            "execution overview",
            "execution guard",
            "execution checkpoint",
            "execution complete",
        ),
    )
    for token in (
        "current worktree",
        "sole durable ownership",
        "not a second owner",
        "native tooling",
        "coordination_revision",
        "snapshot_sha256",
        "--expected-overview-revision",
        "--expected-overview-sha256",
        "all-or-none",
        "semantic resource",
        "fresh passing validation",
        "task state is terminal",
        "product and canonical workflow git delta",
        ".specify",
        ".planning",
        "not an audit exemption",
        "every audited path outside confirmed scope blocks completion",
        "private runtime cache",
        "work recovery inspections are unchanged",
        "bookkeeping_write_scope",
        "full returned planned_write_scope",
        "never hand-edited",
        "serialized ownership",
        "inert preserved history",
        "must not delete",
        "safe additive metadata schema evolution is allowed",
        "recovery-held work remains active safety ownership",
        "exact current compiler output digest",
        "immutable baseline binding",
        "guard cannot widen",
        "recompile and reannounce",
        "--scope-amendments-json",
        "scope-drift-review",
        "original packet",
        "agent-owned recovery",
        "exact future files",
        "final /**",
        "validation commands",
        "official",
        "workflow mutations",
        "never edit it",
        ".workflow.lock",
        "same activity",
    ):
        assert token in lowered, token
    assert "fast|debug|implement|quick" in lowered
    assert "do not pass plan, specify, review, accept, map" in lowered


def _assert_shared_work_board_contract(content: str) -> None:
    lowered = _normalized(content)
    for command in (
        "board reconcile",
        "board show",
        "board feature-bootstrap",
        "work begin",
        "work claim",
        "work scope-add",
        "work checkpoint",
        "work block",
        "work unblock",
        "work finish",
        "work abandon",
        "work interrupt",
        "work resume",
    ):
        assert f"specify-runtime {command}" in lowered, command
    for token in (
        "sqlite cli projection",
        "do not edit",
        "artifact leases",
        "dirty recovery hold",
        "do not delete unknown edits",
        "conflict",
        "yield",
        "specify_work_id",
        "specify_work_fence",
        "not completion shortcuts",
        ".specify/runtime/run-control/run-control.sqlite",
        "legacy .git/specify-runtime/run-control.sqlite",
        "agent-owned",
    ):
        assert token in lowered, token


def _assert_stage_semantics(content: str, stage: str) -> None:
    _assert_no_retired_run_surface(content)
    lowered = _normalized(content)
    assert "current worktree" in lowered
    if stage in ACTIVITY_WORKFLOWS:
        assert "specify-runtime execution guard" in lowered
        assert "specify-runtime execution complete" in lowered
        assert "fresh passing validation" in lowered
    if stage == "specify":
        assert "specify-runtime board feature-bootstrap" in lowered
        assert "--resolved-feature-id <dry-run branch_name>" in lowered
    if stage in {"plan", "tasks"}:
        assert "work board" in lowered
        assert "workflow runtime" in lowered
        assert "artifact" in lowered
    if stage == "review":
        assert "implementation-handoff.json" in lowered
        assert "specify-runtime review prepare" in lowered
        assert "specify-runtime review target-bind" in lowered
        assert "independent" in lowered
        assert "fresh integrated evidence" in lowered
    if stage == "accept":
        assert "read-only with respect to product source" in lowered
        assert "actual final decision" in lowered
        assert "specify-runtime accept prepare" in lowered
        assert "specify-runtime accept closeout" in lowered
        assert "actual human reply" in lowered


def _install_skills_profile(project: Path, integration_key: str, profile: str) -> Path:
    integration = get_integration(integration_key)
    assert integration is not None
    manifest = IntegrationManifest(integration_key, project)
    integration.setup(
        project,
        manifest,
        parsed_options={"workflow_profile": profile},
        script_type="sh",
    )
    return integration.commands_dest(project)


def _mktemp_dir(prefix: str) -> Path:
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=TMP_ROOT))


@pytest.fixture(scope="session", autouse=True)
def isolate_project_launcher_bindings():
    name = "SPECIFY_PROJECT_LAUNCHER_STATE_DIR"
    previous = os.environ.get(name)
    path = _mktemp_dir("project-launcher-bindings-")
    os.environ[name] = str(path)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(scope="session", autouse=True)
def isolate_claude_config_dir():
    name = "CLAUDE_CONFIG_DIR"
    previous = os.environ.get(name)
    path = _mktemp_dir("claude-config-")
    os.environ[name] = str(path)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def local_tmp_path() -> Path:
    path = _mktemp_dir("case-")
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


@pytest.mark.parametrize(
    "path", (CLASSIC_EXECUTION_BOOTSTRAP, ADVANCED_EXECUTION_BOOTSTRAP)
)
def test_shared_bootstrap_preserves_execution_and_work_ownership(path: Path) -> None:
    assert path.is_file()
    assert not path.with_name("run-bootstrap.md").exists()
    content = path.read_text(encoding="utf-8")
    _assert_shared_execution_contract(content)
    _assert_shared_work_board_contract(content)


def test_classic_workflows_load_the_execution_contract_before_modification() -> None:
    include = "{{spec-kit-include: ../command-partials/common/execution-bootstrap.md}}"
    for stage in CLASSIC_MODIFYING_WORKFLOWS:
        if stage == "implement":
            entry = _read("templates/commands/implement.md")
            assert "references/task-intake-and-tracker.md" in entry
            reference = _read("templates/command-references/implement/task-intake-and-tracker.md")
            assert "../../command-partials/common/execution-bootstrap.md" in reference
        else:
            assert include in _read(f"templates/commands/{stage}.md"), stage


def test_advanced_workflows_load_the_renamed_shared_execution_reference() -> None:
    surface_map = json.loads(_read("templates/advanced-skills/_shared/surface-map.json"))
    assert "_shared/execution-bootstrap.md" in surface_map["shared_references"]
    assert "_shared/run-bootstrap.md" not in surface_map["shared_references"]
    for skill_name in ADVANCED_MODIFYING_WORKFLOWS:
        content = _read(f"templates/advanced-skills/{skill_name}/SKILL.md")
        assert "Read " + chr(96) + "references/execution-bootstrap.md" in content, skill_name


def test_durable_team_implementation_keeps_ordinary_ownership_and_existing_authority() -> None:
    classic = _normalized(read_command_with_references("implement-teams"))
    advanced = _normalized(
        read_skill_with_references(ROOT / "templates/advanced-skills/spx-implement-teams/SKILL.md")
    )
    for content in (classic, advanced):
        assert "execution-bootstrap.md" in content or "execution bootstrap" in content
        assert "existing user-authorized delivery scope" in content
        assert "already authorized transfer" in content
        assert "sync-back" in content
        _assert_no_retired_run_surface(content)


def test_feature_bootstrap_reserves_once_and_replays_the_exact_dry_run_identity() -> None:
    for relative in (
        "templates/commands/specify.md",
        "templates/advanced-skills/spx-specify/SKILL.md",
    ):
        lowered = _normalized(_read(relative))
        dry_run = lowered.index("--dry-run")
        contract = lowered.index("spec-kit-feature-bootstrap-v1", dry_run)
        reconcile = lowered.index("specify-runtime board reconcile", contract)
        show = lowered.index("specify-runtime board show", reconcile)
        reservation = lowered.index("specify-runtime board feature-bootstrap --feature-id", show)
        real_script = lowered.index("real create-feature script", reservation)
        assert dry_run < contract < reconcile < show < reservation < real_script
        assert lowered.count("specify-runtime board feature-bootstrap --feature-id") == 1
        for token in (
            "bootstrap_contract",
            "--resolved-feature-id <dry-run branch_name>",
            "-resolvedfeatureid <dry-run branch_name>",
            "--feature-dir <dry-run feature_dir>",
            "unchanged",
            "confirmed write intent",
            "data.work",
            "data.feature_branch_policy",
            "--keep-current-branch",
            "-keepcurrentbranch",
            "board was idle",
            "existing branch behavior",
            "explicit resume",
            "do not query specify-runtime board branch-policy before registration",
            "do not call specify-runtime work begin separately",
        ):
            assert token in lowered, (relative, token)
        _assert_no_retired_run_surface(lowered)


def test_restart_recovery_never_steals_live_work_or_discards_dirty_scope() -> None:
    for path in (CLASSIC_EXECUTION_BOOTSTRAP, ADVANCED_EXECUTION_BOOTSTRAP):
        lowered = _normalized(path.read_text(encoding="utf-8"))
        assert "active same-task work" in lowered
        assert "do not take it over" in lowered
        assert "old owner/session has ended" in lowered
        assert "must not interrupt another live agent" in lowered
        assert "dirty recovery hold" in lowered
        assert "work unblock" in lowered
        assert "current live owner" in lowered
        assert "preserves owner, fence" in lowered
        _assert_commands_in_order(lowered, ("work interrupt", "work resume"))
        assert "--expected-revision <n> --fence <n> --reason <reason>" in lowered


def test_packet_workers_register_exact_compiled_bytes_before_guard_and_native_dispatch() -> None:
    for relative in (
        "templates/commands/implement.md",
        "templates/advanced-skills/spx-implement/SKILL.md",
    ):
        content = _normalized(_read(relative))
        for token in (
            "packet-compile",
            "canonical path",
            "--work-packet-file <receipt.path> --work-packet-sha256 <receipt.sha256>",
            "specify-runtime execution announce --workflow implement",
            "--agent-id <agent-id>",
            "--adapter-id <adapter-id>",
            "before parsing",
            "planned_write_scope",
            "bookkeeping_write_scope",
            "full returned planned_write_scope",
            "do not reconstruct or override",
            "canonical packet path",
            "exact current compiler output digest",
            "immutable baseline binding",
            "guard cannot widen packet-backed scope",
            "recompile and reannounce",
            "semantic scope",
            "native worker dispatch",
            "work_claim",
            "in_progress",
            "--scope-amendments-json",
            "scope-drift-review",
            "same invocation",
            "workflow.json",
            "official",
            "runtime mutation receipt",
            ".workflow.lock",
            "same activity",
        ):
            assert token in content, (relative, token)
        _assert_no_retired_run_surface(content)


@pytest.mark.parametrize("workflow", ACTIVITY_WORKFLOWS)
def test_activity_workflow_sources_preserve_guard_and_validated_completion(workflow: str) -> None:
    classic = read_command_with_references(workflow)
    advanced = read_skill_with_references(
        ROOT / f"templates/advanced-skills/spx-{workflow}/SKILL.md"
    )
    for content in (classic, advanced):
        _assert_stage_semantics(content, workflow)


def test_context_direct_keeps_execution_gates_without_creating_full_workflow_state() -> None:
    for relative in (
        "templates/command-partials/common/context-sufficiency-choice.md",
        "templates/advanced-skills/_shared/context-sufficiency-choice.md",
    ):
        content = _normalized(_read(relative))
        _assert_commands_in_order(
            content, ("execution overview", "execution announce", "execution guard", "execution complete")
        )
        assert "snapshot_sha256" in content
        assert "fresh passing validation" in content
        assert "terminal direct-task state" in content
        assert "skip" in content and "learning start" in content


def test_packet_template_keeps_bookkeeping_separate_from_product_and_ui_contract() -> None:
    packet = json.loads(_read("templates/task-packet-template.json"))
    assert packet["write_scope"] == []
    assert packet["bookkeeping_write_scope"] == []
    assert "bookkeeping_write_scope" not in packet["ui_contract"]
    assert packet["ui_contract"]["source_continuity"]["schema"] == "spec-kit-ui-source-continuity-v1"
    for path in (CLASSIC_EXECUTION_BOOTSTRAP, ADVANCED_EXECUTION_BOOTSTRAP):
        content = _normalized(path.read_text(encoding="utf-8"))
        for canonical_path in (
            "task-index.json",
            "tasks.md",
            "workflow.json",
            "implement-tracker.md",
            "implementation-review/execution-state.json",
            "implementation-review/tasks/<task-id>.json",
            "worker-results/<task-id>.json",
        ):
            assert canonical_path in content
        assert "guard must use the full returned planned_write_scope" in content
        assert "bookkeeping remains cli-owned, never hand-edited" in content
        assert "no wildcard" in content
        assert "serialized ownership" in content


def test_review_and_human_acceptance_keep_product_evidence_and_result_channels() -> None:
    review = read_command_with_references("review")
    accept = read_command_with_references("accept")
    implement = read_command_with_references("implement")
    _assert_stage_semantics(review, "review")
    _assert_stage_semantics(accept, "accept")
    for token in ("structure_snapshot", "visual_capture", "runtime_diagnostics", "result submit"):
        assert token in review
    assert "WorkerTaskResult" in implement
    assert "result-merge" in implement
    assert "rerun every frozen human scenario" in accept


@pytest.mark.parametrize("integration_key", SKILLS_INTEGRATION_SAMPLE_KEYS)
def test_generated_classic_skills_preserve_execution_and_acceptance_contracts(
    local_tmp_path: Path, integration_key: str
) -> None:
    root = _install_skills_profile(local_tmp_path / f"{integration_key}-classic", integration_key, "classic")
    for stage in CLASSIC_MODIFYING_WORKFLOWS:
        content = read_skill_with_references(root / f"sp-{stage}" / "SKILL.md")
        _assert_stage_semantics(content, stage)


@pytest.mark.parametrize("integration_key", SKILLS_INTEGRATION_SAMPLE_KEYS)
def test_generated_advanced_skills_preserve_execution_and_acceptance_contracts(
    local_tmp_path: Path, integration_key: str
) -> None:
    root = _install_skills_profile(local_tmp_path / f"{integration_key}-advanced", integration_key, "advanced")
    shared = root / "references" / "execution-bootstrap.md"
    assert shared.is_file()
    assert not shared.with_name("run-bootstrap.md").exists()
    bootstrap = shared.read_text(encoding="utf-8")
    _assert_shared_execution_contract(bootstrap)
    for stage in CLASSIC_MODIFYING_WORKFLOWS:
        content = read_skill_with_references(root / f"spx-{stage}" / "SKILL.md")
        assert "references/execution-bootstrap.md" in content
        _assert_stage_semantics(content + "\n" + bootstrap, stage)
