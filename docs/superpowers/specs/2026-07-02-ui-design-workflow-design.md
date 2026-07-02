# UI Design Workflow Design

**Date:** 2026-07-02
**Status:** Proposed
**Owner:** Codex

## Summary

Add a first-class UI design workflow to Spec Kit Plus so generated projects can
deliver product-quality interfaces, not only working behavior.

The design introduces:

- a root `DESIGN.md` file as the project design-system contract
- a new `sp-design` workflow for creating, synthesizing, refining, and auditing
  the design system
- a built-in design library made of Spec Kit Plus owned, second-created design
  presets
- `specify design lint`, `specify design export`, and `specify design import`
  helper surfaces
- cross-workflow UI quality carry-forward through `sp-discussion`,
  `sp-specify`, `sp-plan`, `sp-tasks`, and `sp-implement`
- a passive `spec-kit-ui-design` skill and aligned updates to `frontend-design`
  and `webapp-testing`

The guiding rule is:

> UI quality is product scope, not a late polish task.

## Problem Statement

AI coding workflows can often implement the requested functionality correctly while
shipping generic, inconsistent, or visually weak interfaces. The current Spec Kit
Plus flow has pieces that help with UI work, especially the bundled
`frontend-design` and `webapp-testing` passive skills, but the main workflow does
not yet treat design quality as a durable requirement.

The gaps are:

- no root project design-system artifact that agents must read before UI work
- no dedicated workflow for discussing and locking product visual direction
- no way to synthesize strong external or user-provided references into a project
  owned design system
- no cross-stage traceability from design intent to planning constraints, tasks,
  implementation evidence, and review
- no default UI evidence requirement at implementation closeout
- no project-level lint/export/import surface for design-system files

The result is that agents may build useful screens that still feel like default
templates or unrelated one-off styling.

## Research Inputs

External references shaped this design:

- Google Labs `design.md`: useful precedent for a Markdown design-system contract
  aimed at coding/design agents, with structured tokens and lint/export ideas.
  Source: <https://github.com/google-labs-code/design.md>
- VoltAgent `awesome-design-md`: useful evidence that curated `DESIGN.md` files
  can work as a practical style library for AI-assisted UI generation. Source:
  <https://github.com/VoltAgent/awesome-design-md>
- Cursor Designer: useful precedent for packaging UX, UI, IA, and accessibility
  rules as reusable AI-agent guidance. Source:
  <https://github.com/spencergoldade/cursor-designer>
- UI Design Brain: useful precedent for encoding component, layout, interaction,
  anti-pattern, and accessibility knowledge for AI UI work. Source:
  <https://github.com/carmahhawwari/ui-design-brain>
- Microsoft frontend design review skill: useful precedent for review gates that
  evaluate design-system compliance, craft, accessibility, and user-task quality.
  Source:
  <https://github.com/microsoft/skills/blob/main/.github/skills/frontend-design-review/SKILL.md>
- Anthropic frontend design skill: useful precedent for steering agents away from
  generic AI-looking interfaces and toward intentional visual direction. Source:
  <https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md>

Spec Kit Plus should learn from these patterns without depending on any external
tool or copying external design files verbatim.

## Goals

- Make `DESIGN.md` a first-class generated project asset.
- Add `sp-design` as the workflow for product-wide UI style and design-system
  decisions.
- Let users synthesize strong references into their own project design system.
- Keep the built-in design library owned by Spec Kit Plus rather than a direct
  third-party file collection.
- Carry UI decisions through discussion, specification, planning, task generation,
  and implementation.
- Support Web, mobile, desktop, TUI, and CLI output, with platform-appropriate
  evidence requirements.
- Add basic design lint/export/import helpers without making external tools
  mandatory.
- Make UI quality auditable through screenshots, viewport checks, accessibility
  checks, terminal-output checks, or equivalent platform evidence.

## Non-Goals

