# Aggressive Test Suite Trimming Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Delete redundant and low-value pytest code so the suite drops from 3,286 collected tests to roughly 1,200-1,600 while retaining release-critical contracts.

**Architecture:** This is a test-suite reduction, not a production feature. Work proceeds in independently verifiable deletion waves: integration matrix wrappers, template wording locks, presets/extensions permutations, hook/contract variants, cross-shell script combinations, then a careful Codex team pass only if needed.

**Tech Stack:** Python 3.13, pytest 9, Typer CliRunner, PowerShell shell, repository-local `uv run pytest`.

---

## Source Spec

Use the approved design in `docs/superpowers/specs/2026-05-21-test-suite-trimming-design.md`.

The implementation must preserve these contracts:

- CLI/init/install generated assets still have smoke coverage.
- Integration behavior is represented by samples for Markdown, skills, TOML, Copilot, Forge, opencode, Codex, and Generic.
- Registry/config tests still prove every supported integration exists.
- Hook fail-closed behavior remains covered for missing, malformed, unsafe, and clean states.
- Packaging asset inclusion remains covered.
- High-risk state-machine and validation logic keeps compact unit coverage.

## File Structure

Files modified by deletion:

- `tests/integrations/test_integration_*.py`: remove most small per-agent mixin wrappers and duplicate deep integration tests. Keep representative sample files.
- `tests/integrations/test_integration_base_markdown.py`: remove parametrized all-agent deep rendering checks; keep shared mixin helpers and representative behavior tests.
- `tests/integrations/test_integration_base_skills.py`: remove all-skills matrix checks except representative samples.
- `tests/integrations/test_integration_base_toml.py`: keep TOML processing/parser tests and one TOML representative path.
- `tests/integrations/test_registry.py`: keep or strengthen registry coverage so every deleted wrapper remains represented by metadata checks.
- `tests/test_alignment_templates.py`: collapse incidental wording checks and keep broad workflow-contract tests.
- `tests/test_specify_guidance_docs.py`, `tests/test_quick_template_guidance.py`, `tests/test_deep_research_template_guidance.py`, `tests/test_map_scan_build_template_guidance.py`, `tests/test_prd_scan_build_template_guidance.py`, and nearby template guidance files: delete narrow sentence locks that duplicate broader template contracts.
- `tests/test_presets.py`: retain manifest loading, unsafe manifest rejection, install/remove, registry, resolver priority, and CLI smoke; delete equivalent manifest permutation tests.
- `tests/test_extensions.py`: retain manifest loading, unsafe manifest rejection, install/remove, command registration, hook executor, catalog stack, and CLI smoke; delete equivalent schema/priority/file-list permutations.
- `tests/contract/test_hook_cli_surface.py`: keep JSON surface, representative validate-state/preflight/artifact/packet/policy/learning commands, and key map/prd fail-closed cases; delete repeated command aliases and equivalent artifact variants.
- `tests/hooks/test_artifact_hooks.py`: keep representative artifact validators for each workflow phase and consequence gate; delete equivalent missing-field and wording variants.
- `tests/hooks/test_preflight_hooks.py`: keep one representative git-backed preflight per category; delete duplicate git setup cases.
- `tests/test_timestamp_branches.py`: keep a compact branch naming and dry-run contract; delete cross-product shell combinations that exercise the same parser branch.
- `tests/test_project_map_freshness_scripts.py`: keep one Bash and one PowerShell smoke path plus key shared semantics; delete parity matrix rows after shared behavior is covered.
- `tests/codex_team/test_auto_dispatch.py`, `tests/codex_team/test_runtime_bridge.py`, `tests/codex_team/test_task_ops.py`, and adjacent Codex team tests: trim only after lower-risk waves and preserve state-machine safety.

No production files should be modified unless a test import or helper becomes dead and causes collection errors.

## Task 1: Baseline Collection and Accounting

**Files:**
- Read: `docs/superpowers/specs/2026-05-21-test-suite-trimming-design.md`
- Read: `pyproject.toml`
- Read: `tests/**`
- Create if useful: `docs/superpowers/plans/2026-05-21-test-suite-trimming-counts.md`

- [ ] **Step 1: Confirm the current collected test count**

Run:

```powershell
uv run pytest --collect-only -q
```

Expected: the command completes and reports about `3286 tests collected`. If the number differs, record the actual number and use it as the baseline.

