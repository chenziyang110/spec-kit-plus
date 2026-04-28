from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(rel_path: str) -> str:
    return (PROJECT_ROOT / rel_path).read_text(encoding="utf-8")


def test_quickstart_teaches_specify_to_plan_mainline():
    quickstart = _read("docs/quickstart.md")

    assert "move directly from `/speckit.specify` to `/speckit.plan`" in quickstart
    assert "`/speckit.specify` to `/speckit.plan`" in quickstart or "`/speckit.specify` and `/speckit.plan`" in quickstart
    assert "`specify -> plan` as the default path" in quickstart


def test_quickstart_positions_clarify_correctly():
    quickstart = _read("docs/quickstart.md")
    lowered = quickstart.lower()

    assert "/speckit.clarify" in quickstart
    assert "repair lane" in lowered or "needs deeper analysis before planning" in lowered


def test_guidance_docs_explain_skill_groups():
    readme = _read("README.md")
    quickstart = _read("docs/quickstart.md")

    assert "Core workflow skills" in readme
    assert "Support skills" in readme
    assert "Codex-only runtime" in readme
    assert "`clarify`" in readme
    assert "`checklist`" in readme
    assert "`analyze`" in readme
    assert "`debug`" in readme
    assert "`explain`" in readme
    assert "`map-codebase`" in readme
    assert "`specify team`" in readme

    assert "Core workflow skills" in quickstart
    assert "Support skills" in quickstart
    assert "Codex-only runtime" in quickstart
    assert "/speckit.clarify" in quickstart
    assert "/speckit.checklist" in quickstart
    assert "/speckit.analyze" in quickstart
    assert "/speckit.debug" in quickstart
    assert "/speckit.map-codebase" in quickstart


def test_guidance_docs_explain_optional_codex_teams_mcp_refresh():
    readme = _read("README.md")
    quickstart = _read("docs/quickstart.md")

    for content in (readme, quickstart):
        assert 'pip install "specify-cli[mcp]"' in content
        assert "scripts/sync-ecc-to-codex.sh" in content
        assert "scripts/powershell/sync-ecc-to-codex.ps1" in content


def test_guidance_docs_position_constitution_as_seeded_defaults_plus_refinement():
    readme = _read("README.md").lower()
    quickstart = _read("docs/quickstart.md").lower()

    for content in (readme, quickstart):
        assert "default constitution" in content
        assert "project-specific changes" in content
        assert "revise project principles" in content or "establish or revise project principles" in content


def test_guidance_docs_explain_constitution_profiles():
    readme = _read("README.md")
    quickstart = _read("docs/quickstart.md")
    profile_doc = _read("docs/constitution-profiles.md")

    assert "--constitution-profile" in readme
    assert "--constitution-profile" in quickstart
    for content in (readme, quickstart, profile_doc):
        assert "product" in content
        assert "minimal" in content
        assert "library" in content
        assert "regulated" in content


def test_guidance_docs_explain_handbook_navigation_system():
    readme = _read("README.md")
    quickstart = _read("docs/quickstart.md")

    for content in (readme, quickstart):
        assert "Generated projects include `PROJECT-HANDBOOK.md` as the root navigation artifact." in content
        assert "Deep project knowledge lives under `.specify/project-map/`." in content
        assert "atlas-style technical encyclopedia" in content.lower()
        assert ".specify/project-map/status.json" in content
        assert "project-map complete-refresh" in content
        assert "Any code change that alters navigation meaning must update the handbook system." in content


def test_guidance_docs_position_map_codebase_for_existing_projects():
    readme = _read("README.md")
    quickstart = _read("docs/quickstart.md")

    assert "Already have code?" in readme
    assert "Run `map-codebase` first" in readme
    assert "/speckit.map-codebase" in quickstart
    assert "existing codebase" in quickstart.lower()
    assert "required brownfield gate" in readme.lower()
    assert "required brownfield gate" in quickstart.lower()
    assert "task generation" in quickstart.lower()
    assert "dependency graph, runtime flows, state lifecycle, and change-impact view" in readme.lower()
    assert "dependency graph, runtime flows, state lifecycle, and change-impact view" in quickstart.lower()


def test_guidance_docs_explain_that_spec_workflows_do_not_refresh_map_content_directly():
    readme = _read("README.md").lower()
    quickstart = _read("docs/quickstart.md").lower()

    for content in (readme, quickstart):
        assert "mark `.specify/project-map/status.json` dirty" in content or "mark `.specify/project-map/status.json` dirty" in _read("AGENTS.md").lower()
        assert "run `map-codebase` first" in content or "run `/speckit.map-codebase`" in content


def test_guidance_docs_expand_explain_to_handbook_and_project_map_views():
    readme = _read("README.md").lower()
    quickstart = _read("docs/quickstart.md").lower()

    assert "spec, plan, task, implement, or handbook/project-map atlas artifact" in readme
    assert "spec, plan, task, implement, or handbook/project-map atlas artifact" in quickstart


