# CLI Install Path and Passive Skills Alignment

**Date:** 2026-05-10
**Status:** Proposed
**Owner:** Codex

## Summary

This design aligns a bounded set of downstream CLI install locations with the
current `github/spec-kit` baseline while preserving one deliberate product
fork:

- `agy` should install skills into `.agents/skills`
- `cursor-agent` should install skills into `.cursor/skills`
- `trae` should install skills into `.trae/skills`
- `vibe` should install skills into `.vibe/skills`
- `codex` should remain on `.codex/skills`

The work is not just a config-table edit.
In this repository, install locations are consumed by:

- integration config and registrar metadata
- init-time messaging and path reporting
- skills directory discovery helpers
- extension skill registration and cleanup
- preset installation and overwrite flows
- passive skill installation and verification tests
- user-facing documentation that teaches downstream layout

The approved direction is a minimal, high-confidence synchronization:

1. update only the four targeted integrations to the new install locations
2. keep `codex` intentionally unchanged
3. do a repo-wide audit of passive-skill installation and fix only real misses
4. guarantee correctness for newly initialized projects only
5. do not add legacy-path compatibility, dual-write behavior, or migration code

## Problem

The current repository contains a drift between `spec-kit-plus` and the current
`github/spec-kit` downstream install layout for several integrations.

That drift is visible in at least three ways:

1. some integrations still scaffold workflow surfaces into older command,
   prompt, or rule directories instead of the current skills directories
2. some code paths that discover or manipulate skills directories may miss
   downstream projects after a path move unless they are updated together
3. passive skill coverage is uneven across integrations, which creates a risk
   that a path migration appears correct at init time but still fails to copy,
   update, detect, or clean up passive bundled skills in later flows

The user-facing consequence is a product inconsistency:

- the repository documents one install model in places
- some integrations still scaffold another
- some secondary flows may assume old paths
- passive skill behavior can silently differ by integration

This design solves that specific alignment problem without expanding into a
general integration architecture rewrite.

## Goals

- Align new downstream installs for `agy`, `cursor-agent`, `trae`, and `vibe`
  to the current expected skills directories.
- Preserve `codex` on `.codex/skills` as an intentional local product choice.
- Audit passive-skill installation behavior across all integrations and fix
  only verified misses.
- Ensure extension and preset flows continue to work for the moved
  integrations in newly initialized projects.
- Update tests and docs so the new downstream layout is explicit and enforced.

## Non-Goals

- Do not migrate `codex` to `.agents/skills`.
- Do not add `copilot` skills mode in this round.
- Do not preserve old-directory compatibility for the moved integrations.
- Do not dual-write old and new directories.
- Do not add an old-project migration command or path auto-rewriter.
- Do not refactor the entire skills-path system into a new abstraction unless a
  small local change is required to make the approved path moves safe.

## Approved Scope

### Integrations That Must Change

- `agy`: `.agent/skills` -> `.agents/skills`
- `cursor-agent`: `.cursor/commands` -> `.cursor/skills`
- `trae`: `.trae/rules` -> `.trae/skills`
- `vibe`: `.vibe/prompts` -> `.vibe/skills`

### Integrations That Must Not Change

- `codex`: stays on `.codex/skills`
- `copilot`: stays on default `.github/agents` behavior in this round

### Behavioral Scope

The implementation must make newly initialized downstream projects correct.

This means:

- init output goes to the approved new directory
- workflow skills are installed there
- passive skills are installed there
- extension skills can be registered there
- preset updates can discover and write there

This design does not require old directories to keep working after the move.

## Key Product Decision

This should be implemented as a `minimal synchronization pass`, not as a
shared-system rewrite and not as an upstream wholesale transplant.

Three approaches were considered.

### Option 1: Minimal Synchronization Pass

- update only the four targeted integration paths
- audit passive-skill behavior across all integrations
- patch only real misses in shared helpers, tests, or docs
- preserve the local `codex` fork

### Option 2: Shared Skills-Path Refactor

- redesign shared path derivation and directory discovery more broadly
- normalize all skills-based integrations around a stronger central helper

### Option 3: Upstream Port With Local Reverts

- import the nearest upstream implementation behavior broadly
- then selectively revert `codex` and any other undesired deltas

The approved direction is Option 1.

Option 2 is too large for the current problem and increases regression risk.
Option 3 increases the chance of pulling in unrelated behavior changes.
Option 1 directly addresses the concrete install-path and passive-skill problem
with the smallest safe change surface.

## Architecture

The work should be implemented as four coordinated layers.

### 1. Integration Definition Layer

The first source of truth is the integration-specific path metadata.

For each moved integration, update:

- `config["folder"]`
- `config["commands_subdir"]`
- `registrar_config["dir"]`

The goal is for every downstream install-path computation that already derives
from integration config to automatically follow the new location.

This layer must only change the four approved integrations.

### 2. Skills Directory Discovery Layer

The second layer is the helper logic that resolves a skills directory later in
the lifecycle.

Important consumers include:

- `src/specify_cli/__init__.py::_get_skills_dir`
- `src/specify_cli/extensions.py` skills-directory discovery
- `src/specify_cli/presets.py` skills-directory discovery

These flows must resolve the new locations for the moved integrations without
adding legacy compatibility behavior.

The preferred implementation rule is:

- where path discovery already derives from integration config, keep using that
- where a fallback candidate list is required, include the current desired
  paths and remove assumptions that only the old layout matters

This layer must stay bounded.
It is not a license to redesign the full discovery system.

### 3. Passive Skills Alignment Layer

The third layer is passive-skill coverage.

