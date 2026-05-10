# CLI Install Path and Passive Skills Alignment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align new downstream installs for `agy`, `cursor-agent`, `trae`, and `vibe` to the approved skills directories, keep `codex` on `.codex/skills`, and close any real passive-skill misses in init, extension, preset, tests, and docs.

**Architecture:** Treat integration config as the primary path truth, then update shared skills-directory discovery and the affected skills-based consumers to follow those paths. `agy` stays a skills-based integration with a directory move; `cursor-agent`, `trae`, and `vibe` must be promoted from command/prompt-backed integrations to `SkillsIntegration` so passive bundled skills can install into their target directories without compatibility shims.

**Tech Stack:** Python 3.11+, Typer CLI, pytest, existing `IntegrationBase` / `SkillsIntegration` framework, Markdown docs

---

## File Structure

### Runtime files

- `src/specify_cli/integrations/agy/__init__.py`
  - Owns Antigravity integration config and skills install metadata.
- `src/specify_cli/integrations/cursor_agent/__init__.py`
  - Currently owns Cursor command-mode integration behavior and must become a skills-based integration.
- `src/specify_cli/integrations/trae/__init__.py`
  - Currently owns Trae markdown/rules integration behavior and must become a skills-based integration.
- `src/specify_cli/integrations/vibe/__init__.py`
  - Currently owns Vibe markdown/prompts integration behavior and must become a skills-based integration while preserving Vibe-specific post-processing.
- `src/specify_cli/__init__.py`
  - Owns `_get_skills_dir()`, `DEFAULT_SKILLS_DIR`, and init output text that reports installed skill locations.
- `src/specify_cli/extensions.py`
  - Owns extension skill registration and fallback cleanup across agent skills directories.
- `src/specify_cli/presets.py`
  - Owns preset skill overwrite/restore behavior against detected skills directories.

### Tests

- `tests/integrations/test_integration_agy.py`
  - Asserts Agy path config and init output.
- `tests/integrations/test_integration_cursor_agent.py`
  - Currently asserts command-mode Cursor behavior and must be rewritten to skills-mode expectations.
- `tests/integrations/test_integration_trae.py`
  - Must assert Trae skills-mode expectations.
- `tests/integrations/test_integration_vibe.py`
  - Must assert Vibe skills-mode expectations and preserved `user-invocable` frontmatter.
- `tests/test_agent_config_consistency.py`
  - Holds cross-surface path assertions for AGENT_CONFIG and registrar config.
- `tests/test_extensions.py`
  - Holds shared registrar assertions and Codex/Amp separation regression checks.
- `tests/test_presets.py`
  - Holds preset restore behavior, including the Agy skills directory assertion.

### Docs

- `README.md`
  - Teaches users where skills-based integrations install.
- `AGENTS.md`
  - Documents supported agent directories and product conventions in this repository.

## Task 1: Lock Path Expectations With Failing Tests

**Files:**
- Modify: `tests/integrations/test_integration_agy.py`
- Modify: `tests/integrations/test_integration_cursor_agent.py`
- Modify: `tests/integrations/test_integration_trae.py`
- Modify: `tests/integrations/test_integration_vibe.py`
- Modify: `tests/test_agent_config_consistency.py`

- [ ] **Step 1: Rewrite the integration config expectations to the approved directory targets**

```python
class TestAgyIntegration(SkillsIntegrationTests):
    KEY = "agy"
    FOLDER = ".agents/"
    COMMANDS_SUBDIR = "skills"
    REGISTRAR_DIR = ".agents/skills"
    CONTEXT_FILE = "AGENTS.md"


class TestCursorAgentIntegration(SkillsIntegrationTests):
    KEY = "cursor-agent"
    FOLDER = ".cursor/"
    COMMANDS_SUBDIR = "skills"
    REGISTRAR_DIR = ".cursor/skills"
    CONTEXT_FILE = ".cursor/rules/specify-rules.mdc"


class TestTraeIntegration(SkillsIntegrationTests):
    KEY = "trae"
    FOLDER = ".trae/"
    COMMANDS_SUBDIR = "skills"
    REGISTRAR_DIR = ".trae/skills"
    CONTEXT_FILE = ".trae/rules/project_rules.md"


class TestVibeIntegration(SkillsIntegrationTests):
    KEY = "vibe"
    FOLDER = ".vibe/"
    COMMANDS_SUBDIR = "skills"
    REGISTRAR_DIR = ".vibe/skills"
    CONTEXT_FILE = "AGENTS.md"
```

