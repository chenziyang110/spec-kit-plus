from pathlib import Path

import pytest

from specify_cli.execution.packet_compiler import compile_worker_task_packet
from specify_cli.execution.packet_validator import PacketValidationError


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
                "| ui_fidelity_level | [high] |",
                "| design_inputs | [DESIGN.md#settings-panel] |",
                "| ui_required_evidence | [desktop_screenshot, mobile_screenshot] |",
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

    assert [ref.path for ref in packet.required_references] == ["DESIGN.md"]
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
    assert packet.ui_fidelity_requirements.applicable is True
    assert packet.ui_fidelity_requirements.level == "high"
    assert packet.ui_fidelity_requirements.design_inputs == ["DESIGN.md#settings-panel"]
    assert packet.ui_fidelity_requirements.required_evidence == [
        "desktop_screenshot",
        "mobile_screenshot",
    ]
    assert packet.controller_checks_required == [
        "keyboard_navigation_check",
        "state_persistence_check",
    ]


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
