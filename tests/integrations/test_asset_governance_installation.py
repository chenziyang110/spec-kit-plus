"""Asset governance remains reachable across profiles without workflow routing."""

import json
from pathlib import Path

import pytest

from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest


REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("integration_key", ["codex", "claude", "cursor-agent"])
@pytest.mark.parametrize("profile", ["classic", "advanced"])
def test_every_generated_workflow_has_asset_contract_without_profile_leakage(tmp_path, integration_key, profile):
    integration = get_integration(integration_key)
    project = tmp_path / integration_key
    manifest = IntegrationManifest(integration_key, project)
    integration.setup(project, manifest, parsed_options={"workflow_profile": profile}, script_type="sh")
    skills = integration.skills_dest(project)
    passive = skills / "spec-kit-asset-governance/SKILL.md"
    assert passive.is_file() is (profile == "classic")
    workflows = list(skills.glob("sp-*/SKILL.md")) + list(skills.glob("spx-*/SKILL.md"))
    assert workflows
    for workflow in workflows:
        content = workflow.read_text(encoding="utf-8")
        assert "## Document and Asset Placement" in content, workflow
        assert "User-invoked workflow only" in content, workflow
        if workflow.parent.name.startswith("spx-"):
            assert "references/asset-governance.md" in content
            reference = workflow.parent / "references/asset-governance.md"
            assert reference.is_file()
            assert "assets route" in reference.read_text(encoding="utf-8")
    if profile == "classic":
        body = passive.read_text(encoding="utf-8")
        assert "Passive skill invocation must not enter any" in body
        assert "Existing workflow files alone do not activate a workflow" in body
        assert "never describe them as passed" in body.lower()
        assert "allow_implicit_invocation: false" not in body
    assert json.loads((project / ".specify/templates/asset-policy.json").read_text()) == json.loads((REPO_ROOT / "templates/asset-policy.json").read_text())
    assert not (project / ".asset-policy.json").exists()


def test_dual_install_and_repair_preserve_policy_and_user_modified_template(tmp_path):
    integration = get_integration("codex")
    project = tmp_path / "dual"
    project.mkdir()
    policy = project / ".asset-policy.json"
    policy.write_text('{"schema_version":1,"allowed_root_files":["team-report.md"]}\n', encoding="utf-8")
    original = policy.read_bytes()
    manifest = IntegrationManifest("codex", project)
    integration.setup(project, manifest, parsed_options={"workflow_profile": "classic"}, script_type="sh")
    template = project / ".specify/templates/asset-policy.json"
    template.write_text('{"schema_version":1,"source_roots":["custom-source"]}\n', encoding="utf-8")
    modified = template.read_bytes()
    integration.setup(project, manifest, parsed_options={"workflow_profile": "advanced"}, script_type="sh")
    integration.repair_runtime_assets(project, manifest)
    assert policy.read_bytes() == original
    assert template.read_bytes() == modified
    assert (integration.skills_dest(project) / "spec-kit-asset-governance/SKILL.md").is_file()
    assert (integration.skills_dest(project) / "spx-plan/SKILL.md").is_file()


def test_repair_restores_missing_policy_template_without_creating_project_policy(tmp_path):
    integration = get_integration("codex")
    manifest = IntegrationManifest("codex", tmp_path)
    integration.setup(tmp_path, manifest, parsed_options={"workflow_profile": "advanced"}, script_type="sh")
    template = tmp_path / ".specify/templates/asset-policy.json"
    expected = template.read_bytes()
    template.unlink()
    integration.repair_runtime_assets(tmp_path, manifest)
    assert template.read_bytes() == expected
    assert not (tmp_path / ".asset-policy.json").exists()


