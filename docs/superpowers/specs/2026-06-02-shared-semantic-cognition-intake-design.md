# Shared Semantic Cognition Intake Design

**Date:** 2026-06-02
**Status:** Approved direction
**Owner:** Codex

## Summary

This design upgrades project cognition intake from raw-query candidate ranking
to shared semantic normalization for all brownfield workflows.

The expected model is:

- `project-cognition lexicon` exposes a compact project alias and concept
  catalog from the active graph.
- The agent combines the user's natural-language prompt with that project
  vocabulary and writes an explicit `semantic_intake` object.
- The runtime searches with the normalized query, intent facets, alias
  interpretations, negative constraints, and workflow intent.
- Candidate selection is gated by facet coverage, not only top lexical or vector
  similarity.
- Workflow templates consume this shared intake contract through common
  project cognition partials instead of fixing one command at a time.

This must apply across the generated `sp-*` brownfield workflow family. `sp-debug`
is a high-signal consumer because defects often start from vague symptoms, but
the same recall failure can affect planning, implementation, discussion,
analysis, checklist generation, PRD reconstruction, and map maintenance.

## Problem

The current graph-backed lexicon implementation improved the old token-only
model by loading the full active graph candidate universe before ranking. That
fix ensures a relevant candidate outside the store's initial window can still
rank into the returned candidate list.

However, the user-facing workflow still has a semantic gap:

1. The raw user prompt is sent directly to `project-cognition lexicon`.
2. The runtime ranks graph concepts from the raw prompt terms and returns a
   limited candidate window.
3. The agent selects only from the returned window.

This fails when the user's prompt is ambiguous, informal, incomplete, translated,
or imprecise. The agent may understand the likely intent, but the retrieval
layer may still miss it because the raw prompt does not align with project
aliases, paths, or concept summaries.

For example, a user might ask whether "Token usage for today is 230M" is wrong.
An agent can infer likely facets such as token accounting, local session
records, aggregation, daily rollup, date windows, duplicate counting, and unit
conversion. A direct lexical or vector match over the raw prompt may instead
over-rank a broad `Claude CLI` concept because it matches the visible words,
while missing the deeper accounting and aggregation intent.

The current contract makes that failure hard to detect because the agent's
semantic interpretation is implicit. If routing goes wrong, reviewers cannot
tell whether the agent misunderstood the user, the lexicon failed to recall the
right concept, or the query plan selected a plausible but incomplete candidate.

## Goals

- Add a shared semantic intake contract used by all brownfield `sp-*` workflows.
- Make agent-side prompt normalization explicit and auditable.
- Use a project alias catalog before retrieval so agents can translate user
  language into project language.
- Search with normalized intent, facets, constraints, and workflow profile, not
  only raw query text.
- Treat vector similarity as one retrieval signal, not the source of truth.
- Gate selected candidates by facet coverage and explicit rejection rationale.
- Preserve the current `lexicon -> query_plan -> query` shape where possible,
  while adding the missing semantic intake layer.
- Keep project cognition advisory. Live repository evidence still proves
  technical claims.
- Implement through shared command partials, passive skills, runtime contracts,
  and tests so the behavior cannot remain only a remembered discussion.

## Non-Goals

- Do not make project cognition the authority for current source behavior.
- Do not require agents to read raw SQLite graph data.
- Do not dump unbounded source excerpts or full graph documents into every
  workflow prompt.
- Do not make vector search mandatory or sufficient.
- Do not fix only `sp-debug`.
- Do not require user clarification when the agent can derive a bounded,
  evidence-checkable semantic interpretation from project vocabulary.

## Affected Workflows

The shared intake contract applies to brownfield workflows that reason about
existing project structure, behavior, or generated workflow surfaces:

- `sp-discussion`
- `sp-specify`
- `sp-clarify`
- `sp-deep-research`
- `sp-plan`
- `sp-tasks`
- `sp-analyze`
- `sp-fast`
- `sp-quick`
- `sp-implement`
- `sp-debug`
- `sp-checklist`
- `sp-prd-scan`
- `sp-map-update` when classifying changed paths or affected surfaces

Each workflow keeps its own intent profile, but all use the same semantic
intake primitives.

## Design

### 1. Alias Catalog Comes Before Narrow Retrieval

`project-cognition lexicon` should expose a compact alias catalog from the active
graph before the workflow depends on top-N candidate ranking.

The catalog should include compact project vocabulary, not full source evidence:

- concept id
- title
- aliases
- owner
- domain
- node type
- confidence
- path hints
- route hints
- verification hints
- evidence summary tags or short observation labels when available

The catalog may be paginated or budgeted for large projects. The important
property is that the agent can see enough project language to normalize vague
user wording before retrieval narrows the search.

### 2. Agent Writes Explicit `semantic_intake`

