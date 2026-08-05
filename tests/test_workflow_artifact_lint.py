from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli import app
from specify_cli.workflow_artifact_lint import (
    WorkflowArtifactRegistryError,
    default_workflow_artifact_scan_paths,
    load_workflow_artifact_registry,
    scan_workflow_artifact_instructions,
)


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "templates" / "workflow-artifact-registry.json"
RUNNER = CliRunner()


def test_workflow_artifact_registry_is_present_and_parseable() -> None:
    registry = load_workflow_artifact_registry(REGISTRY_PATH)

    assert registry.version >= 1
    assert registry.artifacts
    assert registry.allowlist == ()


def test_registry_covers_runtime_owned_storage_roots() -> None:
    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    patterns_by_id = {
        artifact.id: set(artifact.path_patterns) for artifact in registry.artifacts
    }

    assert ".specify/evidence/**" in patterns_by_id["evidence_store"]
    assert ".specify/runtime/**" in patterns_by_id["runtime_internal_artifacts"]
    assert (
        ".specify/project-cognition/.cognitionignore"
        in patterns_by_id["project_cognition_ignore"]
    )
    assert ".specify/extensions.yml" in patterns_by_id["extension_hook_config"]
    assert {
        ".specify/evidence/**",
        ".specify/runtime/**",
        ".specify/worker-results/**",
    }.issubset(patterns_by_id["workflow_storage_boundary"])


def test_registry_agent_owned_operations_do_not_use_bare_specify_runtime_entries() -> (
    None
):
    raw = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    offenders: list[tuple[str, str, str]] = []

    for artifact in raw["artifacts"]:
        for field in ("owner_cli", "safe_instruction_patterns"):
            for entry in artifact.get(field, []):
                if isinstance(entry, str) and entry.startswith("specify "):
                    offenders.append((artifact["id"], field, entry))

    assert offenders == []


