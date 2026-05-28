from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(rel_path: str) -> str:
    return (PROJECT_ROOT / rel_path).read_text(encoding="utf-8")


def _section(content: str, start: str, end: str) -> str:
    start_index = content.index(start)
    end_index = content.index(end, start_index)
    return content[start_index:end_index]


def _paragraphs_with(content: str, marker: str) -> list[str]:
    return [paragraph for paragraph in content.split("\n\n") if marker in paragraph]


def test_quickstart_teaches_specify_to_plan_mainline():
    quickstart = _read("docs/quickstart.md")

    assert "move directly from `specify` to `plan`" in quickstart
    assert "$sp-specify" in quickstart
    assert "$sp-prd-scan -> $sp-prd-build" in quickstart
    assert "/skill:sp-plan" in quickstart
    assert "/sp.specify" in quickstart
    assert "/sp.prd-scan" in quickstart
    assert "`specify -> plan` as the default path" in quickstart or "specify -> plan -> tasks -> implement" in quickstart
    assert "`specify` -> `deep-research` -> `plan`" in quickstart


def _assert_doc_teaches_user_confirmed_product_scope(rel_path: str) -> None:
    lowered = _read(rel_path).lower()

    assert "scope reduction requires user confirmation" in lowered
    assert "preserve the user's confirmed product scope" in lowered
    assert "minimal viable path" not in lowered
    assert "smallest coherent release slice" not in lowered


def test_docs_teach_user_confirmed_product_scope_not_default_mvp() -> None:
    for rel_path in (
        "README.md",
        "PROJECT-HANDBOOK.md",
        "templates/project-handbook-template.md",
        "docs/quickstart.md",
    ):
        _assert_doc_teaches_user_confirmed_product_scope(rel_path)


def test_docs_teach_command_surface_minimization_preserves_scaffold_operations() -> None:
    for rel_path in (
        "README.md",
        "PROJECT-HANDBOOK.md",
        "templates/project-handbook-template.md",
        "docs/quickstart.md",
        "docs/installation.md",
    ):
        lowered = _read(rel_path).lower()

        assert "command-surface minimization must not delete capability" in lowered
        assert "new/create/scaffold/authoring" in lowered
        assert "manual copy" in lowered
        assert "template-only" in lowered
        assert "tui route" in lowered
        assert "core api" in lowered


def test_quickstart_declares_integration_specific_invocation_syntax():
    readme = _read("README.md")
    quickstart = _read("docs/quickstart.md")
    installation = _read("docs/installation.md")

    assert "Invocation syntax depends on the integration:" in quickstart
    assert "$sp-specify" in quickstart
    assert "$sp-prd-scan -> $sp-prd-build" in quickstart
    assert "/skill:sp-specify" in quickstart
    assert "/skill:sp-prd-scan -> /skill:sp-prd-build" in quickstart
    assert "/sp.specify" in quickstart
    assert "/sp.prd-scan" in quickstart
    assert "Canonical workflow names are integration-neutral" in quickstart
    assert "Slash-dot command integrations" in readme
    assert "Slash-dot command integrations" in quickstart
    assert "Slash-dot command integrations" in installation
    assert "Markdown command integrations" not in readme
    assert "Markdown command integrations" not in quickstart
    assert "Markdown command integrations" not in installation

    for content in (readme, quickstart, installation):
        assert "`/sp-*` is not universal for skills-backed integrations" in content
        assert "canonical workflow names" in content.lower()
        assert "$sp-plan" in content
        assert "$sp-prd-scan -> $sp-prd-build" in content
        assert "/skill:sp-plan" in content
        assert "/skill:sp-prd-scan -> /skill:sp-prd-build" in content
        assert "/sp.plan" in content
        assert "/sp.prd-scan" in content


def test_upgrade_doc_mentions_project_launcher_binding():
    upgrade = _read("docs/upgrade.md")

    assert "specify_launcher" in upgrade
    assert "project launcher" in upgrade.lower()
    assert "runtime" in upgrade.lower()


def test_repo_docs_explain_adaptive_plan_tasks_dispatch_contract() -> None:
    handbook = _read("PROJECT-HANDBOOK.md").lower()

    assert "subagents-first dispatch" not in handbook
    assert "adaptive and mandatory dispatch selection" in handbook
    assert "adaptive plan/tasks dispatch plus mandatory-subagent dispatch/state/review helpers" in handbook

    for rel_path in ("README.md", "PROJECT-HANDBOOK.md"):
        content = _read(rel_path)
        lowered = content.lower()

        assert "execution_model: adaptive" in content
        assert "execution_mode: light | standard | heavy" in content
        assert "dispatch_shape: leader-inline | one-subagent | parallel-subagents | subagent-blocked" in content
        assert "light" in lowered
        assert "leader-inline" in content
        assert "standard" in lowered
        assert "native subagents" in lowered or "native-subagent" in lowered
        assert "capability_degraded: true" in content
        assert "no safe" in lowered
        assert "cannot be packetized safely" in lowered or "unpacketizable" in lowered
        assert "subagent-blocked" in content
        assert "heavy or safety-critical" in lowered
        assert "native subagents are unavailable" in lowered
        assert "managed-team fallback is not part of adaptive plan/tasks dispatch" in lowered


