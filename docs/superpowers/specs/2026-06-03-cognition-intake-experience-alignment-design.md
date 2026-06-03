# Cognition Intake Experience Alignment Design

**Date:** 2026-06-03
**Status:** Draft for user review
**Owner:** Codex
**Related design:** `docs/superpowers/specs/2026-06-02-shared-semantic-cognition-intake-design.md`

## Summary

The shared semantic cognition intake design is correct, but the generated
workflow experience must be audited against it. The user-visible promise is not
only that templates mention `semantic_intake`; it is that every relevant `sp-*`
workflow behaves as if it understands this sequence:

```text
user natural-language input
-> project-cognition lexicon alias catalog
-> agent-written semantic_intake in project language
-> facet-coverage concept selection
-> project-cognition query bundle
-> workflow-specific readiness and minimal_live_reads consumption
```

This design adds an experience-alignment pass across the full generated
workflow family. It treats `sp-debug` as the incident sample, not the only
target. The alignment pass should find where the actual CLI experience diverges
from the approved semantic intake contract, then fix the smallest cross-surface
set that makes the behavior reliable for all brownfield `sp-*` workflows.

## Problem

A real `$sp-debug` run exposed two kinds of mismatch between intended design and
actual experience:

1. The workflow did run `lexicon` before `query`, but the agent-generated
   `query_plan` used an invalid `alias_interpretations` shape. The runtime
   reported a Go struct unmarshalling error instead of a workflow-friendly
   repair hint.
2. `learning start --command debug --format json`, an auxiliary passive-memory
   step, failed with `KeyError: 'learning_type'`. That failure interrupted the
   debug flow before the real project defect investigation began.

Neither failure disproves the semantic intake design. They show that the
experience can still feel wrong when contracts are underspecified, auxiliary
layers are too brittle, or errors describe implementation internals instead of
the next workflow action.

The same mismatch can affect more than `sp-debug`. Any workflow that consumes
project cognition can drift from the intended experience if its template,
passive skill, integration renderer, runtime parser, or tests teach a slightly
different intake contract.

## Goals

- Validate that the actual generated `sp-*` experience matches the approved
  shared semantic cognition intake design.
- Cover all brownfield workflows that use `project-cognition lexicon` and
  `project-cognition query`, not only `sp-debug`.
- Make the alias catalog step operationally meaningful: agents should use it to
  normalize user language into project language before concept selection.
- Make the `query_plan` shape concrete enough that agents can reliably produce
  it, including object-shaped `alias_interpretations`.
- Ensure runtime parser failures explain how to repair the query plan.
- Ensure auxiliary passive learning or memory layers do not block the primary
  workflow unless the command contract declares them as hard gates.
- Add tests that simulate realistic workflow input, including localized or
  informal prompts, rather than only checking that terms appear in templates.

## Non-Goals

- Do not redesign the approved semantic intake model.
- Do not make project cognition authoritative evidence for source behavior.
- Do not fix only the `debug.md` command template.
- Do not require all agents to produce perfect query plans; the runtime should
  still provide useful diagnostics and limited compatibility for common legacy
  shapes.
- Do not make passive learning a hard dependency for ordinary workflow entry.

## Affected Surfaces

The audit and alignment pass applies to:

- shared project cognition partials:
  - `templates/command-partials/common/context-loading-gradient.md`
  - `templates/command-partials/common/planning-context-loading-gradient.md`
  - `templates/command-partials/common/senior-consequence-analysis-gate.md`
    because it owns shared readiness-to-routing wording for `ready`, `review`,
    `ambiguous`, `needs_update`, `needs_rebuild`, and `blocked`
- workflow templates that mention cognition intake:
  - `discussion`, `specify`, `clarify`, `deep-research`, `plan`, `tasks`,
    `analyze`, `fast`, `quick`, `implement`, `debug`, `checklist`, `prd-scan`,
    `map-build`, and `map-update`
  - `map-build` is in scope for its completion-time smoke query even though it
    is not a normal user-intent intake workflow; its lexicon -> semantic_intake
    -> query check must use the same contract as the rest of the runtime
  - `sp-implement-teams` is in scope as a team-execution consumer of the
    `sp-implement` cognition bundle contract. Claude Agent Teams guidance must
    preserve lexicon -> semantic_intake -> query context before `TaskCreate`,
    and generated-skill parity tests should confirm it does not drift from the
    base implementation contract.
- workflow templates that invoke `learning start`, even when they do not
  perform cognition intake:
  - `constitution`, `map-scan`, and any other command template with
    `learning start --command <workflow> --format json`
  - these surfaces are in scope only for passive learning hardening so malformed
    legacy learning index entries cannot block non-cognition workflows
- passive workflow guidance:
  - `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
  - `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
  - `templates/passive-skills/spec-kit-project-learning/SKILL.md`, especially
    its "required preflight memory" wording for light and heavy work
