# Quick task contract

Keep one resumable truth surface in `STATUS.md` and one terminal account in
`SUMMARY.md`. Create `STATUS.md` through `artifact scaffold --kind quick-status`,
then mutate only targeted frontmatter/sections through leased `artifact patch`
calls. Create an absent terminal `SUMMARY.md` with `artifact scaffold --kind
quick-summary`, then patch only its named sections through fresh leases; query
and patch an existing summary on resume. Never submit, reconstruct, or directly
write either file.

`STATUS.md` must keep only information needed to resume safely:

- intent and observable acceptance;
- in-scope and explicitly excluded behavior;
- confirmed `ordered_work_items` with stable `Q1`, `Q2`, ... ids, deliverable-level dependencies, and one-to-one `work_item_acceptance`;
- current `work_item_status` and execution `batches` for safe ordered resume;
- expected or changed paths;
- current focus, next action, blocker, and material decisions;
- verification commands/results and remaining risk.

The user-facing checkpoint is the Quick card in
`references/human-confirmation.md`, followed conditionally by its UI card. Store
the user-owned decisions—including ordered work items, dependencies, and
work-item acceptance—and `ui_confirmation` separately from the
`agent_execution_plan`; one reply confirms both cards when UI applies. The
confirmed order is deliverable-level. Internal implementation sequencing,
lanes, and batches remain agent-owned.

`understanding_confirmed: false` blocks broad investigation, delegation,
implementation, and validation until the user confirms the checkpoint. A
confirmed discussion handoff digest may satisfy the checkpoint only when quick
introduces no semantic delta.

When Quick consumes a confirmed discussion handoff, first patch
`source_discussion_slug`, `source_contract`, and `review_digest` into `STATUS.md` through leased `specify-runtime artifact patch` calls.
Then mark the source consumed with
`{{specify-subcmd:specify-runtime discussion mark-consumed <slug> --feature-dir <quick-workspace>}}`;
the legacy option name accepts the Quick workspace, whose `STATUS.md` is the
required consumption evidence.

Do not reopen confirmation when repository evidence only adds files, call
sites, tests, or implementation detail needed for the same confirmed outcome
within the confirmed boundary, risk, and authority. Patch the affected
`STATUS.md` fields through a fresh `specify-runtime artifact patch` lease and continue.
Reopen only for a material change to outcome, boundaries, a confirmed work item,
deliverable-level order or dependency, work-item acceptance, confirmed UI
direction, user-visible behavior, risk, authority, migration or compatibility
obligations, an independent capability, or an explicit stop condition; first set
`understanding_confirmed: false` and pause substantive work.

Before presenting the amendment, explain in user-facing prose the new evidence,
why the previous confirmation no longer covers the work, the consequence of
omitting it, the current mutation state and safe pause point, and the exact
incremental decision the user owns. Only after that explanation, present
`## Quick Checkpoint Amendment` with only the changed rows or decisions and an
`Unchanged` statement; do not repeat the full initial Quick Checkpoint. Persist
the confirmed delta before resuming, and do not request duplicate confirmation
when the user already approved that exact delta.

For a UI-only material delta, keep the Quick amendment heading, include only
the changed UI Confirmation rows. State that the main checkpoint is unchanged.
The reason-first explanation remains mandatory; do not replay either complete initial table.

Patch `STATUS.md` through its artifact CLI owner at scope changes, before/after
delegated joins, on blockers, and at terminal verification—not after every
command. Repository evidence may resolve
technical questions; ask the user only for product choices or authority the
repository cannot supply.

Execute confirmed work items in dependency order. A worker packet names one
`work_item_id`, its `depends_on` ids, prerequisite evidence, and its exact
work-item acceptance. Do not start a dependent item until every prerequisite is
accepted. Each `work_item_status` is `pending`, `ready`, `in_progress`,
`blocked`, or `accepted`; only `accepted` satisfies a dependency. Implementation
completion without the item's required acceptance evidence does not unlock its
dependents. Independent ready items may share a batch. One completed batch is
progress, not task completion; close only after every work item is accepted and
the overall completion evidence passes.

Scale up task-local planning when the task develops cross-capability behavior,
architectural or migration decisions, compatibility or rollout obligations, or
acceptance that cannot be stated compactly. Put the expanded dependency,
consequence, and acceptance material in `PLAN.md`; keep its active batch,
decision, and evidence statuses in `STATUS.md`. Use multiple dependency-aware
batches and join points as needed. None of these conditions require
`$spx-specify`, and the request must not be shrunk to make Quick appear small.

Unsafe write overlap is a Quick blocker until lanes are resequenced or isolated.
An unknown root cause routes to `$spx-debug`. `$spx-specify` is used only when
the user explicitly replaces direct delivery with a formal spec-first workflow.

At closeout, `SUMMARY.md` records outcome, changed paths, verification actually
run, skipped checks, residual risk, and recovery state. `STATUS.md` points to it
and reaches `resolved` or `blocked` truthfully.
