# Multi-Agent Task Shaping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tighten task shaping and delegated fail-fast behavior by updating workflow templates, runtime result contracts, and regression tests.

**Architecture:** Keep the existing strategy/routing/runtime model and implement this as a focused refinement layer. First lock the new language in template tests. Then update the task and implementation templates. Next extend the delegated worker result schema plus validator for blocked-result evidence. Finally update docs and run targeted regression tests.

**Tech Stack:** Python, dataclasses, Markdown templates, pytest

---

## File Structure

- Modify: `templates/commands/tasks.md`
  - Add task granularity contract, progressive decomposition stop rule, grouped parallel/pipeline guidance.
- Modify: `templates/tasks-template.md`
  - Mirror the new task-shaping language in the generated sample artifact.
- Modify: `templates/commands/implement.md`
  - Add refinement-at-join-point, review-gate, and pipeline checkpoint guidance plus blocked-result evidence requirements.
- Modify: `src/specify_cli/orchestration/models.py`
  - Add a lightweight typed review-gate policy model.
- Modify: `src/specify_cli/orchestration/policy.py`
  - Add a helper that classifies whether a batch requires a review gate and whether a peer-review lane is recommended.
- Modify: `src/specify_cli/orchestration/__init__.py`
  - Export the new review-gate policy type.
- Modify: `src/specify_cli/execution/result_schema.py`
  - Extend blocked worker result metadata.
- Modify: `src/specify_cli/execution/result_validator.py`
  - Reject blocked results that omit required blocker evidence.
- Modify: `README.md`
  - Document the tightened task-shaping rules at the workflow level.
- Modify: `docs/quickstart.md`
  - Mirror the new guidance in user-facing workflow docs.
- Modify: `tests/test_alignment_templates.py`
  - Add assertions for new template wording.
- Modify: `tests/orchestration/test_policy.py`
  - Cover high-risk review-gate classification.
- Modify: `tests/execution/test_result_validator.py`
  - Cover blocked-result validation.

---

### Task 1: Lock the new task-shaping guidance in tests

**Files:**
- Modify: `tests/test_alignment_templates.py`

- [ ] Add failing assertions for task granularity, progressive decomposition, grouped parallelism, and pipeline checkpoints in the `tasks` and `implement` template tests.
- [ ] Assert that blocked delegated execution now requires concrete blocker evidence in the shared implementation guidance.

### Task 2: Update shared task-generation guidance

**Files:**
- Modify: `templates/commands/tasks.md`
- Modify: `templates/tasks-template.md`

- [ ] Add the top-level versus delegated-worker granularity split.
- [ ] Add the progressive decomposition stop rule for later phases.
- [ ] Add grouped parallelism as default and pipeline guidance for dependency-shaped work.
- [ ] Keep the wording integration-neutral.

### Task 3: Update implementation guidance for refinement and pipeline checkpoints

**Files:**
- Modify: `templates/commands/implement.md`

- [ ] Add join-point-time refinement language so leaders can refine the next executable window after each checkpoint.
- [ ] Add explicit pipeline checkpoint language without changing the canonical strategy names.
- [ ] Add high-risk review-gate language so shared surfaces and protocol seams do not cross join points without acceptance.
- [ ] Add fail-fast blocked-result evidence requirements for delegated workers.

### Task 4: Add shared review-gate policy classification

**Files:**
- Modify: `src/specify_cli/orchestration/models.py`
- Modify: `src/specify_cli/orchestration/policy.py`
- Modify: `src/specify_cli/orchestration/__init__.py`
- Modify: `tests/orchestration/test_policy.py`

- [ ] Add a small typed policy model describing whether a batch requires a review gate and whether a peer-review lane is recommended.
- [ ] Add a helper that marks shared-surface, schema, and boundary-contract batches as review-gated.
- [ ] Keep this helper separate from execution-strategy selection so the canonical strategy names remain unchanged.
- [ ] Cover low-risk and high-risk cases in orchestration policy tests.

### Task 5: Strengthen blocked delegated result validation

**Files:**
- Modify: `src/specify_cli/execution/result_schema.py`
- Modify: `src/specify_cli/execution/result_validator.py`
- Modify: `tests/execution/test_result_validator.py`

- [ ] Extend `WorkerTaskResult` with failed-assumption and recovery-action fields.
- [ ] Reject blocked results that lack blocker summary, failed assumption, or suggested recovery action.
- [ ] Preserve the existing `DP3` failure family.

### Task 6: Update workflow docs

**Files:**
- Modify: `README.md`
- Modify: `docs/quickstart.md`

- [ ] Document the new task-shaping rules where workflow behavior is described.
- [ ] Document that only high-risk batches should add review gates or peer-review lanes.
- [ ] Keep the documentation aligned with the shared template language.

### Task 7: Verify the refinement end-to-end

**Files:**
- Modify only if verification reveals drift

- [ ] Run targeted pytest coverage for template assertions, orchestration policy, and execution result validation.
- [ ] Fix any wording or schema drift exposed by the regression run.
