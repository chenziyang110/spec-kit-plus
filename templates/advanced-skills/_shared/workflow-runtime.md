# Workflow runtime

Read this reference only for the feature-bearing
`$spx-specify -> $spx-plan -> $spx-tasks -> $spx-implement -> $spx-accept`
chain. A pre-feature
discussion keeps its own discussion session; once `FEATURE_DIR` exists, the
runtime is authoritative for phase order and resume state.

Do not compose or advance `workflow-state.md` manually. After resolving
`FEATURE_DIR`, run
`{{specify-subcmd:workflow show --feature-dir <feature-dir> --format json}}`.
If state is missing at the first feature stage, enter with
`{{specify-subcmd:workflow enter --command specify --feature-dir <feature-dir> --format json}}`.
When entering any later required stage, run
`{{specify-subcmd:workflow transition --to <this-stage> --feature-dir <feature-dir> --expected-revision <revision> --format json}}`
before writing its artifacts. This transition validates the completed
source-stage artifacts, allows exactly one forward step, and returns exit `10`
without mutation for an incomplete handoff, skipped stage, blocker, or stale
revision.

The destination skill owns the transition. At closeout, recommend the next
skill without entering it. Use
`{{specify-subcmd:workflow next --feature-dir <feature-dir> --format json}}`
and execute only structured `next_argv` when that next skill is separately
invoked.

After safe agent recovery is exhausted, obtain the stable input contract with
`{{specify-subcmd:api schema workflow-block-input --format json}}`, then persist
the detailed blocker through
`{{specify-subcmd:workflow block --input <blocker-json-or-> --format json}}`.
Honor its owner, exact recovery, novice human guide when required, evidence to
return, and resume argv. A bare error or generic request for human help is not a
valid blocked exit.

Only `accept` closes the chain. After explicit human acceptance and the
acceptance-owned closeout succeed, run
`{{specify-subcmd:workflow closeout --feature-dir <feature-dir> --expected-revision <revision> --format json}}`;
it validates acceptance artifacts before marking the workflow complete.
