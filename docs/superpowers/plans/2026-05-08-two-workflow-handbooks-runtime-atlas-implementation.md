# Two-Workflow Handbooks Runtime Atlas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the layered project-map runtime atlas with `DEBUG-HANDBOOK.md` and `BUILD-HANDBOOK.md`, then rewire workflow prompts, packet context, integrations, and tests so those two handbooks become the only primary runtime atlas consumption surface.

**Architecture:** Start by locking the new runtime contract in tests, because the current repository strongly encodes the old atlas model in command templates, shared partials, integration rendering, CLI/help text, and packet compilation. Then implement the new `sp-map-build` output contract, swap every ordinary workflow from atlas-gate to handbook-gate semantics, update packet/integration injection to use handbook chapter bundles, and remove old layered-atlas runtime expectations from docs and tests.

**Tech Stack:** Python 3.13, Typer CLI helpers, Markdown command templates, integration renderers, Codex/Claude/Copilot/Gemini generated surfaces, pytest contract/integration/template tests.

---

## File Structure

```text
MODIFY
  templates/commands/map-build.md
    Purpose: redefine canonical runtime outputs from the old layered atlas to `DEBUG-HANDBOOK.md` and `BUILD-HANDBOOK.md`, plus new reverse-coverage success rules.
  templates/command-partials/map-build/shell.md
    Purpose: restate the two-handbook runtime output model in the short build entrypoint.
  templates/command-partials/common/context-loading-gradient.md
    Purpose: replace the shared atlas gate with the shared handbook gate contract.
  templates/commands/debug.md
    Purpose: require `DEBUG-HANDBOOK.md` and fixed chapter IDs before investigation work.
  templates/commands/specify.md
  templates/commands/plan.md
  templates/commands/tasks.md
  templates/commands/implement.md
  templates/commands/quick.md
  templates/commands/fast.md
  templates/commands/test-scan.md
  templates/commands/test-build.md
  templates/commands/analyze.md
    Purpose: require `BUILD-HANDBOOK.md` or `DEBUG-HANDBOOK.md` with fixed chapter sets instead of layered atlas traversal.
  templates/passive-skills/spec-kit-project-map-gate/SKILL.md
    Purpose: align passive workflow routing guidance with the new handbook-only runtime gate.
  templates/project-handbook-template.md
  templates/project-map/QUICK-NAV.md
  templates/project-map/index/atlas-index.json
  templates/project-map/index/capabilities.json
  templates/project-map/index/symptoms.json
  templates/project-map/root/ARCHITECTURE.md
  templates/project-map/root/STRUCTURE.md
  templates/project-map/root/CONVENTIONS.md
  templates/project-map/root/INTEGRATIONS.md
  templates/project-map/root/WORKFLOWS.md
  templates/project-map/root/TESTING.md
  templates/project-map/root/OPERATIONS.md
  templates/project-map/modules/OVERVIEW.md
  templates/project-map/modules/ARCHITECTURE.md
  templates/project-map/modules/STRUCTURE.md
  templates/project-map/modules/WORKFLOWS.md
  templates/project-map/modules/TESTING.md
  templates/project-map/modules/deep/workflows/TEMPLATE.md
    Purpose: remove old runtime contract assumptions from generated atlas templates and redirect them toward support-only or removal status.
  src/specify_cli/execution/packet_compiler.py
    Purpose: inject handbook-based context bundles and read scopes instead of `PROJECT-HANDBOOK.md` plus `.specify/project-map/root/*.md`.
  src/specify_cli/integrations/base.py
    Purpose: rewrite generated "Crucial First Step" and runtime hard-gate strings for all integrations around handbook-only consumption.
  src/specify_cli/codex_team/result_template.py
  src/specify_cli/debug/cli.py
  src/specify_cli/__init__.py
    Purpose: update CLI/runtime guidance, result templates, and user-facing refresh text to the two-handbook model.
  src/specify_cli/hooks/artifact_validation.py
    Purpose: validate that `sp-map-build` produced the two handbook files and required chapter anchors instead of the old layered runtime outputs.
  src/specify_cli/project_map_status.py
    Purpose: change canonical runtime output expectations and missing-artifact checks to the new handbook set.
  README.md
  PROJECT-HANDBOOK.md
    Purpose: document the new runtime atlas model and remove advice that teaches layered runtime traversal.

TESTS TO MODIFY
  tests/test_map_scan_build_template_guidance.py
  tests/test_alignment_templates.py
  tests/test_project_handbook_templates.py
  tests/test_project_map_layered_contract.py
  tests/test_project_map_entry_contract.py
  tests/test_project_map_capability_truth_layer.py
  tests/execution/test_packet_compiler.py
  tests/execution/test_packet_schema.py
  tests/execution/test_packet_validator.py
  tests/execution/test_result_validator.py
  tests/hooks/test_preflight_hooks.py
  tests/hooks/test_delegation_hooks.py
  tests/hooks/test_learning_hooks.py
  tests/contract/test_hook_cli_surface.py
  tests/integrations/test_integration_base_markdown.py
  tests/integrations/test_integration_base_toml.py
  tests/integrations/test_integration_base_skills.py
  tests/integrations/test_integration_codex.py
  tests/integrations/test_integration_claude.py
  tests/integrations/test_cli.py
  tests/test_extension_skills.py
  tests/test_agent_context_managed_block.py
  tests/test_constitution_defaults.py
  tests/test_constitution_profiles_cli.py
  tests/test_debug_template_guidance.py
    Purpose: delete old layered-atlas runtime assumptions and enforce the handbook-only contract.

NEW TESTS
  tests/test_runtime_handbook_contract.py
    Purpose: lock the new `sp-map-build` runtime outputs and required chapter IDs in one focused contract test file.
```

---

## Task 1: Lock the new two-handbook runtime contract with failing tests

**Files:**
- Create: `tests/test_runtime_handbook_contract.py`
- Modify: `tests/test_map_scan_build_template_guidance.py`
- Modify: `tests/test_alignment_templates.py`

- [ ] **Step 1: Create a focused failing contract test for the new runtime outputs**

Create `tests/test_runtime_handbook_contract.py` with this content:

```python
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def test_map_build_runtime_outputs_are_two_workflow_handbooks():
    content = _read("templates/commands/map-build.md")

    assert "DEBUG-HANDBOOK.md" in content
    assert "BUILD-HANDBOOK.md" in content
    assert "PROJECT-HANDBOOK.md" not in content
    assert ".specify/project-map/QUICK-NAV.md" not in content
    assert ".specify/project-map/index/*.json" not in content
    assert ".specify/project-map/root/*.md" not in content
    assert ".specify/project-map/modules/<module-id>/*.md" not in content


def test_context_loading_gradient_uses_handbook_gate_instead_of_layered_atlas_gate():
    content = _read("templates/command-partials/common/context-loading-gradient.md")

    assert "DEBUG-HANDBOOK.md" in content
    assert "BUILD-HANDBOOK.md" in content
    assert "required chapter ids" in content.lower()
    assert "PROJECT-HANDBOOK.md" not in content
    assert "atlas.entry" not in content
    assert "root topic document" not in content.lower()
    assert "module overview document" not in content.lower()


def test_debug_template_requires_debug_handbook_only():
    content = _read("templates/commands/debug.md")

    assert "DEBUG-HANDBOOK.md" in content
    assert "DEBUG-WORKFLOW-CONTRACT" in content
    assert "SYMPTOM-TO-SURFACE-ROUTING" in content
    assert "SYSTEM-TOPOLOGY-FOR-DEBUG" in content
    assert "INVESTIGATION-PLAYBOOKS" in content
    assert "VERIFICATION-AND-EXIT" in content
    assert "PROJECT-HANDBOOK.md" not in content
    assert ".specify/project-map/root/WORKFLOWS.md" not in content


def test_specify_plan_tasks_templates_require_build_handbook_only():
    expected_chapters = (
        "BUILD-WORKFLOW-CONTRACT",
        "PRODUCT-AND-CAPABILITY-MAP",
        "WORKFLOW-SEQUENCES",
        "MODULE-COLLABORATION",
        "CHANGE-PROPAGATION-RISKS",
    )

    for relative_path in (
        "templates/commands/specify.md",
        "templates/commands/plan.md",
        "templates/commands/tasks.md",
    ):
        content = _read(relative_path)
        assert "BUILD-HANDBOOK.md" in content
        for chapter in expected_chapters:
            assert chapter in content
        assert "PROJECT-HANDBOOK.md" not in content
        assert ".specify/project-map/root/ARCHITECTURE.md" not in content
```

- [ ] **Step 2: Add explicit failing assertions to the existing template guidance tests**

In `tests/test_map_scan_build_template_guidance.py`, add these assertions to the `map-build` expectations:

```python
    assert "DEBUG-HANDBOOK.md" in content
    assert "BUILD-HANDBOOK.md" in content
    assert "PROJECT-HANDBOOK.md" not in content
    assert ".specify/project-map/root/*.md" not in content
    assert ".specify/project-map/modules/<module-id>/*.md" not in content
```

Add these assertions to the shared context-loading guidance expectations:

```python
    assert "DEBUG-HANDBOOK.md" in content
    assert "BUILD-HANDBOOK.md" in content
    assert "required chapter ids" in content.lower()
    assert "PROJECT-HANDBOOK.md" not in content
    assert "atlas.entry" not in content
```

- [ ] **Step 3: Add failing assertions for handbook-only guidance in the alignment test family**

In `tests/test_alignment_templates.py`, add a new focused test:

```python
def test_runtime_alignment_prefers_two_workflow_handbooks_over_layered_atlas():
    debug_template = _read("templates/commands/debug.md")
    build_template = _read("templates/commands/implement.md")
    shared_gate = _read("templates/command-partials/common/context-loading-gradient.md")

    assert "DEBUG-HANDBOOK.md" in debug_template
    assert "BUILD-HANDBOOK.md" in build_template
    assert "PROJECT-HANDBOOK.md" not in shared_gate
    assert "atlas.entry" not in shared_gate
```

- [ ] **Step 4: Run the red test slice**

Run:

```powershell
pytest tests/test_runtime_handbook_contract.py tests/test_map_scan_build_template_guidance.py tests/test_alignment_templates.py -q
```

Expected: FAIL because the repository still encodes the old layered-atlas runtime contract everywhere.

- [ ] **Step 5: Commit the failing runtime-contract tests**

Run:

```powershell
git add tests/test_runtime_handbook_contract.py tests/test_map_scan_build_template_guidance.py tests/test_alignment_templates.py
git commit -m "test: define two-handbook runtime atlas contract"
```

---

## Task 2: Redefine `sp-map-build` runtime outputs around two workflow handbooks

**Files:**
- Modify: `templates/commands/map-build.md`
- Modify: `templates/command-partials/map-build/shell.md`
- Modify: `src/specify_cli/hooks/artifact_validation.py`
- Modify: `src/specify_cli/project_map_status.py`
- Modify: `tests/contract/test_hook_cli_surface.py`

- [ ] **Step 1: Replace the `map-build` output contract**

In `templates/commands/map-build.md`, change the frontmatter and output-contract sections so the only canonical runtime outputs are:

```yaml
description: Use when `sp-map-scan` has produced a complete scan package and you need to build or refresh `DEBUG-HANDBOOK.md` and `BUILD-HANDBOOK.md`.
workflow_contract:
  when_to_use: A completed scan package exists and the canonical two-handbook runtime atlas must be built or refreshed from it.
  primary_objective: Validate the scan package, dispatch read-only explorer packets, write the two workflow handbooks, and prove workflow-operational reverse coverage.
  primary_outputs: '`DEBUG-HANDBOOK.md`, `BUILD-HANDBOOK.md`, `.specify/project-map/map-state.md`, and `.specify/project-map/worker-results/*.json`.'
```

Then replace the old canonical output list with:

```markdown
The only canonical runtime outputs for this command are:

- `DEBUG-HANDBOOK.md`
- `BUILD-HANDBOOK.md`
- `.specify/project-map/map-state.md`
- `.specify/project-map/worker-results/<packet-id>.json`
```

- [ ] **Step 2: Replace the map-build shell partial bullets**

In `templates/command-partials/map-build/shell.md`, replace the context bullets with:

```markdown
- Primary inputs: `.specify/project-map/map-scan.md`, `.specify/project-map/coverage-ledger.json`, `.specify/project-map/coverage-ledger.md`, `.specify/project-map/scan-packets/*.md`, `.specify/project-map/map-state.md`, existing handbooks when present, and live repository evidence.
- This command owns the two workflow handbook runtime outputs.
- If the scan package is incomplete or the accepted evidence cannot support workflow-operational handbook content, produce a scan gap report and route back to `sp-map-scan`.
- Record accepted and rejected packet evidence in `.specify/project-map/map-state.md` and `.specify/project-map/worker-results/*.json`.
```

- [ ] **Step 3: Replace artifact validation’s required runtime outputs**

In `src/specify_cli/hooks/artifact_validation.py`, update `FILE_REQUIRED_ARTIFACTS["map-build"]` and `REQUIRED_ARTIFACTS["map-build"]` to:

```python
    "map-build": (
        "map-state.md",
        "map-scan.md",
        "coverage-ledger.json",
        "DEBUG-HANDBOOK.md",
        "BUILD-HANDBOOK.md",
    ),
```

and:

```python
    "map-build": (
        "map-state.md",
        "map-scan.md",
        "coverage-ledger.json",
        "scan-packets",
        "worker-results",
        "DEBUG-HANDBOOK.md",
        "BUILD-HANDBOOK.md",
    ),
```

- [ ] **Step 4: Add handbook chapter validation**

Still in `src/specify_cli/hooks/artifact_validation.py`, add:

```python
DEBUG_HANDBOOK_REQUIRED_SECTIONS = (
    "## DEBUG-WORKFLOW-CONTRACT",
    "## SYMPTOM-TO-SURFACE-ROUTING",
    "## SYSTEM-TOPOLOGY-FOR-DEBUG",
    "## HOT-PATHS-AND-OWNERS",
    "## FAILURE-PATTERNS",
    "## INVESTIGATION-PLAYBOOKS",
    "## FIX-PROPAGATION-CHECKS",
    "## VERIFICATION-AND-EXIT",
    "## KNOWN-UNKNOWNS",
)

BUILD_HANDBOOK_REQUIRED_SECTIONS = (
    "## BUILD-WORKFLOW-CONTRACT",
    "## PRODUCT-AND-CAPABILITY-MAP",
    "## WORKFLOW-SEQUENCES",
    "## CHANGE-ENTRYPOINTS",
    "## MODULE-COLLABORATION",
    "## CHANGE-PROPAGATION-RISKS",
    "## IMPLEMENTATION-PLAYBOOKS",
    "## VERIFICATION-ROUTES",
    "## KNOWN-UNKNOWNS",
)
```

Add a helper:

```python
def _validate_runtime_handbooks(feature_dir: Path) -> list[str]:
    errors: list[str] = []
    errors.extend(
        _validate_markdown_contains(
            feature_dir / "DEBUG-HANDBOOK.md",
            DEBUG_HANDBOOK_REQUIRED_SECTIONS,
            "DEBUG-HANDBOOK.md",
        )
    )
    errors.extend(
        _validate_markdown_contains(
            feature_dir / "BUILD-HANDBOOK.md",
            BUILD_HANDBOOK_REQUIRED_SECTIONS,
            "BUILD-HANDBOOK.md",
        )
    )
    return errors
```

and wire it into `_validate_map_build_artifacts()`:

```python
    errors.extend(_validate_runtime_handbooks(feature_dir))
```

- [ ] **Step 5: Update canonical project-map status expectations**

In `src/specify_cli/project_map_status.py`, replace the current runtime output lists that still mention `PROJECT-HANDBOOK.md` and `QUICK-NAV.md` with a helper that returns:

```python
def canonical_runtime_handbook_paths(project_root: Path) -> list[Path]:
    return [
        project_root / "DEBUG-HANDBOOK.md",
        project_root / "BUILD-HANDBOOK.md",
    ]
```

Then use those paths in:

- `missing_canonical_project_map_paths()`
- any other status helper that currently assumes `PROJECT-HANDBOOK.md` or `QUICK-NAV.md` are runtime outputs

- [ ] **Step 6: Replace map-build validation fixture expectations**

In `tests/contract/test_hook_cli_surface.py`, replace map-build fixture setup that creates:

- `index/atlas-index.json`
- `index/modules.json`
- `index/relations.json`
- `index/capabilities.json`
- `index/symptoms.json`

with fixtures that create:

```python
"DEBUG-HANDBOOK.md": (
    "## DEBUG-WORKFLOW-CONTRACT\n"
    "## SYMPTOM-TO-SURFACE-ROUTING\n"
    "## SYSTEM-TOPOLOGY-FOR-DEBUG\n"
    "## HOT-PATHS-AND-OWNERS\n"
    "## FAILURE-PATTERNS\n"
    "## INVESTIGATION-PLAYBOOKS\n"
    "## FIX-PROPAGATION-CHECKS\n"
    "## VERIFICATION-AND-EXIT\n"
    "## KNOWN-UNKNOWNS\n"
),
"BUILD-HANDBOOK.md": (
    "## BUILD-WORKFLOW-CONTRACT\n"
    "## PRODUCT-AND-CAPABILITY-MAP\n"
    "## WORKFLOW-SEQUENCES\n"
    "## CHANGE-ENTRYPOINTS\n"
    "## MODULE-COLLABORATION\n"
    "## CHANGE-PROPAGATION-RISKS\n"
    "## IMPLEMENTATION-PLAYBOOKS\n"
    "## VERIFICATION-ROUTES\n"
    "## KNOWN-UNKNOWNS\n"
),
```

- [ ] **Step 7: Run the focused green slice**

Run:

```powershell
pytest tests/test_runtime_handbook_contract.py tests/contract/test_hook_cli_surface.py tests/test_map_scan_build_template_guidance.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit the map-build output-contract change**

Run:

```powershell
git add templates/commands/map-build.md templates/command-partials/map-build/shell.md src/specify_cli/hooks/artifact_validation.py src/specify_cli/project_map_status.py tests/contract/test_hook_cli_surface.py tests/test_runtime_handbook_contract.py tests/test_map_scan_build_template_guidance.py
git commit -m "feat: redefine map-build runtime outputs as workflow handbooks"
```

---

## Task 3: Replace the shared layered atlas gate with a shared handbook gate

**Files:**
- Modify: `templates/command-partials/common/context-loading-gradient.md`
- Modify: `templates/passive-skills/spec-kit-project-map-gate/SKILL.md`
- Modify: `tests/test_alignment_templates.py`

- [ ] **Step 1: Rewrite the shared gate partial**

Replace the full contents of `templates/command-partials/common/context-loading-gradient.md` with:

```markdown
## Runtime Handbook Gate

This command must treat the workflow handbooks as the mandatory pre-source knowledge base.

### Hard Rule

Do not inspect implementation source, run reproduction or tests, compile a
plan, prepare a fix, or emit technical recommendations until the handbook gate has
passed.

### Required Runtime Handbook

- Use `DEBUG-HANDBOOK.md` for `sp-debug`.
- Use `BUILD-HANDBOOK.md` for ordinary non-debug `sp-*` workflows.

### Fixed Chapter Consumption

Every workflow must read the chapter IDs explicitly required by its command contract.
Do not replace chapter consumption with broad freeform scanning of the handbook.

### Command Tier Depth

Tier determines how deeply the workflow must continue through handbook chapters
after the minimum gate, not whether it may skip handbook consumption.

- `trivial`: minimum required chapter set only
- `light`: minimum chapter set plus relevant routing or playbook chapters
- `heavy`: minimum chapter set plus all relevant collaboration, propagation, and verification chapters

### Freshness

Treat handbook freshness as a gate:

- `missing` -> block and refresh through `sp-map-scan -> sp-map-build`
- `stale` -> block and refresh through `sp-map-scan -> sp-map-build`
- `possibly_stale` -> inspect `must_refresh_topics` and `review_topics`; if
  current-task topics intersect `must_refresh_topics`, block and refresh before continuing

### Primary Read Restriction

Do not treat `PROJECT-HANDBOOK.md`, `.specify/project-map/index/*.json`,
`.specify/project-map/root/*.md`, or `.specify/project-map/modules/**` as primary
runtime read surfaces. If handbook coverage is insufficient, refresh the handbooks
or move to live repository evidence; do not re-enter a layered atlas traversal phase.
```

- [ ] **Step 2: Rewrite the passive project-map gate skill**

In `templates/passive-skills/spec-kit-project-map-gate/SKILL.md`, replace the old description and bullets that tell agents to read `PROJECT-HANDBOOK.md`, `QUICK-NAV.md`, root docs, and module docs with wording that says:

```markdown
description: "Use when changing, reviewing, planning against, or debugging an existing Spec Kit Plus codebase. Require `DEBUG-HANDBOOK.md` or `BUILD-HANDBOOK.md` first, or route to `sp-map-scan -> sp-map-build` when that runtime handbook coverage is missing or stale."
```

and add bullets that explicitly say:

- read `DEBUG-HANDBOOK.md` for `sp-debug`
- read `BUILD-HANDBOOK.md` for other ordinary brownfield workflows
- do not use `PROJECT-HANDBOOK.md` or layered project-map files as the primary runtime read path

- [ ] **Step 3: Tighten the shared gate test expectations**

In `tests/test_alignment_templates.py`, add:

```python
def test_shared_context_gate_is_handbook_only():
    content = _read("templates/command-partials/common/context-loading-gradient.md")
    lowered = content.lower()

    assert "debug-handbook.md" in lowered
    assert "build-handbook.md" in lowered
    assert "required runtime handbook" in lowered
    assert "project-handbook.md" not in lowered
    assert "atlas.entry" not in lowered
    assert "module overview document" not in lowered
```

- [ ] **Step 4: Run the gate-alignment tests**

Run:

```powershell
pytest tests/test_alignment_templates.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the handbook gate rewrite**

Run:

```powershell
git add templates/command-partials/common/context-loading-gradient.md templates/passive-skills/spec-kit-project-map-gate/SKILL.md tests/test_alignment_templates.py
git commit -m "feat: replace atlas gate with runtime handbook gate"
```

---

## Task 4: Convert ordinary workflow prompts to fixed handbook chapter consumption

**Files:**
- Modify: `templates/commands/debug.md`
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/commands/implement.md`
- Modify: `templates/commands/quick.md`
- Modify: `templates/commands/fast.md`
- Modify: `templates/commands/test-scan.md`
- Modify: `templates/commands/test-build.md`
- Modify: `templates/commands/analyze.md`
- Modify: `tests/test_debug_template_guidance.py`
- Modify: `tests/test_alignment_templates.py`

- [ ] **Step 1: Rewrite `sp-debug` handbook requirements**

In `templates/commands/debug.md`, replace the atlas-gate block and all direct reads of:

- `PROJECT-HANDBOOK.md`
- `.specify/project-map/index/symptoms.json`
- `.specify/project-map/index/capabilities.json`
- `.specify/project-map/root/*.md`
- `.specify/project-map/modules/<module-id>/**`

with this contract language:

```markdown
## Debug Handbook Gate

Before observer framing moves into reproduction, logs, tests, or source-code reads,
pass the handbook gate by reading:

1. `DEBUG-HANDBOOK.md`
2. `DEBUG-WORKFLOW-CONTRACT`
3. `SYMPTOM-TO-SURFACE-ROUTING`
4. `SYSTEM-TOPOLOGY-FOR-DEBUG`
5. `INVESTIGATION-PLAYBOOKS`
6. `VERIFICATION-AND-EXIT`
```

Then add:

```markdown
- [AGENT] If `DEBUG-HANDBOOK.md` is missing, stale, or insufficient for the failing area, stop and tell the user to run `{{invoke:map-scan}}`, then `{{invoke:map-build}}`; wait for that refresh before root-cause analysis continues.
- Treat `DEBUG-HANDBOOK.md` as the only primary runtime atlas read surface for `sp-debug`.
- Do not route through `PROJECT-HANDBOOK.md` or `.specify/project-map/**/*.md` before beginning repository evidence work.
```

