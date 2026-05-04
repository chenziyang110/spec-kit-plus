import json
from pathlib import Path

from .template_utils import read_template


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(rel_path: str) -> str:
    return read_template(rel_path)


def _json_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        keys = set(value)
        for nested in value.values():
            keys.update(_json_keys(nested))
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for item in value:
            keys.update(_json_keys(item))
        return keys
    return set()


def _assert_command_tier_labels_in_markdown(content: str) -> None:
    lines = {line.lstrip() for line in content.lower().splitlines()}
    assert "- fast smoke:" in lines
    assert "- focused:" in lines
    assert "- full:" in lines


def _section_between(content: str, heading: str, next_heading: str) -> str:
    start = content.find(heading)
    assert start != -1
    end = content.find(next_heading, start)
    assert end != -1
    return content[start:end]


def _assert_json_role_metadata(
    artifact: dict[str, object],
    *,
    role: str,
    owns: tuple[str, ...],
    must_not_become: tuple[str, ...],
) -> None:
    assert artifact["control_plane_role"] == role
    for owned_surface in owns:
        assert owned_surface in artifact["owns"]
    for forbidden_surface in must_not_become:
        assert forbidden_surface in artifact["must_not_become"]


def _assert_mandatory_subagent_guidance(content: str) -> None:
    lowered = content.lower()

    assert "all substantive tasks in ordinary `sp-*` workflows default to and must use subagents" in lowered
    assert "the leader orchestrates:" in lowered
    assert "before dispatch, every subagent lane needs a task contract" in lowered
    assert "structured handoff" in lowered
    assert "execution_model: subagent-mandatory" in lowered
    assert "dispatch_shape: one-subagent | parallel-subagents" in lowered
    assert "execution_surface: native-subagents" in lowered


def test_testing_workflow_templates_require_mandatory_subagent_guidance():
    _assert_mandatory_subagent_guidance(_read("templates/commands/test-scan.md"))
    _assert_mandatory_subagent_guidance(_read("templates/commands/test-build.md"))


def test_test_scan_template_deep_scans_and_emits_build_plan():
    content = _read("templates/commands/test-scan.md")
    lowered = content.lower()

    assert "## Workflow Contract Summary" in content
    assert "read-only scan" in lowered
    assert ".specify/testing/TEST_SCAN.md".lower() in lowered
    assert ".specify/testing/TEST_BUILD_PLAN.md".lower() in lowered
    assert ".specify/testing/TEST_BUILD_PLAN.json".lower() in lowered
    assert ".specify/testing/UNIT_TEST_SYSTEM_REQUEST.md".lower() in lowered
    assert "{{specify-subcmd:testing inventory --format json}}" in lowered
    assert "module_kind" in lowered
    assert "framework_confidence" in lowered
    assert "selected_skill" in lowered
    assert "risk tier" in lowered
    assert "p0" in lowered
    assert "truth_owning_files" in lowered
    assert "public_entrypoints" in lowered
    assert "missing_scenarios" in lowered
    assert "readiness" in lowered
    assert "`ready`" in content
    assert "`needs-leader-review`" in content
    assert "`needs-research`" in content
    assert "`blocked`" in content
    assert "test-scan-template.md" in lowered
    assert "test-build-plan-template.md" in lowered
    assert "test-build-plan-template.json" in lowered
    assert "unit-test-system-request-template.md" in lowered


def test_test_scan_template_generates_downstream_control_plane_fields():
    content = _read("templates/commands/test-scan.md")
    lowered = content.lower()
    packet_block = _section_between(
        lowered,
        "5. **compile `testscanpacket` lanes**",
        "6. **dispatch read-only scan subagents**",
    )
    module_evidence_block = _section_between(
        lowered,
        "7. **build module evidence records**",
        "8. **compile build-ready lanes**",
    )

    assert "covered-module status" in packet_block
    assert "`covered` / `partial` / `missing` / `unknown`" in packet_block
    assert "covered_module_status" in packet_block
    assert "candidate command tiers" in packet_block
    assert "`fast smoke`, `focused`, and `full`" in packet_block
    assert "candidate_command_tiers" in packet_block
    assert "candidate layer mix" in packet_block
    assert "`small / medium / large`" in packet_block
    assert "candidate_layer_mix" in packet_block
    assert "local integration seams and their local integration seam expectations" in packet_block
    assert "local_integration_seam_expectations" in packet_block

    assert "covered-module status" in module_evidence_block
    assert "candidate layer mix across `small / medium / large` tests" in module_evidence_block
    assert "candidate command tiers" in module_evidence_block
    assert "`fast smoke` for the cheapest confidence check" in module_evidence_block
    assert "`focused` for the lane acceptance command" in module_evidence_block
    assert "`full` for the broader regression command" in module_evidence_block
    assert "local integration seam expectations" in module_evidence_block
    assert "adapter, filesystem, process, network, database, cli, or workflow seam" in module_evidence_block


