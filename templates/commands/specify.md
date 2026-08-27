---
description: Use when a new or changed feature request needs the artifact CLI for guided discovery and a planning-ready specification package.
workflow_contract:
  when_to_use: A new or changed feature request needs a planning-ready specification package instead of immediate implementation.
  primary_objective: 'Produce and patch the planning-ready specification contract only through `specify-runtime artifact`, followed by deterministic completeness and traceability review.'
  primary_outputs: 'CLI-owned `spec-contract.json`, `spec.md`, triggered views, and `workflow-state.md`, created or changed only through `specify-runtime artifact`.'
  default_handoff: 'After user review, recommend exactly one next command: `/sp.plan`, `/sp.specify`, or `/sp.deep-research`.'
handoffs:
  - label: Build Technical Plan
    agent: sp.plan
    prompt: Create a plan for the spec. I am building with...
  - label: Prove Feasibility Before Plan
    agent: sp.deep-research
    prompt: Prove the unverified implementation-chain risks recorded by sp-specify, then hand findings and demo evidence to sp-plan.
    send: true
scripts:
  sh: scripts/bash/create-new-feature.sh "{ARGS}"
  ps: scripts/powershell/create-new-feature.ps1 "{ARGS}"
---

{{spec-kit-include: ../command-partials/specify/shell.md}}

{{spec-kit-include: ../command-partials/common/senior-consequence-analysis-gate.md}}

{{spec-kit-include: ../command-partials/common/agent-phase-handoff.md}}
{{spec-kit-include: ../command-partials/common/run-bootstrap.md}}

{{spec-kit-include: ../command-partials/common/planning-cognition.md}}

[AGENT] For project-cognition-backed semantic intake, routing, audit, resume, or final-claim gates, read `references/semantic-work-contract.md`.

{{spec-kit-include: ../command-partials/common/read-only-evidence-lanes.md}}

[AGENT] `sp-specify` first performs the read-only feature dry run described
below, then starts a new Run with the returned feature identity. When the exact
Run metadata and real feature-creation child argv are ready, use
`specify-runtime run launch` as the single call that records and supervises the
new Run. Older runtimes without `run.launch` fall back to `specify-runtime run
create` followed by `specify-runtime run supervise`.

## Main Flow

