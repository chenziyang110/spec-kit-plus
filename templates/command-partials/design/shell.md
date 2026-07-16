# sp-design: Design System Workflow

You are running `sp-design`. This is a design-system workflow, not an implementation workflow.

## Objective

Produce, refine, synthesize, or audit the project's root `DESIGN.md` design-system contract so downstream UI work has a stable visual and interaction system before implementation starts.

## Process

Follow the phase lock, intake, synthesis, review, and closeout steps below. Keep the work design-only unless the user explicitly starts a downstream implementation workflow after reviewing the design output.

## Workflow Phase Lock

- Create or resume `.specify/design/design-state.md` before substantial design synthesis.
- Set durable state with:
  - `active_command: sp-design`
  - `phase_mode: design-only`
  - `current_stage: context-intake`
  - `allowed_writes: DESIGN.md, .specify/design/design-state.md, .specify/design/references.md, .specify/design/options.md, .specify/design/review.md, .specify/memory/project-rules.md`
  - `forbidden_actions: edit source code, edit tests, write CSS/theme implementation files, create UI components, create feature specs, create plan artifacts, create task artifacts`
- When resuming after compaction, read `.specify/design/design-state.md` before continuing.

## Allowed Writes

- `DESIGN.md`
- `.specify/design/design-state.md`
- `.specify/design/references.md`
- `.specify/design/options.md`
- `.specify/design/review.md`
- stable design rules in `.specify/memory/project-rules.md` when they should become shared project defaults

## Forbidden Writes

- source code
- UI components
- CSS or theme implementation files
- tests
- business feature specs
- plan or task artifacts outside the active design workflow

## Modes

Infer the mode from the user's request:

- `create`: generate a new project design system from product context.
- `synthesize`: transform references into an original design system.
- `refine`: update an existing `DESIGN.md`.
- `audit`: inspect whether the current design system is enough for upcoming UI work.

If the mode is ambiguous, choose the smallest safe mode and state the assumption.

## Intake

1. Read `DESIGN.md` if it exists.
   If it declares `design_system.status: bootstrap`, treat it as a starter to
   replace, not an approved constraint or evidence that design work is done.
2. Read `.specify/design/references.md`, `.specify/design/options.md`, and `.specify/design/review.md` if they exist.
3. Read `README.md`, project handbook files, existing UI surfaces, and existing design files. Use the command's shared Learning intake for project rules and reusable lessons.
4. Use project cognition to locate likely UI entry points, token/theme owners,
   reusable component owners, responsive/state patterns, visual or accessibility
   tests, and design assets; verify every selected route in live files before it
   becomes design evidence.
5. Classify the experience separately by work type, surface type (`landing`,
   `product-workspace`, `hybrid`, or `existing-pattern-maintenance`), and
   platform (`web`, `mobile`, `desktop`, `tui`, or `cli`).
6. If references are supplied as URLs, screenshots, text notes, existing design files, or imported summaries, assign each an explicit intent: `exact`, `preserve-structure`, `inspiration`, `extract-tokens`, or `do-not-copy`.
7. When built-in presets help, read one of the shipped preset files such as `.specify/templates/design-library/workbench-precision.md` or `templates/design-library/workbench-precision.md` and treat it as inspiration, not as a forced brand.

## Synthesis Rules

- Write the project's own `DESIGN.md` as the final output.
- Present two or three project-specific design directions when creating or synthesizing a design system.
- Before proposing them, name the product subject, audience, and single user job.
- Each direction must state a visual thesis, content thesis, interaction thesis,
  signature element, platform fit, state strategy, safe system choices, and any
  deliberate creative risk with its gain and cost.
- Give every direction an inspectable visual artifact such as a moodboard,
  rendered static composition, or screenshot. Ask the user to approve the
  visual direction before writing or replacing `DESIGN.md`; a prose label alone
  is not approval.
- Ask the user to approve a direction; approval refers to its inspectable visual
  artifact and recorded tradeoffs, not only its name.
- Preserve existing project rules unless the user approves a design-system change that supersedes them.
- Do not copy external brand names, protected visual identity, proprietary token names, or third-party file text into the final design system.
- Normalize approved direction into `spec-kit-design-v1` YAML front matter plus readable Markdown guidance.
- Set `design_system.status: approved` and record
  `design_system.approval.status`, the selected direction, and concrete product
  or repository `source_refs`, plus `approval.visual_refs`. Record
  `product_context` and `direction_contract`. Remove unresolved placeholders and generic
  starter choices that are not justified by those sources.

## Output Contract

The workflow output is a root `DESIGN.md` contract plus supporting `.specify/design/*` state, references, options, and review artifacts when relevant.

## Required DESIGN.md Shape

`DESIGN.md` must contain:

- YAML front matter with `design_system.schema: spec-kit-design-v1`
- `design_system.status: approved` plus approval direction and source refs
- product subject, audience, single job, and approved visual reference
- visual, content, and interaction theses plus one signature element
- `design_system.name`
- `design_system.version`
- `design_system.platforms`
- token categories for `color`, `spacing`, `radius`, and `typography`
- component required states and token references
- accessibility intent
- Markdown sections for `Product Feel`, `Platforms`, `Component Rules`, `Anti-Patterns`, `UI QA Checklist`, and `Design Change Policy`

## Review

Before closeout:

1. Run `specify design lint --level ready` when the CLI helper is available.
2. Write `.specify/design/review.md` with:
   - selected mode
   - inputs read
   - approved direction
   - approved visual reference
   - platforms covered
   - design-system risks
   - lint result
   - recommended next workflow
3. Ask the user to review the written design before downstream workflows consume it as locked input.

## Closeout

Close with the design-system status, changed files, lint result, and exactly one recommended next command.

## Guardrails

- Do not edit source code, tests, CSS/theme implementation files, UI components, feature specs, plan artifacts, or task artifacts from this command.
- Do not clone protected brands or copy third-party design files into `DESIGN.md`; synthesize project-owned design principles and tokens.
- Do not let downstream workflows treat an unaudited or contradictory `DESIGN.md` as locked input.
