# Learning Command-Surface Safety Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make learning-related runtime advice executable or explicitly non-runnable, while aligning templates, docs, and tests to the corrected learning command-surface contract.

**Architecture:** Tighten the learning product surface in four layers. First, lock the desired behavior in hook and template tests. Second, update runtime hook messaging so placeholder commands are never emitted as runnable advice. Third, align workflow templates, passive skill guidance, and quickstart wording to the same contract while resolving `sp-fast` and `sp-quick` inconsistencies. Fourth, run focused regressions to prove the new safety rule and prevent reintroduction.

**Tech Stack:** Python, Typer CLI, pytest, Markdown workflow templates and docs

---

### Task 1: Lock runtime learning advice safety in tests

**Files:**
- Modify: `tests/hooks/test_learning_hooks.py`

- [ ] **Step 1: Write failing tests for non-executable learning actions**

Add tests that assert runtime learning hook actions no longer contain placeholder
command fragments such as `...` or `<...>` when presented as runnable advice.

```python
def test_learning_review_missing_review_does_not_emit_placeholder_capture_command(tmp_path: Path):
    project = _create_project(tmp_path)

    result = run_quality_hook(
        project,
        "workflow.learning.review",
        {"command_name": "implement", "terminal_status": "resolved"},
    )

    assert result.status == "blocked"
    assert all("..." not in action for action in result.actions)
    assert all("<" not in action for action in result.actions)
    assert any("--type" in action for action in result.actions)
    assert any("--summary" in action for action in result.actions)
    assert any("--evidence" in action for action in result.actions)


def test_learning_review_recent_signal_does_not_emit_placeholder_capture_command(tmp_path: Path):
    project = _create_project(tmp_path)

    run_quality_hook(
        project,
        "workflow.learning.signal",
        {
            "command_name": "implement",
            "retry_attempts": 2,
            "hypothesis_changes": 1,
            "validation_failures": 1,
        },
    )

    result = run_quality_hook(
        project,
        "workflow.learning.review",
        {
            "command_name": "implement",
            "terminal_status": "resolved",
            "learning_review": {
                "decision": "none",
                "rationale": "The work eventually completed.",
            },
        },
    )

    assert result.status == "blocked"
    assert all("..." not in action for action in result.actions)
    assert any("--type" in action for action in result.actions)
```

- [ ] **Step 2: Run the focused hook tests to verify RED**

Run: `pytest tests/hooks/test_learning_hooks.py -q`
Expected: FAIL because the current runtime hook actions still contain placeholder
commands with `...`.

- [ ] **Step 3: Commit the failing-test checkpoint**

```bash
git add tests/hooks/test_learning_hooks.py
git commit -m "test: lock learning runtime command-surface safety"
```

### Task 2: Lock template contract consistency in tests

**Files:**
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_command_surface_semantics.py`

- [ ] **Step 1: Write failing template/contract assertions**

Replace placeholder-preserving assertions with consistency checks for the new
contract.

```python
def test_fast_and_quick_learning_contracts_are_self_consistent() -> None:
    fast_content = _read("templates/commands/fast.md")
    quick_content = _read("templates/commands/quick.md")

    assert "Skip all learning hooks" in fast_content
    assert "{{specify-subcmd:learning capture --command fast ...}}" not in fast_content

    assert "Auto-capture learnings on resolution only. No review, no signal." in quick_content
    assert "{{specify-subcmd:hook review-learning --command quick" not in quick_content


def test_learning_docs_use_labeled_command_shapes_instead_of_fake_runnable_commands() -> None:
    quickstart = (PROJECT_ROOT / "docs" / "quickstart.md").read_text(encoding="utf-8")
    learning_skill = (
        PROJECT_ROOT
        / "templates"
        / "passive-skills"
        / "spec-kit-project-learning"
        / "SKILL.md"
    ).read_text(encoding="utf-8")

    assert "Command shape:" in quickstart
    assert "Required options:" in quickstart
    assert "`specify hook review-learning --command <workflow> --terminal-status <resolved|blocked> ...`" not in quickstart
    assert "Command shape:" in learning_skill
    assert "Required options:" in learning_skill
```

- [ ] **Step 2: Run the focused template tests to verify RED**

Run: `pytest tests/test_alignment_templates.py tests/test_command_surface_semantics.py -q`
Expected: FAIL because current templates and docs still preserve placeholder
command forms and `sp-fast` still includes a contradictory learning capture
instruction.

- [ ] **Step 3: Commit the failing-test checkpoint**

```bash
git add tests/test_alignment_templates.py tests/test_command_surface_semantics.py
git commit -m "test: lock learning template command-surface contract"
```

### Task 3: Remove placeholder runtime advice from learning hooks

**Files:**
- Modify: `src/specify_cli/hooks/learning.py`
- Test: `tests/hooks/test_learning_hooks.py`

- [ ] **Step 1: Update hook actions to use executable commands or explicit required-field guidance**

Change blocked/warning learning hook actions so placeholder `capture-learning`
commands are replaced with explanatory guidance that names required options
without pretending to be a shell-ready command.

```python
actions=[
    f"run `specify hook review-learning --command {command_name} --terminal-status {terminal_status} --decision none --rationale \"...\"` when no reusable learning exists",
    "manual learning capture requires `specify hook capture-learning` with `--type`, `--summary`, and `--evidence`",
]
```

and:

```python
actions=[
    "preserve the reusable lesson with `specify hook capture-learning` after supplying `--type`, `--summary`, and `--evidence`",
    f"or rerun `specify hook review-learning --command {command_name} --terminal-status {terminal_status} --decision deferred --rationale \"...\"` when capture must wait",
]
```

- [ ] **Step 2: Run the hook tests to verify GREEN**

Run: `pytest tests/hooks/test_learning_hooks.py -q`
Expected: PASS

- [ ] **Step 3: Commit the runtime hook fix**

```bash
git add src/specify_cli/hooks/learning.py tests/hooks/test_learning_hooks.py
git commit -m "fix: remove fake runnable learning hook commands"
```

### Task 4: Align workflow templates and passive learning guidance

**Files:**
- Modify: `templates/command-partials/common/learning-layer.md`
- Modify: `templates/commands/fast.md`
- Modify: `templates/commands/quick.md`
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/commands/analyze.md`
- Modify: `templates/commands/checklist.md`
- Modify: `templates/commands/clarify.md`
- Modify: `templates/commands/deep-research.md`
- Modify: `templates/commands/constitution.md`
- Modify: `templates/commands/implement.md`
- Modify: `templates/commands/debug.md`
- Modify: `templates/commands/map-scan.md`
- Modify: `templates/commands/map-build.md`
- Modify: `templates/commands/test-scan.md`
- Modify: `templates/commands/test-build.md`
- Modify: `templates/passive-skills/spec-kit-project-learning/SKILL.md`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Rewrite learning command-shape guidance**

