# Specification Quality Gate

**Purpose**: Define the mechanical and judgment-based checks that a spec artifact set must pass before being declared planning-ready. This gate is tiered — not every task requires every check.

## Artifact Contract Gate

Before applying the tiered quality checks, `specify-runtime validate spec` validates the current
`sp-specify -> sp-plan` artifact contract. This contract gate is mechanical and
planning-readiness oriented: it proves the required handoff surfaces exist and
do not record a planning blocker.

Canonical required artifacts:

- `spec-contract.json` as Agent-facing authority
- `spec.md` as the project-facing rendering

`alignment.md`, `context.md`, `references.md`, requirements diagnostics, and
pointer-only compatibility transitions are conditional. They are required only
when referenced by `spec-contract.json.artifact_refs` or when a legacy package
does not yet contain `spec-contract.json`.

Required canonical contract signals:

- `status: planning-ready`
- non-empty `target_need` and `acceptance_criteria`
- typed scope, constraints, decisions, semantic delta, capability-operation,
  obligation-ref, context-capsule, open-item, and artifact-ref fields
- `transition.status: ready`
- empty `transition.blockers`
- `transition.next_action: /sp.plan`

Legacy packages remain supported through the previous alignment/context,
workflow-state, requirements checklist, and compatibility handoff contract.

Blocking conditions:

- canonical required artifact missing or empty
- invalid or incomplete `spec-contract.json`
- planning-ready status or ready transition missing
- transition blockers remain open
- acceptance criteria are empty
- must-preserve refs are malformed or unstable

Warning-only conditions:

- semantic delta is non-empty but approved user review is not recorded
- an optional rendered view referenced by the contract is stale or missing

## Tier Selection

Choose the tier based on task classification and boundary sensitivity:

| Tier | Triggers | Checks |
|------|----------|--------|
| **light** | Bug fix, docs/config change, local refactor with no new capabilities | scout-summary, capability-triage, execution-mode |
| **standard** | New capability, cross-module change, any work with consumers or integration boundaries | light + change-propagation, non-functional, error-contract, config-effective-when, test-strategy |
| **deep** | Greenfield system, protocol/service boundary, security-sensitive, stateful/async behavior | standard + quantified NFR thresholds, full error contracts, all config effective-when |

## Gate Items

### 1. Context Capsule (light+)

The canonical context capsule carries only boundary refs, selected capability
refs, evidence refs, minimal live reads, validation routes, and stale
conditions. A separate `context.md` is needed only when the evidence has
independent project-review value. Legacy packages still use the structured
scout summary topics below:

- **Ownership & truth sources**: which modules own the touched area, where canonical state/behavior lives
- **Reusable assets**: existing components, services, hooks, or patterns that can be reused
- **Change-propagation hotspots**: which surfaces are likely affected by this change
- **Integration boundaries**: upstream/downstream dependencies and contract boundaries
- **Verification entry points**: where to find relevant tests, how to validate changes
- **Known unknowns**: stale evidence, weak mappings, observability gaps

**Machine check**: `specify-runtime validate spec` verifies keyword coverage across these 6 topic groups.

### 2. Capability Triage (light+, spec.md)

Every capability in the capability map must carry one of three state labels:

| Label | Meaning |
|-------|---------|
| **confirmed** / 已证明 | Direct evidence exists in the repository or prior work |
| **inferred** / 可推断 | Low-risk default based on mature industry patterns |
| **unresolved** / 未验证 | Requires feasibility proof before planning — route to `/sp.deep-research` |

At least 80% of capabilities must be labeled. Unlabeled capabilities imply incomplete analysis.

**Machine check**: `specify-runtime validate spec` counts capabilities and verifies label coverage.

### 3. Execution Mode (legacy packages)

Canonical specification quality is independent of whether discovery ran inline
or used read-only evidence lanes. Legacy packages may still record an execution
mode in workflow state or alignment for compatibility.

### 4. Change-Propagation Evidence (standard+)

A structured table mapping each change surface to its consumers:

| Column | Content |
|--------|---------|
| Change surface | The interface, model, config, or behavior being changed |
| Direct consumers | Modules that directly depend on the changed surface |
| Indirect consumers | Modules affected through transitive dependencies |
| Risk / compatibility | Type of breakage risk (BREAKING, MEDIUM, LOW) |

When the contract references a separate context view, it must have at least one
data row if the change has consumers. Otherwise stable evidence refs in the
context capsule are sufficient and planning resolves the detailed interface map.

**Machine check**: `specify-runtime validate spec` verifies that a change-propagation or impact section contains a data table.

### 5. Non-Functional Requirements (standard+, spec.md)

At least 2 of 4 NFR dimensions must be addressed:

- **Performance**: latency, throughput, startup time, resource usage
- **Security**: auth model, injection prevention, permission boundaries
- **Reliability**: fault tolerance, graceful degradation, recovery behavior
- **Observability**: logging, metrics, tracing signals

Dimensions with no special constraints should be recorded as "accepts standard engineering defaults."

**Machine check**: `specify-runtime validate spec` probes keyword presence for each dimension.

**Deep tier**: All 4 dimensions must have quantified thresholds, not just mentions.

### 6. Error User-Visible Contract (standard+, spec.md)

For each error or failure path described in the spec, the user-visible behavior must be declared:

- What does the end user see? (banner, toast, blank state, etc.)
- Can the user take action? (retry, cancel, fallback)
- What happens to in-flight data? (preserved, discarded, cached)

If error paths are described only as internal states or exception types, the contract is incomplete.

**Machine check**: `specify-runtime validate spec` heuristically compares error mentions to user-visible behavior mentions.

**Deep tier**: Every error path must have an explicit user-visible behavior contract.

### 7. Configuration Effective-When (standard+, spec.md or context.md)

Every configuration item must declare when changes take effect:

| Effective-When | Example |
|----------------|---------|
| immediate | Flow control threshold |
| next session | Shell path |
| after restart | Plugin directory |
| next process creation | PTY binary path |

Without effective-when declarations, planners may design stateful update mechanisms with race conditions.

**Machine check**: `specify-runtime validate spec` checks for effective-when keywords near configuration declarations.

**Deep tier**: Every configuration item must have an effective-when declaration.

### 8. Test Strategy per Capability (standard+, spec.md)

Each capability should carry a minimal test strategy note:

- Test type: unit, integration, contract, E2E
- Platform coverage: OS, browser, runtime variants
- Key scenarios that must be verified

This enables planners to estimate test effort during task decomposition.

**Machine check**: `specify-runtime validate spec` checks for test strategy keywords within capability sections.

## Artifact Review Gate (Conditional Human Review)

When semantic delta is non-empty or a user-owned decision remains unresolved, a human reviewer confirms:

- [ ] Planning Summary states a business outcome, not a documentation deliverable
- [ ] Gray areas were resolved or explicitly deferred with rationale
- [ ] Feasibility gate was evaluated per capability (not a blanket "not needed")
- [ ] The user explicitly reviewed and approved the changed decision set
- [ ] The recommended next command matches the actual state of the artifacts

## Tooling

- `specify lint --dir <FEATURE_DIR> --tier <light|standard|deep>` invokes the packaged `specify-runtime validate spec` gate
- Agents use `--format json`; compact output omits passing check names unless `--show-passes` is requested
- Exit code 0 = checks pass, 1 = checks fail or execution fails, 2 = invalid tier/format usage
- Items without the machine-check tag require human judgment only when their trigger applies
- The tool has zero runtime dependencies (single Go binary)
