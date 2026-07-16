# Project Cognition Compass Architecture Design

**Date:** 2026-06-15
**Status:** Draft for user review
**Owner:** Codex
**Related designs:**
- `docs/superpowers/specs/2026-06-02-shared-semantic-cognition-intake-design.md`
- `docs/superpowers/specs/2026-06-03-cognition-intake-experience-alignment-design.md`
- `docs/superpowers/specs/2026-06-03-project-cognition-alias-schema-cleanup-design.md`
- `docs/superpowers/specs/2026-06-12-agent-owned-cognition-normalization-design.md`

## Summary

Project cognition should become a two-layer navigation system:

- The default layer is a compact **compass packet** that gives the agent the
  shortest first evidence path.
- The expansion layer keeps the broader map, raw candidate universe, graph
  neighbors, related paths, and coverage diagnostics available on demand.

The goal is not to make project cognition prove source behavior. The goal is to
help the agent reach live evidence quickly without dumping a path universe into
the chat. Budget limits output volume, not coverage truth.

## Problem

A downstream `sp-debug` run in `F:\github\cc-jiangxia` exposed the failure mode:

- The graph was queryable and `validate-build` reported query readiness.
- Status was still `partial_refresh` and `review`.
- A symptom-first mixed Chinese/English query about desktop model switching,
  provider runtime override, DeepSeek startup failure, square glyphs, and small
  viewport returned a broad fallback concept as the top result.
- That fallback concept, `Coverage paths not in existing nodes`, carried more
  than 3000 paths and could expand into a 20k-line payload.

This is the wrong user and agent experience. The user expected a compass:
enough direction to start reading the right code and related surfaces. The
runtime instead exposed a high-density map dump. That makes the workflow noisy
and can also mislead an agent into treating broad coverage artifacts as real
route candidates.

## Goals

- Keep project cognition as advisory navigation, not authoritative evidence.
- Make the default response compact enough for chat and agent context.
- Preserve key information: where to look, why those paths matter, how to
  verify, what coverage is missing, and what may need expansion.
- Prevent a short default packet from being mistaken for the complete edit set.
- Separate real route candidates from coverage diagnostics and expansion-only
  material.
- Keep `lexicon -> semantic_intake -> query` as the advanced flow.
- Add a first-class `compass` flow for default workflow intake.
- Ensure broad fallback nodes and path-universe concepts cannot become primary
  route candidates.
- Support localized, mixed-language, colloquial, and symptom-first prompts
  without pretending the CLI owns semantic judgment.

## Non-Goals

- Do not make project cognition prove current source behavior.
- Do not replace live file reads, tests, logs, or reproduction evidence.
- Do not remove the existing `lexicon` and `query` commands.
- Do not implement full symbol, entrypoint, test, or vector retrieval systems
  as part of the first compass architecture change.
- Do not hide coverage gaps to make the default response look cleaner.
- Do not require the agent to treat the first-pass path set as the final set of
  files to modify.

## Design Principles

### Budget Limits Output, Not Coverage Truth

The default response may return only 5 to 15 first-pass paths, but it must still
state which intent facets are covered, partial, missing, or require expansion
before a fix claim.

### First Evidence Path Is Not Final Edit Scope

`minimal_live_reads` and `first_pass_paths` are the first evidence path. They
are not a complete modification list. Workflow guidance must explicitly forbid
claiming the final edit scope from the compass packet alone.

### Route Candidates Are Not Coverage Diagnostics

Project cognition must stop mixing all candidate-like things into one ranked
list. A broad fallback node may be useful as a diagnostic, but it is not a route.

### Agent Owns Semantics, CLI Owns Structure

The CLI may tokenize, rank, group, budget, suppress broad fallbacks, and report
mechanical diagnostics. The agent still owns interpretation of user wording,
facet selection, and live evidence proof.

## Architecture

The runtime has two user-facing layers.

```text
user prompt
  -> project-cognition compass
  -> compact compass_packet
  -> agent first-pass live reads
  -> evidence-backed route refinement
  -> optional project-cognition expand
```

The existing advanced flow remains available:

```text
project-cognition lexicon
  -> agent semantic_intake and concept decisions
  -> project-cognition query
  -> route pack and minimal live reads
```

