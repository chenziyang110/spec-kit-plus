"""Verify conditional cognition contracts in installed, profile-owned surfaces."""

import hashlib
import json
import os
import re
import shlex
from pathlib import Path

import pytest

from specify_cli.integrations import get_integration
from specify_cli.integrations.base import COGNITION_CAPSULE_REUSE_GUIDANCE
from specify_cli.integrations.manifest import IntegrationManifest
from specify_cli.launcher import write_runtime_launcher_config
from specify_cli.specify_runtime import project_runtime_launcher_arg


ROOT = Path(__file__).resolve().parents[1]
SHARED_ENTRIES = (
    "templates/command-partials/common/context-loading-gradient.md",
    "templates/command-partials/common/planning-context-loading-gradient.md",
    "templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md",
    "templates/advanced-skills/_shared/project-cognition.md",
)


def _normalized(content: str) -> str:
    return " ".join(content.split())


def _assert_reuse_contract(content: str) -> None:
    normalized = _normalized(content)
    for binding in (
        "task/query", "intent", "target", "scope", "facets", "negative constraints",
        "permissions", "live-source/evidence digests", "runtime identity",
        "expansion_ref.id", "query_fingerprint", "active_generation_id",
        "navigation_digest", "claim-revision", "resume", "recovery",
        "cognition.expansion.snapshot.v2", "status=ok", "expansion_contract_version=2",
        "readiness=query_ready|review",
        "outer exit code 0 alone is not proof", "Learning index/source evidence",
        "project rules", "graph digest does not prove Learning unchanged",
    ):
        assert binding in normalized, binding
    assert "actual read-only" in normalized
    assert "preparatory" in normalized.lower()
    assert "do not repeat" in normalized or "does not restart" in normalized
    assert "Missing, stale" in normalized


def _assert_paging_contract(content: str) -> None:
    normalized = _normalized(content)
    for binding in (
        "catalog_page.next_argv", "revision", "snapshot_bound", "navigation_digest",
        "offset", "limit", "returned", "total", "owners", "consumers/dependencies",
        "verification routes", "negative constraints", "missing_facets",
        "first word match", "insufficient_index", "resolution_state=resolved_exact",
        "total_count", "returned_count", "has_more", "next_argv",
        "cognition.catalog.snapshot.v1", "cognition.claim-evidence.page.v1",
    ):
        assert binding in normalized, binding
    assert "replace only" in normalized and "executable" in normalized
    assert "--offset <next_offset>" not in content
    assert "using `catalog_page.next_offset` while" not in content


@pytest.mark.parametrize("relative", SHARED_ENTRIES)
def test_shared_intake_requires_bound_snapshot_and_complete_facets(relative: str) -> None:
    content = (ROOT / relative).read_text(encoding="utf-8")
    _assert_reuse_contract(content)
    _assert_paging_contract(content)
    assert "Capability IDs" in content or "capabilities, not CLI commands" in content


@pytest.mark.parametrize("integration_key", ["codex", "claude"])
def test_implement_and_teams_use_the_same_reuse_gate(
    tmp_path: Path, integration_key: str,
) -> None:
    integration = get_integration(integration_key)
    gate = integration._project_cognition_query_gate_line(
        command_name="implement", command_step="before assigning team-managed work",
    )
    assert COGNITION_CAPSULE_REUSE_GUIDANCE in gate
    skill = tmp_path / "SKILL.md"
    skill.write_text("# Team fixture\n", encoding="utf-8")
    manifest = IntegrationManifest(integration_key, tmp_path)
    integration._augment_implement_teams_shared_contract(
        [], tmp_path, manifest, skill,
        canonical_command="sp-implement", teams_command="sp-implement-teams",
        backend_label="fixture backend",
    )
    teams = skill.read_text(encoding="utf-8")
    assert "**Current-Task Navigation Repair**" in teams
    assert "before assigning team-managed work" in teams
    assert "1. run `{{specify-subcmd:specify-runtime cognition compass" not in teams
    _assert_reuse_contract(teams)
    _assert_paging_contract(teams)