def test_quickstart_positions_clarify_correctly():
    quickstart = _read("docs/quickstart.md")
    lowered = quickstart.lower()

    assert "/sp-clarify" in quickstart
    assert "repair lane" in lowered or "needs deeper analysis before planning" in lowered


def test_guidance_docs_explain_skill_groups():
    readme = _read("README.md")
    quickstart = _read("docs/quickstart.md")

    assert "Core workflow skills" in readme
    assert "Support skills" in readme
    assert "Codex-only runtime" in readme
    assert "`auto`" in readme
    assert "`discussion`" in readme
    assert "`clarify`" in readme
    assert "`deep-research`" in readme
    assert "`prd`" in readme
    assert "`checklist`" in readme
    assert "`analyze`" in readme
    assert "`debug`" in readme
    assert "`explain`" in readme
    assert "`map-scan`" in readme
    assert "`map-build`" in readme
    assert "`sp-teams`" in readme

    assert "Core workflow skills" in quickstart
    assert "Support skills" in quickstart
    assert "Codex-only runtime" in quickstart
    assert "`discussion`" in quickstart
    skill_map = _section(quickstart, "## Skill Map", "For Codex team-mode execution")
    assert "`constitution`, `specify`, `plan`, `tasks`, `implement`" in skill_map
    assert "`map-scan`, `map-build`, `map-update`, `auto`, `discussion`, `prd-scan`, `prd-build`, `prd` (deprecated compatibility entrypoint), `clarify`, `deep-research` (`research` alias), `checklist`, `analyze`, `debug`, `explain`" in skill_map
    assert "/sp-" not in skill_map


def test_guidance_docs_position_discussion_before_specify() -> None:
    readme = _read("README.md")
    quickstart = _read("docs/quickstart.md")
    installation = _read("docs/installation.md")

    for content in (readme, quickstart, installation):
        matching_guidance = []
        for paragraph in _paragraphs_with(content, "`discussion`"):
            normalized = re.sub(r"\s+", " ", paragraph).lower()
            if (
                "rough idea" in normalized
                and ("before formal specification" in normalized or "pre-spec" in normalized)
                and "handoff-to-specify.md" in paragraph
                and "explicit" in normalized
                and "does not automatically invoke `specify`" in normalized
            ):
                matching_guidance.append(paragraph)

        assert matching_guidance


def test_guidance_docs_explain_discussion_boundary_and_unified_handoff() -> None:
    readme = _read("README.md")
    handbook = _read("PROJECT-HANDBOOK.md")
    generated_handbook = _read("templates/project-handbook-template.md")

    for content in (readme, handbook, generated_handbook):
        lowered = content.lower()
        assert "Context Boundary Gate" in content
        assert "target project root" in lowered
        assert "current project cognition cannot prove another project's" in lowered
        assert "handoff-to-specify.md" in content
        assert "handoff-to-specify.json" in content
        assert "single unified handoff" in lowered or "one unified handoff" in lowered
        assert "classifies each turn" in lowered or "classifies each user turn" in lowered
        assert "live evidence" in lowered
        assert "project cognition" in lowered
        assert "advisory navigation" in lowered
        assert "semantic checkpoints" in lowered
        assert "draft unified handoff pair" in lowered or "one unified handoff pair" in lowered
        assert "quality_gate" in content
        assert "user confirmation" in lowered
        assert "split-plan.md" not in content
        assert "handoffs/<candidate_id>" not in content
        assert "CAND-001" not in content
        assert "CAND-002" not in content


def test_readme_documents_inline_project_cognition_closeout() -> None:
    readme = _read("README.md").lower()

    assert "workflow-owned mutation closeout is inline" in readme
    assert (
        "sp-map-update remains the external/manual maintenance workflow" in readme
        or "`sp-map-update` remains the external/manual maintenance workflow" in readme
    )