- [ ] **Step 2: Rewrite build-side workflow handbook requirements**

In each of:

- `templates/commands/specify.md`
- `templates/commands/plan.md`
- `templates/commands/tasks.md`
- `templates/commands/implement.md`
- `templates/commands/quick.md`
- `templates/commands/fast.md`
- `templates/commands/test-scan.md`
- `templates/commands/test-build.md`
- `templates/commands/analyze.md`

replace the old atlas gate and layered read instructions with handbook-only requirements.

For `specify`, `plan`, and `tasks`, add:

```markdown
Pass the handbook gate by reading:

1. `BUILD-HANDBOOK.md`
2. `BUILD-WORKFLOW-CONTRACT`
3. `PRODUCT-AND-CAPABILITY-MAP`
4. `WORKFLOW-SEQUENCES`
5. `MODULE-COLLABORATION`
6. `CHANGE-PROPAGATION-RISKS`
```

For `implement`, `quick`, and `fast`, add:

```markdown
Pass the handbook gate by reading:

1. `BUILD-HANDBOOK.md`
2. `BUILD-WORKFLOW-CONTRACT`
3. `PRODUCT-AND-CAPABILITY-MAP`
4. `CHANGE-ENTRYPOINTS`
5. `IMPLEMENTATION-PLAYBOOKS`
6. `CHANGE-PROPAGATION-RISKS`
7. `VERIFICATION-ROUTES`
```

