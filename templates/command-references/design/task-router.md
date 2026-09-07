Trigger: at every `sp-design` entry or resume, before asking design questions, selecting a mode, or mutating a design artifact.

Purpose: route one public design skill from the user's natural-language prompt and current design state without exposing user-selected subcommands.

Preserved Contract: `sp-design` remains the single public entry point; routing separates contract action, surface posture, and reference-input strategy, resumes active work before reclassification, and hands domain-external work to its owning workflow.

## Single Public Entry Point

- Keep one public skill or command named `sp-design`. Infer the route from the
  user's prompt, `.specify/design/index.json`, matching change workspaces,
  live UI, supplied references, and the
  originally blocked workflow.
- Do not register or expose `sp-design:create`, `sp-design:refine`,
  `sp-design:audit`, or equivalent colon-namespaced mode skills. Do not require
  the user to know an internal mode name.
- Persist the compact route as:

```text
contract_action: create | refine | audit
surface_posture: greenfield | inherit-existing | page-overhaul-authorized
input_strategy: context | synthesize
route_reason: <one evidence-based sentence>
```

After `specify-runtime design change` or `specify-runtime design iterate`
scaffolds the workspace, use
`specify-runtime artifact patch` to store the canonical route in
`.specify/design/changes/<UD-ID>/brief.md`. If the derived design
state exposes a selected-mode field, treat it only as a compatibility
projection of `contract_action`; do not invent a second writable workflow-state file.
Use the same owner CLI to repeat the route in review when it explains closeout.

`contract_action` describes the `UD-*` artifact lifecycle, not permission to
redraw a product. `surface_posture` describes visual authority and must exactly
match `style_authority.mode`. Creating a missing design contract for a live
product is therefore `contract_action: create` plus
`surface_posture: inherit-existing`, never a greenfield page.

## Routing Dimensions

- `create`: allocate a new `UD-*` workspace for a bounded greenfield or
  extension change that has no matching nonterminal workspace.
- `refine`: continue an unapproved draft. When approved truth changes, create
  its digest-pinned successor with `specify-runtime design iterate`; never
  mutate the approved change or manually reconstruct its lineage.
- `audit`: inspect one declared scope, change contract, provenance, live
  adoption, or drift without changing approved design truth.
- `context`: derive direction from confirmed product context and verified live
  project evidence.
- `synthesize`: use supplied screenshots, URLs, design exports, notes, or other
  references with explicit reference intents. Synthesize is an input strategy,
  not a terminal task type; combine it with `create` or `refine`.

## Direction Checkpoint Flow

Every create/refine route uses the same platform-neutral staged flow:
`intake -> concept-calibration -> direction-confirmed -> contract-completion ->
formal-approval -> register`. This sequence is independent of Web, desktop,
mobile, CLI, TUI, or content profile selection; platform references only add
profile-specific obligations after the shared checkpoint names are pinned.

Stage 1 is `intake -> concept-calibration -> direction-confirmed`. It keeps one
current concept and a stage 1 minimum viable contract: exact scope, selected
profiles, subject, audience, single job, taste read/dials, primary layout or
signature element, layout-changing critical state coverage, contrast, focus,
reduced-motion feasibility, and one stress target. It may offer 2-3 textual
choices to resolve direction ambiguity, but do not generate three full boards
or ask the user to pick among complete visual alternatives. The Agent must not
auto-add an unselected profile because a later matrix would be convenient.

Before presenting a direction as ready to complete, call the advertised
`preview-lint concept` capability through `specify-runtime design` using exact
runtime names from preflight. Concept lint must create the current byte-bound
concept receipt; when inspection is available, pass its protected-surface
review through `--inspection-json`. Only after that receipt exists may the
workflow ask for explicit direction confirmation, and only after that user
confirmation may it call `direction-confirm`. A lint pass alone must not create
the direction sidecar. The resulting direction-confirmed
sidecar is non-consumable: it is not approval, not a register event, and not
input that Plan, Tasks, Implement, Quick, or Review may adopt. It only proves
that the single current concept is coherent enough to finish its contract.

Stage 2 is `contract-completion -> formal-approval -> register`. Full source
continuity denominators, mature Web adoption rows, complete scenario,
interaction, editing, data-state, accessibility, navigation, content, motion,
and `DH-*` handoff matrices are deferred to contract-completion after
direction-confirmed. Contract completion must start from the next numbered
round because a round with a `.direction.json` sidecar can never be formally
approved. The next round inherits the confirmed visual direction by default; if
matrix work exposes a needed visual change, revise that new round and confirm
or approve it there. Only explicit approve/register truth may feed formal or
direct delivery.

