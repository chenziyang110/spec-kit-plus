# sp-discussion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `sp-discussion` as a generated, resumable pre-specification discussion workflow with explicit user-controlled handoff into `sp-specify`.

**Architecture:** Implement this as a template-driven workflow, not a new Python runtime graph. `sp-discussion` owns independent state under `.specify/discussions/<slug>/discussion-state.md`; `sp-specify` gains an explicit handoff consumption contract for `.specify/discussions/<slug>/handoff-to-specify.md`. Existing integration renderers should pick up the new command from `templates/commands/discussion.md`, with targeted registration, docs, and tests updated where command lists are explicit.

**Tech Stack:** Python 3.11+, Typer CLI, Markdown/TOML/skills integration templates, pytest.

---

## File Structure

- Create `templates/commands/discussion.md`: Main workflow contract for `sp-discussion`, including frontmatter, role, session lifecycle, state/artifact rules, staged cognition gate, technical options board, and explicit handoff gate.
- Create `templates/command-partials/discussion/shell.md`: Shell partial for generated integration command summaries.
- Create `templates/discussion-state-template.md`: Independent discussion state template copied into generated projects as a static template; it is not feature `workflow-state.md`.
- Modify `templates/commands/specify.md`: Add explicit discussion handoff intake before feature description parsing, without bypassing the existing brainstorming kernel.
- Modify `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`: Route rough ideas and not-yet-ready requirements to `sp-discussion`; preserve `sp-specify` for formal spec generation.
- Modify `templates/passive-skills/spec-kit-project-map-gate/SKILL.md`: Add staged gate language for `sp-discussion`.
- Modify `src/specify_cli/__init__.py`: Add `discussion` to `SKILL_DESCRIPTIONS`, add a surface-only Typer command, update generated init guidance and managed AGENTS block text.
- Modify `src/specify_cli/integrations/base.py`: Add `discussion` to question-driven command enhancement so supported runtimes ask one bounded question cleanly.
- Modify `src/specify_cli/extensions.py`: Add `discussion` to `_FALLBACK_CORE_COMMAND_NAMES`.
- Modify `pyproject.toml`: Force-include `templates/discussion-state-template.md`.
- Modify docs: `README.md`, `docs/quickstart.md`, `docs/installation.md`, `PROJECT-HANDBOOK.md`, and `templates/project-handbook-template.md` where skill maps or workflow overviews list support workflows.
- Modify tests: `tests/test_alignment_templates.py`, `tests/test_specify_guidance_docs.py`, `tests/integrations/test_integration_base_markdown.py`, `tests/integrations/test_integration_base_toml.py`, `tests/integrations/test_integration_base_skills.py`, `tests/integrations/test_cli.py`, `tests/test_extensions.py`, and high-risk integration-specific tests if they have explicit command lists.

Do not modify `templates/workflow-state-template.md` for this feature. Do not add `sp-discussion` to `EXPECTED_WORKFLOW_STATE` in `src/specify_cli/hooks/state_validation.py`.

---

### Task 1: Template Contract Tests

**Files:**
- Modify: `tests/test_alignment_templates.py`
- Test-only target: `templates/commands/discussion.md`
- Test-only target: `templates/command-partials/discussion/shell.md`
- Test-only target: `templates/discussion-state-template.md`
- Test-only target: `templates/commands/specify.md`
- Test-only target: `templates/workflow-state-template.md`
- Test-only target: `src/specify_cli/hooks/state_validation.py`

- [ ] **Step 1: Add failing tests for the new discussion command contract**

Add these tests near other workflow-template contract tests in `tests/test_alignment_templates.py`:

