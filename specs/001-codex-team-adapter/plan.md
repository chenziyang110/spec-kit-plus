# Implementation Plan: Codex Team Runtime Import

**Branch**: `001-codex-team-adapter` | **Date**: 2026-04-10 | **Spec**: [F:\github\spec-kit-plus\specs\001-codex-team-adapter\spec.md](F:\github\spec-kit-plus\specs\001-codex-team-adapter\spec.md)
**Input**: Feature specification from `/specs/001-codex-team-adapter/spec.md`

## Summary

Import the oh-my-codex team/runtime stack into `spec-kit-plus` as a source-controlled embedded subsystem, then expose it only through `specify`-owned Codex surfaces. The first release changes Codex initialization and command flow, keeps non-Codex integrations untouched, requires `tmux`, and must validate a near-complete runtime loop: bootstrap, dispatch, state tracking, failure signaling, and cleanup.

## Technical Context

**Language/Version**: Python 3.11+ for the existing CLI, plus an imported Node.js 20+ / TypeScript / Rust runtime subtree for the embedded team engine  
**Primary Dependencies**: `typer`, `rich`, `json5`, `pyyaml`, existing integration registry, imported tmux team/runtime assets, `tmux` as an operator dependency  
**Storage**: File-based project artifacts and runtime state under the project workspace; integration manifests remain hash-tracked in `.specify/integrations/`  
**Testing**: `pytest`, `typer.testing.CliRunner`, integration fixture projects, runtime smoke coverage in tmux-capable environments  
**Target Platform**: Spec Kit Plus CLI projects, with first-release runtime guarantees only for tmux-capable environments  
**Project Type**: CLI tooling product with generated agent assets and an embedded runtime subsystem  
**Performance Goals**: Codex initialization must remain interactive, unsupported-environment checks must fail fast in a single command invocation, and runtime bootstrap must be operator-usable without manual file surgery  
**Constraints**: No automatic fallback for missing `tmux`; no behavioral changes for non-Codex integrations; preserve reviewable/reversible delivery despite mixed-language import; first release must prove bootstrap, dispatch, state, failure, and cleanup  
**Scale/Scope**: One new Codex-only runtime capability lane, one embedded upstream-derived runtime subtree, and one release cycle focused on new Codex projects rather than mandatory migration of existing projects

## Input Risks From Alignment

- `specify`-owned command and skill names still need final naming decisions during planning and implementation.
- Missing-`tmux` messaging and operator interaction details still need explicit design, although the boundary is already fixed.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Specification-First Delivery**: PASS. Feature spec and alignment report exist and are sufficiently bounded.
- **Simplicity and Scope Discipline**: CONDITIONAL PASS. The imported runtime subtree is a complexity increase, but it is directly required by the user and limited to Codex-only first release scope.
- **Test-Backed Changes**: PASS WITH PLANNING REQUIREMENT. Plan includes integration and runtime validation before completion.
- **Security by Default**: PASS WITH DESIGN REQUIREMENT. Runtime state, generated skills, and operator messages must avoid unsafe fallbacks and secret leakage.
- **Reviewable, Reversible Delivery**: PASS WITH STRUCTURE REQUIREMENT. The imported runtime must be isolated into explicit directories and guarded by Codex-only installation boundaries.
- **Evidence Before Completion**: PASS. First-release acceptance explicitly requires runtime bootstrap, dispatch, state recording, failure signaling, and cleanup evidence.
- **No Unrequested Fallbacks**: PASS. The plan keeps `tmux` as a hard requirement and rejects automatic non-tmux fallback behavior.

## Project Structure

### Documentation (this feature)

```text
specs/001-codex-team-adapter/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── cli-surface.md
│   └── generated-assets.md
└── tasks.md
```

### Source Code (repository root)

```text
src/specify_cli/
├── __init__.py                    # existing CLI surface; add specify-owned team commands
├── integrations/
│   └── codex/                     # extend Codex install behavior and defaults
├── codex_team/                    # new Codex-only orchestration/install boundary
│   ├── __init__.py
│   ├── commands.py
│   ├── installer.py
│   ├── manifests.py
│   ├── runtime_bridge.py
│   └── state_paths.py
└── runtime_vendor/                # imported oh-my-codex-derived runtime subtree metadata/helpers

templates/
├── commands/                      # extend with Codex-owned team skill template if needed
└── [existing shared templates]

scripts/
├── bash/
├── powershell/
└── [runtime bootstrap/update helpers as needed]

tests/
├── integrations/                  # Codex install behavior and non-Codex isolation
├── codex_team/                    # new unit/integration coverage for command routing and manifests
└── contract/                      # generated asset and CLI contract tests
```

