---
description: Use when sp-implement has completed and the integrated product must be started, exercised, repaired, and proven usable from real entrypoints before human acceptance.
workflow_contract:
  when_to_use: '`implementation-handoff.json` exists, the deterministic workflow runtime is ready to transition from `implement` to `review`, and the integrated product needs system-level verification and repair.'
  primary_objective: Review the implemented software as an operable product, find broken startup, interaction, registration, and end-to-end wiring, repair understood in-scope defects, and revalidate the exact affected paths.
  primary_outputs: A fresh approved `review-state.json`, integrated evidence under `review-evidence/`, resolved or routed findings, and a final implementation summary and human-acceptance guide prepared from the reviewed implementation fingerprint.
  default_handoff: Continue review and bounded repair until approved, hand unknown mechanisms to /sp-debug or upstream truth gaps to their owning workflow, then hand human product acceptance to /sp.accept and stop.
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
3. Start the software from every applicable official real entrypoint and wait for its declared ready signal. Build or resume the required scenario matrix covering startup, the changed user journey, affected shared paths, and applicable UI states. Do not substitute unit tests, file presence, or source inspection for operating the product.
4. Choose leader-direct or native subagent lanes from live workload shape. Compile every delegated `SystemReviewPacket` just in time, keep shared runtime and state ownership with the Leader, and accept worker results only as evidence rather than a final verdict.
5. Exercise real actions and observable results. Trace button, link, menu, form, command, route, handler, provider, factory, service, persistence or external dependency, and user feedback wiring where applicable. For UI scenarios capture integrated `structure_snapshot`, `visual_capture`, and `runtime_diagnostics` evidence from the real entrypoint.
6. Record each mismatch as a finding. Repair an understood bounded in-scope defect here, add or strengthen regression coverage, restart the real product, rerun the exact failed scenario, and revalidate affected journeys. Hand unknown root cause to `{{invoke:debug}}`; reopen `sp-implement`, `sp-tasks`, `sp-plan`, `sp-clarify`, `sp-specify`, or `sp-design` when the owning truth is outside Review.
7. After the final integrated restart, run `{{specify-subcmd:review validate --feature-dir <feature-dir> --format json}}`, record its current fingerprint as the reviewed snapshot, and set approved only when every mandatory scenario passes with required integrated evidence and no blocking finding remains. Then run `{{specify-subcmd:review closeout --feature-dir <feature-dir> --format json}}`, execute its returned `workflow complete-stage` argv separately, recommend `{{invoke:accept}}`, and stop. Do not claim the product is review-approved from worker narration, stale evidence, or automated checks alone.

{{spec-kit-include: ../command-partials/common/inline-project-cognition-update.md}}

## Detailed References

Read [Reference index](references/INDEX.md) before applying detailed contracts.

- [system scenario contract](references/system-scenario-contract.md)
- [subagent review contract](references/subagent-review-contract.md)
- [repair and revalidation](references/repair-and-revalidation.md)
- [final claim and handoff](references/final-claim-and-handoff.md)
