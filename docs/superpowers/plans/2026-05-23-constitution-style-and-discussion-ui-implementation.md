# Constitution Style and Discussion UI Stage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add constitution guidance for following existing project style across all built-in profiles and add an optional UI/interaction discussion stage to `sp-discussion`.

**Architecture:** This is a shared-template change. Constitution behavior lives in the four built-in profile YAML files and the generated product template must remain synchronized with the product profile. Discussion behavior lives in the `sp-discussion` command template, its shell partial, and the discussion state template; integration tests verify rendered command output.

**Tech Stack:** Python, pytest, Markdown command templates, YAML constitution profiles.

---

## File Structure

- Modify `templates/constitution/profiles/product.yml`: add the project-style engineering standard and bump the product constitution profile minor version.
- Modify `templates/constitution/profiles/library.yml`: add the same engineering standard with library-compatible wording and bump the minor version.
- Modify `templates/constitution/profiles/minimal.yml`: add the same engineering standard with minimal-process wording and bump the minor version.
- Modify `templates/constitution/profiles/regulated.yml`: add the same engineering standard with regulated-control wording and bump the minor version.
- Modify `templates/constitution-template.md`: keep it byte-for-byte aligned with the rendered product profile after the product profile changes.
- Modify `templates/discussion-state-template.md`: add `ui-interaction-discussion` to `current_stage` and add `ui_discussion_status`.
- Modify `templates/commands/discussion.md`: add the optional UI/interaction discussion stage, senior UI persona, artifact rules, ASCII sketch guidance, and handoff JSON boundary.
- Modify `templates/command-partials/discussion/shell.md`: summarize the optional UI/interaction stage in the compact shell contract.
- Modify `tests/test_constitution_defaults.py`: assert all built-in profiles materialize the project-style guidance and updated versions.
- Modify `tests/test_constitution_profiles_cli.py`: assert generated CLI projects include the project-style guidance for each profile.
- Modify `tests/test_alignment_templates.py`: assert discussion templates include the UI stage, status field, ASCII sketch boundary, and current-stage enum.
- Modify `tests/integrations/test_integration_base_toml.py`: assert rendered command content preserves the UI discussion contract.
- Modify `tests/integrations/test_integration_codex.py`: assert Codex generated assets include the UI state field and rendered discussion guidance.

## Implementation Notes

Use this shared constitution wording unless a profile needs a shorter surrounding line wrap:

```text
- **Follow Project Style and Structure**: Before implementing, inspect and follow
  the current project's established style, file organization, naming
  conventions, helper APIs, framework patterns, and architecture boundaries.
  Extend existing patterns when they satisfy the requirement. If a broader
  architecture improvement appears warranted, present the recommendation,
  trade-offs, and expected impact to the user before changing direction.
```

Version bump rule: this adds materially expanded guidance, so each changed profile receives a MINOR bump. Expected profile versions after implementation:

- `product`: `1.3.0`
- `library`: `1.2.0`
- `minimal`: `1.2.0`
- `regulated`: `1.2.0`

## Task 1: Add Failing Constitution Profile Tests

**Files:**
- Modify: `tests/test_constitution_defaults.py`
- Modify: `tests/test_constitution_profiles_cli.py`

- [ ] **Step 1: Add a helper assertion for the project-style constitution standard**

In `tests/test_constitution_defaults.py`, add this helper after `_compact`:

```python
def _assert_project_style_standard(content: str) -> None:
    compact = _compact(content)
    assert "Follow Project Style and Structure" in content
    assert "current project's established style, file organization, naming conventions" in compact
    assert "helper APIs, framework patterns, and architecture boundaries" in compact
    assert "present the recommendation, trade-offs, and expected impact to the user" in compact
```

- [ ] **Step 2: Use the helper in each materialized constitution test**

In `test_ensure_constitution_from_template_materializes_defaults`, add:

```python
    _assert_project_style_standard(content)
```

