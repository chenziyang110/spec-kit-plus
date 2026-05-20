# User-Intent Product Scope Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove generated workflow bias toward MVP or smallest-release thinking while preserving user-confirmed scope and the canonical `sp-specify -> sp-plan -> sp-tasks -> sp-implement` backbone.

**Architecture:** This is a template-and-test contract change. First update regression tests to encode user-intent scope semantics, then update command templates, shared artifact templates, passive routing guidance, and docs so generated downstream workflows stop treating product minimization as a default strategy.

**Tech Stack:** Markdown templates, Python `pytest` regression tests, PowerShell shell commands on Windows.

---

## File Structure

Modify these files:

- `tests/test_alignment_templates.py`: Update existing assertions and add regression guards for user-intent product scope language.
- `tests/test_passive_skill_guidance.py`: Add a focused passive routing assertion that command-route minimization is distinct from product-scope minimization.
- `tests/test_specify_guidance_docs.py`: Add or update docs assertions so README/quickstart guidance preserves user-confirmed product scope.
- `templates/commands/discussion.md`: Replace `Minimal viable path` option framing with user-intent-preserving technical options and scope-reduction rules.
- `templates/commands/specify.md`: Replace first-release/minimization language with confirmed product scope, user-confirmed delivery sequence, and explicit scope-reduction permission rules.
- `templates/commands/clarify.md`: Add a short guard that clarification repairs ambiguity without defaulting to smaller scope.
- `templates/commands/deep-research.md`: Add a short guard that demos/research spikes prove feasibility for intended scope rather than replacing product scope.
- `templates/commands/plan.md`: Replace `smallest integration scenario` quickstart language with representative end-to-end validation.
- `templates/commands/tasks.md`: Replace `Suggested first release scope` summary with confirmed delivery scope and user-confirmed sequencing.
- `templates/spec-template.md`: Replace `First-release outcome` and `coherent first release` wording with confirmed product outcome / current delivery boundary language.
- `templates/tasks-template.md`: Remove automatic User Story 1 first-release candidate and release/demo phrasing; keep independently testable priority-ordered stories.
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`: Clarify that the smallest safe route applies only to workflow command selection, not product scope.
- `README.md`, `PROJECT-HANDBOOK.md`, and `docs/quickstart.md`: Update only if the search in Task 1 finds user-facing workflow guidance that still implies default product minimization.

Do not modify historical design docs or prior implementation plans. They are archival records and may intentionally mention old terminology.

---

### Task 1: Add Failing Regression Tests For Scope Semantics

**Files:**
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_passive_skill_guidance.py`
- Modify: `tests/test_specify_guidance_docs.py`

- [ ] **Step 1: Update discussion options assertions**

In `tests/test_alignment_templates.py`, in `test_discussion_staged_cognition_gate_and_technical_options_contract`, replace:

```python
    assert "minimal viable path" in lowered
    assert "architecture-correct path" in lowered
    assert "expansion-ready path" in lowered
```

with:

```python
    assert "user-intent-aligned path" in lowered
    assert "architecture-correct path" in lowered
    assert "expansion-ready path" in lowered
    assert "minimal viable path" not in lowered
    assert "scope reduction requires user confirmation" in lowered
```

- [ ] **Step 2: Update specify scope assertions**

In `tests/test_alignment_templates.py`, in the large specify guidance test containing `assert "first-release scope" in lowered`, replace that assertion and the adjacent MVP assertion with:

```python
    assert "confirmed product scope" in lowered
    assert "user-confirmed delivery sequence" in lowered
    assert "scope reduction requires user confirmation" in lowered
    assert "first-release scope" not in lowered
    assert "mvp scope" not in lowered
```

- [ ] **Step 3: Update spec template scope assertions**

In `tests/test_alignment_templates.py`, in `test_spec_template_defines_scope_boundaries_without_open_clarification_examples`, replace:

```python
    assert "coherent first release" in lowered
    assert "viable mvp" not in lowered
    assert "scope boundaries" not in lowered
```

with:

```python
    assert "confirmed product outcome" in lowered
    assert "user-confirmed delivery boundary" in lowered
    assert "coherent first release" not in lowered
    assert "viable mvp" not in lowered
    assert "scope boundaries" not in lowered
```

- [ ] **Step 4: Rename and update tasks template regression**

In `tests/test_alignment_templates.py`, rename:

