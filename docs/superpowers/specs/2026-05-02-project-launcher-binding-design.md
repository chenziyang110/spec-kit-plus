# Project Launcher Binding Design

**Date:** 2026-05-02  
**Status:** Proposed  
**Scope:** Project-local launcher persistence, generated workflow templates, runtime hook adapters, CLI diagnostics, and regression coverage  
**Primary goal:** Ensure generated Spec Kit workflows and first-party runtime surfaces invoke the same trusted `specify` source that initialized the project instead of silently falling back to an older PATH entry

## Problem

Spec Kit Plus already documents a real upgrade hazard:

- a developer machine can have multiple `specify` executables
- an older `specify.exe` can appear earlier on PATH
- `specify version` is not a reliable differentiator for development builds
- `uvx --refresh --from git+... specify ...` is often the only trustworthy way to force the latest fork

The current product surface only partially contains that risk.

What already exists:

- `specify init` can persist a source-bound `specify_launcher` into `.specify/config.json`
- Claude and Gemini native hook adapters already read that launcher before falling back to PATH
- docs already warn users about PATH pollution during install and upgrade

What is still unsafe:

- generated workflow templates still contain many bare `specify ...` execution instructions
- shared template guidance in `templates/commands/**`, `templates/command-partials/**`, and `src/specify_cli/integrations/base.py` still implies that PATH `specify` is an acceptable runtime default
- internal workflow execution can therefore drift back to an old global CLI even when project initialization used the latest source-bound launcher

This creates a split-brain failure mode:

1. project files are initialized from the latest checkout
2. generated workflows later invoke an older global `specify`
3. the visible workflow surface looks current, but the runtime command surface is stale

That is a real correctness risk, not just a documentation bug.

## Goals

- Bind generated first-party runtime execution to the project-trusted launcher when one exists
- Eliminate high-risk bare `specify` runtime instructions from generated workflow surfaces
- Reuse one shared launcher abstraction across templates, runtime adapters, and diagnostics
- Preserve existing canonical workflow-state tokens and command-surface semantics
- Add explicit diagnostics for launcher drift, PATH conflicts, and missing launcher state
- Keep the fix cross-integration by default rather than Claude/Gemini-only

## Non-Goals

- Renaming the `specify` CLI or the canonical `sp-*` workflow names
- Replacing canonical workflow-state tokens such as `/sp.plan` or `next_command`
- Persisting machine-local absolute interpreter paths into project state
- Migrating all historical projects automatically without a refresh or re-init
- Cleaning up every low-signal historical `specify` mention in archival design docs
- Changing the user-facing invocation syntax projection work added by command-surface semantics

## Decision Summary

Use a project-level launcher abstraction as the shared truth source, then project all first-party runtime CLI calls through that abstraction.

The solution has four parts:

1. Keep `.specify/config.json` `specify_launcher` as the project-trusted launcher source
2. Extend `src/specify_cli/launcher.py` from a write-helper into a reusable launcher subsystem
3. Replace high-risk bare `specify ...` runtime calls in generated templates and integration guidance with launcher-aware placeholders
4. Strengthen runtime fallback behavior and `specify check` so stale CLI execution is detected and surfaced explicitly

## Approaches Considered

### Approach A: Diagnostics only

Add stronger `specify check` warnings and documentation, but leave generated runtime calls unchanged.

**Pros**

- smallest code change
- minimal regression risk

**Cons**

- detects the problem without preventing it
- stale PATH entries can still be used by generated workflows
- does not protect runtime correctness

**Decision**

Rejected. Detection without execution binding is not enough.

### Approach B: Inline the resolved launcher command directly into generated templates

Render a concrete launcher command string into every generated workflow instruction at init time.

**Pros**

- solves most of the direct runtime-path problem
- simple mental model for generated assets

**Cons**

