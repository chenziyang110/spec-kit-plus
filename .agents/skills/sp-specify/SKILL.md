---
name: "sp-specify"
description: "Create or update the feature specification from a natural language feature description."
compatibility: "Requires spec-kit project structure with .specify/ directory"
metadata:
  author: "github-spec-kit"
  source: "templates/commands/specify.md"
---


## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Pre-Execution Checks

**Check for extension hooks (before specification)**:
- Check if `.specify/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.before_specify` key
- If the YAML cannot be parsed or is invalid, skip hook checking silently and continue normally
- Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
- For each remaining hook, do **not** attempt to interpret or evaluate hook `condition` expressions:
  - If the hook has no `condition` field, or it is null/empty, treat the hook as executable
  - If the hook defines a non-empty `condition`, skip the hook and leave condition evaluation to the HookExecutor implementation
- For each executable hook, output the following based on its `optional` flag:
  - **Optional hook** (`optional: true`):
    ```
    ## Extension Hooks

    **Optional Pre-Hook**: {extension}
    Command: `/{command}`
    Description: {description}

    Prompt: {prompt}
    To execute: `/{command}`
    ```
  - **Mandatory hook** (`optional: false`):
    ```
    ## Extension Hooks

    **Automatic Pre-Hook**: {extension}
    Executing: `/{command}`
    EXECUTE_COMMAND: {command}

    Wait for the result of the hook command before proceeding to the Outline.
    ```
- If no hooks are registered or `.specify/extensions.yml` does not exist, skip silently

## Outline

The text the user typed after `/sp.specify` is the initial idea. Your responsibility is to align the requirement until it is planning-ready, or explicitly record that the user chose to force proceed with known risks.

1. Parse the user description.
   - If empty: ERROR "No feature description provided"

2. Generate a concise short name (2-4 words) for the branch.
   - Keep it descriptive and action-oriented when possible.

3. Create the feature branch by running the script once with `--json`/`-Json` and `--short-name`/`-ShortName`.
   - Before running the script, check if `.specify/init-options.json` exists and read `branch_numbering`.
   - If the value is `"timestamp"`, add `--timestamp` or `-Timestamp`.
   - If the value is `"sequential"` or missing, use default numbering.
   - Do not pass `--number`.
   - Parse `BRANCH_NAME`, `SPEC_FILE`, and `FEATURE_DIR` from the JSON response.
   - Set `ALIGNMENT_FILE` to `FEATURE_DIR/alignment.md`.

4. Ensure repository technical documentation exists.
   - Check whether `项目技术文档.md` exists at the repository root.
   - If it is missing, analyze the repository and create `项目技术文档.md`
     before continuing.
   - The generated document must summarize project architecture, directory
     responsibilities, module dependencies, core data flows, external
     interfaces, and project conventions based only on actual repository
     evidence.
   - Use this standard section structure:
     `项目架构概览`, `目录结构及其职责`, `关键模块依赖关系图`,
     `核心类与接口功能说明`, `核心数据流向图`, `API接口清单`,
     `常见的代码模式与约定`.

5. Load context.
   - Read `.specify/templates/spec-template.md`.
   - Read `.specify/templates/alignment-template.md`.
   - Read `项目技术文档.md` if present.
   - Read repository context relevant to the request.
   - Read existing specs/docs if relevant.
   - Read constitution/project guidance if present.

6. Infer task classification.
   Infer exactly one:
   - greenfield project
   - existing feature addition
   - bug fix
   - technical refactor
   - docs/config/process change

   Briefly tell the user your inferred classification and allow correction before continuing.

7. Choose alignment mode.
   - Lightweight mode for local, context-rich changes.
   - Deep mode for greenfield or materially ambiguous work.

8. Decomposition gate.
   - If the request spans multiple independent subsystems, business domains, or release tracks, do not continue as though it were one bounded feature.
   - Stop and help the user decompose it into separate specs or clearly phased releases first.
   - Only continue once the current spec scope is narrow enough to be planned and tested coherently.

9. Run task-type mandatory clarity gates.

   Greenfield project:
   - target users
   - core problem
   - first-release scope
   - out-of-scope boundary
   - core user flows
   - key domain entities
   - success criteria
   - hard constraints if any

   Existing feature addition:
   - affected module or workflow
   - intended users
   - relationship to existing behavior
   - compatibility expectations
   - data/state impact
   - acceptance criteria

   Bug fix:
   - current incorrect behavior
   - expected correct behavior
   - reproduction conditions
   - impact scope
   - regression-sensitive areas
   - completion criteria

   Technical refactor:
   - reason for change
   - change boundary
   - behavior that must remain unchanged
   - risk tolerance
   - migration/transition allowance
   - completion criteria

   Docs/config/process change:
   - changed artifact
   - change objective
   - affected users or teams
   - compatibility/process constraints
   - validation method
   - completion criteria

   Rules:
   - If an item is already clear from context, do not ask.
   - If it is low-risk and inferable, adopt a default silently and record it later under low-risk defaults.
   - If it is high-impact and unclear, ask.