- [ ] **Step 2: Generate a per-file count snapshot**

Run:

```powershell
$rows = @()
foreach ($file in (rg --files tests -g 'test_*.py')) {
    $matches = Select-String -Path $file -Pattern '^def test_|^\s+def test_' -AllMatches
    $rows += [pscustomobject]@{
        Path = $file
        Count = $matches.Matches.Count
    }
}
$rows | Sort-Object Count -Descending | Format-Table -AutoSize
```

Expected: the largest files include `tests/test_presets.py`, `tests/test_extensions.py`, `tests/test_alignment_templates.py`, `tests/contract/test_hook_cli_surface.py`, `tests/integrations/test_cli.py`, `tests/hooks/test_artifact_hooks.py`, `tests/integrations/test_integration_claude.py`, and `tests/test_timestamp_branches.py`.

- [ ] **Step 3: Record deletion accounting**

If you create an accounting note, write:

```markdown
# Test Suite Trimming Counts

Baseline collected tests: 3286

| Pass | Area | Before | After | Delta | Notes |
| --- | --- | ---: | ---: | ---: | --- |
| 1 | Integration wrappers |  |  |  |  |
| 2 | Template wording locks |  |  |  |  |
| 3 | Presets/extensions |  |  |  |  |
| 4 | Hooks/contracts/scripts |  |  |  |  |
| 5 | Codex team cleanup |  |  |  |  |
```

Use the actual baseline value if Step 1 differs.

- [ ] **Step 4: Commit only if an accounting file was created**

Run:

```powershell
git status --short
```

If `docs/superpowers/plans/2026-05-21-test-suite-trimming-counts.md` exists, run:

```powershell
git add docs/superpowers/plans/2026-05-21-test-suite-trimming-counts.md
git commit -m "docs: record test trimming baseline"
```

Expected: either no commit is needed, or one docs-only commit is created.

## Task 2: Delete Redundant Integration Wrapper Matrix

