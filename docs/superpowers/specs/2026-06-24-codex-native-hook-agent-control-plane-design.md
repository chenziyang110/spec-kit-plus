# Codex Native Hook Agent Control Plane Design

## Goal

Refactor the Codex native hook layer into a fast, explicit, agent-owned control plane.

The hook exists to help the agent do better work: avoid unsafe reads or irreversible actions, stay inside the active workflow phase, recover state after session boundaries, avoid blind retries, and continue when stopping would abandon an active obligation. It should not become a second workflow engine, a user-facing explanation layer, or a broad runtime coordinator.

The first implementation pass should preserve behavior while making the structure ready for stronger performance and policy tuning.

## Current Behavior

Managed Codex native hook registrations are generated into `.codex/hooks.json`. The managed events are:

- `SessionStart`
- `UserPromptSubmit`
- `PreToolUse`
- `PostToolUse`
- `Stop`

Each managed event invokes the same Node entrypoint:

```text
dist/scripts/codex-native-hook.js
```

The entrypoint reads JSON from stdin, identifies the event, performs event-specific work, optionally invokes shared `specify hook ...` checks, and writes a Codex hook JSON response when it has context or a blocking decision.

The current implementation is concentrated mainly in:

- `extensions/agent-teams/engine/src/config/codex-hooks.ts`
- `extensions/agent-teams/engine/src/scripts/codex-native-hook.ts`
- `extensions/agent-teams/engine/src/scripts/codex-native-pre-post.ts`
- `extensions/agent-teams/engine/src/hooks/specify-quality-adapter.ts`
- `src/specify_cli/hooks/**`

## Problems

### Native Adapter Overload

`codex-native-hook.ts` does too many jobs at once: event parsing, session reconciliation, prompt guard orchestration, keyword activation, triage, state writes, context recovery, Stop blocking, shared hook invocation, output merging, and event dispatch.

That makes the file hard to reason about and makes small policy changes risky. A future change to Stop behavior can accidentally affect prompt routing or PostToolUse recovery because they share local helpers and output shaping.

### Block Semantics Are Flattened

Many different conditions become `decision: "block"`:

- security or sensitive path violations
- explicit workflow bypass attempts
- broken workflow state
- useful command output that should be reviewed
- active work that should not be abandoned at Stop
- MCP transport failure

Codex receives the same high-level decision even though each block has a different intent and recovery path. This prevents precise tuning and makes noisy blocking harder to reduce safely.

### Too Many Persistent Side Effects Inside Native Events

The hook currently writes or updates runtime state in several event paths. Some of that is necessary, but native hooks should remain narrowly scoped. Persistent writes should be deliberate and isolated so stale session or phase state cannot create Stop loops or incorrect prompt routing.

### Shared Hook Invocation Is Synchronous And Scattered

Shared `specify hook ...` calls are valuable because they keep workflow policy centralized, but they are currently invoked through synchronous process spawning from event logic. Calls should be centralized so the agent can reason about performance cost, failure behavior, and per-event budgets.

The current path also passes sensitive prompt text through process arguments and has no explicit timeout. Both issues should be fixed in the shared hook client design before implementation planning.

### Stop Is High Impact

Stop has the highest leverage and the highest risk. A correct Stop block prevents abandoned active work. A stale Stop block traps the agent in unnecessary continuation. Stop needs the strictest state freshness and de-duplication model.

## Design Principles

### Agent Control Plane

The hook optimizes agent execution, not user-facing ceremony. It should improve agent behavior at the exact moments where native hooks have leverage:

- before a prompt is routed
- before a tool runs
- after a tool returns
- before the session stops
- when a session starts or resumes

### Cheap First

Each event should begin with local, bounded, cheap checks. Shared hook calls, filesystem scans, or expensive state reads should run only when the event context justifies them.

### High Confidence Blocking

Blocking is reserved for high-confidence cases. Low-confidence signals become `additionalContext`. This keeps the agent informed without turning advisory heuristics into friction.

### Typed Outcomes

Every native hook result should have an internal outcome type before it is converted to Codex JSON:

- `advisory`: extra context only
- `hard-block`: unsafe or explicitly forbidden action
- `repair-block`: state is broken and must be repaired
- `review-block`: a result should be inspected before retrying
- `continue-block`: Stop would abandon active work

The Codex wire format can remain unchanged in the first pass, but the internal type must be explicit.

### Snapshot Then Decide

Event handlers should consume a shared `NativeHookContext` snapshot instead of repeatedly deriving cwd, session id, prompt, tool info, workflow state, and mode state. This reduces duplicated inference and avoids inconsistent decisions inside one event.

## Proposed Architecture

### Entry Point

`codex-native-hook.ts` should become a thin CLI entry:

1. Read stdin JSON.
2. Return a deterministic block for malformed JSON.
3. Build or delegate to the native dispatcher.
4. Print output JSON only when there is an output.

No event policy should live in the CLI entry.

### Dispatcher

