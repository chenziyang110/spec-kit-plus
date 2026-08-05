---
name: spec-kit-project-learning
description: Consume and produce reusable project Learning through the Specify CLI. Use at the start and closeout of every non-trivial SP workflow, and whenever user correction, repeated attempts, route changes, blockers, false leads, hidden dependencies, validation failures, tooling traps, or reusable project constraints appear.
---

# Spec Kit Project Learning

Use the Learning CLI as the only agent-facing read surface. Do not parse
`.specify/memory/learnings/INDEX.md`, detail Markdown, compatibility summaries,
or `.planning/learnings/**` directly during normal workflow execution.

## Consume With Progressive Disclosure

1. Run `{{specify-subcmd:specify-runtime learning start --command <classic-command-name> --format json}}`.
2. Use the returned compact cards to identify matching trigger signals.
3. If more summaries are needed, run `{{specify-subcmd:specify-runtime learning list --command <classic-command-name> --format json}}`. Use `--query`, `--type`, `--status`, `--cursor`, or `--all` only when needed.
4. Run the selected card's `show_argv` for one Learning at a time. Do not expand every detail.
5. Apply guidance only when its applicability and trigger signals match live evidence. Current repository evidence overrides stale Learning.

After minimal live inspection identifies a reused operation or changed entry
point, run a contextual second pass from current code, tests, and task/contract
evidence:

```text
{{specify-subcmd:specify-runtime learning list --command <classic-command-name> --context operation_owner=<owner> --context consumer_owner=<consumer> --context outcome=<result-family> --format json}}
```

Do not derive context facets from archived specifications. Exact operation
owner matches may recall cross-command candidates even when the new consumer
differs. Expand one selected match, validate it against live evidence, and do not auto-apply it.

When the entrypoint outcome audit is triggered, persist `learning_context`,
`learning_search_refs`, and all returned `learning_candidate_refs` in its one
spec contract. Give every candidate one `applied`, `not_applicable`, or
`deferred` item in `learning_dispositions`; do not silently ignore it. Applied
Learning traces to requirement/consequence refs, not-applicable needs current
evidence, and deferred needs an explicit deferral ref.

Command shape: `{{specify-subcmd:specify-runtime learning list --command <command> --format json}}`
and then `{{specify-subcmd:specify-runtime learning show --ref <ref> --format json}}`.

SPX names map to the same Classic namespace: `spx-implement` consumes
`--command implement`; `spx-research` consumes `--command deep-research`.

`start`, `list`, and `show` are read-only. They must not capture, merge, confirm,
promote, update age, or increment metrics.

## Produce Learning

Prefer deterministic capture from durable workflow state:

```text
{{specify-subcmd:specify-runtime learning capture-auto --command <command> <state locator> --format json}}
```

To inspect a prospective decision without writing any candidate, registry,
review state, or metric, add `--dry-run`. Its output is already sanitized; do
not recreate an unsanitized explanation outside the runtime.

Use manual capture only when durable state cannot express the lesson. Supply a
small agent-oriented record:

Required options: `--command`, `--type`, `--summary`, and `--evidence`.

- `--summary`: one-line identity
- `--problem`: failure mode or situation
- `--action`: imperative future action
- `--trigger`: observable activation signal; repeat as needed
- `--success`: observable proof the action worked; repeat as needed
- `--avoid`: tempting but harmful action; repeat as needed
- `--exception`: boundary where the guidance should not apply
- `--evidence`: concrete observation or stable reference
- `--type`, `--command`, and optionally `--recurrence-key`

The CLI derives safe defaults for omitted guidance fields, merges by recurrence
key, updates the compact index/detail projection, and preserves provenance.

Summary, trigger_signals, and evidence are sanitized agent-facing projections, not raw incident logs.
trigger_signals are canonical tags for new records; legacy free-form trigger text may appear only for read compatibility.
Raw sensitive values must not enter Learning storage, registry, or read API
payloads. Keep only a safe project-relative reference or digest, and abstract
sensitive but reusable lessons instead of dropping them. Canonical labels and
replacements are:

- `credential`, `email`, `private_key`, `machine_path`:
  `[REDACTED_SECRET]`, `[REDACTED_EMAIL]`, `[REDACTED_PRIVATE_KEY]`,
  `<USER_HOME>/...`
- `personal_identifier`, `business_identifier`, `organization_sensitive`:
  `[REDACTED_PHONE]`, `[REDACTED_BUSINESS_ID]`, `[REDACTED_ORG_TERM]`

Treat learning value and content sensitivity as independent axes. Optional
`assessment` contains:

- `learning_value`: `tier=high|medium|low` plus canonical `reason_codes`
- `content_safety`: `sensitivity=safe|sanitized`,
  `risk_tier=none|moderate|high`, and `redaction_labels`
- `decision=capture-safe|capture-sanitized|defer|ignore` and a sanitized
  `decision_reason`

Capture reusable safe or sanitized lessons. Defer high-value evidence only
when sanitization removes all reusable meaning. Ignore only a low-value
routine/non-reusable signal with an explicit reason; sensitivity alone is never
an eligibility veto. Abstract and retain the reusable lesson; never discard it
merely because its source evidence was sensitive.