**Files:**
- Delete: `tests/integrations/test_integration_amp.py`
- Delete: `tests/integrations/test_integration_auggie.py`
- Delete: `tests/integrations/test_integration_bob.py`
- Delete: `tests/integrations/test_integration_codebuddy.py`
- Delete: `tests/integrations/test_integration_iflow.py`
- Delete: `tests/integrations/test_integration_junie.py`
- Delete: `tests/integrations/test_integration_kilocode.py`
- Delete: `tests/integrations/test_integration_pi.py`
- Delete: `tests/integrations/test_integration_qodercli.py`
- Delete: `tests/integrations/test_integration_qwen.py`
- Delete: `tests/integrations/test_integration_roo.py`
- Delete: `tests/integrations/test_integration_shai.py`
- Delete: `tests/integrations/test_integration_windsurf.py`
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_registry.py`

Keep these integration files for representative or special behavior:

- `tests/integrations/test_integration_base_markdown.py`
- `tests/integrations/test_integration_base_skills.py`
- `tests/integrations/test_integration_base_toml.py`
- `tests/integrations/test_integration_claude.py`
- `tests/integrations/test_integration_codex.py`
- `tests/integrations/test_integration_copilot.py`
- `tests/integrations/test_integration_cursor_agent.py`
- `tests/integrations/test_integration_forge.py`
- `tests/integrations/test_integration_gemini.py`
- `tests/integrations/test_integration_generic.py`
- `tests/integrations/test_integration_kimi.py`
- `tests/integrations/test_integration_kiro_cli.py`
- `tests/integrations/test_integration_opencode.py`
- `tests/integrations/test_integration_subcommand.py`
- `tests/integrations/test_integration_tabnine.py`
- `tests/integrations/test_integration_trae.py`
- `tests/integrations/test_integration_vibe.py`
- `tests/integrations/test_integration_agy.py`

- [ ] **Step 1: Delete plain wrapper files**

Delete these files:

```text
tests/integrations/test_integration_amp.py
tests/integrations/test_integration_auggie.py
tests/integrations/test_integration_bob.py
tests/integrations/test_integration_codebuddy.py
tests/integrations/test_integration_iflow.py
tests/integrations/test_integration_junie.py
tests/integrations/test_integration_kilocode.py
tests/integrations/test_integration_pi.py
tests/integrations/test_integration_qodercli.py
tests/integrations/test_integration_qwen.py
tests/integrations/test_integration_roo.py
tests/integrations/test_integration_shai.py
tests/integrations/test_integration_windsurf.py
```

They only inherit `MarkdownIntegrationTests`, and `tests/integrations/test_registry.py` already checks that all integration keys are registered.

Use `apply_patch` with one delete hunk per file.

- [ ] **Step 2: Replace all-Markdown deep parametrization with representative keys**

In `tests/integrations/test_integration_base_markdown.py`, replace:

```python
MARKDOWN_INTEGRATION_KEYS = sorted(
    key
    for key, integration in INTEGRATION_REGISTRY.items()
    if isinstance(integration, MarkdownIntegration) and key != "generic"
)
```

with:

```python
MARKDOWN_INTEGRATION_SAMPLE_KEYS = ("claude", "opencode", "kiro-cli")
```

Then update the two parametrized tests near the top:

```python
@pytest.mark.parametrize("integration_key", MARKDOWN_INTEGRATION_KEYS)
```

to:

```python
@pytest.mark.parametrize("integration_key", MARKDOWN_INTEGRATION_SAMPLE_KEYS)
```

Expected: broad Markdown template contracts still run for Claude as a rich representative, opencode as the singular directory representative, and Kiro as a prompt-directory representative.

- [ ] **Step 3: Strengthen registry metadata coverage for deleted wrappers**

In `tests/integrations/test_registry.py`, add this test to `TestRegistrarKeyAlignment`:

```python
    @pytest.mark.parametrize(
        ("key", "folder", "commands_subdir"),
        [
            ("amp", ".agents/", "commands"),
            ("auggie", ".augment/", "commands"),
            ("bob", ".bob/", "commands"),
            ("codebuddy", ".codebuddy/", "commands"),
            ("iflow", ".iflow/", "commands"),
            ("junie", ".junie/", "commands"),
            ("kilocode", ".kilocode/", "workflows"),
            ("pi", ".pi/", "prompts"),
            ("qodercli", ".qoder/", "commands"),
            ("qwen", ".qwen/", "commands"),
            ("roo", ".roo/", "commands"),
            ("shai", ".shai/", "commands"),
            ("windsurf", ".windsurf/", "workflows"),
        ],
    )
    def test_reduced_markdown_matrix_preserves_agent_metadata(self, key, folder, commands_subdir):
        integration = get_integration(key)

        assert integration is not None
        assert integration.config["folder"] == folder
        assert integration.config["commands_subdir"] == commands_subdir