def test_test_scan_template_requires_read_only_subagent_evidence():
    content = _read("templates/commands/test-scan.md")
    lowered = content.lower()

    assert 'choose_subagent_dispatch(command_name="test-scan"' in lowered
    assert "execution_model: subagent-mandatory" in lowered
    assert "dispatch_shape: one-subagent | parallel-subagents" in lowered
    assert "execution_surface: native-subagents" in lowered
    assert "one-subagent" in lowered
    assert "parallel-subagents" in lowered
    assert "testscanpacket" in lowered
    assert "mode: read_only" in content
    assert "dispatch read-only scan subagents" in lowered
    assert "inspected files" in lowered
    assert "concrete scenario evidence" in lowered
    assert "subagents must not edit files" in lowered
    assert "before writing `test_build_plan.md` or `test_build_plan.json`" in lowered
    assert "before marking scan complete" in lowered


def test_test_scan_template_prefers_native_scout_subagents_with_handoffs():
    content = _read("templates/commands/test-scan.md")
    lowered = content.lower()

    assert "current-runtime native subagents are the default" in lowered
    assert "for `one-subagent`, dispatch one read-only scout" in lowered
    assert "validated `testscanpacket`" in lowered
    assert "raw scan notes or raw chat summaries are not sufficient" in lowered
    assert "structured handoff" in lowered
    assert "idle subagent output is not an accepted scan result" in lowered
    assert "must wait for every dispatched scan lane" in lowered


def test_test_build_template_consumes_scan_and_dispatches_build_packets():
    content = _read("templates/commands/test-build.md")
    lowered = content.lower()

    assert "## Workflow Contract Summary" in content
    assert ".specify/testing/TEST_SCAN.md".lower() in lowered
    assert ".specify/testing/TEST_BUILD_PLAN.md".lower() in lowered
    assert ".specify/testing/TEST_BUILD_PLAN.json".lower() in lowered
    assert "stop and route to `{{invoke:test-scan}}`" in lowered
    assert 'choose_subagent_dispatch(command_name="test-build"' in lowered
    assert "testbuildpacket" in lowered
    assert "validated `testbuildpacket`" in lowered
    assert "a subagent may only edit files inside its `write_set`" in lowered
    assert "shared config, global fixtures, ci/presubmit, dependency, and production-code edits must be delegated through an explicit validated serial `testbuildpacket`" in lowered
    assert "the leader owns coordination, review, and acceptance only" in lowered
    assert "if the serial lane cannot be safely packetized or dispatched, record `subagent-blocked` and stop for escalation or recovery" in lowered
    assert "reported_status: done | done_with_concerns | blocked | needs_context" in lowered
    assert "idle subagent is not an accepted result" in lowered
    assert "test-quality review lane" in lowered


def test_test_build_template_requires_manual_execution_evidence_and_assets():
    content = _read("templates/commands/test-build.md")
    lowered = content.lower()
    contract_template = _read("templates/testing/testing-contract-template.md").lower()
    playbook_template = _read("templates/testing/testing-playbook-template.md").lower()
    state_template = _read("templates/testing/testing-state-template.md").lower()

    assert ".specify/testing/TESTING_CONTRACT.md".lower() in lowered
    assert ".specify/testing/TESTING_PLAYBOOK.md".lower() in lowered
    assert ".specify/testing/COVERAGE_BASELINE.json".lower() in lowered
    assert "manually execute the canonical test commands" in lowered
    assert "most recent manual validation run" in lowered
    assert "testing-contract-template.md" in lowered
    assert "testing-playbook-template.md" in lowered
    assert "coverage-baseline-template.json" in lowered
    assert "add new tests" in playbook_template
    assert "where tests belong" in playbook_template
    assert "critical public/module-facing behavior" in contract_template
    assert "last_manual_validation" in state_template


