# Map Scan / Map Build Workflow Design

**Date:** 2026-04-29
**Status:** Approved for implementation
**Owner:** Codex

## Summary

This design replaces the current one-step `sp-map-codebase` workflow with a
two-step atlas refresh flow:

```text
sp-map-scan -> sp-map-build
```

The current `sp-map-codebase` prompt already asks for deep coverage, explorer
subagents, capability cards, detailed atlas documents, and a final acceptance
check. The failure is structural: all of that work lives in one prompt, so an
agent can perform a shallow top-level scan, start writing the atlas too early,
and never produce an executable map-building task package.

The new design makes the first step produce a complete, reviewable, and
machine-checkable scan package. The second step must build the handbook and
project-map atlas from that scan package, not from ad hoc exploration.

## Problem Statement

`sp-map-codebase` currently combines five different responsibilities:

1. recover any existing handbook/project-map baseline
2. inventory the repository
3. decide what needs deep exploration
4. dispatch read-only explorer lanes
5. write `PROJECT-HANDBOOK.md` and `.specify/project-map/**`

This creates recurring quality failures:

- the workflow can stop at repository shape and miss nested project-relevant
  directories
- explorer subagents can be optional in practice instead of a planned
  execution model
- there is no durable "map task list" equivalent to `tasks.md`
- the final atlas has no strict reverse link back to everything that was
  inventoried
- shallow summaries can pass because the checklist is prose-only

The goal is not to make prompts longer. The goal is to make coverage and
completion verifiable.

## Goals

- Split mapping into explicit scan and build commands.
- Make `sp-map-scan` produce enough detail for `sp-map-build` to understand and
  map the whole project-relevant repository.
- Require complete project-relevant directory and subdirectory inventory before
  atlas construction begins.
- Allow `sp-map-scan` to use read-only subagents for faster inventory,
  classification, and packet generation.
- Preserve and strengthen the scanning dimensions already present in
  `sp-map-codebase`.
- Make `sp-map-build` refuse to write final atlas documents when the scan
  package is incomplete.
- Add human-readable and machine-readable outputs so tests or hooks can enforce
  the workflow contract.
- Keep cache, dependency, and build-output directories out of deep reading
  while still recording why they were excluded.

## Non-Goals

- Do not keep `sp-map-codebase` as the primary user-facing workflow.
- Do not scan `.git`, virtual environments, caches, build outputs, or generated
  dependency trees at file-by-file depth unless a current task explicitly makes
  them relevant.
- Do not create a second atlas tree. The canonical final outputs remain
  `PROJECT-HANDBOOK.md` and `.specify/project-map/**`.
- Do not let subagents write final atlas documents directly.
- Do not replace the layered atlas model from the existing project-map design.

## Workflow Overview

### 1. `sp-map-scan`

`sp-map-scan` is a planning and coverage workflow. It must not write final atlas
truth. Its job is to produce the complete map-building task package:

```text
.specify/project-map/map-scan.md
.specify/project-map/coverage-ledger.md
.specify/project-map/coverage-ledger.json
.specify/project-map/scan-packets/<lane-id>.md
```

`map-scan.md` is the leader-readable plan. `coverage-ledger.md` is the
human-readable coverage account. `coverage-ledger.json` is the machine-readable
contract. `scan-packets/*.md` are executable read-only work packets for
`sp-map-build`.

### 2. `sp-map-build`

`sp-map-build` is the atlas construction workflow. It reads the scan package,
dispatches read-only explorer subagents according to `scan-packets/*.md`,
integrates their evidence, writes the canonical atlas, and performs reverse
coverage validation.

If `sp-map-build` discovers that the scan package is incomplete, it must not
guess and continue. It must produce a scan gap report and route back to
`sp-map-scan`.

## `sp-map-scan` Contract

### Phase 1: Full Project-Relevant Inventory

`sp-map-scan` must enumerate the project-relevant repository tree, including
nested directories. The scan should be file-list driven, using `rg --files`,
Git-tracked files, and targeted directory listing where needed.

The inventory must include:

- source roots such as `src/`, package directories, and extension runtimes
- tests, fixtures, contract tests, smoke tests, and testing utilities
- templates, passive skills, command templates, worker prompts, and generated
  downstream surfaces
- scripts, shell helpers, PowerShell helpers, and workflow helper tools
- project configuration, lockfiles, lint/test config, devcontainer config, and
  CI workflow files
