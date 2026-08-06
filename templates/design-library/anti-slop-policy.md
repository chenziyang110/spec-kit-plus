# Surface-aware anti-slop policy

This policy corrects default LLM UI fingerprints. It is **subordinate** to an
approved project `DESIGN.md` and its immutable preview/approval/handoff
artifacts. It never authorizes production implementation inside `sp-design` /
`spx-design`, and it never replaces `design approve`.

Use the surface type from the design brief (`landing`, `product-workspace`,
`hybrid`, `existing-pattern-maintenance`) plus audience constraints
(trust-public / accessibility-critical) to select the default lock set. Record
the active locks in `design_brief.anti_slop_locks`.

## Global defaults (all visual surfaces)

Avoid unless the brief or approved design explicitly requires them:

- neon outer glows, pure `#000000` canvases, and oversaturated multi-accent palettes
- interchangeable three equal feature-card rows as the default marketing layout
- placeholder copy, startup-slop verbs ("Elevate", "Seamless", "Unleash"), and fake-perfect metrics
- inventing a second design system when an approved `DESIGN.md` already governs tokens

## Surface splits

### `landing` / marketing / portfolio

- Prefer higher layout variance and a single memorable signature element.
- Ban default AI-purple/blue neon hero aesthetics and section-number eyebrows.
- Hero content must stay scannable; avoid version-label eyebrows unless the
  brief is literally a launch/preview status story.
- Default dial lean: variance 7-9, motion 6-8, density 3-5.

### `product-workspace` / ops / developer tools

- Prefer lower layout variance, clearer hierarchy, and denser information.
- Ban landing-hero theatrics (kinetic type stunts, agency portfolio clichés) as
  defaults for workspace chrome.
- Preserve scanability, status language, and keyboard-first feedback.
- Default dial lean: variance 4-6, motion 2-4, density 6-8.

### `trust-public` / regulated / accessibility-critical

- Prefer restrained motion, high-contrast intent, and real design-system
  foundations when one is expected (`foundation_strategy: real-ds:<name>`).
- Ban experimental layout chaos and low-contrast decorative treatments.
- Default dial lean: variance 3-4, motion 2-3, density 4-5.

### `existing-pattern-maintenance`

- Inherit live product language first; anti-slop locks audit drift only.
- Do not introduce a new aesthetic family without a `refine` approval round.

## Subordination rules

1. If `DESIGN.md` is approved, follow its tokens, components, motion, and
   signature even when they conflict with a lock above.
2. If `DESIGN.md` is bootstrap-only, do not treat seed presets or this policy as
   approved product direction—route create through design.
3. Narrow existing-pattern fixes may proceed with a recorded soft risk when the
   governing live surface is clear; they still must not invent a parallel system.

## Not global constitution

Do not promote landing-only bans (for example absolute em-dash bans or font
blacklists) into project-wide engineering constitution. Keep locks in the
design brief and design-system artifacts where product context can override them.
