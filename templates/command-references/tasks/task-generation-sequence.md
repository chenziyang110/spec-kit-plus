Trigger: when compiling a ready plan contract into a task graph.

Purpose: produce one canonical, dependency-aware execution graph with enough stable information for direct work or just-in-time delegated packets.

Preserved Contract: complete scope, boundaries, interfaces, obligations, verification, parallel safety, and recovery remain executable and traceable.

## Sequence

1. Resolve the feature lane and read canonical `plan-contract.json`.
2. Reuse its context capsule and the phase-level optional `project-cognition compass --intent plan` intake; that shared intake is the only cognition call for an unchanged task-generation pass. Use returned minimal live reads only for missing or stale task-shaping facets. Carry selected capability refs, expected paths, validation routes, forbidden drift, and known unknowns into the task graph. Do not rerun cognition while shaping tasks or packets.

3. Select execution mode:

- `light`: compact leader-direct tasks; no machine graph or lane files unless resume/dependency complexity needs them.
- `standard`: canonical `task-index.json`; delegate decomposition only when isolated lanes materially shorten the critical path.
- `heavy`: canonical graph plus exact parallel/join/recovery constraints; require safe writable lanes when independent high-risk analysis is necessary.

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

7. Write `task-index.json` as canonical for standard/heavy work and render `tasks.md`. In light mode, write only the compact direct task list unless a graph adds real resume value.

8. Write pointer-only `handoff-to-tasks.json` only when compatibility requires it. Do not pre-generate all WorkerTaskPackets; `sp-implement` compiles and validates only the current delegated packet against live code.

When decomposition lanes are delegated, maintain one `task-generation/lane-manifest.json` plus each lane result. Do not create separate evidence-index and checkpoint logs for the same event.
