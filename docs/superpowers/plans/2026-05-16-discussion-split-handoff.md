# Discussion Split Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved discussion split handoff design so `sp-discussion` can assess large discussions, maintain a candidate backlog, and hand one bounded candidate at a time to `sp-specify`.

**Architecture:** This is a template and generated-surface change, not a new runtime workflow. `sp-discussion` owns assessment, split-plan, candidate handoff, and latest-copy guidance under `.specify/discussions/<slug>/`; `sp-specify` consumes candidate metadata and enforces candidate scope boundaries through its command template and brainstorming handoff JSON shape.

**Tech Stack:** Markdown command templates, JSON artifact templates, pytest template/integration tests, README/handbook docs.

---

## Scope Check

The spec covers one workflow contract improvement: discussion-to-specify handoff splitting without adding a new workflow command. It touches several generated surfaces, but they all serve the same behavior. Do not split this into multiple implementation plans.

## File Structure

Modify these files:

- `tests/test_alignment_templates.py`: primary regression tests for shared template contracts.
- `tests/integrations/test_integration_base_markdown.py`: generated Markdown command contract assertions.
- `tests/integrations/test_integration_base_toml.py`: generated TOML command contract assertions.
- `tests/integrations/test_integration_base_skills.py`: generated skills contract assertions.
- `tests/test_specify_guidance_docs.py`: guidance docs positioning tests for discussion continuation.
- `templates/commands/discussion.md`: source-of-truth `sp-discussion` command guidance.
- `templates/command-partials/discussion/shell.md`: concise generated shell guidance for `sp-discussion`.
- `templates/discussion-state-template.md`: durable discussion session state template.
- `templates/commands/specify.md`: `sp-specify` discussion handoff intake guidance.
- `templates/brainstorming-handoff-specify-template.json`: active feature copy shape for discussion/candidate metadata.
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`: routing guidance for rough ideas and large directions.
- `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`: staged cognition guidance for split rationale.
- `README.md`: user-facing workflow docs.
- `PROJECT-HANDBOOK.md`: repository source-of-truth guidance.
- `templates/project-handbook-template.md`: generated handbook guidance.

Inspect but do not modify unless tests prove it is needed:

- `src/specify_cli/hooks/artifact_validation.py`: currently validates required artifact presence for `brainstorming/handoff-to-specify.json`, not detailed JSON schema. Do not add runtime mismatch validation in this pass unless an existing test already expects schema-level validation.

## Task 1: Add Failing Shared Template Tests

**Files:**
- Modify: `tests/test_alignment_templates.py`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Add failing tests for discussion split artifacts**

Append these tests after `test_discussion_command_contract_is_pre_spec_and_resumable`:

```python
def test_discussion_command_supports_handoff_assessment_and_split_backlog() -> None:
    content = _read_project_file("templates/commands/discussion.md")
    lowered = content.lower()

    assert "handoff-assessment.md" in content
    assert "split-plan.md" in content
    assert "handoffs/CAND-001-handoff-to-specify.md" in content
    assert "handoffs/CAND-001-handoff-to-specify.json" in content
    assert "`handoff-to-specify.json`" in content
    assert "ready-for-specify" in content
    assert "split-required" in content
    assert "continue-discussion" in content
    assert "candidate backlog" in lowered
    assert "latest selected candidate" in lowered
    assert "full readable copy" in lowered
    assert "must not be a pointer-only file" in lowered
    assert "must not mark the discussion `completed` merely because the first candidate handoff was written" in content
    assert "Do not add, recommend, or route to `sp-split`" in content
```

- [ ] **Step 2: Add failing tests for discussion shell partial**

Append this test near the discussion command tests:

```python
def test_discussion_shell_partial_mentions_split_outputs_without_single_handoff_assumption() -> None:
    content = _read("templates/command-partials/discussion/shell.md")
    lowered = content.lower()

    assert "handoff-assessment.md" in content
    assert "split-plan.md" in content
    assert "handoffs/CAND-001-handoff-to-specify.md" in content
    assert "`handoff-to-specify.md`" in content
    assert "`handoff-to-specify.json`" in content
    assert "candidate backlog" in lowered
    assert "latest selected candidate copy" in lowered
    assert "not the only handoff output" in lowered