```

Expected: each deleted wrapper still has metadata coverage without rerunning the full inherited mixin.

- [ ] **Step 4: Run integration collection**

Run:

```powershell
uv run pytest --collect-only -q tests/integrations
```

Expected: collection succeeds. The integration test count should drop substantially.

- [ ] **Step 5: Run the reduced integration representative set**

Run:

```powershell
uv run pytest -q tests/integrations/test_registry.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_opencode.py tests/integrations/test_integration_kiro_cli.py
```

Expected: all selected tests pass.

- [ ] **Step 6: Commit integration wrapper deletion**

Run:

```powershell
git add tests/integrations
git commit -m "test: trim redundant markdown integration wrappers"
```

Expected: one commit removes the duplicate wrapper files and keeps metadata coverage.

## Task 3: Trim Skills and TOML Integration Matrix

**Files:**
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Optional delete: `tests/integrations/test_integration_tabnine.py`
- Keep: `tests/integrations/test_integration_codex.py`
- Keep: `tests/integrations/test_integration_agy.py`
- Keep: `tests/integrations/test_integration_trae.py`
- Keep: `tests/integrations/test_integration_vibe.py`
- Keep: `tests/integrations/test_integration_gemini.py`

- [ ] **Step 1: Replace all-skills deep parametrization with representative keys**

In `tests/integrations/test_integration_base_skills.py`, replace:

```python
SKILLS_INTEGRATION_KEYS = sorted(
    key
    for key, integration in INTEGRATION_REGISTRY.items()
    if isinstance(integration, SkillsIntegration)
)
```

with:

```python
SKILLS_INTEGRATION_SAMPLE_KEYS = ("codex", "agy", "vibe")
```

Then replace both decorators:

```python
@pytest.mark.parametrize("integration_key", SKILLS_INTEGRATION_KEYS)
```

with:

```python
@pytest.mark.parametrize("integration_key", SKILLS_INTEGRATION_SAMPLE_KEYS)
```

Expected: Codex covers dedicated Codex skills, Agy covers shared `.agents/skills`, and Vibe covers a dedicated skills directory.

- [ ] **Step 2: Replace all-TOML deep parametrization with representative key**

In `tests/integrations/test_integration_base_toml.py`, replace:

```python
TOML_INTEGRATION_KEYS = sorted(
    key
    for key, integration in INTEGRATION_REGISTRY.items()
    if isinstance(integration, TomlIntegration)
)
```

with:

```python
TOML_INTEGRATION_SAMPLE_KEYS = ("gemini",)
```

Then replace both decorators:

```python
@pytest.mark.parametrize("integration_key", TOML_INTEGRATION_KEYS)
```

with:

```python
@pytest.mark.parametrize("integration_key", TOML_INTEGRATION_SAMPLE_KEYS)
```

Expected: Gemini remains the TOML format representative; parser-specific TOML tests still run in the same file.

- [ ] **Step 3: Decide whether to delete the Tabnine wrapper**

If `tests/integrations/test_registry.py` already checks `tabnine` registration and config through `CommandRegistrar.AGENT_CONFIGS`, delete `tests/integrations/test_integration_tabnine.py`.

If extra explicit metadata is needed, add this case to a metadata parametrization in `tests/integrations/test_registry.py`:

```python
("tabnine", ".tabnine/agent/", "commands")
```

Expected: Tabnine remains represented by registry/config coverage rather than full TOML mixin execution.

- [ ] **Step 4: Run format-family integration tests**

Run:

```powershell
uv run pytest -q tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_agy.py tests/integrations/test_integration_vibe.py tests/integrations/test_integration_gemini.py
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit skills/TOML matrix reduction**

Run:

```powershell
git add tests/integrations
git commit -m "test: sample skills and toml integration matrices"
```

Expected: one commit reduces full-matrix execution while preserving representative integration families.

## Task 4: Reduce Integration CLI and Special-Agent Duplication

**Files:**
- Modify: `tests/integrations/test_cli.py`
- Modify: `tests/integrations/test_integration_claude.py`
- Modify: `tests/integrations/test_integration_codex.py`
- Modify: `tests/integrations/test_integration_gemini.py`
- Keep focused: `tests/integrations/test_integration_copilot.py`
- Keep focused: `tests/integrations/test_integration_forge.py`
- Keep focused: `tests/integrations/test_integration_generic.py`

- [ ] **Step 1: In `tests/integrations/test_cli.py`, keep only representative `init` CLI paths**

Keep tests that prove distinct CLI branches:

```text
test_integration_and_ai_mutually_exclusive
test_unknown_integration_rejected
test_integration_copilot_creates_files
test_ai_copilot_auto_promotes
test_ai_claude_here_preserves_preexisting_commands
test_codex_init_uses_plus_branded_visible_output
test_claude_init_uses_same_skill_surface_without_codex_runtime
test_cursor_init_uses_skills_surface_and_new_directory
test_vibe_init_uses_skills_surface_and_new_directory
test_init_directory_conflict_uses_normalized_error_surface
test_init_installs_brainstorming_truth_templates
test_init_installs_specify_draft_template
test_init_installs_shared_worker_prompt_templates
```

Delete tests that repeat the same init branch for additional non-special agents when a family representative remains.

Expected: `test_cli.py` still covers CLI user-visible branches but stops serving as a second full integration matrix.

- [ ] **Step 2: In `tests/integrations/test_integration_claude.py`, keep Claude-only behavior**

Keep tests for:

```text
hook asset installation and settings merge
hook dispatch adapter schema
uninstall preserving user settings
argument hint injection
Claude-generated skills surface
Claude preset creates skill without commands dir
```

Delete tests that only duplicate base skills or shared command-template checks already covered in `test_integration_base_skills.py`, `test_integration_codex.py`, or template tests.

Expected: Claude remains covered for its hook-heavy and skills-specific behavior, but not every shared generated template sentence.

- [ ] **Step 3: In `tests/integrations/test_integration_codex.py`, keep Codex-only behavior**

Keep tests for:

```text
Codex skills install layout
Codex team template/assets
Codex auto-promotion and skill flags
Codex team generated assets
```

