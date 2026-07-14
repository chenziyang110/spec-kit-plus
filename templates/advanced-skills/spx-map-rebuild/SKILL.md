---
name: spx-map-rebuild
description: Project-cognition rebuild orchestrator for advanced coding models. Use when a full rebuild is required and the independent scan then deterministic build skills should run in sequence.
---

# SPX Map Rebuild

Read `references/project-cognition.md` for its evidence boundary and
`references/rebuild-gates.md`. Do not run Compass intake against a missing or
invalid baseline. This is a convenience orchestrator, not a replacement for
either phase.

Confirm rebuild necessity with
`{{specify-subcmd:project-cognition status --format json}}`. A localized stale
route belongs in `$spx-map-update`.

Run `$spx-map-scan` to completion. Preserve its hard stop: a validated scan is
not a published baseline. Only after scan readiness passes, run
`$spx-map-build`, which consumes that frozen evidence and performs deterministic
construction and validation without a second model-driven repository read.

If either phase blocks, preserve its workbench and report the phase-local
recovery action. Do not skip validation, merge the phase write boundaries, or
claim rebuild completion from scan coverage alone.
