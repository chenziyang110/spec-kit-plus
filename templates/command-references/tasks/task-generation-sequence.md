Trigger: when compiling a ready plan contract into a task graph.

Purpose: produce one canonical, dependency-aware execution graph with enough stable information for direct work or just-in-time delegated packets.

Preserved Contract: complete scope, boundaries, interfaces, obligations, verification, parallel safety, and recovery remain executable and traceable.

## Sequence

1. Resolve the feature lane and query canonical `plan-contract.json` through `specify-runtime artifact show`.
2. Reuse its context capsule and the phase-level optional `specify-runtime cognition compass --intent plan` intake; that shared intake is the only cognition call for an unchanged task-generation pass. Use returned minimal live reads only for missing or stale task-shaping facets. Carry selected capability refs, expected paths, validation routes, forbidden drift, and known unknowns into the task graph. Do not rerun cognition while shaping tasks or packets.

3. Select execution mode:

- `light`: compact leader-direct tasks; no machine graph or lane files unless resume/dependency complexity needs them.
- `standard`: canonical `task-index.json`; delegate decomposition only when isolated lanes materially shorten the critical path.
- `heavy`: canonical graph plus exact parallel/join/recovery constraints; require safely packetized lanes with runtime-owned inline result channels when independent high-risk analysis is necessary.

4. Compile tasks around outcomes and acceptance proof. Each canonical task stores:

- stable id and objective;
- dependencies and packet mode;
- expected write scope or discovery rule;
- required refs and forbidden drift;
- objective acceptance and verification;
- task-relevant interfaces, `MP-*`, `CA-###`, UI/fidelity, and real-entrypoint evidence;
- join point and stop/reopen condition when applicable.

## Complete-First Scope Preservation

Keep protected obligations and the complete confirmed scope executable in the graph.

Do not shrink scope into agent-invented `v1/v2`, `P0/P1`, or a future-work delivery slice. Execution phases and user-story priorities order the complete confirmed scope; they are not delivery deferral. A valid deferral references user confirmation, exact excluded behavior, residual risk, reopen or stop condition, and downstream artifact. If the user did not confirm the deferral, task the behavior or block truthfully.

5. Build dependency edges, parallel batches, join points, and write-set safety. Exact write sets are required for parallel delegation; leader-direct tasks may use a bounded module scope that live evidence can refine. Every explicit join point includes a validation target, validation command or concrete check, pass condition, and recovery on failure.

The graph may describe the full feature delivery shape, but dispatch guidance and packet compilation target only the current ready batch.

6. Validate coverage, acyclicity, task granularity, interface flow, parallel isolation, acceptance/verification, obligation mapping, and target boundary.

7. Submit the semantic task package to `specify-runtime tasks build`, refine it with `specify-runtime tasks upsert`, `specify-runtime tasks set-root`, or `specify-runtime tasks remove`, and call `specify-runtime tasks finalize`. The CLI alone expands the canonical template, validates it, and atomically renders `task-index.json` plus `tasks.md`. Do not use filesystem tools to create, edit, replace, or delete those projections, and do not create a temporary payload file; pass bounded JSON inline. In light mode, the same CLI remains the write authority even when the project-facing projection is compact.

8. Create a pointer-only `handoff-to-tasks.json` only with `specify-runtime tasks handoff --feature-dir <feature-dir> --target tasks --format json` when compatibility requires it, and create `handoff-to-implement.json` with the same command using `--target implement` before implementation handoff. Do not pre-generate all WorkerTaskPackets; `sp-implement` compiles and validates only the current delegated packet against live code.

When decomposition lanes are delegated, each lane has no direct workflow-artifact
write scope. Create an absent `task-generation/lane-manifest.json` through
`specify-runtime artifact scaffold --kind task-generation-lane-manifest`, query
it on resume, replace the bounded `/lanes` array as a whole through fresh leased
JSON-pointer patches, and patch `/status` separately. Never submit the manifest
wholesale or emulate array append. Give each lane the complete
runtime-owned `result submit --command tasks` argv prefix plus inline payload
contract. A read-only evidence worker may satisfy the lane when it can return
the complete structured payload through that CLI channel. The runtime alone
materializes `task-generation/handoffs/<lane-id>.json`; do not create separate
evidence-index and checkpoint logs for the same event.