def test_test_build_template_publishes_control_plane_without_replacing_lane_validation_command():
    content = _read("templates/commands/test-build.md")
    lowered = content.lower()
    durable_assets_block = _section_between(
        lowered,
        "11. **generate durable testing assets**",
        "12. **push the contract back into the main workflow**",
    )
    contract_block = _section_between(
        durable_assets_block,
        "write `.specify/testing/testing_contract.md` with:",
        "write `.specify/testing/testing_playbook.md` with:",
    )
    playbook_block = _section_between(
        durable_assets_block,
        "write `.specify/testing/testing_playbook.md` with:",
        "write `.specify/testing/coverage_baseline.json`",
    )

    assert "covered-module rules" in contract_block
    assert "covered-module status values" in contract_block
    assert "command-tier expectations for `fast smoke`, `focused`, and `full` commands" in contract_block
    assert "local integration seam expectations" in contract_block
    assert "command-tier expectations for `fast smoke`, `focused`, and `full`" in playbook_block
    assert "covered-module rules" in playbook_block
    assert "adding or changing tests" in playbook_block
    assert "local integration seam expectations and examples" in playbook_block
    assert "preserve each lane's canonical `validation_command`" in durable_assets_block
    assert "`validation_command` remains the lane acceptance command" in durable_assets_block
    assert "do not replace it with a command-tier map" in durable_assets_block
    assert "`focused` command should mirror the canonical `validation_command`" in durable_assets_block
    assert "`full` command is the broader regression/final-verification tier" in durable_assets_block
    assert "must not be treated as the lane acceptance command" in durable_assets_block


def test_test_build_template_requires_coverage_uplift_iteration():
    content = _read("templates/commands/test-build.md").lower()
    contract_template = _read("templates/testing/testing-contract-template.md").lower()

    assert "run coverage after the first meaningful test pass" in content
    assert "iterate on uncovered critical paths" in content
    assert "until thresholds are met or an explicit blocker is recorded" in content
    assert "minimum enforcement policy" in contract_template
    assert "coverage objective" in contract_template


def test_test_template_requires_professional_unit_test_system_request_artifact():
    content = _read("templates/commands/test-scan.md").lower()
    request_template = _read("templates/testing/unit-test-system-request-template.md").lower()

    assert "unit_test_system_request.md" in content or "unit-test-system-request.md" in content
    assert "professional-grade brownfield unit-test system request" in content
    assert "small / medium / large" in content
    assert "scenario matrix" in content
    assert "module risk tiers" in content
    assert "coverage uplift waves" in content

    assert "small tests" in request_template
    assert "medium tests" in request_template
    assert "large tests" in request_template
    assert "80%" in request_template
    assert "15%" in request_template
    assert "5%" in request_template
    assert "public contracts" in request_template
    assert "mock / fake strategy" in request_template
    assert "presubmit / ci gate policy" in request_template
    assert "scenario matrix" in request_template


def test_downstream_testing_scan_and_build_plan_roles_are_distinct():
    scan_template = _read("templates/testing/test-scan-template.md").lower()
    build_plan_template = _read("templates/testing/test-build-plan-template.md").lower()
    build_plan_json_content = _read("templates/testing/test-build-plan-template.json")
    build_plan_json = json.loads(build_plan_json_content)
    build_plan_json_text = build_plan_json_content.lower()
    build_plan_json_keys = _json_keys(build_plan_json)

    assert "`.specify/testing/*`" in scan_template
    assert "single downstream testing control plane" in scan_template
    assert "module root" in scan_template
    assert "public entrypoints / contracts" in scan_template
    assert "covered module status" in scan_template
    assert "candidate layer mix" in scan_template
    assert "candidate command tiers" in scan_template
    assert "strict module evidence" in scan_template
    _assert_command_tier_labels_in_markdown(scan_template)

    assert "wave join point" in build_plan_template
    assert "command-tier outcomes" in build_plan_template
    assert "must not become the coverage baseline" in build_plan_template
    assert "- validation_command:" in build_plan_template
    assert "canonical lane validation command" in build_plan_template
    assert "focused" in build_plan_template
    _assert_command_tier_labels_in_markdown(build_plan_template)
    assert "command_tier_outcomes" in build_plan_json_text
    assert "join_point" in build_plan_json_text
    _assert_json_role_metadata(
        build_plan_json,
        role="wave-plan-json",
        owns=(
            "machine-readable wave join points",
            "lane command tiers",
            "command-tier outcomes",
        ),
        must_not_become=(
            "project-wide testing contract",
            "newcomer playbook",
            "coverage baseline",
        ),
    )
    assert set(build_plan_json["waves"][0]["join_point"]["command_tier_outcomes"]) == {
        "fast_smoke",
        "focused",
        "full",
    }
    assert set(build_plan_json["waves"][0]["lanes"][0]["command_tiers"]) == {
        "fast_smoke",
        "focused",
        "full",
    }
    sample_lane = build_plan_json["waves"][0]["lanes"][0]
    assert "validation_command" in sample_lane
    assert sample_lane["validation_command"] == sample_lane["command_tiers"]["focused"]
    for forbidden_key in (
        "testing_contract",
        "testing_playbook",
        "selected_modules",
        "next_action",
        "scenario_matrix",
        "target_mix",
        "scan_status",
        "build_status",
        "last_manual_validation",
    ):
        assert forbidden_key not in build_plan_json_keys


