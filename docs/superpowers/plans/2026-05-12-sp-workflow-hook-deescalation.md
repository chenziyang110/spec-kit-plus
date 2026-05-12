# sp Workflow Hook Deescalation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove routine first-party hook choreography from generated `sp-*` workflow guidance while keeping the hook runtime available for compatibility, diagnostics, tests, and native adapters.

**Architecture:** Change the contract at the prompt/documentation boundary first: tests should assert the absence of routine hook commands and the presence of durable outcome requirements. Then update command templates, passive skills, integration-injected guidance, and public docs to describe state, artifact, packet, result, learning, and project cognition requirements without telling agents to run `specify hook ...` during normal `sp-*` execution. Keep `src/specify_cli/hooks/**` and hook CLI behavior intact except for optional wording cleanup in hook-produced messages.

**Tech Stack:** Python 3.13, Typer CLI, pytest, Markdown templates, generated integration projection helpers.

---

## File Structure

**Design/spec reference**
- Read: `docs/superpowers/specs/2026-05-12-sp-workflow-hook-deescalation-design.md`

**Template surfaces**
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/commands/analyze.md`
- Modify: `templates/commands/deep-research.md`
- Modify: `templates/commands/constitution.md`
- Modify: `templates/commands/implement.md`
- Modify: `templates/commands/quick.md`
- Modify: `templates/commands/debug.md`
- Modify: `templates/commands/fast.md`
- Modify: `templates/commands/clarify.md`
- Modify: `templates/commands/checklist.md`
- Modify: `templates/commands/map-scan.md`
- Modify: `templates/commands/map-build.md`
- Modify: `templates/commands/test-scan.md`
- Modify: `templates/commands/test-build.md`
- Modify: `templates/command-partials/common/learning-layer.md`
- Modify: `templates/passive-skills/spec-kit-project-learning/SKILL.md`
- Modify if search shows hook command text: `templates/passive-skills/subagent-driven-development/SKILL.md`
- Modify if search shows hook command text: `templates/passive-skills/dispatching-parallel-agents/SKILL.md`

**Integration projection surfaces**
- Modify: `src/specify_cli/integrations/base.py`
- Do not modify native adapter internals unless a failing test proves generated prompt guidance still leaks through them: `src/specify_cli/integrations/claude/hooks/claude-hook-dispatch.py`, `src/specify_cli/integrations/gemini/hooks/gemini-hook-dispatch.py`

**Docs**
- Modify: `README.md`
- Modify: `docs/quickstart.md`
- Modify if tests fail or search shows workflow-facing hook guidance: `PROJECT-HANDBOOK.md`

**Tests**
- Modify: `tests/test_hook_template_guidance.py`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_passive_skill_guidance.py`
- Modify: `tests/test_quick_template_guidance.py`
- Modify: `tests/test_command_surface_semantics.py`
- Modify only if exact projection assertions fail: `tests/integrations/test_integration_codex.py`, `tests/integrations/test_integration_base_markdown.py`, `tests/integrations/test_integration_base_skills.py`, `tests/integrations/test_integration_base_toml.py`

---

### Task 1: Replace Hook-Presence Tests With Hook-Deescalation Tests

**Files:**
- Modify: `tests/test_hook_template_guidance.py`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_passive_skill_guidance.py`
- Modify: `tests/test_quick_template_guidance.py`
- Modify: `tests/test_command_surface_semantics.py`

- [ ] **Step 1: Rewrite `tests/test_hook_template_guidance.py` to assert absence of routine hook choreography**

Replace the current positive hook assertions with focused negative assertions and outcome checks. Use helper lists so later failures name the offending file.

```python
from pathlib import Path

from .template_utils import read_template


PROJECT_ROOT = Path(__file__).resolve().parent.parent

ROUTINE_HOOK_FRAGMENTS = (
    "{{specify-subcmd:hook preflight",
    "{{specify-subcmd:hook validate-state",
    "{{specify-subcmd:hook validate-artifacts",
    "{{specify-subcmd:hook checkpoint",
    "{{specify-subcmd:hook monitor-context",
    "{{specify-subcmd:hook workflow-policy",
    "{{specify-subcmd:hook build-compaction",
    "{{specify-subcmd:hook render-statusline",
    "{{specify-subcmd:hook validate-read-path",
    "{{specify-subcmd:hook validate-prompt",
    "{{specify-subcmd:hook signal-learning",
    "{{specify-subcmd:hook review-learning",
    "{{specify-subcmd:hook capture-learning",
    "{{specify-subcmd:hook inject-learning",
    "{{specify-subcmd:hook mark-dirty",
    "{{specify-subcmd:hook complete-refresh",
)

CORE_WORKFLOW_TEMPLATES = (
    "templates/commands/specify.md",
    "templates/commands/plan.md",
    "templates/commands/tasks.md",
    "templates/commands/analyze.md",
    "templates/commands/deep-research.md",
    "templates/commands/constitution.md",
    "templates/commands/implement.md",
    "templates/commands/quick.md",
    "templates/commands/debug.md",
    "templates/commands/fast.md",
    "templates/commands/clarify.md",
    "templates/commands/checklist.md",
    "templates/commands/map-scan.md",
    "templates/commands/map-build.md",
    "templates/commands/test-scan.md",
    "templates/commands/test-build.md",
)


def _assert_no_routine_hook_choreography(path: str) -> None:
    content = read_template(path)
    for fragment in ROUTINE_HOOK_FRAGMENTS:
        assert fragment not in content, f"{path} still contains routine hook choreography: {fragment}"


def test_command_templates_do_not_instruct_routine_hook_choreography() -> None:
    for path in CORE_WORKFLOW_TEMPLATES:
        _assert_no_routine_hook_choreography(path)


