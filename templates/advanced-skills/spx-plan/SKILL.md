---
name: spx-plan
description: Lean technical-planning workflow for advanced coding models. Use when a planning-ready specification needs repository-grounded architecture, interfaces, risks, verification, rollout, and rollback decisions.
---

# SPX Plan

Read `references/project-learning.md` and apply its consume-capture policy.
Read `references/native-subagents.md` when planning lanes are delegated.
Read `references/workflow-runtime.md` and let its CLI own phase state.
Read `references/execution-bootstrap.md`.
Read `references/project-cognition.md`, using cognition intent `plan`.
Always read `references/planning-contract.md`. Read
`references/consequence-gate.md` only on its triggers.
Read `references/ui-quality-gate.md` when the specification is UI-bearing.

Resolve the feature in the current worktree, register only its allowed
planning-artifact scope on Work Board, and resume through the workflow runtime.
Preserve artifact leases, input readiness, and design-only boundaries; do not
create another branch or worktree.

Resolve `FEATURE_DIR` without creating `plan.md`. Do that in the current
worktree, using an explicit feature argument, a validated durable workflow
binding, or the installed prerequisite helper's unique paths-only result. Never
infer it from a Git ref or branch name.
Query the workflow runtime first. Transition from the validated completed
`specify` stage into `plan` on the ordinary forward path. If verified fresh
evidence invalidates Plan while the runtime owns a later stage, use an
evidence-backed `workflow reopen --to plan`. A blocked later stage returns
`pending_reopen_action`; preserve its blocker and perform permitted agent-owned
recovery first. Present the Human Action Guide only for a genuine human-owned
boundary, and execute the returned atomic resolve-and-reopen base argv only after real
resolution evidence exists. Do not ask the user to invoke Plan again before
that transaction succeeds. Only after the transition succeeds, or the atomic
resolve-and-reopen transaction succeeds, run the installed
`.specify/scripts/bash/setup-plan.sh --json` or PowerShell equivalent to create
or preserve the plan skeleton. Run
`{{specify-subcmd:specify-runtime hook validate-state --command plan --feature-dir <feature-dir> --autofix --format json}}`
and withhold dependent writes if it remains invalid. Diagnose and repair
current-owner state through supported runtime routes, then rerun this gate in
the same invocation. A proven upstream truth gap still returns to its owner;
never hand-edit state or bypass validation.

Require `spec-contract.json` with `status: planning-ready`, a ready transition
to `sp-plan`, a current source revision, locked target boundary, zero hard
unknowns, and zero open conflicts. Fail closed to the owning upstream workflow
when any gate fails. Verify architecture claims against cognition-selected live
repository paths.

If Design ran after that planning-ready spec, require a current
`formal-post-specify` receipt and verify it with `specify-runtime design adoption
<feature-ref> --scope <exact-surface> --binding-ref <source-spec-ref>
--binding-sha256 <source-spec-sha256> --expected-change <UD-ID> --format json`.
The unchanged source spec remains requirements/acceptance truth; the receipt is
the exact Design overlay. Do not run a second Specify or resolve “latest”. A
receipt/spec digest mismatch blocks Plan; a real requirements change routes to
Specify.

Record the verified output as
`ui_design_contract.design_adoption_binding` (mode, consumer, exact scope,
revision/change, project-relative source-Spec ref/SHA, and impact SHA). Recheck
it against the current runtime adoption; never trust a model-authored verified
flag. For a source `design_gate.required`, preserve requirement-owned fields
from the unchanged Spec and fill design-owned identity/matrices only from that
verified registered overlay. Any mismatch blocks Plan.

Treat `plan-contract.json#/test_design_gate/decision` as exactly
`not_selected`, `selected`, or `required`. A selected/required binding may be
all-null while production is pending; partial binding is invalid. When Plan
actually consumes a projection, require the complete binding produced by the
independent `$spx-test-design` producer and verify it before use with
`{{specify-subcmd:specify-runtime test-design projection-verify --feature-dir <feature-dir> --projection-ref <project-relative-ref> --expected-sha256 <sha256> --format json}}`.
Omit `--feature-dir` only for explicit project scope. Consume the canonical,
typed pointer-only projection read-only. Never create, patch, replace, weaken,
or copy its publication, projection, cases, data, coverage, gaps, or audit. A
projection needed for a Plan decision routes to `$spx-test-design`; otherwise
Plan may finish with the all-null pending selection and route it next. Test
Design does not require Plan completion. The Plan binding proves only Plan
consumption, never Tasks authorization, and must not use the Plan contract as a
self-hashing basis. Build the Plan projection against the current immutable
upstream `spec-contract.json`; then record only the returned binding in
`plan-contract.json`. Tasks requires its own projection, a fresh feature handoff,
and runtime task-index binding. Plan choices do not rewrite Test Design.

Treat `plan-contract.json#/acceptance_refs` as the exact complete fail-closed
Spec-to-Plan denominator. For a ready version-2 plan it is the unique ordered
list `spec-contract.json#/acceptance_criteria/0..N-1`, covering every live
specification acceptance criterion exactly once; never select a subset,
reconstruct prose labels, or reorder, duplicate, rename, or omit a criterion.

When `spec-contract.json#/feasibility_gate.decision` is `required`, verify the
runtime handoff before choosing the design. Query `deep-research.md` through
`specify-runtime artifact show` only as a derived human-readable projection.
Consume every `PH-###` Planning Handoff item according to its mandatory,
optional, or user-decision contract. Add a level-2 `## Deep Research
Traceability Matrix` to `plan.md` with `Plan Decision`, `Handoff ID`, `Evidence
/ Spike ID`, `Evidence Quality`, and `Plan Action` columns. Missing mandatory
handoffs or untraceable evidence keep planning blocked; a validated
`**Status**: Not needed` handoff carries no invented PH IDs.

