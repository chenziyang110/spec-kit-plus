---
name: worker
description: Team worker protocol for the bundled `sp-team` runtime surface
---

# Worker Skill

This skill is for a Codex session started as an AgentTeams worker pane.

## Identity

You MUST be running with `SP_TEAMS_WORKER` set. It looks like:

`<team-name>/worker-<n>`

## Load Path

When a worker inbox tells you to load this skill, resolve the first existing path:

1. `${CODEX_HOME:-~/.codex}/skills/worker/SKILL.md`
2. `~/.codex/skills/worker/SKILL.md`
3. `<leader_cwd>/.codex/skills/worker/SKILL.md`
4. `<leader_cwd>/skills/worker/SKILL.md`

## Startup ACK

Before task work:

```bash
sp-team send-message --input "{\"team_name\":\"<teamName>\",\"from_worker\":\"<workerName>\",\"to_worker\":\"leader-fixed\",\"body\":\"ACK: <workerName> initialized\"}" --json
```

## Task Flow

1. Resolve state root from `SP_TEAMS_STATE_ROOT`, then worker identity/config fallbacks.
2. Read inbox at `<state_root>/team/<teamName>/workers/<workerName>/inbox.md`.
3. Read task file at `<state_root>/team/<teamName>/tasks/task-<id>.json`.
4. Claim before work:

```bash
sp-team claim-task --input "{\"team_name\":\"<teamName>\",\"task_id\":\"<id>\",\"worker\":\"<workerName>\"}" --json
```

5. Complete or fail through lifecycle API, never by directly editing lifecycle fields in task JSON.
6. Use `sp-team release-task-claim` only for rollback/requeue to `pending`.

## Mailbox

Read and acknowledge mailbox messages with:

```bash
sp-team mailbox-list --input "{\"team_name\":\"<teamName>\",\"worker\":\"<workerName>\"}" --json
sp-team mailbox-mark-delivered --input "{\"team_name\":\"<teamName>\",\"worker\":\"<workerName>\",\"message_id\":\"<MESSAGE_ID>\"}" --json
```

## Rules

- Treat `sp-team` as the only supported runtime CLI surface.
- Prefer inbox/mailbox/task state plus `sp-team ... --json` operations.
- If blocked on a shared file, report blocked state and wait instead of freelancing.