**Structure Decision**: Keep the existing Python CLI as the product shell, add a Codex-only orchestration package under `src/specify_cli/codex_team/`, and isolate imported upstream-derived runtime components behind a dedicated runtime vendor boundary. This keeps non-Codex integrations stable while making the new runtime reviewable and removable.

## Phase 0: Research & Decisions

### Research Goals

1. Confirm how to import upstream runtime capability without turning first release into an external dependency wrapper.
2. Decide the `specify`-owned command surface that replaces `omx` / `$team`.
3. Define Codex-only installation gates so non-Codex integrations remain unchanged.
4. Define the runtime state boundary, failure behavior, and release-time acceptance proof.
5. Confirm migration policy for existing Codex projects without making it a ship blocker.

### Phase 0 Output

- [F:\github\spec-kit-plus\specs\001-codex-team-adapter\research.md](F:\github\spec-kit-plus\specs\001-codex-team-adapter\research.md)

### Research Resolution Summary

- Vendor/import the upstream runtime into the repository instead of rewriting it in Python or depending on an external `omx` install.
- Replace `omx` / `$team` with a `specify`-owned command and generated Codex skill surface.
- Gate installation and visibility strictly inside Codex integration paths.
- Keep `tmux` as a hard dependency with explicit unsupported-environment messaging.
- Treat existing Codex project upgrades as optional support, not first-release blocking scope.

## Phase 1: Design & Contracts

### Data Model

- [F:\github\spec-kit-plus\specs\001-codex-team-adapter\data-model.md](F:\github\spec-kit-plus\specs\001-codex-team-adapter\data-model.md)

### Contracts

- [F:\github\spec-kit-plus\specs\001-codex-team-adapter\contracts\cli-surface.md](F:\github\spec-kit-plus\specs\001-codex-team-adapter\contracts\cli-surface.md)
- [F:\github\spec-kit-plus\specs\001-codex-team-adapter\contracts\generated-assets.md](F:\github\spec-kit-plus\specs\001-codex-team-adapter\contracts\generated-assets.md)

### Operator Quickstart

- [F:\github\spec-kit-plus\specs\001-codex-team-adapter\quickstart.md](F:\github\spec-kit-plus\specs\001-codex-team-adapter\quickstart.md)

### Design Decisions

1. **Product Surface**: Introduce a `specify`-owned team command surface and a Codex-generated team skill, rather than preserving `omx` / `$team` as the official surface.
2. **Capability Boundary**: Install and expose the new runtime only when the selected integration is `codex`.
3. **Runtime Boundary**: Keep the imported runtime subtree isolated so the Python CLI can call it without leaking cross-integration assumptions.
4. **State Boundary**: Preserve manifest-based installation tracking and introduce an explicit runtime-state contract for team sessions and dispatch records.
5. **Release Boundary**: Guarantee first-release behavior for new Codex projects only; treat existing project upgrades as optional migration support.

## Post-Design Constitution Check

- **Specification-First Delivery**: PASS. Design artifacts now map directly to the aligned spec.
- **Simplicity and Scope Discipline**: PASS WITH JUSTIFIED EXCEPTION. The imported subsystem is intentionally isolated and justified by explicit user direction.
- **Test-Backed Changes**: PASS. Quickstart and contracts define executable verification targets.
- **Security by Default**: PASS. No fallback runtime is introduced; unsupported environments fail visibly.
- **Reviewable, Reversible Delivery**: PASS. The design isolates new runtime logic to new directories and Codex-only wiring.
- **Evidence Before Completion**: PASS. Phase outputs define what must be proven before completion.
- **No Unrequested Fallbacks**: PASS. The design keeps explicit `tmux` dependency and avoids hidden degraded modes.

## Implementation Phases

### Phase 2 Preview - Delivery Lanes

1. **Embedded Runtime Lane**
   - Import upstream runtime assets into an isolated vendor boundary.
   - Define bridge points from Python CLI into the embedded runtime.

2. **Codex Integration Lane**
   - Extend Codex integration installation to generate the new team surface.
   - Keep `.agents/skills` and `AGENTS.md` updates Codex-only.

3. **CLI Surface Lane**
   - Add `specify`-owned team commands and operator messages.
   - Add unsupported-environment detection and explicit failure paths.

4. **Verification Lane**
   - Add integration and contract tests for Codex install behavior.
   - Add tmux-capable runtime smoke verification for bootstrap, dispatch, state, failure, and cleanup.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Mixed-language imported runtime subtree | The user explicitly wants the oh-my-codex stack brought into this repository rather than replaced with a lighter approximation | Python-only rewrite would violate the requested approach and create an unrequested fallback architecture |
| New Codex-only orchestration package | The imported runtime must be isolated from the existing generic integration layer | Wiring everything through `__init__.py` alone would create unreviewable coupling and higher regression risk for other integrations |
