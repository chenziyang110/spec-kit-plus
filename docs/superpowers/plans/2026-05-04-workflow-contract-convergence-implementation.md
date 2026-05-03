# Workflow Contract Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Converge Spec Kit Plus onto one enforced workflow contract for feature routing, lane recovery, user-visible command naming, and stale generated-runtime failure handling.

**Architecture:** Tighten the shared routing contract first so artifact workflows bind to the intended feature through explicit `feature-dir` or lane resolution instead of branch-first guesswork. Then expand generated-runtime diagnostics and repair behavior, converge templates and docs onto one visible command surface, and lock the contract with regression tests.

**Tech Stack:** Python 3.13+, Typer, Bash, PowerShell, pytest, ripgrep, Markdown templates and docs

---

## File Structure

### Shared Routing and Script Contract

- Modify: `scripts/bash/common.sh`
  - Keep Bash feature resolution behavior aligned with the formal precedence rules and any new compatibility markers needed by diagnostics.
- Modify: `scripts/powershell/common.ps1`
  - Keep PowerShell feature resolution aligned with the same contract and expose any markers used by compatibility checks.
- Modify: `scripts/bash/check-prerequisites.sh`
  - Enforce explicit-feature or lane-first routing expectations in the shared Bash prerequisite surface.
- Modify: `scripts/powershell/check-prerequisites.ps1`
  - Enforce the same contract for PowerShell and align failure text with the supported upgrade path.

### Workflow Templates and Command Surface

- Modify: `templates/commands/plan.md`
  - Ensure the planning contract uses explicit feature binding or lane resolution consistently and phrases current user-visible guidance only in the supported naming model.
- Modify: `templates/commands/tasks.md`
  - Preserve the same contract for task generation.
- Modify: `templates/commands/analyze.md`
  - Add the missing lane-first routing and explicit feature binding contract so analyze is no longer a routing exception.
- Modify: `templates/commands/implement.md`
  - Keep execution entry aligned with the same feature-binding and stale-runtime expectations.
- Modify: `templates/commands/specify.md`
  - Keep feature-creation guidance aligned with the supported `sp-specify` path and avoid any nonexistent `specify branch` mental model.
- Modify: `templates/passive-skills/spec-kit-project-learning/SKILL.md`
  - Align helper CLI examples with the real `review-learning` command surface.

### CLI Diagnostics and Repair

- Modify: `src/specify_cli/launcher.py`
  - Expand generated-runtime compatibility checks to cover the converged workflow contract, not only stale PowerShell prefix resolution.
- Modify: `src/specify_cli/__init__.py`
  - Ensure user-visible diagnostics, help, and repair-facing guidance match the current contract and expose any new compatibility failure details cleanly.

### Public Docs

- Modify: `README.md`
  - Remove or rewrite any active guidance that leaks old workflow naming or ambiguous feature-routing expectations.
- Modify: `docs/quickstart.md`
  - Align current-facing workflow guidance, helper examples, and stale-runtime recovery guidance with the converged contract.
- Modify: `docs/upgrade.md`
  - Teach the hard-fail plus `check` / `integration repair` upgrade path for stale generated assets.

### Tests

- Modify: `tests/test_alignment_templates.py`
  - Add or update template assertions for analyze-side lane resolution, the supported command surface, and the absence of unsupported helper parameters.
- Modify: `tests/test_timestamp_branches.py`
  - Extend routing tests for explicit feature directories, lane-state resolution, and any new stale-runtime markers in shared scripts.
- Modify: `tests/test_command_surface_semantics.py`
  - Lock the current command-surface rules and prevent old workflow naming from leaking back into active user-facing surfaces.
- Modify: `tests/test_launcher.py`
  - Add or update generated-runtime compatibility diagnostics coverage.
- Modify: `tests/integrations/test_cli.py`
  - Verify `lane resolve`, feature-dir overrides, and repair behavior from the CLI layer.