Create a native dispatcher module responsible for:

- event name normalization
- base context construction
- session id reconciliation hooks
- per-event routing
- output conversion

The dispatcher should call one event handler per native event.

### Context Snapshot

Introduce `NativeHookContext` with stable fields:

- `cwd`
- `eventName`
- `nativeSessionId`
- `canonicalSessionId`
- `threadId`
- `turnId`
- `promptText`
- `toolName`
- `toolUseId`
- `toolInput`
- `toolResponse`
- `activeWorkflow`
- `runtimeStateDir`

The first pass can populate only the fields currently needed. The key is that handlers read from the snapshot instead of re-parsing payload shape.

### Services And Effects Boundary

Context should describe the event. It should not hide side effects. Event handlers should receive a separate `NativeHookServices` object for reads, writes, process execution, shared hook calls, and plugin/event dispatch.

The services boundary should cover current side effects explicitly:

- session reconciliation and session state writes
- runtime state reads and writes
- HUD reconciliation
- hook plugin dispatch
- `.omx/` local git exclude updates
- team transport-failure writes
- compaction artifact writes
- learning signal writes
- Stop repeat-signature persistence

Handlers may request effects through services, but should not directly reach for global filesystem or process helpers unless the helper is part of the service implementation. This keeps extraction from recreating hidden global side effects under new filenames.

`NativeHookEffects` should record effect metadata for tests and diagnostics:

- `kind`
- `eventName`
- `source`
- `target`
- `status`
- `durationMs`
- `errorClass`, when applicable

### Shared Hook Client

Move all `specify hook ...` invocation into a `SharedHookClient`.

The client should:

- expose named methods such as `validatePrompt`, `validateReadPath`, `workflowPolicy`, `buildCompaction`, and `signalLearning`
- dedupe identical calls within one native event
- return a typed result contract: `ok`, `blocked`, `unavailable`, `timeout`, or `invalid-output`
- preserve current fail-open behavior where existing tests require it
- make future replacement with in-process or long-lived execution possible

The first pass should not change the process-spawn mechanism. It should only centralize it.

The result contract should distinguish runtime failures from policy success:

```ts
type SharedHookClientResult =
  | { status: "ok"; payload: SharedQualityHookPayload; durationMs: number }
  | { status: "blocked"; payload: SharedQualityHookPayload; durationMs: number }
  | { status: "unavailable"; reason: string; attemptedPlans: string[]; durationMs: number }
  | { status: "timeout"; timeoutMs: number; attemptedPlan: string; durationMs: number }
  | { status: "invalid-output"; stdoutPreview: string; attemptedPlan: string; durationMs: number };
```

Shared hook timeout budgets should be explicit. Initial budgets:

- `SessionStart`: 1500 ms total shared-hook budget
- `UserPromptSubmit`: 1500 ms total shared-hook budget
- `PreToolUse`: 750 ms total shared-hook budget
- `PostToolUse`: 1500 ms total shared-hook budget
- `Stop`: 5000 ms total shared-hook budget, still below the managed Codex `Stop` timeout

These budgets are design targets for the optimized client. During behavior-preserving extraction, timeout behavior may be introduced behind a compatibility shim if needed, but the API should expose timeouts from the start.

Sensitive input must not be passed through argv in the long-term client. The migration path is:

1. Add stdin-capable shared hook invocation in `specify hook` for payload-bearing checks such as prompt validation.
2. Have `SharedHookClient.validatePrompt` pass prompt text through stdin or a short-lived private payload file rather than process args.
3. Keep argv-only compatibility as fallback during migration.
4. Never include full prompt text in effect logs, timeout diagnostics, or error previews.

### Outcome Model

Create internal result helpers:

- `advisory(event, context)`
- `hardBlock(event, reason, context)`
- `repairBlock(event, reason, context)`
- `reviewBlock(event, reason, context)`
- `continueBlock(event, reason, context)`

Then map them to current Codex output JSON:

```json
{
  "decision": "block",
  "reason": "...",
  "hookSpecificOutput": {
    "hookEventName": "...",
    "additionalContext": "..."
  }
}
```

Advisory-only output remains:

```json
{
  "hookSpecificOutput": {
    "hookEventName": "...",
    "additionalContext": "..."
  }
}
```

Outcome metadata should carry:

- `kind`
- `eventName`
- `source`, for example `native-local`, `shared-hook`, `triage`, `compaction`, or `learning`
- `reason`
- `additionalContext`
- `stopReason`, for Stop-only continuation blocks
- `systemMessage`, when Codex should continue with a specific instruction
- `repeatSignature`, when an outcome must be de-duplicated
- `effectRefs`, linking to `NativeHookEffects`

### Outcome Merge And Precedence

Handlers may produce multiple outcomes. Merge rules must be deterministic:

1. Preserve malformed JSON handling as the outermost hard block.
2. `hard-block` wins over every other outcome.
3. `repair-block` wins over `review-block`, `continue-block`, and advisories.
4. `continue-block` wins over `review-block` during `Stop`.
5. `review-block` wins over advisories.
6. Advisories merge in source order after de-duplication.