Change the version assertion in the same test to:

```python
    assert "**Version**: 1.3.0" in content
```

In `test_ensure_constitution_from_template_materializes_library_profile`, add:

```python
    _assert_project_style_standard(content)
```

Change the version assertion in the same test to:

```python
    assert "**Version**: 1.2.0" in content
```

In `test_ensure_constitution_from_template_materializes_minimal_profile`, add:

```python
    _assert_project_style_standard(content)
```

Change the version assertion in the same test to:

```python
    assert "**Version**: 1.2.0" in content
```

In `test_ensure_constitution_from_template_materializes_regulated_profile`, add:

```python
    _assert_project_style_standard(content)
```

Change the version assertion in the same test to:

```python
    assert "**Version**: 1.2.0" in content
```

- [ ] **Step 3: Assert CLI-generated constitutions contain the same standard**

In `tests/test_constitution_profiles_cli.py`, add this helper after `_compact`:

```python
def _assert_project_style_standard(content: str) -> None:
    compact = _compact(content)
    assert "Follow Project Style and Structure" in content
    assert "current project's established style, file organization, naming conventions" in compact
    assert "helper APIs, framework patterns, and architecture boundaries" in compact
    assert "present the recommendation, trade-offs, and expected impact to the user" in compact
```

Add this assertion to each of these tests:

- `test_init_defaults_to_product_constitution_profile`
- `test_init_with_library_constitution_profile_materializes_project_template`
- `test_init_with_minimal_constitution_profile_materializes_project_constitution`
- `test_init_with_regulated_constitution_profile_materializes_project_constitution`

Use the same line in each test:

```python
    _assert_project_style_standard(constitution)
```

- [ ] **Step 4: Run constitution tests and verify they fail**

Run:

```bash
pytest tests/test_constitution_defaults.py tests/test_constitution_profiles_cli.py -q
```

Expected: FAIL because the profile YAML files do not yet contain `Follow Project Style and Structure` and still use the old profile versions.

## Task 2: Implement Constitution Profile Guidance

**Files:**
- Modify: `templates/constitution/profiles/product.yml`
- Modify: `templates/constitution/profiles/library.yml`
- Modify: `templates/constitution/profiles/minimal.yml`
- Modify: `templates/constitution/profiles/regulated.yml`
- Modify: `templates/constitution-template.md`

- [ ] **Step 1: Update product profile version and engineering standards**

In `templates/constitution/profiles/product.yml`, change:

```yaml
version: 1.2.0
```

to:

```yaml
version: 1.3.0
```

Insert this bullet in `engineering_standards` after the `Technical Evidence` bullet and before `Encoding Preservation`:

```markdown
  - **Follow Project Style and Structure**: Before implementing, inspect and follow
    the current project's established style, file organization, naming
    conventions, helper APIs, framework patterns, and architecture boundaries.
    Extend existing patterns when they satisfy the requirement. If a broader
    architecture improvement appears warranted, present the recommendation,
    trade-offs, and expected impact to the user before changing direction.
```

- [ ] **Step 2: Update library profile version and engineering standards**

In `templates/constitution/profiles/library.yml`, change:

```yaml
version: 1.1.0
```

to:

```yaml
version: 1.2.0
```

Insert this bullet in `engineering_standards` after `SemVer and Release Discipline` and before `Examples and Upgrade Paths`:

```markdown
  - **Follow Project Style and Structure**: Before implementing, inspect and follow
    the current project's established style, file organization, naming
    conventions, helper APIs, framework patterns, and architecture boundaries.
    Extend existing patterns when they satisfy the requirement. If a broader
    architecture improvement appears warranted, present the recommendation,
    trade-offs, and expected impact to the user before changing direction.
```

- [ ] **Step 3: Update minimal profile version and engineering standards**

In `templates/constitution/profiles/minimal.yml`, change:

```yaml
version: 1.1.0
```

to:

```yaml
version: 1.2.0
```

