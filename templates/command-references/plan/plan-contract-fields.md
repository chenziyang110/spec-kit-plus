Trigger: when writing `plan-contract.json`, rendering `plan.md`, or reporting planning completion.

Purpose: keep implementation design machine-actionable, traceable, and minimal for task generation.

Preserved Contract: task generation receives complete scope, architecture/interfaces, constraints, evidence, obligations, verification routes, and recovery without rediscovering design decisions.

## Canonical Plan Contract

Write `plan-contract.json` before rendering `plan.md`. Keep:

- source spec contract and revision;
- `semantic_delta` introduced by planning;
- route, intent, complexity, and confirmed delivery scope;
- the single versioned complete-first scope policy and valid deferrals;
- architecture/module decisions and interface consumes/produces map;
- global constraints and allowed optimization scope;
- task-relevant acceptance, `MP-*`, `CA-###`, UI/fidelity, and evidence refs;
- for UI work, the current work/surface/platform types, direction core, approved visual,
  reference intents, real content/image plans, and structure/visual/runtime
  evidence requirements;
- implementation target and boundary refs;
- conditional artifact refs for research, data model, contracts, and validation scenario;
- review risks, stop/reopen conditions, and compact agent transition to `sp-tasks`.

Do not copy the requirement contract, context capsule prose, evidence bodies, or full consequence analysis. Use stable refs and add only phase-owned decisions.

## Conditional Artifacts

- `research.md`: unresolved implementation-shaping research ran.
- `data-model.md`: new entities, persistence, data shape, or state transitions need independent design.
- `contracts/`: new external/API/protocol boundary needs an independent contract.
- `quickstart.md`: a representative end-to-end validation scenario materially reduces ambiguity; otherwise store it in the plan contract.

## Validation And Transition

Before ready status, validate scope preservation, interface completeness, target boundary, acceptance/obligation coverage, unresolved risks, required refs, and conditional artifact triggers. A deterministic failure returns field errors and recovery; a user-owned semantic change routes upstream.

The transition is agent-only and contains source ref, semantic delta, required refs, blockers, next action, and recovery when blocked. Human completion reporting summarizes the design outcome and next command without exposing internal bookkeeping.
