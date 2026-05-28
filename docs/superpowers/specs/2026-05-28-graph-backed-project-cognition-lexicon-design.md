# Graph-Backed Project Cognition Lexicon Design

**Date:** 2026-05-28
**Status:** Approved direction
**Owner:** Codex

## Summary

This design changes the project cognition query model from query-text-first
matching to graph-backed concept selection.

The expected model is:

- `project-cognition lexicon` reads the current project cognition graph first
- the runtime returns existing project concepts, aliases, paths, evidence, and
  ranked candidates
- the user's natural-language request is used to filter and rank those existing
  concepts, not to invent graph facts
- the agent selects and rejects concepts from that candidate set
- `project-cognition query --query-plan` returns the task-local navigation
  bundle from the selected graph concepts

This is a shared workflow contract. It must be implemented through the common
project cognition partials and passive skills, then consumed by `sp-*`
workflows through their existing `--intent` profiles. It must not be fixed only
inside `sp-quick`.

## Problem

Current generated workflow guidance describes a two-step project cognition
flow:

1. Run `project-cognition lexicon`.
2. Use returned map terms to build a `query_plan`.
3. Run `project-cognition query --query-plan`.

That product contract is sound, but the current runtime implementation is too
thin. `lexicon` tokenizes the user request and wraps those terms as
`concept_candidates`. For a request such as "the GUI feels laggy and not
smooth", the runtime may return candidates derived from the text rather than
project concepts such as GUI, rendering, event loop, performance, main window,
login, or registration.

This creates two failures:

- Downstream agents see a command named `lexicon` and assume it has already
  consulted project cognition, even when it only reflected the raw request.
- The workflow loses the main value of project cognition: selecting from what
  the current project already knows instead of free-form searching from user
  wording.

The right behavior is closed-world concept selection with explicit fallback.
When the graph knows about GUI, login, and registration, the runtime should
surface those project nodes and rank GUI-related nodes for a GUI smoothness
request. When the graph has no relevant concept, the runtime should report
unmapped intent or missing coverage instead of fabricating candidates from the
request text.

## Goals

- Make `project-cognition lexicon` graph-backed by default.
- Treat project cognition nodes and aliases as the candidate universe.
- Use user text only as a matching, ranking, and disambiguation signal.
- Preserve the agent's role as concept selector: choose selected concepts,
  reject unsafe or irrelevant concepts, and write selection reasons.
- Keep `--intent` as a ranking and bundle-shaping profile, not a separate
  direct-query branch.
- Update shared project cognition templates so all `sp-*` workflows inherit
  the same mental model.
- Return coverage gaps, unmapped intent, or weak matches honestly when the
  graph cannot support the request.
- Keep live repository evidence as the proof layer. Project cognition remains
  advisory navigation.

## Non-Goals

- Do not remove the `lexicon -> query_plan -> query` workflow shape.
- Do not make agents read raw SQLite graph data directly.
- Do not make `--intent` disappear. It remains useful as a profile.
- Do not require every workflow template to duplicate the full project
  cognition protocol.
- Do not treat project cognition output as source-code proof.
- Do not force a full map rebuild for ordinary weak matches when live evidence
  and localized update guidance are enough.

## Design

### 1. Candidate Universe Comes From The Graph

`project-cognition lexicon` should load graph-backed candidate material from
`.specify/project-cognition/project-cognition.db` when the runtime baseline is
usable.

The candidate universe should include:

- nodes, including id, type, title, confidence, and paths
- node attributes that encode aliases, domain, owner, workflow, or route hints
- evidence ids and evidence source paths
- path index rows
- path segments and filename-derived aliases
- observation summaries when they are available and evidence-backed
- verification and route hints when graph data contains them

The runtime may derive lightweight aliases from project data, but it must keep
provenance clear. A derived alias is still attached to an existing graph node;
it is not a new project concept.

### 1A. Alias Material Source

The first implementation must not depend on an unpopulated alias table. Today
the runtime schema contains `alias_index`, but the build/import path primarily
imports nodes, edges, observations, and path index rows. Therefore the MVP
lexicon must derive candidate aliases at query time from already imported graph
data:

- node titles
- node ids
- node types
- node attrs, including any `aliases`, `domain`, `owner`, route, or workflow
  fields already present in scan artifacts
- path index rows and path segments
- evidence source paths
- observation summaries when evidence-backed

