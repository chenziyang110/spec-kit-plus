---
name: "spec-kit-workflow-routing"
description: "Use when working inside a Spec Kit Plus repository and the user asks whether a structured sp-* workflow would help, or when a manually invoked sp-* workflow needs routing context."
origin: spec-kit-plus
---

# Spec Kit Workflow Routing

This repository's explicit `sp-*` workflow skills are structured entrypoints that
users normally invoke manually. This passive skill helps recommend a workflow or
interpret a manually invoked workflow; it should not auto-enter a workflow during
ordinary chat or coding. When giving a user an explicit next-step invocation, use
the projected invocation placeholder, such as `{{invoke:specify}}`, rather than
assuming one universal slash-style syntax.

## Workflow Recommendation Discipline

Do not auto-enter an `sp-*` workflow unless the user invokes it. For ordinary
natural-language tasks, answer or work in the current mode while using always-on
project cognition and Project Learning when they matter. You may recommend a
workflow when it would materially improve the outcome.

If the user already invoked an `sp-*` workflow, treat the routing check as
complete and proceed under that workflow's generated contract.

When there is even a 1% chance the current request is asking you to interpret,
continue, or recommend a structured workflow, complete route selection before any response or action,
including a clarifying question, file read, or shell command. The goal is to
route into the right active `sp-*` workflow when one is already invoked, or to
recommend the smallest safe workflow route without silently entering it when ordinary
chat or coding is enough. This command-routing rule does not authorize product-scope minimization.

## Command Surface Discipline

Treat the live `specify --help` output as the only authoritative CLI command
surface.

Before suggesting or running a `specify <subcommand>` invocation, verify that it
exists in `specify --help` or `specify <subcommand> --help`.

Do not invent, paraphrase, or "normalize" unsupported CLI names such as
`specify create-feature`.

Feature creation must stay on `{{invoke:specify}}` plus the generated
create-feature script at `.specify/scripts/bash/create-new-feature.sh` or
`.specify/scripts/powershell/create-new-feature.ps1`, not an imagined
standalone branch-creation command. Default feature workspace names use
`YYYY-MM-DD-<slug>`; numeric prefixes are legacy and require the script's
explicit numeric option.

## Complementary Passive Skills

- `spec-kit-project-cognition-gate` is the brownfield advisory navigation layer.
  Workflow routing can recommend a route or explain a manually invoked `sp-*`
  workflow, while the cognition layer helps decide whether an existing-code task
  should treat map maintenance as follow-up or continue with live evidence.
- `spec-kit-project-learning` is the shared memory layer that applies after routing.
  Once the active workflow is selected, that complementary skill defines the
  workflow-specific learning-start and learning-capture behavior instead of leaving
  those triggers implicit.
- `spec-kit-discussion-handoff-review` owns review discipline for
  `sp-discussion` handoff packages. Use it when checking whether
  canonical `handoff-to-specify.json` can become or remain
  `handoff-ready`, or when a ready closeout summary needs review-quality
  context instead of only file paths and counters.

## Recommendation Rules

- The default generated path is `sp-specify -> sp-plan -> sp-tasks -> sp-implement -> sp-accept`. `sp-checklist` and `sp-analyze` remain visible optional diagnostics, but they are not default quality nets for clean workflow progress. There is no visible separate review route between `sp-tasks` and `sp-implement`; implementation review is embedded in `sp-implement`. `sp-accept` is a separate human product-acceptance stage after technical closeout, not a code-review route.
- Use `sp-fast` for trivial, local, low-risk fixes that touch at most 3 files and do
  not cross a shared surface.
- Use `sp-quick` for bounded work that is still small, but no longer trivial.
- `sp-quick` performs one Understanding Checkpoint before substantive execution for a raw quick request. A user-confirmed discussion contract with no quick-stage `semantic_delta` reuses its confirmed digest instead of asking again. When a checkpoint is needed:
  render the fixed Quick Checkpoint Markdown table with
  `| Decision to confirm | Current understanding |` and user-owned rows for
  request/outcome, visible result, scope, recommended approach,
  assumptions/risks, completion evidence, and reconfirmation trigger. Keep
  technical execution agent-owned. For applicable UI work, append the
  independent UI Confirmation proposal and ask once for both decisions before
  code edits, broad repo analysis, delegation, or validation commands continue.
  Freeform prose or bullet-only confirmations do not satisfy this gate.