def test_quickstart_and_installation_explain_discussion_boundary_handoffs() -> None:
    quickstart = _read("docs/quickstart.md")
    installation = _read("docs/installation.md")

    for content in (quickstart, installation):
        lowered = content.lower()
        assert "Context Boundary Gate" in content
        assert "target project root" in lowered
        assert "reference source" in lowered
        assert "adaptive question pack" in lowered
        assert "primary question" in lowered
        assert "optional same-topic follow-ups" in lowered
        assert "asks one high-impact question at a time" not in lowered
        assert "handoff-to-specify.md" in content
        assert "handoff-to-specify.json" in content
        assert "single unified handoff" in lowered or "one unified handoff" in lowered
        assert "missing json" in lowered
        assert "user confirmation" in lowered
        assert "split-plan.md" not in content
        assert "handoffs/CAND-001-handoff-to-specify" not in content
        assert "handoffs/CAND-002-handoff-to-specify" not in content


def test_quickstart_skill_map_and_guidance_use_canonical_names_not_claude_syntax():
    readme = _read("README.md")
    quickstart = _read("docs/quickstart.md")

    skill_map = _section(quickstart, "## Skill Map", "For Codex team-mode execution")
    support_guidance = _section(quickstart, "Use support skills when they solve a specific gap:", "Passive project learning layer:")

    for section in (skill_map, support_guidance):
        assert "/sp-" not in section

    assert "`map-update` for localized stale cognition runtime refresh" in support_guidance
    assert "changed-path maintenance" in support_guidance
    assert "recorded refresh and ready refresh" in readme.lower()
    assert "support drift is not runtime-truth staleness" in readme.lower()
    assert "`partial_refresh`" in readme
    assert "`support_drift`" in readme
    assert "workflow-owned mutation closeout is inline" in readme.lower()
    assert (
        "sp-map-update remains the external/manual maintenance workflow" in readme.lower()
        or "`sp-map-update` remains the external/manual maintenance workflow" in readme.lower()
    )
    assert "use `map-update` for changed-path" not in readme.lower()
    assert "changed-path and localized stale cognition runtime refresh" not in readme.lower()
    assert "`map-scan` followed by `map-build` only when the baseline is first/missing/unusable, schema failure" in support_guidance
    assert "`deep-research` when a planning-ready spec still needs feasibility evidence" in support_guidance
    assert "`prd-scan` followed by `prd-build` as the existing-project reverse PRD lane" in support_guidance
    assert "heavy reconstruction workflow" in support_guidance
    assert "`L4 Reconstruction-Ready`" in support_guidance
    assert "`config-contracts.json`" in support_guidance
    assert "second repository scan" in support_guidance
    assert "does not automatically hand off to `plan`" in support_guidance
    assert "`analyze` is an optional read-only diagnostic and legacy revalidation pass once `tasks.md` exists" in support_guidance
    assert "`fast` is only for trivial local fixes" in support_guidance
    assert "Optional diagnostics:" in quickstart
    assert "the shared `specify`, `plan`, `tasks`, `implement`, and `debug` workflows" in support_guidance


def test_repo_docs_route_brownfield_runtime_through_cognition_query() -> None:
    readme = _read("README.md").lower()
    handbook = _read("PROJECT-HANDBOOK.md").lower()

    for content in (readme, handbook):
        assert "project-cognition query" in content
        assert "project-cognition.db" in content
        assert "workflow-appropriate slices" not in content


def test_docs_explain_map_scan_build_artifact_field_contract() -> None:
    for rel_path in (
        "README.md",
        "PROJECT-HANDBOOK.md",
        "templates/project-handbook-template.md",
    ):
        content = _read(rel_path)
        lowered = content.lower()

        assert "scan artifacts" in lowered
        assert "`node_id`" in content
        assert "`kind`" in content
        assert "`label`" in content
        assert "`source_node_id`" in content
        assert "`target_node_id`" in content
        assert "`attrs_json`" in content
        assert "`coverage`" in content
        assert "`rows`" in content
        assert "path_index" in content
        assert "nodes[].paths" in content
        assert "coverage.json" in content
        assert "coverage accounting" in lowered


def test_quickstart_taskify_walkthrough_frames_literal_sp_examples_as_claude_style():
    quickstart = _read("docs/quickstart.md")
    walkthrough = _section(quickstart, "## Detailed Example: Building Taskify", "## Key Principles")

    assert "The following Taskify snippets use Claude-style `/sp-*` invocation syntax." in walkthrough
    assert "translate each literal command through the invocation matrix above" in walkthrough
    assert "### Step 2: Define Requirements with `specify`" in walkthrough
    assert "Once `specify` reaches planning-ready alignment, move directly to `plan`." in walkthrough
    assert "using the `checklist` workflow" in walkthrough
    assert "using the `tasks` workflow" in walkthrough
    assert "Finally, implement the solution:" in walkthrough
    assert "/sp-implement" in walkthrough
    assert "Optional diagnostics:" not in walkthrough
    assert "/sp-analyze" not in walkthrough
    assert "If `analyze` finds issues" not in walkthrough
    assert "Define Requirements with `/sp-specify`" not in walkthrough
    assert "Once `/sp-specify`" not in walkthrough
    assert "using the `/sp-" not in walkthrough


