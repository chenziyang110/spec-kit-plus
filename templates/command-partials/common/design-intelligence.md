# Design Intelligence (shared)

Horizontal UI/product design capability for every UI-bearing stage. Not a new
mainline command. Subordinate to approved root `DESIGN.md` plus immutable
preview/approval/handoff when present. Bootstrap `DESIGN.md` is never product
direction.

**UI is a design-system modeling problem, not a one-shot page generation
problem.** Do not jump from a screenshot or idea straight to production markup.
Establish system rules first, then implement against them.

Apply when work changes a user-visible screen, component, layout, navigation or
interaction flow, responsive behavior, visual state, desktop/mobile surface,
TUI layout, or CLI presentation—even without an external screenshot.

{{spec-kit-include: ../design-intelligence/context.md}}

{{spec-kit-include: ../design-intelligence/evidence-rules.md}}

{{spec-kit-include: ../design-intelligence/stage-hooks.md}}

{{spec-kit-include: ../design-intelligence/ui-quality-gate-pointer.md}}

## Non-goals

- No `sp-design-intelligence` or taste top-level command
- No parallel root `.design/` product tree (use `.specify/design/**`)
- No bypass of `specify-runtime design approve` / export digests
- No treating passive anti-slop seeds as approved product direction
- No treating screenshot clone as a substitute for UI System Model
- No second DI vocabulary outside DesignContext / Design Evidence schemas
