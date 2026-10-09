from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.integrations.base import IntegrationBase
from specify_cli.integrations.cursor_agent import CursorAgentIntegration
from specify_cli.launcher import write_runtime_launcher_config


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = (
    ROOT / "templates" / "artifacts" / "project-cognition-workflow-registry.json"
)
REGISTRY_SCHEMA_PATH = (
    ROOT
    / "templates"
    / "artifacts"
    / "project-cognition-workflow-registry.schema.json"
)

MUTATION_WORKFLOWS = {
    "debug": "sp-debug",
    "do": "sp-do",
    "e2e": "sp-e2e",
    "fast": "sp-fast",
    "implement": "sp-implement",
    "implement-teams": "sp-implement",
    "quick": "sp-quick",
    "review": "sp-review",
}
MAINTENANCE_WORKFLOWS = {"map-update": "sp-map-update"}
DIRECT_UPDATE_FRAGMENTS = (
    "specify-runtime cognition delta append --help",
    "specify-runtime cognition update --delta-session",
    "specify-runtime cognition update --payload-file",
)
STRUCTURED_PASSED_VERIFICATION = (
    '{"command":"<agent-owned verification command>","result":"passed",'
    '"artifact":"<optional evidence artifact>"}'
)


def _classic_surface(
    command_name: str,
    *,
    agent_name: str = "codex",
    script_type: str = "sh",
    project_root: Path | None = None,
) -> str:
    command_path = ROOT / "templates" / "commands" / f"{command_name}.md"
    owner_raw = command_path.read_text(encoding="utf-8")
    parts = [
        IntegrationBase.process_template(
            owner_raw,
            agent_name,
            script_type,
            "$ARGUMENTS",
            template_path=command_path,
            project_root=project_root,
        )
    ]
    references_dir = ROOT / "templates" / "command-references" / command_name
    if references_dir.is_dir():
        for reference_path in sorted(references_dir.rglob("*.md")):
            parts.append(
                IntegrationBase.render_command_reference_content(
                    reference_path.read_text(encoding="utf-8"),
                    owner_template_raw=owner_raw,
                    owner_template_path=command_path,
                    reference_path=reference_path,
                    agent_name=agent_name,
                    script_type=script_type,
                    arg_placeholder="$ARGUMENTS",
                    project_root=project_root,
                )
            )
    return "\n".join(parts)


def _generated_classic_surface(command_name: str) -> str:
    command_path = ROOT / "templates" / "commands" / f"{command_name}.md"
    owner_raw = command_path.read_text(encoding="utf-8")
    owner = IntegrationBase.process_template(
        owner_raw,
        "codex",
        "sh",
        "$ARGUMENTS",
        template_path=command_path,
    )
    owner = IntegrationBase()._append_runtime_project_cognition_gate(
        content=owner,
        agent_name="Test Agent",
        command_name=command_name,
    )
    parts = [owner]
    references_dir = ROOT / "templates" / "command-references" / command_name
    if references_dir.is_dir():
        for reference_path in sorted(references_dir.rglob("*.md")):
            parts.append(
                IntegrationBase.render_command_reference_content(
                    reference_path.read_text(encoding="utf-8"),
                    owner_template_raw=owner_raw,
                    owner_template_path=command_path,
                    reference_path=reference_path,
                    agent_name="codex",
                    script_type="sh",
                    arg_placeholder="$ARGUMENTS",
                )
            )
    return "\n".join(parts)


def test_closeout_registry_is_schema_valid_and_covers_every_classic_workflow() -> None:
    registry = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    schema = json.loads(REGISTRY_SCHEMA_PATH.read_text(encoding="utf-8"))

    assert registry["$schema"] == REGISTRY_SCHEMA_PATH.name
    assert registry["schema_version"] == 1
    assert schema["$id"] == REGISTRY_SCHEMA_PATH.name
    validated = IntegrationBase.project_cognition_workflow_registry()
    assert validated == registry

    policies = registry["workflows"]
    command_names = {
        path.stem for path in (ROOT / "templates" / "commands").glob("*.md")
    }
    assert set(policies) == command_names
    assert {
        name: policy["canonical_workflow"]
        for name, policy in policies.items()
        if policy["mode"] == "mutation_closeout"
    } == MUTATION_WORKFLOWS
    assert {
        name: policy["canonical_workflow"]
        for name, policy in policies.items()
        if policy["mode"] == "map_maintenance"
    } == MAINTENANCE_WORKFLOWS


