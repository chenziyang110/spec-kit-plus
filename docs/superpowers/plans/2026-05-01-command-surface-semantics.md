# Command Surface Semantics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Separate canonical workflow-state tokens from user-facing invocation syntax across templates, generated assets, and public docs without breaking existing workflow-state compatibility.

**Architecture:** Keep `/sp.plan`-style canonical workflow tokens as the internal protocol layer while introducing a template-level user-invocation projection path. Shared templates become the source of truth, generation helpers project invocation syntax per integration, and regression tests enforce the boundary between state tokens and user-facing command examples.

**Tech Stack:** Markdown templates, Python generation helpers in `src/specify_cli`, pytest integration tests, public docs in `README.md` and `docs/`.

---

## File Structure

```text
MODIFY:
  templates/commands/specify.md                          — Split canonical-token text from user-facing invocation guidance
  templates/commands/plan.md                             — Replace user-facing hardcoded invocation examples
  templates/commands/tasks.md                            — Replace user-facing hardcoded invocation examples
  templates/commands/auto.md                             — Keep canonical state tokens, project user-facing resume invocations
  templates/commands/analyze.md                          — Split state-routing text from user-facing guidance
  templates/commands/quick.md                            — Split escalation examples and projected invocations
  templates/commands/test-scan.md                        — Split escalation examples and projected invocations
  templates/commands/test-build.md                       — Split escalation examples and projected invocations
  templates/commands/team.md                             — Preserve `sp-teams` as product surface while keeping semantics explicit
  templates/passive-skills/spec-kit-workflow-routing/SKILL.md
  templates/passive-skills/spec-kit-project-map-gate/SKILL.md
  templates/passive-skills/subagent-driven-development/SKILL.md
  templates/passive-skills/dispatching-parallel-agents/SKILL.md
  README.md                                              — Public workflow syntax guidance by integration
  docs/quickstart.md                                     — Replace universal slash examples with integration-aware guidance
  docs/installation.md                                   — Replace universal slash examples with integration-aware guidance
  src/specify_cli/agents.py                              — Shared invocation projection helpers for extension/preset skill generation
  src/specify_cli/integrations/base.py                   — Shared invocation projection for `init` skill generation path
  tests/integrations/test_integration_codex.py           — Generated skill invocation projection assertions
  tests/integrations/test_integration_kimi.py            — Generated skill invocation projection assertions
  tests/integrations/test_cli.py                         — Next-steps integration-specific invocation guidance assertions
  tests/test_specify_guidance_docs.py                    — Public docs invocation guidance assertions
  tests/test_alignment_templates.py                      — Template-level separation of canonical tokens vs user invocations

CREATE:
  tests/test_command_surface_semantics.py                — Focused regression tests for projection semantics and token preservation
```

---

## Phase 1: Shared Projection Infrastructure

### Task 1: Add one shared workflow-invocation projection helper for skills-backed surfaces

**Files:**
- Modify: `src/specify_cli/agents.py`
- Test: `tests/test_command_surface_semantics.py`

- [ ] **Step 1: Write the failing unit test for integration-specific invocation projection**

```python
from specify_cli.agents import CommandRegistrar


def test_apply_skill_invocation_conventions_projects_user_facing_examples_by_agent():
    body = (
        "- Run /sp-plan next.\n"
        "- State token remains `next_command: /sp.plan`.\n"
    )

    codex = CommandRegistrar.apply_skill_invocation_conventions("codex", body)
    kimi = CommandRegistrar.apply_skill_invocation_conventions("kimi", body)
    claude = CommandRegistrar.apply_skill_invocation_conventions("claude", body)

    assert "- Run $sp-plan next." in codex
    assert "- Run /skill:sp-plan next." in kimi
    assert "- Run /sp-plan next." in claude
    assert "`next_command: /sp.plan`" in codex
    assert "`next_command: /sp.plan`" in kimi
    assert "`next_command: /sp.plan`" in claude
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_command_surface_semantics.py -q -k projects_user_facing_examples_by_agent`
Expected: FAIL because the helper or preservation assertions do not exist yet.

- [ ] **Step 3: Implement a shared helper that distinguishes invocation examples from canonical state tokens**

Add or refine helper code in `src/specify_cli/agents.py` so it:

- maps skill-backed integrations to the correct invocation surface
- rewrites slash-style user invocation examples only for skills-backed targets
- preserves `/sp.plan`-style canonical state tokens and `next_command` examples
- prepends an invocation note explaining that canonical state tokens are not always the literal invocation syntax

Implementation shape:

```python
class CommandRegistrar:
    @staticmethod
    def _skill_invocation_example(agent_name: str) -> str | None:
        ...

    @classmethod
    def apply_skill_invocation_conventions(cls, agent_name: str, body: str) -> str:
        ...
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_command_surface_semantics.py -q -k projects_user_facing_examples_by_agent`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/agents.py tests/test_command_surface_semantics.py
git commit -m "feat: add shared skill invocation projection helper"
```

### Task 2: Route `init` skill generation through the same projection helper

**Files:**
- Modify: `src/specify_cli/integrations/base.py`
- Test: `tests/test_command_surface_semantics.py`

- [ ] **Step 1: Write the failing unit test for `init` skill generation path parity**

```python
from pathlib import Path
from typer.testing import CliRunner

from specify_cli import app


def test_init_generated_codex_skill_includes_invocation_note_and_projected_handoff(tmp_path: Path):
    runner = CliRunner()
    target = tmp_path / "codex-projection"

    result = runner.invoke(
        app,
        ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
    )

    assert result.exit_code == 0
    content = (target / ".codex" / "skills" / "sp-specify" / "SKILL.md").read_text(encoding="utf-8")

    assert "## Invocation Syntax" in content
    assert "`$sp-plan`-style syntax" in content
    assert "- **Default handoff**: $sp-plan" in content
    assert "`next_command: /sp.plan`" in content
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_command_surface_semantics.py -q -k init_generated_codex_skill_includes_invocation_note_and_projected_handoff`
Expected: FAIL because the `init` generation path is not yet guaranteed to share the same helper behavior.

- [ ] **Step 3: Update `src/specify_cli/integrations/base.py` to apply the shared helper during skill rendering**

Refine `_render_skill_content(...)` so the body is passed through the same projection helper used by extension and preset skill generation:

```python
from specify_cli.agents import CommandRegistrar

processed_body = CommandRegistrar.apply_skill_invocation_conventions(
    self.key,
    processed_body,
)
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_command_surface_semantics.py -q -k init_generated_codex_skill_includes_invocation_note_and_projected_handoff`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/integrations/base.py tests/test_command_surface_semantics.py
git commit -m "feat: share invocation projection across init skill generation"
```

---

## Phase 2: Template Rule Cleanup

### Task 3: Refactor high-risk command templates to separate canonical tokens from user-facing invocation text

**Files:**
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/commands/auto.md`
- Modify: `templates/commands/analyze.md`
- Modify: `templates/commands/quick.md`
- Modify: `templates/commands/test-scan.md`
- Modify: `templates/commands/test-build.md`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Write the failing template regression test for mixed semantics**

```python
from pathlib import Path


def test_specify_template_keeps_canonical_state_tokens_but_not_universal_user_invocation():
    content = Path("templates/commands/specify.md").read_text(encoding="utf-8")

    assert "`next_command` as `/sp.plan`, `/sp.clarify`, or `/sp.deep-research`" in content
    assert "Default handoff: /sp-plan" not in content
    assert "Default handoff: /sp.plan" not in content
    assert "{{invoke:plan}}" in content
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_alignment_templates.py -q -k keeps_canonical_state_tokens_but_not_universal_user_invocation`
Expected: FAIL because the templates still embed user-facing slash examples directly.

- [ ] **Step 3: Update the templates to use one consistent pattern**

For each listed command template:

- keep canonical state token references in state and contract sections
- replace user-facing "run the next command" language with the shared invocation placeholder form
- split mixed sentences into:
  - one canonical-token statement
  - one user-facing invocation statement

Template examples to apply:

```markdown
- **Default handoff**: `{{invoke:plan}}` once planning-critical ambiguity and feasibility risk are reduced far enough.
- Preserve canonical workflow state tokens such as `next_command: /sp.plan` in artifacts and reports.
```

```markdown
- Route to the canonical workflow token `/sp.plan` in `workflow-state.md`.
- Tell the user to run `{{invoke:plan}}` when a manual next-step recommendation is needed.
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_alignment_templates.py -q -k keeps_canonical_state_tokens_but_not_universal_user_invocation`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add templates/commands/specify.md templates/commands/plan.md templates/commands/tasks.md templates/commands/auto.md templates/commands/analyze.md templates/commands/quick.md templates/commands/test-scan.md templates/commands/test-build.md tests/test_alignment_templates.py
git commit -m "refactor: split canonical tokens from user invocation text in core templates"
```

### Task 4: Refactor workflow-routing passive skills to follow the same rule

