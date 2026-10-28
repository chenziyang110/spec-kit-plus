Trigger: when gathering evidence, reproducing failure, reading logs/tests/source, or building the investigation contract.

Purpose: preserve investigation protocol, mandatory intake contract, reproduction-before-fix, observer framing, evidence plan, and related-risk review.

Preserved Contract: debug must prove reproduction and evidence before forming or acting on root cause.

Session mutation contract: `SESSION PATCH <fields-or-sections>` means build the bounded same-checkpoint delta in memory. When one semantic boundary updates multiple debug-session frontmatter fields or sections and `api list` exposes `artifact.patch-batch`, prefer one `specify-runtime artifact prepare --path .planning/debug/[slug].md` plus one `specify-runtime artifact patch-batch --lease <lease-id>` that aggregates those updates. For a single target update, or on older runtimes, fall back to one leased `specify-runtime artifact patch` using `--frontmatter-json` or `--section`. Every state-oriented `record`, `set`, `populate`, `append`, or `write` instruction below means `SESSION PATCH`; never edit the Markdown file directly.

## Investigation Protocol

### Intake Inputs

Navigation hints are not read authorization. Queue `minimal_live_reads` and
other source/log/test routes during intake; execute them only after accepted
framing. Safe bounded diagnosis does not require repair confirmation.
Repair writes proceed only after confirmation and accepted framing, with exact
approved authority and fresh execution guards. A ready map waives neither gate.

Optional feature artifacts require a valid feature binding and an existing,
relevant artifact. Query only their needed sections through the artifact owner
after the evidence-read gates pass. Standalone Debug does not require a formal
feature package: do not create missing spec, plan, tasks, or context artifacts
or launch a specification workflow merely to satisfy a context checklist.
Missing optional inputs are recorded as not applicable, not fabricated.
A required artifact of an actually bound feature remains a real input gate.