@pytest.mark.parametrize(
    ("template_path", "canonical_workflow"),
    (
        (
            Path("workspace/commands/checkout/templates/commands/fast.md"),
            "sp-fast",
        ),
        (
            Path(
                "workspace/commands/checkout/specify_cli/core_pack/commands/review.md"
            ),
            "sp-review",
        ),
        (
            Path(
                "workspace/command-references/checkout/templates/command-references/quick/validation.md"
            ),
            "sp-quick",
        ),
        (
            Path(
                "workspace/command-partials/checkout/templates/command-partials/implement/shell.md"
            ),
            "sp-implement",
        ),
    ),
)
def test_workflow_token_owner_uses_the_nearest_template_topology(
    template_path: Path,
    canonical_workflow: str,
) -> None:
    assert (
        IntegrationBase.render_project_cognition_workflow_token(
            "{{project-cognition-workflow}}",
            template_path,
        )
        == canonical_workflow
    )


@pytest.mark.parametrize(
    ("command_name", "canonical_workflow"), MUTATION_WORKFLOWS.items()
)
def test_classic_mutation_workflows_render_literal_canonical_closeout_ids(
    command_name: str,
    canonical_workflow: str,
) -> None:
    rendered = _classic_surface(command_name)

    assert f"specify-runtime cognition closeout-plan --workflow {canonical_workflow}" in rendered
    assert "--scope-mode explicit" in rendered
    assert "$ACTIVE_WORKFLOW" not in rendered
    assert "{{project-cognition-workflow}}" not in rendered


@pytest.mark.parametrize(
    ("command_name", "canonical_workflow"), MUTATION_WORKFLOWS.items()
)
def test_generated_mutation_surface_has_one_closeout_contract(
    command_name: str,
    canonical_workflow: str,
) -> None:
    rendered = _generated_classic_surface(command_name)
    lowered = rendered.lower()

    assert rendered.count("### Inline Project Cognition Update") == 1
    assert (
        rendered.count(
            f"specify-runtime cognition closeout-plan --workflow {canonical_workflow}"
        )
        == 2
    )
    assert (
        lowered.count(
            "clean completion requires that receipt-bound finalizer to succeed"
        )
        == 1
    )
    assert "apply_argv" in rendered
    assert "scope_result_state" in rendered
    for update_shape in DIRECT_UPDATE_FRAGMENTS:
        assert update_shape not in rendered


@pytest.mark.parametrize(
    ("command_name", "canonical_workflow"), MUTATION_WORKFLOWS.items()
)
def test_spx_mutation_workflows_own_literal_canonical_closeout_commands(
    command_name: str,
    canonical_workflow: str,
) -> None:
    skill = (
        ROOT / "templates" / "advanced-skills" / f"spx-{command_name}" / "SKILL.md"
    ).read_text(encoding="utf-8")

    assert f"specify-runtime cognition closeout-plan --workflow {canonical_workflow}" in skill
    assert "--scope-mode explicit" in skill
    assert "$ACTIVE_WORKFLOW" not in skill
    assert "<canonical-sp-workflow>" not in skill


def test_rendered_classic_commands_and_references_have_no_renderer_residue() -> None:
    for command_path in sorted((ROOT / "templates" / "commands").glob("*.md")):
        rendered = _classic_surface(command_path.stem)
        assert "{{spec-kit-include:" not in rendered, command_path.name
        assert "$ACTIVE_WORKFLOW" not in rendered, command_path.name
        assert "{{project-cognition-workflow}}" not in rendered, command_path.name


