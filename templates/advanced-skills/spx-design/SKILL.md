---
name: spx-design
description: Prompt-routed UI design-change workflow for advanced coding models that creates, refines, or audits one bounded UD-* contract, optionally synthesizes references, and hands registered truth to formal or direct delivery consumers.
---

# SPX Design

Read `references/project-learning.md` and apply its consume-capture policy.
Read `references/project-cognition.md`, using cognition intent `plan`, and
`references/task-router.md`, then `references/design-contract.md`. Read
`references/ui-quality-gate.md`. For visual create/refine, read
`references/studio-loop.md` and the selected sections of
`references/platform-guidance.md`, probe the live visual capabilities, then
read exactly one of `references/image-round.md` or `references/html-round.md`.
Read `references/consumer-contract.md` before
closeout or approval adoption. Read
`references/consequence-gate.md` when
shared component state or generated consumers change.

Query `.specify/design/index.json` through `specify-runtime artifact show`,
resume a matching nonterminal `UD-*` workspace, then inspect its exact contract,
relevant live UI entry points, existing tokens/components, accessibility rules,
and supplied references. An existing root `DESIGN.md` is a read-only legacy
baseline, never an implicit latest contract. Distinguish
observed product language from new design decisions; do not invent a parallel
system when an established one can be extended.

Determine `delivery_context` before authoring: `design-first` when no
planning-ready feature spec exists, `post-specify` when an exact planning-ready
feature spec contract already owns requirements/scope/acceptance, or
`standalone` for audit-only work. Persist the post-Specify feature consumer,
source-spec ref/SHA-256, and `return_target: plan`. Unchanged post-Specify work
returns directly to Plan; only a genuine requirements change returns to
Specify, the requirements owner.

Resolve `style_authority` from live UI before professional routing. Feature,
component, and partial functional-page work uses `inherit-existing`, cites
exact live token/theme/component/surface refs, protects `global-shell` and
`shared-components`, allows no style delta, and keeps `style_skill_id: null`.
Only explicit user authorization for one exact complete-page visual overhaul
may use `page-overhaul-authorized`; bind the allowed delta and authorization to
that page while retaining shell/shared-component guards. A functional page
refactor or feature addition is not style-change authority. Use `greenfield`
only when no live visual language governs the surface.

For every exact affected surface, use
`specify-runtime design resolve --scope <surface> --format json` to discover
active registered candidates. Resolution is discovery only and never binds a
consumer. Current binding artifacts are singular, so split `composite: true`
results into independently bound consumer units, each with one exact scope and
one binding artifact, rather than selecting or merging one broad contract. When no matching draft
exists, initialize a new bounded direction through
`specify-runtime design change <UD-ID> --title <title> --type <greenfield|preserve|overhaul|extension> --scope <surface> --profiles <profiles>`.
When approved truth is refined, create its exact successor through
`specify-runtime design iterate <SOURCE-UD-ID> <SUCCESSOR-UD-ID> --title <title> --type <preserve|overhaul|extension> [--scope <surface>]... --format json`;
this pins `iteration_of`, `basis_sha256`, the source baseline digest, and
`supersedes` without mutating registered bytes. Every requested successor scope
must still be active on the source; iterate from the active successor or a
remaining source scope after partial supersession.
Set `<change-dir>` to `.specify/design/changes/<UD-ID>`. Resume it through
`artifact show` after interruption or compaction. Persist `active_command: sp-design`,
`phase_mode: design-only`, `current_stage`, the one `active_question`,
`feedback_history`, `prototype_rounds`, approval state, lint result, next action,
and next command. Use
`specify-runtime artifact patch` to store the canonical
`task_type: create | refine | audit`, `input_strategy: context | synthesize`,
and route reason in the design brief; treat any selected mode in derived state
only as a compatibility projection.
Resume the stored route before reclassification. The `allowed_writes` are only
`.specify/design/index.json` through `design change/iterate/register`,
`.specify/design/changes/<UD-ID>/DESIGN.md`, `<change-dir>/brief.md`,
`<change-dir>/previews/*`, `<change-dir>/references.md`,
`<change-dir>/options.md`,
`.specify/design/changes/<UD-ID>/design-contract.json`,
`<change-dir>/review.md`, and stable design rules in
`.specify/memory/project-rules.md` when they truly become project defaults.

