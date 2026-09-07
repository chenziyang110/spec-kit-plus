# Image-primary round

Use only when the live capability probe reports `image_generation: available`.
Do not reuse the HTML authoring prompt.

Create one composite GUI review board for one current concept; do not generate
three full boards. If the user needs choice, return to 2-3 textual choices in
concept-calibration before this round. Have the design CLI persist the exact
final request for the numbered round. The image prompt names: use case and
asset type; generate versus edit; product subject, audience, and job; every
input image role; context; style; composition/framing; aspect ratio and output
dimensions; palette/material/type/icon language; exact text; required states;
invariants; and must-avoid constraints. It contains no DOM, CSS, JavaScript, or
production implementation instructions.

Before invoking the image tool, populate `manifest.input_images`, hold the exact
professional prompt in memory, and send it on stdin to
`specify-runtime design prompt <change-dir>/previews/round-NN.manifest.json --content - --format json`.

The create-only `specify-runtime design prompt` command is the sole owner of
the prompt and generation sidecar; its response returns their paths and SHA-256 receipts. It
does not synthesize the request. A byte-identical retry is idempotent; different
or partial existing bytes require a new numbered round. Use the returned prompt
bytes unchanged; `design import` requires that binding.

For bounded legacy draft recovery, when an unchanged image was already imported
by an older runtime and both managed files are absent, the same
`specify-runtime design prompt <manifest> --content - --format json` owner may
bind it only while the exact prompt bytes remain available; do not import the
image again. If the exact prompt bytes are unavailable, or only one managed
file exists, use a new numbered round instead of reconstructing provenance.

For `surface_posture: inherit-existing`, require `operation: edit`,
`image_editing: available`, and a project-contained `edit-source` with
`fidelity: exact` covering `global-shell` and `shared-components`. Source
continuity binds those protected surfaces as exact/preserve. Never regenerate
the whole page from text; use HTML-primary inside the inherited shell when
image editing is unavailable.

If `image_editing: available`, make a targeted edit and repeat the invariants.
Otherwise regenerate the whole board while carrying accepted invariants. If
`image_inspection: available`, inspect the actual saved pixels—at focused/high
detail for small UI text—against hierarchy, crop, alignment, legibility,
platform authenticity, content, state coverage, and invariants before showing
the user. Pass that comparison through `--inspection-json` to
`preview-lint --level concept`; its concept receipt must exist before the round
is presented as confirmable. If unavailable, set `inspection_owner: user`, make no visual-quality
claim, and revise from the user's observations.

The image is the primary visual conversation; the adjacent manifest remains the
authority for executable interaction, editing behavior, accessibility, motion,
responsive/data branches, and handoff. Freeze explicit approval with `design
approve <round-image> --manifest <manifest> --prompt <prompt>
--image-inspection <available|unavailable> --image-editing
<available|unavailable>`.

When the image tool saves outside the project, run `specify-runtime design
import <saved-image-path> --change <UD-ID> --round NN --format json` immediately
after selecting that result. Continue with the returned change-local path. The
runtime preserves the exact bytes and source digest, permits byte-identical
retry, and blocks replacement of the numbered round; never copy, rename, or
hard-link the file into `previews/` manually.
