# Research: Codex Team Runtime Import

## Decision 1: Import the runtime stack into the repository instead of shelling out to an external install

**Decision**

Embed the oh-my-codex team/runtime implementation into `spec-kit-plus` source control and treat it as a maintained internal subsystem.

**Rationale**

- The user explicitly asked for the runtime to be brought into this project rather than referenced externally.
- External runtime dependency would break the first-release guarantee that `specify init --ai codex` projects get the capability by default.
- Embedded ownership gives the project direct control over Codex-specific product behavior, release cadence, and debugging.

**Alternatives considered**

- Depend on an installed external `omx` binary: rejected because it leaves first-release capability outside the repository boundary.
- Reimplement the runtime in Python: rejected because it changes the requested approach and would be an unrequested fallback architecture.

## Decision 2: Replace `omx` / `$team` with a `specify`-owned product surface

**Decision**

Use `specify` as the official command surface and generate Codex-facing skills around that surface instead of retaining `omx` / `$team` as the formal product entry point.

**Rationale**

- The user explicitly chose a `specify`-owned surface.
- A single product surface aligns with the repository’s current user model, where integrations are installed and managed through `specify`.
- This reduces future confusion when different AI integrations receive different capability subsets.

**Alternatives considered**

- Keep `omx team` and `$team`: rejected because it preserves upstream product identity instead of completing the import into `spec-kit-plus`.
- Ship both `specify` and `omx` surfaces equally: rejected because dual surfaces complicate docs, support, and acceptance criteria.

## Decision 3: Gate the entire capability to Codex for first release

**Decision**

Install and expose the embedded team/runtime only for `codex` integration paths in the first release.

**Rationale**

- The aligned scope requires that other AI integrations remain unaffected.
- Codex already uses a skills-first layout in this repository, which is the lowest-risk place to add the new surface.
- This creates a controlled boundary for later multi-agent adaptation work.

**Alternatives considered**

- Expose the runtime to all integrations immediately: rejected because it expands risk and contradicts the agreed first-release boundary.
- Hide the runtime globally but leave shared infrastructure behind every install: rejected because it still alters non-Codex project outputs.

## Decision 4: Keep `tmux` as a hard dependency with no silent fallback

**Decision**

The first release requires `tmux` and fails visibly when `tmux` is unavailable.

**Rationale**

- The imported runtime model is built around pane/session orchestration rather than optional terminal enhancement.
- The constitution forbids silent fallback when the requested implementation path is explicit.
- A visible failure is more supportable than a degraded pseudo-team mode that behaves differently from the imported design.

**Alternatives considered**

- Provide a single-process fallback: rejected as an unrequested behavioral substitution.
- Claim cross-platform parity without `tmux`: rejected as unverifiable within the agreed first-release scope.

## Decision 5: Treat existing Codex project upgrades as optional support

**Decision**

The first release guarantees new Codex projects and may include an upgrade path for existing Codex projects, but that upgrade path is not a release blocker.

**Rationale**

- This protects delivery focus while still acknowledging existing users.
- It prevents release readiness from being dominated by legacy edge cases before the new-path behavior is stable.
- It keeps migration guidance possible without turning it into a launch dependency.

**Alternatives considered**

- Require migration support for all existing Codex projects on day one: rejected because it widens release scope and raises uncertainty.
- Exclude any future upgrade path entirely: rejected because it would make later adoption unnecessarily difficult.