- Modify: `tests/integrations/test_integration_claude.py`
  - Keep generated asset expectations aligned with the converged contract for a markdown/skills integration.
- Modify: `tests/integrations/test_integration_base_markdown.py`
  - Ensure generated markdown-command surfaces use the current contract and current script markers.
- Modify: `tests/integrations/test_integration_base_skills.py`
  - Ensure generated skills surfaces use the current contract and helper examples.
- Modify: `tests/integrations/test_integration_base_toml.py`
  - Ensure generated TOML-command integrations remain aligned with the same contract.

---

### Task 1: Add failing tests for analyze-side lane routing and command-surface drift

**Files:**
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_command_surface_semantics.py`

- [ ] **Step 1: Add the failing analyze lane-resolution assertions**

In `tests/test_alignment_templates.py`, add this new test near the existing workflow-template contract assertions:

```python
def test_analyze_template_requires_lane_resolution_before_branch_guessing() -> None:
    content = _read("templates/commands/analyze.md")
    lowered = content.lower()

    assert "{{specify-subcmd:lane resolve --command analyze --ensure-worktree}}" in content
    assert "if `feature_dir` is not already explicit" in lowered
    assert "before guessing from branch-only context" in lowered
    assert "when lane resolution returns a materialized lane worktree" in lowered
```

- [ ] **Step 2: Add the failing command-surface assertions**

In `tests/test_command_surface_semantics.py`, add these tests:

```python
def test_readme_does_not_teach_specify_branch_as_a_real_command() -> None:
    readme = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "specify branch" not in readme


def test_upgrade_guide_uses_current_runtime_repair_language() -> None:
    content = (PROJECT_ROOT / "docs" / "upgrade.md").read_text(encoding="utf-8").lower()
    assert "specify check" in content
    assert "specify integration repair" in content
    assert "/speckit." not in content
```

- [ ] **Step 3: Run the focused tests to verify they fail**

Run:

```bash
uv run pytest tests/test_alignment_templates.py::test_analyze_template_requires_lane_resolution_before_branch_guessing tests/test_command_surface_semantics.py::test_readme_does_not_teach_specify_branch_as_a_real_command tests/test_command_surface_semantics.py::test_upgrade_guide_uses_current_runtime_repair_language -q
```

Expected: FAIL because `templates/commands/analyze.md` does not yet contain the lane-resolution contract and active docs may still leak old workflow naming.

- [ ] **Step 4: Commit the red-state tests**

```bash
git add tests/test_alignment_templates.py tests/test_command_surface_semantics.py
git commit -m "test: cover workflow contract convergence gaps"
```

---

### Task 2: Make analyze follow the same lane-first contract as plan and tasks

**Files:**
- Modify: `templates/commands/analyze.md`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Add the lane-resolution contract to analyze**

In `templates/commands/analyze.md`, inside `### 1. Initialize Analysis Context`, insert these bullets immediately after the `{SCRIPT}` setup paragraph:

```md
- If `FEATURE_DIR` is not already explicit, prefer `{{specify-subcmd:lane resolve --command analyze --ensure-worktree}}` before guessing from branch-only context.
- When lane resolution returns a materialized lane worktree, continue analysis from that isolated worktree context so downstream gate decisions stay attached to the same lane boundary.
```

- [ ] **Step 2: Keep analyze’s read-only contract explicit**

In the `## Operating Constraints` section of `templates/commands/analyze.md`, add this paragraph after the existing read-only statement:

```md
Analyze must not switch branches, implicitly check out a "correct" feature branch, or mutate git state in order to determine scope. If the active feature cannot be identified safely through explicit `FEATURE_DIR` binding or lane resolution, fail closed and tell the user how to repair routing.
```

- [ ] **Step 3: Run the focused template tests**

Run:

```bash
uv run pytest tests/test_alignment_templates.py::test_analyze_template_requires_lane_resolution_before_branch_guessing -q
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add templates/commands/analyze.md tests/test_alignment_templates.py
git commit -m "feat: make analyze follow lane-first routing"
```