`compass` may internally reuse lexicon, alias catalog, query-plan primitives,
path indexes, and graph metadata. Its contract is different: it returns a
bounded evidence-routing packet instead of a broad candidate universe.

## CLI Surface

Add:

```text
project-cognition compass --intent <intent> --query "<user prompt>" --format json
project-cognition compass --intent <intent> --query "<user prompt>" --semantic-intake-file <path> --format json
project-cognition compass --intent <intent> --query-plan-file <path> --format json
```

`--query` alone is a mechanical draft mode. It can tokenize, rank, suppress
broad fallbacks, infer low-confidence mechanical facets, and return
`agent_normalization` when semantic intake is required. It must not claim full
facet coverage from raw text alone.

`--semantic-intake-file` and `--query-plan-file` are the precision modes. They
let the agent provide explicit `semantic_intake`, `intent_facets`,
`negative_constraints`, `alias_interpretations`, selected or rejected concepts,
and concept decisions. The coverage gate can only be strict against agent-owned
facets when one of these richer inputs is present.

Optional expansion:

```text
project-cognition expand --id <expansion-id> --section related_paths --format json
project-cognition expand --id <expansion-id> --section raw_candidates --format json
project-cognition expand --id <expansion-id> --section coverage_gaps --format json
project-cognition expand --id <expansion-id> --section graph_neighbors --format json
```

The expansion payload can be written under:

```text
.specify/project-cognition/workbench/expansions/<expansion-id>.json
```

The exact storage file is an implementation detail. The public contract is the
`expansion_ref` object returned in the compass packet.

## Compass Packet

Recommended default shape:

```json
{
  "readiness": "review",
  "compass_state": "usable_with_review",
  "mode": "compass",
  "active_generation_id": "GEN-20260610T112843.959253900Z",
  "candidate_universe_version": 1,
  "query_fingerprint": "qf-7d4b...",
  "summary": "Route first-pass evidence across provider/model switch and UI readability lanes.",
  "intent_facets": [
    {
      "name": "provider/model runtime switch",
      "coverage": "covered_for_first_pass",
      "risk": "first evidence path, not final edit scope"
    }
  ],
  "evidence_lanes": [
    {
      "id": "lane-provider-runtime",
      "title": "Provider/model runtime switch",
      "confidence": "medium",
      "first_pass_paths": [
        {
          "path": "desktop/src/components/controls/ModelSelector.tsx",
          "reason": "User-selected provider/model override originates here.",
          "evidence_hint": "Inspect request shape and persisted runtime selection."
        },
        {
          "path": "src/server/ws/handler.ts",
          "reason": "Runtime override is applied and restart failure is surfaced here.",
          "evidence_hint": "Inspect failed restart rollback and runtimeOverrides state."
        }
      ],
      "verification_hints": [
        "server runtime override rollback regression test",
        "desktop ModelSelector request-shape test"
      ],
      "followup_surfaces": [
        "provider registry",
        "session resume",
        "startup diagnostics redaction"
      ],
      "before_fix_claim": [
        "Confirm provider registry and environment mapping are not the owner.",
        "Confirm failed switch does not poison the next startup truth."
      ]
    }
  ],
  "minimal_live_reads": [
    "desktop/src/components/controls/ModelSelector.tsx",
    "src/server/ws/handler.ts"
  ],
  "coverage_diagnostics": [
    {
      "kind": "broad_fallback_suppressed",
      "severity": "warning",
      "message": "Coverage fallback node matched raw terms but is not a route candidate.",
      "recommended_action": "Use first-pass live reads; consider map update after fix if changed paths remain stale."
    }
  ],
  "expansion_ref": {
    "id": "exp-20260615-example",
    "active_generation_id": "GEN-20260610T112843.959253900Z",
    "candidate_universe_version": 1,
    "query_fingerprint": "qf-7d4b...",
    "available_sections": {
      "related_paths": { "state": "available", "estimated_items": 42 },
      "raw_candidates": { "state": "available", "estimated_items": 120 },
      "coverage_gaps": { "state": "available", "estimated_items": 3 },
      "graph_neighbors": { "state": "available", "estimated_items": 18 }
    },
    "stale_behavior": "expand must return stale_expansion if the active generation, candidate universe version, or query fingerprint no longer matches"
  }
}
```

