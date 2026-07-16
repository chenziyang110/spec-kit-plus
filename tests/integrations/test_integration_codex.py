"""Tests for CodexIntegration."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from specify_cli.launcher import render_command

from .test_base import (
    _assert_canonical_cognition_intake_contract,
    _assert_subagent_using_surfaces_have_discovery,
)
from .test_integration_base_skills import (
    _assert_compact_managed_context,
    _extract_generated_cognition_policy,
)
from tests.template_utils import assert_quick_checkpoint_card_shape

REPO_ROOT = Path(__file__).resolve().parents[2]

STALE_COGNITION_ADDENDUM_PHRASES = (
    "for blocked, stale, missing, or incomplete references",
    "{{invoke:map-scan}} -> {{invoke:map-build}} or "
    + "{{invoke:map-update}} as "
    + "appropriate",
    "status and slice artifacts",
    "status and debug-oriented slice artifacts",
    "required project cognition status and slice artifacts",
    "graph-native runtime coverage",
    "map " + "repair",
    "first-baseline " + "map " + "repair",
    "user explicitly requested " + "map " + "repair",
    "reported map-maintenance action as follow-up " + "unless",
    "when the user wants " + "map " + "repair",
    "missing or " + "stale",
    "follow-up map maintenance when " + "useful",
    "recommend sp-map-update or " + "sp-map-scan -> sp-map-build",
    "recommend map-update or " + "map-scan -> map-build",
    "user wants " + "repair",
    "the user wants " + "repair",
    "path-index-" + "incomplete",
    "path-index " + "incomplete",
    "unadoptable " + "coverage gaps",
)


def _read_skill_with_references(skill_path: Path) -> str:
    parts = [skill_path.read_text(encoding="utf-8")]
    references_dir = skill_path.parent / "references"
    if references_dir.is_dir():
        parts.extend(
            path.read_text(encoding="utf-8")
            for path in sorted(references_dir.glob("**/*.md"))
        )
    return "\n\n".join(parts)


def _assert_stable_subagent_contract(content: str) -> None:
    lower = content.lower()

    assert "native subagents" in lower
    assert "validated `workertaskpacket`" in lower
    assert "structured handoff" in lower
    assert "`sp-teams` only" in lower


def _run_semantic_audit_resume_fixture(resume_path: Path) -> dict[str, object]:
    result = subprocess.run(
        [
            "go",
            "run",
            ".",
            "semantic-audit-resume",
            "--input",
            str(resume_path),
            "--format",
            "json",
        ],
        cwd=REPO_ROOT / "tools" / "project-cognition",
        capture_output=True,
        check=False,
        encoding="utf-8",
        errors="replace",
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_codex_integration_metadata():
    from specify_cli.integrations import get_integration

    integration = get_integration("codex")

    assert integration is not None
    assert integration.config["folder"] == ".codex/"
    assert integration.config["commands_subdir"] == "skills"
    assert integration.context_file == "AGENTS.md"


def test_codex_install_inventory_tracks_core_skills_and_team_assets(tmp_path):
    from specify_cli.codex_team import install_codex_team_assets
    from specify_cli.integrations import get_integration
    from specify_cli.integrations.manifest import IntegrationManifest

    integration = get_integration("codex")
    manifest = IntegrationManifest("codex", tmp_path)

    integration.setup(tmp_path, manifest)
    install_codex_team_assets(tmp_path, manifest, integration_key="codex")

    expected_owned_paths = (
        ".codex/config.toml",
        ".codex/skills/sp-plan/SKILL.md",
        ".codex/skills/sp-implement/SKILL.md",
        ".codex/skills/sp-teams/SKILL.md",
        ".specify/config.json",
        ".specify/teams/README.md",
        ".specify/teams/runtime.json",
    )

    for rel_path in expected_owned_paths:
        assert (tmp_path / rel_path).exists()
        assert rel_path in manifest.files


def test_codex_setup_removes_misplaced_claude_hook_artifacts(tmp_path):
    from specify_cli.integrations import get_integration
    from specify_cli.integrations.manifest import IntegrationManifest
    from specify_cli.launcher import render_claude_hook_launcher

    hooks_path = tmp_path / ".codex" / "hooks.json"
    hooks_path.parent.mkdir(parents=True)
    hooks_path.write_text(
        json.dumps(
            {
                "hooks": {
                    "PostToolUse": [
                        {
                            "matcher": "Bash|Edit|Write|MultiEdit|Task",
                            "hooks": [
                                render_claude_hook_launcher("post-tool-session-state")
                            ],
                        }
                    ]
                }
            }
        )
        + "\n",
        encoding="utf-8",
    )
    hooks_dir = tmp_path / ".codex" / "hooks"
    hooks_dir.mkdir()
    (hooks_dir / "claude-hook-dispatch.py").write_text("print('stale')\n", encoding="utf-8")
    (hooks_dir / "README.md").write_text("# Claude Hook Assets\n", encoding="utf-8")

    integration = get_integration("codex")
    manifest = IntegrationManifest("codex", tmp_path)
    integration.setup(tmp_path, manifest)

    assert not hooks_path.exists()
    assert not (hooks_dir / "claude-hook-dispatch.py").exists()
    assert not hooks_dir.exists()


def test_codex_setup_strips_misplaced_claude_hooks_without_removing_custom_hooks(tmp_path):
    from specify_cli.integrations import get_integration
    from specify_cli.integrations.manifest import IntegrationManifest
    from specify_cli.launcher import render_claude_hook_launcher

    hooks_path = tmp_path / ".codex" / "hooks.json"
    hooks_path.parent.mkdir(parents=True)
    custom_hook = {
        "type": "command",
        "command": "node ./custom-codex-hook.mjs",
    }
    hooks_path.write_text(
        json.dumps(
            {
                "hooks": {
                    "PostToolUse": [
                        {
                            "matcher": "Bash",
                            "hooks": [
                                render_claude_hook_launcher("post-tool-session-state"),
                                custom_hook,
                            ],
                        }
                    ]
                },
                "custom": True,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    integration = get_integration("codex")
    manifest = IntegrationManifest("codex", tmp_path)
    integration.setup(tmp_path, manifest)

    repaired = json.loads(hooks_path.read_text(encoding="utf-8"))
    assert repaired["custom"] is True
    assert repaired["hooks"]["PostToolUse"][0]["hooks"] == [custom_hook]
    assert "specify-hook claude" not in json.dumps(repaired)


def test_codex_uninstall_removes_team_assets_and_restores_existing_configs(tmp_path):
    from specify_cli.codex_team import install_codex_team_assets
    from specify_cli.integrations import get_integration
    from specify_cli.integrations.manifest import IntegrationManifest

    existing_specify_config = '{"custom": true}\n'
    existing_codex_config = 'model = "gpt-test"\n'
    (tmp_path / ".specify").mkdir()
    (tmp_path / ".codex").mkdir()
    (tmp_path / ".specify" / "config.json").write_text(existing_specify_config, encoding="utf-8")
    (tmp_path / ".codex" / "config.toml").write_text(existing_codex_config, encoding="utf-8")

    integration = get_integration("codex")
    manifest = IntegrationManifest("codex", tmp_path)
    integration.setup(tmp_path, manifest)
    install_codex_team_assets(tmp_path, manifest, integration_key="codex")

    removed, skipped = integration.uninstall(tmp_path, manifest)

    removed_rel = {path.resolve().relative_to(tmp_path.resolve()).as_posix() for path in removed}
    assert ".specify/teams/runtime.json" in removed_rel
    assert ".specify/teams/README.md" in removed_rel
    assert ".specify/teams/install-state.json" in removed_rel
    assert skipped == []
    assert (tmp_path / ".specify" / "config.json").read_text(encoding="utf-8") == existing_specify_config
    assert (tmp_path / ".codex" / "config.toml").read_text(encoding="utf-8") == existing_codex_config


class TestCodexIntegration:
    KEY = "codex"
    CONTEXT_FILE = "AGENTS.md"

    def test_init_bootstrapped_context_file_contains_managed_guidance(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app
        import os

        project = tmp_path / f"context-guidance-{self.KEY}"
        project.mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = CliRunner().invoke(app, [
                "init", "--here", "--force", "--ai", self.KEY, "--script", "sh", "--no-git",
                "--ignore-agent-tools",
            ], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 0, f"init --ai {self.KEY} failed: {result.output}"
        content = (project / self.CONTEXT_FILE).read_text(encoding="utf-8")
        assert "## Active Technologies" in content
        _assert_compact_managed_context(content)

    def test_codex_generated_skills_do_not_include_obsolete_cognition_addenda(self, tmp_path):
        from specify_cli.integrations import get_integration
        from specify_cli.integrations.manifest import IntegrationManifest

        integration = get_integration(self.KEY)
        manifest = IntegrationManifest(self.KEY, tmp_path)
        integration.setup(tmp_path, manifest)

        skills_dir = tmp_path / ".codex" / "skills"
        generated = "\n".join(
            _read_skill_with_references(path).lower()
            for path in skills_dir.glob("**/SKILL.md")
        )
        cognition_policy = "\n".join(
            _extract_generated_cognition_policy(path.read_text(encoding="utf-8"))
            for path in skills_dir.glob("**/SKILL.md")
        )

        assert "project-cognition query" in generated
        assert "alias catalog" in generated
        assert "semantic_intake" in generated
        assert "facet coverage" in generated
        assert "concept_decisions" in generated
        assert "covered_facets" in generated
        assert "missing_facets" in generated
        assert "match_sources" in generated
        assert "lexicon_generation_id" in generated
        assert "minimal_live_reads" in generated
        _assert_canonical_cognition_intake_contract(generated)
        assert "returned map terms" not in generated
        for phrase in STALE_COGNITION_ADDENDUM_PHRASES:
            assert phrase not in cognition_policy


class TestCodexAutoPromote:
    """--ai codex auto-promotes to integration path."""

    def test_ai_codex_without_ai_skills_auto_promotes(self, tmp_path):
        """--ai codex should work the same as --integration codex."""
        from typer.testing import CliRunner
        from specify_cli import app

        runner = CliRunner()
        target = tmp_path / "test-proj"
        result = runner.invoke(app, ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"])

        assert result.exit_code == 0, f"init --ai codex failed: {result.output}"
        assert (target / ".codex" / "skills" / "sp-plan" / "SKILL.md").exists()
        assert (target / ".codex" / "skills" / "sp-teams" / "SKILL.md").exists()
        assert (target / ".codex" / "skills" / "spec-kit-workflow-routing" / "SKILL.md").exists()
        assert (target / ".codex" / "skills" / "spec-kit-project-cognition-gate" / "SKILL.md").exists()
        assert not (target / ".codex" / "skills" / "spec-kit-project-map-gate").exists()
        assert (target / ".specify" / "teams" / "runtime.json").exists()
        assert (target / ".specify" / "templates" / "project-handbook-template.md").exists()
        assert (target / ".specify" / "project-cognition").is_dir()
        status = json.loads(
            (target / ".specify" / "project-cognition" / "status.json").read_text(
                encoding="utf-8"
            )
        )
        assert status["baseline_kind"] == "greenfield_empty"
        assert (target / ".specify" / "project-cognition" / "project-cognition.db").exists()
        assert not (target / ".specify" / "templates" / "project-map").exists()
        assert not (target / ".specify" / "project-map").exists()
        cognition_helper = target / ".specify" / "scripts" / "bash" / "project-cognition-freshness.sh"
        assert cognition_helper.exists()
        cognition_helper_text = cognition_helper.read_text(encoding="utf-8")
        assert ".specify/project-map" not in cognition_helper_text
        assert "project-map-freshness" not in cognition_helper_text
        assert "project-cognition" in cognition_helper_text
        assert not (target / ".specify" / "scripts" / "bash" / "project-map-freshness.sh").exists()

        _assert_compact_managed_context((target / "AGENTS.md").read_text(encoding="utf-8"))
        _assert_stable_subagent_contract(
            (target / ".codex" / "skills" / "subagent-driven-development" / "SKILL.md").read_text(
                encoding="utf-8"
            )
        )

    def test_codex_init_generates_sp_ask_read_only_qa_contract(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        runner = CliRunner()
        target = tmp_path / "codex-ask-contract"
        result = runner.invoke(
            app,
            ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
        )

        assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

        skill_path = target / ".codex" / "skills" / "sp-ask" / "SKILL.md"
        template_path = target / ".specify" / "templates" / "commands" / "ask.md"
        partial_path = target / ".specify" / "templates" / "command-partials" / "ask" / "shell.md"
        assert skill_path.exists()
        assert template_path.exists()
        assert partial_path.exists()

        skill_content = skill_path.read_text(encoding="utf-8")
        template_content = template_path.read_text(encoding="utf-8")
        partial_content = partial_path.read_text(encoding="utf-8")
        skill_lower = skill_content.lower()
        partial_lower = partial_content.lower()

        assert "Evidence-Backed Project Q&A" in skill_content
        assert "project cognition provides advisory navigation" in skill_lower
        assert "live evidence is authoritative" in skill_lower
        assert "compass --intent ask" in skill_content
        assert "query --intent ask" in skill_content
        assert "Do not create `.specify/ask/`" in skill_content
        assert "Do not write handoff" in skill_content
        assert "Do not edit source files" in skill_content
        assert "Do not run tests" in skill_content
        assert "Do not run builds" in skill_content
        assert "Do not run package managers" in skill_content
        assert "Do not execute project CLI commands" in skill_content
        assert "discussion-state.md" not in skill_content
        assert "handoff-to-specify" not in skill_content

        assert "# sp-ask" in template_content
        assert "{{spec-kit-include: ../command-partials/ask/shell.md}}" in template_content

        assert "Evidence-Backed Project Q&A" in partial_content
        assert "project-cognition compass --intent ask" in partial_content
        assert "project-cognition query --intent ask" in partial_content
        assert "project cognition as advisory navigation" in partial_lower
        assert "live evidence is authoritative" in partial_lower
        assert "Do not create `.specify/ask/`" in partial_content
        assert "Do not write handoff" in partial_content
        assert "Do not edit source files" in partial_content
        assert "Do not run tests" in partial_content
        assert "Do not run builds" in partial_content
        assert "Do not run package managers" in partial_content
        assert "Do not execute project CLI commands" in partial_content
        assert "discussion-state.md" not in partial_content
        assert "handoff-to-specify" not in partial_content

    def test_codex_init_generates_sp_design_workflow_contract(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        runner = CliRunner()
        target = tmp_path / "codex-design-contract"
        result = runner.invoke(
            app,
            ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
        )

        assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

        skill_path = target / ".codex" / "skills" / "sp-design" / "SKILL.md"
        template_path = target / ".specify" / "templates" / "commands" / "design.md"
        partial_path = target / ".specify" / "templates" / "command-partials" / "design" / "shell.md"
        assert skill_path.exists()
        assert template_path.exists()
        assert partial_path.exists()

        skill_content = skill_path.read_text(encoding="utf-8")
        skill_lower = skill_content.lower()

        assert "DESIGN.md" in skill_content
        assert "design lint" in skill_content
        assert "Forbidden Writes" in skill_content
        assert "CSS or theme implementation files" in skill_content
        assert "active_command: sp-design" in skill_content
        assert "phase_mode: design-only" in skill_content
        assert "source code" in skill_lower

    def test_codex_init_generates_semantic_resume_smoke_contract(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        runner = CliRunner()
        target = tmp_path / "codex-semantic-resume-smoke"
        result = runner.invoke(
            app,
            ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
        )

        assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

        generated_skill = _read_skill_with_references(
            target / ".codex" / "skills" / "sp-debug" / "SKILL.md"
        )
        generated_command_template = (
            target / ".specify" / "templates" / "commands" / "debug.md"
        ).read_text(encoding="utf-8")
        generated_workflow_state = (
            target / ".specify" / "templates" / "workflow-state-template.md"
        ).read_text(encoding="utf-8")
        resume_examples = (
            target / ".specify" / "templates" / "examples" / "semantic-audit-resume" / "scenarios.md"
        )
        resume_validation = (
            target
            / ".specify"
            / "templates"
            / "examples"
            / "semantic-audit-resume"
            / "resume-validation.json"
        )
        route_changed_validation = (
            target
            / ".specify"
            / "templates"
            / "examples"
            / "semantic-audit-resume"
            / "resume-validation-route-changed.json"
        )
        active_claim_validation = (
            target
            / ".specify"
            / "templates"
            / "examples"
            / "semantic-audit-resume"
            / "resume-validation-active-claim-changed.json"
        )
        missing_file_validation = (
            target
            / ".specify"
            / "templates"
            / "examples"
            / "semantic-audit-resume"
            / "resume-validation-missing-file.json"
        )
        claim_ref_validation = (
            target
            / ".specify"
            / "templates"
            / "examples"
            / "semantic-audit-resume"
            / "resume-validation-claim-ref-mismatch.json"
        )
        verification_ref_validation = (
            target
            / ".specify"
            / "templates"
            / "examples"
            / "semantic-audit-resume"
            / "resume-validation-verification-ref-mismatch.json"
        )
        audit_input = (
            target
            / ".specify"
            / "templates"
            / "examples"
            / "semantic-audit-resume"
            / "semantic-audit-input.json"
        )
        audit_output = (
            target
            / ".specify"
            / "templates"
            / "examples"
            / "semantic-audit-resume"
            / "semantic-audit-output.json"
        )
        generated_contract = "\n".join([generated_skill, generated_command_template])
        generated_contract_lower = generated_contract.lower()

        assert "generated resume smoke" in generated_contract
        assert "semantic-audit-input.json.semantic_audit_input.route_decision" in generated_contract
        assert (
            "semantic-audit-output.json.workflow_authorization and "
            "semantic-audit-output.json.claim_readiness"
        ) in generated_contract
        assert "Stale-state detection remains prompt-only in v1.3.6" in generated_contract
        assert "semantic-audit-resume" in generated_contract
        assert "optional runtime validator" in generated_contract
        assert "resume-validation.json" in generated_contract
        assert "resume-validation-route-changed.json" in generated_contract
        assert "resume-validation-active-claim-changed.json" in generated_contract
        assert "resume-validation-missing-file.json" in generated_contract
        assert "resume-validation-claim-ref-mismatch.json" in generated_contract
        assert "resume-validation-verification-ref-mismatch.json" in generated_contract
        assert "prefer the optional runtime validator" in generated_contract_lower
        assert "ephemeral resume-validation.json" in generated_contract_lower
        assert "if the validator returns fresh" in generated_contract_lower
        assert "if the validator is unavailable" in generated_contract_lower
        assert "real downstream resume smoke" in generated_contract_lower
        assert "workflow-local semantic-audit-input.json" in generated_contract_lower
        assert "workflow-local semantic-audit-output.json" in generated_contract_lower
        assert "Prompt fallback remains valid" in generated_contract
        assert "does not authorize source edits, final claims, or P3/P4 permission" in generated_contract
        assert "Graph claim namespace" in generated_contract
        assert "graph_claim_type" in generated_contract
        assert "verified_in_graph_generation" in generated_contract
        assert "cannot set workflow `claim_ready=true`" in generated_contract
        assert "must not populate `claim_verification_refs`" in generated_contract
        assert "Fingerprint mismatches are route-changed" in generated_contract
        assert ".specify/templates/examples/semantic-audit-resume/scenarios.md" in generated_contract
        assert "keep claim_ready false" in generated_contract

        assert "semantic_audit_generated_resume_smoke:" in generated_workflow_state
        assert "semantic_audit_stale_reasons:" in generated_workflow_state
        assert "active-claim-changed" in generated_workflow_state

        assert resume_examples.exists()
        resume_examples_text = resume_examples.read_text(encoding="utf-8")
        assert "Semantic Audit Resume Examples" in resume_examples_text
        assert "verification-ref-mismatch" in resume_examples_text
        assert "resume-validation.json" in resume_examples_text

        assert resume_validation.exists()
        assert route_changed_validation.exists()
        assert active_claim_validation.exists()
        assert missing_file_validation.exists()
        assert claim_ref_validation.exists()
        assert verification_ref_validation.exists()
        assert audit_input.exists()
        assert audit_output.exists()
        resume_validation_payload = json.loads(resume_validation.read_text(encoding="utf-8"))
        resume_validation_state = resume_validation_payload["workflow_state"]
        assert resume_validation_state["semantic_audit_input_path"] == "semantic-audit-input.json"
        assert resume_validation_state["semantic_audit_output_path"] == "semantic-audit-output.json"
        assert resume_validation_state["selected_candidate_ids"] == ["environment-settings-page"]
        assert resume_validation_state["claim_authorization_refs"] == [
            "workflow:debug#root-cause-reviewed"
        ]

    def test_codex_downstream_state_runs_semantic_resume_validator(self, tmp_path):
        if shutil.which("go") is None:
            pytest.skip("Go toolchain unavailable")

        from typer.testing import CliRunner
        from specify_cli import app

        runner = CliRunner()
        target = tmp_path / "codex-semantic-resume-runtime-smoke"
        result = runner.invoke(
            app,
            ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
        )

        assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

        examples_dir = target / ".specify" / "templates" / "examples" / "semantic-audit-resume"
        workflow_state_dir = target / ".planning" / "debug" / "h5-env"
        workflow_state_dir.mkdir(parents=True)
        (workflow_state_dir / "semantic-audit-input.json").write_text(
            (examples_dir / "semantic-audit-input.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )
        (workflow_state_dir / "semantic-audit-output.json").write_text(
            (examples_dir / "semantic-audit-output.json").read_text(encoding="utf-8"),
            encoding="utf-8",
        )

        fresh_resume = workflow_state_dir / "resume-validation.json"
        fresh_resume.write_text(
            json.dumps(
                {
                    "version": 1,
                    "workflow_state": {
                        "semantic_audit_input_path": "semantic-audit-input.json",
                        "semantic_audit_output_path": "semantic-audit-output.json",
                        "semantic_audit_route_fingerprint": "semantic-audit-route:v1:bab591a662cd55d2",
                        "active_claim_type": "root_cause_claim",
                        "selected_candidate_ids": ["environment-settings-page"],
                        "claim_readiness_status": "claim_ready",
                        "claim_authorization_refs": ["workflow:debug#root-cause-reviewed"],
                        "claim_verification_refs": ["test:EnvironmentSettings.test.tsx#passed"],
                    },
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        fresh_payload = _run_semantic_audit_resume_fixture(fresh_resume)
        assert fresh_payload["validator"] == "semantic-audit-resume"
        assert fresh_payload["semantic_audit_generated_resume_smoke"] == "passed"
        assert fresh_payload["semantic_audit_resume_status"] == "fresh"
        assert fresh_payload["semantic_audit_stale_reasons"] == ["none"]
        assert fresh_payload["can_reuse_persisted_claim_readiness"] is True
        assert fresh_payload["grants_permission"] is False
        assert (
            fresh_payload["boundary"]
            == "comparison_only_no_source_edit_or_claim_authorization"
        )

        stale_resume = workflow_state_dir / "resume-validation-route-changed.json"
        stale_resume.write_text(
            json.dumps(
                {
                    "version": 1,
                    "workflow_state": {
                        "semantic_audit_input_path": "semantic-audit-input.json",
                        "semantic_audit_output_path": "semantic-audit-output.json",
                        "semantic_audit_route_fingerprint": "semantic-audit-route:v1:2ed3dba77fe9af12",
                        "active_claim_type": "root_cause_claim",
                        "selected_candidate_ids": ["env-config"],
                        "claim_readiness_status": "claim_ready",
                        "claim_authorization_refs": ["workflow:debug#root-cause-reviewed"],
                        "claim_verification_refs": ["test:EnvironmentSettings.test.tsx#passed"],
                    },
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        stale_payload = _run_semantic_audit_resume_fixture(stale_resume)
        assert stale_payload["validator"] == "semantic-audit-resume"
        assert stale_payload["semantic_audit_generated_resume_smoke"] == "failed"
        assert stale_payload["semantic_audit_resume_status"] == "needs-rerun"
        assert "route-changed" in stale_payload["semantic_audit_stale_reasons"]
        assert stale_payload["can_reuse_persisted_claim_readiness"] is False
        assert stale_payload["grants_permission"] is False

    def test_codex_init_installs_lightweight_discussion_recovery_contract(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        runner = CliRunner()
        target = tmp_path / "codex-discussion-recovery"
        result = runner.invoke(
            app,
            ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
        )

        assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

        skill_content = _read_skill_with_references(
            target / ".codex" / "skills" / "sp-discussion" / "SKILL.md"
        )
        command_template = (target / ".specify" / "templates" / "commands" / "discussion.md").read_text(
            encoding="utf-8"
        )
        state_template = (target / ".specify" / "templates" / "discussion-state-template.md").read_text(
            encoding="utf-8"
        )
        handoff_template = json.loads(
            (target / ".specify" / "templates" / "brainstorming-handoff-specify-template.json").read_text(
                encoding="utf-8"
            )
        )
        generated_discussion = "\n".join([skill_content, command_template]).replace(
            "project-cognition.exe", "project-cognition"
        )
        generated_lower = generated_discussion.lower()

        assert "Turn Classifier" in generated_discussion
        assert "Question Evidence Gate" in generated_discussion
        assert "Cognition Advisory, Code Authority" in generated_discussion
        assert "project-cognition compass --intent discussion" in generated_discussion
        assert "project-cognition query --query-plan" in generated_discussion
        assert "only when `compass_state`, coverage diagnostics, localization, or live evidence requires explicit concept decisions" in generated_discussion
        assert "project-cognition query --intent plan" not in generated_discussion
        assert "ui-interaction-discussion" in generated_discussion
        assert "senior ui and interaction designer" in generated_lower
        assert "ascii sketches" in generated_lower
        assert "ui_sketches_present" in generated_discussion
        assert "ordinary turns do not write local files by default" in generated_lower
        assert "deferred persistence" in generated_lower
        assert "compaction preserve" in generated_lower
        assert "user-triggered save" in generated_lower
        assert "turn count alone is never a save trigger" in generated_lower
        assert "semantic checkpoints" in generated_lower
        assert "adaptive question pack" in generated_lower
        assert "primary question" in generated_lower
        assert "optional follow-up" in generated_lower
        assert "recommended option" in generated_lower
        assert "high-throughput collaborative brief" in generated_lower
        assert "frontstage / backstage separation" in generated_lower
        assert "visible conversation" in generated_lower
        assert "state accounting backstage" in generated_lower
        assert "continue by default" in generated_lower
        assert "do not ask for continuation" in generated_lower
        assert "do not persist every turn" in generated_lower
        assert "checkpoint persistence" in generated_lower
        assert "surface file paths and state updates only" in generated_lower
        assert "adaptive reply contract" in generated_lower
        assert "reply_shape_id" not in generated_discussion
        assert "unified frontstage contract" in generated_lower
        assert "do not choose among named answer templates" in generated_lower
        assert "agent controls heading names" in generated_lower
        assert "`explore -> ground -> decide -> prepare -> review -> ready -> consumed | closed`" in generated_discussion
        assert "discussion responsibility boundary" in generated_lower
        assert "does not own implementation planning" in generated_lower
        assert "do not split the work into p0/p1/p2" in generated_lower
        assert "migration phases" in generated_lower
        assert "task packets" in generated_lower
        assert "no parallel old-backend operation" in generated_lower
        assert "no old-stack cutover fallback" in generated_lower
        assert "no alternate product path" in generated_lower
        assert "database snapshots" in generated_lower
        assert "data-safety mechanisms" in generated_lower
        assert "downstream planning and implementation safety constraints" in generated_lower
        assert "handoff request-changes repair" in generated_lower
        assert "blocked_by_handoff_integrity" in generated_discussion
        assert "the repair belongs to `sp-discussion`" in generated_lower
        assert "update canonical `handoff-to-specify.json`" in generated_lower
        assert "source_contract" in generated_discussion
        assert "field-level validation errors" in generated_discussion
        assert "review_digest" in generated_discussion
        assert "safe default discussion action" in generated_lower
        assert "next-step content rule" in generated_lower
        assert "first-pass content" in generated_lower
        assert "pre-handoff readiness" in generated_lower
        assert "proposed handoff goal" in generated_lower
        assert "without writing or claiming `handoff-assessment.md`" in generated_lower
        assert "decision requested" in generated_lower
        assert "scope to approve" in generated_lower
        assert "allowed approval" in generated_lower
        assert "recommendation-first is not questionless" in generated_lower
        assert "discussion_decision_digest" in generated_discussion
        assert "discussion_requirement_contract" in generated_discussion
        assert "Agent-Facing Requirement Contract" in generated_discussion
        assert "consumer_eligibility" in generated_discussion
        assert "recommended_consumer" in generated_discussion
        assert "planning_constraints" in generated_discussion
        assert "quick_task_candidate" not in generated_discussion
        assert "do not describe current execution or implementation progress" in generated_lower
        assert "locked_direction" in generated_discussion
        assert "rejected_alternatives" in generated_discussion
        assert "accepted_tradeoffs" in generated_discussion
        assert "experience_commitments" in generated_discussion
        assert "review_criteria_carried_forward" in generated_discussion
        assert "must_not_dilute" in generated_discussion
        assert "handoff-ready closeout" in generated_lower
        assert "selected direction" in generated_lower
        assert "target boundary" in generated_lower
        assert "Must-Preserve coverage" in generated_discussion
        assert "package paths" in generated_lower
        assert "next consumption path" in generated_lower
        assert "do not close with only file paths, status counters, or a next command" in generated_lower
        assert "keep ready-summary quality checks internal" in generated_lower
        assert "`ready-for-handoff` or `continue-discussion`" in generated_lower
        assert "canonical json payload" in generated_lower
        assert "confirmed unified handoff pair" not in generated_lower

        assert "latest_event_checkpoint:" in state_template
        assert "ordinary_turn_write_policy: deferred-checkpoint" in state_template
        assert "save_trigger_policy:" in state_template
        assert "checkpoint_value_policy:" in state_template
        assert "pending_context_summary:" in state_template
        assert "compaction_preserve_items:" in state_template
        assert "latest_cognition_readiness:" in state_template
        assert (
            "ui_discussion_status: not_applicable | offered | accepted | skipped | completed | deferred"
            in state_template
        )
        assert "question_pack_mode: single-question | adaptive-pack | none" in state_template
        assert "reply_shape_id:" not in state_template
        assert "frontstage_reply_contract: unified" in state_template
        assert "lifecycle_phase: explore | ground | decide | prepare | review | ready | consumed | closed" in state_template
        assert "primary_question:" in state_template
        assert "optional_followups:" in state_template
        assert "recommendation_required_for_choices: true" in state_template
        assert "handoff-to-specify.json draft after explicit user request and boundary lock" in state_template
        assert "handoff_kind: discussion_requirement_contract" in state_template
        assert "consumer_eligibility:" in state_template
        assert "recommended_consumer:" in state_template
        assert "quick_task_candidate_status:" not in state_template

        assert handoff_template == {
            "version": 3,
            "status": "pending",
            "entry_source": None,
            "discussion_slug": None,
            "source_contract": None,
            "review_digest": None,
            "semantic_delta": [],
            "required_refs": [],
            "blockers": [],
            "next_action": None,
            "recovery": None,
        }
        assert "source_evidence_contract" not in handoff_template


def test_codex_team_template_comes_from_shared_commands_dir(monkeypatch, tmp_path):
    """Codex must discover team.md from the packaged shared commands directory."""
    from specify_cli.integrations.codex import CodexIntegration
    from specify_cli.integrations.base import IntegrationBase

    commands_dir = tmp_path / "commands"
    commands_dir.mkdir()
    (commands_dir / "plan.md").write_text("---\ndescription: plan\n---\nbody\n", encoding="utf-8")
    (commands_dir / "team.md").write_text("---\ndescription: team\n---\nbody\n", encoding="utf-8")

    monkeypatch.setattr(IntegrationBase, "shared_commands_dir", lambda self: commands_dir)

    templates = CodexIntegration().list_command_templates()

    assert commands_dir / "plan.md" in templates
    assert commands_dir / "team.md" in templates


def test_codex_generated_sp_implement_teams_skill_exists_and_is_codex_only(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-implement-teams"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

    skill_path = target / ".codex" / "skills" / "sp-implement-teams" / "SKILL.md"
    assert skill_path.exists()

    content = _read_skill_with_references(skill_path)
    lower = content.lower()
    assert "codex-only" in lower
    assert "psmux" in lower
    assert "native windows" in lower
    assert "sp-teams" in lower
    assert "sp.agent-teams.run" not in lower
    assert "primary product surface" in lower or "primary surface" in lower
    assert "specify extension add agent-teams" not in lower
    assert "shared contract with `sp-implement`" in lower
    assert "canonical implementation workflow" in lower
    assert "task-index.json" in lower
    assert "lifecycle record" in lower
    assert "implement-tracker.md" in lower
    assert "compatibility state only" in lower
    assert "workertaskpacket" in lower
    assert "sp-teams doctor" in lower
    assert "sp-teams live-probe" in lower
    assert "execution_model" in lower
    assert "dispatch_shape" in lower
    assert "execution_surface" in lower
    assert "join point" in lower
    assert "subagent result contract" in lower
    assert "result file handoff path" in lower
    assert ".specify/teams/state/results/<request-id>.json" in lower
    assert "core implementation complete" in lower
    assert "ready for integration testing" in lower
    assert "overall feature completion" in lower
    assert "e2e" in lower
    assert "polish" in lower
    assert "explicit execution packet shape" in lower or "explicit execution packet" in lower
    assert "compass --intent implement" in lower
    assert "minimal_live_reads" in lower
    assert "first_pass_paths" in lower
    assert "coverage_diagnostics" in lower
    assert "expansion_ref" in lower
    assert "lexicon -> semantic_intake -> query" in lower
    assert "project-cognition lexicon --intent implement" not in lower
    assert "write set and shared surfaces" in lower
    assert "explicit verification command or acceptance check" in lower
    assert "completion-handoff protocol" in lower
    assert "platform guardrails" in lower
    assert "status flip alone" in lower
    assert "validation target" in lower
    assert "stale lane" in lower
    assert "if the current feature already has an active runtime session, resume or reuse it" in lower
    assert "do not create a second runtime team for the same feature" in lower
    assert "after each completed join point or ready batch, re-read the tracker and task state" in lower
    assert "select the next ready batch and continue automatically" in lower
    assert "stop only when no ready work remains, a real blocker stops progress, or an explicit human gate is reached" in lower
    assert "planned validation tasks are still ready work" in lower
    assert "do not stop to ask whether validation should start" in lower
    assert "check-prerequisites.sh --json --require-tasks --include-tasks" in lower
    assert "parse `feature_dir` and `available_docs` list" in lower
    assert "all paths must be absolute" in lower
    _assert_canonical_cognition_intake_contract(content)


def test_codex_generated_passive_subagent_skills_include_stable_dispatch_contract(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-passive-dispatch"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

    skills_dir = target / ".codex" / "skills"
    routing = (skills_dir / "spec-kit-workflow-routing" / "SKILL.md").read_text(encoding="utf-8").lower()
    subagent = (skills_dir / "subagent-driven-development" / "SKILL.md").read_text(encoding="utf-8").lower()
    parallel = (skills_dir / "dispatching-parallel-agents" / "SKILL.md").read_text(encoding="utf-8").lower()

    assert "do not auto-enter an `sp-*` workflow unless the user invokes it" in routing
    assert "you may recommend a" in routing
    assert "natural-language tasks" in routing
    assert "always-on" in routing
    assert "project cognition and project learning" in routing
    assert "red flags" in routing
    assert "high-throughput senior product-engineering advisor" in routing
    assert "frontstage / backstage separation" in routing
    assert "does not persist every turn" in routing
    assert "continues by default" in routing
    assert "does not ask for continuation" in routing

    assert "native subagents" in subagent
    assert "validated `workertaskpacket`" in subagent
    assert "must not dispatch from raw task text" in subagent
    assert "review on triggers" in subagent
    assert "single task reviewer" in subagent
    assert "task lifecycle record" in subagent
    assert "`sp-teams` only" in subagent

    assert "2+ independent lanes" in parallel
    assert "current runtime" in parallel
    assert "native subagents" in parallel
    assert "write-set" in parallel
    assert "structured handoff" in parallel
    assert "separate terminal" in parallel
    assert "advise the user to run multiple parallel instances" not in parallel


def test_codex_generated_skills_render_launcher_backed_runtime_commands(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-launcher-render"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

    constitution_content = (target / ".codex" / "skills" / "sp-constitution" / "SKILL.md").read_text(encoding="utf-8")
    constitution_normalized = " ".join(constitution_content.split())
    implement_content = _read_skill_with_references(
        target / ".codex" / "skills" / "sp-implement" / "SKILL.md"
    )
    quick_content = _read_skill_with_references(
        target / ".codex" / "skills" / "sp-quick" / "SKILL.md"
    )

    assert "learning start --command constitution --format json" in constitution_content
    assert "This workflow writes only `.specify/memory/constitution.md`." in constitution_content
    assert "Do not modify templates, command files, docs, project rules, learning files" in constitution_content
    assert "report the highest affected downstream stage instead of editing those artifacts" in constitution_normalized
    assert "record them as pending follow-up items in the Sync Impact Report instead of applying them" in constitution_normalized
    for forbidden in (
        "the constitution must stay synchronized with dependent templates",
        "propagate any downstream template",
        "keep dependent templates, guidance, and lower-order project memory aligned",
        "reopen the highest affected downstream stage",
        "without updating them or flagging them",
    ):
        assert forbidden not in constitution_content.lower()
    assert "{{specify-subcmd:" not in constitution_content

    for content in (implement_content, quick_content):
        assert "WorkerTaskPacket" in content
        assert "structured handoff" in content.lower()
        assert "{{specify-subcmd:hook" not in content

    assert "{{specify-subcmd:" not in implement_content
    assert "{{specify-subcmd:" not in quick_content

    routine_hook_guidance = (
        "hook validate-state --command implement",
        "hook validate-session-state --command implement",
        "hook validate-packet --packet-file",
        "hook validate-state --command quick",
        "hook validate-session-state --command quick",
        "hook monitor-context --command quick",
        "hook checkpoint --command quick",
    )
    for fragment in routine_hook_guidance:
        assert fragment not in implement_content
        assert fragment not in quick_content


def test_codex_implement_teams_template_keeps_only_backend_specific_guidance():
    template = Path("templates/commands/implement-teams.md").read_text(encoding="utf-8")

    assert "## Shared Contract With `sp-implement`" not in template
    assert "scripts:" in template
    assert "--require-tasks --include-tasks" in template
    assert "Run `{SCRIPT}` from repo root and parse `FEATURE_DIR` and `AVAILABLE_DOCS` list." in template
    assert "sp-teams doctor" in template
    assert "sp-teams live-probe" in template
    assert "validation target" in template.lower()
    assert "stale lane" in template.lower()


def test_codex_generated_sp_implement_includes_native_spawn_agent_routing(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-auto-parallel"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

    skill_path = target / ".codex" / "skills" / "sp-implement" / "SKILL.md"
    raw_content = skill_path.read_text(encoding="utf-8")
    content = _read_skill_with_references(skill_path)
    leader_gate_idx = raw_content.find("## Codex Leader Gate")
    main_flow_idx = raw_content.find("## Main Flow")
    auto_parallel_idx = raw_content.find("## Codex Subagents-First Execution")

    assert leader_gate_idx != -1 or "## Orchestration Model" in raw_content
    assert main_flow_idx != -1
    assert auto_parallel_idx == -1 or leader_gate_idx < auto_parallel_idx
    assert "task-index.json" in content.lower()
    assert "compact execution state" in content.lower()
    assert "compass --intent implement" in content.lower()
    assert "current-task navigation repair" in content.lower()
    assert "only when a required ref is stale, missing, or contradicted by live code" in content.lower()
    assert "query --intent implement" not in content.lower()
    assert "minimal_live_reads" in content.lower()
    assert "build-handbook.md" not in content.lower()
    assert "build-workflow-contract" not in content.lower()
    assert "product-and-capability-map" not in content.lower()
    assert "change-entrypoints" not in content.lower()
    assert "first-class implementation context" in content.lower()
    assert "task-graph revision" in content.lower()
    assert "workflow leader" in content.lower()
    assert "spawn_agent" in content
    assert "wait_agent" in content
    assert "close_agent" in content
    assert "result path" in content
    assert "--command implement" in content
    assert "--request-id" in content
    assert "active runtime-managed result channel for that request id" in content.lower()
    assert "json-only command" in content.lower()
    assert "do not append `--format`" in content.lower()
    assert "execution_model: adaptive" in content or "execution model: `adaptive`" in content
    assert "one-subagent" in content and "parallel-subagents" in content
    assert "native-subagents" in content
    assert "leader-direct" in content
    assert "one-subagent" in content
    assert "parallel-subagents" in content
    assert "current ready batch" in content.lower()
    assert "just in time" in content.lower()
    assert "map-update" in content.lower()
    assert "workflow-owned mutation closeout is not an external map-maintenance handoff" in content.lower()
    assert "update --delta-session" in content.lower()
    assert "sp-map-update is for manual/external maintenance and follow-up repair" in content.lower()
    assert "do not claim completion from chat narration" in content.lower()
    assert "validation evidence" in content.lower()
    assert "mutation closeout" in content.lower()
    assert "join point" in content.lower()
    assert "event-triggered review" in content.lower()
    assert "task lifecycle record" in content.lower()
    assert "do not create separate task briefs, review packages, or a duplicate task ledger" in content.lower()
    assert "blocker" in content.lower()
    assert "recovery" in content.lower()
    assert "stop/reopen" in content.lower() or "stop-and-reopen" in content.lower()
    assert "subagent execution" in content.lower()
    assert "prefer `execution_surface: native-subagents`" in content or "spawn_agent" in content
    assert "sp-teams" not in content.lower()
    assert "must not edit a delegated lane's write scope while that subagent is active" in content.lower()
    assert "wait for every subagent's structured handoff" in content.lower()
    assert "do not treat an idle subagent as done work" in content.lower()
    assert "do not dispatch a subagent when required packet fields or required references are missing" in content.lower()
    assert "use leader-direct only if the task independently qualifies" in content.lower()
    assert "Dispatch Fallback" not in content
    assert "max_parallel_subagents = 4" in content
    assert "at most four validated isolated lanes" in content
    assert "launch the selected parallel wave before waiting" in content.lower()


def test_codex_generated_shared_workflow_skills_include_native_spawn_agent_guidance(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-shared-routing"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

    skills_dir = target / ".codex" / "skills"
    for skill_name in ("sp-specify",):
        skill_content = _read_skill_with_references(skills_dir / skill_name / "SKILL.md")
        content = skill_content.lower()
        assert (
            "execution_model: subagent-mandatory" in content
            or "execution model: `subagents-first`" in content
            or "lane_mode: read-only-evidence" in content
        )
        assert "choose_evidence_lane_dispatch" in content
        assert "choose_ui_reference_lane_dispatch" in content
        assert "ui-reference-artifact" in content
        assert "ui-reference-notes.md" in content
        assert "ui-brief.md" in content
        assert "Reference-Implementation" in skill_content
        assert "dispatch_shape: one-subagent | parallel-subagents" in content
        assert "execution_surface: native-subagents" in content
        assert "spawn_agent" in content
        assert "wait_agent" in content
        assert ".specify/project-cognition/" in content
        assert "learning start --command " in content
        assert "--format json" in content
        assert "--detail-level" not in content
        assert "show_argv" in content
        assert ".specify/memory/learnings/index.md" not in content
        assert "spec-contract.json" in content
        assert "semantic_delta" in content
        assert ".planning/learnings/candidates.md" not in content or "compatibility" in content
        assert "if collaboration is justified" not in content
        assert "would benefit from them" not in content
        assert "make the next path explicit" not in content
    for skill_name in ("sp-plan", "sp-tasks"):
        content = _read_skill_with_references(
            skills_dir / skill_name / "SKILL.md"
        ).lower()
        assert "execution_model: adaptive" in content
        assert "execution_mode: light | standard | heavy" in content
        assert "workflow_status: ready | blocked" in content
        assert "execution_surface: leader-inline | native-subagents | none" in content
        assert "codex adaptive dispatch" in content
        assert "apply the adaptive dispatch decision recorded by `choose_subagent_dispatch`" in content
        assert "capability_degraded: true" in content
        assert "dispatch_shape: subagent-blocked" in content
        assert "execution_surface: none" in content
        assert "subagents-first dispatch model" not in content
        assert "leader-inline-fallback" not in content
        assert "execution model: `subagents-first`" not in content
        assert ".specify/project-cognition/" in content
        assert "learning start --command " in content
        assert "--format json" in content
        assert "--detail-level" not in content
        assert "show_argv" in content
        assert ".specify/memory/learnings/index.md" not in content
        assert ".planning/learnings/candidates.md" not in content
        assert "if collaboration is justified" not in content
        assert "would benefit from them" not in content
        assert "make the next path explicit" not in content

    implement_content = _read_skill_with_references(
        skills_dir / "sp-implement" / "SKILL.md"
    ).lower()
    assert "execution_model: adaptive" in implement_content or "execution model: `adaptive`" in implement_content
    assert "leader-direct" in implement_content
    assert "one-subagent" in implement_content and "parallel-subagents" in implement_content
    assert "native-subagents" in implement_content
    assert "spawn_agent" in implement_content
    assert "wait_agent" in implement_content
    assert "close_agent" in implement_content
    assert "task-index.json" in implement_content
    assert "just in time" in implement_content
    assert "event-triggered review" in implement_content
    assert "task lifecycle record" in implement_content
    assert "sp-teams" not in implement_content

    shared_skills = ("sp-specify", "sp-plan", "sp-tasks")
    for skill_name in shared_skills:
        content = _read_skill_with_references(
            skills_dir / skill_name / "SKILL.md"
        ).lower()
        assert "specify team" not in content
        assert "workflow-state.md" in content
        assert "resume state" in content
        assert "canonical" in content
        assert "-contract.json" in content

    assert not (skills_dir / "sp-test-scan" / "SKILL.md").exists()
    assert not (skills_dir / "sp-test-build" / "SKILL.md").exists()

    prd_content = (skills_dir / "sp-prd" / "SKILL.md").read_text(encoding="utf-8").lower()
    assert "deprecated compatibility entrypoint" in prd_content
    assert "sp-prd-scan -> sp-prd-build" in prd_content
    assert "do not describe `sp-prd` as the preferred workflow" in prd_content

    prd_scan_content = (skills_dir / "sp-prd-scan" / "SKILL.md").read_text(encoding="utf-8").lower()
    assert "current repository reality" in prd_scan_content
    assert ".specify/prd-runs/<run-id>/" in prd_scan_content
    assert "capability triage" in prd_scan_content
    assert "critical depth gate" in prd_scan_content
    assert "reconstruction-grade scan package" in prd_scan_content
    assert "evidence label gate" in prd_scan_content

    prd_build_content = (skills_dir / "sp-prd-build" / "SKILL.md").read_text(encoding="utf-8").lower()
    assert "reverse coverage validation" in prd_build_content
    assert "no new facts gate" in prd_build_content

    constitution_content = (skills_dir / "sp-constitution" / "SKILL.md").read_text(encoding="utf-8").lower()
    constitution_normalized = " ".join(constitution_content.split())
    assert "learning start --command constitution --format json" in constitution_content
    assert "show_argv" in constitution_content
    assert ".specify/memory/learnings/index.md" not in constitution_content
    assert ".planning/learnings/candidates.md" not in constitution_content
    assert "this workflow writes only `.specify/memory/constitution.md`." in constitution_content
    assert "do not modify templates, command files, docs, project rules, learning files" in constitution_content
    assert "report the highest affected downstream stage instead of editing those artifacts" in constitution_normalized
    assert "record them as pending follow-up items in the sync impact report instead of applying them" in constitution_normalized
    for forbidden in (
        "the constitution must stay synchronized with dependent templates",
        "propagate any downstream template",
        "keep dependent templates, guidance, and lower-order project memory aligned",
        "reopen the highest affected downstream stage",
        "without updating them or flagging them",
    ):
        assert forbidden not in constitution_content
    assert ".specify/project-cognition/status.json" in constitution_content
    assert "build-handbook.md" not in constitution_content
    assert ".specify/project-map/index/status.json" not in constitution_content
    assert "/sp-map-scan" in constitution_content
    assert "/sp-map-build" in constitution_content
    assert "workflow-state.md" in constitution_content
    assert "/sp-plan" in constitution_content
    assert "/sp-tasks" in constitution_content
    assert "/sp-analyze" in constitution_content


def test_codex_question_driven_skills_prefer_request_user_input_with_fallback(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-question-tool"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

    for skill_name in ("sp-specify", "sp-clarify", "sp-checklist", "sp-quick"):
        content = (target / ".codex" / "skills" / skill_name / "SKILL.md").read_text(encoding="utf-8")
        lower = content.lower()
        assert "request_user_input" in content
        assert "if the current codex runtime exposes it" in lower
        assert "must use it" in lower
        assert "auto_default_recommendation" in content
        assert "must auto-resolve" in lower
        assert "do not invoke the native structured question tool" in lower
        assert "do not render the textual fallback block" in lower
        assert "do not self-authorize textual fallback" in lower
        assert "keep native-tool availability, runtime mode, and fallback mechanics backstage" in lower
        assert "do not tell the user that a structured question tool is unavailable" in lower
        assert "ask the user-facing question directly" in lower
        assert "recommended option first" in lower
        assert "fall back immediately" in lower or "fall back to the" in lower

    quick_content = _read_skill_with_references(
        target / ".codex" / "skills" / "sp-quick" / "SKILL.md"
    ).lower()
    assert "--discuss" in quick_content
    assert "multiple unfinished quick tasks exist" in quick_content
    assert "resolve discussion handoff intake before quick-task execution" in quick_content
    assert "discussion_requirement_contract" in quick_content
    assert "consumer_eligibility.sp-quick.status" in quick_content
    assert "planning constraints" in quick_content
    assert "review_digest" in quick_content
    assert "quick_task_candidate" not in quick_content
    assert "do not repeat user confirmation" in quick_content
    assert_quick_checkpoint_card_shape(quick_content)


def test_codex_generated_skills_preserve_agent_required_marker_lines(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-agent-marker"
    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, result.output

    for skill_name in ("sp-quick", "sp-map-scan", "sp-map-build", "sp-implement", "sp-specify", "sp-prd", "sp-plan", "sp-tasks", "sp-debug"):
        content = (target / ".codex" / "skills" / skill_name / "SKILL.md").read_text(encoding="utf-8")
        assert "[agent]" in content.lower()

    fast_content = (target / ".codex" / "skills" / "sp-fast" / "SKILL.md").read_text(encoding="utf-8").lower()
    assert "[agent]" in fast_content
    assert "leader-direct" in fast_content


def test_codex_generated_plan_tasks_implement_skills_preserve_boundary_guardrails(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-boundary-guardrails"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

    skills_dir = target / ".codex" / "skills"

    plan_content = _read_skill_with_references(skills_dir / "sp-plan" / "SKILL.md")
    assert "spec-contract.json" in plan_content
    assert "plan-contract.json" in plan_content
    assert "Add `Implementation Constitution`" in plan_content
    assert "architecture/module decisions and interface consumes/produces map" in plan_content
    assert "implementation target and boundary refs" in plan_content
    assert "scope preservation, interface completeness, target boundary" in plan_content
    assert "Dispatch Compilation Hints" in plan_content
    assert "planning/lane-manifest.json" in plan_content
    assert "separate evidence-index and checkpoint logs" in plan_content
    assert "Do not synthesize `plan.md`, `research.md`, or `plan-contract.json` from chat-only delegated lane results" in plan_content
    assert "artifact-writing delegated lanes must use writable" in plan_content.lower()
    assert "execution-capable native subagents" in plan_content.lower()
    assert "read-only explorer, reviewer, or diagnostic lane" in plan_content.lower()
    assert "heuristics" not in plan_content.lower()

    clarify_content = (skills_dir / "sp-clarify" / "SKILL.md").read_text(encoding="utf-8")
    assert "clarification/handoffs/<lane-id>.json" in clarify_content
    assert "clarification/evidence-index.json" in clarify_content
    assert "clarification/checkpoints.ndjson" in clarify_content
    assert "consume `clarification/evidence-index.json` before final artifact updates" in clarify_content.lower()
    assert "do not update `spec.md`, `alignment.md`, `context.md`, or `references.md` from chat-only lane results" in clarify_content.lower()

    tasks_content = _read_skill_with_references(skills_dir / "sp-tasks" / "SKILL.md")
    assert "plan-contract.json" in tasks_content
    assert "task-index.json" in tasks_content
    assert "MP-*" in tasks_content
    assert "CA-###" in tasks_content
    assert "capability operation" in tasks_content.lower()
    assert "real-entrypoint" in tasks_content.lower()
    assert "join point" in tasks_content.lower()
    assert "compile delegated packets just in time" in tasks_content.lower()
    assert "task-generation/lane-manifest.json" in tasks_content
    assert "chat-only lane output is not handoff truth" in tasks_content.lower()
    assert "artifact-writing delegated lanes must use writable" in tasks_content.lower()
    assert "execution-capable native subagents" in tasks_content.lower()
    assert "read-only explorer, reviewer, or diagnostic lane" in tasks_content.lower()

    implement_content = _read_skill_with_references(
        skills_dir / "sp-implement" / "SKILL.md"
    )
    assert "task-index.json" in implement_content
    assert "forbidden drift" in implement_content.lower()
    assert "event-triggered review" in implement_content.lower()
    assert "task lifecycle record" in implement_content.lower()
    assert "validated `WorkerTaskPacket`" in implement_content
    assert "dispatch only from validated `workertaskpacket`" in implement_content.lower() or "raw task text alone" in implement_content.lower()

    analyze_content = (skills_dir / "sp-analyze" / "SKILL.md").read_text(encoding="utf-8")
    assert "Boundary Guardrail Gaps" in analyze_content
    assert "BG1" in analyze_content
    assert "BG2" in analyze_content
    assert "BG3" in analyze_content
    assert "DP1" in analyze_content
    assert "DP2" in analyze_content
    assert "DP3" in analyze_content
    assert "Boundary Guardrail Table" in analyze_content
    assert "Closed-loop requirement" in analyze_content
    assert "Recommended Re-entry" in analyze_content
    assert "Blocker Bundle" in analyze_content
    assert "fingerprint-first" in analyze_content.lower()
    assert "missed_by_previous_analyze" in analyze_content
    assert "No more than one task-layer remediation cycle is expected" in analyze_content
    assert "This command does not edit `spec.md`, `context.md`, `plan.md`, or `tasks.md`." in analyze_content
    assert "workflow-state.md" in analyze_content
    assert "analysis-only" in analyze_content.lower()
    assert "`next_command: /sp.implement`" in analyze_content
    assert "If the highest invalid stage is `clarify`" in analyze_content
    assert "planning/lane-manifest.json" in analyze_content
    assert "task-generation/lane-manifest.json" in analyze_content
    assert "accepted planning handoff with no downstream consumer" in analyze_content.lower()
    assert "accepted task-generation handoff with no downstream consumer" in analyze_content.lower()
    assert "non-destructive cross-artifact consistency and boundary-guardrail analysis" in analyze_content.lower()
    assert "re-entry chain" in analyze_content.lower()


def test_codex_generated_sp_map_scan_build_include_native_mapping_guidance(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-map-scan-build"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

    scan_content = (target / ".codex" / "skills" / "sp-map-scan" / "SKILL.md").read_text(encoding="utf-8").lower()
    build_content = (target / ".codex" / "skills" / "sp-map-build" / "SKILL.md").read_text(encoding="utf-8").lower()
    update_content = (target / ".codex" / "skills" / "sp-map-update" / "SKILL.md").read_text(encoding="utf-8").lower()
    assert not (target / ".codex" / "skills" / "sp-map-codebase" / "SKILL.md").exists()

    assert ".specify/project-cognition/" in scan_content
    assert ".specify/project-cognition/evidence/" in scan_content
    assert ".specify/project-cognition/provisional/nodes.json" in scan_content
    assert ".specify/project-cognition/provisional/edges.json" in scan_content
    assert ".specify/project-cognition/provisional/observations.json" in scan_content
    assert ".specify/project-cognition/coverage.json" in scan_content
    assert 'choose_subagent_dispatch(command_name="map-scan"' in scan_content
    assert "evidence" in scan_content
    assert "coverage" in scan_content
    assert "machine-readable scan artifact schema" in scan_content
    assert "source_node_id" in scan_content
    assert "target_node_id" in scan_content
    assert "attrs_json" in scan_content
    assert "coverage.json does not create path_index rows by itself" in scan_content
    assert "spawn_agent" in scan_content
    assert "native subagent capability discovery" in scan_content
    assert "tool discovery" in scan_content
    assert "do not record `subagent-blocked`" in scan_content
    assert "wait_agent" in scan_content
    assert "close_agent" in scan_content
    assert "provisional" in scan_content

    assert ".specify/project-cognition/project-cognition.db" in build_content
    assert "compass --intent implement" in build_content
    assert "query --intent implement" in build_content
    assert "alias catalog" in build_content
    assert "semantic_intake" in build_content
    assert "facet coverage" in build_content
    assert "concept_decisions" in build_content
    assert "lexicon_generation_id" in build_content
    assert "--query-plan" in build_content
    assert "returned map terms" not in build_content
    assert 'choose_subagent_dispatch(command_name="map-build"' in build_content
    assert "path index source contract" in build_content
    assert "nodes.json `paths`" in build_content
    assert "raw graph json artifacts or slices as runtime truth" in build_content
    assert "spawn_agent" in build_content
    assert "native subagent capability discovery" in build_content
    assert "do not record `subagent-blocked`" in build_content
    assert "wait_agent" in build_content
    assert "close_agent" in build_content
    assert "project cognition" in build_content
    assert "confidence" in build_content
    assert "conflict" in build_content

    assert "sp-map-update" in update_content
    assert "project-cognition" in update_content
    assert "spawn_agent" in update_content
    assert "native subagent capability discovery" in update_content
    assert "do not record `subagent-blocked`" in update_content
    assert "wait_agent" in update_content
    assert "diff impact closure" in update_content
    assert "affected graph and alias refresh" in update_content
    assert "user supplement normalization" in update_content
    assert "route-pack reconciliation" in update_content
    assert "prefer the smallest executable update lane set" in update_content
    assert "user-supplied scope remains authoritative unless repository evidence disproves it" in update_content
    assert "do not turn a one-slice or metadata-only refresh into scan-style parallel exploration" in update_content
    assert "leader-inline-fallback for a one-lane update is preferred over forcing extra subagents" in update_content


def test_codex_generated_subagent_workflow_skills_include_capability_discovery(tmp_path):
    from specify_cli.integrations.codex import CodexIntegration
    from specify_cli.integrations.manifest import IntegrationManifest

    target = tmp_path / "codex-subagent-discovery"
    integration = CodexIntegration()
    manifest = IntegrationManifest("codex", target)
    integration.setup(target, manifest)

    _assert_subagent_using_surfaces_have_discovery(
        path
        for path in (target / ".codex" / "skills").glob("sp-*/SKILL.md")
        if path.parent.name != "sp-fast"
    )


def test_codex_generated_sp_debug_includes_leader_led_native_investigation_guidance(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-debug-routing"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

    skill_path = target / ".codex" / "skills" / "sp-debug" / "SKILL.md"
    content = _read_skill_with_references(skill_path).lower()

    assert "learning start --command debug" in content
    assert "learning show" in content or "show_argv" in content
    assert ".specify/memory/learnings/index.md" not in content
    assert ".planning/learnings/candidates.md" not in content or "compatibility" in content
    assert "codex subagent evidence collection" in content
    assert "compass --intent debug" in content
    assert "query --intent debug" in content
    assert "--query-plan" in content
    assert "minimal_live_reads" in content
    assert "execution_model: leader-inline | subagent-assisted | blocked" in content
    assert "dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked" in content
    assert "execution_surface: leader-inline | native-subagents | none" in content
    assert "small focused investigation" in content
    assert "subagent-assisted" in content
    assert "execution_surface: none" in content
    assert "debug-handbook.md" not in content
    assert "debug-workflow-contract" not in content
    assert "<br>" not in content
    assert "plain text for terminal output" in content
    assert "symptom-to-surface-routing" not in content
    assert "system-topology-for-debug" not in content
    assert "observer framing" in content
    assert "map-backed minimum intake" in content
    assert "deep debug intake dispatch" in content
    assert "stage 1a: causal map" in content
    assert "same_issue" in content
    assert "derived_issue" in content
    assert "unrelated_issue" in content
    assert "contrarian candidate" in content
    assert "the think subagent must not read source files" in content
    assert "the think subagent must not inspect logs" in content
    assert "primary suspected loop" in content
    assert "alternative cause candidates" in content
    assert "transition memo" in content
    assert "if cognition freshness is `missing`, continue with live repository evidence" in content
    assert (
        "use `$sp-map-scan -> $sp-map-build` only for brownfield first/missing/unusable baseline, "
        "schema failure, schema v1 or old broad-schema rebuild-required readiness, "
        "zero active-generation `path_index` rows outside baseline-kind exceptions described below, "
        "missing or invalid `alias_index`"
    ) in content
    assert "if cognition freshness is `stale`, treat map output as advisory" in content
    assert "truth-owning layers" in content
    assert "spawn_agent" in content
    assert "wait_agent" in content
    assert "close_agent" in content
    assert "investigating" in content
    assert "debug file" in content
    assert "evidence-gathering" in content or "evidence gathering" in content
    assert "diagnostic_profile" in content
    assert "scheduler-admission" in content or "evidence-gathering" in content
    assert "must not update the debug file" in content
    assert "wait for every subagent's structured handoff" in content
    assert "do not treat an idle subagent as done work" in content
    assert "candidate queue" in content
    assert "root-cause mode" in content
    assert "workflow-owned mutation closeout is not an external map-maintenance handoff" in content
    assert "update --delta-session" in content
    assert "sp-map-update is for manual/external maintenance and follow-up repair" in content


def test_codex_generated_specify_skill_uses_compact_contract_and_reopen(tmp_path):
    from specify_cli.integrations.codex import CodexIntegration
    from specify_cli.integrations.manifest import IntegrationManifest

    target = tmp_path / "codex-specify"
    integration = CodexIntegration()
    manifest = IntegrationManifest("codex", target)
    integration.setup(target, manifest)
    content = _read_skill_with_references(
        target / ".codex" / "skills" / "sp-specify" / "SKILL.md"
    ).lower()
    assert "spec-contract.json" in content
    assert "semantic_delta" in content
    assert "discussion_decision_digest" in content
    assert "decision_digest_ref" in content
    assert "must_not_dilute" in content
    assert "named evidence reference" in content
    assert "stale, missing, or contradictory" in content
    assert "source_files_read" not in content
    assert "do not repeat user review" in content
    assert "reopen" in content
    assert "brainstorming kernel" not in content
    assert "facts-lock" not in content
    assert "route-lock" not in content
    assert "intent-lock" not in content
    assert "complexity-lock" not in content


def test_codex_generated_sp_specify_uses_simplified_flow_wording(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-specify-brainstorming"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

    content = _read_skill_with_references(
        target / ".codex" / "skills" / "sp-specify" / "SKILL.md"
    )
    lowered = content.lower()

    assert "explore project context" in lowered
    assert "one high-impact question at a time" in lowered
    assert "two or three approaches" in lowered or "2-3 approaches" in lowered
    assert "semantic term" in lowered
    assert "spec-contract.json" in content
    assert "semantic_delta" in content
    assert "compile mode" in lowered
    assert "do not repeat user review" in lowered
    assert "reopen" in lowered
    assert "brainstorming kernel" not in lowered
    assert "facts-lock" not in content
    assert "route-lock" not in content
    assert "intent-lock" not in content
    assert "complexity-lock" not in content
    assert "task classification" not in lowered
    assert "active_profile" not in content
    assert "coverage_mode" not in content
    assert "observer gate" not in lowered
    assert "leader-inline-fallback" not in lowered


def test_codex_generated_implement_skill_mentions_task_contract_and_reopen(tmp_path):
    from specify_cli.integrations.codex import CodexIntegration
    from specify_cli.integrations.manifest import IntegrationManifest

    target = tmp_path / "codex-implement"
    integration = CodexIntegration()
    manifest = IntegrationManifest("codex", target)
    integration.setup(target, manifest)
    content = _read_skill_with_references(
        target / ".codex" / "skills" / "sp-implement" / "SKILL.md"
    ).lower()

    assert "task-index.json" in content
    assert "forbidden drift" in content
    assert "task lifecycle record" in content
    assert "event-triggered review" in content
    assert "reopen" in content


def test_codex_debug_skill_prefers_request_user_input_with_fallback(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-debug-question-tool"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

    content = _read_skill_with_references(
        target / ".codex" / "skills" / "sp-debug" / "SKILL.md"
    ).lower()
    assert "request_user_input" in content
    assert "native structured question tool" in content
    assert "missing-information question" in content or "plain-text clarification" in content
    assert "debug understanding checkpoint" in content
    assert "understanding_confirmed: true" in content
    assert "debug checkpoint" in content
    assert "first evidence action" in content


def test_codex_generated_sp_fast_stays_inline_and_lightweight(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-fast-task"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

    skill_path = target / ".codex" / "skills" / "sp-fast" / "SKILL.md"
    content = _read_skill_with_references(skill_path).lower()

    assert "scope gate" in content
    assert "do not run learning intake, hooks, capture, or promotion" in content
    assert "do not parse learning storage" in content
    assert ".specify/memory/learnings/index.md" not in content
    assert "compass --intent implement" in content
    assert "query --query-plan" in content
    assert "only when `compass_state`, coverage diagnostics, localization, or live evidence requires explicit concept decisions" in content
    assert "alias catalog" in content
    assert "semantic_intake" in content
    assert "facet coverage" in content
    assert "concept_decisions" in content
    assert "lexicon_generation_id" in content
    assert "project-language search terms" in content
    assert "repository_search_terms" in content
    assert "do not search only the raw user words" in content
    assert "--query-plan" in content
    assert "minimal_live_reads" in content
    assert "returned map terms" not in content
    assert "build-handbook.md" not in content
    assert "shared surfaces" in content
    assert "cognition gate" in content
    assert "≤3 files touched" in content or "at most 3 files" in content or "no more than 3 files" in content
    assert "no dependency changes" in content
    assert "the leader performs the change directly" in content or "leader-direct" in content
    assert "verify" in content
    assert "completion claim must be backed by live code, tests, scripts, configuration, or authoritative docs" in content
    assert "project cognition can support route selection but cannot be the sole evidence for completion" in content
    assert "map-update" in content
    assert "dirty only when inline update cannot complete" in content
    assert "do not create spec.md" in content or "no spec.md" in content
    assert "no plan.md" in content or "do not create plan.md" in content
    assert "leader-direct" in content or "the leader performs the change directly" in content


def test_codex_generated_sp_quick_supports_lightweight_tracked_execution(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-quick-task"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0, f"init --ai codex failed: {result.output}"

    skill_path = target / ".codex" / "skills" / "sp-quick" / "SKILL.md"
    content = _read_skill_with_references(skill_path).lower()

    assert ".planning/quick/" in content
    assert (
        render_command(
            (
                "learning",
                "start",
                "--command",
                "<classic-command-name>",
                "--format",
                "json",
            )
        ).lower()
        in content
    )
    assert "show_argv" in content
    assert ".specify/memory/learnings/index.md" not in content
    assert ".planning/learnings/candidates.md" not in content
    assert "compass --intent implement" in content
    assert "query --intent implement" in content
    assert "alias catalog" in content
    assert "semantic_intake" in content
    assert "facet coverage" in content
    assert "concept_decisions" in content
    assert "lexicon_generation_id" in content
    assert "--query-plan" in content
    assert "minimal_live_reads" in content
    assert "returned map terms" not in content
    assert "build-handbook.md" not in content
    assert "build-workflow-contract" not in content
    assert "product-and-capability-map" not in content
    assert "--discuss" in content
    assert "--research" in content
    assert "--validate" in content
    assert "--full" in content
    assert "lightweight" in content
    assert "summary.md" in content or "summary artifact" in content
    assert "codex leader gate" in content
    assert "codex quick-task subagent execution" in content
    assert "spawn_agent" in content
    assert "wait_agent" in content
    assert "close_agent" in content
    assert "managed-team" in content
    assert "understanding checkpoint" in content
    assert "understanding_confirmed: true" in content
    assert_quick_checkpoint_card_shape(content)
    assert "<br>" not in content
    assert "plain text for terminal output" in content
    assert "request and outcome" in content
    assert "user-visible result" in content
    assert "recommended approach" in content
    assert "assumptions and risks" in content
    assert "completion evidence" in content
    assert "reconfirmation trigger" in content
    assert "technical execution belongs to the agent" in content
    assert "## ui confirmation" in content
    assert "single confirmation covers both" in content
    assert "done_or_progress_signal" in content
    assert "dispatch_shape: one-subagent | parallel-subagents" in content
    assert "execution_surface: native-subagents" in content
    assert "dispatch to one subagent with a task contract" in content or "one-subagent" in content
    assert "validated `workertaskpacket` or equivalent execution contract preserves quality" in content
    assert "read `.specify/memory/constitution.md` first if it exists" in content
    assert "advisory first pass" in content
    assert "the next concrete action must be dispatch" in content or "once the first lane is chosen" in content
    assert "materially improve throughput" in content
    assert "subagent-blocked" in content
    assert "join point" in content
    assert "leader" in content
    assert "wait for every subagent's structured handoff" in content
    assert "do not treat an idle subagent as done work" in content
    assert ".planning/quick/<id>-<slug>/" in content
    assert ".planning/quick/index.json" in content
    assert "status.md" in content
    assert "current focus" in content
    assert "next action" in content
    assert "completion claim must be backed by live code, tests, scripts, configuration, or authoritative docs" in content
    assert "project cognition can support route selection but cannot be the sole evidence for completion" in content
    assert "map-update" in content
    assert "workflow-owned mutation closeout is not an external map-maintenance handoff" in content
    assert "update --delta-session" in content
    assert "sp-map-update is for manual/external maintenance and follow-up repair" in content
    assert "resume" in content
    assert "resolved/" in content
    assert "status.md template" in content
    assert "status: gathering | planned | executing | validating | blocked | resolved" in content
    assert "dispatch_shape: one-subagent | parallel-subagents" in content
    assert "summary pointer" in content
    assert "if exactly one unfinished quick task exists" in content
    assert "if multiple unfinished quick tasks exist" in content
    assert "ask the user which quick task to continue" in content
