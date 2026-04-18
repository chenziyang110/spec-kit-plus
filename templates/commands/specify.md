---
description: Create or update the feature specification from a natural language feature description.
handoffs:
  - label: Build Technical Plan
    agent: sp.plan
    prompt: Create a plan for the spec. I am building with...
scripts:
  sh: scripts/bash/create-new-feature.sh "{ARGS}"
  ps: scripts/powershell/create-new-feature.ps1 "{ARGS}"
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Pre-Execution Checks

**Check for extension hooks (before specification)**:
- Check if `.specify/extensions.yml` exists in the project root.
- If it exists, read it and look for entries under the `hooks.before_specify` key.
- If the YAML cannot be parsed or is invalid, skip hook checking silently and continue normally.
- Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
- For each remaining hook, do **not** attempt to interpret or evaluate hook `condition` expressions:
  - If the hook has no `condition` field, or it is null/empty, treat the hook as executable.
  - If the hook defines a non-empty `condition`, skip the hook and leave condition evaluation to the HookExecutor implementation.
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
- If no hooks are registered or `.specify/extensions.yml` does not exist, skip silently.

## Outline

The text the user typed after `/sp.specify` is the starting point, not the finished requirement package. Your responsibility is to analyze the whole feature first, decompose it into capabilities, and emit a planning-ready requirement package with confidence tracking rather than a surface summary.

1. Parse the user description.
   - If empty: ERROR "No feature description provided".

2. Generate a concise short name (2-4 words) for the branch.
   - Keep it descriptive and action-oriented when possible.

3. Create the feature branch by running the script once with `--json`/`-Json` and `--short-name`/`-ShortName`.
   - Before running the script, check if `.specify/init-options.json` exists and read `branch_numbering`.
   - If the value is `"timestamp"`, add `--timestamp` or `-Timestamp`.
   - If the value is `"sequential"` or missing, use default numbering.
   - Do not pass `--number`.
   - Parse `BRANCH_NAME`, `SPEC_FILE`, and `FEATURE_DIR` from the JSON response.
   - Set `ALIGNMENT_FILE` to `FEATURE_DIR/alignment.md`.
   - Set `CONTEXT_FILE` to `FEATURE_DIR/context.md`.
   - Set `REFERENCES_FILE` to `FEATURE_DIR/references.md`.

4. Ensure repository navigation system exists.
   - Check whether `PROJECT-HANDBOOK.md` exists at the repository root.
   - Check whether `.specify/project-map/ARCHITECTURE.md`, `.specify/project-map/STRUCTURE.md`, `.specify/project-map/CONVENTIONS.md`, `.specify/project-map/INTEGRATIONS.md`, `.specify/project-map/WORKFLOWS.md`, `.specify/project-map/TESTING.md`, and `.specify/project-map/OPERATIONS.md` exist.
   - If the navigation system is missing, analyze the repository and create it before continuing.
   - Treat `PROJECT-HANDBOOK.md` as the root navigation artifact and use `Topic Map` to choose the smallest relevant topical documents for the touched area.

5. Load context.
   - Read `templates/spec-template.md`.
   - Read `templates/alignment-template.md`.
   - Read `templates/context-template.md`.
   - Read `templates/references-template.md`.
   - Read `.specify/memory/constitution.md` if present.
   - Read `PROJECT-HANDBOOK.md` if present and treat it as the primary codebase-scout input for brownfield understanding.
   - Read the smallest relevant combination of `.specify/project-map/ARCHITECTURE.md`, `.specify/project-map/STRUCTURE.md`, `.specify/project-map/CONVENTIONS.md`, `.specify/project-map/INTEGRATIONS.md`, `.specify/project-map/WORKFLOWS.md`, `.specify/project-map/TESTING.md`, and `.specify/project-map/OPERATIONS.md`.
   - From the handbook navigation system, extract the current module ownership, reusable components/services/hooks, integration points, adjacent workflows, key entities, and architectural constraints relevant to the request.
   - If the topical coverage for the touched area is missing, stale, or too broad, inspect the minimum live files needed to replace guesswork with evidence before asking planning-critical questions.
   - Read repository context relevant to the request.
   - Read existing specs/docs if relevant.
   - Read user-supplied references, examples, or linked material when they materially affect the requirement package.

