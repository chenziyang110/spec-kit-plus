# sp-discussion Advisor Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `sp-discussion` so it behaves like a senior product-engineering advisor that verifies current project truth before technical advice, explains decisions in owner-friendly language, preserves long-discussion context, and avoids narrow toothpaste-style replies.

**Architecture:** This is a shared-template-first behavior change. The core contract lives in `templates/commands/discussion.md`, the generated short-form contract in `templates/command-partials/discussion/shell.md`, durable current-state fields in `templates/discussion-state-template.md`, and passive/user-facing mirrors in passive skills and docs. Tests assert template and generated integration output so all supported integrations inherit the behavior.

**Tech Stack:** Markdown workflow templates, passive skill templates, Python `pytest` template-contract tests, Typer CLI help tests.

---

## File Structure

- Modify `tests/test_alignment_templates.py`
  - Add direct shared-template assertions for Truth Pass, Boss-Friendly Advisor Response, Discussion Compass, Anti-Toothpaste Protocol, and new state fields.
  - Extend passive skill tests so project cognition and workflow routing mirrors carry the new advisor contract where relevant.
- Modify `tests/integrations/test_integration_base_markdown.py`
  - Extend `_assert_discussion_contract()` so generated command outputs include the new advisor contract.
- Modify `tests/integrations/test_integration_base_skills.py`
  - Extend `_assert_discussion_contract()` so generated skills-based outputs include the new advisor contract.
- Modify `tests/test_specify_guidance_docs.py`
  - Extend discussion guidance doc assertions to cover advisor behavior in README, quickstart, installation, root handbook, and generated handbook template.
- Modify `tests/integrations/test_cli.py`
  - Update the discussion CLI help assertion if the CLI description is strengthened.
- Modify `templates/commands/discussion.md`
  - Add the four protocols and integrate them into flow, gates, semantic checkpoints, project context, technical options, and response quality rules.
- Modify `templates/command-partials/discussion/shell.md`
  - Add concise generated-shell guidance for truth pass, advisor response shape, compass, and anti-toothpaste behavior.
- Modify `templates/discussion-state-template.md`
  - Add truth pass, advisor confidence, and discussion compass fields.
- Modify `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
  - Strengthen `sp-discussion` cognition guidance to require a truth pass before source-grounded technical advice.
- Modify `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
  - Strengthen `sp-discussion` routing guidance to describe the senior advisor behavior without changing routing semantics.
- Modify `README.md`, `PROJECT-HANDBOOK.md`, `docs/quickstart.md`, `docs/installation.md`, `templates/project-handbook-template.md`
  - Update user-facing and generated-project descriptions where they already describe `discussion`.
- Modify `src/specify_cli/__init__.py`
  - Update `SKILL_DESCRIPTIONS["discussion"]` and CLI display text only to reflect the advisory upgrade. Do not add a new command.

Stand-down decisions locked into this plan:

- No new workflow command is added.
- No new required `discussion-brief.md` artifact is added in this cut.
- No source implementation behavior outside generated prompt/help/docs text is changed.
- `project-cognition` remains advisory navigation; live repository evidence remains authoritative.

---

### Task 1: Add Failing Shared-Template Tests

**Files:**
- Modify: `tests/test_alignment_templates.py`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Add a shared assertion helper for advisor contract text**

In `tests/test_alignment_templates.py`, insert this helper near the existing discussion tests, before `test_discussion_command_contract_is_pre_spec_and_resumable()`:

```python
def _assert_discussion_advisor_upgrade_contract(content: str) -> None:
    lowered = content.lower()

    assert "Truth Pass" in content
    assert "truth pass" in lowered
    assert "verified_project_facts" in content
    assert "open_assumptions" in content
    assert "evidence_checked" in content
    assert "advice_confidence" in content
    assert "Boss-Friendly Advisor Response" in content
    assert "judgment" in lowered
    assert "evidence" in lowered
    assert "risk" in lowered
    assert "recommendation" in lowered
    assert "next discussion" in lowered
    assert "Discussion Compass" in content
    assert "discussion_compass_status" in content
    assert "current_decision_frame" in content
    assert "confirmed_decisions" in content
    assert "changed_recommendations" in content
    assert "next_discussion_paths" in content
    assert "Anti-Toothpaste Protocol" in content
    assert "show the map" in lowered
    assert "ask only the highest-impact question" in lowered
    assert "do not recommend implementation work before the relevant truth pass" in lowered
```

