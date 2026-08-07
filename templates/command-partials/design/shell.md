# sp-design: Design System Workflow

You are running `sp-design`. This is a design-system workflow, not an implementation workflow.

## Objective

Prompt-route one public `sp-design` entry to create, refine, or audit the
project's root `DESIGN.md` only through `specify-runtime design`; use synthesis
only as the input strategy for create/refine. For a new or unresolved direction, first create a
project-neutral HTML design preview board with three comparable directions so
the user can inspect the actual component, state, responsive, and motion
language before downstream UI work starts.

## Process

Follow the phase lock, intake, synthesis, review, and closeout steps below. Keep the work design-only unless the user explicitly starts a downstream implementation workflow after reviewing the design output.

## Workflow Phase Lock

- Initialize design state through `specify-runtime design preview` and resume it through `artifact show`; never create or edit `.specify/design/design-state.md` directly.
- Set durable state with:
  - `active_command: sp-design`
  - `phase_mode: design-only`
  - `current_stage: context-intake`
  - `allowed_writes: DESIGN.md, .specify/design/design-state.md, .specify/design/design-brief.md, .specify/design/design-system.json, .specify/design/references.md, .specify/design/options.md, .specify/design/previews/*.html, .specify/design/previews/*.approval.json, .specify/design/previews/*.handoff.json, .specify/design/review.md, .specify/memory/project-rules.md`
  - `forbidden_actions: edit source code, edit tests, write CSS/theme implementation files, create UI components, create feature specs, create plan artifacts, create task artifacts`
- When resuming after compaction, query `.specify/design/design-state.md` through `specify-runtime artifact show` before continuing.

## Allowed Writes

- `DESIGN.md`
- `.specify/design/design-state.md`
- `.specify/design/design-brief.md`
- `.specify/design/design-system.json`
- `.specify/design/references.md`
- `.specify/design/options.md`
- `.specify/design/previews/*.html`
- `.specify/design/previews/*.approval.json`
- `.specify/design/previews/*.handoff.json`
- `.specify/design/review.md`
- stable design rules in `.specify/memory/project-rules.md` when they should become shared project defaults

## Forbidden Writes

- source code
- UI components
- CSS or theme implementation files
- tests
- business feature specs
- plan or task artifacts outside the active design workflow

## Prompt Routing

Read `references/task-router.md` at every entry or resume. Infer
`task_type: create | refine | audit` from the prompt and current approval state;
infer `input_strategy: context | synthesize` independently. Resume nonterminal
design work before reclassification. Keep `sp-design` as the only public entry
and never require a colon subskill or explicit mode argument.

## Intake

1. Query `DESIGN.md` through `specify-runtime artifact show` if it exists.
   If it declares `design_system.status: bootstrap`, treat it as a starter to
   replace, not an approved constraint or evidence that design work is done.
2. Query design references/options/review through targeted `specify-runtime artifact show` calls if they exist.
3. Read `README.md`, project handbook files, existing UI surfaces, and existing design files. Use the command's shared Learning intake for project rules and reusable lessons.
4. Use project cognition to locate likely UI entry points, token/theme owners,
   reusable component owners, responsive/state patterns, visual or accessibility
   tests, and design assets; verify every selected route in live files before it
   becomes design evidence.
5. Classify the experience separately by work type, surface type (`landing`,
   `product-workspace`, `hybrid`, or `existing-pattern-maintenance`), and one or
   more capability profiles. Read the deterministic catalog with
   `{{specify-subcmd:specify-runtime design profiles}}`; supported profiles are
   `web`, `mobile`, `desktop`, `cli`, `tui`, `content`, and `no-ui`. A hybrid
   product selects multiple visual profiles rather than collapsing them into a
   single project-type enum.
6. If and only if `no-ui` is supported by current repository evidence, record
   `design_system_status: not-applicable` with that evidence and exit this
   visual workflow. Do not generate three directions, HTML, approval, handoff,
   `ui-target`, or visual comparison, and never combine `no-ui` with a visual
   profile.
