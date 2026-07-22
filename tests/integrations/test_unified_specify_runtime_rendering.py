"""Generated-agent contract for the unified workflow artifact runtime.

These tests intentionally describe the breaking target contract.  They stay RED
until Classic, Advanced, and delegated-worker surfaces route fixed workflow
artifact access through ``specify-runtime``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from specify_cli import _install_shared_infra
from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest


_TEXT_SUFFIXES = {".json", ".md", ".toml", ".yaml", ".yml"}
_NAKED_RUNTIME_COMMAND = re.compile(
    r"\b(?:project-cognition\s+(?:"
    r"build-from-scan|changes|claim-reconcile|closeout-plan|compass|"
    r"complete-refresh|generate-ignore|init-empty|mark-dirty|query|"
    r"record-refresh|scan-(?:accept|checkpoint|lease|prepare|requeue|"
    r"set|status|yield)|semantic-audit-resume|status|update|"
    r"validate-(?:build|scan)"
    r")|spec-lint\s+(?:check|fix|lint|scan|validate))\b",
    re.IGNORECASE,
)


CLASSIC_ARTIFACT_SURFACES = {
    "specify": ("sp-specify", "spec.md"),
    "plan": ("sp-plan", "plan.md"),
    "tasks": ("sp-tasks", "tasks.md"),
    "implement": ("sp-implement", "implement-tracker.md"),
    "review": ("sp-review", "review-state.json"),
    "accept": ("sp-accept", "human-acceptance.json"),
    "discussion": ("sp-discussion", "discussion-state.json"),
    "quick": ("sp-quick", "status.md"),
    "debug": ("sp-debug", ".planning/debug"),
    "map-scan": ("sp-map-scan", "status.json"),
    "map-build": ("sp-map-build", "project-cognition.db"),
    "map-update": ("sp-map-update", "project-cognition.db"),
}


ADVANCED_ARTIFACT_SURFACES = {
    "specify": ("spx-specify", "spec.md"),
    "plan": ("spx-plan", "plan.md"),
    "tasks": ("spx-tasks", "tasks.md"),
    "implement": ("spx-implement", "implement-tracker.md"),
    "review": ("spx-review", "review-state.json"),
    "accept": ("spx-accept", "human-acceptance.json"),
    "discussion": ("spx-discussion", "discussion write-handoff"),
    "quick": ("spx-quick", "status.md"),
    "debug": ("spx-debug", "debug-session.md"),
    "map-scan": ("spx-map-scan", "scan-prepare"),
    "map-build": ("spx-map-build", "build-from-scan"),
    "map-update": ("spx-map-update", "complete-refresh"),
}


WORKER_ARTIFACT_SURFACES = {
    "specify-observer": ("specify-observer.md", "specify-draft.md"),
    "implementer": ("implementer.md", "delegated result handoff path"),
    "task-reviewer": ("task-reviewer.md", "worker-results/"),
    "quick-worker": ("quick-worker.md", "status.md"),
    "debug-investigator": ("debug-investigator.md", "debug file"),
    "map-scan-worker": ("map-scan-worker.md", "scan-checkpoint"),
}


def _install_codex_profile(project: Path, profile: str) -> Path:
    integration = get_integration("codex")
    assert integration is not None
    manifest = IntegrationManifest("codex", project)
    integration.setup(
        project,
        manifest,
        parsed_options={"workflow_profile": profile},
        script_type="sh",
    )
    return integration.skills_dest(project)


@pytest.fixture(scope="module")
def generated_agent_surfaces(
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, Path]:
    classic_project = tmp_path_factory.mktemp("runtime-classic")
    advanced_project = tmp_path_factory.mktemp("runtime-advanced")
    worker_project = tmp_path_factory.mktemp("runtime-workers")

    classic = _install_codex_profile(classic_project, "classic")
    advanced = _install_codex_profile(advanced_project, "advanced")
    assert _install_shared_infra(worker_project, "sh") is True

    return {
        "classic": classic,
        "advanced": advanced,
        "workers": worker_project / ".specify" / "templates" / "worker-prompts",
    }


def _read_generated_tree(root: Path) -> str:
    files = sorted(
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in _TEXT_SUFFIXES
    )
    assert files, f"expected generated text files under {root}"
    return "\n".join(path.read_text(encoding="utf-8") for path in files).lower()


def _runtime_contract_errors(
    root: Path,
    surfaces: dict[str, tuple[str, str]],
    *,
    directories: bool,
) -> list[str]:
    errors: list[str] = []
    for workflow, (relative, artifact_marker) in surfaces.items():
        target = root / relative
        content = (
            _read_generated_tree(target)
            if directories
            else target.read_text(encoding="utf-8").lower()
        )

        assert artifact_marker in content, (
            f"test setup lost the representative {workflow} artifact marker "
            f"{artifact_marker!r} in {target}"
        )
        if "specify-runtime" not in content:
            errors.append(f"{workflow}: missing unified specify-runtime invocation")

        naked_commands = sorted(
            {
                command
                for line in content.splitlines()
                if "specify-runtime" not in line
                for command in _NAKED_RUNTIME_COMMAND.findall(line)
            }
        )
        if naked_commands:
            errors.append(
                f"{workflow}: contains naked legacy runtime command(s): "
                + ", ".join(naked_commands[:3])
            )
    return errors


def test_generated_classic_artifact_workflows_use_unified_specify_runtime(
    generated_agent_surfaces: dict[str, Path],
) -> None:
    errors = _runtime_contract_errors(
        generated_agent_surfaces["classic"],
        CLASSIC_ARTIFACT_SURFACES,
        directories=True,
    )

    assert errors == [], "\n".join(errors)


def test_generated_advanced_artifact_workflows_use_unified_specify_runtime(
    generated_agent_surfaces: dict[str, Path],
) -> None:
    errors = _runtime_contract_errors(
        generated_agent_surfaces["advanced"],
        ADVANCED_ARTIFACT_SURFACES,
        directories=True,
    )

    assert errors == [], "\n".join(errors)


def test_generated_worker_artifact_surfaces_use_unified_specify_runtime(
    generated_agent_surfaces: dict[str, Path],
) -> None:
    errors = _runtime_contract_errors(
        generated_agent_surfaces["workers"],
        WORKER_ARTIFACT_SURFACES,
        directories=False,
    )

    assert errors == [], "\n".join(errors)