Insert this bullet in `engineering_standards` after `Project Cognition Before Existing-System Judgment` and before `Clear Naming`:

```markdown
  - **Follow Project Style and Structure**: Before implementing, inspect and follow
    the current project's established style, file organization, naming
    conventions, helper APIs, framework patterns, and architecture boundaries.
    Extend existing patterns when they satisfy the requirement. If a broader
    architecture improvement appears warranted, present the recommendation,
    trade-offs, and expected impact to the user before changing direction.
```

- [ ] **Step 4: Update regulated profile version and engineering standards**

In `templates/constitution/profiles/regulated.yml`, change:

```yaml
version: 1.1.0
```

to:

```yaml
version: 1.2.0
```

Insert this bullet in `engineering_standards` after `Project Cognition Before Existing-System Judgment` and before `Control Documentation Sync`:

```markdown
  - **Follow Project Style and Structure**: Before implementing, inspect and follow
    the current project's established style, file organization, naming
    conventions, helper APIs, framework patterns, and architecture boundaries.
    Extend existing patterns when they satisfy the requirement. If a broader
    architecture improvement appears warranted, present the recommendation,
    trade-offs, and expected impact to the user before changing direction.
```

- [ ] **Step 5: Regenerate the product constitution template content**

`templates/constitution-template.md` must match `build_constitution_template_for_profile("product")`. Update it manually to mirror the product profile changes:

- change the rendered version line from `**Version**: 1.2.0` to `**Version**: 1.3.0`
- add the same `Follow Project Style and Structure` engineering-standard bullet in the same relative position as `product.yml`

Use the rendered Markdown indentation already present in `templates/constitution-template.md`, not the YAML-indented version.

- [ ] **Step 6: Run constitution tests and verify they pass**

Run:

```bash
pytest tests/test_constitution_defaults.py tests/test_constitution_profiles_cli.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit constitution changes**

Run:

```bash
git add templates/constitution/profiles/product.yml templates/constitution/profiles/library.yml templates/constitution/profiles/minimal.yml templates/constitution/profiles/regulated.yml templates/constitution-template.md tests/test_constitution_defaults.py tests/test_constitution_profiles_cli.py
git commit -m "feat: add project-style constitution standard"
```

## Task 3: Add Failing Discussion UI Stage Tests

**Files:**
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Modify: `tests/integrations/test_integration_codex.py`

- [ ] **Step 1: Extend the main discussion command contract test**

In `tests/test_alignment_templates.py`, inside `test_discussion_command_contract_is_pre_spec_and_resumable`, add:

```python
    assert "senior UI and interaction designer" in content
    assert "15 years" in content
    assert "ui-interaction-discussion" in content
    assert "ASCII sketches" in content
```

- [ ] **Step 2: Add a focused discussion UI stage test**

In `tests/test_alignment_templates.py`, after `test_discussion_staged_cognition_gate_and_technical_options_contract`, add:

```python
def test_discussion_offers_optional_ui_interaction_stage_for_ui_requirements() -> None:
    content = _read("templates/commands/discussion.md")
    shell = _read("templates/command-partials/discussion/shell.md")
    state = _read("templates/discussion-state-template.md")
    combined = "\n".join([content, shell, state])
    lowered = combined.lower()

    assert "ui-interaction-discussion" in combined
    assert "ui_discussion_status: not_applicable | offered | accepted | skipped | completed | deferred" in state
    assert "after functional discussion is stable" in lowered
    assert "optional ui and interaction discussion" in lowered
    assert "senior ui and interaction designer" in lowered
    assert "15 years" in combined
    assert "ascii sketches" in lowered
    assert "markdown is the primary carrier" in lowered
    assert "ui_sketches_present" in combined
    assert "ui_sketch_summary" in combined
    assert "ui_sketch_reference" in combined
    assert "not a blocking gate" in lowered or "not a blocker" in lowered
