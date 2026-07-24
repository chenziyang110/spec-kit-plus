---
name: spx-accept
description: Advanced post-Review human acceptance workflow. Use after fresh approved Review closeout to restore a contextless human's understanding, guide one real product step at a time, and persist an explicit pass, fail, or blocked verdict.
---

# SPX Accept

Read `references/project-learning.md` and apply its consume-only policy.
Read `references/workflow-runtime.md` and let its CLI own phase state.
Read `references/project-cognition.md`, using cognition intent `ask`. Read
`references/acceptance-contract.md` and `references/blocker-resolution.md`. Read
`references/ui-quality-gate.md` when any acceptance scenario is UI-bearing.

Resolve exactly one system-reviewed feature and require a trusted
`review-state.json` with fresh `approved` verdict, its final reviewed
fingerprint, the Review-refreshed `implementation-summary.md`, and a
Review-to-Accept handoff containing `human_acceptance_obligations`,
`human_acceptance_scenarios`, non-empty `reviewed_runtime_targets`, and a
matching target digest. If Review is
missing, blocked, stale, or not approved, hand off to `$spx-review` and stop;
do not bypass Review by routing directly to `$spx-implement`. Transition from the validated `review`
stage into `accept` through the workflow runtime. Only then run
`{{specify-subcmd:specify-runtime accept prepare --feature-dir <feature-dir> --format json}}`
to create or freshness-check `human-acceptance.json`.

Treat the human as returning later with no useful chat memory. Read the summary,
frozen Human Acceptance Universe, and real entrypoint evidence. It covers every
new or changed requirement selected for human end-to-end verification; require
zero uncovered required obligations and reject deleted, downgraded, unmapped,
or source-drifted items. Fill only acceptance-owned progress and orientation in
the installed template/schema; do not invent a smaller scenario set or ask the
human to inspect source, diffs, test logs, specs, plans, or task state.

`accept prepare` materializes `runtime_targets` as an exact immutable projection
of Review's approved `source`, `build`, `deployment`, or `device` targets and
binds each scenario to its matching official entrypoint. Do not invent or edit
identity, artifact, deployment, version, configuration, snapshot, ready
evidence, linked Review scenarios, `identity_evidence_ref`, or
`identity_evidence_sha256`; preserve both identity-evidence fields read-only
with the Review target digest. Safely start or health-check that exact
target, wait for readiness, prepare or reset isolated acceptance data through
documented reversible paths, and open the exact start when tooling permits.
Fill only session `acceptance_status`, `acceptance_ready_evidence`, and
`agent_actions`. Never use production data, deploy without authority, or
perform an irreversible external side effect.

Validate the acceptance-owned rich resume/evidence state with
`{{specify-subcmd:specify-runtime hook validate-state --command accept --feature-dir
<feature-dir> --format json}}`. A changed Review digest, final source
fingerprint, or implementation-summary fingerprint makes the guide stale; hand
off to `$spx-review` to revalidate current product evidence before continuing.

Start with a compact context reset: what changed, why it matters, what the human
will verify, prerequisites, exact entrypoint, and exclusions. Then guide only
one current scenario step. Give an exact action, visible expected result, safe
failure branch, and a tiny reply request. Translate natural replies into durable
step results/evidence and advance the cursor yourself. Persist each actual reply
as a structured human confirmation bound to the runtime-generated confirmation
id, approved target, and reviewed snapshot; use the separate decision
confirmation for the final verdict. Never author a human receipt without an
actual human reply. On an ordinary resume, continue from the cursor.

Do not repeat System Review. Reuse its startup, wiring, automated, diagnostics,
and broad regression proof. Human performs the frozen new-or-changed requirement
journey from the real entrypoint; Agent preparation, automation, or inspection
never counts as human PASS.

This workflow owns human product acceptance, not code review. It may write only
`human-acceptance.json` through the launcher-bound `accept` CLI subcommands and acceptance-owned rich
`workflow-state.md` fields through an `artifact prepare` / `artifact submit`
lease. It never authors the compact `workflow.json` phase lock; only
`specify-runtime workflow` may change it. Do not edit
production source, tests, requirements, planning/task artifacts, or
implementation lifecycle state; do not commit, push, deploy, or invoke a repair
workflow inline. Safe reversible local/sandbox runtime startup, readiness, and
isolated-fixture preparation are session operations, not authority to mutate
production or other workflow artifacts.

PASS requires zero uncovered required human obligations, structured human
passes for every required scenario against a ready Review-approved
`runtime_targets` record bound to the approved reviewed snapshot, zero open
findings, and a separately confirmed final human decision.
Accept does not diagnose. Every failed observation first goes to the Review Leader
through `$spx-review`; this includes apparent requirement gaps,
unknown mechanisms, clear defects, omissions, regressions, and large repairs.
Review creates a new cycle, owns diagnosis, dispatches a read-only diagnostic
packet when the mechanism is unknown, then owns an independent Fix, independent
revalidation, and any later handoff for a proven upstream truth gap. Preserve
the failed scenario as the first return point, but after any repair invalidate
every human result and rerun the full frozen universe; preserve no prior PASS.
A separately stated new-scope request belongs to a later feature workflow and
must not bypass or rewrite the failed acceptance route. Human-owned
environment, permission, protected-system, or physical-device blockers receive
the full Human Action Guide.

After the human explicitly accepts all required scenarios, set the durable state
to `accepted`, run
`{{specify-subcmd:specify-runtime accept closeout --feature-dir <feature-dir> --format json}}`,
then execute that successful response's `next_argv` verbatim; it is the
revision-bound workflow-runtime closeout command, so do not reconstruct it,
and report what they personally verified, residual risk, the state path, and the
next integration or delivery command. Recommend that command; do not invoke it
in this acceptance invocation.