- Query `.planning/debug/[slug].md` through `specify-runtime artifact show` before each resumed action; treat the returned state as the investigation source of truth.
- Query project cognition with `{{specify-subcmd:specify-runtime cognition compass --intent debug --query="$ARGUMENTS" --format json}}`. Read top-level `minimal_live_reads` first, then use lane-level `first_pass_paths` reasons, `verification_hints`, `followup_surfaces`, and `before_fix_claim`. Do not treat first-pass reads as the final edit scope. Use `specify-runtime cognition expand` only when the packet's coverage state or live evidence requires it. Use the advanced `lexicon -> semantic_intake -> query` flow only when `compass_state`, coverage diagnostics, localization, or live evidence requires explicit concept decisions. In that escalation, run `specify-runtime cognition query --query-plan "<query_plan_json>"` with `query_plan`, `semantic_intake`, `concept_decisions`, and facet coverage
- `understanding_confirmed: false` permits safe bounded diagnosis after the intake and observer gates: low-risk reproduction, existing log/source/test reads, and read-only evidence subagents. It blocks fix/source/test/harness/persistent instrumentation writes and fix-worker dispatch until the exact checkpoint decision is approved. Preserve separate external and destructive action gates.
- If truth ownership, competing truths, stale assumptions, or contradiction signals remain ambiguous, perform only the returned `minimal_live_reads` before continuing.
- [AGENT] If cognition freshness is `missing`, continue with live repository evidence when workflow policy allows degraded advisory navigation; recommend `{{invoke:map-scan}}`, then `{{invoke:map-build}}` only as follow-up brownfield first-baseline maintenance unless the user explicitly requested cognition repair or root-cause analysis truly cannot proceed without a usable baseline.
- [AGENT] If cognition freshness is `stale`, treat map output as advisory, continue with live repository evidence when workflow policy allows, and recommend `{{invoke:map-update}}` as follow-up maintenance only when the user requested cognition repair or stale coverage blocks the investigation.
- [AGENT] If cognition freshness is `support_drift`, continue with live repository evidence when workflow policy allows and `SESSION PATCH` the support-surface drift; do not reflexively route to `{{invoke:map-update}}`.
- [AGENT] If cognition freshness is `partial_refresh`, `SESSION PATCH` that refresh data exists but readiness did not pass; follow `recommended_next_action` as advisory unless the workflow truly cannot proceed.
- [AGENT] If cognition freshness is `possibly_stale`, inspect permitted change metadata and plan bounded live verification of affected coverage after framing. Record a follow-up `{{invoke:map-update}}` recommendation only where warranted; do not invoke map maintenance automatically. Ordinary existing-baseline gaps do not require a rebuild. A separate authorized rebuild must follow the runtime-returned action and its actual reasons, not a freshness label alone.
- Treat task-relevant cognition coverage as insufficient when the failing area is named only vaguely, lacks ownership or placement guidance, or lacks workflow, constraint, integration, or regression-sensitive testing guidance.
- [AGENT] If task-relevant cognition coverage is insufficient for the failing area, continue with live repository evidence when workflow policy allows and `SESSION PATCH` whether follow-up `{{invoke:map-update}}` with changed paths or affected surfaces is needed. Use map-update for ordinary existing-baseline gaps. Use map-scan -> map-build only for first/missing/unusable baseline, schema failure, schema v1 or old broad-schema rebuild-required readiness, zero active-generation path_index rows, missing or invalid alias_index, explicit_rebuild_requested, or baseline_identity_invalid; block only when the user requested cognition repair or the investigation truly cannot proceed without refreshed coverage.
- Use the debug cognition slice to identify likely truth-owning layers, adjacent workflows, and observability entry points before forming a hypothesis.
- When `ui_confirmation.applicable` is true, use an existing confirmed UI target
  baseline, or provisional source-backed baseline during diagnosis, only as the
  observation standard: preserve original references and intents, reproduce the
  real entry point at the relevant viewport/window and state, and capture
  pre-fix structure, visual, and runtime evidence. Provisional observations are
  not UI approval. Confirm the UI target together with the evidence-backed
  repair before mutation; do not redesign during diagnosis.
- For UI symptoms, record **UI Debug Mode** classification in the session:
  `visual/layout`, `UX/interaction` (including hover/focus/keyboard/loading/
  empty/error), and/or `taste/generic-look`, with issue, reason, and
  design-aware fix direction (hierarchy, density, feedback, anti-slop/DNA).
  Reproduce the failing state, not only the default happy path.
  Taste/generic-look issues still need evidence at the real entry point; do not
  "restyle" without a named failure mechanism.
- Query `.specify/memory/constitution.md` through `specify-runtime artifact show` if present before forming or validating a fix so the investigation honors project-level MUST/SHOULD constraints.
- Consume project rules and Learning through `learning start --command debug`; expand only selected records whose triggers match the failing area.
- In deep fallback, the leader schedules a **think subagent** when available, or records an authorized leader-inline fallback. The same intake-only evidence restrictions apply to either executor. Never wait for a Python graph engine to dispatch this work.
- During observer framing, the think subagent must not read source files, test files, log files, or feature-specific planning artifacts such as `spec.md`, `plan.md`, `tasks.md`, or `context.md`.
- The think subagent must not read test files or test outputs; save those for the investigator phase.
- The think subagent must not inspect logs or runtime output; keep the analysis at the system-map level.
- The think subagent must not run reproduction commands, test commands, or instrumentation.
- The think subagent uses only the user report plus the current system map to reason about likely owning layers, truth owners, workflow boundaries, and possible failure loops.
- If critical information is still missing during observer framing, ask at most one concise missing-information question before moving on.

{{spec-kit-include: ../../command-partials/common/pre-analysis-protocol.md}}

## Mandatory Intake Contract

All new `sp-debug` sessions follow this default intake path:

`Project Cognition Compass -> Map-Backed Minimum Intake -> Evidence Investigation -> Repair Confirmation -> Fixing -> Verifying -> Human Verify`