For `test-scan` and `test-build`, add:

```markdown
Pass the handbook gate by reading:

1. `BUILD-HANDBOOK.md`
2. `BUILD-WORKFLOW-CONTRACT`
3. `WORKFLOW-SEQUENCES`
4. `CHANGE-PROPAGATION-RISKS`
5. `VERIFICATION-ROUTES`
```

In every file, add:

```markdown
- [AGENT] If `BUILD-HANDBOOK.md` is missing, stale, or insufficient for the touched area, stop and tell the user to run `{{invoke:map-scan}}`, then `{{invoke:map-build}}`; wait for that refresh before continuing.
- Do not treat `PROJECT-HANDBOOK.md` or `.specify/project-map/**/*.md` as the primary runtime read path for this workflow.
```

- [ ] **Step 3: Replace template tests that still assert the old layered path**

In `tests/test_debug_template_guidance.py` and `tests/test_alignment_templates.py`, replace assertions that expect:

- `PROJECT-HANDBOOK.md`
- `.specify/project-map/root/ARCHITECTURE.md`
- `.specify/project-map/root/WORKFLOWS.md`
- `atlas.entry`

with assertions that expect:

- `DEBUG-HANDBOOK.md`
- `BUILD-HANDBOOK.md`
- relevant fixed chapter IDs

