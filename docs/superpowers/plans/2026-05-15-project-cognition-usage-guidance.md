# Project Cognition Usage Guidance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make downstream generated agents know when project cognition is mandatory and force query results to shape routing, artifacts, task packets, and closeout.

**Architecture:** Keep the current project-cognition runtime intact and change only guidance surfaces. Update constitution profile text, all managed agent-context block renderers, workflow templates, and regression tests so generated projects get the same rules across CLIs.

**Tech Stack:** Python/Typer, pytest, Markdown/TOML command templates, Bash, PowerShell, YAML constitution profiles.

---

## File Structure

- Modify `templates/constitution/profiles/product.yml`: add the principle-level rule to Product Delivery engineering standards and bump profile version.
- Modify `templates/constitution/profiles/library.yml`: add the same principle without product-only `.specify/project-cognition/status.json` wording and bump profile version.
- Modify `templates/constitution/profiles/minimal.yml`: add the same principle in lightweight wording and bump profile version.
- Modify `templates/constitution/profiles/regulated.yml`: add the same principle with traceability framing and bump profile version.
- Modify `templates/constitution-template.md`: regenerated product constitution template after profile updates.
- Modify `scripts/bash/update-agent-context.sh`: reconcile Vibe/Trae context paths, add `## Project Cognition Usage`, and clean stale wording in the managed block.
- Modify `scripts/powershell/update-agent-context.ps1`: mirror the Bash path and managed-block changes exactly.
- Modify `src/specify_cli/__init__.py`: mirror the managed-block content used by init bootstrap.
- Modify `src/specify_cli/integrations/base.py`: strengthen integration-generated hard gate addenda so runtime commands explicitly carry cognition facts into execution state before dispatch or edits.
- Modify `src/specify_cli/integrations/vibe/scripts/update-context.sh` and `src/specify_cli/integrations/vibe/scripts/update-context.ps1`: update comments to the canonical context file.
- Modify `src/specify_cli/integrations/trae/scripts/update-context.sh` and `src/specify_cli/integrations/trae/scripts/update-context.ps1`: update comments to the canonical context file.
- Modify `templates/command-partials/common/context-loading-gradient.md`: add the shared "query is complete only when used" rule.
- Modify workflow templates:
  - `templates/commands/specify.md`
  - `templates/commands/clarify.md`
  - `templates/commands/deep-research.md`
  - `templates/commands/plan.md`
  - `templates/commands/tasks.md`
  - `templates/commands/analyze.md`
  - `templates/commands/implement.md`
  - `templates/commands/debug.md`
  - `templates/commands/fast.md`
  - `templates/commands/quick.md`
  - `templates/commands/test-scan.md`
  - `templates/commands/test-build.md`
- Modify `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`: keep passive skill wording aligned with the new managed block and query consumption loop.
- Modify tests:
  - `tests/test_constitution_defaults.py`
  - `tests/test_constitution_profiles_cli.py`
  - `tests/test_agent_config_consistency.py`
  - `tests/test_agent_context_managed_block.py`
  - `tests/test_command_surface_semantics.py`
  - `tests/test_runtime_handbook_contract.py`
  - `tests/integrations/test_integration_base_markdown.py`
  - `tests/integrations/test_integration_base_skills.py`
  - `tests/integrations/test_integration_base_toml.py`
  - `tests/integrations/test_integration_claude.py`
  - focused workflow tests already owning relevant templates, especially `tests/test_alignment_templates.py`, `tests/test_debug_template_guidance.py`, `tests/test_fast_template_guidance.py`, `tests/test_quick_template_guidance.py`, and `tests/test_testing_workflow_guidance.py`.

### Task 1: Lock Constitution Principle Tests

**Files:**
- Modify: `tests/test_constitution_defaults.py`
- Modify: `tests/test_constitution_profiles_cli.py`

- [ ] **Step 1: Add failing product constitution assertions**

In `tests/test_constitution_defaults.py`, update `test_ensure_constitution_from_template_materializes_defaults` with these assertions after the existing `"default brownfield runtime truth surface"` check:

```python
    assert "Project Cognition Before Existing-System Judgment" in content
    assert "agents MUST query project cognition before broad source inspection" in content
    assert "query result MUST guide routing, minimal live reads" in content
```

Also update the expected version from `1.1.0` to `1.2.0`:

```python
    assert "**Version**: 1.2.0" in content
```

- [ ] **Step 2: Add failing non-product profile assertions**

Still in `tests/test_constitution_defaults.py`, update `test_ensure_constitution_from_template_materializes_library_profile` to assert principle-level guidance without requiring the product-only status path:

```python
    assert "Project Cognition Before Existing-System Judgment" in content
    assert "existing project truth" in content
    assert "query result MUST guide routing, minimal live reads" in content
    assert ".specify/project-cognition/status.json" not in content
    assert "**Version**: 1.1.0" in content
```

Replace the old library version assertion:

```python
    assert "**Version**: 1.0.0" in content
```

- [ ] **Step 3: Add CLI init assertions**

In `tests/test_constitution_profiles_cli.py`, update `test_init_defaults_to_product_constitution_profile`:

```python
    assert "Project Cognition Before Existing-System Judgment" in constitution
    assert "agents MUST query project cognition before broad source inspection" in constitution
```

Update `test_init_with_library_constitution_profile_materializes_project_template`:

```python
    assert "Project Cognition Before Existing-System Judgment" in template
    assert "Project Cognition Before Existing-System Judgment" in constitution
    assert ".specify/project-cognition/status.json" not in template
```

- [ ] **Step 4: Run constitution tests and confirm failure**

Run:

```powershell
pytest tests/test_constitution_defaults.py tests/test_constitution_profiles_cli.py -q
```

Expected: FAIL because the new constitution principle and versions are not present yet.

### Task 2: Implement Constitution Profile Guidance

**Files:**
- Modify: `templates/constitution/profiles/product.yml`
- Modify: `templates/constitution/profiles/library.yml`
- Modify: `templates/constitution/profiles/minimal.yml`
- Modify: `templates/constitution/profiles/regulated.yml`
- Modify: `templates/constitution-template.md`