**Files:**
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Modify: `templates/passive-skills/spec-kit-project-map-gate/SKILL.md`
- Modify: `templates/passive-skills/subagent-driven-development/SKILL.md`
- Modify: `templates/passive-skills/dispatching-parallel-agents/SKILL.md`
- Test: `tests/test_command_surface_semantics.py`

- [ ] **Step 1: Write the failing passive-skill regression test**

```python
from pathlib import Path


def test_workflow_routing_passive_skill_uses_placeholder_for_user_invocation_examples():
    content = Path("templates/passive-skills/spec-kit-workflow-routing/SKILL.md").read_text(encoding="utf-8")

    assert "{{invoke:specify}}" in content
    assert "Use `/sp-specify`" not in content
    assert "Use `/sp-plan`" not in content
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_command_surface_semantics.py -q -k workflow_routing_passive_skill_uses_placeholder_for_user_invocation_examples`
Expected: FAIL because the passive skills still teach user-facing slash syntax directly.

- [ ] **Step 3: Update passive skills to stop presenting universal slash-style user examples**

For each listed passive skill:

- keep canonical workflow names where discussing routing semantics
- replace explicit user invocation examples with the placeholder form
- leave `sp-teams` unchanged where it is the actual Codex product surface rather than a projected workflow skill

Example rewrite:

```markdown
- Use `{{invoke:specify}}` when the user needs explicit requirement alignment before planning.
- Preserve canonical state tokens such as `/sp.plan` only where the text is about workflow-state or artifact semantics.
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_command_surface_semantics.py -q -k workflow_routing_passive_skill_uses_placeholder_for_user_invocation_examples`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add templates/passive-skills/spec-kit-workflow-routing/SKILL.md templates/passive-skills/spec-kit-project-map-gate/SKILL.md templates/passive-skills/subagent-driven-development/SKILL.md templates/passive-skills/dispatching-parallel-agents/SKILL.md tests/test_command_surface_semantics.py
git commit -m "refactor: align passive skills with command surface semantics"
```

---

## Phase 3: Public Docs and Next-Steps Output

### Task 5: Make public docs integration-aware instead of slash-default

**Files:**
- Modify: `README.md`
- Modify: `docs/quickstart.md`
- Modify: `docs/installation.md`
- Test: `tests/test_specify_guidance_docs.py`

- [ ] **Step 1: Write the failing doc regression test**

```python
from pathlib import Path


def test_quickstart_declares_integration_specific_invocation_syntax():
    quickstart = Path("docs/quickstart.md").read_text(encoding="utf-8")

    assert "Invocation syntax depends on the integration:" in quickstart
    assert "$sp-specify" in quickstart
    assert "/skill:sp-specify" in quickstart
    assert "/sp.specify" in quickstart
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pytest tests/test_specify_guidance_docs.py -q -k declares_integration_specific_invocation_syntax`
Expected: FAIL if docs still imply slash-style syntax as the default universal surface.

- [ ] **Step 3: Update public docs to separate canonical names from invocation syntax**

Apply these documentation rules:

- mention canonical workflow names separately from invocation examples
- show per-integration invocation examples where the user is expected to type something
- explicitly warn that `/sp-*` is not universal for skills-backed integrations

Concrete edits:

- `README.md`: add an invocation syntax matrix near the workflow section
- `docs/quickstart.md`: add per-integration invocation examples for constitution/specify/plan/tasks
- `docs/installation.md`: replace Claude-only slash assumptions with a short invocation matrix

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/test_specify_guidance_docs.py -q -k declares_integration_specific_invocation_syntax`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add README.md docs/quickstart.md docs/installation.md tests/test_specify_guidance_docs.py
git commit -m "docs: make workflow invocation guidance integration-aware"
```

### Task 6: Verify `specify init` next-steps output stays correct per integration

**Files:**
- Modify: `tests/integrations/test_cli.py`

- [ ] **Step 1: Write the failing integration-output assertion**

```python
def test_kimi_init_next_steps_show_skill_invocation_examples_without_slash_dot_surface(...):
    ...
    assert "/skill:sp-specify" in result.output
    assert "/sp.specify" not in result.output
```

- [ ] **Step 2: Run the test to verify it fails only if output still drifts**

Run: `pytest tests/integrations/test_cli.py -q -k kimi_init_next_steps_show_skill_invocation_examples_without_slash_dot_surface`
Expected: PASS if already correct; otherwise FAIL and drive the fix.

- [ ] **Step 3: If needed, refine `_display_cmd(...)` or adjacent next-steps rendering logic**

Keep these mappings stable:

```python
if codex_skill_mode or agy_skill_mode:
    return f"$sp-{name}"
if claude_skill_mode:
    return f"/sp-{name}"