6. Run a codebase scout before clarification.
   - Treat `PROJECT-HANDBOOK.md` as the default scout artifact for understanding the existing system shape.
   - Use `Topic Map` to choose the smallest relevant topical documents before broad file reads.
   - Build a concise internal scout summary for the request area that names:
     - owning modules or workflows
     - reusable components, services, hooks, commands, or schemas
     - integration boundaries and upstream/downstream dependencies
     - adjacent user flows or screens that this work could accidentally break
     - existing patterns that should bias the questions toward real decision forks
   - If the topical coverage is too broad, stale, or silent on the touched area, read the minimum targeted live files needed to replace guesswork with evidence.
   - Use the scout summary to eliminate low-value questions, sharpen gray areas, and detect when the user's request conflicts with existing repository patterns.

7. Infer task classification.
   Infer exactly one:
   - greenfield project
   - existing feature addition
   - bug fix
   - technical refactor
   - docs/config/process change
   - Task classification changes which requirement dimensions are probed. Use the inferred class to choose the questioning path instead of reusing one generic flow for every request.

   Briefly tell the user your inferred classification and allow correction before continuing.

8. Analyze the whole feature before decomposing it.
   Build a top-down understanding grounded in the project handbook and touched-area topical map plus any targeted live-file reads. It must cover:
   - the feature goal
   - intended users and roles
   - first-release scope
   - business and workflow outcomes
   - critical constraints and assumptions
   - dependencies or preconditions that materially affect planning
   - the currently owning modules, services, screens, commands, or workflows that this request would extend, replace, or bypass
   - reusable code paths or existing patterns that should shape the questioning instead of forcing the user to rediscover repository facts
   - release-shaping risks or external references

9. Choose alignment mode and collaboration strategy.
   - Lightweight mode for local, context-rich changes.
   - Deep mode for greenfield, multi-capability, or materially ambiguous work.
   - Before decomposition begins, assess the current workload shape and agent capability snapshot, then apply the shared policy contract: `choose_execution_strategy(command_name="specify", snapshot, workload_shape)`.
   - Strategy names are canonical and must be used exactly: `single-agent`, `native-multi-agent`, `sidecar-runtime`.
   - Decision order is fixed:
     - If the work does not justify safe fan-out -> `single-agent` (`no-safe-batch`)
     - Else if `snapshot.native_multi_agent` -> `native-multi-agent` (`native-supported`)
     - Else if `snapshot.sidecar_runtime_supported` -> `sidecar-runtime` (`native-missing`)
     - Else -> `single-agent` (`fallback`)
   - If collaboration is justified, keep `specify` lanes limited to:
     - repository and local context analysis
     - external references and supporting material analysis
     - ambiguity, risk, and gap analysis
   - Required join points:
     - before capability decomposition
     - before writing `spec.md`, `alignment.md`, and `context.md`
   - Record the chosen strategy, reason, fallback if any, selected lanes, and join points in `alignment.md`.
   - Keep the shared workflow language integration-neutral. Do not present Codex-only runtime surface wording in this shared template.

10. Decomposition gate.
   - If the request spans multiple independent subsystems, business domains, or release tracks, do not continue as though it were one bounded feature.
   - Stop and help the user decompose it into separate specs or clearly phased releases first.
   - Only continue once the current spec scope is narrow enough to be planned and tested coherently.

11. Capability decomposition.
    - Decompose the analyzed feature into bounded capabilities.
    - Record the purpose of each capability, what scenarios it supports, and how it depends on other capabilities or prerequisites.
    - Separate user-visible capabilities from enabling/supporting capabilities where that improves planning clarity.
    - Note whether each capability is:
      - confirmed by direct evidence,
      - inferred as a low-risk default,
      - or unresolved and still requiring a decision.
    - If capability boundaries remain unclear, continue clarifying until the decomposition is planning-ready or the user explicitly force proceeds.

12. Run task-type mandatory clarity gates.

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
    - Treat this as a planning-critical questioning surface, not a passive cleanup request.
    - Before normal alignment release, collect every planning-critical dimension below: changed artifact, change objective, affected users or teams, compatibility/process constraints, validation method, and completion criteria.
    - Ask for the changed artifact.
    - Ask for the change objective.
    - Ask for the affected users or teams.
    - Ask for compatibility/process constraints.
    - Ask for the validation method.
    - Ask for completion criteria.
    - Do not treat missing answers in this path as passive housekeeping detail or low-priority cleanup context.

    Rules:
    - If an item is already clear from context, do not ask.
    - If it is low-risk and inferable, adopt a default silently and record it later under `Analysis Confidence -> Low-Risk Inferences`.
    - If it is high-impact and unclear, ask.

