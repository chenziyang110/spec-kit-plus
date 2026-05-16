# Sp Specify Lossless State Design

**Date:** 2026-05-16
**Status:** Proposed
**Owner:** Codex

## Summary

This design makes `sp-specify` resilient to context exhaustion and compaction by
adding a lossless, file-backed state model for the whole specification
discovery run.

The approved direction is a three-layer model:

1. `brainstorming/journal.ndjson` is the append-only event source.
2. Stage artifacts are the structured landing points for each `sp-specify`
   phase.
3. Final artifacts are compiled views produced from the journal and stage
   artifacts.

The result is that a later session can resume from disk, validate whether the
current views match the event source, repair stale compiled state, and compile
`spec.md`, `alignment.md`, `context.md`, and `references.md` without relying on
chat memory.

## Problem Statement

`sp-specify` now carries a rich discovery flow:

- repository and project cognition intake
- optional research
- `facts-lock`
- `route-lock`
- `intent-lock`
- `complexity-lock`
- domain clarification
- consequence analysis
- final artifact compilation

The workflow already scaffolds important files such as `facts.json`,
`route.json`, `intent.json`, `complexity.json`,
`handoff-to-specify.json`, `specify-draft.md`, and
`workflow-state.md`. These files are useful, but they primarily act as current
state or human-readable summaries. They do not fully preserve the ordered path
that produced the state.

When a long `sp-specify` run goes through repeated context compaction, the agent
can lose:

- why a fact was accepted
- which user answer resolved an unknown
- which evidence snippet supported a route or complexity choice
- which rejected path was superseded
- which reopen changed a prior conclusion
- which stage state should be trusted when files drift

The current risk is not just losing a transcript. The risk is losing enough
intermediate truth that the final specification package becomes a re-summary of
visible context rather than a deterministic compilation from durable inputs.

## Goals

- Give every `sp-specify` phase a concrete file-backed landing point.
- Preserve the discovery path losslessly enough to recover after compaction.
- Make user answers, evidence, unknown handling, decisions, reopens, and
  compilation steps traceable by stable IDs.
- Keep existing `sp-specify` artifacts as the downstream contract instead of
  replacing them.
- Make final artifact compilation consume the journal and stage artifacts.
- Make resume validate and repair stage artifacts before continuing.
- Avoid storing large raw documents in the main specification files.

## Non-Goals

- Do not store private chain-of-thought or hidden model reasoning.
- Do not require every trivial wording update to become a heavyweight artifact
  migration.
- Do not make Markdown the trusted recovery source.
- Do not remove existing `facts.json`, `route.json`, `intent.json`,
  `complexity.json`, or `handoff-to-specify.json`.
- Do not build a full database-backed event store for the first release.

## User-Approved Decisions

The user approved the hybrid lossless model:

- preserve structure first
- retain raw snippets and hashes for user answers, research, and evidence
- do not rely on summaries alone

The user also clarified that every `sp-specify` stage needs a landing point and
that both resume and final compilation must use those landing points.

## Architecture

### 1. Event Source

Canonical file:

- `FEATURE_DIR/brainstorming/journal.ndjson`

Each line is one append-only JSON event. Events are never rewritten. Corrections
append a new event that references the prior event through fields such as
`supersedes_event_id`, `reopens_decision_id`, or `invalidates_evidence_id`.

Required event envelope:

```json
{
  "event_id": "EVT-000001",
  "schema_version": 1,
  "created_at": "2026-05-16T00:00:00Z",
  "stage": "facts-lock",
  "domain": "goal-and-users",
  "type": "answer_recorded",
  "source": {
    "kind": "user",
    "excerpt": "raw user-visible excerpt",
    "content_hash": "sha256:..."
  },
  "payload": {},
  "writes": [],
  "supersedes_event_id": null
}
```

The source excerpt should be compact but exact enough to recover meaning. Large
documents should live in evidence files and be referenced by ID plus hash.

### 2. Stage Manifest

Canonical file:

- `FEATURE_DIR/brainstorming/stage-manifest.json`

The manifest is the recovery index. It records each stage artifact, status,
hash, event range, last checkpoint, and whether the stage can be trusted for
resume.

Recommended shape:

```json
{
  "version": 1,
  "journal": {
    "path": "brainstorming/journal.ndjson",
    "last_event_id": "EVT-000120",
    "last_checkpoint_id": "CHK-000009"
  },
  "stages": {
    "facts-lock": {
      "artifact": "brainstorming/facts.json",
      "status": "closed",
      "event_range": ["EVT-000001", "EVT-000030"],
      "artifact_hash": "sha256:...",
      "last_compiled_event_id": "EVT-000030",
      "recoverable": true
    }
  }
}
```

Resume should read the manifest before scanning individual stage files.

### 3. Stage Artifacts

Each phase has a structured landing point. These files are not optional summary
notes; they are part of the recovery and compilation contract.

