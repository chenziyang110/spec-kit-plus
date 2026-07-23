# sp-design: Design System Workflow

You are running `sp-design`. This is a design-system workflow, not an implementation workflow.

## Objective

Produce, refine, synthesize, or audit the project's root `DESIGN.md`
design-system contract. For a new or unresolved direction, first create a
project-neutral HTML design preview board with three comparable directions so
the user can inspect the actual component, state, responsive, and motion
language before downstream UI work starts.

## Process

Follow the phase lock, intake, synthesis, review, and closeout steps below. Keep the work design-only unless the user explicitly starts a downstream implementation workflow after reviewing the design output.

## Workflow Phase Lock

- Create or resume `.specify/design/design-state.md` before substantial design synthesis.
- Set durable state with:
  - `active_command: sp-design`
  - `phase_mode: design-only`
  - `current_stage: context-intake`
  - `allowed_writes: DESIGN.md, .specify/design/design-state.md, .specify/design/design-brief.md, .specify/design/references.md, .specify/design/options.md, .specify/design/previews/*.html, .specify/design/review.md, .specify/memory/project-rules.md`
  - `forbidden_actions: edit source code, edit tests, write CSS/theme implementation files, create UI components, create feature specs, create plan artifacts, create task artifacts`
- When resuming after compaction, read `.specify/design/design-state.md` before continuing.

## Allowed Writes

- `DESIGN.md`
- `.specify/design/design-state.md`
- `.specify/design/design-brief.md`
- `.specify/design/references.md`
- `.specify/design/options.md`
- `.specify/design/previews/*.html`
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

## Design Question Loop

1. Create `.specify/design/design-brief.md` from
   `.specify/templates/design-brief-template.md` when the template is
   installed. Store confirmed decisions and unresolved design questions, not a
   conversation transcript.
2. Infer everything supported by the repository, supplied references, and
   prior confirmed answers before asking the user.
3. Ask one high-impact design question at a time when the answer can change
   visual hierarchy, density, component anatomy, motion, responsive
   adaptation, accessibility, reference fidelity, or the approval boundary.
   Make each question build on the user's latest answer and include a concrete
   recommendation when one is justified.
4. Do not ask which production framework, CSS library, or rendering stack to
   use merely to shape the preview. The HTML board is a framework-neutral
   review carrier. Ask about a technical constraint only when it changes the
   target platform or the visual/interaction result.
5. Before generating directions, confirm the product subject, audience, single
   user job, platform/viewports, real or representative content, required
   component/state coverage, meaningful motion moments, reduced-motion
   equivalent, references, and Must Preserve / May Adapt / Must Not boundaries.
6. Continue the question loop until those decisions are either confirmed or
   explicitly represented as bounded differences among the three directions.

## Three-Direction Preview Loop

- For `create`, `synthesize`, or any unresolved high-visibility `refine`, use
  `{{specify-subcmd:design preview --out .specify/design/previews/round-NN.html}}`
  or copy `.specify/templates/design-preview-template.html` when the helper is
  unavailable.
- Each review round contains exactly three project-specific directions in one
  self-contained HTML board. Keep the component inventory, state matrix,
  example content, and viewports identical across all three so the comparison
  isolates visual, density, and motion decisions.
- Replace every scaffold placeholder, set `data-preview-status="candidate"`,
  and run
  `{{specify-subcmd:design preview-lint .specify/design/previews/round-NN.html --level ready}}`.
- Inspect the board in a real browser at representative desktop and mobile
  widths. Verify direction switching, keyboard operation, overflow, component
  states, meaningful animation, and `prefers-reduced-motion`.
- Present the exact round path plus all three direction IDs and tradeoffs. Ask
  the user to select one, combine named elements, or describe what remains
  wrong. Approval must refer to the inspected HTML and one direction ID.
- If the user is not satisfied, update the design brief and generate the next
  `round-NN.html`. Continue until the user approves. Do not overwrite a prior
  review round, and never reinterpret criticism as approval.
- Once approved, freeze that round, record
  `approved_visual_ref: .specify/design/previews/round-NN.html#<direction-id>`
  in the design brief and review, and use the same exact reference in
  `DESIGN.md` `approval.visual_refs`. Later revisions require a new round and
  renewed approval.

## Preview Technology And Content Contract

- The installed `design-preview-template.html` is a universal design specimen,
  not a whole-project mock application and not production source. It must
  remain usable for any project by replacing content and tokens rather than
  changing its product boundary.
- Use modern native web capabilities deliberately: semantic HTML, CSS custom
  properties, cascade layers, fluid `clamp()` scales, container queries,
  progressive view transitions, and a small inline script only for review
  navigation, keyboard support, and motion replay.
- Keep the artifact a single HTML file with no framework, CDN, remote font,
  external CSS/JavaScript, network call, persistence, analytics, or business
  logic. Modernity comes from expressive layout and motion, not dependency
  weight.
- Show foundations, buttons, inputs, navigation, list/data density, feedback,
  default/hover/focus/pressed/loading/disabled/empty/error/success states,
  responsive adaptations, and implementation-facing handoff boundaries.
- Motion must reveal hierarchy, reinforce action, or explain state change.
  Define duration/easing/distance tokens and an equivalent
  `prefers-reduced-motion` experience. Do not scatter decorative animation.
- Preserve the feature-level `ui-target.html` boundary: that later artifact
  owns one feature's concrete composition. The project-level design preview
  owns reusable visual, component, state, density, and motion decisions.

## Synthesis Rules

- Write the project's own `DESIGN.md` as the final output.
- Present the exactly three HTML-backed directions from the active preview
  round when creating or synthesizing a design system.
- Before proposing them, name the product subject, audience, and single user job.
- Each direction must state a visual thesis, content thesis, interaction thesis,
  signature element, platform fit, state strategy, safe system choices, and any
  deliberate creative risk with its gain and cost.
- Render all three through the shared HTML design preview and ask the user to
  approve the inspected direction before writing or replacing `DESIGN.md`; a
  prose label, mood adjective, or unseen file is not approval.
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

The workflow output is a root `DESIGN.md` contract plus the confirmed design
brief, immutable HTML preview rounds, and supporting `.specify/design/*` state,
references, options, and review artifacts.

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

1. Run the active round's
   `{{specify-subcmd:design preview-lint .specify/design/previews/round-NN.html --level ready}}`,
   then run `{{specify-subcmd:design lint --level ready}}` when the CLI helpers
   are available.
2. Write `.specify/design/review.md` with:
   - selected mode
   - inputs read
   - design question decisions
   - preview round and validation result
   - approved direction
   - exact `approved_visual_ref`
   - requested revisions from rejected rounds
   - platforms covered
   - design-system risks
   - lint result
   - recommended next workflow
3. Ask the user to review the written design before downstream workflows consume it as locked input.

## Closeout

Close with the design-system status, changed files, lint result, and exactly one recommended next command.

## Guardrails

- Do not edit source code, tests, CSS/theme implementation files, UI components, feature specs, plan artifacts, or task artifacts from this command.
- Inline HTML/CSS and bounded review-only JavaScript inside
  `.specify/design/previews/*.html` are design artifacts allowed by this
  workflow; they are not application implementation.
- Do not clone protected brands or copy third-party design files into `DESIGN.md`; synthesize project-owned design principles and tokens.
- Do not let downstream workflows treat an unaudited or contradictory `DESIGN.md` as locked input.