```

- [ ] **Step 3: Add failing tests for discussion state split fields**

Extend `test_discussion_state_template_is_independent_from_feature_workflow_state` with these assertions:

```python
    assert "handoff-assessment" in content
    assert "split-mode" in content
    assert "candidate-selection" in content
    assert "## Handoff Assessment" in content
    assert "handoff_assessment_status: not-run | ready-for-specify | split-required | continue-discussion" in content
    assert "## Split Plan" in content
    assert "split_plan_status: none | active | partially-handed-off | completed | blocked" in content
    assert "active_candidate: CAND-xxx | none" in content
    assert "next_recommended_candidate: CAND-xxx | none" in content
    assert "handoffs/*.md" in content
    assert "handoffs/*.json" in content
```

- [ ] **Step 4: Add failing tests for candidate handoff intake**

Extend `test_specify_consumes_explicit_discussion_handoff_without_bypassing_kernel` with these assertions:

```python
    assert ".specify/discussions/<slug>/handoffs/CAND-001-handoff-to-specify.md" in content
    assert "CAND-001-handoff-to-specify.json" in content
    assert "candidate_id" in content
    assert "candidate_title" in content
    assert "source_split_plan" in content
    assert "stage_scope_boundary" in content
    assert "deferred_candidates" in content
    assert "latest selected candidate" in lowered
    assert "same-stem JSON companion" in content
    assert "current feature spec covers one candidate" in lowered
    assert "sibling candidates" in lowered
    assert "handoff integrity error" in lowered
```

- [ ] **Step 5: Add failing test for brainstorming handoff JSON template**

Append this test near the existing brainstorming template tests:

```python
def test_brainstorming_handoff_template_supports_discussion_candidate_metadata() -> None:
    template = json.loads(_read("templates/brainstorming-handoff-specify-template.json"))

    assert template["version"] == 1
    assert template["entry_source"] == "none"
    assert template["discussion_slug"] is None
    assert template["candidate_id"] is None
    assert template["candidate_title"] is None
    assert template["source_split_plan"] is None
    assert template["source_handoff"] is None
    assert template["source_handoff_json"] is None
    assert template["prior_candidates"] == []
    assert template["deferred_candidates"] == []
    assert template["stage_scope_boundary"] is None
    assert template["reopen_condition"] is None
    assert template["must_preserve"] == []
    assert template["conflicts"] == []
    assert template["coverage_status"] == "not-applicable"
    assert template["handoff_integrity"] == "not-checked"
```

If `json` is not already imported at the top of `tests/test_alignment_templates.py`, add:

```python
import json
```

- [ ] **Step 6: Run tests and verify red**

Run:

```powershell
pytest tests/test_alignment_templates.py -q
```

Expected: FAIL with missing strings or missing JSON keys from the new tests.

- [ ] **Step 7: Commit red tests**

```powershell
git add tests/test_alignment_templates.py
git commit -m "test: cover discussion split handoff templates"
```

## Task 2: Add Failing Generated Integration Contract Tests

**Files:**
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Test: `tests/integrations/test_integration_base_markdown.py`
- Test: `tests/integrations/test_integration_base_toml.py`
- Test: `tests/integrations/test_integration_base_skills.py`

- [ ] **Step 1: Extend Markdown discussion contract assertions**

In `tests/integrations/test_integration_base_markdown.py`, update `_assert_discussion_contract`:

```python
def _assert_discussion_contract(command_content: str) -> None:
    command_lower = command_content.lower()

    assert "sp-discussion" in command_content
    assert ".specify/discussions/<slug>/" in command_content
    assert "discussion-state.md" in command_content
    assert "handoff-assessment.md" in command_content
    assert "split-plan.md" in command_content
    assert "handoffs/CAND-001-handoff-to-specify.md" in command_content
    assert "handoffs/CAND-001-handoff-to-specify.json" in command_content
    assert "`handoff-to-specify.md`" in command_content
    assert "`handoff-to-specify.json`" in command_content
    assert (
        "explicit user" in command_lower
        or "user explicitly" in command_lower
        or "explicit-user-request" in command_lower
    )
    assert "senior technical expert" in command_lower
    assert "senior product manager" in command_lower
    assert "candidate backlog" in command_lower
    assert "latest selected candidate" in command_lower
```

- [ ] **Step 2: Apply the same assertion body to TOML integration tests**

In `tests/integrations/test_integration_base_toml.py`, replace `_assert_discussion_contract` with:

```python
def _assert_discussion_contract(command_content: str) -> None:
    command_lower = command_content.lower()

    assert "sp-discussion" in command_content
    assert ".specify/discussions/<slug>/" in command_content
    assert "discussion-state.md" in command_content
    assert "handoff-assessment.md" in command_content
    assert "split-plan.md" in command_content
    assert "handoffs/CAND-001-handoff-to-specify.md" in command_content
    assert "handoffs/CAND-001-handoff-to-specify.json" in command_content
    assert "`handoff-to-specify.md`" in command_content
    assert "`handoff-to-specify.json`" in command_content
    assert (
        "explicit user" in command_lower
        or "user explicitly" in command_lower
        or "explicit-user-request" in command_lower
    )
    assert "senior technical expert" in command_lower
    assert "senior product manager" in command_lower
    assert "candidate backlog" in command_lower
    assert "latest selected candidate" in command_lower
