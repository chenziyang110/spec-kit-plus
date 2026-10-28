"""Scoped semantic registration must be available before mutation closeout."""

import hashlib
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from specify_cli import specify_runtime
from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest


CAPABILITIES = {"cognition.scoped-register", "cognition.scoped-registration.v1"}


@pytest.mark.parametrize("missing", sorted(CAPABILITIES))
def test_launcher_refuses_each_missing_registration_capability(monkeypatch, missing):
    observed = sorted(set(specify_runtime.REQUIRED_CAPABILITIES) - {missing})
    assert "cognition.closeout.binding.v1" in observed
    monkeypatch.setattr(
        specify_runtime.subprocess, "run",
        lambda *_args, **_kwargs: SimpleNamespace(
            returncode=0, stderr="", stdout=json.dumps({
                "status": "ok", "data": {
                    "protocol_version": specify_runtime.EXPECTED_RUNTIME_PROTOCOL,
                    "capability_ids": observed,
                },
            }),
        ),
    )
    assert not specify_runtime.launcher_supports_required_commands(["old-runtime"])


@pytest.mark.parametrize("profile", ["classic", "advanced"])
def test_observed_pre_registration_binary_is_refused_without_mutation(tmp_path, profile):
    binary_name = os.environ.get("SPECIFY_COGNITION_PRE_REGISTRATION_RUNTIME")
    digest = os.environ.get("SPECIFY_COGNITION_PRE_REGISTRATION_RUNTIME_SHA256")
    if not binary_name or not digest:
        pytest.skip("an exact observed pre-registration runtime is required")
    binary = Path(binary_name).resolve()
    assert hashlib.sha256(binary.read_bytes()).hexdigest() == digest
    project = tmp_path / profile
    integration = get_integration("codex")
    integration.setup(
        project, IntegrationManifest("codex", project),
        parsed_options={"workflow_profile": profile}, script_type="ps",
    )
    specify_runtime.write_project_launcher_config(project, binary)
    entrypoint = specify_runtime.project_runtime_entrypoint_path(project)
    before = {str(p.relative_to(project)): p.read_bytes()
              for p in project.rglob("*") if p.is_file()}
    handshake = specify_runtime._runtime_handshake([str(entrypoint)], cwd=project)
    assert handshake is not None
    observed = set(handshake["capability_ids"])
    assert "cognition.closeout.binding.v1" in observed
    assert CAPABILITIES.isdisjoint(observed)
    assert not specify_runtime.launcher_supports_required_commands(
        [str(entrypoint)], cwd=project,
    )
    assert before == {str(p.relative_to(project)): p.read_bytes()
                      for p in project.rglob("*") if p.is_file()}
    assert hashlib.sha256(binary.read_bytes()).hexdigest() == digest


def test_installers_refuse_missing_registration_before_publication():
    root = Path(__file__).resolve().parents[1]
    for name, publication in [
        ("install.sh", "mv -f"),
        ("install.ps1", "Move-Item -LiteralPath $candidate"),
    ]:
        text = (root / "tools/specify-runtime" / name).read_text(encoding="utf-8")
        guard = text.index("Downloaded binary lacks required scoped cognition registration capability")
        assert guard < text.index(publication)
        for capability in CAPABILITIES:
            assert capability in text[:guard]
        if name.endswith(".sh"):
            assert 'if ! "$candidate" api ensure --capabilities ' in text[:guard]
        else:
            assert "$handshakePayload.data.capability_ids -notcontains $capability" in text[:guard]


@pytest.mark.parametrize("integration_key", ["codex", "claude"])
@pytest.mark.parametrize("profile", ["classic", "advanced"])
def test_installed_mutation_entries_require_scoped_semantics(tmp_path, integration_key, profile):
    project = tmp_path / integration_key / profile
    integration = get_integration(integration_key)
    integration.setup(
        project, IntegrationManifest(integration_key, project),
        parsed_options={"workflow_profile": profile}, script_type="ps",
    )
    skills = integration.skills_dest(project)
    prefix = "sp" if profile == "classic" else "spx"
    for command in ["fast", "debug", "implement", "quick", "review", "e2e", "do"]:
        owner = skills / f"{prefix}-{command}"
        effective = " ".join("\n".join(
            p.read_text(encoding="utf-8") for p in sorted(owner.rglob("*.md"))
        ).split())
        assert "cognition.scoped-registration.v1" in effective, command
        assert "cognition-scoped-registration-draft.v1" in effective, command
        assert "registration_apply_argv" in effective, command
        assert "registers into the same update journal before validation and receipt" in effective, command
        assert "do not run standalone scoped-register around shared apply" in effective, command
        if profile == "classic":
            assert "generic verification must not revive" in effective, command
            assert "unknown relationship remains an explicit unresolved obligation" in effective, command
            assert "existing native proof without another begin/seal cycle" in effective, command
        else:
            assert "Generic passing tests cannot revive" in effective, command
            assert "Truncated closures and unknown relations remain unresolved" in effective, command
            assert "existing stronger native proof" in effective, command
        assert "{{specify-subcmd:" not in effective, command
    if profile == "advanced":
        assert not (skills / "spec-kit-project-cognition-gate").exists()