After reading the alias catalog, the agent writes a semantic intake object.
This object is the bridge between user language and project language.

Expected fields:

```json
{
  "raw_query": "Token usage today says 230M, is that wrong?",
  "workflow_intent": "debug",
  "normalized_query": "Investigate local CLI session token usage aggregation and daily accounting accuracy.",
  "intent_facets": [
    "token accounting",
    "usage aggregation",
    "local session records",
    "daily total",
    "date window",
    "duplicate counting",
    "unit conversion"
  ],
  "negative_constraints": [
    "not only CLI launcher invocation behavior",
    "not general model pricing"
  ],
  "alias_interpretations": [
    {
      "alias": "usage",
      "meaning": "token usage aggregation",
      "confidence": "high"
    }
  ],
  "open_semantic_questions": []
}
```

The agent may include inferred facets only when they are reasonable
interpretations of the prompt plus project vocabulary. It must mark uncertain
facets and carry them as coverage requirements or open questions instead of
quietly treating them as facts.

### 3. Hybrid Retrieval Uses Normalized Intent

`project-cognition query` should accept `semantic_intake` or equivalent query
plan fields and use them for retrieval.

Retrieval signals should include:

- alias exact and partial matches
- path and module name matches
- full-text search or BM25-style evidence summary matches
- vector similarity when available
- graph neighbor expansion from matched concepts
- workflow-profile weighting
- explicit negative constraints

Raw query text remains useful, but it should not be the only input to ranking.
Normalized query and facets should improve recall when the user uses wording
that differs from project terminology.

### 4. Facet Coverage Gate

Candidate selection must prove coverage of the semantic facets that matter for
the workflow.

For each selected or rejected candidate, the query plan should record:

- which facets it covers
- which facets it fails to cover
- why it was selected or rejected
- whether the match is lexical, alias-based, vector-based, path-based, or
  inferred from graph neighbors
- confidence and risk

Example rejection:

```json
{
  "concept_id": "concept:GEN-cli:N-claude-cli-launcher",
  "decision": "rejected",
  "selection_reason": "Matches Claude CLI words but does not cover token accounting, aggregation, daily rollup, or unit conversion facets.",
  "covered_facets": ["local CLI"],
  "missing_facets": ["token accounting", "usage aggregation", "daily total"],
  "confidence": "high",
  "risk": "lexical false positive"
}
```

This gate prevents top similarity from becoming route truth.

### 5. Escalation When Coverage Is Weak

A workflow must not blindly continue from a weak first-pass match.

Escalate when any of these are true:

- top candidates cover only surface words and miss core facets
- `positive_matches` is low or only broad concepts match
- candidate window is truncated and relevant facets remain uncovered
- query language is cross-lingual or tokenization is likely weak
- the prompt is informal, incomplete, or asks whether a computed result is wrong
- selected candidates conflict on truth ownership
- returned `minimal_live_reads` do not cover enough of the normalized intent

Escalation options:

- request a larger or next-page alias catalog
- run a broadened semantic query
- include additional normalized facets
- inspect returned minimal live reads before root-cause or planning claims
- ask the user one concise clarification question only when product semantics
  remain genuinely ambiguous

### 6. Workflow Profiles Shape Weighting, Not Intake Mechanics

The shared intake mechanics are consistent. Workflow profiles only shape which
facets and routes are weighted higher.

- `discussion`, `specify`, and `clarify`: product semantics, ambiguity, user
  decisions, capability boundaries, downstream obligations.
- `deep-research`: feasibility unknowns, external evidence boundaries,
  implementation chain proof, demo or spike surfaces.
- `plan` and `tasks`: capabilities, ownership, architecture, constraints,
  implementation routes, verification strategy.
- `fast`, `quick`, and `implement`: source paths, tests, generated assets,
  behavior surfaces, verification commands.
- `debug`: symptoms, reproduction paths, logs, state surfaces, truth owners,
  control and observation boundaries.
- `checklist`: requirement coverage, policy checks, acceptance criteria, known
  ambiguity.
- `prd-scan`: current-state product behavior, UI/API surfaces, runtime
  semantics, configuration, protocols, state machines, error behavior.
- `map-update`: changed-path classification, affected surfaces, adoptable
  concepts, uncertain closure, ignored or excluded paths.

### 7. Query Plan Contract

The query plan should accept the current concept fields plus semantic intake
fields.

Expected fields:

```json
{
  "raw_query": "...",
  "semantic_intake": {
    "workflow_intent": "debug",
    "normalized_query": "...",
    "intent_facets": [],
    "negative_constraints": [],
    "alias_interpretations": [],
    "open_semantic_questions": []
  },
  "selected_concepts": [],
  "rejected_concepts": [],
  "concept_decisions": [],
  "expanded_queries": [],
  "paths": [],
  "lexicon_generation_id": "...",
  "selection_reason": "..."
}
```