- spreads quoting and platform rendering logic across template surfaces
- hard to reuse in hook adapters and diagnostics
- encourages string-level duplication instead of a shared launcher abstraction

**Decision**

Rejected as the primary architecture. Useful as an implementation technique inside a shared renderer, but not as the system boundary.

### Approach C: Project launcher abstraction plus template projection

Persist a project-trusted launcher, expose shared rendering helpers, and make first-party runtime surfaces consume that abstraction.

**Pros**

- fixes the root cause rather than only warning about it
- reusable across templates, runtime adapters, and diagnostics
- preserves cross-integration consistency
- keeps canonical workflow tokens unchanged

**Cons**

- larger change surface than diagnostics-only
- requires shared template and test updates

**Decision**

Accepted.

## Architecture

### Trusted Launcher Source

The trusted project launcher remains:

- `.specify/config.json`
- key: `specify_launcher`

This is the project-local truth about which command should be preferred when first-party runtime surfaces need to invoke the Spec Kit CLI.

The launcher is only persisted when it is portable and source-bound enough to be meaningful across project consumers. A portable `uvx --from git+... specify` form is acceptable. A machine-specific absolute interpreter path is not.

### Shared Launcher Subsystem

`src/specify_cli/launcher.py` currently:

- resolves a best-effort source-bound launcher during init
- writes `specify_launcher` into project config

It should be extended into the shared launcher subsystem for:

- reading project launcher config
- validating launcher payload shape
- rendering operator-readable command strings
- composing full launcher-backed subcommands
- providing template-ready replacement values
- centralizing fallback policy

This keeps command construction, validation, and quoting rules out of templates and out of per-integration duplicate logic.

### Execution Classification

Not every mention of `specify` needs the same enforcement policy. The design distinguishes between:

#### Strong-consistency execution surfaces

These surfaces are actually expected to invoke the CLI during project runtime and therefore must not silently drift to a stale PATH entry:

- native hook adapters
- runtime bridge helpers
- first-party generated instructions that tell the agent to execute `specify hook ...`, `specify learning ...`, `specify result ...`, or `specify testing inventory ...`
- other internal first-party command surfaces that re-enter the CLI

When a valid project launcher exists, these surfaces must prefer it. Silent fallback to a bare PATH `specify` is not acceptable here.

#### Weak-consistency guidance surfaces

These surfaces explain the system but do not directly execute it:

- general docs
- narrative guidance
- operator-facing explanations of workflow concepts

These surfaces do not need to fail fast, but they must stop implying that bare PATH `specify` is automatically trustworthy inside generated projects.

## Template Authoring Model

The command-surface semantics work already separated canonical workflow-state tokens from user invocation syntax. This design adds a third distinction for CLI re-entry:

1. canonical workflow-state tokens
2. user invocation syntax
3. trusted project CLI launcher

These must not be conflated.

### Canonical Workflow-State Tokens

Examples:

- `/sp.plan`
- `/sp.tasks`
- `next_command: /sp.plan`

These remain unchanged. They are protocol and artifact state, not shell commands.

### User Invocation Syntax

Examples:

- `$sp-plan`
- `/sp-plan`
- `/skill:sp-plan`
- `/sp.plan`

These are chat or skill invocation surfaces and remain governed by the existing `{{invoke:*}}` projection rules.

### Trusted Project CLI Launcher

Examples:

- `uvx --refresh --from git+https://github.com/chenziyang110/spec-kit-plus.git specify`
- `uvx --from git+https://github.com/chenziyang110/spec-kit-plus.git@abc123 specify`

This is the command prefix that first-party runtime instructions should use when they need to run CLI subcommands inside a project.

## Template Projection Mechanism

Add shared launcher-aware placeholders to the template pipeline.

Recommended minimum placeholder family:

- `{{specify-cli}}`
  - renders the trusted project launcher prefix for display
- `{{specify-subcmd:<args>}}`
  - renders a full launcher-backed command line

Examples:

