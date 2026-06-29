"""Reusable test mixin for standard SkillsIntegration subclasses.

Each per-agent test file sets ``KEY``, ``FOLDER``, ``COMMANDS_SUBDIR``,
``REGISTRAR_DIR``, and ``CONTEXT_FILE``, then inherits all verification
logic from ``SkillsIntegrationTests``.

Mirrors ``MarkdownIntegrationTests`` / ``TomlIntegrationTests`` closely,
adapted for the ``sp-<name>/SKILL.md`` skills layout.
"""

import os

import yaml

from specify_cli.integrations import INTEGRATION_REGISTRY, get_integration
from specify_cli.integrations.base import SkillsIntegration
from specify_cli.integrations.codex import CodexIntegration
from specify_cli.integrations.manifest import IntegrationManifest
from .test_base import _assert_canonical_cognition_intake_contract

SPEC_KIT_BLOCK_START = "<!-- SPEC-KIT:BEGIN -->"
SHARED_PRD_HELPER = ".specify/scripts/shared/prd-state.py"
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


def _extract_generated_cognition_policy(content: str) -> str:
    lines = content.splitlines()
    selected: set[int] = set()
    needles = (
        "project cognition",
        "map-update",
        "map-scan",
        "map-build",
        "needs_rebuild",
        "needs_update",
        "reference",
        "path_index",
    )
    for index, line in enumerate(lines):
        lowered = line.lower()
        if any(needle in lowered for needle in needles):
            start = max(0, index - 3)
            end = min(len(lines), index + 4)
            selected.update(range(start, end))
    return "\n".join(lines[index] for index in sorted(selected)).lower()


def _assert_compact_managed_context(content: str) -> None:
    lower = content.lower()

    assert SPEC_KIT_BLOCK_START in content
    assert "[AGENT]" in content
    assert "## Always-On Context" in content
    assert "project cognition and project memory are always available" in lower
    assert "even without an active `sp-*` workflow" in lower
    assert "when existing-system truth matters" in lower
    assert "before broad source inspection" in lower
    assert "narrow live reads" in lower
    assert ".specify/memory/project-rules.md" in content
    assert ".specify/memory/learnings/INDEX.md" in content
    assert "## Workflow Recommendations" in content
    assert "do not auto-enter an `sp-*` workflow" in lower
    assert "recommend `sp-discussion`" in lower
    assert "`sp-specify` for formal alignment" in lower
    assert "`sp-deep-research` for feasibility proof" in lower
    assert "`sp-debug` for root-cause diagnosis" in lower
    assert "## Command Surface Rules" in content
    assert "specify --help" in content
    assert "generated create-feature script" in lower
    assert "## Durable State" in content
    assert "prefer durable workflow state and explicit feature paths" in lower
    assert "project cognition freshness truthful" in lower
    assert "store reusable lessons in project memory" in lower

    assert "## Workflow Activation Discipline" not in content
    assert "1% chance" not in content
    assert "## Workflow Routing" not in content
    assert "## Artifact Priority" not in content
    assert "## Brownfield Context Gate" not in content
    assert "## Project Cognition Usage" not in content
    assert "## Map Maintenance" not in content
    assert "sp-fast" not in lower
    assert "sp-quick" not in lower
    assert "sp-test-scan" not in lower
    assert "sp-test-build" not in lower


def test_generated_specify_skill_teaches_simplified_specify_contract(tmp_path):
    target = tmp_path / "codex-skill"
    integration = CodexIntegration()
    manifest = IntegrationManifest("codex", target)
    integration.setup(target, manifest)
    skill = target / ".codex" / "skills" / "sp-specify" / "SKILL.md"
    content = skill.read_text(encoding="utf-8").lower()
    assert "explore project context" in content
    assert "one high-impact question at a time" in content
    assert "two or three approaches" in content or "2-3 approaches" in content
    assert "semantic term" in content
    assert "source_signal_disposition" in content
    assert "handoff-ready" in content
    assert "quality_gate.status: user_confirmed" in content
    assert "planning_gate_status: ready" in content
    assert "derive the feature description" in content
    assert "do not pass the raw handoff" in content
    assert "discussion-log.md" in content
    assert "requirements.md" in content
    assert "open-questions.md" in content
    assert "facts-lock" not in content
    assert "route-lock" not in content
    assert "intent-lock" not in content
    assert "complexity-lock" not in content


