# Spec Kit Plus Claude Context

This repository's broader operating guidance lives in [AGENTS.md](./AGENTS.md).
Use that file as the primary source of truth for workflow routing, brownfield
context gates, and repository conventions.

## Lane Recovery Rules

- Treat concurrent feature work as lane-first, not branch-first.
- Do not assume the current branch name is the canonical feature directory slug.
- For resumable `sp-*` commands, resolve the active feature through durable lane
  state or an explicit `feature_dir` before guessing from branch-only context.
- If a workflow command can accept an explicit `feature_dir`, prefer that
  override over current-branch inference.
- If lane resolution returns one safe candidate and a materialized worktree,
  continue from that isolated worktree context instead of the leader workspace.
- Normalize canonical workflow-state tokens such as `/sp.plan`,
  `/sp.deep-research`, `/sp.tasks`, and `/sp.implement` before comparing them
  against bare command names.
- Prefer `.specify/features/<feature>/` as the canonical generated-project
  feature root. Preserve compatibility with legacy feature roots such as
  `specs/<feature>/` and `.specify/specs/<feature>/` during recovery and
  repair flows.
- Do not fail a resumable workflow only because the current branch is not a
  feature branch when explicit `feature_dir` or unique lane recovery already
  identifies the target feature safely.