Delete tests that duplicate base skills behavior or shared command content already represented by `test_integration_base_skills.py`.

- [ ] **Step 4: In `tests/integrations/test_integration_gemini.py`, keep Gemini TOML and hook-specific behavior**

Keep tests for:

```text
TOML output validity
Gemini hooks/scripts
Gemini CLI auto-promotion
```

Delete shared template wording checks covered by base TOML or workflow guidance tests.

- [ ] **Step 5: Run special-agent tests**

Run:

```powershell
uv run pytest -q tests/integrations/test_cli.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_gemini.py tests/integrations/test_integration_copilot.py tests/integrations/test_integration_forge.py tests/integrations/test_integration_generic.py
```

Expected: all selected tests pass.

- [ ] **Step 6: Commit special integration reduction**

Run:

```powershell
git add tests/integrations
git commit -m "test: keep focused special integration coverage"
```

Expected: one commit keeps special integration contracts and removes duplicate shared behavior checks.

## Task 5: Collapse Template and Guidance Wording Locks

**Files:**
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_specify_guidance_docs.py`
- Modify: `tests/test_quick_template_guidance.py`
- Modify: `tests/test_deep_research_template_guidance.py`
- Modify: `tests/test_map_scan_build_template_guidance.py`
- Modify: `tests/test_prd_scan_build_template_guidance.py`
- Modify: `tests/test_runtime_handbook_contract.py`
- Modify: `tests/test_subagent_mandatory_template_guidance.py`
- Keep helper: `tests/template_utils.py`

- [ ] **Step 1: Keep broad helper assertions in `test_alignment_templates.py`**

Retain helper assertions that express durable contracts:

```text
_assert_subagent_dispatch_contract
_assert_reference_evidence_contract
_assert_must_preserve_ledger_contract
_assert_senior_consequence_gate_contract
_assert_map_update_first_policy
_assert_no_stale_map_policy_phrases
```

Delete tests that only check one incidental phrase when one of these helper assertions covers the same behavior.

Expected: `test_alignment_templates.py` remains a compact contract file rather than a sentence-level lock file.

- [ ] **Step 2: Merge duplicate docs guidance assertions**

In `tests/test_specify_guidance_docs.py`, keep tests for distinct product surfaces:

```text
quickstart teaches specify -> plan
CLARIFY is optional enhancement
sp-deep-research handoff is optional and feeds plan
skill groups are documented
discussion boundary and handoff are documented
```

Delete tests that assert the same product-scope wording across README, quickstart, project handbook, and docs when one representative docs test remains.

- [ ] **Step 3: Trim workflow template guidance files**

For each of these files, keep only tests that protect a distinct workflow contract and delete sentence-level duplicates:

```text
tests/test_quick_template_guidance.py
tests/test_deep_research_template_guidance.py
tests/test_map_scan_build_template_guidance.py
tests/test_prd_scan_build_template_guidance.py
tests/test_runtime_handbook_contract.py
tests/test_subagent_mandatory_template_guidance.py
```

Use this rule: if a test name says the same thing as another test in the file and both read the same template, keep the broader test and delete the narrower one.

- [ ] **Step 4: Run template guidance subset**

Run:

```powershell
uv run pytest -q tests/test_alignment_templates.py tests/test_specify_guidance_docs.py tests/test_quick_template_guidance.py tests/test_deep_research_template_guidance.py tests/test_map_scan_build_template_guidance.py tests/test_prd_scan_build_template_guidance.py tests/test_runtime_handbook_contract.py tests/test_subagent_mandatory_template_guidance.py
```

Expected: all remaining tests pass.

- [ ] **Step 5: Commit template guidance reduction**

Run:

```powershell
git add tests/test_alignment_templates.py tests/test_specify_guidance_docs.py tests/test_quick_template_guidance.py tests/test_deep_research_template_guidance.py tests/test_map_scan_build_template_guidance.py tests/test_prd_scan_build_template_guidance.py tests/test_runtime_handbook_contract.py tests/test_subagent_mandatory_template_guidance.py
git commit -m "test: collapse template wording locks"
```

Expected: one commit removes low-value wording locks while retaining broad workflow contracts.

## Task 6: Trim Preset Tests to Manifest, Install, Registry, and Resolver Contracts

**Files:**
- Modify: `tests/test_presets.py`

- [ ] **Step 1: Preserve these preset test groups**

In `tests/test_presets.py`, keep tests covering:

```text
valid manifest loading
missing or invalid manifest file
required top-level fields
unsafe or invalid preset id/version
template file existence validation
registry add/get/list/remove behavior
manager install and remove happy path
conflict handling
catalog search
resolver priority stack: extension override, preset override, core fallback
CLI smoke for install/list/remove or equivalent user-visible surface
```

- [ ] **Step 2: Delete equivalent manifest permutation tests**

Delete tests that only remove one required field at a time after at least one representative required-field failure remains for each schema level:

```text
schema_version
preset metadata
requires.speckit_version
provides.templates
template entry file/type/name
```

Keep one test per schema level, not one per leaf field.

- [ ] **Step 3: Delete repeated file-list and metadata assertions**

Delete tests that assert every copied file or every metadata field when another test already proves install/remove and manifest parsing. Keep one representative copied-template assertion.

- [ ] **Step 4: Run preset tests**

Run:

```powershell
uv run pytest -q tests/test_presets.py
```

Expected: all remaining preset tests pass.

- [ ] **Step 5: Commit preset reduction**

Run:

```powershell
git add tests/test_presets.py
git commit -m "test: trim preset permutation coverage"
```

Expected: one commit removes low-value preset permutations.

## Task 7: Trim Extension Tests to Manifest, Manager, Command, Hook, and Catalog Contracts

**Files:**
- Modify: `tests/test_extensions.py`

- [ ] **Step 1: Preserve these extension test groups**

In `tests/test_extensions.py`, keep tests covering:

```text
CORE_COMMAND_NAMES alignment with bundled templates
valid manifest loading
missing or invalid manifest file
unsafe extension id/version
command registration behavior
manager install/remove happy path
conflict handling
hook executor behavior
catalog stack behavior
extension ignore behavior
CLI smoke for install/list/remove or equivalent user-visible surface
```

- [ ] **Step 2: Delete equivalent helper permutations**

For `normalize_priority`, keep:

```python
def test_normalize_priority_accepts_positive_integer():
    assert normalize_priority(5) == 5

