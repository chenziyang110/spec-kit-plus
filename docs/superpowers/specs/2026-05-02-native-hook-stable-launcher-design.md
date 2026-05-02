# Native Hook Stable Launcher Design

**Date:** 2026-05-02
**Status:** Proposed
**Owner:** Codex

## Summary

This design hardens the Python-backed native hook entry path used by generated
Claude and Gemini projects.

The approved direction is:

- keep shared workflow truth in the existing `specify hook ...` engine
- keep integration-specific dispatch logic in the existing Claude and Gemini
  hook adapter scripts
- stop writing machine-specific Python command names into generated native hook
  registrations
- introduce one shared project-local stable launcher surface under
  `.specify/bin/`
- resolve Python and launcher availability at runtime instead of at generation
  time
- make repair and diagnostics explicit when the runtime cannot find a valid
  interpreter or launcher

This is not a Go rewrite of the shared hook engine.

This is also not a direct replacement for the existing Claude or Gemini hook
adapter scripts. Those scripts still own host payload parsing and host-specific
response formatting.

## Problem Statement

The current generated Claude and Gemini hook registrations detect a Python
command during `specify init` and then write that command string directly into
the native hook configuration.

Today that can produce commands such as:

- `python3 .../.claude/hooks/claude-hook-dispatch.py ...`
- `python .../.gemini/hooks/gemini-hook-dispatch.py ...`

This is fragile across machines and operating systems because the project may
be initialized on one machine but executed on another where:

- the Python executable has a different name
- the preferred Python executable exists only inside a project-local `.venv`
- Windows supports `py` but not `python3`
- POSIX systems expose `python3` but not `python`
- PATH order or installation layout changes after initialization

The real failure mode is therefore not "the shared `specify hook ...` engine is
Python" but "the first native hook jump bakes in an interpreter choice too
early."

## Goals

- Eliminate machine-specific Python command names from generated Claude and
  Gemini native hook registrations.
- Preserve the existing Python shared hook core and the existing integration
  dispatch scripts.
- Introduce one stable project-local hook launcher contract that can be
  targeted by generated native hook configuration.
- Resolve launcher and interpreter availability at runtime using explicit,
  deterministic precedence rules.
- Make failure states actionable through diagnostics, repair guidance, and
  compatibility checks.
- Create a design that can later swap the internal launcher implementation
  without rewriting every integration's native hook registration format.

## Non-Goals

- Do not rewrite the shared `specify hook ...` engine in Go.
- Do not replace the Claude or Gemini dispatch scripts with a generic shared
  script.
- Do not duplicate workflow policy logic inside the launcher.
- Do not change the shared block, warn, or repair semantics already emitted by
  `specify hook ...`.
- Do not introduce a compiled binary distribution requirement in this phase.

## Current-State Assessment

### Shared Hook Core

The repository already centralizes hook truth in `src/specify_cli/hooks/` and
routes first-party workflow enforcement through `specify hook ...`.

This architecture is correct and should remain the source of truth.

### Claude and Gemini Adapter Layer

The generated Claude and Gemini assets each include a Python dispatch script:

- `.claude/hooks/claude-hook-dispatch.py`
- `.gemini/hooks/gemini-hook-dispatch.py`

These scripts already:

- parse host-specific payloads
- resolve project root
- invoke the shared `specify hook ...` engine
- translate shared outcomes back into host-specific native hook output

They are thin and correctly scoped. They should remain in place.

### Current Fragility

The fragility lives one level above those scripts.

During integration setup, the generated native hook command currently chooses a
Python executable name up front using detection logic such as:

- `python3`
- `python`
- `sys.executable` as a fallback during generation

That means the generated native hook command binds to the generator machine's
runtime assumptions rather than the execution machine's runtime reality.

## Approaches Considered

### 1. Stronger Inline Fallback Commands

Continue generating native hook commands directly, but make them longer and
smarter by embedding fallback chains for `python3`, `python`, `py`, and other
variants.

**Pros**

- minimal structural change
- no new project asset family

**Cons**

- platform-specific quoting and escaping get worse
- generated commands become harder to reason about and test
- every integration keeps owning its own startup fragility
- this still binds stability to command-string cleverness

### 2. Shared Stable Launcher Contract

Generate one shared project-local launcher surface and make Claude and
Gemini native hook registrations call that launcher instead of a specific
Python command.

