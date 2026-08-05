## Project Learning

The CLI is the only agent-facing Learning read surface:

1. Run `{{specify-subcmd:specify-runtime learning start --command <classic-command-name> --format json}}` before deeper non-trivial work.
2. Select summaries by applicability and triggers; use `{{specify-subcmd:specify-runtime learning list --command <classic-command-name> --format json}}` only to filter or page.
3. Execute one matching card's `show_argv`. Do not parse Learning storage.

After minimal live inspection identifies a reused operation or changed entry point, rerun targeted recall with current code, tests, and task/contract evidence, for example `{{specify-subcmd:specify-runtime learning list --command <classic-command-name> --context operation_owner=<owner> --context consumer_owner=<consumer> --context outcome=<result-family> --format json}}`. Do not derive these facets from archived specifications. An exact operation-owner match may surface a cross-command candidate even when the new consumer differs; treat it as a candidate, expand one `show_argv`, verify it against live evidence, and do not auto-apply it.

When the entrypoint outcome audit is triggered, persist the live facets as `learning_context`, the contextual invocation as `learning_search_refs`, and returned refs as `learning_candidate_refs`. Record exactly one `applied`, `not_applicable`, or `deferred` item in `learning_dispositions` for every candidate. Do not silently ignore a candidate: applied Learning traces to requirement/consequence refs, not-applicable needs current evidence, and deferred needs an explicit deferral ref.

`start`, `list`, and `show` are read-only. Current repository evidence,
`.specify/memory/constitution.md`, and explicit user direction override stale or
candidate Learning.

At closeout, corrections, retries, route changes, recovery, false leads, hidden
dependencies, validation/tooling/state/cognition gaps, constraints, and near
misses are capture signals. Prefer `{{specify-subcmd:specify-runtime learning capture-auto}}`
from owning state; manual capture includes summary, problem, action, triggers,
success criteria, avoid items, exceptions, and evidence.

Summary, trigger_signals, and evidence are sanitized agent-facing projections, not raw incident logs.
trigger_signals are canonical tags for new records; legacy free-form trigger text may appear only for read compatibility.
Raw sensitive values must not enter Learning storage, registry, or read API
payloads. Keep only a safe project-relative reference or digest, and abstract
sensitive but reusable lessons instead of dropping them. Canonical
`redaction_labels` are `credential`, `email`, `private_key`, `machine_path`,
`personal_identifier`, `business_identifier`, and `organization_sensitive`;
use `[REDACTED_PHONE]`, `[REDACTED_BUSINESS_ID]`, and `[REDACTED_ORG_TERM]`
beside the existing canonical replacements.

Learning value and sensitivity are independent axes. Optional `assessment`
contains `learning_value`, `content_safety`, `decision`, and
`decision_reason`. Capture reusable safe/sanitized lessons as `capture-safe` or
`capture-sanitized`; defer high-value evidence only when sanitization removes
all reusable meaning. `ignore` is only for low-value routine/non-reusable
signals with an explicit reason. Sensitivity alone is never an eligibility
veto. Abstract and retain the reusable lesson; never discard it merely because
its source evidence was sensitive.
At `learning start`, use mature Learning protection plus a bounded candidate slot:
reserve up to 5 candidate cards beside a 15-card stable quota, and let
either class fill unused capacity. The bound controls disclosure, not storage;
capture every reusable candidate, merge duplicates by recurrence key, and
record an explicit no-learning decision when the signal is not reusable.
Rank candidate disclosure by context, value, recurrence, and novelty, and
diversify repeated type/source/recurrence families when enough candidates exist.

`learning capture-auto ... --dry-run --format json` returns only the sanitized
assessment and writes no candidate, registry, review state, or metric. Optional
`.specify/config.json.project_learning` policy accepts literal
`secret_prefixes`, `sensitive_key_names`, `business_id_prefixes`,
`sensitive_terms`, and `deferred_review_days`; arbitrary regex is forbidden.
Detector lists allow at most 64 distinct 1..128-character literals and review
days 1..365. Invalid policy warns on safe built-in reads and fails Learning writes closed.
The fixed warning is `project_learning_policy_invalid:using_builtin_policy`;
mutation or assessment commands, including dry-run, fail closed.

At closeout use `learning review --command <workflow> --decision
none|captured|auto-captured|deferred|manual-capture-needed [--rationale <text>]
[--recurrence-key <key>]`;
`deferred` and `manual-capture-needed` require rationale and remain pending until matched by a
durable candidate, confirmed learning, or project rule. Captured decisions
succeed only after that match is verified, and `none` is blocked while a
matching deferred/manual decision remains pending. `learning status [--command <workflow>]` and `learning metrics
[--command <workflow>]` are read-only compact status/aggregate-count surfaces.
Status returns only pending/due/age buckets; it omits rationale, Learning refs,
recurrence keys, and timestamps.
Metrics reports canonical totals, decisions, value/risk tiers, reason/label
counts, and derived confirmation rate. Its age buckets come from review state
in memory and are not persisted.
They expose no evidence text or Learning refs and do not mutate age or metrics.

- `fast`: skip unless the task escalates.
- `accept`, `analyze`, `ask`, `auto`, `constitution`, `explain`,
  `implement-teams`, `taskstoissues`, and `team`: consume-only; do not violate
  their write boundaries to capture.
- Other non-trivial workflows: consume before deeper work; capture reusable
  signals at closeout or record a no-learning decision.

The `policy` returned by the CLI is authoritative when prompt wording drifts.
Reading never promotes. A candidate cannot become a rule directly; it must become confirmed learning before explicit project-rule promotion.