- [ ] **Step 4: Run the workflow-template test slice**

Run:

```powershell
pytest tests/test_debug_template_guidance.py tests/test_alignment_templates.py tests/test_runtime_handbook_contract.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the workflow prompt migration**

Run:

```powershell
git add templates/commands/debug.md templates/commands/specify.md templates/commands/plan.md templates/commands/tasks.md templates/commands/implement.md templates/commands/quick.md templates/commands/fast.md templates/commands/test-scan.md templates/commands/test-build.md templates/commands/analyze.md tests/test_debug_template_guidance.py tests/test_alignment_templates.py tests/test_runtime_handbook_contract.py
git commit -m "feat: migrate workflows to handbook-only runtime reads"
```

---

## Task 5: Rewire packet context and runtime result templates to the new handbooks

**Files:**
- Modify: `src/specify_cli/execution/packet_compiler.py`
- Modify: `src/specify_cli/codex_team/result_template.py`
- Modify: `tests/execution/test_packet_compiler.py`
- Modify: `tests/execution/test_packet_schema.py`
- Modify: `tests/execution/test_packet_validator.py`
- Modify: `tests/execution/test_result_validator.py`
- Modify: `tests/hooks/test_preflight_hooks.py`
- Modify: `tests/hooks/test_delegation_hooks.py`
- Modify: `tests/hooks/test_learning_hooks.py`

- [ ] **Step 1: Replace the default packet context bundle source list**

In `src/specify_cli/execution/packet_compiler.py`, replace the current `_context_bundle_from_project_docs()` `specs` list with:

```python
    specs: list[tuple[str, str, str, list[str], str]] = [
        (
            "DEBUG-HANDBOOK.md",
            "runtime_handbook",
            "Workflow-specific runtime handbook for debug investigations.",
            ["workflow_boundary", "architecture_boundary", "validation"],
            "debug runtime handbook is the primary atlas surface for debug work",
        ),
        (
            "BUILD-HANDBOOK.md",
            "runtime_handbook",
            "Workflow-specific runtime handbook for planning, implementation, and test-side work.",
            ["workflow_boundary", "architecture_boundary", "validation", "forbidden_drift"],
            "build runtime handbook is the primary atlas surface for non-debug work",
        ),
        (
            ".specify/testing/TESTING_CONTRACT.md",
            "testing_contract",
            "Project-level testing control plane for covered-module obligations and regression requirements.",
            ["validation", "forbidden_drift"],
            "testing contract constrains what counts as complete",
        ),
        (
            ".specify/testing/TESTING_PLAYBOOK.md",
            "testing_playbook",
            "Testing control-plane command-tier guidance for targeted and full verification during execution.",
            ["validation"],
            "testing playbook provides runnable verification commands",
        ),
        (
            ".specify/testing/COVERAGE_BASELINE.json",
            "coverage_baseline",
            "Testing control-plane coverage baseline for current covered-module status and coverage gaps.",
            ["validation"],
            "coverage baseline captures current covered-module status",
        ),
    ]
