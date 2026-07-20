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

1. Compile the Review Universe and use independent coverage discovery to reconcile authoritative obligations with actual consumer and runtime surfaces.
2. Start each official entrypoint, then run a read-only Review/Audit wave whose workers inspect assigned coverage slices and return evidence/findings without edits.
3. The Leader joins all audit packets, rejects stale or incomplete results, resolves coverage gaps, and freezes the accepted finding set.
4. Run a separate Fix wave for accepted findings. Fix workers receive isolated write scopes and may change implementation/tests but never upstream truth.
5. Join and inspect every repair, restart the real product, then run an independent revalidation wave. The repair author must not verify its own finding.
6. Repeat discovery, repair, and revalidation until the Review Universe has zero uncovered obligations/surfaces and all packets joined.

UI-bearing scenarios require real-entrypoint `structure_snapshot`, `visual_capture`, and `runtime_diagnostics` evidence with `evidence_scope: integrated`. Validate interaction, navigation, loading, empty, error, permission, persistence/reload, responsive, keyboard/focus, console, network, and runtime states when applicable. Automated behavior checks remain distinct from visual and interaction acceptance.

## Delegation

- The Leader orchestrates subagents across the Review/Audit wave, Fix wave, and independent revalidation wave; direct execution is reserved for compact, tightly coupled steps.
- Audit workers are read-only. Fix workers receive finding-bound, non-overlapping write scopes. Revalidation workers are read-only and independent from the repair author.
- Compile each `SystemReviewPacket` just in time from current state and live code. Never dispatch a raw checklist or the entire feature package.
- Serialize paths sharing one browser session, database state, service instance, port, or write set. Integrate worker results before accepting a repair.
- A worker result is evidence only. A worker cannot declare coverage complete or the whole system approved; the Leader owns all joins, zero-uncovered coverage, repair acceptance, and the final verdict after an integrated restart and required regression.

## Output Contract

- Keep `review-state.json` fresh and schema-valid with scenario results, findings, repair/revalidation evidence, cursor, blockers, and next action.
- Store evidence under `review-evidence/` and reference it compactly from state; do not paste large logs or screenshots into agent state.
- After the final integrated restart, run `{{specify-subcmd:review validate --feature-dir <feature-dir> --format json}}`, bind its `current_fingerprint` to `final.reviewed_snapshot_sha256`, and only then set Review `status: approved`. Run `{{specify-subcmd:review closeout --feature-dir <feature-dir> --format json}}` only after all required scenarios pass, all required evidence is integrated and fresh, and blocking findings are zero.
- On successful Review closeout, update Review-owned rich state truthfully, execute the returned revision-bound `workflow complete-stage` argv separately, hand off to `{{invoke:accept}}`, and stop. Do not enter acceptance in this invocation.

## Guardrails

- `sp-review` is not permission to change approved product scope or upstream truth. Every approved-scope defect stays in Review regardless of repair size, including missing code, task omission, and unknown root cause; use a diagnostic packet before a Fix packet when needed.
- Review remains the stage owner through diagnosis, repair, and revalidation. Only a proven requirement truth, design truth, or architecture truth gap may produce an upstream handoff; missing code is not an upstream truth gap.
- Keep the existing event-triggered task review embedded in `sp-implement`; do not duplicate its task lifecycle ledger here.
- Do not claim success because the build passes, tasks are checked, files exist, or a worker says PASS.
- Do not push, deploy, modify protected systems, use real customer data, or perform external writes without explicit authority. Use isolated test data and the shared blocker contract for genuine external boundaries.