def test_downstream_testing_contract_and_playbook_roles_are_distinct():
    contract_template = _read("templates/testing/testing-contract-template.md").lower()
    playbook_template = _read("templates/testing/testing-playbook-template.md").lower()

    assert "covered modules" in contract_template
    assert "mandatory triggers" in contract_template
    assert "command-tier expectations" in contract_template
    _assert_command_tier_labels_in_markdown(contract_template)

    playbook_lines = set(playbook_template.splitlines())
    playbook_run_tests = _section_between(playbook_template, "## run tests", "## add new tests")
    playbook_add_tests = _section_between(playbook_template, "## add new tests", "## coverage")
    playbook_module_notes = _section_between(playbook_template, "## module notes", "## known gaps")

    assert "where tests belong" in playbook_template
    assert "newcomer" in playbook_template
    assert "- where tests belong:" in playbook_lines
    assert "  - small tests:" in playbook_lines
    assert "  - medium tests:" in playbook_lines
    assert "  - large tests:" in playbook_lines
    assert "- naming conventions for new test files:" in playbook_lines
    assert "- shared fixtures, mocks, or factories to reuse:" in playbook_lines
    _assert_command_tier_labels_in_markdown(playbook_template)
    _assert_command_tier_labels_in_markdown(playbook_run_tests)
    assert "- covered-module status guidance:" in playbook_lines
    assert "covered / partial / missing / unknown" in playbook_add_tests
    assert "adding or changing tests" in playbook_add_tests
    assert "- local integration seam expectations:" in playbook_lines
    assert "adapter" in playbook_add_tests
    assert "filesystem" in playbook_add_tests
    assert "process" in playbook_add_tests
    assert "network" in playbook_add_tests
    assert "database" in playbook_add_tests
    assert "cli" in playbook_add_tests
    assert "workflow" in playbook_add_tests
    assert "- local integration seam examples:" in playbook_module_notes


def test_downstream_testing_request_and_state_roles_do_not_collapse():
    request_template = _read("templates/testing/unit-test-system-request-template.md").lower()

    assert "control-plane role" in request_template
    assert "owns the scenario matrix" in request_template
    assert "must not become the wave execution plan" in request_template
    assert "must not become the binding testing contract" in request_template
    assert "must not replace the newcomer playbook commands" in request_template
    assert "scenario matrix" in request_template
    assert "local integration seams" in request_template
    assert "small tests" in request_template
    assert "medium tests" in request_template
    assert "## scenario matrix" in request_template
    assert "## coverage uplift waves" in request_template
    assert "## current test surface assessment" in request_template
    assert "## covered modules" not in request_template
    assert "## mandatory rules" not in request_template
    assert "## add new tests" not in request_template
    assert "## current focus" not in request_template
    assert "## scan artifacts" not in request_template
    assert "## build execution" not in request_template
    assert "## validation evidence" not in request_template
    assert "testbuildpacket inputs" not in request_template
    assert "lane id | readiness | module | risk tier" not in request_template
    for forbidden_token in (
        "join_point",
        "write_set",
        "allowed_actions",
        "result_handoff_path",
        "scan_status",
        "build_status",
        "last_manual_validation",
        "next_action:",
        "next_command:",
        "handoff_reason:",
        "accepted_results:",
        "rejected_results:",
    ):
        assert forbidden_token not in request_template


