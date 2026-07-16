Trigger: before applying a fix, changing source, or declaring the defect resolved.

Purpose: preserve fix gate, minimum change, verification route, and no surface-only fix rule.

Preserved Contract: fixes must target confirmed root cause and be verified through reproduction and relevant tests.

## Fix and Verify Protocol

- Enter `fixing` only after the root cause is confirmed.
- Write a failing automated repro test before changing production code.
- Do not modify production behavior until the RED state is proven.
- If no reliable automated test surface exists for the failing behavior, add the missing harness first or route through `/sp-quick` or `/sp-specify` before code changes.
- Apply the minimum code change needed to address the confirmed root cause when `execution_model: leader-inline`; when `execution_model: subagent-assisted`, delegate it through a validated subagent lane and integrate the returned evidence on the leader path.
- For a confirmed UI target baseline, recapture the same real entry point,
  viewport/window, and state after the fix; compare it with the baseline and
  original references, record runtime diagnostics, and repair observable drift
  before claiming the UI symptom resolved.
- If the fix cannot proceed safely, cannot be packetized for the selected execution path, or cannot be verified, record `subagent-blocked` with `execution_surface: none` and a concrete `blocked_reason`.
- Fix the owning control-plane failure first. Do not treat a UI/status smoothing change as sufficient unless the closed loop is proven healthy end-to-end.
- Classify the fix before verification:
  - write the classification to `fix_scope`
  - `truth-owner`
  - `control-boundary`
  - `observation-boundary`
  - `surface-only`
- `surface-only` means the change smooths or hides the symptom without repairing the owning truth or the broken handoff. A `surface-only` fix cannot satisfy the debug contract.
- After changing code, rerun:
  - the reproduction path,
  - the most relevant tests,
  - and any logging-enhanced repro flow needed to prove the mechanism changed.
- Verify the full control loop, not only one function or field:
  - triggering input,
  - control decision,
  - resource allocation,
  - resulting state transition,
  - and external observation.
- Record `loop_restoration_proof` before moving to `resolved`. This loop restoration proof should show why the full loop is healthy now, not merely why one surface looks better.
- If verification fails, return to `investigating` with updated evidence. Do not keep layering fixes without updating the hypothesis.
- If automated verification or human verification fails repeatedly without producing a stronger causal explanation, stop the local fix loop and create or refresh `.planning/debug/[slug].research.md` before another code change.
- Use that debug-local research checkpoint to record the missing contract facts, environment assumptions, external references, or repository evidence needed to break the loop.
- Treat the returned project cognition compass packet and readiness as the default intake source for brownfield debug runtime coverage; use only returned `minimal_live_reads` when needed.
- Before moving to `awaiting_human_verify` or `resolved`, record `changed_code_paths` with modified, added, deleted, and renamed paths; `changed_behavior_surfaces` for affected commands, APIs, templates, generated assets, state files, tests, docs, validators, packets, or runtime assumptions; `verification_evidence`; and `project_cognition_refresh` when project cognition might be affected.
{{spec-kit-include: ../../command-partials/common/inline-project-cognition-update.md}}
- Manual map maintenance may record ordinary uncertain closure, partial/low-confidence facts, known unknowns, and `minimal_live_reads` for external repair cases. After a successful existing-baseline maintenance refresh, use `{{specify-subcmd:project-cognition complete-refresh --format json}}` only for incremental freshness finalization; `sp-map-build` owns `build-from-scan` and `{{specify-subcmd:project-cognition validate-build --format json}}`, so do not run `complete-refresh` as a rebuild finalizer.
- The completion claim must be backed by live code, tests, scripts, configuration, or authoritative docs; project cognition can support route selection but cannot be the sole evidence for completion. Continue only when verification is truthfully green and no explicit blocker prevents completion.
- [AGENT] Resolved debug sessions should auto-capture reusable lessons from the persisted debug session state into index/detail entries.
- [AGENT] If you are finalizing outside the normal debug CLI closeout path, run `{{specify-subcmd:learning capture-auto --command debug --session-file .planning/debug/[slug].md --format json}}`.
- [AGENT] If the auto-capture pass produced no captured lesson but you still discovered a reusable `pitfall`, `recovery_path`, or `project_constraint`, use the manual `learning capture` helper surface to create or merge a candidate.
  Required options: `--command`, `--type`, `--summary`, `--evidence`
- [AGENT] Before leaving the debug session in a terminal state, apply the Learning Reflex and capture any reusable `pitfall`, `recovery_path`, `tooling_trap`, `false_lead_pattern`, or `project_constraint` through the CLI when durable state did not already preserve it.
- Treat one-off findings as no reusable lesson; store reusable lessons as index/detail entries, and use `{{specify-subcmd:learning promote --target learning ...}}` only after explicit confirmation or proven recurrence.
- Only ask for confirmation when a new learning is highest-signal, such as an explicit user default, clear cross-stage reuse, or repeated recurrence that should become shared project memory.