| Stage | Landing Point | Responsibility |
| --- | --- | --- |
| Intake and workspace | `workflow-state.md`, `brainstorming/journal.ndjson`, `brainstorming/stage-manifest.json` | Original request, feature paths, current stage, next action, recovery pointer |
| Evidence intake | `brainstorming/evidence-index.json`, `brainstorming/evidence/EVD-###.json` | Repo evidence, research findings, pasted materials, source hashes |
| `facts-lock` | `brainstorming/facts.json` | Evidence-backed truth predicates and unknowns |
| `route-lock` | `brainstorming/route.json` | Primary route, matched rules, rejected routes, blocking unknowns |
| `intent-lock` | `brainstorming/intent.json` | Goal, non-goals, success criteria, must-preserve items, optimization scope |
| `complexity-lock` | `brainstorming/complexity.json` | Complexity level, trigger rules, scope, execution mode |
| Domain clarification | `brainstorming/domains.json`, `specify-draft.md` | Domain closure state, questions, answers, reopen history |
| Consequence and risk | `brainstorming/handoff-to-specify.json` | Must-preserve coverage, conflicts, consequence obligations, stop-and-reopen conditions |
| Compile | `spec.md`, `alignment.md`, `context.md`, `references.md` | Human-readable planning package compiled from structured inputs |
| Release | `workflow-state.md`, `checklists/requirements.md` | Final next command and validation state |

### 4. Compiled Views

Existing JSON files and Markdown artifacts remain important, but they become
compiled views over the event source and stage data.

Every structured stage artifact should include a `compiled_from` block:

```json
{
  "compiled_from": {
    "journal": "brainstorming/journal.ndjson",
    "event_range": ["EVT-000001", "EVT-000030"],
    "key_events": ["EVT-000004", "EVT-000018", "EVT-000029"],
    "evidence_ids": ["EVD-001"],
    "compiled_at": "2026-05-16T00:00:00Z"
  }
}
```

Human-facing Markdown may show a compact source block or hide detailed source
maps in machine-readable comments, but the structural trace must exist in the
stage artifacts.

## Event Types

The first release should support these event types:

- `session_started`
- `feature_workspace_created`
- `user_input_captured`
- `question_asked`
- `answer_recorded`
- `repo_evidence_captured`
- `research_evidence_captured`
- `unknown_opened`
- `unknown_resolved`
- `unknown_deferred`
- `unknown_waived`
- `decision_locked`
- `route_selected`
- `complexity_selected`
- `stage_artifact_compiled`
- `reopen_requested`
- `artifact_compiled`
- `checkpoint_written`

This list should stay small enough for agents to follow. New event types should
only be added when existing events cannot express a real recovery or compile
need.

## Evidence Model

Evidence should be separated from lock artifacts so the system can preserve raw
support without bloating the final spec.

Canonical files:

- `brainstorming/evidence-index.json`
- `brainstorming/evidence/EVD-###.json`

Each evidence record should include:

- stable evidence ID
- source kind: `repo`, `user`, `research`, `discussion-handoff`, `reference`
- source path or URL when applicable
- exact excerpt or bounded raw content
- content hash
- captured event ID
- stage and domain relevance
- accepted use in later decisions

Large evidence can be chunked, but every chunk needs an ID and hash. Final
artifacts should cite evidence IDs rather than copy long raw material.

## Resume Flow

Resume must be deterministic and validation-backed.

1. Read `workflow-state.md` for current command, stage, domain, next action,
   next command, and last checkpoint.
2. Read `brainstorming/stage-manifest.json` to locate trusted stage artifacts
   and the last event ID.
3. Replay `brainstorming/journal.ndjson` from the last checkpoint or from the
   start when the checkpoint is missing.
4. Validate each stage artifact's `compiled_from` range and artifact hash
   against the manifest.
5. If a stage artifact and journal disagree, trust the journal, mark the stage
   view stale, and recompile the affected stage artifact before proceeding.
6. Re-read the repaired `workflow-state.md` and continue from its `next_action`.

Markdown files are not trusted for resume except as human-readable companions.
If Markdown disagrees with structured state, structured state wins and Markdown
is regenerated or flagged for repair.

## Compile Flow

Final artifact compilation must consume the structured state package:

- `brainstorming/stage-manifest.json`
- `brainstorming/evidence-index.json`
- `brainstorming/facts.json`
- `brainstorming/route.json`
- `brainstorming/intent.json`
- `brainstorming/complexity.json`
- `brainstorming/domains.json`
- `brainstorming/handoff-to-specify.json`
- cited journal events

The compiler then writes or updates:

- `spec.md`
- `alignment.md`
- `context.md`
- `references.md`
- `checklists/requirements.md`
- `workflow-state.md`

`spec.md`, `alignment.md`, and `context.md` should expose enough source mapping
to diagnose how major conclusions were produced. They do not need to display
every event inline, but important claims must trace to source event IDs or
evidence IDs through the structured artifacts.