- Use `sp-auto` when repository state already records the recommended next step
  and the user wants to continue without naming the exact workflow manually.
- In `sp-auto` routed mode, safe bounded questions and confirmations with one
  recommended/default answer should auto-accept that answer and continue; if the
  answer is not safe to assume, report the blocker and a self-unblock
  recommendation instead of waiting silently.
- Use `sp-ask` before `sp-discussion` when the user wants a read-only project
  question answered with evidence from live files, templates, docs, generated
  state, memory, or project cognition before choosing an action workflow.
  `sp-ask` reads project evidence and answers; it does not write state, create
  handoffs, run tests, run builds, or edit files. Same-topic follow-ups should
  reuse the prior evidence set when it still applies, normalize localized or
  project-slang terms into project vocabulary, and separate proven facts from
  evidence-derived inferences.
- Use `sp-discussion` before `sp-specify` when the request is a rough idea, not-yet-ready requirement, unsettled product direction, or depends on unclear project boundaries. `sp-discussion` is the high-throughput senior product-engineering advisor route: the visible conversation gives the recommended direction, plain-language reason, usable draft or next design step, default next step, and override path, while frontstage / backstage separation keeps state accounting backstage. It uses checkpoint persistence, does not persist every turn, continues by default, does not ask for continuation when a safe default exists, performs a Truth Pass before project-specific technical advice, maintains a Discussion Compass, and applies proactive implication mapping so adjacent implications are surfaced without one-point-at-a-time follow-up loops.
- Use `sp-design` when the request is high-risk UI or design-system work: new product UI, redesign or rebrand, core workflow experience, multi-platform design decisions, high-visibility customer-facing surfaces, or missing/contradictory `DESIGN.md` for a UI-heavy request. Recommend `{{invoke:design}}` rather than letting implementation invent styling. Small UI work can proceed with a recorded soft risk when it is a narrow internal form change, copy or state improvement, already-covered component variant, or low-risk CLI/TUI wording refinement.
- Use `sp-specify` with the UI reference artifact lane when a feature request includes concrete UI reference input for that feature. Use `sp-design` only when the project-wide design system itself is missing, contradictory, or being changed.
- `sp-discussion` must run the Context Boundary Gate before project-specific technical options, affected-file claims, or handoff generation.
- For cross-project or transfer requests, lock the target project root before technicalizing.
- Do not route to `sp-split`; broad directions either become one unified handoff with capability map, sequence, dependencies, deferred scope, and reopen conditions, or stay in `sp-discussion`.
- A valid explicit handoff from discussion is one canonical agent-only JSON contract: `handoff-to-specify.json`, with self-review and user confirmation. Route that contract to `sp-specify` by passing the JSON path or discussion slug; when exactly one unconsumed `handoff-ready` discussion exists, `sp-specify` may consume it directly. Before that ready contract exists, do not tell the user to run `sp-specify`; the next action is `sp-discussion` handoff creation, review, or repair. `specification-input.md` is not a substitute handoff. `sp-specify` must validate ready planning status, user-confirmed quality gate status, zero hard unknowns, zero open conflicts, and source-contract integrity before feature creation.
- When asked to review a discussion handoff, apply
  `spec-kit-discussion-handoff-review`: return `approve`,
  `request-changes`, or `blocked`, apply the ready summary quality check,
  and keep final closeout as a concise handoff card rather than a minimal
  "files updated, next command" summary.
- Use `sp-specify` for new capability, behavior, or requirement changes that are
  ready for an aligned spec package before implementation.
- Use `sp-prd-scan -> sp-prd-build` when an existing repository needs a current-state PRD suite reverse-extracted from code, docs, tests, routes, UI/API surfaces, and project cognition evidence. Treat that pair as the canonical heavy reconstruction PRD lane, a peer workflow path to `sp-specify`, not as a pre-plan requirement, and do not automatically hand off to planning.
- Require the PRD lane to follow `subagent-mandatory` scan semantics for
  substantive runs, carry contract artifacts such as `config-contracts.json`,
  and keep critical claims blocked until `L4 Reconstruction-Ready`.
- Treat `sp-prd-build` as a build-only compilation step: it must not reread the repository, and it must block completion when critical evidence gaps remain.
- Treat `sp-prd` as a deprecated compatibility alias that must route into the
  canonical `sp-prd-scan -> sp-prd-build` flow instead of acting as the primary
  reverse-PRD lane.
