# Agent-Owned Cognition Normalization Design

**Date:** 2026-06-12
**Status:** Draft for user review
**Owner:** Codex
**Related designs:**
- `docs/superpowers/specs/2026-06-02-shared-semantic-cognition-intake-design.md`
- `docs/superpowers/specs/2026-06-03-cognition-intake-experience-alignment-design.md`

## Summary

Project cognition should treat the agent as the semantic decision maker and the
CLI as a structured navigation tool. When `project-cognition lexicon` receives
localized, mixed-language, colloquial, or symptom-first input, the CLI should
not try to become intelligent by translating that input into project concepts.
It should expose the alias catalog, raw lexical result, and a mechanical
diagnostic that tells the agent to perform semantic normalization.

The agent then translates user language into project language, records the
translation in `semantic_intake`, selects or rejects concepts by facet coverage,
adds project-language `repository_search_terms`, and only then calls
`project-cognition query`.

This design applies to all generated workflows that use project cognition, not
only `sp-debug`.

## Problem

A debug prompt such as:

```text
I installed, uninstalled, then installed again, and now the install confirmation
dialog is different from the first time.
```

or the equivalent Chinese user wording can return `score=0` from raw lexicon
ranking even when the repository has relevant project concepts. The failure is
not that the agent cannot understand the user. The failure is that the workflow
can let the raw score become the stopping point.

The current runtime is intentionally conservative:

- it ranks existing graph concepts from query terms
- it exposes the alias catalog and candidate universe
- it avoids inventing concepts from unmatched terms
- it does not perform general natural-language translation

That boundary is correct. The missing piece is stronger workflow guidance and a
small non-intelligent runtime signal that makes the agent-owned normalization
step hard to skip.

## Goals

- Make the agent the explicit owner of dynamic semantic judgment.
- Keep the CLI/tool layer mechanical, structured, and non-authoritative.
- Prevent `score=0` from being interpreted as "no relevant project concept."
- Teach every project-cognition workflow to bridge raw user language to project
  vocabulary before selecting concepts.
- Add a CLI diagnostic that signals "agent normalization required" without
  translating or selecting concepts for the agent.
- Preserve the existing rule: map points, code proves.
- Apply the rule across all workflows that use `project-cognition lexicon` and
  `project-cognition query`.

## Non-Goals

- Do not add general Chinese-to-English or cross-language intelligence to the
  CLI.
- Do not add a runtime synonym dictionary that silently maps user symptoms to
  project concepts.
- Do not create synthetic concept candidates from unmatched user terms.
- Do not make project cognition authoritative evidence for current source
  behavior.
- Do not fix only `sp-debug`.
- Do not require user clarification when the agent can make a bounded,
  evidence-checkable semantic interpretation from the alias catalog.

## Core Boundary

### CLI Responsibilities

The CLI may perform mechanical, auditable work:

- tokenize the raw query
- rank graph-backed concepts by raw lexical overlap
- return the alias catalog and compact route vocabulary
- return `score`, `matched_terms`, `missing_coverage`, readiness, and
  `minimal_live_reads`
- detect mechanical conditions such as CJK input, mixed-language input, and
  zero positive matches
- emit a diagnostic that instructs the agent to perform semantic normalization

The CLI must not decide what the user "really meant" beyond those mechanical
signals.

### Agent Responsibilities

The agent owns semantic judgment:

- interpret localized, colloquial, informal, and symptom-first user wording
- translate user wording into project vocabulary using the alias catalog
- identify workflow-specific facets that must be covered
- choose selected and rejected concepts by facet coverage
- write `semantic_intake`, `alias_interpretations`, `expanded_queries`, and
  `repository_search_terms`
- inspect returned `minimal_live_reads` before making source-behavior claims
- ask a user clarification question only when the semantic interpretation
  cannot be bounded from project vocabulary and live evidence

## Runtime Diagnostic

`project-cognition lexicon --mode catalog` should include a non-intelligent
diagnostic block when raw lexical ranking is not enough.

Recommended shape:

```json
{
  "agent_normalization": {
    "required": true,
    "reason": "raw_terms_did_not_match_project_aliases",
    "triggers": [
      "zero_positive_matches",
      "cjk_or_mixed_language_query"
    ],
    "action": "write_semantic_intake_from_alias_catalog",
    "reminder": "Do not stop at score=0. Translate user language into project vocabulary using the alias catalog."
  }
}
```

The field is advisory guidance to the agent. It is not a route decision.

Recommended trigger rules:

- `positive_matches == 0`
- `missing_coverage` includes `no_graph_candidate_matched_query`
- the raw query contains CJK text or mixed CJK and ASCII text
- the alias catalog is present and non-empty

If the graph is missing, stale, blocked, or greenfield-empty, existing readiness
and recovery guidance remains primary. The diagnostic should not hide runtime
agreement failures.

## Workflow Prompt Contract

All project-cognition workflow prompts should teach the same rule:

```text
If raw lexicon candidates are all score=0, or the prompt is localized,
mixed-language, colloquial, or symptom-first, do not stop at the raw score.
Use the alias catalog as project vocabulary. The agent must translate the user
wording into project-language semantic_intake, intent facets, alias
interpretations, expanded queries, repository_search_terms, and concept
decisions before running project-cognition query.
```

The prompts should make this concrete with examples:

- "install / uninstall / install again" can imply lifecycle, reinstall,
  persisted state, cleanup, and state reset facets.
- "confirmation dialog" can imply confirmation, action plan, preview, confirm
  step, modal, prompt, or a workflow-specific UI component.
- "different from the first time" can imply state-dependent plan generation,
  cached resolution, previous install residue, or persistence drift.