- [ ] **Step 2: Assert the command template carries the advisor contract**

In `test_discussion_command_contract_is_pre_spec_and_resumable()`, after the existing include assertion, add:

```python
    _assert_discussion_advisor_upgrade_contract(content)
```

- [ ] **Step 3: Add a focused command behavior test**

Insert this test after `test_discussion_staged_cognition_gate_and_technical_options_contract()`:

```python
def test_discussion_requires_truth_pass_before_project_specific_advice() -> None:
    content = _read("templates/commands/discussion.md")
    lowered = content.lower()

    assert "## Truth Pass" in content
    assert "current project behavior" in lowered
    assert "existing capability reuse" in lowered
    assert "cross-cli propagation" in lowered
    assert "compatibility, lifecycle, state, security, or downstream workflow risk" in lowered
    assert "before the truth pass completes" in lowered
    assert "must not name affected files, modules, apis, tests, or implementation paths as facts" in lowered
    assert "project cognition remains advisory navigation" in lowered
    assert "live repository evidence proves current project behavior" in lowered
```

- [ ] **Step 4: Add a focused response-shape test**

Insert this test after the truth-pass test:

```python
def test_discussion_uses_boss_friendly_advisor_response_and_compass() -> None:
    content = _read("templates/commands/discussion.md")
    lowered = content.lower()

    assert "## Boss-Friendly Advisor Response" in content
    assert "the first sentence should be understandable to a non-technical owner" in lowered
    assert "judgment:" in lowered
    assert "evidence:" in lowered
    assert "risk:" in lowered
    assert "recommendation:" in lowered
    assert "next discussion paths:" in lowered
    assert "## Discussion Compass" in content
    assert "what are we solving now" in lowered
    assert "what has been confirmed" in lowered
    assert "what changed from earlier thinking" in lowered
    assert "what remains undecided" in lowered
    assert "what is the current recommended direction" in lowered
    assert "where we are" in lowered
```

- [ ] **Step 5: Add a focused anti-toothpaste test**

Insert this test after the response-shape test:

```python
def test_discussion_anti_toothpaste_protocol_maps_adjacent_decisions() -> None:
    content = _read("templates/commands/discussion.md")
    lowered = content.lower()

    assert "## Anti-Toothpaste Protocol" in content
    assert "literal issue the user raised" in lowered
    assert "deeper decision or risk behind it" in lowered
    assert "adjacent product, technical, workflow, or verification implications" in lowered
    assert "which items can be discussed together" in lowered
    assert "which item requires a clear user decision" in lowered
    assert "recommended order for the next discussion steps" in lowered
    assert "the rule is not \"ask many questions.\"" in lowered
    assert "show the map" in lowered
    assert "ask only the highest-impact question" in lowered
```

- [ ] **Step 6: Extend the shell partial test**

In `test_discussion_shell_partial_summarizes_boundary_and_single_handoff_contract()`, add:

```python
    assert "truth pass" in lowered
    assert "boss-friendly advisor response" in lowered
    assert "discussion compass" in lowered
    assert "anti-toothpaste" in lowered
    assert "verified_project_facts" in content
    assert "open_assumptions" in content
    assert "evidence_checked" in content
    assert "advice_confidence" in content
```

- [ ] **Step 7: Extend the state template test**

In `test_discussion_state_template_is_independent_from_feature_workflow_state()`, after the `recommendation_required_for_choices` assertion, add:

```python
    assert "truth_pass_status: not-needed | needed | in-progress | complete | blocked" in content
    assert "verified_project_facts:" in content
    assert "open_assumptions:" in content
    assert "evidence_checked:" in content
    assert "advice_confidence: high | medium | low | blocked | none" in content
    assert "discussion_compass_status: current | stale | missing" in content
    assert "current_decision_frame:" in content
    assert "confirmed_decisions:" in content
    assert "changed_recommendations:" in content
    assert "next_discussion_paths:" in content
```

- [ ] **Step 8: Extend passive skill tests**