```

- [ ] **Step 2: Stop asserting old handbook/root-doc packet order**

In:

- `tests/execution/test_packet_compiler.py`
- `tests/execution/test_packet_schema.py`
- `tests/execution/test_packet_validator.py`
- `tests/execution/test_result_validator.py`
- `tests/hooks/test_preflight_hooks.py`
- `tests/hooks/test_delegation_hooks.py`
- `tests/hooks/test_learning_hooks.py`

replace all expectations that the first context item or read scope is `PROJECT-HANDBOOK.md` or `.specify/project-map/root/WORKFLOWS.md` with expectations for `DEBUG-HANDBOOK.md` and/or `BUILD-HANDBOOK.md`.

Use these concrete assertions:

```python
assert "DEBUG-HANDBOOK.md" in packet.scope.read_scope or "BUILD-HANDBOOK.md" in packet.scope.read_scope
assert packet.context_bundle[0].path in {"DEBUG-HANDBOOK.md", "BUILD-HANDBOOK.md"}
assert "PROJECT-HANDBOOK.md" not in packet.scope.read_scope
```

- [ ] **Step 3: Update runtime result-template defaults**

In `src/specify_cli/codex_team/result_template.py`, replace:

```python
            "paths_read": ["PROJECT-HANDBOOK.md"],