```

- [ ] **Step 3: Apply the same assertion body to skills integration tests**

In `tests/integrations/test_integration_base_skills.py`, replace `_assert_discussion_contract` with this skill-specific version:

```python
def _assert_discussion_contract(skill_content: str) -> None:
    skill_lower = skill_content.lower()

    assert "sp-discussion" in skill_content
    assert ".specify/discussions/<slug>/" in skill_content
    assert "discussion-state.md" in skill_content
    assert "handoff-assessment.md" in skill_content
    assert "split-plan.md" in skill_content
    assert "handoffs/CAND-001-handoff-to-specify.md" in skill_content
    assert "handoffs/CAND-001-handoff-to-specify.json" in skill_content
    assert "`handoff-to-specify.md`" in skill_content
    assert "`handoff-to-specify.json`" in skill_content
    assert (
        "explicit user" in skill_lower
        or "user explicitly" in skill_lower
        or "explicit-user-request" in skill_lower
    )
    assert "senior technical expert" in skill_lower
    assert "senior product manager" in skill_lower
    assert "candidate backlog" in skill_lower
    assert "latest selected candidate" in skill_lower
```

- [ ] **Step 4: Run integration tests and verify red**

Run:

```powershell
pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py -q
pytest tests/integrations/test_integration_codebuddy.py::TestCodebuddyIntegration::test_discussion_command_preserves_pre_specification_contract tests/integrations/test_integration_tabnine.py::TestTabnineIntegration::test_discussion_command_preserves_pre_specification_contract tests/integrations/test_integration_codex.py::TestCodexIntegration::test_discussion_skill_preserves_pre_specification_contract -q
```

Expected: the base mixin files may collect little or no concrete coverage by themselves; the concrete CodeBuddy, Tabnine, and Codex checks must FAIL because generated discussion commands do not yet mention assessment, split plans, candidate handoffs, and JSON companions.

- [ ] **Step 5: Commit red tests**

```powershell
git add tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py
git commit -m "test: cover generated discussion split handoff contracts"
```

## Task 3: Update sp-discussion Command And Shell Partial

**Files:**
- Modify: `templates/commands/discussion.md`
- Modify: `templates/command-partials/discussion/shell.md`
- Test: `tests/test_alignment_templates.py`
- Test: `tests/integrations/test_integration_base_markdown.py`
- Test: `tests/integrations/test_integration_base_toml.py`
- Test: `tests/integrations/test_integration_base_skills.py`

- [ ] **Step 1: Update discussion command frontmatter**

In `templates/commands/discussion.md`, replace `primary_outputs` and `default_handoff` with:

```yaml
  primary_outputs: '`.specify/discussions/<slug>/discussion-state.md`, `discussion-log.md`, `requirements.md`, `technical-options.md`, `project-context.md`, `open-questions.md`, `handoff-assessment.md` when handoff is requested, `split-plan.md` and `handoffs/CAND-001-handoff-to-specify.{md,json}` when splitting is required, plus latest-copy `handoff-to-specify.{md,json}` only after a bounded candidate is selected.'
  default_handoff: Stay in sp-discussion until the user explicitly asks to hand off or continue the next stage; then run handoff assessment and either write a bounded latest-copy handoff-to-specify.{md,json}, enter split mode, or continue discussion.
```

- [ ] **Step 2: Add no-new-workflow guardrail**

In `## Hard Boundaries`, add:

```markdown
- Do not add, recommend, or route to `sp-split`, `sp-breakdown`, or any split-only workflow; split handling stays inside `sp-discussion`.
```

- [ ] **Step 3: Update session store required files**

Replace the `Required files:` list with:

```markdown
Required files:

- `discussion-state.md`
- `discussion-log.md`
- `requirements.md`
- `technical-options.md`
- `project-context.md`
- `open-questions.md`
- `handoff-assessment.md` only after explicit user request to hand off or continue to the next stage
- `split-plan.md` only when handoff assessment returns `split-required`
- `handoffs/CAND-001-handoff-to-specify.md` and `handoffs/CAND-001-handoff-to-specify.json` when a split candidate is selected
- latest-copy `handoff-to-specify.md` and `handoff-to-specify.json` only after a bounded handoff or bounded candidate handoff is selected
```

