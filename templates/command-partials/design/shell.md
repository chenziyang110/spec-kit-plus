# sp-design: UI Design Change Engine

You are running `sp-design`. This is a bounded UI design-change workflow, not an implementation workflow.

{{spec-kit-include: ../common/design-intelligence.md}}

## Objective

Prompt-route one public `sp-design` entry as the **UI Design Change Engine**
(Taste Intelligence + Design System Reverse Engineering + Visual Validation
setup). Create, refine, or audit one bounded `UD-*` change through
`specify-runtime design`; use synthesis only as the input strategy for
create/refine. Set `<change-dir>` to
`.specify/design/changes/<UD-ID>`. Prefer Evidence → UI System Model →
collaborative single-concept iteration over screenshot-to-page cloning or
batch option generation. The global
`.specify/design/index.json` is metadata only. No root design contract
participates in selection or delivery.

## Process

Follow the phase lock, intake, synthesis, review, and closeout steps below. Keep the work design-only unless the user explicitly starts a downstream implementation workflow after reviewing the design output.

## Workflow Phase Lock

- Resolve or create the active workspace by lifecycle state. Resume a matching
  draft from `.specify/design/index.json` when that registry exists; absent
  registration is legitimate discovery absence, not a reason to retry a missing
  artifact. Use stable path-like surface IDs from confirmed source or registered
  metadata, never the whole brief or a prose objective, for every `--scope`. Use
  `specify-runtime design change <UD-ID> --title <title> --type <greenfield|preserve|overhaul|extension> --scope <surface> --profiles <profiles>`
  only for a new bounded change; use
  `specify-runtime design iterate <SOURCE-UD-ID> <SUCCESSOR-UD-ID> --title <title> --type <preserve|overhaul|extension> [--scope <surface>]... --format json`
  when approved truth is being refined. `design iterate` pins `iteration_of`,
  `basis_sha256`, the exact baseline ref, and `supersedes` without mutating its
  registered source. Every requested scope must still be active on that source;
  if partial supersession already covers it, iterate from the active successor
  or choose a remaining active source scope.
- Set durable state with:
  - `active_command: sp-design`
  - `phase_mode: design-only`
  - `current_stage: context-intake`
  - `allowed_writes: .specify/design/index.json, <change-dir>/design-change.md, <change-dir>/brief.md, <change-dir>/design-contract.json, <change-dir>/references.md, <change-dir>/options.md, <change-dir>/previews/*, <change-dir>/review.md, .specify/memory/project-rules.md`
  - `forbidden_actions: edit source code, edit tests, write CSS/theme implementation files, create UI components, create feature specs, create plan artifacts, create task artifacts`
- Persist `active_command`, `phase_mode`, `current_stage`, the one
  `active_question`, `feedback_history`, and `prototype_rounds` inside
  `<change-dir>/brief.md` at each authorized same-checkpoint boundary through one
  prepared lease plus `artifact patch-batch`; older runtimes fall back to leased
  `artifact patch` calls. Never batch across unanswered user questions. Advance stages
  only after their observable exit condition is met:
  `context-intake -> discovery -> concept-brief -> prototype-authoring ->
  visual-review -> revision|approval -> contract-export -> registered`.
- When resuming after compaction, query `.specify/design/index.json` only when
  present or identified by registered metadata, then the
  active `<change-dir>/brief.md` and `<change-dir>/design-change.md` through
  `specify-runtime artifact show` before continuing.

## Allowed Writes

- `.specify/design/index.json` through `specify-runtime design change/iterate/register`
- `.specify/design/changes/<UD-ID>/design-change.md`
- `.specify/design/changes/<UD-ID>/brief.md`
- `.specify/design/changes/<UD-ID>/design-contract.json`
- `.specify/design/changes/<UD-ID>/references.md`
- `.specify/design/changes/<UD-ID>/options.md`
- `.specify/design/changes/<UD-ID>/previews/*`
- `.specify/design/changes/<UD-ID>/review.md`
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

1. Query `.specify/design/index.json` only when it exists or registered metadata
   is returned by scope discovery, and resume a nonterminal change for the
   same objective through targeted `specify-runtime artifact show` calls. Query
   only its exact `design-change.md`, brief, references, options, and review through
   the same owner. Never query or select an unregistered root design document.
