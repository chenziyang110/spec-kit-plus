# Workflow Contract Convergence Design

**Date:** 2026-05-04  
**Status:** Approved for implementation planning  
**Scope:** Shared workflow templates, generated runtime scripts, CLI diagnostics and repair flows, public docs, and contract tests for workflow routing and command-surface behavior  
**Primary goal:** Converge Spec Kit Plus onto one enforced workflow contract for feature resolution, lane recovery, user-visible command naming, and generated-runtime compatibility

## Problem

Spec Kit Plus currently has the right long-term direction but an incomplete
contract.

Parts of the stack already support stronger workflow routing:

- generated prerequisite scripts now accept explicit `--feature-dir` /
  `-FeatureDir`
- shared resolvers already prioritize `SPECIFY_FEATURE` and can consult lane
  state
- `lane resolve` exists as a machine-readable routing surface
- runtime diagnostics already detect at least some stale generated workflow
  scripts

But those capabilities are not yet enforced consistently across the full
workflow product surface. The result is an unstable operator experience in
parallel feature development and recovery-heavy sessions.

The concrete failures this design addresses are:

- workflow commands still fall back to branch-driven routing too easily instead
  of treating explicit feature selection or lane resolution as the source of
  truth
- `sp-analyze` does not yet carry the same lane-first routing contract as
  `sp-plan` and `sp-tasks`
- some user-visible instructions still imply old or nonexistent surfaces such as
  `specify branch` or legacy `/speckit.*` naming
- workflow templates can still reference helper CLI parameters that do not
  exist on the real command surface
- stale generated assets are detected only partially, so users can continue
  running against drifted runtime scripts until they hit confusing failures

This is not a single bug. It is a contract convergence problem spanning CLI
surfaces, generated assets, workflow templates, diagnostics, and docs.

## Goals

- Make `/sp-*` the only user-visible workflow naming contract
- Make explicit `--feature-dir` or unique lane resolution the authoritative
  feature-binding mechanism for workflow commands
- Remove branch-first routing as a primary behavior for planning-artifact
  workflows
- Align `sp-analyze` with the same lane-first contract used by the planning and
  tasking workflows
- Treat stale generated runtime assets as hard failures instead of soft drift
- Ensure `specify check` and `specify integration repair` are the supported
  recovery path when generated workflow assets are outdated
- Prevent templates, docs, and tests from reintroducing nonexistent command or
  parameter surfaces

## Non-Goals

- Supporting old `/speckit.*` naming as an equal long-term contract
- Preserving ambiguous branch-first workflow routing for user convenience
- Adding a new `specify branch` command family
- Implementing behavior changes in downstream generated projects beyond
  surfacing hard failure plus repair guidance
- Expanding this project into broader lane scheduling or stacked-branch product
  work unrelated to the failures above

## Verified Current-State Findings

The following facts were verified in the current repository state before this
design was written:

- `scripts/powershell/check-prerequisites.ps1` already accepts
  `-FeatureDir`
- `scripts/powershell/common.ps1` already prioritizes `SPECIFY_FEATURE`,
  consults lane metadata, and supports prefix-based feature directory matching
- the real `specify hook review-learning` CLI surface does not support
  `--origin-artifact`
- the real lane CLI surface provides `register`, `resolve`, `status`, and
  `materialize-worktree`; there is no `specify branch` command family
- `templates/commands/plan.md` and `templates/commands/tasks.md` already
  instruct agents to prefer `lane resolve --ensure-worktree`
- `templates/commands/analyze.md` does not yet provide the same explicit
  lane-resolution step
- runtime compatibility diagnostics currently detect stale PowerShell feature
  resolvers, but that detection does not yet represent the whole contract

These findings mean the repository does not need a brand-new routing system. It
needs one contract enforced end to end.

## Design Summary

This design converges the workflow system around a single enforced contract with
four pillars:

1. **One visible workflow naming system**
2. **One authoritative feature-binding model**
3. **One hard-fail generated-runtime compatibility model**
4. **One testable source of truth across templates, CLI surfaces, and docs**

The key product decision is to stop carrying old behavior as first-class
compatibility.

Instead:

- `/sp-*` is the only current user-facing workflow family
- explicit feature binding or unique lane resolution must determine workflow
  scope
- stale generated runtime assets must fail closed
- diagnostics and repair must become the explicit upgrade path

## Formal Contract

### 1. Workflow Naming Contract

User-visible workflow guidance must use `/sp-*` naming only.

This applies to:

- README guidance
- quickstart and upgrade docs
- workflow error messages
- template-generated next-step instructions
- generated skill and command text

Legacy `/speckit.*` tokens may still exist only where they are historical
artifacts or internal compatibility references, but they must not be presented
as the active workflow syntax to type.

### 2. Feature-Binding Contract

For any workflow that reads or writes planning artifacts, feature binding must
follow this precedence:

1. explicit `--feature-dir` or `-FeatureDir`
2. a unique `specify lane resolve` result for the current workflow command
3. tightly controlled fallback behavior only when the first two are unavailable
   and the result is unambiguous

Branch name is no longer a first-class source of truth. It is only a fallback
signal that may participate in controlled resolution logic.

### 3. Lane-First Workflow Contract

Any workflow that operates on planning artifacts must either:

- receive an explicit feature directory, or
- run through lane resolution before continuing

This applies to `sp-plan`, `sp-tasks`, `sp-analyze`, `sp-implement`, and other
artifact workflows with equivalent routing needs.

Templates must not merely suggest lane resolution informally. They must treat
it as part of the workflow contract.

### 4. Read-Only Safety Contract

Read-only workflows such as `sp-analyze` must never modify git state as part of
normal routing or recovery.

That means:

- no implicit branch switches
- no implicit checkout to "the correct" branch
- no silent workspace relocation that changes user git state

If workflow scope cannot be determined safely, the workflow must fail with
explicit remediation guidance.

### 5. Generated Runtime Compatibility Contract

Generated runtime assets are part of the product contract. If they are stale in
a way that can break workflow routing or command semantics, runtime execution
must fail closed.

Examples include:

- stale feature resolution helpers
- stale workflow templates that reference nonexistent command surfaces
- stale generated hook guidance that references unsupported parameters
- stale routing behavior that relies on exact branch-to-feature matches

`specify check` must detect these incompatibilities, and `specify integration
repair` must be the supported repair path.

### 6. Command-Surface Integrity Contract

No template, help text, or public doc may instruct users or generated agents to
use:

- nonexistent command families
- nonexistent helper options
- legacy workflow naming as if it were the current default

The real CLI surface and the generated workflow surface must match exactly.

## Implementation Layers

### Layer 1: Shared Feature Resolution and Lane Recovery

Unify feature-binding behavior across shared workflow entrypoints.

Required changes:

- promote shared resolution helpers into the contract authority
- ensure artifact workflows consume explicit feature binding or lane resolution
  before artifact validation proceeds
- add the missing lane-first routing step to `sp-analyze`
- remove any residual assumptions that current branch name alone is sufficient
  to select a feature in parallel lane scenarios

Primary owned surfaces:

- `scripts/bash/common.sh`
- `scripts/powershell/common.ps1`
- `scripts/bash/check-prerequisites.sh`
- `scripts/powershell/check-prerequisites.ps1`
- workflow templates that invoke those scripts

### Layer 2: Generated Runtime Hard-Fail Detection and Repair

Expand runtime diagnostics so stale generated surfaces are treated as explicit
product incompatibilities instead of best-effort warnings.

Required changes:

- add compatibility checks for the full workflow-routing contract, not only one
  stale PowerShell helper case
- make `specify check` surface actionable failure codes and repair guidance
- make `specify integration repair` refresh all generated assets required by the
  new contract

Primary owned surfaces:

- `src/specify_cli/launcher.py`
- `src/specify_cli/__init__.py`
- integration repair helpers
- generated asset compatibility tests

### Layer 3: Template, Help, and Documentation Convergence

Remove mixed or outdated user-visible guidance so the product teaches one
current workflow model only.

Required changes:

- remove any current-facing `/speckit.*` guidance from active docs and template
  surfaces
- remove any suggestion that `specify branch` is a real command family
- remove or rewrite references to unsupported helper options such as
  `--origin-artifact`
- make upgrade and quickstart guidance explicitly point users to `check` and
  `integration repair` for stale generated workflow assets

Primary owned surfaces:

- `templates/commands/**`
- selected passive skills
- `README.md`
- `docs/quickstart.md`
- `docs/upgrade.md`

### Layer 4: Contract Tests

Codify the new workflow contract so drift is blocked by tests rather than
rediscovered by users.

Required changes:

- add or extend tests that assert no user-visible workflow guidance points to
  obsolete naming or nonexistent commands
- add routing tests covering explicit feature directories, lane resolution, and
  parallel lane ambiguity
- add stale-runtime compatibility tests for `check` and repair flows
- add read-only safety tests ensuring `sp-analyze` does not rely on hidden git
  state mutation

