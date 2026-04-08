---
description: Identify underspecified areas in the current feature spec by asking up to 5 highly targeted clarification questions and encoding answers back into the spec.
handoffs:
  - label: Build Technical Plan
    agent: sp.plan
    prompt: Create a plan for the spec. I am building with...
scripts:
   sh: scripts/bash/check-prerequisites.sh --json --paths-only
   ps: scripts/powershell/check-prerequisites.ps1 -Json -PathsOnly
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Outline

Goal: Re-open and refine the current feature specification by clarifying ambiguity, correcting misalignment, adding newly provided requirements or constraints, and updating the alignment decision accordingly.

Note: This workflow is still expected to complete before `/sp.plan` when requirements materially change. It can also be used after `specify` to add new information, repair a misunderstood requirement, or revise the scope.

Execution steps:

1. Run `{SCRIPT}` from repo root once (`--json --paths-only` / `-Json -PathsOnly`). Parse:
   - `FEATURE_DIR`
   - `FEATURE_SPEC`
   - (Optionally `IMPL_PLAN`, `TASKS` for chained flows.)
   - If JSON parsing fails, abort and instruct the user to re-run `/sp.specify` or verify feature branch environment.

2. Ensure repository technical documentation exists.
   - Check whether `项目技术文档.md` exists at the repository root.
   - If it is missing, analyze the repository and create `项目技术文档.md`
     before continuing.
   - Use this standard section structure:
     `项目架构概览`, `目录结构及其职责`, `关键模块依赖关系图`,
     `核心类与接口功能说明`, `核心数据流向图`, `API接口清单`,
     `常见的代码模式与约定`.

3. Load the current spec file, `FEATURE_DIR/alignment.md` if present, and
   `项目技术文档.md` if present. Perform a structured ambiguity and coverage
   scan using this taxonomy. For each category, mark status: Clear / Partial /
   Missing.

   Functional Scope & Behavior:
   - Core user goals & success criteria
   - Explicit out-of-scope declarations
   - User roles / personas differentiation

   Domain & Data Model:
   - Entities, attributes, relationships
   - Identity & uniqueness rules
   - Lifecycle/state transitions
   - Data volume / scale assumptions

   Interaction & UX Flow:
   - Critical user journeys / sequences
   - Error/empty/loading states
   - Accessibility or localization notes

   Non-Functional Quality Attributes:
   - Performance
   - Scalability
   - Reliability & availability
   - Observability
   - Security & privacy
   - Compliance / regulatory constraints

   Integration & External Dependencies:
   - External services/APIs and failure modes
   - Data import/export formats
   - Protocol/versioning assumptions

   Edge Cases & Failure Handling:
   - Negative scenarios
   - Rate limiting / throttling
   - Conflict resolution

   Constraints & Tradeoffs:
   - Technical constraints
   - Explicit tradeoffs or rejected alternatives

   Terminology & Consistency:
   - Canonical glossary terms
   - Avoided synonyms / deprecated terms

   Completion Signals:
   - Acceptance criteria testability
   - Measurable done indicators

   Misc / Placeholders:
   - TODO markers / unresolved decisions
   - Ambiguous adjectives lacking quantification

4. Generate an internal prioritized queue of candidate clarification questions (maximum 5). Do not output them all at once.
   - Only include questions whose answers materially impact architecture, data modeling, task decomposition, test design, UX behavior, operational readiness, or compliance validation.
   - Skip questions already answered or better deferred to planning.

5. Sequential questioning loop:
   - Present exactly one question at a time.
   - Prefer concise multiple-choice answers when useful.
   - For short-answer prompts, constrain to a short phrase.
   - Allow the user to provide new requirements, new constraints, corrections, or scope changes, not just answers to ambiguity.
   - Use the user's current language for all user-visible clarification content, including questions, summaries, follow-up prompts, and completion reporting.
   - Stop when:
     - all critical ambiguities are resolved, or
     - the user signals completion, or
     - you reach 5 asked questions.

6. Integration after each accepted answer:
   - Update the spec in memory and on disk.
   - Update `alignment.md` in parallel. If it does not exist, create it using the current best understanding.
   - Apply each answer to the most appropriate section:
     - Functional ambiguity -> Functional Requirements / Scope Boundaries
     - User interaction / actor distinction -> User Stories
     - Data shape / entities -> Key Entities or requirements
     - Non-functional constraint -> Success Criteria
     - Edge case / negative flow -> Edge Cases
     - Terminology conflict -> normalize throughout the spec
   - Preserve formatting and do not reorder unrelated sections.

7. Validation after each write plus final pass:
   - Clarification summary is updated without duplication.
   - No contradictory earlier statement remains.
   - Markdown structure stays valid.
   - Terminology stays consistent.

8. Update the alignment decision before reporting:
   - Use `Aligned: ready for plan` only when no unresolved high-impact ambiguity remains.
   - Use `Force proceed with known risks` if unresolved high-impact ambiguity remains and the user explicitly wants to continue.
   - Record new requirements, constraints, or corrections in both the spec and `alignment.md`.

9. Write the updated spec back to `FEATURE_SPEC` and write the updated alignment report to `FEATURE_DIR/alignment.md`.

10. Report completion:
   - Number of questions asked & answered
   - Path to updated spec
   - Path to updated alignment report
   - Sections touched
   - Coverage summary table with Status: Resolved / Deferred / Clear / Outstanding
   - Alignment decision: `Aligned: ready for plan` or `Force proceed with known risks`
   - Recommended next command

Behavior rules:

- If no meaningful ambiguities are found, respond: "No critical ambiguities detected worth formal clarification."
- If the spec file is missing, instruct the user to run `/sp.specify` first.
- Never exceed 5 total asked questions (clarification retries for a single question do not count as new questions).
- Respect user early termination signals ("stop", "done", "proceed").
- Use this command to add newly provided requirements or constraints, not just to answer old questions.
- Match the user's current language for all user-visible output unless a literal command name, file path, or fixed status value must remain unchanged.

Context for prioritization: {ARGS}