7. If references are supplied as URLs, screenshots, text notes, existing design files, or imported summaries, assign each an explicit intent: `exact`, `preserve-structure`, `inspiration`, `extract-tokens`, or `do-not-copy`.
8. When built-in presets help, read shipped files under
   `.specify/templates/design-library/` or `templates/design-library/`
   (including aesthetic seeds and `anti-slop-policy.md`) and treat them as
   inspiration only—never as approved product direction or a substitute for
   `design approve`.

## Design Question Loop

1. Create `.specify/design/design-brief.md` with
   `specify-runtime artifact scaffold --kind design-brief --path .specify/design/design-brief.md`,
   then fill only its affected frontmatter fields and named sections through
   leased `artifact patch` calls. The runtime expands the installed stable
   template; never read and reproduce that boilerplate in memory. Store
   confirmed decisions and unresolved design questions, not a conversation
   transcript.
2. Infer everything supported by the repository, supplied references, and
   prior confirmed answers before asking the user.
3. **Taste intake gate (create / project-wide refine):** before three-direction
   preview work, patch durable taste fields into the brief:
   - `design_read`: one-line "Reading this as: <kind> for <audience>, with a
     <vibe> language, leaning toward <foundation or aesthetic family>"
   - `dials.variance` / `dials.motion` / `dials.density` (integers 1-10) plus
     `dials.inference_reason`
   - `aesthetic_family`, `foundation_strategy`
     (`owned-tokens` | `real-ds:<name>` | `live-product-extension`)
   - `redesign_mode` when refining or auditing live UI
     (`greenfield` | `preserve` | `overhaul`)
   - `anti_slop_locks` selected from
     `.specify/templates/design-library/anti-slop-policy.md` (surface-aware;
     subordinate to an already approved `DESIGN.md`)
   - `reference_board_intents` when `input_strategy: synthesize`
     (`mood` | `layout` | `type` | `color-only`); references are evidence, not
     a license to copy protected brand or artwork
4. Ask one high-impact design question at a time when the answer can change
   visual hierarchy, density, component anatomy, motion, responsive
   adaptation, accessibility, reference fidelity, dial vectors, or the approval
   boundary. Make each question build on the user's latest answer and include a
   concrete recommendation when one is justified.
5. Do not ask which production framework, CSS library, or rendering stack to
   use merely to shape the preview. The HTML board is a framework-neutral
   review carrier. Ask about a technical constraint only when it changes the
   target platform or the visual/interaction result.
6. Before generating directions, confirm the product subject, audience, single
   user job, modules, locales, color modes, platform/viewports, real or
   representative content, required component/state coverage, meaningful
   motion moments, reduced-motion equivalent, references, taste intake fields,
   and Must Preserve / May Adapt / Must Not boundaries.
7. Continue the question loop until those decisions are either confirmed or
   explicitly represented as bounded differences among the three directions.
8. Record each confirmed choice as a stable design decision (`DS-<KIND>-NNN`)
   with its statement, source, status, affected surfaces, and verification
   method. The brief is the decision ledger; do not leave important choices
   trapped only in conversation prose.

## Redesign Protocol (refine / audit)

When live UI or an approved system already exists:

1. Detect mode: `preserve` modernizes without breaking brand; `overhaul` allows
   a new visual language while preserving content/IA unless asked otherwise.
2. Audit before mutate: brand tokens, IA, signature interactions, AI-slop
   patterns to retire, current dial reading of the live surface, and web SEO
   or analytics ID risks when applicable.
3. `audit` reports readiness and drift without changing approved truth.
   Promote to `refine` only when design truth must change, then open a new
   immutable review round.

## Three-Direction Preview Loop (freeform board)