def test_downstream_testing_coverage_baseline_json_role_is_distinct():
    coverage_baseline_content = _read("templates/testing/coverage-baseline-template.json")
    coverage_baseline = json.loads(coverage_baseline_content)
    coverage_baseline_keys = _json_keys(coverage_baseline)
    coverage_baseline_text = coverage_baseline_content.lower()

    assert coverage_baseline["control_plane_role"] == "coverage-baseline-json"
    _assert_json_role_metadata(
        coverage_baseline,
        role="coverage-baseline-json",
        owns=(
            "module coverage baselines",
            "hotspot context",
            "coverage command-tier tracking",
        ),
        must_not_become=(
            "wave execution plan",
            "newcomer command playbook",
            "testing contract",
        ),
    )
    assert set(coverage_baseline["modules"][0]["command_tiers"]) == {
        "fast_smoke",
        "focused",
        "full",
    }
    for forbidden_key in (
        "waves",
        "join_point",
        "next_action",
        "selected_modules",
        "scenario_matrix",
        "target_mix",
        "scan_status",
        "build_status",
        "last_manual_validation",
    ):
        assert forbidden_key not in coverage_baseline_keys
    assert "hotspots" in coverage_baseline_text
    assert "command_tiers" in coverage_baseline_text
    assert "module_root" in coverage_baseline_text


def test_downstream_testing_state_role_does_not_collapse():
    state_template = _read("templates/testing/testing-state-template.md").lower()

    assert "control_plane_role" in state_template
    assert "lifecycle and routing tracker" in state_template
    assert "scan evidence" in state_template
    assert "build-plan lane packets" in state_template
    assert "contract rules" in state_template
    assert "playbook instructions" in state_template
    assert "hotspot_context" in state_template
    assert "command_tiers" in state_template
    assert "- fast smoke:" in state_template
    assert "- focused:" in state_template
    assert "- full:" in state_template
    assert "## module evidence" not in state_template
    assert "## covered modules" not in state_template
    assert "## add new tests" not in state_template
    assert "## scenario matrix" not in state_template
    assert "## coverage uplift waves" not in state_template
    assert "## current test surface assessment" not in state_template
    assert "## presubmit / ci gate policy" not in state_template
    assert "## allowed testability refactors" not in state_template
    for forbidden_phrase in (
        "public entrypoints / contracts",
        "risk tier",
        "readiness",
        "result_handoff_path",
        "allowed_actions",
    ):
        assert forbidden_phrase not in state_template


def test_test_scan_and_build_templates_use_handbook_and_project_map_gates():
    scan_content = _read("templates/commands/test-scan.md")
    build_content = _read("templates/commands/test-build.md")

    for content in (scan_content, build_content):
        assert "[AGENT] If freshness is `missing` or `stale`, run `/sp-map-scan` followed by `/sp-map-build` before continuing, then reload the generated navigation artifacts." in content
        assert "freshness is `possibly_stale`" in content
        assert "PROJECT-HANDBOOK.md" in content
        assert "[AGENT] Read `PROJECT-HANDBOOK.md`." in content
        assert "Read the smallest relevant combination of `.specify/project-map/root/ARCHITECTURE.md`" in content


def test_test_template_emits_result_driven_handoff_recommendation():
    content = _read("templates/commands/test-build.md")
    lowered = content.lower()
    state_template = _read("templates/testing/testing-state-template.md")

    assert "classify the next workflow recommendation before the final report" in lowered
    assert "recommend exactly one next command" in lowered
    assert "persist the recommendation in `testing_state_file`" in lowered
    assert "`next_command`" in content
    assert "resume the previous workflow" in lowered
    assert "recommend `{{invoke:fast}}`" in content
    assert "recommend `{{invoke:quick}}`" in content
    assert "recommend `{{invoke:specify}}`" in content
    assert "recommend `{{invoke:debug}}`" in content
    assert "resume `{{invoke:implement}}`" in content
    assert "single command, config, or helper repair" in lowered
    assert "single bounded module or surface" in lowered
    assert "multiple modules, multiple failure classes" in lowered
    assert "coverage uplift program" in lowered
    assert "execution-time regression inside an already active feature" in lowered
    assert "include the recommended next command and one-line rationale in the final report" in lowered
    assert "- next_command:" in state_template
    assert "- handoff_reason:" in state_template


def test_testing_state_tracks_scan_and_build_lifecycle():
    state_template = _read("templates/testing/testing-state-template.md")
    lowered = state_template.lower()

    assert "active_command: sp-test-scan" in state_template
    assert "scan_status" in lowered
    assert "build_status" in lowered
    assert "test_scan" in lowered
    assert "test_build_plan" in lowered
    assert "test_build_plan_json" in lowered
    assert "current_wave" in lowered
    assert "current_lane" in lowered
    assert "accepted_results" in lowered
    assert "rejected_results" in lowered
    assert "failed_validation" in lowered