**Pros**

- centralizes the unstable part of the system
- keeps existing host-specific dispatch scripts and shared hook core intact
- makes runtime resolution deterministic and testable
- provides a future seam for internal reimplementation without changing
  integration config formats

**Cons**

- adds a new generated asset family under `.specify/bin/`
- requires migration and repair handling for existing projects

### 3. Go Binary Launcher

Replace the first jump with a cross-platform compiled executable.

**Pros**

- avoids Python executable naming issues for the first jump
- strongest isolation from PATH naming differences

**Cons**

- adds packaging, architecture, release, and upgrade burden
- still does not remove the Python shared core dependency
- is significantly heavier than the failure mode requires today

## Recommendation

Adopt **Approach 2: Shared Stable Launcher Contract**.

It solves the actual problem while preserving the architecture that is already
working well:

- native adapters stay thin
- shared workflow truth stays centralized
- runtime resolution moves to execution time instead of generation time

This is the best long-term contract because future implementation changes,
including a possible Go launcher later, can happen behind the same stable
entrypoint without forcing native hook config changes across integrations.

## Approved Architecture

The design introduces a two-step entry path:

1. generated native hook config calls a shared project-local launcher entry
2. the launcher entry resolves a valid Python runtime and delegates to a shared
   Python launcher implementation
3. the shared Python launcher delegates to the existing integration dispatch
   script
4. the integration dispatch script preserves the existing shared-hook call path

### Stable Calling Chain

Claude:

```text
Claude native hook
-> .specify/bin/specify-hook claude <route>
-> runtime resolution
-> .specify/bin/specify-hook.py claude <route>
-> .claude/hooks/claude-hook-dispatch.py <route>
-> specify hook ...
```

Gemini:

```text
Gemini native hook
-> .specify/bin/specify-hook gemini <route>
-> runtime resolution
-> .specify/bin/specify-hook.py gemini <route>
-> .gemini/hooks/gemini-hook-dispatch.py <route>
-> specify hook ...
```

### Responsibility Split

- `.specify/bin/specify-hook*`
  - solves startup stability
  - resolves runtime availability
  - starts the shared Python launcher implementation

- `.specify/bin/specify-hook.py`
  - receives the normalized launcher arguments
  - dispatches to the right integration adapter
  - stays below the generated shell entrypoint and above the existing
    integration adapter scripts

- `.claude/hooks/claude-hook-dispatch.py`
  - parses Claude payloads
  - converts shared hook outcomes to Claude hook responses

- `.gemini/hooks/gemini-hook-dispatch.py`
  - parses Gemini payloads
  - converts shared hook outcomes to Gemini hook responses

- `specify hook ...`
  - remains the source of product policy truth

## File Layout

Generated projects should gain a shared hook launcher surface under
`.specify/bin/`.

Recommended generated assets:

- POSIX: `.specify/bin/specify-hook`
- Windows: `.specify/bin/specify-hook.cmd`
- Shared Python launcher: `.specify/bin/specify-hook.py`

The existing integration assets remain:

- `.claude/hooks/claude-hook-dispatch.py`
- `.gemini/hooks/gemini-hook-dispatch.py`

Repository source assets should live in a shared runtime-owned source location
under `src/specify_cli/` so both Claude and Gemini setup can install them as
generated runtime infrastructure.

## Runtime Resolution Contract

The launcher system has two separate resolution concerns:

1. **startup runtime resolution**
   - how the stable entrypoint finds a Python runtime capable of starting the
     shared launcher implementation
2. **shared hook core resolution**
   - how the existing integration dispatch scripts find the preferred
     `specify hook ...` command path once Python is already running

The design must keep these two concerns distinct.

### Startup Runtime Resolution Order

1. explicit runtime override from environment
2. project-local virtual environment Python
3. system-level Python fallback
4. hard failure with actionable diagnostics

### 1. Explicit Runtime Override

Highest-priority startup overrides should be dedicated to runtime selection,
not reused from the existing shared-hook core override surface.

Recommended new variables:

- `SPECIFY_HOOK_RUNTIME_ARGV`
- `SPECIFY_HOOK_RUNTIME_COMMAND`

These are intended for CI, constrained environments, or temporary operator
repair when the project needs to force a particular interpreter or runtime
entry form for the launcher itself.

### 2. Project-Local Virtual Environment