- [ ] **Step 2: Update the path-specific test bodies to assert the new install locations**

```python
def test_ai_agy_without_ai_skills_auto_promotes(self, tmp_path):
    ...
    assert (target / ".agents" / "skills" / "sp-plan" / "SKILL.md").exists()


def test_cursor_skills_init_writes_workflow_skills(tmp_path):
    ...
    assert (target / ".cursor" / "skills" / "sp-plan" / "SKILL.md").exists()
    assert (target / ".cursor" / "skills" / "spec-kit-workflow-routing" / "SKILL.md").exists()


def test_vibe_skills_init_writes_passive_skills(tmp_path):
    ...
    assert (target / ".vibe" / "skills" / "sp-plan" / "SKILL.md").exists()
    assert (target / ".vibe" / "skills" / "dispatching-parallel-agents" / "SKILL.md").exists()
```

- [ ] **Step 3: Replace command-mode Cursor assertions with skills-mode assertions**

```python
def test_cursor_skills_project_contains_quick_skill(tmp_path):
    ...
    skill_path = target / ".cursor" / "skills" / "sp-quick" / "SKILL.md"
    content = skill_path.read_text(encoding="utf-8").lower()

    assert ".specify/memory/constitution.md" in content
    assert "execution model: `subagents-first`" in content
    assert "cursor subagent dispatch contract" in content or "subagent dispatch contract" in content
```

- [ ] **Step 4: Update the shared config consistency assertions**

```python
def test_trae_in_agent_config(self):
    assert AGENT_CONFIG["trae"]["folder"] == ".trae/"
    assert AGENT_CONFIG["trae"]["commands_subdir"] == "skills"


def test_trae_in_extension_registrar(self):
    trae_cfg = CommandRegistrar.AGENT_CONFIGS["trae"]
    assert trae_cfg["dir"] == ".trae/skills"
    assert trae_cfg["extension"] == "/SKILL.md"
```

- [ ] **Step 5: Run the targeted tests to verify they fail against current code**

Run:

```bash
pytest tests/integrations/test_integration_agy.py tests/integrations/test_integration_cursor_agent.py tests/integrations/test_integration_trae.py tests/integrations/test_integration_vibe.py tests/test_agent_config_consistency.py -q
```

Expected: FAIL with path mismatches such as `.agent/skills`, `.cursor/commands`, `.trae/rules`, `.vibe/prompts`, or failures because `CursorAgentIntegration`, `TraeIntegration`, and `VibeIntegration` are still command-mode integrations.

- [ ] **Step 6: Commit the failing-test baseline**

```bash
git add tests/integrations/test_integration_agy.py tests/integrations/test_integration_cursor_agent.py tests/integrations/test_integration_trae.py tests/integrations/test_integration_vibe.py tests/test_agent_config_consistency.py
git commit -m "test: lock cli skill path expectations"
```

## Task 2: Move Agy and Promote Cursor/Trae/Vibe to Skills Integrations

**Files:**
- Modify: `src/specify_cli/integrations/agy/__init__.py`
- Modify: `src/specify_cli/integrations/cursor_agent/__init__.py`
- Modify: `src/specify_cli/integrations/trae/__init__.py`
- Modify: `src/specify_cli/integrations/vibe/__init__.py`

- [ ] **Step 1: Update Agy’s skills directory metadata**

```python
class AgyIntegration(SkillsIntegration):
    key = "agy"
    config = {
        "name": "Antigravity",
        "folder": ".agents/",
        "commands_subdir": "skills",
        "install_url": None,
        "requires_cli": False,
    }
    registrar_config = {
        "dir": ".agents/skills",
        "format": "markdown",
        "args": "$ARGUMENTS",
        "extension": "/SKILL.md",
    }
```