def test_guidance_docs_do_not_teach_fixed_heavy_specify_lifecycle() -> None:
    readme = _read("README.md")
    quickstart = _read("docs/quickstart.md")
    installation = _read("docs/installation.md")

    for content in (readme, quickstart, installation):
        lowered = content.lower()
        assert "fixed heavy discovery" not in lowered
        assert "intent-analysis" not in content
        assert "intent-confirmation" not in content
        assert "question-batch" not in content
        assert "batch-adversarial-review" not in content
        assert "completeness-audit" not in content
        assert "final-handoff-decision" not in content
        assert "intent-analyst" not in content
        assert "adversarial-reviewer" not in content
        assert "completeness-auditor" not in content
        assert "goal-and-users" not in content
        assert "triggers-and-primary-flow" not in content
        assert "boundaries-and-non-goals" not in content
        assert "failure-paths-exceptions-and-permissions" not in content
        assert "dependencies-constraints-and-upstream-downstream-impact" not in content
        assert "acceptance-and-completeness-gap-closure" not in content
        assert "task classification" not in lowered


def test_guidance_docs_teach_specify_as_collaborative_reviewed_flow() -> None:
    readme = _read("README.md")
    quickstart = _read("docs/quickstart.md")
    installation = _read("docs/installation.md")

    for content in (readme, quickstart, installation):
        lowered = content.lower()
        assert "collaborative reviewed specification flow" in lowered
        assert "one question at a time" in lowered
        assert "semantic term" in lowered
        assert "two or three" in lowered and "approaches" in lowered
        assert "user review" in lowered
        assert "source_signal_disposition" in content
        assert "discussion-log.md" in content
        assert "requirements.md" in content
        assert "open-questions.md" in content
        assert "facts-lock" not in lowered
        assert "route-lock" not in lowered
        assert "intent-lock" not in lowered
        assert "complexity-lock" not in lowered


def test_guidance_docs_explain_semantic_specify_traceability() -> None:
    readme = _read("README.md")
    quickstart = _read("docs/quickstart.md")
    installation = _read("docs/installation.md")
    handbook = _read("PROJECT-HANDBOOK.md")
    generated_handbook = _read("templates/project-handbook-template.md")

    for content in (readme, quickstart, installation, handbook, generated_handbook):
        lowered = content.lower()
        assert "semantic" in lowered
        assert "source_signal_disposition" in content
        assert "semantic term decisions" in lowered
        assert "upstream intent disposition" in lowered
        assert "out-of-scope conflicts" in lowered
        assert "journal.ndjson" not in content
        assert "stage-manifest.json" not in content
        assert "lossless" not in lowered
        assert "compiled_from" not in content


def test_guidance_docs_explain_analyze_tasks_convergence_contract() -> None:
    readme = _read("README.md")
    handbook = _read("PROJECT-HANDBOOK.md")
    handbook_lower = handbook.lower()

    for content in (readme, handbook):
        lowered = content.lower()
        assert "complete blocker bundle" in lowered
        assert "implementation-readiness self-audit" in lowered
        assert "repeated `tasks -> analyze -> tasks` loops are abnormal" in content
        assert "only use `analyze` again when explicitly required by legacy or diagnostic state" in content
        assert "directly to `plan`, `clarify`, or `deep-research`" in content

    assert "tasks/implement default contract" in handbook_lower
    assert "implementation-readiness self-audit" in handbook_lower
    assert "clean completion writes `next_command: /sp.implement`" in handbook_lower
    assert "`sp-analyze` remains an optional diagnostic and legacy revalidation route only when explicitly invoked or recorded in existing state" in handbook_lower


def test_guidance_docs_teach_consequence_gate_across_workflow_mainline() -> None:
    readme = _read("README.md")
    quickstart = _read("docs/quickstart.md")

    for content in (readme, quickstart):
        lowered = content.lower()
        assert "senior consequence analysis gate" in lowered
        assert "`discussion`" in content
        assert "`specify`" in content
        assert "`plan`" in content
        assert "`tasks`" in content
        assert "`fast`" in content
        assert "`quick`" in content
        assert "`debug`" in content
        assert "close team" in lowered
        assert "running workers" in lowered
        assert "ca-###" in lowered