def test_planning_templates_preserve_state_and_artifact_outcome_requirements() -> None:
    expected = {
        "templates/commands/specify.md": ("workflow-state.md", "spec.md", "alignment.md", "context.md"),
        "templates/commands/plan.md": ("workflow-state.md", "plan.md"),
        "templates/commands/tasks.md": ("workflow-state.md", "tasks.md"),
        "templates/commands/analyze.md": ("workflow-state.md",),
        "templates/commands/deep-research.md": ("workflow-state.md", "deep-research.md"),
        "templates/commands/constitution.md": ("workflow-state.md", ".specify/memory/constitution.md"),
    }

    for path, fragments in expected.items():
        content = read_template(path)
        for fragment in fragments:
            assert fragment in content, f"{path} lost durable outcome requirement: {fragment}"
        lowered = content.lower()
        assert "state" in lowered
        assert "artifact" in lowered or path.endswith("constitution.md")


def test_execution_templates_preserve_contract_outcomes_without_hook_commands() -> None:
    implement = read_template("templates/commands/implement.md")
    quick = read_template("templates/commands/quick.md")
    debug = read_template("templates/commands/debug.md")

    assert "WorkerTaskPacket" in implement
    assert "WorkerTaskResult" in implement
    assert "Dispatch only from validated `WorkerTaskPacket`" in implement
    assert "structured handoff" in implement
    assert "project-map complete-refresh" in implement
    assert "project-map mark-dirty" in implement

    assert "STATUS.md" in quick
    assert "WorkerTaskPacket" in quick
    assert "structured handoff" in quick
    assert "project-map complete-refresh" in quick
    assert "project-map mark-dirty" in quick

    assert "debug session" in debug.lower()
    assert "evidence" in debug.lower()
    assert "project-map complete-refresh" in debug
    assert "project-map mark-dirty" in debug
```

- [ ] **Step 2: Update learning assertions in `tests/test_alignment_templates.py`**

Replace `test_core_sp_templates_use_learning_review_hooks` with a direct-learning version. Keep the existing helper imports and `_read`.

```python
def test_core_sp_templates_use_direct_passive_learning_without_hook_gates():
    learning_layer = _read("templates/command-partials/common/learning-layer.md")
    assert ".specify/memory/learnings/INDEX.md" in learning_layer
    assert "Learning Reflex" in learning_layer
    assert "detail document" in learning_layer
    assert "{{specify-subcmd:hook" not in learning_layer
    assert "learning capture-auto" in learning_layer

    command_templates = {
        "specify": "templates/commands/specify.md",
        "clarify": "templates/commands/clarify.md",
        "deep-research": "templates/commands/deep-research.md",
        "plan": "templates/commands/plan.md",
        "tasks": "templates/commands/tasks.md",
        "analyze": "templates/commands/analyze.md",
        "test-scan": "templates/commands/test-scan.md",
        "test-build": "templates/commands/test-build.md",
        "implement": "templates/commands/implement.md",
        "debug": "templates/commands/debug.md",
        "map-scan": "templates/commands/map-scan.md",
        "map-build": "templates/commands/map-build.md",
    }

    for template_path in command_templates.values():
        content = _read(template_path)
        assert "{{specify-subcmd:hook signal-learning" not in content
        assert "{{specify-subcmd:hook review-learning" not in content
        assert "{{specify-subcmd:hook capture-learning" not in content
        assert "Learning Reflex" in content
        assert ".specify/memory/learnings/INDEX.md" in content

    quick_content = _read("templates/commands/quick.md")
    assert "{{specify-subcmd:hook review-learning --command quick" not in quick_content
    assert ".specify/memory/learnings/INDEX.md" in quick_content
    assert "Learning Reflex" in quick_content
    assert "detail document" in quick_content

    fast_content = _read("templates/commands/fast.md")
    assert ".specify/memory/learnings/INDEX.md" in fast_content
    assert "Learning Reflex" in fast_content
    assert "detail document" in fast_content
    assert "{{specify-subcmd:learning capture --command fast ...}}" not in fast_content
```

- [ ] **Step 3: Update project-learning passive skill assertions in `tests/test_alignment_templates.py`**

Replace `test_project_learning_skill_documents_product_level_hooks` with:

```python
def test_project_learning_skill_documents_direct_learning_helpers_not_hook_gates():
    content = _read("templates/passive-skills/spec-kit-project-learning/SKILL.md")

    assert "Direct Learning Helpers" in content
    assert "learning start" in content
    assert "learning capture-auto" in content
    assert "{{specify-subcmd:hook signal-learning" not in content
    assert "{{specify-subcmd:hook review-learning" not in content
    assert "{{specify-subcmd:hook capture-learning" not in content
    assert "{{specify-subcmd:hook inject-learning" not in content
    assert "tooling_trap" in content
    assert "map_coverage_gap" in content
    assert "Do NOT" in content