13. Run an implementation-oriented analysis pass before concluding alignment.
    Cover at minimum:
    - scenario and usage path coverage
    - capability sequencing or dependency constraints
    - data, entity, or state implications
    - compatibility and migration expectations
    - external integrations or handoff dependencies
    - acceptance-test shaping details
    - planning-sensitive risks and gaps

14. Identify gray areas before concluding alignment.
   - Identify 3-5 planning-relevant gray areas: decisions that could reasonably go multiple ways and would materially change implementation, planning, or testing.
   - Derive gray areas from the combination of user intent, `PROJECT-HANDBOOK.md`, and targeted repository evidence instead of from a generic question catalog.
   - Prefer feature-specific decision surfaces over generic categories.
   - Do not use generic labels like "UX", "behavior", or "data handling" when a more concrete decision point can be named from the actual codebase and request.
   - Good gray areas name the concrete fork in outcome, for example `empty-state recovery`, `permission downgrade behavior`, `sync trigger timing`, or `existing dashboard card reuse`.
   - Each gray area should be captured internally with:
     - a concrete decision label
     - why the decision changes implementation or test shape
     - which codebase evidence or owning module made this gray area relevant
     - what additional detail is still missing before a planner could safely proceed
   - For each high-impact gray area, default to resolving at least these decision dimensions unless one is genuinely not applicable:
     - desired happy-path behavior
     - edge case or failure-path behavior
     - compatibility, migration, or neighboring-workflow impact
     - acceptance proof: what evidence would show this decision was implemented correctly
   - Typical gray-area domains include workflow behavior, role/permission handling, data/state transitions, compatibility or migration behavior, failure handling, external integrations, and validation approach.
   - Use the gray-area list to decide what to ask next rather than falling back to generic catch-all questions.
    - Record resolved gray-area outcomes under `Locked Decisions` when they are fixed enough for planning.
    - Record user-approved flexibility under `Claude Discretion`.
    - Record cited specs, ADRs, examples, or policies under `Canonical References`.
    - Record out-of-scope ideas surfaced during clarification under `Deferred / Future Ideas`.
    - Synthesize these decisions into `context.md` so downstream planning does not rely on reconstructing them from prose alone.

15. Run a high-impact ambiguity scan.
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
    - capability boundaries
    - dependency sequencing

    The user saying "I already explained it" is not sufficient reason to stop. Judge clarity from the perspective of a future planner, implementer, and tester.
    If planning-critical ambiguity remains around scope, workflow behavior, constraints, or success criteria, continue clarification instead of releasing normal alignment.

