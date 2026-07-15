"""
Unit tests for extension skill auto-registration.

Tests cover:
- SKILL.md generation when --ai-skills was used during init
- No skills created when ai_skills not active
- SKILL.md content correctness
- Existing user-modified skills not overwritten
- Skill cleanup on extension removal
- Registry metadata includes registered_skills
"""

import json
import os
import re
import pytest
import tempfile
import shutil
import yaml
from pathlib import Path

from specify_cli.extensions import (
    ExtensionManager,
)
from specify_cli import SKILL_DESCRIPTIONS
from tests.template_utils import read_skill_with_references


# ===== Helpers =====

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _body_without_frontmatter(skill_path: Path) -> str:
    content = skill_path.read_text(encoding="utf-8")
    match = re.match(r"\A---\s*\r?\n.*?\r?\n---\s*\r?\n", content, re.S)
    return content[match.end():] if match else content


def _extract_section(text: str, heading: str) -> str:
    match = re.search(rf"(?ms)^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)", text)
    assert match, f"Missing section: {heading}"
    return match.group(1)


def _bullet_lines(text: str) -> list[str]:
    return [match.group(1).strip().lower() for match in re.finditer(r"(?m)^\s*-\s+(.+)$", text)]


def _assert_bullet_contains(bullets: list[str], needle: str) -> None:
    assert any(needle in bullet for bullet in bullets), f"Expected bullet containing: {needle}"


def _assert_terms_in_order(text: str, *terms: str) -> None:
    pattern = ".*?".join(re.escape(term) for term in terms)
    assert re.search(pattern, text, re.IGNORECASE | re.DOTALL), (
        f"Expected ordered sequence: {terms}"
    )

def _create_init_options(project_root: Path, ai: str = "claude", ai_skills: bool = True):
    """Write a .specify/init-options.json file."""
    opts_dir = project_root / ".specify"
    opts_dir.mkdir(parents=True, exist_ok=True)
    opts_file = opts_dir / "init-options.json"
    opts_file.write_text(json.dumps({
        "ai": ai,
        "ai_skills": ai_skills,
        "script": "sh",
    }))


def _create_skills_dir(project_root: Path, ai: str = "claude") -> Path:
    """Create and return the expected skills directory for the given agent."""
    # Match the logic in _get_skills_dir() from specify_cli
    from specify_cli import AGENT_CONFIG

    agent_config = AGENT_CONFIG.get(ai, {})
    agent_folder = agent_config.get("folder", "")
    if agent_folder:
        skills_dir = project_root / agent_folder.rstrip("/") / "skills"
    else:
        skills_dir = project_root / ".agents" / "skills"

    skills_dir.mkdir(parents=True, exist_ok=True)
    return skills_dir


def _create_extension_dir(temp_dir: Path, ext_id: str = "test-ext") -> Path:
    """Create a complete extension directory with manifest and command files."""
    ext_dir = temp_dir / ext_id
    ext_dir.mkdir()

    manifest_data = {
        "schema_version": "1.0",
        "extension": {
            "id": ext_id,
            "name": "Test Extension",
            "version": "1.0.0",
            "description": "A test extension for skill registration",
        },
        "requires": {
            "speckit_version": ">=0.1.0",
        },
        "provides": {
            "commands": [
                {
                    "name": f"sp.{ext_id}.hello",
                    "file": "commands/hello.md",
                    "description": "Test hello command",
                },
                {
                    "name": f"sp.{ext_id}.world",
                    "file": "commands/world.md",
                    "description": "Test world command",
                },
            ]
        },
    }

    with open(ext_dir / "extension.yml", "w") as f:
        yaml.dump(manifest_data, f)

    commands_dir = ext_dir / "commands"
    commands_dir.mkdir()

    (commands_dir / "hello.md").write_text(
        "---\n"
        "description: \"Test hello command\"\n"
        "---\n"
        "\n"
        "# Hello Command\n"
        "\n"
        "Run this to say hello.\n"
        "$ARGUMENTS\n"
    )

    (commands_dir / "world.md").write_text(
        "---\n"
        "description: \"Test world command\"\n"
        "---\n"
        "\n"
        "# World Command\n"
        "\n"
        "Run this to greet the world.\n"
    )

    return ext_dir


# ===== Fixtures =====

@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    tmpdir = tempfile.mkdtemp()
    yield Path(tmpdir)
    shutil.rmtree(tmpdir)


@pytest.fixture
def project_dir(temp_dir):
    """Create a mock spec-kit project directory."""
    proj_dir = temp_dir / "project"
    proj_dir.mkdir()

    # Create .specify directory
    specify_dir = proj_dir / ".specify"
    specify_dir.mkdir()

    return proj_dir


@pytest.fixture
def extension_dir(temp_dir):
    """Create a complete extension directory."""
    return _create_extension_dir(temp_dir)


@pytest.fixture
def skills_project(project_dir):
    """Create a project with --ai-skills enabled and skills directory."""
    _create_init_options(project_dir, ai="claude", ai_skills=True)
    skills_dir = _create_skills_dir(project_dir, ai="claude")
    return project_dir, skills_dir


@pytest.fixture
def no_skills_project(project_dir):
    """Create a project without --ai-skills."""
    _create_init_options(project_dir, ai="claude", ai_skills=False)
    return project_dir


# ===== ExtensionManager._get_skills_dir Tests =====

class TestExtensionManagerGetSkillsDir:
    """Test _get_skills_dir() on ExtensionManager."""

    def test_returns_skills_dir_when_active(self, skills_project):
        """Should return skills dir when ai_skills is true and dir exists."""
        project_dir, skills_dir = skills_project
        manager = ExtensionManager(project_dir)
        result = manager._get_skills_dir()
        assert result == skills_dir

    def test_returns_none_when_no_ai_skills(self, no_skills_project):
        """Should return None when ai_skills is false."""
        manager = ExtensionManager(no_skills_project)
        result = manager._get_skills_dir()
        assert result is None

    def test_returns_cursor_skills_dir_for_native_skill_integration(self, project_dir):
        """Cursor agent should resolve to the moved .cursor/skills directory."""
        _create_init_options(project_dir, ai="cursor-agent", ai_skills=True)
        skills_dir = _create_skills_dir(project_dir, ai="cursor-agent")

        manager = ExtensionManager(project_dir)
        result = manager._get_skills_dir()

        assert result == skills_dir