2. For each exact affected surface, derive its stable path-like ID from confirmed
   source surfaces or registered metadata, then run
   `specify-runtime design resolve --scope <exact-surface> --format json` to discover
   active registered candidates. Resolution is discovery only: it never binds
   a consumer or chooses “latest.” A `composite: true` result means the broad
   surface crosses multiple active contracts. Current consumer bindings are
   singular, so split it into independently bound consumer units, each with one
   exact scope and one binding artifact, instead of choosing or merging a
   candidate for the whole surface. Never send the whole brief or a cross-platform
   prose sentence as scope. Missing registry/coverage means discovery absence;
   required approved Design still needs its approval and registration gates.
3. If no matching draft exists, allocate a stable `UD-*` ID. Run
   `specify-runtime design change` for a new bounded direction. For an approved
   source being refined, run `specify-runtime design iterate` so lineage and
   source bytes are exact; do not manually reconstruct its baseline digest or
   mutate the approved source.
4. Read `README.md`, project handbook files, existing UI surfaces, and existing
   design files. Use the command's shared Learning intake for project rules and
   reusable lessons. Determine the delivery origin before designing:
   - `design-first`: no planning-ready feature spec owns the request; after
     approval the next formal consumer is Specify;
   - `post-specify`: a planning-ready feature `spec-contract.json` already owns
     requirements, scope, and acceptance; record its exact consumer ref, path,
     SHA-256, and `return_target: plan` in `delivery_context`;
   - `standalone`: audit-only work with no immediate consumer.
   A late design overlay must not require a second requirements workflow pass when requirements stay
   unchanged. A genuine requirements, scope, or acceptance change exits this
   lane and returns to the requirements owner before design adoption.
5. **UI Evidence Analysis (when references or live UI exist):** collect sources
   into a surface/page map; extract candidate tokens, components, states, and
   responsive rules; enumerate pointer/mouse, keyboard/focus, touch, and
   command interactions plus empty/populated/partial/error/permission/offline
   data scenarios and stretch/overflow behavior; tag each claim with evidence level
   Design Evidence v1 (`measured` | `inferred` | `assumption`; alias
   `evidence-backed-inference`) with rationale when not measured and source or
   source_gap when inferred. Do not treat screenshot similarity as measured
   truth.
6. **Source Continuity (when reconstructing, migrating, adapting, or completing
   an interface from prior evidence):** treat screenshots, HTML/design exports,
   live source surfaces, source code/resources/tests, runnable source products,
   and business rules as complementary authorities rather than assuming one
   screenshot proves the product. Load the routed
   `specialist-source-grounded-reconstruction` reference and patch a structured
   `source_continuity` contract with
   `schema: spec-kit-ui-source-continuity-v1`, `applicability`, `mode`, `reason`,
   the complete `coverage.surface_ids` / `interaction_ids` / `component_ids`
   universe, and `authority_refs` into the brief and final
   `design_change.verification.source_continuity`. Discover
   deep surfaces and states; map each surface with one of `preserve`, `adapt`,
   `replace`, `merge`, `split`, or `retire`; trace every actionable control to
   an `action_bindings` row with `interaction_id`, `source_refs`,
   `user_promise`, `business_outcome`, `side_effects`, `final_state`, and
   `verification`; linked interaction/scenario rows own feedback and recovery.
   Record icons, images, fonts, and other resources in `asset_bindings` using
   the schema's semantic role, source refs, target strategy/ref, provenance,
   fallback, and placeholder policy. Every icon binding
   uses `placeholder_policy: forbid-character-substitution`; a glyph, emoji, or
   ASCII character is not a substitute asset. Keep unknown surfaces, actions,
   outcomes, states, assets, and evidence conflicts in `unresolved_gaps` with an
   owner and next discovery action. An applicable ready contract cannot hide a
   material gap by calling it retired. This command discovers and approves the
   continuity contract only; it does not implement the target or claim runtime
   parity.
7. Use project cognition to locate likely UI entry points, token/theme owners,
   reusable component owners, responsive/state patterns, visual or accessibility
   tests, and design assets; verify every selected route in live files before it
   becomes design evidence.