- docs, README files, workflow docs, release docs, and upgrade docs
- project state surfaces such as `.specify/`, `PROJECT-HANDBOOK.md`, and
  project-map templates
- integration adapters, MCP/config/runtime installer surfaces, and supported
  agent adaptation layers
- packaging, release, bundled asset, and distribution metadata surfaces

The inventory may bucket these surfaces without file-by-file deep reading:

- `.git/`
- `.venv/` and other virtual environments
- `.pytest_cache/`, `.ruff_cache/`, and similar tool caches
- `dist/`, `build/`, temporary output, generated logs, and smoke-test output
- external dependency, vendor, or cache directories

Excluded buckets still appear in the coverage ledger with:

- `excluded_from_deep_read: true`
- reason
- owner/category
- when-to-revisit condition

### Phase 2: Coverage Classification

Every project-relevant directory or file family must receive a classification.

Allowed categories:

- `source`
- `test`
- `template-generated-surface`
- `script`
- `config`
- `documentation`
- `runtime`
- `integration`
- `packaging-release`
- `state-artifact`
- `vendor-cache-build-output`
- `unknown`

`unknown` is a scan failure unless the item is explicitly marked as blocked
with a concrete next read needed. `sp-map-build` must not accept a scan package
that still contains unresolved `unknown` coverage rows.

### Phase 3: Reading Depth Assignment

Each ledger row must choose one reading depth:

- `inventory`: existence, category, ownership, and revisit condition are enough
- `sampled`: representative files were read to establish a pattern
- `deep-read`: the lane must read the relevant files, entrypoints, or contracts
  closely before atlas writing

Critical and important surfaces cannot be left at `inventory` depth unless they
are excluded buckets with a clear reason.

### Phase 4: Criticality Scoring

Each row must be scored:

- `critical`: required for architecture, workflow, API, integration, runtime,
  security, packaging, or verification correctness
- `important`: meaningful for future maintainers, but not a central boundary
- `low-risk`: can be bucketed or summarized, with a revisit condition

Critical rows require a scan packet, an atlas target, and a verification route.
Important rows require an atlas target or an explicit grouping under another
surface. Low-risk rows require owner/category and revisit condition.

### Phase 5: Scan Packet Generation

`sp-map-scan` must generate `scan-packets/<lane-id>.md` files that `sp-map-build`
can execute directly.

Each packet must include:

- lane ID and title
- scope and owned ledger row IDs
- required files/directories to inspect
- intentionally excluded paths and reasons
- required questions to answer
- expected evidence format
- final atlas target documents
- join points and dependencies
- minimum verification route
- blocked conditions

Subagents may be used during `sp-map-scan` to accelerate inventory and
classification, but they remain read-only. The scan leader owns final ledger
normalization and packet quality.

## Required Scan Dimensions

These dimensions are extracted from the existing `sp-map-codebase` contract and
become required fields in the scan package.

1. **Project shape and stack**
   - project type, technology stack, build tooling, deployment shape

2. **Architecture overview**
   - architecture pattern, layers, core abstractions, truth ownership,
     boundaries, cross-cutting concerns

3. **Directory ownership**
   - directory responsibilities, major subdirectories, write surfaces, shared
     coordination files, placement guidance

4. **Module dependency graph**
   - module relationships, import/require direction, strong coupling,
     risky cycles, shared surfaces

5. **Core code elements**
   - core classes, interfaces, abstract types, enums, major functions,
     utility modules, state/data models

6. **Entry and API surfaces**
   - CLI commands, routes, controllers, exported endpoints, method families,
     parameter semantics, return shapes, error contracts

7. **Data and state flows**
   - data lineage, runtime events, state lifecycle, state transitions,
     persistence/cache checkpoints, handoff fields

8. **User and maintainer workflows**
   - entry-to-exit flows, handoffs, adjacent workflow risks, operator flows,
     recovery paths

9. **Integrations and protocol boundaries**
   - external tools/services, integration adapters, IPC/bridge/native-host
     seams, message/pipe/protocol semantics, runtime assumptions

10. **Build, release, and runtime**
    - build pipeline, packaging, bundled assets, release workflow, startup
      paths, runtime topology, recovery instructions

11. **Testing and verification**
    - test layers, test directories, smallest meaningful checks,
      regression-sensitive areas, minimum verification commands

12. **Risk, security, observability, and evolution**
    - change propagation, security boundaries, permission model,
      observability, failure modes, decision history, known unknowns,
      low-confidence areas

