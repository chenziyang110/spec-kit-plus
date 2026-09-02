---
description: Use when a project or feature needs an independent evidence-backed Test Universe, professional test cases, test-material requirements, coverage traceability, and typed pointer-only projections for downstream consumers.
workflow_contract:
  when_to_use: Use as an independent producer for a project or feature whenever test obligations, cases, materials, gaps, or consumer projections are needed; the default formal path may still invoke it after plan and before tasks.
  primary_objective: Freeze the evidence boundary, coordinate read-only discovery and independent audit lanes, and produce runtime-validated test-design planning artifacts without implementing or running tests.
  primary_outputs: 'Project mode writes `.specify/test-design/`; feature mode writes `<FEATURE_DIR>/test-design/`. The runtime owns `test-state.json`, `test-universe.json`, `test-catalog.json`, `test-data-manifest.json`, `coverage-matrix.json`, `test-gaps.json`, `lane-manifest.json`, accepted lane results, and the optional feature `handoff-to-tasks.json`.'
  default_handoff: Publish a validated package, build only requested typed consumer projections, and route to the selected consumer; in the default formal path, /sp.tasks follows the feature Tasks projection and compatibility handoff.
handoffs:
  - label: Create Tasks
    agent: sp.tasks
    prompt: Build the executable task graph from the verified Test Design Tasks projection, compatibility pointer handoff, and current plan.
    send: true
---

{{spec-kit-include: ../command-partials/test-design/shell.md}}

{{spec-kit-include: ../command-partials/common/senior-consequence-analysis-gate.md}}

[AGENT] For project-cognition-backed semantic intake, routing, audit, resume, or final-claim gates, read `references/semantic-work-contract.md`.

## Detailed References

Read [Reference index](references/INDEX.md) before applying the stable test-design and worker contracts.

- [test-design contract](references/test-design-contract.md)
- [worker contract](references/worker-contract.md)
- [semantic work contract](references/semantic-work-contract.md)

## Leader and Subagent Boundary

Use `execution_model: subagent-mandatory`, `execution_surface: native-subagents`,
and `dispatch_shape: one-subagent | parallel-subagents`. The Leader owns mode
selection, frozen scope, lane preparation, join points, contradiction
resolution, canonical synthesis, lane acceptance, completeness qualification,
validation, and handoff. It must not replace a substantive discovery or
independent-audit lane with unrecorded inline work.

Each worker receives only the self-contained, runtime-generated brief returned
for one leased lane. Workers are read-only over product, test, fixture,
configuration, workflow, and canonical test-design files. They submit proposals
through the runtime result channel; they never edit global artifacts, accept
their own attempt, synthesize the catalog, validate completeness, or create the
Tasks handoff. If one native worker cannot execute a substantive lane, yield it
and redispatch serially or to another independent worker in the same
invocation. Keep the orchestrator waiting on runtime state; do not ask the user
to repair, requeue, or re-invoke Test Design. If the platform exposes no
independent worker surface, preserve an agent-owned capability blocker and
exact lane resume action rather than weakening the evidence boundary.

## Independent Producer and Feature Workflow Boundary

- Test Design is an **independent producer**. Feature mode does not require a completed Plan or Plan completion. It may start from an explicitly selected feature boundary, current code/tests/configuration, live evidence, a specification, or an existing Plan. If a feature workflow exists, query it with `{{specify-subcmd:specify-runtime workflow show --feature-dir <feature-dir> --format json}}` only to bind current source refs and consumer context; Test Design must not transition, reopen, complete, or edit `FEATURE_DIR/workflow.json`.
- `project-baseline` is standalone and must not require or create a feature workflow.
- `incremental-update` and `audit` reuse an existing project or feature artifact root selected explicitly from current state. Never silently retarget an active feature or mix project and feature artifacts.
- When mode, root, included paths, exclusions, or risk dimensions are materially ambiguous, ask one concise confirmation before `init`.

## Runtime-Owned Flow

