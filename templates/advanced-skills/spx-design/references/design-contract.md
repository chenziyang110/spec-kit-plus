# Design-system contract

Use the root `DESIGN.md` as the shared visual and interaction constraint for
feature work. Ground it in current product surfaces and confirmed references.
An initialized `status: bootstrap` file is input to replace, not a locked
direction.

Include only applicable decisions:

- product subject, audience, single user job, and surface/platform fit;
- visual, content, and interaction theses; one recognizable signature; safe
  system choices; and deliberate creative risks with gain/cost;
- color, type, spacing, elevation, motion, iconography, and density tokens;
- component anatomy, variants, states, composition, and reuse rules;
- navigation, feedback, empty/loading/error, and destructive interactions;
- responsive breakpoints or adaptation rules;
- accessibility semantics, focus, contrast, input, and reduced-motion behavior;
- reference fidelity and later visual evidence requirements.

Before locking a new or materially changed direction, use the installed
`design-preview-template.html` as the stable project-level review carrier. One
numbered HTML round holds exactly three directions and one shared comparison
baseline: foundations, components, required states, data density, motion,
responsive frames, and handoff boundaries. Keep it self-contained and
framework-neutral. Modern CSS and bounded inline review behavior may express
direction switching and meaningful animation, but the artifact must not load
remote code/assets, persist data, call a network, simulate business logic, or
claim to be production implementation.

Every direction defines motion purpose plus duration, easing, distance or
spatial behavior, and a `prefers-reduced-motion` equivalent. Compare all three
with the same content and state matrix. If none is satisfactory, incorporate
the user's named feedback into a new immutable round. Approval identifies the
exact round path and direction ID. Freeze it with
`{{specify-subcmd:design approve <round-path> --direction <direction-id> --format json}}`;
the resulting sidecar, preview SHA-256, manifest SHA-256, review round, and
approved decision IDs are the approval truth. Carry those values unchanged
through `DESIGN.md`, the feature UI brief, plan/task UI contracts, and final
visual comparison. A verbal hybrid is not approvable; render it as a new
direction in a new immutable round.

For a new or high-visibility direction, persist an inspectable approved visual
reference in `approval.visual_refs`. Assign each source an explicit use intent;
reference intent and fidelity are separate decisions. Use real product content
and owned/licensed imagery plans instead of lorem ipsum or decorative
placeholders that mask layout risk.

Name existing implementation owners and planned gaps without pretending a
planned token or component already exists. When auditing, cite concrete live
surfaces and distinguish contract drift from intentional exception. Avoid
generic aesthetic prose that cannot guide or verify downstream work.

The embedded preview manifest and visible specimen must agree. Canonical
`DS-<KIND>-NNN` decisions cover color, typography, spacing, component anatomy,
motion/reduced motion, responsive adaptation, and representative content as
applicable. Each decision names its source, affected surfaces, implementation
token or owner, and verification method. Export the approved `DESIGN.md` to
`.specify/design/design-system.json`; downstream work consumes that stable
shape instead of re-authoring the design from prose.

The project-level design preview and feature-level `ui-target.html` are
different artifacts. The preview approves reusable visual, component, state,
density, and motion language. The target later describes one feature
composition and cannot silently replace or weaken the approved preview
reference.