class TestBuiltInSkillGeneration:
    """Built-in skill scaffolding should expose the latest command surfaces."""

    @staticmethod
    def _frontmatter(skill_path: Path) -> dict:
        content = skill_path.read_text(encoding="utf-8")
        parts = content.split("---", 2)
        return yaml.safe_load(parts[1])

    def test_claude_ai_skills_include_new_command_surfaces(self, temp_dir):
        from typer.testing import CliRunner
        from specify_cli import app

        project_dir = temp_dir / "claude-skill-surfaces"
        project_dir.mkdir()

        old_cwd = Path.cwd()
        try:
            os.chdir(project_dir)
            runner = CliRunner()
            result = runner.invoke(
                app,
                [
                    "init",
                    "--here",
                    "--ai",
                    "claude",
                    "--ai-skills",
                    "--script",
                    "sh",
                    "--no-git",
                    "--ignore-agent-tools",
                ],
                catch_exceptions=False,
            )
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 0, result.output

        skills_dir = project_dir / ".claude" / "skills"
        assert (skills_dir / "sp-clarify" / "SKILL.md").exists()
        assert (skills_dir / "sp-deep-research" / "SKILL.md").exists()
        assert (skills_dir / "sp-explain" / "SKILL.md").exists()
        assert (skills_dir / "sp-map-scan" / "SKILL.md").exists()
        assert (skills_dir / "sp-map-build" / "SKILL.md").exists()
        assert not (skills_dir / "sp-map-codebase" / "SKILL.md").exists()
        assert not (skills_dir / "sp-test-scan" / "SKILL.md").exists()
        assert not (skills_dir / "sp-test-build" / "SKILL.md").exists()
        assert not (skills_dir / "sp-test" / "SKILL.md").exists()
        assert (skills_dir / "sp-fast" / "SKILL.md").exists()
        assert (skills_dir / "sp-quick" / "SKILL.md").exists()
        assert (skills_dir / "sp-prd" / "SKILL.md").exists()
        assert (project_dir / ".specify" / "templates" / "context-template.md").exists()
        assert (project_dir / ".specify" / "templates" / "project-rules-template.md").exists()
        assert (project_dir / ".specify" / "templates" / "project-confirmed-learnings-template.md").exists()
        assert (project_dir / ".specify" / "templates" / "project-learnings-index-template.md").exists()
        assert (project_dir / ".specify" / "templates" / "project-learning-detail-template.md").exists()
        assert (project_dir / ".specify" / "templates" / "project-learning-record-schema.json").exists()
        assert not (project_dir / ".specify" / "templates" / "testing").exists()

        def _skill_body(skill_name: str) -> str:
            return read_skill_with_references(skills_dir / skill_name / "SKILL.md")

        for skill_name in (
            "sp-specify",
            "sp-deep-research",
            "sp-plan",
            "sp-implement",
            "sp-debug",
            "sp-quick",
        ):
            body = _skill_body(skill_name).lower()
            assert "learning start --command " in body
            assert "--format json" in body
            assert "--detail-level" not in body
            assert "show_argv" in body
            assert ".specify/memory/learnings/index.md" not in body
            assert ".planning/learnings/candidates.md" not in body or "compatibility" in body
            assert "workflow contract summary" in body
            assert "routing metadata only" in body
        fast_body = _skill_body("sp-fast").lower()
        assert "do not run learning intake" in fast_body
        assert ".specify/memory/learnings/index.md" not in fast_body
        assert "workflow contract summary" in fast_body
        assert "routing metadata only" in fast_body
        constitution_body = _skill_body("sp-constitution").lower()
        constitution = (project_dir / ".specify" / "memory" / "constitution.md").read_text(encoding="utf-8").lower()
        assert "learning start --command constitution --format json" in constitution_body
        assert "show_argv" in constitution_body
        assert ".specify/memory/learnings/index.md" not in constitution_body
        assert ".planning/learnings/candidates.md" not in constitution_body
        assert ".specify/project-cognition/status.json" in constitution
        assert "workflow-appropriate cognition" in constitution
        assert "advisory project cognition index" in constitution
        assert "map points, code proves" in constitution
        assert "map-update" in constitution
        assert "/sp-map-scan" in constitution_body
        assert "/sp-map-build" in constitution_body
        assert "workflow-state.md" in constitution_body
        assert "/sp-plan" in constitution_body
        assert "/sp-tasks" in constitution_body
        assert "/sp-analyze" in constitution_body
        assert (project_dir / ".specify" / "templates" / "references-template.md").exists()
        assert "clarify" in result.output.lower()

        explain_body = _skill_body("sp-explain")
        explain_tui = _extract_section(explain_body, "TUI Requirements").lower()
        explain_blocks = _bullet_lines(explain_tui)
        _assert_bullet_contains(explain_blocks, "stage header")
        _assert_bullet_contains(explain_blocks, "status block")
        _assert_bullet_contains(explain_blocks, "explanation block")
        _assert_bullet_contains(explain_blocks, "risk block")
        _assert_bullet_contains(explain_blocks, "next-step block")
        assert "open blocks" in explain_body.lower()
        assert "stage-aware" in explain_tui
        assert re.search(r"`specify`: explain .*everyday terms", explain_tui)
        assert re.search(r"`plan`: explain .*implementation approach", explain_tui)
        assert re.search(r"`tasks`: explain .*concrete work", explain_tui)
        assert re.search(r"`implement`: explain .*progress.*current scope.*active risks", explain_tui)
        assert "choose_subagent_dispatch" in explain_body.lower()
        assert "packetized and dispatched safely" in explain_body.lower()
        assert "supporting artifact cross-check" in explain_body.lower()
        assert "before rendering the final explanation" in explain_body.lower()

        specify_body = _skill_body("sp-specify")
        assert "pre-analysis protocol" in specify_body.lower()
        assert "native structured question tool" in specify_body.lower()
        assert "fallback-only text format guidance" in specify_body.lower()
        assert "if a native structured question tool is available, you must use it" in specify_body.lower()
        assert "do not render the textual fallback block when the native tool is available" in specify_body.lower()
        assert "do not self-authorize textual fallback because the question seems simple" in specify_body.lower()
        assert "only fall back after the native tool is unavailable or the tool call fails" in specify_body.lower()
        assert "Stage header" in specify_body or "stage header" in specify_body.lower()
        assert "Question header" in specify_body or "question header" in specify_body.lower()
        assert "Prompt" in specify_body or "prompt" in specify_body.lower()
        assert "Recommendation" in specify_body or "recommendation" in specify_body.lower()
        assert "Options" in specify_body or "options" in specify_body.lower()
        assert "Reply instruction" in specify_body or "reply instruction" in specify_body.lower()
        assert "/sp.plan" in specify_body
        assert "guided requirement discovery" in specify_body.lower()
        assert "fixed heavy discovery lifecycle" in specify_body.lower()
        assert "final-handoff-decision" in specify_body.lower()
        assert "planning-relevant gray areas" in specify_body.lower()
        assert "project-cognition compass --intent plan" in specify_body
        assert "project-cognition query --intent plan --query-plan" in specify_body
        assert "--query-plan" in specify_body
        assert "minimal_live_reads" in specify_body
        assert "named evidence reference" in specify_body.lower()
        assert "returned map terms" not in specify_body.lower()
        assert "BUILD-HANDBOOK.md" not in specify_body
        assert "BUILD-WORKFLOW-CONTRACT" not in specify_body
        assert "PRODUCT-AND-CAPABILITY-MAP" not in specify_body
        assert "spec-contract.json" in specify_body
        assert "compile mode" in specify_body.lower()
        assert "semantic_delta" in specify_body
        assert "one bounded `project-cognition compass" in specify_body
        assert "do not build a second broad repository summary" in specify_body.lower()
        assert "workflow-state.md" in specify_body
        assert "specify workflow show --feature-dir <feature-dir> --format json" in specify_body
        assert "specify workflow enter --command specify" in specify_body
        assert "deterministic runtime owns `workflow-state.md`" in specify_body
        assert "create or resume sparse `WORKFLOW_STATE_FILE`" not in specify_body
        assert "Do not implement code, edit source files, edit tests, or run implementation-oriented fix loops from `sp-specify`." in specify_body
        assert "open live files only for the named gap" in specify_body.lower()
        assert "clarify only planning-critical ambiguity" in specify_body.lower()
        assert "context.md" in specify_body
        assert "independent project-review value" in specify_body.lower()
        assert "/sp.clarify" in specify_body or "{{invoke:clarify}}" in specify_body
        assert "final-handoff-decision" in specify_body
        assert "/sp.deep-research" in specify_body or "{{invoke:deep-research}}" in specify_body
        assert "git-baseline freshness" in specify_body.lower()
        assert "complete-refresh" in specify_body
        assert "manual override/fallback" in specify_body.lower()
        assert "run `/sp-map-scan` followed by `/sp-map-build`" in specify_body

        prd_body = _skill_body("sp-prd")
        prd_lower = prd_body.lower()
        assert "deprecated compatibility entrypoint" in prd_lower
        assert "compatibility-only" in prd_lower
        assert "route the work through the canonical flow instead" in prd_lower
        assert "sp-prd-scan" in prd_body
        assert "sp-prd-build" in prd_body
        assert ".specify/prd-runs/<run-id>/prd-scan.md" in prd_body
        assert "exports/prd.md" in prd_body
        assert "old one-step semantics" in prd_lower
        assert "do not skip `sp-prd-scan` and jump straight to `sp-prd-build`" in prd_lower
        plan_body = _skill_body("sp-plan")
        assert "Add `Implementation Constitution`" in plan_body
        assert "spec-contract.json" in plan_body
        assert "plan-contract.json" in plan_body
        assert "architecture/module decisions and interface consumes/produces map" in plan_body
        assert "implementation target and boundary refs" in plan_body
        assert "Dispatch Compilation Hints" in plan_body
        assert "workflow-state.md" in plan_body
        assert "enter `plan` with the deterministic workflow transition" in plan_body.lower()
        assert "workflow transition --to <this-stage>" in plan_body
        assert "do not edit source/runtime/test files" in plan_body.lower()
        assert "planning does not grant permission to start execution" in plan_body.lower()
        assert "planning/handoffs/<lane-id>.json" in plan_body
        assert "planning/lane-manifest.json" in plan_body
        assert "do not create separate evidence-index and checkpoint logs" in plan_body.lower()
        assert "do not synthesize `plan.md`, `research.md`, or `plan-contract.json` from chat-only delegated lane results" in plan_body.lower()
        assert "artifact-writing delegated planning lanes must be dispatched" in plan_body.lower()
        assert "writable, execution-capable native subagent" in plan_body.lower()
        assert "do not dispatch a read-only explorer, reviewer, or diagnostic lane" in plan_body.lower()
        assert "execution_model: adaptive" in plan_body
        assert "execution_mode: light | standard | heavy" in plan_body
        assert "one result per lane" in plan_body.lower()
        assert "git-baseline freshness" in plan_body.lower()
        assert "complete-refresh" in plan_body
        assert "manual override/fallback" in plan_body.lower()
        assert "run `/sp-map-scan` followed by `/sp-map-build`" in plan_body

        clarify_body = _skill_body("sp-clarify")
        assert "clarification/handoffs/<lane-id>.json" in clarify_body
        assert "clarification/evidence-index.json" in clarify_body
        assert "clarification/checkpoints.ndjson" in clarify_body
        assert "consume `clarification/evidence-index.json` before final artifact updates" in clarify_body.lower()
        assert "do not update `spec.md`, `alignment.md`, `context.md`, or `references.md` from chat-only lane results" in clarify_body.lower()

        tasks_body = _skill_body("sp-tasks")
        assert "plan-contract.json" in tasks_body
        assert "task-index.json" in tasks_body
        assert "forbidden drift" in tasks_body.lower()
        assert "MP-*" in tasks_body
        assert "CA-###" in tasks_body
        assert "workflow-state.md" in tasks_body
        assert "enter `tasks` through the deterministic workflow transition" in tasks_body.lower()
        assert "the cli owns phase state" in tasks_body.lower()
        assert "one result per lane under `task-generation/handoffs/`" in tasks_body.lower()
        assert "task-generation/lane-manifest.json" in tasks_body
        assert "do not create separate evidence-index and checkpoint logs" in tasks_body.lower()
        assert "chat-only lane output is not handoff truth" in tasks_body.lower()
        assert "keep implementation blocked" in tasks_body.lower()
        assert "execution_model: adaptive" in tasks_body
        assert "execution_mode: light | standard | heavy" in tasks_body
        assert "compile delegated packets just in time" in tasks_body.lower()
        assert "risk and behavior driven validation" in tasks_body.lower()
        assert "no-new-test rationale" in tasks_body.lower()
        assert "replacement validation" in tasks_body.lower()
        assert "residual risk" in tasks_body.lower()
        assert "minimum light-mode `tasks.md` contract" in tasks_body.lower()
        assert "recommended next command" in tasks_body.lower()
        assert "git-baseline freshness" in tasks_body.lower()
        assert "complete-refresh" in tasks_body
        assert "manual override/fallback" in tasks_body.lower()
        assert "run `/sp-map-scan` followed by `/sp-map-build`" in tasks_body
        routing_body = _body_without_frontmatter(PROJECT_ROOT / "templates" / "passive-skills" / "spec-kit-workflow-routing" / "SKILL.md").lower()
        assert "default generated path is `sp-specify -> sp-plan -> sp-tasks -> sp-implement -> sp-accept`" in routing_body
        assert "use `sp-implement` after `sp-tasks` produces canonical `task-index.json` or a light direct task list and records `/sp.implement`." in routing_body
        assert "use `sp-analyze` only for optional diagnostics, explicit user requests, or persisted legacy `/sp.analyze` state." in routing_body
        assert "clean completed `sp-tasks` state with `/sp.implement` routes directly to" in routing_body
        assert "it does not need an `sp-auto` hop" in routing_body

        implement_body = _skill_body("sp-implement")
        assert "task-index.json" in implement_body
        assert "execution_model: adaptive" in implement_body
        assert "leader-direct" in implement_body
        assert "forbidden drift" in implement_body.lower()
        assert "just in time" in implement_body.lower()
        assert "event-triggered review" in implement_body.lower()
        assert "task lifecycle record" in implement_body.lower()
        assert "validated `workertaskpacket`" in implement_body.lower()
        assert "dispatch only from validated `workertaskpacket`" in implement_body.lower() or "raw task text alone" in implement_body.lower()
        assert "write or select the smallest failing test or reproducible check first" in implement_body.lower()
        assert "run it before production edits" in implement_body.lower()
        assert "rerun the same red gate and require green" in implement_body.lower()

        analyze_body = _skill_body("sp-analyze")
        assert "Boundary Guardrail Gaps" in analyze_body
        assert "BG1" in analyze_body
        assert "BG2" in analyze_body
        assert "BG3" in analyze_body
        assert "DP1" in analyze_body
        assert "DP2" in analyze_body
        assert "DP3" in analyze_body
        assert "Boundary Guardrail Table" in analyze_body
        assert "Boundary Guardrail Gap Count" in analyze_body
        assert "output exactly one `Recommended Next Command`" in analyze_body
        assert "Closed-loop requirement" in analyze_body
        assert "Recommended Re-entry" in analyze_body
        assert "This command does not edit `spec.md`, `context.md`, `plan.md`, or `tasks.md`." in analyze_body
        assert "this command may update `workflow-state.md` to record the cleared or blocked gate result" in analyze_body.lower()
        assert "analysis-only" in analyze_body.lower()
        assert "`next_command: /sp.implement`" in analyze_body
        assert "If the highest invalid stage is `clarify`" in analyze_body
        assert "spec-contract.json" in analyze_body
        assert "plan-contract.json" in analyze_body
        assert "task-index.json" in analyze_body
        assert "planning/lane-manifest.json" in analyze_body
        assert "task-generation/lane-manifest.json" in analyze_body
        assert "accepted planning handoff with no downstream consumer" in analyze_body.lower()
        assert "accepted task-generation handoff with no downstream consumer" in analyze_body.lower()
        assert "If the remaining issue is execution-only, the re-entry chain MUST begin at" in analyze_body
        assert "exact workflow re-entry path" in analyze_body

        scan_body = _skill_body("sp-map-scan")
        scan_lower = scan_body.lower()
        assert ".specify/project-cognition/status.json" in scan_body
        assert ".specify/project-cognition/evidence/" in scan_body
        assert ".specify/project-cognition/provisional/nodes.json" in scan_body
        assert ".specify/project-cognition/provisional/edges.json" in scan_body
        assert ".specify/project-cognition/provisional/observations.json" in scan_body
        assert ".specify/project-cognition/coverage.json" in scan_body
        assert 'choose_subagent_dispatch(command_name="map-scan"' in scan_body
        assert "enumerate project-internal evidence comprehensively" in scan_body
        assert "high-value `.git` evolution surfaces" in scan_body
        assert "stay graph-native from the start" in scan_lower
        assert "provisional nodes and candidate edges" in scan_lower
        assert "evidence harvested" in scan_lower

        build_body = _skill_body("sp-map-build")
        assert ".specify/project-cognition/status.json" in build_body
        assert ".specify/project-cognition/project-cognition.db" in build_body
        assert 'choose_subagent_dispatch(command_name="map-build"' in build_body
        assert "route back to `/sp-map-scan`" in build_body
        assert "Required Graph Semantics" in build_body
        assert "queryable task-local bundle generation" in build_body
        assert "query-ready baseline" in build_body
        assert "Do not publish handbook-first runtime truth" in build_body
        assert "validate scan completeness for graph reconstruction" in build_body
        assert "build schema v5 `alias_index` rows" in build_body
        assert "synthesize `concept_candidates` from graph-backed aliases" in build_body
        assert "status.json` reflects a query-ready baseline" in build_body

        fast_body = _skill_body("sp-fast")
        assert "write a failing targeted test or failing repro check before editing production code" in fast_body.lower()
        assert "do not use manual sanity checks as a substitute for red" in fast_body.lower()
        assert "/sp-quick" in fast_body.lower()
        assert "/sp-debug" in fast_body.lower()
        assert "root cause is still unknown" in fast_body.lower() or "root cause is not yet known" in fast_body.lower()

        quick_body = _skill_body("sp-quick")
        assert "first executable lane must produce a failing automated test or failing repro check before production edits begin" in quick_body.lower()
        assert "do not write production code until the red state is captured" in quick_body.lower()
        assert "bootstrap the smallest viable test surface first" in quick_body.lower()
        assert "/sp-specify" in quick_body.lower()
        assert "/sp-debug" in quick_body.lower()
        assert "root cause is still unknown" in quick_body.lower() or "root cause is not yet known" in quick_body.lower()
        assert "surface-only" in quick_body.lower() or "symptom-only" in quick_body.lower()

        checklist_body = _skill_body("sp-checklist")
        checklist_lower = checklist_body.lower()
        assert ".specify/memory/constitution.md" in checklist_lower
        assert "learning start --command <classic-command-name> --format json" in checklist_lower
        assert "show_argv" in checklist_lower
        assert ".specify/memory/learnings/index.md" not in checklist_lower
        assert ".planning/learnings/candidates.md" not in checklist_lower
        assert "consume-only" in checklist_lower
        assert "project-cognition compass --intent plan" in checklist_lower
        assert "lexicon -> semantic_intake -> query" in checklist_lower
        assert "query --intent plan --query-plan" in checklist_lower or "query --query-plan" in checklist_lower
        assert "alias catalog" in checklist_lower
        assert "semantic_intake" in checklist_lower
        assert "facet coverage" in checklist_lower
        assert "concept_decisions" in checklist_lower
        assert "lexicon_generation_id" in checklist_lower
        assert "--query-plan" in checklist_lower
        assert "task-local bundle" in checklist_lower
        assert "minimal_live_reads" in checklist_lower
        assert "returned map terms" not in checklist_lower
        assert ".specify/project-cognition/slices/change.json" not in checklist_lower
        assert "build-handbook.md" not in checklist_lower
        assert "touched area's owning surfaces" in checklist_lower
        assert "recommended_next_action" in checklist_lower
        assert "route through the returned `recommended_next_action`" in checklist_body
        assert "recommend `/sp-specify`" in checklist_lower or "recommend `/sp.specify`" in checklist_lower
        assert "recommend `/sp-plan`" in checklist_lower
        assert "optional" in checklist_lower

        debug_body = _skill_body("sp-debug")
        debug_lower = debug_body.lower()
        assert "observer framing" in debug_lower
        assert "map-backed minimum intake" in debug_lower
        assert "deep fallback intake" in debug_lower
        assert "stage 1a: causal map" in debug_lower
        assert "same_issue" in debug_lower
        assert "derived_issue" in debug_lower
        assert "unrelated_issue" in debug_lower
        assert "debug understanding checkpoint" in debug_lower
        assert "understanding_confirmed: true" in debug_lower
        assert "wait for user confirmation" in debug_lower
        assert "contrarian candidate" in debug_lower
        assert "causal_map_completed: true" in debug_lower
        assert "investigation_contract_completed: true" in debug_lower
        assert "the think subagent must not read source files" in debug_lower
        assert "the think subagent must not inspect logs" in debug_lower
        assert "the think subagent must not read test files" in debug_lower
        assert "primary suspected loop" in debug_lower
        assert "alternative cause candidates" in debug_lower
        assert "transition memo" in debug_lower
        assert "automatically continue into evidence investigation" in debug_lower
        assert "write a failing automated repro test before changing production code" in debug_lower
        assert "do not modify production behavior until the red state is proven" in debug_lower
        assert "add the missing harness first or route through `/sp-quick` or `/sp-specify`" in debug_lower
        assert "alternative_hypotheses_considered" in debug_lower
        assert "alternative_hypotheses_ruled_out" in debug_lower
        assert "root_cause_confidence" in debug_lower
        assert "fix_scope" in debug_lower
        assert "loop_restoration_proof" in debug_lower
        assert "surface-only" in debug_lower
        assert "candidate queue" in debug_lower
        assert "root-cause mode" in debug_lower


