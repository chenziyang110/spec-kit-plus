# Accessibility Localization

This specialist skill focuses on accessibility, keyboard support, readable content, localization, and platform-sensitive text behavior.

## Apply when

- The user mentions accessibility, keyboard, screen readers, focus, contrast, or reduced motion.
- The interface must support multiple languages or platform-specific text conventions.
- Copy length, date format, number format, or input behavior changes across locales.

## Decisions to resolve

- Which accessibility targets matter for this surface.
- Whether the product needs screen-reader friendliness, keyboard-first support, or reduced-motion behavior.
- Which locales, scripts, or writing directions must be respected.
- What copy or labels are platform-specific.

## Image-primary augmentation

- Use image-primary to inspect visible contrast, label clarity, density, and text wrapping.
- Generate locale-specific examples when the text length or script changes the layout.

## HTML-primary augmentation

- Use HTML-primary when the user needs to test keyboard paths, focus order, or localized copy live.
- Ask one question at a time about locale coverage and accessibility priorities.
- Keep the prototype honest about label length and assistive behavior.

## Quality gate

- Pass only when the UI is readable, operable, and locale-aware.
- Verify focus visibility, target sizes, labels, and text expansion behavior.
- Reject interfaces that rely on color alone or break when translated.

