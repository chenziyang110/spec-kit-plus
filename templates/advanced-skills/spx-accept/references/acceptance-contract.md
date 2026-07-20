# Human acceptance contract

`human-acceptance.json` is the canonical resumable state. Start from the
installed `.specify/templates/human-acceptance-state-template.json`; its schema
is authoritative. Stable fields belong to the template/runtime, not prose
reconstruction.

## Readiness and freshness

Acceptance starts only after successful system Review closeout produced a fresh
`review-state.json` with `status: approved`, a final reviewed source fingerprint,
and a trusted `implementation-summary.md`. The Review-to-Accept handoff contains
`human_acceptance_obligations`, `human_acceptance_scenarios`, non-empty
`reviewed_runtime_targets`, and their digest; it does not prefill human PASS.
`accept prepare` records the Review digest, summary digest, reviewed evidence
snapshot, target digest, and frozen obligation/scenario contracts while excluding acceptance-owned
session progress. If the Review verdict is no longer approved or any
recorded digest/fingerprint differs, status is `stale` and no prior verdict can
close acceptance. Return to `$spx-review`; only that owner may revalidate the
product and refresh the acceptance handoff.

Use CLI-owned `workflow-runtime.json` as the required phase lock. Use rich
`workflow-state.md` only for acceptance-owned resume and evidence state:

- `active_command: sp-accept`
- `phase_mode: acceptance-only`
- allowed writes: `human-acceptance.json` and acceptance-owned workflow state
- forbidden writes: source, tests, requirements, plan/tasks, implementation or
  Review records, production/protected external systems; safe reversible
  local/sandbox runtime and isolated-fixture preparation remains allowed
- current scenario/step, blocker, and exact next route

## Contextless-human orientation

Assume the human remembers nothing. Populate:

- `outcome`: what now exists;
- `why_it_matters`: the user problem/value;
- `user_visible_changes`: concrete observable behavior;
- `not_in_scope`: exclusions that prevent false expectations;
- `prerequisites`: accounts, data, app state, device, or local setup;
- `start_here`: one exact real entrypoint.

Use user-facing labels and ordinary language. Do not require knowledge of
branches, architecture, files, tests, specs, or previous chat.

## Scenario construction

Treat `human_acceptance_obligations` as the frozen Human Acceptance Universe.
It covers every new or changed requirement selected for human end-to-end
verification. Require zero uncovered required obligations, reject deletion,
required-to-optional downgrade, lost source refs, or missing mappings, and use
the supplied `human_acceptance_scenarios` rather than inventing a smaller set.
A scenario states requirement refs, user value, required/optional status,
official entrypoint, and starting state.
Every step contains:

- exact action or click path, with placeholders explained;
- visible expected result;
- safe failure branch and evidence to collect;
- a tiny `response_prompt` that a contextless human can answer;
- durable result, observed result, and sanitized evidence.

Prefer real user journeys over test-by-test or file-by-file checks. Do not ask
the human to run a broad automated test suite unless operating that tool is the
actual product behavior being accepted.

Do not repeat System Review. Reuse its startup, wiring, diagnostics, automated,
and broad regression proof. Human performs each frozen requirement journey from
the real entrypoint and reports the observation; Agent setup or inspection is
not acceptance evidence.

## Agent preparation and runtime identity

`accept prepare` copies each Review-approved `source`, `build`, `deployment`, or
`device` target into `runtime_targets` and binds scenarios by official
entrypoint. Identity, artifact, deployment, version, configuration, snapshot,
ready evidence, linked Review-scenario fields, `identity_evidence_ref`, and
`identity_evidence_sha256` are immutable and must match the Review target digest
exactly. Acceptance preserves both identity-evidence fields read-only and never
regenerates their JSON or byte digest. Before the first human action, safely start or
health-check that target, prepare or reset isolated acceptance data through
documented reversible paths, and open the exact starting location. Acceptance
may fill only `acceptance_status`, `acceptance_ready_evidence`, and
`agent_actions`. Do not use production data, deploy without authority, perform
irreversible external effects, or perform the human's acceptance actions.

## Conversation controller

Show a compact orientation once, then only the current step. Wait for the
human, interpret their natural reply, persist it as a structured confirmation
bound to the runtime-generated confirmation id, approved target, and reviewed
snapshot, and advance. The final decision uses its separate confirmation. The human may
answer “看到了”, “没看到”, PASS/FAIL, attach a screenshot, or paste a short
sanitized error; the agent owns mapping that reply into state.

Do not dump the whole checklist as homework. If the human explicitly requests a
printable checklist, it is a view over the same state; guided progress and
verdict rules remain unchanged.

## Verdicts and routes

- `accepted`: the Human Acceptance Universe has zero uncovered required
  obligations, every required scenario has structured human `pass` evidence
  against a ready Review-approved `runtime_targets` record bound to the
  approved reviewed snapshot, no finding is open, overall is `pass`, and the
  separate human decision confirmation says `accept`.
- `rejected`: a required observation failed; create a finding with expected,
  observed, evidence, and route.
- `blocked`: a required observation cannot currently run; preserve the cursor.
- automated verification, agent inspection, or no response never equals human
  acceptance.

Routes are handoff-and-stop. Accept does not diagnose. Every failed observation
first goes to the Review Leader through `spx-review`, including an apparent
requirement gap, unknown mechanism, clear defect, omission, regression, or large
repair. The Review Leader creates a new cycle and owns diagnosis, an independent
Fix, independent revalidation, and dispatches a read-only diagnostic packet when the mechanism is unknown; only
after proving a requirement, design, or architecture truth gap may the Leader
hand it to the upstream owner. Human-only access/authority remains in `spx-accept` with
a Human Action Guide. A separately stated new-scope request belongs to a later
feature workflow; it is not a repair route for a failed observation.

For every non-human failed observation, first run
`{{specify-subcmd:accept route-repair --feature-dir <feature-dir> --finding-id <finding-id> --route <review-route> --expected-revision <revision> --evidence <sanitized-evidence> --format json}}`.
The runtime invalidates the prior verdict and every human result, preserves the
failed scenario as the first retest cursor, and reopens `review`. Invoke `repair_handoff_command` separately and
stop. Review remains the stage owner for the acceptance finding; only a proven
requirement, design, or architecture truth gap may leave Review for its upstream
owner. The
owning required stage reads the reopened CLI state, completes it through
`workflow complete-stage`, and progresses every required stage in order. Only
after the runtime re-enters active `accept` execute
`acceptance_return_argv` to rebuild/freshness-check the guide, start at the
preserved failed cursor, and rerun the entire frozen Human Acceptance Universe.
Preserve no PASS from before the repair.

The CLI alone writes `repair_resume`, appends completed cycles to
`repair_history`, and marks Review-routed findings resolved after a fresh
matching Review. Never synthesize those records or edit a finding to
`resolved`; closeout requires an unbroken repair chain ending at the current
approved Review.

After `accept closeout` succeeds and its exact `next_argv` commits terminal
workflow closeout, the acceptance state, immutable terminal snapshot, and
completed runtime are read-only. Changed implementation scope starts a new
feature workflow; never rewrite the terminal verdict to draft or stale.
