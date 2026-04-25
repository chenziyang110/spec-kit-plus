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
    assert ".specify/testing/testing-state.md" in lowered
    assert "bootstrap" in lowered
    assert "refresh" in lowered
    assert "audit-only" in lowered
    assert ".specify/templates/passive-skills/*-testing/" in lowered
    assert "testing-contract-template.md" in lowered
    assert "testing-playbook-template.md" in lowered
    assert "coverage-baseline-template.json" in lowered
    assert 'choose_execution_strategy(command_name="test"' in lowered
    assert "single-agent" in lowered
    assert "native-multi-agent" in lowered
    assert "sidecar-runtime" in lowered
    assert "before mutating shared repository test framework/config files" in lowered
    assert "before writing the consolidated `.specify/testing/*` artifacts" in lowered


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
    assert ".specify/testing/TESTING_CONTRACT.md" in template_content
    assert "tests are expected by default" in template_content.lower()


def test_implement_and_debug_templates_treat_testing_contract_as_binding():
    implement_content = _read("templates/commands/implement.md").lower()
    debug_content = _read("templates/commands/debug.md").lower()

    assert ".specify/testing/TESTING_CONTRACT.md".lower() in implement_content
    assert ".specify/testing/TESTING_PLAYBOOK.md".lower() in implement_content
    assert "testing contract is binding when present" in implement_content
    assert "add or update the required failing tests or regression tests" in implement_content
    assert ".specify/testing/TESTING_CONTRACT.md".lower() in debug_content
    assert ".specify/testing/TESTING_PLAYBOOK.md".lower() in debug_content
    assert "add or update a regression test" in debug_content