```python
def test_discussion_command_contract_is_pre_spec_and_resumable() -> None:
    content = _read("templates/commands/discussion.md")
    lowered = content.lower()

    assert "sp-discussion" in content
    assert "senior technical expert" in lowered
    assert "senior product manager" in lowered
    assert ".specify/discussions/<slug>/" in content
    assert "discussion-state.md" in content
    assert "discussion-log.md" in content
    assert "requirements.md" in content
    assert "technical-options.md" in content
    assert "project-context.md" in content
    assert "open-questions.md" in content
    assert "handoff-to-specify.md" in content
    assert "active | blocked | handoff-ready | completed | abandoned" in content
    assert "multiple incomplete discussions" in lowered
    assert "updated_at" in content
    assert "do not create feature branches" in lowered
    assert "do not edit source code" in lowered
    assert "do not edit tests" in lowered
    assert "do not automatically run" in lowered
    assert "explicit user" in lowered
    assert "{{spec-kit-include: ../command-partials/discussion/shell.md}}" in content


def test_discussion_staged_cognition_gate_and_technical_options_contract() -> None:
    content = _read("templates/commands/discussion.md")
    lowered = content.lower()

    assert "product framing may begin before project cognition" in lowered
    assert "forbidden before the cognition gate" in lowered
    assert ".specify/project-cognition/status.json" in content
    assert ".specify/project-cognition/slices/change.json" in content
    assert "clearly greenfield" in lowered
    assert "source-code reads" in lowered
    assert "technical options board" in lowered
    assert "minimal viable path" in lowered
    assert "architecture-correct path" in lowered
    assert "expansion-ready path" in lowered
    assert "2-3" in content


def test_discussion_state_template_is_independent_from_feature_workflow_state() -> None:
    content = _read("templates/discussion-state-template.md")
    workflow_state = _read("templates/workflow-state-template.md")
    hook_state = _read_project_file("src/specify_cli/hooks/state_validation.py")

    assert "state_surface: discussion-state" in content
    assert "active_command: sp-discussion" in content
    assert "phase_mode: discussion-only" in content
    assert "status: active | blocked | handoff-ready | completed | abandoned" in content
    assert "updated_at:" in content
    assert "## Allowed Artifact Writes" in content
    assert "discussion-state.md" in content
    assert "handoff-to-specify.md" in content
    assert "sp-discussion" not in workflow_state
    assert '"discussion"' not in hook_state
    assert "sp-discussion" not in hook_state


def test_specify_consumes_explicit_discussion_handoff_without_bypassing_kernel() -> None:
    content = _read("templates/commands/specify.md")
    lowered = content.lower()

    assert ".specify/discussions/<slug>/handoff-to-specify.md" in content
    assert "pasted discussion handoff" in lowered
    assert "entry_source: sp-discussion" in content
    assert "authoritative input" in lowered
    assert "not a bypass" in lowered
    assert "confirmed requirements" in lowered
    assert "open questions" in lowered
    assert "blocking_level" in content
    assert "references.md" in content
    assert "reopen reason" in lowered
```

- [ ] **Step 2: Run the new failing tests**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_discussion_command_contract_is_pre_spec_and_resumable tests/test_alignment_templates.py::test_discussion_staged_cognition_gate_and_technical_options_contract tests/test_alignment_templates.py::test_discussion_state_template_is_independent_from_feature_workflow_state tests/test_alignment_templates.py::test_specify_consumes_explicit_discussion_handoff_without_bypassing_kernel -q
```

Expected: FAIL because `discussion.md`, the shell partial, and `discussion-state-template.md` do not exist yet and `specify.md` lacks the handoff contract.

- [ ] **Step 3: Commit failing tests**

```powershell
git add tests/test_alignment_templates.py
git commit -m "test: capture sp discussion template contracts"
```

---

### Task 2: Add Discussion Templates

**Files:**
- Create: `templates/commands/discussion.md`
- Create: `templates/command-partials/discussion/shell.md`
- Create: `templates/discussion-state-template.md`
- Modify: `pyproject.toml`

- [ ] **Step 1: Create the command partial**

Create `templates/command-partials/discussion/shell.md`:

```markdown
{{spec-kit-include: ../common/user-input.md}}

## Objective

Drive a resumable product and technical discussion that matures a rough idea into requirements and implementation options before formal specification.

## Context

- Primary inputs: the user's idea, the current discussion session under `.specify/discussions/<slug>/`, passive project memory, and project cognition when the discussion reaches source-grounded technical judgment.
- `discussion-state.md` is the durable session state source of truth.
- `sp-discussion` is upstream of `sp-specify`; it does not create feature branches or write formal feature artifacts.

## Process

- Create or resume the discussion session.
- Ask one high-impact question at a time.
- Preserve key decisions in `discussion-log.md`.
- Keep `requirements.md`, `technical-options.md`, `project-context.md`, and `open-questions.md` current.
- Generate `handoff-to-specify.md` only after explicit user request.

## Output Contract

- Maintain the independent discussion state and artifacts under `.specify/discussions/<slug>/`.
- Provide 2-3 project-grounded technical options when implementation strategy affects the requirement.
- Report unresolved questions honestly instead of forcing planning readiness.

## Guardrails

- Do not edit source code or tests.
- Do not create feature branches or feature directories.
- Do not automatically invoke or route into `sp-specify`.
- Do not make project-specific technical claims before the staged cognition gate passes.
```

- [ ] **Step 2: Create the discussion state template**

Create `templates/discussion-state-template.md`:

```markdown
# Discussion State: [TOPIC]