Deep fallback path:

`Stage 1A Causal Map -> Stage 1B Investigation Contract + Log Investigation Plan -> Evidence Investigation -> Repair Confirmation -> Fixing -> Verifying -> Human Verify`

Canonical stage map:

- `Default Intake: Map-Backed Minimum Intake`
- `Stage 1A: Causal Map`
- `Stage 1B: Investigation Contract + Log Investigation Plan`
- `Stage 2: Evidence Investigation`
- `Stage 3: Fix`
- `Stage 4: Verify`

Do not enter reproduction, log review, test inspection, source-code reads, or evidence collection until the session records all of the following:

- `causal_map_completed: true`
- `investigation_contract_completed: true`
- `log_investigation_plan_completed: true`
- `observer_framing_completed: true`

`understanding_confirmed` is not a diagnosis prerequisite. Before repair writes
or fix-worker dispatch, additionally require explicit approval of the current
evidence-backed repair checkpoint and its matching `confirmation_digest`.

Repeated failure does not reopen observer-shape choices. It upgrades downstream investigation strength only, including `root_cause` mode and stronger instrumentation requirements.

### Default Intake: Map-Backed Minimum Intake

- Use the returned project cognition compass packet as the default intake source when readiness is `query_ready` or `review`.
- Persist the selected capability/symptom, route pack, returned `minimal_live_reads`, competing truths, and coverage gaps through a fresh `specify-runtime artifact patch` lease before source-level work.
- Generate the smallest sufficient intake package:
  - primary map-backed candidate,
  - materially different contrarian candidate,
  - first probe,
  - existing logs or command output to inspect,
  - candidate-separating signals,
  - nearest-neighbor related-risk target.
- Persist the minimum package in the existing `Causal Map`, `Observer Framing`, `Investigation Contract`, `Log Investigation Plan`, and `Transition Memo` sections. Validate their substantive contents against the selected-mode Observer Gate before setting completion flags.
- `SESSION PATCH` `causal_map_completed: true`, `investigation_contract_completed: true`, `log_investigation_plan_completed: true`, and `observer_framing_completed: true` from this package only when the map clearly names an owner, boundary, or minimal read path.
- `SESSION PATCH` `skip_observer_reason: map-backed-minimum-intake` when the deep Stage 1A/1B subagents are not needed.
- Do not use broad repository reads to compensate for a vague map. If the query bundle lacks ownership, placement, constraints, regression-sensitive tests, or minimal reads, use the deep fallback below; a map-maintenance recommendation is not an automatic workflow switch.

### Deep Fallback Intake

When advisory cognition is absent or unusable, use report-grounded deep intake
under the existing Stage 1A -> Stage 1B restrictions. Mark unknown owners,
paths and state explicitly; candidate loops are hypotheses, not live facts.
Use the confirmed report and available permitted system context to supply
discriminating probes and falsifiers, then verify the complete deep framing
before opening evidence reads. Do not invent a map, claim graph freshness, or
mark an empty framing package accepted. If a user-owned fact is essential,
ask only for that missing fact. Do not invoke map maintenance automatically.
An absent map is different from an unavailable canonical artifact runtime:
recover that runtime through its owning bootstrap, never by direct state writes.

### Stage 1A: Causal Map (Think Subagent)

- This stage is **fallback/deep mode**, not the normal map-backed path. Inspect the persisted gate and its actual artifacts; the leader compiles the bounded Stage 1A assignment from this contract. No graph-engine callback is required.
- **Leader's responsibility**:
  1. Supply the confirmed report, available system-map context, explicit unknowns, allowed reads, and required causal-map fields. Missing map data stays unknown; never fabricate graph evidence.
  2. Dispatch through the available native subagent surface, or record an authorized leader-inline fallback with the same intake-only restrictions.
  3. Require a structured result. If the selected worker format uses prose plus a `---` YAML block, parse and validate that block in memory; malformed output is returned for bounded repair, not accepted by existence.
  4. Check every required field, family, candidate and falsifier against the assignment, then `SESSION PATCH` the accepted `causal_map`, including `dimension_scan` and `candidate_board`.
  5. Set `causal_map_completed: true` only after acceptance. Stage 1B depends on this accepted output and must not run concurrently with its producer.