- [ ] **Step 4: Replace discussion flow with assessment-aware flow**

Replace the `## Discussion Flow` numbered list with:

```markdown
## Discussion Flow

1. Create or resume the discussion session.
2. Record the user's raw idea in `discussion-log.md`.
3. Ask one high-impact question at a time.
4. Keep `open-questions.md` grouped by blocking level.
5. Refresh `requirements.md` whenever a material requirement decision changes.
6. Enter technical options only when implementation strategy affects the requirement.
7. When the user explicitly asks to hand off, feed the discussion to `sp-specify`, or continue the next stage, run handoff assessment before writing any handoff.
8. If assessment returns `ready-for-specify`, write a bounded `handoff-to-specify.md` and `handoff-to-specify.json`.
9. If assessment returns `split-required`, write or refresh `split-plan.md`, keep the discussion incomplete, ask the user to select one candidate, and then write candidate-specific handoff files plus latest-copy handoff files.
10. If assessment returns `continue-discussion`, return to the question loop.
```

- [ ] **Step 5: Insert handoff assessment section**

Insert this section before `## Handoff To sp-specify`:

```markdown
## Handoff Assessment

Handoff assessment is explicit-user-request only. Run it when the user says the discussion is done, asks to hand off, asks to feed the result to `sp-specify`, or asks to continue the next stage.

Write or refresh `handoff-assessment.md` with:

- decision status: `ready-for-specify`, `split-required`, or `continue-discussion`
- rationale citing `requirements.md`, `technical-options.md`, `project-context.md`, `open-questions.md`, or explicit user confirmation
- assessment dimensions: feature coherence, independent value, planning shape, implementation dependency, validation split, and risk profile
- required next action: `write-handoff`, `enter-split-mode`, or `continue-discussion`

Assessment outcomes:

- `ready-for-specify`: the mature discussion describes one coherent feature boundary. Write bounded latest-copy `handoff-to-specify.md` and `handoff-to-specify.json`.
- `split-required`: the mature discussion contains multiple independently valuable candidates, release tracks, business domains, validation packages, or implementation chains. Enter split mode and write `split-plan.md`.
- `continue-discussion`: the issue is missing clarity rather than overbreadth. Return to the question loop.
```

- [ ] **Step 6: Insert split mode and continuation section**

Insert after the handoff assessment section:

```markdown
## Split Mode Inside sp-discussion

When assessment returns `split-required`, write or refresh `split-plan.md`. The split plan is a candidate backlog, not an implementation plan and not a task list.

Each candidate must have:

- stable ID such as `CAND-001`
- title
- status: `not-started | handoff-ready | handed-off | in-progress | completed | deferred | blocked`
- goal
- scope
- non-goals
- acceptance signals
- dependencies
- risks
- recommended next step: `sp-specify | continue-discussion | deep-research-later | defer`
- handoff path
- optional feature directory
- completion evidence

`split-plan.md` must include `Original Direction`, `Split Rationale`, `Candidate Backlog`, `Recommended Sequence`, and `Resume Guidance`.

A discussion with an active split backlog remains incomplete until every candidate is `completed`, `deferred`, or explicitly abandoned by the user. Do not mark the discussion `completed` merely because the first candidate handoff was written.

When the user returns and asks for the next stage, read `split-plan.md`, inspect candidate statuses, recommend the next candidate whose dependencies are completed or waived, and ask the user to choose when more than one candidate is viable. If completion evidence for a previous candidate is missing, ask whether it is completed, in progress, blocked, or only handed off.
```

- [ ] **Step 7: Replace handoff section**

Replace `## Handoff To sp-specify` with:

```markdown
## Handoff To sp-specify

Handoff is explicit-user-request only and follows handoff assessment.

For `ready-for-specify`, write latest-copy `handoff-to-specify.md` and `handoff-to-specify.json` with one bounded feature scope.

For `split-required`, first write `split-plan.md`. After the user selects one candidate, write canonical candidate handoffs:

- `handoffs/CAND-001-handoff-to-specify.md`
- `handoffs/CAND-001-handoff-to-specify.json`

Then refresh latest-copy compatibility files in the same operation:

- `handoff-to-specify.md`
- `handoff-to-specify.json`

The latest-copy files must be full readable copies of the selected candidate handoff and JSON. They must not be pointer-only files because existing `sp-specify` intake expects the supplied path to contain the user-reviewable handoff artifact.

Candidate handoff Markdown must include:

- frontmatter: `source_command: sp-discussion`, `discussion_slug`, `candidate_id`, `candidate_title`, `status: handoff-ready`, `source_split_plan`, `updated_at`, and `source_files`
- candidate scope
- confirmed product goal and users
- in scope
- out of scope
- acceptance signals
- prior candidates and dependencies
- deferred candidates
- project-context evidence and inference notes
- open questions with blocking levels
- Must-Preserve Ledger
- instructions for `sp-specify`

Candidate JSON must mirror the Markdown and include `discussion_slug`, `candidate_id`, `candidate_title`, `source_split_plan`, `source_markdown`, `latest_legacy_markdown`, `prior_candidates`, `deferred_candidates`, `stage_scope_boundary`, `reopen_condition`, and `must_preserve`.

Markdown and JSON must agree on `discussion_slug`, `candidate_id`, `candidate_title`, `status`, `source_split_plan`, and every Must-Preserve Ledger item ID, type, claim, blocking level, owner, latest resolve phase, and status.

After writing the handoff, tell the user to invoke the generated integration's `sp-specify` command form with the bounded handoff path. Do not invoke it yourself.
```

- [ ] **Step 8: Update shell partial**

In `templates/command-partials/discussion/shell.md`, update `## Process` to:

```markdown
## Process

- Create or resume the discussion session.
- Ask one high-impact question at a time.
- Preserve key decisions in `discussion-log.md`.
- Keep `requirements.md`, `technical-options.md`, `project-context.md`, and `open-questions.md` current.
- When the user explicitly asks to hand off or continue the next stage, write `handoff-assessment.md` first.
- If assessment returns `split-required`, maintain `split-plan.md` as the candidate backlog and generate `handoffs/CAND-001-handoff-to-specify.{md,json}` only after the user selects a candidate.
- Refresh latest selected candidate copy files `handoff-to-specify.md` and `handoff-to-specify.json` together for compatibility.
```

Update `## Output Contract` to include:

```markdown
- Keep `handoff-to-specify.md` and `handoff-to-specify.json` as latest selected candidate copy files, not the only handoff output.
- Keep candidate-specific handoffs under `handoffs/` canonical when split mode is active.
```

- [ ] **Step 9: Run focused tests and verify green for this task**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_discussion_command_contract_is_pre_spec_and_resumable tests/test_alignment_templates.py::test_discussion_command_supports_handoff_assessment_and_split_backlog tests/test_alignment_templates.py::test_discussion_shell_partial_mentions_split_outputs_without_single_handoff_assumption -q
```

Expected: PASS.

- [ ] **Step 10: Commit**

```powershell
git add templates/commands/discussion.md templates/command-partials/discussion/shell.md
git commit -m "docs: add discussion split handoff guidance"
```

## Task 4: Update Discussion State Template

**Files:**
- Modify: `templates/discussion-state-template.md`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Replace Session Routing current_stage line**

In `templates/discussion-state-template.md`, replace the `current_stage` line with:

```markdown
- current_stage: session-intake | idea-framing | context-grounding | question-loop | technical-options | requirements-synthesis | handoff-assessment | split-mode | candidate-selection | handoff-on-request
```

- [ ] **Step 2: Add handoff assessment and split plan state sections**

Insert this block after `## Session Selection`:

```markdown
## Handoff Assessment

- handoff_assessment_status: not-run | ready-for-specify | split-required | continue-discussion
- handoff_assessment_path: handoff-assessment.md | none
- handoff_assessment_decided_at: [ISO-8601 timestamp or none]

## Split Plan

- split_plan_status: none | active | partially-handed-off | completed | blocked
- split_plan_path: split-plan.md | none
- active_candidate: CAND-xxx | none
- next_recommended_candidate: CAND-xxx | none
- backlog_completion_rule: discussion remains incomplete until every candidate is completed, deferred, or explicitly abandoned
```

- [ ] **Step 3: Extend allowed artifact writes**

Add these bullets under `## Allowed Artifact Writes`:

```markdown
- handoff-assessment.md only after explicit user request
- split-plan.md only when handoff assessment returns split-required
- handoffs/*.md only after candidate selection
- handoffs/*.json only after candidate selection
- handoff-to-specify.json only after explicit user request and bounded handoff selection
```

- [ ] **Step 4: Extend forbidden actions**

Add:

```markdown
- add, recommend, or route to sp-split
- mark discussion completed while split-plan.md has unfinished candidates
- write pointer-only handoff-to-specify.md or handoff-to-specify.json
```

- [ ] **Step 5: Extend authoritative files and handoff fields**

