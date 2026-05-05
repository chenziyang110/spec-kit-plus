# PRD Export Suite Guide: [PROJECT]

**Run ID**: [RUN_ID]
**Derived From**: `master/master-pack.md`
**Status**: Draft

This guide is the package navigation entry for the PRD export suite. `prd.md`
is the primary reader-facing PRD. All consequential claims should preserve
Evidence/Inference/Unknown labeling.

## What This Package Contains

- **Product**: [PROJECT]
- **Run ID**: [RUN_ID]
- **Project mode**: [ui | service | mixed]
- **Primary reader-facing PRD**: `prd.md`
- **Internal synthesis truth source**: `../master/master-pack.md`

## Recommended Reading Paths

### Quick Engineering Handoff

1. `prd.md` for product scope, capability overview, and unknown posture.
2. `runtime-behaviors.md` for current operational behavior and system interactions.
3. `verification-surface.md` for behavior locks and minimum regression checks.

### Interface and Integration Review

1. `prd.md` for the top-level product and boundary summary.
2. `integration-contracts.md` for dependencies and cross-system seams.
3. `protocol-contracts.md` for field-level or boundary-level exchange details.
4. `config-contracts.md` for runtime switches, defaults, and precedence.

### State and Failure Analysis

1. `prd.md` for the major user/system flows.
2. `state-machines.md` for state transitions, triggers, and recovery paths.
3. `error-semantics.md` for failure exposure and recovery behavior.

### Pre-Change Risk Assessment

1. `prd.md` for the current-state capability inventory.
2. `reconstruction-risks.md` for fidelity risks and unresolved gaps.
3. `verification-surface.md` for the checks required to keep behavior stable.

## Document Map

| File | Primary Question Answered | When To Read | Related Documents |
|------|---------------------------|--------------|-------------------|
| `prd.md` | What does the product do today? | Start here after this guide | `runtime-behaviors.md`, `reconstruction-risks.md` |
| `reconstruction-appendix.md` | What supporting reconstruction detail did the build preserve? | When you need extra context behind the main PRD | `prd.md`, `data-model.md` |
| `data-model.md` | What entities, rules, and structure anchor the product? | When changing data shape or domain rules | `state-machines.md`, `protocol-contracts.md` |
| `integration-contracts.md` | What systems, dependencies, and boundaries are involved? | Before changing integrations or external dependencies | `protocol-contracts.md`, `config-contracts.md` |
| `runtime-behaviors.md` | How does the system behave at runtime today? | During onboarding or behavior tracing | `verification-surface.md`, `error-semantics.md` |
| `config-contracts.md` | Which settings control behavior and in what order? | Before changing configuration or rollout behavior | `runtime-behaviors.md`, `integration-contracts.md` |
| `protocol-contracts.md` | What fields, payloads, or boundary contracts matter? | Before changing IO, schema, or compatibility behavior | `integration-contracts.md`, `data-model.md` |
| `state-machines.md` | Which states and transitions govern key flows? | During lifecycle or state debugging work | `error-semantics.md`, `runtime-behaviors.md` |
| `error-semantics.md` | How do failures surface and recover? | Before changing resilience or UX around errors | `state-machines.md`, `verification-surface.md` |
| `verification-surface.md` | How do we prove behavior still matches the reconstruction? | Before or after product changes | `runtime-behaviors.md`, `reconstruction-risks.md` |
| `reconstruction-risks.md` | Which parts of the reconstruction are least certain? | Before risky refactors or handoff decisions | `prd.md`, `verification-surface.md` |

## Confidence And Gaps

- **Strongest evidence areas**: [Summarize where Evidence dominates the suite.]
- **Inference-heavy areas**: [Summarize where interpretation is still doing more work.]
- **Highest-risk unknowns**: [Summarize the unknowns a maintainer should validate first.]
- **Recommended verification focus**: Start with `verification-surface.md`
  and the most relevant topic document before making changes in low-confidence
  areas.

## Package Usage Notes

- `README.md` is the package guide.
- `prd.md` is the primary reader-facing PRD.
- `../master/master-pack.md` is the internal synthesis truth source, not the
  preferred first read.
- Use the topic documents when you need deep evidence about one question
  instead of scanning the whole export suite.