8. Resolve `style_authority` from live evidence before professional skill
   routing. Feature, component, and partial functional-page work inside an
   existing product uses `inherit-existing`, records exact live UI
   `source_refs`, protects `global-shell` and `shared-components`, permits no
   style-delta surfaces, and cannot select a style skill. Only explicit user
   authorization to visually overhaul one exact complete page may use
   `page-overhaul-authorized`; record that page as the sole allowed style-delta
   surface and the approval checkpoint as `authorization_source`. Adding or
   refactoring one function page does not authorize a new product-wide style.
   Use `greenfield` only when no governing live UI language exists.
9. Classify the experience separately by work type, surface type (`landing`,
   `product-workspace`, `hybrid`, or `existing-pattern-maintenance`), and one or
   more capability profiles. Read the deterministic catalog with
   `{{specify-subcmd:specify-runtime design profiles}}`; supported profiles are
   `web`, `mobile`, `desktop`, `cli`, `tui`, `content`, and `no-ui`. A hybrid
   product selects multiple visual profiles rather than collapsing them into a
   single project-type enum.
10. If and only if `no-ui` is supported by current repository evidence, record
   `design_system_status: not-applicable` with that evidence and exit this
   visual workflow. Do not generate a concept, image, HTML, approval, handoff,
   `ui-target`, or visual comparison, and never combine `no-ui` with a visual
   profile.
11. If references are supplied as URLs, screenshots, text notes, existing design files, or imported summaries, assign each an explicit intent: `exact`, `preserve-structure`, `inspiration`, `extract-tokens`, or `do-not-copy`.
12. When built-in presets help, read shipped files under
   `.specify/templates/design-library/` or `templates/design-library/`
   (including aesthetic seeds and `anti-slop-policy.md`) and treat them as
   inspiration only—never as approved product direction or a substitute for
   `design approve`.

## Design Question Loop

1. Use the scaffolded `<change-dir>/brief.md`, then fill only its affected
   frontmatter fields and named sections through
   leased `artifact patch` calls. The runtime expands the installed stable
   template; never read and reproduce that boilerplate in memory. Store
   confirmed decisions and unresolved design questions, not a conversation
   transcript.
2. Infer everything supported by the repository, supplied references, and
   prior confirmed answers before asking the user.
3. **Taste intake gate (create / substantive refine):** before single-concept
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
     subordinate to the exact applicable registered design change)
   - `reference_board_intents` when `input_strategy: synthesize`
     (`mood` | `layout` | `type` | `color-only`); references are evidence, not
     a license to copy protected brand or artwork. The approved baseline is
     evidence to preserve or supersede within its exact scope. It cannot
     authorize deviation from live style authority.
4. Use the professional reference package bundled with `sp-design`.
   Before medium-specific authoring, read
   `.specify/templates/ui-professional-skills/router.md` (source-tree fallback:
   `templates/ui-professional-skills/router.md`) and resolve
   `professional_skill_route`. Record `domain_skill_id`, `style_skill_id`,
   `specialist_skill_ids`, `matched_signals`, `loaded_refs`, the compact
   `mature_web_ui_resource_ids` shortlist, `web_ui_asset_inventory`, explainable
   `mature_web_ui_selection`, its deterministic `component_adoption_plan` and
   read-only official-resource refresh result, plus `smoothness_acceptance_ids`
   and performance budgets when Web UI
   applies; pass the actual project root to the deterministic router and load only the
   selected one domain, zero-or-one style, and zero-to-two specialist
   references. For Web component work, follow the router-triggered
   `web-component-selection.md`: reuse inspected live components first, then
   select one compatible mature primary system plus only justified headless or
   specialist support. Pass the resolved `style_authority` to the deterministic router.
   For `inherit-existing`, `style_skill_id` and style references must remain
   null/absent; domain and specialists may improve the UI only inside the live
   language. Never load the whole UI professional skill pack. If the router
   reports material ambiguity, ask its one high-impact question and do not
   author a visual round until answered. Read its
   `references/discovery-dialogue.md` and
   `references/visual-capability-routing.md`, then load exactly one relevant
   platform reference from `references/platform-web.md`,
   `references/platform-apple.md`, `references/platform-windows.md`, or
   `references/platform-android.md`. Read
   `references/image-generation-studio.md` for an
   image-primary round. Read `references/html-prototype-studio.md` plus
   `references/prototype-craft.md` for an HTML-primary round. Augment the chosen
   medium's prompt with the exact selected professional references; never reuse
   an image-generation prompt as an HTML-authoring prompt. Before presentation
   or revision read `references/critique-loop.md`.
