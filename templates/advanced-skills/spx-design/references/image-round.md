# Image-primary round

Use only when the live capability probe reports `image_generation: available`.
Do not reuse the HTML authoring prompt.

Create one composite GUI review board for one current concept and have the
design CLI persist the exact final request for the numbered round. The image prompt names: use case and
asset type; generate versus edit; product subject, audience, and job; every
input image role; context; style; composition/framing; aspect ratio and output
dimensions; palette/material/type/icon language; exact text; required states;
invariants; and must-avoid constraints. It contains no DOM, CSS, JavaScript, or
production implementation instructions.

If `image_editing: available`, make a targeted edit and repeat the invariants.
Otherwise regenerate the whole board while carrying accepted invariants. If
`image_inspection: available`, inspect the actual saved pixels—at focused/high
detail for small UI text—against hierarchy, crop, alignment, legibility,
platform authenticity, content, state coverage, and invariants before showing
the user. If unavailable, set `inspection_owner: user`, make no visual-quality
claim, and revise from the user's observations.

The image is the primary visual conversation; the adjacent manifest remains the
authority for executable interaction, editing behavior, accessibility, motion,
responsive/data branches, and handoff. Freeze explicit approval with `design
approve <round-image> --manifest <manifest> --prompt <prompt>
--image-inspection <available|unavailable> --image-editing
<available|unavailable>`.