13. **Template and generated-surface propagation**
    - source templates, generated command/skill surfaces, integration-specific
      transformations, downstream file paths, tests that lock the generated
      behavior

14. **Coverage reverse index**
    - every critical or important surface must name the final atlas document
      where it will be explained

## `map-scan.md` Structure

`map-scan.md` should be concise but complete enough to drive the next command.

Required sections:

1. Run metadata
2. Repository scope and exclusions
3. Scan strategy and subagent use
4. Coverage summary
5. Module and topic candidates
6. Critical surfaces
7. Scan packet index
8. Join points
9. Build readiness checklist
10. Known scan gaps
11. Handoff to `sp-map-build`

The build readiness checklist must fail if:

- any project-relevant row is uncategorized
- any row remains `unknown` without a blocker
- any critical row lacks a scan packet
- any critical or important row lacks an atlas target
- any scan packet lacks required questions or evidence format
- excluded buckets lack a reason and revisit condition

## `coverage-ledger.json` Shape

The JSON contract should stay simple enough for tests and hooks.

```json
{
  "version": 1,
  "generated_by": "sp-map-scan",
  "generated_at": "YYYY-MM-DDTHH:MM:SSZ",
  "repo_root": ".",
  "focus": "",
  "rows": [
    {
      "id": "SURF-001",
      "path_glob": "templates/commands/*.md",
      "category": "template-generated-surface",
      "owner": "workflow templates",
      "module_id": "specify-cli-core",
      "criticality": "critical",
      "reading_depth": "deep-read",
      "scan_packet": "SCAN-templates-workflows",
      "atlas_targets": [
        ".specify/project-map/root/WORKFLOWS.md",
        ".specify/project-map/modules/specify-cli-core/WORKFLOWS.md"
      ],
      "verification": "pytest tests/test_*template* -q",
      "excluded_from_deep_read": false,
      "exclusion_reason": "",
      "when_to_revisit": "workflow template behavior changes",
      "status": "ready"
    }
  ],
  "blockers": [],
  "summary": {
    "unknown_rows": 0,
    "critical_rows_without_packet": 0,
    "rows_without_atlas_target": 0
  }
}
```

`sp-map-build` can rely on this schema for refusal checks and reverse coverage
validation.

## Scan Packet Template

Each `scan-packets/<lane-id>.md` must use this structure:

```markdown
# SCAN-<id>: <title>

## Scope

- Ledger rows:
- Paths:
- Project area:

## Required Reads

- <path or glob> - reason

## Excluded Paths

- <path or glob> - reason - when to revisit

## Required Questions

- What owns this surface?
- Where does the truth live?
- What entrypoints, contracts, state fields, or handoffs matter?
- What consumes or feeds this surface?
- How does change propagate?
- What should future work extend here?
- What should future work avoid extending here?
- What minimum verification proves this surface still works?
- What unknowns or low-confidence claims remain?

## Expected Evidence

- paths_read:
- key_facts:
- confidence:
- unknowns:
- minimum_verification:
- recommended_atlas_updates:

## Atlas Targets

- <PROJECT-HANDBOOK.md or .specify/project-map path>

## Join Points

- <join point and pass condition>

## Blocked Conditions

- <condition that must route back to sp-map-scan>
```

## `sp-map-build` Contract

`sp-map-build` begins with validation, not writing.

It must:

1. read `map-scan.md`, `coverage-ledger.json`, and all scan packets
2. fail fast if scan readiness checks fail
3. dispatch read-only explorer subagents for the declared packets whenever the
   chosen execution strategy supports native multi-agent work
4. require every explorer result to include paths read, facts, confidence,
   unknowns, verification route, and recommended atlas targets
5. integrate the evidence as leader-owned atlas writes
6. write or refresh only canonical atlas outputs
7. perform reverse coverage validation
8. finalize freshness through the project-map helper after successful refresh

`sp-map-build` must not accept:

- packet results without paths read
- packet results that only summarize without evidence
- unresolved critical rows
- atlas documents that stop at directory names without responsibilities
- API/entry surfaces without owner, consumer, change propagation, and
  verification route
- final atlas outputs that omit scan packet unknowns from known unknowns,
  low-confidence areas, or module stale state

## Reverse Coverage Validation

Before reporting success, `sp-map-build` must prove closure:

- every `critical` row appears in at least one final atlas target
- every `important` row appears in a final atlas target or an explicitly named
  grouped surface