def test_guidance_docs_frame_analyze_as_pre_implement_gate():
    readme = _read("README.md").lower()
    quickstart = _read("docs/quickstart.md").lower()

    assert "tasks -> analyze -> implement" in readme
    assert "before implementation, run `/speckit.analyze`" in quickstart
    assert "default pre-implementation gate" in readme
    assert "required gate before implementation once `tasks.md` exists" in quickstart


def test_guidance_docs_explain_fast_quick_specify_routing():
    readme = _read("README.md").lower()
    quickstart = _read("docs/quickstart.md").lower()

    for content in (readme, quickstart):
        assert "sp-fast" in content or "/speckit.fast" in content
        assert "sp-quick" in content or "/speckit.quick" in content
        assert "more than 3 files" in content
        assert "shared surface" in content
        assert "multiple independent capabilities" in content
        assert "compatibility" in content
        assert "acceptance criteria" in content
        assert "root cause" in content
        assert "sp-debug" in content or "/speckit.debug" in content
        assert "symptom" in content


def test_guidance_docs_explain_failing_test_first_execution_rule():
    readme = _read("README.md").lower()
    quickstart = _read("docs/quickstart.md").lower()

    for content in (readme, quickstart):
        assert "failing test first" in content
        assert "sp-fast" in content or "/speckit.fast" in content
        assert "sp-quick" in content or "/speckit.quick" in content
        assert "sp-implement" in content or "/speckit.implement" in content
        assert "sp-debug" in content or "/speckit.debug" in content


def test_guidance_docs_explain_passive_project_learning_layer():
    readme = _read("README.md")
    quickstart = _read("docs/quickstart.md")
    local_dev = _read("docs/local-development.md")

    for content in (readme, quickstart):
        assert ".specify/memory/project-rules.md" in content
        assert ".specify/memory/project-learnings.md" in content
        assert ".planning/learnings/candidates.md" in content
        assert "passive project learning" in content.lower()
        assert "specify learning start" in content
        assert "specify learning capture" in content
        assert "specify learning promote" in content

    assert "specify learning ensure --format json" in local_dev
    assert "specify learning status --format json" in local_dev


def test_guidance_docs_explain_project_memory_as_global_shared_context():
    readme = _read("README.md").lower()
    quickstart = _read("docs/quickstart.md").lower()
    agents = _read("AGENTS.md").lower()

    for content in (readme, quickstart, agents):
        assert "shared project memory" in content
        assert "not just when a `sp-*` workflow is active" in content or "not limited to spec workflows" in content


def test_guidance_docs_publish_native_hook_coverage_matrix():
    readme = _read("README.md")
    quickstart = _read("docs/quickstart.md")

    for content in (readme, quickstart):
        assert "Native hook coverage matrix" in content
        assert "Claude" in content
        assert "Codex/OMX" in content
        assert "Gemini" in content
        assert "Other integrations" in content
        assert "Learning signal bridge" in content
        assert "Native terminal review gate" in content


def test_guidance_docs_include_learning_aggregate_surface():
    readme = Path("README.md").read_text(encoding="utf-8")
    quickstart = Path("docs/quickstart.md").read_text(encoding="utf-8")

    assert "specify learning aggregate" in readme
    assert "specify learning aggregate" in quickstart


def test_guidance_docs_explain_implementation_constitution_and_boundary_guardrails():
    readme = _read("README.md")
    quickstart = _read("docs/quickstart.md")

    for content in (readme, quickstart):
        assert "Implementation Constitution" in content
        assert "boundary ownership" in content
        assert "forbidden implementation drift" in content
        assert "required implementation references" in content
        assert "implementation guardrails" in content
        assert "owning framework" in content or "owning framework, defining reference files" in content


def test_guidance_docs_explain_boundary_guardrail_issue_family():
    readme = _read("README.md")
    quickstart = _read("docs/quickstart.md")

    assert "BG1" in readme
    assert "BG2" in readme
    assert "BG3" in readme
    assert "missing `Implementation Constitution`" in readme
    assert "missing task guardrails" in readme
    assert "missing implementation-time boundary confirmation" in readme

    assert "BG1" in quickstart
    assert "BG2" in quickstart
    assert "BG3" in quickstart


def test_guidance_docs_explain_analyze_reentry_loop():
    readme = _read("README.md")
    quickstart = _read("docs/quickstart.md")

    for content in (readme, quickstart):
        assert "when you run" in content.lower()
        assert "gate, not a dead-end audit" in content
        assert "reopen the highest invalid stage" in content
        assert "regenerate downstream artifacts" in content
        assert "If the defect is in `spec.md` or `context.md`" in content or "If the problem is in `spec.md` or `context.md`" in content
        assert "If the defect is in `plan.md`" in content or "If the problem is in `plan.md`" in content
        assert "If the defect is only in `tasks.md`" in content or "If the problem is only in `tasks.md`" in content
        assert "execution-only" in content
        assert "provisional" in content
        assert "started or finished" in content