`concept_decisions` should support:

- `concept_id`
- `decision`
- `selection_reason`
- `covered_facets`
- `missing_facets`
- `match_sources`
- `confidence`
- `risk`
- `paths`

Compatibility aliases such as `path_hints` and `reason` can remain supported,
but generated workflows should teach the richer shape.

### 8. Runtime API Shape

The runtime can evolve in small steps.

Recommended command shape:

```text
project-cognition lexicon --intent <intent> --query "<raw_query>" --mode catalog --format json
project-cognition query --intent <intent> --query-plan-file <query_plan_json> --format json
```

Alternative compatible shape:

```text
project-cognition lexicon --intent <intent> --query "<raw_query>" --include-catalog --limit <n> --format json
```

The important contract is not the exact flag name. The runtime must return
enough compact alias material for semantic normalization before a workflow
trusts a narrow ranked candidate window.

### 9. Template Contract

Shared workflow wording should say:

```text
Run project cognition semantic intake before broad source inspection. Retrieve
the project alias catalog, write semantic_intake from the user prompt plus
project vocabulary, then run project-cognition query using normalized_query,
intent_facets, selected_concepts, rejected_concepts, concept_decisions, and
lexicon_generation_id. Candidate selection must satisfy facet coverage; do not
trust top similarity alone.
```

Workflow-local snippets should only specify the intent profile and any
workflow-specific consumption rules.

## Required Surface Changes

Runtime:

- `tools/project-cognition/internal/query/lexicon.go`
- `tools/project-cognition/internal/query/query.go`
- `tools/project-cognition/internal/store/store.go`
- `tools/project-cognition/internal/cli/cli.go`
- runtime tests under `tools/project-cognition/internal/query`,
  `tools/project-cognition/internal/store`, and
  `tools/project-cognition/internal/cli`

Shared generated workflow surfaces:

- `templates/command-partials/common/context-loading-gradient.md`
- `templates/command-partials/common/planning-context-loading-gradient.md`
- `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- direct workflow templates that mention lexicon or query planning
- `templates/project-handbook-template.md`

Integration renderers:

- `src/specify_cli/integrations/base.py`
- any integration-specific template or augmentation that injects cognition
  guidance

Docs:

- `README.md`
- `PROJECT-HANDBOOK.md`
- this design and the implementation plan that follows

Tests:

- template alignment tests
- generated integration tests for Markdown, TOML, skills-based, and Codex
  surfaces
- runtime contract tests for alias catalog, semantic intake parsing, hybrid
  retrieval, facet coverage, and escalation guidance

## Testing Strategy

Runtime tests should cover:

- lexicon catalog returns compact aliases for all active graph concepts within
  a budgeted or paginated contract
- query accepts `semantic_intake`
- normalized query and facets can retrieve a concept that raw query top-N misses
- negative constraints demote lexical false positives
- facet coverage appears in selected and rejected concept decisions
- truncated candidate windows produce escalation signals when uncovered facets
  remain
- cross-lingual or non-ASCII prompts do not silently produce overconfident
  lexical matches
- selected concept resolution still honors `lexicon_generation_id`

Template and integration tests should cover:

- shared partials mention alias catalog, `semantic_intake`,
  `normalized_query`, `intent_facets`, `negative_constraints`,
  `concept_decisions`, and facet coverage
- generated `sp-*` workflows no longer teach raw prompt to top-N candidate
  routing as sufficient
- `sp-debug` is not the only workflow that receives the new contract
- passive skills tell agents not to trust top vector or lexical similarity alone
- docs explain that project cognition remains advisory and live evidence still
  proves technical claims

## Rollout

1. Add runtime support for alias catalog payloads.
2. Add `semantic_intake` parsing and normalization fields to query plans.
3. Add retrieval weighting for normalized query, facets, aliases, paths, and
   negative constraints.
4. Add facet coverage fields to concept decisions and query output.
5. Teach shared partials and passive skills the shared semantic intake contract.
6. Update direct workflow snippets and integration renderers.
7. Update docs and handbook template.
8. Add regression tests that fail if only `sp-debug` receives the contract.
9. Run Go runtime tests and focused Python template/integration tests.

## Open Decisions

- Exact CLI flag shape for alias catalog mode.
- Whether catalog pagination is required in the first implementation or whether
  a budgeted compact payload is enough.
- Whether vector search is implemented immediately or the first version uses
  alias, FTS, path, and graph-neighbor retrieval.
- How to score facet coverage across workflow profiles.
- Whether generated workflows should always perform semantic intake or only do
  so for brownfield tasks with existing project cognition.
- Whether a missing alias catalog should degrade to current graph-backed
  lexicon behavior or force live minimal reads before route claims.
