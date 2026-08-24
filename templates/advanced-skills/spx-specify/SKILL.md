---
name: spx-specify
description: Lean feature-specification workflow for advanced coding models. Use when a new capability or supplied feature PRD needs planning-ready requirements, acceptance, scope, and constraints.
---

# SPX Specify

Read `references/project-learning.md` and apply its consume-capture policy.
Read `references/workflow-runtime.md` and let its CLI own phase state.
Read `references/run-bootstrap.md`.
Read `references/project-cognition.md`, using cognition intent `plan`.
Read `references/requirements-contract.md`. Read
`references/discussion-handoff.md` when consuming a ready discussion and
`references/ui-and-handoffs.md` plus `references/ui-quality-gate.md` for any
UI-bearing feature, with or without supplied references. Read
`references/consequence-gate.md` only on its triggers.

`$spx-specify` first performs the read-only feature dry run below, then starts a
new feature Run with that identity. Record it with `specify-runtime run create`;
execute the real feature creation and later artifact work only through
`specify-runtime run supervise`.

Inspect project rules, relevant live behavior, a supplied feature PRD, and any
confirmed discussion context. Clarify only decisions that materially change scope, behavior,
interfaces, risk, or acceptance; make safe assumptions explicit. Preserve every
confirmed capability and do not silently reduce the request to an MVP.

For new feature state, first run the exact installed
`.specify/scripts/bash/create-new-feature.sh` with the original description plus
`--dry-run --json`, or its PowerShell equivalent with `-DryRun -Json`. This
read-only call happens before any feature write or branch action; retain its
exact `BRANCH_NAME` as `feature_id` and exact `FEATURE_DIR` as `feature_dir`.
Require the dry-run receipt's exact `BOOTSTRAP_CONTRACT` field to equal
`spec-kit-feature-bootstrap-v1`. If it is absent or different, stop before the
managed or unhosted registration paths and before any branch action or feature
write; run `{{specify-subcmd:integration repair}}` through the trusted project
Specify launcher, then repeat the dry run.
Every real script invocation must replay the dry-run `BRANCH_NAME` unchanged
with `--resolved-feature-id <dry-run BRANCH_NAME>` or PowerShell
`-ResolvedFeatureId <dry-run BRANCH_NAME>`; never recompute its timestamp or
automatic feature number. On the managed path, record
`subject_type=feature` with
`--subject-type feature --subject-id <dry-run BRANCH_NAME>`, then execute the
real create-feature script only inside `specify-runtime run
supervise`. The supervisor binds the exact feature directory as a confirmed
write intent. Its child always stays on the allocated private/current ref and
does not create or switch to a business feature branch.

On an unhosted path, first reconcile and show the board, then call exactly one
`specify-runtime board feature-bootstrap --feature-id <dry-run BRANCH_NAME> --feature-dir <dry-run FEATURE_DIR> --summary <summary> --agent-id <agent-id> --adapter-id <adapter-id> --format json`.
It atomically registers Work, confirms that write intent, and
returns `data.work` plus `data.feature_branch_policy`. Do not query
`specify-runtime board branch-policy` before registration, and do not call
`specify-runtime work begin` separately. Only then execute the real
create-feature script. For `keep-current`, pass `--keep-current-branch` or
PowerShell `-KeepCurrentBranch` and do not create or switch branches. Only for
`default` because the board was idle does existing branch behavior remain
unchanged. Stop on any dry-run, reservation, or real-script failure, and require
the real `FEATURE_DIR` to exactly match the dry-run value. Then create
the authoritative `spec-contract.json` with `specify-runtime artifact scaffold --kind spec-contract`, then fill targeted JSON pointers through leased `artifact patch` calls. For a new project-facing
view, use this Skill's compact `assets/spec.md` only as section guidance for the
prerequisite-script-created `spec.md` skeleton: query it through `artifact show`
and fill named sections through leased `artifact patch --section`; never emit or
resubmit the full stable template. Preserve existing semantic work when
revising an established spec. For substantive UI work, create `ui-brief.md`
through `specify-runtime artifact scaffold --kind ui-brief` and patch its
semantic fields; when original UI references exist, likewise scaffold
`ui-reference-notes.md` with `artifact scaffold --kind ui-reference-notes`.
Use `assets/ui-brief.md` only as compact field guidance, never as content to
reproduce. A narrow existing-pattern adjustment may instead record why a
separate brief adds no decision value.