The preview board is chrome plus three freeform direction canvases, not a fixed
product UI specimen grid. Follow taste-skill-style creative authorship: invent
layout, type, motion, and composition freely for each direction while governance
stays machine-checkable via the embedded manifest and ready lint.

- For `create`, or any unresolved high-visibility `refine`, with either input
  strategy, scaffold the compact source with
  `{{specify-subcmd:specify-runtime design preview-manifest --profiles <comma-separated-profile-ids> --out .specify/design/previews/round-NN.manifest.json}}`,
  fill project-specific manifest fields through leased `specify-runtime artifact patch`
  calls, then render the freeform board shell with
  `{{specify-subcmd:specify-runtime design preview --manifest .specify/design/previews/round-NN.manifest.json --out .specify/design/previews/round-NN.html}}`.
- **Author creative HTML/CSS inside each `#direction-*` canvas** after render.
  Hand-editing direction canvases is expected. Preserve stable direction IDs
  (`direction-a|b|c`), board chrome, hash routing, and `#design-preview-manifest`.
  Do not treat freeform seed copy as product UI.
- Each review round holds exactly three project-specific directions in one
  self-contained HTML board. Keep comparison content constant; change design
  language freely. Manifest capability profiles still project specimens/states
  for handoff contracts without forcing a fixed specimen HTML layout.
- Force direction divergence while holding comparison content constant: each
  direction needs its own project-specific `dials` triple
  (variance/motion/density with non-scaffold inference reasons), unique
  `signature_element`, and `aesthetic_family`. Ready lint rejects scaffold
  baseline taste wording, near-duplicate dial vectors (multi-axis distance),
  near-duplicate signatures, and identical visual token payloads
  (typography/geometry/density/elevation/motion/modes). Do not ship template
  dials unchanged.
- Configure the manifest with representative content for every specimen,
  directions, boundaries, tokens, every decision-to-owner mapping, modes, and
  targets. Keep registry-required capabilities and specimen kinds; add a
  project-specific capability/specimen only when its profile, content keys,
  states, owner, and acceptance coverage are explicit. The renderer
  must produce the matching embedded `spec-kit-design-preview-manifest-v1`;
  then run
  `{{specify-subcmd:specify-runtime design preview-lint .specify/design/previews/round-NN.html --level ready}}`.
- Inspect the board in a real browser at representative desktop and mobile
  widths. Verify direction switching, keyboard operation, overflow, component
  states, meaningful animation, and `prefers-reduced-motion`.
- Present the exact round path plus all three direction IDs and tradeoffs. Ask
  the user to select one, combine named elements, or describe what remains
  wrong. Approval must refer to the inspected HTML and one direction ID.
- A requested combination is a fourth, new composition: encode it as a named
  direction in the next immutable round and have the user inspect that result.
  Never approve a verbal mix of fragments from different directions.
- If the user is not satisfied, patch the design brief through `specify-runtime
  artifact patch` and generate the next `round-NN.html` only with
  `specify-runtime design preview`. Continue until the user approves. Do not overwrite a prior
  review round, and never reinterpret criticism as approval.
- Once the user explicitly approves, freeze it with
  `{{specify-subcmd:specify-runtime design approve .specify/design/previews/round-NN.html --direction <direction-id> --format json}}`.
  This command changes the candidate to approved, embeds the selected
  direction and writes immutable `.approval.json` plus selected-direction
  `.handoff.json` sidecars. Record
  `approved_visual_ref: .specify/design/previews/round-NN.html#<direction-id>`
  plus the returned preview, manifest, and handoff SHA-256 values, handoff ref,
  review round, exact `DS-*` decision IDs, and exact `DH-*` handoff contract IDs
  plus the approved capability profile and specimen IDs in the brief and
  review. Use the same values in `DESIGN.md` `approval`,
  `capability_profiles`, and `specimens`.
  Later revisions require a new round and renewed approval; an edited approved
  file or stale/missing approval or handoff sidecar is invalid.

## Preview Technology And Content Contract