---

### Task 3: Expand generated-runtime compatibility diagnostics for stale workflow contract assets

**Files:**
- Modify: `src/specify_cli/launcher.py`
- Modify: `tests/test_launcher.py`
- Modify: `tests/integrations/test_cli.py`

- [ ] **Step 1: Add the failing launcher diagnostic tests**

In `tests/test_launcher.py`, add a targeted compatibility test:

```python
def test_diagnose_runtime_flags_stale_analyze_template_and_learning_surface(tmp_path: Path) -> None:
    project_root = tmp_path
    (project_root / ".specify" / "scripts" / "powershell").mkdir(parents=True, exist_ok=True)
    (project_root / ".specify" / "scripts" / "powershell" / "common.ps1").write_text(
        "function Find-FeatureDirByPrefix {}\nFind-FeatureDirByPrefix -RepoRoot $repoRoot -BranchName $currentBranch\n",
        encoding="utf-8",
    )
    (project_root / ".specify" / "templates" / "commands").mkdir(parents=True, exist_ok=True)
    (project_root / ".specify" / "templates" / "commands" / "analyze.md").write_text(
        "Run scripts/powershell/check-prerequisites.ps1 -Json -RequireTasks -IncludeTasks\n",
        encoding="utf-8",
    )
    (project_root / ".specify" / "templates" / "passive-skills").mkdir(parents=True, exist_ok=True)
    (project_root / ".specify" / "templates" / "passive-skills" / "learning.md").write_text(
        "specify hook review-learning --command analyze --origin-artifact plan.md\n",
        encoding="utf-8",
    )

    issues = diagnose_project_runtime_compatibility(project_root)
    codes = {issue["code"] for issue in issues}

    assert "stale-analyze-lane-routing-template" in codes
    assert "stale-review-learning-command-surface" in codes
```

In `tests/integrations/test_cli.py`, add a CLI-facing expectation:

```python
def test_check_reports_workflow_contract_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project_root = tmp_path / "project"
    project_root.mkdir()
    (project_root / ".specify").mkdir()
    monkeypatch.chdir(project_root)
    # fixture helper should write stale generated assets here before invoking the app
```

Use the local CLI test helpers already present in the file to assert that `specify check` reports the new issue codes once the stale assets exist.

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
uv run pytest tests/test_launcher.py -k workflow_contract tests/integrations/test_cli.py -k workflow_contract -q
```

Expected: FAIL because `diagnose_project_runtime_compatibility()` does not yet inspect generated analyze templates or stale `review-learning` command examples.

- [ ] **Step 3: Extend `diagnose_project_runtime_compatibility()`**

In `src/specify_cli/launcher.py`, add generated-asset checks alongside the existing PowerShell resolver diagnostics:

```python
    generated_analyze = project_root / ".specify" / "templates" / "commands" / "analyze.md"
    generated_learning = project_root / ".specify" / "templates" / "passive-skills" / "learning.md"
```

Add checks that append issues with these codes when the generated assets are stale:

```python
                    "code": "stale-analyze-lane-routing-template",
                    "summary": "Generated analyze workflow guidance is stale and does not require lane resolution before branch-only fallback.",
                    "repair": "Run `specify integration repair` (or re-run `specify init --here --force --ai <agent>`) so generated workflow templates refresh to the current routing contract.",
```

```python
                    "code": "stale-review-learning-command-surface",
                    "summary": "Generated learning guidance still references unsupported `review-learning` helper options.",
                    "repair": "Run `specify integration repair` so generated workflow and passive-skill assets refresh to the current helper command surface.",