If an implementation chooses to persist aliases in `alias_index` or
`symbol_index` for performance or richer matching, that is not a lexicon-only
change. It must update scan artifact contracts, `map-build`, import code, and
validation tests in the same pass so the persisted index has a reliable data
source. Tests that require aliases in the first pass should seed node attrs,
paths, or evidence-backed observations unless the implementation also ships
alias-index population.

### 2. User Query Ranks Existing Concepts

The user's request is a selector over the graph-backed candidate universe.

For example:

```text
User request:
The whole GUI program feels laggy, not smooth, and like the refresh rate is too
low.
```

If the graph contains GUI, login, registration, rendering, event loop, and
performance concepts, `lexicon` should rank GUI/rendering/performance concepts
above login or registration. Login and registration may still be returned as
related but weak candidates if they belong to GUI flows. They should not be
selected by default when the user described a whole-program smoothness problem.

The runtime should return enough evidence for the agent to decide:

- why a candidate matched
- which terms matched
- which aliases matched
- which path or capability owns the candidate
- whether the match is broad, weak, ambiguous, or high-confidence

### 3. Closed-World Default With Fallback

The default behavior is closed-world selection:

- selected concepts must refer to existing graph concepts
- rejected concepts should also refer to existing graph concepts when possible
- expanded queries may contain natural-language refinements, but they must not
  pretend to be graph facts

If the graph has no relevant candidates, `lexicon` should return an explicit
coverage state instead of manufacturing useful-looking candidates from the
user's words.

Useful fallback fields include:

- `unmapped_intent`
- `missing_coverage`
- `weak_matches`
- `coverage_gap_reason`
- `suggested_live_reads`
- `recommended_next_action`

The agent may then continue with bounded live repository evidence when the
workflow allows it, or recommend `sp-map-update` or `sp-map-scan -> sp-map-build`
according to the existing freshness and rebuild rules.

### 4. Intent Is A Profile, Not A Query Branch

`--intent` should not decide whether project cognition reads the graph. All
supported intents use the same graph-backed candidate universe.

The intent controls weighting, returned detail, and downstream bundle shape:

- `plan`: prefer capabilities, workflows, product boundaries, specs, plans,
  acceptance criteria, and architectural ownership.
- `implement`: prefer source paths, owning modules, callsites, tests,
  generated assets, verification routes, and likely affected surfaces.
- `debug`: prefer symptoms, reproduction surfaces, logs, profiling hooks,
  historical defects, state surfaces, and root-cause investigation lanes.
- `research` and `discussion`: prefer feasibility signals, external evidence
  boundaries, source-grounded options, and handoff-ready route hints.

The runtime can use these profiles to adjust candidate scores and route-pack
contents, but it should not implement separate free-form query behavior per
intent.

### 5. Agent Selection Contract

The agent consumes the `lexicon` payload and writes a `query_plan`.

Required agent decisions:

- `selected_concepts`: graph-backed candidates that match the user's task and
  workflow objective
- `rejected_concepts`: candidates that were considered but not safe or relevant
  enough to select
- `selection_reason`: why each selected or rejected concept was handled that
  way
- `expanded_queries`: natural-language or domain-language refinements used only
  to improve retrieval
- `paths`: selected or hinted graph-backed paths when the candidate evidence
  justifies them

The compatibility fields remain string arrays, but they are not enough to
preserve reviewable decisions. The query plan must also support
`concept_decisions`:

```json
{
  "selected_concepts": ["concept:GEN-0001:N-gui"],
  "rejected_concepts": ["concept:GEN-0001:N-login"],
  "concept_decisions": [
    {
      "concept_id": "concept:GEN-0001:N-gui",
      "decision": "selected",
      "selection_reason": "The user described whole-program GUI smoothness and this node owns the GUI surface.",
      "confidence": "high"
    },
    {
      "concept_id": "concept:GEN-0001:N-login",
      "decision": "rejected",
      "selection_reason": "Login is a GUI flow but the request is not authentication-specific.",
      "confidence": "medium"
    }
  ]
}
```

`selection_reason` remains as a global summary for backward compatibility.
`concept_decisions` is the durable per-concept explanation. When both are
present, `query` should prefer `concept_decisions` for per-concept rationale and
use the global `selection_reason` only as a summary. Older agents may still send
only `selected_concepts`, `rejected_concepts`, and `selection_reason`; `query`
must accept that shape but should report weaker traceability.

The agent must not treat `lexicon` as the final answer. The query is complete
only after readiness has been interpreted, `query --query-plan` has returned a
task-local bundle, and live evidence has proven any technical claims.

