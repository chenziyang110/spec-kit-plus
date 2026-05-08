# Graph-Native Downstream Workflow Adoption Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `.specify/project-cognition/status.json` plus workflow-specific slices the default downstream brownfield runtime truth surface, while shrinking `DEBUG-HANDBOOK.md`, `BUILD-HANDBOOK.md`, and `.specify/project-map/**` to explicit one-release compatibility surfaces.

**Architecture:** Execute this as a consumer-chain cutover rather than a docs-only rewrite. First, unify the shared cognition gate and stale/missing guidance. Second, propagate the new contract through runtime helpers and structured packet/result surfaces. Third, migrate downstream workflow templates and passive skills to read cognition artifacts by default. Finally, sweep broad docs, generated guidance, and tests so only intentional compatibility remains, and lock that state with an explicit compatibility inventory plus convergence assertions.

**Tech Stack:** Python 3.13, Typer CLI hooks, Markdown workflow templates, passive skills, Bash/PowerShell managed guidance scripts, pytest

---

## Scope Check

This spec touches several broad surfaces, but they are not independent subsystems.
They form one coupled downstream consumer chain:

- shared brownfield gate
- runtime helper behavior
- workflow contract wording
- passive/generated guidance
- docs and convergence tests

Splitting this into separate implementation plans would create false progress and
leave the product in an internally contradictory state.
This plan keeps the cutover in one lane, but breaks execution into small,
reviewable tasks with focused test suites and one commit per task.

## File Structure

### Shared gate and freshness surfaces

- Modify: `templates/command-partials/common/context-loading-gradient.md`
  - Keep this as the only authoritative brownfield pre-source gate.
- Modify: `templates/command-partials/common/navigation-check.md`
  - Downgrade this to an explicit compatibility shim only.
- Modify: `src/specify_cli/project_map_status.py`
  - Keep `project-map` command compatibility, but make its guidance and minimum
    read set cognition-first.
- Modify: `src/specify_cli/hooks/project_map.py`
  - Return cognition-first stale/missing warnings and block reasons.
- Test: `tests/test_project_map_hard_gate_guidance.py`
- Test: `tests/test_alignment_templates.py`

### Runtime helper propagation

- Modify: `src/specify_cli/hooks/preflight.py`
  - Preserve current behavior, but surface cognition-first wording and overlap
    guidance.
- Modify: `src/specify_cli/debug/cli.py`
  - Replace handbook refresh errors with cognition runtime refresh errors.
- Modify: `src/specify_cli/codex_team/result_template.py`
  - Replace handbook-based `paths_read` defaults with cognition status/slice
    receipts.
- Modify: `tests/hooks/test_preflight_hooks.py`
- Modify: `tests/execution/test_packet_schema.py`
- Modify: `tests/execution/test_result_validator.py`
- Modify: `tests/integrations/test_cli.py`

### Build-path downstream workflow contracts

- Modify: `templates/commands/fast.md`
- Modify: `templates/commands/quick.md`
- Modify: `templates/commands/implement.md`
- Modify: `templates/commands/analyze.md`
- Modify: `templates/command-partials/quick/shell.md`
- Modify: `templates/command-partials/implement/shell.md`
- Modify: `templates/command-partials/analyze/shell.md`
- Modify: `tests/test_fast_template_guidance.py`
- Modify: `tests/test_quick_template_guidance.py`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `tests/integrations/test_integration_base_toml.py`

### Debug, explain, and testing workflow contracts