Under `## Authoritative Files`, add:

```markdown
- handoff-assessment.md when present
- split-plan.md when present
- handoffs/CAND-xxx-handoff-to-specify.md when present
- handoffs/CAND-xxx-handoff-to-specify.json when present
```

Under `## Handoff`, replace the fields with:

```markdown
- handoff_to_specify: none
- handoff_to_specify_json: none
- active_candidate_handoff: none
- active_candidate_handoff_json: none
- handoff_requested_by_user: false
- next_command: none
```

- [ ] **Step 6: Run focused state template test**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_discussion_state_template_is_independent_from_feature_workflow_state -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add templates/discussion-state-template.md
git commit -m "docs: track discussion split state"
```

## Task 5: Update sp-specify Intake And Brainstorming Handoff JSON

**Files:**
- Modify: `templates/commands/specify.md`
- Modify: `templates/brainstorming-handoff-specify-template.json`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Replace Discussion Handoff Intake section**

In `templates/commands/specify.md`, replace the entire `## Discussion Handoff Intake` section with:

```markdown
## Discussion Handoff Intake

If the user invokes `sp-specify` with an explicit path to `.specify/discussions/<slug>/handoff-to-specify.md`, `.specify/discussions/<slug>/handoffs/CAND-001-handoff-to-specify.md`, or pastes a discussion handoff block, read that handoff before parsing the feature request.

- Treat the discussion handoff as an authoritative input to the brainstorming kernel, not a bypass around it.
- When the supplied path is Markdown, look for the same-stem JSON companion first. For a candidate handoff, read `handoffs/CAND-001-handoff-to-specify.json`. For the legacy latest handoff, read `handoff-to-specify.json`.
- If candidate Markdown and candidate JSON disagree on `discussion_slug`, `candidate_id`, `candidate_title`, `status`, `source_split_plan`, or Must-Preserve Ledger identity fields, block with a handoff integrity error and tell the user to refresh the `sp-discussion` handoff.
- If legacy latest Markdown and legacy latest JSON disagree on the selected `candidate_id`, block rather than choosing one representation.
- If candidate Markdown exists but candidate JSON is missing, reconstruct the active feature copy into `brainstorming/handoff-to-specify.json`, record the reconstruction source, and report a handoff repair advisory.
- If only JSON exists and Markdown is missing, reject the handoff because the user-reviewable source is absent.
- Record `entry_source: sp-discussion` and the handoff path or pasted discussion handoff marker in the generated feature artifacts.
- When `candidate_id` is present, record `discussion_slug`, `candidate_id`, `candidate_title`, `source_split_plan`, `handoff_path`, `prior_candidates`, `deferred_candidates`, `stage_scope_boundary`, and `reopen_condition` in `brainstorming/handoff-to-specify.json`, `context.md`, `references.md`, or `workflow-state.md` according to artifact responsibility.
- The current feature spec covers one candidate. Sibling candidates named in `split-plan.md` are out of scope unless the user returns to `sp-discussion` and selects a new candidate handoff.
- If the user asks inside `sp-specify` to include a sibling candidate, run the decomposition gate. Continue only for internal capability decomposition within the selected candidate. If the request crosses the candidate boundary, stop and tell the user to return to `sp-discussion` to update or select the candidate.
- Preserve confirmed requirements, confirmed non-goals, settled decisions, selected technical direction, candidate boundaries, prior dependencies, and deferred sibling candidates in `facts.json`, `intent.json`, `complexity.json`, `handoff-to-specify.json`, `specify-draft.md`, `spec.md`, `alignment.md`, `context.md`, or `references.md` according to the existing `sp-specify` artifact responsibilities.
- Convert open questions from the handoff into explicit unknowns with `field`, `question`, `blocking_level`, `resolver`, `latest_resolve_phase`, and `status`.
- Cite the discussion handoff, candidate JSON companion when present, `source_split_plan`, and relevant `project-context.md` evidence in `references.md` or `context.md`.
- Do not re-ask settled discussion questions unless repository evidence, constitution rules, or user correction contradicts the handoff.
- If a settled discussion conclusion is reopened, record the reopen reason before changing the derived spec package.
- Do not directly update `split-plan.md` from `sp-specify`; `sp-discussion` owns discussion backlog state.
```

- [ ] **Step 2: Update brainstorming handoff JSON template**

Replace `templates/brainstorming-handoff-specify-template.json` with:

```json
{
  "version": 1,
  "status": "pending",
  "entry_source": "none",
  "source_handoff": null,
  "source_handoff_json": null,
  "discussion_slug": null,
  "candidate_id": null,
  "candidate_title": null,
  "source_split_plan": null,
  "prior_candidates": [],
  "deferred_candidates": [],
  "stage_scope_boundary": null,
  "reopen_condition": null,
  "must_preserve": [],
  "conflicts": [],
  "coverage_status": "not-applicable",
  "handoff_integrity": "not-checked",
  "facts_file": "brainstorming/facts.json",
  "route_file": "brainstorming/route.json",
  "intent_file": "brainstorming/intent.json",
  "complexity_file": "brainstorming/complexity.json",
  "soft_unknowns": [],
  "compile_ready": false
}
```

- [ ] **Step 3: Inspect artifact validation**

Run:

```powershell
rg -n "handoff-to-specify|must_preserve|candidate_id|source_split_plan" src/specify_cli/hooks/artifact_validation.py tests/hooks
```

Expected: current hook validation only requires `brainstorming/handoff-to-specify.json` presence and does not reject extra keys. If the search shows schema-level validation, update the validator and tests in this same task to allow the new keys. If no schema-level validation exists, do not modify `src/specify_cli/hooks/artifact_validation.py`.

- [ ] **Step 4: Run focused tests**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_specify_consumes_explicit_discussion_handoff_without_bypassing_kernel tests/test_alignment_templates.py::test_brainstorming_handoff_template_supports_discussion_candidate_metadata tests/hooks/test_artifact_hooks.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

If artifact validation was not changed:

```powershell
git add templates/commands/specify.md templates/brainstorming-handoff-specify-template.json
git commit -m "docs: teach specify candidate discussion handoffs"
```

If artifact validation was changed:

```powershell
git add templates/commands/specify.md templates/brainstorming-handoff-specify-template.json src/specify_cli/hooks/artifact_validation.py tests/hooks
git commit -m "docs: teach specify candidate discussion handoffs"
```

## Task 6: Update Routing, Cognition Gate, README, And Handbooks

**Files:**
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Modify: `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `templates/project-handbook-template.md`
- Modify: `tests/test_specify_guidance_docs.py`
- Test: `tests/test_alignment_templates.py`
- Test: `tests/test_specify_guidance_docs.py`

- [ ] **Step 1: Add guidance doc failing test**

In `tests/test_specify_guidance_docs.py`, append:

```python
def test_guidance_docs_explain_discussion_split_continuation() -> None:
    readme = _read("README.md")
    handbook = _read("PROJECT-HANDBOOK.md")
    generated_handbook = _read("templates/project-handbook-template.md")

    for content in (readme, handbook, generated_handbook):
        lowered = content.lower()
        assert "handoff-assessment.md" in content
        assert "split-plan.md" in content
        assert "candidate backlog" in lowered
        assert "return to the same discussion" in lowered
        assert "handoffs/CAND-001-handoff-to-specify.md" in content
        assert "handoff-to-specify.json" in content
