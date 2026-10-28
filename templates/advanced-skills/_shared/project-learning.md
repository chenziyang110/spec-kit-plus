# Project Learning

`spx-quick` and `spx-debug` apply their pre-intake context sufficiency gate
before this reference. When it passes and the user explicitly selects
context-direct, follow that branch's explicit discovery-skip policy and do not run Learning
intake, capture, or review. Insufficient evidence, a full-branch choice, or
scope expansion ends the exception and restores the policy below.

Use the Learning CLI as the only agent-facing read surface. Do not parse the
learning index, detail Markdown, compatibility summary, or runtime candidate
files directly during normal execution.

## Intake

Before relying on bound reuse, run
`{{specify-subcmd:specify-runtime api ensure --capabilities learning.applicability.v1 --format json}}`.
The versioned capability extends existing owners; no `learning applicability`
command exists. An old runtime must be repaired or the lesson deferred.
After minimal live reads identify the exact source directory, use
`{{specify-subcmd:specify-runtime learning start --command <classic-command-name> --context component=src/owner --context constraint_file=constraints.json --format json}}`.
Carry the same context through `list` and its selected `show_argv`; add
`--context counterevidence_file=tests/current-counterexample.txt` for a current
contradiction. Read `applicability.state`, `applicable`, `reason_codes` and detail
`checks`. `rejected` forbids reuse; `degraded`, missing legacy bindings or unknown
versions require deferral and current evidence. Only `applicable` can support
considering reuse after live verification of component, current source bytes and
constraints. Facet ranking, recurrence and graph freshness are not semantic proof.
Rejected candidates are excluded from promotion-ready notes; confirmation notes
retain rejection reasons. Explicit confirmation cannot repair changed sources.

For every non-trivial workflow, run:

```text
{{specify-subcmd:specify-runtime learning start --command <classic-command-name> --format json}}
```

SPX and Classic share one namespace: pass `implement` for `spx-implement` and
`deep-research` for `spx-deep-research`. Select by compact `summary`, `action`,
`applies_to`, and `trigger_signals`. Use `learning list` only to filter or page
more summaries. Execute one selected card's `show_argv` only when its triggers
match the active work. Live evidence overrides stale Learning.

Reuse this Learning intake and the current cognition context capsule once per
unchanged workflow intake. Preparatory capability checks, artifact queries,
script dry runs, and board operations do not by themselves restart intake.
Refresh only for changed request/scope, relevant source evidence, workflow
binding, Learning applicability, cognition freshness/generation, or a required
resume/recovery gate that invalidates the prior intake. Contextual recall for
a newly evidenced operation remains valid; do not repeat the same recall after
every command. Verification and mutation-closeout freshness gates remain intact.

After minimal live inspection identifies a reused operation or changed entry
point, rerun targeted recall from current code, tests, and task/contract
evidence:

```text
{{specify-subcmd:specify-runtime learning list --command <classic-command-name> --context operation_owner=<owner> --context consumer_owner=<consumer> --context outcome=<result-family> --format json}}
```

Do not derive context facets from archived specifications. An exact operation
owner can recall a cross-command candidate even when a new consumer differs.
Expand one match, verify it against live evidence, and do not auto-apply it.

When the entrypoint outcome audit is triggered, persist `learning_context`,
`learning_search_refs`, and all returned `learning_candidate_refs` in its one
spec contract. Give every candidate one `applied`, `not_applicable`, or
`deferred` item in `learning_dispositions`; do not silently ignore it. Applied
Learning traces to requirement/consequence refs, not-applicable needs current
evidence, and deferred needs an explicit deferral ref.

`start`, `list`, and `show` are read-only. Never capture or promote while
consuming.

## Trigger And Capture

In owned `workflow-state.md`, record explicit semantic signals under
`## Learning Triggers` as `kind: compact evidence`; `capture-auto` maps the kind
to a Learning type and future action.

Treat user corrections, repeated attempts, route changes, blockers, recovery
paths, false leads, decisive signals, hidden dependencies, validation gaps,
tooling traps, state loss, cognition gaps, reusable constraints, and near misses
as capture signals. Skip routine outcomes, raw output, duplicates, and vague
speculation.

Prefer `learning capture-auto` from the owning durable workflow state. Use
manual `learning capture` only when state cannot express the lesson; provide a
one-line summary plus problem, imperative action, trigger signals, success
criteria, avoid items, exceptions, and concrete evidence when known.

Bind a genuine reusable signal with `capture` or owning-state `capture-auto` flags
`--component src/owner --source-file src/owner/entry.go --constraint-file constraints.json --evidence-kind recovery`.
Evidence kinds are `failure|recovery|correction|constraint`; repeat source/constraint
flags, and preserve counterexamples with `--counterevidence-file`. Runtime-owned
hashes and sizes derive from current files, never caller hashes or Gold/scoring
answers. Do not fabricate business origins or capture ordinary success.
Use safe project-relative references, product sources inside the exact component;
reject redirected paths, private runtime storage and raw sensitive references.
Current facts stay Cognition, lessons Learning, methods the existing Playbook
owner. Preserve Do-before-Learning write locking; reads never acquire mutation
ownership or confirm/promote a lesson.