```

- [ ] **Step 3: Extend the discussion state template independence test**

In `test_discussion_state_template_is_independent_from_feature_workflow_state`, add:

```python
    assert "ui-interaction-discussion" in content
    assert "ui_discussion_status: not_applicable | offered | accepted | skipped | completed | deferred" in content
```

- [ ] **Step 4: Extend integration command assertions**

In `tests/integrations/test_integration_base_toml.py`, inside `_assert_discussion_contract`, add:

```python
    assert "ui-interaction-discussion" in command_content
    assert "optional UI and interaction discussion" in command_content
    assert "senior UI and interaction designer" in command_content
    assert "ASCII sketches" in command_content
    assert "ui_sketches_present" in command_content
```

- [ ] **Step 5: Extend Codex generated asset assertions**

In `tests/integrations/test_integration_codex.py`, inside `test_codex_init_installs_lightweight_discussion_recovery_contract`, add these assertions after `generated_lower` is created:

```python
        assert "ui-interaction-discussion" in generated_discussion
        assert "senior UI and interaction designer" in generated_discussion
        assert "ASCII sketches" in generated_discussion
        assert "ui_sketches_present" in generated_discussion
```

Add this assertion near the existing `state_template` assertions:

```python
        assert "ui_discussion_status: not_applicable | offered | accepted | skipped | completed | deferred" in state_template
```

- [ ] **Step 6: Run discussion tests and verify they fail**

Run:

```bash
pytest tests/test_alignment_templates.py::test_discussion_command_contract_is_pre_spec_and_resumable tests/test_alignment_templates.py::test_discussion_offers_optional_ui_interaction_stage_for_ui_requirements tests/test_alignment_templates.py::test_discussion_state_template_is_independent_from_feature_workflow_state tests/integrations/test_integration_codex.py::TestCodexAutoPromote::test_codex_init_installs_lightweight_discussion_recovery_contract -q
pytest tests/integrations/test_integration_base_toml.py -k discussion_command_preserves_pre_specification_contract -q
```

Expected: FAIL because the templates do not yet include `ui-interaction-discussion`, `ui_discussion_status`, or UI sketch fields.

If the TOML integration test class name differs, run:

```bash
pytest tests/integrations/test_integration_base_toml.py -k discussion_command_preserves_pre_specification_contract -q
```

Expected: FAIL for the same missing UI-stage strings.

## Task 4: Implement Discussion UI Stage Templates

**Files:**
- Modify: `templates/discussion-state-template.md`
- Modify: `templates/commands/discussion.md`
- Modify: `templates/command-partials/discussion/shell.md`

- [ ] **Step 1: Add the UI stage and status to the state template**

In `templates/discussion-state-template.md`, update the `current_stage` line to:

```markdown
- current_stage: context-intake | product-framing | context-grounding | question-loop | technical-options | ui-interaction-discussion | handoff-assessment | handoff-draft | handoff-self-review | handoff-user-review | handoff-ready
```

After the `readiness_note` line, add:

```markdown
- ui_discussion_status: not_applicable | offered | accepted | skipped | completed | deferred
```

- [ ] **Step 2: Update the discussion role with UI expertise**

In `templates/commands/discussion.md`, under `## Role`, add this bullet after the technical expert perspective:

```markdown
- UI and interaction design perspective: when the requirement includes user-interface surfaces, guide the user like a senior UI and interaction designer with 15 years of practical UI delivery experience, using natural-language requirements and optional ASCII sketches that downstream agents can implement.
```

- [ ] **Step 3: Add UI stage to the discussion flow**

In `templates/commands/discussion.md`, insert this stage after `technical-options` and before `handoff-assessment`. Renumber the later stages so `handoff-ready` remains the final stage:

```markdown
6. `ui-interaction-discussion`
   - Enter only after functional discussion is stable and the matured requirement includes UI-facing scope such as screens, components, layout, navigation, visual hierarchy, interaction states, user-facing copy, accessibility, or workflow feedback.
   - Offer the stage as an optional UI and interaction discussion before handoff assessment. If the user skips it, record `ui_discussion_status: skipped` or `deferred` and continue when other handoff gates are satisfied.
   - Act as a senior UI and interaction designer with 15 years of practical project experience. Guide the user through primary screens, user journey, information hierarchy, component responsibilities, key interactions, loading, empty, success, warning, error, disabled, permission, responsive, density, accessibility, keyboard, focus, and copy expectations when relevant.
   - Use natural language first. ASCII sketches are allowed when they clarify rough screen structure, layout grouping, state transitions, or flow relationships for downstream implementers.
```

- [ ] **Step 4: Add a dedicated UI discussion section**

In `templates/commands/discussion.md`, add this section after `## Technical Options Board` and before `## Handoff Assessment`:

```markdown
## Optional UI and Interaction Discussion

When the functional discussion is stable and the requirement includes UI-facing scope, offer an optional `ui-interaction-discussion` stage before handoff assessment.

Trigger examples:

- screens, pages, views, panels, dashboards, forms, components, or navigation
- user journeys, interaction flows, state transitions, or workflow feedback
- visual hierarchy, layout, density, responsive behavior, or information architecture
- loading, empty, success, warning, error, disabled, or permission states
- accessibility, keyboard behavior, focus management, or user-facing copy that affects interaction quality

If the user accepts, set `ui_discussion_status: accepted` and guide the discussion as a senior UI and interaction designer with 15 years of practical UI delivery experience. Ask only high-impact UI questions. Provide opinionated recommendations when the user benefits from design judgment, and preserve confirmed UI decisions in `requirements.md`, `technical-options.md`, `open-questions.md`, and the unified handoff pair.

If the user skips, set `ui_discussion_status: skipped` or `deferred`. Skipping the UI pass is not a blocking gate unless the feature cannot be specified without a UI decision. Preserve deferred UI decisions in `open-questions.md` and in the handoff's blocking or soft unknowns.

ASCII sketches are allowed as optional text guidance. Use them to show rough layout, grouping, or flow, not pixel-perfect design. Markdown is the primary carrier for sketches because it preserves multi-line readability. JSON must not duplicate raw multi-line sketches; use `ui_sketches_present`, `ui_sketch_summary`, and `ui_sketch_reference` to point back to the Markdown section.
```

- [ ] **Step 5: Add UI fields to the handoff instructions**

In `templates/commands/discussion.md`, under `## Handoff To sp-specify`, add these bullets to the "The handoff must include" list:

```markdown
- `ui_discussion`: `ui_discussion_status`, confirmed UI decisions, deferred UI decisions, interaction expectations, state requirements, accessibility expectations, and whether ASCII sketches are present
- `ui_sketch_reference`: Markdown section reference for ASCII sketches when `ui_sketches_present` is true
```

In `## Handoff JSON Companion`, add:

```markdown
For UI-facing work, the JSON companion must preserve `ui_discussion_status`, `ui_sketches_present`, `ui_sketch_summary`, and `ui_sketch_reference`. Markdown is the primary carrier for raw ASCII sketches; JSON records only structured status, summary, and reference fields.
```

- [ ] **Step 6: Update shell partial summary**

In `templates/command-partials/discussion/shell.md`, add this process bullet after "Refresh `requirements.md`, `technical-options.md`, `project-context.md`, and `open-questions.md` only at semantic checkpoints.":

```markdown
- After functional discussion is stable, offer an optional UI and interaction discussion for UI-facing requirements; record `ui_discussion_status` and preserve confirmed or deferred UI decisions without making the UI pass a mandatory handoff gate.
```

Add this output-contract bullet after "Preserve `coverage_status`, `planning_gate_status`, `hard_unknown_count`, and `open_conflict_count` for the downstream fidelity gate.":