- The think subagent produces a causal map based on the user report plus the current system map. It does NOT read source code, logs, or run commands.
- The causal map must include:
  - `symptom_anchor`
  - `closed_loop_path`
  - `break_edges`
  - `bypass_paths`
  - `family_coverage`
  - `candidates`
  - `adjacent_risk_targets`
  - `dimension_scan`
  - `candidate_board`
- The causal map candidates are the widened alternative cause candidates for the observer-framing phase.
- Cover at least 3 failure families.
- Produce at least 3 candidates.
- Produce at least 3 alternative cause candidates.
- Each family must include a falsifier, not just a plausible guess.
- Stage 1A is still intake-only fallback work: no source-code reads, test reads, log reads, or repro commands are allowed while `observer_framing_completed` is not `true`.

### Stage 1B: Investigation Contract + Log Investigation Plan

- After Stage 1A is accepted, the leader compiles the Stage 1B contract-planner assignment against that exact causal map and candidate board.
- **Leader's responsibility**:
  1. Supply the accepted Stage 1A output, its evidence basis, required fields below, and the same intake-only restrictions; use a native subagent or recorded authorized fallback.
  2. Check the returned structured result for complete candidate coverage, ordering, log intent and usable evidence routes. Repair missing rows before accepting the result.
  3. `SESSION PATCH` accepted `observer_framing`, `transition_memo`, `investigation_contract`, and top-level `log_investigation_plan` together at this semantic checkpoint where batch patching is supported.
  4. Set `investigation_contract_completed: true` and `log_investigation_plan_completed: true` only after the corresponding artifacts pass their contract.
  5. Set `observer_framing_completed: true` only after both dependent stages are accepted; a returned status or file's existence is not gate evidence.
- The contract planner does not widen the hypothesis space. It converts the causal map into:
  - `primary suspected loop`
  - `primary_candidate`
  - `contrarian_candidate`
  - `candidate_queue`
  - `related_risk_targets`
  - `transition_memo`
  - `top_candidates`
  - `log_investigation_plan`
- The contract planner must preserve candidate-board ordering and runtime-log intent instead of collapsing them into a generic probe note.
- Stage 1B must still leave the session with a clear `contrarian candidate`, a `recommended first probe`, and a transition memo that can automatically continue into evidence investigation.

### Stage 2: Evidence Investigation

- The transition memo comes from the selected accepted intake package: map-backed minimum intake or deep Stage 1B, whether delegated or produced by an authorized leader-inline fallback.
- **Leader's responsibility**: Validate and persist the selected package's `transition_memo` fields: `first_candidate_to_test`, `why_first`, `evidence_unlock`, and `carry_forward_notes`. Do not require a deep contract-planner result when minimum intake already satisfies the contract.
- After `SESSION PATCH` persists the selected accepted intake package and its gates pass, automatically continue into evidence investigation. Do not stop for confirmation unless human action is required.
- Treat the transition memo as the bridge between the outsider view and the investigator view. The later evidence phase must carry the observer framing forward instead of discarding it.

### Observer Gate
- Before evidence investigation begins, verify all of the following in the debug session:
  - `causal_map_completed: true`
  - `investigation_contract_completed: true`
  - `log_investigation_plan_completed: true`
  - `observer_framing_completed: true`
  - `Causal Map` satisfies the selected intake mode: map-backed minimum intake preserves its owner/boundary route, primary and contrarian candidates, first probe and candidate-separating signals; deep fallback additionally requires `dimension_scan`, `candidate_board`, at least three failure families/candidates and their falsifiers
  - Do not impose deep-only fields on a valid `map-backed-minimum-intake` package or redo accepted framing just to populate them
  - `Observer Framing` contains the required outsider-analysis fields
  - `Transition Memo` contains `first_candidate_to_test`, `why_first`, and at least one `evidence_unlock` entry
  - `Investigation Contract` contains `primary_candidate_id`, `candidate_queue`, and related-risk targets
  - `Log Investigation Plan` contains existing log targets, candidate signal mapping, and observability escalation guidance
