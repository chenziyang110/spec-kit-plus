---
description: Use when a project or planned feature needs an evidence-backed Test Universe, professional test cases, test-material requirements, coverage traceability, and a pointer-only handoff before task decomposition.
workflow_contract:
  when_to_use: Use after plan and before tasks for an active feature, or independently for a project baseline, incremental update, or audit of existing test-design artifacts.
  primary_objective: Freeze the evidence boundary, coordinate read-only discovery and independent audit lanes, and produce runtime-validated test-design planning artifacts without implementing or running tests.
  primary_outputs: 'Project mode writes `.specify/test-design/`; feature mode writes `<FEATURE_DIR>/test-design/`. The runtime owns `test-state.json`, `test-universe.json`, `test-catalog.json`, `test-data-manifest.json`, `coverage-matrix.json`, `test-gaps.json`, `lane-manifest.json`, accepted lane results, and the optional feature `handoff-to-tasks.json`.'
  default_handoff: /sp.tasks only after a feature-scoped validate and handoff succeeds; project-baseline and audit modes may close without entering the feature delivery chain.
handoffs:
  - label: Create Tasks
    agent: sp.tasks
    prompt: Build the executable task graph from the validated test-design pointer handoff and the completed plan.
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
Tasks handoff. If native subagents cannot execute a substantive lane, keep the
lane pending or yielded, record the blocker, and stop rather than weakening the
evidence boundary.

## Feature Workflow Lock

- For `feature` mode, first query `{{specify-subcmd:specify-runtime workflow show --feature-dir <feature-dir> --format json}}`. Require the feature workflow to show `stage=plan`, `status=completed`, and Tasks as the legal next stage. Test Design is an optional auxiliary planning workflow: it must not transition, reopen, complete, or edit `FEATURE_DIR/workflow.json`.
- `project-baseline` is standalone and must not require or create a feature workflow.
- `incremental-update` and `audit` reuse an existing project or feature artifact root selected explicitly from current state. Never silently retarget an active feature or mix project and feature artifacts.
- When mode, root, included paths, exclusions, or risk dimensions are materially ambiguous, ask one concise confirmation before `init`.

## Runtime-Owned Flow