def test_generated_template_sources_do_not_depend_on_active_workflow_environment() -> None:
    for path in sorted((ROOT / "templates").rglob("*")):
        if path.is_file() and path.suffix.lower() in {".md", ".json", ".toml"}:
            assert "$ACTIVE_WORKFLOW" not in path.read_text(
                encoding="utf-8"
            ), path.relative_to(ROOT)

    for relative_path in ("README.md", "PROJECT-HANDBOOK.md"):
        assert "$ACTIVE_WORKFLOW" not in (ROOT / relative_path).read_text(
            encoding="utf-8"
        ), relative_path


def test_classic_map_update_has_one_planner_first_update_path() -> None:
    rendered = _classic_surface("map-update")

    planner = "specify-runtime cognition closeout-plan --workflow sp-map-update"
    assert rendered.count(planner) == 1
    assert "--changed-path" in rendered
    assert "apply_argv" in rendered
    for fragment in DIRECT_UPDATE_FRAGMENTS:
        assert fragment not in rendered


def test_spx_map_update_uses_the_registry_canonical_workflow() -> None:
    skill = (
        ROOT / "templates" / "advanced-skills" / "spx-map-update" / "SKILL.md"
    ).read_text(encoding="utf-8")

    assert "specify-runtime cognition closeout-plan --workflow sp-map-update" in skill
    assert "specify-runtime cognition closeout-plan --workflow map-update" not in skill


def test_map_update_profiles_use_the_receipt_bound_finalizer_for_no_op() -> None:
    classic = _classic_surface("map-update")
    spx = (
        ROOT / "templates" / "advanced-skills" / "spx-map-update" / "SKILL.md"
    ).read_text(encoding="utf-8")

    for content in (classic, spx):
        _assert_receipt_finalizer_gate(content)
        _assert_audit_only_inputs(content)
        assert "`no_op` result may finish freshness metadata" not in content


def test_non_mutation_workflows_do_not_conditionally_claim_mutation_closeout() -> None:
    non_mutation = {
        path.stem for path in (ROOT / "templates" / "commands").glob("*.md")
    } - set(MUTATION_WORKFLOWS) - set(MAINTENANCE_WORKFLOWS) - {
        "map-build",
        "map-scan",
    }

    for command_name in sorted(non_mutation):
        classic = (
            ROOT / "templates" / "commands" / f"{command_name}.md"
        ).read_text(encoding="utf-8")
        spx = (
            ROOT
            / "templates"
            / "advanced-skills"
            / f"spx-{command_name}"
            / "SKILL.md"
        ).read_text(encoding="utf-8")
        assert "inline-project-cognition-update.md" not in classic, command_name
        assert "specify-runtime cognition closeout-plan --workflow" not in spx, command_name

    planning_context = (
        ROOT
        / "templates"
        / "command-partials"
        / "common"
        / "planning-context-loading-gradient.md"
    ).read_text(encoding="utf-8")
    assert "inline-project-cognition-update.md" not in planning_context
    assert "planning-only" in planning_context.lower()

    base = IntegrationBase()
    for command_name in ("specify", "plan", "tasks"):
        rendered = base._append_planning_skill_cognition_refresh_guidance(
            content=f"# {command_name}\n",
            command_name=command_name,
        )
        assert "## Project Cognition Navigation (Planning Only)" in rendered
        assert "specify-runtime cognition status --format json" in rendered
        assert ".specify/project-cognition/status.json" not in rendered
        assert ".specify/project-cognition/project-cognition.db" not in rendered
        assert "Git-baseline freshness" in rendered
        assert "specify-runtime cognition closeout-plan --workflow" not in rendered
        assert "run inline project cognition update" not in rendered
        for fragment in DIRECT_UPDATE_FRAGMENTS:
            assert fragment not in rendered


def test_readme_separates_planning_handoff_from_mutation_closeout() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "Planning-only workflows do not acquire source mutation authority" in readme
    assert "hand off to a registry-owned mutation workflow" in readme
    assert "unless they actually change source/runtime/template/config/test/generated-asset surfaces" not in readme
    assert "Shared `specify-runtime cognition closeout apply`" in readme
    assert "completes refresh only when globally eligible" in readme
    assert "`scope_result_state`/`scope_partial_reasons`" in readme
    assert "`update_argv` remains low-level compatibility/debug only" in readme
    assert "Clean closeout gates on `result_state=ready` or `result_state=no_op`, not `status=ok`" not in readme


