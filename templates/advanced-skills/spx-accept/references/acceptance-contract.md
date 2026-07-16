# Human acceptance contract

`human-acceptance.json` is the canonical resumable state. Start from the
installed `.specify/templates/human-acceptance-state-template.json`; its schema
is authoritative. Stable fields belong to the template/runtime, not prose
reconstruction.

## Readiness and freshness

Acceptance starts only after successful implementation closeout created a
trusted `implementation-summary.md`. `accept prepare` records the summary digest
and an implementation evidence snapshot covering current HEAD, tracked diff,
and untracked implementation files while excluding acceptance-owned state. If
the current snapshot differs from `prepared_from_sha256`, status is `stale` and
no prior verdict can close acceptance. Rebuild orientation/scenarios from
current evidence, update the summary and snapshot digests, and rerun validation.

Use `workflow-state.md` as phase state:

- `active_command: sp-accept`
- `phase_mode: acceptance-only`
- allowed writes: `human-acceptance.json` and acceptance-owned workflow state
- forbidden writes: source, tests, requirements, plan/tasks, implementation
  records, external systems
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

- clear implementation repair: `spx-implement`;
- unknown mechanism/regression: `spx-debug`;
- existing requirement gap or contradiction: `spx-clarify`;
- genuinely new scope: `spx-specify`;
- human-only access/authority: retain `spx-accept` with a Human Action Guide.

After repair, rerun `accept prepare`. Reuse passed scenarios only when their
implementation evidence and dependencies are unchanged; otherwise reset the
affected results and cursor.