16. Clarification loop.
    - Keep the interaction feeling like guided requirement discovery rather than a shallow questionnaire.
    - Ask only high-value questions.
    - Before asking a planning-critical question, check whether `PROJECT-HANDBOOK.md` or touched-area topical documents already answer it; do not ask the user for facts the codebase can supply.
    - Use grouped questions for simple/local changes.
    - Use one question at a time for complex/high-risk cases.
    - Ask at most one unanswered high-impact question per message.
    - Let unresolved gray areas drive the next question; do not rotate through generic requirement categories once the active gray area is known.
    - Keep the active gray area open until the decision is specific enough that a downstream planner would not need to reopen it for behavior, boundary, or acceptance-shaping detail.
    - Make the next question build directly on the user's most recent answer rather than resetting to generic prompts.
    - Use the previous answer to choose the next narrowing move, not a recycled generic checklist question.
    - Use code-aware follow-ups when possible: reference the current module, workflow, entity, command, or reusable pattern named in the handbook/project-map navigation system or repository evidence so the question is about the real decision fork, not an abstract category.
    - If the user's answer is vague, shallow, or contradictory, respond with a targeted narrowing question, example, or recommendation tied to the planning-critical ambiguity.
    - Do not accept long but still ambiguous answers as sufficient.
    - Challenge contradictions or vague answers when important ambiguity remains.
    - Keep stronger follow-up behavior tied to planning-relevant ambiguity, not generic conversation depth.
    - Apply a specificity test before leaving a gray area: if a different planner or implementer would still need to ask clarifying questions to execute safely, keep drilling into that area instead of moving on.
    - Do not leave a gray area merely because the user expressed a preference; stay on it until behavior boundaries, failure handling, compatibility impact, and acceptance-shaping detail are either fixed, intentionally deferred, or explicitly granted as `Claude Discretion`.
    - For high-impact gray areas, treat the default minimum depth as: happy path, failure path, compatibility impact, and acceptance proof. If one of those dimensions is not applicable, say so explicitly instead of skipping it silently.
    - Treat the following as anti-surface warning signs that require another narrowing question instead of release:
      - the user only states a preference word such as "simple", "intuitive", "robust", or "clean" without concrete behavior
      - the user chooses an option but the boundary conditions, failure behavior, or affected neighboring workflow remain unclear
      - the user confirms a direction but there is still no acceptance proof for how success will be judged
      - the requested behavior appears to conflict with the current owning module or existing repository pattern and the difference has not been explained
    - Concrete examples that MUST trigger another narrowing question instead of release:
      - "make it more intuitive"
      - "handle permissions normally"
      - "keep it compatible"
      - "show an error if something goes wrong"
      - "use the existing pattern"
      - "it should feel fast"
      - "just validate the data properly"
      - "admins can handle the special cases"
      - "don't break existing clients"
    - For answers like those, the next question must convert the vague intent into concrete behavior, edge handling, compatibility scope, or acceptance evidence rather than acknowledging and moving on.
    - Treat these as category-specific anti-surface gaps unless they are made concrete:
      - vague success standard: words like "fast", "smooth", "easy", "clear", or "works well" without observable success criteria
      - vague data rule: words like "valid", "clean", "normalized", or "properly formatted" without explicit field rules, transitions, or rejection behavior
      - vague permission boundary: words like "normal permissions", "admin behavior", or "authorized users" without role/action matrix or downgrade/override behavior
      - vague compatibility claim: phrases like "keep compatibility" or "don't break clients" without naming the preserved interface, version boundary, migration expectation, or failure mode
    - Use recommendation and example scaffolding when they help the user answer more clearly without forcing a rigid response path.
    - Use the user's current language for all user-visible clarification content, including questions, summaries, status updates, and the current-understanding restatement.
    - Default to concise clarification turns: after the user answers, ask the next question directly unless a recap is necessary.
    - Do not restate the full current understanding after every answer.
    - Use at most a one-line checkpoint when helpful, for example `Confirmed so far:` or `Still open:`.
    - Reserve the full current-understanding recap for moments when it adds clear value: the user asks for a recap, the thread has become long enough that context may drift, a contradiction must be reconciled, or you are about to conclude alignment.
    - When you do restate current understanding, organize it in grouped sections by information layer, not as a flat list.
    - Keep grouped recaps compact; omit sections that would be empty, repetitive, or low-value.
    - Use shared open question blocks for every interactive question in this workflow.
    - Each open question block must present, in order: a stage header, question header, prompt, example when useful, recommendation, options, and reply instruction.
    - Keep the stage header minimal: `SPECIFY SESSION` plus the current question counter, for example `2 / 5`.
    - Use the question header for a short topic label only.
    - Default to a one-sentence prompt. Put extra context into the example line, grouped sub-points, or recommendation line instead of turning the prompt into a paragraph.
    - Include a one-line `Example` row whenever the topic benefits from a concrete case.
    - When you present options, mark exactly one option in the recommendation with a `[ RECOMMENDED ]` badge and follow it with a single short rationale sentence.
    - Keep the open block visually structured through ordering, spacing, and labels rather than right-side borders or closed ASCII framing.
    - Do not rely on interactive selection widgets. Assume the user will answer in plain text.
    - After the options, explicitly invite natural-language replies, for example: `Reply naturally, for example: "A", "选 C", "我选推荐项"`.
    - Accept common natural-language answer forms such as `A`, `选A`, `我选 C`, `推荐的那个`, or a short paraphrase that clearly matches one option.
    - After parsing the answer, acknowledge it with one lightweight confirmation line and continue, for example: `Recorded: C - Normalize first`.
    - Do not repeat the same question in both the summary and the follow-up ask.
    - If you include a grouped recap and are about to ask the next question immediately, summarize it briefly under `Outstanding Questions` instead of restating the full wording there.
    - Save the full synthesis for the alignment-ready turn, the written artifacts (`alignment.md`, `context.md`, `spec.md`, `references.md`), or when the user explicitly asks to see everything collected so far.
    - Do not turn this into a freeform brainstorming workflow.
    - each clarification turn should contain at most one short checkpoint or one grouped recap, plus one question block.

