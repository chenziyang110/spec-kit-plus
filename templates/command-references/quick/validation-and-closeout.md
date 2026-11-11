Trigger: before final summary, coverage claim, map update, or resolved/blocked state.

Purpose: preserve completion standard, propagation, coverage, output contract, and guardrails.

Preserved Contract: quick completion requires changed surfaces, verification evidence, coverage truth, and truthful resolved/blocked state.

## Completion Standard

Before a build, package, or test attempt, optionally retrieve method cards. First
negotiate `{{specify-subcmd:specify-runtime api ensure --capabilities playbook.find,playbook.show --format json}}`;
if unavailable, continue Quick's own verification without method reuse. Otherwise use
`{{specify-subcmd:specify-runtime playbook find --query <operation-goal> --format json}}`.
Read only a matching pinned `show_argv` and needed `expand_argv`, then check live
scripts, prerequisites, scope, and outputs. This is read-only advice inside the
current Quick Work: preserve its complete verification denominator, item ledger,
and acceptance gates. Do not implicitly invoke DO, create another Work/DoSession,
or substitute historical method success for fresh evidence.

- Quick completion means a transparent closed loop over the complete confirmed outcome: sweep every affected surface, make the required changes across all planned batches, run meaningful verification at the required depth, and record the resulting coverage truthfully.
- Completion requires all three:
  - the change itself is implemented in code, docs, config, or templates as needed
  - at least one smallest meaningful executable verification step has run
  - any unverified surface or remaining gap is called out explicitly instead of being implied away
- For ordered multi-task work, completion additionally requires every confirmed
  work item to have a terminal accepted status, its own mapped acceptance
  evidence, and satisfied dependencies. A passing final check cannot hide a
  skipped or failed work item.
- The final `SUMMARY.md` must include `changed_code_paths` with modified, added, deleted, and renamed paths; `changed_behavior_surfaces` for affected commands, APIs, templates, generated assets, state files, tests, docs, validators, packets, or runtime assumptions; `verification_evidence`; and `project_cognition_refresh` with the shared apply result or authorized source-bound dirty fallback outcome whenever project cognition might be affected.
- `should be fine`, `likely unaffected`, or `not expected to break` are not completion evidence.
- If the change is implemented but verification or coverage is incomplete, do not claim the task is complete. Mark the remaining gap explicitly and continue the sweep or leave the task blocked with the concrete reason.
{{spec-kit-include: ../../command-partials/common/inline-project-cognition-update.md}}

### Hard close gate (runtime-enforced)

Terminal order for source-changing quick work:

Require `cognition.closeout.recovery.v1` and `cognition.closeout.binding.v1` through the shared closeout capability
check before this tail; an older runtime must follow its upgrade/recovery action.

1. After accepted joins, first call the planner in the shared inline closeout contract for the owned changed paths, then use its inputs to begin the native current-work/source binding. Run final verification against that basis and seal it with fresh observations. Legacy or copied passing logs cannot bind newly changed bytes.
2. Inline cognition closeout: use the plan already obtained → complete truthful agent fields → execute returned shared `apply_argv`. Shared apply owns update, validation, eligible finalization, and the durable receipt; do not stamp a second receipt.
3. If an intent is already durable, inspect the exact intent and consume its digest-bound repair/replay actions. Keep Quick active until its own receipt allows close. Only when no trustworthy intent can be formed because the graph is missing or incompatible may Quick negotiate `cognition.closeout.bound-fallback.v1` and use the standalone `quick cognition-closeout <id> --result-state mark-dirty --binding-id <sealed-current-binding-id> --reason "…" --format json` fallback. Binding `begin` can derive current accepted outputs from the joined native Quick Work even when the planner is blocked. Run fresh verification and `seal` that basis first. Runtime requires unchanged source/dependency bytes, complete accepted outputs and no pending intent; a missing native proof keeps the workflow blocked. Unbound legacy receipts remain audit-only.
4. `SUMMARY.md` includes `project_cognition_refresh`; inspect `quick status` and require `cognition_closeout.allowed_close=true`.
5. `specify-runtime quick close <id> resolved` (positional status required)