- Use `sp-clarify` when an existing spec package needs deeper analysis before
  planning can safely proceed.
- Use `sp-deep-research` when the requirements are clear but feasibility, external
  evidence, optional multi-agent research, or a disposable demo is needed to prove
  the implementation chain before planning. It must write a Planning Handoff for
  `sp-plan`; skip it for minor changes to already-proven project behavior.
- Treat `sp-research` as a compatibility alias for `sp-deep-research`. It must
  route into the canonical feasibility gate and must not create separate
  `sp-research` artifacts or workflow state.
- Use `sp-plan` only after a valid spec package exists.
- Use `sp-tasks` only after planning artifacts are ready.
- Use `sp-implement` after `sp-tasks` produces canonical `task-index.json` or a light direct task list and records `/sp.implement`. `sp-implement` selects leader-direct or delegated execution per task, compiles delegated packets just in time, runs event-triggered review, and records result/validation/review/recovery once in the task lifecycle record. Product goal, scope, architecture, required evidence, `MP-*`, `CA-###`, and feasibility conflicts route back to their upstream owner.
- Route planned implementation to `sp-implement`; review is embedded and event-triggered by drift, parallel joins, validation failure, obligation conflicts, or the review-window threshold. Repair only task-layer defects locally and route upstream truth defects to their owner. Do not route to a separate public review command or require task briefs, review packages, a duplicate ledger, and branch review for every task.
- Use `sp-accept` after successful implementation closeout. It assumes the human remembers nothing, restores product context, guides one real-entrypoint step at a time, persists explicit human observations, and never edits source. A failed observation routes to implement/debug or upstream requirements; technical checks and silence never count as human PASS.
- Use `sp-debug` for regressions, bugs, broken behavior, or incident-style recovery.
- `sp-debug` is complexity-based: small focused investigations may stay
  leader-inline, while broad, independent, or parallel evidence lanes use
  subagent-assisted execution. If the next safe step is unavailable, unsafe, or
  cannot be packetized, record the blocked state instead of forcing delegation.
- Use `sp-map-update` before other workflow steps when project cognition runtime
  coverage is stale or too weak for a localized touched area and the user wants
  map maintenance first, including ordinary existing-baseline gaps.
- If `baseline_kind=greenfield_empty`, continue with workflow artifacts and live requirements. Do not recommend map-scan -> map-build solely because the graph has no paths.
- Use map-update for ordinary existing-baseline gaps. Use map-scan -> map-build
  only for brownfield first/missing/unusable baseline, schema failure, schema v1
  or old broad-schema rebuild-required readiness, zero active-generation
  path_index rows outside `greenfield_empty`, missing or invalid `alias_index`,
  `explicit_rebuild_requested`, or `baseline_identity_invalid`.
  Schema v5 is current-only. The runtime does not migrate schema v4 or older
  databases and does not archive or replace them. Remove the incompatible project-cognition.db
  explicitly before `sp-map-scan -> sp-map-build` with the current binary.