class TestSkillDescriptions:
    """Built-in command descriptions should stay aligned with bundled templates."""

    def test_skill_descriptions_include_new_surfaces(self):
        for name, description in SKILL_DESCRIPTIONS.items():
            if name == "prd":
                continue
            assert description.startswith("Use when"), f"{name} description should be trigger-oriented"

        assert "guided requirement discovery" in SKILL_DESCRIPTIONS["specify"].lower()
        assert "planning-ready specification package" in SKILL_DESCRIPTIONS["specify"].lower()
        assert "current-state prd extraction" in SKILL_DESCRIPTIONS["prd"].lower()
        assert "without automatically handing off to planning" in SKILL_DESCRIPTIONS["prd"].lower()
        assert "planning-critical gaps" in SKILL_DESCRIPTIONS["clarify"].lower()
        assert "feasibility risk" in SKILL_DESCRIPTIONS["deep-research"].lower()
        assert "planning handoff" in SKILL_DESCRIPTIONS["deep-research"].lower()
        assert "plain language" in SKILL_DESCRIPTIONS["explain"].lower()
        assert "implementation planning" in SKILL_DESCRIPTIONS["plan"].lower()
        assert "dependency-aware tasks" in SKILL_DESCRIPTIONS["tasks"].lower()
        assert "tracked implementation workflow" in SKILL_DESCRIPTIONS["implement"].lower()
        assert "boundary-guardrail analysis" in SKILL_DESCRIPTIONS["analyze"].lower()
        assert "development rules" in SKILL_DESCRIPTIONS["constitution"].lower()
        assert "checklist" in SKILL_DESCRIPTIONS["checklist"].lower()
        assert "truly trivial" in SKILL_DESCRIPTIONS["fast"].lower()
        assert "lightweight tracked planning" in SKILL_DESCRIPTIONS["quick"].lower()
        assert "graph-native cognition baseline" in SKILL_DESCRIPTIONS["map-scan"].lower()
        assert "map-scan" in SKILL_DESCRIPTIONS["map-build"].lower()
        assert "github issues" in SKILL_DESCRIPTIONS["taskstoissues"].lower()

    def test_returns_none_when_no_init_options(self, project_dir):
        """Should return None when init-options.json is missing."""
        manager = ExtensionManager(project_dir)
        result = manager._get_skills_dir()
        assert result is None

    def test_returns_none_when_skills_dir_missing(self, project_dir):
        """Should return None when skills dir doesn't exist on disk."""
        _create_init_options(project_dir, ai="claude", ai_skills=True)
        # Don't create the skills directory
        manager = ExtensionManager(project_dir)
        result = manager._get_skills_dir()
        assert result is None

    def test_returns_kimi_skills_dir_when_ai_skills_disabled(self, project_dir):
        """Kimi should still use its native skills dir when ai_skills is false."""
        _create_init_options(project_dir, ai="kimi", ai_skills=False)
        skills_dir = _create_skills_dir(project_dir, ai="kimi")
        manager = ExtensionManager(project_dir)
        result = manager._get_skills_dir()
        assert result == skills_dir

    def test_returns_none_for_non_dict_init_options(self, project_dir):
        """Corrupted-but-parseable init-options should not crash skill-dir lookup."""
        opts_file = project_dir / ".specify" / "init-options.json"
        opts_file.parent.mkdir(parents=True, exist_ok=True)
        opts_file.write_text("[]")
        _create_skills_dir(project_dir, ai="claude")
        manager = ExtensionManager(project_dir)
        result = manager._get_skills_dir()
        assert result is None