When deep research is present, treat the runtime-published structured research
artifacts as canonical and `deep-research.md` as a derived projection. Record
Plan consumption in `plan-contract.json#/deep_research_binding` only through
leased JSON-pointer patches after `specify-runtime deep-research verify-handoff
--feature-dir <feature-dir> --handoff-ref <handoff-ref> --expected-sha256
<handoff-sha256> --format json` confirms the selected handoff. Preserve exactly
`decision`, `handoff_ref`, `handoff_sha256`, `source_spec_sha256`,
`state_revision`, `claim_status`, and `handoff_ids`. A verified `not_needed`
claim still binds the handoff with an empty `handoff_ids` array. Never infer
those fields from prose or rebuild them from the Markdown projection.

Create `plan-contract.json` only with `specify-runtime artifact scaffold --kind
plan-contract`, then fill it through leased JSON-pointer patches; never read or
reproduce the installed JSON template. Treat this Skill's compact
`assets/plan.md` as section guidance for the setup-created `plan.md` skeleton:
query the skeleton through `artifact show` and fill only named sections through
leased `artifact patch --section`; never emit or resubmit the full stable template. Cover affected components and files,
interfaces and data, compatibility or migration, security, verification,
rollout or rollback, and material risks only when relevant.

For UI-bearing work, query `ui-brief.md`, then its exact registered
`.specify/design/changes/<UD-ID>/design-contract.json` and matching
change-local `design-change.md` through targeted `specify-runtime artifact show`
calls. Treat the change-local JSON as the machine-readable source of truth and
its `design-change.md` as the human-readable projection. Never select an unbound newer
change from `.specify/design/index.json`. Consume the returned
contract sections, original fidelity sources, and the spec design contract. Set
`ui_design_contract.ui_applicable: true`, preserve `ui_brief_ref`, and record
`design_readiness`. Populate it with the current direction contract,
surface/platform classification, approved visual,
preview/manifest/handoff SHA-256 values, immutable handoff ref, selected `DS-*`
decisions and `DH-*` contracts, component/color-mode/responsive/motion
contracts, exact `style_authority`, reference intents, real content/image plans, design-system
adoption, required states, must-preserve rules, real entry points,
viewport/state acceptance matrix, comparison tolerance, accepted deviations,
and the evidence triad. Carry verified cognition routes into the compact
context capsule. Do not defer these decisions to tasks.

If design-changing feasibility remains unproven, stop and route the named
question to `$spx-deep-research`; do not hide research inside generic plan
prose. Repair requirement contradictions through `$spx-specify`.

When bounded implementation-shaping research is triggered, create `research.md`
with `specify-runtime artifact scaffold --kind research --path <feature-dir>/research.md`
and fill only relevant sections through leased `artifact patch`; never reproduce
the stable template in an inline submission. Create other fixed conditional
outputs only as `data-model.md` through `artifact scaffold --kind data-model`
for new data/state or persistence design and `quickstart.md` through `artifact
scaffold --kind quickstart` for a material end-to-end validation scenario, then
patch named sections. External or protocol
files under `contracts/` are format-dependent and use `artifact prepare` plus
inline `artifact submit` rather than a fake universal schema.
Otherwise patch the skip reason into `plan-contract.json` through a leased JSON-pointer `artifact patch`. Refresh existing agent
contexts with the installed `update-agent-context` script after the plan is
valid.

When planning lanes are delegated, create an absent
`planning/lane-manifest.json` with `artifact scaffold --kind planning-lane-manifest --path <feature-dir>/planning/lane-manifest.json` and
query it on resume. Parallelize only isolated lanes; shared handoff or
research surfaces stay serial `one-subagent`. Submit each compact lane result
inline through `result submit --command plan`; the runtime alone writes its
handoff. At material joins, replace the bounded `/lanes` array as a whole
through a fresh leased JSON-pointer patch and patch `/status` separately at
closeout. Never emulate array append, submit the manifest wholesale, or
duplicate lane events.

Validate the plan contract and compact plan view against confirmed requirements
and live owners. Do not create tasks or task artifacts such as `tasks.md` or
`task-index.json`; also do not create checklists, issues, production source,
tests, migrations, or runtime configuration in this workflow. Preserve canonical
`/sp.*` state identifiers. This invocation authorizes only this workflow stage.
Run `{{specify-subcmd:specify-runtime hook validate-artifacts --command plan --feature-dir <feature-dir> --format json}}`
and repair or block on a non-OK result.
Do not accept a deep-research handoff on surface presence alone. Before Plan
reports readiness, verify the selected handoff and its source binding against
the current runtime-owned structured research package. Any stale, tampered,
foreign, partial, or claim-mismatched handoff blocks planning and routes back
to `$spx-deep-research` or the owning upstream workflow for regeneration.
Stop after reporting the validated plan. When the user requested a dedicated
test design or the plan's risk and coverage obligations warrant one, record the
gate as `selected` or `required` and recommend the independent
`$spx-test-design` workflow; otherwise record `not_selected` and recommend
`$spx-tasks`. The default formal path remains Plan -> optional Test Design ->
Tasks, without making completed Plan an entry prerequisite for Test Design.
Do not invoke `$spx-test-design`. Do not invoke `$spx-tasks` in this run; a
handoff is not authorization to execute either workflow.
