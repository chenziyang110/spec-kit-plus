Trigger: at every `sp-design` entry or resume, before asking design questions, selecting a mode, or mutating a design artifact.

Purpose: route one public design skill from the user's natural-language prompt and current design state without exposing user-selected subcommands.

Preserved Contract: `sp-design` remains the single public entry point; routing separates task type from reference-input strategy, resumes active work before reclassification, and hands domain-external work to its owning workflow.

## Single Public Entry Point

- Keep one public skill or command named `sp-design`. Infer the route from the
  user's prompt, `DESIGN.md`, design state, supplied references, and the
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

After scaffolding the brief, use `specify-runtime artifact patch` to store the
canonical route in `.specify/design/design-brief.md`. If the derived design
state exposes a selected-mode field, treat it only as a compatibility
projection of `task_type`; do not invent a second writable workflow-state file.
Use the same owner CLI to repeat the route in review when it explains closeout.

## Routing Dimensions

- `create`: route here when `specify-runtime design` must establish the first
  approved project-level design system because
  `DESIGN.md` is missing, bootstrap-only, or otherwise has no approved visual
  truth.
- `refine`: create a new immutable approval round for a project-wide change to
  an approved direction, tokens, density, component/state rules, responsive or
  motion behavior, brand language, or platform expectations.
- `audit`: inspect readiness, consistency, provenance, live adoption, or drift
  without changing approved design truth.
- `context`: derive direction from confirmed product context and verified live
  project evidence.
- `synthesize`: use supplied screenshots, URLs, design exports, notes, or other
  references with explicit reference intents. Synthesize is an input strategy,
  not a terminal task type; combine it with `create` or `refine`.

## Resume Before Reclassification

1. Query `.specify/design/design-state.md` and
   `.specify/design/design-brief.md` through `artifact show` first when they
   exist.
2. If they record nonterminal work for the same objective, resume before
   reclassification at the brief's exact `task_type` and `input_strategy` plus
   the derived state's current stage.
3. Treat approval, feedback, and continuation messages as lifecycle events for
   that active task, not as new audit/create/refine prompts.
4. Reclassify only when the user explicitly changes the objective or live
   evidence proves that the stored route cannot complete safely. Record the
   material route delta before continuing.

## Decision Table

| Current truth and prompt | Route |
| --- | --- |
| Missing or bootstrap `DESIGN.md`; establish a baseline | `create/context` |
| Missing or bootstrap `DESIGN.md`; references shape the baseline | `create/synthesize` |
| Approved `DESIGN.md`; change project-wide visual or interaction truth | `refine/context` |
| Approved `DESIGN.md`; new references shape a project-wide revision | `refine/synthesize` |
| Check readiness, coverage, provenance, consistency, or drift only | `audit/context` |
| Current evidence proves `no-ui` | record `not-applicable` and exit the visual lane |

For ambiguity between `create` and `refine`, approval status decides. For
ambiguity between `audit` and mutation, start with `audit`; promote to
`create`/`refine` only when the evidence proves design truth must change.

## Domain Boundary Routing

- Route production framework, database, dependency, deployment, or
  implementation architecture decisions to `sp-plan`; durable non-negotiable
  engineering principles belong to `sp-constitution`.
- Route feature behavior, scope, and acceptance truth to `sp-specify`, or to
  `sp-quick` when the user chooses direct delivery and the outcome is already
  confirmable.
- Route implementation drift against correct approved design to `sp-review` or
  the active implementation workflow. Do not rewrite design truth to excuse a
  code defect.