def test_team_template_has_valid_frontmatter_boundary():
    content = (PROJECT_ROOT / "templates" / "commands" / "team.md").read_text(encoding="utf-8")

    assert content.startswith("---\n")
    assert "description:" in content.split("---", 2)[1]


# ===== Extension Skill Registration Tests =====

def test_extension_skills_follow_cursor_skills_dir(project_dir, extension_dir):
    _create_init_options(project_dir, ai="cursor-agent", ai_skills=True)
    skills_dir = _create_skills_dir(project_dir, ai="cursor-agent")

    manager = ExtensionManager(project_dir)
    manager.install_from_directory(extension_dir, "0.1.0", register_commands=False)

    assert (skills_dir / "sp-test-ext-hello" / "SKILL.md").exists()
    assert (skills_dir / "sp-test-ext-world" / "SKILL.md").exists()


class TestExtensionSkillRegistration:
    """Test _register_extension_skills() on ExtensionManager."""

    def test_skills_created_when_ai_skills_active(self, skills_project, extension_dir):
        """Skills should be created when ai_skills is enabled."""
        project_dir, skills_dir = skills_project
        manager = ExtensionManager(project_dir)
        manager.install_from_directory(
            extension_dir, "0.1.0", register_commands=False
        )

        # Check that skill directories were created
        skill_dirs = sorted([d.name for d in skills_dir.iterdir() if d.is_dir()])
        assert "sp-test-ext-hello" in skill_dirs
        assert "sp-test-ext-world" in skill_dirs

    def test_skill_md_content_correct(self, skills_project, extension_dir):
        """SKILL.md should have correct agentskills.io structure."""
        project_dir, skills_dir = skills_project
        manager = ExtensionManager(project_dir)
        manager.install_from_directory(
            extension_dir, "0.1.0", register_commands=False
        )

        skill_file = skills_dir / "sp-test-ext-hello" / "SKILL.md"
        assert skill_file.exists()
        content = skill_file.read_text()

        # Check structure
        assert content.startswith("---\n")
        assert "name: sp-test-ext-hello" in content
        assert "description:" in content
        assert "Test hello command" in content
        assert "source: extension:test-ext" in content
        assert "author: github-spec-kit" in content
        assert "compatibility:" in content
        assert "Run this to say hello." in content

    def test_skill_md_has_parseable_yaml(self, skills_project, extension_dir):
        """Generated SKILL.md should contain valid, parseable YAML frontmatter."""
        project_dir, skills_dir = skills_project
        manager = ExtensionManager(project_dir)
        manager.install_from_directory(
            extension_dir, "0.1.0", register_commands=False
        )

        skill_file = skills_dir / "sp-test-ext-hello" / "SKILL.md"
        content = skill_file.read_text()

        assert content.startswith("---\n")
        parts = content.split("---", 2)
        assert len(parts) >= 3
        parsed = yaml.safe_load(parts[1])
        assert isinstance(parsed, dict)
        assert parsed["name"] == "sp-test-ext-hello"
        assert "description" in parsed
        assert "disable-model-invocation" not in parsed

    def test_no_skills_when_ai_skills_disabled(self, no_skills_project, extension_dir):
        """No skills should be created when ai_skills is false."""
        manager = ExtensionManager(no_skills_project)
        manifest = manager.install_from_directory(
            extension_dir, "0.1.0", register_commands=False
        )

        # Verify registry
        metadata = manager.registry.get(manifest.id)
        assert metadata["registered_skills"] == []

    def test_no_skills_when_init_options_missing(self, project_dir, extension_dir):
        """No skills should be created when init-options.json is absent."""
        manager = ExtensionManager(project_dir)
        manifest = manager.install_from_directory(
            extension_dir, "0.1.0", register_commands=False
        )

        metadata = manager.registry.get(manifest.id)
        assert metadata["registered_skills"] == []

    def test_existing_skill_not_overwritten(self, skills_project, extension_dir):
        """Pre-existing SKILL.md should not be overwritten."""
        project_dir, skills_dir = skills_project

        # Pre-create a custom skill
        custom_dir = skills_dir / "sp-test-ext-hello"
        custom_dir.mkdir(parents=True)
        custom_content = "# My Custom Hello Skill\nUser-modified content\n"
        (custom_dir / "SKILL.md").write_text(custom_content)

        manager = ExtensionManager(project_dir)
        manifest = manager.install_from_directory(
            extension_dir, "0.1.0", register_commands=False
        )

        # Custom skill should be untouched
        assert (custom_dir / "SKILL.md").read_text() == custom_content

        # But the other skill should still be created
        metadata = manager.registry.get(manifest.id)
        assert "sp-test-ext-world" in metadata["registered_skills"]
        # The pre-existing one should NOT be in registered_skills (it was skipped)
        assert "sp-test-ext-hello" not in metadata["registered_skills"]

    def test_registered_skills_in_registry(self, skills_project, extension_dir):
        """Registry should contain registered_skills list."""
        project_dir, skills_dir = skills_project
        manager = ExtensionManager(project_dir)
        manifest = manager.install_from_directory(
            extension_dir, "0.1.0", register_commands=False
        )

        metadata = manager.registry.get(manifest.id)
        assert "registered_skills" in metadata
        assert len(metadata["registered_skills"]) == 2
        assert "sp-test-ext-hello" in metadata["registered_skills"]
        assert "sp-test-ext-world" in metadata["registered_skills"]

    def test_kimi_uses_hyphenated_skill_names(self, project_dir, temp_dir):
        """Kimi agent should use the same hyphenated skill names as hooks."""
        _create_init_options(project_dir, ai="kimi", ai_skills=True)
        _create_skills_dir(project_dir, ai="kimi")
        ext_dir = _create_extension_dir(temp_dir, ext_id="test-ext")

        manager = ExtensionManager(project_dir)
        manifest = manager.install_from_directory(
            ext_dir, "0.1.0", register_commands=False
        )

        metadata = manager.registry.get(manifest.id)
        assert "sp-test-ext-hello" in metadata["registered_skills"]
        assert "sp-test-ext-world" in metadata["registered_skills"]

    def test_kimi_creates_skills_when_ai_skills_disabled(self, project_dir, temp_dir):
        """Kimi should still auto-register extension skills in native-skills mode."""
        _create_init_options(project_dir, ai="kimi", ai_skills=False)
        skills_dir = _create_skills_dir(project_dir, ai="kimi")
        ext_dir = _create_extension_dir(temp_dir, ext_id="test-ext")

        manager = ExtensionManager(project_dir)
        manifest = manager.install_from_directory(
            ext_dir, "0.1.0", register_commands=False
        )

        metadata = manager.registry.get(manifest.id)
        assert "sp-test-ext-hello" in metadata["registered_skills"]
        assert "sp-test-ext-world" in metadata["registered_skills"]
        assert (skills_dir / "sp-test-ext-hello" / "SKILL.md").exists()

    def test_skill_registration_resolves_script_placeholders(self, project_dir, temp_dir):
        """Auto-registered extension skills should resolve script placeholders."""
        _create_init_options(project_dir, ai="claude", ai_skills=True)
        skills_dir = _create_skills_dir(project_dir, ai="claude")

        ext_dir = temp_dir / "scripted-ext"
        ext_dir.mkdir()
        manifest_data = {
            "schema_version": "1.0",
            "extension": {
                "id": "scripted-ext",
                "name": "Scripted Extension",
                "version": "1.0.0",
                "description": "Test",
            },
            "requires": {"speckit_version": ">=0.1.0"},
            "provides": {
                "commands": [
                    {
                        "name": "sp.scripted-ext.plan",
                        "file": "commands/plan.md",
                        "description": "Scripted plan command",
                    }
                ]
            },
        }
        with open(ext_dir / "extension.yml", "w") as f:
            yaml.dump(manifest_data, f)

        (ext_dir / "commands").mkdir()
        (ext_dir / "commands" / "plan.md").write_text(
            "---\n"
            "description: Scripted plan command\n"
            "scripts:\n"
            "  sh: ../../scripts/bash/setup-plan.sh --json \"{ARGS}\"\n"
            "agent_scripts:\n"
            "  sh: ../../scripts/bash/update-agent-context.sh __AGENT__\n"
            "---\n\n"
            "Run {SCRIPT}\n"
            "Then {AGENT_SCRIPT}\n"
            "Review templates/checklist.md and memory/constitution.md for __AGENT__.\n"
        )

        manager = ExtensionManager(project_dir)
        manager.install_from_directory(ext_dir, "0.1.0", register_commands=False)

        content = (skills_dir / "sp-scripted-ext-plan" / "SKILL.md").read_text()
        assert "{SCRIPT}" not in content
        assert "{AGENT_SCRIPT}" not in content
        assert "{ARGS}" not in content
        assert "__AGENT__" not in content
        assert '.specify/scripts/bash/setup-plan.sh --json "$ARGUMENTS"' in content
        assert ".specify/scripts/bash/update-agent-context.sh claude" in content
        assert ".specify/templates/checklist.md" in content
        assert ".specify/memory/constitution.md" in content

    def test_missing_command_file_skipped(self, skills_project, temp_dir):
        """Commands with missing source files should be skipped gracefully."""
        project_dir, skills_dir = skills_project

        ext_dir = temp_dir / "missing-cmd-ext"
        ext_dir.mkdir()
        manifest_data = {
            "schema_version": "1.0",
            "extension": {
                "id": "missing-cmd-ext",
                "name": "Missing Cmd Extension",
                "version": "1.0.0",
                "description": "Test",
            },
            "requires": {"speckit_version": ">=0.1.0"},
            "provides": {
                "commands": [
                    {
                        "name": "sp.missing-cmd-ext.exists",
                        "file": "commands/exists.md",
                        "description": "Exists",
                    },
                    {
                        "name": "sp.missing-cmd-ext.ghost",
                        "file": "commands/ghost.md",
                        "description": "Does not exist",
                    },
                ]
            },
        }
        with open(ext_dir / "extension.yml", "w") as f:
            yaml.dump(manifest_data, f)

        (ext_dir / "commands").mkdir()
        (ext_dir / "commands" / "exists.md").write_text(
            "---\ndescription: Exists\n---\n\n# Exists\n\nBody.\n"
        )
        # Intentionally do NOT create ghost.md

        manager = ExtensionManager(project_dir)
        manifest = manager.install_from_directory(
            ext_dir, "0.1.0", register_commands=False
        )

        metadata = manager.registry.get(manifest.id)
        assert "sp-missing-cmd-ext-exists" in metadata["registered_skills"]
        assert "sp-missing-cmd-ext-ghost" not in metadata["registered_skills"]