1. **Freeze scope.** Build the `init` input in memory with non-empty `query`, `source_refs`, `included_paths`, and `risk_dimensions`, plus explicit `excluded_paths`. Freeze source revisions or fingerprints before any lane is prepared. Project Cognition with intent `test_design` is advisory routing; live repository and approved workflow artifacts remain truth.
2. **Initialize or CAS-reopen exactly one root.** Choose one stable integration-native Leader identity for this run. `project-baseline` and `feature` create new roots only: run `{{specify-subcmd:specify-runtime test-design init --scope project --mode project-baseline --leader-id <leader-id> --input-json '<inline|@path|->' --format json}}` or `{{specify-subcmd:specify-runtime test-design init --scope feature --mode feature --feature-dir <feature-dir> --leader-id <leader-id> --input-json '<inline|@path|->' --format json}}`. For `incremental-update` or `audit`, first read status, then run the matching form with the same `--leader-id`, `--mode <incremental-update|audit>`, and `--expected-revision <revision>` against that existing root. The runtime preserves stable canonical IDs and resets lane, validation, and handoff state; audit must retain the exact frozen boundary, while incremental update accepts only the explicitly supplied boundary delta. Prefer `@path` or stdin for large JSON on Windows. Never hand-author or overwrite state or canonical artifacts.
3. **Resume from machine state.** Run `{{specify-subcmd:specify-runtime test-design status --feature-dir <feature-dir> --format json}}` for feature scope, or omit `--feature-dir` for project scope. Follow the returned phase, pending lanes, blocker, and next action rather than chat memory.
4. **Author and build the Test Universe.** Inspect each initialized canonical artifact with targeted `specify-runtime artifact show` calls. Populate the universe, catalog, data manifest, and coverage matrix only through fresh `artifact lease` plus JSON-pointer `artifact patch` mutations; never replace a whole canonical file. Then run `{{specify-subcmd:specify-runtime test-design universe-build --feature-dir <feature-dir> --expected-revision <revision> --format json}}`, omitting `--feature-dir` only for project scope. Audit the projection of requirements, `TO-*` obligations, capabilities, journeys, contracts, states, risks, existing verification, regressions, consumers, and operational obligations.
5. **Prepare bounded discovery lanes.** Submit a `lanes` array to `{{specify-subcmd:specify-runtime test-design lane-prepare --feature-dir <feature-dir> --expected-revision <revision> --input-json '<inline|@path|->' --format json}}`. Each lane declares stable identity, kind, title, obligation IDs, non-broad `read_paths`, and concrete questions. Partition by capability, risk, consumer chain, or material question; avoid duplicate investigation.
6. **Lease only available work.** Use status before each wave, then call `{{specify-subcmd:specify-runtime test-design lane-lease --feature-dir <feature-dir> --expected-revision <revision> --worker-id <worker-id> --format json}}` once per available subagent slot. Dispatch the returned brief unchanged with `.specify/templates/worker-prompts/test-design-worker.md`.
7. **Checkpoint or yield.** A worker submits the schema-shaped result with the returned `checkpoint_argv_prefix`, whose owned verb is `specify-runtime test-design lane-checkpoint`, and its result JSON. When the bounded assignment cannot finish safely, execute the returned `yield_argv_prefix`, whose owned verb is `specify-runtime test-design lane-yield`, with `--reason <exact-reason>`; never reconstruct either command from stale state, omit unread paths, or fabricate terminal coverage.
8. **Accept only verified attempts.** The Leader compares inspected paths, verified evidence records, exact per-`TO-*` `obligation_results`, candidate cases, data requirements, contradictions, unknowns, and bidirectional gaps against the leased packet, then calls `{{specify-subcmd:specify-runtime test-design lane-accept --feature-dir <feature-dir> --expected-revision <revision> --lane-id <lane-id> --attempt-id <attempt-id> --format json}}`. Requeue or yield incomplete work; never normalize a rejected result by editing runtime files.
9. **Synthesize canonical test truth.** After all discovery lanes join, the Leader reviews accepted proposals, registers accepted evidence, and merges approved case/data/coverage changes through fresh leased JSON-pointer artifact patches. Submit approved gap rows through `{{specify-subcmd:specify-runtime test-design gap-reconcile --feature-dir <feature-dir> --expected-revision <revision> --leader-id <leader-id> --input-json <gap-json> --format json}}`; the runtime atomically maintains `GAP-*` plus reverse `TO-*` / `COV-*` refs. Only then run `{{specify-subcmd:specify-runtime test-design synthesize --feature-dir <feature-dir> --expected-revision <revision> --leader-id <leader-id> --format json}}` with the same Leader identity recorded by init. The runtime validates the canonical bundle and accepted evidence, checks stable IDs, cross-links, source fingerprints, and global artifact writes, records artifact digests, and advances runtime state; it does not silently turn worker proposals into truth.
10. **Run an independent audit wave.** Call `{{specify-subcmd:specify-runtime test-design audit-prepare --feature-dir <feature-dir> --expected-revision <revision> --format json}}`, lease the generated `AUDIT-*` lane to a worker identity that is neither the Leader nor any accepted discovery worker, and use the same checkpoint or yield plus Leader acceptance sequence. The result must include non-empty canonical-artifact inspections, verified evidence, per-obligation accounting, and explicit audit checks; findings may be empty only after those checks pass. If no independent auditor is available, leave the lane pending or yielded and block validation/handoff.
11. **Validate the bounded claim.** Run `{{specify-subcmd:specify-runtime test-design validate --feature-dir <feature-dir> --expected-revision <revision> --format json}}`. Accept only the runtime claim statuses `complete_against_frozen_scope`, `qualified_with_declared_gaps`, `blocked`, or `stale`. `complete_against_frozen_scope` requires zero unaccounted obligations and an accepted independent audit. Do not use or claim `absolutely_complete`; changed sources, missing evidence, or unresolved blocking risk invalidate that claim.
12. **Hand off pointers, never copied prose.** For a feature result whose validated claim permits downstream work, call `{{specify-subcmd:specify-runtime test-design handoff --feature-dir <feature-dir> --expected-revision <revision> --format json}}`. Only the runtime writes `handoff-to-tasks.json` with canonical `test_case_refs`, `test_data_refs`, artifact digests, gap and audit refs, state revision, source fingerprint, and `next_command: /sp.tasks`. Project-baseline output remains a reusable planning baseline unless the user explicitly selects a feature consumer.

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
`{{specify-subcmd:specify-runtime evidence register --content '<payload>' --scope test-design --source <source> --provenance <provenance>}}` and imports accepted external or binary material with
`{{specify-subcmd:specify-runtime evidence import --file <path> --scope test-design --source <source> --provenance <provenance>}}`. Workers only propose evidence; they never register their own result as accepted truth. Verify the returned content-addressed record and cite its `evidence_id` / `record_ref` from material and coverage rows.

When the missing truth is external feasibility, a normative oracle, a disposable
proof, or evidence that cannot be established by bounded read-only search, stop
with the affected `TO-*` rows explicit and hand off to `sp-deep-research`.
Resume Test Design only from its primary-source findings, evidence records, and
Planning Handoff; do not fabricate a material or downgrade the obligation.

## Planning-Only Hard Boundary

- Do not implement, modify, run, or repair product tests, fixtures, harnesses, source code, migrations, build files, deployment configuration, or production data.
- Do not claim tests passed, behavior is fixed, or release is safe; this workflow designs evidence obligations and materials only.
- `sp-tasks` owns executable work decomposition, `sp-implement` owns test and fixture implementation, `sp-review` owns integrated real-entrypoint proof and bounded repair, and `sp-accept` owns human judgment.
- Preserve every exclusion, qualified gap, blocker, residual risk, evidence freshness rule, and update trigger in the canonical runtime artifacts and pointer handoff.

{{spec-kit-include: ../command-partials/common/learning-layer.md}}