@pytest.mark.parametrize(
    "command_name",
    MUTATION_WORKFLOWS,
)
def test_shared_integration_gate_does_not_duplicate_closeout_contract(
    command_name: str,
) -> None:
    original = "# Workflow\n"
    rendered = IntegrationBase()._append_runtime_project_cognition_gate(
        content=original,
        agent_name="Test Agent",
        command_name=command_name,
    )

    assert "specify-runtime cognition closeout-plan --workflow" not in rendered
    assert "update_argv" not in rendered
    for fragment in DIRECT_UPDATE_FRAGMENTS:
        assert fragment not in rendered
    if command_name in IntegrationBase.RUNTIME_SUBAGENT_CONTRACT_COMMANDS:
        assert "Project Cognition Advisory Gate" in rendered
        assert "single semantic owner is the shared inline closeout contract" in rendered
    else:
        assert rendered == original


def test_cursor_advisory_does_not_reintroduce_direct_update_commands() -> None:
    addendum = CursorAgentIntegration._cursor_project_cognition_advisory_addendum()

    assert "follow the rendered planner-first closeout contract" in addendum.lower()
    for fragment in DIRECT_UPDATE_FRAGMENTS:
        assert fragment not in addendum


def _assert_receipt_finalizer_gate(content: str) -> None:
    normalized = " ".join(content.split())
    validate = "specify-runtime cognition validate-build --format json"
    finalize = "specify-runtime cognition complete-refresh --format json"
    assert validate in content
    assert finalize in content
    assert content.index(validate) < content.index(finalize)
    assert "ready|no_op" in content
    assert "scope_result_state" in content
    assert "scope_ready" in content
    assert "apply_argv" in content
    assert "status=ok" in content
    assert "readiness=query_ready" in content
    assert "validate-build receipt" in content or "bound receipt" in content
    assert "pending finalization" in content
    for blocked_state in (
        "partial_refresh",
        "needs_rebuild",
        "blocked",
        "recorded",
    ):
        assert blocked_state in content
    assert "must not run" in normalized
    assert "`complete-refresh`" in content


def _assert_audit_only_inputs(content: str) -> None:
    assert "audit-only `path_changes`" in content
    assert "graph-changing `changed_paths`" in content
    assert "free-text verification" in content
    assert "result=recorded" in content
    assert "structured" in content
    assert "result=passed" in content


def test_classic_inline_closeout_requires_receipt_bound_finalization() -> None:
    partial = (
        ROOT
        / "templates"
        / "command-partials"
        / "common"
        / "inline-project-cognition-update.md"
    ).read_text(encoding="utf-8")

    _assert_receipt_finalizer_gate(partial)
    _assert_audit_only_inputs(partial)
    assert STRUCTURED_PASSED_VERIFICATION in partial
    assert "array of command-result strings" not in partial


def test_shared_closeout_transport_keeps_completed_payload_off_process_argv() -> None:
    surfaces = (
        ROOT
        / "templates"
        / "command-partials"
        / "common"
        / "inline-project-cognition-update.md",
        ROOT
        / "templates"
        / "advanced-skills"
        / "_shared"
        / "project-cognition.md",
    )

    for surface in surfaces:
        content = surface.read_text(encoding="utf-8")
        normalized = " ".join(content.split()).lower()
        assert "--payload-json -" in content, surface
        assert "completed payload" in normalized and "stdin" in normalized, surface
        assert "substitute that object for `<inline-json>` in `apply_argv`" not in content, surface
        assert "--payload-json '<inline-json>'" not in content, surface


def test_shared_closeout_recovers_only_the_direct_pending_predecessor() -> None:
    contract_surfaces = (
        ROOT
        / "templates"
        / "command-partials"
        / "common"
        / "inline-project-cognition-update.md",
        ROOT
        / "templates"
        / "advanced-skills"
        / "_shared"
        / "project-cognition.md",
        ROOT
        / "templates"
        / "passive-skills"
        / "spec-kit-project-cognition-gate"
        / "SKILL.md",
    )

    for surface in contract_surfaces:
        content = surface.read_text(encoding="utf-8")
        assert "`pending_finalization`" in content, surface
        assert "one direct predecessor" in content, surface
        assert "`predecessor_recovery`" in content, surface
        assert "current mutation accounting" in content, surface
        assert "must not scan older" in content, surface


