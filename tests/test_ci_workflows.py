"""Regression coverage for the Python and Go CI verification entry points."""

from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parent.parent


def _test_workflow() -> dict:
    # BaseLoader preserves GitHub's `on` key instead of YAML 1.1's boolean True.
    return yaml.load(
        (ROOT / ".github" / "workflows" / "test.yml").read_text(encoding="utf-8"),
        Loader=yaml.BaseLoader,
    )


def test_go_regressions_run_for_pull_requests_and_main() -> None:
    workflow = _test_workflow()
    assert "pull_request" in workflow["on"]
    assert "main" in workflow["on"]["push"]["branches"]
    job = workflow["jobs"].get("go")
    assert job is not None, "CI must execute the native Go regression suite"
    assert not job.get("if"), "Native regressions must not depend on release events"
    assert job.get("continue-on-error", "false") == "false"

    for command in ("go test -count=1 ./...", "go vet ./..."):
        matching_steps = [
            step
            for step in job["steps"]
            if command in step.get("run", "").splitlines()
        ]
        assert matching_steps, f"CI is missing {command}"
        for step in matching_steps:
            working_directory = step.get(
                "working-directory",
                job.get("defaults", {}).get("run", {}).get("working-directory"),
            )
            assert working_directory == "tools/specify-runtime"
            assert not step.get("if")
            assert step.get("continue-on-error", "false") == "false"


@pytest.mark.parametrize("job_name", ["go", "pytest"])
def test_go_toolchain_is_prepared_before_runtime_checks(job_name: str) -> None:
    jobs = _test_workflow()["jobs"]
    assert job_name in jobs, f"CI is missing the {job_name} job"
    steps = jobs[job_name]["steps"]
    setup_indexes = [
        index
        for index, step in enumerate(steps)
        if step.get("uses", "").startswith("actions/setup-go@")
    ]
    assert setup_indexes, f"{job_name} must explicitly install the Go toolchain"
    setup_index = setup_indexes[0]
    setup = steps[setup_index]
    assert setup["with"]["go-version-file"] == "tools/specify-runtime/go.mod"
    assert setup["with"]["cache-dependency-path"] == "tools/specify-runtime/go.sum"
    assert not setup.get("if")

    runtime_commands = [
        index
        for index, step in enumerate(steps)
        if any(
            command in step.get("run", "")
            for command in ("go test", "go vet", "pytest")
        )
    ]
    assert runtime_commands
    assert setup_index < min(runtime_commands)