In `test_workflow_routing_mentions_discussion_before_specify_for_rough_ideas()`, add:

```python
    assert "senior product-engineering advisor" in lowered
    assert "truth pass" in lowered
    assert "discussion compass" in lowered
    assert "anti-toothpaste" in lowered
```

In `test_project_cognition_gate_has_staged_discussion_gate()`, add:

```python
    assert "truth pass" in lowered
    assert "verified_project_facts" in content
    assert "open_assumptions" in content
    assert "evidence_checked" in content
    assert "advice_confidence" in content
```

- [ ] **Step 9: Run shared-template tests and verify they fail**

Run:

```powershell
pytest tests/test_alignment_templates.py -k "discussion or project_cognition_gate_has_staged_discussion_gate or workflow_routing_mentions_discussion" -q
```

Expected: FAIL with missing strings such as `Truth Pass`, `Boss-Friendly Advisor Response`, `discussion_compass_status`, and `anti-toothpaste`.

- [ ] **Step 10: Commit failing tests**

```powershell
git add tests/test_alignment_templates.py
git commit -m "test: define discussion advisor contract"
```

---

### Task 2: Implement Core Discussion Template and State Contract

**Files:**
- Modify: `templates/commands/discussion.md`
- Modify: `templates/command-partials/discussion/shell.md`
- Modify: `templates/discussion-state-template.md`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Strengthen the role section**

In `templates/commands/discussion.md`, replace:

```markdown
You are a senior technical expert and senior product manager working with the user to shape an idea before formal specification.
```

with:

```markdown
You are a senior product-engineering advisor: a senior technical expert and senior product manager working with the user to shape an idea before formal specification.
```

- [ ] **Step 2: Add Truth Pass section**

Insert this section after `## Question Evidence Gate` and before `## Adaptive Question Pack`:

```markdown
## Truth Pass

When the user asks for advice that depends on current project reality, complete a bounded truth pass before giving project-specific technical options, affected-surface claims, testing strategy claims, or implementation-path recommendations.

The truth pass is required when the turn involves current project behavior, command/template/script/test/documentation surfaces, implementation path or affected surface claims, existing capability reuse, cross-CLI propagation, compatibility, lifecycle, state, security, or downstream workflow risk.

The truth pass records:

- `verified_project_facts`: facts proven from live files, command output, tests, docs, or explicitly cited evidence
- `open_assumptions`: claims still unproven after bounded lookup
- `evidence_checked`: project cognition route, returned `minimal_live_reads`, repository files, commands, tests, docs, or user-provided references inspected
- `advice_confidence`: `high`, `medium`, `low`, or `blocked`

Project cognition remains advisory navigation. It helps select minimal live reads, but live repository evidence proves current project behavior.

Before the truth pass completes, `sp-discussion` may discuss product intent and decision shape, but must not name affected files, modules, APIs, tests, or implementation paths as facts. If evidence is insufficient, say so directly and explain what must be checked next instead of packaging an assumption as a recommendation.
```

- [ ] **Step 3: Add Boss-Friendly Advisor Response section**

Insert this section after `## Truth Pass`:

```markdown
## Boss-Friendly Advisor Response

Answer like a senior product-engineering advisor, not a support chatbot. For substantive turns, start with the decision-level meaning in plain language, then provide technical evidence.

Scale this response shape to the turn:

Judgment:
The decision-level answer in plain language.

Evidence:
What is known from project truth, user-confirmed intent, or explicit assumptions.

Risk:
What can go wrong if the obvious or premature path is chosen.

Recommendation:
The advised direction, including when not to choose it.

Next discussion paths:
The most useful adjacent decisions or checks to consider next.

The first sentence should be understandable to a non-technical owner. Technical detail follows only after the decision-level judgment is clear.

If evidence is insufficient, say: "I cannot responsibly recommend an implementation path yet because this depends on the current project shape. I need to verify the existing command, template, and test surfaces first." Adapt the evidence targets to the actual turn.
```

- [ ] **Step 4: Add Discussion Compass section**

Insert this section after `## Boss-Friendly Advisor Response`:

```markdown
## Discussion Compass

Maintain a compact current discussion compass so the user does not have to remember earlier turns.

The compass answers:

- what are we solving now?
- what has been confirmed?
- what changed from earlier thinking?
- what remains undecided?
- what is the current recommended direction?
- what is the next useful decision?

Refresh the compass in `discussion-state.md` at semantic checkpoints. In normal replies, include a short `Where we are` section when it helps orientation, especially after several turns on the same topic, a topic change, a confirmed product decision, a newly proven project fact, a changed recommendation, a handoff-readiness discussion, or when the user signals that context is becoming hard to track.

The compass is not a transcript. It is a decision-oriented summary.
```

- [ ] **Step 5: Add Anti-Toothpaste Protocol section**

Insert this section after `## Discussion Compass`:

```markdown
## Anti-Toothpaste Protocol

Do not make the user extract value one tiny answer at a time.

When the user raises a point, infer the broader decision surface and proactively identify:

- the literal issue the user raised
- the deeper decision or risk behind it
- adjacent product, technical, workflow, or verification implications
- which items can be discussed together
- which item requires a clear user decision
- a recommended order for the next discussion steps

The rule is not "ask many questions." The rule is:

- show the map
- recommend a next path
- ask only the highest-impact question when user judgment is needed

This extends the Adaptive Question Pack. Adaptive questions reduce narrow back-and-forth, but the anti-toothpaste protocol also requires the agent to surface the surrounding decision map and avoid passively waiting for the user to discover every implication.
```

- [ ] **Step 6: Update Discussion Flow entries**

In `templates/commands/discussion.md`, update these numbered flow entries:

For `context-grounding`, replace the three bullets with:

```markdown
   - Enter only after relevant boundaries are locked.
   - Use current project cognition only for current project facts.
   - Complete the Truth Pass before source-grounded recommendations, affected-surface claims, or project-specific implementation options.
   - For an external target, confirm `target_project_root` first. If target cognition is stale or missing, record target evidence status instead of treating current project cognition as proof.
```

For `question-loop`, add:

```markdown
   - Apply the Anti-Toothpaste Protocol before asking: show the decision map, recommend a next path, and ask only the highest-impact question when user judgment is needed.
```

For `technical-options`, replace the two bullets with:

```markdown
   - Present 2-3 implementation paths only when strategy affects requirements, the Context Boundary Gate is resolved, and the Truth Pass has established the relevant current-project facts or explicit assumptions.
   - Use the Boss-Friendly Advisor Response shape: include recommendation, evidence, trade-offs, risks, verification approach, rollback, recovery, or user-confirmed scope-adjustment path, and required evidence.
```

- [ ] **Step 7: Update Staged Project Cognition Gate forbidden language**

In `templates/commands/discussion.md`, replace:

```markdown
- project-specific technical recommendations
- affected module, file, or API claims
- implementation path recommendations
- source-code reads
- testing strategy claims tied to existing code
```

with:

```markdown
- project-specific technical recommendations
- affected module, file, API, or test claims
- implementation path recommendations
- testing strategy claims tied to existing code
- confident advice that hides open assumptions
```

Do not keep `source-code reads` in this forbidden list; the truth pass must allow bounded live reads when current project facts matter.

- [ ] **Step 8: Update Semantic Checkpoints targets**

In the `Semantic Checkpoints` section, add checkpoint triggers:

```markdown
- truth pass status changes
- the discussion compass becomes stale or a recommendation changes
```

Replace the `discussion-state.md` target bullet with:

```markdown
- discussion-state.md: short current summary, stage, confirmed decisions, open questions, boundary status, latest evidence route, truth pass status, advice confidence, discussion compass, and current question pack.
```

Replace the `project-context.md` target bullet with:

```markdown
- project-context.md only when source-grounding evidence, truth-pass evidence, assumptions, advice confidence, or cognition coverage changes.
```

- [ ] **Step 9: Update Technical Options Board**

In `Technical Options Board`, append this paragraph:

```markdown
Each option must distinguish evidence-backed facts from assumptions. If an option depends on an unverified claim, mark it as assumption-backed, name the evidence needed, and avoid presenting it as the recommended implementation path until the evidence is checked or the user accepts the assumption explicitly.
```

- [ ] **Step 10: Update shell partial process and output contract**

In `templates/command-partials/discussion/shell.md`, after the project cognition process bullet, add:

```markdown
- Complete a Truth Pass before source-grounded technical advice, affected-surface claims, implementation-path recommendations, or testing strategy claims tied to existing code; record `verified_project_facts`, `open_assumptions`, `evidence_checked`, and `advice_confidence`.
- Use a Boss-Friendly Advisor Response for substantive turns: lead with plain-language judgment, then evidence, risk, recommendation, and next discussion paths.
- Maintain a Discussion Compass in `discussion-state.md` so long conversations preserve what is being solved, what is confirmed, what changed, what remains undecided, the current recommendation, and the next useful decision.
- Apply the Anti-Toothpaste Protocol: show the broader decision map, recommend a next path, and ask only the highest-impact question when user judgment is needed.
```

In the Output Contract list, after "Report unresolved questions honestly...", add:

```markdown
- Distinguish verified project facts from open assumptions before presenting technical options.
- Keep the current discussion compass fresh at semantic checkpoints.
```

In Guardrails, replace:

```markdown
- Do not make project-specific technical claims before the Context Boundary Gate and staged cognition gate pass.
```

with:

```markdown
- Do not make project-specific technical claims before the Context Boundary Gate, staged cognition gate, and Truth Pass pass.
```

- [ ] **Step 11: Add state fields**

In `templates/discussion-state-template.md`, after `ui_discussion_status`, insert:

```markdown

## Advisor Contract

- truth_pass_status: not-needed | needed | in-progress | complete | blocked
- verified_project_facts: []
- open_assumptions: []
- evidence_checked: []
- advice_confidence: high | medium | low | blocked | none
- discussion_compass_status: current | stale | missing
- current_decision_frame: [one-sentence decision-level framing or none]
- confirmed_decisions: []
- changed_recommendations: []
- next_discussion_paths: []
```

In `Evidence Navigation`, add:

```markdown
- truth_pass_authority_rule: verify current-project facts with live evidence before technical advice
```

- [ ] **Step 12: Run shared-template tests**

Run:

```powershell
pytest tests/test_alignment_templates.py -k "discussion or project_cognition_gate_has_staged_discussion_gate or workflow_routing_mentions_discussion" -q
```

Expected: Some tests may still fail for passive skills until Task 3. Core command, shell, and state assertions should pass.

- [ ] **Step 13: Commit core templates**

```powershell
git add templates/commands/discussion.md templates/command-partials/discussion/shell.md templates/discussion-state-template.md
git commit -m "feat: add discussion advisor protocol"
```

---

### Task 3: Propagate Passive Skills, Docs, and CLI Help

**Files:**
- Modify: `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `docs/quickstart.md`
- Modify: `docs/installation.md`
- Modify: `templates/project-handbook-template.md`
- Modify: `src/specify_cli/__init__.py`
- Modify: `tests/test_specify_guidance_docs.py`
- Modify: `tests/integrations/test_cli.py`
- Test: `tests/test_alignment_templates.py`
- Test: `tests/test_specify_guidance_docs.py`
- Test: `tests/integrations/test_cli.py`

- [ ] **Step 1: Update project cognition passive skill**

In `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`, replace the existing `sp-discussion` bullet that starts with `For sp-discussion, product framing may begin...` with:

```markdown
- For `sp-discussion`, product framing may begin before the cognition gate. Before
  technical options, affected-surface claims, testing strategy claims tied to
  existing code, implementation-path recommendations, or source-grounded
  recommendations, complete the workflow's Truth Pass with the active
  launcher-backed project cognition query planning flow and bounded live evidence.
  Use `project-cognition lexicon --intent discussion` and
  `project-cognition query --intent discussion` for discussion grounding. Record
  `verified_project_facts`, `open_assumptions`, `evidence_checked`, and
  `advice_confidence`. Do not use `--intent plan` from `sp-discussion`.