`quick close … resolved` **blocks** when confirmed `write_scope` / `changed_code_paths` imply project mutation and no valid `cognition-closeout.json` exists. `item-accept` + tests alone cannot close. Inspect the gate with `specify-runtime quick status <id>` → `cognition_closeout` (`required`, `status`, `allowed_close`, `result_state`).

Greenfield / empty graph minimum compliance: when `baseline_kind=greenfield_empty` or compass has no adoptable paths, still obtain `no_op` through shared apply or a runtime-authorized bound `mark-dirty` receipt with an explicit reason (for example `greenfield_empty; no path_index to adopt`). Leaving `project_cognition_refresh.status: not-needed` after real source edits is invalid. Report remaining graph debt and the returned guarded repair action with an unclean fallback.

- Manual map maintenance may record ordinary uncertain closure, partial/low-confidence facts, known unknowns, and `minimal_live_reads` for external repair cases. After a successful existing-baseline maintenance refresh, use `{{specify-subcmd:specify-runtime cognition complete-refresh --format json}}` only for incremental freshness finalization; `sp-map-build` owns `build-from-scan` and `{{specify-subcmd:specify-runtime cognition validate-build --format json}}`, so do not run `complete-refresh` as a rebuild finalizer.

## Propagating Change Rule

- Treat interface signature changes, return-type changes, sync-to-async conversions, renamed commands, renamed config keys, path changes, and similar high-spread edits as a propagating change.
- For any propagating change, the leader must write a minimal plan before editing.
- That plan must name the affected surfaces to sweep, at minimum:
  - implementation
  - wrappers or bindings
  - examples
  - tests
  - docs
  - callsites
- Do not collapse a propagating change into ad-hoc search-and-edit work. The leader must be able to state what will be checked and how completion will be proven.

## Coverage Before Completion

- For propagating changes, sampling is not sufficient.
- Completion requires either:
  - a full-coverage check of every affected callsite or surface
  - or a scripted or pattern-based verification that covers the entire affected set
- If the current pass only covers representative examples, do not claim completion.
- If coverage is still incomplete, continue the sweep, add stronger search or verification, or mark the task blocked with the exact remaining gap.
- `All affected surfaces` means the declared sweep set, not just the files already inspected.

## Output Contract

- Keep `STATUS.md` accurate enough that another session can resume without chat memory.
- Keep the final ordered work-item ledger in `STATUS.md` and summarize every
  work item's outcome and acceptance evidence in `SUMMARY.md`.
- Produce scoped implementation changes, verification evidence, and a truthful resolved/blocked state for the quick task.
- `SUMMARY.md` reports changed code paths, changed behavior surfaces, verification evidence, residual risk, and the `project_cognition_refresh` outcome when project cognition might be affected.
- Preserve scale-up and checkpoint-amendment history so it is clear how the task grew while remaining inside quick and which user-owned decisions were reconfirmed.

## Guardrails

- Do not create a new full feature spec for quick tasks.
- Keep quick-task tracking under `.planning/quick/`.
- Preserve a lightweight planning and validation path rather than skipping discipline entirely.
- Keep each quick task coherent and self-contained. A single quick task may contain multiple capabilities, lanes, batches, architecture decisions, migrations, and acceptance rows when they serve one confirmed outcome.
- Keep leader responsibilities explicit: the leader owns scope, strategy selection, join points, validation, and summary while substantive task work remains packetized for subagent lanes.
- Keep concrete execution on subagent lanes whenever possible. `subagent-blocked` is the final blocked status after recovery options are exhausted, not the default path.
- Quick-task state must be resumable from `STATUS.md` without depending on chat history.
