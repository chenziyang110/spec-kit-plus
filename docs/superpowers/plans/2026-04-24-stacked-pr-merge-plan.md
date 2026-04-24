# Stacked PR Merge Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** safely merge the four stacked AI-agent lifecycle PRs into `main` with minimal review ambiguity, explicit blocker handling, and a deterministic retargeting sequence.

**Architecture:** handle this as two phases. First, clear the shared CI blockers that currently keep every PR in an `UNSTABLE` state. Second, merge the feature stack in dependency order (`PR1 -> PR2 -> PR3 -> PR4`), retargeting each downstream PR to `main` after its parent merges so GitHub diffs collapse to the intended slice.

**Tech Stack:** Git, GitHub CLI (`gh`), GitHub Actions, pytest, Ruff, stacked PR workflow

---

## Current State

As of 2026-04-24, the stack is:

1. `PR1` — [#7](https://github.com/chenziyang110/spec-kit-plus/pull/7)
   - Title: `feat: add learning aggregation workflow`
   - Base: `main`
   - Head: `feature/learning-aggregate-foundation`
   - Files changed:
     - `README.md`
     - `docs/quickstart.md`
     - `src/specify_cli/__init__.py`
     - `src/specify_cli/learning_aggregate.py`
     - `src/specify_cli/learnings.py`
     - `tests/test_learning_aggregate.py`
     - `tests/test_learning_cli.py`
     - `tests/test_specify_guidance_docs.py`

2. `PR2` — [#8](https://github.com/chenziyang110/spec-kit-plus/pull/8)
   - Title: `feat: add intent-aware verification contracts`
   - Base: `feature/learning-aggregate-foundation`
   - Head: `feature/intent-verification-gate`
   - Key surfaces:
     - `src/specify_cli/debug/*`
     - `src/specify_cli/execution/*`
     - `src/specify_cli/verification.py`
     - `templates/commands/{implement,debug,quick}.md`
     - `templates/debug.md`
     - execution/debug/template tests

3. `PR3` — [#9](https://github.com/chenziyang110/spec-kit-plus/pull/9)
   - Title: `feat: add review-gated batch runtime loop`
   - Base: `feature/intent-verification-gate`
   - Head: `feature/review-loop-runtime`
   - Key surfaces:
     - `src/specify_cli/codex_team/auto_dispatch.py`
     - `src/specify_cli/codex_team/runtime_state.py`
     - `src/specify_cli/codex_team/state_paths.py`
     - `src/specify_cli/execution/review_schema.py`
     - `src/specify_cli/orchestration/review_loop.py`
     - `tests/codex_team/test_auto_dispatch.py`
     - `tests/codex_team/test_review_loop.py`

4. `PR4` — [#10](https://github.com/chenziyang110/spec-kit-plus/pull/10)
   - Title: `feat: add durable eval workflow`
   - Base: `feature/review-loop-runtime`
   - Head: `feature/durable-eval-layer`
   - Files changed:
     - `README.md`
     - `docs/quickstart.md`
     - `src/specify_cli/__init__.py`
     - `src/specify_cli/eval_runner.py`
     - `src/specify_cli/evals.py`
     - `tests/test_eval_cli.py`
     - `tests/test_eval_runner.py`
     - `tests/test_specify_guidance_docs.py`

## Shared Merge Blockers

All four PRs currently report `mergeStateStatus=UNSTABLE`.

The failures are not four unrelated feature failures. They are two shared CI blockers:

### Blocker A: shared Ruff failures

Current `ruff` failures visible in CI:

- [src/specify_cli/__init__.py](/F:/github/spec-kit-plus/src/specify_cli/__init__.py:79)
  - unused `worker_task_result_payload` import
- [src/specify_cli/codex_team/auto_dispatch.py](/F:/github/spec-kit-plus/src/specify_cli/codex_team/auto_dispatch.py:16)
  - unused `result_record_path` import
- [src/specify_cli/debug/graph.py](/F:/github/spec-kit-plus/src/specify_cli/debug/graph.py:16)
  - unused `ValidationResult` import
- [src/specify_cli/execution/__init__.py](/F:/github/spec-kit-plus/src/specify_cli/execution/__init__.py:27)
  - duplicate `ValidationResult` import/re-export

These are code hygiene issues, not design issues. They should be fixed before any merge decision.

### Blocker B: Linux-only brittle debug help test

Current CI failure:

- [tests/test_debug_cli.py](/F:/github/spec-kit-plus/tests/test_debug_cli.py:257)
  - `test_debug_help_lists_dispatch_option`

Observed behavior in Linux CI:

- Rich/Typer help rendering contains the dispatch option, but the formatted output tokenizes it as `-dispatch` rather than the literal `--dispatch` substring expected by the test.

Implication:

- This is a test robustness issue, not a product regression in the stacked feature work.
- The test should normalize ANSI/Rich formatting or accept either `-dispatch` or `--dispatch` after de-styling.

## Recommended Merge Strategy

### Phase 0: Land CI Stabilization First

Do **not** start merging the feature stack before clearing the shared CI blockers.

Recommended actions:

- [ ] Create a small `ci-stabilization` branch from `main`
- [ ] Fix the 4 Ruff issues
- [ ] Make `tests/test_debug_cli.py::test_debug_help_lists_dispatch_option` robust to Rich/Typer formatting on Linux
- [ ] Verify with:

```bash
uvx ruff check src/
python -m pytest tests/test_debug_cli.py::test_debug_help_lists_dispatch_option -q
python -m pytest
```

- [ ] Merge the CI stabilization patch into `main`

Why first:

- Without this, every stacked PR remains red for reasons unrelated to the review content.
- Reviewers will waste time re-evaluating known CI noise instead of the real feature slices.

### Phase 1: Merge PR1

Target PR:

- [#7](https://github.com/chenziyang110/spec-kit-plus/pull/7)

Review focus:

- `learning_aggregate.py` API shape
- `learnings.py` summary additions
- `specify learning aggregate` CLI ergonomics
- documentation wording

Risk profile:

- Low
- Mostly additive
- No runtime coordination changes

Required checks after CI stabilization lands:

- [ ] Update branch from latest `main`
- [ ] Re-run GitHub checks
- [ ] Review that `learning aggregate` still writes only to `.planning/learnings/reports/` and does not fork storage into a new directory hierarchy

Merge command if operating by CLI:

```bash
gh pr merge 7 --merge --delete-branch=false
```

### Phase 2: Retarget PR2 To `main`

After PR1 merges:

- [ ] Retarget PR2 base to `main`

```bash
gh pr edit 8 --base main
```

- [ ] Wait for GitHub to recompute the diff and rerun checks

### Phase 3: Merge PR2

Target PR:

- [#8](https://github.com/chenziyang110/spec-kit-plus/pull/8)

Review focus:

- `ExecutionIntent` contract in `packet_schema.py`
- packet validation strictness changes
- shared `verification.py` semantics
- debug persistence additions
- template contract alignment for `implement`, `debug`, and `quick`

Risk profile:

- Medium-high
- Schema changes plus debug execution flow updates

Required checks:

- [ ] Confirm packet round-trip and result validation tests still pass
- [ ] Confirm debug session persistence remains backward-compatible for unknown fields
- [ ] Confirm template assertions cover the new execution-intent semantics

Merge command:

```bash
gh pr merge 8 --merge --delete-branch=false
```

### Phase 4: Retarget PR3 To `main`

After PR2 merges:

- [ ] Retarget PR3 base to `main`

```bash
gh pr edit 9 --base main
```

- [ ] Wait for GitHub to recompute the diff and rerun checks

### Phase 5: Merge PR3

Target PR:

- [#9](https://github.com/chenziyang110/spec-kit-plus/pull/9)

Review focus:

- `review_required`, `review_status`, and `review_round` semantics in `BatchRecord`
- `auto_dispatch.py` state transitions
- `complete_dispatched_batch()` behavior for review-gated batches
- `review_loop.py` classification and fix-plan behavior

Risk profile:

- Medium
- Runtime behavior changes, but bounded to batch lifecycle and state records

Required checks:

- [ ] Confirm high-risk batches now stop at `awaiting_review`
- [ ] Confirm join points remain `review_pending` until review is recorded
- [ ] Confirm low-risk batches still complete normally

Merge command:

```bash
gh pr merge 9 --merge --delete-branch=false
```

### Phase 6: Retarget PR4 To `main`

After PR3 merges:

- [ ] Retarget PR4 base to `main`

```bash
gh pr edit 10 --base main
```

- [ ] Wait for GitHub to recompute the diff and rerun checks

### Phase 7: Merge PR4

Target PR:

- [#10](https://github.com/chenziyang110/spec-kit-plus/pull/10)

Review focus:

- `.specify/evals/` storage shape
- `eval create|status|run` CLI behavior
- default inference from project learning/rule memory
- method-specific default expectations for `rule-check`, `file-check`, `grep-check`, `command-check`

Risk profile:

- Low-medium
- Additive storage and CLI surface

Required checks:

- [ ] Confirm `.specify/evals/index.json` and `cases/*.md` stay deterministic
- [ ] Confirm `eval create` works both from explicit arguments and inferred learning/rule sources
- [ ] Confirm `eval run` updates `last_run` / `last_result`

Merge command:

```bash
gh pr merge 10 --merge --delete-branch=false
```

## Post-Merge Cleanup

Only after the full stack is merged and all downstream PRs have been retargeted or closed:

- [ ] Delete merged feature branches from GitHub
- [ ] Remove local worktrees:

```bash
git worktree remove "C:/Users/11034/.config/superpowers/worktrees/spec-kit-plus/learning-aggregate-foundation"
git worktree remove "C:/Users/11034/.config/superpowers/worktrees/spec-kit-plus/intent-verification-gate"
git worktree remove "C:/Users/11034/.config/superpowers/worktrees/spec-kit-plus/review-loop-runtime"
git worktree remove "C:/Users/11034/.config/superpowers/worktrees/spec-kit-plus/durable-eval-layer"
```

- [ ] Confirm `main` is clean locally:

```bash
git checkout main
git pull
python -m pytest
uvx ruff check src/
```

## Reviewer Checklist

For every PR in the stack:

- [ ] Is the diff still limited to the intended slice after retargeting?
- [ ] Are schema additions matched by serializer/parser tests?
- [ ] Are template changes backed by contract tests?
- [ ] Are runtime-state transitions covered by tests, not just prompt text?
- [ ] Is any CI failure still a known shared blocker rather than a new regression?

## Final Recommendation

Recommended real merge order:

1. CI stabilization patch to `main`
2. PR1 `#7`
3. PR2 `#8`
4. PR3 `#9`
5. PR4 `#10`

Do **not** collapse the stack into one merge unless review bandwidth is severely constrained. The current slicing is good:

- `PR1` establishes learning aggregation
- `PR2` establishes intent-aware verification contracts
- `PR3` establishes review-gated runtime batch semantics
- `PR4` establishes durable eval storage and execution

That sequence preserves architectural clarity and keeps rollback surface manageable.
