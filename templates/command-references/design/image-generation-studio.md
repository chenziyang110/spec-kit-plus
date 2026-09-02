Trigger: Only when the current concept round uses generated imagery as its primary review medium.
Purpose: Produce one review board, its exact generation or edit prompt, and a machine-readable manifest.
Preserved Contract: Bind the inspected image, prompt, manifest, capabilities, and immutable round without substituting generation for approval.

# Professional image-generation studio

Use this reference only for an `image-primary` round. Do not reuse the HTML
authoring prompt: image generation controls pixels, composition, and visual
invariants; it does not author a DOM, CSS system, or executable interaction.

## One concept board per immutable round

Generate one composite review board for the same current concept, never three
unrelated alternatives. Do not generate three full boards; if the user needs
choice, use 2-3 textual choices during concept-calibration before this image
round. Choose the target aspect ratio and pixel dimensions before generation.
The board should make one principal surface dominant and show only the labeled
component, state, responsive, or platform specimens needed to judge that
concept. A multi-platform scope keeps one shared thesis but uses clearly
labeled native frames; it must not disguise every platform as Web.

Use the design CLI to persist the exact final prompt and primary raster artifact
for the numbered round. Keep the compact round manifest as the machine contract.
The image is the visual review
surface; the manifest remains the authority for interactions, editing behavior,
accessibility, motion, data branches, and exact implementation handoff.

## Image prompt contract

Write a generation or edit prompt with these explicit sections:

1. **Use case and asset type** — GUI concept review board, target platform, and
   whether this is a new `generate` request or an `edit` of a named prior image.
2. **Subject and single job** — the actual product subject, audience, task, and
   representative content; never “a modern dashboard.”
3. **Input-image roles** — label every attached image as edit source, exact
   content asset, layout reference, style reference, or inspiration, with the
   permitted transfer intent.
4. **Context and scene** — device/window frame, product environment, visible
   modules, data density, state, locale, and color mode.
5. **Style and visual system** — aesthetic family, typography character,
   palette, materials, iconography, spacing rhythm, shape language, and one
   signature element grounded in the brief.
6. **Composition and framing** — hierarchy, focal region, grid, relative scale,
   whitespace, camera/view, labeled specimen placement, aspect ratio, and exact
   output dimensions.
7. **Exact text** — short critical labels and values in quotation marks. Keep
   them limited and inspect legibility; the manifest owns long-form exact copy.
8. **Interaction/state cues** — selected, focus, pending, error, empty, offline,
   permission, or responsive specimens that must be visibly distinguishable.
9. **Invariants** — everything an edit or regeneration must preserve: product
   identity, layout regions, accepted palette/type, signature, content, and
   user-approved details.
10. **Must avoid** — generic card grids, fake feature inventory, illegible text,
    decorative chrome, copied protected branding, platform-inaccurate controls,
    and any brief-specific prohibition.

Keep the prompt descriptive and visual. Do not include HTML, DOM, CSS,
JavaScript, component-library implementation instructions, or production code.

## Generate, inspect, and revise

1. Attach every reference the tool can actually receive and label its role in
   the prompt. Do not rely on remembered conversation images when the current
   tool call cannot include them.
2. Generate one board. Do not select a hidden alternative for the user.
3. If `image_inspection: available`, open the saved output at sufficient detail
   and inspect hierarchy, crop, alignment, type/text legibility, palette,
   platform authenticity, content credibility, state coverage, and invariants.
   Use focused crops or higher-detail inspection for dense text and small UI.
4. Repair one consequential issue at a time. When editing is available, name
   the exact region/change and repeat all invariants. Otherwise regenerate with
   the same prompt contract plus a compact change block.
5. If image inspection is unavailable, present the image without a
   visual-quality claim. Ask what feels right and what is visibly wrong, then
   translate the user's observations into a targeted edit/regeneration prompt.
6. Save every reviewed result as a new numbered round. Never overwrite a
   reviewed or approved image.

Image tools may save their output outside the project. Immediately bring the
selected bytes under the design runtime's ownership with:

`specify-runtime design import <saved-image-path> --change <UD-ID> --round NN --format json`

Use the returned change-local path for inspection, presentation, and approval.
The import validates the raster signature, records its SHA-256 and provenance,
allows only a byte-identical retry, and refuses to replace an existing round.
Do not copy, rename, or hard-link generated pixels into `previews/` by hand.

Generated UI imagery is not executable proof. It cannot demonstrate focus
order, input mechanics, resize continuity, reduced motion, or failure recovery;
those remain explicit manifest/handoff contracts and later real-entrypoint
evidence.

After explicit approval of the named image, freeze it with:

`specify-runtime design approve <change-dir>/previews/round-NN.png --direction direction-main --manifest <change-dir>/previews/round-NN.manifest.json --prompt <change-dir>/previews/round-NN.prompt.md --image-inspection <available|unavailable> --image-editing <available|unavailable> --format json`

Sources informing this prompt contract:

- https://github.com/openai/skills/blob/main/skills/.system/imagegen/SKILL.md
- https://github.com/openai/role-specific-plugins/blob/main/plugins/product-design/skills/ideate/SKILL.md
- https://ai.google.dev/gemini-api/docs/imagen