`minimal_live_reads` is the top-level deduped, ordered union of lane
`first_pass_paths`. Existing generated workflows can consume this field without
losing the richer per-path reasons inside each lane.

## Output Budgets

Default budgets are adaptive:

- Single focused issue: 1 to 2 evidence lanes and 5 to 10 first-pass paths.
- Two independent symptom surfaces: 2 to 3 evidence lanes and 8 to 15 paths.
- More than three independent surfaces: return at most 3 lanes and mark the
  rest as `needs_expansion_before_fix_claim`.
- Each lane should prefer 3 to 6 first-pass paths.
- Each lane should carry at least one verification hint when a plausible local
  test, log, smoke lane, or repro path is known.

These are presentation budgets. The runtime may inspect a wider graph internally
and may store larger expansion material off-chat.

## Data Model

### RouteCandidate

A project concept that can serve as a first-pass evidence route.

```json
{
  "id": "route-server-runtime-override",
  "source_node_id": "N-123",
  "title": "Server runtime override startup path",
  "confidence": "medium",
  "matched_facets": [
    "provider/model switch",
    "startup failure"
  ],
  "primary_paths": [
    "src/server/ws/handler.ts"
  ],
  "reason": "Owns runtime override application and restart error propagation."
}
```

### CoverageDiagnostic

A graph quality, freshness, ambiguity, or fallback condition.

```json
{
  "kind": "fallback_candidate_suppressed",
  "severity": "warning",
  "message": "Coverage paths not in existing nodes matched raw terms but is too broad for route selection.",
  "affected_facets": [
    "desktop",
    "provider/model switch"
  ],
  "recommended_action": "Use first-pass live reads and preserve missing coverage in closeout."
}
```

### EvidenceLane

The agent-facing work unit in the default packet.

```json
{
  "id": "lane-provider-runtime",
  "title": "Provider/model runtime switch",
  "coverage": "covered_for_first_pass",
  "first_pass_paths": [],
  "verification_hints": [],
  "followup_surfaces": [],
  "before_fix_claim": []
}
```

### ExpansionBundle

Stored large detail that should not be printed by default.

```json
{
  "id": "exp-20260615-example",
  "active_generation_id": "GEN-20260610T112843.959253900Z",
  "candidate_universe_version": 1,
  "query_fingerprint": "qf-7d4b...",
  "sections": {
    "related_paths": { "state": "available", "estimated_items": 42 },
    "raw_candidates": { "state": "available", "estimated_items": 120 },
    "coverage_gaps": { "state": "available", "estimated_items": 3 },
    "graph_neighbors": { "state": "available", "estimated_items": 18 }
  },
  "storage": ".specify/project-cognition/workbench/expansions/exp-20260615-example.json"
}
```

`expand` must validate the bundle before returning a section. If
`active_generation_id`, `candidate_universe_version`, or `query_fingerprint`
does not match the current runtime state or request context, it returns a
structured `stale_expansion` response with a rerun-compass recovery action
instead of serving stale route material.

## Candidate Classification

The compass command should classify internal candidates before budgeting output.

### Route Candidate Criteria

A candidate can become a route candidate when it has:

- bounded path scope
- a meaningful owner, component, behavior surface, or workflow role
- at least one matched intent facet
- a reason that can be expressed as a first-pass evidence action

### Coverage Diagnostic Criteria

A candidate becomes a coverage diagnostic when it is:

- a broad fallback such as coverage paths without existing nodes
- a stale-path or partial-refresh signal
- a candidate-window truncation signal
- a graph agreement or generation concern
- a low-confidence map maintenance issue

Coverage diagnostics can lower confidence, request expansion, or recommend map
maintenance after live evidence work. They cannot be primary route candidates.

Broad fallback suppression is structural, not title-text based. The runtime must
classify fallback material from typed metadata such as node type, attrs,
coverage relation, path-count thresholds, or explicit fallback provenance. It
must not rely on matching a display title such as `Coverage paths not in existing
nodes`.

### Expansion Candidate Criteria

A candidate becomes expansion-only when it may matter but is not needed for the
first-pass route, such as:

- graph neighbors
- adjacent risk surfaces
- broad related paths
- raw candidate universe entries
- long coverage details