1. Resolve discussion handoff intake before feature creation through `specify-runtime discussion resolve --intent sp-specify [--slug <slug>] --format json` plus `validate-handoff` and targeted `artifact show`; require canonical agent-only `handoff-to-specify.json`, verify `handoff-ready`, `quality_gate.status: user_confirmed`, `recommended_consumer: sp-specify`, `topic_ownership.owner_slug` equal to the resolved slug, and `planning_gate_status: ready`, derive the feature description, and do not pass the raw contract path as the feature description. With no arguments and exactly one unconsumed `status: handoff-ready` discussion eligible for `sp-specify`, the resolver may select it. If multiple unconsumed `handoff-ready` discussions exist or multiple candidates are returned, stop and ask for the slug; never guess and do not select latest. Do not use `specification-input.md`, `discussion-state.md`, or other discussion source files as a substitute.
2. Verify the bounded bootstrap surface once with `{{specify-subcmd:specify-runtime api ensure --capabilities api.ensure,run.launch,workflow.ensure,artifact.scaffold,artifact.patch,artifact.patch-batch --format json}}` and reuse its `capability_set_sha256`; older runtimes fall back once to `{{specify-subcmd:specify-runtime api list --format json}}`. Run `{SCRIPT}` from the repo root as the generated create-feature script. Before any feature write or branch action, first invoke that exact command with the original description plus `--dry-run --json` (PowerShell: `-DryRun -Json`). This is a read-only call; retain its exact `BRANCH_NAME` as `feature_id` and exact `FEATURE_DIR` as `feature_dir`, and stop if either is missing. Require the receipt's exact `BOOTSTRAP_CONTRACT` field to equal `spec-kit-feature-bootstrap-v1`; if it is absent or different, stop before the managed or unhosted path and before any branch action or feature write, request the operator's human-only integration repair action through the exact trusted project Specify launcher command named by the dry-run diagnostic, then repeat the dry run. Every real script invocation must replay that dry-run identity unchanged with `--resolved-feature-id <dry-run BRANCH_NAME>` or PowerShell `-ResolvedFeatureId <dry-run BRANCH_NAME>`; never recompute the timestamp or automatic feature number. On the managed path, record `subject_type=feature` with `--subject-type feature --subject-id <dry-run BRANCH_NAME>`, then run the real create-feature script through the single-call `specify-runtime run launch` path. The supervisor binds the exact feature directory as a confirmed write intent, and the child always stays on its allocated private/current ref; it does not create or switch to a business feature branch. On the unhosted path, first reconcile and show the board, then invoke exactly one `specify-runtime board feature-bootstrap --feature-id <dry-run BRANCH_NAME> --feature-dir <dry-run FEATURE_DIR> --summary <summary> --agent-id <agent-id> --adapter-id <adapter-id> --format json`. It atomically registers Work, records that confirmed write intent, and returns `data.work` and `data.feature_branch_policy`. Do not query `specify-runtime board branch-policy` before registration, and do not call `specify-runtime work begin` separately. Only then run the real create-feature script: for `keep-current`, also pass `--keep-current-branch` or PowerShell `-KeepCurrentBranch` and do not create or switch branches; only for `default` because the board was idle does existing branch behavior remain unchanged. Generated projects use `.specify/scripts/bash/create-new-feature.sh` or `.specify/scripts/powershell/create-new-feature.ps1`. If the feature-creation script exits non-zero, stop with its evidence. The board command reserves work but does not create the feature, so do not substitute an invented feature-creation CLI. After the real script returns `FEATURE_DIR`, verify that it exactly matches the dry-run `FEATURE_DIR`, then enter or resume `specify` through the deterministic workflow runtime before writing any feature artifact.
3. Explore project context with project cognition as advisory navigation, then prove current facts from live files and record source evidence.
4. Select discovery mode for a raw request or compile mode for a confirmed discussion contract. In compile mode, compute `semantic_delta`, ask only about a planning-critical delta, and do not repeat user review when `semantic_delta` is empty.
5. Decompose semantic terms into explicit decisions and capability operations in `spec-contract.json`. Build `acceptance_coverage` as one stable `requirement_ref`/`acceptance_ref` pair per row: cover every `scope.in` and `capability_operations` JSON Pointer, map every acceptance criterion exactly once, and never use one criterion as the closure proof for multiple independent requirements. Present two or three approaches only when behavior, boundary, compatibility, or acceptance proof changes.
6. Preserve the discussion contract by reference. Query supporting discussion artifacts through their artifact/evidence CLI owner only when a named evidence reference is stale, missing, or contradictory; carry its existing decision digest instead of rebuilding it. Treat `topic_ownership.routed_topics` as cross-discussion pointers only; do not pull branch/link/defer side-topic decisions into this feature unless the user explicitly resolves and consumes that other discussion.
7. For UI-facing work—with or without supplied screenshots—run
   `specify-runtime design resolve --scope <exact-surface> --format json` for
   discovery, then query `.specify/design/index.json` through
   `specify-runtime artifact show` and inspect only the returned registered
   change(s). Resolution never adopts or selects “latest.” Because the current
   formal binding is singular, split a composite result into independently
   bound feature units, each with one exact scope, `spec-contract.json`, and
   `ui-brief.md`. Query each exact
   `.specify/design/changes/<UD-ID>/design-change.md`, sibling
   `design-contract.json`, and live UI evidence through targeted
   `specify-runtime artifact show` calls. Compile
   `Experience Requirements`, design readiness
   (`design_system_status`, `design_risk_level`), a compact adoption
   `ui-brief.md` via `specify-runtime artifact scaffold --kind ui-brief` plus
   leased `artifact patch` calls, and the exact `design_contract` for
   substantive UI changes. Pin the `UD-*` ID/ref, registered contract SHA-256,
   approved visual/handoff digests, selected `DS-*`/`DH-*` rows, work type,
   surface/platform, feature entry points/states, reference intents, real
   content/image plans, and the structure/visual/runtime evidence triad. Before
   replacing an existing binding, run
   `specify-runtime design diff <CURRENT-UD-ID> <CANDIDATE-UD-ID> --format json`
   and record the semantic delta, then run
   `specify-runtime design impact feature:<feature-id> --change <CANDIDATE-UD-ID> --scope <exact-surface> --mode formal --expected-change <CURRENT-UD-ID|none> --format json`
   before changing either binding. Present its affected `DS-*`/`DH-*` IDs,
   `preserved_bindings`, `invalidated_bindings`, and `reconcile_from`. Use fresh leased
   `specify-runtime artifact patch` calls to set the complete replacement
   binding in `spec-contract.json` and `ui-brief.md` first. Compute SHA-256 over
   the exact spec-contract bytes, then execute
   `specify-runtime design adopt feature:<feature-id> --change <UD-ID> --scope <exact-surface> --mode formal --binding-ref <feature-dir>/spec-contract.json --binding-sha256 <sha256> --expected-change <CURRENT-UD-ID|none> --format json`.
   A failed compare-and-swap blocks downstream regeneration. After success,
   follow the receipt's `reconcile_from`: reconcile Specify-owned UI binding
   fields when listed, mark only invalidated Plan/Tasks/affected Review surfaces
   pending for their owners, preserve completed implementation and unaffected
   Review evidence, and never directly rewrite another stage's artifact. Treat
   a missing or unregistered applicable change as a strong blocker and a
   narrow existing-pattern adoption gap as a soft risk. When raw UI references
   exist, additionally use `choose_ui_reference_lane_dispatch`,
   `ui-reference-artifact`, and `Reference-Implementation` fidelity evidence.
8. Create `spec-contract.json` with `artifact scaffold --kind spec-contract`, then fill only targeted JSON pointers through leased `artifact patch`. Query the prerequisite-script-created `spec.md` skeleton through `artifact show` and fill named sections through leased `artifact patch --section`; never emit or resubmit the stable template. Route every conditional project-facing artifact through its registered CLI owner. Never write canonical files directly or stage temporary payload files. Run deterministic validation and fail closed if incomplete.

Create only specification-stage outputs. Do not create `plan-contract.json`, `plan.md`, research/design-plan artifacts, `tasks.md`, or `task-index.json`; the separately invoked planning and task workflows own them. Do not edit production source, tests, migrations, or runtime configuration.

## Detailed References

Read [Reference index](references/INDEX.md) before applying detailed contracts.

- [discussion handoff validation](references/discussion-handoff-validation.md)
- [semantic traceability](references/semantic-traceability.md)
- [ui reference lane](references/ui-reference-lane.md)
- [artifact package](references/artifact-package.md)
- [question cadence and review](references/question-cadence-and-review.md)
- [self review and quality gates](references/self-review-and-quality-gates.md)
