# [PROJECT NAME] Development Guidelines

Auto-generated from all feature plans. Last updated: [DATE]

## Active Technologies

[EXTRACTED FROM ALL PLAN.MD FILES]

## Project Structure

```text
[ACTUAL STRUCTURE FROM PLANS]
```

## Commands

[ONLY COMMANDS FOR ACTIVE TECHNOLOGIES]

## Code Style

[LANGUAGE-SPECIFIC, ONLY FOR LANGUAGES IN USE]

## Recent Changes

[LAST 3 FEATURES AND WHAT THEY ADDED]

## Workflow Recovery Rules

- Treat concurrent feature work as lane-first, not branch-first.
- Resolve resumable workflow targets through durable lane state or explicit feature paths before guessing from the current branch name.
- If a workflow records canonical next-command tokens like `/sp.plan` or `/sp.implement`, normalize them before comparing against bare command names.
- If lane resolution returns a unique safe candidate and a materialized worktree, continue from that isolated worktree context instead of assuming the current workspace is correct.
- Preserve compatibility with legacy feature roots such as `.specify/specs/<feature>/` when recovery logic or generated scripts need to reopen an existing feature package.

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