- Do not implement source UI components as part of `sp-design`.
- Do not let `sp-design` write CSS, application code, tests, or business specs.
- Do not copy external `DESIGN.md` files verbatim and remove attribution.
- Do not depend on Google `design.md` CLI or any external design CLI to make the
  feature work.
- Do not require pixel-perfect visual diffing in v1.
- Do not block every small UI change on a full design-system workflow.
- Do not treat Web-only visual rules as sufficient for mobile, desktop, TUI, or
  CLI interfaces.

## User Experience

The user can run `sp-design` when:

- starting a new product
- adding UI to a project that lacks design direction
- redesigning a core experience
- importing or synthesizing references
- auditing whether the current `DESIGN.md` is strong enough for upcoming UI work

Typical prompts:

- "Create a design direction for this product."
- "Use these screenshots as inspiration and turn them into our own design system."
- "Audit our current DESIGN.md before we build the dashboard."
- "Make this feel like a precise developer tool, but still approachable."
- "Revise the mobile design rules without changing the Web app direction."

The workflow should ask product-design questions one at a time, offer two or three
directions, and write `DESIGN.md` only after the user confirms the direction.

## Design System Asset

Generated projects should receive a root `DESIGN.md` by default. It is the
human-readable and agent-readable design-system contract for the project.

The default file is a template, not a strong preset. It contains enough structure
that agents know what to fill and what to obey.

Recommended sections:

- Product Design Intent
- Supported Platforms
- Visual Direction
- Design Tokens
- Typography
- Spacing And Density
- Layout Rules
- Components
- Interaction States
- Motion
- Accessibility
- Platform Adaptation
- Anti-Patterns
- UI QA Checklist
- Design Change Policy

The file should be compact enough for agents to read routinely, but concrete
enough to constrain implementation choices.

## DESIGN.md v1 Schema

`DESIGN.md` v1 should be Markdown with YAML front matter. The YAML front matter
is the machine-readable contract for lint and export. The Markdown body is the
human-readable rationale and agent guidance.

Minimum front matter shape:

```yaml
---
design_system:
  schema: spec-kit-design-v1
  name: project-design-system
  version: 1
  platforms:
    - web
    - mobile
    - desktop
    - tui
    - cli
  tokens:
    color:
      surface.canvas:
        value: "#ffffff"
        usage: primary app background
      text.primary:
        value: "#111827"
        usage: primary text
    spacing:
      scale.4:
        value: "16px"
        usage: default section gap
    radius:
      control:
        value: "6px"
        usage: buttons, inputs, compact cards
    typography:
      body.family:
        value: "system-ui"
        usage: default interface text
  components:
    button:
      required_states:
        - default
        - hover
        - focus
        - disabled
        - loading
      token_refs:
        background: "{color.surface.canvas}"
        text: "{color.text.primary}"
  accessibility:
    contrast_intent: WCAG AA for ordinary text where platform allows
    focus_visible: required
    keyboard_navigation: required
---
```

V1 parser boundary:

- Parse only YAML front matter for lint and export.
- Treat Markdown sections as guidance, not as normative token data.
- Require `design_system.schema: spec-kit-design-v1`.
- Require token categories to be maps of `name -> {value, usage}`.
- Require token names to be dot-separated ASCII identifiers under their category.
- Validate token references with the `{category.token.name}` syntax.
- Validate references only inside machine-readable front matter fields such as
  `components.*.token_refs`.
- Allow unknown front matter keys so future schema versions can extend the file
  without breaking v1 readers.

Export rules:

- `specify design export --format json` emits the normalized
  `design_system.tokens` tree plus component token references.
- `specify design export --format tailwind` maps supported token categories to
  Tailwind theme fields: colors, spacing, borderRadius, fontFamily, fontSize,
  boxShadow, and animation where present.
- Unsupported token categories remain in the JSON export and are reported as
  skipped for Tailwind export rather than causing export failure.

## Built-In Design Library

