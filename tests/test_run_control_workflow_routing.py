from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest


ROOT = Path(__file__).resolve().parents[1]
TMP_ROOT = ROOT / ".tmp" / "test_run_control_workflow_routing"
CLASSIC_RUN_BOOTSTRAP = (
    ROOT / "templates" / "command-partials" / "common" / "run-bootstrap.md"
)
ADVANCED_RUN_BOOTSTRAP = (
    ROOT / "templates" / "advanced-skills" / "_shared" / "run-bootstrap.md"
)
SKILLS_INTEGRATION_SAMPLE_KEYS = ("codex", "agy", "vibe", "zcode")

CLASSIC_MODIFYING_WORKFLOWS = (
    "quick",
    "debug",
    "fast",
    "specify",
    "plan",
    "tasks",
    "implement",
    "review",
    "accept",
)
ADVANCED_MODIFYING_WORKFLOWS = tuple(f"spx-{name}" for name in CLASSIC_MODIFYING_WORKFLOWS)

STAGE_PHRASES = {
    "quick": ("new run",),
    "debug": ("new run",),
    "fast": ("new run",),
    "specify": ("feature run", "new run"),
    "plan": ("same run",),
    "tasks": ("same run",),
    "implement": ("same run",),
    "review": ("immutable candidate", "new result"),
    "accept": ("read-only with respect to product source", "actual final decision"),
}


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _mktemp_dir(prefix: str) -> Path:
    TMP_ROOT.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=prefix, dir=TMP_ROOT))


def _normalized(content: str) -> str:
    return " ".join(content.lower().split())


def _assert_shared_run_bootstrap_contract(content: str) -> None:
    lowered = _normalized(content)

    for command in (
        "specify-runtime run create",
        "specify-runtime run show",
        "specify-runtime run supervise",
        "specify-runtime result show",
        "specify-runtime candidate build",
        "candidate review",
        "accept receipt",
        "cas publish",
        "sync safe",
    ):
        assert command in content

    assert "control-plane intent only" in lowered
    assert "forces child cwd" in lowered
    assert "immutable result" in lowered
    assert "exactly one" in lowered
    assert "primary workspace" in lowered
    assert "pre-launch snapshot" in lowered
    assert "specify-runtime run integrate" not in content


def _assert_stage_semantics(content: str, stage: str) -> None:
    lowered = _normalized(content)

    assert "specify-runtime run supervise" in content
    for phrase in STAGE_PHRASES[stage]:
        assert phrase in lowered

    if stage in {"quick", "debug", "fast", "specify"}:
        assert "specify-runtime run create" in content
    if stage in {"plan", "tasks", "implement"}:
        assert "specify-runtime run show" in content
    if stage == "review":
        assert "specify-runtime candidate show" in content
        assert "specify-runtime candidate review" in content
        assert "review target-bind" in lowered
    if stage == "accept":
        assert "specify-runtime accept receipt" in content
        assert "specify-runtime cas publish" in content
        assert "specify-runtime sync safe" in content


def _install_skills_profile(project: Path, integration_key: str, profile: str) -> Path:
    integration = get_integration(integration_key)
    assert integration is not None
    manifest = IntegrationManifest(integration_key, project)
    integration.setup(
        project,
        manifest,
        parsed_options={"workflow_profile": profile},
        script_type="sh",
    )
    return integration.commands_dest(project)


@pytest.fixture(scope="session", autouse=True)
def isolate_project_launcher_bindings():
    name = "SPECIFY_PROJECT_LAUNCHER_STATE_DIR"
    previous = os.environ.get(name)
    path = _mktemp_dir("project-launcher-bindings-")
    os.environ[name] = str(path)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(scope="session", autouse=True)
def isolate_claude_config_dir():
    name = "CLAUDE_CONFIG_DIR"
    previous = os.environ.get(name)
    path = _mktemp_dir("claude-config-")
    os.environ[name] = str(path)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = previous
        shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def local_tmp_path() -> Path:
    path = _mktemp_dir("case-")
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)


def test_classic_modifying_workflows_include_shared_run_bootstrap_partial() -> None:
    assert CLASSIC_RUN_BOOTSTRAP.is_file(), CLASSIC_RUN_BOOTSTRAP
    _assert_shared_run_bootstrap_contract(CLASSIC_RUN_BOOTSTRAP.read_text(encoding="utf-8"))

    include = "{{spec-kit-include: ../command-partials/common/run-bootstrap.md}}"
    for stage in CLASSIC_MODIFYING_WORKFLOWS:
        assert include in _read(f"templates/commands/{stage}.md"), stage


def test_advanced_modifying_workflows_read_shared_run_bootstrap_reference() -> None:
    assert ADVANCED_RUN_BOOTSTRAP.is_file(), ADVANCED_RUN_BOOTSTRAP
    _assert_shared_run_bootstrap_contract(
        ADVANCED_RUN_BOOTSTRAP.read_text(encoding="utf-8")
    )

    surface_map = json.loads(
        _read("templates/advanced-skills/_shared/surface-map.json")
    )
    assert "_shared/run-bootstrap.md" in surface_map["shared_references"]

    for skill_name in ADVANCED_MODIFYING_WORKFLOWS:
        content = _read(f"templates/advanced-skills/{skill_name}/SKILL.md")
        assert "Read `references/run-bootstrap.md`" in content, skill_name


@pytest.mark.parametrize("integration_key", SKILLS_INTEGRATION_SAMPLE_KEYS)
def test_generated_classic_skill_surfaces_preserve_run_control_semantics(
    local_tmp_path: Path, integration_key: str
) -> None:
    root = _install_skills_profile(
        local_tmp_path / f"{integration_key}-classic", integration_key, "classic"
    )

    for stage in CLASSIC_MODIFYING_WORKFLOWS:
        skill = root / f"sp-{stage}" / "SKILL.md"
        content = skill.read_text(encoding="utf-8")
        _assert_stage_semantics(content, stage)


@pytest.mark.parametrize("integration_key", SKILLS_INTEGRATION_SAMPLE_KEYS)
def test_generated_advanced_skill_surfaces_preserve_run_control_semantics(
    local_tmp_path: Path, integration_key: str
) -> None:
    root = _install_skills_profile(
        local_tmp_path / f"{integration_key}-advanced", integration_key, "advanced"
    )

    shared_reference = root / "references" / "run-bootstrap.md"
    assert shared_reference.is_file(), shared_reference
    _assert_shared_run_bootstrap_contract(shared_reference.read_text(encoding="utf-8"))

    for stage in CLASSIC_MODIFYING_WORKFLOWS:
        skill = root / f"spx-{stage}" / "SKILL.md"
        content = skill.read_text(encoding="utf-8")
        assert "Read `references/run-bootstrap.md`" in content, stage
        _assert_stage_semantics(content, stage)
