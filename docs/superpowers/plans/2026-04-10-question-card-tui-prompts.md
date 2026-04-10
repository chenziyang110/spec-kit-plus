# Question Card TUI Prompts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade `specify` and `clarify` question prompts to a shared high-quality question-card protocol with recommendations, examples, and natural-language reply handling guidance.

**Architecture:** Keep this change prompt-template driven. Define one shared questioning contract in the `specify` and `clarify` command templates, mirror the same contract into the generated Codex skill files, and lock it with lightweight template tests so future edits do not regress the interaction shape.

**Tech Stack:** Markdown command templates, Codex skill mirror files, pytest

---

### Task 1: Lock the desired prompt contract with tests

**Files:**
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_clarify_template.py`

- [ ] Add assertions for the shared question-card protocol in `specify` and `clarify`.
- [ ] Add assertions for examples, recommended answers, short rationale, natural-language replies, and lightweight confirmation wording.
- [ ] Run the targeted tests and confirm they fail before template edits.

### Task 2: Update core command templates

**Files:**
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/clarify.md`

- [ ] Replace the old free-form questioning guidance with the shared question-card format.
- [ ] Keep the existing alignment/clarification rules intact while adding the new display and answer-parsing instructions.
- [ ] Ensure the text explicitly covers minimal headers, one-sentence questions, one-line examples, recommended answers, and concise confirmation after answer capture.

### Task 3: Sync generated Codex skill mirrors

**Files:**
- Modify: `.agents/skills/sp-specify/SKILL.md`
- Modify: `.agents/skills/sp-clarify/SKILL.md`

- [ ] Mirror the same question-card protocol into the skill files so local Codex skill content stays aligned with the command templates.
- [ ] Preserve existing metadata and command handoff behavior.

### Task 4: Verify targeted coverage

**Files:**
- Test: `tests/test_alignment_templates.py`
- Test: `tests/test_clarify_template.py`

- [ ] Run `pytest tests/test_alignment_templates.py tests/test_clarify_template.py -v`.
- [ ] Fix any failures without widening scope beyond the shared question-card prompt contract.
