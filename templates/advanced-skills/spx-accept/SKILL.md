---
name: spx-accept
description: Advanced post-implementation human acceptance workflow. Use after verified closeout to restore a contextless human's understanding, guide one real product step at a time, and persist an explicit pass, fail, or blocked verdict.
---

# SPX Accept

Read `references/project-learning.md` and apply its consume-only policy.
Read `references/workflow-runtime.md` and let its CLI own phase state.
Read `references/project-cognition.md`, using cognition intent `ask`. Read
`references/acceptance-contract.md` and `references/blocker-resolution.md`. Read
`references/ui-quality-gate.md` when any acceptance scenario is UI-bearing.

Resolve exactly one system-reviewed feature and require a trusted
`review-state.json` with fresh `approved` verdict, its final reviewed
fingerprint, and the Review-refreshed `implementation-summary.md`. If Review is
missing, blocked, stale, or not approved, hand off to `$spx-review` and stop;
do not bypass Review by routing directly to `$spx-implement`. Transition from the validated `review`
stage into `accept` through the workflow runtime. Only then run
`{{specify-subcmd:accept prepare --feature-dir <feature-dir> --format json}}`
to create or freshness-check `human-acceptance.json`.

Treat the human as returning later with no useful chat memory. Read the summary,
relevant acceptance truth, and real entrypoint evidence, then fill the installed
human-acceptance template/schema with a plain-language orientation and the
smallest complete set of user-value scenarios. Do not ask the human to inspect
source, diffs, test logs, specs, plans, or task state.

Validate the acceptance-owned rich resume/evidence state with
`{{specify-subcmd:hook validate-state --command accept --feature-dir
<feature-dir> --format json}}`. A changed Review digest, final source
fingerprint, or implementation-summary fingerprint makes the guide stale; hand
off to `$spx-review` to revalidate current product evidence before continuing.

Start with a compact context reset: what changed, why it matters, what the human
will verify, prerequisites, exact entrypoint, and exclusions. Then guide only
one current scenario step. Give an exact action, visible expected result, safe
failure branch, and a tiny reply request. Translate natural replies into durable
step results/evidence and advance the cursor yourself. On resume, continue from
that cursor without replaying passed steps.

This workflow owns human product acceptance, not code review. It may write only
`human-acceptance.json` and acceptance-owned workflow-state fields. Do not edit
production source, tests, requirements, planning/task artifacts, or
implementation lifecycle state; do not commit, push, deploy, or invoke a repair
workflow inline.

PASS requires explicit human passes for every required scenario. On a mismatch,
record expected versus observed behavior and evidence, then hand off and stop:
every product/runtime defect goes to `$spx-review`, including an unknown
mechanism that requires a Review-owned read-only diagnostic packet before its
Fix packet; changed or missing existing requirements go to `$spx-clarify`, and
new scope goes to `$spx-specify`. Preserve the failed scenario as the return
point. Human-owned
environment, permission, protected-system, or physical-device blockers receive
the full Human Action Guide.

After the human explicitly accepts all required scenarios, set the durable state
to `accepted`, run
`{{specify-subcmd:accept closeout --feature-dir <feature-dir> --format json}}`,
then execute that successful response's `next_argv` verbatim; it is the
revision-bound workflow-runtime closeout command, so do not reconstruct it,
and report what they personally verified, residual risk, the state path, and the
next integration or delivery command. Recommend that command; do not invoke it
in this acceptance invocation.
