{{spec-kit-include: ../common/user-input.md}}

## Objective

Guide a contextless human through accepting completed product behavior and keep the conversation resumable from `FEATURE_DIR/human-acceptance.json`.

## Process

## Intake and Freshness

- Resolve the feature with `{SCRIPT}` or lane state; stop on an uncertain or ambiguous lane.
- Require fresh `review-state.json` with `status: approved`, every mandatory scenario passed, no blocking finding, and a reviewed fingerprint matching current implementation/configuration evidence. Require the Review-to-Accept handoff's `human_acceptance_obligations`, `human_acceptance_scenarios`, non-empty `reviewed_runtime_targets`, and matching runtime-target digest.
- Transition from the validated `review` stage into `accept` through CLI-owned `workflow.json` via `specify-runtime workflow` before any acceptance-owned write; the runtime state is the required phase lock.
- Run `{{specify-subcmd:specify-runtime accept prepare --feature-dir <feature-dir> --format json}}`. This creates the deterministic state skeleton after Review closeout or reports that the existing guide is stale/conflicting.
- Read the reviewed `implementation-summary.md`, `human-acceptance.json`, frozen Human Acceptance Universe, and real user entrypoint. Each new or changed requirement selected for human verification must retain a stable obligation/scenario mapping; require zero uncovered required obligations and reject deleted, downgraded, unmapped, or source-drifted items. Use Review/code/test evidence only to prepare accurate instructions; do not ask the human to understand it.
- `accept prepare` materializes `runtime_targets` as an exact immutable projection of Review's approved `source`, `build`, `deployment`, or `device` targets and binds scenarios to matching official entrypoints. Do not invent or edit target identity, artifact, deployment, version, configuration, snapshot, ready evidence, linked Review scenarios, `identity_evidence_ref`, or `identity_evidence_sha256`; preserve both identity-evidence fields read-only with the Review target digest. Safely start or health-check that exact target, wait for readiness, prepare or reset isolated acceptance data through documented reversible paths, and open the exact start. Fill only `acceptance_status`, `acceptance_ready_evidence`, and `agent_actions`; do not use production data, deploy without authority, or perform irreversible external effects.
- Validate acceptance-owned rich resume/evidence state with `{{specify-subcmd:specify-runtime hook validate-state --command accept --feature-dir <feature-dir> --format json}}`.

## Zero-Context Reset

Before asking the human to do anything, give them a compact reset:

- what was added or changed;
- what user problem it solves;
- which new or changed requirement journeys they will personally verify;
- prerequisites and exact starting entrypoint;
- what is intentionally outside this acceptance.

Use product words and concrete labels. Do not assume they remember the feature name, branch, commands, architecture, prior decisions, or the last conversation.

## Guided Conversation

- Do not repeat System Review. Reuse its startup, wiring, automated, diagnostics, and broad regression proof; the human acceptance scenarios cover the frozen requirement delta and genuinely human-observable end-to-end outcomes.
- Lead one scenario and one step at a time. Do not present the entire procedure as homework unless the human explicitly asks for a printable checklist.
- For the current step, state the exact click path or command, explain placeholders, state the expected visible result, and state the safe failure branch.
- End with one tiny response request such as “回复 `看到了`；如果没有，发当前画面或报错文本（不要发密钥）”.
- Human performs the real end-to-end actions. The Agent maintains the prepared session, interprets the human's natural reply, and records a structured confirmation bound to the runtime-generated `confirmation_id`, Review-approved runtime target, and reviewed snapshot without changing its meaning. It then updates the step/scenario result and cursor. The final decision uses its separate confirmation id. Agent preparation, automation, or inspection never counts as human PASS and cannot author a receipt without an actual human reply.
- On resume, restate only the accepted context and the exact current step. A fresh Review repair cycle resets every scenario, so rerun the full frozen universe and preserve no earlier PASS.

## Verdict Rules

- `accepted`: the Human Acceptance Universe has zero uncovered required obligations, every required scenario is explicitly `pass` with structured human confirmation against a ready Review-approved `runtime_targets` record bound to the approved reviewed snapshot, no finding is open, `overall.verdict` is `pass`, and the separately confirmed human decision is `accept`.
- `rejected`: at least one observed required behavior fails and the finding records expected, observed, evidence, and repair route.
- `blocked`: the next required observation cannot be performed; preserve the cursor and provide a self-contained Human Action Guide when the boundary is genuinely human-owned.
- Automated tests, agent visual inspection, implementation closeout, or silence from the human never substitute for human PASS.

## Output Contract

- Keep `human-acceptance.json` schema-valid, fresh against the approved Review fingerprint and implementation evidence, and sufficient to resume from the exact current step.
- Preserve the frozen `human_acceptance_obligations`, `human_acceptance_scenarios`, coverage ledger, reviewed target digest, and immutable target identity fields; Acceptance may record only session readiness/actions, progress, human confirmations, and observations, and must not shrink or reinterpret authoritative scope.
- The visible reply restores only the context needed now, gives one current action and expected result, and asks for one minimal human observation.
- Final output records accepted, rejected, or blocked honestly and names the exact next workflow without invoking it.
- After the successful `accept closeout` `next_argv` commits terminal state through `specify-runtime workflow closeout`, `human-acceptance.json`, its immutable terminal snapshot, and the completed runtime are read-only. Changed implementation scope starts a new feature workflow; never rewrite the terminal verdict to draft or stale.

## Guardrails

- Allowed: acceptance-owned fields in runtime-managed `human-acceptance.json`, written through the launcher-bound `accept` CLI subcommands; acceptance-owned rich resume/evidence in `workflow-state.md`, written only through an `artifact prepare` / `artifact submit` lease. Acceptance never authors `workflow.json`; only `specify-runtime workflow` changes that compact phase lock during route-repair or terminal closeout.
- Acceptance must not write production source, tests, `spec.md`, planning/task artifacts, implementation lifecycle records, commits, pushes, deployments, production data, or silent cross-workflow fixes. It may perform only the safe reversible local/sandbox runtime and isolated-fixture preparation described above.
- Accept does not diagnose. Every failed observation first goes to the Review Leader. Record raw expected/observed evidence and, before the handoff, run `{{specify-subcmd:specify-runtime accept route-repair --feature-dir <feature-dir> --finding-id <finding-id> --route <review-route> --expected-revision <revision> --evidence <sanitized-evidence> --format json}}`; do not use it for `human-action`. The result invalidates the prior acceptance and Review verdict, preserves the failed cursor as the first retest point, and returns `repair_handoff_command`, `owning_stage_command`, and `acceptance_return_argv`. Invoke the returned Review handoff separately and stop. Review creates a new cycle, owns diagnosis, uses a read-only diagnostic packet when needed, then owns an independent Fix, independent revalidation, and any later handoff for a proven upstream truth gap. After repair, Review must complete fresh cycle-specific evidence and Acceptance must rerun the entire frozen Human Acceptance Universe with no preserved PASS. A separately stated new-scope request belongs to a later feature workflow and must not rewrite or bypass the failed acceptance route.
- The CLI alone owns `repair_resume`, the append-only `repair_history`, and resolution of Review-routed findings. Never hand-mark one `resolved`: acceptance closeout requires an unbroken route-repair history whose latest cycle matches the current approved Review.

{{spec-kit-include: ../common/blocker-resolution.md}}