def test_normalize_priority_uses_default_for_invalid_values():
    assert normalize_priority(0) == 10
    assert normalize_priority(-1) == 10
    assert normalize_priority(None) == 10
    assert normalize_priority("invalid") == 10
```

Delete separate tests for string numbers, floats, empty strings, and custom defaults unless production behavior depends on those exact cases.

- [ ] **Step 3: Delete equivalent manifest permutations**

Keep one representative failure per schema level and delete one-test-per-leaf-field variants.

- [ ] **Step 4: Delete repeated install file-list assertions**

Keep one install happy path and one conflict path. Delete tests that repeat all copied files or metadata fields without asserting distinct behavior.

- [ ] **Step 5: Run extension tests**

Run:

```powershell
uv run pytest -q tests/test_extensions.py
```

Expected: all remaining extension tests pass.

- [ ] **Step 6: Commit extension reduction**

Run:

```powershell
git add tests/test_extensions.py
git commit -m "test: trim extension permutation coverage"
```

Expected: one commit removes low-value extension permutations.

## Task 8: Reduce Hook and Contract Variant Tests

**Files:**
- Modify: `tests/contract/test_hook_cli_surface.py`
- Modify: `tests/hooks/test_artifact_hooks.py`
- Modify: `tests/hooks/test_preflight_hooks.py`
- Modify if needed: `tests/hooks/test_state_hooks.py`
- Modify if needed: `tests/hooks/test_workflow_policy_hooks.py`

- [ ] **Step 1: Keep hook CLI JSON surfaces**

In `tests/contract/test_hook_cli_surface.py`, keep tests for parseable JSON from:

```text
hook validate-state
hook preflight
hook checkpoint
hook validate-artifacts
hook validate-packet
hook monitor-context
hook validate-prompt
hook validate-commit
hook workflow-policy
hook build-compaction
hook review-learning
hook signal-learning
hook complete-refresh
hook capture-learning
```

Delete duplicate tests that only prove the same command accepts both an alias and a long spelling, after one alias contract remains.

- [ ] **Step 2: Keep representative artifact fail-closed cases**

In `tests/hooks/test_artifact_hooks.py`, keep one missing/malformed/unsafe/clean case for these workflows:

```text
specify
clarify
plan
tasks
deep-research
constitution
prd
prd-scan
prd-build
map-scan
map-build
map-update
```

Delete repeated variants that only change a missing field name, stage enum variant, or wording detail when the same validator branch remains covered.

- [ ] **Step 3: Keep only distinct preflight categories**

In `tests/hooks/test_preflight_hooks.py`, keep one git-backed case for:

```text
clean pass
dirty project cognition advisory
support drift copy
path index gap routing
baseline rebuild routing
```

Delete repeated git initialization scenarios that differ only in fixture prose or alternate file names.

- [ ] **Step 4: Run hook and contract subset**

Run:

```powershell
uv run pytest -q tests/contract/test_hook_cli_surface.py tests/hooks/test_artifact_hooks.py tests/hooks/test_preflight_hooks.py tests/hooks/test_state_hooks.py tests/hooks/test_workflow_policy_hooks.py
```

Expected: all remaining tests pass.

- [ ] **Step 5: Commit hook/contract reduction**

Run:

```powershell
git add tests/contract/test_hook_cli_surface.py tests/hooks/test_artifact_hooks.py tests/hooks/test_preflight_hooks.py tests/hooks/test_state_hooks.py tests/hooks/test_workflow_policy_hooks.py
git commit -m "test: reduce hook and contract variants"
```

Expected: one commit removes equivalent hook variants while retaining fail-closed coverage.

## Task 9: Trim Cross-Shell Script Combination Tests

**Files:**
- Modify: `tests/test_timestamp_branches.py`
- Modify: `tests/test_project_map_freshness_scripts.py`
- Modify if needed: `tests/test_agent_context_managed_block.py`
- Modify if needed: `tests/test_cursor_frontmatter.py`

- [ ] **Step 1: Keep core branch naming scenarios**

In `tests/test_timestamp_branches.py`, keep:

```text
timestamp branch creation
sequential branch creation with existing specs
four-digit sequential prefix
reject main branch
find feature dir by timestamp and sequential prefix
explicit feature dir override for one shell
one end-to-end timestamp flow
one allow-existing flow
one dry-run JSON flow
one no-git dry-run flow
one PowerShell smoke for dry-run
one PowerShell smoke for feature path resolution
```

Delete cross-product duplicates such as every dry-run output/no-branch/no-dir/empty-repo/short-name/timestamp/number variant when one parser branch test remains.

- [ ] **Step 2: Keep project-map freshness script parity smoke**

In `tests/test_project_map_freshness_scripts.py`, keep:

```text
Bash check reads canonical status
PowerShell check reads canonical status
Bash record/complete refresh writes canonical state
PowerShell record/complete refresh writes canonical state
dirty topic order is stable
one parameterized path classification sample for live, support, and ignored paths
```

Delete large parity matrices after one Bash and one PowerShell contract proves equivalent behavior.

- [ ] **Step 3: Run script tests**

Run:

```powershell
uv run pytest -q tests/test_timestamp_branches.py tests/test_project_map_freshness_scripts.py tests/test_agent_context_managed_block.py tests/test_cursor_frontmatter.py
```

Expected: all remaining tests pass, with shell availability skips unchanged.

- [ ] **Step 4: Commit script combination reduction**

Run:

```powershell
git add tests/test_timestamp_branches.py tests/test_project_map_freshness_scripts.py tests/test_agent_context_managed_block.py tests/test_cursor_frontmatter.py
git commit -m "test: trim cross-shell script combinations"
```

Expected: one commit reduces subprocess-heavy script combinations.

## Task 10: Carefully Trim Codex Team Variants if Count Is Still Above Target

**Files:**
- Modify if needed: `tests/codex_team/test_auto_dispatch.py`
- Modify if needed: `tests/codex_team/test_runtime_bridge.py`
- Modify if needed: `tests/codex_team/test_task_ops.py`
- Modify if needed: `tests/codex_team/test_agent_teams_executor.py`
- Modify if needed: `tests/contract/test_codex_team_auto_dispatch_cli.py`
- Modify if needed: `tests/contract/test_codex_team_cli_api_surface.py`
- Modify if needed: `tests/contract/test_codex_team_cli_surface.py`

- [ ] **Step 1: Check current collection count before trimming Codex team**

Run:

```powershell
uv run pytest --collect-only -q
```

Expected: if collected tests are already between 1,200 and 1,600, skip this task and do not trim Codex team.

- [ ] **Step 2: Preserve state-machine tests**

Do not delete tests that cover:

```text
invalid task transitions
claim conflicts
result submission validation
dispatch record corruption
missing structured worker result
runtime backend detection user guidance
team CLI/API JSON payloads
```

- [ ] **Step 3: Delete only equivalent Codex team variants**

Delete tests that differ only by:

```text
minor metadata field
alternate message wording
mocked backend availability combination with identical user-visible result
end-to-end dispatch path already covered by lower-level transition and CLI/API tests
```

When in doubt, keep the Codex team test. This is the highest-risk area in the reduction plan.

- [ ] **Step 4: Run Codex team tests**

Run:

```powershell
uv run pytest -q tests/codex_team tests/contract/test_codex_team_auto_dispatch_cli.py tests/contract/test_codex_team_cli_api_surface.py tests/contract/test_codex_team_cli_surface.py
```

Expected: all remaining Codex team tests pass.

- [ ] **Step 5: Commit Codex team reduction if any files changed**

Run:

```powershell
git status --short
```

If Codex team files changed, run:

```powershell
git add tests/codex_team tests/contract/test_codex_team_auto_dispatch_cli.py tests/contract/test_codex_team_cli_api_surface.py tests/contract/test_codex_team_cli_surface.py
git commit -m "test: trim redundant codex team variants"
```

Expected: no commit is made if no Codex team trimming was needed.

## Task 11: Final Collection, Full Suite, and Risk Audit

**Files:**
- Read: all modified test files
- Optional update: `docs/superpowers/plans/2026-05-21-test-suite-trimming-counts.md`

- [ ] **Step 1: Confirm final collected test count**

Run:

```powershell
uv run pytest --collect-only -q
```

Expected: the final count is between 1,200 and 1,600. If it is above 1,600, identify the next largest low-risk family and repeat the relevant trimming task. If it is below 1,200, review whether high-risk contracts were over-deleted.

- [ ] **Step 2: Run the full reduced suite**

Run:

```powershell
uv run pytest -q
```

Expected: all remaining tests pass. If failures occur, fix only the failing reduced tests or restore a necessary helper; do not edit production code unless a dead test helper import is the only issue.

- [ ] **Step 3: Verify representative integration coverage remains**

Run:

```powershell
uv run pytest -q tests/integrations/test_registry.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_copilot.py tests/integrations/test_integration_forge.py tests/integrations/test_integration_generic.py tests/integrations/test_integration_codex.py
```

Expected: all pass.

- [ ] **Step 4: Verify hook fail-closed coverage remains**

Run:

```powershell
uv run pytest -q tests/contract/test_hook_cli_surface.py tests/hooks/test_artifact_hooks.py tests/hooks/test_preflight_hooks.py
```

Expected: all pass.

- [ ] **Step 5: Review git diff for accidental production changes**

Run:

```powershell
git diff --stat HEAD
git diff --name-only HEAD
```

Expected: changed files are test files and optional accounting docs only.

- [ ] **Step 6: Commit final accounting if changed**

If `docs/superpowers/plans/2026-05-21-test-suite-trimming-counts.md` was updated, run:

```powershell
git add docs/superpowers/plans/2026-05-21-test-suite-trimming-counts.md
git commit -m "docs: summarize test suite trimming results"
```

Expected: the final accounting documents baseline, final count, and removed families.

## Self-Review

Spec coverage:

- Aggressive deletion target is covered by Tasks 2-10 and final count gate in Task 11.
- Representative integration matrix is covered by Tasks 2-4 and Task 11 Step 3.
- Template wording reduction is covered by Task 5.
- Preset/extension trimming is covered by Tasks 6-7.
- Hook fail-closed retention is covered by Task 8 and Task 11 Step 4.
- Script combination trimming is covered by Task 9.
- Codex team caution is covered by Task 10.

Placeholder scan:

- The plan contains no unfinished markers or unspecified implementation placeholders.
- Optional steps are explicit and conditional on observed collection count or whether an accounting file exists.

Type and path consistency:

- All paths are repository-relative.
- Commands use PowerShell syntax because the active shell is PowerShell.
- Commit boundaries match the deletion waves.