If the project contains a usable `.venv`, prefer it over generic PATH lookup.

This helps ensure the hook path follows the project's own runtime when
available.

### 3. System Python Fallback

System fallback remains platform-aware:

- Windows: prefer `py`, then `python`
- POSIX: prefer `/usr/bin/env python3`, then `/usr/bin/env python`

This fallback is runtime behavior, not a command string baked into generated
hook config.

### 4. Explicit Failure

If no valid Python runtime can be resolved for startup, the launcher must fail
clearly and actionably.

It should report:

- which startup resolution sources were attempted
- what failed
- how to repair the project

It should not silently downgrade into brittle behavior.

### Shared Hook Core Resolution

Once the shared Python launcher has started the integration dispatch script, the
existing shared-hook core resolution remains responsible for deciding how
`specify hook ...` itself is invoked.

That second-hop resolution should continue to prefer:

1. `SPECIFY_HOOK_ARGV` / `SPECIFY_HOOK_COMMAND`
2. persisted `specify_launcher` from `.specify/config.json`
3. project-local virtual environment Python
4. system-level Python fallback
5. hard failure with actionable diagnostics

This keeps the existing project-trusted launcher model intact while avoiding
the mistake of treating `specify_launcher` as the mechanism that solves the
very first jump into Python.

### Persisted Project Launcher

If `.specify/config.json` contains `specify_launcher`, the launcher should use
that as a trusted preferred source for the shared `specify hook ...` call path
after Python startup has already succeeded.

This preserves the repository's current "trusted launcher" model.

## Compatibility and Upgrade Path

### New Projects

`specify init` should generate shared launcher assets and wire Claude/Gemini
managed hook registrations to call the launcher.

### Existing Projects

`specify integration repair` should:

- install the shared launcher assets if missing
- rewrite managed Claude and Gemini native hook commands from direct
  `python ...dispatch.py` forms to `.specify/bin/specify-hook <integration>
  <route>` forms

### Diagnostics

`specify check` should detect stale managed hook registrations that still point
directly at interpreter-specific dispatch commands and report them as a stale
runtime surface requiring repair.

This prevents users from discovering the problem only at runtime.

## Failure Semantics

The launcher layer must distinguish between startup failures and shared policy
outcomes.

### Launcher-Level Failures

Examples:

- no usable Python runtime found for startup
- shared `specify_launcher` configured but unavailable after adapter startup
- target integration dispatch script missing

These should return explicit repair guidance such as:

- run `specify integration repair`
- re-run `specify init --here --force ...`
- repair `.venv`
- verify `py`, `python3`, or `python`

### Shared Hook Outcomes

If the launcher successfully starts the integration dispatch script, then the
existing `specify hook ...` block, warn, and repair semantics remain unchanged.

The launcher must not reinterpret product policy.

## Testing Strategy

### Unit Coverage

Add focused tests for:

- runtime resolution precedence
- project launcher loading
- `.venv` detection
- Windows command rendering
- POSIX command rendering
- missing runtime diagnostics

### Integration Coverage

Add or update tests to assert:

- generated Claude managed hook commands target the shared launcher
- generated Gemini managed hook commands target the shared launcher
- repair rewrites stale managed hook commands
- launcher assets are installed into generated projects
- missing runtime conditions produce actionable repair errors

### Regression Constraints

The change must not:

- break `.claude/hooks/claude-hook-dispatch.py`
- break `.gemini/hooks/gemini-hook-dispatch.py`
- change the existing `specify hook ...` output contract
- weaken existing project-launcher binding behavior

## Tradeoffs

This design adds one more generated layer, but that extra layer buys a cleaner
contract boundary:

- native hook config no longer owns interpreter selection
- host adapter scripts no longer need to be the place where startup policy is
  solved
- future runtime changes can happen behind one stable entrypoint

That trade is favorable because it removes the real source of cross-machine
startup drift while avoiding a premature compiled-runtime migration.

## Future Evolution

This design intentionally leaves room for later internal changes behind the
same stable launcher contract.

Possible future directions:

- replace the launcher internals with a Go binary if distribution economics
  later justify it
- expand the shared launcher concept to other Python-backed generated runtime
  helper surfaces
- add richer diagnostics and self-heal recommendations through `specify check`
  and `integration repair`

The critical rule is that future evolution should preserve the stable
project-local launcher contract once it ships.