def test_plan_template_consumes_testing_contract_when_present():
    content = _read("templates/commands/plan.md")
    lowered = content.lower()

    assert ".specify/testing/TESTING_CONTRACT.md".lower() in lowered
    assert ".specify/testing/TESTING_PLAYBOOK.md".lower() in lowered
    assert ".specify/testing/COVERAGE_BASELINE.json".lower() in lowered
    assert "copy the project-level testing rules into the implementation plan" in lowered
    assert "canonical test, targeted-test, and coverage commands" in lowered
    assert "module priority waves" in lowered
    assert "covered-module policy" in lowered
    assert "`small / medium / large` policy" in lowered
    assert "scenario matrix expectations" in lowered
    assert "local integration seam expectations" in lowered
    assert "allowed testability refactors" in lowered
    assert "coverage goals" in lowered
    assert "ci gate expectations" in lowered
    assert "command-tier expectations for `fast smoke`, `focused`, and `full`" in lowered


def test_specify_template_preserves_brownfield_testing_control_plane_inputs():
    content = _read("templates/commands/specify.md").lower()

    assert ".specify/testing/unit_test_system_request.md" in content
    assert "covered-module policy" in content
    assert "scenario matrix expectations" in content
    assert "local integration seam expectations" in content
    assert "command-tier expectations for `fast smoke`, `focused`, and `full`" in content
    assert "preserve these stronger brownfield testing inputs" in content


def test_tasks_template_makes_tests_contract_driven():
    command_content = _read("templates/commands/tasks.md")
    template_content = _read("templates/tasks-template.md")
    task_generation_rules = command_content[
        command_content.index("## Task Generation Rules") :
    ].lower()

    assert ".specify/testing/TESTING_CONTRACT.md" in command_content
    assert ".specify/testing/TESTING_PLAYBOOK.md" in command_content
    assert ".specify/testing/COVERAGE_BASELINE.json" in command_content
    assert "tests are contract-driven" in command_content.lower()
    assert "treat tests as default deliverables" in command_content.lower()
    assert "whether or not `.specify/testing/testing_contract.md` exists" in command_content.lower()
    assert "behavior changes, bug fixes, and refactors" in command_content.lower()
    assert "tests (if requested)" not in task_generation_rules
    assert "or the spec explicitly requires tests" not in task_generation_rules
    assert "tests specific to that story for behavior changes, bug fixes, refactors, and regression-sensitive modules" in task_generation_rules
    assert "contract test tasks by default before implementation" in task_generation_rules
    assert "add explicit bootstrap tasks to establish the smallest runnable test surface first" in command_content.lower()
    assert "small tests" in command_content.lower()
    assert "medium tests" in command_content.lower()
    assert "fast smoke" in command_content.lower()
    assert "focused" in command_content.lower()
    assert "full" in command_content.lower()
    assert "validation_command remains the focused lane acceptance command" in command_content.lower()
    assert ".specify/testing/TESTING_CONTRACT.md" in template_content
    assert "tests are expected by default" in template_content.lower()
    assert "ensure they fail before implementation" in template_content.lower()


def test_implement_and_debug_templates_treat_testing_contract_as_binding():
    implement_content = _read("templates/commands/implement.md").lower()
    debug_content = _read("templates/commands/debug.md").lower()

    assert ".specify/testing/TESTING_CONTRACT.md".lower() in implement_content
    assert ".specify/testing/TESTING_PLAYBOOK.md".lower() in implement_content
    assert "testing contract is binding when present" in implement_content
    assert "add or update the required failing tests or regression tests" in implement_content
    assert "write the failing test first for every behavior-changing task, bug fix, or refactor" in implement_content
    assert "do not write production code for the batch until the red state is verified" in implement_content
    assert "command-tier expectations for `fast smoke`, `focused`, and `full`" in implement_content
    assert "run the focused tier as the lane acceptance check" in implement_content
    assert ".specify/testing/TESTING_CONTRACT.md".lower() in debug_content
    assert ".specify/testing/TESTING_PLAYBOOK.md".lower() in debug_content
    assert "add or update a regression test" in debug_content
    assert "write a failing automated repro test before changing production code" in debug_content
    assert "command-tier expectations for `fast smoke`, `focused`, and `full`" in debug_content
    assert "use the fast smoke tier for the cheapest repro check" in debug_content