- The installed `design-preview-template.html` is a universal review carrier
  with a baseline specimen, not a claim that every product uses the same Web
  controls, a whole-project mock application, or production source. Keep the
  review shell stable while the authored manifest stays project-specific; the
  platform-adaptive specimen contract owns which surfaces and states apply.
- Use modern native web capabilities deliberately: semantic HTML, CSS custom
  properties, cascade layers, fluid `clamp()` scales, container queries,
  progressive view transitions, URL-addressable direction/state controls, and
  a small inline script only for review navigation, keyboard support, live
  viewport/state switching, comparison, and motion replay.
- Keep the artifact a single HTML file with no framework, CDN, remote font,
  external CSS/JavaScript, network call, persistence, analytics, or business
  logic. Modernity comes from expressive layout and motion, not dependency
  weight.
- Show the specimens derived from the selected profiles: browser layout/forms
  for Web, safe-area/touch/keyboard behavior for mobile, window/menu/multi-pane
  behavior for desktop, help/outcome/progress and piped/no-color behavior for
  CLI, cell-grid/focus/overlay behavior for TUI, and editorial/media/localized/
  print flow for content-led products. Do not retain irrelevant Web controls as
  a universal baseline.
- Keep the visible specimen and embedded manifest in sync. Every approved
  color, type, spacing, component, motion, responsive, and content rule needs a
  stable decision ID and an implementation token or named owner. The preview
  is executable design evidence, not merely a styled gallery.
- Make the handoff itself visible before approval. The complete capability
  model and its specimen IDs, component anatomy and required states,
  presentation targets, visual acceptance rows, structured
  comparison tolerance, implementation bindings, and permitted deviations
  use stable `DH-*` IDs. Ready lint must reject an unknown/no-UI profile,
  missing required capability or specimen kind, direction/specimen drift,
  uncovered states, profile targets, specimens, or `DS-*` decisions. The
  approved `.handoff.json` is generated from
  the selected direction; never summarize or re-author it by hand.
- Motion must reveal hierarchy, reinforce action, or explain state change.
  Define duration/easing/distance tokens and an equivalent
  `prefers-reduced-motion` experience. Do not scatter decorative animation.
- Preserve the feature-level `ui-target.html` boundary: that later artifact
  owns one feature's concrete composition. The project-level design preview
  owns reusable visual, component, state, density, and motion decisions.

## Synthesis Rules

- Export the project's `DESIGN.md` only through `specify-runtime design export` from the approved round. Never write `DESIGN.md` directly.
- Present exactly the three HTML-backed directions from the active preview
  round when creating a design system or when synthesis shapes a material
  refinement.
- Before proposing them, name the product subject, audience, and single user job.
- Each direction must state a visual thesis, content thesis, interaction thesis,
  signature element, platform fit, state strategy, safe system choices, and any
  deliberate creative risk with its gain and cost.
- Render all three through the shared HTML design preview and ask the user to
  approve the inspected direction before running `specify-runtime design export` for `DESIGN.md`; a
  prose label, mood adjective, or unseen file is not approval.
- Ask the user to approve a direction; approval refers to its inspectable visual
  artifact and recorded tradeoffs, not only its name.
- Preserve existing project rules unless the user approves a design-system change that supersedes them.
- Do not copy external brand names, protected visual identity, proprietary token names, or third-party file text into the final design system.
- Normalize approved direction into `spec-kit-design-v1` YAML front matter plus readable Markdown guidance.
- Set `design_system.status: approved` and record
  `design_system.approval.status`, the selected direction, and concrete product
  or repository `source_refs`, plus `approval.visual_refs`, review round,
  preview/manifest/handoff SHA-256 values, immutable handoff ref, approved
  decision IDs, and approved handoff contract IDs. Record
  `product_context`, `direction_contract`, color modes, responsive/content
  contracts, decisions, and verification matrices. Remove unresolved
  placeholders and generic starter choices that are not justified by those
  sources.

