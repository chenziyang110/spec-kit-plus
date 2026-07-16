# Workflow Blocker

Use this view only after the workflow has exhausted safe, authorized recovery.
Do not create a separate artifact merely to repeat information already owned by
workflow state or a task lifecycle record.

## Blocked

- Blocker ID: `<stable workflow-local id>`
- Workflow / stage: `<sp-* or spx-*>` / `<stage>`
- Category / owner: `<category>` / `<agent|user|maintainer|external-system>`
- What is blocked: `<one-sentence summary>`
- Why it is blocked: `<specific cause, not only "validation failed">`
- Evidence: `<sanitized command output, status, artifact path, or external result>`
- Automatic recovery attempted: `<action -> result; write none when none was safe>`
- Affected scope: `<what cannot continue and what remains safe>`
- Exact next action: `<smallest action that can change the state>`
- Unblock criteria: `<observable result>`
- Resume point: `<command or exact instruction>`

## Human Action Guide

Include this section only when `human_action_required: true`.

- Goal: `<what the human will accomplish>`
- Why a human is required: `<authority, credential, external UI, subjective
  decision, physical device, or protected environment the agent cannot own>`
- Before you start: `<required account, role, URL, artifact, branch, or local
  state>`
- Safety: `<what must not be pasted, changed, approved, or retried blindly>`

1. **<Step title>** — `<exact click path or command, with placeholders
   explained>`
   - Expected: `<visible success signal>`
   - If not: `<diagnostic or safe alternative>`
2. **Verify** — `<independent check that the blocker is actually removed>`
   - Expected: `<observable result>`
   - If not: `<what evidence to collect instead of guessing>`

Return `<specific status, sanitized output, URL/ID, screenshot, or decision>`.
Never return secrets, session cookies, private keys, or full access tokens.
Then resume with `<command or exact message>`.