# ===== Extension Skill Unregistration Tests =====

class TestExtensionSkillUnregistration:
    """Test _unregister_extension_skills() on ExtensionManager."""

    def test_skills_removed_on_extension_remove(self, skills_project, extension_dir):
        """Removing an extension should clean up its skill directories."""
        project_dir, skills_dir = skills_project
        manager = ExtensionManager(project_dir)
        manifest = manager.install_from_directory(
            extension_dir, "0.1.0", register_commands=False
        )

        # Verify skills exist
        assert (skills_dir / "sp-test-ext-hello" / "SKILL.md").exists()
        assert (skills_dir / "sp-test-ext-world" / "SKILL.md").exists()

        # Remove extension
        result = manager.remove(manifest.id, keep_config=False)
        assert result is True

        # Skills should be gone
        assert not (skills_dir / "sp-test-ext-hello").exists()
        assert not (skills_dir / "sp-test-ext-world").exists()

    def test_other_skills_preserved_on_remove(self, skills_project, extension_dir):
        """Non-extension skills should not be affected by extension removal."""
        project_dir, skills_dir = skills_project

        # Pre-create a custom skill
        custom_dir = skills_dir / "my-custom-skill"
        custom_dir.mkdir(parents=True)
        (custom_dir / "SKILL.md").write_text("# My Custom Skill\n")

        manager = ExtensionManager(project_dir)
        manifest = manager.install_from_directory(
            extension_dir, "0.1.0", register_commands=False
        )

        manager.remove(manifest.id, keep_config=False)

        # Custom skill should still exist
        assert (custom_dir / "SKILL.md").exists()
        assert (custom_dir / "SKILL.md").read_text() == "# My Custom Skill\n"

    def test_remove_handles_already_deleted_skills(self, skills_project, extension_dir):
        """Gracefully handle case where skill dirs were already deleted."""
        project_dir, skills_dir = skills_project
        manager = ExtensionManager(project_dir)
        manifest = manager.install_from_directory(
            extension_dir, "0.1.0", register_commands=False
        )

        # Manually delete skill dirs before calling remove
        shutil.rmtree(skills_dir / "sp-test-ext-hello")
        shutil.rmtree(skills_dir / "sp-test-ext-world")

        # Should not raise
        result = manager.remove(manifest.id, keep_config=False)
        assert result is True

    def test_remove_no_skills_when_not_active(self, no_skills_project, extension_dir):
        """Removal without active skills should not attempt skill cleanup."""
        manager = ExtensionManager(no_skills_project)
        manifest = manager.install_from_directory(
            extension_dir, "0.1.0", register_commands=False
        )

        # Should not raise even though no skills exist
        result = manager.remove(manifest.id, keep_config=False)
        assert result is True


