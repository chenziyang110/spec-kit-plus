# sp-discussion Lightweight Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `sp-discussion` evidence-first and lightweight during ordinary conversation while preserving durable recovery and strict handoff quality.

**Architecture:** This is a generated workflow contract change. Update the `sp-discussion` command template, shell partial, discussion state template, project cognition guidance, JSON handoff template, validation tests, and docs together. Project cognition remains advisory navigation; live repository evidence proves facts; ordinary turns append compact events and checkpoint only on semantic triggers; explicit handoff writes a draft Markdown/JSON pair before self-review and user confirmation.

**Tech Stack:** Markdown command templates, JSON artifact templates, Python artifact validators, pytest template tests, integration rendering tests, README/handbook docs.

---

## Reference Spec

- `docs/superpowers/specs/2026-05-21-sp-discussion-lightweight-recovery-design.md`

## Implementation Choice

Represent the evidence distinctions inside `source_evidence` as structured entries instead of adding new top-level JSON fields.

Each structured `source_evidence` entry should support these fields:

```json
{
  "source_type": "project_cognition_route | live_code_evidence | user_confirmation | explicit_assumption | external_source | missing | conflict",
  "evidence_status": "proven | inferred | stale-advisory | missing | conflict",
  "source": "path, command, user confirmation, or external reference",
  "claim": "specific fact or decision supported by the evidence",
  "project_cognition_route": [],
  "live_code_evidence": [],
  "needs_refresh": false,
  "notes": null
}
```

This keeps the JSON contract explicit without spreading `project_cognition_route`, `live_code_evidence`, `evidence_status`, and `needs_refresh` as top-level fields across downstream artifacts.

## File Structure

- `tests/test_alignment_templates.py`: primary template contract tests for `sp-discussion`, discussion state, and JSON handoff template.
- `tests/test_runtime_handbook_contract.py`: shared cognition guidance and docs assertions.
- `tests/integrations/test_integration_base_markdown.py`: rendered Markdown command contract.
- `tests/integrations/test_integration_base_toml.py`: rendered TOML prompt contract.
- `tests/integrations/test_integration_base_skills.py`: rendered skills contract.
- `tests/hooks/test_artifact_hooks.py`: JSON handoff validation behavior for structured `source_evidence`.
- `templates/commands/discussion.md`: source-of-truth `sp-discussion` prompt.
- `templates/command-partials/discussion/shell.md`: concise generated shell guidance.
- `templates/discussion-state-template.md`: recovery/checkpoint and draft handoff state fields.
- `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`: shared advisory cognition policy.
- `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`: routing hints for discussion before specify.
- `templates/brainstorming-handoff-specify-template.json`: structured `source_evidence` example contract.
- `src/specify_cli/hooks/artifact_validation.py`: validation for structured source evidence entries.
- `README.md`, `PROJECT-HANDBOOK.md`, `templates/project-handbook-template.md`: public and generated documentation.
- `src/specify_cli/integrations/base.py`: inspect only; update only if generated integration addenda conflict with the new discussion wording.

---

### Task 1: Add Failing Template Tests For Evidence-First Discussion

**Files:**
- Modify: `tests/test_alignment_templates.py`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Update the discussion cognition test to require discussion intent**

In `tests/test_alignment_templates.py`, replace the project-cognition assertions inside `test_discussion_staged_cognition_gate_and_technical_options_contract` with:

```python
    assert "project-cognition lexicon --intent discussion" in content
    assert "project-cognition query --intent discussion" in content
    assert "project-cognition query --intent plan" not in content
    assert "Question Evidence Gate" in content
    assert "Turn Classifier" in content
    assert "Cognition Advisory, Code Authority" in content
    assert "runtime truth" not in lowered
    assert "live repository" in lowered
    assert "readiness=blocked" in content
```

Keep the existing assertions for product framing, forbidden before the cognition gate, `minimal_live_reads`, clearly greenfield behavior, technical options board, and 2-3 options.

- [ ] **Step 2: Add a test for lightweight event logging and semantic checkpoints**

Add this test near the existing discussion tests:

```python
def test_discussion_uses_lightweight_events_and_semantic_checkpoints() -> None:
    content = _read("templates/commands/discussion.md")
    shell = _read("templates/command-partials/discussion/shell.md")
    state = _read("templates/discussion-state-template.md")
    combined = "\n".join([content, shell, state])
    lowered = combined.lower()

    assert "Lightweight Recovery Log" in content
    assert "Semantic Checkpoints" in content
    assert "ordinary turns append" in lowered
    assert "compact event" in lowered
    assert "checkpoint triggers" in lowered
    assert "do not refresh all files" in lowered
    assert "requirements.md only when product requirements have changed enough to matter" in combined
    assert "technical-options.md only when options are introduced, revised, selected, or rejected" in combined
    assert "project-context.md only when source-grounding evidence or cognition coverage changes" in combined
    assert "open-questions.md only when blocking or soft unknowns materially change" in combined
```