5. State the current `design_read`, confidence, and the missing decision before
   asking. Ask one high-impact design question at a time when the answer can change
   visual hierarchy, density, component anatomy, motion, responsive
   adaptation, accessibility, reference fidelity, dial vectors, or the approval
   boundary. Make each question build on the user's latest answer and include a
   concrete recommendation or agent guess when one is justified. Do not ask for
   facts already present in the repository, references, or confirmed brief.
6. Do not advance past an unanswered question. If the user asks for context,
   examples, implications, or trade-offs, answer that clarification and re-ask
   the same decision more clearly; keep `active_question.status: open`.
7. Do not ask which production framework, CSS library, image model, or rendering
   stack to use merely to shape the review artifact. The selected visual medium
   is implementation-neutral. Ask about a technical constraint only when it changes the
   target platform or the visual/interaction result.
8. Before generating the current concept, confirm the product subject, audience, single
   user job, modules, locales, color modes, platform/viewports, real or
   representative content, required component/state coverage, meaningful
   motion moments, reduced-motion equivalent, references, taste intake fields,
   component interaction modes, data-state scenarios, resize/stretch behavior,
   and Must Preserve / May Adapt / Must Not boundaries.
9. Continue the question loop until those decisions are confirmed or recorded
   as bounded, visible assumptions. Do not manufacture more questions once the
   concept can be explained and evaluated without inventing product facts.
10. Record each confirmed choice as a stable design decision (`DS-<KIND>-NNN`)
   with its statement, source, status, affected surfaces, and verification
   method. The brief is the decision ledger; do not leave important choices
   trapped only in conversation prose.

## Redesign Protocol (refine / audit)

When live UI or an approved system already exists:

1. Detect mode: `preserve` modernizes without breaking brand. `overhaul` allows
   a new visual language only for an explicitly authorized exact complete page;
   it does not unlock the global shell, shared components, sibling pages, or a
   local feature surface. Without that authorization, use
   `style_authority.mode: inherit-existing` even when the page structure is
   substantially refactored.
2. Audit before mutate: brand tokens, IA, signature interactions, AI-slop
   patterns to retire, current dial reading of the live surface, and web SEO
   or analytics ID risks when applicable.
3. `audit` reports readiness and drift without changing approved truth.
   Promote to `refine` only when design truth must change, then open a new
   immutable change with `specify-runtime design iterate`; a new preview round
   inside the source workspace is only for an unapproved draft, never for
   changing a registered contract.

## Capability-Aware Single-Concept Preview Loop

Each immutable round contains one current concept (`direction-main`). The Agent
and user improve that single concept in the same direction through dialogue; never generate three
unrelated visual systems for one review round.

- At every entry and resume, inspect the live capability surface for three
  independent values: `image_generation`, `image_inspection`, and
  `image_editing`. Do not hard-code capability from an Agent, model, CLI, or
  integration name. Read
  `references/visual-capability-routing.md` and patch the
  probe evidence plus route into `brief.md`.
- Route `image_generation: available` to `image-primary`, regardless of whether
  inspection is available. Route `image_generation: unavailable` to
  `html-primary`. Inspection available means `inspection_owner:
  agent-and-user`; unavailable means `inspection_owner: user` and the Agent
  makes no visual-quality claim. Editing availability changes targeted edit
  versus full regeneration only.
- For every route, scaffold and complete the compact source with
  `{{specify-subcmd:specify-runtime design preview-manifest --profiles <comma-separated-profile-ids> --out <change-dir>/previews/round-NN.manifest.json}}`.
  Configure representative content, capability profiles/specimens, the one
  direction, boundaries, tokens, decisions, owner mappings, modes, targets,
  and complete `DS-*` / `DH-*` coverage. Patch `visual_collaboration` with the
  exact live probe before authoring the visual; ready lint rejects a missing,
  contradictory, or medium-mismatched route.
- **Image-primary lane:** read
  `references/image-generation-studio.md`. Use the design CLI to persist the exact
  professional generate/edit request for the numbered round, then generate one
  composite image board for the current concept. Image prompts own
  subject, context, style, composition, aspect ratio, exact text, reference
  roles, and edit invariants; they are not HTML/DOM/CSS prompts. When image
  inspection is available, open the actual saved pixels, critique, repair, and
  re-inspect. Without inspection, show the image, make no visual-quality claim,
  and revise from the user's observations.