Use the scaffolded `<change-dir>/brief.md`, then refine only affected
frontmatter fields and named sections through leased
`artifact patch` calls. The runtime expands the installed template; never read
and reproduce its stable boilerplate in memory. Infer repository evidence first, then ask one
high-impact design question at a time when the answer can change hierarchy,
density, component anatomy, motion, responsive/accessibility behavior,
reference fidelity, dial vectors, or approval scope. State the current design
read, confidence, and missing decision; include a recommendation or current
guess. Do not ask for facts already present. Do not advance past an unanswered
question: if the user asks for context or trade-offs, answer and re-ask the same
decision. Do not ask for a production framework
merely to shape a framework-neutral preview. For visual create and substantive
refine, patch taste intake into the brief before single-concept preview work:
one-line `design_read`, dials (variance/motion/density) with inference reason,
`aesthetic_family`, `foundation_strategy`, `redesign_mode` when live UI exists,
surface-aware `anti_slop_locks`, and synthesize `reference_board_intents`
(`mood`/`layout`/`type`/`color-only`) when references shape the board.
Read `.specify/templates/ui-professional-skills/router.md`, resolve and persist
`professional_skill_route` with `domain_skill_id`, `style_skill_id`,
`specialist_skill_ids`, `matched_signals`, `loaded_refs`, and
`mature_web_ui_resource_ids`, `web_ui_asset_inventory`,
`mature_web_ui_selection`, and `smoothness_acceptance_ids` when Web UI applies.
Pass the actual project root to the deterministic router, then load only the selected
one domain, zero-or-one style, and zero-to-two specialist references. Web
component work also reads the router-triggered `web-component-selection.md`:
reuse inspected live components first, select at most one compatible mature
primary system, and add only exact headless or specialist gaps. Load official
Agent/MCP/LLM material only for selected candidates.
Pass the resolved `style_authority` to the router; `inherit-existing` suppresses
all style refs while retaining relevant domain/specialist expertise.
Do not load the entire UI professional skill catalog. A material routing
ambiguity owns the same one-high-impact-question stop; resume the pinned route
for an active immutable round. The selected references augment the eventual
image-primary or html-primary prompt separately and never replace approved
references or registered design truth.
Confirm subject, audience, single
job, modules, locales, modes, platforms/viewports, comparison content,
component/state coverage, meaningful motion and `prefers-reduced-motion`, and
Must Preserve / May Adapt / Must Not boundaries. Record confirmed choices as
stable `DS-<KIND>-NNN` decisions with source, status, affected surfaces, and
verification; the brief is the decision ledger, not a chat transcript.

Read `{{specify-subcmd:specify-runtime design profiles}}` and select one or more
independent capability profiles: `web`, `mobile`, `desktop`, `cli`, `tui`, or
`content`. Hybrid products keep multiple profiles. If current repository
evidence proves `no-ui`, record `design_system_status: not-applicable` with that
evidence and exit without preview, approval, handoff, `ui-target`, or visual
comparison; never combine `no-ui` with a visual profile.

Before visual authoring, inspect the current session's live capability surface
and persist independent `image_generation`, `image_inspection`, and
`image_editing` values plus evidence in the brief. Do not hard-code capability
from an Agent, model, CLI, or integration. Generation available selects
`image-primary`; generation unavailable selects `html-primary`. Inspection
available sets `inspection_owner: agent-and-user`; unavailable sets
`inspection_owner: user` and forbids a visual-quality claim. Editing availability
selects targeted image edit versus full regeneration, not a different concept.

Every `refine` that changes approved design truth must use `design iterate` to
create a new `UD-*` workspace as a digest-pinned successor; an export, hand-authored lineage, or
in-place mutation of an approved change is not a substitute. For `create` and
those `refine` routes, author `<change-dir>/previews/round-NN.manifest.json` from
`{{specify-subcmd:specify-runtime design preview-manifest --profiles <comma-separated-profile-ids> --out <change-dir>/previews/round-NN.manifest.json}}`,
then configure its one current concept, boundaries, modes, decisions, and full
`DH-*` handoff contract. Patch `visual_collaboration` with the exact live
generation/inspection/editing probe; ready lint rejects missing,
contradictory, or medium-mismatched capability truth.

For `image-primary`, read `references/image-round.md`, use the design CLI to
persist the exact generate/edit prompt for the numbered round, and generate one
composite image board for that round. Image prompts own subject, context, style,
composition, aspect ratio, exact text, input-image roles, and invariants; they
are not HTML authoring prompts. Inspect actual saved pixels when possible; when
inspection is unavailable, show the image without a visual-quality claim and
revise from user observations. Freeze explicit approval with `specify-runtime design approve
<round-image> --direction direction-main --manifest <manifest> --prompt
<prompt> --image-inspection <available|unavailable> --image-editing
<available|unavailable> --format json`.