1. **Freeze scope from authoritative evidence.** Build the `init` input in memory with non-empty `query`, `source_refs`, `included_paths`, and `risk_dimensions`, plus explicit `excluded_paths`. Current code is final authority for implemented behavior; tests, configuration, official schemas/contracts, and live runtime evidence corroborate it. Project Cognition with intent `test_design` is navigation only and no cognition claim may replace code verification. A specification or Plan may contribute an intended-behavior basis, but neither is required to start. Freeze source revisions or fingerprints before any lane is prepared.
2. **Initialize or CAS-reopen exactly one root.** Choose one stable integration-native Leader identity for this run. `project-baseline` and `feature` create new roots only: run `{{specify-subcmd:specify-runtime test-design init --scope project --mode project-baseline --leader-id <leader-id> --input-json '<inline|@path|->' --format json}}` or `{{specify-subcmd:specify-runtime test-design init --scope feature --mode feature --feature-dir <feature-dir> --leader-id <leader-id> --input-json '<inline|@path|->' --format json}}`. For `incremental-update` or `audit`, first read status, then run the matching form with the same `--leader-id`, `--mode <incremental-update|audit>`, and `--expected-revision <revision>` against that existing root. The runtime preserves stable canonical IDs and resets lane, validation, and handoff state; audit must retain the exact frozen boundary, while incremental update accepts only the explicitly supplied boundary delta. Prefer `@path` or stdin for large JSON on Windows. Never hand-author or overwrite state or canonical artifacts.
3. **Resume from machine state.** Run `{{specify-subcmd:specify-runtime test-design status --feature-dir <feature-dir> --format json}}` for feature scope, or omit `--feature-dir` for project scope. Follow runtime state rather than chat memory. For `blocked` or `stale`, consume `recovery_action` in the same invocation: agent-owned repair executes its exact `base_argv`; genuine authority-owned input waits for real evidence but never asks the user to repair lifecycle state or reconstruct a command. `next_action` otherwise expresses the default formal Tasks route.
4. **Author and build the Test Universe.** Inspect each initialized canonical artifact with targeted `specify-runtime artifact show` calls. Populate the universe, catalog, data manifest, and coverage matrix only through fresh `artifact lease` plus JSON-pointer `artifact patch` mutations; never replace a whole canonical file. Then run `{{specify-subcmd:specify-runtime test-design universe-build --feature-dir <feature-dir> --expected-revision <revision> --format json}}`, omitting `--feature-dir` only for project scope. Audit the projection of requirements, `TO-*` obligations, capabilities, journeys, contracts, states, risks, existing verification, regressions, consumers, and operational obligations.
5. **Prepare bounded discovery lanes.** Submit a `lanes` array to `{{specify-subcmd:specify-runtime test-design lane-prepare --feature-dir <feature-dir> --expected-revision <revision> --input-json '<inline|@path|->' --format json}}`. Each lane declares stable identity, kind, title, obligation IDs, non-broad `read_paths`, and concrete questions. Partition by capability, risk, consumer chain, or material question; avoid duplicate investigation.
6. **Lease only available work.** Use status before each wave, then call `{{specify-subcmd:specify-runtime test-design lane-lease --feature-dir <feature-dir> --expected-revision <revision> --worker-id <worker-id> --format json}}` once per available subagent slot. Dispatch the returned brief unchanged with `.specify/templates/worker-prompts/test-design-worker.md`.
7. **Checkpoint or yield.** A worker submits the schema-shaped result with the returned `checkpoint_argv_prefix`, whose owned verb is `specify-runtime test-design lane-checkpoint`, and its result JSON. When the bounded assignment cannot finish safely, execute the returned `yield_argv_prefix`, whose owned verb is `specify-runtime test-design lane-yield`, with `--reason <exact-reason>`; never reconstruct either command from stale state, omit unread paths, or fabricate terminal coverage.
8. **Accept only verified attempts.** The Leader compares inspected paths, verified evidence records, exact per-`TO-*` `obligation_results`, candidate cases, data requirements, contradictions, unknowns, and bidirectional gaps against the leased packet, then calls `{{specify-subcmd:specify-runtime test-design lane-accept --feature-dir <feature-dir> --expected-revision <revision> --lane-id <lane-id> --attempt-id <attempt-id> --format json}}`. Requeue or yield incomplete work; never normalize a rejected result by editing runtime files.
9. **Synthesize canonical test truth.** After all discovery lanes join, the Leader reviews accepted proposals, registers accepted evidence, and merges approved case/data/coverage changes through fresh leased JSON-pointer artifact patches. Submit approved gap rows through `{{specify-subcmd:specify-runtime test-design gap-reconcile --feature-dir <feature-dir> --expected-revision <revision> --leader-id <leader-id> --input-json <gap-json> --format json}}`; the runtime atomically maintains `GAP-*` plus reverse `TO-*` / `COV-*` refs. Only then run `{{specify-subcmd:specify-runtime test-design synthesize --feature-dir <feature-dir> --expected-revision <revision> --leader-id <leader-id> --format json}}` with the same Leader identity recorded by init. The runtime validates the canonical bundle and accepted evidence, checks stable IDs, cross-links, source fingerprints, and global artifact writes, records artifact digests, and advances runtime state; it does not silently turn worker proposals into truth.
10. **Run an independent audit wave.** Call `{{specify-subcmd:specify-runtime test-design audit-prepare --feature-dir <feature-dir> --expected-revision <revision> --format json}}`, lease the generated `AUDIT-*` lane to an independent worker, and use the same checkpoint/yield/accept sequence. If one auditor is unavailable, redispatch or wait in the same invocation; never self-audit or make the user repair the lane.
11. **Validate the bounded claim.** Run `{{specify-subcmd:specify-runtime test-design validate --feature-dir <feature-dir> --expected-revision <revision> --format json}}`. Accept only `complete_against_frozen_scope`, `qualified_with_declared_gaps`, `blocked`, or `stale`; never claim `absolutely_complete`. A blocked or stale result stays with Test Design: execute returned `recovery_action` in the same invocation for agent-owned repair, then rebuild and audit; only genuine authority-owned evidence may wait.
12. **Preserve the Tasks compatibility handoff.** Call `{{specify-subcmd:specify-runtime test-design handoff --feature-dir <feature-dir> --expected-revision <revision> --format json}}` for an eligible feature result. Handoff does not authorize an immediate Tasks return: execute its returned publish `next_argv` and do not return to Tasks before publication and projection verification finish.
13. **Publish, project, verify, and return.** Preserve `validate -> handoff -> publish -> projection-build --consumer tasks -> projection-verify` for Tasks; Plan/Quick/Review publish directly when eligible. Run `specify-runtime test-design publish`, then consume `projection_action` for `specify-runtime test-design projection-build`; execute the returned next_argv, owned by `specify-runtime test-design projection-verify`, exactly. Successful verification returns the selected consumer. Pass that action to the current orchestrator so it returns to the original consumer without asking the user to re-invoke it. Publications/projections remain runtime-owned pointer contracts.

