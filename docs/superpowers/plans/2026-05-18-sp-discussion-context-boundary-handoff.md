# sp-discussion Context Boundary Handoff Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved `sp-discussion` context-boundary and unified handoff contract so cross-project, reference-source, external-system, and existing-module requests cannot drift into unsupported downstream planning.

**Architecture:** This is a generated workflow contract change, not a new runtime engine. The `sp-discussion` templates own boundary intake, one-question-at-a-time clarification, single-pair handoff drafting, self-review, and user confirmation; `sp-specify`, `sp-plan`, and `sp-tasks` defensively consume the structured handoff and reject missing boundary facts instead of repairing them.

**Tech Stack:** Markdown command templates, JSON artifact templates, passive skills, pytest template tests, integration rendering tests, README/handbook/quickstart documentation.

---

## Scope Check

The approved spec covers one workflow contract family: `sp-discussion` boundary locking and downstream handoff quality. The work spans templates, docs, and tests because those are generated product surfaces, but the behavior is one coherent flow.

Do not add a Python runtime schema validator in this increment. Do not add a new `sp-split` workflow. Do not let this become Codex-specific.

## Source Spec

- Design: `docs/superpowers/specs/2026-05-18-sp-discussion-context-boundary-handoff-design.md`
- Superseded behavior to remove: `split-plan.md` candidate backlog handoffs and `handoffs/<candidate_id>-handoff-to-specify.{md,json}` as active `sp-discussion` output.

## File Structure

- Modify `tests/test_alignment_templates.py`: replace old split/candidate assertions with boundary gate, unified handoff, role-object, JSON-companion, and downstream plan/tasks assertions.
- Modify `tests/test_specify_guidance_docs.py`: replace split-continuation docs tests with unified handoff and boundary docs tests, including `docs/quickstart.md` and `docs/installation.md`.
- Modify `tests/integrations/test_integration_base_markdown.py`: generated Markdown command assertions for the new `sp-discussion` and `sp-specify` contracts.
- Modify `tests/integrations/test_integration_base_toml.py`: generated TOML prompt assertions for the same contracts.
- Modify `tests/integrations/test_integration_base_skills.py`: generated skills assertions for the same contracts.
- Modify `templates/commands/discussion.md`: source-of-truth `sp-discussion` workflow contract.
- Modify `templates/command-partials/discussion/shell.md`: concise generated shell guidance for `sp-discussion`.
- Modify `templates/discussion-state-template.md`: durable discussion state fields for boundary and handoff review.
- Modify `templates/brainstorming-handoff-specify-template.json`: active feature copy shape for the structured handoff.
- Modify `templates/commands/specify.md`: `sp-specify` defensive discussion handoff intake.
- Modify `templates/command-partials/specify/shell.md`: concise `sp-specify` intake contract.
- Modify `templates/commands/plan.md`: pre-plan validation and cross-project cognition behavior.
- Modify `templates/command-partials/plan/shell.md`: concise plan-side target boundary contract.
- Modify `templates/plan-template.md`: explicit implementation target boundary section in generated plans.
- Modify `templates/plan-contract-template.json`: machine-readable target boundary carry-forward fields.
- Modify `templates/commands/tasks.md`: task-generation target-root and evidence inheritance rules.
- Modify `templates/command-partials/tasks/shell.md`: concise tasks-side target boundary contract.
- Modify `templates/tasks-template.md`: target-root, target-relative path, and evidence status guidance in generated task files.
- Modify `templates/task-packet-template.json`: machine-readable target boundary fields for task packets.
- Modify `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`: rough-idea routing and no split workflow guidance.
- Modify `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`: project-scoped cognition and external target guidance.
- Modify `README.md`: user-facing workflow guidance.
- Modify `PROJECT-HANDBOOK.md`: source-of-truth repository guidance.
- Modify `templates/project-handbook-template.md`: generated handbook guidance.
- Modify `docs/quickstart.md`: walkthrough guidance for boundary-locking `discussion`.
- Modify `docs/installation.md`: installation/user workflow guidance for boundary-locking `discussion`.

Inspect but do not modify unless a focused test proves it is required:

- `src/specify_cli/hooks/artifact_validation.py`: schema-level discussion handoff validation is a follow-up, not this increment.
- `src/specify_cli/integrations/base.py`: generated integration rendering should pick up template changes without renderer changes.

---

### Task 1: Replace Split Handoff Tests With Boundary And Unified Handoff Tests

**Files:**
- Modify: `tests/test_alignment_templates.py`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Replace old split-specific discussion tests**

In `tests/test_alignment_templates.py`, replace `test_discussion_command_supports_handoff_assessment_and_split_backlog` with:

```python
def test_discussion_command_locks_context_boundary_before_technicalization() -> None:
    content = _read_project_file("templates/commands/discussion.md")
    lowered = content.lower()

    assert "Context Boundary Gate" in content
    assert "context-intake" in content
    assert "product-framing" in content
    assert "context-grounding" in content
    assert "technical-options" in content
    assert "handoff-self-review" in content
    assert "handoff-user-review" in content
    assert "handoff-ready" in content
    assert "ask one boundary question at a time" in lowered
    assert "must not provide project-specific technical recommendations" in lowered
    assert "must not name affected files, modules, apis, or tests as facts" in lowered
    assert "target project root immediately" in lowered
    assert "current project's cognition cannot prove another project's implementation facts" in lowered
```

Add this new test immediately after it:

```python
def test_discussion_command_requires_single_unified_handoff_pair() -> None:
    content = _read_project_file("templates/commands/discussion.md")
    lowered = content.lower()

    assert ".specify/discussions/<slug>/handoff-to-specify.md" in content
    assert ".specify/discussions/<slug>/handoff-to-specify.json" in content
    assert "one complete handoff package" in lowered
    assert "single unified handoff pair" in lowered
    assert "capability_map" in content
    assert "recommended_sequence" in content
    assert "deferred_scope" in content
    assert "continue-discussion" in content
    assert "do not write `split-plan.md`" in lowered
    assert "do not write candidate-specific handoff" in lowered
    assert "candidate backlog" not in lowered
    assert "CAND-001" not in content
    assert "CAND-002" not in content
```

- [ ] **Step 2: Replace the shell partial split test**

Replace `test_discussion_shell_partial_mentions_split_outputs_without_single_handoff_assumption` with:

```python
def test_discussion_shell_partial_summarizes_boundary_and_single_handoff_contract() -> None:
    content = _read("templates/command-partials/discussion/shell.md")
    lowered = content.lower()

    assert "Context Boundary Gate" in content
    assert "target project root" in lowered
    assert "reference source" in lowered
    assert "external system" in lowered
    assert "one high-impact question at a time" in lowered
    assert "one complete handoff package" in lowered
    assert "`handoff-to-specify.md`" in content
    assert "`handoff-to-specify.json`" in content
    assert "self-review" in lowered
    assert "user confirmation" in lowered
    assert "handoffs/<candidate_id>" not in content
    assert "split-plan.md" not in content
```

- [ ] **Step 3: Update discussion state assertions**

In `test_discussion_state_template_is_independent_from_feature_workflow_state`, replace the old handoff assessment and split-plan assertions with:

```python
    assert "context-intake" in content
    assert "product-framing" in content
    assert "context-grounding" in content
    assert "handoff-self-review" in content
    assert "handoff-user-review" in content
    assert "## Context Boundary" in content
    assert "context_boundary_status: not-started | needs-user-input | locked | blocked" in content
    assert "current_project_root:" in content
    assert "current_project_roles:" in content
    assert "target_project_root:" in content
    assert "target_project_roles:" in content
    assert "reference_sources:" in content
    assert "external_systems:" in content
    assert "boundary_blockers:" in content
    assert "## Handoff Review" in content
    assert "handoff_review_status: not-started | draft | self-review-passed | user-confirmed | blocked" in content
    assert "handoff_user_confirmed_at:" in content
    assert "handoff_blocker_reason:" in content
    assert "handoff-to-specify.md only after explicit user request, boundary lock, self-review pass, and user confirmation" in content
    assert "handoff-to-specify.json only after explicit user request, boundary lock, self-review pass, and user confirmation" in content
    assert "handoffs/*.md" not in content
    assert "handoffs/*.json" not in content
    assert "split_plan_status" not in content
    assert "active_candidate" not in content
```