- Modify: `templates/commands/debug.md`
- Modify: `templates/commands/explain.md`
- Modify: `templates/commands/test-scan.md`
- Modify: `templates/commands/test-build.md`
- Modify: `templates/command-partials/debug/shell.md`
- Modify: `templates/command-partials/test-scan/shell.md`
- Modify: `templates/command-partials/test/shell.md`
- Modify: `templates/passive-skills/spec-kit-project-map-gate/SKILL.md`
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Modify: `tests/test_debug_template_guidance.py`
- Modify: `tests/test_testing_workflow_guidance.py`
- Modify: `tests/test_passive_skill_guidance.py`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/integrations/test_integration_codex.py`
- Modify: `tests/integrations/test_integration_claude.py`

### Docs, managed guidance, and generated defaults

- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `docs/quickstart.md`
- Modify: `scripts/bash/update-agent-context.sh`
- Modify: `scripts/powershell/update-agent-context.ps1`
- Modify: `templates/constitution-template.md`
- Modify: `templates/constitution/profiles/product.yml`
- Modify: `templates/project-handbook-template.md`
- Modify: `tests/test_agent_context_managed_block.py`
- Modify: `tests/test_constitution_defaults.py`
- Modify: `tests/test_constitution_profiles_cli.py`
- Modify: `tests/test_project_handbook_templates.py`
- Modify: `tests/test_extension_skills.py`
- Modify: `tests/test_specify_guidance_docs.py`

### Compatibility inventory and convergence lock

- Create: `docs/project-cognition-compatibility-inventory.md`
  - Record the intentional one-release compatibility surfaces.
- Create: `tests/test_graph_native_downstream_adoption.py`
  - Fail if legacy runtime truth tokens leak outside the explicit allowlist.

## Task 1: Cut over the shared cognition gate and stale/missing guidance

**Files:**
- Modify: `templates/command-partials/common/context-loading-gradient.md`
- Modify: `templates/command-partials/common/navigation-check.md`
- Modify: `src/specify_cli/project_map_status.py`
- Modify: `src/specify_cli/hooks/project_map.py`
- Test: `tests/test_project_map_hard_gate_guidance.py`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Write failing shared-gate tests**

Add or replace assertions in `tests/test_project_map_hard_gate_guidance.py`
and `tests/test_alignment_templates.py` so the shared gate contract becomes
cognition-first.

Use assertions like:

```python
content = _read("templates/command-partials/common/context-loading-gradient.md").lower()
assert ".specify/project-cognition/status.json" in content
assert "sp-map-update" in content
assert "build-handbook.md" not in content
assert "debug-handbook.md" not in content