```python
def test_tasks_templates_default_to_phased_delivery_not_mvp():
```

to:

```python
def test_tasks_templates_preserve_user_confirmed_delivery_scope_not_mvp():
```

Inside that test, replace:

```python
    assert "phased delivery" in command_content.lower()
    assert "suggested first release scope" in command_content.lower()
```

with:

```python
    assert "user-confirmed delivery sequence" in command_content.lower()
    assert "confirmed delivery scope" in command_content.lower()
    assert "scope reduction requires user confirmation" in command_content.lower()
    assert "suggested first release scope" not in command_content.lower()
    assert "smallest coherent release slice" not in command_content.lower()
```

Replace:

```python
    assert "phased delivery" in template_content.lower()
    assert "first release candidate" in template_content.lower()
```

with:

```python
    assert "user-confirmed delivery sequence" in template_content.lower()
    assert "confirmed delivery boundary" in template_content.lower()
    assert "first release candidate" not in template_content.lower()
    assert "release/demo if ready" not in template_content.lower()
    assert "release/demo" not in template_content.lower()
```

Keep the existing assertions for `parallel batch`, `join point`, `write set`, `**[AGENT]**`, and MVP-negative checks.

- [ ] **Step 5: Add global generated-template forbidden phrase test**

Add this test near the other template contract tests in `tests/test_alignment_templates.py`:

```python
def test_generated_workflow_templates_do_not_default_to_product_minimization() -> None:
    checked_paths = [
        "templates/commands/discussion.md",
        "templates/commands/specify.md",
        "templates/commands/clarify.md",
        "templates/commands/deep-research.md",
        "templates/commands/plan.md",
        "templates/commands/tasks.md",
        "templates/spec-template.md",
        "templates/plan-template.md",
        "templates/tasks-template.md",
        "templates/passive-skills/spec-kit-workflow-routing/SKILL.md",
    ]
    forbidden = [
        "minimal viable path",
        "smallest coherent release slice",
        "suggested mvp scope",
        "mvp first",
        "mvp increment",
        "mvp!",
        "first story release",
        "user story 1 - [title] (priority: p1) first release candidate",
        "release/demo if ready",
        "smallest integration scenario",
    ]

    for rel_path in checked_paths:
        lowered = _read(rel_path).lower()
        for phrase in forbidden:
            assert phrase not in lowered, f"{phrase!r} should not appear in {rel_path}"

    specify = _read("templates/commands/specify.md").lower()
    assert "do not treat product minimization as the default strategy" in specify
    assert "scope reduction requires user confirmation" in specify
```

- [ ] **Step 6: Add passive routing distinction test**

In `tests/test_passive_skill_guidance.py`, add:

```python
def test_workflow_routing_distinguishes_command_route_from_product_scope() -> None:
    content = _read("templates/passive-skills/spec-kit-workflow-routing/SKILL.md").lower()

    assert "smallest safe workflow route" in content
    assert "does not authorize product-scope minimization" in content
    assert "preserve the user's confirmed product scope" in content
```

- [ ] **Step 7: Add docs guidance test**

In `tests/test_specify_guidance_docs.py`, add:

```python
def test_docs_teach_user_confirmed_product_scope_not_default_mvp() -> None:
    combined = "\n".join(
        _read(path).lower()
        for path in ("README.md", "PROJECT-HANDBOOK.md", "docs/quickstart.md")
    )

    assert "scope reduction requires user confirmation" in combined
    assert "preserve the user's confirmed product scope" in combined
    assert "minimal viable path" not in combined
    assert "smallest coherent release slice" not in combined
```

- [ ] **Step 8: Run the focused tests to verify they fail**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_discussion_staged_cognition_gate_and_technical_options_contract tests/test_alignment_templates.py::test_spec_template_defines_scope_boundaries_without_open_clarification_examples tests/test_alignment_templates.py::test_tasks_templates_preserve_user_confirmed_delivery_scope_not_mvp tests/test_alignment_templates.py::test_generated_workflow_templates_do_not_default_to_product_minimization tests/test_passive_skill_guidance.py::test_workflow_routing_distinguishes_command_route_from_product_scope tests/test_specify_guidance_docs.py::test_docs_teach_user_confirmed_product_scope_not_default_mvp -q
```

Expected: FAIL because templates and docs still contain old minimization language.

- [ ] **Step 9: Commit failing tests**

Run:

```powershell
git add tests/test_alignment_templates.py tests/test_passive_skill_guidance.py tests/test_specify_guidance_docs.py
git commit -m "test: guard user-intent product scope semantics"
```

Expected: Commit succeeds.

---

### Task 2: Update Discussion, Specify, Clarify, And Deep Research Templates

**Files:**
- Modify: `templates/commands/discussion.md`
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/clarify.md`
- Modify: `templates/commands/deep-research.md`