- If any observer-gate item is missing, repair the owning map-backed intake, Stage 1A, or Stage 1B artifact before reading code, logs, tests, or running reproduction. Preserve unaffected accepted artifacts.
- No source-code reads, test reads, log reads, or repro commands are allowed while `observer_framing_completed` is not `true`.

### Stage 2A: Reproduction Gate
- `SESSION PATCH` expected behavior, actual behavior, reproduction steps, and observed errors before running the first repro.
- Confirm that the bug is reproducible through a command, script, or explicit manual sequence.
- If reproduction is not yet verified, continue bounded diagnosis of the missing signal; do not promote a root cause or enter fixing. Recover available local prerequisites rather than hand the first failure to the user.
- Bind every experiment to the current source revision or relevant file digests, worktree, environment, inputs/seed, exact command or manual sequence, expected failure signature, observed output/exit code, and evidence reference. Store these facts in existing `Symptoms`, `Evidence`, and `Resolution` sections, not a new state file.
- A harness/import/permission/timeout failure does not reproduce a different target defect. If that supporting mechanism is itself the confirmed target, its exact failing signature is valid target evidence. Otherwise repair the supporting cause, then rerun the original target check. Preserve both failures separately.
- For intermittent behavior, record attempts and outcomes under controlled inputs before and after the fix; one non-reproduction is not proof of resolution. Set a bounded diagnostic experiment budget with a next discriminating probe, not an arbitrary success count.

### Stage 2B: Log Review
- Inspect existing logs, error output, and test output before changing code.
- Logs are a first-class evidence source and existing logs come first.
- Treat logs as evidence, not background noise: if a log line materially changes the hypothesis space, add it in memory to the session `Evidence` section with its source path/command, then persist the complete section with `SESSION PATCH`.
- Identify whether the current observability already shows:
  - where the failure occurs,
  - which inputs or branches matter,
  - what external dependencies returned,
  - and what state changed immediately before failure.
- With a valid feature binding, query existing relevant `spec.md`, `plan.md`, and `tasks.md` through targeted `specify-runtime artifact show` calls. Apply the optional feature artifacts rule; do not invent feature context for standalone Debug.
- If `context.md` exists, query it through `specify-runtime artifact show --section` so locked decisions are not bypassed.
- For runtime bugs, use the investigation contract's `log_investigation_plan` log investigation plan to decide:
  - which existing log targets to inspect first,
  - which candidate-specific signals should appear there,
  - whether logs are sufficient,
  - and whether instrumentation or a user log request must happen before fixing.

### Required Framing Before Hypothesis
- Before committing to a root-cause theory, persist a **Truth Ownership Map** in the existing `Truth Ownership` section through a fresh `specify-runtime artifact patch --section` lease:
  - which layer owns the decision truth,
  - which layers only reflect or cache it,
  - and what evidence supports that ownership claim.
- Split state into **Control State** and **Observation State**:
  - `Control State` covers counters, queues, admission sets, scheduler slots, ownership sets, and other values used to make decisions.
  - `Observation State` covers UI status, logs, task tables, snapshots, event streams, and other externally visible projections.
- `SESSION PATCH` the expected **Closed Loop**:
  - input event -> control decision -> resource allocation -> state transition -> external observation
- Prefer hypotheses that explain the control-plane truth, not just the visible symptom layer.