## Resume Before Reclassification

1. Query `.specify/design/index.json` and matching
   `.specify/design/changes/<UD-ID>/brief.md` / `design-change.md` through
   `artifact show` first when they exist.
2. If they record nonterminal work for the same objective, resume before
   reclassification at the brief's exact `contract_action`, `surface_posture`,
   and `input_strategy` plus the derived state's current stage.
3. Treat approval, feedback, and continuation messages as lifecycle events for
   that active task, not as new audit/create/refine prompts.
4. Reclassify only when the user explicitly changes the objective or live
   evidence proves that the stored route cannot complete safely. Record the
   material route delta before continuing.

## Scope Resolution

Derive each stable path-like surface ID from confirmed source or registered
metadata; split surfaces and never pass the whole brief or prose as `--scope`.
Missing registry/coverage is legitimate discovery absence: do not blindly
artifact-show a missing index or replace required approved Design with a risk
note. Preserve existing approval, registration, and late-design adoption gates.

Run `specify-runtime design resolve --scope <exact-surface> --format json` when
registered design coverage shapes routing. This is discovery only; it neither
selects “latest” nor adopts a result. If it returns `composite: true`, split the
broad scope into independently bound consumer units before downstream
adoption. The current binding artifacts are singular: each unit owns one exact
scope and one binding artifact. Do not collapse parent and successor candidates
into one invented contract.

## Style Authority Routing

Resolve `style_authority` before selecting the UI Professional Skill route.
Live product UI is authoritative for feature, component, and partial functional
page work: use `inherit-existing`, cite exact token/theme/component/surface
sources, protect `global-shell` and `shared-components`, allow no style delta,
and keep `style_skill_id: null`. Domain and specialist advice may refine the
bounded UI without changing its visual language.

Route to `page-overhaul-authorized` only after the user explicitly approves a
visual-language change for one exact complete page. Bind the authorization and
allowed delta to that page; the surrounding shell and shared components remain
protected. A functional page refactor or new feature page defaults to
`inherit-existing`. `greenfield` requires repository evidence that no live UI
language governs the new surface.

## Decision Table

| Current truth and prompt | Route |
| --- | --- |
| No matching nonterminal change; establish a bounded design | `create/context` |
| No matching change; references shape the bounded design | `create/synthesize` |
| Approved change/live scope must intentionally change | new `refine/context` successor via `design iterate` |
| References shape an intentional replacement | new `refine/synthesize` successor via `design iterate` |
| Check readiness, coverage, provenance, consistency, or drift only | `audit/context` |
| Current evidence proves `no-ui` | record `not-applicable` and exit the visual lane |

For ambiguity between `create` and `refine`, the matching scope and approval
status decide. Approved truth always means a new change ID. For
ambiguity between `audit` and mutation, start with `audit`; promote to
`create`/`refine` only when the evidence proves design truth must change.

## Domain Boundary Routing

- Route production framework, database, dependency, deployment, or
  implementation architecture decisions to `sp-plan`; durable non-negotiable
  engineering principles belong to `sp-constitution`.
- Route feature behavior, scope, and acceptance truth to `sp-specify`, or to
  `sp-quick` when the user chooses direct delivery and the outcome is already
  confirmable. When a planning-ready source spec already owns unchanged
  requirements, persist `delivery_context.origin: post-specify`; after Design
  approval return directly to Plan through `formal-post-specify`, not through a
  second Specify. Only a real requirements, scope, or acceptance change reopens
  Specify.
- Route implementation drift against correct approved design to `sp-review` or
  the active implementation workflow. Do not rewrite design truth to excuse a
  code defect.

## Taste Intake And Synthesize Intents

- Visual `create` and substantive `refine` require durable taste intake in the
  design-brief artifact (scaffold/patch via `specify-runtime artifact` only)
  before single-concept preview work: `design_read`, dials with inference
  reason, `aesthetic_family`, `foundation_strategy`, `redesign_mode` when live
  UI exists, and `anti_slop_locks` from the surface-aware policy.
- `input_strategy: synthesize` may attach reference-board intents
  (`mood`, `layout`, `type`, `color-only`). Keep original inspectable assets;
  prose alone is not a fidelity source. Third-party references are evidence,
  not a license to copy protected brand, artwork, or trade dress.
- Do not register or expose colon-namespaced design skills (including create,
  refine, audit, or taste variants). Taste is an intake layer inside this
  single public entry.
