# Design Intelligence (shared)

Horizontal UI/product design capability for every UI-bearing stage. Not a new
mainline command. Subordinate to the exact registered
`.specify/design/changes/<UD-ID>/design-change.md` selected by the consumer, plus its
immutable preview/approval/handoff. No root design contract participates in
selection or delivery.

**UI is a design-system modeling problem, not a one-shot page generation
problem.** Do not jump from a screenshot or idea straight to production markup.
Establish system rules first, then implement against them.

Apply when work changes a user-visible screen, component, layout, navigation or
interaction flow, responsive behavior, visual state, desktop/mobile surface,
TUI layout, or CLI presentation—even without an external screenshot.

For Design discovery, derive one exact stable path-like surface ID from
confirmed source surfaces or registered metadata before each
`specify-runtime design resolve --scope <exact-surface> --format json` call.
Split Web, CLI, API, and other surfaces into separate scoped queries; never pass
the whole brief, a prose objective, or a cross-platform sentence as `--scope`.
Query `.specify/design/index.json` through `specify-runtime artifact show` only
when it exists or the resolver identifies registered metadata. A missing registry or zero matching changes is legitimate
discovery absence, not an artifact-read failure to retry. It does not waive
required approved Design: new/high-visibility UI must still obtain and register
an approved change, not replace that contract with a prose risk note. Preserve
the late-design `formal-post-specify` receipt and unchanged-spec return to Plan,
plus all existing approval, registration, and adoption gates.

{{spec-kit-include: ../design-intelligence/shared-foundation.md}}

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