- every scan packet is consumed
- every accepted packet result has paths read and confidence
- every command/API/integration/runtime entrypoint has owner, consumer, change
  propagation, and verification
- every low-confidence area is visible in Known Unknowns, Low-Confidence Areas,
  or module `deep_stale`
- every excluded bucket has a reason and revisit condition
- `PROJECT-HANDBOOK.md` stays index-first and routes to deeper topical docs

If any check fails, the workflow continues mapping or routes back to
`sp-map-scan`; it must not report success.

## Output Ownership

`sp-map-scan` owns:

- `.specify/project-map/map-scan.md`
- `.specify/project-map/coverage-ledger.md`
- `.specify/project-map/coverage-ledger.json`
- `.specify/project-map/scan-packets/*.md`

`sp-map-build` owns:

- `PROJECT-HANDBOOK.md`
- `.specify/project-map/index/*.json`
- `.specify/project-map/root/*.md`
- `.specify/project-map/modules/<module-id>/*.md`
- `.specify/project-map/modules/<module-id>/deep/**` when packeted and needed
- `.specify/project-map/index/status.json`

Both commands may read previous atlas outputs, passive memory, and project
templates. Only `sp-map-build` writes final atlas truth.

## Migration Requirements

Implementation should update the shared workflow surface rather than a single
integration only.

Required migration points:

- add `templates/commands/map-scan.md`
- add `templates/commands/map-build.md`
- remove or retire `templates/commands/map-codebase.md` from generated command
  surfaces
- add command partials for `map-scan` and `map-build`
- update workflow routing guidance from `sp-map-codebase` to
  `sp-map-scan -> sp-map-build`
- update README and quickstart brownfield guidance
- update passive project-map gate wording
- update Codex, Claude, Cursor, Copilot, Gemini, TOML, Markdown, and
  skills-based integration expectations through shared templates
- update Codex native multi-agent augmentation for the new command names
- update tests that currently assert `sp-map-codebase`
- add template tests for scan packet and ledger requirements
- add integration tests that generated skills/commands include `sp-map-scan`
  and `sp-map-build`

Because the user approved a breaking workflow rename, compatibility aliases are
not required for the main design.

## Testing Strategy

Focused tests should prove the contract, not just file existence.

Add or update tests for:

- command template inventory includes `map-scan` and `map-build`
- generated command/skill surfaces include the new workflows
- generated surfaces no longer advertise `sp-map-codebase` as the brownfield
  gate
- `map-scan` template requires full project-relevant inventory
- `map-scan` template requires `coverage-ledger.md`,
  `coverage-ledger.json`, and `scan-packets/*.md`
- `map-scan` template includes inclusion/exclusion rules for project-relevant
  paths and cache/build-output buckets
- `map-scan` template includes the 14 required scan dimensions
- `map-build` template refuses incomplete scan packages
- `map-build` template requires reverse coverage validation
- Codex augmentation tells native subagents how to handle scan and build lanes
- docs route brownfield work through `sp-map-scan -> sp-map-build`

Manual validation for the implementation should include generating a sample
project with at least one skills-based and one Markdown/TOML integration and
checking that the emitted command names, handoffs, and routing text agree.

## Risks and Mitigations

- **Risk:** The scan package becomes too heavy for small repositories.
  **Mitigation:** Low-risk rows can stay bucketed at `inventory` depth, but they
  still need owner/category and revisit condition.

- **Risk:** Agents treat JSON as optional.
  **Mitigation:** `sp-map-build` starts with JSON readiness checks and refuses
  incomplete packages.

- **Risk:** Subagents produce narrative summaries.
  **Mitigation:** Packet result acceptance requires paths read, facts,
  confidence, unknowns, verification, and atlas targets.

- **Risk:** Final atlas still omits scanned areas.
  **Mitigation:** Reverse coverage validation links ledger rows back to atlas
  targets before success.

- **Risk:** Breaking rename leaves stale docs/tests.
  **Mitigation:** Update all shared docs, routing, generated assets, and tests in
  one implementation pass.

## Decision

Proceed with a breaking replacement of `sp-map-codebase` by
`sp-map-scan -> sp-map-build`.

The quality bar is that `sp-map-build` can only succeed when the scan package
fully covers project-relevant surfaces, every critical surface has a packet and
atlas target, explorer evidence is accepted with paths and confidence, and the
final atlas passes reverse coverage validation.
