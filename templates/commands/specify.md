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

[AGENT] Before specification decisions involving lifecycle or running state,
destructive operations, shared state, downstream consumers, compatibility, or
multiple-behavior semantics, read
`references/senior-consequence-analysis.md` and complete that gate. Preserve
stable `CA-###` obligations plus the Affected Object Map, State-Behavior
Matrix, Dependency Impact Table, Recovery And Validation Contract, and
Coverage Gaps; neither planning readiness nor a final claim may bypass it.

{{spec-kit-include: ../command-partials/common/agent-phase-handoff.md}}
{{spec-kit-include: ../command-partials/common/execution-bootstrap.md}}

[AGENT] For project-cognition-backed semantic intake, routing, audit, resume, or final-claim gates, read `references/semantic-work-contract.md`.

[AGENT] When a planning-relevant gap requires project-cognition navigation or
a bounded read-only evidence lane, read
`references/planning-and-evidence-navigation.md` before expanding repository
reads or dispatching evidence work. The leader retains specification judgment
and must prove technical claims from live evidence.

[AGENT] `sp-specify` first performs the read-only feature dry run described
below, reserves that exact feature scope once through Work Board, then executes
the real script with the same identity and returned branch policy. Resume
existing feature state explicitly; do not allocate another worktree or replace
the workflow's artifact and approval gates.

## Main Flow

1. Resolve discussion handoff intake before feature creation through `specify-runtime discussion resolve --intent sp-specify [--slug <slug>] --format json` plus `validate-handoff` and targeted `artifact show`; require canonical agent-only `handoff-to-specify.json`, verify `handoff-ready`, `quality_gate.status: user_confirmed`, `recommended_consumer: sp-specify`, `topic_ownership.owner_slug` equal to the resolved slug, and `planning_gate_status: ready`, derive the feature description, and do not pass the raw contract path as the feature description. With no arguments and exactly one unconsumed `status: handoff-ready` discussion eligible for `sp-specify`, the resolver may select it. If multiple unconsumed `handoff-ready` discussions exist or multiple candidates are returned, stop and ask for the slug; never guess and do not select latest. Do not use `specification-input.md`, `discussion-state.md`, or other discussion source files as a substitute.
2. Verify the bounded bootstrap surface once with `{{specify-subcmd:specify-runtime api ensure --capabilities api.ensure,board.feature-bootstrap,workflow.ensure,artifact.scaffold,artifact.patch,artifact.patch-batch --format json}}` and reuse its `capability_set_sha256`; older runtimes fall back once to `{{specify-subcmd:specify-runtime api list --format json}}`. Before any feature write or branch action, run `{SCRIPT}` from the repo root with the original description plus `--dry-run --json` (PowerShell: `-DryRun -Json`). Retain its exact `BRANCH_NAME` as `feature_id` and exact `FEATURE_DIR` as `feature_dir`; stop if either is missing. Require `BOOTSTRAP_CONTRACT` to equal `spec-kit-feature-bootstrap-v1`; a missing or different contract stops before Work registration, branch action, or feature writes. Request the operator's human-only integration repair action through the exact trusted project Specify launcher command named by the diagnostic, then repeat the dry run.
   Next run `specify-runtime board reconcile` and `specify-runtime board show`, then exactly one `specify-runtime board feature-bootstrap --feature-id <dry-run BRANCH_NAME> --feature-dir <dry-run FEATURE_DIR> --summary <summary> --agent-id <agent-id> --adapter-id <adapter-id> --format json`. It atomically registers Work, records the exact feature directory as a confirmed write intent, and returns `data.work` plus `data.feature_branch_policy`. Do not query `specify-runtime board branch-policy` before registration, and do not call `specify-runtime work begin` separately.
   Only then run the real create-feature script, replaying the dry-run identity unchanged with `--resolved-feature-id <dry-run BRANCH_NAME>` or PowerShell `-ResolvedFeatureId <dry-run BRANCH_NAME>`; never recompute the timestamp or automatic feature number. For `keep-current`, also pass `--keep-current-branch` or PowerShell `-KeepCurrentBranch` and do not create or switch branches; only for `default` because the board was idle does existing branch behavior remain unchanged. Generated projects use `.specify/scripts/bash/create-new-feature.sh` or `.specify/scripts/powershell/create-new-feature.ps1`. Stop on any dry-run, reservation, or real-script failure. The board reserves work but does not create the feature; do not invent another feature-creation CLI. Require the real `FEATURE_DIR` to exactly match the dry-run value and require explicit resume for an existing feature directory. Then enter or resume `specify` through the deterministic workflow runtime before writing any feature artifact, retaining the same scoped Work owner and existing artifact leases.