- `sp-map-update` is for manual/external maintenance as the external/manual maintenance entrypoint for user edits, interrupted workflow repair, explicit map maintenance, and follow-up repair. A source-changing `sp-*` workflow does not hand off its own verified changes to `sp-map-update`; it runs inline project cognition update during closeout from its workflow-owned changed paths, affected surfaces, and verification evidence. In shared routing summaries, sp-map-update is for manual/external maintenance.
- Workflow-owned mutation closeout is not an external map-maintenance handoff. If the active workflow changed project-related source, runtime, templates, generated assets, config, tests, state contracts, or behavior-bearing docs, closeout must run `project-cognition closeout-plan --workflow "$ACTIVE_WORKFLOW" --format json` before recording inline project cognition update data.
- When `DELTA_SESSION_ID` exists, pass `--delta-session "$DELTA_SESSION_ID"` to `closeout-plan`. Fill fields listed in `required_agent_fields` from live evidence; optional payload/delta fields such as `known_unknowns` and `boundary` are populated only when evidence supports them. Follow `update_mode=delta_session` by completing `delta_append_draft.argv_prefix` with evidence placeholders, appending the workflow closeout delta event, then running structured `update_argv`. Follow `update_mode=payload_file` by writing the completed `payload_draft`, then running structured `update_argv`. The display-only `update_command` and display-only `delta_append_command` placeholders are not execution strings.
- Use `known_unknowns` only for blockers that make the cognition update unsafe to trust. If the working tree contains unrelated dirty/untracked paths and the workflow uses explicit workflow-owned paths, record that as `confidence_notes` or `boundary.initial_dirty_paths`, not as a blocking `known_unknowns` item.
- Before update recording, resolve `unknown_path_dispositions` by setting `agent_disposition` to `adoptable`, `review_only`, `ignored`, or `blocking_known_unknown`. Verified `adoptable` paths do not become blocking `known_unknowns`. Only `blocking_known_unknown` dispositions become payload or delta known unknowns. `agent_disposition=adoptable` is an agent accounting decision, not proof that runtime indexing already succeeded; after `update_argv` runs, inspect `result_state`, `adopted_paths`, `review_paths`, `minimal_live_reads`, and `partial_refresh_reasons`.
- Clean closeout keys on `result_state`, not `status=ok`, `update_id`, `last_update_id`, or freshness alone; `recorded` is legacy recorded-only partial/blocked output. If `partial_refresh_reasons` includes `missing_passing_verification_result`, repair the payload or delta evidence and rerun `update_argv` before final closeout instead of routing to `sp-map-update`. Never run the `complete-refresh` or `clear-dirty` helper after `result_state=partial_refresh`, `needs_rebuild`, `blocked`, or legacy `recorded`. Use `project-cognition mark-dirty --reason "workflow-closeout-failed" --format json` only when planner/update is unavailable, fails before recording useful update data, cannot safely identify workflow-owned scope, is blocked by runtime state, or verification/workflow completion is not trustworthy. Workflow-owned mutation closeout is not external map maintenance. Dirty state is fallback-only after inline update cannot complete.
- Use `sp-analyze` only for optional diagnostics, explicit user requests, or persisted legacy `/sp.analyze` state.
- Use `sp-explain` when the user needs a plain-language explanation of current
  artifacts or runtime state.
- For brownfield debug or extension work, the selected workflow must consume the
  project cognition runtime and capability truth layer when a capability or
  symptom route exists; do not jump straight to broad repository search.