```markdown
- For UI-facing work, preserve `ui_discussion_status`; confirmed UI decisions; deferred UI unknowns; and Markdown-carried ASCII sketches with JSON fields `ui_sketches_present`, `ui_sketch_summary`, and `ui_sketch_reference`.
```

- [ ] **Step 7: Run discussion tests and verify they pass**

Run:

```bash
pytest tests/test_alignment_templates.py::test_discussion_command_contract_is_pre_spec_and_resumable tests/test_alignment_templates.py::test_discussion_offers_optional_ui_interaction_stage_for_ui_requirements tests/test_alignment_templates.py::test_discussion_state_template_is_independent_from_feature_workflow_state tests/integrations/test_integration_codex.py::TestCodexAutoPromote::test_codex_init_installs_lightweight_discussion_recovery_contract -q
pytest tests/integrations/test_integration_base_toml.py -k discussion_command_preserves_pre_specification_contract -q
```

Expected: PASS.

- [ ] **Step 8: Commit discussion changes**

Run:

```bash
git add templates/discussion-state-template.md templates/commands/discussion.md templates/command-partials/discussion/shell.md tests/test_alignment_templates.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_codex.py
git commit -m "feat: add optional ui discussion stage"
```

## Task 5: Run Focused Cross-Surface Verification

**Files:**
- No source edits expected unless verification exposes drift.

- [ ] **Step 1: Run template alignment and constitution regression tests**

Run:

```bash
pytest tests/test_alignment_templates.py tests/test_constitution_defaults.py tests/test_constitution_profiles_cli.py -q
```

Expected: PASS.

- [ ] **Step 2: Run integration rendering tests touched by discussion templates**

Run:

```bash
pytest tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_codex.py -q
```

Expected: PASS.

- [ ] **Step 3: Check generated template packaging references**

Run:

```bash
rg -n "discussion-state-template.md|templates/constitution|templates/commands|templates/command-partials" pyproject.toml
```

Expected: output includes the existing package include entries for `templates/constitution`, `templates/constitution-template.md`, and `templates/discussion-state-template.md`. No packaging edit is expected for this change.

- [ ] **Step 4: Review diff for scope creep**

Run:

```bash
git diff --stat HEAD~2..HEAD
git diff HEAD~2..HEAD -- templates/constitution/profiles/product.yml templates/constitution/profiles/library.yml templates/constitution/profiles/minimal.yml templates/constitution/profiles/regulated.yml templates/constitution-template.md templates/discussion-state-template.md templates/commands/discussion.md templates/command-partials/discussion/shell.md tests/test_constitution_defaults.py tests/test_constitution_profiles_cli.py tests/test_alignment_templates.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_codex.py
```

Expected: diff contains only constitution style guidance, profile version bumps, UI discussion stage guidance, state field additions, and matching tests.

- [ ] **Step 5: Commit any verification-only corrections**

If Step 1 or Step 2 exposed a small wording mismatch and you fixed it, commit with:

```bash
git add templates tests
git commit -m "test: align workflow template assertions"
```

Expected: no commit is needed if all tests passed without further edits.

## Self-Review Checklist

- Spec coverage: Task 2 covers all four built-in constitution profiles. Task 4 covers optional `ui-interaction-discussion`, senior UI persona, natural-language guidance, ASCII sketches, Markdown/JSON boundary, and skipped/deferred UI status.
- Artifact coverage: `discussion-state.md` gains `ui_discussion_status` and `current_stage` gains `ui-interaction-discussion`.
- Handoff coverage: Markdown carries raw ASCII sketches; JSON carries `ui_sketches_present`, `ui_sketch_summary`, and `ui_sketch_reference`.
- Existing contract preservation: `sp-discussion` remains pre-spec, handoff remains explicit-user-request only, and `sp-specify` is not invoked automatically.
- Verification coverage: constitution defaults, CLI materialization, template alignment, TOML rendering, and Codex generated assets are all covered by targeted tests.
