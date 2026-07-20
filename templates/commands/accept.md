---
description: Use when mandatory system review is approved and a human needs to understand and personally accept the reviewed feature without relying on old chat context.
workflow_contract:
  when_to_use: '`review-state.json` is fresh and approved, `implementation-summary.md` exists for the reviewed fingerprint, and a human should be guided through product acceptance before integration or delivery.'
  primary_objective: Restore the human's context, prepare the reviewed product safely, guide the human through end-to-end verification of every new or changed requirement, persist observed results, and produce an explicit accepted, rejected, or blocked verdict.
  primary_outputs: A fresh, schema-valid `human-acceptance.json` whose frozen Human Acceptance Universe has zero uncovered required obligations, a verified runtime identity, zero-context orientation, ordered human-performed scenarios, step results, evidence, findings, resume cursor, and overall human verdict.
  default_handoff: On pass, continue to integration or delivery; every failed observation first goes to the Review Leader for diagnosis, repair, independent revalidation, or a proven upstream-truth handoff. Human-only access remains blocked in Acceptance with an exact guide.
scripts:
  sh: scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
  ps: scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks
---

{{spec-kit-include: ../command-partials/accept/shell.md}}

{{spec-kit-include: ../command-partials/common/agent-phase-handoff.md}}

## Main Flow

1. Resolve the exact reviewed feature and require a trusted `implementation-summary.md` plus fresh `review-state.json` with `status: approved`, passing mandatory scenarios, required integrated evidence, no blocking finding, and a matching reviewed fingerprint. Require the Review-to-Accept handoff's `human_acceptance_obligations`, `human_acceptance_scenarios`, non-empty `reviewed_runtime_targets`, and matching runtime-target digest. Transition from `review` to `accept` through the deterministic workflow runtime; it validates Review closeout and stops on exit `10`. Only then prepare or freshness-check `human-acceptance.json` with `{{specify-subcmd:accept prepare --feature-dir <feature-dir> --format json}}`. If Review is absent, failed, blocked, stale, incomplete, or lacks that identity basis, hand back to `{{invoke:review}}` and stop.
2. Read the implementation summary and the frozen Human Acceptance Universe. It contains every new or changed requirement selected for human end-to-end verification. Require zero uncovered required obligations and reject deleted, downgraded, unmapped, or source-drifted obligations. Treat the human as returning with no useful memory of the prior conversation.
3. `accept prepare` materializes `runtime_targets` as an exact immutable projection of Review's approved targets (`source`, `build`, `deployment`, or `device`) and binds each scenario to the matching official entrypoint. Do not invent or edit target identity, artifact, deployment, version, configuration, snapshot, ready evidence, linked Review scenarios, `identity_evidence_ref`, or `identity_evidence_sha256`; preserve both identity-evidence fields read-only with the Review target digest. Before asking the human to act, safely start or health-check that exact target, wait for readiness, prepare or reset isolated acceptance test data through documented reversible paths, and open the exact starting point when tooling permits. Acceptance may fill only session fields such as `acceptance_status`, `acceptance_ready_evidence`, and `agent_actions`. Never use production data, deploy without authority, or perform an irreversible external side effect.
4. Explain the outcome, why it matters, the new or changed requirements the human will verify, exclusions, prerequisites, and exact starting point in ordinary product language. Use the frozen `human_acceptance_scenarios`; do not invent a smaller scope. Every step names the exact human action, visible expected result, safe failure branch, and minimal reply/evidence to return. Do not repeat System Review: reuse its startup, wiring, automated, diagnostics, and broad regression proof instead of turning that matrix into human homework.
5. Present a short context reset, then guide only the current step. Human performs the real end-to-end requirement journey; the Agent explains labels and placeholders, maintains the environment, may inspect sanitized diagnostics after an observation, persists the human's actual result and resume cursor, and advances one step at a time. Accept short replies such as “看到了”, “没有”, “通过”, or a screenshot/error; translate each actual reply into a structured human confirmation bound to the runtime-generated `confirmation_id`, runtime target, and reviewed snapshot without changing its meaning. Record the final human decision through the separate decision confirmation. Agent preparation, automation, or inspection never counts as human PASS and cannot author these receipts without an actual human reply.
6. PASS only when every required human acceptance obligation is covered, every required scenario has an explicit structured human pass bound to a ready Review-approved `runtime_targets` record and reviewed snapshot, no finding remains open, and the human makes the final acceptance decision. Record any mismatch as raw expected/observed/evidence without editing production source. Accept does not diagnose. Every failed observation first goes to the Review Leader; Review owns diagnosis, an independent Fix, independent revalidation, and any later proven upstream-truth route. Any repair creates a fresh Review cycle and invalidates every human scenario, so Acceptance reruns the full frozen Human Acceptance Universe beginning at the failed cursor and preserves no old PASS. Run `{{specify-subcmd:accept closeout --feature-dir <feature-dir> --format json}}` only after explicit human acceptance, then execute its successful `next_argv` verbatim to commit terminal workflow closeout; never reconstruct the revision-bound command.

## Workflow Boundary

- This is human product acceptance, not the task review embedded in `sp-implement` or the mandatory system proof-and-repair work owned by `sp-review`.
- This workflow may write only `human-acceptance.json` and the acceptance-owned fields of `workflow-state.md`. It must not edit production source, tests, specs, plans, tasks, or implementation lifecycle records.
- Safe reversible acceptance-session operations are allowed: start or stop an approved local/sandbox target, check readiness, open the reviewed start location, and prepare or reset isolated test fixtures through documented commands. Preserve Review's immutable target identity and record only acceptance-session readiness/actions; these operations do not authorize production mutation, deployment, or the human's verdict.
- Technical implementation and system Review can be complete while human acceptance remains pending. Never collapse those statuses.
- If the reviewed fingerprint, Review evidence, runtime-target digest, or implementation summary fingerprint changed, mark acceptance stale and return to `{{invoke:review}}` before rebuilding the guide. Never reuse a previous PASS after a repair or against changed implementation evidence.
- Do not dump a long checklist and leave the human alone. Lead one current step, say what success looks like, say what to return if it fails, and preserve the next resume point.

## Failure Routing

- Accept does not diagnose or select an implementation/upstream owner. Record the human's expected result, actual observation, sanitized evidence, runtime identity, and preserved scenario cursor.
- Every failed observation first goes to the Review Leader through `{{invoke:review}}`, including an apparent requirement gap, unknown mechanism, clear code defect, missing implementation, regression, or large repair. Review performs diagnosis, dispatching a read-only diagnostic packet when the mechanism is unknown, then owns an independent Fix and independent revalidation in a new Review cycle; only Review may hand off a proven requirement, design, or architecture truth gap to its upstream owner. After repair, rerun every frozen human scenario; do not preserve a prior PASS.
- Environment, permission, protected service, or physical-device access blocks the next step: preserve the cursor and use the shared Human Action Guide contract without creating a repair route.
- A separately stated new-scope request is not an acceptance-failure classification. Record it outside the failed scenario for a later feature workflow; do not use it to bypass Review or rewrite the frozen Human Acceptance Universe.
- The human cannot decide yet: keep `status: in_progress` or `blocked`; do not manufacture a verdict.

## Completion Reply

On acceptance, summarize in the human's language:

- what they personally verified;
- which scenarios passed and any intentionally unrun optional scenarios;
- residual risk or exclusions;
- where the durable acceptance record lives;
- the exact next delivery or integration action, without invoking it automatically.