- [ ] **Step 4: Replace candidate consequence test**

Replace `test_discussion_consequence_gate_covers_json_and_candidate_handoffs` with:

```python
def test_discussion_consequence_gate_covers_unified_handoff_pair() -> None:
    content = _read("templates/commands/discussion.md")
    lowered = content.lower()

    assert "Senior Maintainer Review" in content
    assert "handoff-to-specify.md" in content
    assert "handoff-to-specify.json" in content
    assert "markdown and json handoffs must agree" in lowered
    assert "consequence obligation ids" in lowered
    assert "must not mark the discussion `handoff-ready`" in content
    assert "unified handoff" in lowered
    assert "CAND-001-handoff-to-specify.md" not in content
    assert "selected candidate handoff" not in lowered
```

- [ ] **Step 5: Replace `sp-specify` discussion intake assertions**

Replace the body of `test_specify_consumes_explicit_discussion_handoff_without_bypassing_kernel` with:

```python
def test_specify_consumes_confirmed_unified_discussion_handoff_without_repair() -> None:
    content = _read("templates/commands/specify.md")
    lowered = content.lower()

    assert ".specify/discussions/<slug>/handoff-to-specify.md" in content
    assert ".specify/discussions/<slug>/handoff-to-specify.json" in content
    assert "authoritative input" in lowered
    assert "not a bypass" in lowered
    assert "quality_gate.status" in content
    assert "user_confirmed" in content
    assert "handoff_goal" in content
    assert "context_boundary" in content
    assert "current_project_roles" in content
    assert "target_project_roles" in content
    assert "`role`, `scope`, `evidence_source`, and `notes`" in content
    assert "target_project_root" in content
    assert "missing json is a hard handoff integrity blocker" in lowered
    assert "return to `sp-discussion`" in content
    assert "blocked_by_handoff_integrity" in content
    assert "current project's cognition is not proof of target-project implementation facts" in lowered
    assert "pasted discussion handoff" in lowered
    assert "entry_source: sp-discussion" in content
    assert "confirmed requirements" in lowered
    assert "open questions" in lowered
    assert "blocking_level" in content
    assert "references.md" in content
    assert "do not reconstruct" in lowered
    assert "candidate-specific handoff" in lowered
    assert "deprecated compatibility" in lowered
```

- [ ] **Step 6: Add JSON template contract tests**

Replace `test_brainstorming_handoff_template_supports_discussion_candidate_metadata` with:

```python
def test_brainstorming_handoff_template_supports_context_boundary_quality_gate() -> None:
    template = json.loads(_read("templates/brainstorming-handoff-specify-template.json"))

    assert template["version"] == 2
    assert template["entry_source"] is None
    assert template["handoff_goal"] is None
    assert template["context_boundary"]["current_project_root"] is None
    assert template["context_boundary"]["current_project_roles"] == []
    assert template["context_boundary"]["target_project_root"] is None
    assert template["context_boundary"]["target_project_roles"] == []
    assert template["context_boundary"]["reference_projects"] == []
    assert template["context_boundary"]["external_systems"] == []
    assert template["context_boundary"]["path_status"] == "unknown"
    assert template["context_boundary"]["boundary_confidence"] == "unknown"
    assert template["context_boundary"]["boundary_unknowns"] == []
    assert template["context_boundary"]["role_object_contract"]["required_fields"] == [
        "role",
        "scope",
        "evidence_source",
        "notes",
    ]
    assert "implementation_target" in template
    assert template["implementation_target"]["target_root"] is None
    assert template["implementation_target"]["target_paths"] == []
    assert "current project cognition cannot prove another project's implementation facts" in (
        template["implementation_target"]["current_project_cognition_scope_note"].lower()
    )
    assert template["source_evidence"] == []
    assert template["blocking_unknowns"] == []
    assert template["downstream_instructions"]["capability_map"] == []
    assert template["downstream_instructions"]["recommended_sequence"] == []
    assert template["downstream_instructions"]["deferred_scope"] == []
    assert template["quality_gate"]["status"] == "draft"
    assert template["quality_gate"]["user_review_required"] is True
    assert template["quality_gate"]["user_confirmed_at"] is None
    assert template["quality_gate"]["blocked_reasons"] == []
    assert template["candidate_id"] is None
    assert template["source_split_plan"] is None
```

- [ ] **Step 7: Add plan/tasks downstream boundary tests**

Append these tests near `test_plan_tasks_and_implement_preserve_discussion_fidelity_obligations`:

```python
def test_plan_template_rejects_cross_project_handoff_without_target_context() -> None:
    plan = _read("templates/commands/plan.md")
    shell = _read("templates/command-partials/plan/shell.md")
    plan_template = _read("templates/plan-template.md")
    contract = json.loads(_read("templates/plan-contract-template.json"))
    combined = "\n".join([plan, shell, plan_template])
    lowered = combined.lower()

    assert "target_project_root" in combined
    assert "quality_gate.user_confirmed" in combined
    assert "hard unknowns" in lowered
    assert "current project's cognition" in lowered
    assert "not proof of target-project implementation facts" in lowered
    assert "artifact-only planning may proceed only with explicit minimal live reads" in lowered
    assert "must not tell the user to run current-project" in lowered
    assert contract["context_boundary"] == {}
    assert contract["implementation_target"] == {}
    assert contract["target_project_root"] is None
    assert contract["target_evidence_status"] is None


def test_tasks_template_inherits_implementation_target_boundary() -> None:
    tasks = _read("templates/commands/tasks.md")
    shell = _read("templates/command-partials/tasks/shell.md")
    task_template = _read("templates/tasks-template.md")
    packet = json.loads(_read("templates/task-packet-template.json"))
    combined = "\n".join([tasks, shell, task_template])
    lowered = combined.lower()

    assert "target root" in lowered
    assert "target-relative path" in lowered
    assert "evidence status" in lowered
    assert "mp-*" in lowered
    assert "boundary constraints" in lowered
    assert "forbidden drift" in lowered
    assert "must not silently point to the current repository" in lowered
    assert "reference-only" in lowered
    assert packet["implementation_target"] == {}
    assert packet["target_root"] is None
    assert packet["target_relative_paths"] == []
    assert packet["evidence_status"] is None
    assert packet["boundary_constraints"] == []
```

- [ ] **Step 8: Run the focused template tests and verify red**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_discussion_command_locks_context_boundary_before_technicalization tests/test_alignment_templates.py::test_discussion_command_requires_single_unified_handoff_pair tests/test_alignment_templates.py::test_discussion_shell_partial_summarizes_boundary_and_single_handoff_contract tests/test_alignment_templates.py::test_discussion_state_template_is_independent_from_feature_workflow_state tests/test_alignment_templates.py::test_discussion_consequence_gate_covers_unified_handoff_pair tests/test_alignment_templates.py::test_specify_consumes_confirmed_unified_discussion_handoff_without_repair tests/test_alignment_templates.py::test_brainstorming_handoff_template_supports_context_boundary_quality_gate tests/test_alignment_templates.py::test_plan_template_rejects_cross_project_handoff_without_target_context tests/test_alignment_templates.py::test_tasks_template_inherits_implementation_target_boundary -q
```

Expected: FAIL because the templates still describe split/candidate handoffs, JSON reconstruction, and missing boundary fields.

- [ ] **Step 9: Commit red tests**

```powershell
git add tests/test_alignment_templates.py
git commit -m "test: cover discussion boundary handoff contract"
```

---

### Task 2: Update `sp-discussion` Command And Shell Partial

**Files:**
- Modify: `templates/commands/discussion.md`
- Modify: `templates/command-partials/discussion/shell.md`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Replace `discussion.md` frontmatter outputs**

In `templates/commands/discussion.md`, replace `primary_outputs` and `default_handoff` with:

```yaml
  primary_outputs: '`.specify/discussions/<slug>/discussion-state.md`, `discussion-log.md`, `requirements.md`, `technical-options.md`, `project-context.md`, `open-questions.md`, `handoff-assessment.md` when handoff is requested, plus exactly one unified handoff pair `.specify/discussions/<slug>/handoff-to-specify.md` and `.specify/discussions/<slug>/handoff-to-specify.json` only after boundary lock, self-review, and user confirmation.'
  default_handoff: Stay in sp-discussion until the user explicitly asks to hand off or continue the next stage; then run boundary-aware handoff assessment and either produce one confirmed unified handoff pair or continue discussion.
