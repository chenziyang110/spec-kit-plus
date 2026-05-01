---
description: "Use when facing 2+ independent test failures, bugs, research questions, map lanes, or implementation tasks that can run without shared write state. Dispatch native subagents through the owning sp-* workflow."
---

# Dispatching Parallel Agents (Spec Kit Plus)

Use this skill when there are 2+ independent lanes: unrelated failing tests,
separate bugs, distinct modules, read-only evidence lanes, testing-system build
lanes, map scan/build lanes, or implementation tasks with non-overlapping
write-sets.

The stable default is current-runtime dispatch. Do not turn parallel work into a
user coordination problem when native subagents are available.

Current routing vocabulary:

- Use subagents-first execution for bounded delegated work.
- Dispatch `one-subagent` when one safe lane is ready.
- Dispatch `parallel-subagents` when two or more independent lanes can run
  concurrently.
- Use `leader-inline-fallback` only after recording why delegation is
  unavailable, unsafe, or not packetized.
- Do not use old strategy labels as routing choices.

## When to Use

- 2+ independent lanes can be understood or changed without waiting on each
  other.
- Each lane has a clear owner, scope, and verification target.
- Write-set overlap is absent or can be explicitly sequenced at a join point.
- Running the lanes in parallel materially improves throughput, evidence quality,
  or verification confidence.

## Process

1. **Route first**: Select the owning `sp-*` workflow before dispatch. Common
   canonical routes are `sp-quick`, `sp-debug`, `sp-test-scan`, `sp-test-build`,
   `sp-map-scan`, `sp-map-build`, and `sp-implement`. When telling the user what
   to type, use placeholders such as `{{invoke:quick}}`, `{{invoke:debug}}`,
   `{{invoke:test-scan}}`, `{{invoke:test-build}}`, `{{invoke:map-scan}}`,
   `{{invoke:map-build}}`, or `{{invoke:implement}}`.
2. **Split lanes**: Name each lane, purpose, read context, write-set, forbidden
   paths, shared surfaces, and verification target.
3. **Check conflicts**: Do not dispatch two writers to the same file or shared
   state unless one lane is explicitly read-only or the workflow defines a safe
   join point.
4. **Packetize**: Use the workflow's validated `WorkerTaskPacket` or equivalent
   execution packet. Raw task text is not enough.
5. **Dispatch native subagents**: Use `parallel-subagents` on the
   `native-subagents` surface first, such as Codex `spawn_agent`/`wait_agent`,
   Claude Task, or the active CLI's equivalent. Keep the leader focused on
   integration and conflict resolution.
6. **Join on structured handoff**: Each worker must report changed files,
   verification run, failures, open risks, and whether its acceptance target is
   met. Integrate only after the handoff is specific enough to review.

## Fallbacks

- Use `sp-teams` only when Codex work needs durable team state, result files,
  explicit join tracking, or lifecycle control beyond one in-session burst.
- Use a separate terminal only when the current runtime has no native subagents
  and no managed-team path can safely represent the lanes.
- If lanes share write state or one fix may resolve the others, keep the work in
  one sequential workflow run until the dependency is clarified.

## Behavioral Rules

- Do not fix unrelated systems in one leader-inline pass when current-runtime
  native subagents can handle independent bounded lanes.
- Do not dispatch agents that will modify the same write-set concurrently.
- Do not ask the user to manually coordinate parallel terminals as the first
  option.
- Do not mark a lane complete from silence, idle status, or a vague summary.
- If the first split reveals hidden coupling, stop parallel execution and move
  the coupled work behind one owner or join point.

## Red Flags

- "Fix all failing tests" with failures spread across unrelated modules.
- Multiple implementation tasks touch different write-sets, but the leader is
  about to execute them serially without checking native subagents.
- A worker prompt does not include a write-set, forbidden paths, or verification
  target.
- A handoff says "done" without file paths and command output summary.
- The fallback plan starts with "open another separate terminal" even though the
  current runtime supports native subagents.