- **HTML-primary lane:** read `references/html-prototype-studio.md`,
  `references/prototype-craft.md`, and selected platform guidance. Render
  `{{specify-subcmd:specify-runtime design preview --manifest <change-dir>/previews/round-NN.manifest.json --out <change-dir>/previews/round-NN.html}}`,
  replace the seed with one complete project-specific concept, set
  `data-prototype-status="authored"`, and preserve the stable direction ID,
  hash routing, embedded manifest, and inspectable `data-ui-*` hooks. Run
  `{{specify-subcmd:specify-runtime design preview-lint <change-dir>/previews/round-NN.html --level ready}}`.
  When inspection is available, inspect real browser captures at every target,
  repair, and recapture. Without it, provide the stable HTML deep link and make
  no visual-quality claim.
- Present the exact artifact, medium, thesis, signature, preserved decisions,
  intentional risk, and known trade-offs. Ask what feels right and what remains
  wrong. Do not ask the user to choose a hidden or prose-only alternative.
- If the user is not satisfied, classify feedback as preserve/change/question/
  out-of-scope, patch `feedback_history` and affected decisions, and revise the
  same direction in a new immutable round. Do not overwrite a reviewed round,
  restart from an unrelated aesthetic, or reinterpret criticism as approval.
- Do not advance past an unanswered question during feedback. A request for
  explanation keeps that feedback decision open.
- Only explicit approval of the named reviewed round is approval. For HTML,
  freeze with
  `{{specify-subcmd:specify-runtime design approve <change-dir>/previews/round-NN.html --direction direction-main --format json}}`.
  For images, freeze the image, manifest, and exact generation prompt together:
  `{{specify-subcmd:specify-runtime design approve <change-dir>/previews/round-NN.png --direction direction-main --manifest <change-dir>/previews/round-NN.manifest.json --prompt <change-dir>/previews/round-NN.prompt.md --image-inspection <available|unavailable> --image-editing <available|unavailable> --format json}}`.
  Record `approved_visual_ref` with the actual extension and `#direction-main`,
  plus returned preview/image, manifest, prompt (image lane), and handoff
  SHA-256 values, handoff ref, review round, exact `DS-*` IDs, exact `DH-*`
  IDs, profile IDs, and specimen IDs. Later revisions require a new immutable
  round and renewed approval; edited artifacts or stale/missing sidecars are
  invalid.

## HTML Preview Technology And Content Contract

- The installed `design-preview-template.html` is a universal review carrier
  with a baseline specimen, not a claim that every product uses the same Web
  controls, a whole-project mock application, or production source. Keep the
  review shell stable while the authored manifest stays project-specific; the
  platform-adaptive specimen contract owns which surfaces and states apply.
- Use modern native web capabilities deliberately: semantic HTML, CSS custom
  properties, cascade layers, fluid `clamp()` scales, container queries,
  progressive view transitions, URL-addressable concept/state controls, and
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
  owns one feature's concrete composition. The change-level design preview
  owns visual, component, state, density, and motion decisions only for its
  declared `UD-*` scope.

## Synthesis Rules

- Complete the change-local `design-change.md` from the approved round, then lint,
  export, and register that exact file. Never rewrite another approved change.
- Present the one image-primary or HTML-primary current concept from the active
  preview round.
  Discuss alternatives in text only when they clarify a decision; render a new
  immutable round when feedback changes the concept.
- Before proposing them, name the product subject, audience, and single user job.
- The concept must state a visual thesis, content thesis, interaction thesis,
  signature element, platform fit, state strategy, safe system choices, and any
  deliberate creative risk with its gain and cost.
- Render the concept through the selected visual medium and ask the user to
  approve the reviewed round before running `specify-runtime design export` for `design-change.md`; a
  prose label, mood adjective, or unseen file is not approval.
- Ask the user for explicit approval of the round; approval refers to its inspectable visual
  artifact and recorded tradeoffs, not only its name.
- Preserve existing project rules unless the user approves a design-system change that supersedes them.
- Do not copy external brand names, protected visual identity, proprietary token names, or third-party file text into the final design system.
- Normalize the approved direction into `spec-kit-ui-design-change-v1` YAML
  front matter plus readable Markdown guidance.