## Current Command

- active_command: sp-discussion
- state_surface: discussion-state
- status: active | blocked | handoff-ready | completed | abandoned
- slug: [normalized-slug]
- updated_at: [ISO-8601 timestamp]

## Phase Mode

- phase_mode: discussion-only
- summary: [Short current-state summary for resume context]

## Session Routing

- current_stage: session-intake | idea-framing | context-grounding | question-loop | technical-options | requirements-synthesis | handoff-on-request
- current_topic: [Short topic label]
- next_question: [One high-impact question or none]
- blocker_reason: none
- readiness_note: [why the discussion is or is not ready for explicit handoff]

## Session Selection

- incomplete_statuses: active, blocked, handoff-ready
- resume_rule: resume only when exactly one incomplete discussion is available or the user selected a slug
- collision_rule: append date or short numeric suffix when a generated slug already exists

## Allowed Artifact Writes

- discussion-state.md
- discussion-log.md
- requirements.md
- technical-options.md
- project-context.md
- open-questions.md
- handoff-to-specify.md only after explicit user request

## Forbidden Actions

- create feature branch
- create feature directory
- write spec.md
- write plan.md
- write tasks.md
- edit source code
- edit tests
- run implementation-oriented fix loops
- automatically invoke sp-specify
- infer handoff readiness without explicit user instruction

## Authoritative Files

- discussion-state.md
- discussion-log.md
- requirements.md
- technical-options.md
- project-context.md
- open-questions.md

## Handoff

- handoff_to_specify: none
- handoff_requested_by_user: false
- next_command: none
```

- [ ] **Step 3: Create the discussion command template**

Create `templates/commands/discussion.md` with this structure:

```markdown
---
description: Use when a rough idea or requirement needs a resumable senior product and technical discussion before formal specification.
workflow_contract:
  when_to_use: A rough idea or requirement needs product/technical discussion before it is ready for sp-specify.
  primary_objective: Build a durable discussion package that matures the idea into requirements and technical implementation options.
  primary_outputs: `.specify/discussions/<slug>/discussion-state.md`, `discussion-log.md`, `requirements.md`, `technical-options.md`, `project-context.md`, `open-questions.md`, and explicit `handoff-to-specify.md` only when requested by the user.
  default_handoff: Stay in sp-discussion until the user explicitly asks to hand off; then write handoff-to-specify.md and tell the user how to invoke sp-specify.
---

{{spec-kit-include: ../command-partials/discussion/shell.md}}

## Role

You are a senior technical expert and senior product manager working with the user to shape an idea before formal specification.

- Product manager perspective: clarify target users, jobs, scenarios, success criteria, scope, non-goals, permissions, failure paths, and acceptance signals.
- Technical expert perspective: understand current project context, identify likely capability surfaces, compare implementation paths, and explain trade-offs in a way that helps the user choose.
- You recommend options, but the user chooses product direction and explicitly controls handoff to `sp-specify`.

## Hard Boundaries

- Do not create feature branches.
- Do not create feature directories.
- Do not write `spec.md`, `plan.md`, `tasks.md`, or implementation artifacts.
- Do not edit source code.
- Do not edit tests.
- Do not run implementation-oriented fix loops.
- Do not automatically run, invoke, or route into `sp-specify`.
- Do not create or refresh `handoff-to-specify.md` unless the user explicitly asks to hand off, feed, or pass the discussion to `sp-specify`.

## Session Store

All state lives under `.specify/discussions/<slug>/`.

Required files:

- `discussion-state.md`
- `discussion-log.md`
- `requirements.md`
- `technical-options.md`
- `project-context.md`
- `open-questions.md`
- `handoff-to-specify.md` only after explicit user request

Use `templates/discussion-state-template.md` when initializing `discussion-state.md`.

## Session Selection

- Normalize user-provided slugs to lowercase ASCII, trim separators, replace non-alphanumeric runs with `-`, collapse duplicate separators, and cap the slug at a readable length.
- If a generated slug collides, append a date or short numeric suffix.
- Valid statuses are `active | blocked | handoff-ready | completed | abandoned`.
- Incomplete statuses are `active`, `blocked`, and `handoff-ready`.
- If the user specifies a slug, resume or create that slug according to the user's wording.
- If no slug is specified and exactly one incomplete discussion exists, resume it.
- If multiple incomplete discussions exist, list candidates with slug, status, summary, and `updated_at`, then ask the user to choose one or explicitly start a new discussion.
- Sort candidates by `updated_at` in `discussion-state.md`; fall back to the state file modification time only when `updated_at` is missing.

