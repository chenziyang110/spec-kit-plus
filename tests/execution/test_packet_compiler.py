import json
from pathlib import Path

import pytest

from specify_cli.execution.packet_compiler import (
    _ui_contract_from_task_entry,
    compile_worker_task_packet,
)
from specify_cli.execution.packet_validator import PacketValidationError
from specify_cli.execution.result_schema import (
    RuleAcknowledgement,
    UIVerification,
    ValidationResult,
    WorkerTaskResult,
)
from specify_cli.execution.result_validator import validate_worker_task_result


def test_compile_worker_task_packet_prefers_canonical_task_index_for_jit_packet(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)
    memory_dir = project_root / ".specify" / "memory"
    memory_dir.mkdir(parents=True)
    (memory_dir / "constitution.md").write_text(
        "# Constitution\n\n- Preserve public behavior and prove validation.\n",
        encoding="utf-8",
    )
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {
                "version": 2,
                "status": "ready",
                "tasks": [
                    {
                        "id": "T017",
                        "objective": "Implement auth flow",
                        "expected_write_scope": ["src/services/auth_service.py"],
                        "read_scope": ["src/contracts/auth.py"],
                        "required_refs": ["src/contracts/auth.py"],
                        "forbidden_drift": ["Do not create a parallel auth stack"],
                        "acceptance": ["Auth flow passes the real service test"],
                        "verification": ["pytest tests/unit/test_auth_service.py -q"],
                        "must_preserve_refs": ["MP-001"],
                        "consequence_obligation_refs": ["CA-001"],
                        "capability_operation_refs": ["CAP-auth"],
                        "required_consumer_evidence": ["real_entrypoint_evidence"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    packet = compile_worker_task_packet(
        project_root=project_root,
        feature_dir=feature_dir,
        task_id="T017",
    )

    assert packet.objective == "Implement auth flow"
    assert packet.scope.write_scope == ["src/services/auth_service.py"]
    assert "src/contracts/auth.py" in packet.scope.read_scope
    assert packet.validation_gates == ["pytest tests/unit/test_auth_service.py -q"]
    assert packet.acceptance_criteria == ["Auth flow passes the real service test"]
    assert packet.capability_operations == ["CAP-auth"]
    assert packet.required_evidence == ["real_entrypoint_evidence"]
    assert [item.id for item in packet.must_preserve_obligations] == ["MP-001"]
    assert [item.obligation_id for item in packet.consequence_obligations] == ["CA-001"]


def test_compile_worker_task_packet_prefers_structured_task_index_ui_contract(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-ui-feature"
    feature_dir.mkdir(parents=True)
    memory_dir = project_root / ".specify" / "memory"
    memory_dir.mkdir(parents=True)
    (memory_dir / "constitution.md").write_text(
        "# Constitution\n\n- Preserve the approved UI contract.\n",
        encoding="utf-8",
    )
    (feature_dir / "plan-contract.json").write_text(
        json.dumps(
            {
                "ui_design_contract": {
                    "ui_applicable": True,
                    "entry_points": ["/settings"],
                    "token_strategy": ["reuse settings tokens"],
                    "component_strategy": ["reuse settings form controls"],
                },
                "context_capsule": {
                    "minimal_live_reads": ["src/ui/theme.ts"],
                    "validation_routes": ["tests/e2e/settings.spec.ts"],
                },
            }
        ),
        encoding="utf-8",
    )
    (feature_dir / "task-index.json").write_text(
        json.dumps(
            {
                "version": 2,
                "status": "ready",
                "tasks": [
                    {
                        "id": "T021",
                        "objective": "Implement the responsive settings surface",
                        "expected_write_scope": ["src/ui/settings.tsx"],
                        "verification": ["npm test -- settings-ui"],
                        "acceptance": ["Desktop and mobile states match the UI brief"],
                        "ui_contract": {
                            "ui_work_type": "feature-extension",
                            "surface_type": "product-workspace",
                            "platforms": ["web"],
                            "subject": "account settings",
                            "audience": "signed-in account owners",
                            "single_job": "review and update account preferences",
                            "visual_thesis": "compact hierarchy keeps settings scannable",
                            "content_thesis": "render real preference labels and saved values",
                            "interaction_thesis": "changes provide immediate local feedback",
                            "signature_element": "persistent section progress rail",
                            "approved_visual_ref": "DESIGN.md#settings-direction",
                            "design_sources": [
                                "DESIGN.md",
                                "specs/001-ui-feature/ui-brief.md",
                            ],
                            "reference_notes": "specs/001-ui-feature/ui-reference-notes.md",
                            "visual_target": "specs/001-ui-feature/ui-target.html",
                            "reference_intents": [
                                {
                                    "ref": "specs/001-ui-feature/ui-target.html",
                                    "intent": "preserve-structure",
                                }
                            ],
                            "real_content_plan": [
                                {
                                    "source_ref": "src/settings/schema.ts",
                                    "applies_to_states": ["ready", "error"],
                                }
                            ],
                            "image_plan": [],
                            "fidelity_level": "high",
                            "must_preserve": ["compact two-column hierarchy"],
                            "may_adapt": ["framework markup"],
                            "must_not": ["collapse settings into cards"],
                            "required_states": ["loading", "error", "success"],
                            "required_evidence": [
                                "structure_snapshot",
                                "visual_capture",
                                "runtime_diagnostics",
                                "visual_comparison_or_human_review",
                            ],
                        },
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n- [ ] T021 Implement UI without duplicated markdown contract\n",
        encoding="utf-8",
    )

    packet = compile_worker_task_packet(
        project_root=project_root,
        feature_dir=feature_dir,
        task_id="T021",
    )

    assert packet.ui_contract.fidelity_level == "high"
    assert packet.ui_contract.surface_type == "product-workspace"
    assert packet.ui_contract.approved_visual_ref == "DESIGN.md#settings-direction"
    assert packet.ui_contract.reference_intents[0]["intent"] == "preserve-structure"
    assert (
        packet.ui_contract.real_content_plan[0]["source_ref"]
        == "src/settings/schema.ts"
    )
    assert packet.ui_contract.required_states == ["loading", "error", "success"]
    assert packet.ui_contract.must_not == ["collapse settings into cards"]
    assert packet.ui_contract.required_evidence == [
        "structure_snapshot",
        "visual_capture",
        "runtime_diagnostics",
        "visual_comparison_or_human_review",
    ]
    assert {item["kind"] for item in packet.context_nav} >= {
        "ui_entrypoint",
        "design_source",
        "minimal_live_read",
        "visual_test_route",
    }
    assert "src/ui/theme.ts" in {item.path for item in packet.context_bundle}
    reference_paths = [item.path for item in packet.required_references]
    assert "DESIGN.md" in reference_paths
    assert "specs/001-ui-feature/ui-brief.md" in reference_paths

    documented_result = WorkerTaskResult(
        task_id="T021",
        status="success",
        changed_files=["src/ui/settings.tsx"],
        validation_results=[
            ValidationResult(
                command="npm test -- settings-ui",
                status="passed",
                output="settings UI tests passed",
            )
        ],
        ui_evidence=[
            {
                "kind": "structure_snapshot",
                "ref": "artifacts/ui/settings-structure.json",
            },
            {
                "kind": "visual_capture",
                "ref": "artifacts/ui/settings.png",
            },
            {
                "kind": "runtime_diagnostics",
                "ref": "artifacts/ui/settings-runtime.txt",
            },
        ],
        ui_verification=UIVerification(
            contract_check="pass",
            runtime_evidence="pass",
            visual_comparison="passed",
            fidelity_status="passed",
        ),
        summary="Implemented and visually verified the settings surface.",
        rule_acknowledgement=RuleAcknowledgement(
            required_references_read=True,
            forbidden_drift_respected=True,
            context_bundle_read=True,
            paths_read=[
                item.path for item in packet.context_bundle if item.must_read
            ],
        ),
    )

    assert validate_worker_task_result(documented_result, packet) is documented_result


def test_current_ui_contract_rejects_obsolete_version_and_duplicate_payload() -> None:
    with pytest.raises(PacketValidationError, match="contract_version"):
        _ui_contract_from_task_entry({"ui_contract": {"contract_version": 2}})

    with pytest.raises(PacketValidationError, match="ui_fidelity_requirements"):
        _ui_contract_from_task_entry(
            {"ui_contract": {"fidelity_level": "high"}, "ui_fidelity_requirements": {}}
        )


def test_compile_worker_task_packet_rejects_malformed_canonical_task_index(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)
    (feature_dir / "task-index.json").write_text("{not-json", encoding="utf-8")
    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n- [ ] T017 Implement fallback behavior in src/fallback.py\n",
        encoding="utf-8",
    )

    with pytest.raises(PacketValidationError, match="task-index.json is malformed"):
        compile_worker_task_packet(
            project_root=project_root,
            feature_dir=feature_dir,
            task_id="T017",
        )


def test_compile_worker_task_packet_rejects_task_missing_from_canonical_index(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)
    (feature_dir / "task-index.json").write_text(
        json.dumps({"version": 2, "status": "ready", "tasks": []}),
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "# Tasks\n\n- [ ] T017 Implement stale rendered behavior in src/stale.py\n",
        encoding="utf-8",
    )

    with pytest.raises(PacketValidationError, match="T017 is missing from canonical task-index.json"):
        compile_worker_task_packet(
            project_root=project_root,
            feature_dir=feature_dir,
            task_id="T017",
        )


def test_compile_worker_task_packet_merges_constitution_plan_and_task_sources(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)
    (project_root / ".specify" / "memory").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition" / "status.json").write_text(
        '{"version": 1, "graph_ready": true}\n',
        encoding="utf-8",
    )
    (project_root / ".specify" / "project-cognition" / "project-cognition.db").write_bytes(
        b"SQLite test database marker"
    )
    (project_root / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n\n- MUST add tests for public behavior\n",
        encoding="utf-8",
    )
    (feature_dir / "plan.md").write_text(
        "\n".join(
            [
                "## Implementation Constitution",
                "",
                "### Required Implementation References",
                "",
                "- `src/contracts/auth.py`",
                "",
                "### Forbidden Implementation Drift",
                "",
                "- Do not create a parallel auth stack",
                "",
                "### Platform Guardrails",
                "",
                "- supported_platforms: windows, linux",
                "- require conditional compilation for unix-only APIs",
                "",
                "### Completion Handoff Protocol",
                "",
                "- send task_started before long-running work",
                "- write structured result handoff before idling",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "\n".join(
            [
                "## Validation Gates",
                "",
                "- pytest tests/unit/test_auth_service.py -q",
                "",
                "## Consequence Obligation Mapping",
                "",
                "| Obligation ID | Task IDs | Affected State/Dependency | Required References | Validation | Stop/Reopen Condition |",
                "| --- | --- | --- | --- | --- | --- |",
                "| CA-001 | T017 | team, worker | src/contracts/auth.py | pytest tests/unit/test_auth_service.py -q | No validation proves drain behavior |",
                "",
                "- [ ] T017 [US1] Implement auth flow in src/services/auth_service.py",
            ]
        ),
        encoding="utf-8",
    )

    packet = compile_worker_task_packet(
        project_root=project_root,
        feature_dir=feature_dir,
        task_id="T017",
    )

    assert packet.task_id == "T017"
    assert packet.story_id == "US1"
    assert "src/contracts/auth.py" in [ref.path for ref in packet.required_references]
    assert any("public behavior" in rule.lower() for rule in packet.hard_rules)
    assert packet.scope.write_scope == ["src/services/auth_service.py"]
    assert packet.validation_gates == ["pytest tests/unit/test_auth_service.py -q"]
    assert [item.path for item in packet.context_bundle] == [
        ".specify/project-cognition/status.json",
        ".specify/project-cognition/project-cognition.db",
        "src/contracts/auth.py",
    ]
    assert [item.read_order for item in packet.context_bundle] == list(range(1, 4))
    assert packet.context_bundle[0].kind == "project_cognition"
    assert packet.context_bundle[1].kind == "project_cognition"
    assert packet.context_bundle[-1].kind == "task_reference"
    assert ".specify/project-cognition/status.json" in packet.scope.read_scope
    assert ".specify/project-cognition/project-cognition.db" in packet.scope.read_scope
    assert ".specify/project-cognition/slices/change.json" not in packet.scope.read_scope
    assert ".specify/project-cognition/slices/debug.json" not in packet.scope.read_scope
    assert "PROJECT-HANDBOOK.md" not in packet.scope.read_scope
    assert packet.platform_guardrails == [
        "supported_platforms: windows, linux",
        "require conditional compilation for unix-only APIs",
    ]
    assert packet.handoff_requirements[-2:] == [
        "send task_started before long-running work",
        "write structured result handoff before idling",
    ]
    assert packet.consequence_obligations[0].obligation_id == "CA-001"
    assert packet.consequence_obligations[0].affected_objects == ["team", "worker"]
    assert packet.consequence_obligations[0].recovery_validation_refs == ["pytest tests/unit/test_auth_service.py -q"]


def test_compile_worker_task_packet_carries_capability_operation_guards(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)
    (project_root / ".specify" / "memory").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition" / "status.json").write_text(
        '{"version": 1, "graph_ready": true}\n',
        encoding="utf-8",
    )
    (project_root / ".specify" / "project-cognition" / "project-cognition.db").write_bytes(
        b"SQLite test database marker"
    )
    (project_root / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n\n- MUST add tests for public behavior\n",
        encoding="utf-8",
    )
    (feature_dir / "plan.md").write_text(
        "\n".join(
            [
                "## Required Implementation References",
                "",
                "- `src/cli/new.ts`",
                "",
                "## Forbidden Implementation Drift",
                "",
                "- Do not add public commands beyond jx-skills/check/publish",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "\n".join(
            [
                "## Validation Gates",
                "",
                "- npm test -- tests/cli/new.test.ts",
                "",
                "## Capability Operation Coverage",
                "",
                "| Operation | Upstream Source | Selected Entry Point | Task IDs / Packet Fields | Validation | Degradation Check |",
                "| --- | --- | --- | --- | --- | --- |",
                "| create/scaffold skill | spec.md#capability-preservation-ledger | TUI route | T017, does_not_remove, capability_operations | npm test -- tests/cli/new.test.ts | not template-only / not manual-copy-only |",
                "",
                "## Task Guardrail Index",
                "",
                "- T017 -> does-not-remove guard: preserve create/scaffold skill via TUI route",
                "",
                "- [ ] T017 [US1] Implement authoring route in src/cli/new.ts",
            ]
        ),
        encoding="utf-8",
    )

    packet = compile_worker_task_packet(
        project_root=project_root,
        feature_dir=feature_dir,
        task_id="T017",
    )

    assert packet.does_not_remove == ["preserve create/scaffold skill via TUI route"]
    assert packet.capability_operations == ["create/scaffold skill -> TUI route"]


def test_compile_worker_task_packet_reads_enriched_task_contract_fields(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)
    (project_root / ".specify" / "memory").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition" / "status.json").write_text(
        '{"version": 1, "graph_ready": true}\n',
        encoding="utf-8",
    )
    (project_root / ".specify" / "project-cognition" / "project-cognition.db").write_bytes(
        b"SQLite test database marker"
    )
    (project_root / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n\n- MUST add tests for public behavior\n",
        encoding="utf-8",
    )
    (feature_dir / "plan.md").write_text(
        "\n".join(
            [
                "## Required Implementation References",
                "",
                "- `src/cli/router.ts`",
                "",
                "## Forbidden Implementation Drift",
                "",
                "- Do not add public commands beyond check and publish",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "\n".join(
            [
                "## Validation Gates",
                "",
                "- npm test -- tests/cli/router.test.ts",
                "",
                "## T018: Wire authoring route",
                "",
                "### Scope Boundaries",
                "| Field | Value |",
                "|-------|-------|",
                "| write_scope | [src/cli/router.ts] |",
                "| read_scope | [src/cli/new.ts] |",
                "| forbidden | [.env] |",
                "| does_not_remove | [scaffold capability via TUI route] |",
                "| capability_operations | [create/scaffold skill -> TUI route] |",
                "| consumer_surfaces | [OpenTUI Inspector renders TargetSelectionPanel] |",
                "| required_evidence | [consumer_evidence, real_entrypoint_evidence] |",
                "",
                "### Anti-Goals",
                "- Do not add public commands beyond check and publish",
                "",
                "- [ ] T018 [US1] Wire authoring route",
            ]
        ),
        encoding="utf-8",
    )

    packet = compile_worker_task_packet(
        project_root=project_root,
        feature_dir=feature_dir,
        task_id="T018",
    )

    assert packet.anti_goals == ["Do not add public commands beyond check and publish"]
    assert packet.scope.write_scope == ["src/cli/router.ts"]
    assert "src/cli/new.ts" in packet.scope.read_scope
    assert ".env" in packet.forbidden_drift
    assert ".env" in packet.intent.constraints
    assert packet.does_not_remove == ["scaffold capability via TUI route"]
    assert packet.capability_operations == ["create/scaffold skill -> TUI route"]
    assert packet.consumer_surfaces == ["OpenTUI Inspector renders TargetSelectionPanel"]
    assert packet.required_evidence == ["consumer_evidence", "real_entrypoint_evidence"]


def test_compile_worker_task_packet_compiles_review_contract_fields(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)
    (project_root / ".specify" / "memory").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition" / "status.json").write_text(
        '{"version": 1, "graph_ready": true}\n',
        encoding="utf-8",
    )
    (project_root / ".specify" / "project-cognition" / "project-cognition.db").write_bytes(
        b"SQLite test database marker"
    )
    (project_root / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n\n- MUST add tests for public behavior\n",
        encoding="utf-8",
    )
    (feature_dir / "plan.md").write_text(
        "\n".join(
            [
                "## Required Implementation References",
                "",
                "- `DESIGN.md`",
                "",
                "## Forbidden Implementation Drift",
                "",
                "- Do not change generated settings routes",
                "",
                "## Global Constraints",
                "",
                "- Preserve current keyboard navigation",
                "- Keep settings changes local to the panel",
                "",
                "## Review-Risk Notes",
                "",
                "- Screenshot drift can hide responsive regressions",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "\n".join(
            [
                "## Validation Gates",
                "",
                "- npm test -- tests/settings-panel.test.ts",
                "",
                "## T021: Build settings panel",
                "",
                "### Scope Boundaries",
                "| Field | Value |",
                "|-------|-------|",
                "| write_scope | [src/ui/settings-panel.tsx] |",
                "| read_scope | [src/ui/settings-state.ts] |",
                "| consumes | [settings_state, design_tokens] |",
                "| produces | [settings_panel_events, responsive_settings_markup] |",
                "| review_inputs | [DESIGN.md, screenshots/settings-panel.png] |",
                "| review_risks | [Keyboard shortcuts may regress] |",
                "| controller_checks_required | [keyboard_navigation_check, state_persistence_check] |",
                "| global_constraints | [Do not introduce a new state store] |",
                "",
                "- [ ] T021 [US2] Build settings panel",
            ]
        ),
        encoding="utf-8",
    )

    packet = compile_worker_task_packet(
        project_root=project_root,
        feature_dir=feature_dir,
        task_id="T021",
    )

    reference_paths = [ref.path for ref in packet.required_references]
    assert reference_paths == [
        "DESIGN.md",
        "screenshots/settings-panel.png",
    ]
    assert packet.forbidden_drift == ["Do not change generated settings routes"]
    assert "Do not change generated settings routes" in packet.intent.constraints
    assert packet.scope.write_scope == ["src/ui/settings-panel.tsx"]
    assert "src/ui/settings-state.ts" in packet.scope.read_scope
    assert packet.global_constraints == [
        "Preserve current keyboard navigation",
        "Keep settings changes local to the panel",
        "Do not introduce a new state store",
    ]
    assert packet.interfaces.consumes == ["settings_state", "design_tokens"]
    assert packet.interfaces.produces == [
        "settings_panel_events",
        "responsive_settings_markup",
    ]
    assert packet.review_inputs == ["DESIGN.md", "screenshots/settings-panel.png"]
    assert packet.review_risks == [
        "Screenshot drift can hide responsive regressions",
        "Keyboard shortcuts may regress",
    ]
    assert packet.controller_checks_required == [
        "keyboard_navigation_check",
        "state_persistence_check",
    ]
    assert "screenshots/settings-panel.png" in packet.scope.read_scope


def test_compile_worker_task_packet_rejects_markdown_only_ui_contract(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-ui-feature"
    feature_dir.mkdir(parents=True)
    (project_root / ".specify" / "memory").mkdir(parents=True)
    (project_root / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n\n- MUST preserve UI implementation contracts\n",
        encoding="utf-8",
    )
    (project_root / "DESIGN.md").write_text("# Design\n", encoding="utf-8")
    (feature_dir / "ui-reference-notes.md").write_text("# UI Reference Notes\n", encoding="utf-8")
    (feature_dir / "ui-brief.md").write_text("# UI Brief\n", encoding="utf-8")
    (feature_dir / "ui-target.html").write_text("<!doctype html>\n", encoding="utf-8")
    (feature_dir / "plan.md").write_text("## Required Implementation References\n\n- DESIGN.md\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text(
        "\n".join(
            [
                "## Validation Gates",
                "",
                "- npm test -- exceptions",
                "",
                "## T021: Implement exception panel UI",
                "",
                "### Scope Boundaries",
                "| Field | Value |",
                "|-------|-------|",
                "| write_scope | [src/app/exceptions/page.tsx] |",
                "| read_scope | [DESIGN.md, specs/001-ui-feature/ui-brief.md] |",
                "| required_evidence | [reference_source_evidence, ui_fidelity_criteria, real_entrypoint_ui_evidence, visual_comparison_or_human_review] |",
                "",
                "### UI Implementation Contract",
                "| Field | Value |",
                "|-------|-------|",
                "| design_sources | [DESIGN.md, specs/001-ui-feature/ui-brief.md] |",
                "| reference_notes | specs/001-ui-feature/ui-reference-notes.md |",
                "| visual_target | specs/001-ui-feature/ui-target.html |",
                "| ui_fidelity_mode | approximate |",
                "| must_preserve | [three-column layout, compact table density] |",
                "| may_adapt | [icons, minor spacing] |",
                "| must_not | [copy third-party source, turn table into cards] |",
                "| required_states | [loading, empty, error] |",
                "| required_evidence | [desktop screenshot, mobile screenshot] |",
                "",
                "- [ ] T021 [US1] Implement exception panel UI",
            ]
        ),
        encoding="utf-8",
    )

    with pytest.raises(PacketValidationError, match="no canonical task-index ui_contract"):
        compile_worker_task_packet(
            project_root=project_root,
            feature_dir=feature_dir,
            task_id="T021",
        )
def test_compile_worker_task_packet_accepts_materialized_task_input(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)
    (project_root / ".specify" / "memory").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition" / "status.json").write_text(
        '{"version": 1, "graph_ready": true}\n',
        encoding="utf-8",
    )
    (project_root / ".specify" / "project-cognition" / "project-cognition.db").write_bytes(
        b"SQLite test database marker"
    )
    (project_root / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n\n- MUST preserve the runtime contract\n",
        encoding="utf-8",
    )
    (feature_dir / "plan.md").write_text(
        "\n".join(
            [
                "## Required Implementation References",
                "",
                "- `src/contracts/auth.py`",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "\n".join(
            [
                "## Validation Gates",
                "",
                "- pytest tests/unit/test_bll_manager.py -q",
            ]
        ),
        encoding="utf-8",
    )

    packet = compile_worker_task_packet(
        project_root=project_root,
        feature_dir=feature_dir,
        task_id="BLL-lane",
        task_body="[US1] Refactor BLL lane in src/bll_manager.py",
    )

    assert packet.task_id == "BLL-lane"
    assert packet.story_id == "US1"
    assert packet.scope.write_scope == ["src/bll_manager.py"]
    assert packet.context_bundle[0].path == ".specify/project-cognition/status.json"
    assert packet.validation_gates == ["pytest tests/unit/test_bll_manager.py -q"]


def test_compile_worker_task_packet_accepts_short_consequence_mapping_rows(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)
    (project_root / ".specify" / "memory").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition" / "status.json").write_text(
        '{"version": 1, "graph_ready": true}\n',
        encoding="utf-8",
    )
    (project_root / ".specify" / "project-cognition" / "project-cognition.db").write_bytes(
        b"SQLite test database marker"
    )
    (project_root / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n\n- MUST add tests for public behavior\n",
        encoding="utf-8",
    )
    (feature_dir / "plan.md").write_text(
        "\n".join(
            [
                "## Required Implementation References",
                "",
                "- `src/contracts/auth.py`",
                "",
                "## Forbidden Implementation Drift",
                "",
                "- Do not create a parallel auth stack",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "\n".join(
            [
                "## Validation Gates",
                "",
                "- pytest tests/unit/test_auth_service.py -q",
                "",
                "## Consequence Obligation Mapping",
                "",
                "| Obligation ID | Task IDs | Validation |",
                "| --- | --- | --- |",
                "| CA-001 | T017 | pytest tests/unit/test_auth_service.py -q |",
                "",
                "- [ ] T017 [US1] Implement auth flow in src/services/auth_service.py",
            ]
        ),
        encoding="utf-8",
    )

    packet = compile_worker_task_packet(
        project_root=project_root,
        feature_dir=feature_dir,
        task_id="T017",
    )

    obligation = packet.consequence_obligations[0]
    assert obligation.obligation_id == "CA-001"
    assert obligation.claim == "CA-001 consequence obligation for T017"
    assert obligation.affected_objects == ["T017"]
    assert obligation.recovery_validation_refs == ["pytest tests/unit/test_auth_service.py -q"]
    assert (
        obligation.stop_and_reopen_condition
        == "No validation evidence supplied for CA-001"
    )


def test_compile_worker_task_packet_requires_explicit_validation_gates(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)
    (project_root / ".specify" / "memory").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition" / "status.json").write_text(
        '{"version": 1, "graph_ready": true}\n',
        encoding="utf-8",
    )
    (project_root / ".specify" / "project-cognition" / "project-cognition.db").write_bytes(
        b"SQLite test database marker"
    )
    (project_root / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n\n- MUST add tests for public behavior\n",
        encoding="utf-8",
    )
    (feature_dir / "plan.md").write_text(
        "\n".join(
            [
                "## Implementation Constitution",
                "",
                "### Required Implementation References",
                "",
                "- `src/contracts/auth.py`",
                "",
                "### Forbidden Implementation Drift",
                "",
                "- Do not create a parallel auth stack",
                "",
                "### Platform Guardrails",
                "",
                "- supported_platforms: windows, linux",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "- [ ] T017 [US1] Implement auth flow in src/services/auth_service.py\n",
        encoding="utf-8",
    )

    with pytest.raises(PacketValidationError) as exc:
        compile_worker_task_packet(
            project_root=project_root,
            feature_dir=feature_dir,
            task_id="T017",
        )

    assert exc.value.code == "DP1"
    assert "validation_gates" in exc.value.message
