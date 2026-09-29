event-sequence testing together. Unknown expected behavior is an oracle gap.
Pairwise factors do not discover missing conditions or establish event order.

Enumerate actual classes, boundary values (including unit and rule), decision
rows, transitions and risky compound cases as operation
`conditions: [{id, dimension, description, source_refs}]`. New books include
all discovered conditions; optional fields preserve legacy v1 readability, not
a completeness exemption. Bind each condition to a concrete scenario witness
with `condition_checks: [{condition, step_id, oracle_id}]`. Distinct conditions
in one dimension need distinct witness steps, so one input cannot cover L-1,
L and L+1. Prefer separate cases when outcomes differ. `check` exposes missing
conditions behind broad dimension tags; `audit` reports passing condition and
timing witnesses separately. Model discovery and oracle quality still need audit.

```text
python .specify/scripts/shared/e2e_scenarios.py catalog
A screenshot is not proof of durable files/server state: use independent
filesystem/API/CLI/database readback for side effects. Logs can support an action
or checkpoint, but a success log alone is not an independent effect oracle.
Missing oracles remain blocked even when the screen appears correct.

Keep expected and actual observations separate. Preserve each attempt; failed
pending-human-review. No absolute completeness, release safety or acceptance
claim. Formal delivery remains tasks -> implement -> review -> accept.

## Scoped mutation closeout

Only actual scoped test-asset changes trigger mutation closeout. Observation
alone never authorizes product writes or requires an invented source mutation.
`specify e2e` only prints native-entrypoint guidance; it does not execute tests.
For changed assets, use canonical `sp-e2e` in the shared cognition runtime:

```text
{{specify-subcmd:specify-runtime cognition closeout-plan --workflow sp-e2e --scope-dir <feature-or-scope> --scope-mode explicit --format json}}
```

Append one `--changed-path` per workflow-owned path (both rename endpoints);
exclude unrelated dirty files. Pass the existing `--delta-session` when present.
Read `references/project-cognition.md` for the shared closeout/recovery contract.
Fill only requested agent fields from actual evidence, preserve planner-owned
scope/identity, and execute its exact `apply_argv`. Inline payloads go to stdin
with `--payload-json -`, not an invented argv or hand-written runtime file.
Structured verification uses exact `passed|failed|recorded`; failed, stale or
unexecuted tests never become `passed` to satisfy closeout.

Shared apply owns validation, eligible finalization and the durable receipt;
never sequence update/validate/finalize yourself. Inspect `scope_result_state`,
`result_state`, receipt and global debt separately. Report partial/blocked
closeout and run its exact recovery action. A persisted intent uses guarded
inspect/repair/replay, never direct state edits or a mark-dirty bypass. Only when
no trustworthy intent can exist use the documented dirty fallback with reason.
Do not claim clean mutation completion or close Work before supported receipt
verification succeeds; observation/execution results remain separate claims.

At a blocked exit retain stage, category, owner, exact cause, sanitized evidence,
attempted recovery, affected IDs, next action, observable unblock criteria and
