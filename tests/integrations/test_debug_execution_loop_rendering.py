"""Install actual Debug prompts in native formats; do not mock the renderer.

These assertions prove delivery and repair of the prompt contract, not that an
LLM executed it, or that any particular product defect has been fixed.
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest

from specify_cli import _install_shared_infra
from specify_cli.integrations import get_integration
from specify_cli.integrations.base import SkillsIntegration
from specify_cli.integrations.manifest import IntegrationManifest


@pytest.fixture(scope="module", params=[
    ("codex", "classic", "sh"), ("codex", "advanced", "sh"),
    ("claude", "classic", "sh"), ("claude", "advanced", "sh"),
    ("gemini", "classic", "sh"),
    ("codex", "classic", "ps"), ("codex", "advanced", "ps"),
], ids=lambda values: "-".join(values))
def installed_debug(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory):
    agent, profile, script_type = request.param
    project = tmp_path_factory.mktemp(f"debug-loop-{agent}-{profile}-{script_type}")
    integration = get_integration(agent)
    assert integration is not None
    assert _install_shared_infra(project, script_type) is True
    manifest = IntegrationManifest(agent, project)
    created = integration.setup(project, manifest,
        parsed_options={"workflow_profile": profile}, script_type=script_type)
    if isinstance(integration, SkillsIntegration):
        prefix = "spx" if profile == "advanced" else "sp"
        entry = integration.skills_dest(project) / f"{prefix}-debug/SKILL.md"
    else:
        matches = [path for path in created if path.name == integration.command_filename("debug")]
        assert len(matches) == 1
        entry = matches[0]
    assert entry.is_file()
    return project, integration, manifest, profile, script_type, entry


def _effective_text(entry: Path) -> str:
    content = entry.read_text(encoding="utf-8")
    if entry.suffix == ".toml":
        content = tomllib.loads(content)["prompt"]
    references = entry.parent / "references"
    if references.is_dir():
        content += "\n" + "\n".join(path.read_text(encoding="utf-8")
            for path in sorted(references.glob("*.md")))
    return re.sub(r"\s+", " ", content).lower()


def test_installed_debug_reaches_full_loop_and_worker_contract(installed_debug) -> None:
    project, _, _, profile, _, entry = installed_debug
    content = _effective_text(entry)
    for required in (
        "recency alone", "earliest", "do not impose deep-only fields",
        "red must match the target", "lease conflict", "newer evidence",
        "input revision", "wrong-session", "final integrated revision",
        "awaiting_human_verify", "explicit human confirmation", "same invocation",
    ):
        assert required in content, (entry, required)
    for forbidden in (
        "the graph engine (gatheringnode) will return", "gathering returns an `await_input`",
        "explicit human confirmation or an evidence-backed classification",
        "if that expands beyond the debug fix lane, route it through",
        "{{spec-kit-include:", "execute_command: debug",
    ):
        assert forbidden not in content, (entry, forbidden)
    worker = (entry.parent / "references/investigator-worker.md" if profile == "advanced"
              else project / ".specify/templates/worker-prompts/debug-investigator.md")
    worker_text = re.sub(r"\s+", " ", worker.read_text(encoding="utf-8")).lower()
    assert "session/lane identity" in worker_text
    assert "a claim awaiting acceptance" in worker_text


def test_missing_debug_reference_repair_preserves_user_edits(installed_debug) -> None:
    project, integration, manifest, profile, script_type, entry = installed_debug
    if not isinstance(integration, SkillsIntegration):
        pytest.skip("The TOML entrypoint embeds its references rather than owning skill sidecars")
    filename = "investigation-contract.md" if profile == "advanced" else "debug-state.md"
    reference = entry.parent / "references" / filename
    assert reference.is_file()
    expected = reference.read_bytes()
    original_entry = entry.read_bytes()
    user_content = original_entry + b"\n<!-- user-owned debug note -->\n"
    try:
        entry.write_bytes(user_content)
        reference.unlink()
        if profile == "advanced":
            integration.repair_missing_advanced_skill_files(project, manifest, script_type=script_type)
        else:
            integration.repair_missing_command_reference_sidecars(project, manifest, script_type=script_type)
        assert reference.read_bytes() == expected
        assert entry.read_bytes() == user_content
    finally:
        entry.write_bytes(original_entry)
        # Restore fixture isolation even if a repair assertion fails.
        if not reference.exists():
            reference.write_bytes(expected)