## Discussion Flow

1. Create or resume the discussion session.
2. Record the user's raw idea in `discussion-log.md`.
3. Ask one high-impact question at a time.
4. Keep `open-questions.md` grouped by blocking level.
5. Refresh `requirements.md` whenever a material requirement decision changes.
6. Enter technical options only when implementation strategy affects the requirement.
7. Generate `handoff-to-specify.md` only after explicit user request.

## Staged Project Cognition Gate

Product framing may begin before project cognition is available.

Allowed before the cognition gate:

- session creation or resume
- user goal framing
- audience and scenario clarification
- scope, non-goal, and success-signal questions
- recording unknowns and assumptions

Forbidden before the cognition gate:

- project-specific technical recommendations
- affected module, file, or API claims
- implementation path recommendations
- source-code reads
- testing strategy claims tied to existing code

Before `context-grounding`, `technical-options`, affected-surface analysis, or source-grounded recommendations, read:

1. `.specify/project-cognition/status.json`
2. `.specify/project-cognition/slices/change.json`
3. `.specify/project-cognition/graph/nodes.json`, `edges.json`, `claims.json`, or `conflicts.json` only when ownership, adjacency, or implementation placement remains unclear

Freshness handling:

- `missing`: stop and tell the user to run `{{invoke:map-scan}} -> {{invoke:map-build}}`.
- `stale`: stop and tell the user to run `{{invoke:map-update}}`.
- `support_drift`: stop for support-surface cleanup without reflexively routing to `{{invoke:map-update}}`.
- `partial_refresh`: stop and follow `recommended_next_action`.
- `possibly_stale`: inspect affected graph scope and route to localized refresh if coverage is not safe enough.

If the idea is clearly greenfield or does not depend on existing project structure, record the stand-down reason in `project-context.md` and avoid existing-code placement claims.

## Technical Options Board

When implementation strategy affects the requirement, present 2-3 options before locking direction:

- Minimal viable path
- Architecture-correct path
- Expansion-ready path

For each option, include product behavior enabled, impacted modules or files, complexity, migration or compatibility concerns, testing strategy, risks, rollback or de-scope path, and recommendation rationale.

## Handoff To sp-specify

Handoff is explicit-user-request only.

When requested, write or refresh `handoff-to-specify.md` with:

- frontmatter: `source_command: sp-discussion`, `discussion_slug`, `status: handoff-ready`, `updated_at`, and `source_files`
- confirmed product goal and users
- confirmed scope and non-goals
- confirmed scenarios and acceptance signals
- selected or still-open technical direction
- project-context evidence and inference notes
- unresolved questions with blocking levels
- instructions for `sp-specify` about settled decisions and remaining decisions

After writing the handoff, tell the user to invoke the generated integration's `sp-specify` command form with the handoff path. Do not invoke it yourself.
```

- [ ] **Step 4: Add package include for the discussion state template**

In `pyproject.toml`, add this line near the other individual templates:

```toml
"templates/discussion-state-template.md" = "specify_cli/core_pack/templates/discussion-state-template.md"
```

- [ ] **Step 5: Run template contract tests**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_discussion_command_contract_is_pre_spec_and_resumable tests/test_alignment_templates.py::test_discussion_staged_cognition_gate_and_technical_options_contract tests/test_alignment_templates.py::test_discussion_state_template_is_independent_from_feature_workflow_state -q
```

Expected: PASS for the discussion templates. The `sp-specify` handoff test still fails until Task 3.

- [ ] **Step 6: Commit discussion templates**

```powershell
git add templates/commands/discussion.md templates/command-partials/discussion/shell.md templates/discussion-state-template.md pyproject.toml tests/test_alignment_templates.py
git commit -m "feat: add sp discussion templates"
```

---

### Task 3: Add sp-specify Handoff Consumption Contract

**Files:**
- Modify: `templates/commands/specify.md`
- Modify: `tests/test_alignment_templates.py`

- [ ] **Step 1: Add handoff intake language to `sp-specify`**

In `templates/commands/specify.md`, add a section before the current Outline step that parses the user description. Use this text:

```markdown
## Discussion Handoff Intake

If the user invokes `sp-specify` with an explicit path to `.specify/discussions/<slug>/handoff-to-specify.md`, or pastes a discussion handoff block, read that handoff before parsing the feature request.

- Treat the discussion handoff as an authoritative input to the brainstorming kernel, not a bypass around it.
- Record `entry_source: sp-discussion` and the handoff path or pasted-handoff marker in the generated feature artifacts.
- Preserve confirmed requirements, confirmed non-goals, settled decisions, and selected technical direction in `facts.json`, `intent.json`, `complexity.json`, `handoff-to-specify.json`, `specify-draft.md`, `spec.md`, `alignment.md`, `context.md`, or `references.md` according to the existing `sp-specify` artifact responsibilities.
- Convert open questions from the handoff into explicit unknowns with `field`, `question`, `blocking_level`, `resolver`, `latest_resolve_phase`, and `status`.
- Cite the discussion handoff and relevant `project-context.md` evidence in `references.md` or `context.md`.
- Do not re-ask settled discussion questions unless repository evidence, constitution rules, or user correction contradicts the handoff.
- If a settled discussion conclusion is reopened, record the reopen reason before changing the derived spec package.
```

- [ ] **Step 2: Run the handoff contract test**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_specify_consumes_explicit_discussion_handoff_without_bypassing_kernel -q
```

Expected: PASS.

- [ ] **Step 3: Commit handoff contract**

```powershell
git add templates/commands/specify.md tests/test_alignment_templates.py
git commit -m "feat: teach specify discussion handoffs"
```

---

### Task 4: Routing, Question Tool, CLI, and Extension Registration

**Files:**
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Modify: `templates/passive-skills/spec-kit-project-map-gate/SKILL.md`
- Modify: `src/specify_cli/integrations/base.py`
- Modify: `src/specify_cli/__init__.py`
- Modify: `src/specify_cli/extensions.py`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `tests/integrations/test_cli.py`
- Modify: `tests/test_extensions.py`

- [ ] **Step 1: Add failing routing and registration tests**

Add these assertions to `tests/test_alignment_templates.py`:

```python
def test_workflow_routing_mentions_discussion_before_specify_for_rough_ideas() -> None:
    content = _read("templates/passive-skills/spec-kit-workflow-routing/SKILL.md")
    lowered = content.lower()

    assert "sp-discussion" in content
    assert "rough idea" in lowered
    assert "not-yet-ready" in lowered
    assert "pre-spec" in lowered or "before formal specification" in lowered
    assert "explicit handoff" in lowered
    assert "{{invoke:discussion}}" in content
    assert "{{invoke:specify}}" in content


def test_project_map_gate_has_staged_discussion_gate() -> None:
    content = _read("templates/passive-skills/spec-kit-project-map-gate/SKILL.md")
    lowered = content.lower()

    assert "sp-discussion" in content
    assert "product framing" in lowered
    assert "before the cognition gate" in lowered
    assert "technical options" in lowered
    assert ".specify/project-cognition/slices/change.json" in content
```

In each integration base mixin, update the question-driven loop from:

```python
for name in ("specify", "clarify", "deep-research", "checklist", "quick", "debug"):
```

to:

```python
for name in ("specify", "discussion", "clarify", "deep-research", "checklist", "quick", "debug"):
```

Also add in those tests that `discussion` content includes `"one high-impact question"` or `"structured question preference"`.

In `tests/integrations/test_cli.py`, extend `test_top_level_cli_exposes_graph_native_map_commands` or add a new test:

```python
def test_top_level_cli_exposes_discussion_entrypoint():
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    root_help = runner.invoke(app, ["--help"], catch_exceptions=False)
    discussion_help = runner.invoke(app, ["discussion", "--help"], catch_exceptions=False)

    assert root_help.exit_code == 0, root_help.output
    assert discussion_help.exit_code == 0, discussion_help.output
    assert "discussion" in root_help.output
    assert "resumable product/technical discussion" in discussion_help.output.lower()
```

In `tests/test_extensions.py`, keep `test_core_command_names_match_bundled_templates` unchanged because it derives the expected set from `templates/commands`. Add this fallback-specific assertion immediately after it:

```python
def test_fallback_core_command_names_include_discussion():
    from specify_cli.extensions import _FALLBACK_CORE_COMMAND_NAMES

    assert "discussion" in _FALLBACK_CORE_COMMAND_NAMES
```

- [ ] **Step 2: Run failing registration tests**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_workflow_routing_mentions_discussion_before_specify_for_rough_ideas tests/test_alignment_templates.py::test_project_map_gate_has_staged_discussion_gate tests/integrations/test_cli.py::test_top_level_cli_exposes_discussion_entrypoint tests/test_extensions.py::test_fallback_core_command_names_include_discussion -q
```

Expected: FAIL until code and passive skills are updated.

- [ ] **Step 3: Update passive workflow routing**

In `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`:

- Change the frontmatter `description` string from:

```yaml
description: "Use when working inside a Spec Kit Plus repository and the user asks for feature work, planning, implementation, explanation, debugging, or code changes without explicitly naming the right sp-* workflow. Route the request to the correct active skill before proceeding."
```

to:

```yaml
description: "Use when working inside a Spec Kit Plus repository and the user asks for feature work, discussion, planning, implementation, explanation, debugging, or code changes without explicitly naming the right sp-* workflow. Route the request to the correct active skill before proceeding."
```

- Replace the existing `sp-specify` routing bullet with these two bullets:

```markdown
- Use `sp-discussion` for rough ideas, not-yet-ready requirements, or multi-turn product/technical exploration before formal specification. It preserves `.specify/discussions/<slug>/` state and only hands off to `sp-specify` on explicit user request.
- Use `sp-specify` for new capability, behavior, or requirement changes that are ready for an aligned spec package before implementation.
```

- Add invocation example:

```markdown
- Pre-spec discussion: `{{invoke:discussion}}`
```

- Add behavioral rule:

```markdown
- Do not skip from `sp-discussion` into `sp-specify` unless the user explicitly requests handoff.
```

- [ ] **Step 4: Update project map gate**

In `templates/passive-skills/spec-kit-project-map-gate/SKILL.md`, add language:

```markdown
- For `sp-discussion`, product framing may begin before the cognition gate. Before technical options, affected-surface claims, source-code reads, or source-grounded recommendations, read `.specify/project-cognition/status.json` and `.specify/project-cognition/slices/change.json`.
```

Also add `sp-discussion` to any list of ordinary brownfield workflows that use `slices/change.json`.

- [ ] **Step 5: Update question tool preference in integration base**

In `src/specify_cli/integrations/base.py`:

- Add `discussion` to `_question_tool_use_cases`:

```python
"discussion": [
    "one high-impact product or technical clarification",
    "resume selection when multiple incomplete discussions exist",
    "explicit handoff confirmation before writing `handoff-to-specify.md`",
],
```

- Add a fallback hint:

```python
"discussion": "If the native tool is unavailable in the current runtime or the tool call fails, ask one concise plain-text product or technical question and continue with the discussion state update.",
```

- Add `"discussion"` to `question_driven_commands`.

- [ ] **Step 6: Update CLI descriptions and entrypoint**

In `src/specify_cli/__init__.py`:

- Add:

```python
"discussion": "Use when a rough idea or requirement needs a resumable product/technical discussion before formal specification.",
```

to `SKILL_DESCRIPTIONS`.

- Add a Typer command near other surface-only workflow commands:

```python
@app.command("discussion", help=SKILL_DESCRIPTIONS["discussion"])
def discussion_command() -> None:
    """Workflow entrypoint surface for resumable pre-specification discussion."""
    _workflow_entrypoint_surface_only("discussion")
```

- Add `sp-discussion` to managed AGENTS block routing:

```python
"- Use `sp-discussion` when a rough idea needs resumable senior product and technical discussion before formal specification.",
```

- Add discussion to init "Support skills" and enhancement lists:

```python
steps_lines.append(f"   - [cyan]{_display_cmd('discussion')}[/] - Mature a rough idea through resumable product and technical discussion before formal specification")
```

and:

```python
f"○ [cyan]{_display_cmd('discussion')}[/] [bright_black](pre-spec discussion)[/bright_black] - Preserve product and technical discussion state before explicit handoff to [cyan]{_display_cmd('specify')}[/]",
```

- [ ] **Step 7: Update extension fallback core names**

In `src/specify_cli/extensions.py`, add `"discussion"` to `_FALLBACK_CORE_COMMAND_NAMES`.

- [ ] **Step 8: Run routing and registration tests**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_workflow_routing_mentions_discussion_before_specify_for_rough_ideas tests/test_alignment_templates.py::test_project_map_gate_has_staged_discussion_gate tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_gemini.py tests/integrations/test_cli.py::test_top_level_cli_exposes_discussion_entrypoint tests/test_extensions.py::test_fallback_core_command_names_include_discussion -q
```

Expected: PASS.

- [ ] **Step 9: Commit routing and registration**

```powershell
git add templates/passive-skills/spec-kit-workflow-routing/SKILL.md templates/passive-skills/spec-kit-project-map-gate/SKILL.md src/specify_cli/integrations/base.py src/specify_cli/__init__.py src/specify_cli/extensions.py tests/test_alignment_templates.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_cli.py tests/test_extensions.py
git commit -m "feat: register sp discussion workflow"
```

---

### Task 5: Documentation Updates

**Files:**
- Modify: `README.md`
- Modify: `docs/quickstart.md`
- Modify: `docs/installation.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `templates/project-handbook-template.md`
- Modify: `tests/test_specify_guidance_docs.py`