- Default project cognition intake is `project-cognition compass --intent <intent> --query="$ARGUMENTS" --format json`.
  Consume the packet in this order:
  1. Read top-level `epistemic_contract` first. Require `graph_role=route_candidate_only`, `fact_source_of_truth=live_repository`, `live_verification_required=true`, `graph_only_claims_allowed=false`, and `unverified_claim_action=withhold`.
  2. Read top-level `minimal_live_reads` and use those files as the bounded first live evidence route.
  3. Then use lane-level `first_pass_paths` for reasons, evidence hints, verification hints, follow-up surfaces, and `before_fix_claim` checks.
  4. Read lane-level `claim_refs` only as compact route candidates. `route_confidence` is scoped by `confidence_scope=route_candidate`; inspect `state`, `freshness`, and `stale`, and require live verification before using a claim as repository truth.
  5. Treat `coverage_diagnostics` as confidence and closeout signals, never as route candidates.
  6. Treat `expansion_ref` as a normal continuation path. Run `project-cognition expand --id <id> --section claim_evidence --format json` when an active claim needs bounded `source_path`/`span` evidence; advanced `project-cognition query` may also return top-level `claim_signals` with bounded evidence refs.
  7. Do not infer final edit scope from `minimal_live_reads`, `first_pass_paths`, `claim_refs`, `claim_signals`, or `claim_evidence`.
  Compass applies graph claims only as a bounded rerank after repository-backed route eligibility is established. `match_score` remains the eligibility score; lane `claim_ranking.adjustment` may only move an already-matched candidate by `+1` for fresh `supported`/`verified_in_graph_generation`, `-1` for stale, or `-2` for contradicted. Claims cannot create candidates and cannot replace live verification. When `coverage_diagnostics` contains `stale_claim_signal` or `contradicted_claim_signal`, treat the packet as `usable_with_review`, follow `reconcile_claims_with_minimal_live_reads`, and complete the lane-specific refresh or reconciliation action against the live repository.
  For decisive claim-specific evidence, provide only reconciliation intent: workflow, stable `claim_id`, reason, repository-relative `source_path`, bounded line `span`, `supporting` or `contradicting` role, and optional claim-specific verification. Run `project-cognition claim-reconcile prepare --input <intent.json> --format json`; the runtime owns every integrity field and the prepared packet path. Execute the returned `apply_argv` exactly (`project-cognition claim-reconcile apply --input <prepared_packet_path> --format json`). Generic workflow verification is insufficient. On ready, rerun Compass once; on partial or blocked, withhold the claim.
  The `epistemic_contract` cannot authorize source changes and cannot prove current behavior. Carry `epistemic_contract` into the selected workflow, withhold unverified claims, and let contradictory live evidence override the route candidate.
  Graph claims are indexed assertions. Even `verified_in_graph_generation` is only an active graph-generation state, not current repository truth; graph claims cannot authorize source changes and cannot set workflow `claim_ready=true`. Route with them, but require bounded live evidence and the separate workflow final-claim gate before any root-cause, fixed, completed, or release-safe claim.
  Readiness values are `query_ready`, `review`, `needs_rebuild`, `blocked`, and `unsupported_runtime`. Compass-specific advice is in `compass_state` and `recommended_next_action`.
  When `compass_state=needs_semantic_intake`, the agent writes `semantic_intake` from project vocabulary and reruns compass with `--semantic-intake-file`, or uses the advanced `lexicon -> semantic_intake -> query` path when explicit concept decisions are needed.
  Advanced routing remains available as `project-cognition lexicon --mode catalog`, agent-authored `semantic_intake` and `concept_decisions`, then `project-cognition query --query-plan`. Use it when the first compass packet is too draft-like, a workflow needs explicit concept decisions, or coverage cannot be resolved from the default packet.
  The current query contract is `claim_retrieval_contract_version=2` and `candidate_universe_version=2`; carry the latter from lexicon into every explicit query plan. Never parse missing or non-current versions as legacy input; rerun lexicon or compass with the current binary and repair the install if needed.
  The advanced path still requires `normalized_query`, `intent_facets`, `negative_constraints`, `alias_interpretations`, `selected_concepts`, `rejected_concepts`, `concept_decisions`, `covered_facets`, `missing_facets`, `match_sources`, `lexicon_generation_id`, `expanded_queries`, `repository_search_terms`, and facet coverage; do not trust top similarity alone.
  If the query command reports query-plan diagnostics, preserve its `warnings`, `repair_hints`, normalized `query_plan`, structured `errors`, and `expected_shape` so the workflow can repair the plan instead of ending on a raw parser exception.
  Agent-owned semantic normalization is mandatory for the advanced path. The raw lexicon ranking and `agent_normalization` are only bootstrap signals for retrieving the alias catalog and candidate universe; they are not route decisions. Raw lexicon ranking is only a bootstrap. Treat `agent_normalization.required=true` as a non-intelligent CLI reminder to write `semantic_intake` from the alias catalog (action: write_semantic_intake_from_alias_catalog). If `agent_normalization` is omitted, `omitted => required=false`: treat it as `required=false`; omission does not make raw lexical ranking authoritative. If raw `concept_candidates` are all `score=0`, or the prompt is localized, mixed-language, CJK, colloquial, symptom-first, or mixed-language or CJK text, do not stop at the raw score. CJK or mixed CJK/ASCII input still requires agent normalization even when positive raw lexical matches exist because embedded project tokens do not translate the surrounding user language. Extract embedded project terms such as command names, UI labels, file stems, state names, adapter names, and skill or package identifiers from the user's wording and the alias catalog. The agent still owns translation; `agent_normalization` is advisory guidance, not a route decision. Put those translated terms into `normalized_query`, `alias_interpretations`, `intent_facets`, `expanded_queries`, and `repository_search_terms`, then select or reject concepts by facet coverage.
  Before source search, write project-language search terms derived from the alias catalog, `semantic_intake`, selected candidates, and route metadata. Write them as `repository_search_terms`; include component names, state names, file names, command names, UI labels, and route names when present. Do not search only the raw user words. Use these project-language search terms before broad repository search.

## Consequence-Aware Routing

Recommend against `fast` when a request triggers the Senior Consequence Analysis Gate. Use `quick` only for bounded consequence work with durable `STATUS.md` fields. Recommend `discussion` or `specify` when lifecycle semantics, running work, destructive policy, shared state, downstream consumers, or acceptance criteria need product decisions. Recommend `debug` when the issue is a failure with unknown root cause.