@pytest.mark.parametrize("integration_key", ["codex", "claude"])
@pytest.mark.parametrize("script_type", ["sh", "ps"])
@pytest.mark.parametrize("profile", ["classic", "advanced"])
def test_installed_profiles_render_conditional_intake_without_ownership_drift(
    tmp_path: Path, integration_key: str, script_type: str, profile: str,
    record_property,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    runtime = tmp_path / "runtime-binding-fixture.exe"
    runtime.write_bytes(b"fixture binding only; never executed")
    write_runtime_launcher_config(project, runtime)
    integration = get_integration(integration_key)
    manifest = IntegrationManifest(integration_key, project)
    integration.setup(
        project, manifest, parsed_options={"workflow_profile": profile},
        script_type=script_type,
    )
    skills = integration.skills_dest(project)
    if profile == "classic":
        entries = [skills / "spec-kit-project-cognition-gate/SKILL.md"]
        ask = (skills / "sp-ask/SKILL.md").read_text(encoding="utf-8")
        assert "valid-capsule check" in ask
        assert "Chat continuity alone" in ask
        assert "actual read-only" in ask
        assert "inner payload's `status=ok`" in ask
        assert "catalog_page.next_argv" in ask
        teams = (skills / "sp-implement-teams/SKILL.md").read_text(encoding="utf-8")
        _assert_reuse_contract(teams)
        _assert_paging_contract(teams)
        assert "Include the verified capsule or fresh packet" in teams
        assert not (skills / "spx-ask").exists()
    else:
        entries = sorted(skills.glob("spx-*/references/project-cognition.md"))
        assert len(entries) == 30
        entries.append(skills / "references/project-cognition.md")
        assert not (skills / "spec-kit-project-cognition-gate").exists()
        assert {path.name for path in skills.glob("sp-*")} == {
            "sp-map-scan", "sp-map-build", "sp-map-update",
        }

    planning_consumers = []
    for command in ("plan", "tasks"):
        name = f"{'sp' if profile == 'classic' else 'spx'}-{command}"
        entry = skills / name / "SKILL.md"
        entry_content = entry.read_text(encoding="utf-8")
        if profile == "classic":
            assert "## Project Cognition Advisory Gate" in entry_content
            contract = entry
            contract_content = entry_content
        else:
            assert "Read `references/project-cognition.md`" in entry_content
            contract = entry.parent / "references/project-cognition.md"
            contract_content = contract.read_text(encoding="utf-8")
        _assert_reuse_contract(contract_content)
        _assert_paging_contract(contract_content)
        expansions = re.findall(
            r"`([^`\r\n]*\bcognition expand [^`\r\n]+)`", contract_content,
        )
        assert expansions
        for expansion in expansions:
            argv = [token.strip("'\"") for token in shlex.split(expansion, posix=os.name != "nt")]
            assert "--id" in argv and argv[argv.index("--id") + 1] == "<id>"
            assert "--section" in argv
            assert "--ref" not in argv
            assert project_runtime_launcher_arg() in expansion
        assert "expansion_ref.available_sections" in contract_content
        assert entry.relative_to(project).as_posix() in manifest.files
        assert contract.relative_to(project).as_posix() in manifest.files
        planning_consumers.append({
            "entry": entry.relative_to(project).as_posix(),
            "entry_sha256": hashlib.sha256(entry.read_bytes()).hexdigest(),
            "contract": contract.relative_to(project).as_posix(),
            "contract_sha256": hashlib.sha256(contract.read_bytes()).hexdigest(),
            "expansion_commands": expansions,
        })
    record_property("installed_planning_consumers", json.dumps(planning_consumers))

    observed = []
    for entry in entries:
        content = entry.read_text(encoding="utf-8")
        _assert_reuse_contract(content)
        _assert_paging_contract(content)
        assert project_runtime_launcher_arg() in content
        assert "{{specify-subcmd:" not in content
        assert "SPECIFY_RUNTIME_LAUNCHER_UNAVAILABLE:" not in content
        assert entry.relative_to(project).as_posix() in manifest.files
        observed.append({
            "path": entry.relative_to(project).as_posix(),
            "sha256": hashlib.sha256(entry.read_bytes()).hexdigest(),
        })
    record_property("installed_conditional_intake_bindings", json.dumps(observed))


@pytest.mark.parametrize("integration_key", ["codex", "claude"])
@pytest.mark.parametrize("script_type", ["sh", "ps"])
def test_advanced_classic_map_companions_remain_byte_equivalent(
    tmp_path: Path, integration_key: str, script_type: str,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    runtime = tmp_path / "runtime-binding-fixture.exe"
    runtime.write_bytes(b"fixture binding only; never executed")
    write_runtime_launcher_config(project, runtime)
    integration = get_integration(integration_key)
    manifest = IntegrationManifest(integration_key, project)
    integration.setup(
        project, manifest, parsed_options={"workflow_profile": "classic"},
        script_type=script_type,
    )
    skills = integration.skills_dest(project)
    original = {
        path.relative_to(skills).as_posix(): path.read_bytes()
        for command in ("sp-map-scan", "sp-map-build", "sp-map-update")
        for path in (skills / command).rglob("*")
        if path.is_file()
    }
    assert "catalog_page.next_argv" in original["sp-map-build/SKILL.md"].decode()
    fresh_project = tmp_path / "fresh-advanced"
    fresh_project.mkdir()
    write_runtime_launcher_config(fresh_project, runtime)
    fresh_manifest = IntegrationManifest(integration_key, fresh_project)
    integration.setup(
        fresh_project, fresh_manifest, parsed_options={"workflow_profile": "advanced"},
        script_type=script_type,
    )
    fresh_skills = integration.skills_dest(fresh_project)
    assert all((fresh_skills / relative).read_bytes() == data for relative, data in original.items())
    integration.setup(
        project, manifest, parsed_options={"workflow_profile": "advanced"},
        script_type=script_type,
    )
    assert all((skills / relative).read_bytes() == data for relative, data in original.items())
    # Missing-only repair must restore native finalization without changing a
    # separately user-modified companion or its registered supporting assets.
    restored_path = fresh_skills / "sp-map-scan/SKILL.md"
    restored_path.unlink()
    custom_path = fresh_skills / "sp-map-build/SKILL.md"
    custom_content = custom_path.read_bytes() + b"\nUser-owned map note.\n"
    custom_path.write_bytes(custom_content)
    repaired = integration.repair_runtime_assets(
        fresh_project, fresh_manifest, script_type=script_type,
    )
    assert restored_path in repaired
    assert restored_path.read_bytes() == original["sp-map-scan/SKILL.md"]
    assert custom_path not in repaired
    assert custom_path.read_bytes() == custom_content
    assert all(
        (fresh_skills / relative).read_bytes() == data
        for relative, data in original.items()
        if relative != "sp-map-build/SKILL.md"
    )


def test_ask_and_map_guidance_do_not_reconstruct_catalog_offsets() -> None:
    for relative in (
        "templates/command-partials/ask/shell.md", "templates/commands/map-build.md",
        "templates/advanced-skills/spx-map-build/SKILL.md",
        "templates/project-handbook-template.md",
    ):
        content = (ROOT / relative).read_text(encoding="utf-8")
        assert "catalog_page.next_argv" in content
        assert "catalog_page.next_offset" not in content
        assert "first word match" in _normalized(content) or "one easy lexical match" in _normalized(content)
        assert "executable" in content
