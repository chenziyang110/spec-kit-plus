"""Keep default cognition navigation small without losing triggered contracts."""

import hashlib
import json
import re
from pathlib import Path

import pytest

from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest
from specify_cli.launcher import write_runtime_launcher_config
from specify_cli.specify_runtime import project_runtime_launcher_arg

from .template_utils import read_cognition_contract

ROOT = Path(__file__).resolve().parents[1]
ADVANCED = ROOT / "templates/advanced-skills/_shared"
PASSIVE = ROOT / "templates/passive-skills/spec-kit-project-cognition-gate"
LINK = re.compile(r"\]\(((?:references/)?project-cognition-(?:closeout|semantic-audit)\.md)\)")


@pytest.mark.parametrize("entry", [ADVANCED / "project-cognition.md", PASSIVE / "SKILL.md"])
def test_default_navigation_has_explicit_mutation_and_resume_triggers(entry: Path) -> None:
    content = entry.read_text(encoding="utf-8")
    assert "minimal_live_reads" in content
    assert "live" in content and "evidence" in content
    assert "Before an owning mutation workflow changes" in content
    assert "resuming unfinished closeout, a blocked queued intent, or predecessor" in content
    assert "read-only" in content.lower() and "planning-only artifact" in content.lower()
    assert "does not waive closeout ownership" in content or "never waives this closeout gate" in content
    assert "--verification-json -" not in content
    assert "replacement_input_digest" not in content
    assert "predecessor_recovery_blocked" not in content
    assert "mutation-receipt --workflow" not in content
    for relative in LINK.findall(content):
        assert (entry.parent / relative).is_file()


def test_semantic_audit_is_required_before_sensitive_claims_and_resume() -> None:
    entry = (ADVANCED / "project-cognition.md").read_text(encoding="utf-8")
    assert "Before semantic routing affects permission, source-write scope, resume" in entry
    assert "read it before reusing any persisted semantic route or `claim_ready`" in entry
    assert "semantic-audit --input-json" not in entry
    contract = read_cognition_contract(ADVANCED / "project-cognition.md")
    for token in (
        "semantic-audit --input-json", "semantic-audit-resume --input-json",
        "atomically writes both", "never recreate", "never create a resume-validation file",
        "workflow_authorization", "claim-specific", "keep the final claim blocked",
        "lower safe permission", "do not create canonical audit files",
    ):
        assert token in contract, token


@pytest.mark.parametrize("profile", ["classic", "advanced"])
@pytest.mark.parametrize("script_type", ["sh", "ps"])
@pytest.mark.parametrize("integration_key", ["codex", "claude"])
def test_installed_triggered_contracts_are_rendered_reachable_and_owned(
    tmp_path: Path, profile: str, script_type: str, integration_key: str, record_property,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    runtime = tmp_path / "runtime-fixture.exe"
    runtime.write_bytes(b"runtime binding fixture; not executed")
    write_runtime_launcher_config(project, runtime)
    integration = get_integration(integration_key)
    manifest = IntegrationManifest(integration_key, project)
    integration.setup(project, manifest, parsed_options={"workflow_profile": profile}, script_type=script_type)
    skills = integration.skills_dest(project)
    if profile == "classic":
        entries = [skills / "spec-kit-project-cognition-gate/SKILL.md"]
        # Non-template support assets retain their original bytes.
        raw = ROOT / "templates/passive-skills/code-review-skill/reference/react.md"
        assert (skills / "code-review-skill/reference/react.md").read_bytes() == raw.read_bytes()
    else:
        assert not (skills / "spec-kit-project-cognition-gate").exists()
        entries = sorted(skills.glob("spx-*/references/project-cognition.md"))
        assert len(entries) == 30
        entries.append(skills / "references/project-cognition.md")
        assert {path.name for path in skills.glob("sp-*")} == {"sp-map-scan", "sp-map-build", "sp-map-update"}

    bindings = []
    for entry in entries:
        relatives = LINK.findall(entry.read_text(encoding="utf-8"))
        assert len(relatives) == (2 if profile == "advanced" else 1)
        for relative in relatives:
            path = entry.parent / relative
            content = path.read_text(encoding="utf-8")
            assert "{{specify-subcmd:" not in content
            assert "{{invoke:" not in content
            assert "SPECIFY_RUNTIME_LAUNCHER_UNAVAILABLE" not in content
            assert project_runtime_launcher_arg() in content
            assert path.relative_to(project).as_posix() in manifest.files
            bindings.append({"path": path.relative_to(project).as_posix(), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        effective = read_cognition_contract(entry)
        for required in ("predecessor_recovery_blocked", "replacement_input_digest", "--verification-json -", "same update lock", "Never invent verification commands"):
            assert required in effective
    record_property("installed_entries", len(entries))
    record_property("installed_reference_bindings", json.dumps(bindings))


@pytest.mark.parametrize("profile", ["classic", "advanced"])
@pytest.mark.parametrize("script_type", ["sh", "ps"])
def test_repair_restores_only_missing_owned_triggered_reference(
    tmp_path: Path, profile: str, script_type: str,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    runtime = tmp_path / "runtime-fixture.exe"
    runtime.write_bytes(b"runtime binding fixture; not executed")
    write_runtime_launcher_config(project, runtime)
    integration = get_integration("codex")
    manifest = IntegrationManifest("codex", project)
    integration.setup(project, manifest, parsed_options={"workflow_profile": profile}, script_type=script_type)
    skills = integration.skills_dest(project)
    prefix = "spec-kit-project-cognition-gate" if profile == "classic" else "spx-ask"
    reference = skills / prefix / "references/project-cognition-closeout.md"
    original = reference.read_bytes()
    reference.unlink()
    repaired = integration.repair_runtime_assets(project, manifest, script_type=script_type)
    assert reference in repaired
    assert reference.read_bytes() == original
    reference.write_bytes(original + b"\nUser-owned closeout note.\n")
    modified = reference.read_bytes()
    assert reference not in integration.repair_runtime_assets(project, manifest, script_type=script_type)
    assert reference.read_bytes() == modified
    assert (skills / "spec-kit-project-cognition-gate").exists() == (profile == "classic")


def test_advanced_shared_reference_inventory_includes_triggered_contracts() -> None:
    surface_map = json.loads((ADVANCED / "surface-map.json").read_text(encoding="utf-8"))
    for name in ("project-cognition.md", "project-cognition-closeout.md", "project-cognition-semantic-audit.md"):
        assert f"_shared/{name}" in surface_map["shared_references"]
        assert (ADVANCED / name).is_file()
