# Task graph contract

Tasks express independently verifiable outcomes, not a narrated coding recipe.
Trace every confirmed requirement, plan decision, must-preserve behavior, and
triggered consequence obligation to at least one task or explicit deferral.

Before decomposition, query `test_design_gate.decision` through
`specify-runtime artifact show` and interpret it as
`not_selected|selected|required`. A selected/required Tasks projection must pass
`specify-runtime test-design projection-verify --feature-dir <feature-dir>
--projection-ref <project-relative-ref> --expected-sha256 <sha256>`. It is a
canonical typed pointer-only, read-only input. Tasks must not mutate or copy the
Test Design publication, projection, catalog, data, coverage, gaps, or audit.
Missing or non-current selected input routes to the independent
`$spx-test-design` producer. `not_selected` with no root is the only optional
skip. The Tasks CLI still owns the compatibility handoff binding and rejects
user-authored `test_design_*` fields or foreign task refs.
The Plan binding may be all-null pending or Plan-only and is never Tasks
authorization. The Tasks projection is a read-only decomposition input. Only
the fresh feature handoff plus runtime task-index binding authorizes and
enforces the exact member set.

For a ready version-2 task index, `acceptance_refs` is the complete unique
ordered **copy of `plan-contract.acceptance_refs` values** (typically
`spec-contract.json#/acceptance_criteria/0..N-1`). The pointer spelling
`plan-contract.json#/acceptance_refs/N` is accepted and rewritten to those
values. The Human Acceptance Universe is non-empty, every obligation
`source_ref` uses one of those acceptance values, and every scenario declares
its human actor, official entrypoint, linked required Review scenario,
observable steps, and complete obligation mapping. Missing files, omitted refs,
downgraded obligations, or regenerated fallback universes are contract failures.

Task authoring JSON flags (`--definition-json`, `--task-json`, `--patch-json`)
accept inline JSON, `@path`, or `-` (stdin). Prefer `@path` on Windows for large
packages. `set-root` cannot author CLI-owned `transition`/`status`/`version`/
`tasks`; use `finalize` for transition readiness. Per-task `title` aliases
`objective`; `done_condition` aliases `acceptance`.

For each `acceptance_ref`, at least one required `review_obligations` path must
terminate in a dedicated required `system_review_scenarios` row whose required
acceptance-source set is exactly that ref. Shared or broad regression scenarios
may remain as additional coverage but cannot serve as a dedicated witness for
any ref. Every required human-acceptance scenario must link at least one
dedicated required Review scenario for its own `acceptance_ref`.

A task is ready when its authoritative inputs and dependencies are stable, its
write surface is bounded, and a worker can tell completion from failure. Use
dependency edges for true prerequisites, not display ordering. Two tasks are
parallel-safe only when neither consumes the other's uncommitted result and
their writes, generated outputs, state mutations, and verification fixtures do
not collide.
Every `expected_write_scope` entry must be an exact future file, an exact
directory path, or a bounded subtree ending with `/**`. Reject filename globs
such as `*_test.go`, `?`, `[]`, `/*`, or middle `**` before dispatch. If the
task may create or modify companion tests, migrations, fixtures, generated
files, or other companion artifacts, list those future writes explicitly.
When the exact filename is unknown, use the narrowest containing directory or
bounded subtree ending with `/**`. Validation commands and `pytest tests/...`
references are evidence only and never grant write authority.

The graph and its Markdown projection are CLI-owned. Pass semantic task/root
objects inline to the Tasks CLI; use `build`, `upsert`, `set-root`, `remove`,
and `finalize` for every mutation. Read targeted fields through
`specify-runtime artifact show --json-pointer ...`. Direct filesystem writes,
whole-file rewrites, and temporary authoring payloads are invalid workflow
operations.

Every task records required refs, forbidden drift, packet mode, objective
acceptance, verification, stop/reopen criteria, and failure recovery. A join
point records its members, validation target, command or concrete check, pass
condition, and recovery on failure before dependent tasks become ready.

For every active entrypoint outcome, propagate its existing CA into top-level
`consequence_obligation_refs`, a task's `consequence_obligation_ids`, and a
required `review_obligations` row mapped to required real-entrypoint
`system_review_scenarios`. Reuse that consequence/Review chain; do not create a
parallel outcome-coverage object. Submit user-visible recovery, retry,
cancellation, foreground escalation, and request retention through `build`/`upsert`; the task CLI renders `tasks.md`.

Keep setup and foundational work before feature slices; verify at natural join
points. If a task discovers unknown product behavior or architecture, the task
graph is not the place to decide it—reopen the owning upstream workflow.

UI tasks additionally query the plan `ui_design_contract` and feature
`ui-brief.md` through targeted `specify-runtime artifact show` calls. Each task owns a bounded surface/state outcome and carries
task-specific `ui_contract`, fidelity level, design inputs, required states,
real entry points, current direction fields, task-relevant reference/content/image
records, exact `design_change_id`/`design_change_ref`/`design_change_sha256`/
`design_contract_ref`, exact `style_authority`, immutable handoff ref/digest, task-relevant `DH-*` contract IDs,
exact `interaction_matrix` / `editing_matrix` / `data_state_matrix` rows, component
`interaction_modes` / `data_scenarios`, responsive `stretch_behavior` /
`overflow_behavior`, structure/visual/runtime evidence, and comparison or human review. Never reduce these rows to
`required_states`; every data-bearing task includes empty and populated data,
and applicable tasks include keyboard/focus, recovery, and active resize. Use
`assets/ui-task.md` for the project-facing detail and
`assets/ui-task-index-entry.json` as the semantic field catalog. Submit only
meaningful non-default values; `specify-runtime tasks` expands the exact canonical
shape from the packaged task-packet template. General UI
without an external fidelity target still sets `ui_contract.fidelity_level` to
`approximate` against the approved design/brief; use `inspiration` only when it
is the approved reference relationship. Missing UI fields are a graph defect, not
`not_applicable`.
Never resolve “latest” from `.specify/design/index.json`; copy the exact
registered binding selected by the feature `ui-brief.md`.
Never let a worker reinterpret `inherit-existing` as permission to restyle or
expand an authorized page delta into protected shell/shared-component surfaces.
Task contracts may select a plan subset of `DH-*` IDs, and all UI tasks together
must cover the plan set. They do not rewrite the selected handoff rows.

## Professional UI contract continuity

Every UI task carries the exact `source_continuity` contract when source-grounded,
plus its applicable exact subset of `surface_catalog`,
`scenario_matrix`, `interaction_matrix`, `editing_matrix`, `data_state_matrix`,
`accessibility_matrix`, `navigation_matrix`, `content_matrix`,
`motion_contract`, and `usability_validation`, including the exact
`smoothness_acceptance_ids` and performance budgets, plus component
adoption/permission rows, variants/content constraints/semantic tokens/governance/iconography. All UI
tasks together cover Plan. Split risk-based or pairwise scenarios, never an
unbounded Cartesian product, and keep target-user human review visible.
Each selected surface copies one exact `entrypoint_id` from top-level
`official_entrypoints`; missing, unknown, or multiple bindings block finalize.