- [ ] **Step 2: Convert Cursor from `MarkdownIntegration` to `SkillsIntegration`**

```python
from ..base import IntegrationOption, SkillsIntegration


class CursorAgentIntegration(SkillsIntegration):
    key = "cursor-agent"
    config = {
        "name": "Cursor",
        "folder": ".cursor/",
        "commands_subdir": "skills",
        "install_url": None,
        "requires_cli": False,
    }
    registrar_config = {
        "dir": ".cursor/skills",
        "format": "markdown",
        "args": "$ARGUMENTS",
        "extension": "/SKILL.md",
    }
    context_file = ".cursor/rules/specify-rules.mdc"
    multi_install_safe = True

    @classmethod
    def options(cls) -> list[IntegrationOption]:
        return [
            IntegrationOption(
                "--skills",
                is_flag=True,
                default=True,
                help="Install as agent skills (recommended for Cursor)",
            ),
        ]
```

- [ ] **Step 3: Remove Cursor command-dir post-processing and preserve only behavior that still applies to skill files**

```python
def post_init_bootstrap(
    self,
    project_root: Path,
    manifest: IntegrationManifest,
) -> list[Path]:
    return []
```

Expected implementation note:
- delete `commands_dest()` consumers and `sp.quick.md` assumptions
- if any Cursor-specific augmentation is still required, retarget it to
  `skills_dest(project_root) / "sp-quick" / "SKILL.md"`
- do not keep `.cursor/commands` as a fallback path

- [ ] **Step 4: Convert Trae from `MarkdownIntegration` to `SkillsIntegration`**

```python
from ..base import IntegrationOption, SkillsIntegration


class TraeIntegration(SkillsIntegration):
    key = "trae"
    config = {
        "name": "Trae",
        "folder": ".trae/",
        "commands_subdir": "skills",
        "install_url": None,
        "requires_cli": False,
    }
    registrar_config = {
        "dir": ".trae/skills",
        "format": "markdown",
        "args": "$ARGUMENTS",
        "extension": "/SKILL.md",
    }
    context_file = ".trae/rules/project_rules.md"
    multi_install_safe = True

    @classmethod
    def options(cls) -> list[IntegrationOption]:
        return [
            IntegrationOption(
                "--skills",
                is_flag=True,
                default=True,
                help="Install as agent skills (default for Trae)",
            ),
        ]
```

- [ ] **Step 5: Convert Vibe from `MarkdownIntegration` to `SkillsIntegration` and preserve Vibe-specific skill frontmatter injection**

```python
from ..base import IntegrationOption, SkillsIntegration


class VibeIntegration(SkillsIntegration):
    key = "vibe"
    config = {
        "name": "Mistral Vibe",
        "folder": ".vibe/",
        "commands_subdir": "skills",
        "install_url": "https://github.com/mistralai/mistral-vibe",
        "requires_cli": True,
    }
    registrar_config = {
        "dir": ".vibe/skills",
        "format": "markdown",
        "args": "$ARGUMENTS",
        "extension": "/SKILL.md",
    }
    context_file = "AGENTS.md"
```

Expected implementation note:
- keep `_inject_frontmatter_flag()`, `post_process_skill_content()`, and the
  `setup()` post-processing loop
- retarget that loop to `self.skills_dest(project_root)`
- keep the `user-invocable: true` assertion valid for all generated `SKILL.md`

- [ ] **Step 6: Run the moved integration tests to verify they now pass**

Run:

```bash
pytest tests/integrations/test_integration_agy.py tests/integrations/test_integration_cursor_agent.py tests/integrations/test_integration_trae.py tests/integrations/test_integration_vibe.py tests/test_agent_config_consistency.py -q
```

Expected: PASS

- [ ] **Step 7: Commit the integration migration**

```bash
git add src/specify_cli/integrations/agy/__init__.py src/specify_cli/integrations/cursor_agent/__init__.py src/specify_cli/integrations/trae/__init__.py src/specify_cli/integrations/vibe/__init__.py tests/integrations/test_integration_agy.py tests/integrations/test_integration_cursor_agent.py tests/integrations/test_integration_trae.py tests/integrations/test_integration_vibe.py tests/test_agent_config_consistency.py
git commit -m "feat: align skills install paths for agy cursor trae and vibe"
```