- [ ] **Step 1: Add failing docs tests**

In `tests/test_specify_guidance_docs.py`, update `test_guidance_docs_explain_skill_groups`:

```python
assert "`discussion`" in readme
...
assert "`discussion`" in quickstart
...
assert "`map-scan`, `map-build`, `map-update`, `test-scan`, `test-build`, `auto`, `discussion`, `prd-scan`, `prd-build`, `prd` (deprecated compatibility entrypoint), `clarify`, `deep-research` (`research` alias), `checklist`, `analyze`, `debug`, `explain`" in skill_map
```

Add a new docs test:

```python
def test_guidance_docs_position_discussion_before_specify() -> None:
    readme = _read("README.md")
    quickstart = _read("docs/quickstart.md")
    installation = _read("docs/installation.md")

    for content in (readme, quickstart, installation):
        lowered = content.lower()
        assert "`discussion`" in content
        assert "rough idea" in lowered
        assert "before formal specification" in lowered or "pre-spec" in lowered
        assert "handoff-to-specify.md" in content
        assert "explicit" in lowered
        assert "does not automatically" in lowered
```

- [ ] **Step 2: Run failing docs tests**

Run:

```powershell
pytest tests/test_specify_guidance_docs.py::test_guidance_docs_explain_skill_groups tests/test_specify_guidance_docs.py::test_guidance_docs_position_discussion_before_specify -q
```

Expected: FAIL until docs are updated.

- [ ] **Step 3: Update README skill map and guidance**

In `README.md`:

- Add `discussion` to the Support skills list after `auto`.
- Add a conditional gate bullet:

```markdown
- `discussion` to shape a rough idea through resumable senior product and technical discussion before formal specification. It writes `.specify/discussions/<slug>/` artifacts and creates `handoff-to-specify.md` only when the user explicitly requests handoff; it does not automatically invoke `specify`.
```

- Add a routing guide sentence:

```markdown
Use `discussion` before `specify` when the idea is still exploratory, has major product trade-offs, or needs multiple technical implementation paths before the user chooses a direction.
```

- [ ] **Step 4: Update quickstart and installation**

In `docs/quickstart.md`:

- Add `discussion` to the Support skills list after `auto`.
- Add a "Use support skills" bullet mirroring README.

In `docs/installation.md`:

- Add a short paragraph near invocation examples:

```markdown
Use the canonical `discussion` workflow for rough ideas that need resumable product and technical exploration before formal `specify`. It stores `.specify/discussions/<slug>/` artifacts and only creates `handoff-to-specify.md` when the user explicitly asks to hand off.
```

- [ ] **Step 5: Update handbooks**

In `PROJECT-HANDBOOK.md`, add a bullet near workflow contract generation:

```markdown
- **Pre-spec discussion**: `sp-discussion` stores resumable product/technical discussions under `.specify/discussions/<slug>/`, produces technical options and requirements drafts, and only hands off to `sp-specify` through explicit `handoff-to-specify.md`.
```

In `templates/project-handbook-template.md`, add equivalent generated-project guidance.

- [ ] **Step 6: Run docs tests**

Run:

```powershell
pytest tests/test_specify_guidance_docs.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit docs**

```powershell
git add README.md docs/quickstart.md docs/installation.md PROJECT-HANDBOOK.md templates/project-handbook-template.md tests/test_specify_guidance_docs.py
git commit -m "docs: describe sp discussion workflow"
```

---

### Task 6: Integration Generation Coverage

**Files:**
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `tests/integrations/test_cli.py`
- Modify: `tests/integrations/test_integration_codex.py`, `tests/integrations/test_integration_claude.py`, and `tests/integrations/test_integration_gemini.py` only when their explicit shared-command inventory assertions omit the new `sp-discussion` skill.

- [ ] **Step 1: Add generated discussion assertions to integration mixins**

In `MarkdownIntegrationTests`, add:

```python
def test_discussion_command_is_generated_with_state_and_handoff_contract(self, tmp_path):
    i = get_integration(self.KEY)
    m = IntegrationManifest(self.KEY, tmp_path)
    i.setup(tmp_path, m)

    content = (i.commands_dest(tmp_path) / i.command_filename("discussion")).read_text(encoding="utf-8").lower()
    assert "sp-discussion" in content
    assert ".specify/discussions/<slug>/" in content
    assert "discussion-state.md" in content
    assert "handoff-to-specify.md" in content
    assert "explicit user" in content
    assert "senior technical expert" in content
    assert "senior product manager" in content