```

Use simple string checks first:

- analyze template missing `lane resolve --command analyze --ensure-worktree`
- generated learning/help content contains `--origin-artifact`

- [ ] **Step 4: Update CLI-facing expectations**

Adjust the relevant `specify check` CLI tests in `tests/integrations/test_cli.py` so they assert the new issue codes and repair text appear in the command output.

- [ ] **Step 5: Re-run the focused tests**

Run:

```bash
uv run pytest tests/test_launcher.py -k workflow_contract tests/integrations/test_cli.py -k workflow_contract -q
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/specify_cli/launcher.py tests/test_launcher.py tests/integrations/test_cli.py
git commit -m "feat: detect stale workflow contract runtime assets"
```

---

### Task 4: Align public docs and active templates with the supported command surface

**Files:**
- Modify: `README.md`
- Modify: `docs/quickstart.md`
- Modify: `docs/upgrade.md`
- Modify: `templates/commands/specify.md`
- Modify: `templates/passive-skills/spec-kit-project-learning/SKILL.md`
- Test: `tests/test_command_surface_semantics.py`
- Test: `tests/test_alignment_templates.py`

- [ ] **Step 1: Remove unsupported helper option guidance**

In `templates/passive-skills/spec-kit-project-learning/SKILL.md`, ensure helper examples use only the supported surface:

```md
- `{{specify-subcmd:hook review-learning --command <command-name> --terminal-status <status> ...}}`
```

and remove any generated or active example that mentions:

```md
--origin-artifact
```

- [ ] **Step 2: Keep feature-creation guidance on the supported path**

In `templates/commands/specify.md`, add a short explicit line in the setup area:

```md
- Treat `sp-specify` plus the generated create-feature script as the supported feature-creation path. Do not infer or recommend a separate `specify branch` command family.
```

- [ ] **Step 3: Rewrite current-facing upgrade guidance around hard-fail plus repair**

In `docs/upgrade.md`, add a short section under runtime launcher binding:

```md
### Workflow contract drift after CLI upgrades

If `specify check` reports stale generated workflow routing or stale helper command surfaces, treat that as a hard incompatibility rather than a warning. Run `specify integration repair` to refresh the generated assets before continuing with `sp-*` workflows.
```

Make the surrounding examples prefer:

```bash
specify check
specify integration repair
```

over telling users to continue running stale generated workflow assets.

- [ ] **Step 4: Keep README and quickstart free of nonexistent command families**

Scan `README.md` and `docs/quickstart.md` and remove any active instruction that teaches:

```text
specify branch
/speckit.
```

Historical references may remain only in low-signal archival design notes outside active operator guidance.

- [ ] **Step 5: Run the focused doc/template tests**

Run:

```bash
uv run pytest tests/test_command_surface_semantics.py tests/test_alignment_templates.py -q
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add README.md docs/quickstart.md docs/upgrade.md templates/commands/specify.md templates/passive-skills/spec-kit-project-learning/SKILL.md tests/test_command_surface_semantics.py tests/test_alignment_templates.py
git commit -m "docs: converge workflow command surface guidance"
```

---

### Task 5: Strengthen shared script and CLI tests around explicit feature binding and lane-state precedence

**Files:**
- Modify: `tests/test_timestamp_branches.py`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/integrations/test_cli.py`

- [ ] **Step 1: Add a focused explicit-feature-dir regression**

In `tests/test_timestamp_branches.py`, add this Bash-side test near `TestExplicitFeatureDirOverrides`:

```python
@requires_bash
def test_check_prerequisites_paths_only_keeps_explicit_feature_dir_over_branch_guess(tmp_path: Path):
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=tmp_path, check=True)
    subprocess.run(["git", "checkout", "-b", "033-provider-management-port"], cwd=tmp_path, check=True)
    scripts_dir = tmp_path / "scripts" / "bash"
    scripts_dir.mkdir(parents=True)
    shutil.copy(CHECK_PREREQUISITES, scripts_dir / "check-prerequisites.sh")
    shutil.copy(COMMON_SH, scripts_dir / "common.sh")
    (tmp_path / ".specify" / "specs" / "032-terminal-module-rewrite").mkdir(parents=True)

    result = run_check_prerequisites(
        tmp_path,
        "--json",
        "--paths-only",
        "--feature-dir",
        ".specify/specs/032-terminal-module-rewrite",
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["FEATURE_DIR"].endswith("/.specify/specs/032-terminal-module-rewrite")
```