Preserve exact `style_authority` in the spec/brief chain. Existing-product
feature and partial-page work inherits live UI; only explicitly authorized
exact complete-page overhaul scope may change style, with `global-shell` and
`shared-components` protected. Do not rerun Specify merely because Design
happened after a planning-ready spec: an unchanged late design overlay binds
through `formal-post-specify` and returns to Plan. Only a genuine requirements,
scope, or acceptance change re-enters this workflow.

Treat `alignment.md`, `context.md`, and `references.md` as conditional
project-facing views, not parallel truth. When one has independent review
value, create an absent stable view with `artifact scaffold --kind alignment`,
`--kind specify-context`, or `--kind references`, then fill only named sections
through fresh leased `artifact patch` calls. The feature bootstrap normally
creates `context.md`, so query and patch it instead of replacing it. Never emit
or submit any of these stable templates wholesale. When a requirements
checklist is genuinely needed, pass only a compact semantic checklist object to
`specify-runtime artifact checklist`; the CLI owns Markdown and `CHK###` IDs.

After the feature directory exists, enter or resume `specify` through the
workflow runtime before substantive artifact work. Keep specification truth in
the contract rather than reconstructing phase state. Create rich
`workflow-state.md` with `specify-runtime artifact scaffold --kind workflow-state`, or resume it through targeted `artifact show` and leased `artifact patch` calls, for specification evidence,
resume details, and Learning; it does not own phase order or runtime revision.
Run
`{{specify-subcmd:specify-runtime hook validate-state --command specify --feature-dir <feature-dir> --autofix --format json}}`
and stop if the repaired state remains invalid.
Create specification-stage outputs only through their registered artifact CLI owners: `spec-contract.json`, `spec.md`,
triggered alignment/context/reference views, a triggered `ui-brief.md`, and
specification evidence or workflow-owned rich state.
Do not create `plan-contract.json`, `plan.md`, `research.md`, `data-model.md`,
`contracts/`, `quickstart.md`, `tasks.md`, or `task-index.json`; `$spx-plan` and
`$spx-tasks` own those downstream artifacts.

An existing PRD used as input to one feature compiles into the ordinary spec
contract with source traceability. Route project-wide principles to
`$spx-constitution`, exploratory ideas to `$spx-discussion`, existing-spec gaps
back through `$spx-specify`, and repository reconstruction to `$spx-prd-scan`.

Make requirements and acceptance observable. Populate `acceptance_coverage`
with unique canonical JSON Pointer pairs from every `scope.in` and
`capability_operations` requirement to `acceptance_criteria`; every requirement
must be covered and every criterion must map exactly once, never serving as the
closure proof for multiple independent requirements. Resolve contradictions and
planning-blocking unknowns; ask only the smallest decision batch needed. Run the installed artifact validator when
available and preserve canonical `/sp.*` transition values required by the
runtime.
Before reporting planning-ready, run
`{{specify-subcmd:specify-runtime hook validate-artifacts --command specify --feature-dir <feature-dir> --format json}}`;
fail closed on any blocked result and repair the owning artifact or upstream
handoff.

Do not implement or edit production code, tests, migrations, or runtime
configuration. This invocation authorizes only this workflow stage. Stop after
reporting the specification result and recommend exactly one next workflow. Do
not invoke `$spx-plan`, `$spx-deep-research`, or any other next
workflow in this run; a handoff is not authorization to execute it.