```

with:

```python
            "paths_read": ["BUILD-HANDBOOK.md"],
```

and adjust any descriptive string from “handbook/root navigation artifact” to “runtime workflow handbook.”

- [ ] **Step 4: Run the packet and hook validation slice**

Run:

```powershell
pytest tests/execution/test_packet_compiler.py tests/execution/test_packet_schema.py tests/execution/test_packet_validator.py tests/execution/test_result_validator.py tests/hooks/test_preflight_hooks.py tests/hooks/test_delegation_hooks.py tests/hooks/test_learning_hooks.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit the packet-context migration**

Run:

```powershell
git add src/specify_cli/execution/packet_compiler.py src/specify_cli/codex_team/result_template.py tests/execution/test_packet_compiler.py tests/execution/test_packet_schema.py tests/execution/test_packet_validator.py tests/execution/test_result_validator.py tests/hooks/test_preflight_hooks.py tests/hooks/test_delegation_hooks.py tests/hooks/test_learning_hooks.py
git commit -m "feat: switch packet context to runtime handbooks"
```

---

## Task 6: Rewrite generated integration surfaces and CLI/help text

**Files:**
- Modify: `src/specify_cli/integrations/base.py`
- Modify: `src/specify_cli/__init__.py`
- Modify: `src/specify_cli/debug/cli.py`
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `tests/integrations/test_integration_codex.py`
- Modify: `tests/integrations/test_integration_claude.py`
- Modify: `tests/integrations/test_cli.py`
- Modify: `tests/test_extension_skills.py`
- Modify: `tests/test_agent_context_managed_block.py`
- Modify: `tests/test_constitution_defaults.py`
- Modify: `tests/test_constitution_profiles_cli.py`

