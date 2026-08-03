# Spec Kit Plus Claude Context

This repository's broader operating guidance lives in [AGENTS.md](./AGENTS.md).
Use that file as the primary source of truth for workflow routing, brownfield
context gates, and repository conventions.

When a task extends, debugs, or refactors an existing capability and the atlas
is fresh enough to trust, read atlas truth in this order:
`symptom -> capability deep workflow -> module workflows -> root workflows`
before broad source search.

## Command Surface Rules

- Treat the live `specify --help` output as the only authoritative CLI command surface.
- Before suggesting or running a `specify <subcommand>` invocation, verify that `specify --help` or `specify <subcommand> --help` exposes it.
- Do not invent, paraphrase, or "normalize" unsupported CLI names such as `specify create-feature`.
- Feature creation must follow `sp-specify` plus the generated create-feature script at `.specify/scripts/bash/create-new-feature.sh` or `.specify/scripts/powershell/create-new-feature.ps1`, not a separate imagined branch-creation command family.

## Run Recovery Rules

- Treat every modifying `sp-*` invocation, including the first, as an independent
  Run with a supervisor-owned Git worktree and private ref.
- When `SPECIFY_RUN_MANAGED=1`, require the current directory to equal
  `SPECIFY_RUN_WORKSPACE`; stop instead of switching worktrees when the binding
  does not match.
- Resolve a feature from an explicit `feature_dir`, then a validated managed Run
  subject, then one unambiguous paths-only helper result. Never infer it from the
  current branch or the Run's private Git ref.
- Never resume an expired or interrupted Attempt directly. The supervisor fences
  it, quarantines its workspace generation, and starts a replacement generation.
- A workflow agent never merges its own private ref. Successful Runs publish an
  immutable Candidate; target-serialized Run integration records the Result.
- Normalize canonical workflow-state tokens such as `/sp.plan`,
  `/sp.deep-research`, `/sp.tasks`, and `/sp.implement` before comparing them
  against bare command names.
- Prefer `.specify/features/<feature>/` as the canonical generated-project
  feature root. Preserve compatibility with legacy feature roots such as
  `specs/<feature>/` and `.specify/specs/<feature>/` during recovery and
  repair flows.
- Do not fail a resumable workflow only because the current branch is not a
  feature branch when an explicit `feature_dir` or the managed Run subject
  identifies the target feature safely.
