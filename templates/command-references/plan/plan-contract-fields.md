Trigger: when writing plan.md, research.md, plan-contract.json, workflow-state.md, or the completion report.

Purpose: preserve the full outline, artifact writing contract fields, completion fields, and cognition follow-up semantics.

Preserved Contract: plan-contract fields, dispatch fields, review-risk notes, and planning completion reporting remain unchanged.

## Outline

1. **Setup**: Run `{SCRIPT}` from repo root and parse JSON for `FEATURE_SPEC`, `IMPL_PLAN`, `SPECS_DIR`, `BRANCH`, and `FEATURE_DIR`.
   - If `FEATURE_DIR` is not already explicit, prefer `{{specify-subcmd:lane resolve --command plan --ensure-worktree}}` before guessing from branch-only context.
   - When lane resolution returns a materialized lane worktree, continue planning from that isolated worktree context rather than assuming the leader workspace is the only source of truth for this feature lane.
   - Set `WORKFLOW_STATE_FILE` to `FEATURE_DIR/workflow-state.md`.
   - [AGENT] Create or resume `WORKFLOW_STATE_FILE` before substantial planning analysis.
   - Read `templates/workflow-state-template.md`.
   - If `WORKFLOW_STATE_FILE` already exists, read it first and preserve still-valid `next_action`, `exit_criteria`, and `next_command` details instead of relying on chat memory alone.
   - Persist at least these fields for the active pass:
     - `active_command: sp-plan`
     - `phase_mode: design-only`
     - `allowed_artifact_writes: plan.md, research.md, data-model.md, contracts/, quickstart.md, plan-contract.json, planning/handoffs/*.json, planning/evidence-index.json, planning/checkpoints.ndjson, workflow-state.md`
     - `forbidden_actions: edit source code, edit tests, implement behavior, start execution from plan artifacts`
     - `authoritative_files: spec.md, alignment.md, context.md, plan.md, research.md, plan-contract.json, planning/handoffs/*.json, planning/evidence-index.json`
   - When resuming after compaction, re-read `WORKFLOW_STATE_FILE` before proceeding.
   - If native hook policy redirects a prompt-entry phase jump, return to `WORKFLOW_STATE_FILE`; repeated or explicit phase jumps are blocked by shared workflow policy.

2. **Ensure project cognition runtime exists and record planning advisory state**:
   - Check whether `.specify/project-cognition/status.json` exists.
   - If it exists, use the project cognition freshness helper for the active script variant to assess freshness before trusting the current project cognition baseline.
   - [AGENT] If freshness is `missing`, continue with live repository evidence when workflow policy allows degraded advisory navigation; recommend `{{invoke:map-scan}}`, then `{{invoke:map-build}}` only as follow-up brownfield first-baseline maintenance unless the user explicitly requested cognition repair or planning truly cannot proceed without a usable baseline.
   - [AGENT] If freshness is `stale`, record a planning advisory, continue with minimal live reads from the query result, and do not require `{{invoke:map-update}}` during artifact-only `sp-plan` work.
   - [AGENT] If freshness is `support_drift`, record a planning advisory about support-surface drift and continue only with evidence-backed reads; do not reflexively route to `{{invoke:map-update}}`.
   - [AGENT] If freshness is `partial_refresh`, record a planning advisory that the refresh was incomplete, preserve `recommended_next_action`, and continue only when query results plus minimal live reads are sufficient for implementation planning.
   - [AGENT] If freshness is `possibly_stale`, inspect the reported changed paths and reasons plus `must_refresh_topics` and `review_topics`. For artifact-only `sp-plan` work, record a planning advisory for any overlapping topics, review those topic files and minimal live reads, and continue without requiring `{{invoke:map-scan}}`/`{{invoke:map-build}}`.
   - Check whether `.specify/project-cognition/status.json` exists at the repository root.
   - [AGENT] If the project cognition runtime is missing, continue with live repository evidence when workflow policy allows degraded advisory navigation; recommend `{{invoke:map-scan}}`, then `{{invoke:map-build}}` only as follow-up brownfield first-baseline maintenance unless the user explicitly requested cognition repair or planning truly cannot proceed without a usable baseline.
   - Treat task-relevant coverage as insufficient when the touched area is named only vaguely, lacks ownership or placement guidance, or lacks workflow, constraint, integration, or regression-sensitive testing guidance.
   - [AGENT] If task-relevant coverage is insufficient for the current planning request, record a planning advisory, continue with minimal live reads and targeted planning assumptions, and do not require a project cognition refresh during `sp-plan`.