- [ ] **Step 3: Add a test for draft handoff state**

Update `test_discussion_state_template_is_independent_from_feature_workflow_state` by replacing the two existing strings:

```python
    assert "handoff-to-specify.md only after explicit user request, boundary lock, self-review pass, and user confirmation" in content
    assert "handoff-to-specify.json only after explicit user request, boundary lock, self-review pass, and user confirmation" in content
```

with:

```python
    assert "handoff-to-specify.md draft after explicit user request and boundary lock" in content
    assert "handoff-to-specify.json draft after explicit user request and boundary lock" in content
    assert "mark handoff-ready only after self-review pass and user confirmation" in content
```

Also add:

```python
    assert "latest_event_checkpoint:" in content
    assert "last_compaction_checkpoint:" in content
    assert "latest_cognition_readiness:" in content
```

- [ ] **Step 4: Run the focused tests and verify they fail**

Run:

```powershell
pytest tests/test_alignment_templates.py -k "discussion_staged_cognition or lightweight_events or discussion_state_template" -q
```

Expected: FAIL because `discussion.md` still uses `--intent plan`, lacks the new gates, and `discussion-state-template.md` still says handoff files exist only after user confirmation.

---

### Task 2: Add Failing Tests For Structured Source Evidence

**Files:**
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/hooks/test_artifact_hooks.py`
- Test: `tests/test_alignment_templates.py`
- Test: `tests/hooks/test_artifact_hooks.py`

- [ ] **Step 1: Extend the JSON handoff template test**

In `test_brainstorming_handoff_template_supports_context_boundary_quality_gate`, replace:

```python
    assert template.get("source_evidence") == []
```

with:

```python
    source_evidence = template.get("source_evidence")
    assert isinstance(source_evidence, list)
    assert source_evidence == []
    source_contract = template.get("source_evidence_contract")
    assert isinstance(source_contract, dict)
    assert source_contract.get("required_fields") == [
        "source_type",
        "evidence_status",
        "source",
        "claim",
    ]
    assert "project_cognition_route" in source_contract.get("optional_fields", [])
    assert "live_code_evidence" in source_contract.get("optional_fields", [])
    assert "needs_refresh" in source_contract.get("optional_fields", [])
    assert source_contract.get("allowed_evidence_statuses") == [
        "proven",
        "inferred",
        "stale-advisory",
        "missing",
        "conflict",
    ]