For `html-primary`, read `references/html-round.md`, render
`{{specify-subcmd:specify-runtime design preview --manifest <change-dir>/previews/round-NN.manifest.json --out <change-dir>/previews/round-NN.html}}`,
replace the seed with one complete project-specific semantic HTML/DOM/CSS
concept, set `data-prototype-status="authored"`, and preserve the stable route,
embedded manifest, and inspectable hooks. Run ready lint and inspect real
browser captures when possible; otherwise provide the deep link without a
visual-quality claim. Freeze explicit approval with
`{{specify-subcmd:specify-runtime design approve <change-dir>/previews/round-NN.html --direction direction-main --format json}}`.

Present the exact current artifact and revise the same direction in a new
immutable round from preserve/change/question feedback. Do not overwrite prior
rounds, branch into three unrelated concepts, or treat criticism or vague
praise as approval. Record `approved_visual_ref` with the actual artifact
extension plus returned preview/image, manifest, prompt when applicable, and
handoff SHA-256 values, sidecars, exact decision and handoff contract IDs,
capability profile IDs, and specimen IDs in the brief, review, and `DESIGN.md`.
An edited approved artifact or missing/stale sidecar is invalid.
Refinement that does not change approved truth needs no ceremonial
re-selection; any changed truth requires a new inspected round and explicit approval.

The visible handoff is part of what the user approves. Ready lint must reject
unknown/no-UI profiles, missing required capabilities/specimen kinds,
direction/specimen drift, or any required state, target, specimen, or `DS-*`
decision not covered by a `DH-*` visual acceptance row. `design approve`
projects the selected direction and complete capability model
into the immutable handoff; never manually rewrite that artifact or replace it
with a prose summary.

Complete `<change-dir>/DESIGN.md` from the approved round. Use
`assets/design-change.md` as content guidance while the installed
`design-change-template.md` owns the schema. Record only
decisions that constrain downstream UI work: principles, foundations, tokens,
component and interaction rules, responsive/accessibility behavior, reference
fidelity, and required visual evidence. Make exceptions explicit and
verifiable.

Set `design_change.status: approved`, record the selected direction and
product/repository source refs plus `approval.visual_refs`, review round,
preview/manifest/handoff SHA-256 values, immutable handoff ref, decision IDs,
and handoff contract IDs. Replace every asset
placeholder, run `{{specify-subcmd:specify-runtime design lint <change-dir>/DESIGN.md --level ready}}`, then export the
deterministic implementation contract with
`{{specify-subcmd:specify-runtime design export <change-dir>/DESIGN.md --format json --out .specify/design/changes/<UD-ID>/design-contract.json}}`.
Finally pin the exact contract and enforce overlap/supersedes with
`{{specify-subcmd:specify-runtime design register <change-dir>/DESIGN.md --format json}}`.
Registration subtracts only intersecting successor scopes, records them as
`superseded_scopes`, and leaves the parent active elsewhere. For a successor,
run
`{{specify-subcmd:specify-runtime design diff <SOURCE-UD-ID> <UD-ID> --format json}}`
and record the lineage, scope, stable `DS-*`, `DH-*`, and changed-section delta
in review before adoption. For an already bound consumer, its owning workflow
must also run read-only `specify-runtime design impact ... --expected-change
<CURRENT-UD-ID|none>` before patching, present `preserved_bindings`,
`invalidated_bindings`, and `reconcile_from`, then reconcile only after the
compare-and-swap adoption receipt succeeds.
Do not hand off a structurally valid but generic or unapproved seed.

If `<change-dir>/review.md` is absent, create its fixed shape with
`specify-runtime artifact scaffold --kind design-review --path <change-dir>/review.md`;
otherwise query it through `artifact show`. Patch only its named sections with
the mode, inputs, approved direction, visual and handoff references, hashes,
decision and handoff contract IDs, covered platforms, risks, lint/export
results, and one recommended next workflow, using a fresh lease per section.
Never submit or reconstruct the whole review document. Ask the user to review the CLI-exported `DESIGN.md` before
recording the final design handoff; approval of an earlier
direction artifact does not silently approve a drifted final contract.

This workflow owns one UI design-change contract, not production implementation.
Do not edit application source, tests, or generated component code. Preserve
useful existing decisions and validate that referenced tokens/components exist
or are clearly marked planned. Apply `references/consumer-contract.md`: route
design-first formal adoption through `$spx-specify`, post-Specify adoption
through `formal-post-specify` directly to `$spx-plan`, and direct delivery
through `$spx-quick`. A post-Specify route must not require a second Specify
unless Design uncovered a requirements change. Resume an originally blocked
workflow only after an audit pass proves its existing binding remains exact. A
new approval never silently retargets active delivery. The change-level preview owns decisions declared for its scope; the later
feature-level `ui-target.html` owns one feature's concrete composition. This
invocation authorizes only this workflow stage; do not invoke another workflow
in this run.