Use an immutable upstream consumer basis: Plan uses the current feature
`spec-contract.json`; Quick uses the runtime-owned
`.planning/quick/<id>/confirmation.json`; Tasks uses the finalized
`plan-contract.json`; Review uses `implementation-handoff.json`. Never use the
consumer artifact that will receive `projection_binding` as its own basis.

For project scope, use the same commands without `--feature-dir`; never invent a
feature directory merely to satisfy an example argv.

## Test-Material Contract

Every required dataset, fixture, golden file, reference vector, account/role,
environment, clock, external response, or device state receives exactly one
disposition: `reuse`, `generate`, `search`, `request`, `block`, or `defer`.
Record readiness, provenance refs, sensitivity, privacy/PII handling, license,
reproducibility or seed, sanitization, retention, cleanup, applicable cases,
and the observable oracle.

- `reuse`: identify the existing authoritative material and prove that it is safe and current.
- `generate`: record a deterministic recipe; this workflow may keep a safe workflow-local planning sample but must not materialize repository fixtures.
- `search`: use primary, official, authoritative, or appropriately licensed sources and preserve provenance; never turn an unattributed search result into test truth.
- `request`: name the human-owned input, why it is required, safe transfer constraints, unblock evidence, and exact resume point.
- `block`: identify the affected obligations and why no safe executable case can yet be designed.
- `defer`: record owner, residual risk, reason, and a concrete revisit condition.

Never ingest unsanitized production customer data, secrets, credentials, private
keys, or unlicensed material. Never disguise unresolved material readiness as a
generated placeholder.

The Leader stores accepted textual source extracts or structured provenance with
`{{specify-subcmd:specify-runtime evidence register --content <inline-payload|@path|-> --scope test-design --source <source> --provenance <provenance>}}` and imports accepted external or binary material with
`{{specify-subcmd:specify-runtime evidence import --file <path> --scope test-design --source <source> --provenance <provenance>}}`. Workers only propose evidence; they never register their own result as accepted truth. Verify the returned content-addressed record and cite its `evidence_id` / `record_ref` from material and coverage rows.

Bounded external research remains a Test Design discovery lane. The existing
`sp-deep-research` runtime is plan-only Deep Research and returns to Plan; do
not route an independent test-design run directly to it. When a disposable
proof or planning feasibility decision is genuinely required, return the typed
`TO-*`/`GAP-*` blocker to the original consumer: Plan may own plan-only Deep
Research and then reselect Test Design; Quick/Tasks/Review retain repair
ownership on their own path. Do not fabricate a material or downgrade scope.

## Planning-Only Hard Boundary

- Do not implement, modify, run, or repair product tests, fixtures, harnesses, source code, migrations, build files, deployment configuration, or production data.
- Do not claim tests passed, behavior is fixed, or release is safe; this workflow designs evidence obligations and materials only.
- `sp-tasks` owns executable work decomposition, `sp-implement` owns test and fixture implementation, `sp-review` owns integrated real-entrypoint proof and bounded repair, and `sp-accept` owns human judgment.
- Preserve every exclusion, qualified gap, blocker, residual risk, evidence freshness rule, and update trigger in canonical runtime artifacts, the publication, typed projections, and the compatibility Tasks handoff.

{{spec-kit-include: ../command-partials/common/learning-layer.md}}