```

- [ ] **Step 4: Update constitution hook assertions in `tests/test_alignment_templates.py`**

In `test_constitution_template_uses_current_shared_context_and_reentry_contract`, replace these three assertions:

```python
assert "{{specify-subcmd:hook validate-state --command constitution --feature-dir \"$feature_dir\"}}" in lowered
assert "{{specify-subcmd:hook validate-artifacts --command constitution --feature-dir \"$feature_dir\"}}" in lowered
assert "{{specify-subcmd:hook checkpoint --command constitution --feature-dir \"$feature_dir\"}}" in lowered
```

with:

```python
assert "{{specify-subcmd:hook" not in lowered
assert "keep `workflow-state.md` current" in lowered
assert "verify the constitution artifact set" in lowered
assert "update durable state before handoff" in lowered
```

- [ ] **Step 5: Update project cognition dirty fallback assertions**

In `tests/test_alignment_templates.py`, replace the `stale_normal_path_phrases` entry:

```python
"prefer `{{specify-subcmd:hook mark-dirty --reason \"<reason>\"}}` as the shared dirty-mark path",
```

with:

```python
"prefer `project-map mark-dirty` as the shared dirty-mark path",
```

In `tests/test_quick_template_guidance.py`, replace:

```python
assert "use `{{specify-subcmd:hook mark-dirty --reason \"<reason>\"}}` as the manual override/fallback" in content
```

with:

```python
assert "use `project-map mark-dirty` as the manual override/fallback" in content
```

- [ ] **Step 6: Update passive skill guidance assertions**

In `tests/test_passive_skill_guidance.py`, replace these assertions:

```python
assert "hook review-learning --command <command-name>" in content
assert "command shape: `{{specify-subcmd:hook capture-learning --command <command-name>" in content
```

with:

```python
assert "learning capture-auto --command implement --feature-dir" in content
assert "hook review-learning --command <command-name>" not in content
assert "{{specify-subcmd:hook capture-learning" not in content
```

- [ ] **Step 7: Update README/quickstart command surface assertions**

In `tests/test_command_surface_semantics.py`, update `test_readme_and_quickstart_label_remaining_helper_command_shapes` so it no longer expects hook dirty guidance:

```python
assert "command shape: `specify hook mark-dirty --reason " not in readme
assert "command shape: `specify project-map mark-dirty --reason " in readme
assert "command shape: `specify project-cognition mark-dirty --reason " in readme
```

Also add an assertion to `test_readme_and_quickstart_label_workflow_hook_helper_surfaces_as_command_shapes`:

```python
assert "normal `sp-*` workflow steps should not call `specify hook" in readme
assert "normal `sp-*` workflow steps should not call `specify hook" in quickstart
```

- [ ] **Step 8: Run the focused tests and confirm they fail for the intended reason**

Run:

```powershell
pytest tests/test_hook_template_guidance.py tests/test_alignment_templates.py::test_core_sp_templates_use_direct_passive_learning_without_hook_gates tests/test_alignment_templates.py::test_project_learning_skill_documents_direct_learning_helpers_not_hook_gates tests/test_alignment_templates.py::test_constitution_template_uses_current_shared_context_and_reentry_contract tests/test_passive_skill_guidance.py::test_project_learning_focuses_on_memory_triggers_storage_and_promotion tests/test_quick_template_guidance.py::test_quick_template_refreshes_project_cognition_when_truth_surfaces_change tests/test_command_surface_semantics.py::test_readme_and_quickstart_label_workflow_hook_helper_surfaces_as_command_shapes tests/test_command_surface_semantics.py::test_readme_and_quickstart_label_remaining_helper_command_shapes -q
```

Expected: FAIL because templates and docs still contain routine `{{specify-subcmd:hook ...}}` guidance and old learning hook sections.

- [ ] **Step 9: Commit failing tests**

```powershell
git add tests/test_hook_template_guidance.py tests/test_alignment_templates.py tests/test_passive_skill_guidance.py tests/test_quick_template_guidance.py tests/test_command_surface_semantics.py
git commit -m "test: expect sp workflow hook deescalation"
```

---

### Task 2: Remove Routine Hook Choreography From Command Templates

**Files:**
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/commands/analyze.md`
- Modify: `templates/commands/deep-research.md`
- Modify: `templates/commands/constitution.md`
- Modify: `templates/commands/implement.md`
- Modify: `templates/commands/quick.md`
- Modify: `templates/commands/debug.md`
- Modify: `templates/commands/fast.md`
- Modify: `templates/commands/clarify.md`
- Modify: `templates/commands/checklist.md`
- Modify: `templates/commands/map-scan.md`
- Modify: `templates/commands/map-build.md`
- Modify: `templates/commands/test-scan.md`
- Modify: `templates/commands/test-build.md`

- [ ] **Step 1: Replace first-party hook sections in planning templates**

In `templates/commands/specify.md`, replace the section headed:

```markdown
**Run first-party workflow quality hooks once `FEATURE_DIR` is known**:
```

and its four hook bullets with:

```markdown
**Maintain workflow quality without hook choreography**:
- Confirm project cognition and workflow-entry prerequisites before deeper workflow execution so stale or invalid entry conditions are surfaced early.
- After `WORKFLOW_STATE_FILE` is created or resumed, keep `workflow-state.md` current with `active_command: sp-specify`, the current phase, authoritative files, allowed writes, forbidden actions, and the next handoff.
- Before final handoff, verify that `spec.md`, `alignment.md`, `context.md`, and `workflow-state.md` exist and match this workflow's output contract.
- Update durable state before compaction-risk transitions or after major artifact synthesis so another session can resume from files instead of chat history.
```

Apply the same pattern to:

`templates/commands/plan.md`:

```markdown
**Maintain workflow quality without hook choreography**:
- Confirm project cognition and workflow-entry prerequisites before deeper planning so stale brownfield routing or invalid entry conditions are handled early.
- After `WORKFLOW_STATE_FILE` is created or resumed, keep `workflow-state.md` aligned with the `sp-plan` contract and current planning phase.
- Before final handoff, verify that the minimum plan artifact set exists and matches the plan output contract.
- Update durable state before compaction-risk transitions or after large planning artifact synthesis.
```

`templates/commands/tasks.md`:

```markdown
**Maintain workflow quality without hook choreography**:
- Confirm project cognition and workflow-entry prerequisites before decomposition continues.
- After `WORKFLOW_STATE_FILE` is created or resumed, keep `workflow-state.md` aligned with the `sp-tasks` contract and current task-generation phase.
- Before final handoff, verify that `tasks.md` and `workflow-state.md` exist and match this workflow's output contract.
- Update durable state before compaction-risk transitions or after major task-batch synthesis.
```

`templates/commands/analyze.md`:

```markdown
## Workflow Quality Requirements

- Once `FEATURE_DIR` is known, confirm stale brownfield routing, invalid workflow entry, and required upstream artifacts before deeper analysis.
- After `WORKFLOW_STATE_FILE` is created or resumed, keep `workflow-state.md` aligned with the `sp-analyze` contract.
- Before final gate reporting, verify the required analyze-side artifact set from durable files rather than chat narration.
- Update durable state before compaction-risk transitions or after large findings synthesis.
```

`templates/commands/deep-research.md`:

```markdown
**Maintain workflow quality without hook choreography**:
- Confirm stale brownfield routing, invalid workflow entry, and required upstream artifacts before deeper research.
- After `WORKFLOW_STATE_FILE` is created or resumed, keep `workflow-state.md` aligned with the `sp-deep-research` contract.
- Before final handoff, verify that `deep-research.md` and `workflow-state.md` exist and match this workflow's output contract.
- Update durable state before compaction-risk transitions or after prototype evidence is synthesized.
```

`templates/commands/constitution.md`:

```markdown
**Maintain workflow quality without hook choreography**:
- Keep `workflow-state.md` current with `active_command: sp-constitution`, `phase_mode: planning-only`, authoritative files, allowed writes, forbidden actions, and next handoff.
- Verify the constitution artifact set before final handoff, including `.specify/memory/constitution.md`, affected templates, and downstream state notes.
- Update durable state before handoff so later `sp-specify`, `sp-plan`, `sp-tasks`, or `sp-analyze` work can resume without relying on chat memory.
```

- [ ] **Step 2: Replace execution hook sections**

In `templates/commands/implement.md`, replace the section headed:

```markdown
**Run first-party workflow quality hooks once `FEATURE_DIR` is known**:
```

and all hook bullets through the project cognition dirty/fresh bullet with:

```markdown
**Maintain workflow quality without hook choreography**:
- Before execution, confirm project cognition freshness, analyze-gate readiness, and valid execution entry from durable files.
- After `implement-tracker.md` is created or resumed, keep it current and resumable before choosing the next batch.
- Before choosing the next batch, compare `workflow-state.md` and `implement-tracker.md` so execution state does not silently disagree with planning state.
- Before subagent dispatch, compile a `WorkerTaskPacket` or equivalent execution contract that includes objective, authoritative inputs, read scope, write scope, forbidden drift, validation checks, and done criteria.
- Before accepting a subagent handoff at a join point, require structured result evidence compatible with the shared `WorkerTaskResult` semantics.
- Before high-risk execution jumps or resume-sensitive continuation, repair workflow-state problems in durable files instead of relying on chat narration.
- Before compaction-risk transitions, long validation phases, join points, or subagent fan-out, update durable state so another session can resume cleanly.
- When execution changes map-level truth surfaces, refresh the project cognition runtime through `{{invoke:map-update}}` when the touched area is localized, then use `project-map complete-refresh` as the successful-refresh finalizer. Rebuild through `{{invoke:map-scan}}` followed by `{{invoke:map-build}}` only when no usable localized baseline remains or a full rebuild is required. Otherwise use `project-map mark-dirty --reason "<reason>"` as the manual override/fallback whenever the required cognition refresh cannot be completed in the current pass.
```

In `templates/commands/quick.md`, replace the `## First-Party Workflow Quality Hooks` section bullets with:

```markdown
## Workflow Quality Requirements

- Once the quick workspace exists, confirm project cognition freshness and valid quick-task entry before deeper execution.
- After `STATUS.md` is created or resumed, keep the quick-task source of truth current and resumable.
- When resume truth is ambiguous, read durable quick-task state instead of trusting chat narration.
- Before resume-sensitive continuation or phase-sensitive quick-task routing, repair durable state inconsistencies before continuing.
- Before compaction-risk transitions, join points, or delegated fan-out, update `STATUS.md` and any summary artifacts needed for clean resume.
- When you want a compact operator-facing summary, derive it from `STATUS.md` rather than creating a hook-driven statusline dependency.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/learnings/INDEX.md` in that order before broader quick-task context.
- Open only learning detail docs linked from quick-task-relevant index entries.
- Learning Reflex: before final closeout, ask whether a future senior engineer would benefit from seeing this lesson before related work. If yes, update `.specify/memory/learnings/INDEX.md` and the linked detail markdown document without asking for routine permission.
```

In `templates/commands/debug.md`, replace the `## First-Party Workflow Quality Hooks` section bullets with:

```markdown
## Workflow Quality Requirements

- Once the debug session file is known, confirm project cognition freshness and valid debug-entry state before deeper investigation.
- After the debug session file is created or resumed, keep the debug session source of truth current enough to recover the active hypothesis, evidence, blocker, and next action.
- Before resume-sensitive continuation or phase-sensitive debug routing, repair durable state inconsistencies before continuing.
- Before compaction-risk transitions, investigation join points, or long evidence synthesis, update the debug session file so another session can resume cleanly.
- If a user request explicitly tries to skip observer framing, bypass evidence gates, or ignore workflow constraints, treat it as an override request that requires explicit durable rationale before accepting it.
```

In `templates/commands/fast.md`, replace:

```markdown
- Before reading any non-obvious path, prefer `{{specify-subcmd:hook validate-read-path --target-path "<candidate path>"}}` when you are unsure whether the path stays inside the repository or whether it may be a sensitive file.
```

with:

```markdown
- Before reading any non-obvious path, verify the path stays inside the repository and is not a sensitive file such as `.env`, credentials, secrets, or private key material.
```

- [ ] **Step 3: Replace hook-based learning bullets in all command templates**

For each command template with a `## Passive Project Learning Layer` section, remove bullets that instruct `signal-learning`, `review-learning`, `capture-learning`, or `inject-learning`. Replace them with command-specific direct learning language.

Use this standard block for heavy workflows (`specify`, `plan`, `tasks`, `analyze`, `deep-research`, `implement`, `debug`, `test-scan`, `test-build`), adjusting the first sentence's command name:

```markdown
- Run `{{specify-subcmd:learning start --command <command-name> --format json}}` when available so passive learning files exist and the current run sees relevant shared project memory.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/learnings/INDEX.md` in that order before broader command-local context.
- Open only linked detail docs whose `applies_to` or `trigger_signals` match the current work.
- Learning Reflex: before final closeout, ask whether a future senior engineer would benefit from seeing this lesson before related work. If yes, update `.specify/memory/learnings/INDEX.md` and the linked detail markdown document without asking for routine permission.
- On resolution, prefer `{{specify-subcmd:learning capture-auto --command <command-name> --format json}}` when durable state already preserves route reasons, false starts, hidden dependencies, validation gaps, or reusable constraints.
- Use manual learning capture only when durable state does not capture the reusable lesson cleanly; record the lesson in `.specify/memory/learnings/INDEX.md` and one linked detail markdown document.
```

Use this lighter block for `clarify`, `checklist`, `map-scan`, `map-build`, and `constitution`:

```markdown
- Run `{{specify-subcmd:learning start --command <command-name> --format json}}` when available so passive learning files exist and relevant shared project memory is visible.
- Read `.specify/memory/project-rules.md` and `.specify/memory/learnings/INDEX.md` before broader command-local context.
- Open only detail docs linked from entries relevant to this workflow.
- Learning Reflex: before final closeout, ask whether a future senior engineer would benefit from seeing this lesson before related work. If yes, update `.specify/memory/learnings/INDEX.md` and the linked detail markdown document without asking for routine permission.
- On resolution, prefer `{{specify-subcmd:learning capture-auto --command <command-name> --format json}}` when durable state already preserves route reasons, false starts, hidden dependencies, validation gaps, or reusable constraints.
- Use manual learning capture only when durable state does not capture the reusable lesson cleanly; record the lesson in `.specify/memory/learnings/INDEX.md` and one linked detail markdown document.
```

For `quick`, keep the existing memory reads but ensure no hook command remains. For `fast`, keep trivial-tier behavior: no learning command unless the task escalates or exposes reusable project memory.

- [ ] **Step 4: Replace project cognition hook aliases in command templates**

Search:

```powershell
rg -n "{{specify-subcmd:hook (mark-dirty|complete-refresh)|hook mark-dirty|hook complete-refresh" templates/commands
```

Replace every workflow-facing occurrence with public command wording:

- `{{specify-subcmd:hook complete-refresh}}` -> `project-map complete-refresh`
- `{{specify-subcmd:hook mark-dirty --reason "<reason>"}}` -> `project-map mark-dirty --reason "<reason>"`

Use prose instead of runnable placeholder syntax unless the surrounding section is explicitly a command-shape reference. Example replacement for `templates/commands/clarify.md`:

```markdown
if this repair pass proves the current project cognition runtime no longer captures the touched area's ownership, workflow, integration boundary, or verification surface accurately enough, treat git-baseline freshness in `.specify/project-map/index/status.json` as the truth source; if a full refresh can be completed now, run `{{invoke:map-scan}}` followed by `{{invoke:map-build}}` and `project-map complete-refresh` as the successful-refresh finalizer, otherwise use `project-map mark-dirty --reason "<reason>"` as the manual override/fallback before later brownfield implementation proceeds
```

- [ ] **Step 5: Run hook-choreography search against templates**

Run:

```powershell
rg -n "{{specify-subcmd:hook|hook preflight|hook validate|hook checkpoint|hook workflow-policy|hook monitor-context|hook signal-learning|hook review-learning|hook capture-learning|hook inject-learning|hook mark-dirty|hook complete-refresh|hook render-statusline|hook validate-read-path|hook validate-prompt|hook build-compaction" templates/commands templates/command-partials templates/passive-skills
```

Expected: no results in `templates/commands/**`, `templates/command-partials/**`, or passive skills, except historical explanatory text that is not generated workflow instruction. Prefer zero results.

- [ ] **Step 6: Run focused tests**

Run:

```powershell
pytest tests/test_hook_template_guidance.py tests/test_alignment_templates.py::test_core_sp_templates_use_direct_passive_learning_without_hook_gates tests/test_alignment_templates.py::test_constitution_template_uses_current_shared_context_and_reentry_contract tests/test_quick_template_guidance.py::test_quick_template_refreshes_project_cognition_when_truth_surfaces_change -q
```

Expected: PASS for hook-template and updated alignment tests. If failures name exact missing outcome phrases, update template wording rather than reintroducing hook commands.

- [ ] **Step 7: Commit template deescalation**

```powershell
git add templates/commands templates/command-partials templates/passive-skills tests/test_hook_template_guidance.py tests/test_alignment_templates.py tests/test_quick_template_guidance.py
git commit -m "fix: remove hook choreography from sp workflow templates"
```

---

### Task 3: Deescalate Passive Learning Skill and Shared Learning Partial

**Files:**
- Modify: `templates/command-partials/common/learning-layer.md`
- Modify: `templates/passive-skills/spec-kit-project-learning/SKILL.md`
- Modify: `tests/test_passive_skill_guidance.py`
- Modify: `tests/test_command_surface_semantics.py`

- [ ] **Step 1: Replace hook mentions in `templates/command-partials/common/learning-layer.md`**

Replace the Tier table and tier bullets only where they mention hook signaling. The final Tier: heavy section should contain:

```markdown
### Tier: heavy
- Run `{{specify-subcmd:learning start}}` with the current command name so shared memory and relevant detail refs are visible.
- Read `.specify/memory/constitution.md`, `.specify/memory/project-rules.md`, and `.specify/memory/learnings/INDEX.md` in that order before broader command-local context.
- Open only linked detail docs whose `applies_to` or `trigger_signals` match the current work.
- Before final completion or blocked reporting, perform learning closeout: capture or merge an index/detail lesson when future reuse is plausible, or explicitly decide the run was one-off.
- Prefer `{{specify-subcmd:learning capture-auto}}` when durable state already preserves route reasons, false starts, hidden dependencies, validation gaps, or reusable constraints.
- Use manual memory edits only when durable state does not capture the lesson cleanly: update `.specify/memory/learnings/INDEX.md` and one linked detail markdown document.
- Promote to `project-rules.md` or constitution only after recurrence, explicit user confirmation, or stable cross-workflow governance value.
```

- [ ] **Step 2: Replace `First-Party Learning Hooks` in `templates/passive-skills/spec-kit-project-learning/SKILL.md`**

Find the section headed `First-Party Learning Hooks` and replace it with:

```markdown
## Direct Learning Helpers

Use direct learning helpers for low-noise memory lifecycle work. Do not turn ordinary workflow closeout into hook choreography.

- `{{specify-subcmd:learning start}}`
  - Command shape: `{{specify-subcmd:learning start --command <command-name> --format json}}`
- `{{specify-subcmd:learning capture-auto}}`
  - Command shape: `{{specify-subcmd:learning capture-auto --command <command-name> --format json}}`
  - Use this when durable workflow state already preserves route reasons, false starts, hidden dependencies, validation gaps, or reusable constraints.
- Manual memory capture
  - Update `.specify/memory/learnings/INDEX.md` and one linked detail markdown document when automatic capture cannot express the lesson clearly.
- `{{specify-subcmd:learning aggregate}}`
  - Command shape: `{{specify-subcmd:learning aggregate --format json}}`
- `{{specify-subcmd:learning promote}}`
  - Command shape: `{{specify-subcmd:learning promote --recurrence-key <key> --target learning|rule}}`

Hook-based learning commands remain compatibility and native-adapter internals. Normal `sp-*` workflow steps should not call them.
```

Keep the later learning type lists, promotion heuristics, and storage rules intact.

- [ ] **Step 3: Remove remaining hook-learning command shapes**

Run:

```powershell
rg -n "hook signal-learning|hook review-learning|hook capture-learning|hook inject-learning|{{specify-subcmd:hook" templates/command-partials/common/learning-layer.md templates/passive-skills/spec-kit-project-learning/SKILL.md
```

Expected: no results.

- [ ] **Step 4: Run learning-focused tests**

Run:

```powershell
pytest tests/test_passive_skill_guidance.py::test_project_learning_focuses_on_memory_triggers_storage_and_promotion tests/test_command_surface_semantics.py::test_learning_surfaces_do_not_reference_removed_origin_artifact_option tests/test_command_surface_semantics.py::test_learning_contract_surfaces_do_not_ship_fake_runnable_placeholder_commands -q
```

Expected: PASS. If `test_learning_surfaces_do_not_reference_removed_origin_artifact_option` still expects `command shape:` from hook sections, adjust it to accept `learning capture-auto` command shapes and no hook learning text.

- [ ] **Step 5: Commit passive learning deescalation**

```powershell
git add templates/command-partials/common/learning-layer.md templates/passive-skills/spec-kit-project-learning/SKILL.md tests/test_passive_skill_guidance.py tests/test_command_surface_semantics.py
git commit -m "fix: move learning guidance off hook gates"
```

---

### Task 4: Remove Hook Guidance From Integration-Injected Addenda

**Files:**
- Modify: `src/specify_cli/integrations/base.py`
- Modify if failures appear: `tests/integrations/test_integration_base_markdown.py`
- Modify if failures appear: `tests/integrations/test_integration_base_skills.py`
- Modify if failures appear: `tests/integrations/test_integration_base_toml.py`
- Modify if failures appear: `tests/integrations/test_integration_codex.py`

- [ ] **Step 1: Replace implement leader gate hook instructions**

In `src/specify_cli/integrations/base.py`, inside `_append_implement_leader_gate`, replace:

```python
"- When the project launcher is available, use `{{specify-subcmd:hook validate-state --command implement --feature-dir \"$FEATURE_DIR\"}}` and `{{specify-subcmd:hook validate-session-state --command implement --feature-dir \"$FEATURE_DIR\"}}` before choosing the next batch so shared product checks verify the execution state.\n"
```

with:

```python
"- Before choosing the next batch, compare `workflow-state.md` and `implement-tracker.md` so execution state does not silently disagree with planning state.\n"
```

Replace:

```python
"- Before subagent dispatch, prefer `{{specify-subcmd:hook validate-packet --packet-file <packet-json>}}` when the current runtime has written the packet to disk.\n"
```

with:

```python
"- Before subagent dispatch, validate the packet contract in memory or through the runtime validator when the current runtime has written a packet file.\n"
```

- [ ] **Step 2: Replace quick leader gate and routing hook instructions**

Inside `_append_quick_leader_gate`, replace:

```python
"- When the project launcher is available, use `{{specify-subcmd:hook validate-state --command quick --workspace <quick-workspace>}}` and `{{specify-subcmd:hook validate-session-state --command quick --workspace <quick-workspace>}}` before choosing the next lane so shared product checks verify quick-task resume truth.\n"
```

with:

```python
"- Before choosing the next lane, read `STATUS.md` and any quick-task summary artifacts so resume truth comes from durable state instead of chat narration.\n"
```

Inside `_append_quick_routing_contract`, replace:

```python
"- Before compaction-risk transitions or join points, prefer `{{specify-subcmd:hook monitor-context --command quick --workspace <quick-workspace>}}` and follow checkpoint recommendations with `{{specify-subcmd:hook checkpoint --command quick --workspace <quick-workspace>}}`.\n"
```

with:

```python
"- Before compaction-risk transitions or join points, update `STATUS.md` and any summary artifacts needed for clean resume.\n"
```

- [ ] **Step 3: Add integration projection regression if no existing test catches this**

If focused integration tests do not fail before Step 1, add a new test to `tests/integrations/test_integration_codex.py`:

```python
def test_generated_codex_implement_skill_does_not_reintroduce_hook_choreography(tmp_path):
    project = tmp_path / "codex-no-hook-choreography"
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["init", str(project), "--ai", "codex", "--ai-skills", "--no-git", "--ignore-agent-tools"],
    )
    assert result.exit_code == 0, result.output

    implement = (project / ".codex" / "skills" / "sp-implement" / "SKILL.md").read_text(encoding="utf-8")
    quick = (project / ".codex" / "skills" / "sp-quick" / "SKILL.md").read_text(encoding="utf-8")

    for content in (implement, quick):
        assert "{{specify-subcmd:hook" not in content
        assert "WorkerTaskPacket" in content
        assert "structured handoff" in content
```

Use the existing imports and init style from nearby tests rather than duplicating incompatible helper setup.

- [ ] **Step 4: Run integration-focused tests**

Run:

```powershell
pytest tests/integrations/test_integration_codex.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py -q
```

Expected: PASS after updating any assertions that expected hook command text from injected addenda. Do not change native adapter tests unless this task intentionally changes adapter installation/default behavior.

- [ ] **Step 5: Commit integration addenda deescalation**

```powershell
git add src/specify_cli/integrations/base.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py
git commit -m "fix: stop integration addenda from reintroducing hook choreography"
```

---

### Task 5: Update Public Docs To Reclassify `specify hook`

**Files:**
- Modify: `README.md`
- Modify: `docs/quickstart.md`
- Modify if search shows workflow-facing hook guidance: `PROJECT-HANDBOOK.md`
- Modify: `tests/test_command_surface_semantics.py`

- [ ] **Step 1: Rewrite README hook sections**

In `README.md`, find the section that starts with "First-party workflow quality hooks:" and replace the hook catalog with:

```markdown
First-party hook runtime:

- `specify hook ...` is a compatibility, diagnostic, and native-adapter surface. Normal `sp-*` workflow steps should not call `specify hook ...`; generated workflows express quality requirements through durable state, artifact, packet, result, verification, learning, and project cognition contracts instead.
- Keep using hook commands when debugging a generated project, preserving compatibility with older generated assets, or running a native adapter that translates host hook events into shared checks.
- Important diagnostic command shapes:
  - `specify hook validate-state --command <workflow> --feature-dir <dir>`
  - `specify hook validate-session-state --command <workflow> --feature-dir <dir>`
  - `specify hook validate-packet --packet-file <path>`
  - `specify hook validate-result --packet-file <packet> --result-file <result>`
  - `specify hook validate-read-path --target-path <path>`
  - `specify hook validate-prompt --prompt-text "<text>"`
- Project cognition freshness should use the public project-map/project-cognition commands:
  - Command shape: `specify project-map complete-refresh`
  - Command shape: `specify project-map mark-dirty --reason "<reason>" [--origin-command <workflow>] [--origin-feature-dir <dir>] [--origin-lane-id <lane-id>] [--packet-file <packet-json>]`
  - Command shape: `specify project-cognition complete-refresh`
  - Command shape: `specify project-cognition mark-dirty --reason "<reason>" [--origin-command <workflow>] [--origin-feature-dir <dir>] [--origin-lane-id <lane-id>] [--packet-file <packet-json>]`
```

Keep native hook adapter descriptions, but change learning lines:

```markdown
- Learning capture and terminal learning review remain direct learning-memory responsibilities; native hooks may surface soft signals, but normal `sp-*` workflow steps should not call hook learning commands.
```

- [ ] **Step 2: Rewrite quickstart hook sections**

In `docs/quickstart.md`, replace the learning hook catalog and workflow hook helper catalog with equivalent low-noise guidance:

```markdown
Hook runtime and diagnostics:

- `specify hook ...` is kept for compatibility, diagnostics, tests, and native adapters. Normal `sp-*` workflow steps should not call `specify hook ...`.
- Use durable workflow state, artifact checks, packet/result contracts, verification output, and direct project learning memory during normal work.
- Diagnostic command shapes:
  - `specify hook validate-state --command <workflow> --feature-dir <dir>`
  - `specify hook validate-session-state --command <workflow> --feature-dir <dir>`
  - `specify hook validate-packet --packet-file <path>`
  - `specify hook validate-result --packet-file <packet> --result-file <result>`
- Use project cognition commands for freshness:
  - Command shape: `specify project-map complete-refresh`
  - Command shape: `specify project-map mark-dirty --reason "<reason>"`
  - Command shape: `specify project-cognition complete-refresh`
  - Command shape: `specify project-cognition mark-dirty --reason "<reason>"`
```

Update native adapter bullets so they describe internal translation without telling users to run hook commands manually.

- [ ] **Step 3: Search docs for old hook workflow instructions**

Run:

```powershell
rg -n "Use `specify hook|use `specify hook|normal .*call `specify hook|cross-workflow closeout gate|hook signal-learning|hook review-learning|hook capture-learning|hook inject-learning|command shape: `specify hook mark-dirty" README.md docs/quickstart.md PROJECT-HANDBOOK.md
```

Expected: no user-facing instruction to use hook commands during normal `sp-*` work; no hook dirty command shape in README/quickstart. It is acceptable for docs to say native adapters internally call `specify hook ...`.

- [ ] **Step 4: Run docs tests**

Run:

```powershell
pytest tests/test_command_surface_semantics.py tests/test_specify_guidance_docs.py -q
```

Expected: PASS. If tests still expect old hook catalogs, update them to assert compatibility/diagnostic framing.

- [ ] **Step 5: Commit docs update**

```powershell
git add README.md docs/quickstart.md PROJECT-HANDBOOK.md tests/test_command_surface_semantics.py
git commit -m "docs: reclassify hook commands as diagnostic surfaces"
```

---

### Task 6: Preserve Hook Runtime Compatibility and Clean Hook-Produced Learning Wording

**Files:**
- Modify only if desired by test expectations: `src/specify_cli/hooks/learning.py`
- Test: `tests/hooks/test_learning_hooks.py`
- Test: `tests/contract/test_hook_cli_surface.py`

- [ ] **Step 1: Decide whether hook-produced action text should remain explicit**

Run:

```powershell
pytest tests/hooks/test_learning_hooks.py tests/contract/test_hook_cli_surface.py -q
```

Expected before optional cleanup: PASS. These tests prove hook CLI compatibility still works.

- [ ] **Step 2: If product wording should avoid telling agents to run hook learning commands, update `src/specify_cli/hooks/learning.py` actions**

Only do this if docs/template deescalation is complete and you want the hook result text itself to avoid reinforcing hook choreography. Replace action strings that say:

```python
f"run `specify hook review-learning --command {command_name} --terminal-status resolved` before terminal closeout"
"if the friction exposed a reusable pitfall, workflow gap, hidden constraint, or tooling trap, capture it with `specify hook capture-learning` after supplying `--type`, `--summary`, and `--evidence`"
```

with:

```python
f"complete direct learning closeout for `sp-{command_name}` before terminal reporting"
"if the friction exposed a reusable pitfall, workflow gap, hidden constraint, or tooling trap, capture it in `.specify/memory/learnings/INDEX.md` and one linked detail document"
```

Apply equivalent changes to later action strings that reference `specify hook capture-learning` or `specify hook review-learning`.

- [ ] **Step 3: Update `tests/hooks/test_learning_hooks.py` if Step 2 changed wording**

Replace:

```python
assert "run `specify hook review-learning" in result.actions[0]
```

with:

```python
assert "complete direct learning closeout" in result.actions[0]
```

- [ ] **Step 4: Run hook runtime tests**

Run:

```powershell
pytest tests/hooks tests/contract/test_hook_cli_surface.py -q
```

Expected: PASS. This confirms the runtime was preserved even though workflow prompts stopped using it.

- [ ] **Step 5: Commit optional hook wording cleanup**

If files changed:

```powershell
git add src/specify_cli/hooks/learning.py tests/hooks/test_learning_hooks.py
git commit -m "fix: soften learning hook action wording"
```

If no files changed, skip this commit.

---

### Task 7: Run Global Search, Regenerate Confidence, and Final Verification

**Files:**
- No planned source edits unless verification finds misses.

- [ ] **Step 1: Run final hook choreography search**

Run:

```powershell
rg -n "{{specify-subcmd:hook|hook preflight|hook validate|hook checkpoint|hook workflow-policy|hook monitor-context|hook signal-learning|hook review-learning|hook capture-learning|hook inject-learning|hook mark-dirty|hook complete-refresh|hook render-statusline|hook validate-read-path|hook validate-prompt|hook build-compaction" templates src/specify_cli/integrations/base.py README.md docs/quickstart.md PROJECT-HANDBOOK.md tests
```

Expected:
- No results under `templates/commands/**`, `templates/command-partials/**`, `templates/passive-skills/**`, or `src/specify_cli/integrations/base.py`.
- Results may remain in `src/specify_cli/hooks/**`, native adapter scripts, hook CLI tests, launcher tests, and historical design docs if the search includes `docs/superpowers/**`.
- README/quickstart may mention `specify hook ...` only as compatibility, diagnostics, tests, or native-adapter internals.

- [ ] **Step 2: Run focused regression suite**

Run:

```powershell
pytest tests/test_hook_template_guidance.py tests/test_alignment_templates.py tests/test_passive_skill_guidance.py tests/test_quick_template_guidance.py tests/test_command_surface_semantics.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py tests/hooks tests/contract/test_hook_cli_surface.py -q
```

Expected: PASS.

- [ ] **Step 3: Run broader template/integration suite if focused suite passes**

Run:

```powershell
pytest tests/test_*template* tests/integrations -q
```

Expected: PASS or only failures unrelated to hook deescalation. Investigate any failure that mentions hook text, learning helper text, generated skill content, or project cognition dirty/fresh guidance.

- [ ] **Step 4: Inspect git diff**

Run:

```powershell
git diff --stat
git diff -- templates src README.md docs tests
```

Expected:
- No edits to `src/specify_cli/hooks/**` unless Task 6 optional wording cleanup was done.
- No deletion of hook CLI command implementations.
- Prompt/docs changes replace hook commands with outcome requirements and public project cognition commands.

- [ ] **Step 5: Commit final fixes if verification required additional edits**

If verification produced additional source/test/doc changes:

```powershell
git add templates src README.md docs tests
git commit -m "test: verify sp workflow hook deescalation"
```

If no additional edits were made after prior commits, skip this commit.

---

## Self-Review

Spec coverage:
- Removes routine `specify hook ...` usage from generated `sp-*` prompts: Tasks 1, 2, 4, and 7.
- Preserves hook runtime compatibility: Task 6.
- Keeps packet/result contracts strong: Tasks 1, 2, and 4.
- Moves learning off hook gates: Tasks 1, 2, and 3.
- Uses public project cognition commands instead of hook aliases: Tasks 2 and 5.
- Updates docs and tests: Tasks 1, 5, and 7.

Placeholder scan:
- No `TBD`, `TODO`, or unspecified implementation step is left in this plan.
- Each code-changing task includes exact files, concrete replacement text, commands, and expected outcomes.

Risk notes:
- Native adapter internals are intentionally left intact unless tests prove generated prompt surfaces still leak hook choreography.
- Existing generated projects remain compatible because hook CLI commands are not removed.