17. Apply a current-understanding or confirmation gate before release.
    - Before releasing `Aligned: ready for plan`, provide a grouped recap that covers goal, users and roles, scope boundaries, locked decisions, technical constraints or assumptions, and outstanding questions.
    - Explicitly ask the user to confirm or correct the current understanding before `Aligned: ready for plan`.
    - Treat this as an explicit pre-release check rather than a courtesy recap.
    - If the user corrects the recap, update the active understanding and continue clarification.
    - If planning-critical gaps remain after the recap, do not release `Aligned: ready for plan`.

18. Apply a release readiness gate.
    - If the requirement package has enough clarity to plan safely inside `sp-specify`, release `Aligned: ready for plan`.
    - If common docs/config/process-change flows or bounded feature work can reach planning-ready alignment inside `sp-specify`, do so without needing `/sp.spec-extend`.
    - If planning-critical gaps remain but the spec package is still salvageable, recommend `/sp.spec-extend` as the next command instead of `/sp.plan`.
    - Only use `Force proceed with known risks` when the user accepts that unresolved planning risk will be carried into downstream work.
    - Make the closeout explicit: if ambiguity remains, ask whether the user wants to continue exploring or move to the next step with the documented risks.
    - Do not release `Aligned: ready for plan` when the current understanding still depends on taste words, implicit defaults, or untested assumptions in place of concrete behavior, boundary handling, compatibility impact, or acceptance proof.

    Use this open question block structure in the user's current language:

    ```text
    Stage header
    SPECIFY SESSION - 2 / 5

    Question header
    [Short topic label]

    Prompt
    [One-sentence question stem]

    Example
    [One-line concrete example]

    Recommendation
    [ RECOMMENDED ] [Option letter]
    [One short rationale sentence]

    Options
    A. [Option text]
    B. [Option text]
    C. [Option text]
    D. [Option text]

    Reply instruction

    Reply naturally, for example: "A", "选 C", "我选推荐项"
    ```

    Use this grouped recap structure in the user's current language:

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

19. Alignment decision gate.
    Decide exactly one:
    - `Aligned: ready for plan`
      Use only when:
      - mandatory clarity gates are sufficiently resolved
      - the whole-feature analysis is complete
      - capability decomposition is bounded enough to plan
      - no unresolved high-impact ambiguity remains
      - the spec can be written as a bounded, testable document
      - no `[NEEDS CLARIFICATION]` markers are needed
    - `Force proceed with known risks`
      Use only when:
      - unresolved high-impact ambiguity remains
      - the user explicitly chooses to continue anyway

    Before `Aligned: ready for plan`, run a current-understanding or confirmation gate.
    - Present the grouped current understanding as an explicit pre-release check.
    - Ask the user to confirm or correct the current understanding before `Aligned: ready for plan`.
    - common docs/config/process-change flows can reach planning-ready alignment inside `sp-specify` when this gate passes and no planning-critical ambiguity remains.
    - keep this path inside `sp-specify`, without needing `/sp.spec-extend`.

    If planning-critical ambiguity remains around scope, workflow behavior, constraints, or success criteria, keep the workflow in clarification until it is resolved or the user explicitly chooses `Force proceed with known risks`.

    If neither condition is met, continue clarification.

20. Write `spec.md` to `SPEC_FILE` using the template structure.
    Requirements:
    - clean result-state document only
    - no `[NEEDS CLARIFICATION]`
    - no speculative implementation details presented as facts
    - include the analyzed whole-feature overview
    - include scenarios and usage paths
    - include capability decomposition
    - include implementation-oriented analysis suitable for planning
    - include alignment state showing confirmed vs inferred vs unresolved
    - include risks and gaps that could affect planning
    - requirements must be testable
    - scope must be bounded
    - emit a planning-ready requirement package rather than a surface summary

21. Write `alignment.md` to `ALIGNMENT_FILE`.
    It must include:
    - task classification
    - current aligned understanding
    - confirmed facts
    - low-risk inferences
    - unresolved items
    - clarification summary
    - release decision:
      - `Aligned: ready for plan`
      - or `Force proceed with known risks`
    - downstream planning impact
    - reason for the release decision