- A successor records `relationships.iteration_of`, the matching source in
  `relationships.supersedes`, and the exact source digest in index
  `basis_sha256`. Registration subtracts only intersecting scopes from the
  source and records them as `superseded_scopes`; the parent remains active for
  every uncovered scope and is fully `superseded` only when all of its roots
  are covered.
- Set `design_change.status: approved` and record
  `design_change.approval.status`, the selected direction, and concrete product
  or repository `source_refs`, plus `approval.visual_refs`, review round,
  visual/manifest/handoff SHA-256 values, conditional image-prompt digest, immutable handoff ref, approved
  decision IDs, and approved handoff contract IDs. Record
  `product_context`, `direction_contract`, color modes, responsive/content
  contracts, decisions, and verification matrices. When source continuity
  applies, preserve its exact authority refs, surface/action dispositions,
  `business_outcome` and `final_state` promises, `asset_bindings`, and
  `unresolved_gaps`; never collapse them into a screenshot-fidelity note.
  Remove unresolved
  placeholders and generic starter choices that are not justified by those
  sources.

## Output Contract

The workflow output is `.specify/design/changes/<UD-ID>/design-change.md` plus its
confirmed brief, immutable image-primary or HTML-primary visual rounds, review artifacts,
`design-contract.json`, and selected-direction handoff sidecar. The index stores
metadata and exact consumer bindings; it never contains design prose.
Never write `<change-dir>/design-change.md` directly; patch only its named frontmatter
fields and sections through fresh leased `specify-runtime artifact patch` calls.

## Required design-change.md Shape

The change-local `design-change.md` must contain:

- YAML front matter with `design_change.schema: spec-kit-ui-design-change-v1`
- stable ID, title, change type, scopes, baseline refs, relationships, and
  Must Preserve / May Adapt / Must Not boundaries
- exact `style_authority` with mode, scope level, inspected live source refs,
  protected surfaces, allowed style-delta surfaces, and authorization source
- `relationships.iteration_of` for a successor (null otherwise), with the same
  source in `supersedes` and its exact digest-pinned baseline
- `design_change.status: approved` plus approval direction, source refs,
  immutable visual and handoff references, review round,
  visual/manifest/handoff SHA-256 values, conditional image-prompt provenance, approved decision IDs, and approved
  handoff contract IDs
- product subject, audience, single job, and approved visual reference
- visual, content, and interaction theses; one signature element; safe system
  choices; and deliberate creative risks
- `design_change.name`
- `design_change.version`
- `design_change.platforms`
- non-empty token categories for `color`, `spacing`, `radius`, `typography`, and
  `motion`, plus applicable elevation, sizing, and layout tokens
- color-mode contracts, including required accessibility modes
- component required states, token references, and design decision references
- responsive breakpoints/adaptations and real-content/imagery rules
- applicable structured `source_continuity`: exact bidirectional coverage IDs,
  authority refs; surface bindings
  with `preserve`/`adapt`/`replace`/`merge`/`split`/`retire` disposition;
  action bindings through `business_outcome` and `final_state`;
  `asset_bindings` with provenance, target refs, accessibility fallback, and
  `forbid-character-substitution`; and ready-safe `unresolved_gaps`
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
   `{{specify-subcmd:specify-runtime design preview-lint <change-dir>/previews/round-NN.<html|png|jpg|jpeg|webp> --level ready}}`,
   then run `{{specify-subcmd:specify-runtime design lint <change-dir>/design-change.md --level ready}}` when the CLI helpers
   are available. Export the same approved contract with
   `{{specify-subcmd:specify-runtime design export <change-dir>/design-change.md --format json --out <change-dir>/design-contract.json}}`,
   then pin it with
   `{{specify-subcmd:specify-runtime design register <change-dir>/design-change.md --format json}}`
   so implementation consumes deterministic data rather than reconstructing
   YAML prose. For a successor, immediately run
   `{{specify-subcmd:specify-runtime design diff <SOURCE-UD-ID> <UD-ID> --format json}}`
   and record the scope, stable `DS-*` decision, `DH-*` handoff-contract, and
   changed-section delta in review before recommending adoption. For every
   already bound consumer, instruct its owning workflow to run read-only
   `specify-runtime design impact ... --expected-change <CURRENT-UD-ID|none>`
   before patching and to present `preserved_bindings`,
   `invalidated_bindings`, and `reconcile_from`.