- [ ] **Step 1: Update product profile**

In `templates/constitution/profiles/product.yml`, change:

```yaml
version: 1.1.0
```

to:

```yaml
version: 1.2.0
```

Add this bullet as the first item under `engineering_standards: |` and `## Engineering Standards`:

```markdown
  - **Project Cognition Before Existing-System Judgment**: When work depends on
    existing project truth, agents MUST query project cognition before broad
    source inspection, planning, debugging, implementation, task decomposition,
    or subagent dispatch. The query result MUST guide routing, minimal live
    reads, boundary constraints, and verification strategy.
```

- [ ] **Step 2: Update library profile**

In `templates/constitution/profiles/library.yml`, change:

```yaml
version: 1.0.0
```

to:

```yaml
version: 1.1.0
```

Add this first engineering standards bullet:

```markdown
  - **Project Cognition Before Existing-System Judgment**: When work depends on
    existing project truth, agents MUST query project cognition before broad
    source inspection, planning, debugging, implementation, task decomposition,
    or subagent dispatch. The query result MUST guide routing, minimal live
    reads, public-surface boundaries, compatibility constraints, and
    verification strategy.
```

- [ ] **Step 3: Update minimal profile**

In `templates/constitution/profiles/minimal.yml`, change:

```yaml
version: 1.0.0
```

to:

```yaml
version: 1.1.0
```

Add this first engineering standards bullet:

```markdown
  - **Project Cognition Before Existing-System Judgment**: When work depends on
    existing project truth, agents MUST query project cognition before broad
    source inspection, planning, debugging, implementation, task decomposition,
    or subagent dispatch. The query result MUST guide routing, minimal live
    reads, scope boundaries, and verification strategy.
```

- [ ] **Step 4: Update regulated profile**

In `templates/constitution/profiles/regulated.yml`, change:

```yaml
version: 1.0.0
```

to:

```yaml
version: 1.1.0
```

Add this first engineering standards bullet:

```markdown
  - **Project Cognition Before Existing-System Judgment**: When work depends on
    existing project truth, agents MUST query project cognition before broad
    source inspection, planning, debugging, implementation, task decomposition,
    or subagent dispatch. The query result MUST guide routing, minimal live
    reads, trust boundaries, control impact, and verification strategy.
```

- [ ] **Step 5: Regenerate the shipped product constitution template**

Run:

```powershell
@'
from pathlib import Path
from specify_cli import build_constitution_template_for_profile

repo = Path.cwd()
rendered, _ = build_constitution_template_for_profile("product", repo)
(repo / "templates" / "constitution-template.md").write_text(rendered, encoding="utf-8")
'@ | python -
```

Expected: `templates/constitution-template.md` now includes the new product engineering-standard bullet and product version remains materialized through the profile at init time.

- [ ] **Step 6: Run constitution tests**

Run:

```powershell
pytest tests/test_constitution_defaults.py tests/test_constitution_profiles_cli.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit constitution changes**

Run:

```powershell
git add templates/constitution/profiles/product.yml templates/constitution/profiles/library.yml templates/constitution/profiles/minimal.yml templates/constitution/profiles/regulated.yml templates/constitution-template.md tests/test_constitution_defaults.py tests/test_constitution_profiles_cli.py
git commit -m "docs: add project cognition constitution principle"
```

### Task 3: Lock Context File Path Reconciliation Tests

**Files:**
- Modify: `tests/test_agent_config_consistency.py`
- Modify: `tests/test_agent_context_managed_block.py`

- [ ] **Step 1: Add integration metadata parity test**

In `tests/test_agent_config_consistency.py`, add this helper near `REPO_ROOT`:

```python
SCRIPT_CONTEXT_PATHS = {
    "claude": "CLAUDE.md",
    "gemini": "GEMINI.md",
    "copilot": ".github/copilot-instructions.md",
    "cursor-agent": ".cursor/rules/specify-rules.mdc",
    "qwen": "QWEN.md",
    "opencode": "AGENTS.md",
    "codex": "AGENTS.md",
    "windsurf": ".windsurf/rules/specify-rules.md",
    "junie": ".junie/AGENTS.md",
    "kilocode": ".kilocode/rules/specify-rules.md",
    "auggie": ".augment/rules/specify-rules.md",
    "roo": ".roo/rules/specify-rules.md",
    "codebuddy": "CODEBUDDY.md",
    "qodercli": "QODER.md",
    "amp": "AGENTS.md",
    "shai": "SHAI.md",
    "tabnine": "TABNINE.md",
    "kiro-cli": "AGENTS.md",
    "agy": "AGENTS.md",
    "bob": "AGENTS.md",
    "vibe": "AGENTS.md",
    "kimi": "KIMI.md",
    "trae": ".trae/rules/project_rules.md",
    "pi": "AGENTS.md",
    "iflow": "IFLOW.md",
    "forge": "AGENTS.md",
}
```

Then add this test method inside `TestAgentConfigConsistency`:

```python
    def test_agent_context_script_paths_match_integration_context_files(self):
        """Shared update scripts should target each integration's canonical context file."""
        for key, expected_path in SCRIPT_CONTEXT_PATHS.items():
            integration = get_integration(key)
            assert integration is not None, key
            assert integration.context_file == expected_path
```

This test deliberately records the reconciled target set. The implementation must make the scripts match these paths.

- [ ] **Step 2: Add generated script target checks**

In `tests/test_agent_config_consistency.py`, extend `test_trae_in_agent_context_scripts`:

```python
        assert ".trae/rules/project_rules.md" in bash_text
        assert ".trae/rules/project_rules.md" in pwsh_text
        assert ".trae/rules/AGENTS.md" not in bash_text
        assert ".trae/rules/AGENTS.md" not in pwsh_text
