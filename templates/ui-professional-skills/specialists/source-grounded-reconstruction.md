# Source-Grounded Reconstruction

This specialist skill reconstructs or migrates a user interface from existing
evidence while preserving the product capabilities that the visible reference
alone cannot prove. It is technology-neutral: the source and target may be
desktop, mobile, Web, embedded, CLI, TUI, or a hybrid.

## Apply when

- A screenshot, design export, HTML prototype, or existing page governs the
  target appearance or structure.
- Existing source code, a runnable product, documentation, tests, or business
  rules govern hidden surfaces, interaction behavior, or final outcomes.
- A UI is being migrated, replatformed, rewritten, cloned within authorized
  product boundaries, or completed after a shallow visual reconstruction.
- Visible controls exist in the target but their deeper routes, states, assets,
  side effects, or user-promised results may be missing.

## Evidence roles

Treat each available input as evidence with a bounded role, never as proof of
the whole product:

- screenshots and recordings show visible composition and sampled states;
- HTML, UI description files, and accessibility trees reveal structure and
  sometimes local interaction;
- source code, resources, tests, and configuration reveal possible controls,
  routes, assets, permissions, and side effects;
- the runnable source product reveals reachability, dynamic surfaces, event
  order, feedback, failure behavior, and actual final state;
- requirements, domain rules, and user observation establish the business
  promise when implementation evidence is incomplete or contradictory.

Record the authority, freshness, conflicts, and gaps for every source. Do not
infer hidden behavior from visual similarity or assume that dormant source code
is reachable in the shipped product.

## Source continuity contract

When applicable, produce one structured `source_continuity` contract and carry
it through the selected Design or Quick path. It contains:

- `schema: spec-kit-ui-source-continuity-v1`, `applicability`, `mode`, and a
  source-grounded `reason`;
- `coverage.surface_ids`, `coverage.interaction_ids`, and
  `coverage.component_ids`: the complete discovered/selected ID universe;
  each set must exactly equal the corresponding surface, action, and asset
  binding targets so partial reconstruction cannot pass as complete;
- `authority_refs`: stable references to the governing screenshot, HTML/live
  surface, source, runtime capture, requirements, and business evidence;
- `surface_bindings`: every discovered source surface mapped to a stable target
  surface, its evidence, and exactly one disposition: `preserve`, `adapt`,
  `replace`, `merge`, `split`, or `retire`;
- `action_bindings`: each user trigger recorded with `interaction_id`,
  `source_refs`, `user_promise`, `business_outcome`, `side_effects`,
  `final_state`, and source-target `verification`; linked interaction/scenario
  rows own event order, feedback, cancellation, and recovery mechanics;
- `asset_bindings`: icons, images, fonts, sounds, illustrations, and other
  identity-bearing resources recorded with `component_id`, `semantic_role`,
  `source_refs`, `target_strategy`, `target_ref`, `provenance`, `fallback`, and
  `placeholder_policy`;
- `unresolved_gaps`: strings that name the unknown surface, action, outcome,
  state, asset, or conflict plus its owner and exact next discovery action.

An applicable ready contract has no unresolved gap that can make the target
incomplete, misleading, destructive, or unverifiable. Do not silently classify
an unexplored surface as retired or treat a missing action as a visual detail.

## Surface and behavior discovery

Build the surface inventory from all available sources, not only the initial
screen. Probe menus, toolbars, tabs, drawers, dialogs, popovers, context menus,
secondary windows, deep routes, system integration, shortcuts, drag/drop,
hover/focus behavior, and dynamically generated views. Exercise applicable
empty, populated, loading, partial, error, permission, offline, pending,
cancelled, repeated, and restored states.

For every actionable control trace the complete promise chain:

`input -> UI event -> route/command -> domain operation -> side effect -> feedback -> final state`

The existence of a handler, component, IPC command, API route, or service is
not proof that the control is reachable or fulfills its `business_outcome`.
Record alternate entry paths such as toolbar, menu, shortcut, gesture, or
command when they promise the same result.

## Asset fidelity

Inventory source assets before substituting them. Preserve or deliberately map
semantic role, family, state variants, size, optical alignment, accessibility
name, provenance, and distribution rights through the binding and linked
component contract. Every applicable icon binding uses
`placeholder_policy: forbid-character-substitution`: do not replace an icon or
image with Unicode characters, emoji, arbitrary text glyphs, or ASCII art.
A character is valid only when it is the approved literal content, not a cheap
stand-in for a missing asset. Missing or legally unusable assets remain an
`unresolved_gaps` item until an owned replacement or explicit exception is
approved.

## Image-primary augmentation

- Use the original visual evidence in the board, preserving its stated intent.
- Show discovered secondary surfaces and representative states, not only the
  most flattering starting screen.
- Annotate decisions whose source is runtime or business evidence rather than
  pixels so the board does not imply that appearance proves behavior.

## HTML-primary augmentation

- Model the discovered surface graph and bounded interaction states in the
  review-only prototype without adding production integration.
- Keep deep paths, menus, dialogs, error/recovery states, and asset roles
  inspectable where they change the design contract.
- Do not simulate a success outcome that has no confirmed business semantics;
  expose it as an unresolved contract question instead.

## Delivery and quality gate

- Design remains design-only: it discovers and approves `source_continuity`,
  but does not write target application code or claim runtime parity.
- Quick may own the full direct-delivery migration or reconstruction when its
  confirmed checkpoint binds this contract; depth and surface count increase
  task-local discovery, lanes, and evidence rather than forcing a formal-spec
  handoff.
- Implementation packets receive the exact applicable surface, action, and
  asset bindings; workers do not rediscover or silently weaken them.
- Execution remains technology-neutral. After the runtime derives the
  task/Q-bound continuity manifest, materialize `source-continuity-adapter-plan`
  from the capabilities actually available: one or more generic adapters cover
  source/target surface enumeration, action execution, side-effect observation,
  asset inspection, and visual capture. The plan permits only symbolic tool
  refs, declared execution/write/network policies, typed evidence, and bounded
  actions; it never embeds platform scripts, command/argv/env/install fields,
  or an uncovered lane. Evidence provenance and observation rows bind the exact
  `adapter_id`; the report and worker result bind the immutable plan ref/digest.
- Review runs both source and target real entrypoints when the source is
  runnable, executes matched scenarios with equivalent safe data, and compares
  reachability, feedback, side effects, `business_outcome`, and `final_state`.
  When the source cannot run, use the strongest remaining authority and record
  the withheld parity claim.
- Pass only when coverage is bidirectional and every in-scope surface has an explicit disposition, every
  promised action reaches its verified final state, every asset has an owned
  binding, `unresolved_gaps` is ready-safe, and visual fidelity plus behavioral
  continuity are reported as separate claims.