## Checkpoint Rules

The workflow must write a checkpoint before any transition where compaction
would otherwise risk losing important state.

Required checkpoints:

- after capturing the original request
- after every high-impact user answer
- after capturing important repository or research evidence
- before and after each lock closes
- before and after a domain reopen
- before final artifact compilation
- after final artifact compilation
- before stopping with `/sp.clarify`, `/sp.deep-research`, or `/sp.plan`

Each checkpoint appends a `checkpoint_written` journal event and updates:

- `workflow-state.md`
- `brainstorming/stage-manifest.json`
- the current stage artifact's `compiled_from` block

## Validation Rules

The artifact validation hook should learn the new contract.

Validation should fail when:

- `journal.ndjson` is missing for an active or completed `sp-specify` package
- `stage-manifest.json` is missing
- a closed stage artifact lacks `compiled_from`
- a closed stage artifact's hash does not match the manifest
- `workflow-state.md` points to a checkpoint not present in the journal
- a hard unknown is closed without a resolving event or evidence reference
- a route or complexity decision lacks matched rule event IDs
- final artifacts claim planning readiness while required stage artifacts are
  stale or unrecoverable

Validation may warn, not fail, when:

- legacy packages lack the new files but were created before the migration
- Markdown companion files are stale while structured artifacts are valid

## Template Impact

The implementation should update these product surfaces together:

- `templates/commands/specify.md`
- `templates/command-partials/specify/shell.md`
- `templates/workflow-state-template.md`
- `templates/specify-draft-template.md`
- `templates/brainstorming-*-template.json`
- new `templates/brainstorming-stage-manifest-template.json`
- new `templates/brainstorming-domains-template.json`
- new `templates/brainstorming-evidence-index-template.json`
- new `templates/brainstorming-evidence-record-template.json`
- `scripts/bash/create-new-feature.sh`
- `scripts/powershell/create-new-feature.ps1`
- `scripts/bash/common.sh`
- `scripts/powershell/common.ps1`
- `src/specify_cli/hooks/artifact_validation.py`
- packaging entries in `pyproject.toml`
- guidance docs that describe `sp-specify` recovery behavior

This is a workflow-product change, not a local-only prompt edit.

## Migration Strategy

New feature work should receive the lossless state files during feature
scaffolding.

Existing feature packages should be handled compatibly:

- if `journal.ndjson` is missing, mark the package as legacy
- do not pretend legacy summaries are lossless
- allow planning to continue only under existing validation rules unless the
  user asks to repair the package
- if repair is requested, create a journal with a `legacy_state_imported` event
  and preserve the limitation explicitly

## Testing Impact

Add or update tests for:

- feature scaffolding includes journal, manifest, domains, and evidence index
- packaged templates include the new files
- `sp-specify` template requires checkpoints at the approved transitions
- validation rejects closed stage artifacts without `compiled_from`
- validation rejects manifest hash mismatch
- validation rejects workflow-state checkpoint pointers not present in journal
- final artifact templates preserve source map guidance
- legacy packages receive warnings rather than false lossless claims

Likely test files:

- `tests/test_alignment_templates.py`
- `tests/test_specify_guidance_docs.py`
- `tests/contract/test_hook_cli_surface.py`
- integration tests for bash and PowerShell feature scaffolding

## Risks

### Complexity Risk

Agents may treat the journal as busywork unless the template contract is direct
and repetitive. The first release should keep event types limited and give
small examples at each stage.

### Drift Risk

The journal, stage artifacts, manifest, and Markdown views can drift if updates
are not coupled. The manifest and validation hook are the mitigation.

### Size Risk

Raw evidence can grow quickly. The evidence model should store bounded excerpts
plus hashes by default and only retain larger chunks when needed for recovery.

### Legacy Risk

Existing generated projects will not have the new files. Migration must avoid
claiming old packages are lossless.

## Acceptance Criteria

The design is implemented when:

1. New `sp-specify` feature work creates `journal.ndjson`,
   `stage-manifest.json`, `domains.json`, and an evidence index.
2. Every `sp-specify` phase has a structured landing point.
3. Stage artifacts record `compiled_from` journal ranges and key event IDs.
4. Resume reads `workflow-state.md`, the manifest, journal, and stage artifacts
   before continuing.
5. Journal replay wins over stale compiled views.
6. Final artifacts are compiled from stage artifacts and cited journal or
   evidence events, not from chat memory.
7. Validation blocks planning readiness when required lossless state is missing,
   stale, or internally inconsistent for non-legacy packages.
8. Legacy packages are clearly marked as non-lossless instead of silently
   upgraded.

## Decision

Proceed with the three-layer design:

- append-only journal as the lossless event source
- per-stage JSON artifacts as mandatory landing points
- manifest-backed resume and compile validation

Markdown remains useful for human review, but trusted recovery and final
compilation are driven by JSON artifacts plus the event journal.
