# Plan: Stable Passive Team Trigger (Mirroring oh-my-codex)

## Objective
Fix the "passive team agent trigger" issue in `spec-kit-plus` to match the stable behavior of `oh-my-codex`. Ensure the agent team triggers automatically during task execution, analysis, and enhancement without requiring manual commands or overly strict markdown markers.

## Analysis of Discrepancies
1. **Config Location**: Codex CLI expects `notify` hook in `.codex/config.toml`, but we write to `.specify/config.json`.
2. **Batching Logic**: `find_next_ready_parallel_batch` requires explicit `**Parallel Batch**` headers. `oh-my-codex` is likely more flexible or uses intent detection.
3. **Passive Parallelism**: Our `assess_passive_parallelism` is implemented but not hooked into the `notify_hook.py`.
4. **Hook Invocation**: `python -m ...` might fail if the environment is not set up correctly.

## Proposed Changes

### 1. Update Installer (`src/specify_cli/codex_team/installer.py`)
- Also update/create `.codex/config.toml` with the `notify` hook.
- Use a more robust command format for the hook.

### 2. Enhance Auto Dispatch (`src/specify_cli/codex_team/auto_dispatch.py`)
- Improve `find_next_ready_parallel_batch` to automatically group ready tasks with `[P]` markers into a "virtual" parallel batch if no explicit batch header exists.
- Integrate `assess_passive_parallelism` into the routing flow.

### 3. Upgrade Notify Hook (`src/specify_cli/codex_team/notify_hook.py`)
- Inspect the turn payload for "team intent" or "parallelizable work".
- Add logging to help users diagnose why a trigger did or did not happen.

### 4. Improve Integration Logic (`src/specify_cli/integrations/codex/__init__.py`)
- Ensure `setup` correctly calls the new installer logic.

## Implementation Steps

1. **Step 1: Robust Batching**
   - Modify `auto_dispatch.py` to support "Inferred Parallel Batches" from `[P]` markers.
2. **Step 2: Correct Config Registration**
   - Modify `installer.py` to write to `.codex/config.toml`.
3. **Step 3: Intent-aware Hook**
   - Modify `notify_hook.py` to analyze turn content.
4. **Step 4: Verification**
   - Test the hook with a mock payload.