- [ ] **Step 1: Update discussion technical options board**

In `templates/commands/discussion.md`, replace:

```markdown
- Minimal viable path
- Architecture-correct path
- Expansion-ready path
```

with:

```markdown
- User-intent-aligned path
- Architecture-correct path
- Expansion-ready path
```

Immediately after that list, add:

```markdown
Scope reduction requires user confirmation. Do not present a smaller validation build, MVP-style slice, pilot, prototype, or first-story release as the default recommendation unless the user explicitly asked for that shape, the request already defines that delivery boundary, or a named constraint makes reduced scope a decision the user must confirm.
```

In the following sentence, replace `rollback or de-scope path` with `rollback, recovery, or user-confirmed scope-adjustment path`.

- [ ] **Step 2: Update specify facts-lock and feature analysis bullets**

In `templates/commands/specify.md`, replace each of these bullets:

```markdown
   - first-release scope boundaries
```

and:

```markdown
   - first-release scope
```

with:

```markdown
   - confirmed product scope and any user-confirmed delivery sequence
```

In the grouped recap block, replace:

```text
    [Scope Boundaries]
    - [First-release scope]
    - [Out-of-scope boundary]
```

with:

```text
    [Confirmed Product Scope]
    - [Current product scope to plan]
    - [User-confirmed deferrals or out-of-scope boundary]
    - [User-confirmed delivery sequence, if any]
```

- [ ] **Step 3: Strengthen specify AI generation rule**

In `templates/commands/specify.md`, replace rule 8:

```markdown
8. Do not treat MVP minimization as the default strategy; scope the first release to a coherent, quality-appropriate slice unless the user explicitly asks for a smaller release.
```

with:

```markdown
8. Do not treat product minimization as the default strategy. Preserve the user's confirmed product scope and plan toward the best product-quality implementation path for that scope. Scope reduction requires user confirmation: only record a smaller version, MVP, prototype, pilot, experiment, demo, proof-of-concept, staged release, or deferred capability when the user asked for it, the input already defines that boundary, or a named constraint forces a user-confirmed scope decision.
```

- [ ] **Step 4: Add clarify guard**

In `templates/commands/clarify.md`, after the clarification loop guidance that says `Ask only the minimum number of questions required to make planning reliable again.`, add:

```markdown
   - Do not use scope minimization as a shortcut to resolve ambiguity. Preserve the user's confirmed product scope; scope reduction requires user confirmation or a named constraint that blocks reliable planning.
```

- [ ] **Step 5: Add deep research guard**

In `templates/commands/deep-research.md`, near the guidance for disposable demos or planning handoff, add:

```markdown
- Disposable demos, research spikes, and proof artifacts validate feasibility for the user's intended capability. They are not a replacement product scope and must not be reframed as the delivered product unless the user explicitly confirms that reduced scope.
```

- [ ] **Step 6: Run focused tests**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_discussion_staged_cognition_gate_and_technical_options_contract tests/test_alignment_templates.py::test_generated_workflow_templates_do_not_default_to_product_minimization -q
```

Expected: Discussion and specify-related assertions pass or move failures to plan/tasks/spec surfaces not yet updated.

- [ ] **Step 7: Commit command template scope contract changes**

Run:

```powershell
git add templates/commands/discussion.md templates/commands/specify.md templates/commands/clarify.md templates/commands/deep-research.md
git commit -m "fix: preserve user-confirmed scope in requirement workflows"
```

Expected: Commit succeeds.

---

### Task 3: Update Plan, Tasks, Spec, And Tasks Templates

**Files:**
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/spec-template.md`
- Modify: `templates/tasks-template.md`

- [ ] **Step 1: Update plan quickstart language**

In `templates/commands/plan.md`, replace:

```markdown
3. **`quickstart.md`** — Generate for every feature. Keep it focused on the smallest integration scenario that validates the feature works end-to-end.
```