if kimi_skill_mode:
    return f"/skill:sp-{name}"
return f"/sp.{name}"
```

Do not let documentation or template cleanup regress the next-steps CLI output semantics.

- [ ] **Step 4: Run the test to verify it passes**

Run: `pytest tests/integrations/test_cli.py -q -k kimi_init_next_steps_show_skill_invocation_examples_without_slash_dot_surface`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/integrations/test_cli.py src/specify_cli/__init__.py
git commit -m "test: lock integration-specific next-steps invocation output"
```

---

## Phase 4: Full Regression Matrix

### Task 7: Add focused regression tests for generated assets across key integrations

**Files:**
- Modify: `tests/integrations/test_integration_codex.py`
- Modify: `tests/integrations/test_integration_kimi.py`
- Create: `tests/test_command_surface_semantics.py`

- [ ] **Step 1: Write failing integration tests for generated invocation notes and canonical-token preservation**

```python
def test_codex_generated_skills_explain_invocation_syntax_vs_canonical_state(...):
    ...
    assert "## Invocation Syntax" in content
    assert "`$sp-plan`-style syntax" in content
    assert "canonical workflow-state identifiers and handoff values" in content
    assert "- **Default handoff**: $sp-plan" in content


def test_kimi_generated_skills_explain_invocation_syntax_vs_canonical_state(...):
    ...
    assert "## Invocation Syntax" in content
    assert "`/skill:sp-plan`-style syntax" in content
    assert "- **Default handoff**: /skill:sp-tasks" in content
```

- [ ] **Step 2: Run the tests to verify they fail only when generated content is still inconsistent**

Run: `pytest tests/integrations/test_integration_codex.py -q -k invocation_syntax`
Expected: PASS if already correct; otherwise FAIL and drive the fix.

Run: `pytest tests/integrations/test_integration_kimi.py -q -k invocation_syntax`
Expected: PASS if already correct; otherwise FAIL and drive the fix.

- [ ] **Step 3: Normalize any remaining generated-surface wording inconsistencies**

If assertions fail, fix the projection helper or template wording so generated assets:

- explain the active invocation syntax
- preserve canonical token wording where required
- no longer present a universal slash-style next-step recommendation

- [ ] **Step 4: Run the tests to verify they pass**

Run: `pytest tests/integrations/test_integration_codex.py -q -k invocation_syntax`
Expected: PASS

Run: `pytest tests/integrations/test_integration_kimi.py -q -k invocation_syntax`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/integrations/test_integration_codex.py tests/integrations/test_integration_kimi.py tests/test_command_surface_semantics.py
git commit -m "test: add command surface semantics regression coverage"
```

### Task 8: Run the targeted verification suite and finalize

**Files:**
- Modify: none

- [ ] **Step 1: Run targeted template, docs, and integration tests**

Run: `pytest tests/test_command_surface_semantics.py tests/test_specify_guidance_docs.py tests/test_alignment_templates.py tests/integrations/test_cli.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_kimi.py -q`
Expected: PASS

- [ ] **Step 2: Run one broader integration smoke sweep**

Run: `pytest tests/integrations -q`
Expected: PASS

- [ ] **Step 3: Review the final diff for semantic boundary correctness**

Run: `git diff --stat HEAD~8..HEAD`
Expected: shows changes only in:

- shared templates
- docs
- projection helpers
- tests

And confirms:

- no state-layer token migration
- no renaming of canonical workflows
- no unintended `sp-teams` surface changes

- [ ] **Step 4: Commit the verification checkpoint**

```bash
git add -A
git commit -m "chore: verify command surface semantics rollout"
```

---

## Spec Coverage Check

This plan covers every requirement in `docs/superpowers/specs/2026-05-01-command-surface-semantics-design.md`:

- three-layer model preserved
- canonical token compatibility preserved
- template-authoring rule enforcement added
- shared projection helper centralized
- `init` and extension/preset chains aligned
- public docs corrected
- high-risk templates and passive skills cleaned
- regression tests added for projection and token preservation

No spec sections are left without an implementation phase.

## Placeholder Scan

This plan intentionally avoids placeholders like `TODO`, `TBD`, or "implement later". The only variable text is in code examples and exact test names, all of which are concretely defined.

## Type and Naming Consistency Check

Naming used consistently across tasks:

- canonical workflow token
- user invocation surface
- integration projection
- invocation placeholder
- `apply_skill_invocation_conventions(...)`

Generated asset examples remain aligned with the design:

- Codex -> `$sp-*`
- Claude -> `/sp-*`
- Kimi -> `/skill:sp-*`
- Markdown command integrations -> `/sp.*`