`SkillsIntegration.setup()` already installs passive bundled skills into the
resolved skills directory. The main risk is not the base installer itself.
The main risk is every other flow that assumes a skills directory exists at an
older location, or forgets to operate on some integrations entirely.

This layer requires a full audit across integrations for:

- initial passive-skill install
- extension skill registration
- extension skill cleanup
- preset overwrite and backfill behavior
- test expectations that assert passive-skill presence

The rule for this audit is strict:

- fix only verified misses
- do not churn integrations that already behave correctly
- do not rewrite passive-skill infrastructure for style reasons

### 4. Contract Proof Layer

The fourth layer is the proof surface.

Any path move that is not enforced by tests and explained in docs will drift
again.

This layer must cover:

- integration config assertions
- skills-destination assertions
- CLI initialization assertions
- passive-skill presence assertions
- extension and preset behavior where affected
- docs that explicitly teach downstream locations

## Detailed Change Surface

### Code Surfaces

Primary runtime surfaces expected to change:

- `src/specify_cli/integrations/agy/__init__.py`
- `src/specify_cli/integrations/cursor_agent/__init__.py`
- `src/specify_cli/integrations/trae/__init__.py`
- `src/specify_cli/integrations/vibe/__init__.py`
- `src/specify_cli/__init__.py`
- `src/specify_cli/extensions.py`
- `src/specify_cli/presets.py`

Other shared surfaces should change only if the audit proves they consume the
old paths directly.

### Test Surfaces

Expected test movement includes:

- integration-specific path assertions
- shared skills-base tests
- CLI initialization tests
- extension skill tests
- preset tests
- passive-skill installation assertions

The verification goal is not broad snapshot churn.
The verification goal is to prove that the four moved integrations now behave
correctly and that `claude` and `codex` still behave correctly.

### Documentation Surfaces

Expected documentation updates include:

- `README.md`
- `AGENTS.md`
- any integration reference text that explicitly names downstream directories

Docs must describe the intended layout after the change:

- `claude -> .claude/skills`
- `codex -> .codex/skills`
- `agy -> .agents/skills`
- `cursor-agent -> .cursor/skills`
- `trae -> .trae/skills`
- `vibe -> .vibe/skills`

## Passive Skills Audit Rules

The passive-skills audit should use the following classification.

### `correct`

The integration:

- installs passive bundled skills into the expected skills directory
- can be discovered by follow-on flows that operate on skills directories
- does not need any code change

### `missed-path-consumer`

The integration installs into the right place after a path move, but another
consumer still reads or writes the old path.

Examples:

- extension skills registered into the wrong directory
- preset updates targeting a stale path
- tests still asserting the old location

These must be fixed.

### `non-skills-integration`

The integration is command-, prompt-, or agent-file based and does not install
passive bundled skills as a skills integration.

These do not require forced conversion in this round.

## Acceptance Criteria

The implementation is complete only when all of the following are true.

1. A new project initialized for `agy` installs workflow and passive skills
   into `.agents/skills`.
2. A new project initialized for `cursor-agent` installs workflow and passive
   skills into `.cursor/skills`.
3. A new project initialized for `trae` installs workflow and passive skills
   into `.trae/skills`.
4. A new project initialized for `vibe` installs workflow and passive skills
   into `.vibe/skills`.
5. `codex` still installs workflow and passive skills into `.codex/skills`.
6. `claude` still installs workflow and passive skills into `.claude/skills`.
7. Extension skill registration and cleanup continue to work for moved
   integrations in newly initialized projects.
8. Preset skill discovery and update flows continue to work for moved
   integrations in newly initialized projects.
9. No legacy compatibility path logic or dual-write behavior is added for the
   moved integrations.
10. Tests and docs match the approved install locations.

## Verification Plan

The implementation should be verified in this order.

1. Run targeted integration tests for the four moved integrations.
2. Run shared skills-base tests that cover passive bundled skills.
3. Run CLI/init tests that assert downstream install locations.
4. Run extension and preset tests that exercise skills-directory discovery.
5. Run regression coverage for `claude` and `codex`.

If a failure appears outside those paths, only expand scope when the failure is
causally tied to the moved install locations or passive-skill audit.

## Risks

### Risk 1: Hidden Path Consumers

Some code paths may not define the directory themselves, but may still assume a
specific old layout in tests, cleanup flows, or fallback discovery code.

Mitigation:

- audit all skills-directory discovery and candidate-path logic
- update hard-coded assertions to derive from integration config where possible

### Risk 2: Passive-Skill False Confidence

An integration can appear fixed because the main workflow skills install in the
new directory while passive-skill follow-on flows still miss it.

Mitigation:

- verify passive bundled skills explicitly in the moved integrations
- verify extension and preset flows in addition to init

### Risk 3: Accidental Codex Drift

Because upstream currently uses `.agents/skills` for Codex, broad path
normalization work could accidentally drag `codex` away from the local product
decision.

Mitigation:

- keep `codex` called out explicitly in tests and docs as a protected local
  fork
- reject any implementation that changes `codex` path behavior in this round

## Open Questions Resolved

- `codex` should not be aligned to upstream in this round.
- `copilot` skills mode should not be added in this round.
- passive skills should be audited across all integrations, but code should
  change only where a real miss is found.
- compatibility strategy is new-project-only; old layouts are not preserved.

## Implementation Readiness

This design is ready for implementation planning.

The implementation plan should preserve the same boundaries:

- move only `agy`, `cursor-agent`, `trae`, and `vibe`
- keep `codex` unchanged
- audit passive skills repo-wide, but patch only verified misses
- validate new-project behavior only