with:

```markdown
3. **`quickstart.md`** — Generate for every feature. Keep it focused on a representative end-to-end validation scenario that proves the confirmed product scope works through the relevant integration boundary.
```

- [ ] **Step 2: Update tasks command report summary**

In `templates/commands/tasks.md`, replace:

```markdown
    - Suggested first release scope (based on the smallest coherent release slice, not automatically limited to just User Story 1)
```

with:

```markdown
    - Confirmed delivery scope and user-confirmed delivery sequence, including any user-confirmed deferrals or constraint-driven scope adjustments
    - Scope reduction requires user confirmation; do not infer a smaller release from User Story 1 or the smallest independently testable story
```

- [ ] **Step 3: Update spec template first-release wording**

In `templates/spec-template.md`, replace:

```markdown
- **First-release outcome**: [What a coherent first release must achieve]
```

with:

```markdown
- **Confirmed product outcome**: [What the user-confirmed product scope must achieve]
```

Find the phrase `coherent first release` and replace the surrounding sentence with language that uses:

```text
user-confirmed delivery boundary
```

Preserve the `## Current Delivery Boundary`, `### In Scope`, and `### Out of Scope` sections.

- [ ] **Step 4: Update tasks template phase heading**

In `templates/tasks-template.md`, replace:

```markdown
## Phase 3: User Story 1 - [Title] (Priority: P1) First Release Candidate
```

with:

```markdown
## Phase 3: User Story 1 - [Title] (Priority: P1)
```

- [ ] **Step 5: Replace automatic first-release section**

In `templates/tasks-template.md`, replace the entire section:

```markdown
### First Release Candidate

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Release/demo if ready

### Phased Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Release/Demo if it forms a coherent first release candidate
3. Add User Story 2 → Test independently → Release/Demo
4. Add User Story 3 → Test independently → Release/Demo
5. Each story adds value without breaking previous stories
```

with:

```markdown
### Confirmed Delivery Boundary

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL - blocks all stories)
3. Complete every user story and supporting task included in the confirmed product scope
4. **STOP and VALIDATE**: Run the representative end-to-end validation scenario from `quickstart.md` and the independent tests for each included story
5. Treat delivery as ready only when the user-confirmed scope, quality gates, and regression evidence are complete

### User-Confirmed Delivery Sequence

1. Complete Setup + Foundational → Foundation ready
2. Add each confirmed story in priority order or in the user-approved parallel sequence
3. Test each story independently before dependent work continues
4. Preserve user-confirmed deferrals and non-goals explicitly; do not infer a smaller release from User Story 1
5. Each story adds value without breaking previous stories
```

- [ ] **Step 6: Run focused alignment tests**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_spec_template_defines_scope_boundaries_without_open_clarification_examples tests/test_alignment_templates.py::test_tasks_templates_preserve_user_confirmed_delivery_scope_not_mvp tests/test_alignment_templates.py::test_generated_workflow_templates_do_not_default_to_product_minimization -q
```

Expected: PASS for plan/tasks/spec wording. If failures mention archival docs under `docs/superpowers/specs` or `docs/superpowers/plans`, update the forbidden-phrase test to check generated workflow surfaces only, not archival design records.

- [ ] **Step 7: Commit planning and task template changes**

Run:

```powershell
git add templates/commands/plan.md templates/commands/tasks.md templates/spec-template.md templates/tasks-template.md tests/test_alignment_templates.py
git commit -m "fix: remove default first-release minimization from templates"
```

Expected: Commit succeeds.

---

### Task 4: Update Passive Routing And User Docs

**Files:**
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `docs/quickstart.md`

- [ ] **Step 1: Update passive routing goal language**

In `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`, replace:

```markdown
recommend the smallest safe workflow without silently entering it when ordinary
chat or coding is enough.
```

with:

```markdown
recommend the smallest safe workflow route without silently entering it when ordinary
chat or coding is enough. This command-routing rule does not authorize product-scope minimization.
```

- [ ] **Step 2: Update passive routing behavioral rule**

In `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`, replace:

```markdown
- If multiple recommendations seem plausible, suggest the smallest safe route and
  make the next escalation trigger explicit.
