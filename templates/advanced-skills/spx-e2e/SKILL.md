event-sequence testing together. Unknown expected behavior is an oracle gap.
Pairwise factors do not discover missing conditions or establish event order.

```text
python .specify/scripts/shared/e2e_scenarios.py catalog
A screenshot is not proof of durable files/server state: use independent
filesystem/API/CLI/database/log readback for side effects. Missing oracles remain
blocked even when the screen appears correct.

Keep expected and actual observations separate. Preserve each attempt; failed
pending-human-review. No absolute completeness, release safety or acceptance
claim. Formal delivery remains tasks -> implement -> review -> accept.

At a blocked exit retain stage, category, owner, exact cause, sanitized evidence,
attempted recovery, affected IDs, next action, observable unblock criteria and
