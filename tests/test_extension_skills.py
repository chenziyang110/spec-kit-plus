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
    ExtensionManifest,
    ExtensionManager,
    ExtensionError,
)
from specify_cli import SKILL_DESCRIPTIONS


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
        assert (skills_dir / "sp-map-codebase" / "SKILL.md").exists()
        assert (skills_dir / "sp-test" / "SKILL.md").exists()
        assert (skills_dir / "sp-fast" / "SKILL.md").exists()
        assert (skills_dir / "sp-quick" / "SKILL.md").exists()
        assert (project_dir / ".specify" / "templates" / "context-template.md").exists()
        assert (project_dir / ".specify" / "templates" / "project-rules-template.md").exists()
        assert (project_dir / ".specify" / "templates" / "project-learnings-template.md").exists()
        assert (project_dir / ".specify" / "templates" / "testing" / "testing-contract-template.md").exists()
        assert (project_dir / ".specify" / "templates" / "testing" / "testing-playbook-template.md").exists()
        assert (project_dir / ".specify" / "templates" / "testing" / "coverage-baseline-template.json").exists()

        for skill_name in ("sp-specify", "sp-deep-research", "sp-plan", "sp-test", "sp-implement", "sp-debug", "sp-fast", "sp-quick"):
            body = _body_without_frontmatter(skills_dir / skill_name / "SKILL.md").lower()
            assert ".specify/memory/project-rules.md" in body
            assert ".specify/memory/project-learnings.md" in body
            assert ".planning/learnings/candidates.md" in body
            assert "workflow contract summary" in body
            assert "routing metadata only" in body
        constitution_body = _body_without_frontmatter(skills_dir / "sp-constitution" / "SKILL.md").lower()
        assert ".specify/memory/project-rules.md" in constitution_body
        assert ".specify/memory/project-learnings.md" in constitution_body
        assert ".planning/learnings/candidates.md" in constitution_body
        assert "specify learning start --command constitution --format json" in constitution_body
        assert "project-handbook.md" in constitution_body
        assert ".specify/project-map/index/status.json" in constitution_body
        assert "/sp-map-codebase" in constitution_body
        assert "workflow-state.md" in constitution_body
        assert "/sp-plan" in constitution_body
        assert "/sp-tasks" in constitution_body
        assert "/sp-analyze" in constitution_body
        assert (project_dir / ".specify" / "templates" / "references-template.md").exists()
        assert "clarify" in result.output.lower()

        explain_body = _body_without_frontmatter(skills_dir / "sp-explain" / "SKILL.md")
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
        assert "single-lane" in explain_body.lower()
        assert "supporting artifact cross-check" in explain_body.lower()
        assert "before rendering the final explanation" in explain_body.lower()

        specify_body = _body_without_frontmatter(skills_dir / "sp-specify" / "SKILL.md")
        specify_outline = _extract_section(specify_body, "Outline")
        assert "open question block" in specify_outline.lower()
        assert "native structured question tool" in specify_body.lower()
        assert "fallback-only text format guidance" in specify_body.lower()
        assert "if a native structured question tool is available, you must use it" in specify_body.lower()
        assert "do not render the textual fallback block when the native tool is available" in specify_body.lower()
        assert "do not self-authorize textual fallback because the question seems simple" in specify_body.lower()
        assert "only fall back after the native tool is unavailable or the tool call fails" in specify_body.lower()
        _assert_terms_in_order(
            specify_outline,
            "Stage header",
            "Question header",
            "Prompt",
            "Recommendation",
            "Options",
            "Reply instruction",
        )
        assert "/sp.plan" in specify_body
        assert "guided requirement discovery" in specify_body.lower()
        assert "current-understanding or confirmation gate" in specify_body.lower()
        assert "planning-relevant gray areas" in specify_body.lower()
        assert "PROJECT-HANDBOOK.md" in specify_body
        assert ".specify/project-map/root/ARCHITECTURE.md" in specify_body
        assert ".specify/project-map/root/WORKFLOWS.md" in specify_body
        assert "Topic Map" in specify_body
        assert "coverage-model check" in specify_body
        assert "truth-owning surfaces" in specify_body
        assert "change-propagation hotspots" in specify_body
        assert "verification entry points" in specify_body
        assert "known unknowns relevant to the request" in specify_body
        assert "module ownership, reusable components/services/hooks, integration points" in specify_body
        assert "workflow-state.md" in specify_body
        assert "Read `.specify/templates/workflow-state-template.md`." in specify_body
        assert "Create or resume `WORKFLOW_STATE_FILE` immediately after `FEATURE_DIR` is known." in specify_body
        assert "phase_mode: planning-only" in specify_body
        assert "Do not implement code, edit source files, edit tests, or run implementation-oriented fix loops from `sp-specify`." in specify_body
        assert "If the topical coverage for the touched area is missing, stale, or too broad" in specify_body
        assert "Run a codebase scout before clarification." in specify_body
        assert "Build a concise internal scout summary for the request area" in specify_body
        assert "truth-owning surfaces and shared coordination surfaces" in specify_body
        assert "change-propagation hotspots, consumer surfaces, and neighboring surfaces likely to require review" in specify_body
        assert "verification entry points and regression-sensitive checks" in specify_body
        assert "known unknowns, stale evidence boundaries, or observability gaps" in specify_body
        assert "grounded in the project handbook and touched-area topical map" in specify_body
        assert "Do not use generic labels like \"UX\", \"behavior\", or \"data handling\"" in specify_body
        assert "Each gray area should be captured internally with:" in specify_body
        assert "desired happy-path behavior" in specify_body
        assert "edge case or failure-path behavior" in specify_body
        assert "compatibility, migration, or neighboring-workflow impact" in specify_body
        assert "Use code-aware follow-ups when possible" in specify_body
        assert "Apply a specificity test before leaving a gray area" in specify_body
        assert "Do not leave a gray area merely because the user expressed a preference" in specify_body
        assert "default minimum depth as: happy path, failure path, compatibility impact, and acceptance proof" in specify_body
        assert "context.md" in specify_body
        assert "Write `context.md` to `CONTEXT_FILE`." in specify_body
        assert "Locked decisions are preserved in context.md" in specify_body
        assert "recommend `/sp.clarify` as the next command instead of `/sp.plan`" in specify_body
        assert "recommended review follow-up: `/sp.clarify`" in specify_body
        assert "without needing `/sp.clarify`" in specify_body
        assert "mark `.specify/project-map/index/status.json` dirty" in specify_body.lower()
        assert "recommend `/sp-map-codebase`" in specify_body

        plan_body = _body_without_frontmatter(skills_dir / "sp-plan" / "SKILL.md")
        assert "Add `Implementation Constitution`" in plan_body
        assert "architecture invariants, boundary ownership, forbidden implementation drift" in plan_body
        assert "Promote framework and boundary rules from \"technical background\" into explicit implementation constraints" in plan_body
        assert "no locked planning decision or implementation constitution rule has been silently omitted" in plan_body
        assert "Promote framework and boundary rules from \"technical background\" into explicit implementation constraints" in plan_body
        assert "Dispatch Compilation Hints" in plan_body
        assert "workflow-state.md" in plan_body
        assert "phase_mode: design-only" in plan_body
        assert "Do not implement code, edit source files, edit tests, or treat planning as implicit permission to start execution." in plan_body
        assert "recommended follow-up quality check: `/sp.checklist`" in plan_body
        assert "mark `.specify/project-map/index/status.json` dirty" in plan_body.lower()
        assert "recommend `/sp-map-codebase`" in plan_body

        tasks_body = _body_without_frontmatter(skills_dir / "sp-tasks" / "SKILL.md")
        assert "Extract `Locked Planning Decisions`, `Implementation Constitution`" in tasks_body
        assert "boundary-defining references or forbidden drift" in tasks_body
        assert "implementation-guardrails phase before setup" in tasks_body
        assert "locked planning decision or implementation constitution rule" in tasks_body
        assert "Task Guardrail Index" in tasks_body
        assert "workflow-state.md" in tasks_body
        assert "phase_mode: task-generation-only" in tasks_body
        assert "Do not implement code, edit source files, edit tests, or treat task generation as permission to start execution." in tasks_body
        assert "whether or not `.specify/testing/testing_contract.md` exists" in tasks_body.lower()
        assert "behavior changes, bug fixes, and refactors" in tasks_body.lower()
        assert "add explicit bootstrap tasks to establish the smallest runnable test surface first" in tasks_body.lower()
        assert "recommended next command: `/sp.analyze`" in tasks_body.lower()
        assert "implementation remains blocked until `/sp-analyze`" in tasks_body.lower()
        assert "do not hand off directly to `/sp-implement` from `sp-tasks`" in tasks_body.lower()
        assert "mark `.specify/project-map/index/status.json` dirty" in tasks_body.lower()
        assert "recommend `/sp-map-codebase`" in tasks_body

        implement_body = _body_without_frontmatter(skills_dir / "sp-implement" / "SKILL.md")
        assert "Extract `Implementation Constitution` from `plan.md`" in implement_body
        assert "What framework or boundary pattern owns the touched surface?" in implement_body
        assert "Which files define the existing pattern that must be preserved?" in implement_body
        assert "What implementation drift is forbidden for this batch?" in implement_body
        assert "**Boundary-pattern preservation**" in implement_body
        assert "compile and validate the packet before any delegated work begins" in implement_body
        assert "validated `workertaskpacket`" in implement_body.lower()
        assert "must not dispatch from raw task text alone" in implement_body.lower()
        assert "write the failing test first for every behavior-changing task, bug fix, or refactor" in implement_body.lower()
        assert "do not write production code for the batch until the red state is verified" in implement_body.lower()
        assert "if `workflow_state_file` still points to `/sp.analyze`" in implement_body.lower()
        assert "do not self-authorize an `/sp-implement` start from chat memory alone" in implement_body.lower()

        analyze_body = _body_without_frontmatter(skills_dir / "sp-analyze" / "SKILL.md")
        assert "Boundary Guardrail Gaps" in analyze_body
        assert "BG1" in analyze_body
        assert "BG2" in analyze_body
        assert "BG3" in analyze_body
        assert "DP1" in analyze_body
        assert "DP2" in analyze_body
        assert "DP3" in analyze_body
        assert "Boundary Guardrail Table" in analyze_body
        assert "Boundary Guardrail Gap Count" in analyze_body
        assert "If a `Boundary Guardrail Gap` exists" in analyze_body
        assert "Closed-loop requirement" in analyze_body
        assert "Recommended Re-entry" in analyze_body
        assert "This command does not edit `spec.md`, `context.md`, `plan.md`, or `tasks.md`." in analyze_body
        assert "this command may update `workflow-state.md` to record the cleared or blocked gate result" in analyze_body.lower()
        assert "analysis-only" in analyze_body.lower()
        assert "`next_command: /sp.implement`" in analyze_body
        assert "If the highest-impact issue lives in `spec.md` or `context.md`" in analyze_body
        assert "If analysis runs after `/sp-implement` has already started or finished" in analyze_body
        assert "exact workflow re-entry path" in analyze_body

        map_body = _body_without_frontmatter(skills_dir / "sp-map-codebase" / "SKILL.md")
        assert "PROJECT-HANDBOOK.md" in map_body
        assert ".specify/project-map/index/atlas-index.json" in map_body
        assert ".specify/project-map/root/ARCHITECTURE.md" in map_body
        assert ".specify/project-map/modules/<module-id>/OVERVIEW.md" in map_body
        assert 'choose_execution_strategy(command_name="map-codebase"' in map_body
        assert "run `/sp-map-codebase`" in map_body
        assert "complete-refresh" in map_body
        assert "do not create `.planning/codebase/`" in map_body
        assert "Layering exists so map consumers can read detail on demand" in map_body
        assert "Do not treat layering as permission to discard technical detail." in map_body
        assert "deep_stale" in map_body
        assert "external or exported API contracts" in map_body
        assert "core data models, state semantics, and handoff fields" in map_body
        assert "IPC, bridge, native-host, message, pipe, or protocol seams" in map_body
        assert "`PROJECT-HANDBOOK.md` must stay concise and index-first" in map_body
        assert "macro scan and architecture identification" in map_body.lower()
        assert "directory structure deep analysis" in map_body.lower()
        assert "dependency relationships and module analysis" in map_body.lower()
        assert "core code element review" in map_body.lower()
        assert "data flow and api surface mapping" in map_body.lower()
        assert "patterns and conventions synthesis" in map_body.lower()
        assert "the generated navigation system should collectively cover the equivalent of these seven technical-document chapters" in map_body.lower()

        test_body = _body_without_frontmatter(skills_dir / "sp-test" / "SKILL.md")
        assert ".specify/testing/TESTING_CONTRACT.md" in test_body
        assert ".specify/testing/TESTING_PLAYBOOK.md" in test_body
        assert ".specify/testing/COVERAGE_BASELINE.json" in test_body
        assert "audit-only" in test_body.lower()
        assert "bootstrap" in test_body.lower()
        assert "refresh" in test_body.lower()
        assert ".specify/templates/passive-skills/*-testing/" in test_body.lower()
        assert 'choose_execution_strategy(command_name="test"' in test_body.lower()
        assert "single-lane" in test_body.lower()
        assert "native-multi-agent" in test_body.lower()
        assert "sidecar-runtime" in test_body.lower()
        assert "before mutating shared repository test framework/config files" in test_body.lower()
        assert "if `project-handbook.md` or the required `.specify/project-map/` files are missing, run `/sp-map-codebase` before continuing" in test_body.lower()
        assert "if testing-surface coverage is insufficient for the current repository, run `/sp-map-codebase` before continuing" in test_body.lower()
        assert "read `project-handbook.md`." in test_body.lower()
        assert "classify the next workflow recommendation before the final report" in test_body.lower()
        assert "recommend exactly one next command" in test_body.lower()
        assert "recommend `/sp-quick`" in test_body.lower()
        assert "recommend `/sp-specify`" in test_body.lower()
        assert "recommend `/sp-debug`" in test_body.lower()
        assert "resume `/sp-implement`" in test_body.lower()
        assert "manually execute the canonical test commands" in test_body.lower()
        assert "most recent manual validation run" in test_body.lower()
        assert "run coverage after the first meaningful test pass" in test_body.lower()
        assert "iterate on uncovered critical paths" in test_body.lower()

        fast_body = _body_without_frontmatter(skills_dir / "sp-fast" / "SKILL.md")
        assert "write a failing targeted test or failing repro check before editing production code" in fast_body.lower()
        assert "do not use manual sanity checks as a substitute for red" in fast_body.lower()
        assert "/sp-test" in fast_body.lower()
        assert "/sp-debug" in fast_body.lower()
        assert "root cause is still unknown" in fast_body.lower() or "root cause is not yet known" in fast_body.lower()

        quick_body = _body_without_frontmatter(skills_dir / "sp-quick" / "SKILL.md")
        assert "first executable lane must produce a failing automated test or failing repro check before production edits begin" in quick_body.lower()
        assert "do not write production code until the red state is captured" in quick_body.lower()
        assert "bootstrap the smallest viable test surface first" in quick_body.lower()
        assert "/sp-test" in quick_body.lower()
        assert "/sp-debug" in quick_body.lower()
        assert "root cause is still unknown" in quick_body.lower() or "root cause is not yet known" in quick_body.lower()
        assert "surface-only" in quick_body.lower() or "symptom-only" in quick_body.lower()

        checklist_body = _body_without_frontmatter(skills_dir / "sp-checklist" / "SKILL.md")
        checklist_lower = checklist_body.lower()
        assert ".specify/memory/constitution.md" in checklist_lower
        assert ".specify/memory/project-rules.md" in checklist_lower
        assert ".specify/memory/project-learnings.md" in checklist_lower
        assert ".planning/learnings/candidates.md" in checklist_lower
        assert "specify learning start --command checklist --format json" in checklist_lower
        assert "specify learning capture --command checklist" in checklist_lower
        assert "project-handbook.md" in checklist_lower
        assert ".specify/project-map/index/status.json" in checklist_lower
        assert "run `/sp-map-codebase` before continuing" in checklist_lower
        assert "recommend `/sp-specify`" in checklist_lower or "recommend `/sp.specify`" in checklist_lower
        assert "recommend `/sp-plan`" in checklist_lower
        assert "recommend `/sp-analyze`" in checklist_lower

        debug_body = _body_without_frontmatter(skills_dir / "sp-debug" / "SKILL.md")
        debug_lower = debug_body.lower()
        assert "observer framing" in debug_lower
        assert "compressed observer framing" in debug_lower
        assert "full observer framing" in debug_lower
        assert "do not read source files" in debug_lower
        assert "do not inspect logs" in debug_lower
        assert "do not read test files" in debug_lower
        assert "primary suspected loop" in debug_lower
        assert "alternative cause candidates" in debug_lower
        assert "transition memo" in debug_lower
        assert "automatically continue into evidence investigation" in debug_lower
        assert "write a failing automated repro test before changing production code" in debug_lower
        assert "do not modify production behavior until the red state is proven" in debug_lower
        assert "add the missing harness first or route through `/sp-test`" in debug_lower
        assert "alternative_hypotheses_considered" in debug_lower
        assert "alternative_hypotheses_ruled_out" in debug_lower
        assert "root_cause_confidence" in debug_lower
        assert "fix_scope" in debug_lower
        assert "loop_restoration_proof" in debug_lower
        assert "surface-only" in debug_lower