- `{{specify-subcmd:hook validate-state --command plan --feature-dir "$FEATURE_DIR"}}`
- `{{specify-subcmd:learning start --command plan --format json}}`
- `{{specify-subcmd:result path}}`
- `{{specify-subcmd:testing inventory --format json}}`

This keeps the shared templates declarative while centralizing rendering policy in Python.

## Fallback and Failure Policy

### Priority Order

When a first-party runtime surface needs to invoke Spec Kit:

1. project launcher from `.specify/config.json`
2. explicit environment override intended for runtime injection
3. controlled source-aware fallback such as `python -m specify_cli`, but only when the current process can prove it is operating in the intended source/install context
4. bare `specify` on PATH only as a last-resort compatibility path, and never silently in strong-consistency execution surfaces

### Missing Launcher

If the project has no `specify_launcher`:

- do not persist a machine-local absolute interpreter path as a replacement
- surface that the project is in compatibility mode
- recommend re-running `specify init --here --force ...` from a trusted launcher source when launcher binding is required

For strong-consistency execution surfaces, compatibility mode may still be too risky. Those surfaces may warn or block depending on whether a safe fallback exists.

### Invalid Launcher

If launcher config is malformed, empty, or references an unavailable executable:

- treat this as a real configuration problem
- do not silently collapse to PATH `specify`
- emit a structured error or warning that identifies the broken launcher state

### Strong-Consistency Surfaces

For:

- native hooks
- runtime-managed result submission helpers
- other first-party internal execution channels

the default behavior should move from "run something if possible" to "prefer correctness of launcher binding, fail loudly when that correctness cannot be preserved."

## Code Changes

### 1. `src/specify_cli/launcher.py`

Expand it from a persistence helper into the central launcher module.

Responsibilities:

- read project config launcher
- validate launcher payload shape
- render launcher command strings
- compose full argv for subcommands
- expose helper APIs used by template processing
- expose helper APIs used by hook/runtime adapters

### 2. `src/specify_cli/integrations/base.py`

Replace hardcoded high-risk strings such as:

- `specify hook ...`

with launcher-aware shared guidance so generated integrations stop reintroducing the bare PATH assumption through shared prose.

### 3. `templates/commands/**`

Replace high-risk runtime CLI instructions that currently use bare `specify`:

- `specify hook ...`
- `specify learning ...`
- `specify result ...`
- `specify testing inventory ...`

These are the highest-priority execution-risk surfaces.

### 4. `templates/command-partials/**`

Replace shared partial content that emits the same high-risk patterns, especially:

- `common/learning-layer.md`
- `test-scan/shell.md`
- any shared partials that describe hook, learning, result, or testing CLI re-entry

This is required so individual commands do not regress through shared includes.

### 5. Native Hook Adapters

Claude and Gemini adapters already read `specify_launcher`. They should be tightened so that strong-consistency execution uses explicit launcher correctness rules rather than permissive silent fallback.

The goal is not to remove all fallback paths. The goal is to stop stale PATH execution from looking like a safe success path.

### 6. CLI Diagnostics

Enhance `specify check` to detect:

- multiple `specify` entries on PATH
- missing project launcher in the current project
- mismatch between PATH-first `specify` and the project launcher
- missing key command surfaces that indicate an older CLI is being used

Remediation should be explicit and action-oriented rather than generic.

## Files and Surfaces In Scope

### High-priority source surfaces

- `src/specify_cli/launcher.py`
- `src/specify_cli/__init__.py`
- `src/specify_cli/integrations/base.py`
- `src/specify_cli/integrations/claude/hooks/claude-hook-dispatch.py`
- `src/specify_cli/integrations/gemini/hooks/gemini-hook-dispatch.py`

### High-priority template surfaces

- `templates/commands/**`
- `templates/command-partials/**`

### High-priority docs

- `README.md`
- `docs/quickstart.md`
- `docs/upgrade.md`