### 6. Query Uses The Selected Concepts

`project-cognition query --query-plan` should use selected graph concepts to
return a task-local navigation bundle.

The bundle should include:

- selected and rejected concepts
- affected nodes
- route pack
- minimal live reads
- relevant paths
- evidence traces
- verification routes
- missing coverage
- ambiguity, conflicts, and weak coverage
- subgraph slices needed by the active workflow

When a query plan names selected concepts, query should resolve those concepts
through graph ids or stable candidate ids, not only through path hints.

### 6A. Generation And Candidate Provenance

`lexicon` and `query` must preserve the graph generation that made the
candidate set meaningful.

The lexicon payload should include:

- `active_generation_id`
- `lexicon_generation_id`
- `candidate_universe_version`
- `candidate_universe.counts`
- `candidate_universe.truncated`
- `candidate_universe.selection_window`

Candidate ids must be stable inside one active generation. The first
implementation should use graph node ids as the compatibility concept ids when
the candidate maps one-to-one to a node:

```text
concept:<active_generation_id>:<node_id>
```

When a candidate represents a specific alias, path segment, or evidence-backed
derived match for the same node, the candidate id may append a source-qualified
suffix:

```text
concept:<active_generation_id>:<node_id>:alias:<normalized-alias-hash>
concept:<active_generation_id>:<node_id>:path:<normalized-path-hash>
```

The query plan may carry both `selected_concepts` and
`lexicon_generation_id`. If the graph active generation changes between
`lexicon` and `query`, `query` must not silently reinterpret closed-world
selections against a different graph. It should return an ambiguity or coverage
gap state with a clear reason, such as `lexicon_generation_mismatch`, and ask
the agent to rerun `lexicon` unless the selected ids are still valid and the
runtime can prove compatibility.

### 7. Shared Template Contract

Because most `sp-*` workflows use project cognition, the mental model must live
in shared template surfaces.

Shared guidance should say:

```text
Run `project-cognition lexicon` to retrieve graph-backed project concept
candidates. Inspect the returned candidates, select and reject existing project
concepts, write selection reasons, then construct `query_plan` and run
`project-cognition query --query-plan`.
```

Shared guidance should avoid saying that the agent should generate a query plan
from "returned map terms" if the phrase can be read as raw keyword expansion.
The more precise wording is "returned graph-backed project concept candidates."

Individual workflow templates should only declare their intent profile and any
workflow-specific consumption rules. They should not duplicate the full
lexicon/query contract.

### 8. Integration Renderers Are First-Class Surfaces

Generated output is not produced only from `templates/**`. Integration renderers
and appenders can inject project cognition guidance after template processing.
Those generated addenda must use the same graph-backed concept-selection
contract as the shared partials.

In particular, generation code must not keep appending wording such as
"translate raw user intent into a query plan using returned map terms" when the
shared templates have moved to graph-backed project concept candidates. The
implementation plan must audit generated Markdown, TOML, skills-based, Codex,
and integration-specific command surfaces, including appenders in
`src/specify_cli/integrations/base.py` and agent-specific templates under
`src/specify_cli/integrations/**`.

## Required Surface Changes

Implementation should update these surfaces together:

- `tools/project-cognition/internal/query/lexicon.go`
- `tools/project-cognition/internal/query/query.go`
- `tools/project-cognition/internal/store/**` if graph lookup helpers are
  needed
- `tools/project-cognition/internal/store/import.go`
- `tools/project-cognition/internal/store/schema.go`
- `tools/project-cognition/internal/build/build.go`
- `tools/project-cognition/internal/scanartifacts/**`
- `tools/project-cognition/internal/cli/cli.go` if new JSON fields or options
  are exposed
