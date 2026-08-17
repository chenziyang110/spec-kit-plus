Trigger: when writing `plan-contract.json`, rendering `plan.md`, or reporting planning completion.

Purpose: keep implementation design machine-actionable, traceable, and minimal for task generation.

Preserved Contract: task generation receives complete scope, architecture/interfaces, constraints, evidence, obligations, verification routes, and recovery without rediscovering design decisions.

## Canonical Plan Contract

Scaffold `plan-contract.json` through its artifact CLI owner, then fill targeted JSON pointers before patching named sections in the deterministic `plan.md` skeleton. Never submit or reconstruct the whole contract. Keep:

- source spec contract and revision;
- verified `deep_research_binding` when Deep Research exists, including the
  handoff ref, source hash, handoff hash, revision, claim, and consumed
  `PH-###` / `EVD-###` / `SPK-###` ids;
- `semantic_delta` introduced by planning;
- route, intent, complexity, and confirmed delivery scope;
- the single versioned complete-first scope policy and valid deferrals;
- architecture/module decisions and interface consumes/produces map;
- global constraints and allowed optimization scope;
- exact canonical acceptance refs for every specification criterion, followed by task-relevant `MP-*`, `CA-###`, UI/fidelity, and evidence refs;
- for UI work, the current work/surface/platform types, direction core, approved visual,
  reference intents, real content/image plans, and structure/visual/runtime
  evidence requirements;
- implementation target and boundary refs;
- conditional artifact refs for research, data model, contracts, and validation scenario;
- review risks, stop/reopen conditions, and compact agent transition to `sp-tasks`.

### Test Design Gate

Keep `test_design_gate.decision` as exactly `not_selected`, `selected`, or
`required`, with reason refs and the runtime-shaped `projection_binding`.
For `selected` or `required`, the binding is either entirely null while
production is pending, or all refs, SHA-256 values, source fingerprint, and
state revision are present and current; partial binding is invalid. Before Plan use,
run `specify-runtime test-design projection-verify --feature-dir <feature-dir>
--projection-ref <project-relative-ref> --expected-sha256 <sha256>`; omit
`--feature-dir` only for project scope. The projection is a canonical typed
pointer-only input consumed read-only. Plan must not author or patch the Test
Design publication, projection, cases, data, coverage, gaps, or audit. Missing
input needed by Plan routes to independent `sp-test-design`; otherwise the
all-null pending selection routes there after Plan. It does not require a
completed Plan. `not_selected` has no fabricated binding. The Plan binding
proves only Plan consumption, never Tasks authorization; Tasks requires a fresh
feature handoff, its own verified projection, and runtime task-index binding.
Avoid a Plan-contract basis/hash cycle.

Do not copy the requirement contract, context capsule prose, evidence bodies, or full consequence analysis. Use stable refs and add only phase-owned decisions.

### Deep Research Binding

When Deep Research ran, verify the runtime-published handoff before planning
consumes it. `plan-contract.json` must store one `deep_research_binding`
describing the accepted handoff:

- canonical handoff ref under `research/handoff-to-plan/`
- source runtime state ref and source hash
- handoff hash and revision
- accepted claim identifier
- ordered consumed `PH-###`, `EVD-###`, and `SPK-###` ids
- verification result and refusal reason when blocked

Do not bind directly to chat output or to `deep-research.md` alone. The
compatibility projection may help human review, but the runtime handoff and its
verification metadata are the canonical plan intake.

`acceptance_refs` is a fail-closed denominator, not a selected subset. For a
ready version-2 contract it must be the complete, unique, ordered list
`spec-contract.json#/acceptance_criteria/0..N-1`; no specification acceptance
criterion may be omitted, duplicated, renamed, or replaced with a prose label.

### Entrypoint Outcome Decisions

Query `spec-contract.json#/entrypoint_outcome_contract` through `specify-runtime artifact show`; when triggered, consume each preserved/adapted outcome through its existing `CA-###` refs. Do not copy the result inventory and do not add a parallel Plan outcome ledger. Put the technical design in `operational_consequence_decisions`; every referenced decision records `producer_result_ref`, `consumer_owner`, `state_transition`, `interaction_owner`, `interaction_policy`, `request_retention`, `retry_identity`, `cancel_behavior`, and non-empty `validation_refs`.

For a `recoverable-user-input` outcome, also record non-empty `security_constraints`. Explicitly distinguish prohibited unrelated shell/home/confirmation UI from interaction required to recover the operation. Planning is blocked when an active outcome CA has no consequence obligation or operational decision.

## Conditional Artifacts

- `research.md`: unresolved implementation-shaping research ran.
- `data-model.md`: new entities, persistence, data shape, or state transitions need independent design.
- `contracts/`: new external/API/protocol boundary needs an independent contract.
- `quickstart.md`: a representative end-to-end validation scenario materially reduces ambiguity; otherwise store it in the plan contract.

## Validation And Transition

Before ready status, validate scope preservation, interface completeness, target boundary, acceptance/obligation coverage, unresolved risks, required refs, and conditional artifact triggers. A deterministic failure returns field errors and recovery; a user-owned semantic change routes upstream.

The transition is agent-only and contains source ref, semantic delta, required refs, blockers, next action, and recovery when blocked. Human completion reporting summarizes the design outcome and next command without exposing internal bookkeeping.