```

In `TomlIntegrationTests`, add the same test but parse TOML first:

```python
def test_discussion_command_is_generated_with_state_and_handoff_contract(self, tmp_path):
    i = get_integration(self.KEY)
    m = IntegrationManifest(self.KEY, tmp_path)
    i.setup(tmp_path, m)

    raw = (i.commands_dest(tmp_path) / i.command_filename("discussion")).read_text(encoding="utf-8")
    parsed = tomllib.loads(raw)
    content = parsed["prompt"].lower()
    assert "sp-discussion" in content
    assert ".specify/discussions/<slug>/" in content
    assert "discussion-state.md" in content
    assert "handoff-to-specify.md" in content
    assert "explicit user" in content
    assert "senior technical expert" in content
    assert "senior product manager" in content
```

In `SkillsIntegrationTests`, add:

```python
def test_discussion_skill_is_generated_with_state_and_handoff_contract(self, tmp_path):
    i = get_integration(self.KEY)
    m = IntegrationManifest(self.KEY, tmp_path)
    i.setup(tmp_path, m)

    content = (i.skills_dest(tmp_path) / "sp-discussion" / "SKILL.md").read_text(encoding="utf-8").lower()
    assert "sp-discussion" in content
    assert ".specify/discussions/<slug>/" in content
    assert "discussion-state.md" in content
    assert "handoff-to-specify.md" in content
    assert "explicit user" in content
    assert "senior technical expert" in content
    assert "senior product manager" in content
```

- [ ] **Step 2: Update CLI generated skills smoke tests**

In `tests/integrations/test_cli.py`, update explicit skill tuples that currently include `"sp-specify", "sp-plan", ...` to include `"sp-discussion"` when they are intended to verify shared workflow skill generation. Do not add discussion to tests that are specifically scoped to implement/debug/quick runtime contracts.

Example:

```python
for skill_name in ("sp-specify", "sp-discussion", "sp-plan", "sp-test-scan", "sp-test-build", "sp-tasks", "sp-explain", "sp-debug"):
```

- [ ] **Step 3: Run integration smoke tests**

Run:

```powershell
pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_cli.py -q
```

Expected: PASS after adjusting any explicit command inventories. If failures point to integration-specific explicit lists, update only those lists and rerun the failing file.

- [ ] **Step 4: Commit integration coverage**

```powershell
git add tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_cli.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_gemini.py
git commit -m "test: cover sp discussion generation"
```

---

### Task 7: Final Verification And Cleanup

**Files:**
- Review all touched files.

- [ ] **Step 1: Run focused template and docs tests**

Run:

```powershell
pytest tests/test_alignment_templates.py tests/test_specify_guidance_docs.py tests/test_extensions.py -q
```

Expected: PASS.

- [ ] **Step 2: Run focused integration tests**

Run:

```powershell
pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_cli.py -q
```

Expected: PASS.

- [ ] **Step 3: Run lint-free static sanity checks**

Run:

```powershell
rg -n "sp-discussion|discussion-only|discussion-state|handoff-to-specify" templates src tests README.md docs PROJECT-HANDBOOK.md pyproject.toml
```

Expected: Results include the new intended surfaces. Confirm there are no hits adding `sp-discussion` to `templates/workflow-state-template.md` or `EXPECTED_WORKFLOW_STATE`.

Run:

```powershell
rg -n "sp-discussion" templates\\workflow-state-template.md src\\specify_cli\\hooks\\state_validation.py
```

Expected: no output.

- [ ] **Step 4: Check package file inclusion**

Run:

```powershell
rg -n "discussion-state-template|templates/commands|templates/command-partials" pyproject.toml
```

Expected: `templates/discussion-state-template.md` is force-included, and command directories remain included.

- [ ] **Step 5: Review diff**

Run:

```powershell
git diff --stat HEAD
git diff HEAD -- templates src tests README.md docs PROJECT-HANDBOOK.md pyproject.toml
```

Expected: Diff only contains `sp-discussion` implementation, docs, and tests.

- [ ] **Step 6: Final commit if any verification fixes were needed**

If Step 1-5 required fixes after the previous commits:

```powershell
git add templates src tests README.md docs PROJECT-HANDBOOK.md pyproject.toml
git commit -m "fix: align sp discussion workflow surfaces"
```

If no fixes were needed, do not create an empty commit.