Spec Kit Plus should include a built-in design library under
`templates/design-library/**`.

This library is not a direct archive of third-party design files. It is a curated
set of Spec Kit Plus owned design presets created by studying strong product and
design-system references, abstracting their reusable principles, removing
brand-specific expression, and writing original `DESIGN.md` presets in the Spec
Kit Plus format.

Initial library entries:

- `workbench-precision`: dense professional tools, dashboards, CRM, admin panels
- `developer-tool-sharp`: developer products, IDE-like tools, infra consoles
- `data-dense-ops`: observability, logistics, analytics, monitoring, operations
- `consumer-mobile-polished`: consumer mobile apps and cross-platform app shells
- `editorial-commerce`: product, content, media, commerce, and brand storytelling
- `ai-product-calm`: AI assistants, model tools, research surfaces, agent consoles

Each entry should include:

- `DESIGN.md`: the preset design-system file
- `preview.md`: short human-readable summary of what the preset is for
- optional example tokens or export fixtures when needed for tests

The library may be informed by GitHub, official design systems, public websites,
articles, screenshots, user-provided examples, and internal curation. The source
type is not a product boundary. The built-in files are treated as Spec Kit Plus
original presets after synthesis.

## Design Synthesis

`sp-design` supports synthesis from references.

Inputs may include:

- URL
- screenshot
- existing `DESIGN.md`
- design system documentation
- public product page
- user-written style notes
- built-in preset

The synthesis process:

1. Extract design intent: tone, density, color relationships, typography feel,
   layout rhythm, component conventions, states, motion, platform assumptions, and
   accessibility posture.
2. Remove protected expression: brand names, logos, proprietary copy, exact page
   composition, trademarked terms, and source-specific identity.
3. Normalize to Spec Kit Plus design schema.
4. Present two or three project-specific design directions.
5. After user approval, write the project's own `DESIGN.md`.

The output is not a copied artifact. It is the user's project design system.

## sp-design Workflow Contract

`sp-design` is a design-system workflow, not an implementation workflow.

Allowed writes:

- `DESIGN.md`
- `.specify/design/design-state.md`
- `.specify/design/references.md`
- `.specify/design/options.md`
- `.specify/design/review.md`
- stable design rules in `.specify/memory/project-rules.md` when they should
  become shared project defaults

Forbidden writes:

- source code
- UI components
- CSS or theme implementation files
- tests
- business feature specs
- plan or task artifacts outside the active design workflow

Supported modes:

- `create`: generate a new project design system from product context
- `synthesize`: transform references into an original design system
- `refine`: update an existing `DESIGN.md`
- `audit`: inspect whether the current design system is enough for upcoming UI work

Workflow steps:

1. Read project context: README, app structure, existing UI surfaces, existing
   design files, project memory, and relevant learnings.
2. Identify interface platforms: Web, mobile, desktop, TUI, CLI output, or a
   combination.
3. Collect references: built-in design library, user inputs, external references,
   screenshots, or existing design files.
4. Extract design direction and constraints.
5. Present two or three approaches with trade-offs.
6. Ask the user to approve a direction.
7. Write or update `DESIGN.md`.
8. Run design self-review and optional `specify design lint`.
9. Ask the user to review the written design before downstream workflows consume
   it as locked input.

## Cross-Workflow Carry-Forward

### sp-discussion

`sp-discussion` should recognize UI-facing signals:

- UI, UX, IA, visual design, screen, layout, navigation, component, styling
- design system, brand, tone, density, spacing, typography, accessibility
- Web, mobile, desktop, TUI, CLI output

When UI signals appear, it records design intent and experience commitments in the
discussion state and handoff. For new products, redesigns, brand changes, and core
experience changes, it should route to or recommend `sp-design`. For small UI
changes, it may continue while recording a design-system soft risk.

Discussion handoffs should include:

- `experience_commitments`
- `design_system_requirements`
- `design_system_status`
- `design_risk_level`