Use the smallest accurate machine type: `pitfall`, `recovery_path`,
`user_preference`, `project_constraint`, `workflow_gap`, `routing_mistake`,
`verification_gap`, `state_surface_gap`, `map_coverage_gap`, `tooling_trap`,
`false_lead_pattern`, `near_miss`, or `decision_debt`.

## Trigger Rules

When the workflow owns `workflow-state.md`, patch explicit semantic signals
under `## Learning Triggers` through leased `specify-runtime artifact patch --section`
as `kind: compact evidence`; `capture-auto` maps
the canonical kind to the appropriate Learning type and future action.

Capture or review a candidate when any of these occurs:

- the user corrects an assumption, default, route, or repeated behavior
- two or more attempts, retries, or hypothesis changes were needed
- a blocker required a non-obvious recovery path
- a false lead, rejected path, or decisive signal would save future work
- a hidden dependency or project constraint changed execution
- verification failed, was missing, or exposed a reusable gap
- environment/tooling behavior looked like a product defect
- workflow state failed to preserve information needed after resume
- cognition coverage omitted a truth-owning surface
- a near miss avoided a risky or destructive action

At `learning start`, use mature Learning protection plus a bounded candidate slot:
reserve up to 5 candidate cards beside a 15-card stable quota, and let
either class fill unused capacity. The bound controls disclosure, not storage;
capture every reusable candidate, merge duplicates by recurrence key, and
record an explicit no-learning decision when the signal is not reusable.
Rank candidate slots by context match, value, recurrence, and novelty. When the
catalog is large enough, diversify repeated learning type, source command, and
recurrence family instead of allowing one family to occupy all five slots.

Skip routine outcomes, raw command output, duplicates, vague speculation, and
facts that belong only to the current task.

## Workflow Policies

- `skip`: `fast`. Do not start or capture Learning unless the task escalates.
- `consume-only`: `accept`, `analyze`, `ask`, `auto`, `constitution`, `explain`,
  `implement-teams`, `taskstoissues`, and `team`. Read relevant Learning; defer
  capture to the workflow that owns an allowed durable write surface.
- `consume-capture`: all other non-trivial workflows. Consume before deeper
  work and run `capture-auto` at terminal closeout when durable state contains a
  reusable signal; otherwise make an explicit no-learning decision.

The `policy` returned by `learning start/list` is authoritative if this list and
the installed runtime differ.

Optional project detector policy lives at `.specify/config.json.project_learning`.
It accepts only literal `secret_prefixes`, `sensitive_key_names`,
`business_id_prefixes`, `sensitive_terms`, and `deferred_review_days`; arbitrary
regular expressions are forbidden. Each list allows at most 64 distinct
1..128-character literals and review days range from 1 to 365. Invalid policy
leaves reads protected by built-in detectors with warning
`project_learning_policy_invalid:using_builtin_policy`; mutation or assessment
commands, including dry-run, fail closed.

## Review And Aggregate Status

At terminal closeout record the runtime-owned decision:

```text
{{specify-subcmd:specify-runtime learning review --command <workflow> --decision none|captured|auto-captured|deferred|manual-capture-needed [--rationale <text>] [--recurrence-key <key>] --format json}}
```

`deferred` and `manual-capture-needed` require rationale and remain pending
until a matching durable candidate, confirmed learning, or project rule clears
them. `captured`/`auto-captured` succeeds only after that match is verified;
`none` is blocked while a matching deferred/manual decision remains pending. Inspect them with
`learning status [--command <workflow>] --format json`; it returns compact
pending/due/age buckets only, without evidence, rationale, Learning refs,
recurrence keys, or timestamps. Inspect aggregate
totals, decisions, value/risk tiers, reason/label counts, and derived
confirmation rate with `learning metrics [--command <workflow>] --format json`.
Age buckets are derived from review state in memory and are not persisted in
metrics storage. Both commands are read-only and must not update age or counters.

## Lifecycle

```text
workflow evidence
  -> candidate (capture / capture-auto)
  -> confirmed learning (explicit promote or confirmation)
  -> project rule (explicit promote after recurrence or stable governance value)
```

Reading never changes lifecycle state. A candidate becomes promotion-ready when
recurrence or signal strength justifies review; it is not silently promoted at
the start of an unrelated workflow.
A candidate cannot become a rule directly; it must become confirmed learning before explicit project-rule promotion.

## Agent Detail Contract

`learning list` returns compact cards: `ref`, `summary`, `action`, `type`,
`status`, `signal`, `occurrences`, `applies_to`, `trigger_signals`, and
`show_argv`, plus optional `assessment`.

`learning show` returns one full record grouped as:

- `guidance`: problem, action, avoid, success criteria, exceptions
- `applicability`: commands, trigger signals, scope
- `evidence`: observation, decisive signal, false starts, rejected paths, root-cause family
- `provenance`: source command, first/last seen, occurrences, source layer
- `lifecycle`: signal, pain score, injection targets, promotion hint
- `assessment`: independent learning value, content safety, and capture decision

Treat the CLI record as the consumption contract. Storage files are runtime
implementation details and compatibility projections.

## Guardrails

- Do not create Learning merely to prove the reflex ran.
- Do not expand every detail document at workflow start.
- Do not let candidate Learning override constitution, explicit user direction,
  or current repository evidence.
- Do not promote during a read command.
- Do not write Learning from a consume-only workflow whose write boundary
  forbids it; preserve the signal in its owning durable state and route capture.