## Coverage Gate

Every compass packet must account for the best available facet set.

- In mechanical draft mode (`--query` only), facets are low-confidence
  `mechanical_query_facets` derived from raw terms, aliases, and match signals.
- In precision mode (`--semantic-intake-file` or `--query-plan-file`), facets
  come from agent-owned `semantic_intake.intent_facets` and concept decisions.
- The runtime must label which source was used, so workflows know whether the
  packet is a draft route or a semantic-intake-backed route.

Valid coverage states:

- `covered_for_first_pass`
- `partial`
- `separate_lane`
- `missing`
- `needs_expansion_before_fix_claim`
- `needs_user_clarification`

If an intent facet has no route candidate and no coverage diagnostic, the
packet must mark that facet as `needs_expansion_before_fix_claim` or
`needs_user_clarification`. The packet must not silently omit the facet to stay
short.

## Workflow Consumption Rules

Generated workflows should consume project cognition as:

```text
project-cognition compass
  -> read first_pass_paths
  -> prove or reject route with live evidence
  -> expand only when coverage_state or evidence requires it
```

Rules:

1. `first_pass_paths` and `minimal_live_reads` are not final edit scope.
2. Before production edits, the agent must satisfy or explicitly rule out each
   lane's `before_fix_claim` items.
3. Coverage diagnostics affect confidence and closeout; they do not become
   route candidates.
4. `expansion_ref` is a normal continuation path, not a failure state.
5. Final closeout must record actual changed paths, changed behavior surfaces,
   verification evidence, and project-cognition refresh outcome based on live
   work.

## Readiness Semantics

`compass` must preserve the current project-cognition runtime readiness values:

- `query_ready`: compass packet is usable as a first evidence route.
- `review`: use the packet, but inspect only first-pass reads until evidence
  proves or rejects the route.
- `needs_rebuild`: reserve for missing, unusable, schema-invalid, or
  rebuild-required baselines.
- `blocked`: report the runtime blocker and do not imply route confidence.
- `unsupported_runtime`: report the unsupported runtime and do not create route
  confidence.

Compass-specific guidance belongs in `compass_state` and
`recommended_next_action`, not in new readiness values. Recommended
`compass_state` values:

- `usable`
- `usable_with_review`
- `needs_semantic_intake`
- `needs_expansion_before_fix_claim`
- `needs_user_clarification`
- `stale_expansion`
- `blocked`

## Localized And Symptom-First Input

For CJK, mixed-language, colloquial, and symptom-first prompts:

- The CLI should reuse the existing `agent_normalization` object shape when
  appropriate.
- The CLI should not invent translations or synthetic concepts.
- The compass packet may include project vocabulary hints and first-pass live
  search terms.
- The agent still writes or carries semantic interpretation before making source
  behavior claims.

Recommended shape:

```json
{
  "agent_normalization": {
    "required": true,
    "reason": "raw_terms_did_not_match_project_aliases",
    "triggers": ["cjk_or_mixed_language_query"],
    "action": "write_semantic_intake_from_alias_catalog",
    "reminder": "Translate user language into project vocabulary before fix claims."
  }
}
```

## Example: Desktop Model Switch Failure

Given a symptom that includes:

- failed provider/model switch
- `runtimeOverride.providerId`
- `runtimeOverride.modelId`
- DeepSeek model id
- CLI startup exit code 143
- square glyphs
- too-small desktop viewport

The compass packet should produce separate lanes:

1. Provider/model runtime switch
   - desktop model selector
   - sessions API or store
   - server runtime override handler
   - CLI startup or runtime env boundary
   - provider registry/model catalog
   - relevant tests

2. UI readability and layout
   - global CSS and font stack
   - app zoom persistence
   - Tauri window minimum size
   - chat error rendering component
   - relevant desktop tests

It should suppress broad coverage fallback nodes from primary route selection
and report them as coverage diagnostics.

## Required Surface Changes

Runtime:

- `tools/project-cognition/internal/cli/cli.go`
- `tools/project-cognition/internal/query/lexicon.go`
- `tools/project-cognition/internal/query/query.go`
- a new compass package or focused files under `tools/project-cognition/internal/query/`
- `tools/project-cognition/internal/store/store.go`
- runtime tests under `tools/project-cognition/internal/query` and
  `tools/project-cognition/internal/cli`