2. If `<change-dir>/review.md` is absent, create its fixed shape with
   `specify-runtime artifact scaffold --kind design-review --path <change-dir>/review.md`.
   Otherwise query it through `artifact show`. Patch only these named semantic
   sections through one same-checkpoint `artifact patch-batch`; older runtimes
   fall back to a fresh `artifact patch` lease per section. Never submit or reconstruct the
   whole review document:
   - selected task type and input strategy
   - inputs read
   - design question decisions
   - preview round and validation result
   - approved direction
   - exact `approved_visual_ref`
   - visual/manifest/handoff SHA-256 values, conditional image-prompt provenance, and approval/handoff sidecars
   - approved design decision IDs
   - approved handoff contract IDs
   - requested revisions from rejected rounds
   - platforms covered
   - applicable `source_continuity`, source-evidence coverage, unresolved-gap
     disposition, and the source-target real-entrypoint scenarios that
     downstream Quick/Implement/Review must execute
   - design-system risks
   - lint result
   - recommended next workflow
3. Ask the user to review the written design before downstream workflows consume it as locked input.

## Closeout

Read `references/consumer-contract.md`, then close with the design-change
status, changed files, lint/register result, pinned approval identity, and exactly one
recommended next command. Do not bypass explicit feature or Quick adoption of a
new approval.

- For `delivery_context.origin: design-first`, recommend Specify. Specify owns
  requirements and binds the approved Design before Plan.
- For `delivery_context.origin: post-specify`, preserve the source spec bytes.
  Run `specify-runtime design impact <feature-ref> --change <UD-ID> --scope
  <exact-surface> --mode formal-post-specify --expected-change
  <CURRENT-UD-ID|none>`, then adopt with the same mode using the unchanged source
  `spec-contract.json` path and SHA-256. Verify the receipt read-only with
  `specify-runtime design adoption <feature-ref> --scope <exact-surface>
  --binding-ref <source-spec-ref> --binding-sha256 <source-spec-sha256>
  --expected-change <UD-ID>`. The next command is Plan. The normal route is
  `specify -> design -> plan` and must not require a second Specify.
- If Design uncovered a real requirements change, do not use
  `formal-post-specify`; return the semantic delta to Specify, the requirements
  owner, then resume from the newly bound contract.

## Guardrails

- Do not edit source code, tests, CSS/theme implementation files, UI components, feature specs, plan artifacts, or task artifacts from this command.
- Inline HTML/CSS and bounded review-only JavaScript inside
  `.specify/design/changes/<UD-ID>/previews/*.html` are design artifacts allowed by this
  workflow; they are not application implementation.
- Never hand-edit an approved preview or its sidecar. Generate a new numbered
  candidate round, obtain approval, and let `design approve` freeze it.
- Do not clone protected brands or copy third-party design files into `design-change.md`; synthesize project-owned design principles and tokens.
- Do not let downstream workflows treat an unaudited, unregistered, or
  contradictory change as locked input. A new approval must never silently
  retarget an existing Feature or Quick workspace.
- Do not treat visual resemblance, a present handler, or a compiled target as
  source continuity. Design records the source-target verification contract;
  Quick/Implement/Review must exercise the real entrypoints and prove each
  mapped `business_outcome` and `final_state` after implementation.

## Professional UI Contract Continuity

For substantive UI, approve complete `interaction_matrix`, `editing_matrix`,
`data_state_matrix`, `accessibility_matrix`, `navigation_matrix`,
`content_matrix`, `motion_contract`, and `usability_validation` values under
`design_change.verification`, plus the component governance fields. Bind
`source_continuity` when prior visual, structural, source-code, runtime, or
business evidence governs reconstruction: preserve `asset_bindings`, block
unowned `unresolved_gaps`, and enforce `forbid-character-substitution` for icon
and image mappings. Bind routed
the exact nested adoption row into every affected `component_contracts` row,
preserve each `surface_catalog[].entrypoint_id` as the exact official
real-entrypoint binding,
and bind `smoothness_acceptance_ids` plus performance budgets into the applicable interaction, motion, and
`usability_validation` rows without adding another
evidence kind. Compare risk-based or pairwise scenarios, never an unbounded Cartesian product, and do
not let automated tests or screenshots stand in for required target-user review.
