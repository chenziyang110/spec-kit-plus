# Specify Analysis Rework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rework the Spec Kit Plus requirement workflow so `specify` becomes the sole pre-planning analysis entry point, add `spec-extend` and a stage explanation command, and introduce passive parallelism rules that can later drive multi-agent behavior without manual user selection.

**Architecture:** Start by locking the new workflow contract in tests, then reshape the command templates and spec artifacts to match the new analysis-first model. After the template layer is stable, add the new command surfaces and compatibility behavior in the Python CLI, then extend the Codex runtime dispatch layer with conservative passive-parallelism primitives and finish by validating the full end-to-end command surface.

**Tech Stack:** Python, Typer, Rich, Markdown command templates, packaged scaffolding assets, pytest

---

### Task 1: Lock the redesigned workflow contract in tests

**Files:**
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_clarify_template.py`
- Modify: `tests/integrations/test_cli.py`

- [ ] **Step 1: Add template assertions for the new mainline**

Update `tests/test_alignment_templates.py` so it asserts:
- `templates/commands/specify.md` describes `specify` as analysis-first and capable of producing planning-ready output on its own
- `templates/commands/plan.md` no longer teaches `specify -> clarify -> plan`
- `templates/commands/clarify.md` is treated as deprecated or compatibility-only
- new command templates for `spec-extend` and the stage explanation command are expected once added

- [ ] **Step 2: Replace clarify-specific assumptions with compatibility assertions**

Update `tests/test_clarify_template.py` so it stops enforcing the old "ask at least 5 questions" flow and instead verifies:
- `clarify` is compatibility-oriented
- `clarify` routes to `spec-extend` semantics
- the template still preserves alignment/report update behavior during the migration period

- [ ] **Step 3: Add CLI-surface expectations for new commands**

Extend `tests/integrations/test_cli.py` to assert the generated command/skill surfaces include:
- `sp-spec-extend`
- `sp-explain` or the final selected explanation command name
- updated descriptions for `specify`, `clarify`, and `plan`

- [ ] **Step 4: Run focused tests and confirm they fail before implementation**

Run:
```powershell
pytest tests/test_alignment_templates.py tests/test_clarify_template.py tests/integrations/test_cli.py -q
```

Expected:
- Failures showing the repository still advertises the old `specify -> clarify -> plan` contract
- Missing command-template expectations for the new commands

### Task 2: Rebuild the spec artifact contract around analysis-first output

**Files:**
- Modify: `templates/commands/specify.md`
- Modify: `templates/spec-template.md`
- Modify: `templates/alignment-template.md`
- Add: `templates/references-template.md`

- [ ] **Step 1: Rewrite `specify` around top-down analysis plus capability decomposition**

Update `templates/commands/specify.md` so the workflow explicitly:
- analyzes the whole feature first
- decomposes into capabilities
- records confirmed vs inferred vs unresolved states
- emits a planning-ready requirement package rather than a surface summary

- [ ] **Step 2: Replace the spec template with the new layered structure**

Update `templates/spec-template.md` so it includes sections for:
- overview
- scenarios and usage paths
- capability decomposition
- implementation-oriented analysis
- alignment state
- risks and gaps

- [ ] **Step 3: Teach alignment output to track analysis confidence**

Update `templates/alignment-template.md` so it records:
- confirmed facts
- low-risk inferences
- unresolved items
- release decision and downstream planning impact

- [ ] **Step 4: Add a dedicated reference-memory template**

Create `templates/references-template.md` with fields for:
- source
- description
- relevance
- reusable insights
- spec impact mapping

- [ ] **Step 5: Run focused template tests**

Run:
```powershell
pytest tests/test_alignment_templates.py -q
```

Expected:
- Template tests pass with the new `specify`/spec/alignment contract

### Task 3: Add `spec-extend` and the stage explanation command to the template layer

**Files:**
- Add: `templates/commands/spec-extend.md`
- Add: `templates/commands/explain.md`
- Modify: `templates/commands/clarify.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/tasks.md`

- [ ] **Step 1: Create the `spec-extend` command template**

Add `templates/commands/spec-extend.md` describing a workflow that:
- reads current spec artifacts
- scans for weak spots and misalignment
- optionally uses multi-agent research where justified
- updates `spec.md`, `alignment.md`, and `references.md`

- [ ] **Step 2: Create the stage explanation command template**

Add `templates/commands/explain.md` describing stage-aware plain-language interpretation for:
- `specify`
- `plan`
- `tasks`
- `implement`

Include explicit TUI expectations such as banner, status card, open-risk panel, and next-step panel.

- [ ] **Step 3: Downgrade `clarify` into compatibility mode**

Update `templates/commands/clarify.md` so it:
- clearly states it is no longer the main path
- preserves existing users through a compatibility bridge
- routes users toward `spec-extend`

- [ ] **Step 4: Update planning and task templates to consume the new spec shape**

Update `templates/commands/plan.md` and `templates/commands/tasks.md` so they:
- assume `specify` already performed the deep requirement analysis
- reference capability decomposition and references memory
- stop instructing users to treat `clarify` as the normal next step

- [ ] **Step 5: Run focused template regressions**

Run:
```powershell
pytest tests/test_alignment_templates.py tests/test_clarify_template.py -q
```

Expected:
- All template-level tests pass against the new command set and compatibility path

### Task 4: Register the new command surfaces in the CLI and packaged scaffolding

**Files:**
- Modify: `src/specify_cli/__init__.py`
- Modify: `tests/integrations/test_cli.py`
- Modify: `tests/test_extension_skills.py`

- [ ] **Step 1: Add the new command descriptions**

Update `SKILL_DESCRIPTIONS` and any related command-description surfaces in `src/specify_cli/__init__.py` so they include:
- `spec-extend`
- `explain`
- revised descriptions for `specify`, `clarify`, and `plan`

- [ ] **Step 2: Ensure bundled scaffolding picks up the new command templates**

Verify that the command-copy/install flow in `src/specify_cli/__init__.py` treats the new templates the same way as existing commands when scaffolding `.specify/`, `.agents/skills/`, or agent command directories.

- [ ] **Step 3: Update integration and skill-generation expectations**

Extend `tests/integrations/test_cli.py` and `tests/test_extension_skills.py` so generated projects assert the presence of:
- `sp-spec-extend`
- `sp-explain`

and confirm old `sp-clarify` remains available only as compatibility behavior.

- [ ] **Step 4: Run focused CLI and generation tests**

Run:
```powershell
pytest tests/integrations/test_cli.py tests/test_extension_skills.py -q
```

Expected:
- Generated command and skill surfaces include the new command files
- No regressions in existing integration packaging

### Task 5: Add passive-parallelism primitives for analysis and enhancement stages

**Files:**
- Modify: `src/specify_cli/codex_team/auto_dispatch.py`
- Add: `tests/codex_team/test_passive_parallelism.py`
- Modify: `tests/codex_team/test_auto_dispatch.py`

- [ ] **Step 1: Extract a stage-policy decision surface**

Refactor or extend the dispatch logic so a future command layer can ask a deterministic question like:
- should passive parallelism trigger for this stage?

Base the decision on inputs such as:
- number of references
- number of capabilities
- independent problem domains
- write-scope overlap

- [ ] **Step 2: Keep the first implementation conservative**

Do not make the runtime auto-dispatch everything. Limit the first policy helpers to reusable detection functions and payload shapes that command-layer logic can call safely.

- [ ] **Step 3: Add direct tests for passive-parallelism decisions**

Create `tests/codex_team/test_passive_parallelism.py` to cover:
- trigger for multi-reference analysis
- no trigger for unclear or tightly coupled work
- trigger for independent capability planning
- no trigger when write scopes overlap

- [ ] **Step 4: Keep existing batch-routing tests green**

Update `tests/codex_team/test_auto_dispatch.py` only as needed so the new helpers do not break current explicit parallel batch behavior.

- [ ] **Step 5: Run focused runtime tests**

Run:
```powershell
pytest tests/codex_team/test_auto_dispatch.py tests/codex_team/test_passive_parallelism.py -q
```

Expected:
- Existing explicit batch dispatch still passes
- New passive-policy tests pass without changing current runtime semantics unexpectedly

### Task 6: Validate end-to-end wording, migration, and documentation surfaces

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `CHANGELOG.md`
- Modify: `docs/superpowers/specs/2026-04-11-specify-analysis-rework-design.md`
- Modify: `docs/superpowers/plans/2026-04-11-specify-analysis-rework-implementation.md`

- [ ] **Step 1: Update user-facing workflow guidance**

Revise `README.md` and any workflow text in `AGENTS.md` that currently teaches or implies:
```text
specify -> clarify -> plan
```

Replace it with:
```text
specify -> plan
```

and mention `spec-extend` as the optional enhancement path.

- [ ] **Step 2: Record the architectural change**

Add a concise `CHANGELOG.md` entry describing:
- analysis-first `specify`
- new `spec-extend`
- new explanation command
- compatibility treatment of `clarify`

- [ ] **Step 3: Re-read the design and plan docs for consistency**

Verify the shipped implementation still matches:
- `docs/superpowers/specs/2026-04-11-specify-analysis-rework-design.md`
- this implementation plan

Update these docs if file names, command names, or scope changed during implementation.

- [ ] **Step 4: Run the full focused verification set**

Run:
```powershell
pytest tests/test_alignment_templates.py tests/test_clarify_template.py tests/integrations/test_cli.py tests/test_extension_skills.py tests/codex_team/test_auto_dispatch.py tests/codex_team/test_passive_parallelism.py -q
```

Expected:
- All focused tests pass
- The repository consistently advertises the new workflow and command set

## Verification Notes

- `pytest tests/test_alignment_templates.py -q`
- `pytest tests/test_clarify_template.py -q`
- `pytest tests/integrations/test_cli.py -q`
- `pytest tests/test_extension_skills.py -q`
- `pytest tests/codex_team/test_auto_dispatch.py -q`
- `pytest tests/codex_team/test_passive_parallelism.py -q`
- `pytest tests/test_alignment_templates.py tests/test_clarify_template.py tests/integrations/test_cli.py tests/test_extension_skills.py tests/codex_team/test_auto_dispatch.py tests/codex_team/test_passive_parallelism.py -q`