```

Add a new Vibe context check:

```python
    def test_vibe_agent_context_scripts_use_root_agents_file(self):
        """Mistral Vibe context updates should follow integration metadata."""
        bash_text = (REPO_ROOT / "scripts" / "bash" / "update-agent-context.sh").read_text(encoding="utf-8")
        pwsh_text = (REPO_ROOT / "scripts" / "powershell" / "update-agent-context.ps1").read_text(encoding="utf-8")

        assert "VIBE_FILE=\"$AGENTS_FILE\"" in bash_text
        assert "$VIBE_FILE     = Join-Path $REPO_ROOT 'AGENTS.md'" in pwsh_text
        assert ".vibe/agents/specify-agents.md" not in bash_text
        assert ".vibe/agents/specify-agents.md" not in pwsh_text
```

- [ ] **Step 3: Add update-script behavior checks**

In `tests/test_agent_context_managed_block.py`, add:

```python
@pytest.mark.skipif(shutil.which("bash") is None, reason="bash is not installed")
def test_bash_script_updates_vibe_root_agents_file(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_repo(repo)

    result = _run_bash_update(repo, "vibe")

    assert result.returncode == 0, result.stderr
    assert (repo / "AGENTS.md").exists()
    assert not (repo / ".vibe" / "agents" / "specify-agents.md").exists()


def test_powershell_script_updates_vibe_root_agents_file(tmp_path: Path) -> None:
    if POWERSHELL is None:
        pytest.skip("PowerShell is not installed")

    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_repo(repo)

    result = _run_powershell_update(repo, "vibe")

    assert result.returncode == 0, result.stderr
    assert (repo / "AGENTS.md").exists()
    assert not (repo / ".vibe" / "agents" / "specify-agents.md").exists()


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash is not installed")
def test_bash_script_updates_trae_project_rules_file(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_repo(repo)

    result = _run_bash_update(repo, "trae")

    assert result.returncode == 0, result.stderr
    assert (repo / ".trae" / "rules" / "project_rules.md").exists()
    assert not (repo / ".trae" / "rules" / "AGENTS.md").exists()


def test_powershell_script_updates_trae_project_rules_file(tmp_path: Path) -> None:
    if POWERSHELL is None:
        pytest.skip("PowerShell is not installed")

    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_repo(repo)

    result = _run_powershell_update(repo, "trae")

    assert result.returncode == 0, result.stderr
    assert (repo / ".trae" / "rules" / "project_rules.md").exists()
    assert not (repo / ".trae" / "rules" / "AGENTS.md").exists()
```

- [ ] **Step 4: Run targeted path tests and confirm failure**

Run:

```powershell
pytest tests/test_agent_config_consistency.py::TestAgentConfigConsistency::test_trae_in_agent_context_scripts tests/test_agent_config_consistency.py::TestAgentConfigConsistency::test_vibe_agent_context_scripts_use_root_agents_file tests/test_agent_context_managed_block.py -q
```

Expected: FAIL on current Vibe/Trae shared script paths.

### Task 4: Reconcile Context File Paths

**Files:**
- Modify: `scripts/bash/update-agent-context.sh`
- Modify: `scripts/powershell/update-agent-context.ps1`
- Modify: `src/specify_cli/integrations/vibe/scripts/update-context.sh`
- Modify: `src/specify_cli/integrations/vibe/scripts/update-context.ps1`
- Modify: `src/specify_cli/integrations/trae/scripts/update-context.sh`
- Modify: `src/specify_cli/integrations/trae/scripts/update-context.ps1`

- [ ] **Step 1: Change Bash Vibe and Trae target variables**

In `scripts/bash/update-agent-context.sh`, replace:

```bash
VIBE_FILE="$REPO_ROOT/.vibe/agents/specify-agents.md"
KIMI_FILE="$REPO_ROOT/KIMI.md"
TRAE_FILE="$REPO_ROOT/.trae/rules/AGENTS.md"
```

with:

```bash
VIBE_FILE="$AGENTS_FILE"
KIMI_FILE="$REPO_ROOT/KIMI.md"
TRAE_FILE="$REPO_ROOT/.trae/rules/project_rules.md"
```

- [ ] **Step 2: Change PowerShell Vibe and Trae target variables**

In `scripts/powershell/update-agent-context.ps1`, replace:

```powershell
$VIBE_FILE     = Join-Path $REPO_ROOT '.vibe/agents/specify-agents.md'
$KIMI_FILE     = Join-Path $REPO_ROOT 'KIMI.md'
$TRAE_FILE     = Join-Path $REPO_ROOT '.trae/rules/AGENTS.md'
```

with:

```powershell
$VIBE_FILE     = Join-Path $REPO_ROOT 'AGENTS.md'
$KIMI_FILE     = Join-Path $REPO_ROOT 'KIMI.md'
$TRAE_FILE     = Join-Path $REPO_ROOT '.trae/rules/project_rules.md'
```

- [ ] **Step 3: Update integration wrapper comments**

In `src/specify_cli/integrations/vibe/scripts/update-context.sh`, replace the header comment with:

```bash
# update-context.sh — Mistral Vibe integration: create/update AGENTS.md
```

In `src/specify_cli/integrations/vibe/scripts/update-context.ps1`, replace the header comment with:

```powershell
# update-context.ps1 — Mistral Vibe integration: create/update AGENTS.md
```

In `src/specify_cli/integrations/trae/scripts/update-context.sh`, replace the header comment with:

```bash
# update-context.sh — Trae integration: create/update .trae/rules/project_rules.md
```

In `src/specify_cli/integrations/trae/scripts/update-context.ps1`, replace the header comment with:

```powershell
# update-context.ps1 — Trae integration: create/update .trae/rules/project_rules.md
```

- [ ] **Step 4: Run path tests**

Run:

```powershell
pytest tests/test_agent_config_consistency.py::TestAgentConfigConsistency::test_trae_in_agent_context_scripts tests/test_agent_config_consistency.py::TestAgentConfigConsistency::test_vibe_agent_context_scripts_use_root_agents_file tests/test_agent_context_managed_block.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit path reconciliation**

Run:

```powershell
git add scripts/bash/update-agent-context.sh scripts/powershell/update-agent-context.ps1 src/specify_cli/integrations/vibe/scripts/update-context.sh src/specify_cli/integrations/vibe/scripts/update-context.ps1 src/specify_cli/integrations/trae/scripts/update-context.sh src/specify_cli/integrations/trae/scripts/update-context.ps1 tests/test_agent_config_consistency.py tests/test_agent_context_managed_block.py
git commit -m "fix: align agent context file targets"
```

### Task 5: Lock Managed Context Usage Guidance Tests

**Files:**
- Modify: `tests/test_agent_context_managed_block.py`
- Modify: `tests/test_command_surface_semantics.py`
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Modify: `tests/integrations/test_integration_claude.py`

- [ ] **Step 1: Strengthen shared managed block assertions**

In `tests/test_agent_context_managed_block.py`, update `_assert_managed_block_has_stable_subagent_routing` with:

```python
    assert "## project cognition usage" in lower
    assert "agent context files" in lower
    assert "existing-system truth" in lower
    assert "changing existing functionality or behavior" in lower
    assert "task decomposition" in lower
    assert "debugging symptoms" in lower
    assert "testing strategy" in lower
    assert "closeout" in lower
    assert "risk, context cost, and user goal" in lower
    assert "a project-cognition query is not complete when it returns json" in lower
    assert "readiness drives routing" in lower
    assert "minimal_live_reads constrains inspection" in lower
    assert "carried into the next workflow artifact or execution state" in lower
    assert "--intent <workflow-intent>" in lower
    assert "plan`, `implement`, `debug`, `test`, and `research`" in lower
    assert "include them through `--paths`" in lower
    assert "do not assume every integration uses `agents.md`" in lower
```

Replace stale wording assertions in the same helper:

```python
    assert "graph-native cognition baseline" in lower
    assert "graph-native runtime" in lower
    assert "map-level truth" in lower
```

with:

```python
    assert "project cognition baseline" in lower
    assert "query-backed runtime" in lower
    assert "project-cognition truth" in lower
    assert "known-stale handbook state" not in lower
    assert "map-level truth" not in lower
```

- [ ] **Step 2: Update managed block semantic test**

In `tests/test_command_surface_semantics.py`, update `test_update_agent_context_managed_block_uses_refresh_or_dirty_binary_and_memory_semantics`:

```python
        assert "## project cognition usage" in content
        assert "mandatory when existing-system truth is required" in content
        assert "risk, context cost, and user goal" in content
        assert "a project-cognition query is not complete when it returns json" in content
        assert "plan`, `implement`, `debug`, `test`, and `research`" in content
        assert "do not assume every integration uses `agents.md`" in content
        assert "do not continue under known-stale handbook state without choosing one of those paths" not in content
        assert "map-level truth" not in content
```

- [ ] **Step 3: Add init bootstrap assertions for base integrations**

In each of these methods, add the same assertions after the existing `SPEC_KIT_BLOCK_START` assertion:

- `tests/integrations/test_integration_base_markdown.py::MarkdownIntegrationTests.test_init_bootstrapped_context_file_contains_managed_guidance`
- `tests/integrations/test_integration_base_skills.py::SkillsIntegrationTests.test_init_bootstrapped_context_file_contains_managed_guidance`
- `tests/integrations/test_integration_base_toml.py::TomlIntegrationTests.test_init_bootstrapped_context_file_contains_managed_guidance`

Assertions:

```python
        lower = content.lower()
        assert "## project cognition usage" in lower
        assert "mandatory when existing-system truth is required" in lower
        assert "changing existing functionality or behavior" in lower
        assert "debugging symptoms" in lower
        assert "testing strategy" in lower
        assert "risk, context cost, and user goal" in lower
        assert "a project-cognition query is not complete when it returns json" in lower
        assert "readiness drives routing" in lower
        assert "minimal_live_reads constrains inspection" in lower
        assert "carried into the next workflow artifact or execution state" in lower
        assert "do not assume every integration uses `agents.md`" in lower
```

- [ ] **Step 4: Add Claude bootstrap assertion**

In `tests/integrations/test_integration_claude.py`, find `test_init_bootstrapped_context_file_contains_managed_guidance` with `rg -n "test_init_bootstrapped_context_file_contains_managed_guidance" tests/integrations/test_integration_claude.py` and add:

```python
        lower = content.lower()
        assert "## project cognition usage" in lower
        assert "mandatory when existing-system truth is required" in lower
        assert "risk, context cost, and user goal" in lower
        assert "a project-cognition query is not complete when it returns json" in lower
        assert "do not assume every integration uses `agents.md`" in lower
```

Also update existing bootstrap assertions in the base integration tests only for the init context-file managed guidance checks:

```python
        assert "graph-native cognition baseline" in content.lower()
```

should become:

```python
        assert "project cognition baseline" in content.lower()
```

Do not globally remove `graph-native` wording from map-scan/map-build help, project-cognition internals, or tests that intentionally describe the graph-native baseline lifecycle outside the generated agent context managed block.

- [ ] **Step 5: Run targeted managed-block tests and confirm failure**

Run:

```powershell
pytest tests/test_agent_context_managed_block.py tests/test_command_surface_semantics.py::test_update_agent_context_managed_block_emitters_remain_cross_shell_equivalent tests/test_command_surface_semantics.py::test_update_agent_context_managed_block_uses_refresh_or_dirty_binary_and_memory_semantics tests/integrations/test_integration_codex.py::TestCodexIntegration::test_init_bootstrapped_context_file_contains_managed_guidance tests/integrations/test_integration_gemini.py::TestGeminiIntegration::test_init_bootstrapped_context_file_contains_managed_guidance tests/integrations/test_integration_claude.py::TestClaudeIntegration::test_init_bootstrapped_context_file_contains_managed_guidance -q
```

Expected: FAIL because the new usage section is not implemented yet.

### Task 6: Implement Managed Context Usage Guidance

**Files:**
- Modify: `scripts/bash/update-agent-context.sh`
- Modify: `scripts/powershell/update-agent-context.ps1`
- Modify: `src/specify_cli/__init__.py`

- [ ] **Step 1: Add the usage section to the Bash managed block**

In `scripts/bash/update-agent-context.sh`, insert this section immediately after `## Brownfield Context Gate` and its existing bullets, before `## Project Memory`:

```markdown
## Project Cognition Usage

- Project cognition is mandatory when existing-system truth is required. If the task needs to know how this project is organized, implemented, owned, integrated, or verified, query project cognition before broad source inspection, planning, debugging, testing strategy, implementation, task decomposition, or subagent dispatch.
- The same rule applies across agent context files; do not assume every integration uses `AGENTS.md`.
- When the task does not require existing-system truth, decide based on risk, context cost, and user goal; this is not a bypass for existing-system judgment.
- Mandatory scenarios include changing existing functionality or behavior such as login, payment, routing, permissions, import/export, notifications, or background jobs; judging module ownership, truth owners, architecture boundaries, reuse points, integration points, state surfaces, or consumer impact; writing or updating `specify`, `plan`, or `tasks` outputs for the current project; running `implement`, `quick`, or `fast` work against existing code, tests, configuration, routes, protocols, data models, or workflows; debugging symptoms that map to existing capabilities, entrypoints, state surfaces, or test surfaces; decomposing tasks, compiling task packets, or dispatching subagents that need read scope, write scope, required references, or validation commands; choosing testing strategy, verification entry points, regression scope, or coverage-gap handling; changing architecture boundaries, workflow contracts, integration contracts, ownership, or verification entry points; and closeout when work changed project-cognition truth.
- Query through the project launcher or generated command renderer with `project-cognition query --intent <workflow-intent> --query "<task summary>" --format json`. Valid workflow intents include at least `plan`, `implement`, `debug`, `test`, and `research`. When relevant paths are known from the user request or upstream artifacts, include them through `--paths`.
- Use readiness for routing: `ready` continues with the task-local bundle; `review` permits only returned `minimal_live_reads` before trusting the runtime; `ambiguous` asks the user or upstream artifact to select the intended candidate; `needs_update` routes through `sp-map-update`; `needs_rebuild` routes through `sp-map-scan`, then `sp-map-build`; `blocked` stops with the runtime issue.
- Extract and carry forward the matched capability or symptom, affected nodes and subgraph, `minimal_live_reads`, missing coverage, evidence traces, verification routes, ambiguity, conflicts, and weak coverage.
- Constrain first live reads to `minimal_live_reads` plus directly relevant durable workflow artifacts. Expand search only when those reads do not answer the task.
- A project-cognition query is not complete when it returns JSON. It is complete only when readiness drives routing, `minimal_live_reads` constrains inspection, and relevant facts are carried into the next workflow artifact or execution state.
```

- [ ] **Step 2: Replace stale managed-block wording in Bash**

In the same Bash managed block, replace:

```markdown
- If the graph-native cognition baseline is missing, stop and tell the user to run the runtime's `map-scan` workflow entrypoint followed by `map-build`, then wait for that refresh before continuing.
- If the graph runtime is stale or too weak for the touched area, use `sp-map-update` after baseline creation before broader work continues.
```

with:

```markdown
- If the project cognition baseline is missing, stop and tell the user to run the runtime's `map-scan` workflow entrypoint followed by `map-build`, then wait for that refresh before continuing.
- If the query-backed runtime is stale or too weak for the touched area, use `sp-map-update` after baseline creation before broader work continues.
```

Replace:

```markdown
- Do not continue under known-stale handbook state without choosing one of those paths.
- Do not treat consumed project cognition query context as self-maintaining; the agent changing map-level truth is responsible for keeping the query-backed runtime current.
```

with:

```markdown
- Do not continue under stale project-cognition truth without choosing one of those paths.
- Do not treat consumed project cognition query context as self-maintaining; the agent changing project-cognition truth is responsible for keeping the query-backed runtime current.
```

- [ ] **Step 3: Mirror the same managed block changes in PowerShell**

In `scripts/powershell/update-agent-context.ps1`, insert the same `## Project Cognition Usage` lines as single-quoted string entries in `Get-SpecKitManagedBlock`, using doubled single quotes only where needed.

Mirror the same stale wording replacements:

```powershell
'- If the project cognition baseline is missing, stop and tell the user to run the runtime''s `map-scan` workflow entrypoint followed by `map-build`, then wait for that refresh before continuing.'
'- If the query-backed runtime is stale or too weak for the touched area, use `sp-map-update` after baseline creation before broader work continues.'
'- Do not continue under stale project-cognition truth without choosing one of those paths.'
'- Do not treat consumed project cognition query context as self-maintaining; the agent changing project-cognition truth is responsible for keeping the query-backed runtime current.'
```

- [ ] **Step 4: Mirror the managed block in Python init bootstrap**

In `src/specify_cli/__init__.py`, update `_render_spec_kit_managed_block` with the same `## Project Cognition Usage` section and stale wording replacements.

Use Python string quoting like:

```python
            "## Project Cognition Usage",
            "",
            "- Project cognition is mandatory when existing-system truth is required. If the task needs to know how this project is organized, implemented, owned, integrated, or verified, query project cognition before broad source inspection, planning, debugging, testing strategy, implementation, task decomposition, or subagent dispatch.",
```

- [ ] **Step 5: Confirm Bash/PowerShell managed block equivalence**

Run:

```powershell
pytest tests/test_command_surface_semantics.py::test_update_agent_context_managed_block_emitters_remain_cross_shell_equivalent -q
```

Expected: PASS. If it fails, use the diff in the assertion output to make Bash and PowerShell managed blocks text-equivalent after newline normalization.

- [ ] **Step 6: Run managed-block tests**

Run:

```powershell
pytest tests/test_agent_context_managed_block.py tests/test_command_surface_semantics.py::test_update_agent_context_managed_block_uses_refresh_or_dirty_binary_and_memory_semantics tests/integrations/test_integration_codex.py::TestCodexIntegration::test_init_bootstrapped_context_file_contains_managed_guidance tests/integrations/test_integration_gemini.py::TestGeminiIntegration::test_init_bootstrapped_context_file_contains_managed_guidance tests/integrations/test_integration_claude.py::TestClaudeIntegration::test_init_bootstrapped_context_file_contains_managed_guidance -q
```

Expected: PASS.

- [ ] **Step 7: Commit managed context guidance**

Run:

```powershell
git add scripts/bash/update-agent-context.sh scripts/powershell/update-agent-context.ps1 src/specify_cli/__init__.py tests/test_agent_context_managed_block.py tests/test_command_surface_semantics.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_claude.py
git commit -m "docs: teach project cognition usage scenarios"
```

### Task 7: Lock Workflow Carry-Forward Tests

**Files:**
- Modify: `tests/test_runtime_handbook_contract.py`
- Modify: focused workflow tests listed below

- [ ] **Step 1: Add shared carry-forward test**

In `tests/test_runtime_handbook_contract.py`, add:

```python
def test_context_loading_gradient_requires_cognition_carry_forward() -> None:
    content = _read("templates/command-partials/common/context-loading-gradient.md").lower()

    assert "a project-cognition query is not complete when it returns json" in content
    assert "readiness drives routing" in content
    assert "minimal_live_reads constrains inspection" in content
    assert "next workflow artifact or execution state" in content
```

- [ ] **Step 2: Add template carry-forward matrix test**

In `tests/test_runtime_handbook_contract.py`, add:

```python
def test_workflow_templates_carry_project_cognition_facts_forward() -> None:
    expectations = {
        "templates/commands/specify.md": ("context.md", "ownership", "verification routes"),
        "templates/commands/clarify.md": ("clarified spec package", "ownership", "verification"),
        "templates/commands/deep-research.md": ("deep-research.md", "repository facts", "external research"),
        "templates/commands/plan.md": ("Implementation Constitution", "verification strategy", "plan-contract.json"),
        "templates/commands/tasks.md": ("tasks.md", "task-index.json", "task packets"),
        "templates/commands/analyze.md": ("cognition-backed blocker evidence", "clarify", "deep-research"),
        "templates/commands/implement.md": ("implement-tracker.md", "WorkerTaskPacket", "minimal live reads"),
        "templates/commands/debug.md": ("debug session state", "competing truths", "coverage gaps"),
        "templates/commands/fast.md": ("fast-task state or report", "verification route", "minimal reads"),
        "templates/commands/quick.md": ("STATUS.md", "validation route", "known risk"),
        "templates/commands/test-scan.md": ("TEST_SCAN.md", "TEST_BUILD_PLAN", "testing-surface ownership"),
        "templates/commands/test-build.md": ("TEST_BUILD_PLAN", "testing-state.md", "coverage gaps"),
    }

    for rel_path, phrases in expectations.items():
        content = _read(rel_path).lower()
        assert "project-cognition query" in content, rel_path
        for phrase in phrases:
            assert phrase.lower() in content, f"{rel_path} missing {phrase!r}"
```

- [ ] **Step 3: Add focused assertions where tests already exist**

Update existing focused tests with one or two high-signal assertions:

In `tests/test_debug_template_guidance.py`:

```python
    assert "debug session state" in content.lower()
    assert "competing truths" in content.lower()
    assert "coverage gaps" in content.lower()
```

In `tests/test_fast_template_guidance.py`:

```python
    assert "fast-task state or report" in content.lower()
    assert "verification route" in content.lower()
```

In `tests/test_quick_template_guidance.py`:

```python
    assert "STATUS.md" in content
    assert "validation route" in content.lower()
    assert "known risk" in content.lower()
```

In `tests/test_testing_workflow_guidance.py`, add assertions to the test-scan and test-build guidance tests:

```python
    assert "testing-surface ownership" in content.lower()
    assert "coverage gaps" in content.lower()
    assert "required live reads" in content.lower()
```

- [ ] **Step 4: Run carry-forward tests and confirm failure**

Run:

```powershell
pytest tests/test_runtime_handbook_contract.py tests/test_debug_template_guidance.py tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_testing_workflow_guidance.py -q
```

Expected: FAIL because carry-forward wording is incomplete.

### Task 8: Implement Shared Carry-Forward Rules

**Files:**
- Modify: `templates/command-partials/common/context-loading-gradient.md`
- Modify: `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`

- [ ] **Step 1: Update shared context-loading partial**

In `templates/command-partials/common/context-loading-gradient.md`, after `### Fixed Bundle Consumption`, add:

```markdown
### Query Completion

A project-cognition query is not complete when it returns JSON. It is complete
only when readiness drives routing, `minimal_live_reads` constrains inspection,
and relevant facts are carried into the next workflow artifact or execution
state.

Extract and carry forward the matched capability or symptom, affected nodes and
subgraph, `minimal_live_reads`, missing coverage, evidence traces, verification
routes, ambiguity, conflicts, and weak coverage.
```

- [ ] **Step 2: Update passive skill**

In `templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md`, add this bullet under `## Hard Gate`:

```markdown
- A project-cognition query is not complete when it returns JSON. It is complete
  only when readiness drives routing, `minimal_live_reads` constrains
  inspection, and relevant facts are carried into the next workflow artifact or
  execution state.
```

Add this bullet after it:

```markdown
- Extract and carry forward the matched capability or symptom, affected nodes,
  `minimal_live_reads`, missing coverage, evidence traces, verification routes,
  ambiguity, conflicts, and weak coverage.
```

- [ ] **Step 3: Run shared carry-forward test**

Run:

```powershell
pytest tests/test_runtime_handbook_contract.py::test_context_loading_gradient_requires_cognition_carry_forward -q
```

Expected: PASS.

### Task 9: Implement Workflow Carry-Forward Targets

**Files:**
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/clarify.md`
- Modify: `templates/commands/deep-research.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/commands/analyze.md`
- Modify: `templates/commands/implement.md`
- Modify: `templates/commands/debug.md`
- Modify: `templates/commands/fast.md`
- Modify: `templates/commands/quick.md`
- Modify: `templates/commands/test-scan.md`
- Modify: `templates/commands/test-build.md`

- [ ] **Step 1: Update `sp-specify`**

In `templates/commands/specify.md`, after the existing project cognition extraction bullet around the hard gate, add:

```markdown
   - **CARRY FORWARD**: Write project-cognition ownership, affected surfaces,
     reusable assets, verification routes, and known unknowns into `context.md`
     and the brainstorming handoff where they materially shape the downstream
     plan. Do not leave these facts only in the transient query output.
```

- [ ] **Step 2: Update `sp-clarify`**

In `templates/commands/clarify.md`, after the project cognition readiness handling, add:

```markdown
   - **CARRY FORWARD**: Use project-cognition facts to decide whether an
     apparent requirement gap is already answered by repository truth. Preserve
     selected ownership, boundary, ambiguity, and verification facts in the
     clarified spec package before routing back to planning.
```

- [ ] **Step 3: Update `sp-deep-research`**

In `templates/commands/deep-research.md`, after the project cognition query block, add:

```markdown
   - **CARRY FORWARD**: Treat project-cognition results as repository-grounded
     starting context. Preserve cited capabilities, constraints, affected
     surfaces, and verification routes in `deep-research.md`, and distinguish
     repository facts from external research findings.
```

- [ ] **Step 4: Update `sp-plan`**

In `templates/commands/plan.md`, after the readiness list for the project cognition query, add:

```markdown
   - **CARRY FORWARD**: Promote project-cognition facts into planning
     constraints, `Implementation Constitution`, boundary rules, verification
     strategy, and `plan-contract.json` when they affect implementation shape.
```

- [ ] **Step 5: Update `sp-tasks`**

In `templates/commands/tasks.md`, after the readiness list for the project cognition query, add:

```markdown
   - **CARRY FORWARD**: Carry cognition-derived required references, write
     scopes, validation commands, forbidden drift, and known unknowns into
     `tasks.md`, `task-index.json`, and task packets.
```

- [ ] **Step 6: Update `sp-analyze`**

In `templates/commands/analyze.md`, after `- Consume the project-cognition query bundle.`, add:

```markdown
- Preserve cognition-backed blocker evidence when classifying whether issues
  belong to `plan`, `clarify`, `deep-research`, or task-layer remediation. The
  analysis report and `workflow-state.md` blocker bundle must keep the selected
  capability, boundary fact, ambiguity, or verification evidence that justified
  the route.
```

- [ ] **Step 7: Update `sp-implement`**

In `templates/commands/implement.md`, after the project cognition readiness block, add:

```markdown
- **CARRY FORWARD**: Before dispatch or code edits, write the selected
  capability, minimal live reads, boundary constraints, required references,
  validation route, and evidence gaps into `implement-tracker.md` or the current
  `WorkerTaskPacket`. Do not dispatch from a packet that omits the relevant
  project-cognition facts.
```

- [ ] **Step 8: Update `sp-debug`**

In `templates/commands/debug.md`, after the project cognition query block, add:

```markdown
- **CARRY FORWARD**: Write the selected capability or symptom, evidence routes,
  minimal reads, competing truths, and unresolved coverage gaps into debug
  session state before making root-cause claims.
```

- [ ] **Step 9: Update `sp-fast`**

In `templates/commands/fast.md`, after the readiness list, add:

```markdown
   - **CARRY FORWARD**: Use project-cognition signals to decide whether
     fast-path execution is still safe. Carry the selected capability, minimal
     reads, and verification route into the fast-task state or report.
```

- [ ] **Step 10: Update `sp-quick`**

In `templates/commands/quick.md`, update the `STATUS.md Template` under `## Execution Intent` by adding:

```markdown
cognition_facts:
  selected_capability: [capability, route, symptom, or unknown]
  minimal_reads:
    - [project-cognition minimal_live_reads entry used before wider inspection]
  validation_route: [test, command, manual check, or unknown]
  known_risk: [ambiguity, weak coverage, forbidden drift, or none]
```

Also add this lifecycle bullet after the project cognition readiness block:

```markdown
- **CARRY FORWARD**: Write the selected capability, minimal reads, validation
  route, and known risk into quick-task `STATUS.md` before implementation
  proceeds.
```

- [ ] **Step 11: Update `sp-test-scan`**

In `templates/commands/test-scan.md`, after the project cognition readiness list, add:

```markdown
   - **CARRY FORWARD**: Carry project-cognition testing-surface ownership,
     covered modules, verification nodes, coverage gaps, and required live
     reads into `TEST_SCAN.md`, `TEST_BUILD_PLAN.md`, `TEST_BUILD_PLAN.json`,
     and `testing-state.md`.
```

- [ ] **Step 12: Update `sp-test-build`**

In `templates/commands/test-build.md`, after the testing-surface coverage insufficiency bullets, add:

```markdown
   - **CARRY FORWARD**: Carry project-cognition testing-surface ownership,
     covered modules, verification nodes, coverage gaps, and required live
     reads from the query bundle and `TEST_BUILD_PLAN` into `testing-state.md`
     before selecting build lanes.
```

- [ ] **Step 13: Run carry-forward tests**

Run:

```powershell
pytest tests/test_runtime_handbook_contract.py tests/test_debug_template_guidance.py tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_testing_workflow_guidance.py -q
```

Expected: PASS.

- [ ] **Step 14: Commit workflow carry-forward guidance**

Run:

```powershell
git add templates/command-partials/common/context-loading-gradient.md templates/passive-skills/spec-kit-project-cognition-gate/SKILL.md templates/commands/specify.md templates/commands/clarify.md templates/commands/deep-research.md templates/commands/plan.md templates/commands/tasks.md templates/commands/analyze.md templates/commands/implement.md templates/commands/debug.md templates/commands/fast.md templates/commands/quick.md templates/commands/test-scan.md templates/commands/test-build.md tests/test_runtime_handbook_contract.py tests/test_debug_template_guidance.py tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_testing_workflow_guidance.py
git commit -m "docs: require cognition carry-forward in workflows"
```

### Task 10: Align Integration Runtime Addenda

**Files:**
- Modify: `src/specify_cli/integrations/base.py`
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `tests/integrations/test_integration_base_toml.py`

- [ ] **Step 1: Add failing runtime addendum assertions**

In `test_runtime_commands_hard_gate_project_cognition_reads` in each base test file, add:

```python
            assert "carry forward" in content
            assert "next workflow artifact or execution state" in content
```

For Markdown and skills base tests, also add:

```python
            if f.name.endswith("sp.implement.md") or f.parent.name == "sp-implement":
                assert "implement-tracker.md" in content
                assert "workertaskpacket" in content
            if f.name.endswith("sp.quick.md") or f.parent.name == "sp-quick":
                assert "status.md" in content
            if f.name.endswith("sp.debug.md") or f.parent.name == "sp-debug":
                assert "debug session state" in content
```

For TOML, use name checks against `f.name`:

```python
            if "implement" in f.name:
                assert "implement-tracker.md" in content
                assert "workertaskpacket" in content
            if "quick" in f.name:
                assert "status.md" in content
            if "debug" in f.name:
                assert "debug session state" in content
```

- [ ] **Step 2: Run integration runtime tests and confirm failure**

Run:

```powershell
pytest tests/integrations/test_integration_codex.py::TestCodexIntegration::test_runtime_commands_hard_gate_project_cognition_reads tests/integrations/test_integration_gemini.py::TestGeminiIntegration::test_runtime_commands_hard_gate_project_cognition_reads -q
```

Expected: FAIL because generated addenda do not yet include carry-forward language.

- [ ] **Step 3: Update `src/specify_cli/integrations/base.py` addendum**

In `_append_runtime_project_cognition_gate`, after the existing "Treat this as a hard gate" bullet, append command-specific carry-forward guidance.

Add this mapping before `addendum = (`:

```python
        carry_forward = {
            "implement": "- Carry forward the selected capability, minimal live reads, boundary constraints, required references, validation route, and evidence gaps into `implement-tracker.md` or the current `WorkerTaskPacket` before dispatch or code edits.\n",
            "debug": "- Carry forward the selected capability or symptom, evidence routes, minimal reads, competing truths, and unresolved coverage gaps into debug session state before root-cause claims.\n",
            "quick": "- Carry forward the selected capability, minimal reads, validation route, and known risk into quick-task `STATUS.md` before implementation proceeds.\n",
        }[command_name]
```

Then include it in the addendum:

```python
            "- A project-cognition query is not complete when it returns JSON. It is complete only when readiness drives routing, `minimal_live_reads` constrains inspection, and relevant facts are carried into the next workflow artifact or execution state.\n"
            f"{carry_forward}"
```

- [ ] **Step 4: Run integration runtime tests**

Run:

```powershell
pytest tests/integrations/test_integration_codex.py::TestCodexIntegration::test_runtime_commands_hard_gate_project_cognition_reads tests/integrations/test_integration_gemini.py::TestGeminiIntegration::test_runtime_commands_hard_gate_project_cognition_reads -q
```

Expected: PASS.

- [ ] **Step 5: Commit integration addendum alignment**

Run:

```powershell
git add src/specify_cli/integrations/base.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py
git commit -m "docs: carry cognition facts into runtime addenda"
```

### Task 11: Full Verification and Final Cleanup

**Files:**
- Verify all modified files.

- [ ] **Step 1: Search for stale context-file paths**

Run:

```powershell
rg -n "\.vibe/agents/specify-agents\.md|\.trae/rules/AGENTS\.md" scripts src tests templates README.md PROJECT-HANDBOOK.md
```

Expected: no output.

- [ ] **Step 2: Search for stale managed-block wording**

Run:

```powershell
rg -n "known-stale handbook state|map-level truth|graph-native cognition baseline|graph-native runtime" scripts/bash/update-agent-context.sh scripts/powershell/update-agent-context.ps1 src/specify_cli/__init__.py
```

Expected: no output from the three managed-block renderers.

- [ ] **Step 3: Run focused regression suite**

Run:

```powershell
pytest tests/test_constitution_defaults.py tests/test_constitution_profiles_cli.py tests/test_agent_config_consistency.py tests/test_agent_context_managed_block.py tests/test_command_surface_semantics.py::test_update_agent_context_managed_block_emitters_remain_cross_shell_equivalent tests/test_command_surface_semantics.py::test_update_agent_context_managed_block_uses_refresh_or_dirty_binary_and_memory_semantics tests/test_runtime_handbook_contract.py tests/test_debug_template_guidance.py tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_testing_workflow_guidance.py tests/integrations/test_integration_codex.py::TestCodexIntegration::test_runtime_commands_hard_gate_project_cognition_reads tests/integrations/test_integration_gemini.py::TestGeminiIntegration::test_runtime_commands_hard_gate_project_cognition_reads tests/integrations/test_integration_claude.py::TestClaudeIntegration::test_init_bootstrapped_context_file_contains_managed_guidance -q
```

Expected: PASS.

- [ ] **Step 4: Run broader template alignment tests**

Run:

```powershell
pytest tests/test_alignment_templates.py tests/test_extension_skills.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_gemini.py tests/integrations/test_integration_claude.py -q
```

Expected: PASS. If failures are old wording assertions, update tests only when the product text intentionally changed and still preserves the same behavior.

- [ ] **Step 5: Inspect diff**

Run:

```powershell
git diff --check
git status --short
git diff --stat
```

Expected: no whitespace errors; only expected files modified.

- [ ] **Step 6: Commit final cleanup if needed**

If Step 4 or Step 5 required cleanup, run:

```powershell
git add <changed-files>
git commit -m "test: cover project cognition guidance propagation"
```

If no cleanup was needed, do not create an empty commit.

## Notes for Implementers

- Do not change `project-cognition query` scoring, alias matching, graph schema, or database behavior in this work.
- Use the launcher-backed renderer form in generated workflow templates: `{{specify-subcmd:project-cognition query --intent <intent> --query "$ARGUMENTS" --format json}}`.
- In human-facing shared context guidance, describe invocation as project-launcher or generated-renderer backed. Do not imply a bare PATH command is the only correct shape.
- The complete generated context-file target set comes from integration metadata and update scripts. Vibe should converge to `AGENTS.md`; Trae should converge to `.trae/rules/project_rules.md`.
- Avoid bypass wording. Say when project cognition is mandatory and when the agent decides based on risk, context cost, and user goal.
- Keep all managed block renderers semantically aligned: Bash, PowerShell, and Python init bootstrap.
