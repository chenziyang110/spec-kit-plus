{{spec-kit-include: ../common/user-input.md}}

## Objective

Prove that the integrated implementation is an operable product from its official real entrypoints, repair bounded implementation defects, and preserve enough evidence to resume or make the final review claim honestly.

## Process

## Intake And Runtime Ownership

- Resolve exactly one feature and inspect `workflow show` before mutation. Transition from completed `implement` to `review` with the runtime-returned revision; do not hand-edit `workflow-runtime.json`.
- Run `{{specify-subcmd:review prepare --feature-dir <feature-dir> --format json}}`. Treat `implementation-handoff.json` as the implementation-to-review source contract and `review-state.json` as Review's resumable truth.
- The Leader owns `review-state.json`, the official runtime instances, ports, test data, finding lifecycle, repair acceptance, and final verdict.
- On resume, run `{{specify-subcmd:review resume-audit --feature-dir <feature-dir> --format json}}` when available. Continue from the exact scenario/finding cursor and invalidate evidence whose implementation fingerprint or source revision is stale.

## System Review Loop

1. Start or restart each applicable official real entrypoint and prove its ready signal without hidden manual setup.
2. Execute every mandatory scenario as a user journey with explicit preconditions, actions, and observable expected results.
3. Inspect the actual consumer chain for the current path: button or command, route, handler/controller, provider/factory/service, persistence or external dependency, and visible feedback.
4. Record sanitized integrated evidence and any finding in Review-owned state.
5. Repair understood in-scope defects, then restart and rerun the exact failed scenario plus affected regression paths. Never close a finding from source inspection alone.
6. Repeat until approved or until a structured handoff/blocker is required.

UI-bearing scenarios require real-entrypoint `structure_snapshot`, `visual_capture`, and `runtime_diagnostics` evidence with `evidence_scope: integrated`. Validate interaction, navigation, loading, empty, error, permission, persistence/reload, responsive, keyboard/focus, console, network, and runtime states when applicable. Automated behavior checks remain distinct from visual and interaction acceptance.

## Delegation

- Use leader-direct execution for compact, tightly coupled review work. Use subagents for independent read-only wiring audits, isolated user journeys, or non-overlapping repair write sets that materially benefit from isolation or parallelism.
- Compile each `SystemReviewPacket` just in time from current state and live code. Never dispatch a raw checklist or the entire feature package.
- Serialize paths sharing one browser session, database state, service instance, port, or write set. Integrate worker results before accepting a repair.
- A worker result is evidence only. A worker must not declare the whole system approved; the Leader owns the final verdict after an integrated restart and required regression.

## Output Contract

- Keep `review-state.json` fresh and schema-valid with scenario results, findings, repair/revalidation evidence, cursor, blockers, and next action.
- Store evidence under `review-evidence/` and reference it compactly from state; do not paste large logs or screenshots into agent state.
- After the final integrated restart, run `{{specify-subcmd:review validate --feature-dir <feature-dir> --format json}}`, bind its `current_fingerprint` to `final.reviewed_snapshot_sha256`, and only then set Review `status: approved`. Run `{{specify-subcmd:review closeout --feature-dir <feature-dir> --format json}}` only after all required scenarios pass, all required evidence is integrated and fresh, and blocking findings are zero.
- On successful Review closeout, update Review-owned rich state truthfully, execute the returned revision-bound `workflow complete-stage` argv separately, hand off to `{{invoke:accept}}`, and stop. Do not enter acceptance in this invocation.

## Guardrails

- `sp-review` is not permission to change approved product scope or upstream truth. Repair clear implementation and wiring defects only.
- Keep the existing event-triggered task review embedded in `sp-implement`; do not duplicate its task lifecycle ledger here.
- Do not claim success because the build passes, tasks are checked, files exist, or a worker says PASS.
- Do not push, deploy, modify protected systems, use real customer data, or perform external writes without explicit authority. Use isolated test data and the shared blocker contract for genuine external boundaries.