### sp-specify

`sp-specify` must read `DESIGN.md` when the feature has user-interface scope.

The spec package should capture:

- Experience Requirements in `spec.md`
- design-system readiness in `alignment.md`
- relevant design references and gaps in `context.md`
- whether a missing or insufficient design system is a blocker or soft risk

Strong blocker triggers:

- new product UI
- redesign or rebrand
- core workflow experience
- multi-platform design decisions
- high-visibility customer-facing surface

Soft-risk cases:

- small internal form changes
- narrow copy or state improvements
- already-covered component variants
- low-risk CLI/TUI wording refinements

### sp-plan

`sp-plan` turns `DESIGN.md` into implementation constraints.

The plan should include a `Design System Adoption` section with:

- design-system source and status
- token strategy
- component reuse and extension policy
- platform adaptation strategy
- accessibility requirements
- screenshot or output evidence strategy
- forbidden styling drift

Plan artifacts should make it clear where implementers may use judgment and where
the design system is binding.

### sp-tasks

`sp-tasks` generates design-quality execution work.

`tasks.md` should include `Design Quality Coverage` for user-visible surfaces:

- surface name
- design source
- required states
- platform coverage
- evidence required
- task IDs that implement and verify the surface

UI tasks should cover:

- default, hover, focus, disabled, loading, empty, error, and success states when
  relevant
- responsive layout or platform adaptation
- accessibility checks
- screenshots, terminal samples, recordings, or manual review artifacts
- no-color or narrow-terminal modes for TUI/CLI

### sp-implement

`sp-implement` reads `DESIGN.md`, `Design Quality Coverage`, and task evidence
requirements before executing UI work.

It may not close UI tasks with only `tests passed` unless the accepted task package
explicitly says that tests are sufficient evidence. Usual evidence should include:

- Web: Playwright screenshots, viewport checks, accessibility checks, and visual
  review notes
- mobile or desktop: screenshots or recordings, platform-state coverage, and
  accessibility checks where available
- TUI or CLI: representative output, narrow-width output, no-color output, error
  and empty states, and readability checks

If implementation finds `DESIGN.md` missing, contradictory, or insufficient, it
records a blocker and routes back to `sp-design`, `sp-plan`, or `sp-specify`
according to ownership.

## Helper Commands

### specify design lint

Checks:

- `DESIGN.md` exists when requested
- required sections are present
- token names and references are internally consistent
- platform sections are present for declared platforms
- component states are covered
- accessibility intent is present
- anti-patterns are explicit
- design QA checklist is present

The lint command does not decide whether a design is beautiful. It checks whether
the design system is complete enough for agents to use.

### specify design export

Exports design tokens from `DESIGN.md` into machine-readable formats.

Initial formats:

- `json`
- `tailwind`
- DTCG-like JSON when the token shape can support it cleanly

The export surface helps implementation avoid ad hoc style decisions.

### specify design import

Creates a reference summary from a URL, file, screenshot description, text notes,
or existing `DESIGN.md`.

It should not write the final project `DESIGN.md` directly. It produces an input
for `sp-design`, which then presents directions and writes the final design system
after user approval.

## Passive Skills

### spec-kit-ui-design

Add a passive skill that triggers for UI, UX, design system, visual quality,
accessibility, platform interface, and component work.

Responsibilities:

- read `DESIGN.md` before UI work
- apply platform-specific UI quality rules
- detect missing design-system guidance
- preserve design-system constraints during planning and implementation
- require evidence appropriate to the platform
- reject generic one-off styling when a project design system exists

### frontend-design

Keep the existing Web-focused creative skill, but make it subordinate to
`DESIGN.md`.

If `DESIGN.md` exists, the skill should use it as the design system and avoid
inventing unrelated bold aesthetics.

If no design system exists and the work is high-visibility or core experience,
the skill should recommend `sp-design` before implementation.

### webapp-testing

