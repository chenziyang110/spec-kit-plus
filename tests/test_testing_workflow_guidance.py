from pathlib import Path

from .template_utils import read_template


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(rel_path: str) -> str:
    return read_template(rel_path)


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
    _assert_mandatory_subagent_guidance(_read("templates/commands/test.md"))
    _assert_mandatory_subagent_guidance(_read("templates/commands/test-scan.md"))
    _assert_mandatory_subagent_guidance(_read("templates/commands/test-build.md"))


def test_test_template_routes_to_scan_or_build():
    content = _read("templates/commands/test.md")
    lowered = content.lower()

    assert "## Workflow Contract Summary" in content
    assert "compatibility router" in lowered
    assert "/sp-test-scan" in content
    assert "/sp-test-build" in content
    assert ".specify/testing/TEST_SCAN.md".lower() in lowered
    assert ".specify/testing/TEST_BUILD_PLAN.md".lower() in lowered
    assert ".specify/testing/TEST_BUILD_PLAN.json".lower() in lowered
    assert ".specify/testing/UNIT_TEST_SYSTEM_REQUEST.md".lower() in lowered
    assert ".specify/testing/testing-state.md" in lowered
    assert "do not write tests" in lowered
    assert "report exactly one next command" in lowered


def test_test_scan_template_deep_scans_and_emits_build_plan():
    content = _read("templates/commands/test-scan.md")
    lowered = content.lower()

    assert "## Workflow Contract Summary" in content
    assert "read-only scan" in lowered
    assert ".specify/testing/TEST_SCAN.md".lower() in lowered
    assert ".specify/testing/TEST_BUILD_PLAN.md".lower() in lowered
    assert ".specify/testing/TEST_BUILD_PLAN.json".lower() in lowered
    assert ".specify/testing/UNIT_TEST_SYSTEM_REQUEST.md".lower() in lowered
    assert "specify testing inventory --format json" in lowered
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
    assert "where new tests belong" in playbook_template
    assert "critical public/module-facing behavior" in contract_template
    assert "last_manual_validation" in state_template


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

    assert "active_command: sp-test" in state_template
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


def test_tasks_template_makes_tests_contract_driven():
    command_content = _read("templates/commands/tasks.md")
    template_content = _read("templates/tasks-template.md")

    assert ".specify/testing/TESTING_CONTRACT.md" in command_content
    assert ".specify/testing/TESTING_PLAYBOOK.md" in command_content
    assert ".specify/testing/COVERAGE_BASELINE.json" in command_content
    assert "tests are contract-driven" in command_content.lower()
    assert "treat tests as default deliverables" in command_content.lower()
    assert "whether or not `.specify/testing/testing_contract.md` exists" in command_content.lower()
    assert "behavior changes, bug fixes, and refactors" in command_content.lower()
    assert "add explicit bootstrap tasks to establish the smallest runnable test surface first" in command_content.lower()
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
    assert ".specify/testing/TESTING_CONTRACT.md".lower() in debug_content
    assert ".specify/testing/TESTING_PLAYBOOK.md".lower() in debug_content
    assert "add or update a regression test" in debug_content
    assert "write a failing automated repro test before changing production code" in debug_content