def test_shared_closeout_contract_owns_atomic_intent_replay_and_identity_repair() -> None:
    surfaces = (
        ROOT
        / "templates"
        / "command-partials"
        / "common"
        / "inline-project-cognition-update.md",
        ROOT
        / "templates"
        / "advanced-skills"
        / "_shared"
        / "project-cognition.md",
        ROOT
        / "templates"
        / "passive-skills"
        / "spec-kit-project-cognition-gate"
        / "SKILL.md",
    )

    for surface in surfaces:
        content = surface.read_text(encoding="utf-8")
        assert "same update lock" in content, surface
        assert "mutation intent" in content, surface
        assert "`predecessor_recovery_blocked`" in content, surface
        assert "cognition closeout replay" in content, surface
        assert "cognition identity-repair plan" in content, surface
        assert "cognition identity-repair apply" in content, surface

    for surface in (
        ROOT / "README.md",
        ROOT / "PROJECT-HANDBOOK.md",
        ROOT / "templates" / "project-handbook-template.md",
    ):
        content = surface.read_text(encoding="utf-8")
        assert "mutation intent" in content, surface
        assert "closeout replay" in content, surface

    for surface in (
        ROOT / "README.md",
        ROOT / "PROJECT-HANDBOOK.md",
        ROOT / "templates" / "project-handbook-template.md",
    ):
        content = surface.read_text(encoding="utf-8")
        assert "one direct predecessor" in content, surface
        assert "pending_finalization" in content, surface


def _assert_closeout_intent_recovery_contract(content: str) -> None:
    normalized = " ".join(content.split())
    for required in (
        "repair_update_or_replay_intent",
        "cognition closeout inspect",
        "cognition closeout repair",
        "--intent-id",
        "--expected-digest",
        "--verification-json -",
        "blocked_intent_id",
        "input_digest",
        "repair_argv",
        "replay_argv",
        "intent_repaired",
        "replacement_intent_id",
        "replacement_input_digest",
        "blocked scope receipt",
        "Stop retrying the same failing apply",
        "Never invent verification commands",
        "Do not edit or delete intent JSON",
        "do not rebuild merely",
    ):
        assert required in normalized, required


@pytest.mark.parametrize(
    "relative_path",
    (
        "templates/command-partials/common/inline-project-cognition-update.md",
        "templates/advanced-skills/_shared/project-cognition.md",
        "templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md",
    ),
)
def test_shared_closeout_contract_has_receipt_independent_intent_recovery(
    relative_path: str,
) -> None:
    surface = ROOT / relative_path
    _assert_closeout_intent_recovery_contract(
        IntegrationBase.render_template_content(
            surface.read_text(encoding="utf-8"), template_path=surface
        )
    )


@pytest.mark.parametrize("command_name", (*MUTATION_WORKFLOWS, *MAINTENANCE_WORKFLOWS))
def test_classic_mutation_workflows_render_intent_recovery(command_name: str) -> None:
    _assert_closeout_intent_recovery_contract(_classic_surface(command_name))


@pytest.mark.parametrize("agent_name", ("codex", "claude", "gemini", "cursor-agent"))
@pytest.mark.parametrize("script_type", ("sh", "ps"))
def test_closeout_intent_recovery_renders_across_cli_integrations(
    tmp_path: Path, agent_name: str, script_type: str
) -> None:
    binary = tmp_path / ".specify" / "bin" / "specify-runtime"
    binary.parent.mkdir(parents=True)
    binary.write_text("runtime", encoding="utf-8")
    write_runtime_launcher_config(tmp_path, binary)
    content = _classic_surface(
        "fast", agent_name=agent_name, script_type=script_type, project_root=tmp_path
    )

    _assert_closeout_intent_recovery_contract(content)
    assert "{{specify-subcmd:" not in content