When two blocking outcomes of the same precedence exist, keep the first local/native block as the primary `reason` and append later contexts with source attribution. Shared hook blocks should not erase a local Stop `stopReason`; they may add context and recovery instructions.

Stop-specific merge rules:

- `stopReason` belongs to the primary `continue-block`.
- `systemMessage` belongs to the primary Stop block unless a later hard block supersedes it.
- `repeatSignature` is computed from the primary Stop obligation and canonical session id.
- compaction, learning, and context-monitor results are advisory unless their shared hook result is a hard or repair block.
- repeated Stop blocks with the same signature should suppress duplicate output when the native payload indicates Stop hook re-entry.

## Event Responsibilities

### SessionStart

Purpose: restore enough context for the agent to resume correctly.

Responsibilities:

- reconcile native and canonical session ids
- emit bounded active-state summaries
- surface compact recovery cues
- avoid heavy validation and broad scanning

It should not block in normal operation.

### UserPromptSubmit

Purpose: prevent prompt-driven workflow bypass and improve route selection.

Responsibilities:

- run prompt guard when prompt text exists
- detect explicit workflow phase drift
- record keyword activation where needed
- produce advisory triage for no-keyword prompts
- refresh HUD/session prompt state as a best-effort side effect

Blocking should remain limited to explicit bypass or repeated phase drift. Triage should remain advisory.

### PreToolUse

Purpose: stop unsafe or invalid actions before execution.

Responsibilities:

- inspect `Bash` commands only when matched by the Codex hook matcher
- block sensitive or out-of-root read targets
- block invalid commit-message paths when enforcement applies
- block commands missing required execution context
- emit advisory context for high-risk destructive fixtures

This handler must be fast and deterministic.

### PostToolUse

Purpose: interpret the immediate tool result so the agent does not blindly retry or lose state.

Responsibilities:

- detect MCP transport failure
- classify hard Bash setup failures
- require review of informative non-zero command output
- merge learning and compaction advisory context when active workflow state exists
- suppress repeated identical advisories

PostToolUse should not become a general workflow judge.

### Stop

Purpose: prevent the agent from stopping when active obligations would be abandoned.

Responsibilities:

- detect active mode/team/skill obligations
- detect pending question obligations
- detect active workflow recovery obligations
- use strict repeat signatures to avoid stop loops
- merge context monitor, compaction, and learning signals

Stop blocks must be high confidence and session-scoped wherever possible.

## Refactor Plan

### Phase 1: Characterization And Types

Add tests or assertions around current output behavior where coverage is weak. Introduce internal types without changing behavior:

- `NativeHookContext`
- `NativeHookOutcome`
- `SharedHookClient`

Keep public exports such as `dispatchCodexNativeHook` stable for existing tests.

### Phase 2: Extract Event Modules

Move event-specific logic into separate modules:

- `native-session-start.ts`
- `native-user-prompt.ts`
- `native-tool-use.ts`
- `native-stop.ts`
- `native-shared.ts`
- `shared-hook-client.ts`

The extraction should be mechanical. Existing tests should continue to pass after each slice.

### Phase 3: Normalize Blocking Semantics

After extraction, annotate all blocks with internal outcome kinds while preserving Codex output. This enables later policy tuning without changing the native protocol.

### Phase 4: Performance And Noise Tuning

Only after behavior-preserving extraction:

- avoid shared hook calls when no active workflow exists
- cache active workflow discovery within one event
- set event-level budgets
- downgrade low-confidence blocks to advisory where evidence supports it
- strengthen Stop freshness checks

## Non-Goals For The First Implementation Pass

- Do not change `.codex/hooks.json` shape.
- Do not remove any managed hook event.
- Do not change Codex wire output JSON.
- Do not weaken existing safety or workflow enforcement.
- Do not replace `specify hook ...` spawning yet.
- Do not redesign `sp-*` workflows.
- Do not rewrite team or mode runtime behavior.

## Verification

Minimum verification before claiming the refactor is complete:

```text
cd extensions/agent-teams/engine
npm run test:native-hooks
```

Python-side compatibility checks:

```text
pytest tests/contract/test_hook_cli_surface.py tests/codex_team/test_sync_ecc_to_codex_scripts.py -q
```

If the implementation touches generated Codex integration behavior, also run:

```text
pytest tests/integrations/test_integration_codex.py tests/integrations/test_integration_subcommand.py -q
```

## Success Criteria

The refactor is successful when:

- current behavior remains test-compatible
- the CLI entry is thin
- each native event has a clear handler boundary
- shared hook invocation is centralized
- internal block kinds are explicit
- repeated context inference is reduced
- future performance tuning can be made without editing one giant event file

The result should make the hook more agent-native: fast enough to stay invisible, strict enough to prevent real drift, and structured enough that later policy tuning is safe.
