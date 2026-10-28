# Implementation worker contract

Delegate a bounded task with stable inputs. Prefer isolated writes for
parallel waves; when consecutive ready tasks share write scope, keep them
serial `one-subagent` (resume or re-dispatch)—do not treat that as automatic
leader-direct. The leader retains task graph, join, task acceptance,
task-level review, and final implementation verification ownership. The later
system Review remains an independent workflow.

The hashed packet pins product scope and separate runtime-derived
`bookkeeping_write_scope`; product `write_scope` and `ui_contract` stay unchanged.
Guard execution announce's full returned `planned_write_scope` union, never only
the product paths. Bookkeeping paths remain CLI-owned and never hand-edited.
Shared feature metadata overlap requires serialized ownership; do not drop
those paths, use a wildcard, or add a broad `.specify` audit exemption to force
parallel dispatch.

Exact feature `workflow.json` is part of compiler-owned bookkeeping so official
`specify-runtime workflow` mutations retain their own audit without becoming
worker product drift; it belongs exclusively to that runtime owner and remains
outside Leader/worker content and product `--scope-amendments-json` input.
Announce binds the exact workflow state and latest mutation receipt when
present. Completion accepts a changed state only when it is active Implement
and matches a newer runtime mutation receipt, then reports the path and receipt
digest. Valid-shaped hand edits, malformed state, and unresolved blockers
remain agent-owned until official resolution resumes the same Activity. The
completion transaction rechecks both exact digests while holding the workflow
mutation lock before authority release; drift keeps the same Activity active.
The feature-local `.workflow.lock` and workflow-mutation receipt storage are
private transport, not packet scope.

Product `write_scope` accepts only exact future files, exact directories, or
bounded subtrees ending with `/**`. Filename globs such as `*_test.go`, `?`,
`[]`, `/*`, or middle `**` are invalid. If the task will create or modify
companion tests, migrations, fixtures, generated files, or other companion
artifacts, those future writes must already be declared in `expected_write_scope`.
Validation commands and `pytest tests/...` references are evidence only and do
not grant write authority. When the exact future filename is unknown, Tasks
must use the narrowest containing directory or bounded subtree ending with
`/**`.
If one causal companion path is discovered after dispatch, stop before that
write when possible and return it to the Leader. The Leader keeps recovery in
the same invocation by refreshing overview and rerunning the existing
`execution guard` with the complete union plus `--scope-amendments-json`.
Runtime preserves the original packet, marks late discovery from Git delta,
and requires an independent passing `scope-drift-review`; `work scope-add`
cannot bypass this route.

Provide the worker:

- full task outcome and authoritative contract refs;
- allowed read/write paths and forbidden paths;
- dependencies, must-preserve and consequence obligations;
- acceptance, accepted change-set RED/baseline gate-attempt ref or
  test-authoring-only status, cheap task checks, deferred logical gates, and
  required real-entrypoint coverage;
- exact structured result destination or return shape.

If Test Design applies, provide only the verified task packet subset:
`test_case_refs`, `test_data_refs`, and its runtime-owned binding. The worker
uses those canonical refs read-only as task-local oracle and material inputs.
It must not read a global Test Design projection, merge refs from a
noncanonical Markdown task projection, or edit canonical Test Design cases,
data, coverage, gaps, audit, publication,
projection, or handoff. A missing or conflicting ref returns a blocked result.

For a UI-bearing task, the packet carries `ui_contract`, original visual
references with use intent, approved visual ref, real content/image plans,
required states, and the integrated evidence triad. Return changed surfaces,
state/viewport requirements, and visual risks; do not run the full viewport/state
capture loop per Txx. The Leader records canonical `structure_snapshot`,
`visual_capture`, and `runtime_diagnostics` with `evidence_scope: integrated`
during a Leader-owned validation attempt. Before dispatch, the leader ensures the worker can
read the installed skill-local `references/ui-quality-gate.md` and names it in
the dispatch context; the worker may not replace inspectable sources with a
prose summary.

Require a result containing status, changed paths, cheap task checks, test
impact, consumer or UI coverage notes when triggered, blockers, failed
assumptions, and recovery guidance. Workers must not run a test suite, full
build, service startup, E2E journey, or browser capture per Txx, and they cannot
open a logical gate or validation attempt.
A `success` result is acceptance-ready: every canonical `task_checks` entry is
present exactly as a passed validation command, every validation row passes,
and blockers are empty. Put known downstream work in a separate task, approved
deferral, or blocked result; never represent it as failed validation inside a
current-task `success`.
Required field name is `validation_results` (array of `{command, status:
"passed"|"failed"|"skipped", summary?}`), not `validation`. Worker `status` is
`success|blocked|failed` (`DONE` is not accepted). Expand the schema with
`specify-runtime api schema implement-result-merge-input --format json`.
`evidence register` does not replace `validation_results`.
The worker returns this bounded object to the leader or submits it inline through
the runtime-managed result channel. The leader merges it with
`{{specify-subcmd:specify-runtime implement result-merge --feature-dir <feature-dir> --task-id <task-id> --result-json <inline-json|@path|-> --format json}}`;
neither party writes a canonical or temporary result
file under `worker-results/` directly.
Include the packet's `cognition_delta_contract` in the handoff obligations.
Before compilation/dispatch, require
`{{specify-subcmd:specify-runtime api ensure --capabilities cognition.worker-delta.v1 --format json}}`;
repair or upgrade a missing capability before source-changing work.
The result's `cognition_delta` uses `schema: "spec-kit-cognition-delta-v1"`,
`version: 1`, and reported `identity`. Include every retained `changed_paths`
from success, blocked, failed, or rejected attempts; `path_changes` records
add/modify/delete/rename, with both rename endpoints in that denominator.
Preserve behavior, owner/consumer/interface, generated chain, state contract,
verification/evidence, invalidated claim, unknown, confidence and recovery
facets as nested JSON candidates. The runtime retains each submission and
binds acceptance to its exact result; workers cannot supply
`submission_history` or `cognition_result_binding`. Conflicting legacy aliases
are refused. At the join, the leader's native closeout planner reads stored
results and histories; unaccepted semantics remain candidates while retained
edits remain in invalidation accounting. Shared-claim or path conflicts must
be resolved explicitly, never overwritten with the last worker summary.
Cheap producer-to-consumer wiring evidence remains task-local when a consumer
surface is named. Defer only runtime real-entrypoint proof to the Leader attempt;
do not defer the static "created but not wired" check.
Validate packet/result with the installed hook helpers when available. Do not
accept idle execution, an unwritten handoff, or synthetic-only proof for a
real-entrypoint requirement.

The leader must not edit an active worker write scope. After the join, inspect
the integrated diff and collect the task's gates into one change-set validation
attempt. The ledger has three logical gates shared across Implement and Review;
physical retries remain attempts inside the owning gate and workers never open
them.
Prefer targeted
edits that preserve approved working structure; do not replace whole UI files
when a bounded change can converge safely. A worker may report
concerns; it may not redefine confirmed product scope or declare the whole
feature complete.
