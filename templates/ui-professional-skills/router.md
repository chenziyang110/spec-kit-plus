# UI Professional Skill Router

Use this router for substantive GUI create or refine work across web, Windows,
macOS, Android, iOS, desktop, mobile, TUI, and visually designed CLI surfaces.
It is a progressive-disclosure router, not another approval authority.

## Resolve the pack

In an installed project, resolve this directory from
`.specify/templates/ui-professional-skills/`. When maintaining Spec Kit Plus
itself, use `templates/ui-professional-skills/`.

Read `catalog.json` first. Do not load every domain, style, or specialist file.
Match the user's current description, approved references, registered design
truth, platform constraints, and prior answers against the compact catalog.
Resolve `style_authority` before choosing a style reference. The optional
deterministic helper is:

```text
python <pack-dir>/route.py --query "<normalized user intent and constraints>" --style-authority <greenfield|inherit-existing|page-overhaul-authorized> --project-root <project-root>
```

For Web work, pass the actual project root. The helper reads only catalog-listed
local manifests and paths; it does not traverse arbitrary source, use the
network, install dependencies, or mutate the project.

## Mature Web UI Resources

For Web UI work, read `mature_web_ui_resources` from `catalog.json` as a compact
resource index for frameworks, component libraries, headless primitives, design
systems, specialist libraries, and agent-specific material. Then read
`web-component-selection.md`; prefer mature components before inventing base
interactions. Dialogs, menus, selects, comboboxes, tabs, tables, forms, toasts,
tooltips, sliders, drawers, command palettes, and accessible focus behavior
should normally come from the current project library or a deliberately
selected mature resource.

Carry `mature_web_ui_resource_ids` in `professional_skill_route` when the route
touches Web, React, Vue, Tailwind, component libraries, or reusable UI systems.
Also persist the compact `web_ui_asset_inventory`, explainable
`mature_web_ui_selection`, and applicable `smoothness_acceptance_ids`. An
unscanned inventory makes the selection provisional; do not turn a provisional
candidate into an installation or migration decision.
Use the catalog entries as source pointers and guardrails, not as permission to
install dependencies, switch libraries, copy protected templates, or override
the live product style authority. In existing products, first reuse inspected
local tokens and components; only propose a new library when the gap is real,
scoped, and compatible with the current stack. Keep the shortlist sparse: one
primary component system, an optional compatible headless layer, and only the
specialist libraries justified by exact capabilities. Load Agent Skills, MCP,
`llms.txt`, or Markdown docs only for a selected candidate.

## Style authority gate

Live product UI is the default style authority. For a feature, component, or
partial functional-page change, set `mode: inherit-existing`, name the inspected
token/theme/component/surface files in `source_refs`, protect `global-shell` and
`shared-components`, keep `allowed_style_delta_surfaces: []`, and force
`style_skill_id: null`. Domain and specialist skills may improve hierarchy,
interaction, accessibility, content, and platform fit, but they must not replace
the current visual language.

Use `page-overhaul-authorized` only when the user explicitly authorizes a visual
overhaul of the exact complete page named in `scope.surfaces`. Record that page
in `allowed_style_delta_surfaces` and the user's exact approval checkpoint in
`authorization_source`; the surrounding global shell and shared components stay
protected. A local feature request, a newly added functional page inside an
existing product, or a vague request to “modernize” is not page-overhaul
authorization. Use `greenfield` only when repository evidence confirms there is
no governing live UI language.

## Sparse selection contract

Select exactly one domain, zero or one style, and zero to two specialists.
Load only those exact references after selection, so a normal round adds at
most four professional references. A selected style is a bias, never a license
to copy a named product, overwrite project truth, or bypass `style_authority`.

When two candidates would materially change hierarchy, interaction, platform
behavior, or visual language, ask one high-impact question and stop before
loading the conflicting references. Do not present a batch questionnaire. If the
route is already recorded for an active immutable round, resume the pinned route;
reroute only after user feedback or registered scope changes invalidate it.

Use this precedence order:

1. approved references and the exact registered design change;
2. explicit user intent, brand/legal rules, platform conventions, and
   accessibility requirements;
3. the selected domain skill;
4. `style_authority`, then the optional style skill when that authority allows one;
5. specialists, which tighten their concern but do not redesign the product.

## Persisted route

Patch `professional_skill_route` into the design brief and the current
change-local design contract:

```yaml
professional_skill_route:
  catalog_version: spec-kit-ui-professional-v1
  status: resolved
  domain_skill_id: domain-general-interface
  style_skill_id: null
  specialist_skill_ids: []
  matched_signals: {}
  loaded_refs: []
  unresolved_candidates: []
  mature_web_ui_resource_ids: []
  web_ui_asset_inventory:
    status: not-scanned
    manifest_refs: []
    lockfile_refs: []
    framework_ids: []
    installed_resources: []
    component_roots: []
    token_refs: []
    theme_refs: []
    surface_refs: []
  mature_web_ui_selection:
    status: not-applicable
    primary_resource_id: null
    supporting_resource_ids: []
    agent_resource_ids: []
    candidates: []
    confirmation_codes: []
  smoothness_acceptance_ids: []
```

`matched_signals` records concise user/reference/platform evidence, not hidden
reasoning. `loaded_refs` must equal the exact selected references. Keep
`status: question-required` and list only the conflicting IDs in
`unresolved_candidates` while a routing question is unanswered.
When mature Web UI selection is `provisional` or `unresolved`, persist the
overall route `status: unresolved`; a resolved domain or style choice must not
hide an unscanned, conflicting, or unmapped live component system.
Candidate `reason_codes` are stable evidence labels, not prose reasoning. Carry
the selected smoothness IDs into existing interaction, motion, and
`usability_validation` rows; they do not introduce a new evidence kind.

## Medium-specific use

For an **image-primary** round, use the selected references to augment the
image-generation or image-edit prompt: subject, art direction, composition,
material, camera/view, platform frame, exact visible copy, states, and
must-preserve invariants. Do not paste HTML/CSS instructions into that prompt.

For an **html-primary** round, use the same route to augment semantic structure,
layout, tokens, responsive behavior, component states, content fidelity,
interaction feedback, and accessibility. Do not recycle the image prompt as an
HTML implementation prompt.

Both media routes author one current concept, gather feedback, and revise that
same direction in a new inspected immutable round. Neither the router nor a
style reference can approve or freeze a concept; only explicit user approval
can do that.