For incomplete forms, replace `run ...` style pseudo-commands with explicit
labels such as `Command shape:` and `Required options:`. Remove the contradictory
`sp-fast` capture instruction. Ensure `sp-quick` remains auto-capture-only.

```markdown
- [AGENT] Before final completion or blocked reporting, use the `review-learning`
  helper surface for terminal closeout.
  Command shape: `{{specify-subcmd:hook review-learning --command plan --terminal-status <resolved|blocked> --decision <none|captured|deferred> --rationale "<why>"}}`
- [AGENT] When durable state does not capture the reusable lesson cleanly, use
  the manual `capture-learning` hook surface instead of auto-capture.
  Required options: `--command`, `--type`, `--summary`, `--evidence`
```

For `sp-fast`, remove:

```markdown
- [AGENT] Before the final report, capture any new ... learning through `{{specify-subcmd:learning capture --command fast ...}}`.
```

- [ ] **Step 2: Run the template contract tests to verify GREEN**

Run: `pytest tests/test_alignment_templates.py -q`
Expected: PASS

- [ ] **Step 3: Commit the template guidance cleanup**

```bash
git add templates/command-partials/common/learning-layer.md templates/commands/*.md templates/passive-skills/spec-kit-project-learning/SKILL.md tests/test_alignment_templates.py
git commit -m "fix: align learning workflow template command surfaces"
```

### Task 5: Align public docs and semantic contract tests

**Files:**
- Modify: `docs/quickstart.md`
- Modify: `tests/test_command_surface_semantics.py`

- [ ] **Step 1: Rewrite quickstart learning helper examples as labeled command surfaces**

Keep the helper surface discoverable, but stop presenting incomplete commands as
copy-paste-ready instructions.

```markdown
- `specify hook review-learning`
  Command shape: `specify hook review-learning --command <workflow> --terminal-status <resolved|blocked> --decision <none|captured|deferred> --rationale "<why>"`
- `specify hook capture-learning`
  Required options: `--command`, `--type`, `--summary`, `--evidence`
```

- [ ] **Step 2: Run semantic contract tests to verify GREEN**

Run: `pytest tests/test_command_surface_semantics.py -q`
Expected: PASS

- [ ] **Step 3: Commit the doc/semantic contract fix**

```bash
git add docs/quickstart.md tests/test_command_surface_semantics.py
git commit -m "docs: clarify learning command-surface examples"
```

### Task 6: Run focused regression and verify no learning placeholders remain

**Files:**
- Verify only

- [ ] **Step 1: Run the focused regression suite**

Run:

```bash
pytest tests/hooks/test_learning_hooks.py tests/test_alignment_templates.py tests/test_command_surface_semantics.py -q
```

Expected: PASS

- [ ] **Step 2: Search for remaining learning placeholder command leaks**

Run:

```bash
rg -n "capture-learning --command .*\\.\\.\\.|review-learning --command .*\\.\\.\\.|hook review-learning --command quick|learning capture --command fast" templates docs src/specify_cli tests
```

Expected: no matches in the active learning runtime/templates/docs/tests contract
surfaces except historical design/plan documents.

- [ ] **Step 3: Review diff and commit final verification checkpoint**

```bash
git diff -- src/specify_cli/hooks/learning.py templates/command-partials/common/learning-layer.md templates/commands docs/quickstart.md templates/passive-skills/spec-kit-project-learning/SKILL.md tests/hooks/test_learning_hooks.py tests/test_alignment_templates.py tests/test_command_surface_semantics.py
git commit -m "test: verify learning command-surface safety contract"
```

## Self-Review

- Spec coverage:
  - runtime fake command removal: Task 3
  - template/passive-skill/doc separation of command shape vs executable advice: Tasks 4 and 5
  - `sp-fast` / `sp-quick` contract consistency: Task 4
  - regression enforcement: Tasks 1, 2, and 6
- Placeholder scan:
  - no `TBD`, `TODO`, or unresolved implementation notes remain in this plan
- Type consistency:
  - command names and file paths match the current repository surfaces verified during brainstorming

Plan complete and saved to `docs/superpowers/plans/2026-05-05-learning-command-surface-safety-implementation.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
