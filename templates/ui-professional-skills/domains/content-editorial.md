# Content Editorial

This domain covers publishing surfaces, reading experiences, documentation-like pages, knowledge products, and editorial storytelling.

## Apply when

- The user needs a reading-first or content-first interface.
- The surface is about articles, guides, libraries, notes, documentation, or editorial landing pages.
- Typography, rhythm, and hierarchy matter more than dense app chrome.
- The content must remain readable across long text, nested sections, and changing article lengths.

## Decisions to resolve

- What the reading goal is: skim, study, compare, or follow a narrative.
- Which editorial tone is appropriate for the subject.
- How much navigation should be visible versus hidden.
- Which content blocks are mandatory and which are optional.
- Whether the page is meant to feel publication-like, documentation-like, or mixed.

## Image-primary augmentation

- Use image-primary when the agent can inspect a page or generated concept.
- Focus the prompt on typography, composition, and section rhythm.
- Use image generation to explore a reading layout, then inspect it for line length, density, and hierarchy.
- Do not let imagery overwhelm the actual content.

## HTML-primary augmentation

- Use HTML-primary when the content needs to be iterated live or the user wants working text structure first.
- Keep headings, lead copy, and article flow stable while discussing the visual direction.
- Ask one question at a time when the answer affects reading depth, navigation, or typography.
- Preserve real content length instead of simplifying it away.

## Quality gate

- Pass only when the page reads comfortably and the structure helps comprehension.
- Verify typography, line length, spacing rhythm, and anchor behavior.
- Reject layouts that look like a marketing page pretending to be editorial.
- Escalate to the accessibility or motion specialists if reading, contrast, or animated transitions are the main risk.