```

- [ ] **Step 2: Update hard boundaries**

In `## Hard Boundaries`, keep the existing no-implementation bullets and replace split-related bullets with:

```markdown
- Do not add, recommend, or route to `sp-split`, `sp-breakdown`, or any split-only workflow.
- Do not write `split-plan.md`.
- Do not write candidate-specific handoff Markdown or JSON under `handoffs/`.
- Do not create or refresh `handoff-to-specify.md` or `handoff-to-specify.json` unless the user explicitly asks to hand off, the Context Boundary Gate is locked, the handoff self-review passes, and the user confirms the handoff.
- Do not tell the user to proceed to `sp-specify` before `quality_gate.status` is user-confirmed.
```

- [ ] **Step 3: Replace session store required files**

Replace the `Required files:` block in `templates/commands/discussion.md` with:

```markdown
Required files:

- `discussion-state.md`
- `discussion-log.md`
- `requirements.md`
- `technical-options.md`
- `project-context.md`
- `open-questions.md`
- `handoff-assessment.md` only after explicit user request to hand off or continue to the next stage
- `handoff-to-specify.md` only after a bounded unified handoff passes self-review and user confirmation
- `handoff-to-specify.json` only after a bounded unified handoff passes self-review and user confirmation

Do not create `split-plan.md` or candidate-specific `handoffs/` files. Complex directions stay inside the single handoff through `capability_map`, `recommended_sequence`, `dependencies`, `deferred_scope`, and `reopen_conditions`, or remain in `continue-discussion` until the user confirms a unified scope.
```

- [ ] **Step 4: Replace the discussion flow**

Replace the `## Discussion Flow` section with:

```markdown
## Discussion Flow

1. `context-intake`
   - Identify current project root, user goal, current project roles, target project, target root, reference sources, external systems, path hints, and evidence sources.
   - Run the Context Boundary Gate before project-specific technical options, affected-file claims, or handoff drafting.
   - If the gate is unresolved, ask one boundary question at a time.

2. `product-framing`
   - Clarify goal, users, scenario, scope, non-goals, success signals, constraints, and blocked unknowns.
   - Product framing may continue when target paths are missing, but target-specific implementation claims are forbidden.

3. `context-grounding`
   - Enter only after relevant boundaries are locked.
   - Use current project cognition only for current project facts.
   - For an external target, confirm `target_project_root` first. If target cognition is stale or missing, record target evidence status instead of treating current project cognition as proof.

4. `question-loop`
   - Ask exactly one high-impact question per turn unless the remaining topic is local and low risk.
   - Track hard and soft unknowns in `open-questions.md`.

5. `technical-options`
   - Present 2-3 implementation paths only when strategy affects requirements and the Context Boundary Gate is resolved.
   - Include recommendation, trade-offs, risks, verification approach, rollback or de-scope path, and required evidence.

6. `handoff-assessment`
   - Decide whether one complete handoff package can be produced or discussion must continue.
   - If the direction is too broad to express as one coherent handoff, the result is `continue-discussion`.

7. `handoff-draft`
   - Write Markdown and JSON together only after explicit user request and a bounded unified scope.
   - The handoff is a contract, not a prose summary.

8. `handoff-self-review`
   - Check placeholders, contradictions, missing goal, missing target path, unresolved hard unknowns, weak evidence provenance, Markdown/JSON drift, Must-Preserve coverage, and consequence obligations.

9. `handoff-user-review`
   - Ask the user to review the handoff.
   - User confirmation is required before `handoff-ready`.

10. `handoff-ready`
   - Only after user confirmation. Then tell the user how to invoke the integration-appropriate `sp-specify` command with `.specify/discussions/<slug>/handoff-to-specify.md`.
```

- [ ] **Step 5: Insert the Context Boundary Gate section**

Insert this section before `## Staged Project Cognition Gate`:

```markdown
## Context Boundary Gate

The Context Boundary Gate triggers semantically when the user request implies an unclear boundary involving:

- execution target project or target root
- current repository role
- reference project or source artifact
- external system or service boundary
- existing module, package, adapter, generated artifact, or workflow surface
- path where work must land
- source of truth for existing behavior
- evidence source needed before making technical claims

When the gate triggers and the relevant boundary is not locked, `sp-discussion` may continue only with boundary clarification and product framing. It must not provide project-specific technical recommendations, name affected files, modules, APIs, or tests as facts, claim a target implementation path, write handoff files, mark the discussion `handoff-ready`, or tell the user to proceed to `sp-specify`.

For cross-project transfer requests, lock the target project root immediately. If the target root is unknown, continue only with goal, scope, non-goals, and success signals. The handoff must say whether the active repository is the implementation target, a reference source, both, or unrelated. Current project's cognition cannot prove another project's implementation facts.
```

- [ ] **Step 6: Replace handoff assessment and remove split mode sections**

Delete the `## Split Mode Inside sp-discussion` section. Replace `## Handoff Assessment` with:

```markdown
## Handoff Assessment

Handoff assessment is explicit-user-request only. Run it when the user says the discussion is done, asks to hand off, asks to feed the result to `sp-specify`, or asks to continue the next stage.

Write or refresh `handoff-assessment.md` with:

- decision status: `ready-for-specify` or `continue-discussion`
- rationale citing `requirements.md`, `technical-options.md`, `project-context.md`, `open-questions.md`, boundary evidence, or explicit user confirmation
- assessment dimensions: feature coherence, implementation target clarity, current repository role, reference source clarity, planning shape, validation shape, and risk profile
- required next action: `write-unified-handoff` or `continue-discussion`

Assessment outcomes:

- `ready-for-specify`: the mature discussion describes one coherent handoff boundary with locked context. Write the unified `handoff-to-specify.md` and `handoff-to-specify.json` pair.
- `continue-discussion`: the discussion is missing clarity, boundary facts, evidence provenance, user confirmation, or a coherent unified scope. Return to the question loop.

Do not use `split-required`. Do not write `split-plan.md`. Broad work must be represented inside the single handoff through a capability map, recommended sequence, dependencies, deferred scope, and reopen conditions, or stay in discussion until the scope is coherent.
```

- [ ] **Step 7: Replace `## Handoff To sp-specify`**

Replace the existing `## Handoff To sp-specify` section up to `## Must-Preserve Ledger` with:

```markdown
## Handoff To sp-specify

Handoff is explicit-user-request only and follows handoff assessment.

Write exactly one current handoff pair:

- `.specify/discussions/<slug>/handoff-to-specify.md`
- `.specify/discussions/<slug>/handoff-to-specify.json`

Both files are mandatory. Missing Markdown is invalid because the user-reviewable source is absent. Missing JSON is invalid because downstream workflows need structured boundary, review, and Must-Preserve status. Do not reconstruct a missing JSON companion during handoff; refresh the handoff in `sp-discussion` instead.

The handoff Markdown and JSON must agree on `handoff_goal`, `discussion_slug`, context boundary fields, implementation target fields, quality gate status, Must-Preserve IDs, Senior Consequence Analysis status, and open blockers.

The handoff must include:

- `handoff_goal`: one concrete statement of what is being handed to `sp-specify`
- `context_boundary`: `current_project_root`, `current_project_roles`, `target_project_root`, `target_project_roles`, `reference_projects`, `external_systems`, `path_status`, `boundary_confidence`, and `boundary_unknowns`
- role objects in `current_project_roles` and `target_project_roles`, each with `role`, `scope`, `evidence_source`, and `notes`
- `implementation_target`: actual project to change, target root path when local, target paths or modules, target paths still to verify, target project cognition status, and the statement that current project cognition cannot prove another project's implementation facts
- `source_evidence`: source type for each important conclusion, such as user confirmation, current project cognition, target project cognition, reference project cognition, live read, external source, or explicit assumption
- `blocking_unknowns`: hard unknowns that block readiness and soft unknowns with owner, latest resolve phase, and stop-and-reopen condition
- `downstream_instructions`: settled decisions, assumptions to preserve, conflicts requiring return to `sp-discussion`, capability map, recommended sequence, dependencies, deferred scope, and reopen conditions
- `quality_gate`: `status`, `self_reviewed_at`, `user_review_required`, `user_confirmed_at`, and `blocked_reasons`
```

- [ ] **Step 8: Add the handoff quality gate**

Insert this section after the Must-Preserve Ledger section:

```markdown
## Handoff Quality Gate

The handoff quality gate is mandatory. `sp-discussion` must not mark a handoff ready when any of these checks fail:

- missing or vague `handoff_goal`
- Context Boundary Gate still unresolved
- cross-project request lacks `target_project_root`
- target path exists but evidence source is not named
- current repository roles are not an explicit list of role objects
- target project roles are not an explicit list of role objects when a target exists
- role objects lack `role`, `scope`, `evidence_source`, or `notes`
- Markdown or JSON companion is missing
- Markdown and JSON disagree on shared fields
- hard unknowns remain open
- soft unknowns lack owner, latest resolve phase, or stop-and-reopen condition
- Must-Preserve Ledger omits goal, scope, non-goals, key decisions, acceptance signals, path constraints, or blocking questions
- quality gate lacks self-review status
- user has not reviewed and confirmed the handoff

Before user confirmation, the handoff can exist only as a draft. Do not recommend `sp-specify` until `quality_gate.status` records user confirmation.
```

- [ ] **Step 9: Update the discussion shell partial**

Replace `templates/command-partials/discussion/shell.md` with this content:

```markdown
{{spec-kit-include: ../common/user-input.md}}

## Objective

Drive a resumable product and technical discussion that locks context boundaries, matures a rough idea into requirements and implementation options, and produces one reviewed handoff contract before formal specification.

## Context

- Primary inputs: the user's idea, the current discussion session under `.specify/discussions/<slug>/`, passive project memory, boundary evidence, and project cognition only when the discussion reaches source-grounded technical judgment.
- `discussion-state.md` is the durable session state source of truth.
- `sp-discussion` is upstream of `sp-specify`; it does not create feature branches or write formal feature artifacts.

## Process

- Create or resume the discussion session.
- Run the Context Boundary Gate before project-specific technical options, affected-file claims, implementation-path claims, or handoff generation.
- Ask one boundary or high-impact question at a time.
- Preserve key decisions in `discussion-log.md`.
- Keep `requirements.md`, `technical-options.md`, `project-context.md`, and `open-questions.md` current.
- If the user asks to transfer functionality into another project, lock `target_project_root` immediately before technicalizing.
- When the user explicitly asks to hand off or continue the next stage, write `handoff-assessment.md` first.
- If the direction is coherent and boundary-locked, write exactly one complete handoff package: `handoff-to-specify.md` and `handoff-to-specify.json`.
- If the direction is too broad to express as one coherent package, continue the discussion instead of writing candidate-specific handoff files.
- Run handoff self-review and require user confirmation before marking `handoff-ready`.
- When senior consequence analysis triggers, preserve `CA-###` obligations, affected objects, lifecycle states, dependency impact, recovery/validation needs, coverage gaps, and stop-and-reopen conditions in the unified handoff pair.

## Output Contract

- Maintain the independent discussion state and artifacts under `.specify/discussions/<slug>/`.
- Provide 2-3 project-grounded technical options only after the relevant boundary is locked.
- Report unresolved questions honestly instead of forcing planning readiness.
- Write `handoff-to-specify.md` and `handoff-to-specify.json` together; both files are mandatory for a valid handoff.
- Do not write `split-plan.md` or `handoffs/<candidate_id>-handoff-to-specify.{md,json}`.
- When explicit handoff is requested, include `handoff_goal`, `context_boundary`, `implementation_target`, `source_evidence`, `blocking_unknowns`, `downstream_instructions`, `quality_gate`, and a Must-Preserve Ledger.
- Do not mark handoff ready if role objects, target path context, evidence provenance, self-review status, user confirmation, or blocking unknown handling is missing.
- Preserve `coverage_status`, `planning_gate_status`, `hard_unknown_count`, and `open_conflict_count` for the downstream fidelity gate.

## Guardrails

- Do not edit source code or tests.
- Do not create feature branches or feature directories.
- Do not automatically invoke or route into `sp-specify`.
- Do not make project-specific technical claims before the Context Boundary Gate and staged cognition gate pass.
- Do not use current project cognition to prove another project's implementation facts.
```

- [ ] **Step 10: Run focused discussion tests**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_discussion_command_locks_context_boundary_before_technicalization tests/test_alignment_templates.py::test_discussion_command_requires_single_unified_handoff_pair tests/test_alignment_templates.py::test_discussion_shell_partial_summarizes_boundary_and_single_handoff_contract tests/test_alignment_templates.py::test_discussion_consequence_gate_covers_unified_handoff_pair tests/test_alignment_templates.py::test_discussion_handoff_requires_must_preserve_ledger_contract -q
```

Expected: PASS.

- [ ] **Step 11: Commit**

```powershell
git add templates/commands/discussion.md templates/command-partials/discussion/shell.md
git commit -m "docs: define discussion boundary handoff contract"
```

---

### Task 3: Update Discussion State And Handoff JSON Templates

**Files:**
- Modify: `templates/discussion-state-template.md`
- Modify: `templates/brainstorming-handoff-specify-template.json`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Replace `templates/discussion-state-template.md`**

Replace the file with:

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

- current_stage: context-intake | product-framing | context-grounding | question-loop | technical-options | handoff-assessment | handoff-draft | handoff-self-review | handoff-user-review | handoff-ready
- current_topic: [Short topic label]
- next_question: [One boundary or high-impact question, or none]
- blocker_reason: none
- readiness_note: [why the discussion is or is not ready for explicit handoff]

## Context Boundary

- context_boundary_status: not-started | needs-user-input | locked | blocked
- current_project_root: [absolute path or none]
- current_project_roles: []
- target_project_root: [absolute path, external target, or none]
- target_project_roles: []
- reference_sources: []
- external_systems: []
- boundary_blockers: []
- path_status: unknown | user-confirmed | target-read-confirmed | blocked
- boundary_confidence: unknown | low | medium | high

## Session Selection

- incomplete_statuses: active, blocked, handoff-ready
- resume_rule: resume only when exactly one incomplete discussion is available or the user selected a slug
- collision_rule: append date or short numeric suffix when a generated slug already exists

## Handoff Assessment

- handoff_assessment_status: not-run | ready-for-specify | continue-discussion
- handoff_assessment_path: handoff-assessment.md | none
- handoff_assessment_decided_at: [ISO-8601 timestamp or none]
- handoff_scope_shape: unified | blocked

## Handoff Review

- handoff_review_status: not-started | draft | self-review-passed | user-confirmed | blocked
- handoff_user_confirmed_at: [ISO-8601 timestamp or none]
- handoff_blocker_reason: none
- handoff_quality_gate: draft | self_review_passed | user_confirmed | blocked

## Allowed Artifact Writes

- discussion-state.md
- discussion-log.md
- requirements.md
- technical-options.md
- project-context.md
- open-questions.md
- handoff-assessment.md only after explicit user request
- handoff-to-specify.md only after explicit user request, boundary lock, self-review pass, and user confirmation
- handoff-to-specify.json only after explicit user request, boundary lock, self-review pass, and user confirmation

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
- add, recommend, or route to sp-split
- write split-plan.md
- write handoffs/<candidate_id>-handoff-to-specify.md
- write handoffs/<candidate_id>-handoff-to-specify.json
- write pointer-only handoff-to-specify.md or handoff-to-specify.json
- use current project cognition to prove another project's implementation facts

## Authoritative Files

- discussion-state.md
- discussion-log.md
- requirements.md
- technical-options.md
- project-context.md
- open-questions.md
- handoff-assessment.md when present
- handoff-to-specify.md when user-confirmed
- handoff-to-specify.json when user-confirmed

## Senior Consequence Analysis

- consequence_gate_status: not-triggered | triggered | ready | blocked | stood-down
- trigger_reason: none
- stand_down_reason: none
- active_consequence_obligations: []
- latest_consequence_handoff: none
- coverage_gap_count: 0

## Handoff