def _assert_discussion_contract(skill_content: str) -> None:
    skill_lower = skill_content.lower()

    assert "sp-discussion" in skill_content
    assert ".specify/discussions/<slug>/" in skill_content
    assert "discussion-state.md" in skill_content
    assert "handoff-assessment.md" in skill_content
    assert "Turn Classifier" in skill_content
    assert "Question Evidence Gate" in skill_content
    assert "Cognition Advisory, Code Authority" in skill_content
    assert "project-cognition compass --intent discussion" in skill_content
    assert "project-cognition query --query-plan" in skill_content
    assert "only when `compass_state`, coverage diagnostics, localization, or live evidence requires explicit concept decisions" in skill_content
    assert "project-cognition query --intent plan" not in skill_content
    assert "ordinary turns do not write local files by default" in skill_lower
    assert "deferred persistence" in skill_lower
    assert "compaction preserve" in skill_lower
    assert "user-triggered save" in skill_lower
    assert "five-turn" in skill_lower
    assert "semantic checkpoints" in skill_lower
    assert "draft pair" in skill_lower
    assert "truth pass" in skill_lower
    assert "verified_project_facts" in skill_content
    assert "open_assumptions" in skill_content
    assert "evidence_checked" in skill_content
    assert "advice_confidence" in skill_content
    assert "high-throughput collaborative brief" in skill_lower
    assert "frontstage / backstage separation" in skill_lower
    assert "visible conversation" in skill_lower
    assert "state accounting backstage" in skill_lower
    assert "continue by default" in skill_lower
    assert "do not ask for continuation" in skill_lower
    assert "do not persist every turn" in skill_lower
    assert "checkpoint persistence" in skill_lower
    assert "surface file paths and state updates only" in skill_lower
    assert "discussion compass" in skill_lower
    assert "anti-toothpaste" in skill_lower
    assert "ask only when user judgment is genuinely required" in skill_lower
    assert "Context Boundary Gate" in skill_content
    assert "target project root" in skill_lower
    assert "adaptive question pack" in skill_lower
    assert "primary question" in skill_lower
    assert "optional follow-up" in skill_lower
    assert "recommended option" in skill_lower
    assert "adaptive reply contract" in skill_lower
    assert "reply_shape_id" not in skill_content
    assert "unified frontstage contract" in skill_lower
    assert "do not choose among named answer templates" in skill_lower
    assert "agent controls heading names" in skill_lower
    assert "discussion responsibility boundary" in skill_lower
    assert "does not own implementation planning" in skill_lower
    assert "do not split the work into p0/p1/p2" in skill_lower
    assert "migration phases" in skill_lower
    assert "task packets" in skill_lower
    assert "those belong to `sp-plan`, `sp-tasks`, or `sp-implement`" in skill_lower
    assert "no parallel old-backend operation" in skill_lower
    assert "no old-stack cutover fallback" in skill_lower
    assert "no alternate product path" in skill_lower
    assert "database snapshots" in skill_lower
    assert "data-safety mechanisms" in skill_lower
    assert "downstream planning and implementation safety constraints" in skill_lower
    assert "handoff request-changes repair" in skill_lower
    assert "blocked_by_handoff_integrity" in skill_content
    assert "the repair belongs to `sp-discussion`" in skill_lower
    assert "refresh `handoff-to-specify.md` and `handoff-to-specify.json` together" in skill_lower
    assert "source_handoff_json" in skill_content
    assert "source_files_read" in skill_content
    assert "handoff_status" in skill_content
    assert "handoff-review" in skill_content
    assert "recommendation-first is not questionless" in skill_lower
    assert "one unified" in skill_lower or "single unified" in skill_lower
    assert "discussion_requirement_contract" in skill_content
    assert "Agent-Facing Requirement Contract" in skill_content
    assert "consumer_eligibility" in skill_content
    assert "recommended_consumer" in skill_content
    assert "quick_task_candidate" in skill_content
    assert "Do not describe current execution or implementation progress" in skill_content
    assert "handoff-to-specify.md" in skill_content
    assert "handoff-to-specify.json" in skill_content
    assert "Handoff Reviewer Guide" in skill_content
    assert "Approve only if" in skill_content
    assert "Request changes if" in skill_content
    assert "does not know Spec Kit internals" in skill_content
    assert "quality_gate" in skill_content
    assert "user confirmation" in skill_lower
    assert "Must-Preserve Ledger" in skill_content
    assert "discussion_decision_digest" in skill_content
    assert "locked_direction" in skill_content
    assert "rejected_alternatives" in skill_content
    assert "accepted_tradeoffs" in skill_content
    assert "experience_commitments" in skill_content
    assert "review_criteria_carried_forward" in skill_content
    assert "must_not_dilute" in skill_content
    assert "handoff-ready closeout" in skill_lower
    assert "selected direction" in skill_lower
    assert "target boundary" in skill_lower
    assert "Must-Preserve coverage" in skill_content
    assert "package paths" in skill_lower
    assert "next consumption path" in skill_lower
    assert "do not close with only file paths, status counters, or a next command" in skill_lower
    assert "keep ready-summary quality checks internal" in skill_lower
    assert "coverage_status" in skill_content
    assert "planning_gate_status" in skill_content
    assert (
        "explicit user" in skill_lower
        or "user explicitly" in skill_lower
        or "explicit-user-request" in skill_lower
    )
    assert "senior technical expert" in skill_lower
    assert "senior product manager" in skill_lower
    assert "senior consequence analysis gate" in skill_lower
    assert "affected object map" in skill_lower
    assert "state-behavior matrix" in skill_lower
    assert "split-plan.md" not in skill_content
    assert "handoffs/<candidate_id>" not in skill_content
    assert "CAND-001" not in skill_content


def _assert_ask_contract(content: str) -> None:
    lowered = content.lower()

    assert "sp-ask" in content
    assert "Evidence-Backed Project Q&A" in content
    assert "project-cognition compass --intent ask" in content
    assert "project-cognition query --intent ask" in content
    assert "project cognition provides advisory navigation" in lowered
    assert "live evidence is authoritative" in lowered
    assert "do not create `.specify/ask/`" in lowered
    assert "do not write handoff" in lowered
    assert "do not edit source files" in lowered
    assert "do not run tests" in lowered
    assert "do not run builds" in lowered
    assert "do not run package managers" in lowered
    assert "do not execute project cli" in lowered
    assert "answer first" in lowered
    assert "next step" in lowered
    assert "discussion-state.md" not in content
    assert "handoff-to-specify" not in content


def _assert_runtime_cognition_carry_forward(content: str, command_name: str) -> None:
    advisory_index = content.find("project cognition advisory gate")
    assert advisory_index != -1
    assert "carry forward" in content
    assert "next workflow artifact or execution state" in content
    assert "mutation closeout" in content
    assert "workflow-owned mutation closeout is not an external map-maintenance handoff" in content
    assert "inline project cognition update" in content
    assert "project-cognition delta append" in content
    assert "project-cognition update --delta-session" in content
    assert "project-cognition update --payload-file" in content
    assert "verification_evidence" in content
    assert "generated_surface_notes" in content
    assert "result_state" in content
    assert "update_id" in content
    assert "clean closeout" in content
    assert "not `update_id`, `last_update_id`, or freshness alone" in content
    assert "recorded-only output" in content
    assert "project-cognition update --changed-path" not in content
    assert "sp-map-update is for manual/external maintenance and follow-up repair" in content
    assert "actual `{{invoke:map-update}}` refresh" not in content
    assert "project_cognition_refresh` recommending" not in content
    assert "project_cognition_refresh recommending" not in content
    assert "recommends `{{invoke:map-update}}` as follow-up map maintenance" not in content
    assert "recommended `{{invoke:map-update}}` refresh when applicable" not in content

    if command_name == "implement":
        orchestration_index = content.find("## orchestration model")
        if orchestration_index != -1:
            assert advisory_index < orchestration_index
        assert "implement-tracker.md" in content
        assert "workertaskpacket" in content
    elif command_name == "quick":
        assert "status.md" in content
    elif command_name == "debug":
        assert "debug session state" in content


