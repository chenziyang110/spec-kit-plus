# Mature Web Component Selection

Read this reference only when the current route changes Web UI or a reusable Web
component system. The catalog is a maintained shortlist, not an instruction to
install every candidate.

## Evidence before selection

Inspect the live package manifest and lockfile, imported component packages,
local component directories, tokens/themes, framework and major versions,
license constraints, browser targets, SSR/hydration boundaries, and the exact
component capabilities the design requires. Existing-product
`style_authority: inherit-existing` keeps the current visual language and favors
its installed components.

Run the deterministic router with `--project-root <project-root>` to capture the
bounded local `web_ui_asset_inventory`. Treat `not-scanned`, `partial`, or
`unavailable` as a stop against final dependency selection; the Agent may still
present provisional candidates with compact reason and confirmation codes.

## Preference ladder

1. Reuse an accessible live component that already satisfies the states and
   interaction contract.
2. Extend the current component system through its documented API or primitive
   layer.
3. Select one mature primary system compatible with the live framework,
   styling model, accessibility target, license, and maintenance policy.
4. Add at most one headless layer when the primary system lacks a required
   behavior and at most one specialist library for a real table, chart, editor,
   motion, drag-and-drop, virtualization, or floating-UI gap.
5. Author a new primitive only after recording the missing capability and why
   no compatible mature component can satisfy it.

Do not combine multiple full component systems on one surface. Do not replace a
working library to chase a visual trend. A copied-source registry component is
owned application code after adoption; a package component remains governed by
its upstream API, version, and license.

## Category fit

- Use a styled component library or complete design system when delivery speed,
  coherent defaults, broad state coverage, and enterprise patterns dominate.
- Use headless primitives when the product needs a distinctive visual language
  but must not reimplement focus, keyboard, overlay, selection, or form
  behavior.
- Use Web Components when framework neutrality or multi-framework delivery is a
  real constraint and the target SSR/toolchain support is proven.
- Use specialist libraries only for their hard capability. A data grid, chart,
  rich-text editor, drag-and-drop engine, or animation library must not become a
  second general design system.

## Agent material

After the shortlist is resolved, load only the selected library's official
Agent Skill, MCP server, `llms.txt`, Markdown documentation, version page, and
accessibility or migration page that the current task needs. Prefer live
official material over remembered props or third-party examples. Agent material
improves retrieval; it does not authorize dependency installation, license
acceptance, registry trust, upgrades, or migration.

## Smoothness contract

"Smooth" means predictable response, preserved focus/selection/scroll, visible
pending and cancellation states, no duplicate activation, bounded layout work,
and an equivalent reduced-motion path. Prefer native/CSS motion for simple
transitions; add a motion library only for measured choreography needs. Use
virtualization only for proven data volume, and test its keyboard and screen
reader tradeoffs. Validate real content, dense states, resize, touch, keyboard,
IME, slow async completion, cancellation, and reduced motion at the production
entrypoint. A mature component is a foundation, not proof of acceptance.

Use the routed `smoothness_acceptance_ids` as pointers into the current
`interaction_matrix`, `motion_contract`, and
`usability_validation.smoothness_acceptance_ids`. Prove them using the existing
typed structure, visual, and runtime evidence plus visual comparison or human
review; do not invent a fourth UI evidence kind.

At the real entrypoint, materialize the CLI-owned lab manifest with
`specify-runtime evidence smoothness-manifest --feature-dir <feature-dir>
--task-id <Txxx> --format json`. Run the manifest's exact viewport, interaction,
reduced-motion, interruption, and performance matrix through Playwright or the
available browser runner, then submit only observed results through
`specify-runtime evidence smoothness-validate`. The returned report ref and
SHA-256 bind the exact acceptance IDs; screenshots or test pass counts alone do
not close smoothness acceptance.

## Handoff

Persist the compact candidate IDs, local asset inventory, explainable selection,
`component_adoption_plan`, official refresh result, smoothness IDs, and budgets
in `professional_skill_route`. In each affected
`component_contracts` row, name the selected live or upstream component in
`component`, choose `governance: reuse|extend|new`, bind semantic tokens and
required states, and copy the exact nested `adoption` row with action,
package/version/license, source/component refs, reason/basis codes, and
permission state. Copy applicable smoothness IDs and budgets into
`usability_validation`. Downstream Plan and Implement
re-check the installed version and official docs before code or dependency
changes.