- handoff_to_specify: none
- handoff_to_specify_json: none
- handoff_goal: none
- quality_gate_status: draft | self_review_passed | user_confirmed | blocked
- handoff_requested_by_user: false
- next_command: none
```

- [ ] **Step 2: Replace `templates/brainstorming-handoff-specify-template.json`**

Replace the file with:

```json
{
  "version": 2,
  "status": "pending",
  "stage": "consequence-risk",
  "entry_source": null,
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
  "handoff_goal": null,
  "context_boundary": {
    "current_project_root": null,
    "current_project_roles": [],
    "target_project_root": null,
    "target_project_roles": [],
    "reference_projects": [],
    "external_systems": [],
    "path_status": "unknown",
    "boundary_confidence": "unknown",
    "boundary_unknowns": [],
    "role_object_contract": {
      "required_fields": [
        "role",
        "scope",
        "evidence_source",
        "notes"
      ],
      "allowed_roles": [
        "implementation_target",
        "reference_source",
        "template_source",
        "discussion_host",
        "unrelated"
      ]
    }
  },
  "implementation_target": {
    "actual_project": null,
    "target_root": null,
    "target_paths": [],
    "required_target_paths_to_verify": [],
    "target_project_cognition_status": null,
    "current_project_cognition_scope_note": "Current project cognition cannot prove another project's implementation facts."
  },
  "source_evidence": [],
  "blocking_unknowns": [],
  "downstream_instructions": {
    "settled_decisions": [],
    "preserved_assumptions": [],
    "conflicts_requiring_return": [],
    "capability_map": [],
    "recommended_sequence": [],
    "dependencies": [],
    "deferred_scope": [],
    "reopen_conditions": []
  },
  "quality_gate": {
    "status": "draft",
    "self_reviewed_at": null,
    "user_review_required": true,
    "user_confirmed_at": null,
    "blocked_reasons": []
  },
  "facts_file": "brainstorming/facts.json",
  "route_file": "brainstorming/route.json",
  "intent_file": "brainstorming/intent.json",
  "complexity_file": "brainstorming/complexity.json",
  "soft_unknowns": [],
  "unknowns": [],
  "must_preserve": [],
  "conflicts": [],
  "coverage_status": "not_started",
  "planning_gate_status": "blocked_by_incomplete_coverage",
  "handoff_integrity": "not-checked",
  "hard_unknown_count": 0,
  "open_conflict_count": 0,
  "compile_ready": false,
  "consequence_gate": {
    "triggered": false,
    "trigger_reason": null,
    "status": "not-applicable",
    "stand_down_reason": null
  },
  "consequence_analysis": {
    "affected_object_map": [],
    "state_behavior_matrix": [],
    "dependency_impact": [],
    "recovery_and_validation": [],
    "coverage_gaps": []
  },
  "consequence_obligations": [],
  "stop_and_reopen_conditions": [],
  "compiled_from": {
    "journal": "brainstorming/journal.ndjson",
    "event_range": [],
    "key_events": [],
    "evidence_ids": [],
    "compiled_at": null
  }
}
```

- [ ] **Step 3: Run focused template tests**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_discussion_state_template_is_independent_from_feature_workflow_state tests/test_alignment_templates.py::test_brainstorming_handoff_template_supports_context_boundary_quality_gate tests/test_alignment_templates.py::test_structured_json_templates_preserve_fidelity_status_fields tests/test_alignment_templates.py::test_structured_consequence_json_templates_exist -q
```

Expected: PASS.

- [ ] **Step 4: Commit**

```powershell
git add templates/discussion-state-template.md templates/brainstorming-handoff-specify-template.json
git commit -m "docs: add discussion boundary state templates"
```

---

### Task 4: Update `sp-specify` Defensive Handoff Intake

**Files:**
- Modify: `templates/commands/specify.md`
- Modify: `templates/command-partials/specify/shell.md`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Replace the `## Discussion Handoff Intake` section in `templates/commands/specify.md`**

Replace the entire section with:

```markdown
## Discussion Handoff Intake

If the user invokes `sp-specify` with an explicit path to `.specify/discussions/<slug>/handoff-to-specify.md`, `.specify/discussions/<slug>/handoff-to-specify.json`, or pastes a discussion handoff block, read that handoff before parsing the feature request.

- Treat the discussion handoff as an authoritative input to the brainstorming kernel, not a bypass around it.
- Accept only the unified handoff pair for the discussion: `handoff-to-specify.md` plus same-directory `handoff-to-specify.json`.
- Reject candidate-specific handoff files under `handoffs/`, `split-plan.md`, and deprecated compatibility metadata such as `candidate_id` or `source_split_plan` as active discussion handoff inputs. Those fields may remain null in JSON templates for compatibility, but they are not the current handoff route.
- When the supplied path is Markdown, read the same-directory `handoff-to-specify.json` companion before proceeding.
- Missing Markdown is invalid because the user-reviewable source is absent.
- Missing JSON is a hard handoff integrity blocker. Do not reconstruct the JSON companion from Markdown. Return to `sp-discussion` and refresh the handoff so Markdown and JSON are produced and reviewed together.
- If Markdown and JSON disagree on `handoff_goal`, `discussion_slug`, `context_boundary`, `implementation_target`, `quality_gate`, Must-Preserve item identity fields, or Senior Consequence Analysis fields, set `coverage_status: blocked_by_handoff_integrity`, block with a handoff integrity error, and tell the user to refresh the `sp-discussion` handoff.
- Require `quality_gate.status` to be `user_confirmed` or require equivalent `quality_gate.user_confirmed_at` evidence. Draft and self-review-only handoffs are not accepted.
- Require a concrete `handoff_goal`. Generic language such as "continue the discussion result" is invalid.
- Require complete `context_boundary` fields, including `current_project_roles` and required `target_project_roles`. Each role object must include `role`, `scope`, `evidence_source`, and `notes`.
- Require `target_project_root` when the request is cross-project, transfers functionality into another project, or names an external implementation target.
- Require hard unknowns to be closed before planning readiness. Soft unknowns must carry owner, latest resolve phase, and stop-and-reopen condition.
- Record `entry_source: sp-discussion` and the handoff path or pasted discussion handoff marker in the generated feature artifacts.
- Copy `handoff_goal`, `context_boundary`, `implementation_target`, `source_evidence`, `blocking_unknowns`, `downstream_instructions`, `quality_gate`, and the Must-Preserve Ledger into `FEATURE_DIR/brainstorming/handoff-to-specify.json`.
- Preserve boundary facts, capability map, delivery sequence, dependencies, deferred scope, confirmed requirements, confirmed non-goals, settled decisions, selected technical direction, critical references, trade-off rationale, and path constraints in `facts.json`, `intent.json`, `complexity.json`, `handoff-to-specify.json`, `specify-draft.md`, `spec.md`, `alignment.md`, `context.md`, or `references.md` according to the existing artifact responsibilities.
- Convert open questions from the handoff into explicit unknowns with `field`, `question`, `blocking_level`, `resolver`, `latest_resolve_phase`, `status`, and a user-visible reopen reason when the unknown can reopen upstream discussion truth.
- Cite the discussion handoff, JSON companion, `source_evidence`, and relevant `project-context.md` evidence in `references.md` or `context.md`.
- Do not re-ask settled discussion questions unless repository evidence, constitution rules, or user correction contradicts the handoff.
- If `target_project_root` differs from `current_project_root`, state that the current project's cognition is not proof of target-project implementation facts. Record whether target evidence comes from target cognition, minimal live reads, user confirmation, or explicit assumptions.
- If a settled discussion conclusion conflicts with repository evidence, constitution rules, project rules, project cognition evidence, or architecture constraints, block and ask the user to choose keep, revise, drop, or defer with an explicit risk contract. Do not silently reinterpret the ledger item.
- If a settled discussion conclusion is reopened, record the reopen reason before changing the derived spec package.
```

- [ ] **Step 2: Update the Discussion Fidelity Coverage Gate section**

In the same file, extend `## Discussion Fidelity Coverage Gate` with:

```markdown
Planning can be ready only when the handoff integrity check passes, `quality_gate` is user-confirmed, coverage is complete, no hard unknowns remain open, no conflicts remain open, and the context boundary is complete enough for `sp-plan` to choose the correct project context.

For cross-project handoffs, do not route the user to current-project `sp-map-scan -> sp-map-build` to prove target files. The correct recovery is target project path confirmation, target project cognition, minimal live reads in the target, or return to `sp-discussion` for missing boundary facts.
```

- [ ] **Step 3: Update `templates/command-partials/specify/shell.md`**

Add these bullets under `## Process` after the brainstorming truth bullets:

```markdown
- When invoked with a discussion handoff, accept only the unified `.specify/discussions/<slug>/handoff-to-specify.md` plus `.json` pair.
- Reject missing JSON as a hard handoff integrity blocker; do not reconstruct the JSON companion from Markdown.
- Require `handoff_goal`, complete `context_boundary`, role objects with `role`, `scope`, `evidence_source`, and `notes`, target root when cross-project, closed hard unknowns, and user-confirmed `quality_gate`.
- Reject candidate-specific handoff paths and return to `sp-discussion` to refresh the unified handoff.
- When target differs from current project, record that current project cognition cannot prove target-project implementation facts.
```

Add this bullet under `## Output Contract`:

```markdown
- Preserve discussion boundary facts, implementation target, source evidence, capability map, delivery sequence, deferred scope, quality gate, and Must-Preserve obligations in the brainstorming truth package and compiled spec artifacts.
```

- [ ] **Step 4: Run focused specify tests**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_specify_consumes_confirmed_unified_discussion_handoff_without_repair tests/test_alignment_templates.py::test_specify_discussion_handoff_has_coverage_and_planning_gate_split tests/test_alignment_templates.py::test_specify_template_requires_lossless_journal_stage_manifest_and_checkpoints tests/test_alignment_templates.py::test_specify_template_requires_brainstorming_lock_flow_and_handoff_chain -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add templates/commands/specify.md templates/command-partials/specify/shell.md
git commit -m "docs: harden specify discussion handoff intake"
```

---

### Task 5: Carry Target Boundary Through `sp-plan` And `sp-tasks`

**Files:**
- Modify: `templates/commands/plan.md`
- Modify: `templates/command-partials/plan/shell.md`
- Modify: `templates/plan-template.md`
- Modify: `templates/plan-contract-template.json`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/command-partials/tasks/shell.md`
- Modify: `templates/tasks-template.md`
- Modify: `templates/task-packet-template.json`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Update `templates/commands/plan.md` pre-plan handoff validation**

In the section that reads `FEATURE_DIR/brainstorming/handoff-to-specify.json`, extend the bullet list with:

```markdown
   - If `quality_gate.user_confirmed` or equivalent user-confirmed `quality_gate.status` is missing, stop and route back to `{{invoke:specify}}` or `sp-discussion` according to the recorded blocker.
   - If `handoff_goal` is missing or vague, stop and route back to `sp-discussion` for handoff refresh.
   - If `context_boundary` is incomplete, stop before structural planning.
   - If `target_project_root` is required but missing, stop before structural planning.
   - If hard unknowns or open conflicts remain, stop and report the named blocker.
   - If `target_project_root` differs from `current_project_root`, plan from the target project context. Current project's cognition is not proof of target-project implementation facts.
   - For cross-project implementation, artifact-only planning may proceed only with explicit minimal live reads, target path confirmation, and recorded risk when target cognition is stale or missing.
   - Do not tell the user to run current-project `{{invoke:map-scan}} -> {{invoke:map-build}}` to fix target-project coverage.
```

- [ ] **Step 2: Update `templates/command-partials/plan/shell.md`**

Add these bullets under `## Process`:

```markdown
- Validate `FEATURE_DIR/brainstorming/handoff-to-specify.json` before planning from a discussion handoff.
- Stop when `planning_gate_status` is not `ready`, `quality_gate.user_confirmed` is missing, `context_boundary` is incomplete, target project root is required but missing, hard unknowns remain open, or conflicts remain open.
- For cross-project implementation, plan from the target project context and record that current project cognition cannot prove target-project implementation facts.
- Use target cognition, minimal live reads in the target, user confirmation, or explicit assumptions for target evidence; do not ask the user to rebuild current-project cognition for target files.
```

- [ ] **Step 3: Update `templates/plan-template.md`**

Add this section after the existing Must-Preserve carry-forward section:

```markdown
## Implementation Target Boundary

- **Current project root**: [copy from `brainstorming/handoff-to-specify.json` `context_boundary.current_project_root`]
- **Current project roles**: [copy role objects with `role`, `scope`, `evidence_source`, and `notes`]
- **Target project root**: [copy from `context_boundary.target_project_root` or record why no external target exists]
- **Target project roles**: [copy role objects with `role`, `scope`, `evidence_source`, and `notes`]
- **Target paths/modules**: [copy verified target paths or required target paths still to verify]
- **Target evidence status**: [target cognition, minimal live reads, user confirmation, external source, or explicit assumption]
- **Reference sources**: [copy discussion `reference_projects` / discussion-state `reference_sources` as reference-only evidence]
- **Cognition scope rule**: Current project cognition cannot prove another project's implementation facts.
- **Stop condition**: If a required target root or target-relative path cannot be confirmed before implementation-shaping design, stop and return to `sp-discussion` or the user for boundary repair.
```

- [ ] **Step 4: Update `templates/plan-contract-template.json`**

Add these top-level keys after `"planning_gate_status": null`:

```json
  "context_boundary": {},
  "implementation_target": {},
  "target_project_root": null,
  "target_relative_paths": [],
  "target_evidence_status": null,
  "reference_projects": [],
  "boundary_constraints": [],
```

Verify the JSON remains valid with:

```powershell
python -m json.tool templates/plan-contract-template.json > $null
```

Expected: exit code 0.

- [ ] **Step 5: Update `templates/commands/tasks.md`**

In the context loading section where `plan.md` and `plan-contract.json` are read, add:

```markdown
   - Read the implementation target boundary from `plan.md#Implementation Target Boundary`, `plan-contract.json`, and `brainstorming/handoff-to-specify.json`.
   - Every implementation-shaping task must state target root, target-relative path or path discovery step, evidence status, relevant `MP-*` obligations, boundary constraints, and forbidden drift.
   - Do not silently point tasks to the current repository unless the handoff says the current repository is the implementation target.
   - If a task uses a reference project path, state why that path is reference-only or transfer evidence.
   - Stop task generation when the target root is required but missing or when target-relative paths cannot be discovered without guessing.
```

- [ ] **Step 6: Update `templates/command-partials/tasks/shell.md`**

Add these bullets under `## Process`:

```markdown
- Load implementation target boundary from `plan.md`, `plan-contract.json`, and `brainstorming/handoff-to-specify.json`.
- Carry target root, target-relative paths or discovery steps, evidence status, relevant `MP-*` obligations, and boundary constraints into every implementation-shaping task.
- Reject task packages that silently use the current repository when the handoff identifies another implementation target.
- Mark reference project paths as reference-only or transfer evidence instead of implementation paths.
```

- [ ] **Step 7: Update `templates/tasks-template.md`**

Add this section after `## Task Guardrail Index`:

```markdown
## Implementation Target Boundary

- **Target root**: Copy from `plan-contract.json` or `plan.md#Implementation Target Boundary`.
- **Target-relative paths**: Every implementation task must name a target-relative path or an explicit path discovery step.
- **Evidence status**: Each target path must say whether it is confirmed by target cognition, minimal live read, user confirmation, external source, or explicit assumption.
- **Reference-only paths**: If a task cites a reference project path, label it as reference-only or transfer evidence.
- **Forbidden drift**: Tasks must not silently point to the current repository unless the handoff identifies the current repository as the implementation target.
```

Add this row to the enriched task example under `### Scope Boundaries`:

```markdown
| target_root | [absolute target project root or same as current project root] |
| target_relative_paths | [target-relative implementation paths or path discovery step] |
| evidence_status | [target cognition, minimal live read, user confirmation, external source, or explicit assumption] |
```

- [ ] **Step 8: Update `templates/task-packet-template.json`**

Add these top-level keys after `"allowed_optimization_scope": []`:

```json
  "implementation_target": {},
  "target_root": null,
  "target_relative_paths": [],
  "evidence_status": null,
  "boundary_constraints": [],
```

Verify the JSON remains valid with:

```powershell
python -m json.tool templates/task-packet-template.json > $null
```

Expected: exit code 0.

