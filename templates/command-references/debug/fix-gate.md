Trigger: before applying a fix, changing source, or declaring the defect resolved.

Purpose: preserve fix gate, minimum change, verification route, and no surface-only fix rule.

Preserved Contract: fixes must target confirmed root cause and be verified through reproduction and relevant tests.

Session mutation contract: `SESSION PATCH <fields-or-sections>` means build the bounded change in memory, run `specify-runtime artifact prepare --path .planning/debug/[slug].md`, then apply it with `specify-runtime artifact patch --lease <lease-id>` using `--frontmatter-json` or `--section`. Every debug-state update below means `SESSION PATCH`; never edit the Markdown file directly.

## Fix and Verify Protocol

- Enter `fixing` only after the root cause is confirmed.
- Write a failing automated repro test before changing production code.
- Do not modify production behavior until the RED state is proven.
- If no reliable automated test surface exists for the failing behavior, add the missing harness first. If that expands beyond the debug fix lane, route it through `/sp-quick`; use `/sp-specify` only when the user explicitly chooses a formal spec-first path.
- Apply the minimum code change needed to address the confirmed root cause when `execution_model: leader-inline`; when `execution_model: subagent-assisted`, delegate it through a validated subagent lane and integrate the returned evidence on the leader path.
- For a confirmed UI target baseline, recapture the same real entry point,
  viewport/window, and state after the fix; compare it with the baseline and
  original references, record runtime diagnostics, and repair observable drift
  before claiming the UI symptom resolved.
- If the fix cannot proceed safely, cannot be packetized for the selected execution path, or cannot be verified, persist `subagent-blocked`, `execution_surface: none`, and a concrete `blocked_reason` through a fresh `specify-runtime artifact patch` lease.
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
- If verification fails, return to `investigating` with updated evidence. Do not keep layering fixes without updating the hypothesis.
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
