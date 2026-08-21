# Live visual capability routing

Read this reference before choosing a review medium. Capability belongs to the
current session's callable tools, not to an integration name, model family, or
remembered product description.

## Probe three independent capabilities

Inspect the live capability surface at every `sp-design` entry and resume. Do
not hard-code capability from the Agent or CLI name. Record only evidence that
is visible in the current tool inventory:

- `image_generation`: can this session create a new raster image?
- `image_inspection`: can this session open and reason over the actual pixels
  of supplied and generated images?
- `image_editing`: can this session revise an existing image while preserving
  named regions and invariants?

Each value is `available` or `unavailable`. Never infer image inspection from
image generation, or editing from generation. A text model calling an external
generator may have generation without vision or edit support.

## Select the primary review route

| image_generation | image_inspection | Primary medium | Inspection owner | Required behavior |
| --- | --- | --- | --- | --- |
| available | available | `image-primary` | `agent-and-user` | Generate one concept board, inspect its actual pixels, repair, then present it. |
| available | unavailable | `image-primary` | `user` | Generate and present the board, make no visual-quality claim, and revise from the user's concrete observations. |
| unavailable | available | `html-primary` | `agent-and-user` | Author the HTML concept, inspect real browser captures, repair, then present it. |
| unavailable | unavailable | `html-primary` | `user` | Author the HTML concept, provide the stable deep link, and make no visual-quality claim before user review. |

If `image_editing: available`, revise the prior generated board with a targeted
edit and a repeated invariant block. If unavailable, regenerate the whole board
while carrying the same invariant block. This changes the production technique,
not the immutable-round rule.

Persist the probe evidence, selected `primary_medium`, `inspection_owner`, and
prompt strategy in `brief.md`. Re-probe on resume because tools may have changed;
if the route changes after a reviewed round, create a new immutable round and
record the reason. Do not silently convert an approved image to HTML or vice
versa.

## Reference-image truthfulness

- When image inspection is available, open the actual image. Label every input
  by role (`baseline`, `layout reference`, `style reference`, `content asset`,
  or `edit source`) and state what may and may not transfer.
- Never infer visual details from a filename, alt text, URL, or prior prose
  summary when the pixels were not inspected.
- When image inspection is unavailable, tell the user the reference is
  uninspected and ask for the smallest textual constraints needed to proceed.
  The user owns visual critique; the Agent may still reason over the manifest,
  interaction contract, and explicit feedback.
- Comparing a source and candidate means opening both actual artifacts. A
  screenshot path or digest proves identity, not visual fidelity.

Sources informing this route:

- https://github.com/openai/skills/blob/main/skills/.system/imagegen/SKILL.md
- https://github.com/openai/role-specific-plugins/blob/main/plugins/product-design/skills/ideate/SKILL.md
- https://github.com/openai/role-specific-plugins/blob/main/plugins/product-design/skills/design-qa/SKILL.md
- https://platform.claude.com/docs/en/build-with-claude/vision