- [ ] **Step 9: Run focused plan/tasks tests**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_plan_template_rejects_cross_project_handoff_without_target_context tests/test_alignment_templates.py::test_tasks_template_inherits_implementation_target_boundary tests/test_alignment_templates.py::test_plan_tasks_and_implement_preserve_discussion_fidelity_obligations tests/test_alignment_templates.py::test_plan_tasks_and_implement_templates_consume_structured_handoff_contracts -q
```

Expected: PASS.

- [ ] **Step 10: Commit**

```powershell
git add templates/commands/plan.md templates/command-partials/plan/shell.md templates/plan-template.md templates/plan-contract-template.json templates/commands/tasks.md templates/command-partials/tasks/shell.md templates/tasks-template.md templates/task-packet-template.json
git commit -m "docs: carry discussion target boundary into planning"
```

---

### Task 6: Update Docs And Passive Skills

**Files:**
- Modify: `tests/test_specify_guidance_docs.py`
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Modify: `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `templates/project-handbook-template.md`
- Modify: `docs/quickstart.md`
- Modify: `docs/installation.md`
- Test: `tests/test_specify_guidance_docs.py`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Replace old docs tests for split/candidate handoffs**

In `tests/test_specify_guidance_docs.py`, replace `test_guidance_docs_explain_discussion_split_continuation` with:

```python
def test_guidance_docs_explain_discussion_boundary_and_unified_handoff() -> None:
    readme = _read("README.md")
    handbook = _read("PROJECT-HANDBOOK.md")
    generated_handbook = _read("templates/project-handbook-template.md")

    for content in (readme, handbook, generated_handbook):
        lowered = content.lower()
        assert "Context Boundary Gate" in content
        assert "target project root" in lowered
        assert "current project cognition cannot prove another project's" in lowered
        assert "handoff-to-specify.md" in content
        assert "handoff-to-specify.json" in content
        assert "single unified handoff" in lowered or "one unified handoff" in lowered
        assert "quality_gate" in content
        assert "user confirmation" in lowered
        assert "split-plan.md" not in content
        assert "handoffs/<candidate_id>" not in content
        assert "CAND-001" not in content
        assert "CAND-002" not in content
```

Replace `test_quickstart_and_installation_explain_discussion_candidate_handoffs` with:

```python
def test_quickstart_and_installation_explain_discussion_boundary_handoffs() -> None:
    quickstart = _read("docs/quickstart.md")
    installation = _read("docs/installation.md")

    for content in (quickstart, installation):
        lowered = content.lower()
        assert "Context Boundary Gate" in content
        assert "target project root" in lowered
        assert "reference source" in lowered
        assert "handoff-to-specify.md" in content
        assert "handoff-to-specify.json" in content
        assert "single unified handoff" in lowered or "one unified handoff" in lowered
        assert "missing json" in lowered
        assert "user confirmation" in lowered
        assert "split-plan.md" not in content
        assert "handoffs/CAND-001-handoff-to-specify" not in content
        assert "handoffs/CAND-002-handoff-to-specify" not in content
```

- [ ] **Step 2: Run docs tests and verify red**

Run:

```powershell
pytest tests/test_specify_guidance_docs.py::test_guidance_docs_explain_discussion_boundary_and_unified_handoff tests/test_specify_guidance_docs.py::test_quickstart_and_installation_explain_discussion_boundary_handoffs -q
```

Expected: FAIL because docs still teach split-plan and candidate handoffs.

- [ ] **Step 3: Update workflow routing passive skill**

In `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`, update the `sp-discussion` guidance to include:

```markdown
- Use `sp-discussion` before `sp-specify` when the idea is rough, the product direction is unsettled, or the request depends on unclear project boundaries.
- `sp-discussion` must run the Context Boundary Gate before project-specific technical options, affected-file claims, or handoff generation.
- For cross-project or transfer requests, lock the target project root before technicalizing.
- Do not route to `sp-split`; broad directions either become one unified handoff with capability map, sequence, dependencies, deferred scope, and reopen conditions, or stay in `sp-discussion`.
- A valid discussion handoff is one pair: `handoff-to-specify.md` and `handoff-to-specify.json`, with self-review and user confirmation.
```

- [ ] **Step 4: Update project cognition gate passive skill**

In `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`, add:

```markdown
- Project cognition is project-scoped. Current project cognition proves only current project facts.
- In `sp-discussion`, if the implementation target is another repository or external project, lock `target_project_root` before source-grounded technical claims.
- Reference project cognition is supplemental-only and cannot replace target evidence.
- If target root is unknown, block technical options and handoff readiness; continue only with product framing and explicit unknowns.
- If target root is known but target cognition is stale or missing, use target cognition, minimal live reads in the target, user confirmation, or explicit assumptions. Do not ask the user to rebuild current-project cognition for target files.
```

- [ ] **Step 5: Update README discussion guidance**

Replace the README paragraph beginning `Use discussion before specify` and the bullet beginning ``- `discussion` to shape`` with wording that includes:

```markdown
Use `discussion` before `specify` when the idea is exploratory, has product trade-offs, or has unclear context boundaries. `discussion` runs a Context Boundary Gate before technical options or handoff generation: target project root, current repository role, reference sources, external systems, and evidence sources must be explicit before the workflow names project-specific implementation facts.

For cross-project work, current project cognition cannot prove another project's files. Lock the target project root and record whether target evidence comes from target cognition, minimal live reads, user confirmation, external source, or explicit assumptions.
```

Use this updated support-skill bullet:

```markdown
- `discussion` to shape a rough idea through resumable senior product and technical discussion before formal specification. It writes `.specify/discussions/<slug>/` artifacts, runs the Context Boundary Gate before technicalizing unclear target/reference/external boundaries, and creates exactly one unified `handoff-to-specify.md` plus `handoff-to-specify.json` pair only after explicit handoff request, self-review, and user confirmation. The handoff includes `handoff_goal`, `context_boundary`, `implementation_target`, `source_evidence`, `blocking_unknowns`, `downstream_instructions`, `quality_gate`, and a Must-Preserve Ledger. It does not automatically invoke `specify`.
```

- [ ] **Step 6: Update handbook surfaces**

In `PROJECT-HANDBOOK.md` and `templates/project-handbook-template.md`, replace the `Pre-spec discussion` bullet with:

```markdown
- **Pre-spec discussion**: `sp-discussion` stores resumable product/technical discussions under `.specify/discussions/<slug>/`, runs a Context Boundary Gate before technical options or handoff generation, and only hands off after explicit user request, self-review, and user confirmation. Cross-project requests must lock `target_project_root`; current project cognition cannot prove another project's implementation facts. The valid handoff is one unified `handoff-to-specify.md` plus `handoff-to-specify.json` pair with `handoff_goal`, `context_boundary`, `implementation_target`, evidence provenance, `quality_gate`, Must-Preserve Ledger, coverage status, and planning gate status. Downstream workflows must preserve each protected item or block for a user decision.
```

- [ ] **Step 7: Update quickstart and installation docs**

In both `docs/quickstart.md` and `docs/installation.md`, replace the current discussion paragraph that mentions `split-plan.md`, candidate backlog, or `handoffs/CAND-*` with:

```markdown
Use the canonical `discussion` workflow for rough ideas that need resumable product/technical discussion before formal specification. `discussion` stores `.specify/discussions/<slug>/` artifacts, asks one high-impact question at a time, and runs the Context Boundary Gate before technical options or handoff generation. If the request crosses projects, references another codebase, names an external system, or depends on an existing module, lock the target project root, current project role, reference source, and evidence source before making project-specific claims.

When the user explicitly asks to hand off, `discussion` writes exactly one unified `handoff-to-specify.md` plus `handoff-to-specify.json` pair only after self-review and user confirmation. Missing JSON is a hard integrity blocker for downstream intake. Broad directions stay in `discussion` until they can be expressed as one handoff with a capability map, recommended sequence, dependencies, deferred scope, and reopen conditions.
```

- [ ] **Step 8: Run focused docs and passive-skill tests**

Run:

```powershell
pytest tests/test_specify_guidance_docs.py::test_guidance_docs_position_discussion_before_specify tests/test_specify_guidance_docs.py::test_guidance_docs_explain_discussion_boundary_and_unified_handoff tests/test_specify_guidance_docs.py::test_quickstart_and_installation_explain_discussion_boundary_handoffs tests/test_alignment_templates.py::test_workflow_routing_mentions_discussion_before_specify_for_rough_ideas tests/test_alignment_templates.py::test_project_cognition_gate_has_staged_discussion_gate -q
```

Expected: PASS.

- [ ] **Step 9: Commit**

```powershell
git add tests/test_specify_guidance_docs.py templates/passive-skills/spec-kit-workflow-routing/SKILL.md templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md README.md PROJECT-HANDBOOK.md templates/project-handbook-template.md docs/quickstart.md docs/installation.md
git commit -m "docs: document discussion boundary handoffs"
```