- runtime:
  - `tools/project-cognition/internal/query/lexicon.go`
  - `tools/project-cognition/internal/query/query.go`
  - `tools/project-cognition/internal/cli/cli.go`
  - `src/specify_cli/learnings.py`
- integration and generated asset renderers:
  - `src/specify_cli/integrations/base.py`
  - integration-specific command or skill rendering tests
- regression tests:
  - template alignment tests
  - project-cognition query parser/runtime tests
  - learning CLI compatibility tests
  - integration generation tests for Markdown, TOML, and skills-based agents

## Experience Contract

Every relevant `sp-*` workflow should satisfy these user-visible checkpoints.

### 1. Lexicon Is First-Class Intake

The workflow retrieves `project-cognition lexicon --mode catalog` before it
depends on a narrowed candidate set. The alias catalog is not decorative
context. It is the vocabulary source the agent uses to translate user wording
into project wording.

### 2. User Input Is Normalized Explicitly

The workflow records a `semantic_intake` object that preserves the user request
and expresses the agent's interpretation in project language:

```json
{
  "raw_query": "PE程序下驱动下载目前好像有点问题，现象就是卡在进度95卡了很久很久 排查下问题",
  "semantic_intake": {
    "workflow_intent": "debug",
    "normalized_query": "Investigate driver download progress stalling near 95 percent in the WinPE program flow.",
    "intent_facets": [
      "WinPE runtime",
      "driver download",
      "progress reporting",
      "95 percent stall",
      "download completion transition"
    ],
    "negative_constraints": [
      "not a general UI progress display issue unless linked to download state"
    ],
    "alias_interpretations": [
      {
        "alias": "PE程序",
        "meaning": "WinPE environment program flow",
        "confidence": "high"
      }
    ],
    "open_semantic_questions": []
  }
}
```

The workflow may carry uncertain interpretations as `open_semantic_questions`,
but it should not silently use uncertain facts as route truth.

### 3. Concept Selection Uses Facet Coverage

Selected and rejected concepts must include `concept_decisions` that explain:

- covered facets
- missing facets
- match sources
- confidence
- risk or rejection reason

Top similarity, raw keyword overlap, or vector ranking alone cannot justify the
selected route.

### 4. Readiness Produces A Concrete Next Action

The workflow consumes the query bundle:

- `ready`: continue with the returned route pack.
- `review`: inspect only the returned `minimal_live_reads` before expanding.
- `ambiguous`: ask a bounded clarification question.
- `needs_update` or weak localized coverage: recommend `sp-map-update` when map
  maintenance is the appropriate next action, while preserving live-evidence
  fallback rules from the advisory cognition contract.
- `needs_rebuild`: reserve `sp-map-scan -> sp-map-build` for first/missing or
  unusable baselines and documented rebuild triggers.
- `blocked`: report the blocking runtime state clearly.

The user should never see a raw parser exception as the final workflow guidance
when a repairable query-plan shape caused the issue.

### 5. Auxiliary Layers Cannot Mask The Primary Workflow

Passive learning and memory preflight should help the workflow reuse project
experience. They must not prevent `sp-*` from reaching its primary intake unless
the command contract explicitly says the auxiliary layer is mandatory. For
light and heavy workflows, a failed learning start should be reported as a
preflight warning with fallback reads, not as the end of the main workflow.

## Design

### 1. Add A Cross-Workflow Experience Audit

Before changing behavior, build an audit table for the relevant `sp-*` surfaces:

```text
workflow/surface
design checkpoint
current wording or runtime behavior
real-experience risk
required fix
test coverage
```

The audit should use at least one realistic localized prompt and one informal
English prompt. The localized prompt should exercise alias interpretation and
tokenization weaknesses. The informal English prompt should exercise facet
coverage over top-similarity matching.

### 2. Normalize The Query Plan Example In Shared Partials

The shared partials should include one compact, copyable query plan skeleton
with correct field shapes. Workflow templates should reference the shared
contract and add only intent-specific constraints. This reduces drift across
Markdown, TOML, prompt, and skills-based integrations.

The example must include object-shaped `alias_interpretations`, not a string
array. It should also show `concept_decisions` with `covered_facets`,
`missing_facets`, and `match_sources`.

### 3. Make Runtime Errors Workflow-Friendly

`project-cognition query` should detect common query-plan shape mistakes and
return actionable diagnostics. Workflows call it with `--format json`, so the
diagnostics contract must be machine-readable:

- When coercion succeeds, stdout JSON should include the normal query payload
  plus `warnings` or `repair_hints`, and the returned `query_plan` should show
  the normalized shape actually used by the runtime. Exit code should remain
  zero unless the query itself fails for another reason.