def _assert_embedded_implement_review_contract(content: str) -> None:
    lowered = content.lower()

    assert "embedded implement review" in lowered
    assert "pre-implement review" in lowered
    assert "join-point drift review" in lowered
    assert "sequential review window" in lowered
    assert "review_window_policy" in content
    assert "implementation-review/reviews.ndjson" in content
    assert "implementation-review/repairs.ndjson" in content
    assert "/sp.review" not in content
    assert "sp-review" not in content



SKILLS_INTEGRATION_SAMPLE_KEYS = ("codex", "agy", "vibe")


def test_collected_skills_integrations_preserve_shared_discussion_contracts(tmp_path):
    for integration_key in SKILLS_INTEGRATION_SAMPLE_KEYS:
        project = tmp_path / integration_key
        integration = get_integration(integration_key)
        manifest = IntegrationManifest(integration_key, project)
        integration.setup(project, manifest)

        generated = "\n".join(
            path.read_text(encoding="utf-8").lower()
            for path in integration.skills_dest(project).glob("**/SKILL.md")
        )

        assert "senior consequence analysis gate" in generated, integration_key
        assert "affected object map" in generated, integration_key
        assert "state-behavior matrix" in generated, integration_key
        assert "dependency impact table" in generated, integration_key
        assert "ca-###" in generated, integration_key
        _assert_canonical_cognition_intake_contract(generated)

        discussion_path = integration.skills_dest(project) / "sp-discussion" / "SKILL.md"
        assert discussion_path.exists(), integration_key
        _assert_discussion_contract(discussion_path.read_text(encoding="utf-8"))


def test_collected_skills_integrations_preserve_ask_contract(tmp_path):
    for integration_key in INTEGRATION_REGISTRY:
        integration = get_integration(integration_key)
        if not isinstance(integration, SkillsIntegration):
            continue

        project = tmp_path / integration_key
        manifest = IntegrationManifest(integration_key, project)
        integration.setup(project, manifest)

        ask_path = integration.skills_dest(project) / "sp-ask" / "SKILL.md"
        assert ask_path.exists(), integration_key
        _assert_ask_contract(ask_path.read_text(encoding="utf-8"))


def test_collected_skills_integrations_embed_internal_implement_review_loop(tmp_path):
    for integration_key in SKILLS_INTEGRATION_SAMPLE_KEYS:
        project = tmp_path / integration_key
        integration = get_integration(integration_key)
        manifest = IntegrationManifest(integration_key, project)
        integration.setup(project, manifest)

        implement_path = integration.skills_dest(project) / "sp-implement" / "SKILL.md"
        assert implement_path.exists(), integration_key
        _assert_embedded_implement_review_contract(implement_path.read_text(encoding="utf-8"))


def test_generated_planning_skills_require_inline_cognition_update_for_source_changes(tmp_path):
    for integration_key in SKILLS_INTEGRATION_SAMPLE_KEYS:
        project = tmp_path / integration_key
        integration = get_integration(integration_key)
        manifest = IntegrationManifest(integration_key, project)
        integration.setup(project, manifest)

        for skill_name in ("sp-specify", "sp-plan", "sp-tasks"):
            content = (
                integration.skills_dest(project) / skill_name / "SKILL.md"
            ).read_text(encoding="utf-8").lower()
            assert "artifact-only" in content
            assert "do not call `project-cognition mark-dirty`" in content
            assert (
                "if this planning workflow makes actual source/runtime/template/config/test/generated-asset changes"
                in content
            )
            assert "run inline project cognition update" in content
            assert "sp-map-update is for manual/external maintenance" in content