# ===== Command File Without Frontmatter =====

class TestExtensionSkillEdgeCases:
    """Test edge cases in extension skill registration."""

    def test_install_with_non_dict_init_options_does_not_crash(self, project_dir, extension_dir):
        """Corrupted init-options payloads should disable skill registration, not crash install."""
        opts_file = project_dir / ".specify" / "init-options.json"
        opts_file.parent.mkdir(parents=True, exist_ok=True)
        opts_file.write_text("[]")
        _create_skills_dir(project_dir, ai="claude")

        manager = ExtensionManager(project_dir)
        manifest = manager.install_from_directory(
            extension_dir, "0.1.0", register_commands=False
        )

        metadata = manager.registry.get(manifest.id)
        assert metadata["registered_skills"] == []

    def test_command_without_frontmatter(self, skills_project, temp_dir):
        """Commands without YAML frontmatter should still produce valid skills."""
        project_dir, skills_dir = skills_project

        ext_dir = temp_dir / "nofm-ext"
        ext_dir.mkdir()
        manifest_data = {
            "schema_version": "1.0",
            "extension": {
                "id": "nofm-ext",
                "name": "No Frontmatter Extension",
                "version": "1.0.0",
                "description": "Test",
            },
            "requires": {"speckit_version": ">=0.1.0"},
            "provides": {
                "commands": [
                    {
                        "name": "sp.nofm-ext.plain",
                        "file": "commands/plain.md",
                        "description": "Plain command",
                    }
                ]
            },
        }
        with open(ext_dir / "extension.yml", "w") as f:
            yaml.dump(manifest_data, f)

        (ext_dir / "commands").mkdir()
        (ext_dir / "commands" / "plain.md").write_text(
            "# Plain Command\n\nBody without frontmatter.\n"
        )

        manager = ExtensionManager(project_dir)
        manager.install_from_directory(
            ext_dir, "0.1.0", register_commands=False
        )

        skill_file = skills_dir / "sp-nofm-ext-plain" / "SKILL.md"
        assert skill_file.exists()
        content = skill_file.read_text()
        assert "name: sp-nofm-ext-plain" in content
        # Fallback description when no frontmatter description
        assert "Extension command: sp.nofm-ext.plain" in content
        assert "Body without frontmatter." in content

    def test_gemini_agent_skills(self, project_dir, temp_dir):
        """Gemini agent should use .gemini/skills/ for skill directory."""
        _create_init_options(project_dir, ai="gemini", ai_skills=True)
        _create_skills_dir(project_dir, ai="gemini")
        ext_dir = _create_extension_dir(temp_dir, ext_id="test-ext")

        manager = ExtensionManager(project_dir)
        manager.install_from_directory(
            ext_dir, "0.1.0", register_commands=False
        )

        skills_dir = project_dir / ".gemini" / "skills"
        assert (skills_dir / "sp-test-ext-hello" / "SKILL.md").exists()
        assert (skills_dir / "sp-test-ext-world" / "SKILL.md").exists()

    def test_multiple_extensions_independent_skills(self, skills_project, temp_dir):
        """Installing and removing different extensions should be independent."""
        project_dir, skills_dir = skills_project

        ext_dir_a = _create_extension_dir(temp_dir, ext_id="ext-a")
        ext_dir_b = _create_extension_dir(temp_dir, ext_id="ext-b")

        manager = ExtensionManager(project_dir)
        manager.install_from_directory(
            ext_dir_a, "0.1.0", register_commands=False
        )
        manager.install_from_directory(
            ext_dir_b, "0.1.0", register_commands=False
        )

        # Both should have skills
        assert (skills_dir / "sp-ext-a-hello" / "SKILL.md").exists()
        assert (skills_dir / "sp-ext-b-hello" / "SKILL.md").exists()

        # Remove ext-a
        manager.remove("ext-a", keep_config=False)

        # ext-a skills gone, ext-b skills preserved
        assert not (skills_dir / "sp-ext-a-hello").exists()
        assert (skills_dir / "sp-ext-b-hello" / "SKILL.md").exists()

    def test_malformed_frontmatter_handled(self, skills_project, temp_dir):
        """Commands with invalid YAML frontmatter should still produce valid skills."""
        project_dir, skills_dir = skills_project

        ext_dir = temp_dir / "badfm-ext"
        ext_dir.mkdir()
        manifest_data = {
            "schema_version": "1.0",
            "extension": {
                "id": "badfm-ext",
                "name": "Bad Frontmatter Extension",
                "version": "1.0.0",
                "description": "Test",
            },
            "requires": {"speckit_version": ">=0.1.0"},
            "provides": {
                "commands": [
                    {
                        "name": "sp.badfm-ext.broken",
                        "file": "commands/broken.md",
                        "description": "Broken frontmatter",
                    }
                ]
            },
        }
        with open(ext_dir / "extension.yml", "w") as f:
            yaml.dump(manifest_data, f)

        (ext_dir / "commands").mkdir()
        # Malformed YAML: invalid key-value syntax
        (ext_dir / "commands" / "broken.md").write_text(
            "---\n"
            "description: [invalid yaml\n"
            "  unclosed: bracket\n"
            "---\n"
            "\n"
            "# Broken Command\n"
            "\n"
            "This body should still be used.\n"
        )

        manager = ExtensionManager(project_dir)
        # Should not raise
        manager.install_from_directory(
            ext_dir, "0.1.0", register_commands=False
        )

        skill_file = skills_dir / "sp-badfm-ext-broken" / "SKILL.md"
        assert skill_file.exists()
        content = skill_file.read_text()
        # Fallback description since frontmatter was invalid
        assert "Extension command: sp.badfm-ext.broken" in content
        assert "This body should still be used." in content

    def test_remove_cleans_up_when_init_options_deleted(self, skills_project, extension_dir):
        """Skills should be cleaned up even if init-options.json is deleted after install."""
        project_dir, skills_dir = skills_project
        manager = ExtensionManager(project_dir)
        manifest = manager.install_from_directory(
            extension_dir, "0.1.0", register_commands=False
        )

        # Verify skills exist
        assert (skills_dir / "sp-test-ext-hello" / "SKILL.md").exists()

        # Delete init-options.json to simulate user change
        init_opts = project_dir / ".specify" / "init-options.json"
        init_opts.unlink()

        # Remove should still clean up via fallback scan
        result = manager.remove(manifest.id, keep_config=False)
        assert result is True
        assert not (skills_dir / "sp-test-ext-hello").exists()
        assert not (skills_dir / "sp-test-ext-world").exists()

    def test_remove_cleans_up_when_ai_skills_toggled(self, skills_project, extension_dir):
        """Skills should be cleaned up even if ai_skills is toggled to false after install."""
        project_dir, skills_dir = skills_project
        manager = ExtensionManager(project_dir)
        manifest = manager.install_from_directory(
            extension_dir, "0.1.0", register_commands=False
        )

        # Verify skills exist
        assert (skills_dir / "sp-test-ext-hello" / "SKILL.md").exists()

        # Toggle ai_skills to false
        _create_init_options(project_dir, ai="claude", ai_skills=False)

        # Remove should still clean up via fallback scan
        result = manager.remove(manifest.id, keep_config=False)
        assert result is True
        assert not (skills_dir / "sp-test-ext-hello").exists()
        assert not (skills_dir / "sp-test-ext-world").exists()


def test_integration_guidance_uses_logical_atlas_contract_language():
    content = (PROJECT_ROOT / "src" / "specify_cli" / "integrations" / "base.py").read_text(encoding="utf-8").lower()
    assert "build-handbook.md" not in content
    assert "debug-handbook.md" not in content
    assert "runtime handbook contract" not in content