## Task 3: Align Shared Skills Directory Discovery Without Legacy Compatibility

**Files:**
- Modify: `src/specify_cli/__init__.py`

- [ ] **Step 1: Write a focused failing test for `_get_skills_dir()` path resolution**

```python
def test_get_skills_dir_uses_agent_config_for_moved_skill_agents(tmp_path):
    from specify_cli import _get_skills_dir

    assert _get_skills_dir(tmp_path, "agy") == tmp_path / ".agents" / "skills"
    assert _get_skills_dir(tmp_path, "cursor-agent") == tmp_path / ".cursor" / "skills"
    assert _get_skills_dir(tmp_path, "trae") == tmp_path / ".trae" / "skills"
    assert _get_skills_dir(tmp_path, "vibe") == tmp_path / ".vibe" / "skills"
    assert _get_skills_dir(tmp_path, "codex") == tmp_path / ".codex" / "skills"
```

- [ ] **Step 2: Run the focused test to verify the pre-change failure mode**

Run:

```bash
pytest tests/test_agent_config_consistency.py -q
```

Expected: FAIL if any moved integration still resolves through its old folder/subdir or if `codex` path handling regresses.

- [ ] **Step 3: Keep `_get_skills_dir()` config-driven and retain the Codex-only local fork**

```python
def _get_skills_dir(project_path: Path, selected_ai: str) -> Path:
    agent_config = AGENT_CONFIG.get(selected_ai, {})
    agent_folder = agent_config.get("folder", "")
    if agent_folder:
        preferred = project_path / agent_folder.rstrip("/") / "skills"
        if selected_ai == "codex":
            legacy = project_path / ".agents" / "skills"
            if not preferred.exists() and legacy.exists():
                return legacy
        return preferred
    return project_path / ".agents" / "skills"
```

Expected implementation note:
- the only compatibility exception that survives is the existing Codex local fork behavior
- do not add old-path fallbacks for `agy`, `cursor-agent`, `trae`, or `vibe`

- [ ] **Step 4: Run the same focused test again**

Run:

```bash
pytest tests/test_agent_config_consistency.py -q
```

Expected: PASS

- [ ] **Step 5: Commit the shared path-resolution update**

```bash
git add src/specify_cli/__init__.py tests/test_agent_config_consistency.py
git commit -m "fix: keep skills dir resolution aligned with moved agents"
```

## Task 4: Audit and Fix Extension Skill Registration and Cleanup

**Files:**
- Modify: `src/specify_cli/extensions.py`
- Modify: `tests/test_extensions.py`
- Modify: `tests/test_extension_skills.py`

- [ ] **Step 1: Add failing extension tests for a moved skills-based integration**

```python
def test_register_commands_for_all_agents_distinguishes_agy_from_amp(self, extension_dir, project_dir):
    skills_dir = project_dir / ".agents" / "skills"
    skills_dir.mkdir(parents=True)

    manifest = ExtensionManifest(extension_dir / "extension.yml")
    registrar = CommandRegistrar()
    registered = registrar.register_commands_for_all_agents(manifest, extension_dir, project_dir)

    assert "agy" in registered
    assert "amp" not in registered


def test_extension_skills_follow_cursor_skills_dir(project_dir, extension_dir):
    _create_init_options(project_dir, ai="cursor-agent", ai_skills=True)
    _create_skills_dir(project_dir, ai="cursor-agent")

    manager = ExtensionManager(project_dir)
    manager.install_from_directory(extension_dir, "0.1.0", register_commands=False)

    assert (project_dir / ".cursor" / "skills" / "sp-test-ext-hello" / "SKILL.md").exists()
```

- [ ] **Step 2: Run the extension-focused tests to verify current misses**

Run:

```bash
pytest tests/test_extensions.py tests/test_extension_skills.py -q
```

Expected: FAIL if extension skill registration still assumes the old moved paths or misses new skills-based agents in cleanup/discovery flows.