- CLI help and command-surface tests for the hard-coded `project-cognition`
  command list
- release and install compatibility surfaces for the standalone
  `project-cognition` binary
- launcher/runtime compatibility tests that verify generated
  `{{specify-subcmd:project-cognition ...}}` placeholders can render `compass`
  and `expand` invocations through the pinned binary

Workflow surfaces:

- `templates/commands/*.md` where project cognition is used for brownfield
  intake
- `templates/command-partials/common/context-loading-gradient.md`
- `templates/command-partials/common/planning-context-loading-gradient.md`
- `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- `templates/project-handbook-template.md`

Integration and docs:

- `src/specify_cli/project_cognition_runtime.py`
- `src/specify_cli/launcher.py`
- `src/specify_cli/integrations/base.py`
- relevant integration rendering tests
- `.github/workflows/release.yml`
- `.github/workflows/release-project-cognition.yml`
- `tools/project-cognition/install.sh`
- `tools/project-cognition/install.ps1`
- `README.md`
- `PROJECT-HANDBOOK.md`

## Testing Strategy

Runtime tests should cover:

- `compass` returns a compact packet for a focused query.
- `compass --query` marks mechanical facet coverage as draft quality.
- `compass --semantic-intake-file` and `compass --query-plan-file` use
  agent-owned facets for strict coverage accounting.
- broad fallback nodes are suppressed from `evidence_lanes`.
- broad fallback nodes appear as `coverage_diagnostics`.
- broad fallback suppression uses typed metadata or structural provenance, not
  display-title matching.
- first-pass paths are budgeted while uncovered facets remain visible.
- CJK or mixed-language prompts set agent-normalization diagnostics without
  synthetic translation.
- `expansion_ref` points to stored sections for raw candidates and related
  paths.
- `expand` returns the requested section without requiring chat-level raw dumps.
- stale or missing expansion bundles return structured recovery guidance.
- `readiness=review` preserves first-pass routes and coverage diagnostics.
- current readiness values stay `query_ready`, `review`, `blocked`,
  `needs_rebuild`, or `unsupported_runtime`.

Workflow/template tests should cover:

- generated workflows call or recommend `project-cognition compass` for default
  brownfield intake.
- workflows still allow the advanced `lexicon -> semantic_intake -> query` flow.
- workflow wording says first-pass paths are not final edit scope.
- coverage diagnostics are not route candidates.
- `sp-debug`, one planning workflow, one execution workflow, and skills-based
  integrations all preserve the same compass contract.
- launcher rendering tests cover `project-cognition compass` and
  `project-cognition expand`.

Experience tests should cover:

- a mixed Chinese/English desktop model-switch symptom does not produce a
  20k-line chat payload.
- the default packet includes multiple lanes when the symptom has independent
  surfaces.
- agent-facing output includes where, why, verification hints, follow-up
  surfaces, and coverage state.

## Acceptance Criteria

- Default project-cognition intake returns a compass packet rather than a raw
  path universe.
- The packet remains compact but does not hide uncovered facets.
- Broad fallback nodes never appear as primary route candidates.
- Agents cannot reasonably infer that first-pass paths are the complete edit
  list.
- Expansion is explicit and available when first-pass evidence is insufficient.
- Existing `lexicon` and `query` workflows remain usable for advanced routing.
- Documentation and generated workflow guidance consistently describe project
  cognition as a compass and live code as proof.

## Rollout

1. Add runtime `compass` payload types and classification logic.
2. Add CLI command routing for `project-cognition compass`.
3. Add expansion bundle storage and `project-cognition expand`.
4. Update workflow guidance to consume compass packets by default.
5. Preserve and document the advanced `lexicon -> semantic_intake -> query`
   path.
6. Add runtime, template, integration, and experience regression tests.
7. Use downstream projects to rebuild or refresh cognition baselines when they
   need the new compass behavior.

## Design Decision

Use the two-layer compass architecture:

- default: short, coverage-aware first evidence path
- expansion: explicit full map and raw diagnostics

This satisfies the product goal: project cognition should provide a precise
starting route for the agent, while making it impossible to confuse a short
default packet with the complete scope of work.
