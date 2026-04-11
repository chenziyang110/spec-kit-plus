# TUI Visual System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace brittle right-bordered ASCII card layouts with a unified open, single-side emphasis TUI system across template-driven interactions and Rich-rendered CLI panels.

**Architecture:** First lock the new visual contract in tests, then update the command templates that define the interactive card language, then normalize the Rich panel output in `src/specify_cli/__init__.py`, and finally verify the whole TUI family behaves as one coherent system without reintroducing right-side borders or boxed-card dependence.

**Tech Stack:** Python, Rich, Markdown command templates, pytest

---

### Task 1: Lock the TUI visual contract in tests

**Files:**
- Modify: `tests/test_alignment_templates.py`
- Add: `tests/test_tui_visual_contract.py`

- [ ] **Step 1: Add template-level assertions for the new open-block visual contract**

Update `tests/test_alignment_templates.py` so it verifies the relevant command templates no longer depend on right-side borders or closed ASCII box framing for primary interaction cards.

- [ ] **Step 2: Add a dedicated TUI visual contract test file**

Create `tests/test_tui_visual_contract.py` with contract-level assertions for:
- no right-side `|` card framing in primary template interaction surfaces
- open question block structure for `specify`
- stage-header / status / risk / next-step expectations in `explain`
- compatibility-mode visual distinction in `clarify`

- [ ] **Step 3: Keep the tests structural rather than copy-locked**

Make the new tests assert layout semantics and stable markers, not exact whitespace or full prose.

- [ ] **Step 4: Run the focused TUI contract tests and confirm they fail before implementation**

Run:
```powershell
pytest tests/test_alignment_templates.py tests/test_tui_visual_contract.py -q
```

Expected:
- failures showing the current templates still use older boxed-card assumptions or do not yet expose the new visual structure

### Task 2: Rebuild template-driven interaction surfaces around open single-side emphasis

**Files:**
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/clarify.md`
- Modify: `templates/commands/spec-extend.md`
- Modify: `templates/commands/explain.md`

- [ ] **Step 1: Redesign `specify` question blocks**

Update `templates/commands/specify.md` so the question-card contract becomes an open question block:
- stage header
- question header
- prompt
- example
- recommendation
- options
- reply instruction

Remove right-side border dependence and boxed-card closure.

- [ ] **Step 2: Apply the same open-block language to `clarify`**

Update `templates/commands/clarify.md` so compatibility-mode questioning and summaries follow the same open-block visual grammar, with stronger compatibility emphasis where relevant.

- [ ] **Step 3: Normalize `spec-extend` and `explain`**

Update:
- `templates/commands/spec-extend.md`
- `templates/commands/explain.md`

so they explicitly use:
- stage header
- status block
- explanation block
- risk block
- next-step block

- [ ] **Step 4: Run focused template verification**

Run:
```powershell
pytest tests/test_alignment_templates.py tests/test_clarify_template.py tests/test_tui_visual_contract.py -q
```

Expected:
- all template-driven TUI contract tests pass

### Task 3: Normalize Rich CLI panels to the same visual system

**Files:**
- Modify: `src/specify_cli/__init__.py`
- Modify: `tests/integrations/test_cli.py`

- [ ] **Step 1: Audit the main Rich panel surfaces**

Update `src/specify_cli/__init__.py` so these surfaces align with the new design language:
- next-step panels
- enhancement panels
- warning/error panels
- environment/status panels where practical

- [ ] **Step 2: Reduce closed-box feel where possible without breaking clarity**

Use lighter, more hierarchical presentation:
- stronger titles
- clearer status emphasis
- cleaner next-step emphasis
- less dependence on full-panel enclosure as the main organizing device

- [ ] **Step 3: Keep compatibility with existing CLI behavior**

Do not change command semantics. Only normalize the visual presentation and panel hierarchy.

- [ ] **Step 4: Update CLI tests as needed**

Adjust `tests/integrations/test_cli.py` only where the user-visible panel structure or labels changed materially.

- [ ] **Step 5: Run focused CLI/TUI verification**

Run:
```powershell
pytest tests/integrations/test_cli.py tests/test_tui_visual_contract.py -q
```

Expected:
- the visual contract remains green after Rich panel normalization

### Task 4: Add regression coverage for stage explanation and next-step emphasis

**Files:**
- Modify: `tests/test_tui_visual_contract.py`
- Modify: `tests/test_extension_skills.py`

- [ ] **Step 1: Lock the `explain` structure more directly**

Add or refine tests so `explain` keeps:
- stage-aware explanation behavior
- status presence
- risk emphasis
- next-step emphasis

without requiring exact prose.

- [ ] **Step 2: Verify generated skills still preserve the TUI-facing structure**

Update `tests/test_extension_skills.py` if needed so generated skill content for `sp-explain`, `sp-specify`, or compatibility `sp-clarify` still mirrors the intended TUI contract.

- [ ] **Step 3: Run focused regression checks**

Run:
```powershell
pytest tests/test_tui_visual_contract.py tests/test_extension_skills.py -q
```

Expected:
- generated skill surfaces and source templates remain visually aligned

### Task 5: Final focused verification and implementation notes

**Files:**
- Modify: `docs/superpowers/specs/2026-04-12-tui-visual-system-design.md`
- Modify: `docs/superpowers/plans/2026-04-12-tui-visual-system-implementation.md`

- [ ] **Step 1: Re-read the design against the shipped output**

If the implementation finalizes any naming or scope details differently than the current spec, update the design doc accordingly.

- [ ] **Step 2: Add short post-implementation notes to this plan**

Record any resolved trade-offs, especially around:
- how much framing remains in Rich panels
- how the open-block question structure was implemented
- any surfaces intentionally left for future passes

- [ ] **Step 3: Run the final focused verification set**

Run:
```powershell
pytest tests/test_alignment_templates.py tests/test_clarify_template.py tests/test_tui_visual_contract.py tests/integrations/test_cli.py tests/test_extension_skills.py -q
```

Expected:
- all focused TUI-related verification passes

## Verification Notes

- `pytest tests/test_alignment_templates.py tests/test_tui_visual_contract.py -q`
- `pytest tests/test_alignment_templates.py tests/test_clarify_template.py tests/test_tui_visual_contract.py -q`
- `pytest tests/integrations/test_cli.py tests/test_tui_visual_contract.py -q`
- `pytest tests/test_tui_visual_contract.py tests/test_extension_skills.py -q`
- `pytest tests/test_alignment_templates.py tests/test_clarify_template.py tests/test_tui_visual_contract.py tests/integrations/test_cli.py tests/test_extension_skills.py -q`