Summary, trigger_signals, and evidence are sanitized agent-facing projections, not raw incident logs.
trigger_signals are canonical tags for new records; legacy free-form trigger text may appear only for read compatibility.
Raw sensitive values must not enter Learning storage, registry, or read API
payloads. Keep only a safe project-relative reference or digest, and abstract
sensitive but reusable lessons instead of dropping them. Canonical
`redaction_labels` are `credential`, `email`, `private_key`, `machine_path`,
`personal_identifier`, `business_identifier`, and `organization_sensitive`;
their replacements include `[REDACTED_SECRET]`, `[REDACTED_EMAIL]`,
`[REDACTED_PRIVATE_KEY]`, `<USER_HOME>/...`, `[REDACTED_PHONE]`,
`[REDACTED_BUSINESS_ID]`, and `[REDACTED_ORG_TERM]`.

Assess learning value independently from sensitivity. Optional `assessment`
exposes `learning_value.tier/reason_codes`,
`content_safety.sensitivity/risk_tier/redaction_labels`, `decision`, and a
content-free `decision_reason`. Reusable safe lessons are `capture-safe`;
reusable sanitized lessons are `capture-sanitized`; high-value evidence that
loses all reusable meaning after sanitization is `defer`. Use `ignore` only for
low-value routine/non-reusable signals with an explicit reason. Sensitivity
alone is never an eligibility veto. Abstract and retain the reusable lesson;
never discard it merely because its source evidence was sensitive.

Policies:

- consume-only: fast, accept, analyze, ask, auto, constitution, explain,
  implement-teams, taskstoissues, and team. Preserve a signal in owning state;
  do not violate the workflow write boundary to capture it.
- all other non-trivial skills: consume before deeper work and run
  `capture-auto` at terminal closeout when durable state contains a reusable
  signal; otherwise record an explicit no-learning decision in normal closeout.

The runtime `policy` field wins if these prompts drift.

At `learning start`, use mature Learning protection plus a bounded candidate slot:
reserve up to 5 candidate cards beside a 15-card stable quota, and let
either class fill unused capacity. The bound controls disclosure, not storage;
capture every reusable candidate, merge duplicates by recurrence key, and
record an explicit no-learning decision when the signal is not reusable.
Rank candidate slots by context match, assessed value, recurrence, and novelty;
when enough candidates exist, diversify repeated type, source-command, and
recurrence families rather than allowing one family to consume every slot.

Use `learning capture-auto ... --dry-run --format json` to inspect the sanitized
assessment without changing candidates, registries, review state, or metrics.
Optional project policy lives at `.specify/config.json.project_learning` and
supports only literal `secret_prefixes`, `sensitive_key_names`,
`business_id_prefixes`, `sensitive_terms`, and `deferred_review_days`; never
invent a regex detector. Each detector list is limited to 64 distinct literals
of 1..128 characters, and review days to 1..365. Invalid policy keeps read
commands on built-in safety rules with warning
`project_learning_policy_invalid:using_builtin_policy`; mutation or assessment
commands, including dry-run, fail closed.

At terminal closeout, use `learning review --command <workflow> --decision
none|captured|auto-captured|deferred|manual-capture-needed [--rationale <text>]
[--recurrence-key <key>]`.
`deferred` and `manual-capture-needed` require rationale and remain pending
until a matching durable candidate, confirmed learning, or project rule clears
them. `captured`/`auto-captured` succeeds only after that match is verified;
`none` is blocked while a matching deferred/manual decision remains pending.
`learning status [--command
<workflow>]` and `learning metrics [--command <workflow>]` are read-only:
status returns only aggregate pending/due/age buckets and omits rationale,
Learning refs, recurrence keys, and timestamps, while metrics exposes aggregate
totals, decisions, value/risk tiers, reason/label counts, and derived
confirmation rate. Metrics derives age buckets from review state in memory and
never persists them. Neither may store or expose evidence text or Learning refs, nor
advance age or counters merely because it was read.

## Progressive Detail Contract

`learning list` returns compact cards with `ref`, `summary`, `action`, type,
status, signal, occurrences, applicability, triggers, and `show_argv`.
`learning show` expands exactly one record into guidance, applicability,
evidence, provenance, and lifecycle groups.

Capture creates or merges a candidate. Confirmation/promotion is explicit;
reading does not promote and must never silently promote. A candidate cannot become a rule directly; it must become confirmed learning before explicit project-rule promotion. Project-rule
promotion requires recurrence, explicit confirmation, or stable cross-workflow
governance value.
