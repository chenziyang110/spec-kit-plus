Trigger: before final summary, coverage claim, map update, or resolved/blocked state.

Purpose: preserve completion standard, propagation, coverage, output contract, and guardrails.

Preserved Contract: quick completion requires changed surfaces, verification evidence, coverage truth, and truthful resolved/blocked state.

## Completion Standard

- Quick completion means a small, transparent closed loop: sweep the affected surfaces, make the required change, run at least one meaningful verification step, and record the resulting coverage truthfully.
- Completion requires all three:
  - the change itself is implemented in code, docs, config, or templates as needed
  - at least one smallest meaningful executable verification step has run
  - any unverified surface or remaining gap is called out explicitly instead of being implied away
- The final `SUMMARY.md` must include `changed_code_paths` with modified, added, deleted, and renamed paths; `changed_behavior_surfaces` for affected commands, APIs, templates, generated assets, state files, tests, docs, validators, packets, or runtime assumptions; `verification_evidence`; and `project_cognition_refresh` with the inline update result or fallback `project-cognition mark-dirty` outcome whenever project cognition might be affected.
- `should be fine`, `likely unaffected`, or `not expected to break` are not completion evidence.
- If the change is implemented but verification or coverage is incomplete, do not claim the task is complete. Mark the remaining gap explicitly and continue the sweep or leave the task blocked with the concrete reason.
{{spec-kit-include: ../../command-partials/common/inline-project-cognition-update.md}}
- Manual map maintenance may record ordinary uncertain closure, partial/low-confidence facts, known unknowns, and `minimal_live_reads` for external repair cases. After a successful existing-baseline maintenance refresh, use `{{specify-subcmd:project-cognition complete-refresh --format json}}` only for incremental freshness finalization; `sp-map-build` owns `build-from-scan` and `{{specify-subcmd:project-cognition validate-build --format json}}`, so do not run `complete-refresh` as a rebuild finalizer.

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
- Produce scoped implementation changes, verification evidence, and a truthful resolved/blocked state for the quick task.
- `SUMMARY.md` reports changed code paths, changed behavior surfaces, verification evidence, residual risk, and the `project_cognition_refresh` outcome when project cognition might be affected.
- Preserve escalation history so it is clear why the task stayed quick or needed to grow.

## Guardrails

- Do not create a new full feature spec for quick tasks.
- Keep quick-task tracking under `.planning/quick/`.
- Preserve a lightweight planning and validation path rather than skipping discipline entirely.
- Keep quick tasks atomic and self-contained.
- Keep leader responsibilities explicit: the leader owns scope, strategy selection, join points, validation, and summary while substantive task work remains packetized for subagent lanes.
- Keep concrete execution on subagent lanes whenever possible. `subagent-blocked` is the final blocked status after recovery options are exhausted, not the default path.
- Quick-task state must be resumable from `STATUS.md` without depending on chat history.