- [ ] **Step 3: Keep extension registration config-driven and ensure fallback scanning reaches the moved directories**

```python
candidate_dirs: set[Path] = set()
for cfg in AGENT_CONFIG.values():
    folder = cfg.get("folder", "")
    if folder:
        candidate_dirs.add(self.project_root / folder.rstrip("/") / "skills")
candidate_dirs.add(self.project_root / DEFAULT_SKILLS_DIR)
candidate_dirs.add(self.project_root / ".codex" / "skills")
```

Expected implementation note:
- this block already points in the right direction once agent config is corrected
- only change it if a real moved-path miss appears in tests
- do not add legacy scanning for `.agent/skills`, `.cursor/commands`, `.trae/rules`, or `.vibe/prompts`

- [ ] **Step 4: Update the registrar assertions that were tied to the old paths**

```python
def test_agy_agent_config_present(self):
    assert CommandRegistrar.AGENT_CONFIGS["agy"]["dir"] == ".agents/skills"
    assert CommandRegistrar.AGENT_CONFIGS["agy"]["extension"] == "/SKILL.md"
```

- [ ] **Step 5: Re-run the extension tests**

Run:

```bash
pytest tests/test_extensions.py tests/test_extension_skills.py -q
```

Expected: PASS

- [ ] **Step 6: Commit the extension-surface fixes**

```bash
git add src/specify_cli/extensions.py tests/test_extensions.py tests/test_extension_skills.py
git commit -m "fix: align extension skills with moved agent directories"
```

## Task 5: Audit and Fix Preset Skill Discovery and Restore

**Files:**
- Modify: `src/specify_cli/presets.py`
- Modify: `tests/test_presets.py`

- [ ] **Step 1: Add or rewrite preset tests so they target the new moved skills directories**

```python
def test_agy_skill_restored_on_preset_remove(self, project_dir, temp_dir):
    self._write_init_options(project_dir, ai="agy", ai_skills=True)
    skills_dir = project_dir / ".agents" / "skills"
    self._create_skill(skills_dir, "sp-specify", body="before override")
    ...


def test_cursor_preset_updates_skills_dir(self, project_dir, temp_dir):
    self._write_init_options(project_dir, ai="cursor-agent", ai_skills=True)
    skills_dir = project_dir / ".cursor" / "skills"
    self._create_skill(skills_dir, "sp-specify", body="before override")
    ...
    assert "preset body" in (skills_dir / "sp-specify" / "SKILL.md").read_text()
```

- [ ] **Step 2: Run the preset-focused tests to verify they fail against stale assumptions**

Run:

```bash
pytest tests/test_presets.py -q
```

Expected: FAIL where preset skill restore or overwrite still references `.agent/skills` or misses the newly promoted skills-based integrations.

- [ ] **Step 3: Keep preset discovery config-driven and patch only proven misses**

```python
skills_dir = _get_skills_dir(self.project_root, agent)
if not skills_dir.is_dir():
    return None
```

Expected implementation note:
- prefer fixing tests or path-specific assumptions over adding new branching
- if the shared helper already resolves the new paths, do not add extra preset-specific path tables

- [ ] **Step 4: Re-run the preset tests**

Run:

```bash
pytest tests/test_presets.py -q
```

Expected: PASS

- [ ] **Step 5: Commit the preset-surface fixes**

```bash
git add src/specify_cli/presets.py tests/test_presets.py
git commit -m "fix: align preset skills with moved agent directories"
```