@pytest.mark.parametrize("integration_key", ["codex", "claude"])
def test_repair_restores_owned_passive_entrypoint_and_preserves_user_edit(tmp_path, integration_key):
    integration = get_integration(integration_key)
    manifest = IntegrationManifest(integration_key, tmp_path)
    integration.setup(tmp_path, manifest, parsed_options={"workflow_profile": "classic"}, script_type="sh")
    skill = integration.skills_dest(tmp_path) / "spec-kit-asset-governance/SKILL.md"
    original = skill.read_bytes()
    skill.unlink()
    integration.repair_runtime_assets(tmp_path, manifest, script_type="sh")
    assert skill.read_bytes() == original
    skill.write_bytes(original + b"\nProject-specific output convention.\n")
    modified = skill.read_bytes()
    integration.repair_runtime_assets(tmp_path, manifest, script_type="sh")
    assert skill.read_bytes() == modified


def test_advanced_repair_restores_asset_reference_without_classic_bundle(tmp_path):
    integration = get_integration("codex")
    manifest = IntegrationManifest("codex", tmp_path)
    integration.setup(tmp_path, manifest, parsed_options={"workflow_profile": "advanced"}, script_type="sh")
    skill = integration.skills_dest(tmp_path) / "spx-plan/SKILL.md"
    reference = skill.parent / "references/asset-governance.md"
    expected_skill, expected_reference = skill.read_bytes(), reference.read_bytes()
    skill.unlink()
    reference.unlink()
    integration.repair_runtime_assets(tmp_path, manifest, script_type="sh")
    assert skill.read_bytes() == expected_skill
    assert reference.read_bytes() == expected_reference
    assert not (integration.skills_dest(tmp_path) / "spec-kit-asset-governance").exists()


@pytest.mark.parametrize("integration_key", ["claude", "gemini"])
def test_native_integration_installs_shared_asset_adapter(tmp_path, integration_key):
    integration = get_integration(integration_key)
    manifest = IntegrationManifest(integration_key, tmp_path)
    integration.setup(tmp_path, manifest, script_type="sh")
    helper = tmp_path / ".specify/bin/specify-asset-guard.py"
    assert helper.read_bytes() == (REPO_ROOT / "src/specify_cli/shared_hooks/specify-asset-guard.py").read_bytes()
    assert helper.relative_to(tmp_path).as_posix() in manifest.files
    if integration_key == "gemini":
        hooks = json.loads((tmp_path / ".gemini/settings.json").read_text())["hooks"]
        assert "AfterAgent" in hooks
    else:
        hooks = json.loads((tmp_path / ".claude/settings.json").read_text())["hooks"]
        assert "Stop" in hooks


def test_codex_install_does_not_invent_native_file_hooks(tmp_path):
    integration = get_integration("codex")
    integration.setup(tmp_path, IntegrationManifest("codex", tmp_path), script_type="sh")
    assert not (tmp_path / ".codex/hooks.json").exists()
    assert not (tmp_path / ".codex/hooks/claude-hook-dispatch.py").exists()


def test_custom_command_destination_keeps_the_asset_contract(tmp_path):
    integration = get_integration("generic")
    manifest = IntegrationManifest("generic", tmp_path)
    integration.setup(tmp_path, manifest, parsed_options={"commands_dir": ".team-agent/actions"}, script_type="sh")
    commands = list((tmp_path / ".team-agent/actions").glob("*.md"))
    assert commands
    for command in commands:
        assert "## Document and Asset Placement" in command.read_text(encoding="utf-8")
    assert (tmp_path / ".specify/templates/asset-policy.json").is_file()


@pytest.mark.parametrize("script_type", ["sh", "ps"])
def test_gemini_asset_closeout_installs_once_and_uninstalls_without_removing_user_hook(tmp_path, script_type):
    integration = get_integration("gemini")
    manifest = IntegrationManifest("gemini", tmp_path)
    settings = tmp_path / ".gemini/settings.json"
    settings.parent.mkdir()
    user_hook = {"matcher": "*", "hooks": [{"name": "team-closeout", "type": "command", "command": "team-closeout-command"}]}
    mention_hook = {"matcher": "*", "hooks": [{"name": "describe-launcher", "type": "command", "command": "echo /some/project/.specify/bin/specify-hook gemini after-agent"}]}
    settings.write_text(json.dumps({"hooks": {"AfterAgent": [user_hook, mention_hook]}, "theme": "custom"}), encoding="utf-8")
    for _ in range(2):
        integration.setup(tmp_path, manifest, script_type=script_type)
    entries = json.loads(settings.read_text(encoding="utf-8"))["hooks"]["AfterAgent"]
    managed = [hook for entry in entries for hook in entry["hooks"] if hook.get("name") == "spec-kit-after-agent-assets"]
    assert len(managed) == 1
    assert user_hook in entries
    assert mention_hook in entries
    integration.uninstall(tmp_path, manifest)
    retained = json.loads(settings.read_text(encoding="utf-8"))
    assert retained["hooks"]["AfterAgent"] == [user_hook, mention_hook]
    assert retained["theme"] == "custom"


