from pathlib import Path

from .template_utils import read_template


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(rel_path: str) -> str:
    return read_template(rel_path)


def test_test_template_bootstraps_testing_contract_assets():
    content = _read("templates/commands/test.md")
    lowered = content.lower()

    assert "## Workflow Contract Summary" in content
    assert "project-wide unit testing system" in lowered
    assert ".specify/testing/TESTING_CONTRACT.md".lower() in lowered
    assert ".specify/testing/TESTING_PLAYBOOK.md".lower() in lowered
    assert ".specify/testing/COVERAGE_BASELINE.json".lower() in lowered
    assert ".specify/testing/UNIT_TEST_SYSTEM_REQUEST.md".lower() in lowered
    assert ".specify/testing/testing-state.md" in lowered
    assert "bootstrap" in lowered
    assert "refresh" in lowered
    assert "audit-only" in lowered
    assert ".specify/templates/passive-skills/*-testing/" in lowered
    assert "specify testing inventory --format json" in lowered
    assert "module_kind" in lowered
    assert "framework_confidence" in lowered
    assert "selected_skill" in lowered
    assert "testing-contract-template.md" in lowered
    assert "testing-playbook-template.md" in lowered
    assert "coverage-baseline-template.json" in lowered
    assert "unit-test-system-request-template.md" in lowered
    assert 'choose_execution_strategy(command_name="test"' in lowered
    assert "single-lane" in lowered
    assert "native-multi-agent" in lowered
    assert "sidecar-runtime" in lowered
    assert "before mutating shared repository test framework/config files" in lowered
    assert "before writing the consolidated `.specify/testing/*` artifacts" in lowered


def test_test_template_prefers_auto_capture_from_testing_state() -> None:
    content = _read("templates/commands/test.md").lower()

    assert "capture-auto --command test" in content
    assert "testing-state already captures reusable gaps" in content or "testing-state already captures reusable" in content
    assert "fall back to `specify hook capture-learning --command test" in content


def test_test_template_explains_bundled_language_testing_skills():
    content = _read("templates/commands/test.md")
    lowered = content.lower()
    state_template = _read("templates/testing/testing-state-template.md").lower()

    assert "built-in `sp-test` language testing lane" in content
    assert "templates/passive-skills/*-testing/" in lowered
    assert ".specify/templates/passive-skills/*-testing/" in lowered
    assert "not an unrelated optional addon" in lowered
    assert "explicitly tell the user" in lowered
    assert "selected bundled language testing skills" in lowered
    assert "bundled `sp-test` language skills" in state_template


def test_test_template_requires_manual_execution_evidence_and_add_test_guidance():
    content = _read("templates/commands/test.md")
    lowered = content.lower()
    contract_template = _read("templates/testing/testing-contract-template.md").lower()
    playbook_template = _read("templates/testing/testing-playbook-template.md").lower()
    state_template = _read("templates/testing/testing-state-template.md").lower()

    assert "manually execute the canonical test commands" in lowered
    assert "most recent manual validation run" in lowered
    assert "add new tests" in playbook_template
    assert "where new tests belong" in playbook_template
    assert "critical public/module-facing behavior" in contract_template
    assert "last_manual_validation" in state_template


def test_test_template_requires_coverage_uplift_iteration():
    content = _read("templates/commands/test.md").lower()
    contract_template = _read("templates/testing/testing-contract-template.md").lower()

    assert "run coverage after the first meaningful test pass" in content
    assert "iterate on uncovered critical paths" in content
    assert "until thresholds are met or an explicit blocker is recorded" in content
    assert "minimum enforcement policy" in contract_template
    assert "coverage objective" in contract_template


def test_test_template_requires_professional_unit_test_system_request_artifact():
    content = _read("templates/commands/test.md").lower()
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


def test_test_template_uses_handbook_and_project_map_gates():
    content = _read("templates/commands/test.md")

    assert "[AGENT] If freshness is `missing` or `stale`, run `/sp-map-codebase` before continuing, then reload the generated navigation artifacts." in content
    assert "[AGENT] If freshness is `possibly_stale`, inspect the reported changed paths, reasons, `must_refresh_topics`, and `review_topics`." in content
    assert "[AGENT] If `PROJECT-HANDBOOK.md` or the required `.specify/project-map/` files are missing, run `/sp-map-codebase` before continuing, then reload the generated navigation artifacts." in content
    assert "[AGENT] If testing-surface coverage is insufficient for the current repository, run `/sp-map-codebase` before continuing, then reload the generated navigation artifacts." in content
    assert "[AGENT] Read `PROJECT-HANDBOOK.md`." in content
    assert "Read the smallest relevant combination of `.specify/project-map/root/ARCHITECTURE.md`" in content


def test_test_template_emits_result_driven_handoff_recommendation():
    content = _read("templates/commands/test.md")
    lowered = content.lower()
    state_template = _read("templates/testing/testing-state-template.md")

    assert "classify the next workflow recommendation before the final report" in lowered
    assert "recommend exactly one next command" in lowered
    assert "persist the recommendation in `testing_state_file`" in lowered
    assert "`next_command`" in content
    assert "resume the previous workflow" in lowered
    assert "recommend `/sp-fast`" in content
    assert "recommend `/sp-quick`" in content
    assert "recommend `/sp-specify`" in content
    assert "recommend `/sp-debug`" in content
    assert "resume `/sp-implement`" in content
    assert "single command, config, or helper repair" in lowered
    assert "single bounded module or surface" in lowered
    assert "multiple modules, multiple failure classes" in lowered
    assert "coverage uplift program" in lowered
    assert "execution-time regression inside an already active feature" in lowered
    assert "include the recommended next command and one-line rationale in the final report" in lowered
    assert "- next_command:" in state_template
    assert "- handoff_reason:" in state_template


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
