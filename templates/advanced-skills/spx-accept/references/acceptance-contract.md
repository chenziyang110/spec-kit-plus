# Human acceptance contract

`human-acceptance.json` is the canonical resumable state. Start from the
installed `.specify/templates/human-acceptance-state-template.json`; its schema
is authoritative. Stable fields belong to the template/runtime, not prose
reconstruction.

## Readiness and freshness

Acceptance starts only after successful system Review closeout produced a fresh
`review-state.json` with `status: approved`, a final reviewed source fingerprint,
and a trusted `implementation-summary.md`. `accept prepare` records the Review
digest, summary digest, and reviewed evidence snapshot while excluding
acceptance-owned state. If the Review verdict is no longer approved or any
recorded digest/fingerprint differs, status is `stale` and no prior verdict can
close acceptance. Return to `$spx-review`; only that owner may revalidate the
product and refresh the acceptance handoff.

Use CLI-owned `workflow-runtime.json` as the required phase lock. Use rich
`workflow-state.md` only for acceptance-owned resume and evidence state:

- `active_command: sp-accept`
- `phase_mode: acceptance-only`
- allowed writes: `human-acceptance.json` and acceptance-owned workflow state
- forbidden writes: source, tests, requirements, plan/tasks, implementation or
  Review records, external systems
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

Cover every required user-visible acceptance outcome with the smallest ordered
set. A scenario states user value, required/optional status, and starting state.
Every step contains:

- exact action or click path, with placeholders explained;
- visible expected result;
- safe failure branch and evidence to collect;
- a tiny `response_prompt` that a contextless human can answer;
- durable result, observed result, and sanitized evidence.

Prefer real user journeys over test-by-test or file-by-file checks. Do not ask
the human to run a broad automated test suite unless operating that tool is the
actual product behavior being accepted.

## Conversation controller

Show a compact orientation once, then only the current step. Wait for the
human, interpret their natural reply, persist it, and advance. The human may
answer “看到了”, “没看到”, PASS/FAIL, attach a screenshot, or paste a short
sanitized error; the agent owns mapping that reply into state.

Do not dump the whole checklist as homework. If the human explicitly requests a
printable checklist, it is a view over the same state; guided progress and
verdict rules remain unchanged.

## Verdicts and routes

- `accepted`: every required scenario has explicit human `pass` and overall is
  `pass`.
- `rejected`: a required observation failed; create a finding with expected,
  observed, evidence, and route.
- `blocked`: a required observation cannot currently run; preserve the cursor.
- automated verification, agent inspection, or no response never equals human
  acceptance.

Routes are handoff-and-stop:

- every product/runtime defect, including unknown mechanisms and regressions:
  `spx-review`; its Leader dispatches a read-only diagnostic packet when the
  root cause is unknown, then owns the Fix and independent revalidation waves;
- existing requirement gap or contradiction: `spx-clarify`;
- genuinely new scope: `spx-specify`;
- human-only access/authority: retain `spx-accept` with a Human Action Guide.

For every non-human repair route, first run
`{{specify-subcmd:accept route-repair --feature-dir <feature-dir> --finding-id <finding-id> --route <recorded-route> --expected-revision <revision> --evidence <sanitized-evidence> --format json}}`.
The runtime invalidates the prior verdict, preserves the failed scenario as the
cursor, and reopens `review` for product/runtime defects or `specify` for
clarify/specify routes. Invoke `repair_handoff_command` separately and stop.
Clarify must not write CLI-owned `workflow-runtime.json`; it may update the
feature's rich `workflow-state.md` specification resume/evidence sections.
Review remains the stage owner for missing code, large approved-scope omissions,
and unknown root causes; only a proven requirement, design, or architecture
truth gap may leave Review for its upstream owner. The
owning required stage reads the reopened CLI state, completes it through
`workflow complete-stage`, and progresses every required stage in order. Only
after the runtime re-enters active `accept` execute
`acceptance_return_argv` to rebuild/freshness-check the guide and resume the
preserved failed scenario. Reuse prior passes only after fresh evidence proves
their implementation dependencies did not change.

After `accept closeout` succeeds and its exact `next_argv` commits terminal
workflow closeout, the acceptance state, immutable terminal snapshot, and
completed runtime are read-only. Changed implementation scope starts a new
feature workflow; never rewrite the terminal verdict to draft or stale.