- `templates/command-partials/common/context-loading-gradient.md`
- `templates/command-partials/common/planning-context-loading-gradient.md`
- `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- workflow templates that directly mention lexicon/query, including
  `templates/commands/{specify,clarify,deep-research,plan,tasks,analyze,fast,quick,implement,debug,discussion,checklist,prd-scan,map-build}.md`
- `README.md`
- `PROJECT-HANDBOOK.md`
- `src/specify_cli/integrations/base.py`
- integration-specific appenders and templates under
  `src/specify_cli/integrations/**`
- generated integration tests for Markdown, TOML, skills-based, and Codex
  surfaces
- project cognition runtime tests
- template alignment tests that assert the project cognition contract

The implementation should prefer shared partial wording over repetitive
workflow-local edits wherever possible.

## JSON Contract Changes

`lexicon` should keep the current top-level fields but strengthen their
meaning.

Expected top-level fields:

- `readiness`
- `recommended_next_action`
- `intent`
- `query`
- `active_generation_id`
- `lexicon_generation_id`
- `candidate_universe_version`
- `terms`
- `available_terms`
- `concept_candidates`
- `query_planning_contract`
- `candidate_universe`
- `matching_profile`
- `unmapped_intent`
- `missing_coverage`

Each `concept_candidates` item should include:

- `concept_id`
- `node_id`
- `label`
- `title`
- `target_type`
- `node_type`
- `aliases`
- `matched_terms`
- `colloquial_matches`
- `paths`
- `evidence_ids`
- `confidence`
- `score`
- `rank`
- `domain`
- `owner`
- `route_hints`
- `verification_hints`
- `disambiguation_hint`
- `selection_guidance`

Fields may be omitted when unavailable, but the runtime should prefer empty
lists or explicit missing coverage over misleading placeholder values.

`query_plan` should accept these fields:

- `raw_query`
- `expanded_queries`
- `paths`
- `path_hints`
- `selected_concepts`
- `rejected_concepts`
- `concept_decisions`
- `selection_reason`
- `lexicon_generation_id`
- `reason` as the compatibility alias for `selection_reason`

Each `concept_decisions` item should include:

- `concept_id`
- `decision`: `selected`, `rejected`, or `deferred`
- `selection_reason`
- `confidence`
- optional `paths`
- optional `risk`

`selected_concepts` and `rejected_concepts` stay as string-array compatibility
fields. Implementations should not upgrade them to object arrays unless they
also preserve the old string-array input shape.

## Testing Strategy

Runtime tests should cover:

- lexicon reads graph nodes instead of only user query terms
- graph aliases are returned as candidates
- path-derived aliases attach to existing graph nodes
- `implement` ranks source/test/verification-heavy candidates higher
- `plan` ranks capability/workflow/spec candidates higher
- `debug` ranks symptom/repro/log/profiling candidates higher
- irrelevant graph concepts are returned as weak or rejected guidance rather
  than silently selected
- no relevant graph candidates produces `unmapped_intent` or missing coverage
- query resolves selected concept ids to affected nodes and minimal live reads
- query preserves and consumes per-concept decisions
- query detects `lexicon_generation_id` mismatch when active generation changes
- missing or blocked runtime state preserves existing readiness behavior
- alias tests either seed query-time-derived alias sources or verify
  alias-index population through build/import in the same pass

Template and integration tests should cover:

- shared partials teach graph-backed candidate selection
- generated `sp-*` workflows still call `lexicon` before `query`
- workflow-local wording does not imply raw query-token candidates are enough
- passive skills teach `--intent` as a profile
- Codex skill generation receives the same shared contract
- integration renderers and appenders no longer inject the old "returned map
  terms" mental model after template processing

## Rollout

1. Add graph lookup helpers for nodes, aliases, paths, and evidence summaries.
2. Replace token-only lexicon candidate construction with graph-backed
   candidate ranking.
3. Add intent profiles for ranking and bundle shaping.
4. Add `active_generation_id`, `lexicon_generation_id`,
   `candidate_universe_version`, and stable candidate id provenance.
5. Add `concept_decisions` while preserving string-array compatibility for
   `selected_concepts` and `rejected_concepts`.
6. Teach query to resolve selected concept ids, not just path hints, and to
   reject or flag generation mismatches.
7. Decide whether alias matching is query-time-derived only for the first pass
   or persisted through `alias_index`; if persisted, update build/import and
   scan artifact contracts in the same pass.
8. Update shared project cognition partials and passive skills.
9. Update integration renderers and generated addenda.
10. Update direct workflow wording only where it bypasses the shared partial.
11. Update README, handbook, and generated integration tests.
12. Run Go runtime tests and Python template/integration tests.

## Open Decisions

- Whether `lexicon` should return the full candidate universe for small
  projects or only ranked candidates plus universe counts.
- Whether Chinese and other non-ASCII user queries need a dedicated tokenizer
  in the first pass or can rely on alias matching plus substring scoring.
- Whether `query` should reject selected concept ids that were not present in
  the preceding `lexicon` payload, or accept any valid graph id for resumability.
- Whether persisted `alias_index` population should ship in the first runtime
  pass or follow after query-time derivation proves the matching behavior.