---

### Task 7: Update Generated Integration Contract Tests

**Files:**
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Test: integration test files listed below

- [ ] **Step 1: Update Markdown integration helper**

In `tests/integrations/test_integration_base_markdown.py`, replace split/candidate assertions inside `_assert_discussion_contract` with:

```python
    assert "Context Boundary Gate" in command_content
    assert "target project root" in command_lower
    assert "one high-impact question at a time" in command_lower
    assert "one unified" in command_lower or "single unified" in command_lower
    assert "handoff-to-specify.md" in command_content
    assert "handoff-to-specify.json" in command_content
    assert "quality_gate" in command_content
    assert "user confirmation" in command_lower
    assert "Must-Preserve Ledger" in command_content
    assert "coverage_status" in command_content
    assert "planning_gate_status" in command_content
    assert "split-plan.md" not in command_content
    assert "handoffs/<candidate_id>" not in command_content
    assert "CAND-001" not in command_content
```

Add this test to `MarkdownIntegrationTests`:

```python
    def test_specify_command_rejects_bad_discussion_handoffs(self, tmp_path):
        i = get_integration(self.KEY)
        m = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, m)

        content = (i.commands_dest(tmp_path) / i.command_filename("specify")).read_text(encoding="utf-8")
        lowered = content.lower()

        assert "missing JSON is a hard handoff integrity blocker" in content
        assert "quality_gate.status" in content
        assert "current_project_roles" in content
    assert "target_project_roles" in content
    assert "target_project_root" in content
    assert "current project's cognition is not proof of target-project implementation facts" in lowered
    assert "do not reconstruct" in lowered
    assert "handoffs/<candidate_id>" not in content
```

- [ ] **Step 2: Update TOML integration helper**

Apply the same helper assertions and `test_specify_command_rejects_bad_discussion_handoffs` to `tests/integrations/test_integration_base_toml.py`, reading `parsed["prompt"]` for the `specify` command:

```python
        parsed = tomllib.loads((i.commands_dest(tmp_path) / i.command_filename("specify")).read_text(encoding="utf-8"))
        content = parsed["prompt"]
```

- [ ] **Step 3: Update skills integration helper**

In `tests/integrations/test_integration_base_skills.py`, replace split/candidate assertions inside `_assert_discussion_contract` with:

```python
    assert "Context Boundary Gate" in skill_content
    assert "target project root" in skill_lower
    assert "one high-impact question at a time" in skill_lower
    assert "one unified" in skill_lower or "single unified" in skill_lower
    assert "handoff-to-specify.md" in skill_content
    assert "handoff-to-specify.json" in skill_content
    assert "quality_gate" in skill_content
    assert "user confirmation" in skill_lower
    assert "Must-Preserve Ledger" in skill_content
    assert "coverage_status" in skill_content
    assert "planning_gate_status" in skill_content
    assert "split-plan.md" not in skill_content
    assert "handoffs/<candidate_id>" not in skill_content
    assert "CAND-001" not in skill_content
```

Extend `test_specify_skill_preserves_discussion_fidelity_contract` with:

```python
        assert "missing JSON is a hard handoff integrity blocker" in content
        assert "quality_gate.status" in content
        assert "current_project_roles" in content
        assert "target_project_roles" in content
        assert "target_project_root" in content
        assert "current project's cognition is not proof of target-project implementation facts" in lowered
        assert "do not reconstruct" in lowered
        assert "handoffs/<candidate_id>" not in content
```

- [ ] **Step 4: Run integration tests**

Run:

```powershell
pytest tests/integrations/test_integration_codex.py tests/integrations/test_integration_gemini.py tests/integrations/test_integration_codebuddy.py tests/integrations/test_integration_tabnine.py -q
```

Expected: PASS.

- [ ] **Step 5: Run base integration tests when collectable**

Run:

```powershell
pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py -q
```

Expected: PASS or no concrete tests collected for abstract mixins. Any concrete failure means the generated output did not preserve the contract.

- [ ] **Step 6: Commit**

```powershell
git add tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py
git commit -m "test: verify generated discussion boundary handoffs"
```

---

### Task 8: Final Verification

**Files:**
- No source edits expected unless verification reveals a missed contract surface.

- [ ] **Step 1: Run core template tests**

Run:

```powershell
pytest tests/test_alignment_templates.py -q
```

Expected: PASS.

- [ ] **Step 2: Run docs tests**

Run:

```powershell
pytest tests/test_specify_guidance_docs.py -q
```

Expected: PASS.

- [ ] **Step 3: Run integration rendering tests**

Run:

```powershell
pytest tests/integrations/test_integration_codex.py tests/integrations/test_integration_gemini.py tests/integrations/test_integration_codebuddy.py tests/integrations/test_integration_tabnine.py -q
```

Expected: PASS.

- [ ] **Step 4: Run JSON validity checks**

Run:

```powershell
python -m json.tool templates/brainstorming-handoff-specify-template.json > $null
python -m json.tool templates/plan-contract-template.json > $null
python -m json.tool templates/task-packet-template.json > $null
```

Expected: all commands exit 0.

- [ ] **Step 5: Search for superseded active split guidance**

Run:

```powershell
rg -n "split-plan.md|handoffs/<candidate_id>|handoffs/CAND-|candidate backlog|selected candidate handoff|latest selected candidate|reconstruct the JSON|reconstruct.*handoff" templates/commands templates/command-partials templates/passive-skills README.md PROJECT-HANDBOOK.md templates/project-handbook-template.md docs/quickstart.md docs/installation.md tests
```

Expected: no matches that describe active `sp-discussion` handoff behavior. Matches are allowed only when they explicitly say deprecated compatibility fields are rejected or are inside this implementation plan.

For every match outside this plan, classify it before closing:

```text
allowed: negative rejection, deprecated compatibility field, or test assertion that forbids active use
blocked: active workflow guidance that creates split-plan.md, candidate backlog, CAND-* handoff files, or reconstructs missing JSON
```

No `blocked` matches may remain.

- [ ] **Step 6: Run whitespace and status checks**

Run:

```powershell
git diff --check
git status --short
```

Expected: `git diff --check` prints no whitespace errors. `git status --short` shows only intentional files before the final commit or is clean after commits.

- [ ] **Step 7: Commit verification fixes if needed**

If Steps 1-6 required edits, commit them:

```powershell
git add tests/test_alignment_templates.py tests/test_specify_guidance_docs.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py templates/commands/discussion.md templates/command-partials/discussion/shell.md templates/discussion-state-template.md templates/brainstorming-handoff-specify-template.json templates/commands/specify.md templates/command-partials/specify/shell.md templates/commands/plan.md templates/command-partials/plan/shell.md templates/plan-template.md templates/plan-contract-template.json templates/commands/tasks.md templates/command-partials/tasks/shell.md templates/tasks-template.md templates/task-packet-template.json templates/passive-skills/spec-kit-workflow-routing/SKILL.md templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md README.md PROJECT-HANDBOOK.md templates/project-handbook-template.md docs/quickstart.md docs/installation.md
git commit -m "fix: align discussion boundary handoff surfaces"
```

If no files changed after prior commits, do not create an empty commit.

## Self-Review Checklist

- Spec coverage: Tasks cover the Context Boundary Gate, cross-project target-root locking, one-question discussion discipline, unified handoff pair, role-object contract, source evidence, blocking unknowns, quality gate, user confirmation, hard missing-JSON blocker, no JSON reconstruction, downstream `sp-specify` rejection, `sp-plan` cross-project cognition handling, `sp-tasks` target inheritance, docs including quickstart and installation, and integration rendering.
- Deprecated split behavior: Old `split-plan.md` and `handoffs/<candidate_id>` behavior is removed from active guidance and rejected by `sp-specify`.
- Placeholder scan: The implementation snippets do not use missing-content markers as plan instructions. Bracketed values appear only inside generated workflow templates that intentionally show user-editable state fields.
- Type consistency: `handoff_goal`, `context_boundary`, `implementation_target`, `source_evidence`, `blocking_unknowns`, `downstream_instructions`, `quality_gate`, `current_project_roles`, `target_project_roles`, `target_project_root`, and `target_relative_paths` are named consistently across tests, templates, and JSON.
- Test coverage: Red tests are written before template changes; final verification covers shared templates, docs, JSON validity, and generated integration surfaces.
