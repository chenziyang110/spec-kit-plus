Trigger: at every `sp-design` entry or resume, before asking design questions, selecting a mode, or mutating a design artifact.

Purpose: route one public design skill from the user's natural-language prompt and current design state without exposing user-selected subcommands.

Preserved Contract: `sp-design` remains the single public entry point; routing separates task type from reference-input strategy, resumes active work before reclassification, and hands domain-external work to its owning workflow.

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
task_type: create | refine | audit
input_strategy: context | synthesize
route_reason: <one evidence-based sentence>
```

After `specify-runtime design change` or `specify-runtime design iterate`
scaffolds the workspace, use
`specify-runtime artifact patch` to store the canonical route in
`.specify/design/changes/<UD-ID>/brief.md`. If the derived design
state exposes a selected-mode field, treat it only as a compatibility
projection of `task_type`; do not invent a second writable workflow-state file.
Use the same owner CLI to repeat the route in review when it explains closeout.

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

## Resume Before Reclassification

1. Query `.specify/design/index.json` and matching
   `.specify/design/changes/<UD-ID>/brief.md` / `design-change.md` through
   `artifact show` first when they exist.
2. If they record nonterminal work for the same objective, resume before
   reclassification at the brief's exact `task_type` and `input_strategy` plus
   the derived state's current stage.
3. Treat approval, feedback, and continuation messages as lifecycle events for
   that active task, not as new audit/create/refine prompts.
4. Reclassify only when the user explicitly changes the objective or live
   evidence proves that the stored route cannot complete safely. Record the
   material route delta before continuing.

## Scope Resolution

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