The agent must decide which of those interpretations are actually supported by
the alias catalog and live evidence. The examples are semantic moves, not
hard-coded runtime mappings.

## Query Plan Requirements

After normalization, the query plan should carry:

```json
{
  "raw_query": "I installed, uninstalled, then installed again, and now the install confirmation dialog is different from the first time.",
  "semantic_intake": {
    "workflow_intent": "debug",
    "normalized_query": "Investigate reinstall lifecycle state and confirmation preview drift after uninstall.",
    "intent_facets": [
      "install lifecycle",
      "uninstall cleanup",
      "reinstall state",
      "confirmation preview",
      "state-dependent action plan"
    ],
    "negative_constraints": [
      "not general visual styling unless tied to lifecycle state"
    ],
    "alias_interpretations": [
      {
        "alias": "confirmation dialog",
        "meaning": "confirmation preview or action-plan confirm step",
        "confidence": "medium"
      }
    ],
    "open_semantic_questions": []
  },
  "selected_concepts": [
    "concept:GEN-current:N-lifecycle-confirmation"
  ],
  "rejected_concepts": [
    "concept:GEN-current:N-unrelated-modal-shell"
  ],
  "concept_decisions": [
    {
      "concept_id": "concept:GEN-current:N-lifecycle-confirmation",
      "decision": "selected",
      "selection_reason": "Covers lifecycle transitions and the confirmation preview path.",
      "covered_facets": [
        "install lifecycle",
        "confirmation preview",
        "state-dependent action plan"
      ],
      "missing_facets": [
        "uninstall cleanup implementation"
      ],
      "match_sources": [
        "alias_catalog",
        "agent_semantic_normalization"
      ],
      "confidence": "medium",
      "risk": "Needs live evidence for uninstall cleanup ownership.",
      "paths": [
        "src/tui/state/reducer.ts",
        "src/tui/components/PlanPreview.tsx"
      ]
    }
  ],
  "expanded_queries": [
    "reinstall lifecycle confirmation preview drift",
    "uninstall cleanup action plan state"
  ],
  "repository_search_terms": [
    "installPlan",
    "uninstall",
    "PlanPreview",
    "confirmation",
    "action plan",
    "lifecycle"
  ],
  "paths": [
    "src/tui/state/reducer.ts",
    "src/tui/components/PlanPreview.tsx"
  ],
  "lexicon_generation_id": "GEN-current",
  "selection_reason": "The raw symptom is localized around lifecycle state and confirmation preview behavior; selected concepts cover those facets before live reads prove the owner."
}
```

Concept selection is valid only when the selected concepts cover the important
facets. A candidate with lexical overlap but missing core facets should be
rejected with a clear reason.

## Data Flow

1. Workflow calls `project-cognition lexicon --intent debug --query
   "I installed, uninstalled, then installed again..." --mode catalog
   --format json`.
2. CLI returns raw terms, graph-backed candidates, alias catalog, readiness, and
   possibly `agent_normalization.required=true`.
3. Agent reads the alias catalog and writes semantic intake in project language.
4. Agent records selected and rejected concepts with facet coverage.
5. Agent writes project-language repository search terms.
6. Workflow calls `project-cognition query --intent debug --query-plan`.
7. Agent follows readiness and reads returned `minimal_live_reads`.
8. Technical claims are proven from live repository evidence.

## Error Handling

- If runtime agreement is blocked, missing, stale, or rebuild-required, preserve
  existing readiness routing. Do not let `agent_normalization` override map
  maintenance guidance.
- If raw candidate scores are zero but an alias catalog exists, the workflow
  should continue through agent-owned normalization instead of reporting
  "unmapped" as final.
- If the agent cannot produce a bounded interpretation from the alias catalog,
  it should ask one concise clarification question or proceed with explicit
  open semantic questions and bounded live reads.
- If query-plan parsing reports warnings or repair hints, the workflow should
  repair the plan shape and preserve diagnostics instead of ending on a raw
  parser exception.

## Testing Strategy

Runtime tests should cover:

- `agent_normalization.required=true` for zero positive matches with a usable
  alias catalog.
- CJK and mixed-language queries trigger the diagnostic without inventing
  concepts.
- blocked, missing, stale, and greenfield-empty states keep their existing
  readiness guidance.
- existing raw lexical matches do not require the diagnostic unless a separate
  trigger applies.

Template and integration tests should cover:

- shared project cognition partials mention agent-owned normalization as the
  mandatory response to `score=0`, CJK, mixed-language, colloquial, and
  symptom-first prompts.
- affected `sp-*` workflows preserve the same lexicon -> semantic_intake ->
  query sequence.
- generated Markdown, TOML, prompt, and skill surfaces include the same
  agent-as-brain / CLI-as-tool boundary.
- `sp-debug` includes examples around lifecycle, reinstall, confirmation, and
  state drift without hard-coding those examples into runtime behavior.

Experience tests should cover:

- a localized symptom prompt can proceed through agent-written
  `semantic_intake` despite raw `score=0`.
- query plans include `repository_search_terms` derived from project language,
  not only raw user words.
- selected and rejected concept decisions include `covered_facets`,
  `missing_facets`, and `match_sources`.

## Acceptance Criteria

- CLI remains a structured tool and does not become the semantic decision maker.
- Agent-owned semantic normalization is explicit in every affected workflow.
- `score=0` is treated as a trigger for semantic bridging, not as final failure.
- `project-cognition lexicon` can mechanically tell the agent normalization is
  required without translating user intent.
- Query plans generated after normalization preserve raw input, project-language
  interpretation, facet coverage, concept decisions, and repository search
  terms.
- Tests prevent a debug-only fix and protect cross-workflow alignment.