@pytest.mark.parametrize("command,managed", [
    ('"$GEMINI_PROJECT_DIR"/.specify/bin/specify-hook gemini after-agent', True),
    ('"$GEMINI_PROJECT_DIR"/.specify/bin/specify-hook.cmd gemini after-agent', True),
    ('& "$env:GEMINI_PROJECT_DIR/.specify/bin/specify-hook.cmd" gemini after-agent', True),
    ('python "C:\\Project Space\\.specify\\bin\\specify-hook.py" gemini after-agent', True),
    ('python "$GEMINI_PROJECT_DIR/.gemini/hooks/gemini-hook-dispatch.py" before-tool', True),
    ('echo /some/project/.specify/bin/specify-hook gemini after-agent', False),
    ('echo gemini-hook-dispatch.py before-tool', False),
    ('echo x; /some/project/.specify/bin/specify-hook gemini after-agent', False),
    ('/some/project/.specify/bin/specify-hook gemini after-agent && team-closeout', False),
    ('"$(echo /some/project)/.specify/bin/specify-hook" gemini after-agent', False),
])
def test_gemini_managed_hook_requires_complete_launcher_argv(command, managed):
    integration = get_integration("gemini")
    assert integration._is_managed_hook_command(command, integration._managed_hook_command_suffixes()) is managed


@pytest.mark.parametrize("script_type", ["sh", "ps"])
def test_claude_asset_hook_upgrade_and_uninstall_preserve_user_launcher_mentions(tmp_path, script_type):
    integration = get_integration("claude")
    manifest = IntegrationManifest("claude", tmp_path)
    settings = tmp_path / ".claude/settings.json"
    settings.parent.mkdir()
    commands = [
        "echo /some/project/.specify/bin/specify-hook claude stop-monitor",
        "echo claude-hook-dispatch.py stop-monitor",
        "/some/project/.specify/bin/specify-hook claude stop-monitor && team-closeout",
        "node -e \"console.log('specify-hook.mjs')\" specify-hook claude stop-monitor",
    ]
    user_entries = [{"matcher": "", "hooks": [{"type": "command", "command": command}]} for command in commands]
    user_entries.extend({"matcher": "", "hooks": [hook]} for hook in [
        {"type": "command", "command": "node", "args": ["/team/tools/audit-specify-hook.mjs"]},
        {"type": "command", "command": "node", "args": ["${CLAUDE_PROJECT_DIR}/.specify/bin/specify-hook.mjs", "claude", "stop-monitor", "--team-flag"]},
        {"type": "command", "command": "node", "args": ["-e", "console.log('specify-hook.mjs')", "claude", "team-event"]},
        {"type": "command", "command": "node", "args": ["-e", "console.log('specify-hook.mjs')", "specify-hook", "claude", "stop-monitor"]},
    ])
    settings.write_text(json.dumps({"hooks": {"Stop": user_entries}, "theme": "custom"}), encoding="utf-8")
    for _ in range(2):
        integration.setup(tmp_path, manifest, script_type=script_type)
    entries = json.loads(settings.read_text(encoding="utf-8"))["hooks"]["Stop"]
    for entry in user_entries:
        assert entry in entries
    integration.uninstall(tmp_path, manifest)
    retained = json.loads(settings.read_text(encoding="utf-8"))
    assert retained["hooks"]["Stop"] == user_entries
    assert retained["theme"] == "custom"