class SkillsIntegrationTests:
    """Mixin — set class-level constants and inherit these tests.

    Required class attrs on subclass::

        KEY: str              — integration registry key
        FOLDER: str           — e.g. ".agents/"
        COMMANDS_SUBDIR: str  — e.g. "skills"
        REGISTRAR_DIR: str    — e.g. ".agents/skills"
        CONTEXT_FILE: str     — e.g. "AGENTS.md"
    """

    KEY: str
    FOLDER: str
    COMMANDS_SUBDIR: str
    REGISTRAR_DIR: str
    CONTEXT_FILE: str

    # -- Registration -----------------------------------------------------

    def test_registered(self):
        assert self.KEY in INTEGRATION_REGISTRY
        assert get_integration(self.KEY) is not None

    def test_generated_skills_do_not_include_obsolete_cognition_addenda(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)

        skills_dir = i.skills_dest(tmp_path)
        generated = "\n".join(path.read_text(encoding="utf-8").lower() for path in skills_dir.glob("**/SKILL.md"))
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

    def test_generated_project_cognition_gate_reference_refresh_uses_closed_conditions(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)

        skill = i.skills_dest(tmp_path) / "spec-kit-project-cognition-gate" / "SKILL.md"
        content = " ".join(skill.read_text(encoding="utf-8").lower().replace("`", "").split())

        assert "for blocked, stale, or incomplete references" in content
        assert "fall back to minimal live reads" in content
        assert "map-update" in content
        assert "localized stale coverage" in content
        assert "weak reference coverage" in content
        assert "external/manual changed-path map maintenance" in content
        assert "ordinary existing-baseline gaps after a usable reference baseline" in content
        assert "for missing or unusable reference baselines" in content
        assert "map-scan" in content
        assert "map-build" in content
        assert "reference project only for first/missing/unusable baseline" in content
        for condition in (
            "schema failure",
            "zero active-generation path_index rows",
            "explicit_rebuild_requested",
            "baseline_identity_invalid",
        ):
            assert condition in content

        assert "ordinary changed-path maintenance" not in content
        for phrase in STALE_COGNITION_ADDENDUM_PHRASES:
            assert phrase not in content

    def test_runtime_commands_hard_gate_project_cognition_reads(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)

        skills_dir = i.skills_dest(tmp_path)
        for name in ("implement", "debug", "quick"):
            content = (skills_dir / f"sp-{name}" / "SKILL.md").read_text(encoding="utf-8").lower()

            assert "advisory gate" in content
            assert "project cognition" in content
            assert "project-cognition query" in content
            assert "alias catalog" in content
            assert "semantic_intake" in content
            assert "facet coverage" in content
            assert "concept_decisions" in content
            assert "lexicon_generation_id" in content
            assert "minimal_live_reads" in content
            assert "returned map terms" not in content
            assert "map-scan" in content
            assert "map-build" in content
            _assert_runtime_cognition_carry_forward(content, name)
            if name == "debug":
                assert "project-cognition query --query-plan" in content
                assert "debug-handbook.md" not in content
            else:
                assert "build-handbook.md" not in content
                assert "map-update" in content

    def test_is_skills_integration(self):
        assert isinstance(get_integration(self.KEY), SkillsIntegration)

    # -- Config -----------------------------------------------------------

    def test_config_folder(self):
        i = get_integration(self.KEY)
        assert i.config["folder"] == self.FOLDER

    def test_config_commands_subdir(self):
        i = get_integration(self.KEY)
        assert i.config["commands_subdir"] == self.COMMANDS_SUBDIR

    def test_registrar_config(self):
        i = get_integration(self.KEY)
        assert i.registrar_config["dir"] == self.REGISTRAR_DIR
        assert i.registrar_config["format"] == "markdown"
        assert i.registrar_config["args"] == "$ARGUMENTS"
        assert i.registrar_config["extension"] == "/SKILL.md"

    def test_context_file(self):
        i = get_integration(self.KEY)
        assert i.context_file == self.CONTEXT_FILE

    # -- Setup / teardown -------------------------------------------------

    def test_setup_creates_files(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.setup(tmp_path, m)
        assert len(created) > 0
        skills_dir = i.skills_dest(tmp_path).resolve()
        expected_skill_dirs = {
            *(f"sp-{command}" for command in self._skill_commands()),
            *self._passive_skill_names(),
        }
        generated_files = [f for f in created if "scripts" not in f.parts]
        skill_manifests = [f for f in generated_files if f.name == "SKILL.md"]

        assert skill_manifests, "No generated SKILL.md files were created"
        for f in generated_files:
            assert f.exists()
            rel = f.resolve().relative_to(skills_dir)
            assert rel.parts[0] in expected_skill_dirs
        for f in skill_manifests:
            assert f.parent.name in expected_skill_dirs

    def test_setup_writes_to_correct_directory(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.setup(tmp_path, m)
        expected_dir = i.skills_dest(tmp_path)
        assert expected_dir.exists(), f"Expected directory {expected_dir} was not created"
        expected_skill_dirs = {
            *(f"sp-{command}" for command in self._skill_commands()),
            *self._passive_skill_names(),
        }
        generated_files = [f for f in created if "scripts" not in f.parts]
        skill_manifests = [f for f in generated_files if f.name == "SKILL.md"]
        assert len(skill_manifests) > 0, "No skill files were created"
        for f in generated_files:
            rel = f.resolve().relative_to(expected_dir.resolve())
            assert rel.parts[0] in expected_skill_dirs, f"{f} is not under {expected_dir}"

    def test_skill_directory_structure(self, tmp_path):
        """Commands and passive skills produce their expected skill directories."""
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.setup(tmp_path, m)
        skill_files = [f for f in created if f.name == "SKILL.md"]

        expected_commands = set(self._skill_commands())
        expected_passive_skills = set(self._passive_skill_names())

        # Derive command names from the skill directory names
        actual_commands = set()
        actual_passive_skills = set()
        for f in skill_files:
            skill_dir_name = f.parent.name
            if skill_dir_name.startswith("sp-"):
                actual_commands.add(skill_dir_name.removeprefix("sp-"))
            else:
                actual_passive_skills.add(skill_dir_name)

        assert actual_commands == expected_commands
        assert actual_passive_skills == expected_passive_skills

    def test_research_alias_skill_routes_to_deep_research(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)

        alias_path = i.skills_dest(tmp_path) / "sp-research" / "SKILL.md"
        assert alias_path.exists()
        content = alias_path.read_text(encoding="utf-8")
        lowered = content.lower()

        assert "name: \"sp-research\"" in content
        assert "compatibility alias" in lowered
        assert "sp-deep-research" in content
        assert "active_command: sp-deep-research" in content
        assert "active_command: sp-research" not in content

    def test_integrate_skill_is_generated(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)

        integrate_path = i.skills_dest(tmp_path) / "sp-integrate" / "SKILL.md"
        assert integrate_path.exists()
        content = integrate_path.read_text(encoding="utf-8").lower()
        assert "closeout" in content or "close out" in content
        assert "do not fold this workflow into `sp-implement`" in content

    def test_discussion_skill_preserves_pre_specification_contract(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)

        discussion_path = i.skills_dest(tmp_path) / "sp-discussion" / "SKILL.md"
        assert discussion_path.exists()
        _assert_discussion_contract(discussion_path.read_text(encoding="utf-8"))

    def test_ask_skill_preserves_read_only_qa_contract(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)

        ask_path = i.skills_dest(tmp_path) / "sp-ask" / "SKILL.md"
        assert ask_path.exists()
        _assert_ask_contract(ask_path.read_text(encoding="utf-8"))

    def test_specify_skill_preserves_discussion_fidelity_contract(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)

        content = (i.skills_dest(tmp_path) / "sp-specify" / "SKILL.md").read_text(encoding="utf-8")
        lowered = content.lower()

        assert "Must-Preserve Ledger" in content
        assert "coverage_status" in content
        assert "planning_gate_status" in content
        assert "entry_source: sp-discussion" in content
        assert "discussion-log.md" in content
        assert "requirements.md" in content
        assert "open-questions.md" in content
        assert "source_signal_disposition" in content
        assert "Discussion Decision Digest" in content
        assert "discussion_decision_digest" in content
        assert "review_criteria_carried_forward" in content
        assert "must_not_dilute" in content
        assert "source_files_read" in content
        assert "not only the handoff summary" in lowered
        assert "capability-like" in lowered
        assert "handoffs/<candidate_id>" not in content
        assert "do not silently" in lowered

    def test_generated_primary_workflows_include_consequence_gate(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)

        generated = "\n".join(
            path.read_text(encoding="utf-8").lower()
            for path in i.skills_dest(tmp_path).glob("**/SKILL.md")
        )

        assert "senior consequence analysis gate" in generated
        assert "affected object map" in generated
        assert "state-behavior matrix" in generated
        assert "dependency impact table" in generated
        assert "ca-###" in generated

    def test_passive_skills_use_distinct_non_sp_namespace(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.setup(tmp_path, m)
        passive_skill_files = [
            f for f in created if f.name == "SKILL.md" and not f.parent.name.startswith("sp-")
        ]

        assert passive_skill_files, "Expected at least one passive skill to be generated"
        for skill_file in passive_skill_files:
            content = skill_file.read_text(encoding="utf-8")
            parts = content.split("---", 2)
            fm = yaml.safe_load(parts[1])
            assert fm["name"] == skill_file.parent.name
            assert not fm["name"].startswith("sp-")
            assert fm["metadata"]["source"].startswith("templates/passive-skills/")

    def test_skill_frontmatter_structure(self, tmp_path):
        """SKILL.md must have name, description, compatibility, metadata."""
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.setup(tmp_path, m)
        skill_files = [f for f in created if f.name == "SKILL.md"]

        for f in skill_files:
            content = f.read_text(encoding="utf-8")
            assert content.startswith("---\n"), f"{f} missing frontmatter"
            parts = content.split("---", 2)
            fm = yaml.safe_load(parts[1])
            assert "name" in fm, f"{f} frontmatter missing 'name'"
            assert "description" in fm, f"{f} frontmatter missing 'description'"
            assert "compatibility" in fm, f"{f} frontmatter missing 'compatibility'"
            assert "metadata" in fm, f"{f} frontmatter missing 'metadata'"
            assert fm["metadata"]["author"] == "github-spec-kit"
            assert "source" in fm["metadata"]

    def test_skill_uses_template_descriptions(self, tmp_path):
        """SKILL.md should use the original template description for ZIP parity."""
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.setup(tmp_path, m)
        skill_files = [f for f in created if f.name == "SKILL.md"]

        for f in skill_files:
            content = f.read_text(encoding="utf-8")
            parts = content.split("---", 2)
            fm = yaml.safe_load(parts[1])
            # Description must be a non-empty string (from the template)
            assert isinstance(fm["description"], str)
            assert len(fm["description"]) > 0, f"{f} has empty description"

    def test_templates_are_processed(self, tmp_path):
        """Skill body must have placeholders replaced, not raw templates."""
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.setup(tmp_path, m)
        skill_files = [f for f in created if f.name == "SKILL.md"]
        assert len(skill_files) > 0
        for f in skill_files:
            content = f.read_text(encoding="utf-8")
            assert "{SCRIPT}" not in content, f"{f.name} has unprocessed {{SCRIPT}}"
            assert "__AGENT__" not in content, f"{f.name} has unprocessed __AGENT__"
            assert "{ARGS}" not in content, f"{f.name} has unprocessed {{ARGS}}"

    def test_feature_creation_surfaces_use_explicit_helper_paths_without_fake_cli(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)

        surfaces = [i.skills_dest(tmp_path) / "sp-specify" / "SKILL.md"]

        context_path = tmp_path / self.CONTEXT_FILE
        if context_path.exists():
            surfaces.append(context_path)

        routing_skill = i.skills_dest(tmp_path) / "spec-kit-workflow-routing" / "SKILL.md"
        if routing_skill.exists():
            surfaces.append(routing_skill)
            routing_content = routing_skill.read_text(encoding="utf-8").lower()
            assert "high-throughput senior product-engineering advisor" in routing_content
            assert "frontstage / backstage separation" in routing_content
            assert "does not persist every turn" in routing_content
            assert "continues by default" in routing_content
            assert "does not ask for continuation" in routing_content

        for path in surfaces:
            content = path.read_text(encoding="utf-8").lower()
            assert ".specify/scripts/bash/create-new-feature.sh" in content, f"{path} missing bash helper path"
            assert ".specify/scripts/powershell/create-new-feature.ps1" in content, f"{path} missing powershell helper path"
            assert "run `specify create-feature`" not in content, f"{path} teaches fake runnable create-feature command"
            assert "use `specify create-feature`" not in content, f"{path} teaches fake runnable create-feature command"

    def test_skill_body_has_content(self, tmp_path):
        """Each SKILL.md body should contain template content after the frontmatter."""
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.setup(tmp_path, m)
        skill_files = [f for f in created if f.name == "SKILL.md"]
        for f in skill_files:
            content = f.read_text(encoding="utf-8")
            # Body is everything after the second ---
            parts = content.split("---", 2)
            body = parts[2].strip() if len(parts) >= 3 else ""
            assert len(body) > 0, f"{f} has empty body"

    def test_implement_skill_has_shared_leader_gate(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)

        implement_path = i.skills_dest(tmp_path) / "sp-implement" / "SKILL.md"
        content = implement_path.read_text(encoding="utf-8")
        lowered = content.lower()

        assert "## Orchestration Model" in content
        assert "leader and orchestrator" in lowered
        assert "not the concrete implementer" in lowered
        assert "autonomous blocker recovery" in lowered
        assert "Dispatch `one-subagent` when one validated `WorkerTaskPacket` is ready" in content
        assert "dispatch `parallel-subagents` when multiple validated packets have isolated write sets" in content
        assert "delegation surface contract" in lowered
        assert "dispatch only from validated `workertaskpacket`" in lowered
        assert "must not edit implementation files directly while subagent execution is active" in lowered

    def test_runtime_skills_have_shared_subagent_dispatch_and_result_contracts(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)

        for name in ("implement", "debug", "quick"):
            content = (i.skills_dest(tmp_path) / f"sp-{name}" / "SKILL.md").read_text(encoding="utf-8").lower()
            assert "subagent dispatch contract" in content
            assert "subagent dispatch" in content
            assert "native subagent capability discovery" in content
            assert "do not record `subagent-blocked`" in content
            if name == "implement":
                assert "durable fallback decision" in content
                assert "dispatch fallback" not in content
                assert "actual_surface: leader-inline" not in content
            else:
                assert "fallback path" in content
            assert "subagent result contract" in content
            assert "result handoff path" in content
            assert "reported_status" in content
            assert "needs_context" in content

    def test_debug_and_quick_skills_have_shared_leader_and_routing_sections(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)
        agent_name = i.config["name"].replace(" CLI", "")

        debug_content = (i.skills_dest(tmp_path) / "sp-debug" / "SKILL.md").read_text(encoding="utf-8").lower()
        quick_content = (i.skills_dest(tmp_path) / "sp-quick" / "SKILL.md").read_text(encoding="utf-8").lower()

        assert f"## {agent_name} Leader Gate".lower() in debug_content
        assert "you are the **leader**, not a freeform debugger" in debug_content
        assert "investigation routing contract" in debug_content
        assert "execution_model: leader-inline | subagent-assisted | blocked" in debug_content
        assert "dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked" in debug_content
        assert "execution_surface: leader-inline | native-subagents | none" in debug_content
        assert "small focused investigation" in debug_content
        assert "subagent-assisted" in debug_content
        assert "debug understanding checkpoint" in debug_content
        assert "understanding_confirmed: true" in debug_content
        assert "debug checkpoint" in debug_content
        assert "first evidence action" in debug_content
        assert "<br>" not in debug_content
        assert "plain text for terminal output" in debug_content
        assert "resolve discussion handoff intake before quick-task execution" in quick_content
        assert "discussion_requirement_contract" in quick_content
        assert "consumer_eligibility.sp-quick.status" in quick_content
        assert "quick_task_candidate" in quick_content
        assert "do not skip the understanding checkpoint" in quick_content

        assert f"## {agent_name} Leader Gate".lower() in quick_content
        assert "you are the **leader**, not the concrete implementer" in quick_content
        assert "quick execution routing" in quick_content
        assert "understanding checkpoint" in quick_content
        assert "quick checkpoint" in quick_content
        assert "understanding_confirmed: true" in quick_content
        assert "<br>" not in quick_content
        assert "plain text for terminal output" in quick_content
        assert "dispatch_shape: one-subagent | parallel-subagents" in quick_content
        assert "execution_surface: native-subagents" in quick_content
        assert "validated `workertaskpacket` or equivalent execution contract preserves quality" in quick_content

    def test_map_scan_build_skills_require_native_explorer_lanes_when_selected(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)

        skills_dir = i.skills_dest(tmp_path)
        assert not (skills_dir / "sp-map-codebase" / "SKILL.md").exists()

        scan_content = (skills_dir / "sp-map-scan" / "SKILL.md").read_text(encoding="utf-8").lower()
        build_content = (skills_dir / "sp-map-build" / "SKILL.md").read_text(encoding="utf-8").lower()
        assert 'choose_subagent_dispatch(command_name="map-scan"' in scan_content
        assert 'choose_subagent_dispatch(command_name="map-build"' in build_content
        assert "execution_model: subagent-mandatory" in scan_content or "execution model: `subagents-first`" in scan_content
        assert "execution_model: subagent-mandatory" in build_content or "execution model: `subagents-first`" in build_content
        assert "dispatch_shape: one-subagent | parallel-subagents" in scan_content
        assert "dispatch_shape: one-subagent | parallel-subagents" in build_content
        assert "execution_surface: native-subagents" in scan_content
        assert "execution_surface: native-subagents" in build_content
        assert ".specify/project-cognition/" in scan_content
        assert "provisional" in scan_content
        assert "evidence" in scan_content
        assert "machine-readable scan artifact schema" in scan_content
        assert "source_node_id" in scan_content
        assert "target_node_id" in scan_content
        assert "attrs_json" in scan_content
        assert "coverage.json does not create path_index rows by itself" in scan_content
        assert ".specify/project-cognition/project-cognition.db" in build_content
        assert "path index source contract" in build_content
        assert "nodes.json `paths`" in build_content
        assert "project launcher configured in `.specify/config.json`" in build_content
        assert "project-cognition query" in build_content
        assert "raw graph json artifacts or slices as runtime truth" in build_content

    def test_question_driven_skills_define_native_tool_preference_with_fallback(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)
        agent_name = i.config["name"].replace(" CLI", "").lower()

        for name in ("specify", "discussion", "clarify", "deep-research", "checklist", "quick", "debug"):
            content = (i.skills_dest(tmp_path) / f"sp-{name}" / "SKILL.md").read_text(encoding="utf-8").lower()
            assert f"## {agent_name} structured question preference" in content
            assert "native structured question tool" in content
            assert "fallback-only guidance" in content
            assert "must use it" in content
            assert "auto_default_recommendation" in content
            assert "must auto-resolve" in content
            assert "do not invoke the native structured question tool" in content
            assert "do not render the textual fallback block" in content
            assert "do not self-authorize textual fallback" in content
            assert (
                "template's existing textual question format" in content
                or "existing plain-text" in content
                or "shared open question block structure" in content
                or "plain-text confirmation question" in content
                or "textual question format" in content
                or "plain-text clarification" in content
                or "missing-information question" in content
                or "research-track decision" in content
                or "one high-impact question" in content
            )
            assert "active question exactly once" in content

    def test_generated_specify_skill_teaches_simplified_specify_contract(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)

        content = (i.skills_dest(tmp_path) / "sp-specify" / "SKILL.md").read_text(encoding="utf-8").lower()
        assert "explore project context" in content
        assert "one high-impact question at a time" in content
        assert "two or three approaches" in content or "2-3 approaches" in content
        assert "semantic term" in content
        assert "source_signal_disposition" in content
        assert "discussion-log.md" in content
        assert "requirements.md" in content
        assert "open-questions.md" in content
        assert "facts-lock" not in content
        assert "route-lock" not in content
        assert "intent-lock" not in content
        assert "complexity-lock" not in content

    def test_all_files_tracked_in_manifest(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.setup(tmp_path, m)
        for f in created:
            rel = f.resolve().relative_to(tmp_path.resolve()).as_posix()
            assert rel in m.files, f"{rel} not tracked in manifest"

    def test_install_uninstall_roundtrip(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.install(tmp_path, m)
        assert len(created) > 0
        m.save()
        for f in created:
            assert f.exists()
        removed, skipped = i.uninstall(tmp_path, m)
        assert len(removed) == len(created)
        assert skipped == []

    def test_modified_file_survives_uninstall(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        created = i.install(tmp_path, m)
        m.save()
        modified_file = created[0]
        modified_file.write_text("user modified this", encoding="utf-8")
        removed, skipped = i.uninstall(tmp_path, m)
        assert modified_file.exists()
        assert modified_file in skipped

    def test_pre_existing_skills_not_removed(self, tmp_path):
        """Pre-existing non-speckit skills should be left untouched."""
        i = get_integration(self.KEY)
        skills_dir = i.skills_dest(tmp_path)
        foreign_dir = skills_dir / "other-tool"
        foreign_dir.mkdir(parents=True)
        (foreign_dir / "SKILL.md").write_text("# Foreign skill\n")

        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)

        assert (foreign_dir / "SKILL.md").exists(), "Foreign skill was removed"

    # -- Scripts ----------------------------------------------------------

    def test_setup_installs_update_context_scripts(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)
        scripts_dir = tmp_path / ".specify" / "integrations" / self.KEY / "scripts"
        assert scripts_dir.is_dir(), f"Scripts directory not created for {self.KEY}"
        assert (scripts_dir / "update-context.sh").exists()
        assert (scripts_dir / "update-context.ps1").exists()

    def test_scripts_tracked_in_manifest(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)
        script_rels = [k for k in m.files if "update-context" in k]
        assert len(script_rels) >= 2

    def test_sh_script_is_executable(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)
        sh = tmp_path / ".specify" / "integrations" / self.KEY / "scripts" / "update-context.sh"
        assert os.access(sh, os.X_OK)

    # -- CLI auto-promote -------------------------------------------------

    def test_ai_flag_auto_promotes(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / f"promote-{self.KEY}"
        project.mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            runner = CliRunner()
            result = runner.invoke(app, [
                "init", "--here", "--ai", self.KEY, "--script", "sh", "--no-git",
                "--ignore-agent-tools",
            ], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)
        assert result.exit_code == 0, f"init --ai {self.KEY} failed: {result.output}"
        i = get_integration(self.KEY)
        skills_dir = i.skills_dest(project)
        assert skills_dir.is_dir(), f"--ai {self.KEY} did not create skills directory"
        for skill_name in self._passive_skill_names():
            assert (skills_dir / skill_name / "SKILL.md").exists(), (
                f"--ai {self.KEY} did not install passive skill {skill_name}"
            )

    def test_init_bootstraps_context_file(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / f"context-{self.KEY}"
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
        assert (project / self.CONTEXT_FILE).is_file(), (
            f"--ai {self.KEY} did not create context file {self.CONTEXT_FILE}"
        )

    def test_init_bootstrapped_context_file_contains_managed_guidance(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

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

    def test_init_augments_existing_context_file_with_managed_guidance(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / f"context-existing-{self.KEY}"
        project.mkdir()
        context_path = project / self.CONTEXT_FILE
        context_path.parent.mkdir(parents=True, exist_ok=True)
        initial = "# User Context\n\nKeep this line.\n"
        context_path.write_text(initial, encoding="utf-8")

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
        content = context_path.read_text(encoding="utf-8")
        assert content.startswith(initial)
        _assert_compact_managed_context(content)

    def test_integration_flag_creates_files(self, tmp_path):
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / f"int-{self.KEY}"
        project.mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            runner = CliRunner()
            result = runner.invoke(app, [
                "init", "--here", "--integration", self.KEY, "--script", "sh", "--no-git",
                "--ignore-agent-tools",
            ], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)
        assert result.exit_code == 0, f"init --integration {self.KEY} failed: {result.output}"
        i = get_integration(self.KEY)
        skills_dir = i.skills_dest(project)
        assert skills_dir.is_dir(), f"Skills directory {skills_dir} not created"
        for skill_name in self._passive_skill_names():
            assert (skills_dir / skill_name / "SKILL.md").exists(), (
                f"--integration {self.KEY} did not install passive skill {skill_name}"
            )

    # -- IntegrationOption ------------------------------------------------

    def test_options_include_skills_flag(self):
        i = get_integration(self.KEY)
        opts = i.options()
        skills_opts = [o for o in opts if o.name == "--skills"]
        assert len(skills_opts) == 1
        assert skills_opts[0].is_flag is True

    # -- Complete file inventory ------------------------------------------

    def _skill_commands(self) -> list[str]:
        i = get_integration(self.KEY)
        commands = []
        for template in i.list_command_templates():
            commands.append("teams" if template.stem == "team" else template.stem)
        return commands

    def _template_files(self) -> list[str]:
        i = get_integration(self.KEY)
        templates_dir = i.shared_templates_dir()
        if not templates_dir or not templates_dir.is_dir():
            return []

        return sorted(
            rel_path
            for path in templates_dir.rglob("*")
            if path.is_file()
            and path.name != "vscode-settings.json"
            for rel_path in (path.relative_to(templates_dir).as_posix(),)
            if not rel_path.startswith("project-map/")
        )

    def _passive_skill_names(self) -> list[str]:
        i = get_integration(self.KEY)
        passive_dir = i.shared_passive_skills_dir()
        if not passive_dir or not passive_dir.is_dir():
            return []

        return sorted(
            path.name
            for path in passive_dir.iterdir()
            if path.is_dir() and (path / "SKILL.md").is_file()
        )

    def _passive_skill_files(self) -> list[str]:
        i = get_integration(self.KEY)
        passive_dir = i.shared_passive_skills_dir()
        if not passive_dir or not passive_dir.is_dir():
            return []

        return sorted(
            path.relative_to(passive_dir).as_posix()
            for path in passive_dir.rglob("*")
            if path.is_file()
        )

    def _expected_files(self, script_variant: str) -> list[str]:
        """Build the full expected file list for a given script variant."""
        i = get_integration(self.KEY)
        skills_prefix = i.config["folder"].rstrip("/") + "/" + i.config.get("commands_subdir", "skills")

        files = []
        # Skill files
        for cmd in self._skill_commands():
            files.append(f"{skills_prefix}/sp-{cmd}/SKILL.md")
        for relative_file in self._passive_skill_files():
            files.append(f"{skills_prefix}/{relative_file}")
        files.append(self.CONTEXT_FILE)
        # Integration metadata
        files += [
            ".specify/config.json",
            ".specify/init-options.json",
            ".specify/integration.json",
            f".specify/integrations/{self.KEY}.manifest.json",
            f".specify/integrations/{self.KEY}/scripts/update-context.ps1",
            f".specify/integrations/{self.KEY}/scripts/update-context.sh",
            ".specify/integrations/speckit.manifest.json",
            ".specify/memory/constitution.md",
            ".specify/memory/learnings/INDEX.md",
            ".specify/memory/project-learnings.md",
            ".specify/memory/project-rules.md",
        ]
        # Script variant
        if script_variant == "sh":
            files += [
                ".specify/scripts/bash/check-prerequisites.sh",
                ".specify/scripts/bash/common.sh",
                ".specify/scripts/bash/create-new-feature.sh",
                ".specify/scripts/bash/discussion-state.sh",
                ".specify/scripts/bash/prd-state.sh",
                ".specify/scripts/bash/project-cognition-freshness.sh",
                ".specify/scripts/bash/quick-state.sh",
                ".specify/scripts/bash/sync-ecc-to-codex.sh",
                ".specify/scripts/bash/setup-plan.sh",
                ".specify/scripts/bash/update-agent-context.sh",
            ]
        else:
            files += [
                ".specify/scripts/powershell/check-prerequisites.ps1",
                ".specify/scripts/powershell/common.ps1",
                ".specify/scripts/powershell/create-new-feature.ps1",
                ".specify/scripts/powershell/discussion-state.ps1",
                ".specify/scripts/powershell/prd-state.ps1",
                ".specify/scripts/powershell/project-cognition-freshness.ps1",
                ".specify/scripts/powershell/quick-state.ps1",
                ".specify/scripts/powershell/sync-ecc-to-codex.ps1",
                ".specify/scripts/powershell/setup-plan.ps1",
                ".specify/scripts/powershell/update-agent-context.ps1",
            ]
        files.append(SHARED_PRD_HELPER)
        # Templates
        files += [f".specify/templates/{name}" for name in self._template_files()]
        return sorted(files)

    def test_complete_file_inventory_sh(self, tmp_path):
        """Every file produced by specify init --integration <key> --script sh."""
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / f"inventory-sh-{self.KEY}"
        project.mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = CliRunner().invoke(app, [
                "init", "--here", "--integration", self.KEY,
                "--script", "sh", "--no-git", "--ignore-agent-tools",
            ], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)
        assert result.exit_code == 0, f"init failed: {result.output}"
        actual = sorted(
            p.relative_to(project).as_posix()
            for p in project.rglob("*") if p.is_file()
        )
        expected = self._expected_files("sh")
        assert actual == expected, (
            f"Missing: {sorted(set(expected) - set(actual))}\n"
            f"Extra: {sorted(set(actual) - set(expected))}"
        )

    def test_complete_file_inventory_ps(self, tmp_path):
        """Every file produced by specify init --integration <key> --script ps."""
        from typer.testing import CliRunner
        from specify_cli import app

        project = tmp_path / f"inventory-ps-{self.KEY}"
        project.mkdir()
        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = CliRunner().invoke(app, [
                "init", "--here", "--integration", self.KEY,
                "--script", "ps", "--no-git", "--ignore-agent-tools",
            ], catch_exceptions=False)
        finally:
            os.chdir(old_cwd)
        assert result.exit_code == 0, f"init failed: {result.output}"
        actual = sorted(
            p.relative_to(project).as_posix()
            for p in project.rglob("*") if p.is_file()
        )
        expected = self._expected_files("ps")
        assert actual == expected, (
            f"Missing: {sorted(set(expected) - set(actual))}\n"
            f"Extra: {sorted(set(actual) - set(expected))}"
        )