22. Write `context.md` to `CONTEXT_FILE`.
    It must include:
    - phase or feature boundary
    - locked decisions
    - Claude discretion
    - canonical references
    - existing code insights when relevant
    - specific user signals that would change implementation shape
    - outstanding questions when force proceeding
    - deferred or future ideas
    - enough implementation context that downstream planning does not need to reconstruct these decisions from prose scattered across other artifacts

23. Write `references.md` to `REFERENCES_FILE` when any meaningful source material was used.
    It must include, for each retained source:
    - source
    - description
    - relevance
    - reusable insights
    - spec impact mapping

24. Generate or update `FEATURE_DIR/checklists/requirements.md` with these validation items:

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
    - [ ] Capability decomposition is planning-ready
    - [ ] Confirmed vs inferred vs unresolved states are recorded

    ## Alignment Readiness

    - [ ] alignment.md exists
    - [ ] context.md exists
    - [ ] Task classification is recorded
    - [ ] Release decision is recorded
    - [ ] Release decision is either `Aligned: ready for plan` or `Force proceed with known risks`
    - [ ] Locked decisions are preserved in context.md
    - [ ] Remaining risks are empty for normal completion

    ## Notes

    - Items marked incomplete require spec updates before `/sp.plan`
    ```

25. Re-run validation after edits. Normal completion must pass all required checks.

26. Report completion with:
    - branch name
    - spec file path
    - alignment report path
    - context file path
    - references file path when created
    - checklist results
    - release decision
    - readiness for the next phase (`/sp.plan` for the mainline, or `/sp.spec-extend` when deeper analysis is still needed)
    - Use the user's current language for the completion report and any explanatory text, while preserving literal command names, file paths, and fixed status values exactly as written.

27. **Check for extension hooks**: After reporting completion, check if `.specify/extensions.yml` exists in the project root.
    - If it exists, read it and look for entries under the `hooks.after_specify` key.
    - If the YAML cannot be parsed or is invalid, skip hook checking silently and continue normally.
    - Filter out hooks where `enabled` is explicitly `false`. Treat hooks without an `enabled` field as enabled by default.
    - For each remaining hook, do **not** attempt to interpret or evaluate hook `condition` expressions:
      - If the hook has no `condition` field, or it is null/empty, treat the hook as executable.
      - If the hook defines a non-empty `condition`, skip the hook and leave condition evaluation to the HookExecutor implementation.
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
    - If no hooks are registered or `.specify/extensions.yml` does not exist, skip silently.

## Quick Guidelines

- Focus on **WHAT** users need, **WHY** they need it, and what a planner must preserve.
- Start with whole-feature analysis before writing capability details.
- Decompose into capabilities only after the whole feature is understood.
- Distinguish confirmed facts, low-risk inferences, and unresolved items explicitly.
- Avoid HOW to implement unless a dependency, constraint, or planning risk must be named.
- Write for business stakeholders and planners, not only developers.
- Do not embed checklists in the spec itself.
- Low-risk defaults may be adopted silently.
- High-impact ambiguity must be resolved or explicitly force-continued.
- Preserve maintainable wording and avoid brittle, surface-only summaries.

### Section Requirements

- **Mandatory sections**: Must be completed for every feature.
- **Optional sections**: Include only when relevant to the feature.
- When a section doesn't apply, remove it entirely (do not leave "N/A").

### For AI Generation

1. Do not guess high-impact decisions that materially affect scope, UX, compatibility, security, data shape, acceptance testing, capability boundaries, or downstream planning.
2. Use low-risk defaults quietly and record them in `alignment.md` plus the alignment state in `spec.md` when relevant.
3. If the user thinks they have explained the request clearly but important ambiguity remains, keep clarifying.
4. Think like a planner and tester: if a requirement cannot be planned or tested reliably, it is not aligned enough yet.
5. Normal completion requires no open clarification markers.
6. If the user insists on continuing anyway, allow `Force proceed with known risks`, but record the unresolved items and likely downstream impact.
7. Match the user's current language for all user-visible output unless a literal command name, file path, or fixed status value must remain unchanged.
8. Do not treat MVP minimization as the default strategy; scope the first release to a coherent, quality-appropriate slice unless the user explicitly asks for a smaller release.
