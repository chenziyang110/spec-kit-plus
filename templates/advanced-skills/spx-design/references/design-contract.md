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

For a new or high-visibility direction, persist an inspectable approved visual
reference in `approval.visual_refs`. Assign each source an explicit use intent;
reference intent and fidelity are separate decisions. Use real product content
and owned/licensed imagery plans instead of lorem ipsum or decorative
placeholders that mask layout risk.

Name existing implementation owners and planned gaps without pretending a
planned token or component already exists. When auditing, cite concrete live
surfaces and distinguish contract drift from intentional exception. Avoid
generic aesthetic prose that cannot guide or verify downstream work.