## Detailed Behavior Changes

### A. `sp-analyze` Must Become Lane-First

`sp-analyze` currently lacks the same explicit lane-resolution contract already
present in `sp-plan` and `sp-tasks`.

This design requires:

- adding explicit lane-resolution guidance to the shared analyze template
- ensuring analyze-side prerequisite resolution can accept an explicit feature
  directory cleanly
- failing closed when analyze cannot determine scope unambiguously

### B. Old Naming Must Stop Leaking Through Active Docs

Historical references can remain in low-signal design history, but the current
operator path must not present `/speckit.*` as the workflow surface users should
invoke today.

Current-facing docs and generated content must use the active `/sp-*` surface.

### C. `specify branch` Must Not Exist Implicitly

The product must not leave room for users or agents to infer a nonexistent
`specify branch` family from surrounding wording.

The supported feature-creation path is still `sp-specify` plus generated
scripts and lane registration behavior. Docs and templates must reflect that
explicitly.

### D. Unsupported Helper Parameters Must Be Eliminated

If a template or doc mentions a helper CLI option, that option must exist on
the real command surface.

This design specifically calls out the need to remove unsupported
`review-learning` option references and to test that such drift cannot return.

### E. Hard Failure Beats Ambiguous Recovery

When the workflow contract cannot be satisfied safely, the product must fail and
tell the user how to recover. This applies especially to:

- ambiguous lane resolution
- missing explicit feature binding in parallel development contexts
- stale generated runtime assets
- outdated helper scripts that no longer satisfy the routing contract

## Failure Model

The system must fail closed in the following cases:

- explicit `feature-dir` is absent and lane resolution is ambiguous
- a generated runtime asset is too stale to satisfy the routing contract
- a workflow surface references helper options or commands not present in the
  actual CLI
- read-only routing would require mutating git state to continue

Failure output must include:

- the failure reason
- the relevant feature or lane context when known
- the supported next action
- `specify check` / `specify integration repair` guidance where generated asset
  drift is involved

## Verification Strategy

The repair is complete only if the following regression families are covered.

### 1. Feature-Binding Regression

Verify:

- explicit feature directory always wins
- unique lane resolution is respected for the relevant workflow
- artifact workflows do not silently bind to the wrong feature in parallel lane
  scenarios

### 2. Command-Surface Regression

Verify:

- no active doc or template teaches nonexistent command families
- no active doc or template teaches unsupported helper options
- current workflow naming is consistently `/sp-*`

### 3. Generated Runtime Compatibility Regression

Verify:

- stale generated helpers are detected by `specify check`
- incompatible generated assets fail closed in runtime-sensitive paths
- repair refreshes those assets to the current contract

### 4. Repair Regression

Verify:

- `specify integration repair` updates the generated workflow assets required by
  this contract
- post-repair diagnostics no longer report the corresponding compatibility
  issues

### 5. Read-Only Safety Regression

Verify:

- `sp-analyze` stays read-only with respect to git state
- analyze routing does not depend on hidden branch switching

## Rollout Sequence

Recommended implementation order:

1. strengthen shared routing and `sp-analyze`
2. expand compatibility diagnostics and repair behavior
3. converge templates, help text, and public docs
4. lock behavior with regression tests

This ordering ensures the hard contract exists before docs and generated repair
flows point users at it.

## Risks

- tightening the contract will surface more failures in stale generated
  projects, which is intentional but may initially feel harsher
- docs and templates are spread across multiple generation paths, so incomplete
  convergence would reintroduce mixed guidance
- stale-runtime detection that is too narrow will preserve confusing drift;
  detection that is too broad could over-block healthy generated projects

These are acceptable risks. The current ambiguity is more damaging than a
well-scoped hard-fail upgrade path.

## Success Criteria

This design is successful when:

- artifact workflows consistently bind to the intended feature without
  branch-first guesswork
- `sp-analyze` no longer acts as a routing exception in parallel lane scenarios
- current docs and templates teach one workflow naming surface only
- templates do not reference nonexistent commands or helper parameters
- stale generated assets are detected and repaired through supported product
  flows
- contract tests prevent regression of these behaviors

## Implementation Planning Notes

The follow-up implementation plan should be organized around the same four
layers described above and should explicitly track:

- shared routing surfaces
- generated runtime compatibility surfaces
- user-visible docs and templates
- regression coverage

It should also include a focused inventory of current user-visible files that
still teach mixed workflow naming or unsupported helper surfaces so those
convergences can be executed intentionally instead of opportunistically.
