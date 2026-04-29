## Objective

Point the user at the supported Codex team/runtime surface and keep unsupported runtime aliases or backdoors out of the primary workflow.

## Context

- This surface is Codex-only.
- It exists to route users to the official `sp-teams` product entry point rather than to internal runtime plumbing.
- The runtime still requires a tmux-capable environment and the generated Codex team assets.

## Process

- Present the official runtime surface and its first-release boundary.
- Validate that the required runtime prerequisites exist.
- Redirect users away from unsupported or deprecated entry points.

## Output Contract

- Provide runtime entrypoint guidance and validation expectations only.
- Keep the supported operator-facing command surface unambiguous.

## Guardrails

- Do not surface this guidance through non-Codex integrations.
- Do not teach internal or deprecated aliases as the supported product surface.
- Do not imply the runtime works without the required environment prerequisites.