class TestSkillDescriptions:
    """Built-in command descriptions should stay aligned with bundled templates."""

    def test_skill_descriptions_include_new_surfaces(self):
        for name, description in SKILL_DESCRIPTIONS.items():
            assert description.startswith("Use when"), f"{name} description should be trigger-oriented"

        assert "guided requirement discovery" in SKILL_DESCRIPTIONS["specify"].lower()
        assert "planning-ready specification package" in SKILL_DESCRIPTIONS["specify"].lower()
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
        assert "testing system" in SKILL_DESCRIPTIONS["test"].lower()
        assert "truly trivial" in SKILL_DESCRIPTIONS["fast"].lower()
        assert "lightweight tracked planning" in SKILL_DESCRIPTIONS["quick"].lower()
        assert "handbook/project-map coverage" in SKILL_DESCRIPTIONS["map-codebase"].lower()
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

class TestExtensionSkillRegistration:
    """Test _register_extension_skills() on ExtensionManager."""

    def test_skills_created_when_ai_skills_active(self, skills_project, extension_dir):
        """Skills should be created when ai_skills is enabled."""
        project_dir, skills_dir = skills_project
        manager = ExtensionManager(project_dir)
        manifest = manager.install_from_directory(
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
        assert parsed["disable-model-invocation"] is True

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
        manifest = manager.install_from_directory(
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
        manifest = manager.install_from_directory(
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
        manifest_a = manager.install_from_directory(
            ext_dir_a, "0.1.0", register_commands=False
        )
        manifest_b = manager.install_from_directory(
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
        manifest = manager.install_from_directory(
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