## Task 6: Update User-Facing Path Documentation

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`

- [ ] **Step 1: Rewrite the path tables and prose to the approved downstream layout**

```markdown
| **Cursor** | `.cursor/skills/` | Markdown | N/A (IDE-based) | Cursor IDE (`--ai cursor-agent`) |
| **Trae** | `.trae/skills/` | Markdown | N/A (IDE-based) | Trae IDE |
| **Mistral Vibe** | `.vibe/skills/` | Markdown | `vibe` | Mistral Vibe CLI |
```

And:

```markdown
- Antigravity: `.agents/skills/`
- Codex: `.codex/skills/`
- Cursor: `.cursor/skills/`
- Trae: `.trae/skills/`
- Mistral Vibe: `.vibe/skills/`
```

- [ ] **Step 2: Preserve the explicit Codex local fork wording**

```markdown
For Codex and other skills-based integrations, the generated commands are installed in skills form. Codex now uses the dedicated `.codex/skills/` directory for generated skills.
```

Expected implementation note:
- do not rewrite README to say Codex uses `.agents/skills`
- do not document old directories as supported compatibility paths

- [ ] **Step 3: Run a targeted text scan to confirm no stale moved-path docs remain**

Run:

```bash
rg -n "\.agent/skills|\.cursor/commands|\.trae/rules|\.vibe/prompts" README.md AGENTS.md
```

Expected: no matches for active downstream layout guidance

- [ ] **Step 4: Commit the doc updates**

```bash
git add README.md AGENTS.md
git commit -m "docs: align agent skills path guidance"
```

## Task 7: Run Final Regression Verification

**Files:**
- Modify: none
- Test: `tests/integrations/test_integration_agy.py`
- Test: `tests/integrations/test_integration_cursor_agent.py`
- Test: `tests/integrations/test_integration_trae.py`
- Test: `tests/integrations/test_integration_vibe.py`
- Test: `tests/integrations/test_integration_codex.py`
- Test: `tests/integrations/test_integration_claude.py`
- Test: `tests/test_agent_config_consistency.py`
- Test: `tests/test_extensions.py`
- Test: `tests/test_extension_skills.py`
- Test: `tests/test_presets.py`

- [ ] **Step 1: Run the moved-integration and shared-path regression suite**

Run:

```bash
pytest tests/integrations/test_integration_agy.py tests/integrations/test_integration_cursor_agent.py tests/integrations/test_integration_trae.py tests/integrations/test_integration_vibe.py tests/test_agent_config_consistency.py tests/test_extensions.py tests/test_extension_skills.py tests/test_presets.py -q
```

Expected: PASS

- [ ] **Step 2: Run the protected baseline regressions for Claude and Codex**

Run:

```bash
pytest tests/integrations/test_integration_claude.py tests/integrations/test_integration_codex.py -q
```

Expected: PASS, proving `.claude/skills` and `.codex/skills` remain intact.

- [ ] **Step 3: Run a narrow CLI smoke test for downstream init output text**

Run:

```bash
pytest tests/integrations/test_cli.py -q
```

Expected: PASS for assertions that print `.claude/skills` and `.codex/skills`, with any moved-agent path assertions updated to their new directories.

- [ ] **Step 4: Review the final diff for unintended scope expansion**

Run:

```bash
git diff --stat HEAD~6..HEAD
git diff -- src/specify_cli/integrations/codex/__init__.py
```

Expected:
- the diff shows the four moved integrations, shared skills discovery, tests, and docs
- the Codex diff is empty

- [ ] **Step 5: Commit the final verification pass**

```bash
git add -A
git commit -m "test: verify cli skills path alignment"
```

## Self-Review

### Spec coverage

- `agy` path move is covered in Task 2 and verified in Tasks 1 and 7.
- `cursor-agent`, `trae`, and `vibe` promotion to skills integrations is covered in Task 2 and verified in Tasks 1 and 7.
- shared skills-directory discovery is covered in Task 3.
- extension passive-skill alignment is covered in Task 4.
- preset passive-skill alignment is covered in Task 5.
- docs alignment is covered in Task 6.
- `codex` local fork preservation and `claude` baseline preservation are verified in Task 7.

No spec requirement is left without a task.

### Placeholder scan

- No `TBD`, `TODO`, `implement later`, or “similar to Task N” placeholders remain.
- Each code-changing task includes concrete code or explicit implementation notes tied to exact files.
- Each verification step includes exact commands and expected outcomes.

### Type consistency

- Moved skills-based integrations consistently use `SkillsIntegration`, `commands_subdir = "skills"`, and `registrar_config["extension"] = "/SKILL.md"`.
- Protected baselines consistently remain `claude -> .claude/skills` and `codex -> .codex/skills`.
- The plan consistently treats old moved paths as unsupported after the change.