## User Invocation Examples

Use canonical workflow names above when describing routing semantics, workflow
state, or artifact handoffs. Use projected invocation placeholders when telling a
user what to type:

- New capability alignment: `{{invoke:specify}}`
- Read-only project Q&A: `{{invoke:ask}}`
- Pre-spec discussion: `{{invoke:discussion}}`
- Existing-project PRD extraction: `{{invoke:prd-scan}} -> {{invoke:prd-build}}`
- Planning handoff: `{{invoke:plan}}`
- Task generation: `{{invoke:tasks}}`
- Implementation execution: `{{invoke:implement}}`
- Debugging route: `{{invoke:debug}}`
- Localized map refresh detour: `{{invoke:map-update}}`
- Full map rebuild detour: `{{invoke:map-scan}} -> {{invoke:map-build}}`

## Subagent Routing

- Use native subagents for bounded delegated work after the owning workflow
  selects or permits delegation.
- Dispatch `one-subagent` when one safe lane is ready.
- Dispatch `parallel-subagents` when two or more independent lanes can run
  concurrently.
- Record a fallback or blocked reason when a workflow-selected delegated lane
  cannot proceed because delegation is unavailable, unsafe, or not packetized.
- Do not use old strategy labels as routing choices.
- `sp-fast` is the main leader-inline route; use it only when the work is
  trivial, local, low risk, and does not benefit from delegated verification.
- For `sp-quick`, complete the one-time Understanding Checkpoint before
  substantive execution; after confirmation, use delegated lanes when they are
  safe and packetized.
- For `sp-debug`, choose leader-inline for small focused investigations and
  subagent-assisted execution for broad, independent, or parallel evidence
  lanes.
- For `sp-map-scan`, `sp-map-build`, and `sp-implement`, leader + subagents is
  the default execution shape for independent bounded lanes when the current
  runtime supports delegation.
- Use `sp-teams` only when Codex work needs durable team state, explicit join-point
  tracking, or lifecycle control beyond one in-session subagent burst.

## Behavioral Rules

- Do not replace a user-invoked `sp-*` workflow with ad hoc implementation.
- If multiple workflow recommendations seem plausible, suggest the smallest safe workflow route and make the next escalation trigger explicit.
- Complete-first scope preservation: workflow-route minimization is only about choosing the command surface. Preserve the user's complete user-confirmed scope; do not shrink scope toward a smaller MVP, pilot, prototype, first-story release, future-work delivery slice, agent-invented `v1/v2`, or agent-invented `P0/P1` unless the user asked for that shape or confirmed it after a named constraint/trade-off. Complexity alone is not a valid reason to defer or block ordinary work; use sequencing, dependencies, batches, join points, refinement checkpoints, and validation paths. Runtime capability limits are blockers only under the adaptive execution policy for heavy, safety-critical, or unpacketizable work, and they do not reduce scope.
- If the user intent is effectively "continue with the recommended next step",
  follow the uniquely recorded canonical `next_command` directly. Use `sp-auto`
  only when the user explicitly chooses automatic state reconciliation or no
  unique canonical next command can be proven safely.
- Clean completed `sp-tasks` state with `/sp.implement` routes directly to
  `sp-implement`; it does not need an `sp-auto` hop.
- Keep `sp-*` workflows as visible optional entrypoints. This passive skill should
  recommend them, not become a competing workflow.
- If the user is already invoking the correct `sp-*` skill, do not redirect.
- Do not skip from `sp-discussion` into `sp-specify` unless the user explicitly
  requests handoff and the ready JSON contract exists.
- If a required next step is a user-invoked workflow entrypoint rather than an
  in-workflow action, stop the current flow and tell the user exactly what to run.
- Do not self-execute a different explicit `sp-*` workflow just because the current
  workflow discovered a stale gate or missing prerequisite. Hand off by telling the
  user to run the projected invocation, then wait.

## Red Flags

- You are about to auto-enter an `sp-*` workflow that the user did not invoke.
- You are presenting a workflow recommendation as mandatory when ordinary chat,
  coding, or review would satisfy the request.
- The user is exploring rough requirements, but you did not mention `sp-discussion`
  as an optional structured path.
- You are treating "small" as a reason to recommend `sp-fast` automatically instead
  of staying in the user's requested mode.
- You found independent lanes but have not considered `one-subagent` or
  `parallel-subagents` dispatch.