10. Run a high-impact ambiguity scan.
   Detect unresolved ambiguity affecting:
   - scope
   - users/roles
   - security/permissions
   - workflow behavior
   - data/entities
   - compatibility
   - acceptance tests
   - success criteria
   - rollout/migration impact

   The user saying "I already explained it" is not sufficient reason to stop. Judge clarity from the perspective of a future planner, implementer, and tester.

11. Clarification loop.
   - Ask only high-value questions.
   - Use grouped questions for simple/local changes.
   - Use one question at a time for complex/high-risk cases.
   - Ask at most one unanswered high-impact question per message.
   - Challenge contradictions or vague answers when important ambiguity remains.
   - Use the user's current language for all user-visible clarification content, including questions, summaries, status updates, and the current-understanding restatement.
   - Use a shared question-card format for every interactive question in this workflow.
   - Keep the header minimal: `SPECIFY SESSION` plus the current question counter, for example `2 / 5`.
   - Default to a one-sentence question stem. Put extra context into the example line, grouped sub-points, or recommendation line instead of turning the stem into a paragraph.
   - Include a one-line `Example` row whenever the topic benefits from a concrete case.
   - When you present options, mark exactly one option with a `[ RECOMMENDED ]` badge and follow it with a single short rationale sentence.
   - Prefer a strong boxed card when the environment supports it. If not, fall back to a simplified card while preserving the same sections and ordering.
   - Do not rely on interactive selection widgets. Assume the user will answer in plain text.
   - After the options, explicitly invite natural-language replies, for example: `Reply naturally, for example: "A", "选 C", "我选推荐项"`.
   - Accept common natural-language answer forms such as `A`, `选A`, `我选 C`, `推荐的那个`, or a short paraphrase that clearly matches one option.
   - After parsing the answer, acknowledge it with one lightweight confirmation line and continue, for example: `Recorded: C - Normalize first`.
   - Default to concise clarification turns: after the user answers, ask the next question directly unless a recap is necessary.
   - Do not restate the full current understanding after every answer.
   - Use at most a one-line checkpoint when helpful, for example `Confirmed so far:` or `Still open:`.
   - Reserve the full current-understanding recap for moments when it adds clear value: the user asks for a recap, the thread has become long enough that context may drift, a contradiction must be reconciled, or you are about to conclude alignment.
   - When you do restate current understanding, organize it in grouped sections by information layer, not as a flat list.
   - Keep grouped recaps compact; omit sections that would be empty, repetitive, or low-value.
   - Do not repeat the same question in both the summary and the follow-up ask.
   - If you include a grouped recap and are about to ask the next question immediately, summarize it briefly under `Outstanding Questions` instead of restating the full wording there.
   - Save the full synthesis for the alignment-ready turn, the written artifacts (`alignment.md`, `spec.md`), or when the user explicitly asks to see everything collected so far.
   - Do not add a second recap after the question; each clarification turn should contain at most one short checkpoint or one grouped recap, plus one question block.

   Use this question-card structure in the user's current language:

   ```text
   ┌─ SPECIFY SESSION ─────────────────────────────── 2 / 5 ─┐
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

   Use this structure in the user's current language:

   ```text
   [Current understanding heading]

   [Business Goals]
   - [Requested outcome]
   - [Why it matters / intended business value]

   [Users & Roles]
   - [Target users / audience]
   - [Relevant roles or permission groups]

   [Scope Boundaries]
   - [First-release scope]
   - [Out-of-scope boundary]

   [Business Rules]
   - [Expected behaviors / capabilities]
   - [Rules, workflows, or policy constraints]

   [Technical Constraints / Assumptions]
   - [Given platform, integration, architecture, or deployment constraints]

   [Confirmed Decisions]
   - [Decisions already fixed enough to plan against]

   [Outstanding Questions]
   - [Open question / confirmation still needed]
   ```

12. Alignment decision gate.
    Decide exactly one:
    - `Aligned: ready for plan`
      Use only when:
      - mandatory clarity gates are sufficiently resolved
      - no unresolved high-impact ambiguity remains
      - the spec can be written as a bounded, testable document
      - no `[NEEDS CLARIFICATION]` markers are needed
    - `Force proceed with known risks`
      Use only when:
      - unresolved high-impact ambiguity remains
      - the user explicitly chooses to continue anyway

    If neither condition is met, continue clarification.

13. Write `spec.md` to `SPEC_FILE` using the template structure.
    Requirements:
    - clean result-state document only
    - no `[NEEDS CLARIFICATION]`
    - no speculative implementation details
    - requirements must be testable
    - scope must be bounded

14. Write `alignment.md` to `ALIGNMENT_FILE`.
    It must include:
    - task classification
    - current aligned understanding
    - confirmed key decisions
    - low-risk defaults adopted
    - clarification summary
    - remaining risks (if any)
    - release decision:
      - `Aligned: ready for plan`
      - or `Force proceed with known risks`
    - reason for the release decision

15. Generate or update `FEATURE_DIR/checklists/requirements.md` with these validation items:

    ```markdown
    # Specification Quality Checklist: [FEATURE NAME]

    **Purpose**: Validate specification completeness and alignment before planning
    **Created**: [DATE]
    **Feature**: [Link to spec.md]
    **Alignment Report**: [Link to alignment.md]

    ## Content Quality

    - [ ] No implementation details (languages, frameworks, APIs)
    - [ ] Focused on user value and business needs
    - [ ] Written for non-technical stakeholders
    - [ ] All mandatory sections completed

    ## Requirement Completeness

    - [ ] No [NEEDS CLARIFICATION] markers remain
    - [ ] Requirements are testable and unambiguous
    - [ ] Success criteria are measurable
    - [ ] Scope boundaries are explicit
    - [ ] All acceptance scenarios are defined
    - [ ] Edge cases are identified
    - [ ] Dependencies and assumptions identified

    ## Alignment Readiness

    - [ ] alignment.md exists
    - [ ] Task classification is recorded
    - [ ] Release decision is recorded
    - [ ] Release decision is either `Aligned: ready for plan` or `Force proceed with known risks`
    - [ ] Remaining risks are empty for normal completion

    ## Notes

    - Items marked incomplete require spec updates before `/sp.plan`
    ```

16. Re-run validation after edits. Normal completion must pass all required checks.

17. Report completion with:
    - branch name
    - spec file path
    - alignment report path
    - checklist results
    - release decision
    - readiness for the next phase (`/sp.clarify` or `/sp.plan`)
    - Use the user's current language for the completion report and any explanatory text, while preserving literal command names, file paths, and fixed status values exactly as written.

18. **Check for extension hooks**: After reporting completion, check if `.specify/extensions.yml` exists in the project root.
   - If it exists, read it and look for entries under the `hooks.after_specify` key
   - If the YAML cannot be parsed or is invalid, skip hook checking silently and continue normally
   - Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
   - For each remaining hook, do **not** attempt to interpret or evaluate hook `condition` expressions:
     - If the hook has no `condition` field, or it is null/empty, treat the hook as executable
     - If the hook defines a non-empty `condition`, skip the hook and leave condition evaluation to the HookExecutor implementation
   - For each executable hook, output the following based on its `optional` flag:
     - **Optional hook** (`optional: true`):
       ```
       ## Extension Hooks

       **Optional Hook**: {extension}
       Command: `/{command}`
       Description: {description}

       Prompt: {prompt}
       To execute: `/{command}`
       ```
     - **Mandatory hook** (`optional: false`):
       ```
       ## Extension Hooks

       **Automatic Hook**: {extension}
       Executing: `/{command}`
       EXECUTE_COMMAND: {command}
       ```
   - If no hooks are registered or `.specify/extensions.yml` does not exist, skip silently

## Quick Guidelines

- Focus on **WHAT** users need and **WHY**.
- Avoid HOW to implement (no tech stack, APIs, code structure).
- Write for business stakeholders, not developers.
- Do not embed checklists in the spec itself.
- Low-risk defaults may be adopted silently.
- High-impact ambiguity must be resolved or explicitly force-continued.

### Section Requirements

- **Mandatory sections**: Must be completed for every feature
- **Optional sections**: Include only when relevant to the feature
- When a section doesn't apply, remove it entirely (do not leave "N/A")

### For AI Generation

1. Do not guess high-impact decisions that materially affect scope, UX, compatibility, security, data shape, or acceptance testing.
2. Use low-risk defaults quietly and record them in `alignment.md` plus the Assumptions section when relevant.
3. If the user thinks they have explained the request clearly but important ambiguity remains, keep clarifying.
4. Think like a planner and tester: if a requirement cannot be planned or tested reliably, it is not aligned enough yet.
5. Normal completion requires no open clarification markers.
6. If the user insists on continuing anyway, allow `Force proceed with known risks`, but record the unresolved items and likely downstream impact.
7. Match the user's current language for all user-visible output unless a literal command name, file path, or fixed status value must remain unchanged.
8. Do not treat MVP minimization as the default strategy; scope the first release to a coherent, quality-appropriate slice unless the user explicitly asks for an MVP.

### Success Criteria Guidelines

Success criteria must be:

1. **Measurable**: Include specific metrics (time, percentage, count, rate)
2. **Technology-agnostic**: No mention of frameworks, languages, databases, or tools
3. **User-focused**: Describe outcomes from user/business perspective, not system internals
4. **Verifiable**: Can be tested/validated without knowing implementation details
