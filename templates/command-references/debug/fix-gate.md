Trigger: before applying a fix, changing source, or declaring the defect resolved.

Purpose: preserve fix gate, minimum change, verification route, and no surface-only fix rule.

Preserved Contract: fixes must target confirmed root cause and be verified through reproduction and relevant tests.

Session mutation contract: `SESSION PATCH <fields-or-sections>` means build the bounded same-checkpoint delta in memory. When one semantic boundary updates multiple debug-session frontmatter fields or sections and `api list` exposes `artifact.patch-batch`, prefer one `specify-runtime artifact prepare --path .planning/debug/[slug].md` plus one `specify-runtime artifact patch-batch --lease <lease-id>` that aggregates those updates. For a single target update, or on older runtimes, fall back to one leased `specify-runtime artifact patch` using `--frontmatter-json` or `--section`. Every debug-state update below means `SESSION PATCH`; never edit the Markdown file directly.

## Write Authorization and Guard Scope

Before any source, test, harness, configuration, or instrumentation write,
check the confirmed authority, current anchors, and declared scope through
`specify-runtime execution guard`. Diagnosis-only authority does not permit
these writes; use Diagnosis-Only Delivery in `references/debug-state.md`.
Register necessary supporting scope through the current owner. After scope
expansion or source drift affecting the binding, renew the guard before the
affected write; an earlier guard is not an unlimited editing permit.

A permitted supporting repair or diagnostic probe may precede original target
RED only within its own guarded scope. Preserve its before-state, causal
evidence, observed result, and cleanup separately. This does not bypass target
RED before changing the original target's production behavior, authorize an
unrelated refactor, or count supporting recovery as resolution of that defect.

## Fix and Verify Protocol

- Enter `fixing` only after the root cause is confirmed.
- Write a failing automated repro test before changing production code.
- Do not modify production behavior until the RED state is proven.
- If no reliable automated test surface exists for the failing behavior, add the missing harness first. Preserve the Debug session, expand the smallest authorized causal scope through its owner, and repair the harness inside the active Debug recovery lane. Verify the harness and resume the original reproduction in the same invocation; do not route an agent-capable harness repair to another workflow. Use `/sp-specify` only when the user explicitly chooses a formal spec-first path.
- RED must match the target failure signature on the pre-fix behavior. An import error, missing dependency, timeout, or broken fixture does not satisfy RED for a different defect. Preserve the original failure evidence and do not weaken the assertion to obtain GREEN.
- Before production edits, verify exact fix authority, current source/patch anchors, accepted causal evidence, and `specify-runtime execution guard`. Diagnosis-only authority does not permit a fix or instrumentation write. Keep unrelated user changes untouched.
- Apply the minimum code change needed to address the confirmed root cause when `execution_model: leader-inline`; when `execution_model: subagent-assisted`, delegate it through a validated subagent lane and integrate the returned evidence on the leader path.
- For a confirmed UI target baseline, recapture the same real entry point,
  viewport/window, and state after the fix; compare it with the baseline and
  original references, record runtime diagnostics, and repair observable drift
  before claiming the UI symptom resolved.
- If the selected delegated fix cannot be packetized, repair the packet or
  dispatch surface, use a safe leader-owned lane when eligible, or expand a
  tracked internal Debug recovery lane and return. Persist `subagent-blocked` only as dispatch
  evidence. Mark the Debug workflow blocked only when the fix or verification
  needs a proven human/external boundary and no safe authorized fallback exists.
- Fix the owning control-plane failure first. Do not treat a UI/status smoothing change as sufficient unless the closed loop is proven healthy end-to-end.
- Classify the fix before verification:
  - include the classification in the in-memory `fix_scope` patch payload and persist it through `specify-runtime artifact patch`
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
- Patch `loop_restoration_proof` through a fresh `specify-runtime artifact patch` lease before moving to `resolved`. This loop restoration proof should show why the full loop is healthy now, not merely why one surface looks better.
- If verification fails, return to `investigating` with updated evidence. Distinguish the target defect, a repair-induced regression, and an infrastructure failure. Recover supporting failures and resume the original gate; a repair-induced regression invalidates affected downstream evidence. Do not keep layering fixes without updating the hypothesis.
- Before final verification, remove only session-owned temporary probes/resources or document deliberately retained diagnostics. Re-run affected checks after cleanup on the final integrated revision. Never restore an entire file or reset the worktree to discard a failed patch; reverse only owned changes after inspecting the current diff.
- If automated or human verification fails repeatedly without a stronger causal explanation, stop the local fix loop. If `.planning/debug/[slug].research.md` is absent, create its fixed shape with `specify-runtime artifact scaffold --kind research --path .planning/debug/[slug].research.md`; otherwise query it with `artifact show`. Patch only its named semantic sections through fresh leases, never submit or reconstruct the whole checkpoint, and do not change code again until the research gate is satisfied.
- Persist missing contract facts, environment assumptions, external references, or repository evidence into that debug-local research checkpoint through fresh `specify-runtime artifact patch` leases.
- Treat the returned project cognition compass packet and readiness as the default intake source for brownfield debug runtime coverage; use only returned `minimal_live_reads` when needed.
- Before moving to `awaiting_human_verify` or `resolved`, persist `changed_code_paths`, `changed_behavior_surfaces`, `verification_evidence`, and `project_cognition_refresh` through fresh `specify-runtime artifact patch` leases. Include modified, added, deleted, and renamed paths plus affected commands, APIs, templates, generated assets, state files, tests, docs, validators, packets, or runtime assumptions.
{{spec-kit-include: ../../command-partials/common/inline-project-cognition-update.md}}
- Manual map maintenance may record ordinary uncertain closure, partial/low-confidence facts, known unknowns, and `minimal_live_reads` for external repair cases. After a successful existing-baseline maintenance refresh, use `{{specify-subcmd:specify-runtime cognition complete-refresh --format json}}` only for incremental freshness finalization; `sp-map-build` owns `build-from-scan` and `{{specify-subcmd:specify-runtime cognition validate-build --format json}}`, so do not run `complete-refresh` as a rebuild finalizer.
- The completion claim must be backed by live code, tests, scripts, configuration, or authoritative docs; project cognition can support route selection but cannot be the sole evidence for completion. Continue only when verification is truthfully green and no explicit blocker prevents completion.
- [AGENT] Resolved debug sessions should auto-capture reusable lessons from the persisted debug session state into index/detail entries.
- [AGENT] If you are finalizing outside the normal debug CLI closeout path, run `{{specify-subcmd:specify-runtime learning capture-auto --command debug --session-file .planning/debug/[slug].md --format json}}`.
- [AGENT] If the auto-capture pass produced no captured lesson but you still discovered a reusable `pitfall`, `recovery_path`, or `project_constraint`, use the manual `learning capture` helper surface to create or merge a candidate.
  Required options: `--command`, `--type`, `--summary`, `--evidence`
- [AGENT] Before leaving the debug session in a terminal state, apply the Learning Reflex and capture any reusable `pitfall`, `recovery_path`, `tooling_trap`, `false_lead_pattern`, or `project_constraint` through the CLI when durable state did not already preserve it.
- Treat one-off findings as no reusable lesson; store reusable lessons as index/detail entries, and use `{{specify-subcmd:specify-runtime learning promote --target learning ...}}` only after explicit confirmation or proven recurrence.
- Only ask for confirmation when a new learning is highest-signal, such as an explicit user default, clear cross-stage reuse, or repeated recurrence that should become shared project memory.