```

- [ ] **Step 2: Update workflow routing passive skill**

In `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`, replace:

```markdown
- Use `sp-discussion` before `sp-specify` when the request is a rough idea, not-yet-ready requirement, unsettled product direction, or depends on unclear project boundaries.
```

with:

```markdown
- Use `sp-discussion` before `sp-specify` when the request is a rough idea, not-yet-ready requirement, unsettled product direction, or depends on unclear project boundaries. `sp-discussion` is the senior product-engineering advisor route: it performs a Truth Pass before project-specific technical advice, gives boss-friendly judgment with evidence and risk, maintains a Discussion Compass for long conversations, and applies the Anti-Toothpaste Protocol so the user does not have to pull out every implication one turn at a time.
```

- [ ] **Step 3: Update README discussion descriptions**

In `README.md`, update the two discussion paragraphs at the currently matched lines around 190 and 324. Preserve existing handoff details, and add this sentence to each:

```markdown
It acts as a senior product-engineering advisor: it performs a Truth Pass before project-specific technical advice, separates verified project facts from assumptions, gives boss-friendly judgment with evidence, risk, recommendation, and next discussion paths, maintains a Discussion Compass during long conversations, and avoids toothpaste-style one-point-at-a-time replies.
```

- [ ] **Step 4: Update PROJECT-HANDBOOK discussion description**

In `PROJECT-HANDBOOK.md`, update the `**Pre-spec discussion**` bullet to include:

```markdown
It is a senior product-engineering advisor surface: before project-specific technical advice it performs a Truth Pass, separates verified facts from assumptions, reports advice confidence, gives owner-readable judgment with evidence and risk, maintains a Discussion Compass, and proactively maps adjacent decisions instead of forcing toothpaste-style follow-up.
```

- [ ] **Step 5: Update generated handbook template**

In `templates/project-handbook-template.md`, update the `**Pre-spec discussion**` bullet with the same sentence from Step 4.

- [ ] **Step 6: Update quickstart discussion guidance**

In `docs/quickstart.md`, update the support-skill `discussion` bullet around line 293. Preserve the existing artifact and handoff wording, and add:

```markdown
It acts as a senior product-engineering advisor: before project-specific technical advice it performs a Truth Pass, records verified project facts, open assumptions, checked evidence, and advice confidence, gives boss-friendly judgment with evidence and risk, maintains a Discussion Compass, and avoids toothpaste-style one-point-at-a-time replies.
```

- [ ] **Step 7: Update installation discussion guidance**

In `docs/installation.md`, update the canonical `discussion` workflow paragraph around line 172. Preserve the existing artifact and handoff wording, and add the same sentence from Step 6.

- [ ] **Step 8: Update CLI help description**

In `src/specify_cli/__init__.py`, replace:

```python
"discussion": "Use when a rough idea or requirement needs a resumable product/technical discussion before formal specification.",
```

with:

```python
"discussion": "Use when a rough idea or requirement needs a resumable senior product-engineering discussion before formal specification.",
```

Replace the two display strings:

```python
"Mature a rough idea through resumable product and technical discussion before formal specification"
"Preserve product and technical discussion state before explicit handoff to [cyan]{_display_cmd('specify')}[/]"
```

with:

```python
"Mature a rough idea through resumable senior product-engineering discussion before formal specification"
"Preserve senior product-engineering discussion state before explicit handoff to [cyan]{_display_cmd('specify')}[/]"
```

- [ ] **Step 9: Update CLI help test**

In `tests/integrations/test_cli.py`, replace:

```python
assert "resumable product/technical" in discussion_help.output.lower()
```

with:

```python
assert "resumable senior product-engineering" in discussion_help.output.lower()
```

- [ ] **Step 10: Update guidance docs tests**

In `tests/test_specify_guidance_docs.py`, in `test_guidance_docs_position_discussion_before_specify()`, add these required substrings inside the loop for README, quickstart, and installation:

```python
        assert "senior product-engineering advisor" in content.lower()
        assert "truth pass" in content.lower()
        assert "discussion compass" in content.lower()
```

In `test_guidance_docs_explain_discussion_boundary_and_unified_handoff()`, add inside the loop for README, handbook, and generated handbook:

```python
        assert "senior product-engineering advisor" in lowered
        assert "verified facts" in lowered or "verified project facts" in lowered
        assert "advice confidence" in lowered
        assert "discussion compass" in lowered