shim = _read("templates/command-partials/common/navigation-check.md").lower()
assert "compatibility shim" in shim
assert "must not define the primary brownfield contract" in shim
assert "project-handbook.md" not in shim
assert "index/capabilities.json" not in shim
```

- [ ] **Step 2: Run the shared-gate test slice and confirm it fails**

Run:

```powershell
pytest tests/test_project_map_hard_gate_guidance.py tests/test_alignment_templates.py -q
```

Expected: FAIL because `navigation-check.md` still teaches
`PROJECT-HANDBOOK.md` and `.specify/project-map/index/*.json` as primary
surfaces, and the stale/missing guidance still centers the old atlas wording.

- [ ] **Step 3: Implement the shared-gate cutover**

Edit `templates/command-partials/common/navigation-check.md` so the entire file
becomes a short compatibility note instead of a fallback brownfield contract.

Use content shaped like:

```md
> **Compatibility note:** `context-loading-gradient.md` is the only authoritative
> brownfield hard gate. This file remains only for templates that have not yet
> migrated and must not define the primary brownfield contract.

- Resolve `.specify/project-cognition/status.json` first.
- Treat `missing` as a rebuild through `{{invoke:map-scan}}`, then `{{invoke:map-build}}`.
- Treat `stale` as an incremental refresh through `{{invoke:map-update}}`.
- Treat `possibly_stale` as a touched-area coverage decision rooted in cognition slices.
- Do not require `PROJECT-HANDBOOK.md`, `.specify/project-map/index/*.json`,
  `.specify/project-map/root/*.md`, or `.specify/project-map/modules/**` as the
  primary runtime read path.
```

Then update stale/missing wording in `src/specify_cli/project_map_status.py`
and `src/specify_cli/hooks/project_map.py` so the canonical messages read like:

```python
MISSING_COGNITION_BASELINE_GUIDANCE = (
    "Run /sp-map-scan, then /sp-map-build to create the initial project cognition baseline."
)
STALE_COGNITION_BASELINE_GUIDANCE = (
    "Use /sp-map-update when the project cognition runtime is stale or too weak for the touched area. "
    "If no usable baseline remains, rebuild it with /sp-map-scan followed by /sp-map-build."
)
```

and:

```python
if state == "stale" and normalized in STALE_BLOCK_COMMANDS:
    return HookResult(
        event="project_map.refresh.validate",
        status="blocked",
        severity="critical",
        errors=reasons or [
            "project cognition runtime freshness is stale; refresh through /sp-map-update or rebuild through /sp-map-scan -> /sp-map-build"
        ],
        data={"freshness": freshness},
    )
```

- [ ] **Step 4: Re-run the shared-gate test slice**

Run:

```powershell
pytest tests/test_project_map_hard_gate_guidance.py tests/test_alignment_templates.py -q
```

Expected: PASS for the updated shared-gate assertions.

- [ ] **Step 5: Commit the shared-gate cutover**

Run:

```bash
git add templates/command-partials/common/context-loading-gradient.md templates/command-partials/common/navigation-check.md src/specify_cli/project_map_status.py src/specify_cli/hooks/project_map.py tests/test_project_map_hard_gate_guidance.py tests/test_alignment_templates.py
git commit -m "refactor: make the shared brownfield gate cognition-first"
```

## Task 2: Propagate cognition-first runtime helper and result/packet receipts

**Files:**
- Modify: `src/specify_cli/hooks/preflight.py`
- Modify: `src/specify_cli/debug/cli.py`
- Modify: `src/specify_cli/codex_team/result_template.py`
- Modify: `tests/hooks/test_preflight_hooks.py`
- Modify: `tests/execution/test_packet_schema.py`
- Modify: `tests/execution/test_result_validator.py`
- Modify: `tests/integrations/test_cli.py`

- [ ] **Step 1: Write failing helper and receipt tests**

Update packet/result tests so they no longer model handbook paths as the
default context bundle.

Use concrete replacements like:

```python
ContextBundleItem(
    path=".specify/project-cognition/status.json",
    kind="project_map",
    purpose="Project cognition runtime status baseline for graph readiness, stale paths, and refresh metadata.",
    required_for=["workflow_boundary"],
    read_order=1,
    must_read=True,
    selection_reason="project cognition status is the primary brownfield baseline before delegated execution",
),
ContextBundleItem(
    path=".specify/project-cognition/slices/change.json",
    kind="task_reference",
    purpose="Project cognition change slice for touched-area routing and localized brownfield context.",
    required_for=["workflow_boundary", "forbidden_drift"],
    read_order=2,
    must_read=True,
    selection_reason="change slice grounds the touched-area execution context when present",
)
```

and rule acknowledgement receipts like:

```python
paths_read=[
    ".specify/project-cognition/status.json",
    ".specify/project-cognition/slices/change.json",
]
```

In `tests/hooks/test_preflight_hooks.py`, add assertions like:

```python
assert any("project cognition runtime" in message.lower() for message in result.warnings + result.errors)
assert any("map-update" in message.lower() or "map-scan" in message.lower() for message in result.warnings + result.errors)
```

In `tests/integrations/test_cli.py`, replace the JSON fixture fragment:

```python
"read_scope": [
    ".specify/project-cognition/status.json",
    ".specify/project-cognition/slices/change.json",
],
"context_bundle": [
    {
        "path": ".specify/project-cognition/status.json",
        "kind": "project_map",
        "purpose": "project cognition routing context",
        "required_for": ["workflow_boundary"],
        "read_order": 1,
        "must_read": True,
        "selection_reason": "cognition status is the default brownfield context",
    }
],
```

- [ ] **Step 2: Run the helper contract test slice and confirm it fails**

Run:

```powershell
pytest tests/hooks/test_preflight_hooks.py tests/execution/test_packet_schema.py tests/execution/test_result_validator.py tests/integrations/test_cli.py -q
```

Expected: FAIL because the sample packet/result fixtures and schema hints still
encode `BUILD-HANDBOOK.md` and `DEBUG-HANDBOOK.md`.

- [ ] **Step 3: Implement the helper propagation**

Update `src/specify_cli/codex_team/result_template.py` so the schema hint
defaults point at cognition receipts:

```python
"rule_acknowledgement": {
    "required_references_read": True,
    "forbidden_drift_respected": True,
    "context_bundle_read": True,
    "paths_read": [
        ".specify/project-cognition/status.json",
        ".specify/project-cognition/slices/change.json",
    ],
    "critical_notes": [
        "what cognition status, slice, or conflict signal you confirmed before execution",
    ],
},
```

Update `src/specify_cli/debug/cli.py` so debug preflight errors stop demanding
handbook refresh:

```python
if freshness in {"missing", "stale"}:
    console.print(
        f"[red]Error:[/red] Project cognition runtime freshness is {freshness}. "
        "Refresh the runtime through `sp-map-update` or rebuild it with `sp-map-scan`, then `sp-map-build`, before debug."
    )
```

Update `src/specify_cli/hooks/preflight.py` only where needed so the surfaced
warnings and errors use `project cognition runtime` wording instead of
`project-map freshness` wording.

- [ ] **Step 4: Re-run the helper contract test slice**

Run:

```powershell
pytest tests/hooks/test_preflight_hooks.py tests/execution/test_packet_schema.py tests/execution/test_result_validator.py tests/integrations/test_cli.py -q
```

Expected: PASS for the updated helper receipts and wording.

- [ ] **Step 5: Commit the helper propagation**

Run:

```bash
git add src/specify_cli/hooks/preflight.py src/specify_cli/debug/cli.py src/specify_cli/codex_team/result_template.py tests/hooks/test_preflight_hooks.py tests/execution/test_packet_schema.py tests/execution/test_result_validator.py tests/integrations/test_cli.py
git commit -m "refactor: propagate cognition-first runtime helper contracts"
```

## Task 3: Migrate build-path downstream workflow contracts

**Files:**
- Modify: `templates/commands/fast.md`
- Modify: `templates/commands/quick.md`
- Modify: `templates/commands/implement.md`
- Modify: `templates/commands/analyze.md`
- Modify: `templates/command-partials/quick/shell.md`
- Modify: `templates/command-partials/implement/shell.md`
- Modify: `templates/command-partials/analyze/shell.md`
- Modify: `tests/test_fast_template_guidance.py`
- Modify: `tests/test_quick_template_guidance.py`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `tests/integrations/test_integration_base_toml.py`

- [ ] **Step 1: Write failing build-path workflow tests**

Add or replace assertions so the targeted downstream workflows require
cognition artifacts instead of handbook reads.

Use assertions shaped like:

```python
content = _read("templates/commands/fast.md")
lowered = content.lower()
assert ".specify/project-cognition/status.json" in content
assert ".specify/project-cognition/slices/change.json" in content
assert "build-handbook.md" not in lowered
assert "debug-handbook.md" not in lowered
assert "project-map/index/status.json" not in lowered
```

and:

```python
content = _read("templates/commands/implement.md")
assert "Use `/sp-map-update` when the graph runtime is stale or too weak for the touched area." in content
assert "reload `BUILD-HANDBOOK.md`" not in content
assert "Read `BUILD-HANDBOOK.md`" not in content
```

- [ ] **Step 2: Run the build-path workflow test slice and confirm it fails**

Run:

```powershell
pytest tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_alignment_templates.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py -q
```

Expected: FAIL because the build-path templates still enumerate
`BUILD-HANDBOOK.md` and handbook chapter IDs as the first required reads.

- [ ] **Step 3: Rewrite the build-path workflow templates**

In `templates/commands/fast.md`, replace the handbook read list with a
cognition-first list:

```md
2. **Pass the project cognition gate**
   - {{spec-kit-include: ../command-partials/common/context-loading-gradient.md}}
   - **This command tier: trivial.** Pass the cognition gate by reading:
     1. `.specify/project-cognition/status.json`
     2. `.specify/project-cognition/slices/change.json`
     3. add graph or testing artifacts only if the change slice does not fully cover the touched area
```

In `templates/commands/quick.md`, `templates/commands/implement.md`, and
`templates/commands/analyze.md`, replace the old required-read blocks with the
same core pattern:

```md
**This command tier: light.** Pass the cognition gate by reading:
1. `.specify/project-cognition/status.json`
2. `.specify/project-cognition/slices/change.json`
3. workflow-specific graph artifacts only when the change slice does not fully cover ownership, propagation, or verification routes
```

Also update the shell partials so their primary input bullets read like:

```md
- Primary inputs: the user's request, passive learning files, the project cognition runtime (`status.json`, required slices, and targeted live evidence), and the smallest workflow-local state files needed for the touched area.
```

Replace closeout wording that still says refresh `DEBUG-HANDBOOK.md` and
`BUILD-HANDBOOK.md` with:

```md
- If the completed work changed runtime truth-owning surfaces, refresh the project cognition runtime through `{{invoke:map-update}}` when the touched area is localized. Rebuild through `{{invoke:map-scan}}`, then `{{invoke:map-build}}` only when no usable localized baseline remains or a full rebuild is required.
```

- [ ] **Step 4: Re-run the build-path workflow test slice**

Run:

```powershell
pytest tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_alignment_templates.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py -q
```

Expected: PASS for the build-path workflow contract updates.

- [ ] **Step 5: Commit the build-path workflow migration**

Run:

```bash
git add templates/commands/fast.md templates/commands/quick.md templates/commands/implement.md templates/commands/analyze.md templates/command-partials/quick/shell.md templates/command-partials/implement/shell.md templates/command-partials/analyze/shell.md tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_alignment_templates.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py
git commit -m "refactor: migrate build-path workflows to cognition slices"
```

## Task 4: Migrate debug, explain, testing workflows, and passive gate skills

**Files:**
- Modify: `templates/commands/debug.md`
- Modify: `templates/commands/explain.md`
- Modify: `templates/commands/test-scan.md`
- Modify: `templates/commands/test-build.md`
- Modify: `templates/command-partials/debug/shell.md`
- Modify: `templates/command-partials/test-scan/shell.md`
- Modify: `templates/command-partials/test/shell.md`
- Modify: `templates/passive-skills/spec-kit-project-map-gate/SKILL.md`
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`
- Modify: `tests/test_debug_template_guidance.py`
- Modify: `tests/test_testing_workflow_guidance.py`
- Modify: `tests/test_passive_skill_guidance.py`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/integrations/test_integration_codex.py`
- Modify: `tests/integrations/test_integration_claude.py`

- [ ] **Step 1: Write failing debug/explain/testing/passive-skill tests**

Replace handbook-first assertions with cognition-first assertions.

Use exact expectations like:

```python
content = _read("templates/commands/debug.md")
assert ".specify/project-cognition/status.json" in content
assert ".specify/project-cognition/slices/debug.json" in content
assert ".specify/project-cognition/graph/claims.json" in content
assert ".specify/project-cognition/graph/conflicts.json" in content
assert "DEBUG-HANDBOOK.md" not in content
```

For `test-scan` and `test-build`:

```python
assert '".specify/project-cognition/status.json"' in content
assert '".specify/project-cognition/slices/change.json"' in content
assert '"BUILD-HANDBOOK.md"' not in content
```

For the passive gate skill:

```python
content = _read("templates/passive-skills/spec-kit-project-map-gate/SKILL.md").lower()
assert ".specify/project-cognition/status.json" in content
assert "read `debug-handbook.md`" not in content
assert "read `build-handbook.md`" not in content
assert "compatibility" in content
```

- [ ] **Step 2: Run the debug/testing/passive-skill test slice and confirm it fails**

Run:

```powershell
pytest tests/test_debug_template_guidance.py tests/test_testing_workflow_guidance.py tests/test_passive_skill_guidance.py tests/test_alignment_templates.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py -q
```

Expected: FAIL because the current templates still treat `DEBUG-HANDBOOK.md`
and `BUILD-HANDBOOK.md` as default runtime truth surfaces.

- [ ] **Step 3: Rewrite the targeted workflow and passive skill contracts**

In `templates/commands/debug.md`, replace the `Debug Handbook Gate` block with:

```md
## Debug Cognition Gate

Before observer framing moves into reproduction, logs, tests, or source-code reads, pass the cognition gate by reading:

1. `.specify/project-cognition/status.json`
2. `.specify/project-cognition/slices/debug.json`
3. `.specify/project-cognition/graph/claims.json` when truth ownership is still ambiguous
4. `.specify/project-cognition/graph/conflicts.json` when competing truths or stale assumptions exist
```

In `templates/commands/explain.md`, change the brownfield resolution bullets to:

```md
- If the user explicitly asks about project cognition, touched-area state, or brownfield runtime truth, resolve `.specify/project-cognition/status.json` and the smallest matching slice first.
- Explain handbook or project-map artifacts only when the user explicitly requests the compatibility/export surfaces themselves.
```

In `templates/commands/test-scan.md` and `templates/commands/test-build.md`,
replace handbook reads and `read_refs` JSON with:

```json
"read_refs": [
  ".specify/project-cognition/status.json",
  ".specify/project-cognition/slices/change.json",
  ".specify/testing/TESTING_CONTRACT.md",
  ".specify/testing/TESTING_PLAYBOOK.md"
]
```

Update `templates/passive-skills/spec-kit-project-map-gate/SKILL.md` to say:

```md
- Read `.specify/project-cognition/status.json` first.
- Read `.specify/project-cognition/slices/debug.json` for `sp-debug`.
- Read `.specify/project-cognition/slices/change.json` for other ordinary brownfield workflows.
- Treat `DEBUG-HANDBOOK.md`, `BUILD-HANDBOOK.md`, and `.specify/project-map/**` as compatibility/export surfaces, not the default runtime truth path.
```

and update `templates/passive-skills/spec-kit-workflow-routing/SKILL.md` so its
stale-context guidance routes through the cognition runtime rather than the
handbook system.

- [ ] **Step 4: Re-run the debug/testing/passive-skill test slice**

Run:

```powershell
pytest tests/test_debug_template_guidance.py tests/test_testing_workflow_guidance.py tests/test_passive_skill_guidance.py tests/test_alignment_templates.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py -q
```

Expected: PASS for the debug, explain, testing, and passive-skill migration.

- [ ] **Step 5: Commit the debug/testing/passive-skill migration**

Run:

```bash
git add templates/commands/debug.md templates/commands/explain.md templates/commands/test-scan.md templates/commands/test-build.md templates/command-partials/debug/shell.md templates/command-partials/test-scan/shell.md templates/command-partials/test/shell.md templates/passive-skills/spec-kit-project-map-gate/SKILL.md templates/passive-skills/spec-kit-workflow-routing/SKILL.md tests/test_debug_template_guidance.py tests/test_testing_workflow_guidance.py tests/test_passive_skill_guidance.py tests/test_alignment_templates.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py
git commit -m "refactor: migrate debug and testing workflows to cognition runtime"
```

## Task 5: Sweep docs, managed guidance, and generated default contracts

**Files:**
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `docs/quickstart.md`
- Modify: `scripts/bash/update-agent-context.sh`
- Modify: `scripts/powershell/update-agent-context.ps1`
- Modify: `templates/constitution-template.md`
- Modify: `templates/constitution/profiles/product.yml`
- Modify: `templates/project-handbook-template.md`
- Modify: `tests/test_agent_context_managed_block.py`
- Modify: `tests/test_constitution_defaults.py`
- Modify: `tests/test_constitution_profiles_cli.py`
- Modify: `tests/test_project_handbook_templates.py`
- Modify: `tests/test_extension_skills.py`
- Modify: `tests/test_specify_guidance_docs.py`

- [ ] **Step 1: Write failing docs/guidance tests**

Replace handbook-first assertions in the docs and generated guidance tests with
cognition-first assertions.

Use concrete expectations like:

```python
content = _read("README.md").lower()
assert ".specify/project-cognition/status.json" in content
assert ".specify/project-cognition/slices/change.json" in content
assert "build-handbook.md is the primary runtime surface" not in content
assert "debug-handbook.md is the primary runtime surface" not in content
```

For the managed block tests:

```python
assert "The runtime atlas is graph-native" in content
assert ".specify/project-cognition/status.json" in content
assert "use `sp-map-update`" in content.lower()
assert "DEBUG-HANDBOOK.md" not in content
assert "BUILD-HANDBOOK.md" not in content
```

For constitution/profile tests:

```python
assert "Maintain `.specify/project-cognition/status.json` and workflow-appropriate cognition slices as the default brownfield runtime truth surface" in content
assert "Maintain `DEBUG-HANDBOOK.md` and `BUILD-HANDBOOK.md` as the primary runtime atlas" not in content
```

- [ ] **Step 2: Run the docs/guidance test slice and confirm it fails**

Run:

```powershell
pytest tests/test_agent_context_managed_block.py tests/test_constitution_defaults.py tests/test_constitution_profiles_cli.py tests/test_project_handbook_templates.py tests/test_extension_skills.py tests/test_specify_guidance_docs.py -q
```

Expected: FAIL because docs, generated defaults, and managed guidance still
teach the two-handbook runtime as the default brownfield surface.

- [ ] **Step 3: Rewrite the docs and generated guidance**

In `README.md`, `PROJECT-HANDBOOK.md`, and `docs/quickstart.md`, replace the
default runtime atlas explanation with wording like:

```md
- Generated projects use `.specify/project-cognition/status.json` plus workflow-appropriate slices as the default brownfield runtime truth surface.
- `DEBUG-HANDBOOK.md`, `BUILD-HANDBOOK.md`, and `.specify/project-map/**` remain compatibility/export surfaces only during the migration window.
- Use `map-update` for localized stale cognition runtime refresh; use `map-scan` followed by `map-build` when no usable baseline remains or a full rebuild is required.
```

In `scripts/bash/update-agent-context.sh` and
`scripts/powershell/update-agent-context.ps1`, make the managed block render
the same cognition-first bullets:

```text
- The runtime atlas is graph-native: use `.specify/project-cognition/status.json` plus the workflow-appropriate slices before broader repository analysis.
- Treat `DEBUG-HANDBOOK.md`, `BUILD-HANDBOOK.md`, and `.specify/project-map/**` as compatibility/export surfaces, not the primary runtime truth path.
- If graph-native cognition coverage is missing, stop and tell the user to run `sp-map-scan`, then `sp-map-build`.
- If the runtime is stale or too weak for the touched area, use `sp-map-update`.
```

In `templates/constitution-template.md` and
`templates/constitution/profiles/product.yml`, replace the old technical source
of truth sentence with:

```md
- **Technical Source of Truth**: Maintain `.specify/project-cognition/status.json` and workflow-appropriate cognition slices as the default brownfield runtime truth surface. Legacy handbook or project-map exports are compatibility surfaces only.
```

In `templates/project-handbook-template.md`, keep the handbook artifact, but
label it explicitly as a compatibility/export view instead of the runtime
source of truth.

- [ ] **Step 4: Re-run the docs/guidance test slice**

Run:

```powershell
pytest tests/test_agent_context_managed_block.py tests/test_constitution_defaults.py tests/test_constitution_profiles_cli.py tests/test_project_handbook_templates.py tests/test_extension_skills.py tests/test_specify_guidance_docs.py -q
```

Expected: PASS for the docs, managed block, and generated-default updates.

- [ ] **Step 5: Commit the docs/guidance sweep**

Run:

```bash
git add README.md PROJECT-HANDBOOK.md docs/quickstart.md scripts/bash/update-agent-context.sh scripts/powershell/update-agent-context.ps1 templates/constitution-template.md templates/constitution/profiles/product.yml templates/project-handbook-template.md tests/test_agent_context_managed_block.py tests/test_constitution_defaults.py tests/test_constitution_profiles_cli.py tests/test_project_handbook_templates.py tests/test_extension_skills.py tests/test_specify_guidance_docs.py
git commit -m "docs: teach project cognition as the default brownfield surface"
```

## Task 6: Add compatibility inventory and lock convergence with repo-wide assertions

**Files:**
- Create: `docs/project-cognition-compatibility-inventory.md`
- Create: `tests/test_graph_native_downstream_adoption.py`

- [ ] **Step 1: Write the failing convergence test**

Create `tests/test_graph_native_downstream_adoption.py` with a strict allowlist.

Use this test body:

```python
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCANNED_FILES = [
    "README.md",
    "PROJECT-HANDBOOK.md",
    "docs/quickstart.md",
    "templates/commands/fast.md",
    "templates/commands/quick.md",
    "templates/commands/implement.md",
    "templates/commands/analyze.md",
    "templates/commands/debug.md",
    "templates/commands/explain.md",
    "templates/commands/test-scan.md",
    "templates/commands/test-build.md",
    "templates/passive-skills/spec-kit-project-map-gate/SKILL.md",
    "templates/passive-skills/spec-kit-workflow-routing/SKILL.md",
]
LEGACY_TOKENS = ("BUILD-HANDBOOK.md", "DEBUG-HANDBOOK.md", ".specify/project-map/")
ALLOWLIST = {
    "docs/project-cognition-compatibility-inventory.md",
    "templates/project-handbook-template.md",
}


def test_legacy_runtime_surface_tokens_are_confined_to_the_allowlist() -> None:
    unexpected: list[str] = []
    for rel_path in SCANNED_FILES:
        if rel_path in ALLOWLIST:
            continue
        text = (PROJECT_ROOT / rel_path).read_text(encoding="utf-8")
        if any(token in text for token in LEGACY_TOKENS):
            unexpected.append(rel_path)
    assert unexpected == []
```

- [ ] **Step 2: Run the convergence assertion and confirm it fails**

Run:

```powershell
pytest tests/test_graph_native_downstream_adoption.py -q
```

Expected: FAIL until the inventory exists and the repo-wide migration is
complete.

- [ ] **Step 3: Write the explicit compatibility inventory**

Create `docs/project-cognition-compatibility-inventory.md` with concrete
content:

```md
# Project Cognition Compatibility Inventory

## Intentional One-Release Compatibility Surfaces

- `project-map` CLI naming remains as an external compatibility shell while runtime semantics are cognition-first.
- `DEBUG-HANDBOOK.md` may remain as a reader-facing compatibility/export artifact.
- `BUILD-HANDBOOK.md` may remain as a reader-facing compatibility/export artifact.
- `.specify/project-map/**` may remain as support-only, reference-only, or export-only continuity surfaces.

## Not Default Runtime Truth

These surfaces must not be the default gate, packet context, or first-read path for downstream workflows.

- `DEBUG-HANDBOOK.md`
- `BUILD-HANDBOOK.md`
- `.specify/project-map/index/*.json`
- `.specify/project-map/root/*.md`
- `.specify/project-map/modules/**`
```

- [ ] **Step 4: Run the full convergence sweep**

Run the repo-wide search first:

```powershell
rg -n "DEBUG-HANDBOOK|BUILD-HANDBOOK|project-map|project cognition|map-update" templates src tests README.md PROJECT-HANDBOOK.md docs
```

Expected: remaining hits should be either:

- explicit compatibility inventory
- compatibility/export documentation
- intentionally preserved `project-map` CLI shell surfaces

Then run the targeted suite:

```powershell
pytest tests/test_project_map_hard_gate_guidance.py tests/hooks/test_preflight_hooks.py tests/execution/test_packet_schema.py tests/execution/test_result_validator.py tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_debug_template_guidance.py tests/test_testing_workflow_guidance.py tests/test_passive_skill_guidance.py tests/test_agent_context_managed_block.py tests/test_constitution_defaults.py tests/test_constitution_profiles_cli.py tests/test_project_handbook_templates.py tests/test_extension_skills.py tests/test_specify_guidance_docs.py tests/test_graph_native_downstream_adoption.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py tests/integrations/test_cli.py -q
```

Expected: PASS with only allowlisted compatibility hits left in the search
output.

- [ ] **Step 5: Commit the convergence lock**

Run:

```bash
git add docs/project-cognition-compatibility-inventory.md tests/test_graph_native_downstream_adoption.py
git commit -m "test: lock graph-native downstream workflow adoption"
```

## Self-Review

- Spec coverage: this plan covers the shared gate, runtime helpers, downstream
  workflows, passive/generated guidance, docs, compatibility inventory, and
  convergence verification described in the approved design spec.
- Placeholder scan: no step uses `TODO`, `TBD`, or undefined "handle later"
  language. Each task names exact files, snippets, commands, and expected test
  outcomes.
- Type consistency: the plan uses the same canonical runtime artifacts
  throughout:
  - `.specify/project-cognition/status.json`
  - `.specify/project-cognition/slices/change.json`
  - `.specify/project-cognition/slices/debug.json`
  - compatibility-only `DEBUG-HANDBOOK.md`, `BUILD-HANDBOOK.md`,
    `.specify/project-map/**`

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-08-graph-native-downstream-workflow-adoption.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