def test_workflow_artifact_registry_rejects_invalid_allowlist_reason(
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "workflow-artifact-registry.json"
    registry_path.write_text(
        json.dumps(
            {
                "version": 1,
                "artifacts": [
                    {
                        "id": "spec_contract",
                        "path_patterns": ["**/spec-contract.json"],
                        "path_hints": ["spec-contract.json"],
                        "owner_cli": [
                            "specify-runtime artifact prepare --path <project-relative-path>",
                            "specify-runtime artifact submit --lease <lease-id> --content '<inline-content>'",
                        ],
                    }
                ],
                "allowlist": [
                    {
                        "path": "templates/commands/specify.md",
                        "artifact_id": "spec_contract",
                        "operation": "write",
                        "line_pattern": "write `spec-contract.json`",
                        "reason": "   ",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(WorkflowArtifactRegistryError, match="allowlist entry reason"):
        load_workflow_artifact_registry(registry_path)


def test_registered_owner_cli_instruction_is_not_reported(tmp_path: Path) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text(
        "\n".join(
            [
                "Use `specify-runtime artifact prepare --path <project-relative-path>`.",
                "Then run `specify-runtime artifact submit --lease <lease-id> --content '<inline-content>'`.",
            ]
        ),
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert report.violations == []


def test_scaffold_owned_artifact_rejects_whole_file_submit_guidance(
    tmp_path: Path,
) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text(
        "Create `spec-contract.json` through `specify-runtime artifact prepare|submit`.\n",
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert [(item.artifact_id, item.operation) for item in report.violations] == [
        ("spec_contract", "submit")
    ]
    assert "scaffold and targeted patch" in report.violations[0].message


def test_negated_whole_file_submit_guidance_remains_valid(tmp_path: Path) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text(
        "Never create `spec-contract.json` through `artifact submit`; use `artifact scaffold --kind spec-contract` and targeted `artifact patch`.\n",
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert report.violations == []


@pytest.mark.parametrize(
    "option",
    [
        "--content-file",
        "--result-file",
        "--recovery-file",
        "--input",
        "--payload-file",
        "--semantic-intake-file",
        "--query-plan-file",
    ],
)
def test_agent_facing_temporary_file_handoff_is_reported(
    tmp_path: Path, option: str
) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text(
        f"Run `specify-runtime artifact submit {option} <temporary-file>`.\n",
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert [(item.artifact_id, item.artifact_hint) for item in report.violations] == [
        ("temporary_authoring_payload", option)
    ]


def test_negated_temporary_file_handoff_is_allowed_as_guardrail(tmp_path: Path) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text(
        "Never create a result file or use `--result-file`; submit JSON inline.\n",
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert report.violations == []


def test_runtime_prepared_input_packet_is_allowed(tmp_path: Path) -> None:
    source = tmp_path / "command.md"
    source.write_text(
        "Run `specify-runtime cognition claim-reconcile apply --input "
        "<prepared_packet_path> --format json`; the packet is runtime-created.\n",
        encoding="utf-8",
    )

    report = scan_workflow_artifact_instructions(
        [source], load_workflow_artifact_registry(REGISTRY_PATH)
    )

    assert report.violations == []


def test_inline_json_input_option_is_allowed(tmp_path: Path) -> None:
    source = tmp_path / "team.md"
    source.write_text(
        'Run `sp-teams api claim-task --input \'{"task_id":"T001"}\' --json`.\n',
        encoding="utf-8",
    )

    report = scan_workflow_artifact_instructions(
        [source], load_workflow_artifact_registry(REGISTRY_PATH)
    )

    assert report.violations == []


def test_direct_debug_state_field_write_is_reported(tmp_path: Path) -> None:
    source = tmp_path / "debug.md"
    source.write_text(
        "Update the debug session `Current Focus` before dispatch.\n",
        encoding="utf-8",
    )

    report = scan_workflow_artifact_instructions(
        [source], load_workflow_artifact_registry(REGISTRY_PATH)
    )

    assert [(item.artifact_id, item.operation) for item in report.violations] == [
        ("debug_artifacts", "write")
    ]


def test_debug_session_patch_macro_is_allowed(tmp_path: Path) -> None:
    source = tmp_path / "debug.md"
    source.write_text(
        "`SESSION PATCH` the debug session `Current Focus` before dispatch.\n",
        encoding="utf-8",
    )

    report = scan_workflow_artifact_instructions(
        [source], load_workflow_artifact_registry(REGISTRY_PATH)
    )

    assert report.violations == []


def test_direct_write_instruction_for_registered_artifact_is_reported(
    tmp_path: Path,
) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text(
        "Write `spec-contract.json` first, then render the project-facing artifacts.\n",
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert len(report.violations) == 1
    violation = report.violations[0]
    assert violation.artifact_id == "spec_contract"
    assert violation.operation == "write"
    assert violation.path == prompt


def test_legacy_implementation_handoff_draft_is_reported(tmp_path: Path) -> None:
    prompt = tmp_path / "implement.md"
    prompt.write_text(
        "Create `.tmp-implementation-handoff-contract.json` before closeout.\n",
        encoding="utf-8",
    )

    report = scan_workflow_artifact_instructions(
        [prompt], load_workflow_artifact_registry(REGISTRY_PATH)
    )

    assert [(item.artifact_id, item.operation) for item in report.violations] == [
        ("legacy_implementation_handoff_draft", "write")
    ]


def test_later_negative_condition_does_not_hide_positive_write(
    tmp_path: Path,
) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text(
        "Write `context.md` only when stable refs cannot carry the evidence.\n",
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert [(item.artifact_id, item.operation) for item in report.violations] == [
        ("feature_views", "write")
    ]


def test_owner_cli_in_another_clause_does_not_pardon_direct_write(
    tmp_path: Path,
) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text(
        "Use `specify-runtime artifact submit` for another record. Write `spec-contract.json` directly.\n",
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert [(item.artifact_id, item.operation) for item in report.violations] == [
        ("spec_contract", "write")
    ]


def test_anaphoric_direct_update_after_artifact_sentence_is_reported(
    tmp_path: Path,
) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text(
        "The debug session file is the source of truth. Update it before every action.\n",
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert [(item.artifact_id, item.operation) for item in report.violations] == [
        ("debug_artifacts", "write")
    ]


def test_anaphoric_update_through_owner_cli_is_not_reported(tmp_path: Path) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text(
        "The debug session file is the source of truth. Update it only through "
        "`specify-runtime artifact patch`.\n",
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert report.violations == []


def test_gerund_direct_write_to_registered_artifact_is_reported(
    tmp_path: Path,
) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text(
        "Finish by writing improved results into `spec.md`.\n",
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert [(item.artifact_id, item.operation) for item in report.violations] == [
        ("feature_spec", "write")
    ]


def test_generic_filesystem_handoff_write_is_reported(tmp_path: Path) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text(
        "Without a managed channel, write the result to the declared filesystem handoff path.\n",
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert [(item.artifact_id, item.operation) for item in report.violations] == [
        ("worker_result", "write")
    ]


def test_unlisted_artifact_under_workflow_storage_is_still_guarded(
    tmp_path: Path,
) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text(
        "Write `.specify/features/001-demo/new-state.json` directly.\n",
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert [(item.artifact_id, item.operation) for item in report.violations] == [
        ("workflow_storage_boundary", "write")
    ]


def test_unlisted_workflow_storage_path_must_still_route_through_cli(
    tmp_path: Path,
) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text(
        "Create `.specify/features/001-demo/new-state.json` only through "
        "`specify-runtime artifact prepare` plus inline `artifact submit`.\n",
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert report.violations == []


def test_explicitly_negated_direct_operation_is_not_reported(tmp_path: Path) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text(
        "Do not create or write `spec-contract.json` directly.\n",
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert report.violations == []


def test_repo_tree_is_green_without_exceptions_and_new_violation_fails(
    tmp_path: Path,
) -> None:
    registry = load_workflow_artifact_registry(REGISTRY_PATH)

    repo_report = scan_workflow_artifact_instructions(
        default_workflow_artifact_scan_paths(ROOT),
        registry,
    )
    assert repo_report.violations == []
    assert registry.allowlist == ()

    prompt = tmp_path / "new-command.md"
    prompt.write_text(
        "Append one compact event to `discussion-log.jsonl` before returning.\n",
        encoding="utf-8",
    )

    report = scan_workflow_artifact_instructions([prompt], registry)

    assert [violation.operation for violation in report.violations] == ["append"]
    assert report.violations[0].artifact_id == "discussion_log"


def test_default_scan_includes_live_guidance_but_not_historical_design_records() -> (
    None
):
    paths = default_workflow_artifact_scan_paths(ROOT)

    assert ROOT / "templates" in paths
    assert ROOT / "AGENTS.md" in paths
    assert ROOT / "README.md" in paths
    assert ROOT / "PROJECT-HANDBOOK.md" in paths
    assert ROOT / "src" / "specify_cli" / "integrations" in paths
    assert ROOT / "src" / "specify_cli" / "__init__.py" in paths
    assert ROOT / "src" / "specify_cli" / "learnings.py" in paths
    assert ROOT / "src" / "specify_cli" / "hooks" / "learning.py" in paths
    assert ROOT / "src" / "specify_cli" / "hooks" / "state_validation.py" in paths
    assert ROOT / "scripts" / "bash" / "update-agent-context.sh" in paths
    assert ROOT / "scripts" / "powershell" / "update-agent-context.ps1" in paths
    assert ROOT / "docs" / "upgrade.md" in paths
    assert ROOT / "docs" / "design" in paths
    assert all("superpowers" not in path.parts for path in paths)


def test_direct_read_instruction_for_registered_artifact_is_reported(
    tmp_path: Path,
) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text("Read `task-index.json` and choose a task.\n", encoding="utf-8")

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert [item.operation for item in report.violations] == ["read"]
    assert report.violations[0].artifact_id == "task_index"


def test_later_cli_reference_does_not_excuse_an_earlier_raw_read(
    tmp_path: Path,
) -> None:
    prompt = tmp_path / "handbook.md"
    prompt.write_text(
        "Read `.specify/project-cognition/status.json` plus the task-local "
        "`specify-runtime cognition compass` packet.\n",
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert ("project_cognition_artifacts", "read") in {
        (item.artifact_id, item.operation) for item in report.violations
    }


def test_multiline_read_heading_applies_to_artifact_bullets(tmp_path: Path) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text(
        "Before continuing, read:\n\n- `.specify/project-cognition/status.json`\n",
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert ("project_cognition_artifacts", "read") in {
        (item.artifact_id, item.operation) for item in report.violations
    }


def test_multiline_required_reference_can_use_registered_owner_cli(
    tmp_path: Path,
) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text(
        "Required references:\n\n"
        "- Query `.specify/project-cognition/status.json` through "
        "`specify-runtime cognition status --format json`.\n",
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert report.violations == []


@pytest.mark.parametrize(
    "instruction",
    [
        "Use `.specify/project-cognition/status.json` to assess readiness.",
        "Include `.specify/project-cognition/status.json` in teammate context.",
        "Check whether `.specify/project-cognition/status.json` exists.",
    ],
)
def test_implicit_artifact_reads_require_the_owner_cli(
    tmp_path: Path, instruction: str
) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text(instruction + "\n", encoding="utf-8")

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert ("project_cognition_artifacts", "read") in {
        (item.artifact_id, item.operation) for item in report.violations
    }


def test_extension_config_existence_probe_is_reported(tmp_path: Path) -> None:
    prompt = tmp_path / "extension.md"
    prompt.write_text(
        "Check if `.specify/extensions.yml` exists, then read its hooks.\n",
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert ("extension_hook_config", "read") in {
        (item.artifact_id, item.operation) for item in report.violations
    }


def test_extension_hook_plan_owns_extension_config_read(tmp_path: Path) -> None:
    prompt = tmp_path / "extension.md"
    prompt.write_text(
        "Run `specify-runtime hook extension-plan --event before_plan --format json`; "
        "never inspect `.specify/extensions.yml`.\n",
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert report.violations == []


def test_review_verb_for_registered_handoff_counts_as_a_read(tmp_path: Path) -> None:
    prompt = tmp_path / "review.md"
    prompt.write_text(
        "Review `.specify/discussions/<slug>/handoff-to-specify.json`.\n",
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert ("discussion_handoff", "read") in {
        (item.artifact_id, item.operation) for item in report.violations
    }


def test_review_through_registered_owner_cli_is_allowed(tmp_path: Path) -> None:
    prompt = tmp_path / "review.md"
    prompt.write_text(
        "Review `.specify/discussions/<slug>/handoff-to-specify.json` through "
        "`specify-runtime artifact show --path <path> --view full`.\n",
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert report.violations == []


def test_legacy_python_runtime_command_is_reported(tmp_path: Path) -> None:
    prompt = tmp_path / "templates" / "commands" / "prompt.md"
    prompt.parent.mkdir(parents=True)
    prompt.write_text(
        "Run `specify workflow transition --to review --feature-dir <feature-dir>`.\n",
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert [(item.artifact_id, item.operation) for item in report.violations] == [
        ("legacy_python_runtime", "invoke")
    ]


@pytest.mark.parametrize(
    "instruction",
    [
        "Agents consume it through `specify learning start --command plan`.",
        "Run `python -m specify_cli learning capture-auto --command plan`.",
        "Run `{{specify-subcmd:learning promote --target rule}}`.",
        "Let `specify sp-teams` materialize the team state.",
    ],
)
def test_agent_control_plane_cannot_fall_back_to_python_cli(
    tmp_path: Path, instruction: str
) -> None:
    prompt = tmp_path / "templates" / "commands" / "prompt.md"
    prompt.parent.mkdir(parents=True)
    prompt.write_text(instruction + "\n", encoding="utf-8")

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert ("legacy_python_runtime", "invoke") in {
        (item.artifact_id, item.operation) for item in report.violations
    }


def test_human_learning_maintenance_command_is_allowed(tmp_path: Path) -> None:
    prompt = tmp_path / "README.md"
    prompt.write_text(
        "Human operators may run `specify learning ensure --format json`.\n",
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert report.violations == []


def test_negated_legacy_python_runtime_warning_is_allowed(tmp_path: Path) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text(
        "Do not probe `specify cognition` or `python -m specify workflow`.\n",
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert report.violations == []


def test_inline_evidence_cannot_masquerade_as_an_existing_object_path(
    tmp_path: Path,
) -> None:
    prompt = tmp_path / "templates" / "advanced-skills" / "review.md"
    prompt.parent.mkdir(parents=True)
    prompt.write_text(
        "Run `specify-runtime evidence register --object '<inline-json>'`.\n",
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert ("invalid_runtime_invocation", "invoke") in {
        (item.artifact_id, item.operation) for item in report.violations
    }


def test_python_generator_instruction_is_scanned(tmp_path: Path) -> None:
    prompt = tmp_path / "integration.py"
    prompt.write_text(
        'guidance = (\n    "Read "\n    "`task-index.json` and choose a task.\\n"\n)\n',
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert [(item.artifact_id, item.operation) for item in report.violations] == [
        ("task_index", "read")
    ]


def test_toml_command_instruction_is_scanned(tmp_path: Path) -> None:
    prompt = tmp_path / "sp.tasks.toml"
    prompt.write_text(
        'prompt = "Run `node -e \\"require(\'./task-index.json\')\\"`."\n',
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert [(item.artifact_id, item.operation) for item in report.violations] == [
        ("task_index", "read")
    ]


def test_registered_instruction_source_catches_anaphoric_write(
    tmp_path: Path,
) -> None:
    prompt = tmp_path / "templates" / "design-brief-template.md"
    prompt.parent.mkdir()
    prompt.write_text(
        "This file stores the design brief. Update it after every answer.\n",
        encoding="utf-8",
    )

    raw = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    for artifact in raw["artifacts"]:
        if artifact["id"] == "design_scaffold_documents":
            artifact["instruction_sources"] = [prompt.as_posix()]
            break
    registry_path = tmp_path / "workflow-artifact-registry.json"
    registry_path.write_text(json.dumps(raw), encoding="utf-8")

    registry = load_workflow_artifact_registry(registry_path)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert [(item.artifact_id, item.operation) for item in report.violations] == [
        ("design_scaffold_documents", "write")
    ]


def test_direct_open_instruction_for_registered_artifact_is_reported(
    tmp_path: Path,
) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text("Open `task-index.json` and choose a task.\n", encoding="utf-8")

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert [item.operation for item in report.violations] == ["read"]
    assert report.violations[0].artifact_id == "task_index"


def test_direct_copy_of_registered_template_is_reported(tmp_path: Path) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text(
        "If `.specify/memory/constitution.md` is missing, copy the template first.\n",
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert ("constitution_memory", "copy") in [
        (item.artifact_id, item.operation) for item in report.violations
    ]


def test_later_patch_does_not_pardon_agent_reconstruction_from_template(
    tmp_path: Path,
) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text(
        "Scaffold `plan-contract.json` from `plan-contract-template.json`, then "
        "patch it with `specify-runtime artifact patch`.\n",
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert ("plan_contract", "write") in [
        (item.artifact_id, item.operation) for item in report.violations
    ]


def test_runtime_scaffold_command_can_expand_installed_template(tmp_path: Path) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text(
        "Create `plan-contract.json` through `specify-runtime artifact scaffold "
        "--kind plan-contract`; the runtime renders it from the installed template.\n",
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert report.violations == []


def test_unrelated_agent_fill_anchor_is_not_a_debug_state_instruction(
    tmp_path: Path,
) -> None:
    prompt = tmp_path / "quickstart.md"
    prompt.write_text(
        "<!-- agent-fill:verification_evidence -->\n",
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert report.violations == []


def test_owner_cli_later_in_clause_does_not_pardon_explicit_direct_read(
    tmp_path: Path,
) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text(
        "Read `task-index.json` directly, then use `specify-runtime artifact show` if needed.\n",
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert [(item.artifact_id, item.operation) for item in report.violations] == [
        ("task_index", "read")
    ]


def test_third_person_direct_mutation_is_reported(tmp_path: Path) -> None:
    prompt = tmp_path / "integration.py"
    prompt.write_text(
        'guidance = "The leader updates `task-index.json` after every lane.\\n"\n',
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert [(item.artifact_id, item.operation) for item in report.violations] == [
        ("task_index", "write")
    ]


@pytest.mark.parametrize(
    ("instruction", "expected_id"),
    [
        ("Read `.specify/evidence/records/EVD-1.json` directly.", "evidence_store"),
        (
            "Patch `.specify/runtime/transactions/txn-1.json`.",
            "runtime_internal_artifacts",
        ),
        ("Write `.specify/worker-results/lane-1.json`.", "worker_result"),
    ],
)
def test_direct_runtime_storage_operation_is_reported(
    tmp_path: Path, instruction: str, expected_id: str
) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text(instruction + "\n", encoding="utf-8")

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert expected_id in {item.artifact_id for item in report.violations}


@pytest.mark.parametrize(
    ("instruction", "operation"),
    [
        ("Run `cp seed.json task-index.json`.", "copy"),
        ("Run `Set-Content task-index.json $payload`.", "write"),
        ("Run `echo '{}' > task-index.json`.", "write"),
        ("Run `rm task-index.json`.", "delete"),
        ("Run `type task-index.json`.", "read"),
        ("Run `node -e \"const t=require('./task-index.json')\"`.", "read"),
        ("Run `fs.readFileSync('task-index.json')`.", "read"),
        ("Use `apply_patch` to change `task-index.json`.", "write"),
        ("Run `sed -i 's/old/new/' task-index.json`.", "write"),
        ("View `task-index.json` before choosing work.", "read"),
        ("Author `task-index.json` from the task list.", "write"),
        ("Populate `task-index.json` with acceptance rows.", "write"),
        ("Purge `task-index.json` before rebuilding it.", "delete"),
    ],
)
def test_filesystem_command_for_registered_artifact_is_reported(
    tmp_path: Path, instruction: str, operation: str
) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text(instruction + "\n", encoding="utf-8")

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert [(item.artifact_id, item.operation) for item in report.violations] == [
        ("task_index", operation)
    ]


@pytest.mark.parametrize(
    "instruction",
    [
        "The claim type matches `semantic-audit-input.json`.",
        "Runtime state lives under `.specify/teams/`; use the sync-ecc helper for config.",
        "The canonical path is `.specify/discussions/<slug>/handoff-to-specify.json`.",
    ],
)
def test_descriptive_shell_like_words_are_not_reported(
    tmp_path: Path, instruction: str
) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text(instruction + "\n", encoding="utf-8")

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert report.violations == []


def test_structured_data_fence_is_not_treated_as_an_instruction(tmp_path: Path) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text(
        '```json\n{"semantic_audit_input_path": "semantic-audit-input.json", "read_path": "src/app.py"}\n```\n',
        encoding="utf-8",
    )

    registry = load_workflow_artifact_registry(REGISTRY_PATH)
    report = scan_workflow_artifact_instructions([prompt], registry)

    assert report.violations == []


def test_workflow_artifact_lint_cli_fails_closed(tmp_path: Path) -> None:
    prompt = tmp_path / "prompt.md"
    prompt.write_text("Write `implementation-handoff.json`.\n", encoding="utf-8")

    result = RUNNER.invoke(
        app,
        [
            "workflow-artifacts",
            "lint",
            "--path",
            str(prompt),
            "--registry",
            str(REGISTRY_PATH),
            "--format",
            "json",
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["ok"] is False
    assert payload["violations"][0]["artifact_id"] == "implementation_handoff"