### Stage 2C: Observability Assessment
- If the current logs cannot answer those questions, treat observability as insufficient.
- During `investigating`, inspect existing logs, tracing, and outputs first.
  Adding or refining persistent diagnostic logging, tracing, instrumentation, or
  a harness requires the bounded `diagnostic-enablement` checkpoint approval
  when no evidence-backed repair has been approved. Explain the known gap,
  exact diagnostic scope, risks, and verification before writing; rerun the
  reproduction to gather stronger evidence, then return to diagnosis and obtain
  separate `evidence-backed-repair` approval before production changes.
- If logs are insufficient during a runtime bug investigation, you cannot directly enter fixing until the work either extracts decisive signals from existing logs or records an instrumentation / user log request escalation.
- Prefer diagnostic logging that clarifies boundaries, inputs, branches, outputs, and state transitions.
- Prefer **decisive signals** over broad debug noise:
  - queue contents,
  - ownership sets,
  - running/admitted collections,
  - resource counters,
  - and the exact handoff points between decision layers.
- Bias your instrumentation to the active problem profile when one is apparent:
  - **scheduler/admission**: queues, running/admitted sets, slot counters, promotion handoffs
  - **cache/snapshot drift**: authoritative state versus cached state, invalidation timing, refresh paths
  - **UI projection**: source-of-truth state, publish boundary, transformed view-model state, render/polling output
- For runtime bug investigations where the leader cannot access the needed logs directly, produce a concrete user log request packet before fixing. Include the time window, target system, identifiers or correlation keys, exact log sources, and the expected candidate-separating signals.
- If two hypothesis/experiment cycles fail to converge, escalate observability explicitly. Prefer an available read-only discriminating signal; add instrumentation only when the exact approved diagnostic or repair authority and fresh execution guard allow it. Never treat repeated failure as new write permission.

### Stage 2D: Hypothesis Formation
- Form one specific, falsifiable hypothesis from the evidence.
- `SESSION PATCH` the hypothesis, the test to run, and the expected result into `Current Focus`.
- State how the hypothesis relates back to the observer framing board: does it confirm, refine, or eliminate one of the observer candidates?
- State why the hypothesis targets the owning layer or control state rather than a downstream projection.

### Stage 2E: Experiment Loop
- Run one experiment for the active hypothesis.
- Add the observed result to `Evidence` in memory and persist the complete section with `SESSION PATCH`.
- If the result disproves the hypothesis, add it to `Eliminated` in memory, persist the complete section with `SESSION PATCH`, and return to Observability Assessment.
- If the result confirms the failure mechanism, `SESSION PATCH` the root cause. With confirmed `diagnose only` authority, use Diagnosis-Only Delivery in `references/debug-state.md`; otherwise prepare the concrete evidence-backed repair checkpoint before fixing through the causal, RED and write-authorization gates.
- Before leaving this stage, `SESSION PATCH` which plausible causes were considered and which were ruled out so the session shows real causal spread instead of a single-path guess.
- `SESSION PATCH` any **rejected surface fixes** that improved symptoms without restoring the control loop, so future resumes do not mistake symptom relief for root-cause resolution.

### Stage 2F: Root Cause Confirmation
- Before entering fixing, be able to explain:
  - what failed,
  - why it failed,
  - why the active hypothesis is stronger than the eliminated alternatives,
  - which layer owned the broken truth,
  - which decisive signals ruled out the competing explanations,
  - whether the issue was in control state, observation state, or the boundary between them,
  - and what behavior change should resolve the full loop instead of only a local inconsistency.
- `SESSION PATCH` explicit causal coverage before fixing:
  - `alternative_hypotheses_considered`
  - `alternative_hypotheses_ruled_out`
  - `root_cause_confidence`
- Use `root_cause_confidence: confirmed` only when the current explanation is stronger than the ruled-out alternatives and the decisive signals directly support it.
- `SESSION PATCH` the root cause in structured form:
  - `summary`
  - `owning_layer`
  - `broken_control_state`
  - `failure_mechanism`
  - `loop_break`
  - `decisive_signal`
