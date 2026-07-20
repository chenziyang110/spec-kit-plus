---
description: Use when sp-implement has completed and the integrated product must be started, exercised, repaired, and proven usable from real entrypoints before human acceptance.
workflow_contract:
  when_to_use: '`implementation-handoff.json` exists, the deterministic workflow runtime is ready to transition from `implement` to `review`, and the integrated product needs system-level verification and repair.'
  primary_objective: Review the implemented software as an operable product, find broken startup, interaction, registration, and end-to-end wiring, repair understood in-scope defects, and revalidate the exact affected paths.
  primary_outputs: A fresh approved `review-state.json`, integrated evidence under `review-evidence/`, resolved or routed findings, and a final implementation summary and human-acceptance guide prepared from the reviewed implementation fingerprint.
  default_handoff: Continue the Leader-owned Review Universe through independent audit, Fix, join, and revalidation waves until approved; only hand proven requirement, design, or architecture truth gaps to their owning upstream workflow, then hand human product acceptance to /sp.accept and stop.
scripts:
  sh: scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
  ps: scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks
---

{{spec-kit-include: ../command-partials/review/shell.md}}

{{spec-kit-include: ../command-partials/common/senior-consequence-analysis-gate.md}}

{{spec-kit-include: ../command-partials/common/agent-phase-handoff.md}}

[AGENT] For project-cognition-backed semantic intake, routing, audit, resume, or final-claim gates, read `references/semantic-work-contract.md`.

## Main Flow

1. Run `{SCRIPT}` to resolve one implemented feature, inspect repository status, and transition from the validated `implement` stage into `review` through the deterministic workflow runtime. Run `{{specify-subcmd:review prepare --feature-dir <feature-dir> --format json}}`; stop when the implementation handoff or fingerprint is missing, stale, or ambiguous.
2. Read `implementation-handoff.json`, current `review-state.json`, required acceptance refs, official entrypoints, and only the live source needed for the current scenario. Treat this as the mandatory system review after implementation; retain the embedded task review inside `sp-implement` as a separate task-level control.
3. Compile the bounded Review Universe from authoritative acceptance obligations, official entrypoints, changed consumer surfaces, runtime-discovered controls and registrations, and affected regression paths. Use independent coverage discovery so the handoff scenario matrix is a minimum rather than a blind spot; the Leader owns the zero-uncovered reconciliation.
4. Start the software from every applicable official real entrypoint and wait for its declared ready signal. The Leader orchestrates subagents through an independent read-only Review/Audit wave: compile just-in-time audit `SystemReviewPacket`s with disjoint coverage slices, join every result, reconcile duplicate or missing findings, and forbid audit workers from editing product code or declaring coverage complete.
5. Exercise real actions and observable results. Trace button, link, menu, form, command, route, handler, provider, factory, service, persistence or external dependency, and user feedback wiring where applicable. For UI scenarios capture integrated `structure_snapshot`, `visual_capture`, and `runtime_diagnostics` evidence from the real entrypoint.
6. After the audit join, run an independent Fix wave. The Leader sends bounded Fix workers one or more accepted findings with authoritative expected behavior, isolated write scopes, forbidden truth artifacts, and exact regression obligations. Every approved-scope defect stays inside Review regardless of repair size: missing code, a task omission, incomplete tests, broken wiring, and an unknown root cause are not reasons to exit. Use a read-only diagnostic packet for an unknown root cause; Review remains the stage owner and then dispatches the repair itself.
7. Join and inspect every repair result, restart the integrated product, and run an independent revalidation wave. A repair author must not verify its own finding; the Leader or a different read-only subagent reruns the exact failed journey, dependent scenarios, and credible regression set against the post-repair fingerprint.
8. Only a proven upstream truth gap may stop Review: requirement truth that is missing or contradictory, design truth that is missing or contradictory, or architecture truth that must change before any correct implementation is possible. Missing code is not an upstream truth gap. After all packets joined and the Review Universe reports zero uncovered obligations and surfaces, run `{{specify-subcmd:review validate --feature-dir <feature-dir> --format json}}`, bind its current fingerprint, and approve only with fresh integrated evidence and zero blocking findings. Then run `{{specify-subcmd:review closeout --feature-dir <feature-dir> --format json}}`, execute its returned `workflow complete-stage` argv separately, recommend `{{invoke:accept}}`, and stop.

{{spec-kit-include: ../command-partials/common/inline-project-cognition-update.md}}

## Detailed References

Read [Reference index](references/INDEX.md) before applying detailed contracts.

- [system scenario contract](references/system-scenario-contract.md)
- [subagent review contract](references/subagent-review-contract.md)
- [repair and revalidation](references/repair-and-revalidation.md)
- [final claim and handoff](references/final-claim-and-handoff.md)