```

- [ ] **Step 11: Run focused propagation tests**

Run:

```powershell
pytest tests/test_alignment_templates.py -k "discussion or project_cognition_gate_has_staged_discussion_gate or workflow_routing_mentions_discussion" -q
pytest tests/test_specify_guidance_docs.py -k "discussion" -q
pytest tests/integrations/test_cli.py::test_top_level_cli_exposes_discussion_entrypoint -q
```

Expected: PASS.

- [ ] **Step 12: Commit passive/docs/CLI propagation**

```powershell
git add templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md templates/passive-skills/spec-kit-workflow-routing/SKILL.md README.md PROJECT-HANDBOOK.md docs/quickstart.md docs/installation.md templates/project-handbook-template.md src/specify_cli/__init__.py tests/test_specify_guidance_docs.py tests/integrations/test_cli.py
git commit -m "docs: propagate discussion advisor guidance"
```

---

### Task 4: Add Generated Integration Coverage and Final Verification

**Files:**
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Test: `tests/integrations/test_integration_base_markdown.py`
- Test: `tests/integrations/test_integration_base_skills.py`

- [ ] **Step 1: Extend generated markdown discussion contract helper**

In `tests/integrations/test_integration_base_markdown.py`, in `_assert_discussion_contract()`, after the existing senior/consequence assertions, add:

```python
    assert "truth pass" in command_lower
    assert "verified_project_facts" in command_content
    assert "open_assumptions" in command_content
    assert "evidence_checked" in command_content
    assert "advice_confidence" in command_content
    assert "boss-friendly advisor response" in command_lower
    assert "discussion compass" in command_lower
    assert "anti-toothpaste" in command_lower
    assert "ask only the highest-impact question" in command_lower
```

- [ ] **Step 2: Extend generated skills discussion contract helper**

In `tests/integrations/test_integration_base_skills.py`, in `_assert_discussion_contract()`, add the same assertions:

```python
    assert "truth pass" in skill_lower
    assert "verified_project_facts" in skill_content
    assert "open_assumptions" in skill_content
    assert "evidence_checked" in skill_content
    assert "advice_confidence" in skill_content
    assert "boss-friendly advisor response" in skill_lower
    assert "discussion compass" in skill_lower
    assert "anti-toothpaste" in skill_lower
    assert "ask only the highest-impact question" in skill_lower
```

- [ ] **Step 3: Run generated integration tests**

Run:

```powershell
pytest tests/integrations/test_integration_base_markdown.py -k "discussion" -q
pytest tests/integrations/test_integration_base_skills.py -k "discussion" -q
```

Expected: PASS.

- [ ] **Step 4: Run all focused regression tests**

Run:

```powershell
pytest tests/test_alignment_templates.py -k "discussion or project_cognition_gate_has_staged_discussion_gate or workflow_routing_mentions_discussion" -q
pytest tests/test_specify_guidance_docs.py -k "discussion" -q
pytest tests/integrations/test_cli.py::test_top_level_cli_exposes_discussion_entrypoint -q
pytest tests/integrations/test_integration_base_markdown.py -k "discussion" -q
pytest tests/integrations/test_integration_base_skills.py -k "discussion" -q
```

Expected: PASS.

- [ ] **Step 5: Run formatting/whitespace check**

Run:

```powershell
git diff --check
```

Expected: no output.

- [ ] **Step 6: Commit integration coverage**

```powershell
git add tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py
git commit -m "test: verify generated discussion advisor contract"
```

- [ ] **Step 7: Final status check**

Run:

```powershell
git status --short
git log -4 --oneline
```

Expected: clean working tree and the four task commits visible.

---

## Self-Review Against Spec

- Truth Pass: covered by Task 1 tests and Task 2 command/shell/state implementation; passive cognition propagation in Task 3.
- Boss-Friendly Advisor Response: covered by Task 1 tests, Task 2 command/shell text, and generated integration checks in Task 4.
- Discussion Compass: covered by Task 1 state/template assertions, Task 2 state fields and semantic checkpoint updates, docs propagation in Task 3.
- Anti-Toothpaste Protocol: covered by Task 1 command tests, Task 2 protocol text, and routing/docs propagation in Task 3.
- Existing handoff lifecycle: preserved; no new command or artifact added.
- Surface sweep: all approved surfaces are listed with explicit updates. No surface is silently skipped.
- Project cognition authority: preserved as advisory navigation; live evidence remains authoritative.

No implementation task edits source behavior beyond help text and generated prompt/docs surfaces.