3. Explore project context with project cognition as advisory navigation, then prove current facts from live files and record source evidence.
4. Select discovery mode for a raw request or compile mode for a confirmed discussion contract. In compile mode, compute `semantic_delta`, ask only about a planning-critical delta, and do not repeat user review when `semantic_delta` is empty.
5. Decompose semantic terms into explicit decisions and capability operations in `spec-contract.json`. Build `acceptance_coverage` as one stable `requirement_ref`/`acceptance_ref` pair per row: cover every `scope.in` and `capability_operations` JSON Pointer, map every acceptance criterion exactly once, and never use one criterion as the closure proof for multiple independent requirements. Present two or three approaches only when behavior, boundary, compatibility, or acceptance proof changes.
6. Preserve the discussion contract by reference. Query supporting discussion artifacts through their artifact/evidence CLI owner only when a named evidence reference is stale, missing, or contradictory; carry its existing decision digest instead of rebuilding it. Treat `topic_ownership.routed_topics` as cross-discussion pointers only; do not pull branch/link/defer side-topic decisions into this feature unless the user explicitly resolves and consumes that other discussion.
7. For UI-facing work—with or without supplied screenshots—derive one stable
   path-like surface ID from confirmed source surfaces or registered metadata
   per query; split surfaces and never send the whole brief as `--scope`. Run
   `specify-runtime design resolve --scope <exact-surface> --format json` for
   discovery, then query `.specify/design/index.json` only when present or
   identified by registered metadata through
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
   a missing registry as legitimate discovery absence; do not blindly read it.
   A missing or unregistered required change still blocks approved Design
   adoption; route to Design and preserve its approval/registration and
   `formal-post-specify` late-design receipt gates. Never replace required
   approved Design with a prose risk note. Treat only a
   narrow existing-pattern adoption gap as a soft risk. When raw UI references
   exist, additionally use `choose_ui_reference_lane_dispatch`,
   `ui-reference-artifact`, and `Reference-Implementation` fidelity evidence.
8. Create `spec-contract.json` with `artifact scaffold --kind spec-contract`, then fill only targeted JSON pointers through leased `artifact patch`. Query the prerequisite-script-created `spec.md` skeleton through `artifact show` and fill named sections through leased `artifact patch --section`; never emit or resubmit the stable template. Route every conditional project-facing artifact through its registered CLI owner. Never write canonical files directly or stage temporary payload files. Run deterministic validation and fail closed if incomplete.

Create only specification-stage outputs. Do not create `plan-contract.json`, `plan.md`, research/design-plan artifacts, `tasks.md`, or `task-index.json`; the separately invoked planning and task workflows own them. Do not edit production source, tests, migrations, or runtime configuration.

## Detailed References

Read [Reference index](references/INDEX.md) before applying detailed contracts.

- [discussion handoff validation](references/discussion-handoff-validation.md)
- [semantic traceability](references/semantic-traceability.md)
- [planning and evidence navigation](references/planning-and-evidence-navigation.md)
- [UI design intelligence](references/ui-design-intelligence.md)
- [ui reference lane](references/ui-reference-lane.md)
- [senior consequence analysis](references/senior-consequence-analysis.md)
- [artifact package](references/artifact-package.md)
- [question cadence and review](references/question-cadence-and-review.md)
- [self review and quality gates](references/self-review-and-quality-gates.md)
