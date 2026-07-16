---
description: Use when implementation closeout is complete and a human needs to understand and personally accept the finished feature without relying on old chat context.
workflow_contract:
  when_to_use: '`implementation-summary.md` exists, technical closeout passed, and a human should be guided through product acceptance before integration or delivery.'
  primary_objective: Restore the human's context, lead one exact product scenario and step at a time, persist observed results, and produce an explicit accepted, rejected, or blocked verdict.
  primary_outputs: A fresh, schema-valid `human-acceptance.json` with zero-context orientation, ordered scenarios, step results, evidence, findings, resume cursor, and overall human verdict.
  default_handoff: On pass, continue to integration or delivery; on a product defect return to /sp.implement or /sp.debug; on missing or changed requirements return to /sp.clarify or /sp.specify.
scripts:
  sh: scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
  ps: scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks
---

{{spec-kit-include: ../command-partials/accept/shell.md}}

{{spec-kit-include: ../command-partials/common/agent-phase-handoff.md}}

## Main Flow

1. Resolve the exact completed feature and require a trusted `implementation-summary.md`. Transition from `implement` to `accept` through the deterministic workflow runtime; it validates technical closeout and stops on exit `10`. Only then prepare or freshness-check `human-acceptance.json` with `{{specify-subcmd:accept prepare --feature-dir <feature-dir> --format json}}`. If implementation closeout is missing or untrusted, hand back to `{{invoke:implement}}` and stop.
2. Read the implementation summary, spec acceptance, task outcomes, and only the live entrypoint evidence needed to explain the shipped behavior. Treat the human as returning with no useful memory of the prior conversation.
3. Build the acceptance state from `.specify/templates/human-acceptance-state-template.json` and schema. Explain the outcome, why it matters, user-visible changes, exclusions, prerequisites, and exact starting point in ordinary product language. Do not make the human inspect diffs, source, test logs, or planning artifacts.
4. Create the smallest complete ordered scenario set that proves the user-visible value. Every step names the exact action, visible expected result, safe failure branch, and the minimal reply/evidence to return. Validate the state before starting.
5. Present a short context reset, then guide only the current step. Wait for the human's observed result, persist it and the resume cursor, and advance one step at a time. Accept short replies such as “看到了”, “没有”, “通过”, or a screenshot/error; translate them into the structured state yourself.
6. PASS only when every required scenario has an explicit human pass. Record a mismatch as a finding with expected/observed/evidence and route it without editing production source in this workflow. Run `{{specify-subcmd:accept closeout --feature-dir <feature-dir> --format json}}` only after explicit human acceptance, then execute its successful `next_argv` verbatim to commit terminal workflow closeout; never reconstruct the revision-bound command.

## Workflow Boundary

- This is human product acceptance, not the internal code review already embedded in `sp-implement`.
- This workflow may write only `human-acceptance.json` and the acceptance-owned fields of `workflow-state.md`. It must not edit production source, tests, specs, plans, tasks, or implementation lifecycle records.
- A technical implementation can be complete while human acceptance remains pending. Never collapse those two statuses.
- If the implementation summary fingerprint changed, mark acceptance stale, rebuild the guide from current evidence, and restart only the affected scenarios. Never reuse a previous PASS against changed implementation evidence.
- Do not dump a long checklist and leave the human alone. Lead one current step, say what success looks like, say what to return if it fails, and preserve the next resume point.

## Failure Routing

- Observed product behavior differs from the approved requirement and the cause is unknown: record evidence, hand to `{{invoke:debug}}`, and stop.
- The repair is clear and requirements are still correct: record evidence, hand to `{{invoke:implement}}`, and stop.
- The human expects behavior absent from or contradictory to the approved requirement: route to `{{invoke:clarify}}` for an existing feature or `{{invoke:specify}}` for new scope, and stop.
- Environment, permission, protected service, or physical-device access blocks the next step: preserve the cursor and use the shared Human Action Guide contract.
- The human cannot decide yet: keep `status: in_progress` or `blocked`; do not manufacture a verdict.

## Completion Reply

On acceptance, summarize in the human's language:

- what they personally verified;
- which scenarios passed and any intentionally unrun optional scenarios;
- residual risk or exclusions;
- where the durable acceptance record lives;
- the exact next delivery or integration action, without invoking it automatically.
