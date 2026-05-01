# Project-Map Hard Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore `project-map` as the mandatory pre-source knowledge base for all `sp-*` workflows, upgrade Layer 1 into a real atlas entry surface, and align atlas production plus consumption contracts across this repository and generated projects.

**Architecture:** This implementation has four workstreams. First, replace the current tier-minimizing atlas loading rules with a hard atlas gate shared by ordinary `sp-*` workflows. Second, redesign Layer 1 and machine indexes so the atlas behaves like a dictionary and compass rather than a thin route table. Third, introduce logical atlas-reference semantics so the same workflow contract can target generated-project `.specify/project-map/**` outputs and this repository's `templates/project-map/**` truth surface. Fourth, make atlas consumption testable by recording atlas-read evidence in workflow state surfaces and by tightening template, guidance, and freshness tests.

**Tech Stack:** Markdown workflow templates, `{{spec-kit-include: ...}}` partials, JSON atlas index files, Python freshness helpers in `src/specify_cli/project_map_status.py`, pytest template-guidance tests, integration guidance injection in `src/specify_cli/integrations/base.py`.

---

## File Structure

```text
MODIFY
  templates/command-partials/common/context-loading-gradient.md
    Purpose: replace "read less" semantics with a hard atlas gate and tier-specific depth rules.
  templates/command-partials/common/navigation-check.md
    Purpose: either fold into or redirect to the shared atlas gate contract without leaving weaker fallback logic behind.
  templates/commands/fast.md
    Purpose: require atlas gate even for trivial work; remove source-first shortcuts and stale-warning behavior.
  templates/commands/quick.md
    Purpose: require atlas gate, remove warn-only stale behavior, and require root/module atlas reads before execution.
  templates/commands/debug.md
    Purpose: require atlas gate before observer framing moves into repro/log/code work.
  templates/commands/specify.md
    Purpose: replace path-specific layered-loading instructions with hard atlas-gate language and logical references.
  templates/commands/plan.md
    Purpose: align planning reads with the atlas hard gate and logical atlas references.
  templates/commands/tasks.md
    Purpose: align task-generation reads with the atlas hard gate and logical atlas references.
  templates/commands/implement.md
    Purpose: require atlas gate before packet compilation, dispatch, and implementation file reads.
  templates/project-map/QUICK-NAV.md
    Purpose: upgrade Layer 1 from a task-only route table into a dictionary-style entry surface.
  templates/project-map/index/atlas-index.json
    Purpose: expose atlas entrypoints, root topics, module metadata, and query-oriented routing hints.
  templates/project-handbook-template.md
    Purpose: describe the atlas as a hard-read four-layer knowledge base and route readers through the upgraded Layer 1.
  src/specify_cli/project_map_status.py
    Purpose: tighten freshness semantics, support atlas topic gating, and expose helpers that match the new hard-gate rules.
  src/specify_cli/integrations/base.py
    Purpose: replace hardcoded `.specify/project-map/*.md` consumption guidance with logical atlas-contract guidance.
  templates/workflow-state-template.md
    Purpose: add atlas-read evidence fields for resumable workflow state.
  templates/debug.md
    Purpose: add atlas-read evidence fields to debug-session state.

TESTS TO MODIFY
  tests/test_fast_template_guidance.py
  tests/test_quick_template_guidance.py
  tests/test_debug_template_guidance.py
  tests/test_alignment_templates.py
  tests/test_extension_skills.py
  tests/test_project_handbook_templates.py
  tests/test_project_map_layered_contract.py
  tests/test_project_map_status.py
  tests/test_map_scan_build_template_guidance.py
    Purpose: convert existing expectations from warn-first and thin Layer 1 behavior to hard-gate and dictionary-entry behavior.

NEW TESTS
  tests/test_project_map_hard_gate_guidance.py
    Purpose: assert shared hard-gate phrases across `sp-fast`, `sp-quick`, `sp-debug`, `sp-specify`, `sp-plan`, `sp-tasks`, and `sp-implement`.
  tests/test_project_map_entry_contract.py
    Purpose: assert the upgraded Layer 1 schema covers task routes, symptom routes, hotspots, verification entrypoints, and propagation routes.
```

---

## Task 1: Replace context-loading minimization with a shared hard atlas gate

**Files:**
- Modify: `templates/command-partials/common/context-loading-gradient.md`
- Modify: `templates/command-partials/common/navigation-check.md`
- Test: `tests/test_project_map_hard_gate_guidance.py`
- Test: `tests/test_fast_template_guidance.py`
- Test: `tests/test_quick_template_guidance.py`
- Test: `tests/test_debug_template_guidance.py`

- [ ] **Step 1: Write the failing shared hard-gate test**

Create `tests/test_project_map_hard_gate_guidance.py` with the following content:

```python
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(rel_path: str) -> str:
    return (PROJECT_ROOT / rel_path).read_text(encoding="utf-8")


TARGETS = [
    "templates/commands/fast.md",
    "templates/commands/quick.md",
    "templates/commands/debug.md",
    "templates/commands/specify.md",
    "templates/commands/plan.md",
    "templates/commands/tasks.md",
    "templates/commands/implement.md",
]


def test_ordinary_sp_workflows_use_shared_project_map_hard_gate() -> None:
    required_phrases = [
        "project-map hard gate",
        "must pass an atlas gate before",
        "PROJECT-HANDBOOK.md",
        "atlas.entry",
        "atlas.index.status",
        "atlas.index.atlas",
        "at least one relevant root topic document",
        "at least one relevant module overview document",
    ]

    for rel_path in TARGETS:
        content = _read(rel_path)
        lowered = content.lower()
        for phrase in required_phrases:
            assert phrase.lower() in lowered, f\"{rel_path} missing: {phrase}\"
```

- [ ] **Step 2: Run the new test to verify it fails**

Run:

```bash
pytest tests/test_project_map_hard_gate_guidance.py -q
```

Expected: FAIL because the command templates still use the old layered minimization contract and do not contain the new hard-gate phrases.

- [ ] **Step 3: Rewrite `context-loading-gradient.md` into a hard-gate partial**

Replace the full contents of `templates/command-partials/common/context-loading-gradient.md` with:

```markdown
## Project-Map Hard Gate

This command must treat the atlas as a mandatory pre-source knowledge base.

### Hard Rule

Do not inspect implementation source, run reproduction or tests, compile a plan, prepare a fix, or emit technical recommendations until the atlas gate has passed.

### Minimum Atlas Read Set

Every ordinary `sp-*` workflow must read:

1. `PROJECT-HANDBOOK.md`
2. `atlas.entry`
3. `atlas.index.status`
4. `atlas.index.atlas`
5. at least one relevant root topic document
6. at least one relevant module overview document

If the touched area crosses shared surfaces, integration seams, workflow joins, or verification-sensitive boundaries, also read:

- `atlas.index.relations`
- any additional root topic documents named by the entry layer

### Command Tier Depth

Tier determines how deeply the workflow must continue through atlas layers after the minimum gate, not whether it may skip atlas consumption.

| Tier | Commands | Additional depth after gate |
|------|----------|-----------------------------|
| trivial | sp-fast | stay at the minimum atlas read set unless the entry layer names shared-surface risk |
| light | sp-quick, sp-debug | read all root topics and module sections named by Layer 1 for the touched area |
| heavy | sp-specify, sp-plan, sp-tasks, sp-implement | read all relevant root topics, module docs, and relation surfaces needed for the current decision |

### Freshness

Treat atlas freshness as a gate:

- `missing` -> block and refresh through `sp-map-scan -> sp-map-build`
- `stale` -> block and refresh through `sp-map-scan -> sp-map-build`
- `possibly_stale` -> inspect `must_refresh_topics` and `review_topics`; if current-task topics intersect `must_refresh_topics`, block and refresh before continuing

The old `warn but proceed` behavior is not allowed.
```

- [ ] **Step 4: Rewrite `navigation-check.md` so it no longer preserves a weaker fallback path**

Replace the full contents of `templates/command-partials/common/navigation-check.md` with:

```markdown
> **Note:** `context-loading-gradient.md` now defines the shared atlas hard gate. This file remains only as a compatibility shim for templates not yet migrated to the same contract.

- Check whether `.specify/project-map/index/status.json` exists.
- If it exists, use the project-map freshness helper for the active script variant to assess freshness before trusting the current handbook/project-map set.
- [AGENT] If freshness is `missing` or `stale`, run `/sp-map-scan` followed by `/sp-map-build` before continuing, then reload the generated navigation artifacts.
- [AGENT] If freshness is `possibly_stale`, inspect the reported changed paths and reasons plus `must_refresh_topics` and `review_topics`. If the current task intersects `must_refresh_topics`, run `/sp-map-scan` followed by `/sp-map-build` before continuing. If only `review_topics` intersect, review those topic files before deciding whether the atlas remains sufficient.
- Check whether `PROJECT-HANDBOOK.md` exists at the repository root.
- Check whether the required handbook/project-map outputs for the current atlas contract exist.
- [AGENT] If the navigation system is missing, run `/sp-map-scan` followed by `/sp-map-build` before continuing, then reload the generated navigation artifacts.
- Treat task-relevant coverage as a coverage-model check, not just a file-presence check.
- [AGENT] If task-relevant coverage is insufficient for the current request, run `/sp-map-scan` followed by `/sp-map-build` before continuing, then reload the generated navigation artifacts.
```

- [ ] **Step 5: Run the new shared hard-gate test again**

Run:

```bash
pytest tests/test_project_map_hard_gate_guidance.py -q
```

Expected: still FAIL, because the command templates have not yet been updated to include or paraphrase the new hard-gate semantics.

- [ ] **Step 6: Update the existing fast/quick/debug tests to expect the hard-gate behavior**

Make the following targeted edits:

- In `tests/test_fast_template_guidance.py`
  - remove assertions that allow redirect-on-missing rather than hard atlas reads
  - add assertions for:
    - `"project-map hard gate"`
    - `"must pass an atlas gate before"`
    - `"atlas.entry"`
    - `"atlas.index.atlas"`
    - `"The old `warn but proceed` behavior is not allowed."` or equivalent lowered phrase

- In `tests/test_quick_template_guidance.py`
  - replace assertions that accept stale warning behavior with hard-gate assertions
  - add assertions for:
    - `"atlas.entry"`
    - `"atlas.index.atlas"`
    - `"at least one relevant root topic document"`
    - `"at least one relevant module overview document"`

- In `tests/test_debug_template_guidance.py`
  - require the debug template to mention the atlas gate before observer framing, repro, logs, and code tracing

Use exact string edits, not placeholder comments.

- [ ] **Step 7: Run the focused template-guidance tests**

Run:

```bash
pytest tests/test_project_map_hard_gate_guidance.py tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_debug_template_guidance.py -q
```

Expected: FAIL, because the command templates still need to be updated.

- [ ] **Step 8: Commit the partial/test groundwork**

```bash
git add templates/command-partials/common/context-loading-gradient.md templates/command-partials/common/navigation-check.md tests/test_project_map_hard_gate_guidance.py tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_debug_template_guidance.py
git commit -m "test: define project-map hard gate contract"
```

---

## Task 2: Apply the hard atlas gate to ordinary `sp-*` command templates

**Files:**
- Modify: `templates/commands/fast.md`
- Modify: `templates/commands/quick.md`
- Modify: `templates/commands/debug.md`
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/commands/implement.md`
- Test: `tests/test_project_map_hard_gate_guidance.py`
- Test: `tests/test_fast_template_guidance.py`
- Test: `tests/test_quick_template_guidance.py`
- Test: `tests/test_debug_template_guidance.py`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Write the failing command-template expectations**

In `tests/test_alignment_templates.py`, add the following test near the other atlas-routing assertions:

```python
def test_core_planning_templates_use_logical_atlas_references() -> None:
    for rel_path in [
        "templates/commands/specify.md",
        "templates/commands/plan.md",
        "templates/commands/tasks.md",
        "templates/commands/implement.md",
    ]:
        content = _read(rel_path)
        lowered = content.lower()
        assert "atlas.entry" in lowered
        assert "atlas.index.status" in lowered
        assert "atlas.index.atlas" in lowered
        assert "at least one relevant root topic document" in lowered
        assert "at least one relevant module overview document" in lowered
```

- [ ] **Step 2: Run the new planning-template test to verify it fails**

Run:

```bash
pytest tests/test_alignment_templates.py -q
```

Expected: FAIL because the templates still name physical `.specify/project-map/...` paths rather than the logical atlas contract.

- [ ] **Step 3: Update `templates/commands/fast.md` to require the atlas gate**

Make these exact content changes:

- In the `Process` section, replace the current `Read the routing layer` subsection with:

```markdown
2. **Pass the atlas gate**
   - {{spec-kit-include: ../command-partials/common/context-loading-gradient.md}}
   - **This command tier: trivial.** Pass the atlas gate by reading:
     1. `PROJECT-HANDBOOK.md`
     2. `atlas.entry`
     3. `atlas.index.status`
     4. `atlas.index.atlas`
     5. at least one relevant root topic document
     6. at least one relevant module overview document
   - Only after the atlas gate passes may you read the source files to change.
```

- Remove or rewrite any line that says:
  - stale only warns
  - trivial commands skip freshness entirely
  - only `QUICK-NAV` plus source is enough

- Keep the fast-lane scope gate and TDD language intact.

- [ ] **Step 4: Update `templates/commands/quick.md` to require the atlas gate**

Make these exact content changes:

- Replace the `Required Context Inputs` numbered list with:

```markdown
**This command tier: light.** Pass the atlas gate by reading:
1. `PROJECT-HANDBOOK.md`
2. `atlas.entry`
3. `atlas.index.status`
4. `atlas.index.atlas`
5. at least one relevant root topic document
6. at least one relevant module overview document
7. `atlas.index.relations` when Layer 1 names shared-surface or cross-module risk

After the atlas gate passes, continue into any additional root-topic or module-local reads named by Layer 1 for the touched area.
```

- Replace:
  - `"Freshness: ... warn but proceed. Do not trigger rescan."`
  with:
  - `"Freshness: treat `missing` and `stale` as blocking; evaluate `possibly_stale` against `must_refresh_topics` and `review_topics` before continuing."`

- [ ] **Step 5: Update `templates/commands/debug.md` to gate repro/log/code work on atlas completion**

Insert immediately before `## Investigation Protocol`:

```markdown
## Project-Map Hard Gate

Before observer framing moves into reproduction, logs, tests, or source-code reads, pass the atlas gate by reading:

1. `PROJECT-HANDBOOK.md`
2. `atlas.entry`
3. `atlas.index.status`
4. `atlas.index.atlas`
5. the relevant root topic documents for workflows, testing, and operations
6. at least one relevant module overview document
7. `atlas.index.relations` when Layer 1 names cross-module or shared-surface risk
```

Keep the existing debug-stage structure; do not remove observer framing or think-subagent sections.

- [ ] **Step 6: Update `templates/commands/specify.md`, `plan.md`, `tasks.md`, and `implement.md` to use logical atlas references**

For each file:

- keep the existing brownfield gate logic
- replace the path-first contextual bullet lists with atlas-contract wording:
  - `atlas.entry`
  - `atlas.index.status`
  - `atlas.index.atlas`
  - `atlas.index.modules`
  - `atlas.index.relations`
  - relevant root topic documents
  - relevant module overview documents

For `implement.md`, add this exact sentence in the pre-execution context section:

```markdown
Do not compile packets, dispatch subagents, or inspect implementation files until the atlas gate has passed.
```

- [ ] **Step 7: Run the focused template suite**

Run:

```bash
pytest tests/test_project_map_hard_gate_guidance.py tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_debug_template_guidance.py tests/test_alignment_templates.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit the command-template hard-gate rollout**

```bash
git add templates/commands/fast.md templates/commands/quick.md templates/commands/debug.md templates/commands/specify.md templates/commands/plan.md templates/commands/tasks.md templates/commands/implement.md tests/test_alignment_templates.py
git commit -m "feat: require atlas hard gate across sp workflows"
```

---

## Task 3: Redesign Layer 1 into a dictionary-style atlas entry surface

**Files:**
- Modify: `templates/project-map/QUICK-NAV.md`
- Modify: `templates/project-map/index/atlas-index.json`
- Modify: `templates/project-handbook-template.md`
- Test: `tests/test_project_handbook_templates.py`
- Test: `tests/test_project_map_layered_contract.py`
- Test: `tests/test_project_map_entry_contract.py`

- [ ] **Step 1: Write the failing entry-contract test**

Create `tests/test_project_map_entry_contract.py` with:

```python
from pathlib import Path
import json


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_quick_nav_behaves_like_dictionary_entry_surface() -> None:
    content = (PROJECT_ROOT / "templates" / "project-map" / "QUICK-NAV.md").read_text(encoding="utf-8").lower()

    assert "symptom routes" in content
    assert "shared-surface hotspots" in content
    assert "verification routes" in content
    assert "propagation-risk routes" in content
    assert "which module most likely owns the touched area" in content


def test_atlas_index_exposes_query_oriented_entry_metadata() -> None:
    payload = json.loads((PROJECT_ROOT / "templates" / "project-map" / "index" / "atlas-index.json").read_text(encoding="utf-8"))

    assert "entrypoints" in payload
    assert "root_topics" in payload
    assert "module_registry_path" in payload
    assert "relations_path" in payload
    assert "status_path" in payload
```

- [ ] **Step 2: Run the new entry-contract test to verify it fails**

Run:

```bash
pytest tests/test_project_map_entry_contract.py -q
```

Expected: FAIL because `QUICK-NAV.md` is still a thin route table and `atlas-index.json` does not yet advertise dictionary-style retrieval semantics.

- [ ] **Step 3: Upgrade `templates/project-map/QUICK-NAV.md`**

Replace its body with a stronger Layer 1 structure that keeps the current task table but adds these sections and exact headings:

```markdown
## By Symptom
## Shared-Surface Hotspots
## Verification Routes
## Propagation-Risk Routes
```

Include at least these symptom rows:

- workflows are no longer reading project-map
- generated template behavior does not match runtime guidance
- freshness or dirty-state routing looks wrong
- subagent dispatch guidance is inconsistent across workflows

Include at least these hotspot rows:

- `templates/command-partials/common/context-loading-gradient.md`
- `templates/commands/**`
- `src/specify_cli/integrations/base.py`
- `src/specify_cli/project_map_status.py`

Include at least these verification rows:

- atlas template guidance tests
- project-map layered contract tests
- freshness helper tests

- [ ] **Step 4: Upgrade `templates/project-map/index/atlas-index.json` to describe entry-oriented retrieval**

Add the following new top-level fields:

```json
"entry_contract": {
  "layer_1_purpose": "dictionary-style atlas entry surface",
  "supports": [
    "task_routes",
    "symptom_routes",
    "shared_surface_hotspots",
    "verification_routes",
    "propagation_risk_routes"
  ]
},
"recommended_minimum_read_set": [
  "PROJECT-HANDBOOK.md",
  ".specify/project-map/QUICK-NAV.md",
  ".specify/project-map/index/status.json",
  ".specify/project-map/index/atlas-index.json"
]
```

- [ ] **Step 5: Update `templates/project-handbook-template.md` to describe Layer 1 as a dictionary/compass**

Add these phrases verbatim in the `Quick Navigation (Layer 1)` or `How To Read This Project` area:

- `"dictionary-style atlas entry surface"`
- `"task routes, symptom routes, shared-surface hotspots, verification routes, and propagation-risk routes"`
- `"which module most likely owns the touched area"`

- [ ] **Step 6: Update the existing handbook/layered tests**

Make the following changes:

- `tests/test_project_handbook_templates.py`
  - add assertions for the new Layer 1 phrases above
- `tests/test_project_map_layered_contract.py`
  - add an assertion that `templates/project-map/QUICK-NAV.md` includes symptom and verification retrieval language

- [ ] **Step 7: Run the Layer 1 focused test suite**

Run:

```bash
pytest tests/test_project_map_entry_contract.py tests/test_project_handbook_templates.py tests/test_project_map_layered_contract.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit the Layer 1 redesign**

```bash
git add templates/project-map/QUICK-NAV.md templates/project-map/index/atlas-index.json templates/project-handbook-template.md tests/test_project_map_entry_contract.py tests/test_project_handbook_templates.py tests/test_project_map_layered_contract.py
git commit -m "feat: redesign Layer 1 atlas entry surface"
```

---

## Task 4: Align freshness helpers with hard-gate semantics and atlas topic routing

**Files:**
- Modify: `src/specify_cli/project_map_status.py`
- Test: `tests/test_project_map_status.py`

- [ ] **Step 1: Write failing freshness-helper expectations**

In `tests/test_project_map_status.py`, add:

```python
def test_hard_gate_commands_treat_stale_and_missing_as_blocking():
    mod = _load_module()

    assert mod.classify_changed_path("PROJECT-HANDBOOK.md") == "stale"
    result = mod.refresh_plan_for_changed_path("src/routes/api.ts")
    assert "INTEGRATIONS.md" in result["must_refresh_topics"]
    assert "WORKFLOWS.md" in result["must_refresh_topics"]
```

Also update any existing assertions that encode warn-only guidance so they instead assert topic-driven blocking or review routing.

- [ ] **Step 2: Run the freshness-helper test to verify current behavior gaps**

Run:

```bash
pytest tests/test_project_map_status.py -q
```

Expected: FAIL only if the new test or rewritten expectations are stricter than the current helper output.

- [ ] **Step 3: Extend `project_map_status.py` with explicit atlas-contract helpers**

Add these exact helper functions below the existing `canonical_project_map_paths` block:

```python
def atlas_minimum_read_set(project_root: Path) -> list[Path]:
    project_map_index_root = project_map_index_dir(project_root)
    return [
        project_root / "PROJECT-HANDBOOK.md",
        project_map_dir(project_root) / "QUICK-NAV.md",
        project_map_index_root / "status.json",
        project_map_index_root / "atlas-index.json",
    ]


def atlas_root_topic_path(project_root: Path, topic_filename: str) -> Path:
    return project_map_root_dir(project_root) / topic_filename
```

Do not remove existing helpers used by other tests.

- [ ] **Step 4: Tighten helper docstrings and comments to match the new hard-gate contract**

Update the module docstring to include this sentence:

```python
This module now supports atlas hard-gate routing and minimum read-set checks in addition to freshness status.
```

- [ ] **Step 5: Run the freshness-helper suite**

Run:

```bash
pytest tests/test_project_map_status.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit the freshness-helper alignment**

```bash
git add src/specify_cli/project_map_status.py tests/test_project_map_status.py
git commit -m "feat: align project-map status helpers with atlas hard gate"
```

---

## Task 5: Replace physical-path-only guidance with logical atlas-contract guidance

**Files:**
- Modify: `src/specify_cli/integrations/base.py`
- Test: `tests/test_extension_skills.py`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Write the failing integration-guidance expectation**

In `tests/test_extension_skills.py`, add:

```python
def test_integration_guidance_uses_logical_atlas_contract_language():
    content = (PROJECT_ROOT / "src" / "specify_cli" / "integrations" / "base.py").read_text(encoding="utf-8").lower()
    assert "atlas.entry" in content
    assert "atlas.index.status" in content
    assert "logical atlas contract" in content
```

- [ ] **Step 2: Run the extension-guidance test to verify it fails**

Run:

```bash
pytest tests/test_extension_skills.py -q
```

Expected: FAIL because `base.py` still appends guidance that hardcodes `.specify/project-map/*.md`.

- [ ] **Step 3: Update the runtime guidance appenders in `src/specify_cli/integrations/base.py`**

In each of these methods:

- `_append_runtime_project_map_gate`
- `_append_implement_leader_gate`
- `_append_debug_leader_gate`
- `_append_quick_leader_gate`

replace the phrase:

```python
"You MUST read `PROJECT-HANDBOOK.md` and relevant `.specify/project-map/*.md` files ..."
```

with:

```python
"You MUST pass the logical atlas contract first by reading `PROJECT-HANDBOOK.md`, `atlas.entry`, `atlas.index.status`, `atlas.index.atlas`, the relevant root topic documents, and the relevant module overview documents ..."
```

Add this exact sentence to `_append_runtime_project_map_gate`:

```python
"- Treat this as a logical atlas contract, not as a hardcoded physical path contract; generated projects and this repository may resolve the atlas through different files.\n"
```

- [ ] **Step 4: Run the focused guidance tests**

Run:

```bash
pytest tests/test_extension_skills.py tests/test_alignment_templates.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the logical-atlas guidance rollout**

```bash
git add src/specify_cli/integrations/base.py tests/test_extension_skills.py
git commit -m "refactor: use logical atlas contract in integration guidance"
```

---

## Task 6: Record atlas-read evidence in resumable workflow state surfaces

**Files:**
- Modify: `templates/workflow-state-template.md`
- Modify: `templates/debug.md`
- Test: `tests/test_alignment_templates.py`
- Test: `tests/test_debug_template_guidance.py`

- [ ] **Step 1: Write failing state-template expectations**

In `tests/test_alignment_templates.py`, add:

```python
def test_workflow_state_template_includes_atlas_read_evidence_fields() -> None:
    content = _read("templates/workflow-state-template.md").lower()
    assert "atlas_read_completed" in content
    assert "atlas_paths_read" in content
    assert "atlas_root_topics_read" in content
    assert "atlas_module_docs_read" in content
    assert "atlas_status_basis" in content
```

In `tests/test_debug_template_guidance.py`, add:

```python
def test_debug_session_template_includes_atlas_read_evidence_fields() -> None:
    content = (PROJECT_ROOT / "templates" / "debug.md").read_text(encoding="utf-8").lower()
    assert "atlas_read_completed:" in content
    assert "atlas_paths_read:" in content
    assert "atlas_root_topics_read:" in content
    assert "atlas_module_docs_read:" in content
```

- [ ] **Step 2: Run the new state-template tests to verify they fail**

Run:

```bash
pytest tests/test_alignment_templates.py tests/test_debug_template_guidance.py -q
```

Expected: FAIL because the templates do not yet carry atlas-read evidence fields.

- [ ] **Step 3: Add atlas-read evidence fields to `templates/workflow-state-template.md`**

Insert this block after `## Authoritative Files`:

```markdown
## Atlas Read Evidence

- atlas_read_completed: `true | false`
- atlas_paths_read:
  - [atlas artifact actually read before source-level work]
- atlas_root_topics_read:
  - [root topic file actually read]
- atlas_module_docs_read:
  - [module overview or module-local doc actually read]
- atlas_status_basis: [fresh | missing | stale | possibly_stale plus the decision taken]
- atlas_blocked_reason: [why atlas gating blocked work, if it did]
```

- [ ] **Step 4: Add atlas-read evidence fields to `templates/debug.md`**

Inside the frontmatter template block, add:

```markdown
atlas_read_completed: [true only after the atlas gate is complete]
```

After the `## Symptoms` section, add:

```markdown
## Atlas Read Evidence

atlas_paths_read:
  - [atlas artifact actually read before source-level work]
atlas_root_topics_read:
  - [root topic file actually read]
atlas_module_docs_read:
  - [module overview or module-local doc actually read]
atlas_status_basis: [fresh | missing | stale | possibly_stale plus the decision taken]
atlas_blocked_reason: [why atlas gating blocked work, if it did]
```

- [ ] **Step 5: Run the state-template suite**

Run:

```bash
pytest tests/test_alignment_templates.py tests/test_debug_template_guidance.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit the state-evidence changes**

```bash
git add templates/workflow-state-template.md templates/debug.md
git commit -m "feat: record atlas read evidence in workflow state templates"
```

---

## Task 7: Run end-to-end focused regression checks and fix any guidance drift

**Files:**
- Modify as needed: any files from Tasks 1-6
- Test: all focused suites named below

- [ ] **Step 1: Run the focused atlas-consumption regression suite**

Run:

```bash
pytest \
  tests/test_project_map_hard_gate_guidance.py \
  tests/test_project_map_entry_contract.py \
  tests/test_fast_template_guidance.py \
  tests/test_quick_template_guidance.py \
  tests/test_debug_template_guidance.py \
  tests/test_alignment_templates.py \
  tests/test_extension_skills.py \
  tests/test_project_handbook_templates.py \
  tests/test_project_map_layered_contract.py \
  tests/test_project_map_status.py \
  tests/test_map_scan_build_template_guidance.py \
  -q
```

Expected: PASS.

- [ ] **Step 2: If any focused suite fails, make the minimal repair**

Use this rule:

- if the failure is in a command template, repair the template wording
- if the failure is in a shared partial, repair the partial once and rerun the affected tests
- if the failure is in a state/helper/template contract, repair the exact contract file rather than loosening the test

Do not weaken the new hard-gate or Layer 1 dictionary expectations just to make tests pass.

- [ ] **Step 3: Re-run the focused atlas-consumption regression suite**

Run the exact same command from Step 1.

Expected: PASS with no failures.

- [ ] **Step 4: Run one broader template/integration regression command**

Run:

```bash
pytest tests/integrations -q
```

Expected: PASS, or a small number of directly explainable guidance regressions that can be fixed immediately.

- [ ] **Step 5: Commit the verified implementation batch**

```bash
git add templates src/specify_cli tests
git commit -m "feat: restore project-map as hard gate across sp workflows"
```

---

## Spec Coverage Check

- Hard atlas gate for all ordinary `sp-*` workflows: covered by Tasks 1-2.
- `sp-fast` and `sp-quick` must read atlas, not just Layer 1 or source: covered by Task 2.
- Replace `warn but proceed` with blocking freshness rules: covered by Tasks 1-2 and validated in Task 4.
- Upgrade Layer 1 into dictionary-style entry surface: covered by Task 3.
- Make atlas indexes more query-oriented: covered by Task 3.
- Support logical atlas references across this repository and generated projects: covered by Task 5.
- Add atlas-read evidence to state surfaces: covered by Task 6.
- Preserve and strengthen `map-scan/map-build` as atlas production path rather than replacing it: validated through Task 3 expectations and Task 7 regressions.

No spec requirement is intentionally left without a task.

## Placeholder Scan

- No `TBD`, `TODO`, or "implement later" placeholders were left in this plan.
- Every task names exact files, test files, commands, and expected outcomes.
- No task relies on "similar to Task N" shorthand.

## Type and Naming Consistency

- Atlas logical references are consistently named:
  - `atlas.entry`
  - `atlas.index.status`
  - `atlas.index.atlas`
  - `atlas.index.modules`
  - `atlas.index.relations`
- Atlas-read evidence field names are consistent across workflow-state and debug state:
  - `atlas_read_completed`
  - `atlas_paths_read`
  - `atlas_root_topics_read`
  - `atlas_module_docs_read`
  - `atlas_status_basis`
  - `atlas_blocked_reason`
- Freshness semantics consistently use:
  - `missing`
  - `stale`
  - `possibly_stale`
  - `must_refresh_topics`
  - `review_topics`

Plan complete and saved to `docs/superpowers/plans/2026-05-01-project-map-hard-gate-implementation.md`. Two execution options:

1. Subagent-Driven (recommended) - I dispatch a fresh subagent per task, review between tasks, fast iteration

2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