```

- [ ] **Step 2: Add artifact validation tests for source_evidence entries**

In `tests/hooks/test_artifact_hooks.py`, add these tests near other `handoff-to-specify.json` validation tests:

```python
def test_handoff_to_specify_accepts_structured_source_evidence(tmp_path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    handoff_path = feature_dir / "brainstorming" / "handoff-to-specify.json"
    payload = json.loads(_valid_must_preserve_handoff_payload())
    payload["source_evidence"] = [
        {
            "source_type": "project_cognition_route",
            "evidence_status": "stale-advisory",
            "source": ".specify/project-cognition/project-cognition.db",
            "claim": "Project cognition suggested the discussion template as a likely workflow surface.",
            "project_cognition_route": ["templates/commands/discussion.md"],
            "live_code_evidence": ["templates/commands/discussion.md"],
            "needs_refresh": False,
            "notes": "Cognition is advisory; live template read proves the claim.",
        }
    ]
    handoff_path.write_text(json.dumps(payload), encoding="utf-8")

    result = run_quality_hook(
        project_root=project,
        event_name="workflow.artifacts.validate",
        payload={"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "ok"


def test_handoff_to_specify_rejects_invalid_structured_source_evidence(tmp_path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    handoff_path = feature_dir / "brainstorming" / "handoff-to-specify.json"
    payload = json.loads(_valid_must_preserve_handoff_payload())
    payload["source_evidence"] = [
        {
            "source_type": "project_cognition_route",
            "evidence_status": "fresh",
            "source": "",
            "claim": "",
        }
    ]
    handoff_path.write_text(json.dumps(payload), encoding="utf-8")

    result = run_quality_hook(
        project_root=project,
        event_name="workflow.artifacts.validate",
        payload={"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("source_evidence[0].evidence_status" in message for message in result.errors)
    assert any("source_evidence[0].source" in message for message in result.errors)
    assert any("source_evidence[0].claim" in message for message in result.errors)
```

- [ ] **Step 3: Run the focused tests and verify they fail**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_brainstorming_handoff_template_supports_context_boundary_quality_gate tests/hooks/test_artifact_hooks.py -k "source_evidence" -q
```

Expected: FAIL because `source_evidence_contract` and source evidence validation do not exist yet.

---

### Task 3: Update sp-discussion Command Template

**Files:**
- Modify: `templates/commands/discussion.md`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Update frontmatter output wording for draft handoff**

In `templates/commands/discussion.md`, change `workflow_contract.primary_outputs` so it says:

```yaml
  primary_outputs: '`.specify/discussions/<slug>/discussion-state.md`, `discussion-log.md`, `requirements.md`, `technical-options.md`, `project-context.md`, `open-questions.md`, `handoff-assessment.md` when handoff is requested, plus exactly one unified draft handoff pair `.specify/discussions/<slug>/handoff-to-specify.md` and `.specify/discussions/<slug>/handoff-to-specify.json` after explicit handoff request and boundary lock. The pair becomes handoff-ready only after self-review and user confirmation.'
```

- [ ] **Step 2: Replace the hard boundary handoff prohibition**

Replace this bullet:

```markdown
- Do not create or refresh `handoff-to-specify.md` or `handoff-to-specify.json` unless the user explicitly asks to hand off, the Context Boundary Gate is locked, the handoff self-review passes, and the user confirms the handoff.
```

with:

```markdown
- Do not create or refresh `handoff-to-specify.md` or `handoff-to-specify.json` unless the user explicitly asks to hand off and the Context Boundary Gate is locked.
- Before user confirmation, the handoff pair is a draft only. Do not mark the discussion `handoff-ready` or recommend `sp-specify` until handoff self-review passes and the user confirms the handoff.
```

- [ ] **Step 3: Replace the Session Store handoff bullets**

Replace:

```markdown
- `handoff-to-specify.md` only after a bounded unified handoff passes self-review and user confirmation
- `handoff-to-specify.json` only after a bounded unified handoff passes self-review and user confirmation
```

with:

```markdown
- `handoff-to-specify.md` as a draft only after explicit user request, boundary lock, and a bounded unified scope; ready only after self-review and user confirmation
- `handoff-to-specify.json` as a draft companion only after explicit user request, boundary lock, and a bounded unified scope; ready only after self-review and user confirmation
```

- [ ] **Step 4: Insert the Turn Classifier and Question Evidence Gate sections**

Insert this section before `## Discussion Flow`:

```markdown
## Turn Classifier

Before asking a question, classify the user's latest input:

- `product_intent`: goal, user, scenario, desired behavior, non-goal, acceptance signal, preference, or trade-off.
- `current_project_fact`: a question or claim about the active repository's commands, files, workflows, runtime behavior, tests, templates, or docs.
- `target_boundary`: ambiguity about whether the active repository, another local project, a reference project, or an external system is the implementation target.
- `reference_boundary`: ambiguity about which source artifact, project, prior implementation, doc, or external system should be used as evidence.
- `handoff_request`: explicit request to feed the result to `sp-specify`, continue to the next stage, or produce handoff artifacts.
- `continuation_or_resume`: user wants to continue an existing discussion.

The classifier controls the next step. Product intent can be discussed directly or with one product question. Current project facts require evidence lookup before asking the user. Boundary gaps may require one concise boundary question. Handoff requests enter strict handoff assessment. Resume reads compact state and recent events first.

## Question Evidence Gate

Before asking the user a question, decide whether the agent can answer it from evidence.

Ask the user only for product decisions, preferences, trade-offs, genuine boundary gaps, evidence conflicts requiring user judgment, or facts unavailable after bounded lookup.

Do not ask the user when the answer can be found through current repository files, tests, scripts, CLI help, templates, authoritative docs, or a bounded project-cognition route followed by live reads.

When evidence lookup fails, report what was checked and ask one focused question. Do not ask broad questions such as "where is this implemented?" until bounded search and project-cognition navigation have failed.
```

- [ ] **Step 5: Replace the Staged Project Cognition Gate**

In `templates/commands/discussion.md`, replace the current numbered query flow and "runtime truth" paragraph with:

```markdown
Before `context-grounding`, `technical-options`, affected-surface analysis, or source-grounded recommendations, use project cognition only when current-project facts matter:

1. Read `.specify/project-cognition/status.json` for advisory freshness and runtime metadata when present.
2. Run `{{specify-subcmd:project-cognition lexicon --intent discussion --query="$ARGUMENTS" --format json}}`.
3. Translate the returned map terms into a bounded `query_plan` with `selected_concepts`, `rejected_concepts`, `expanded_queries`, `paths`, and `selection_reason`.
4. Run `{{specify-subcmd:project-cognition query --intent discussion --query-plan "<query_plan_json>" --format json}}`.
5. Use the returned readiness, route_pack, subgraph, missing coverage, and `minimal_live_reads` only as advisory navigation.
6. Read the returned `minimal_live_reads` before making project-specific technical claims.

Treat project cognition as advisory navigation and coverage metadata. Use it to choose minimal live reads. Do not treat it as authoritative evidence for current behavior; prove project facts from live repository files before asking the user or making technical claims.
```

- [ ] **Step 6: Replace freshness handling with readiness interpretation**

Replace the current `Freshness handling:` list with:

```markdown
Readiness handling:

- `ready`: read `minimal_live_reads`, then make claims only from live evidence.
- `review`: read `minimal_live_reads`, carry confidence labels, and ask only if live reads still leave the fact unresolved.
- `ambiguous`: present the likely candidates and ask the user to choose the intended target.
- `needs_update`: treat as map-quality advisory for ordinary discussion; use live reads and record the cognition gap. Recommend `{{invoke:map-update}}` only when map maintenance becomes relevant or before a handoff needs stronger coverage.
- `needs_rebuild`: continue product framing if possible, but do not make project-specific technical claims until live evidence proves them or the user accepts an explicit assumption. Recommend `{{invoke:map-scan}} -> {{invoke:map-build}}` only when the user asks for map repair or handoff needs evidence that live reads cannot provide.
- `blocked`: report project cognition as unavailable or degraded, continue with product framing or bounded live evidence when safe, and recommend map repair only when the user asks for map maintenance or handoff needs evidence that live reads cannot provide.
```

- [ ] **Step 7: Add lightweight recovery and checkpoint sections**

Insert this section before `## Technical Options Board`:

```markdown
## Lightweight Recovery Log

Ordinary turns append a compact event to `discussion-log.md`. The event is not a transcript. It records only durable meaning: event kind, user input summary, agent conclusion, evidence used, open question delta, and whether a semantic checkpoint is required.

Do not refresh all structured files on ordinary turns. The event log exists to survive context compaction while keeping normal discussion lightweight.

## Semantic Checkpoints

Refresh structured files only at semantic checkpoints:

- user confirms a goal, non-goal, scope boundary, or important product decision
- discussion stage changes, such as product framing to technical options
- project evidence materially changes the understanding of the request
- a code fact was proven and must survive compaction
- evidence conflict is found
- the user asks for handoff or next-stage continuation
- context compaction risk is high
- an old discussion is resumed and compact state is missing or stale

Checkpoint refresh targets:

- `discussion-state.md`: short current summary, stage, confirmed decisions, open questions, boundary status, latest evidence route, and next question.
- `requirements.md`: only when product requirements have changed enough to matter.
- `technical-options.md`: only when options are introduced, revised, selected, or rejected.
- `project-context.md`: only when source-grounding evidence or cognition coverage changes.
- `open-questions.md`: only when blocking or soft unknowns materially change.

## Recovery Flow

When resuming a discussion, read `discussion-state.md` first, then recent `discussion-log.md` events since the last checkpoint. Read `requirements.md`, `technical-options.md`, `project-context.md`, or `open-questions.md` only when the state summary references them, is stale, is missing, or conflicts with recent events.
```

- [ ] **Step 8: Update source evidence handoff wording**

Replace the `source_evidence` handoff bullet with:

```markdown
- `source_evidence`: structured evidence entries with `source_type`, `evidence_status`, `source`, `claim`, optional `project_cognition_route`, optional `live_code_evidence`, optional `needs_refresh`, and optional `notes`. Project cognition route entries are advisory unless paired with live code, test, script, config, docs, external source, explicit assumption, or user confirmation evidence.
```

- [ ] **Step 9: Run the focused tests**

Run:

```powershell
pytest tests/test_alignment_templates.py -k "discussion_staged_cognition or lightweight_events or discussion_state_template" -q
```

Expected: PASS for the discussion template tests introduced in Task 1.

- [ ] **Step 10: Commit**

```powershell
git add tests/test_alignment_templates.py templates/commands/discussion.md
git commit -m "fix(discussion): make discussion evidence first"
```

---

### Task 4: Update Discussion Shell Partial And State Template

**Files:**
- Modify: `templates/command-partials/discussion/shell.md`
- Modify: `templates/discussion-state-template.md`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Update shell partial process bullets**

In `templates/command-partials/discussion/shell.md`, replace:

```markdown
- Ask one boundary or high-impact question at a time.
- Preserve key decisions in `discussion-log.md`.
- Keep `requirements.md`, `technical-options.md`, `project-context.md`, and `open-questions.md` current.
```

with:

```markdown
- Classify each user turn before asking a question.
- Run the Question Evidence Gate before asking the user; answer repository-discoverable facts from live evidence.
- Ask one boundary, product, trade-off, or evidence-conflict question at a time only when the answer cannot be proven from available evidence.
- Append compact ordinary-turn events to `discussion-log.md`.
- Refresh `requirements.md`, `technical-options.md`, `project-context.md`, and `open-questions.md` only at semantic checkpoints.
```

- [ ] **Step 2: Update shell partial cognition wording**

Add this bullet after the Context Boundary Gate bullet:

```markdown
- Use project cognition as advisory navigation only when current-project facts matter; use `--intent discussion`, read returned `minimal_live_reads`, and prove technical claims from live repository files.
```

- [ ] **Step 3: Update shell partial handoff wording**

Replace:

```markdown
- If the direction is coherent and boundary-locked, write exactly one complete handoff package: `handoff-to-specify.md` and `handoff-to-specify.json`.
```

with:

```markdown
- If the direction is coherent and boundary-locked after explicit handoff request, write exactly one draft handoff package: `handoff-to-specify.md` and `handoff-to-specify.json`.
```

Replace:

```markdown
- Write `handoff-to-specify.md` and `handoff-to-specify.json` together; both files are mandatory for a valid handoff.
```

with:

```markdown
- Write `handoff-to-specify.md` and `handoff-to-specify.json` together as a draft pair; both files are mandatory, and the pair becomes handoff-ready only after self-review and user confirmation.
```

- [ ] **Step 4: Update discussion state template for recovery fields**

In `templates/discussion-state-template.md`, add this section after `## Session Routing`:

```markdown
## Lightweight Recovery

- latest_event_checkpoint: [discussion-log.md event timestamp or none]
- last_compaction_checkpoint: [ISO-8601 timestamp or none]
- compact_summary_status: current | stale | missing
- ordinary_turn_write_policy: append compact event only
- structured_refresh_policy: semantic-checkpoint-only
```

- [ ] **Step 5: Update discussion state template for cognition evidence**

Add this section after `## Context Boundary`:

```markdown
## Evidence Navigation

- latest_cognition_intent: discussion | none
- latest_cognition_readiness: ready | review | ambiguous | needs_update | needs_rebuild | blocked | none
- latest_minimal_live_reads: []
- latest_live_evidence: []
- cognition_authority_rule: project cognition navigates; live repository evidence proves
- unresolved_evidence_conflicts: []
```

- [ ] **Step 6: Update allowed writes in state template**

Replace:

```markdown
- handoff-to-specify.md only after explicit user request, boundary lock, self-review pass, and user confirmation
- handoff-to-specify.json only after explicit user request, boundary lock, self-review pass, and user confirmation
```

with:

```markdown
- handoff-to-specify.md draft after explicit user request and boundary lock; mark handoff-ready only after self-review pass and user confirmation
- handoff-to-specify.json draft after explicit user request and boundary lock; mark handoff-ready only after self-review pass and user confirmation
```

Replace the authoritative file lines:

```markdown
- handoff-to-specify.md when user-confirmed
- handoff-to-specify.json when user-confirmed
```

with:

```markdown
- handoff-to-specify.md when draft or user-confirmed, according to handoff_review_status
- handoff-to-specify.json when draft or user-confirmed, according to handoff_review_status
```

- [ ] **Step 7: Run focused tests**

Run:

```powershell
pytest tests/test_alignment_templates.py -k "discussion_shell_partial or discussion_state_template or lightweight_events" -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add templates/command-partials/discussion/shell.md templates/discussion-state-template.md tests/test_alignment_templates.py
git commit -m "fix(discussion): add lightweight recovery state"
```

---

### Task 5: Update Project Cognition Passive Guidance

**Files:**
- Modify: `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- Modify: `tests/test_runtime_handbook_contract.py`
- Modify: `tests/test_alignment_templates.py`
- Test: `tests/test_runtime_handbook_contract.py`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Update passive skill wording**

In `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`, replace:

```markdown
- Treat the project cognition runtime as the cross-project cognition reference:
  explicit-only, supplemental-only, fresh-only, and minimal read before broader
  live-code inspection. Use it as a runtime truth surface for route and coverage
  decisions, while proving behavior from live project evidence.
```

with:

```markdown
- Treat project cognition as advisory navigation and coverage metadata. Use it
  to choose minimal live reads, ownership hints, consumers, state surfaces,
  verification routes, and coverage gaps. Do not treat it as authoritative
  evidence for current behavior; prove project facts from live repository files.
```

Replace:

```markdown
- A project-cognition query is not complete when it returns JSON. It is complete
  only when readiness drives routing, `minimal_live_reads` constrains
  inspection, and relevant facts are carried into the next workflow artifact or
  execution state.
```

with:

```markdown
- A project-cognition query is not complete when it returns JSON. It is complete
  only when readiness is interpreted as advisory navigation, `minimal_live_reads`
  constrains inspection, live evidence proves technical claims, and relevant
  facts are carried into the next workflow artifact or execution state.
```

- [ ] **Step 2: Add explicit discussion intent guidance**

In the `For sp-discussion` bullet, add:

```markdown
  Use `project-cognition lexicon --intent discussion` and
  `project-cognition query --intent discussion` for discussion grounding. Do not
  use `--intent plan` from `sp-discussion`.
```

- [ ] **Step 3: Add blocked readiness guidance**

In `Freshness State Guidance`, add:

```markdown
- If project cognition readiness is `blocked`, report the runtime issue as
  degraded advisory map state. Ordinary discussion may continue with product
  framing or bounded live evidence; recommend map repair only when the user asks
  for map maintenance or handoff needs evidence that live reads cannot provide.
```

- [ ] **Step 4: Update runtime handbook tests**

In `tests/test_runtime_handbook_contract.py`, update `test_project_cognition_passive_skill_mirrors_query_completion_contract`:

Replace:

```python
    assert "readiness drives routing" in content
```

with:

```python
    assert "readiness is interpreted as advisory navigation" in content
    assert "live evidence proves technical claims" in content
```

Add to `test_project_cognition_gate_has_staged_discussion_gate` in `tests/test_alignment_templates.py`:

```python
    assert "project-cognition lexicon --intent discussion" in content
    assert "project-cognition query --intent discussion" in content
    assert "--intent plan" not in content
```

- [ ] **Step 5: Run focused tests**

Run:

```powershell
pytest tests/test_runtime_handbook_contract.py::test_project_cognition_passive_skill_mirrors_query_completion_contract tests/test_alignment_templates.py -k "project_cognition_gate_has_staged_discussion_gate" -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md tests/test_runtime_handbook_contract.py tests/test_alignment_templates.py
git commit -m "fix(cognition): use discussion advisory intent"
```

---

### Task 6: Add Structured Source Evidence Contract

**Files:**
- Modify: `templates/brainstorming-handoff-specify-template.json`
- Modify: `src/specify_cli/hooks/artifact_validation.py`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/hooks/test_artifact_hooks.py`
- Test: `tests/test_alignment_templates.py`
- Test: `tests/hooks/test_artifact_hooks.py`

- [ ] **Step 1: Add source_evidence_contract to the JSON template**

In `templates/brainstorming-handoff-specify-template.json`, after:

```json
  "source_evidence": [],
```

add:

```json
  "source_evidence_contract": {
    "required_fields": [
      "source_type",
      "evidence_status",
      "source",
      "claim"
    ],
    "optional_fields": [
      "project_cognition_route",
      "live_code_evidence",
      "needs_refresh",
      "notes"
    ],
    "allowed_source_types": [
      "project_cognition_route",
      "live_code_evidence",
      "user_confirmation",
      "explicit_assumption",
      "external_source",
      "missing",
      "conflict"
    ],
    "allowed_evidence_statuses": [
      "proven",
      "inferred",
      "stale-advisory",
      "missing",
      "conflict"
    ],
    "authority_rule": "Project cognition navigates; live repository evidence proves current behavior."
  },
```

- [ ] **Step 2: Add validator constants**

In `src/specify_cli/hooks/artifact_validation.py`, near the other handoff validation constants, add:

```python
SOURCE_EVIDENCE_REQUIRED_FIELDS = ("source_type", "evidence_status", "source", "claim")
SOURCE_EVIDENCE_ALLOWED_TYPES = {
    "project_cognition_route",
    "live_code_evidence",
    "user_confirmation",
    "explicit_assumption",
    "external_source",
    "missing",
    "conflict",
}
SOURCE_EVIDENCE_ALLOWED_STATUSES = {
    "proven",
    "inferred",
    "stale-advisory",
    "missing",
    "conflict",
}
```

- [ ] **Step 3: Add the source evidence validator**

In `src/specify_cli/hooks/artifact_validation.py`, add this helper above `_validate_handoff_to_specify_payload`:

```python
def _validate_source_evidence_entries(payload: dict[str, Any], label: str) -> list[str]:
    errors: list[str] = []
    source_evidence = payload.get("source_evidence", [])
    if source_evidence in (None, ""):
        return errors
    if not isinstance(source_evidence, list):
        return [f"{label} source_evidence must be an array"]

    for index, item in enumerate(source_evidence):
        item_label = f"{label} source_evidence[{index}]"
        if not isinstance(item, dict):
            errors.append(f"{item_label} must be an object")
            continue
        for field in SOURCE_EVIDENCE_REQUIRED_FIELDS:
            if not str(item.get(field) or "").strip():
                errors.append(f"{item_label}.{field} is required")
        source_type = str(item.get("source_type") or "").strip()
        if source_type and source_type not in SOURCE_EVIDENCE_ALLOWED_TYPES:
            errors.append(f"{item_label}.source_type is invalid")
        evidence_status = str(item.get("evidence_status") or "").strip()
        if evidence_status and evidence_status not in SOURCE_EVIDENCE_ALLOWED_STATUSES:
            errors.append(f"{item_label}.evidence_status is invalid")
        for list_field in ("project_cognition_route", "live_code_evidence"):
            value = item.get(list_field)
            if value is not None and not (
                isinstance(value, list) and all(isinstance(entry, str) and entry.strip() for entry in value)
            ):
                errors.append(f"{item_label}.{list_field} must be an array of non-empty strings")
        if "needs_refresh" in item and item.get("needs_refresh") is not None and not isinstance(item.get("needs_refresh"), bool):
            errors.append(f"{item_label}.needs_refresh must be a boolean")
    return errors
```

- [ ] **Step 4: Call the validator**

Inside `_validate_handoff_to_specify_payload`, after `errors.extend(_validate_conflict_records(payload, label))`, add:

```python
    errors.extend(_validate_source_evidence_entries(payload, label))
```

- [ ] **Step 5: Run focused tests**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_brainstorming_handoff_template_supports_context_boundary_quality_gate tests/hooks/test_artifact_hooks.py -k "source_evidence" -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add templates/brainstorming-handoff-specify-template.json src/specify_cli/hooks/artifact_validation.py tests/test_alignment_templates.py tests/hooks/test_artifact_hooks.py
git commit -m "fix(handoff): validate structured source evidence"
```

---

### Task 7: Update Generated Integration Contract Tests

**Files:**
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Test: `tests/integrations/test_integration_base_markdown.py`
- Test: `tests/integrations/test_integration_base_toml.py`
- Test: `tests/integrations/test_integration_base_skills.py`

- [ ] **Step 1: Update the shared discussion contract assertions for Markdown**

In `tests/integrations/test_integration_base_markdown.py`, add these assertions to `_assert_discussion_contract`:

```python
    assert "Turn Classifier" in command_content
    assert "Question Evidence Gate" in command_content
    assert "Cognition Advisory, Code Authority" in command_content
    assert "project-cognition lexicon --intent discussion" in command_content
    assert "project-cognition query --intent discussion" in command_content
    assert "project-cognition query --intent plan" not in command_content
    assert "ordinary turns append" in command_lower
    assert "semantic checkpoints" in command_lower
    assert "draft pair" in command_lower
```

- [ ] **Step 2: Mirror the same assertions for TOML**

In `tests/integrations/test_integration_base_toml.py`, add the same assertions to `_assert_discussion_contract`, replacing `command_content` and `command_lower` with the existing local names.

- [ ] **Step 3: Mirror the same assertions for skills**

In `tests/integrations/test_integration_base_skills.py`, add equivalent assertions to `_assert_discussion_contract`:

```python
    assert "Turn Classifier" in skill_content
    assert "Question Evidence Gate" in skill_content
    assert "Cognition Advisory, Code Authority" in skill_content
    assert "project-cognition lexicon --intent discussion" in skill_content
    assert "project-cognition query --intent discussion" in skill_content
    assert "project-cognition query --intent plan" not in skill_content
    assert "ordinary turns append" in skill_lower
    assert "semantic checkpoints" in skill_lower
    assert "draft pair" in skill_lower
```

- [ ] **Step 4: Run integration rendering tests**

Run:

```powershell
pytest tests/integrations/test_integration_base_markdown.py -k discussion -q
pytest tests/integrations/test_integration_base_toml.py -k discussion -q
pytest tests/integrations/test_integration_base_skills.py -k discussion -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py
git commit -m "test(integrations): assert lightweight discussion contract"
```

---

### Task 8: Update User-Facing Docs

**Files:**
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `templates/project-handbook-template.md`
- Test: `tests/test_specify_guidance_docs.py`
- Test: `tests/test_runtime_handbook_contract.py`

- [ ] **Step 1: Update README discussion bullet**

In `README.md`, update the `discussion` bullet so it says:

```markdown
- `discussion` to shape a rough idea through resumable senior product and technical discussion before formal specification. It classifies each turn, answers repository-discoverable facts from live evidence, uses project cognition only as advisory navigation toward minimal live reads, appends compact ordinary-turn events, and refreshes structured discussion artifacts only at semantic checkpoints. It runs the Context Boundary Gate before technicalizing unclear target/reference/external boundaries and creates one draft unified handoff pair, `handoff-to-specify.md` plus `handoff-to-specify.json`, only after explicit handoff request and boundary lock. The pair becomes handoff-ready only after self-review and user confirmation.
```

Keep the existing list of handoff fields immediately after this text, or reflow it into a second sentence.

- [ ] **Step 2: Update PROJECT-HANDBOOK discussion bullet**

In `PROJECT-HANDBOOK.md`, update the **Pre-spec discussion** bullet with the same policy:

```markdown
`sp-discussion` classifies each user turn, asks only for product judgment or genuine boundary/evidence conflicts, uses project cognition as advisory navigation, proves technical facts from live repository evidence, appends compact ordinary-turn events, and refreshes structured discussion artifacts only at semantic checkpoints.
```

Keep the existing cross-project target-root and unified handoff guidance.

- [ ] **Step 3: Update generated handbook template**

Apply the same wording to `templates/project-handbook-template.md` so generated projects receive the behavior.

- [ ] **Step 4: Update docs tests**

In `tests/test_specify_guidance_docs.py`, add assertions to the existing discussion guidance tests:

```python
        assert "classifies each turn" in lowered
        assert "live evidence" in lowered
        assert "project cognition" in lowered
        assert "advisory navigation" in lowered
        assert "semantic checkpoints" in lowered
        assert "draft unified handoff pair" in lowered
```

In `tests/test_runtime_handbook_contract.py`, update `test_runtime_handbook_docs_are_query_backed` so it no longer expects runtime-truth wording for discussion and instead checks:

```python
    assert "advisory navigation" in lowered
    assert "live repository evidence" in lowered or "live evidence" in lowered
```

- [ ] **Step 5: Run docs tests**

Run:

```powershell
pytest tests/test_specify_guidance_docs.py tests/test_runtime_handbook_contract.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add README.md PROJECT-HANDBOOK.md templates/project-handbook-template.md tests/test_specify_guidance_docs.py tests/test_runtime_handbook_contract.py
git commit -m "docs: document lightweight discussion recovery"
```

---

### Task 9: Full Verification And Final Review

**Files:**
- Read: `docs/superpowers/specs/2026-05-21-sp-discussion-lightweight-recovery-design.md`
- Read: `templates/commands/discussion.md`
- Read: `templates/command-partials/discussion/shell.md`
- Read: `templates/discussion-state-template.md`
- Read: `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- Read: `templates/brainstorming-handoff-specify-template.json`
- Test: focused discussion, integration, docs, and hook test suites

- [ ] **Step 1: Run focused verification suite**

Run:

```powershell
pytest tests/test_alignment_templates.py -k "discussion or brainstorming_handoff_template or project_cognition_gate" -q
pytest tests/hooks/test_artifact_hooks.py -k "handoff_to_specify or source_evidence" -q
pytest tests/integrations/test_integration_base_markdown.py -k discussion -q
pytest tests/integrations/test_integration_base_toml.py -k discussion -q
pytest tests/integrations/test_integration_base_skills.py -k discussion -q
pytest tests/test_specify_guidance_docs.py tests/test_runtime_handbook_contract.py -q
```

Expected: all selected tests PASS.

- [ ] **Step 2: Search for stale discussion intent and runtime truth wording**

Run:

```powershell
rg -n "project-cognition (lexicon|query) --intent plan|runtime truth|Keep `requirements.md`, `technical-options.md`, `project-context.md`, and `open-questions.md` current|handoff-to-specify\\.md only after explicit user request, boundary lock, self-review pass, and user confirmation" templates README.md PROJECT-HANDBOOK.md tests
```

Expected:

- No matches in `templates/commands/discussion.md`, `templates/command-partials/discussion/shell.md`, or `templates/discussion-state-template.md`.
- Matches in unrelated workflows are acceptable only when they are not `sp-discussion` discussion-intent guidance.

- [ ] **Step 3: Verify source evidence schema is valid JSON**

Run:

```powershell
python -m json.tool templates/brainstorming-handoff-specify-template.json > $null
```

Expected: exit code 0.

- [ ] **Step 4: Review changed files**

Run:

```powershell
git status --short
git diff --stat HEAD
```

Expected: only files touched by this plan are modified after the final task commit, or the working tree is clean if each task committed.

- [ ] **Step 5: Handle any final cleanup explicitly**

If Step 4 shows a clean working tree, no action is needed.

If Step 4 shows uncommitted changes, stop and inspect them before committing:

```powershell
git diff --name-only
git diff --stat
git diff
```

Expected: any remaining changes are limited to files named in this plan. Commit only those verified files with a focused message that describes the actual cleanup. Do not use a catch-all `git add .`.

---

## Self-Review Checklist

After executing the plan:

- Every design requirement has a matching implementation task.
- `sp-discussion` uses `--intent discussion`, not `--intent plan`.
- `sp-discussion` says project cognition is advisory and live evidence is authoritative.
- The Question Evidence Gate prevents asking users for repository-discoverable facts.
- Ordinary turns append compact events; structured artifacts refresh at semantic checkpoints.
- Resume reads compact state and recent events before full artifact reload.
- Draft handoff and `handoff-ready` are separate states.
- JSON handoff evidence distinctions live inside structured `source_evidence` entries.
- Integration-rendered Markdown, TOML, and skill outputs preserve the updated discussion contract.
- Docs match templates.
- Focused tests pass.