- When rejection is necessary, stdout JSON should contain a structured error
  payload following existing runtime conventions: `errors` as an array and
  `warnings` as an array are required, while singular `error` or `error_code`
  may be included as compatibility/detail fields. The payload must also include
  `repair_hints` and `expected_shape` for query-plan shape failures. Stderr may
  repeat a concise human message, but stderr-only parser failures are not
  acceptable for `--format json` workflow consumers. The exit code should be
  non-zero.

At minimum:

- If `alias_interpretations` is a string array at either the top level or inside
  `semantic_intake`, either coerce each string into a low-confidence
  `{alias, meaning}` object or return a structured JSON error that shows the
  expected object shape.
- If nested and top-level semantic intake aliases conflict, keep the current
  nested-preferred behavior but report normalized output in the returned
  `query_plan`.
- If `lexicon_generation_id` is missing, keep the query usable but mark the
  generation-drift protection gap.

Compatibility should not hide serious ambiguity. Coercion is acceptable for
small shape errors; unsupported shapes should produce a readable repair hint.

### 4. Harden Passive Learning Start

`learning start` should tolerate legacy or malformed learning index entries
well enough to keep the primary workflow moving. The desired behavior is:

- parse valid entries normally
- skip or normalize recoverable legacy entries
- report skipped malformed entries in JSON diagnostics
- avoid Python `KeyError` for missing fields such as `learning_type`
- leave primary workflow continuation possible with direct memory file reads

This hardening is cross-workflow because `learning start` appears in many
workflow templates, not only `debug`. The passive
`templates/passive-skills/spec-kit-project-learning/SKILL.md` wording must align
with this behavior: "required preflight memory" means required to attempt and
surface when available, not allowed to mask the primary workflow with a legacy
index parser failure.

### 5. Test The Experience, Not Only The Words

Regression tests should assert behavior-level outcomes:

- shared templates include the canonical query plan skeleton
- every relevant workflow points to the shared semantic intake contract
- runtime accepts or clearly rejects common malformed query plan shapes
- diagnostics are identical across inline `--query-plan`, `--query-plan @file`,
  and `--query-plan-file <path>` parse paths
- localized natural-language input can produce semantic-intake-driven concept
  selection without relying only on raw keyword overlap
- `learning start` survives legacy index entries missing optional or formerly
  required fields
- learning hardening tests cover the actual known `learning start` command
  family, including non-cognition workflows such as `constitution`, `map-scan`,
  and `map-build`, not only `debug` or planning/execution cognition workflows
- JSON-mode `project-cognition query` emits machine-readable warnings,
  `repair_hints`, normalized `query_plan` output, or structured JSON errors for
  query-plan shape problems
- generated integration outputs preserve the shared cognition guidance

## Acceptance Criteria

- All affected workflows share one recognizable cognition intake contract.
- No affected workflow teaches raw user input as the sole concept-matching
  source.
- The canonical query plan example uses correct `alias_interpretations` object
  shape.
- `project-cognition query` no longer fails with an opaque struct-unmarshal
  error for the common string-array alias interpretation mistake.
- Successful query-plan coercion returns stdout JSON with warning or repair-hint
  diagnostics and the normalized `query_plan`; unrecoverable query-plan parsing
  returns a structured JSON error under `--format json` rather than stderr-only
  text, with `errors`, `warnings`, `repair_hints`, and `expected_shape`.
- `learning start --command <workflow> --format json` does not terminate with
  `KeyError` when the learning index contains legacy entries.
- Non-cognition workflows that still call `learning start`, including
  `constitution`, `map-scan`, and `map-build`, receive the same legacy-entry
  tolerance and warning diagnostics.
- Tests cover at least `sp-debug`, one planning workflow, one execution
  workflow, `sp-map-build` smoke-query guidance, `sp-implement-teams`
  generated-skill parity, and one generated integration surface.
- Query-plan diagnostics tests cover inline `--query-plan`,
  `--query-plan @file`, and `--query-plan-file <path>`.
- The final user-facing workflow guidance for `review` readiness explains what
  to inspect next through `minimal_live_reads`.

## Open Decisions

- Whether string-array `alias_interpretations` should be silently coerced or
  rejected with a friendly error. The recommended default is coercion with a
  diagnostic warning because it preserves workflow momentum. If implemented,
  coercion should apply both to top-level `alias_interpretations` and nested
  `semantic_intake.alias_interpretations`.
- Whether the experience audit should become a permanent test fixture or a
  one-time design-to-implementation checklist. The recommended default is both:
  write the audit as a temporary implementation artifact under the planning
  workspace or design notes, then encode the durable checks in tests. It does
  not need to become a permanent docs artifact unless it carries decisions that
  future maintainers need outside the tests.

## Implementation Handoff

The implementation plan should start with the audit, then make the smallest
cross-surface changes that close the observed gaps. Do not implement a
`debug`-only fix. Do not bypass the existing shared semantic intake design.