def test_greenfield_with_project_code_uses_structured_rebuild_recovery() -> None:
    surfaces = (
        ROOT
        / "templates"
        / "command-partials"
        / "common"
        / "context-loading-gradient.md",
        ROOT
        / "templates"
        / "advanced-skills"
        / "_shared"
        / "project-cognition.md",
        ROOT
        / "templates"
        / "passive-skills"
        / "spec-kit-project-cognition-gate"
        / "SKILL.md",
    )

    for surface in surfaces:
        content = surface.read_text(encoding="utf-8")
        assert "greenfield_baseline_has_project_code" in content, surface
        assert "project_cognition.rebuild" in content, surface
        assert "map-update" in content, surface
        assert "must not" in content.lower(), surface


def test_blocked_compass_degraded_reads_remain_bounded_advisory_navigation() -> None:
    surfaces = (
        ROOT
        / "templates"
        / "command-partials"
        / "common"
        / "context-loading-gradient.md",
        ROOT
        / "templates"
        / "advanced-skills"
        / "_shared"
        / "project-cognition.md",
        ROOT
        / "templates"
        / "passive-skills"
        / "spec-kit-project-cognition-gate"
        / "SKILL.md",
    )

    for surface in surfaces:
        content = surface.read_text(encoding="utf-8")
        assert "stale_cognition_degraded_navigation" in content, surface
        assert "degraded=true" in content, surface
        assert "minimal_live_reads" in content, surface
        assert "live repository" in content.lower(), surface


def test_fast_pre_work_map_maintenance_cannot_bypass_validation_receipt() -> None:
    fast = (ROOT / "templates" / "commands" / "fast.md").read_text(
        encoding="utf-8"
    )

    assert (
        "After a successful existing-baseline maintenance refresh, use "
        "`{{specify-subcmd:specify-runtime cognition complete-refresh --format json}}`"
    ) not in fast
    assert "receipt-bound `validate-build` then `complete-refresh` sequence" in fast


def test_unknown_path_dispositions_reach_the_typed_update_contract() -> None:
    classic_partial = (
        ROOT
        / "templates"
        / "command-partials"
        / "common"
        / "inline-project-cognition-update.md"
    ).read_text(encoding="utf-8")
    classic_map_update = (
        ROOT / "templates" / "commands" / "map-update.md"
    ).read_text(encoding="utf-8")
    spx_shared = (
        ROOT / "templates" / "advanced-skills" / "_shared" / "project-cognition.md"
    ).read_text(encoding="utf-8")
    spx_map_update = (
        ROOT / "templates" / "advanced-skills" / "spx-map-update" / "SKILL.md"
    ).read_text(encoding="utf-8")

    for content in (classic_partial, classic_map_update, spx_shared, spx_map_update):
        assert "path_changes[].disposition" in content
        assert "agent_disposition" in content
    assert "--path-disposition" in classic_partial


def test_spx_shared_and_owning_mutation_skills_require_receipt_finalization() -> None:
    shared = (
        ROOT / "templates" / "advanced-skills" / "_shared" / "project-cognition.md"
    ).read_text(encoding="utf-8")
    _assert_receipt_finalizer_gate(shared)
    _assert_audit_only_inputs(shared)
    assert STRUCTURED_PASSED_VERIFICATION in shared

    for command_name in MUTATION_WORKFLOWS:
        skill = (
            ROOT
            / "templates"
            / "advanced-skills"
            / f"spx-{command_name}"
            / "SKILL.md"
        ).read_text(encoding="utf-8")
        normalized_skill = " ".join(skill.split())
        assert "apply_argv" in skill, command_name
        assert "owns update, validation, eligible finalization" in normalized_skill, command_name
        assert "references/project-cognition.md" in skill, command_name


@pytest.mark.parametrize(
    ("command_name", "canonical_workflow"), MUTATION_WORKFLOWS.items()
)
def test_generated_mutation_surface_requires_receipt_bound_finalization(
    command_name: str,
    canonical_workflow: str,
) -> None:
    content = _generated_classic_surface(command_name)

    assert f"closeout-plan --workflow {canonical_workflow}" in content
    _assert_receipt_finalizer_gate(content)
    _assert_audit_only_inputs(content)