```

- [ ] **Step 2: Extend workflow routing passive skill**

In `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`, update the `sp-discussion` guidance to include:

```markdown
- For large rough directions, stay in `sp-discussion` first. When the user asks to hand off or continue, `sp-discussion` runs handoff assessment and decides whether to write a bounded handoff, enter split mode with `split-plan.md`, or continue discussion.
- Do not route to `sp-split`; split-required work remains inside `sp-discussion` as a candidate backlog.
- After one candidate is implemented, route "continue next stage" requests back to the same `sp-discussion` slug so the next candidate can be selected from `split-plan.md`.
```

- [ ] **Step 3: Extend project cognition gate passive skill**

In `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`, add:

```markdown
- In `sp-discussion` split mode, product-level candidate splitting may begin from discussion artifacts, but source-grounded split rationale, affected-surface claims, implementation dependency claims, and technical risk classification still require the staged cognition gate.
```

- [ ] **Step 4: Update README discussion guidance**

Replace the README paragraph beginning ``- `discussion` to shape`` with:

```markdown
- `discussion` to shape a rough idea through resumable senior product and technical discussion before formal specification. It writes `.specify/discussions/<slug>/` artifacts and, when the user explicitly requests handoff or the next stage, first writes `handoff-assessment.md`. If the result is one bounded feature, it creates latest-copy `handoff-to-specify.md` and `handoff-to-specify.json`. If the result is too broad for one spec, it maintains `split-plan.md` as a candidate backlog, writes canonical candidate handoffs such as `handoffs/CAND-001-handoff-to-specify.md` and `.json`, and lets the user return to the same discussion for second and later stages. It does not automatically invoke `specify`.
```

Also add this paragraph near the existing `Use discussion before specify` paragraph:

```markdown
When a discussion covers a large direction, do not start a separate split workflow. Finish the discussion first, then let `discussion` run handoff assessment. A split-required assessment keeps the backlog in `split-plan.md`; after the first candidate is implemented, return to the same discussion slug to select the next candidate.
```

- [ ] **Step 5: Update handbook surfaces**

In `PROJECT-HANDBOOK.md`, replace the `Pre-spec discussion` bullet with:

```markdown
- **Pre-spec discussion**: `sp-discussion` stores resumable product/technical discussions under `.specify/discussions/<slug>/`, produces technical options and requirements drafts, and only hands off after explicit user request. Handoff now begins with `handoff-assessment.md`: one bounded result writes latest-copy `handoff-to-specify.{md,json}`, while broad directions stay inside `sp-discussion` through `split-plan.md` candidate backlog entries and canonical `handoffs/CAND-001-handoff-to-specify.{md,json}` files. After one candidate ships, return to the same discussion slug to select the next stage.
```

In `templates/project-handbook-template.md`, replace its matching `Pre-spec discussion` bullet with the same text, preserving line wrapping.

- [ ] **Step 6: Run focused docs tests and verify green**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_workflow_routing_mentions_discussion_before_specify_for_rough_ideas tests/test_alignment_templates.py::test_project_cognition_gate_has_staged_discussion_gate tests/test_specify_guidance_docs.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add templates/passive-skills/spec-kit-workflow-routing/SKILL.md templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md README.md PROJECT-HANDBOOK.md templates/project-handbook-template.md tests/test_specify_guidance_docs.py
git commit -m "docs: document discussion split continuation"
```

## Task 7: Run Full Focused Verification

**Files:**
- No source edits expected.
- Test: `tests/test_alignment_templates.py`
- Test: `tests/test_specify_guidance_docs.py`
- Test: `tests/integrations/test_integration_base_markdown.py`
- Test: `tests/integrations/test_integration_base_toml.py`
- Test: `tests/integrations/test_integration_base_skills.py`
- Test: `tests/hooks/test_artifact_hooks.py`
- Test: `tests/integrations/test_cli.py`

- [ ] **Step 1: Run template and docs tests**

```powershell
pytest tests/test_alignment_templates.py tests/test_specify_guidance_docs.py -q
```

Expected: PASS.

- [ ] **Step 2: Run generated integration tests**

```powershell
pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py -q
```

Expected: PASS.

- [ ] **Step 3: Run artifact and CLI smoke tests**

```powershell
pytest tests/hooks/test_artifact_hooks.py tests/integrations/test_cli.py -q
```

Expected: PASS.

- [ ] **Step 4: Review diff for scope discipline**

Run:

```powershell
git diff --stat
git diff -- templates/commands/discussion.md templates/commands/specify.md templates/discussion-state-template.md templates/brainstorming-handoff-specify-template.json
```

Expected: diff only touches discussion split handoff guidance, state template fields, `sp-specify` intake, brainstorming handoff template keys, routing/docs, and tests. No source implementation files should be changed except `src/specify_cli/hooks/artifact_validation.py` if Task 5 discovered existing schema validation.

- [ ] **Step 5: Final commit if verification-only fixes were needed**

If Step 1-4 required small fixes, commit them:

```powershell
git add tests/test_alignment_templates.py tests/test_specify_guidance_docs.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/hooks/test_artifact_hooks.py templates/commands/discussion.md templates/command-partials/discussion/shell.md templates/discussion-state-template.md templates/commands/specify.md templates/brainstorming-handoff-specify-template.json templates/passive-skills/spec-kit-workflow-routing/SKILL.md templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md README.md PROJECT-HANDBOOK.md templates/project-handbook-template.md src/specify_cli/hooks/artifact_validation.py
git commit -m "test: verify discussion split handoff surfaces"
```

If no files changed after prior commits, do not create an empty commit.

## Self-Review Checklist

- Spec coverage: Tasks cover handoff assessment, split mode, candidate backlog, candidate Markdown/JSON handoffs, latest-copy compatibility, multi-stage continuation, `sp-specify` candidate intake, JSON template metadata, routing/docs, and generated integration surfaces.
- No new workflow: No task adds `sp-split` or any CLI command.
- Artifact ownership: Tasks keep `sp-discussion` as owner of `.specify/discussions/<slug>/` artifacts and `sp-specify` as consumer.
- Testing: Red tests precede template edits, and focused verification covers shared templates, generated integrations, docs, hooks, and CLI smoke.