- [ ] **Step 1: Rewrite the generated “Crucial First Step” strings**

In `src/specify_cli/integrations/base.py`, replace all variants of:

```python
"**Crucial First Step**: You MUST pass the logical atlas contract first by reading `PROJECT-HANDBOOK.md`, `atlas.entry`, `atlas.index.status`, `atlas.index.atlas`, the relevant root topic documents, and the relevant module overview documents ..."
```

with command-specific wording:

For debug:

```python
"**Crucial First Step**: You MUST pass the runtime handbook contract first by reading `DEBUG-HANDBOOK.md` and the fixed chapter IDs required for debug before any investigation or fixes.\n"
```

For non-debug workflows:

```python
"**Crucial First Step**: You MUST pass the runtime handbook contract first by reading `BUILD-HANDBOOK.md` and the fixed chapter IDs required for this workflow before repository analysis or implementation.\n"
```

- [ ] **Step 2: Rewrite top-level CLI guidance**

In `src/specify_cli/__init__.py`, replace user-facing strings that currently say:

- refresh `PROJECT-HANDBOOK.md` and `.specify/project-map/`
- `PROJECT-HANDBOOK.md` is the root navigation artifact
- read `PROJECT-HANDBOOK.md` and the smallest relevant `.specify/project-map/*.md`

with strings that say:

- refresh `DEBUG-HANDBOOK.md` and `BUILD-HANDBOOK.md`
- the runtime atlas is the two workflow handbooks
- ordinary workflows must read the relevant handbook and fixed chapter IDs before proceeding

- [ ] **Step 3: Rewrite the debug CLI stale-atlas message**

In `src/specify_cli/debug/cli.py`, replace:

```python
f"[red]Error:[/red] Project-map freshness is {freshness}. Refresh `PROJECT-HANDBOOK.md` and `.specify/project-map/` before debug."
```

with:

```python
f"[red]Error:[/red] Project-map freshness is {freshness}. Refresh `DEBUG-HANDBOOK.md` and `BUILD-HANDBOOK.md` before debug."
```

- [ ] **Step 4: Update generated-surface integration tests**

In the listed integration test files, replace expectations for:

- `PROJECT-HANDBOOK.md`
- `atlas.entry`
- `.specify/project-map/root/ARCHITECTURE.md`
- `.specify/project-map/root/WORKFLOWS.md`
- `.specify/project-map/index/capabilities.json`

with expectations for:

- `DEBUG-HANDBOOK.md`
- `BUILD-HANDBOOK.md`
- fixed chapter IDs like `DEBUG-WORKFLOW-CONTRACT` and `BUILD-WORKFLOW-CONTRACT`

Make sure Codex/Claude/Markdown/TOML/skills renderers all assert the new contract.

- [ ] **Step 5: Run the integration rendering test slice**

Run:

```powershell
pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py tests/integrations/test_cli.py tests/test_extension_skills.py tests/test_agent_context_managed_block.py tests/test_constitution_defaults.py tests/test_constitution_profiles_cli.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit the integration and CLI migration**

Run:

```powershell
git add src/specify_cli/integrations/base.py src/specify_cli/__init__.py src/specify_cli/debug/cli.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py tests/integrations/test_cli.py tests/test_extension_skills.py tests/test_agent_context_managed_block.py tests/test_constitution_defaults.py tests/test_constitution_profiles_cli.py
git commit -m "feat: render integrations with handbook-only runtime contract"
```

---

## Task 7: Remove old layered-atlas runtime guidance from docs and remaining template surfaces

**Files:**
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `templates/project-handbook-template.md`
- Modify: `tests/test_project_handbook_templates.py`
- Modify: `tests/test_project_map_layered_contract.py`
- Modify: `tests/test_project_map_entry_contract.py`

- [ ] **Step 1: Rewrite README runtime-atlas guidance**

In `README.md`, replace sections that currently describe:

- `PROJECT-HANDBOOK.md` as the root navigation artifact
- `QUICK-NAV.md` / `index/*.json` / `root/*.md` / `modules/**/*.md` as ordinary runtime consumption surfaces

with wording that says:

- runtime atlas consumption is handbook-only
- `DEBUG-HANDBOOK.md` serves `sp-debug`
- `BUILD-HANDBOOK.md` serves other major brownfield workflows
- `sp-map-build` writes support/workbench artifacts only as internal or historical evidence, not as primary runtime read surfaces

- [ ] **Step 2: Rewrite the checked-in `PROJECT-HANDBOOK.md`**

Update `PROJECT-HANDBOOK.md` so its runtime-atlas guidance explains:

- the layered atlas model is being replaced
- ordinary workflows should not rely on `PROJECT-HANDBOOK.md` as a primary runtime read artifact
- the two workflow handbooks are the runtime entrypoint

Do not delete unrelated project-maintenance guidance outside the runtime-atlas topic.

- [ ] **Step 3: Rewrite the generated handbook template**

In `templates/project-handbook-template.md`, remove the current four-layer atlas explanation and replace it with:

```markdown
- **Runtime handbook entrypoints**:
  - `DEBUG-HANDBOOK.md` for `sp-debug`
  - `BUILD-HANDBOOK.md` for ordinary non-debug `sp-*` workflows
- These workflow handbooks are the only primary runtime atlas documents.
- Supporting project-map artifacts are not the primary runtime read path.
```

- [ ] **Step 4: Replace template tests that still bless the layered model**

In `tests/test_project_handbook_templates.py`, `tests/test_project_map_layered_contract.py`, and `tests/test_project_map_entry_contract.py`, replace assertions that require:

- `QUICK-NAV.md`
- `atlas-index.json`
- `modules.json`
- `relations.json`
- root topical docs as the primary runtime route

with assertions that require:

- `DEBUG-HANDBOOK.md`
- `BUILD-HANDBOOK.md`
- handbook-only wording

- [ ] **Step 5: Run the doc/template test slice**

Run:

```powershell
pytest tests/test_project_handbook_templates.py tests/test_project_map_layered_contract.py tests/test_project_map_entry_contract.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit the docs/template cleanup**

Run:

```powershell
git add README.md PROJECT-HANDBOOK.md templates/project-handbook-template.md tests/test_project_handbook_templates.py tests/test_project_map_layered_contract.py tests/test_project_map_entry_contract.py
git commit -m "docs: teach two-workflow runtime handbook model"
```

---

## Task 8: Run the full verification pass and review the migration surface

**Files:**
- No code changes unless verification reveals missed old-atlas assumptions

- [ ] **Step 1: Run the focused handbook-migration suite**

Run:

```powershell
pytest tests/test_runtime_handbook_contract.py tests/test_map_scan_build_template_guidance.py tests/test_alignment_templates.py tests/test_debug_template_guidance.py tests/contract/test_hook_cli_surface.py tests/execution/test_packet_compiler.py tests/execution/test_packet_schema.py tests/execution/test_packet_validator.py tests/execution/test_result_validator.py tests/hooks/test_preflight_hooks.py tests/hooks/test_delegation_hooks.py tests/hooks/test_learning_hooks.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py tests/integrations/test_cli.py tests/test_extension_skills.py tests/test_agent_context_managed_block.py tests/test_constitution_defaults.py tests/test_constitution_profiles_cli.py tests/test_project_handbook_templates.py tests/test_project_map_layered_contract.py tests/test_project_map_entry_contract.py -q
```

Expected: PASS.

- [ ] **Step 2: Run a repo-wide search for forbidden old runtime guidance**

Run:

```powershell
rg -n "PROJECT-HANDBOOK.md|atlas.entry|.specify/project-map/root/|.specify/project-map/modules/|QUICK-NAV.md|index/capabilities.json|index/symptoms.json" src/specify_cli templates tests
```

Expected: only support/workbench references remain. No ordinary workflow prompt, packet context, or primary integration guidance should still teach the old layered runtime path.

- [ ] **Step 3: Review the final diff**

Run:

```powershell
git diff --stat HEAD~7..HEAD
git diff -- templates/commands/map-build.md templates/command-partials/common/context-loading-gradient.md templates/commands/debug.md templates/commands/specify.md templates/commands/plan.md templates/commands/tasks.md templates/commands/implement.md src/specify_cli/execution/packet_compiler.py src/specify_cli/integrations/base.py src/specify_cli/hooks/artifact_validation.py src/specify_cli/project_map_status.py README.md PROJECT-HANDBOOK.md
```

Expected: the diff is limited to the two-handbook runtime migration and test/doc alignment described by this plan.

- [ ] **Step 4: Create a final fixup commit only if verification required changes**

Run only if Step 1 or Step 2 uncovered missed legacy references:

```powershell
git add <verified-fixup-paths>
git commit -m "test: finalize runtime handbook migration coverage"
```

- [ ] **Step 5: Stop for execution mode choice**

Do not start implementation automatically from this plan document. Hand off with the verification evidence and let the user choose subagent-driven or inline execution.
