# Specification Quality Gate

**Purpose**: Define the mechanical and judgment-based checks that a spec artifact set must pass before being declared planning-ready. This gate is tiered — not every task requires every check.

## Tier Selection

Choose the tier based on task classification and boundary sensitivity:

| Tier | Triggers | Checks |
|------|----------|--------|
| **light** | Bug fix, docs/config change, local refactor with no new capabilities | scout-summary, capability-triage, execution-mode |
| **standard** | New capability, cross-module change, any work with consumers or integration boundaries | light + change-propagation, non-functional, error-contract, config-effective-when, test-strategy |
| **deep** | Greenfield system, protocol/service boundary, security-sensitive, stateful/async behavior | standard + quantified NFR thresholds, full error contracts, all config effective-when |

## Gate Items

### 1. Scout Summary (light+, context.md)

The context file must contain a structured summary covering at least 3 of these 6 topics:

- **Ownership & truth sources**: which modules own the touched area, where canonical state/behavior lives
- **Reusable assets**: existing components, services, hooks, or patterns that can be reused
- **Change-propagation hotspots**: which surfaces are likely affected by this change
- **Integration boundaries**: upstream/downstream dependencies and contract boundaries
- **Verification entry points**: where to find relevant tests, how to validate changes
- **Known unknowns**: stale evidence, weak mappings, observability gaps

**Machine check**: `spec-lint` verifies keyword coverage across these 6 topic groups.

### 2. Capability Triage (light+, spec.md)

Every capability in the capability map must carry one of three state labels:

| Label | Meaning |
|-------|---------|
| **confirmed** / 已证明 | Direct evidence exists in the repository or prior work |
| **inferred** / 可推断 | Low-risk default based on mature industry patterns |
| **unresolved** / 未验证 | Requires feasibility proof before planning — route to `/sp.deep-research` |

At least 80% of capabilities must be labeled. Unlabeled capabilities imply incomplete analysis.

**Machine check**: `spec-lint` counts capabilities and verifies label coverage.

### 3. Execution Mode (light+, workflow-state.md or alignment.md)

The execution model must be explicitly recorded:

- `execution_model: subagent-mandatory` — subagents were used for substantive analysis
- `execution_model: single-agent` — executed without subagents; must include rationale

This preserves traceability of how the spec was produced and whether parallel cross-validation occurred.

**Machine check**: `spec-lint` searches for `execution_model` or `execution_mode` with a valid value.

### 4. Change-Propagation Matrix (standard+, context.md)

A structured table mapping each change surface to its consumers:

| Column | Content |
|--------|---------|
| Change surface | The interface, model, config, or behavior being changed |
| Direct consumers | Modules that directly depend on the changed surface |
| Indirect consumers | Modules affected through transitive dependencies |
| Risk / compatibility | Type of breakage risk (BREAKING, MEDIUM, LOW) |

Must have at least one data row if the change has any consumers.

**Machine check**: `spec-lint` verifies that a change-propagation or impact section contains a data table.

### 5. Non-Functional Requirements (standard+, spec.md)

At least 2 of 4 NFR dimensions must be addressed:

- **Performance**: latency, throughput, startup time, resource usage
- **Security**: auth model, injection prevention, permission boundaries
- **Reliability**: fault tolerance, graceful degradation, recovery behavior
- **Observability**: logging, metrics, tracing signals

Dimensions with no special constraints should be recorded as "accepts standard engineering defaults."

**Machine check**: `spec-lint` probes keyword presence for each dimension.

**Deep tier**: All 4 dimensions must have quantified thresholds, not just mentions.

### 6. Error User-Visible Contract (standard+, spec.md)

For each error or failure path described in the spec, the user-visible behavior must be declared:

- What does the end user see? (banner, toast, blank state, etc.)
- Can the user take action? (retry, cancel, fallback)
- What happens to in-flight data? (preserved, discarded, cached)

If error paths are described only as internal states or exception types, the contract is incomplete.

**Machine check**: `spec-lint` heuristically compares error mentions to user-visible behavior mentions.

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

**Machine check**: `spec-lint` checks for effective-when keywords near configuration declarations.

**Deep tier**: Every configuration item must have an effective-when declaration.

### 8. Test Strategy per Capability (standard+, spec.md)

Each capability should carry a minimal test strategy note:

- Test type: unit, integration, contract, E2E
- Platform coverage: OS, browser, runtime variants
- Key scenarios that must be verified

This enables planners to estimate test effort during task decomposition.

**Machine check**: `spec-lint` checks for test strategy keywords within capability sections.

## Artifact Review Gate (Manual)

In addition to the mechanical checks above, a human reviewer must confirm:

- [ ] Planning Summary states a business outcome, not a documentation deliverable
- [ ] Gray areas were resolved or explicitly deferred with rationale
- [ ] Feasibility gate was evaluated per capability (not a blanket "not needed")
- [ ] The user explicitly reviewed and approved the artifact set
- [ ] The recommended next command matches the actual state of the artifacts

## Tooling

- `spec-lint -dir <FEATURE_DIR> -tier <tier>` runs all machine-checkable items
- Exit code 0 = all mechanical checks pass; exit code 1 = failures present
- Items without the machine-check tag require human judgment
- The tool has zero runtime dependencies (single Go binary)
