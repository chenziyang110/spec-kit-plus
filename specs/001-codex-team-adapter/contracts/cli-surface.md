# Contract: CLI Surface

## Intent

Define the first-release user-facing command contract for the imported Codex team/runtime capability.

## Required contract

1. The official product surface is owned by `specify`, not by `omx`.
2. The first-release surface is exposed only when the integration is `codex`.
3. Unsupported environments must fail visibly and immediately.
4. The first-release runtime loop must support observable bootstrap, dispatch, state tracking, failure signaling, and cleanup.

## Command expectations

- A `specify`-owned team command surface exists for Codex projects.
- A Codex-facing generated skill may call that `specify` command surface.
- `omx` and `$team` are not treated as the official product surface in docs or acceptance criteria.
- Non-Codex integrations do not advertise or install this surface by default.

## Failure contract

- Missing `tmux` returns a clear unsupported-environment result.
- Runtime dispatch failure returns a clear failure result that remains inspectable.
- Cleanup must leave a terminal state that operators can distinguish from active execution.
