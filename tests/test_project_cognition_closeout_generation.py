from __future__ import annotations

import json
from pathlib import Path

import pytest

from specify_cli.integrations.base import IntegrationBase
from specify_cli.integrations.cursor_agent import CursorAgentIntegration


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
    "fast": "sp-fast",
    "implement": "sp-implement",
    "implement-teams": "sp-implement",
    "integrate": "sp-integrate",
    "quick": "sp-quick",
    "review": "sp-review",
}
MAINTENANCE_WORKFLOWS = {"map-update": "sp-map-update"}
DIRECT_UPDATE_FRAGMENTS = (
    "project-cognition delta append --help",
    "project-cognition update --delta-session",
    "project-cognition update --payload-file",
)
STRUCTURED_PASSED_VERIFICATION = (
    '{"command":"<agent-owned verification command>","result":"passed",'
    '"artifact":"<optional evidence artifact>"}'
)


def _classic_surface(command_name: str) -> str:
    command_path = ROOT / "templates" / "commands" / f"{command_name}.md"
    owner_raw = command_path.read_text(encoding="utf-8")
    parts = [
        IntegrationBase.process_template(
            owner_raw,
            "codex",
            "sh",
            "$ARGUMENTS",
            template_path=command_path,
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
                    agent_name="codex",
                    script_type="sh",
                    arg_placeholder="$ARGUMENTS",
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

    assert f"project-cognition closeout-plan --workflow {canonical_workflow}" in rendered
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
            f"project-cognition closeout-plan --workflow {canonical_workflow}"
        )
        == 2
    )
    assert (
        lowered.count(
            "clean completion requires that receipt-bound finalizer to succeed"
        )
        == 1
    )
    assert "update_argv" in rendered
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

    assert f"project-cognition closeout-plan --workflow {canonical_workflow}" in skill
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

    planner = "project-cognition closeout-plan --workflow sp-map-update"
    assert rendered.count(planner) == 1
    assert "--changed-path" in rendered
    assert "update_argv" in rendered
    for fragment in DIRECT_UPDATE_FRAGMENTS:
        assert fragment not in rendered


def test_spx_map_update_uses_the_registry_canonical_workflow() -> None:
    skill = (
        ROOT / "templates" / "advanced-skills" / "spx-map-update" / "SKILL.md"
    ).read_text(encoding="utf-8")

    assert "project-cognition closeout-plan --workflow sp-map-update" in skill
    assert "project-cognition closeout-plan --workflow map-update" not in skill


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
        assert "project-cognition closeout-plan --workflow" not in spx, command_name

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
        assert ".specify/project-cognition/status.json" in rendered
        assert ".specify/project-cognition/project-cognition.db" in rendered
        assert "Git-baseline freshness" in rendered
        assert "project-cognition closeout-plan --workflow" not in rendered
        assert "run inline project cognition update" not in rendered
        for fragment in DIRECT_UPDATE_FRAGMENTS:
            assert fragment not in rendered


def test_readme_separates_planning_handoff_from_mutation_closeout() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "Planning-only workflows do not acquire source mutation authority" in readme
    assert "hand off to a registry-owned mutation workflow" in readme
    assert "unless they actually change source/runtime/template/config/test/generated-asset surfaces" not in readme
    assert "selects the finalization branch" in readme
    assert "Clean completion additionally requires" in readme
    assert "`status=ok` and `readiness=query_ready`" in readme
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

    assert "project-cognition closeout-plan --workflow" not in rendered
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
    validate = "project-cognition validate-build --format json"
    finalize = "project-cognition complete-refresh --format json"
    assert validate in content
    assert finalize in content
    assert content.index(validate) < content.index(finalize)
    assert "result_state=ready" in content
    assert "result_state=no_op" in content
    assert "status=ok" in content
    assert "readiness=query_ready" in content
    assert "validate-build receipt" in content
    assert "Compass/query" in content
    assert "pending finalization" in content
    for blocked_state in (
        "partial_refresh",
        "needs_rebuild",
        "blocked",
        "recorded",
    ):
        assert blocked_state in content
    assert "must not run `complete-refresh`" in content


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


def test_fast_pre_work_map_maintenance_cannot_bypass_validation_receipt() -> None:
    fast = (ROOT / "templates" / "commands" / "fast.md").read_text(
        encoding="utf-8"
    )

    assert (
        "After a successful existing-baseline maintenance refresh, use "
        "`{{specify-subcmd:project-cognition complete-refresh --format json}}`"
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
        assert "receipt-bound finalizer gate" in skill, command_name
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