3. **Load context**:
   - Read `FEATURE_SPEC`
   - Read `FEATURE_DIR/brainstorming/handoff-to-specify.json` when present and treat it as the authoritative pre-plan truth package.
   - If `brainstorming/handoff-to-specify.json` contains `must_preserve`, treat those `MP-*` items as planning obligations, not background notes.
   - If `planning_gate_status` is not `ready`, stop and route back to `{{invoke:specify}}` or to the user conflict decision named by the handoff.
   - If `quality_gate.user_confirmed` or equivalent user-confirmed `quality_gate.status` is missing, stop and route back to `{{invoke:specify}}` or `sp-discussion` according to the recorded blocker.
   - If `handoff_goal` is missing or vague, stop and route back to `sp-discussion` for handoff refresh.
   - If `context_boundary` is incomplete, stop before structural planning.
   - If `target_project_root` is required but missing, stop before structural planning.
   - If hard unknowns or open conflicts remain, stop and report the named blocker.
   - If `target_project_root` differs from `current_project_root`, plan from the target project context. Current project's cognition is not proof of target-project implementation facts.
   - For cross-project implementation, artifact-only planning may proceed only with explicit minimal live reads, target path confirmation, and recorded risk when target cognition is stale or missing.
   - Must not tell the user to run current-project `{{invoke:map-scan}} -> {{invoke:map-build}}` to fix target-project coverage.
   - If any `conflicts` item has `status: open`, stop and ask the user to resolve the conflict before planning.
   - Read `plan-contract.json` when present and treat route, intent, complexity as authoritative planning inputs.
   - Read `FEATURE_DIR/alignment.md`
   - Read `FEATURE_DIR/context.md`
   - Read `FEATURE_DIR/references.md` if present
   - Read `FEATURE_DIR/brainstorming/handoff-to-plan.json` if present; preserve route, intent, complexity, and handoff constraints as planning inputs.
   - Read `FEATURE_DIR/deep-research.md` if present
   - Read `FEATURE_DIR/workflow-state.md` if present. When it exists, treat it as semantically required profile-aware planning context, not optional resume trivia.
   - Read `.specify/memory/constitution.md`
   - Read `.specify/memory/project-rules.md` if present
   - Read `.specify/memory/learnings/INDEX.md` if present
   - Open only linked learning detail docs relevant to planning so repeated workflow gaps, implementation constraints, and user defaults are not rediscovered from scratch
   - [AGENT] Query project cognition with `{{specify-subcmd:project-cognition compass --intent plan --query="$ARGUMENTS" --format json}}`. Read top-level `minimal_live_reads` first, then use lane-level `first_pass_paths` reasons, `verification_hints`, `followup_surfaces`, and `before_fix_claim`. Do not treat first-pass reads as the final edit scope. Use `project-cognition expand` only when the packet's coverage state or live evidence requires it. Use the advanced `lexicon -> semantic_intake -> query` flow only when `compass_state`, coverage diagnostics, localization, or live evidence requires explicit concept decisions. In that escalation, run `project-cognition query --query-plan "<query_plan_json>"` with `query_plan`, `semantic_intake`, `concept_decisions`, and facet coverage
   - If the topical coverage for the touched area is missing, stale, too broad, or task-relevant coverage is insufficient, record a planning advisory in the feature artifacts, inspect the minimum live files still needed to replace guesswork with evidence, and carry explicit assumptions or follow-up tasks instead of requiring a project cognition refresh during artifact-only planning work.
   - Read `templates/research-template.md`
   - Read `templates/workflow-state-template.md`
   - Load the copied IMPL_PLAN template
