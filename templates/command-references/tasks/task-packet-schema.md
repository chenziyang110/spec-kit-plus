Trigger: when shaping task-index.json, a compact compatibility transition, or fields needed for just-in-time WorkerTaskPacket compilation.

Purpose: preserve the minimum task-graph fields required to compile a correct worker packet at execution time without repeating project intake.

Preserved Contract: leader-direct tasks stay compact; delegated packets carry objective, scope, required references, forbidden drift, validation, done condition, task-relevant obligations, and recovery.

## Task Packet Schema

- Resolve the feature from its validated durable workflow binding in the current worktree; task shaping does not allocate a branch or worktree.
- Do not run project cognition from packet shaping. Reuse the context capsule and validation routes already stored by planning/task intake.
- Supply only task-shaping fields to `specify-runtime tasks`: objective, dependencies, expected write scope, required refs, acceptance, verification, optional cheap `task_checks`, obligation refs, join point, packet mode, and any task-local `test_case_refs` / `test_data_refs` carried from an optional authoritative test-design handoff. The CLI owns `task-index.json`.
- `expected_write_scope` is a write-authorization list, not an inference target. Each entry must be an exact future file, an exact directory path, or a bounded subtree ending with `/**`. Reject filename globs such as `*_test.go`, `?`, `[]`, `/*`, or middle `**`. If companion tests, migrations, fixtures, generated files, or other companion artifacts may be created or changed, include them explicitly. When the exact filename is unknown, use the narrowest containing directory or bounded subtree ending with `/**`. Validation commands and `pytest tests/...` paths are evidence only and never grant write authority.
- A later-proven causal companion path is an audited Implement recovery, not a reason to rewrite Tasks: the existing execution guard may append one concrete scope amendment while preserving the original packet, and completion then requires independent scope-drift review.
- Root `validation_policy` uses `feature_epochs`, `max_epochs: 3`, `budget_scope: implement-review`, `budget_ref: implementation-review/validation-runs.json`, and `heavy_gate_owner: leader`. The three epochs are logical baseline/convergence/delivery gates; retries, timeout recovery, and deterministic shards are attempts within their gate. `verification` and `required_validation` remain leader-owned shared gates; only `task_checks` compile into a worker packet.
- At the task-index root, store each official executable entrypoint with its command and observable ready signal, plus required system-review scenarios with stable ID, kind, preconditions, actions, expected results, entrypoint ref, and required evidence. This is feature-level Review input, not duplicated per worker packet.
- Use `packet_mode: leader-direct | delegated | parallel-high-risk`.
- `leader-direct` tasks do not need a WorkerTaskPacket.
- For delegated work, `sp-implement` compiles and validates the packet just in time from the current task, live repository state, and stable contract refs.
- The compiler adds `cognition_delta_contract` (schema/version/task ID and worker-candidate authority). It requires retained failure edits and both rename endpoints in the existing result handoff; source binding and acceptance remain runtime-owned. Do not author runtime history or acceptance fields in Tasks or worker inputs. Older packets without this contract remain readable legacy inputs.
- Keep product `write_scope` and `ui_contract` unchanged. The runtime compiler fills separate `bookkeeping_write_scope` with exact feature-local task/index/workflow-phase/tracker/lifecycle/result paths, including `workflow.json`; do not author that list or use a wildcard. The hashed packet pins both sets. Execution announce returns their union as `planned_write_scope` and binds the exact workflow baseline/latest runtime mutation receipt; guard that full returned set. Changed workflow state is accepted only with a newer matching runtime receipt. Bookkeeping remains CLI-owned and is mutated only through its specialized runtime owner, never hand-edited; shared feature metadata overlap requires serialized ownership rather than omitting it from the claim.
- Packet validation rejects filename globbing before dispatch; only exact future files, exact directories, or bounded `/**` subtrees survive into the packet.
- Preserve `test_case_refs` and `test_data_refs` in the canonical task graph and carry them into the just-in-time packet when they exist; they are consumed as authoritative task inputs, not as a separate public workflow surface.
- Carry `global_constraints`, interfaces, review risks, UI fidelity, controller checks, `MP-*`, and `CA-###` only when they affect that task.
- UI-bearing tasks use the complete current `ui_contract` as their only UI
  execution contract. Carry the direction
  core without reinterpreting it, only the task-relevant reference/content/image
  records, and all platform-neutral evidence kinds. When a registered design
  change applies, include its exact `design_change_id`, `design_change_ref`,
  `design_change_sha256`, `design_contract_ref`, and unchanged
  `style_authority`; never resolve “latest” or
  replace it with any unregistered design document. The compiler adds verified
  plan cognition routes as compact `context_nav` instead of raw graph output.
  `inherit-existing` is a worker guard, not optional advice; page-overhaul
  authorization stays bounded to its exact allowed surfaces.
- When screenshots, HTML, a live/runnable product, source code, recordings, or
  prior implementation govern the UI, copy the exact `source_continuity`
  contract. Its authority refs and surface/action/asset bindings preserve
  business outcomes, side effects, final states, source-target verification,
  exact coverage surface/interaction/component ID equality, and
  `forbid-character-substitution`; any `unresolved_gaps` keeps the packet
  non-ready.
- If live evidence invalidates a predicted path or dependency, repair the task graph or stop/reopen; do not hide drift by expanding worker scope silently.
