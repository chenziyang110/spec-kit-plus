# Workflow runtime

Read this reference only for the feature-bearing
`$spx-specify -> $spx-plan -> $spx-tasks -> $spx-implement -> $spx-review -> $spx-accept`
chain. A pre-feature
discussion keeps its own discussion session; once `FEATURE_DIR` exists, the
runtime is authoritative for required phase order in the compact
`FEATURE_DIR/workflow-runtime.json` file.

Do not compose or advance `workflow-runtime.json` manually. `workflow-state.md`
remains the rich workflow-owned evidence and resume surface for Learning,
clarification, research, analysis, and profile-specific details; the phase
runtime must not overwrite or treat it as revision authority. After resolving
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

`completed` closes the current stage, not the whole chain. A completed
non-terminal stage still exposes and permits its one required next transition;
only completed `accept` is terminal. Review owns bounded source/test repair and
must revalidate the current fingerprint before completion. A failed or blocked
acceptance must not reverse `workflow transition` or edit phase state. Route its
recorded finding through `accept route-repair`; that command invalidates the
prior verdict and performs the only legal backward repair handoff to Review.
The Review Leader diagnoses the observation and owns an independent Fix and
revalidation cycle. Only Review may later reopen an upstream truth owner, and
only after evidence proves that correct implementation is impossible under the
current requirement, design, or architecture truth.

At the owning stage's closeout, run
`{{specify-subcmd:workflow complete-stage --feature-dir <feature-dir> --expected-revision <revision> --format json}}`.
It validates artifacts, records non-terminal `status: completed`, and returns
the one legal transition argv. Do not edit phase state manually. The destination
skill owns that transition; recommend it without entering it. Use
`{{specify-subcmd:workflow next --feature-dir <feature-dir> --format json}}`

If fresh evidence invalidates an earlier required stage, do not delete stale
artifacts or hand-edit either state surface. Reopen the highest invalid stage
through
`{{specify-subcmd:workflow reopen --to <specify|plan|tasks|implement|review> --feature-dir <feature-dir> --expected-revision <revision> --reason <compact-reason> --evidence <sanitized-evidence> --invalidated-artifacts <artifact> --format json}}`,
repeating evidence and invalidated-artifact flags as needed. Generic reopen is a
strict backward move or reactivation of the same completed non-accept stage,
including `implement` and `review`; an active same-stage owner simply continues. Resolve
an existing blocker with fresh evidence first. Failed acceptance uses
`accept route-repair`; a completed acceptance is immutable and new scope starts
a distinct feature workflow.

After safe agent recovery is exhausted, obtain the stable input contract with
`{{specify-subcmd:api schema workflow-block-input --format json}}`, then persist
the detailed blocker through
`{{specify-subcmd:workflow block --input <blocker-json-or-> --format json}}`.
Honor its owner, exact recovery, novice human guide when required, evidence to
return, and resume point. A bare error or generic request for human help is not
a valid blocked exit. The runtime rejects replacement of an unresolved blocker,
returns a read-only `show_argv` plus structured `data.resolution_action`, and
keeps `next_argv` empty until evidence exists. Once the criteria are proven,
append each evidence item through the action's declared `--resolution-evidence`
input and execute its `base_argv`; do not reconstruct other flags. This invokes
`workflow resolve`, preserves the prior blocker audit, and reactivates the same
stage.

Review completion is bound to its fresh approved state and final source
fingerprint; any later covered source/configuration change makes Review and
prepared acceptance stale. Only `accept` closes the chain. After explicit human acceptance, run the
acceptance-owned `accept closeout` command and execute its successful response's
`next_argv` verbatim. That revision-bound argv invokes `workflow closeout`; do
not reconstruct it. The runtime validates and snapshots acceptance evidence
before marking the workflow complete.
