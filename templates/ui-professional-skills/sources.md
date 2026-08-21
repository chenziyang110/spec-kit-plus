# UI Professional Skills Sources

This file records the upstream sources used to shape the UI professional skill pack. It is a synthesis reference, not a copy target.

## Verified sources

- Anthropic `frontend-design` - https://github.com/anthropics/skills/blob/main/skills/frontend-design/SKILL.md
  - License: Apache 2.0.
  - Use: baseline design voice, aesthetic discipline, progressive disclosure, and design-focused prompting.

- OpenAI `skill-creator` - https://github.com/openai/skills/blob/main/skills/.system/skill-creator/SKILL.md
  - License: Apache 2.0.
  - Use: skill anatomy, trigger descriptions, progressive disclosure, and resource bundling patterns.

- OpenAI `imagegen` - https://github.com/openai/skills/blob/main/skills/.system/imagegen/SKILL.md
  - License: Apache 2.0.
  - Use: structured image prompt scaffolding, separate generation vs edit constraints, and invariant handling.

- OpenAI `frontend-app-builder` - https://github.com/openai/plugins/blob/main/plugins/build-web-apps/skills/frontend-app-builder/SKILL.md
  - License: Apache 2.0.
  - Use: image-first concepting, faithful implementation, browser verification, and multi-section web UI planning.

- OpenAI `image-to-code` - https://github.com/openai/role-specific-plugins/blob/main/plugins/product-design/skills/image-to-code/SKILL.md
  - License: Apache 2.0.
  - Use: image/mockup to implementation fidelity, rendered comparison, and responsive translation.

- OpenAI `audit` - https://github.com/openai/role-specific-plugins/blob/main/plugins/product-design/skills/audit/SKILL.md
  - License: Apache 2.0.
  - Use: flow, journey, screen, and multi-step UX audit patterns grounded in screenshots.

- OpenAI `design-qa` - https://github.com/openai/role-specific-plugins/blob/main/plugins/product-design/skills/design-qa/SKILL.md
  - License: Apache 2.0.
  - Use: source-target vs rendered-implementation comparison, fidelity gates, and blocked QA handling.

- Vercel Web Interface Guidelines - https://github.com/vercel-labs/web-interface-guidelines/blob/main/command.md
  - License: MIT.
  - Use: keyboardability, focus visibility, forms, responsive layout, reduced motion, content behavior, and accessible copy.

- `web-design-guidelines` example skill - https://github.com/vercel/examples/blob/main/.agents/skills/web-design-guidelines/SKILL.md
  - License: MIT.
  - Use: fetch-latest-guidelines-then-review workflow for browser-facing UI audits.

- nextlevelbuilder `ui-ux-pro-max` - https://github.com/nextlevelbuilder/ui-ux-pro-max-skill/blob/main/.claude/skills/ui-ux-pro-max/SKILL.md
  - License: MIT.
  - Use: platform-aware UI/UX trigger phrasing, stack coverage, and broad UI design intelligence routing.

- pbakaus `impeccable` - https://github.com/pbakaus/impeccable/blob/main/skill/reference/document.md
  - License: Apache 2.0.
  - Use: design vocabulary, anti-patterns, design-system extraction, and agent-facing craft rules.

- Leonxlnx `taste-skill` - https://github.com/Leonxlnx/taste-skill
  - License: repository license at the cited source.
  - Use: aesthetic trigger vocabulary, taste calibration, and anti-generic visual checks.

- Emil Kowalski `skills` - https://github.com/emilkowalski/skills/blob/main/skills/emil-design-eng/SKILL.md
  - License: MIT.
  - Use: animation judgment, motion taste, and the "small details compound" approach to polish.

- shadcn/ui - https://github.com/shadcn-ui/ui/blob/main/skills/shadcn/cli.md
  - License: MIT.
  - Use: registry-driven component sourcing, deterministic docs lookup, and practical component composition.

## How to use these sources

- Use them to shape trigger descriptions, routing tables, and quality gates.
- Do not copy wording verbatim into downstream skill files.
- Prefer one source of truth per behavioral rule whenever possible.
- Treat MIT and Apache sources as reusable reference material, but keep attribution in downstream project policy if you vendor any text or structure closely.