def test_guidance_docs_explain_rule_carrying_worker_packets():
    readme = _read("README.md")
    quickstart = _read("docs/quickstart.md")

    for content in (readme, quickstart):
        assert "Dispatch Compilation Hints" in content
        assert "Task Guardrail Index" in content
        assert "WorkerTaskPacket" in content
        assert "raw task text" in content
        assert "platform guardrails" in content.lower()
        assert "DP1" in content
        assert "DP2" in content
        assert "DP3" in content


def test_guidance_docs_explain_delegated_result_handoff_contract():
    readme = _read("README.md").lower()
    quickstart = _read("docs/quickstart.md").lower()

    assert "runtime-managed result channel" in readme
    assert "specify result submit" in readme
    assert "specify result path" in readme
    assert "feature_dir/worker-results/<task-id>.json" in readme
    assert ".planning/quick/<id>-<slug>/worker-results/<lane-id>.json" in readme
    assert ".planning/debug/results/<session-slug>/<lane-id>.json" in readme
    assert "reported_status" in readme

    assert "worker-results" in quickstart
    assert "specify result submit" in quickstart
    assert "reported_status" in quickstart
    assert "pending placeholder" in quickstart
    assert "do not submit" in readme


def test_guidance_docs_explain_task_shaping_and_fail_fast_rules():
    readme = _read("README.md").lower()
    quickstart = _read("docs/quickstart.md").lower()

    for content in (readme, quickstart):
        assert "coffee-break-sized implementation slice" in content
        assert "roughly 10-20 minutes" in content
        assert "2-5 minute atomic steps" in content
        assert "refine only the current executable window after each join point" in content
        assert "grouped parallelism is the default" in content
        assert "pipeline shape" in content or "pipeline" in content
        assert "review gate" in content
        assert "validation target" in content
        assert "pass condition" in content
        assert "stale lane" in content
        assert "peer-review lane" in content
        assert "failed assumption" in content
        assert "smallest safe recovery step" in content


def test_guidance_docs_explain_single_lane_compatibility_for_execution_workflows():
    readme = _read("README.md").lower()
    quickstart = _read("docs/quickstart.md").lower()

    assert "single-lane" in readme
    assert "topology label for one safe execution lane" in readme
    assert "validated `workertaskpacket` or equivalent execution contract preserves quality" in readme
    assert "single-lane" in quickstart
    assert "topology label for one safe execution lane" in quickstart
    assert "validated `workertaskpacket` or equivalent execution contract preserves quality" in quickstart


def test_guidance_docs_explain_team_runtime_join_point_and_stale_lane_rules():
    readme = _read("README.md").lower()
    quickstart = _read("docs/quickstart.md").lower()

    for content in (readme, quickstart):
        assert "platform guardrails" in content
        assert "validation target" in content
        assert "stale lane" in content


def test_guidance_docs_explain_resumable_quick_management():
    readme = _read("README.md").lower()
    quickstart = _read("docs/quickstart.md").lower()

    for content in (readme, quickstart):
        assert ".planning/quick/<id>-<slug>/" in content
        assert "index.json" in content
        assert "no arguments" in content or "with no arguments" in content
        assert "blocked" in content
        assert "specify quick list" in content
        assert "specify quick status" in content
        assert "specify quick close" in content
        assert "specify quick archive" in content


def test_repo_docs_share_same_workflow_guidance():
    readme = _read("README.md").lower()
    agents = _read("AGENTS.md").lower()
    quickstart = _read("docs/quickstart.md").lower()

    assert "specify -> plan" in readme
    assert "specify -> plan" in agents
    assert "specify -> plan" in quickstart


def test_agents_declares_native_delegation_defaults():
    agents = _read("AGENTS.md").lower()

    assert "native subagents or native delegation surface" in agents
    assert "for codex, that runtime surface is `specify team`" in agents


def test_guidance_docs_explain_agent_marker_and_current_agents_contract() -> None:
    readme = _read("README.md")
    quickstart = _read("docs/quickstart.md")
    agents = _read("AGENTS.md")

    for content in (readme, quickstart):
        assert "[AGENT]" in content
        assert "independent from `[P]`" in content

    assert "AUTONOMY DIRECTIVE" in agents
    assert "native subagents or native delegation surface" in agents.lower()
    assert "specify -> plan" in agents.lower()
    assert "sp-test" in agents.lower()
    assert "specify team" in agents.lower()


def test_guidance_docs_list_auto_learning_and_implement_closeout_helpers() -> None:
    readme = _read("README.md").lower()
    quickstart = _read("docs/quickstart.md").lower()

    for content in (readme, quickstart):
        assert "specify learning capture-auto" in content
        assert "specify implement closeout" in content


def test_guidance_docs_describe_sp_test_as_execution_backed_testing_bootstrap() -> None:
    readme = _read("README.md").lower()
    quickstart = _read("docs/quickstart.md").lower()

    for content in (readme, quickstart):
        assert "manual validation" in content
        assert "coverage baseline" in content
        assert "bundled language testing skills" in content