```

with:

```markdown
- If multiple workflow recommendations seem plausible, suggest the smallest safe workflow route and make the next escalation trigger explicit.
- Workflow-route minimization is only about choosing the command surface. Preserve the user's confirmed product scope; do not steer the product toward a smaller MVP, pilot, prototype, or first-story release unless the user asked for that shape or confirmed it after a named constraint/trade-off.
```

- [ ] **Step 3: Add README workflow guidance**

In `README.md`, near the section that describes `discussion`, `specify`, or the generated workflow path, add:

```markdown
Generated workflows preserve the user's confirmed product scope. Scope reduction requires user confirmation: agents should not steer a requirement toward an MVP, pilot, prototype, first-story release, or smaller validation build unless the user asked for that shape, the request already defines that boundary, or a named constraint makes reduced scope a decision the user confirms.
```

- [ ] **Step 4: Add handbook workflow guidance**

In `PROJECT-HANDBOOK.md`, near the current workflow guidance, add:

```markdown
Generated workflows preserve the user's confirmed product scope. Workflow routing may choose the lightest safe command surface, but it must not convert the user's product intent into a smaller MVP or first-story release. Scope reduction requires user confirmation or a named constraint that forces a scope decision.
```

- [ ] **Step 5: Inspect quickstart before editing**

Run:

```powershell
Select-String -Path docs/quickstart.md -Pattern "MVP","minimum viable","minimal viable","smallest","first release","prototype","pilot","demo","scope" -CaseSensitive:$false -Context 2,2
```

Expected: If there is no product-scope guidance in `docs/quickstart.md`, add a short note near the generated workflow overview:

```markdown
The generated workflow preserves the user's confirmed product scope. A smaller MVP, pilot, prototype, or staged delivery boundary is valid only when the user asks for it, the request already defines it, or the agent names a constraint and the user confirms the scope decision.
```

If `docs/quickstart.md` already contains a suitable section, update that section instead of adding a duplicate paragraph.

- [ ] **Step 6: Run passive/docs tests**

Run:

```powershell
pytest tests/test_passive_skill_guidance.py::test_workflow_routing_distinguishes_command_route_from_product_scope tests/test_specify_guidance_docs.py::test_docs_teach_user_confirmed_product_scope_not_default_mvp -q
```

Expected: PASS.

- [ ] **Step 7: Commit routing and docs**

Run:

```powershell
git add templates/passive-skills/spec-kit-workflow-routing/SKILL.md README.md PROJECT-HANDBOOK.md docs/quickstart.md tests/test_passive_skill_guidance.py tests/test_specify_guidance_docs.py
git commit -m "docs: distinguish workflow routing from product scope"
```

Expected: Commit succeeds.

---

### Task 5: Run Full Verification And Final Cleanup

**Files:**
- No planned edits unless verification exposes a targeted issue.

- [ ] **Step 1: Run minimization search over active product surfaces**

Run:

```powershell
rg -n -i "MVP|minimum viable|minimal viable|smallest coherent|first release candidate|first-release scope|first release scope|Release/Demo|smaller release|smallest integration scenario|User Story 1.*First Release" templates src scripts tests README.md PROJECT-HANDBOOK.md docs/quickstart.md
```

Expected: No hits in active generated product surfaces except tests that intentionally assert forbidden terms are absent. Do not count archival files under `docs/superpowers/specs` or `docs/superpowers/plans`.

- [ ] **Step 2: Run focused template/docs tests**

Run:

```powershell
pytest tests/test_alignment_templates.py tests/test_passive_skill_guidance.py tests/test_specify_guidance_docs.py -q
```

Expected: PASS.

- [ ] **Step 3: Run integration smoke tests for generated command/skill surfaces**

Run:

```powershell
pytest tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py -q
```

Expected: PASS. These tests ensure the changed templates still render across skill, Markdown, and TOML integrations.

- [ ] **Step 4: Run final git diff review**

Run:

```powershell
git status --short
git diff --stat HEAD
git diff --check
```

Expected: No whitespace errors. Remaining uncommitted changes should be only intentional if any verification fixes were needed.

- [ ] **Step 5: Commit any verification fixes**

If Task 5 required edits, run:

```powershell
git add <changed-files>
git commit -m "fix: align scope wording verification"
```

Expected: Commit succeeds. Skip this step if no verification fixes were needed.

- [ ] **Step 6: Report completion**

Final response should include:

- the plan/spec implemented
- the main surfaces changed
- tests run and results
- any residual risk, especially if broad test suites were not run
