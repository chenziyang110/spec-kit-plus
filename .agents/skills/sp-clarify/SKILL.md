---
name: "sp-clarify"
description: "Identify underspecified areas in the current feature spec by asking at least 5 highly targeted clarification questions and encoding answers back into the spec."
compatibility: "Requires spec-kit project structure with .specify/ directory"
metadata:
  author: "github-spec-kit"
  source: "templates/commands/clarify.md"
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

1. Run `.specify/scripts/powershell/check-prerequisites.ps1 -Json -PathsOnly` from repo root once (`--json --paths-only` / `-Json -PathsOnly`). Parse:
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

4. Generate an internal prioritized queue of candidate clarification questions (minimum 5). Do not output them all at once.
   - Only include questions whose answers materially impact architecture, data modeling, task decomposition, test design, UX behavior, operational readiness, or compliance validation.
   - Skip questions already answered or better deferred to planning.
   - Prepare at least 5 high-value questions unless the user has already
     explicitly terminated the clarification phase.

5. Sequential questioning loop:
   - Present exactly one question at a time.
   - Prefer concise multiple-choice answers when useful.
   - For short-answer prompts, constrain to a short phrase.
   - Allow the user to provide new requirements, new constraints, corrections, or scope changes, not just answers to ambiguity.
   - Use the user's current language for all user-visible clarification content, including questions, summaries, follow-up prompts, and completion reporting.
   - Use a shared question-card format for every interactive clarification question.
   - Keep the header minimal: `CLARIFY SESSION` plus the current question counter, for example `4 / 6`.
   - Write a one-sentence question stem only. Put extra context into the example line or the recommendation line instead of expanding the stem into a paragraph.
   - Include a one-line `Example` row whenever the topic could be misunderstood from abstraction alone.
   - When you present options, mark exactly one option with a `[ RECOMMENDED ]` badge and follow it with a single short rationale sentence.
   - Prefer a strong boxed card when the environment supports it. If not, fall back to a simplified card while preserving the same sections and ordering.
   - Do not rely on interactive selection widgets. Assume the user will answer in plain text.
   - After the options, explicitly invite natural-language replies, for example: `Reply naturally, for example: "A", "选 C", "我选推荐项"`.
   - Accept common natural-language answer forms such as `A`, `选A`, `我选 C`, `推荐的那个`, or a short paraphrase that clearly matches one option.
   - After parsing the answer, acknowledge it with one lightweight confirmation line and continue, for example: `Recorded: C - Normalize first`.
   - Default to concise clarification turns: after the user answers, ask the next question directly unless a recap is necessary.
   - Do not restate the full current understanding after every answer.
   - Use at most a one-line checkpoint when helpful, for example `Confirmed so far:` or `Still open:`.
   - Reserve grouped recaps for moments when they add clear value: the user asks for a recap, the thread is long enough that context may drift, a contradiction must be reconciled, or you are about to finish clarification.
   - Keep any recap compact and focused on what materially changed.
   - Save the full synthesis for the final clarification report, the updated written artifacts, or when the user explicitly asks to see everything collected so far.
   - Stop when:
     - the user signals completion, or
     - you have asked at least 5 questions and all critical ambiguities are resolved.
   - If critical ambiguities remain after 5 questions, continue asking beyond 5
     until the remaining ambiguity is either resolved or explicitly deferred by
     the user.

   Use this question-card structure in the user's current language:

   ```text
   ┌─ CLARIFY SESSION ─────────────────────────────── 4 / 6 ─┐
   │ [Short topic label]                                     │
   │                                                         │
   │ [One-sentence question stem]                            │
   │                                                         │
   │ Example                                                 │
   │   [One-line concrete example]                           │
   │                                                         │
   │ [ RECOMMENDED ]  [Option letter]                        │
   │ [One short rationale sentence]                          │
   └─────────────────────────────────────────────────────────┘

   ┌─ OPTIONS ───────────────────────────────────────────────┐
   │ A. [Option text]                                        │
   │ B. [Option text]                                        │
   │ C. [Option text]                                        │
   │ D. [Option text]                                        │
   └─────────────────────────────────────────────────────────┘

   Reply naturally, for example: "A", "选 C", "我选推荐项"
   ```

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

- If the user has already terminated clarification explicitly, stop and report
  the current state.
- If the spec file is missing, instruct the user to run `/sp.specify` first.
- Ask at least 5 total questions unless the user explicitly stops early.
- Clarification retries for a single question do not count as new questions.
- Respect user early termination signals ("stop", "done", "proceed").
- Use this command to add newly provided requirements or constraints, not just to answer old questions.
- Match the user's current language for all user-visible output unless a literal command name, file path, or fixed status value must remain unchanged.

Context for prioritization: $ARGUMENTS
