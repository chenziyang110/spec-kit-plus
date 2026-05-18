# Project Cognition Advisory Map Design

## Summary

Project cognition remains a valuable brownfield navigation system, but it must no longer act as a hard gate for ordinary work. `sp-map-scan`, `sp-map-build`, `project-cognition lexicon`, `project-cognition query`, and `sp-map-update` continue to exist and keep their normal purpose: they help agents find likely owners, affected paths, risks, verification routes, and maintenance context.

The policy change is that map freshness and rebuild/update heuristics stop controlling whether a workflow may proceed. The map points the agent toward evidence; it is not evidence by itself. Technical claims must be backed by live project sources such as code, tests, scripts, configuration, or authoritative documentation.

## Problem

The current project cognition contract treats the runtime as a hard pre-source gate and a runtime truth surface. That creates repeated interruptions in ordinary workflows:

- `needs_update`, `needs_rebuild`, `stale`, and `possibly_stale` states can stop unrelated work.
- Agents route back to `sp-map-update` or `sp-map-scan -> sp-map-build` even when live code inspection would be faster and more reliable.
- Validation and freshness heuristics are useful but not precise enough to be mandatory workflow routing decisions.
- The result is a loop where agents spend too much effort proving the map is fresh instead of using it as a reference and proving conclusions from code.

## Goals

- Keep project cognition scanning, building, querying, and updating available.
- Make project cognition an advisory index, not a workflow-blocking source of truth.
- Replace complex readiness-driven routing with basic usability checks.
- Require code-backed evidence for technical conclusions.
- Recommend map maintenance after relevant work, without making it a completion blocker.
- Make `sp-map-update` useful as a fast bounded maintenance path, including subagent-backed update lanes when appropriate.

## Non-Goals

- Do not remove `sp-map-scan`, `sp-map-build`, `sp-map-update`, or project cognition query commands.
- Do not redesign the SQLite graph schema.
- Do not prevent users from explicitly asking for a full map refresh.
- Do not make agents ignore project cognition when it is available and useful.

## Design

### Map Role

Project cognition becomes an advisory project map:

- It can suggest likely affected files, concepts, owners, risks, and verification routes.
- It can reduce broad repository search by proposing likely live reads.
- It can record known unknowns and partial coverage.
- It cannot alone prove a technical claim, architectural claim, dependency claim, or completion claim.

The governing rule is: map points, code proves.

### Basic Usability Check

Workflows should perform only a small project cognition usability check before consuming the map:

- Status and database files exist when expected.
- JSON and SQLite files are readable.
- Schema and contract versions are basically compatible.
- `lexicon` and `query` can return structurally valid payloads.

If that check fails, the workflow records that project cognition is unavailable or degraded and proceeds through live repository inspection. It should not stop to demand `sp-map-update` or `sp-map-scan -> sp-map-build` unless the user explicitly asked to repair the map first.

### Readiness States

Readiness states such as `needs_update`, `needs_rebuild`, `stale`, and `possibly_stale` are no longer hard workflow routing states for ordinary work.

They may still appear in diagnostics, logs, or map maintenance tools, but downstream workflows should interpret them as map quality hints:

- Use usable map output as a starting point.
- Cross-check all relevant facts against live source files.
- If map output looks wrong or incomplete, expand live reads rather than stopping.
- Mention map maintenance as follow-up when the work materially changes surfaces the map is meant to describe.

### Workflow Behavior

For ordinary `sp-*` workflows:

- Try project cognition as an optional first navigation pass.
- If project cognition is usable, consume its route hints and minimal live reads.
- If project cognition is degraded, skip map-driven routing and inspect the repository directly.
- Do not block planning, implementation, debugging, or review solely because the map asks for update or rebuild.
- Do not call `complete-refresh`, `validate-build`, or `mark-dirty` as a routine requirement of artifact-only work.

### Completion Behavior

When a completed task changes structural, workflow, template, API, verification, runtime, or ownership surfaces, the workflow should recommend maintaining the map:

```text
Project cognition may be stale for the changed surfaces. Recommended follow-up: run sp-map-update with the changed paths.
```

This recommendation is advisory. The task can still complete when source-level verification is complete.

### Map Update

`sp-map-update` remains the preferred maintenance path after normal work. It should be framed as fast map hygiene, not a prerequisite for completing the task that discovered stale map coverage.

`sp-map-update` may use subagents for bounded independent update lanes:

- changed path indexing
- affected owner/consumer updates
- verification route updates
- template or generated-surface propagation updates
- known-unknown and minimal-live-read maintenance

If update cannot prove every affected edge, it should preserve partial facts, low-confidence records, conflicts, known unknowns, and minimal live reads. It should not automatically escalate to a full rebuild unless the user explicitly requests a rebuild or the map maintenance task itself cannot proceed at all without rebuilding its own baseline.

## Error Handling

- Unreadable map files: continue with live repository inspection and report project cognition as unavailable.
- Invalid schema or query payload: ignore map output for the current task and use live code evidence.
- Contradiction between map and source: source wins; record the contradiction as a map maintenance recommendation.
- User explicitly asks to repair map first: run the appropriate map workflow and keep validation inside that workflow.

## Testing Strategy

- Update template tests that currently assert hard-gate wording, runtime-truth wording, or mandatory update/rebuild routing.
- Add assertions that project cognition is described as advisory navigation.
- Add assertions that workflows require code-backed evidence for technical conclusions.
- Add assertions that `needs_update` and `needs_rebuild` are not mandatory downstream workflow stops.
- Preserve tests that validate map-scan, map-build, and map-update can check their own artifacts.
- Add or update guidance tests for advisory completion follow-up after structural changes.

## Documentation Surfaces

The implementation should update these surfaces together:

- `templates/commands/**` workflows that interpret project cognition readiness.
- `templates/command-partials/common/context-loading-gradient.md`.
- `templates/command-partials/common/senior-consequence-analysis-gate.md`.
- `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`.
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`.
- `src/specify_cli/integrations/base.py` generated guidance.
- `README.md` and `PROJECT-HANDBOOK.md`.
- Tests that encode the old hard-gate contract.

## Acceptance Criteria

- Generated workflow guidance no longer calls project cognition a hard gate, mandatory pre-source knowledge base, or runtime truth surface for ordinary work.
- Downstream workflows no longer require `sp-map-update` or `sp-map-scan -> sp-map-build` solely because a map readiness heuristic reports `needs_update`, `needs_rebuild`, stale, or possibly stale.
- Workflows still use project cognition when available as a first-pass navigation aid.
- Workflows state that code, tests, scripts, configuration, and authoritative docs are the evidence sources for technical claims.
- Map maintenance is recommended after relevant structural changes, not required for task completion.
- Map-specific workflows can still validate their own artifacts.
- `sp-map-update` guidance supports bounded subagent-backed maintenance lanes.