- [ ] **Step 2: Add a lane-resolve CLI regression**

In `tests/integrations/test_cli.py`, add a test that:

- registers a lane bound to a feature dir
- calls `lane resolve --command analyze --feature-dir <dir> --ensure-worktree`
- asserts the response mode is `resume`
- asserts the response reason is `explicit-feature-dir`

Use the same style as the existing `lane resolve` CLI tests already in the file.

- [ ] **Step 3: Run the focused routing tests**

Run:

```bash
uv run pytest tests/test_timestamp_branches.py -k "explicit_feature_dir or feature_dir_over_branch" tests/integrations/test_cli.py -k "lane and analyze" -q
```

Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add tests/test_timestamp_branches.py tests/integrations/test_cli.py tests/test_alignment_templates.py
git commit -m "test: lock workflow feature binding precedence"
```

---

### Task 6: Run the contract regression suite and capture the final upgrade-safe state

**Files:**
- Modify: `src/specify_cli/launcher.py` if any last-mile fixes emerge from the full suite
- Modify: `README.md` or `docs/upgrade.md` only if the suite exposes remaining active guidance drift
- Test: all files touched in this plan

- [ ] **Step 1: Run the focused workflow-contract regression suite**

Run:

```bash
uv run pytest tests/test_alignment_templates.py tests/test_command_surface_semantics.py tests/test_timestamp_branches.py tests/test_launcher.py tests/integrations/test_cli.py -q
```

Expected: PASS

- [ ] **Step 2: Run the broader generated-surface integration checks**

Run:

```bash
uv run pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_claude.py -q
```

Expected: PASS

- [ ] **Step 3: If any failures expose remaining command-surface or routing drift, fix the minimal root cause and re-run the affected tests**

Use the smallest necessary fix in the touched source or template file. Do not broaden scope into unrelated workflow changes.

- [ ] **Step 4: Review the final diff**

Run:

```bash
git diff --stat
git diff
```

Expected: only workflow-routing contract, runtime diagnostics, doc convergence, and related tests are changed.

- [ ] **Step 5: Commit**

```bash
git add scripts/bash/common.sh scripts/powershell/common.ps1 scripts/bash/check-prerequisites.sh scripts/powershell/check-prerequisites.ps1 templates/commands/plan.md templates/commands/tasks.md templates/commands/analyze.md templates/commands/implement.md templates/commands/specify.md templates/passive-skills/spec-kit-project-learning/SKILL.md src/specify_cli/launcher.py src/specify_cli/__init__.py README.md docs/quickstart.md docs/upgrade.md tests/test_alignment_templates.py tests/test_command_surface_semantics.py tests/test_timestamp_branches.py tests/test_launcher.py tests/integrations/test_cli.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_claude.py
git commit -m "feat: converge workflow routing and command contracts"
```

---

## Self-Review

### Spec coverage

- Feature routing convergence is covered by Tasks 1, 2, 3, and 5.
- `sp-analyze` lane-first alignment is covered by Task 2 and verified again in Tasks 1 and 5.
- stale generated-runtime hard failure and repair guidance are covered by Task 3 and reinforced in Task 4.
- user-visible command-surface convergence is covered by Tasks 1 and 4.
- regression locking is covered by Tasks 1, 3, 5, and 6.

### Placeholder scan

- No `TODO`, `TBD`, or “implement later” placeholders remain.
- Every task lists exact files and concrete commands.
- The only “minimal fix if failures appear” guidance is constrained to the full-suite task and is paired with exact rerun commands.

### Type and contract consistency

- The plan uses one consistent feature-binding vocabulary: `feature-dir`, `lane resolve`, and “branch-first guesswork”.
- `review-learning` is consistently treated as supporting only `--command`, `--terminal-status`, `--decision`, and `--rationale`.
- The stale-runtime issue codes named in Task 3 are reused consistently in the tests and implementation instructions.