Extend guidance to include:

- viewport screenshot checks
- visual regression-friendly screenshot paths
- accessibility checks where available
- console and layout overflow checks
- evidence naming that can be referenced from `sp-implement` closeout

## Integration Surface

Implementation should update:

- `templates/design-template.md`
- `templates/design-library/**`
- `templates/commands/design.md`
- `templates/command-partials/design/shell.md`
- `templates/passive-skills/spec-kit-ui-design/SKILL.md`
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- `templates/passive-skills/frontend-design/SKILL.md`
- `templates/passive-skills/webapp-testing/SKILL.md`
- `templates/commands/discussion.md`
- `templates/commands/specify.md`
- `templates/commands/plan.md`
- `templates/commands/tasks.md`
- `templates/commands/implement.md`
- `templates/spec-template.md`
- `templates/plan-template.md`
- `templates/tasks-template.md`
- `templates/workflow-state-template.md`
- `templates/project-handbook-template.md`
- `README.md`
- `PROJECT-HANDBOOK.md`
- `pyproject.toml`
- CLI command registration and integration generation surfaces under
  `src/specify_cli/**`
- relevant tests under `tests/**`

The change is a generated project product-surface change, so it should be treated
as cross-CLI by default.

## Validation Strategy

Template and packaging tests:

- `design-template.md` is packaged and installed.
- `design-library/**` is packaged and installed.
- `sp-design` is generated across Markdown, TOML, and skills-based integrations.
- `spec-kit-ui-design` passive skill is installed for skills-based integrations.

Workflow semantics tests:

- `spec-kit-workflow-routing` recommends or routes high-risk UI/design work to
  `sp-design`.
- `sp-discussion` records UI/design intent and routes high-risk UI work to
  `sp-design`.
- `sp-specify` reads and preserves `DESIGN.md` for UI features.
- `sp-plan` includes design-system adoption constraints.
- `sp-tasks` includes design-quality coverage.
- `sp-implement` requires UI evidence before completion.

Helper command tests:

- `specify design lint` detects missing sections and missing state coverage.
- `specify design export --format json` emits token JSON.
- `specify design export --format tailwind` emits a Tailwind-compatible token
  shape.
- `specify design import` creates a reference summary rather than directly
  replacing `DESIGN.md`.

Documentation tests:

- README mentions `sp-design`.
- Project handbook template explains the design-system asset and workflow.
- Supported workflow lists include `sp-design`.

## Success Criteria

- New generated projects include a root `DESIGN.md`.
- Users can run `sp-design` to create, synthesize, refine, or audit design systems.
- UI-related discussion/spec/plan/task/implement flows preserve design intent.
- High-risk UI work is blocked or routed to design-system creation when needed.
- Small UI work can proceed with recorded soft risk when appropriate.
- Implemented UI work produces platform-appropriate evidence.
- Built-in design presets are Spec Kit Plus owned second-created design files.
- `specify design lint/export/import` work without external design tools.

## Implementation Decisions

- `specify init` should install a root `DESIGN.md` for every generated project.
  Non-UI projects can leave it as a short design-system stub, but UI
  projects get a known file path that agents can read before interface work.
- `specify design lint` v1 should ship with structural checks, token-reference
  checks, platform-section checks, component-state coverage checks, and basic
  accessibility-intent checks. It should not attempt subjective visual scoring.
- `specify design export` v1 should support `json` and `tailwind`. DTCG-like
  output is allowed when the token shape supports it, but it should not block the
  first implementation.
- `specify design import` v1 should write a reference summary for `sp-design` to
  consume. It should not directly overwrite `DESIGN.md`.
- Visual companion previews are useful for `sp-design`, but generated workflow v1
  should not depend on a browser companion. Preview support can be added later
  without changing the core `DESIGN.md` contract.

These decisions make the first implementation plan concrete while preserving a
clear path to richer visual previews and stronger token tooling later.