## Out of Scope for First Delivery

- Eliminating every historical archival mention of bare `specify`
- Auto-migrating already-generated projects without a refresh
- Converting every weak-consistency documentation sentence into launcher-specific prose in one pass
- Changing workflow-state artifact formats

## Testing Strategy

### Launcher Unit Tests

Extend launcher tests to cover:

- reading valid project launcher config
- invalid launcher payloads
- full subcommand rendering
- display command rendering
- portable source-bound launcher persistence
- refusal to persist unportable machine-local launcher state

### Template Contract Tests

Add regression tests that scan high-risk generated template surfaces and fail if they contain bare runtime calls such as:

- `specify hook`
- `specify learning`
- `specify result`
- `specify testing inventory`

This should be limited to the execution-risk surfaces so the test is precise rather than noisy.

### Integration Generation Tests

Verify generated command/skill outputs are launcher-aware where they previously recommended bare runtime CLI calls.

### Hook Adapter Tests

Cover:

- project launcher present and valid
- launcher missing
- launcher malformed
- launcher executable unavailable
- fail-fast or warning behavior for strong-consistency execution

### Documentation Tests

Extend existing guidance-doc tests so they distinguish:

- install or upgrade commands that intentionally use `uvx --refresh --from ... specify`
- generated project runtime guidance that must no longer imply bare `specify` is the trusted internal entry

## Rollout Plan

### Phase 1: Launcher Infrastructure

- extend `launcher.py`
- add template rendering support for launcher-aware placeholders
- preserve current init-time launcher persistence behavior

### Phase 2: High-Risk Template Migration

- migrate hook, learning, result, and testing inventory runtime instructions
- update shared partials and shared integration guidance

### Phase 3: Runtime and Diagnostics Hardening

- tighten native hook adapter fallback behavior
- enhance `specify check`
- update upgrade and runtime troubleshooting docs

### Phase 4: Regression Lock

- add template contract tests
- expand launcher tests
- update integration and hook tests

## Acceptance Criteria

- When a project contains a valid `specify_launcher`, first-party runtime execution surfaces prefer it over bare PATH `specify`
- High-risk generated workflow surfaces no longer emit bare `specify hook|learning|result|testing inventory` runtime instructions
- Claude and Gemini native hooks do not silently fall back to an older PATH `specify` when a valid project launcher is available
- `specify check` reports launcher drift and multi-entry PATH conflicts explicitly
- Documentation clearly separates:
  - how to install or upgrade the CLI
  - how runtime behavior inside a generated project stays bound to the trusted launcher

## Risks

### Quoting and Cross-Platform Rendering

Launcher-backed command rendering must be safe for both PowerShell and POSIX-oriented guidance. The implementation should centralize rendering rules rather than duplicating them in templates.

### Over-Blocking Old Projects

Some older projects will not have `specify_launcher`. The first delivery must distinguish between:

- safe compatibility mode with explicit warning
- unsafe silent fallback

Blocking should be reserved for strong-consistency execution surfaces where stale execution is worse than interruption.

### Documentation Drift

If the runtime rules change without matching test coverage, shared docs and generated guidance can diverge again. Template and doc contract tests are therefore part of the design, not optional polish.

## Open Questions Resolved

### Should the project store an absolute local interpreter or venv path?

No. That makes the project state machine-specific and undermines portability.

### Is this only a Claude/Gemini hook fix?

No. The hook adapters are one symptom boundary, but the design is intentionally cross-CLI and shared-template-first.

### Should canonical workflow-state tokens change?

No. This problem is about runtime CLI launcher binding, not workflow-state token design.

## Recommendation

Implement the shared launcher abstraction first, then migrate the high-risk template surfaces, then harden runtime fallback behavior and diagnostics.

That order fixes the actual stale-CLI execution risk while preserving the existing command-surface semantics and keeping the solution reusable across integrations.