## Output Contract

The workflow output is a root `DESIGN.md` contract plus the confirmed design
brief, immutable HTML preview rounds, and supporting `.specify/design/*` state,
  references, options, review artifacts, and the immutable selected-direction
  handoff sidecar.

## Required DESIGN.md Shape

`DESIGN.md` must contain:

- YAML front matter with `design_system.schema: spec-kit-design-v1`
- `design_system.status: approved` plus approval direction, source refs,
  immutable visual and handoff references, review round,
  preview/manifest/handoff SHA-256 values, approved decision IDs, and approved
  handoff contract IDs
- product subject, audience, single job, and approved visual reference
- visual, content, and interaction theses; one signature element; safe system
  choices; and deliberate creative risks
- `design_system.name`
- `design_system.version`
- `design_system.platforms`
- non-empty token categories for `color`, `spacing`, `radius`, `typography`, and
  `motion`, plus applicable elevation, sizing, and layout tokens
- color-mode contracts, including required accessibility modes
- component required states, token references, and design decision references
- responsive breakpoints/adaptations and real-content/imagery rules
- canonical design decisions with verification methods
- required viewport/state evidence, visual tolerance, and accepted deviations
- accessibility intent for contrast, focus, keyboard, reduced motion, touch,
  and forced colors
- Markdown sections for `Product Feel`, `Design Direction`, `Visual And
  Interaction Signature`, `Foundations`, `Platforms`, `Component Rules`,
  `Motion Rules`, `Responsive Behavior`, `Content And Imagery`,
  `Anti-Patterns`, `Design Change Policy`, `UI QA Checklist`, `Reference
  Fidelity`, and `Planned Gaps and Exceptions`

## Review

Before closeout:

1. Run the active round's
   `{{specify-subcmd:specify-runtime design preview-lint .specify/design/previews/round-NN.html --level ready}}`,
   then run `{{specify-subcmd:specify-runtime design lint --level ready}}` when the CLI helpers
   are available. Export the same approved contract with
   `{{specify-subcmd:specify-runtime design export DESIGN.md --format json --out .specify/design/design-system.json}}`
   so implementation consumes deterministic data rather than reconstructing
   YAML prose.
2. If `.specify/design/review.md` is absent, create its fixed shape with
   `specify-runtime artifact scaffold --kind design-review --path .specify/design/review.md`.
   Otherwise query it through `artifact show`. Patch only these named semantic
   sections through a fresh lease per section; never submit or reconstruct the
   whole review document:
   - selected task type and input strategy
   - inputs read
   - design question decisions
   - preview round and validation result
   - approved direction
   - exact `approved_visual_ref`
   - preview/manifest/handoff SHA-256 values and approval/handoff sidecars
   - approved design decision IDs
   - approved handoff contract IDs
   - requested revisions from rejected rounds
   - platforms covered
   - design-system risks
   - lint result
   - recommended next workflow
3. Ask the user to review the written design before downstream workflows consume it as locked input.

## Closeout

Read `references/consumer-contract.md`, then close with the design-system
status, changed files, lint result, pinned approval identity, and exactly one
recommended next command. Do not bypass explicit feature or Quick adoption of a
new approval.

## Guardrails

- Do not edit source code, tests, CSS/theme implementation files, UI components, feature specs, plan artifacts, or task artifacts from this command.
- Inline HTML/CSS and bounded review-only JavaScript inside
  `.specify/design/previews/*.html` are design artifacts allowed by this
  workflow; they are not application implementation.
- Never hand-edit an approved preview or its sidecar. Generate a new numbered
  candidate round, obtain approval, and let `design approve` freeze it.
- Do not clone protected brands or copy third-party design files into `DESIGN.md`; synthesize project-owned design principles and tokens.
- Do not let downstream workflows treat an unaudited or contradictory `DESIGN.md` as locked input.
