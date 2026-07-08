# Lossless Workflow Skill Refactoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the seven core generated workflow skills into compact main files plus lossless references without changing workflow behavior or quality.

**Architecture:** Add a command-reference asset layer beside `templates/commands`. Skills-format integrations render compact `SKILL.md` files and processed `references/` sidecars; Markdown/TOML integrations inline the same processed references into single-file command output. Verification is layered: renderer tests, generated-output tests, repair/preset tests, packaging tests, and workflow coverage ledgers.

**Tech Stack:** Python, pytest, Typer integration tests, Markdown/TOML template rendering, Hatch force-includes, Spec Kit Plus integration manifests.

---

## File Structure

- Modify: `src/specify_cli/integrations/base.py`
  - Owns command reference discovery, reference rendering, unresolved-token validation, single-file inline rendering, skills sidecar installation, and safe missing-sidecar repair helper.
- Modify: `src/specify_cli/integrations/claude/__init__.py`
  - Keeps Claude hook repair behavior and calls the shared sidecar repair helper.
- Modify: `src/specify_cli/integrations/gemini/__init__.py`
  - Keeps Gemini hook repair behavior and calls the shared sidecar repair helper.
- Modify: `src/specify_cli/presets.py`
  - Restores missing safe sidecar references when preset restore regenerates a core workflow skill.
- Modify: `src/specify_cli/__init__.py`
  - Mirrors packaged `command-references` through shared infrastructure when core-pack assets are installed into generated projects.
- Modify: `pyproject.toml`
  - Adds `templates/command-references` to package force-includes.
- Create: `templates/command-references/discussion/`
- Create: `templates/command-references/specify/`
- Create: `templates/command-references/plan/`
- Create: `templates/command-references/tasks/`
- Create: `templates/command-references/implement/`
- Create: `templates/command-references/quick/`
- Create: `templates/command-references/debug/`
  - Each workflow directory contains `INDEX.md` and focused reference files.
- Modify: `templates/commands/discussion.md`
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/commands/implement.md`
- Modify: `templates/commands/quick.md`
- Modify: `templates/commands/debug.md`
  - Each remains the hot-path main-flow skeleton and keeps hard-gate summaries.
- Create: `tests/fixtures/command-reference-coverage/*.json`
  - One coverage ledger per migrated workflow.
- Modify: `tests/integrations/test_base.py`
  - Adds shared renderer and unresolved-token tests.
- Modify: `tests/integrations/test_integration_base_markdown.py`
  - Adds non-skills inline reference assertions.
- Modify: `tests/integrations/test_integration_base_toml.py`
  - Adds TOML inline reference assertions.
- Modify: `tests/integrations/test_integration_base_skills.py`
  - Adds sidecar, index, manifest, reachability, token, and all-skills matrix assertions.
- Modify: `tests/integrations/test_integration_subcommand.py`
  - Adds repair preservation and missing-sidecar restore coverage.
- Modify: `tests/test_alignment_templates.py`
  - Adds source-level reference metadata, reachability, coverage-ledger, packaging, and migrated-rule checks.

## Shared Constants

Use these workflow names consistently:

```python
COMMAND_REFERENCE_WORKFLOWS = frozenset(
    {
        "discussion",
        "specify",
        "plan",
        "tasks",
        "implement",
        "quick",
        "debug",
    }
)
```

Use this unresolved-token rule consistently:

```python
UNRESOLVED_RENDERER_TOKEN_RE = re.compile(
    r"\{SCRIPT\}|\{AGENT_SCRIPT\}|\{ARGS\}|__AGENT__|\{\{invoke:[^}]+}}"
)
```

---

### Task 1: Add Failing Tests For Command Reference Rendering Primitives

**Files:**
- Modify: `tests/integrations/test_base.py`
- Modify: `src/specify_cli/integrations/base.py`

- [ ] **Step 1: Add imports for path fixtures and TOML-safe assertions**

In `tests/integrations/test_base.py`, ensure these imports exist near the top:

```python
from pathlib import Path

import pytest
```

If `pytest` is already imported, add only `Path`.

- [ ] **Step 2: Add a fixture-style test for reference discovery**

Append this test under `class TestBasePrimitives`:

```python
    def test_command_reference_templates_are_discovered_from_workflow_stem(self, tmp_path, monkeypatch):
        refs_root = tmp_path / "command-references"
        workflow_refs = refs_root / "plan"
        workflow_refs.mkdir(parents=True)
        (workflow_refs / "INDEX.md").write_text(
            "# Plan References\n\n- [details](details.md): Trigger: planning detail\n",
            encoding="utf-8",
        )
        (workflow_refs / "details.md").write_text(
            "Trigger: when planning needs details\n\n"
            "Purpose: exercise discovery\n\n"
            "Preserved Contract: keep the plan rules\n",
            encoding="utf-8",
        )

        i = StubIntegration()
        monkeypatch.setattr(type(i), "shared_command_references_dir", lambda self: refs_root)

        assert [path.name for path in i.list_command_reference_templates("plan")] == [
            "INDEX.md",
            "details.md",
        ]
        assert i.list_command_reference_templates("specify") == []
```

- [ ] **Step 3: Add a failing test for owner-context reference rendering**

Append this test under `class TestBasePrimitives`:

```python
    def test_render_command_reference_uses_owner_template_context(self, tmp_path):
        command = tmp_path / "plan.md"
        command.write_text(
            "---\n"
            "description: Plan command\n"
            "scripts:\n"
            "  sh: scripts/bash/setup-plan.sh --json\n"
            "---\n\n"
            "# Plan\n\n"
            "Main body for __AGENT__ using {SCRIPT}, {ARGS}, and {{invoke:tasks}}.\n",
            encoding="utf-8",
        )
        reference = tmp_path / "references" / "details.md"
        reference.parent.mkdir()
        reference.write_text(
            "Trigger: when planning detail is needed\n\n"
            "Purpose: verify owner context\n\n"
            "Preserved Contract: preserve command substitutions\n\n"
            "Use {SCRIPT}, {ARGS}, __AGENT__, and {{invoke:tasks}} here.\n",
            encoding="utf-8",
        )

        rendered = IntegrationBase.render_command_reference_content(
            reference.read_text(encoding="utf-8"),
            owner_template_raw=command.read_text(encoding="utf-8"),
            owner_template_path=command,
            reference_path=reference,
            agent_name="stub",
            script_type="sh",
            arg_placeholder="$ARGUMENTS",
            project_root=tmp_path,
        )

        assert "scripts/bash/setup-plan.sh --json" in rendered
        assert "$ARGUMENTS" in rendered
        assert "__AGENT__" not in rendered
        assert "{SCRIPT}" not in rendered
        assert "{ARGS}" not in rendered
        assert "{{invoke:tasks}}" not in rendered
        assert "$sp-tasks" not in rendered
        assert "/sp.tasks" not in rendered
```

- [ ] **Step 4: Add a failing test for unresolved token validation**

Append this test under `class TestBasePrimitives`:

```python
    def test_validate_no_unresolved_renderer_tokens_reports_path(self, tmp_path):
        path = tmp_path / "references" / "details.md"
        path.parent.mkdir()
        path.write_text("Use {SCRIPT}\n", encoding="utf-8")

        with pytest.raises(ValueError, match=r"details\.md.*\{SCRIPT\}"):
            IntegrationBase.validate_no_unresolved_renderer_tokens(
                path.read_text(encoding="utf-8"),
                path,
            )
```

- [ ] **Step 5: Run the focused tests and verify they fail**

Run:

```powershell
python -m pytest tests/integrations/test_base.py::TestBasePrimitives::test_command_reference_templates_are_discovered_from_workflow_stem tests/integrations/test_base.py::TestBasePrimitives::test_render_command_reference_uses_owner_template_context tests/integrations/test_base.py::TestBasePrimitives::test_validate_no_unresolved_renderer_tokens_reports_path -q
```

Expected: FAIL because `list_command_reference_templates`, `render_command_reference_content`, and `validate_no_unresolved_renderer_tokens` do not exist.

- [ ] **Step 6: Commit the failing tests**

```powershell
git add tests/integrations/test_base.py
git commit -m "test: cover command reference rendering primitives"
```

### Task 2: Implement Shared Command Reference Rendering Primitives

**Files:**
- Modify: `src/specify_cli/integrations/base.py`
- Test: `tests/integrations/test_base.py`

- [ ] **Step 1: Add constants to `IntegrationBase`**

Inside `class IntegrationBase`, after `SUBAGENT_DISCOVERY_TRIGGERS`, add:

```python
    COMMAND_REFERENCE_WORKFLOWS = frozenset(
        {
            "discussion",
            "specify",
            "plan",
            "tasks",
            "implement",
            "quick",
            "debug",
        }
    )
    UNRESOLVED_RENDERER_TOKEN_RE = re.compile(
        r"\{SCRIPT\}|\{AGENT_SCRIPT\}|\{ARGS\}|__AGENT__|\{\{invoke:[^}]+}}"
    )
```

- [ ] **Step 2: Add command-reference directory lookup**

Below `shared_commands_dir`, add:

```python
    def shared_command_references_dir(self) -> Path | None:
        """Return path to shared command reference templates."""
        import inspect

        pkg_dir = Path(inspect.getfile(IntegrationBase)).resolve().parent.parent
        for candidate in [
            pkg_dir / "core_pack" / "command-references",
            pkg_dir.parent.parent / "templates" / "command-references",
        ]:
            if candidate.is_dir():
                return candidate
        return None
```

- [ ] **Step 3: Add reference listing**

Below `list_command_templates`, add:

```python
    def list_command_reference_templates(self, command_name: str) -> list[Path]:
        """Return sorted reference files for a command template stem."""
        references_dir = self.shared_command_references_dir()
        if not references_dir or not references_dir.is_dir():
            return []
        workflow_dir = references_dir / command_name
        if not workflow_dir.is_dir():
            return []
        return sorted(
            path
            for path in workflow_dir.rglob("*")
            if path.is_file()
        )
```

- [ ] **Step 4: Add unresolved-token validation**

Below `write_file_and_record`, add:

```python
    @classmethod
    def validate_no_unresolved_renderer_tokens(
        cls,
        content: str,
        source_path: Path | str,
    ) -> None:
        """Fail if generated content still contains renderer-only tokens."""
        match = cls.UNRESOLVED_RENDERER_TOKEN_RE.search(content)
        if match:
            raise ValueError(
                f"{source_path} contains unresolved renderer token {match.group(0)!r}"
            )
```

- [ ] **Step 5: Add owner-context reference rendering**

Below `validate_no_unresolved_renderer_tokens`, add:

```python
    @classmethod
    def render_command_reference_content(
        cls,
        raw_reference: str,
        *,
        owner_template_raw: str,
        owner_template_path: Path,
        reference_path: Path,
        agent_name: str,
        script_type: str,
        arg_placeholder: str,
        project_root: Path | None = None,
        apply_invocation_conventions: bool = False,
    ) -> str:
        """Render a command reference with the owning command's frontmatter."""
        owner_frontmatter, _ = cls._split_frontmatter(owner_template_raw)
        if owner_frontmatter:
            render_input = f"---\n{owner_frontmatter}---\n\n{raw_reference}"
        else:
            render_input = raw_reference

        rendered = cls.process_template(
            render_input,
            agent_name,
            script_type,
            arg_placeholder,
            template_path=reference_path,
            project_root=project_root,
        )
        _, body = cls._split_frontmatter(rendered)

        if apply_invocation_conventions:
            from specify_cli.agents import CommandRegistrar

            body = CommandRegistrar.apply_skill_invocation_conventions(
                agent_name,
                body,
            )

        cls.validate_no_unresolved_renderer_tokens(body, reference_path)
        return body.lstrip("\r\n")
```

- [ ] **Step 6: Run the focused tests and verify they pass**

Run:

```powershell
python -m pytest tests/integrations/test_base.py::TestBasePrimitives::test_command_reference_templates_are_discovered_from_workflow_stem tests/integrations/test_base.py::TestBasePrimitives::test_render_command_reference_uses_owner_template_context tests/integrations/test_base.py::TestBasePrimitives::test_validate_no_unresolved_renderer_tokens_reports_path -q
```

Expected: PASS.

- [ ] **Step 7: Run existing template primitive tests**

Run:

```powershell
python -m pytest tests/integrations/test_base.py::TestBasePrimitives -q
```

Expected: PASS.

- [ ] **Step 8: Commit the implementation**

```powershell
git add src/specify_cli/integrations/base.py
git commit -m "feat: add command reference rendering primitives"
```

### Task 3: Add Single-File Inline Reference Rendering For Markdown And TOML

**Files:**
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Modify: `src/specify_cli/integrations/base.py`

- [ ] **Step 1: Add Markdown failing test for inline references**

In `tests/integrations/test_integration_base_markdown.py`, add this helper near the imports:

```python
def _write_command_with_reference_fixture(root):
    commands = root / "commands"
    references = root / "command-references" / "plan"
    commands.mkdir(parents=True)
    references.mkdir(parents=True)
    (commands / "plan.md").write_text(
        "---\n"
        "description: Plan command\n"
        "scripts:\n"
        "  sh: scripts/bash/setup-plan.sh --json\n"
        "---\n\n"
        "# Plan Main\n\n"
        "Load [reference index](references/INDEX.md) when details are needed.\n",
        encoding="utf-8",
    )
    (references / "INDEX.md").write_text(
        "# Plan Reference Index\n\n"
        "- [details](details.md): Trigger: detail routing\n",
        encoding="utf-8",
    )
    (references / "details.md").write_text(
        "Trigger: detail routing\n\n"
        "Purpose: prove inline rendering\n\n"
        "Preserved Contract: keep plan details\n\n"
        "Run {SCRIPT} with {ARGS} for __AGENT__ before {{invoke:tasks}}.\n",
        encoding="utf-8",
    )
    return commands, root / "command-references"
```

Add this test under `class MarkdownIntegrationTests`:

```python
    def test_single_file_commands_inline_command_references(self, tmp_path, monkeypatch):
        commands, refs = _write_command_with_reference_fixture(tmp_path / "fixtures")
        i = get_integration(self.KEY)
        monkeypatch.setattr(type(i), "list_command_templates", lambda self: [commands / "plan.md"])
        monkeypatch.setattr(type(i), "shared_command_references_dir", lambda self: refs)

        project = tmp_path / "project"
        manifest = IntegrationManifest(self.KEY, project)
        i.setup(project, manifest, script_type="sh")

        command_path = project / self.FOLDER / self.COMMANDS_SUBDIR / "sp.plan.md"
        content = command_path.read_text(encoding="utf-8")
        assert "## Reference Contracts" in content
        assert "### references/INDEX.md" in content
        assert "### references/details.md" in content
        assert "scripts/bash/setup-plan.sh --json" in content
        assert "{SCRIPT}" not in content
        assert "{ARGS}" not in content
        assert "__AGENT__" not in content
        assert "{{invoke:tasks}}" not in content
```

- [ ] **Step 2: Add TOML failing test for inline references**

In `tests/integrations/test_integration_base_toml.py`, add this helper near the imports:

```python
def _write_toml_command_with_reference_fixture(root):
    commands = root / "commands"
    references = root / "command-references" / "plan"
    commands.mkdir(parents=True)
    references.mkdir(parents=True)
    (commands / "plan.md").write_text(
        "---\n"
        "description: Plan command\n"
        "scripts:\n"
        "  sh: scripts/bash/setup-plan.sh --json\n"
        "---\n\n"
        "# Plan Main\n\n"
        "Load [reference index](references/INDEX.md) when details are needed.\n",
        encoding="utf-8",
    )
    (references / "INDEX.md").write_text(
        "# Plan Reference Index\n\n"
        "- [details](details.md): Trigger: detail routing\n",
        encoding="utf-8",
    )
    (references / "details.md").write_text(
        "Trigger: detail routing\n\n"
        "Purpose: prove inline rendering\n\n"
        "Preserved Contract: keep plan details\n\n"
        "Run {SCRIPT} with {ARGS} for __AGENT__ before {{invoke:tasks}}.\n",
        encoding="utf-8",
    )
    return commands, root / "command-references"
```

Add this test under `class TomlIntegrationTests`:

```python
    def test_toml_commands_inline_command_references(self, tmp_path, monkeypatch):
        commands, refs = _write_toml_command_with_reference_fixture(tmp_path / "fixtures")
        i = get_integration(self.KEY)
        monkeypatch.setattr(type(i), "list_command_templates", lambda self: [commands / "plan.md"])
        monkeypatch.setattr(type(i), "shared_command_references_dir", lambda self: refs)

        project = tmp_path / "project"
        manifest = IntegrationManifest(self.KEY, project)
        i.setup(project, manifest, script_type="sh")

        command_path = project / self.FOLDER / self.COMMANDS_SUBDIR / "sp.plan.toml"
        parsed = tomllib.loads(command_path.read_text(encoding="utf-8"))
        prompt = parsed["prompt"]
        assert "## Reference Contracts" in prompt
        assert "### references/INDEX.md" in prompt
        assert "### references/details.md" in prompt
        assert "scripts/bash/setup-plan.sh --json" in prompt
        assert "{SCRIPT}" not in prompt
        assert "{ARGS}" not in prompt
        assert "__AGENT__" not in prompt
        assert "{{invoke:tasks}}" not in prompt
```

- [ ] **Step 3: Run the new tests and verify they fail**

Run:

```powershell
python -m pytest tests/integrations/test_integration_base_markdown.py::MarkdownIntegrationTests::test_single_file_commands_inline_command_references tests/integrations/test_integration_base_toml.py::TomlIntegrationTests::test_toml_commands_inline_command_references -q
```

Expected: FAIL because Markdown/TOML setup does not inline command references.

- [ ] **Step 4: Add inline rendering helper**

In `src/specify_cli/integrations/base.py`, below `render_command_reference_content`, add:

```python
    def render_inline_command_references(
        self,
        *,
        command_name: str,
        owner_template_raw: str,
        owner_template_path: Path,
        agent_name: str,
        script_type: str,
        arg_placeholder: str,
        project_root: Path,
    ) -> str:
        """Render command references into a single-file command section."""
        reference_files = self.list_command_reference_templates(command_name)
        if not reference_files:
            return ""

        rendered_sections = ["", "## Reference Contracts", ""]
        references_root = reference_files[0].parent
        for path in reference_files:
            try:
                rel = path.relative_to(references_root)
            except ValueError:
                rel = path.name
            display_path = Path("references") / rel
            rendered_sections.append(f"### {display_path.as_posix()}")
            rendered_sections.append("")
            rendered_sections.append(
                self.render_command_reference_content(
                    path.read_text(encoding="utf-8"),
                    owner_template_raw=owner_template_raw,
                    owner_template_path=owner_template_path,
                    reference_path=path,
                    agent_name=agent_name,
                    script_type=script_type,
                    arg_placeholder=arg_placeholder,
                    project_root=project_root,
                ).rstrip()
            )
            rendered_sections.append("")

        rendered = "\n".join(rendered_sections)
        self.validate_no_unresolved_renderer_tokens(rendered, owner_template_path)
        return rendered
```

- [ ] **Step 5: Wire Markdown setup**

In `MarkdownIntegration.setup`, immediately after `processed = self.process_template(...)`, add:

```python
            processed += self.render_inline_command_references(
                command_name=src_file.stem,
                owner_template_raw=raw,
                owner_template_path=src_file,
                agent_name=self.key,
                script_type=script_type,
                arg_placeholder=arg_placeholder,
                project_root=project_root,
            )
```

- [ ] **Step 6: Wire TOML setup**

In `TomlIntegration.setup`, immediately after `processed = self.process_template(...)`, add:

```python
            processed += self.render_inline_command_references(
                command_name=src_file.stem,
                owner_template_raw=raw,
                owner_template_path=src_file,
                agent_name=self.key,
                script_type=script_type,
                arg_placeholder=arg_placeholder,
                project_root=project_root,
            )
```

- [ ] **Step 7: Run focused tests and verify they pass**

Run:

```powershell
python -m pytest tests/integrations/test_integration_base_markdown.py::MarkdownIntegrationTests::test_single_file_commands_inline_command_references tests/integrations/test_integration_base_toml.py::TomlIntegrationTests::test_toml_commands_inline_command_references -q
```

Expected: PASS.

- [ ] **Step 8: Run representative existing integration tests**

Run:

```powershell
python -m pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py -q
```

Expected: PASS.

- [ ] **Step 9: Commit**

```powershell
git add src/specify_cli/integrations/base.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py
git commit -m "feat: inline command references for single-file integrations"
```

### Task 4: Add Skills Sidecar Reference Generation And Reachability Tests

**Files:**
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `src/specify_cli/integrations/base.py`

- [ ] **Step 1: Add sidecar fixture helper**

In `tests/integrations/test_integration_base_skills.py`, add this helper near the imports:

```python
def _write_skill_command_with_reference_fixture(root):
    commands = root / "commands"
    references = root / "command-references" / "plan"
    commands.mkdir(parents=True)
    references.mkdir(parents=True)
    (commands / "plan.md").write_text(
        "---\n"
        "description: Plan command\n"
        "scripts:\n"
        "  sh: scripts/bash/setup-plan.sh --json\n"
        "---\n\n"
        "# Plan Main\n\n"
        "Use [reference index](references/INDEX.md) for detailed contract routing.\n",
        encoding="utf-8",
    )
    (references / "INDEX.md").write_text(
        "# Plan Reference Index\n\n"
        "- [details](details.md): Trigger: detail routing; Purpose: sidecar test; Preserved Contract: sidecar rules\n",
        encoding="utf-8",
    )
    (references / "details.md").write_text(
        "Trigger: detail routing\n\n"
        "Purpose: prove sidecar rendering\n\n"
        "Preserved Contract: keep sidecar details\n\n"
        "Run {SCRIPT} with {ARGS} for __AGENT__ before {{invoke:tasks}}.\n",
        encoding="utf-8",
    )
    return commands, root / "command-references"
```

- [ ] **Step 2: Add failing sidecar generation test**

Under `class SkillsIntegrationTests`, add:

```python
    def test_skills_install_processed_reference_sidecars_and_manifest_entries(self, tmp_path, monkeypatch):
        commands, refs = _write_skill_command_with_reference_fixture(tmp_path / "fixtures")
        i = get_integration(self.KEY)
        monkeypatch.setattr(type(i), "list_command_templates", lambda self: [commands / "plan.md"])
        monkeypatch.setattr(type(i), "shared_command_references_dir", lambda self: refs)

        project = tmp_path / "project"
        manifest = IntegrationManifest(self.KEY, project)
        i.setup(project, manifest, script_type="sh")

        skill_dir = i.skills_dest(project) / "sp-plan"
        skill = skill_dir / "SKILL.md"
        index = skill_dir / "references" / "INDEX.md"
        detail = skill_dir / "references" / "details.md"

        assert skill.exists()
        assert index.exists()
        assert detail.exists()
        assert "references/INDEX.md" in skill.read_text(encoding="utf-8")
        detail_content = detail.read_text(encoding="utf-8")
        assert "scripts/bash/setup-plan.sh --json" in detail_content
        assert "{SCRIPT}" not in detail_content
        assert "{ARGS}" not in detail_content
        assert "__AGENT__" not in detail_content
        assert "{{invoke:tasks}}" not in detail_content
        assert str(index.relative_to(project)).replace("\\", "/") in manifest.files
        assert str(detail.relative_to(project)).replace("\\", "/") in manifest.files
```

- [ ] **Step 3: Add failing all-skills unresolved token test**

Under `class SkillsIntegrationTests`, add:

```python
    def test_generated_reference_sidecars_have_no_unresolved_renderer_tokens(self, tmp_path):
        i = get_integration(self.KEY)
        manifest = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, manifest, script_type="sh")

        for path in i.skills_dest(tmp_path).glob("sp-*/references/**/*.md"):
            content = path.read_text(encoding="utf-8")
            assert "{SCRIPT}" not in content, path
            assert "{AGENT_SCRIPT}" not in content, path
            assert "{ARGS}" not in content, path
            assert "__AGENT__" not in content, path
            assert "{{invoke:" not in content, path
```

- [ ] **Step 4: Add failing reachability test**

Under `class SkillsIntegrationTests`, add:

```python
    def test_generated_reference_sidecars_are_reachable_from_index(self, tmp_path):
        i = get_integration(self.KEY)
        manifest = IntegrationManifest(self.KEY, tmp_path)
        i.setup(tmp_path, manifest, script_type="sh")

        for skill_dir in sorted(i.skills_dest(tmp_path).glob("sp-*")):
            references_dir = skill_dir / "references"
            if not references_dir.exists():
                continue
            skill = skill_dir / "SKILL.md"
            skill_content = skill.read_text(encoding="utf-8")
            assert "references/INDEX.md" in skill_content, skill

            index = references_dir / "INDEX.md"
            assert index.exists(), skill_dir
            index_content = index.read_text(encoding="utf-8")
            for reference in sorted(references_dir.glob("**/*.md")):
                if reference.name == "INDEX.md":
                    continue
                rel = reference.relative_to(references_dir).as_posix()
                assert rel in index_content, reference
```

- [ ] **Step 5: Run new tests and verify they fail**

Run:

```powershell
python -m pytest tests/integrations/test_integration_base_skills.py::SkillsIntegrationTests::test_skills_install_processed_reference_sidecars_and_manifest_entries tests/integrations/test_integration_base_skills.py::SkillsIntegrationTests::test_generated_reference_sidecars_have_no_unresolved_renderer_tokens tests/integrations/test_integration_base_skills.py::SkillsIntegrationTests::test_generated_reference_sidecars_are_reachable_from_index -q
```

Expected: FAIL because sidecar generation does not exist.

- [ ] **Step 6: Add sidecar write helper**

In `src/specify_cli/integrations/base.py`, inside `class SkillsIntegration`, below `_render_skill_content`, add:

```python
    def _copy_command_reference_sidecars(
        self,
        *,
        command_name: str,
        owner_template_raw: str,
        owner_template_path: Path,
        destination_dir: Path,
        project_root: Path,
        manifest: IntegrationManifest,
        script_type: str,
        arg_placeholder: str,
    ) -> list[Path]:
        """Render command references into a skill's references directory."""
        reference_files = self.list_command_reference_templates(command_name)
        if not reference_files:
            return []

        created: list[Path] = []
        references_root = self.shared_command_references_dir() / command_name
        references_dest = destination_dir / "references"

        for src_file in reference_files:
            relative = src_file.relative_to(references_root)
            dst_file = references_dest / relative
            rendered = self.render_command_reference_content(
                src_file.read_text(encoding="utf-8"),
                owner_template_raw=owner_template_raw,
                owner_template_path=owner_template_path,
                reference_path=src_file,
                agent_name=self.key,
                script_type=script_type,
                arg_placeholder=arg_placeholder,
                project_root=project_root,
                apply_invocation_conventions=True,
            )
            created.append(
                self.write_file_and_record(
                    rendered,
                    dst_file,
                    project_root,
                    manifest,
                )
            )

        return created
```

- [ ] **Step 7: Call the helper from `SkillsIntegration.setup`**

In `SkillsIntegration.setup`, after writing `skill_file`, add:

```python
            created.extend(
                self._copy_command_reference_sidecars(
                    command_name=command_name,
                    owner_template_raw=raw,
                    owner_template_path=src_file,
                    destination_dir=skill_dir,
                    project_root=project_root,
                    manifest=manifest,
                    script_type=script_type,
                    arg_placeholder=arg_placeholder,
                )
            )
```

- [ ] **Step 8: Run focused sidecar tests**

Run:

```powershell
python -m pytest tests/integrations/test_integration_base_skills.py::SkillsIntegrationTests::test_skills_install_processed_reference_sidecars_and_manifest_entries tests/integrations/test_integration_base_skills.py::SkillsIntegrationTests::test_generated_reference_sidecars_have_no_unresolved_renderer_tokens tests/integrations/test_integration_base_skills.py::SkillsIntegrationTests::test_generated_reference_sidecars_are_reachable_from_index -q
```

Expected: PASS after fixture tests pass. The all-skills tests pass before migration by finding no sidecars or pass after sidecars exist.

- [ ] **Step 9: Run skills integration tests**

Run:

```powershell
python -m pytest tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_cursor_agent.py tests/integrations/test_integration_kimi.py tests/integrations/test_integration_agy.py tests/integrations/test_integration_vibe.py -q
```

Expected: PASS.

- [ ] **Step 10: Commit**

```powershell
git add src/specify_cli/integrations/base.py tests/integrations/test_integration_base_skills.py
git commit -m "feat: install processed workflow reference sidecars"
```

### Task 5: Package Command References And Mirror Them Into Generated Projects

**Files:**
- Modify: `pyproject.toml`
- Modify: `src/specify_cli/__init__.py`
- Modify: `tests/test_alignment_templates.py`

- [ ] **Step 1: Add packaging failing test**

In `tests/test_alignment_templates.py`, near existing pyproject force-include tests, add:

```python
def test_command_references_are_packaged_core_assets():
    pyproject = _read("pyproject.toml")
    assert '"templates/command-references" = "specify_cli/core_pack/command-references"' in pyproject
```

- [ ] **Step 2: Add shared-infra mirror failing test**

In `tests/test_alignment_templates.py`, add:

```python
def test_shared_infra_mirrors_command_references_from_core_pack():
    content = _read("src/specify_cli/__init__.py")
    assert '"command-references"' in content
    assert "core / extra_name" in content
    assert "dest_templates / extra_name" in content
```

- [ ] **Step 3: Run the new tests and verify they fail**

Run:

```powershell
python -m pytest tests/test_alignment_templates.py::test_command_references_are_packaged_core_assets tests/test_alignment_templates.py::test_shared_infra_mirrors_command_references_from_core_pack -q
```

Expected: FAIL because `command-references` is not included.

- [ ] **Step 4: Add force include**

In `pyproject.toml`, under the command template force-includes, add:

```toml
"templates/command-references" = "specify_cli/core_pack/command-references"
```

- [ ] **Step 5: Mirror command references in shared infra**

In `_install_shared_infra` in `src/specify_cli/__init__.py`, update:

```python
            extra_template_dirs = (
                "command-partials",
                "passive-skills",
                "worker-prompts",
            )
```

to:

```python
            extra_template_dirs = (
                "command-partials",
                "command-references",
                "passive-skills",
                "worker-prompts",
            )
```

- [ ] **Step 6: Run packaging tests**

Run:

```powershell
python -m pytest tests/test_alignment_templates.py::test_command_references_are_packaged_core_assets tests/test_alignment_templates.py::test_shared_infra_mirrors_command_references_from_core_pack -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add pyproject.toml src/specify_cli/__init__.py tests/test_alignment_templates.py
git commit -m "feat: package command reference assets"
```

### Task 6: Add Safe Repair And Preset Restore For Missing Sidecars

**Files:**
- Modify: `src/specify_cli/integrations/base.py`
- Modify: `src/specify_cli/integrations/claude/__init__.py`
- Modify: `src/specify_cli/integrations/gemini/__init__.py`
- Modify: `src/specify_cli/presets.py`
- Modify: `tests/integrations/test_integration_base_skills.py`

- [ ] **Step 1: Add repair test for missing sidecar restoration**

In `tests/integrations/test_integration_base_skills.py`, under `class SkillsIntegrationTests`, add:

```python
    def test_repair_missing_reference_sidecars_restores_manifest_owned_missing_file(self, tmp_path, monkeypatch):
        commands, refs = _write_skill_command_with_reference_fixture(tmp_path / "fixtures")
        i = get_integration(self.KEY)
        monkeypatch.setattr(type(i), "list_command_templates", lambda self: [commands / "plan.md"])
        monkeypatch.setattr(type(i), "shared_command_references_dir", lambda self: refs)

        project = tmp_path / "project"
        manifest = IntegrationManifest(self.KEY, project)
        i.setup(project, manifest, script_type="sh")

        reference = i.skills_dest(project) / "sp-plan" / "references" / "INDEX.md"
        assert reference.exists()
        reference.unlink()

        restored = i.repair_missing_command_reference_sidecars(
            project,
            manifest,
            script_type="sh",
        )

        assert reference in restored
        assert reference.exists()
        assert "Plan Reference Index" in reference.read_text(encoding="utf-8")
```

- [ ] **Step 2: Add repair test for modified sidecar preservation**

In `tests/integrations/test_integration_base_skills.py`, under `class SkillsIntegrationTests`, add:

```python
    def test_repair_missing_reference_sidecars_preserves_existing_modified_file(self, tmp_path, monkeypatch):
        commands, refs = _write_skill_command_with_reference_fixture(tmp_path / "fixtures")
        i = get_integration(self.KEY)
        monkeypatch.setattr(type(i), "list_command_templates", lambda self: [commands / "plan.md"])
        monkeypatch.setattr(type(i), "shared_command_references_dir", lambda self: refs)

        project = tmp_path / "project"
        manifest = IntegrationManifest(self.KEY, project)
        i.setup(project, manifest, script_type="sh")

        reference = i.skills_dest(project) / "sp-plan" / "references" / "INDEX.md"
        original = "# user-modified reference index\n"
        reference.write_text(original, encoding="utf-8")

        restored = i.repair_missing_command_reference_sidecars(
            project,
            manifest,
            script_type="sh",
        )

        assert restored == []
        assert reference.read_text(encoding="utf-8") == original
```

- [ ] **Step 3: Run new repair tests and verify they fail**

Run:

```powershell
python -m pytest tests/integrations/test_integration_base_skills.py::SkillsIntegrationTests::test_repair_missing_reference_sidecars_restores_manifest_owned_missing_file tests/integrations/test_integration_base_skills.py::SkillsIntegrationTests::test_repair_missing_reference_sidecars_preserves_existing_modified_file -q
```

Expected: FAIL because `repair_missing_command_reference_sidecars` does not exist.

- [ ] **Step 4: Add shared sidecar repair helper**

In `SkillsIntegration`, below `_copy_command_reference_sidecars`, add:

```python
    def repair_missing_command_reference_sidecars(
        self,
        project_root: Path,
        manifest: IntegrationManifest,
        *,
        script_type: str,
    ) -> list[Path]:
        """Restore missing manifest-owned reference sidecars without overwriting edits."""
        skills_dir = self.skills_dest(project_root)
        arg_placeholder = (
            self.registrar_config.get("args", "$ARGUMENTS")
            if self.registrar_config
            else "$ARGUMENTS"
        )
        restored: list[Path] = []

        for src_file in self.list_command_templates():
            command_name = src_file.stem
            reference_files = self.list_command_reference_templates(command_name)
            if not reference_files:
                continue
            skill_name = "sp-teams" if command_name == "team" else f"sp-{command_name.replace('.', '-')}"
            skill_dir = skills_dir / skill_name
            if not (skill_dir / "SKILL.md").is_file():
                continue

            owner_raw = src_file.read_text(encoding="utf-8")
            references_root = self.shared_command_references_dir() / command_name
            for reference_src in reference_files:
                relative = reference_src.relative_to(references_root)
                destination = skill_dir / "references" / relative
                rel_manifest_path = destination.resolve().relative_to(project_root.resolve()).as_posix()
                if rel_manifest_path not in manifest.files:
                    continue
                if destination.exists():
                    continue
                rendered = self.render_command_reference_content(
                    reference_src.read_text(encoding="utf-8"),
                    owner_template_raw=owner_raw,
                    owner_template_path=src_file,
                    reference_path=reference_src,
                    agent_name=self.key,
                    script_type=script_type,
                    arg_placeholder=arg_placeholder,
                    project_root=project_root,
                    apply_invocation_conventions=True,
                )
                restored.append(
                    self.write_file_and_record(
                        rendered,
                        destination,
                        project_root,
                        manifest,
                    )
                )

        return restored
```

- [ ] **Step 5: Call sidecar repair from base `SkillsIntegration.repair_runtime_assets`**

Add this method to `SkillsIntegration`:

```python
    def repair_runtime_assets(
        self,
        project_root: Path,
        manifest: IntegrationManifest,
        **opts: Any,
    ) -> list[Path]:
        created = super().repair_runtime_assets(project_root, manifest, **opts)
        created.extend(
            self.repair_missing_command_reference_sidecars(
                project_root,
                manifest,
                script_type=opts.get("script_type", "sh"),
            )
        )
        return created
```

- [ ] **Step 6: Update Claude repair override**

In `ClaudeIntegration.repair_runtime_assets`, before `return created`, add:

```python
        created.extend(
            self.repair_missing_command_reference_sidecars(
                project_root,
                manifest,
                script_type=opts.get("script_type", "sh"),
            )
        )
```

- [ ] **Step 7: Update Gemini repair override**

In `GeminiIntegration.repair_runtime_assets`, before `return created`, add:

```python
        created.extend(
            self.repair_missing_command_reference_sidecars(
                project_root,
                manifest,
                script_type=opts.get("script_type", "sh"),
            )
        )
```

- [ ] **Step 8: Add preset restore helper**

In `src/specify_cli/presets.py`, inside `PresetManager`, add a small helper near `_restore_overridden_core_skills`:

```python
    def _restore_core_skill_references_if_missing(
        self,
        *,
        selected_ai: str,
        short_name: str,
        skill_subdir: Path,
    ) -> None:
        from .integrations import get_integration
        from .integrations.base import SkillsIntegration
        from .integrations.manifest import IntegrationManifest

        integration = get_integration(selected_ai)
        if not isinstance(integration, SkillsIntegration):
            return

        manifest = IntegrationManifest.load(selected_ai, self.project_root)
        integration.repair_missing_command_reference_sidecars(
            self.project_root,
            manifest,
            script_type=load_init_options(self.project_root).get("script", "sh"),
        )
        manifest.save()
```

- [ ] **Step 9: Call preset restore helper after core skill regeneration**

In `_restore_overridden_core_skills`, after `skill_file.write_text(skill_content, encoding="utf-8")`, add:

```python
                if isinstance(selected_ai, str):
                    self._restore_core_skill_references_if_missing(
                        selected_ai=selected_ai,
                        short_name=short_name,
                        skill_subdir=skill_subdir,
                    )
```

- [ ] **Step 10: Run repair tests**

Run:

```powershell
python -m pytest tests/integrations/test_integration_base_skills.py::SkillsIntegrationTests::test_repair_missing_reference_sidecars_restores_manifest_owned_missing_file tests/integrations/test_integration_base_skills.py::SkillsIntegrationTests::test_repair_missing_reference_sidecars_preserves_existing_modified_file tests/integrations/test_integration_subcommand.py::TestIntegrationRepair::test_repair_preserves_user_modified_skill_content -q
```

Expected: PASS.

- [ ] **Step 11: Commit after tests pass**

```powershell
git add src/specify_cli/integrations/base.py src/specify_cli/integrations/claude/__init__.py src/specify_cli/integrations/gemini/__init__.py src/specify_cli/presets.py tests/integrations/test_integration_base_skills.py
git commit -m "feat: repair missing workflow reference sidecars safely"
```

### Task 7: Migrate `sp-discussion` As The Pattern Workflow

**Files:**
- Modify: `templates/commands/discussion.md`
- Create: `templates/command-references/discussion/INDEX.md`
- Create: `templates/command-references/discussion/context-boundary-and-truth.md`
- Create: `templates/command-references/discussion/frontstage-backstage-persistence.md`
- Create: `templates/command-references/discussion/question-and-advice-contract.md`
- Create: `templates/command-references/discussion/handoff-contract.md`
- Create: `templates/command-references/discussion/handoff-review-and-repair.md`
- Create: `templates/command-references/discussion/downstream-consumption.md`
- Create: `templates/command-references/discussion/quality-and-closeout.md`
- Create: `tests/fixtures/command-reference-coverage/discussion.json`
- Modify: `tests/test_alignment_templates.py`

- [ ] **Step 1: Add the discussion reference files with required headers**

Each new reference file must start with this exact three-field pattern:

```markdown
Trigger: before the agent applies this detailed contract.

Purpose: preserve detailed workflow rules outside the main hot path.

Preserved Contract: Migrated from `templates/commands/discussion.md`; this file preserves existing `sp-discussion` behavior and does not define new workflow behavior.
```

Replace the example trigger and purpose with a workflow-specific concrete trigger and purpose in each actual reference file.

- [ ] **Step 2: Move discussion details without rewriting behavior**

Move detailed sections from the current `templates/commands/discussion.md` into the discussion reference files. Preserve field names, filenames, command tokens, JSON keys, user confirmation rules, blocking rules, and quality gates exactly.

Use this mapping:

```text
context-boundary-and-truth.md:
  Context Boundary Gate
  project cognition advisory navigation
  Truth Pass
  verified_project_facts
  open_assumptions
  evidence_checked
  advice_confidence

frontstage-backstage-persistence.md:
  frontstage / backstage separation
  checkpoint persistence
  semantic checkpoints
  deferred persistence
  compaction preservation
  save triggers

question-and-advice-contract.md:
  Turn Classifier
  Question Evidence Gate
  adaptive question pack
  unified frontstage contract
  recommendation-first behavior
  senior consequence analysis

handoff-contract.md:
  discussion_requirement_contract
  handoff-to-specify.md
  handoff-to-specify.json
  consumer_eligibility
  recommended_consumer
  quick_task_candidate
  Must-Preserve Ledger

handoff-review-and-repair.md:
  Handoff Reviewer Guide
  Approve only if
  Request changes if
  blocked_by_handoff_integrity
  source_handoff_json
  source_files_read
  handoff_status
  quality_gate

downstream-consumption.md:
  discussion_decision_digest
  selected direction
  target boundary
  next consumption path
  sp-specify consumption
  sp-quick eligibility

quality-and-closeout.md:
  handoff-ready closeout
  do not close with only file paths
  ready-summary quality checks
  no P0/P1/P2 planning
  no alternate product path
```

- [ ] **Step 3: Keep the main discussion file as a hot-path skeleton**

`templates/commands/discussion.md` must keep:

```markdown
## Main Flow

1. Classify the turn.
2. Run the Context Boundary Gate before project-specific technical advice.
3. Use project cognition only as advisory navigation; prove facts from live evidence.
4. Answer with the unified frontstage contract.
5. Persist only at semantic checkpoints, save triggers, compaction risk, five-turn cadence, or lifecycle transitions.
6. Draft exactly one `discussion_requirement_contract` handoff pair only after explicit handoff request and boundary lock.
7. Self-review and ask for user confirmation before marking handoff ready.
```

Use the existing wording where possible. Keep direct links to:

```markdown
[Reference index](references/INDEX.md)
[Context boundary and truth](references/context-boundary-and-truth.md)
[Persistence](references/frontstage-backstage-persistence.md)
[Handoff contract](references/handoff-contract.md)
[Handoff review and repair](references/handoff-review-and-repair.md)
```

- [ ] **Step 4: Add `INDEX.md`**

`templates/command-references/discussion/INDEX.md` must list every reference file and include each file's trigger. Use this format:

```markdown
# Discussion Reference Index

- [context-boundary-and-truth.md](context-boundary-and-truth.md): Trigger: before project-specific technical advice, repository fact claims, or handoff boundary decisions.
- [frontstage-backstage-persistence.md](frontstage-backstage-persistence.md): Trigger: when deciding whether to write discussion files or preserve compaction state.
- [question-and-advice-contract.md](question-and-advice-contract.md): Trigger: before asking questions, giving recommendation-first advice, or shaping a visible reply.
- [handoff-contract.md](handoff-contract.md): Trigger: when an explicit handoff request is accepted after boundary lock.
- [handoff-review-and-repair.md](handoff-review-and-repair.md): Trigger: before marking handoff ready or repairing a rejected handoff.
- [downstream-consumption.md](downstream-consumption.md): Trigger: when explaining how `sp-specify` or `sp-quick` consumes the handoff.
- [quality-and-closeout.md](quality-and-closeout.md): Trigger: before closeout, ready-summary, or scope-boundary statements.
```

- [ ] **Step 5: Add discussion coverage ledger**

Create `tests/fixtures/command-reference-coverage/discussion.json`:

```json
{
  "workflow": "discussion",
  "source": "templates/commands/discussion.md",
  "entries": [
    {
      "kind": "gate",
      "source_excerpt": "Context Boundary Gate",
      "target": "templates/commands/discussion.md"
    },
    {
      "kind": "state-field",
      "source_excerpt": "verified_project_facts",
      "target": "templates/command-references/discussion/context-boundary-and-truth.md"
    },
    {
      "kind": "handoff-file",
      "source_excerpt": "handoff-to-specify.json",
      "target": "templates/command-references/discussion/handoff-contract.md"
    },
    {
      "kind": "repair",
      "source_excerpt": "blocked_by_handoff_integrity",
      "target": "templates/command-references/discussion/handoff-review-and-repair.md"
    },
    {
      "kind": "closeout",
      "source_excerpt": "do not close with only file paths",
      "target": "templates/command-references/discussion/quality-and-closeout.md"
    }
  ]
}
```

Add more entries until every hard gate, state field group, JSON field group, exception branch, and review gate moved out of the main file has at least one entry.

- [ ] **Step 6: Add alignment tests for discussion references**

In `tests/test_alignment_templates.py`, add:

```python
def test_discussion_reference_files_are_reachable_and_have_required_headers():
    root = PROJECT_ROOT / "templates" / "command-references" / "discussion"
    command = _read("templates/commands/discussion.md")
    index = (root / "INDEX.md").read_text(encoding="utf-8")
    assert "references/INDEX.md" in command

    for path in sorted(root.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        assert "Trigger:" in content, path
        assert "Purpose:" in content, path
        assert "Preserved Contract:" in content, path
        if path.name != "INDEX.md":
            assert path.name in index, path
```

Add:

```python
def test_discussion_reference_coverage_ledger_targets_existing_text():
    ledger = json.loads(
        (PROJECT_ROOT / "tests" / "fixtures" / "command-reference-coverage" / "discussion.json").read_text(encoding="utf-8")
    )
    for entry in ledger["entries"]:
        target = PROJECT_ROOT / entry["target"]
        assert target.exists(), entry
        assert entry["source_excerpt"] in target.read_text(encoding="utf-8"), entry
```

Add `import json` if this file does not already import it.

- [ ] **Step 7: Run discussion checks**

Run:

```powershell
python -m pytest tests/test_alignment_templates.py::test_discussion_reference_files_are_reachable_and_have_required_headers tests/test_alignment_templates.py::test_discussion_reference_coverage_ledger_targets_existing_text tests/integrations/test_integration_base_skills.py::SkillsIntegrationTests::test_generated_reference_sidecars_are_reachable_from_index tests/integrations/test_integration_base_skills.py::SkillsIntegrationTests::test_generated_reference_sidecars_have_no_unresolved_renderer_tokens -q
```

Expected: PASS.

- [ ] **Step 8: Run existing discussion contract tests**

Run:

```powershell
python -m pytest tests/integrations/test_integration_base_markdown.py::test_collected_markdown_integrations_preserve_shared_discussion_contracts tests/integrations/test_integration_base_skills.py::test_collected_skills_integrations_preserve_shared_discussion_contracts tests/integrations/test_integration_base_toml.py::test_collected_toml_integrations_preserve_shared_discussion_contracts -q
```

Expected: PASS. If a contract assertion fails because the text moved into a sidecar, update the assertion helper to read generated `SKILL.md` plus generated `references/**/*.md` for skills, and command output for Markdown/TOML. Do not delete the assertion.

- [ ] **Step 9: Commit**

```powershell
git add templates/commands/discussion.md templates/command-references/discussion tests/fixtures/command-reference-coverage/discussion.json tests/test_alignment_templates.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py
git commit -m "refactor: split discussion workflow references"
```

### Task 8: Migrate `sp-specify`, `sp-plan`, And `sp-tasks`

**Files:**
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/tasks.md`
- Create: `templates/command-references/specify/*.md`
- Create: `templates/command-references/plan/*.md`
- Create: `templates/command-references/tasks/*.md`
- Create: `tests/fixtures/command-reference-coverage/specify.json`
- Create: `tests/fixtures/command-reference-coverage/plan.json`
- Create: `tests/fixtures/command-reference-coverage/tasks.json`
- Modify: `tests/test_alignment_templates.py`

- [ ] **Step 1: Create specify references**

Create these files:

```text
templates/command-references/specify/INDEX.md
templates/command-references/specify/discussion-handoff-validation.md
templates/command-references/specify/semantic-traceability.md
templates/command-references/specify/ui-reference-lane.md
templates/command-references/specify/artifact-package.md
templates/command-references/specify/question-cadence-and-review.md
templates/command-references/specify/self-review-and-quality-gates.md
```

Move existing detailed `sp-specify` rules into those files without changing field names or gate semantics. The main `templates/commands/specify.md` keeps direct links to `references/INDEX.md`, `discussion-handoff-validation.md`, `ui-reference-lane.md`, and `self-review-and-quality-gates.md`.

- [ ] **Step 2: Create plan references**

Create these files:

```text
templates/command-references/plan/INDEX.md
templates/command-references/plan/spec-package-intake.md
templates/command-references/plan/research-and-design-lanes.md
templates/command-references/plan/data-model-contracts-and-quickstart.md
templates/command-references/plan/constitution-risk-and-complexity.md
templates/command-references/plan/subagent-dispatch.md
templates/command-references/plan/plan-contract-fields.md
```

Move existing detailed `sp-plan` rules into those files without changing command tokens, plan contract fields, or risk gates. The main `templates/commands/plan.md` keeps direct links to `references/INDEX.md`, `spec-package-intake.md`, `constitution-risk-and-complexity.md`, and `plan-contract-fields.md`.

- [ ] **Step 3: Create tasks references**

Create these files:

```text
templates/command-references/tasks/INDEX.md
templates/command-references/tasks/plan-intake.md
templates/command-references/tasks/task-generation-sequence.md
templates/command-references/tasks/task-packet-schema.md
templates/command-references/tasks/dependencies-and-parallel-safety.md
templates/command-references/tasks/must-preserve-ledger.md
templates/command-references/tasks/review-and-repair.md
```

Move existing detailed `sp-tasks` rules into those files without changing task packet schema, dependencies, parallel batch semantics, or review gate semantics. The main `templates/commands/tasks.md` keeps direct links to `references/INDEX.md`, `task-generation-sequence.md`, `dependencies-and-parallel-safety.md`, and `review-and-repair.md`.

- [ ] **Step 4: Add coverage ledgers**

Create:

```text
tests/fixtures/command-reference-coverage/specify.json
tests/fixtures/command-reference-coverage/plan.json
tests/fixtures/command-reference-coverage/tasks.json
```

Use this JSON shape for each ledger:

```json
{
  "workflow": "specify",
  "source": "templates/commands/specify.md",
  "entries": [
    {
      "kind": "gate",
      "source_excerpt": "Discussion Decision Digest",
      "target": "templates/command-references/specify/discussion-handoff-validation.md"
    }
  ]
}
```

Replace the sample workflow, source, excerpt, and target values with real entries for every moved gate, state field group, JSON key group, exception branch, review gate, validation gate, and artifact package rule.

- [ ] **Step 5: Generalize alignment tests**

Refactor the discussion-only tests from Task 7 into parameterized tests:

```python
MIGRATED_COMMAND_REFERENCE_WORKFLOWS = (
    "discussion",
    "specify",
    "plan",
    "tasks",
)
```

Use the same required-header, index reachability, and coverage-ledger assertions for each workflow.

- [ ] **Step 6: Run planning workflow checks**

Run:

```powershell
python -m pytest tests/test_alignment_templates.py::test_command_reference_files_are_reachable_and_have_required_headers tests/test_alignment_templates.py::test_command_reference_coverage_ledgers_target_existing_text -q
```

Expected: PASS.

- [ ] **Step 7: Run generated integration checks**

Run:

```powershell
python -m pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add templates/commands/specify.md templates/commands/plan.md templates/commands/tasks.md templates/command-references/specify templates/command-references/plan templates/command-references/tasks tests/fixtures/command-reference-coverage/specify.json tests/fixtures/command-reference-coverage/plan.json tests/fixtures/command-reference-coverage/tasks.json tests/test_alignment_templates.py
git commit -m "refactor: split planning workflow references"
```

### Task 9: Migrate `sp-implement`, `sp-quick`, And `sp-debug`

**Files:**
- Modify: `templates/commands/implement.md`
- Modify: `templates/commands/quick.md`
- Modify: `templates/commands/debug.md`
- Create: `templates/command-references/implement/*.md`
- Create: `templates/command-references/quick/*.md`
- Create: `templates/command-references/debug/*.md`
- Create: `tests/fixtures/command-reference-coverage/implement.json`
- Create: `tests/fixtures/command-reference-coverage/quick.json`
- Create: `tests/fixtures/command-reference-coverage/debug.json`
- Modify: `tests/test_alignment_templates.py`

- [ ] **Step 1: Create implement references**

Create these files:

```text
templates/command-references/implement/INDEX.md
templates/command-references/implement/task-intake-and-tracker.md
templates/command-references/implement/red-first-and-validation.md
templates/command-references/implement/subagent-worker-contract.md
templates/command-references/implement/join-point-review.md
templates/command-references/implement/safe-repair-loop.md
templates/command-references/implement/branch-review-and-closeout.md
```

Move detailed implementation rules into those files without changing RED-first, task-only execution, review windows, repair ownership, worker packet, or branch review semantics. The main `templates/commands/implement.md` keeps direct links to `references/INDEX.md`, `red-first-and-validation.md`, `join-point-review.md`, and `safe-repair-loop.md`.

- [ ] **Step 2: Create quick references**

Create these files:

```text
templates/command-references/quick/INDEX.md
templates/command-references/quick/intake-and-checkpoint.md
templates/command-references/quick/workspace-state.md
templates/command-references/quick/handoff-consumption.md
templates/command-references/quick/packetized-work.md
templates/command-references/quick/validation-and-closeout.md
```

Move detailed quick workflow rules into those files without changing Understanding Checkpoint, confirmation, small-scope routing, workspace state, validation, or stop condition semantics. The main `templates/commands/quick.md` keeps direct links to `references/INDEX.md`, `intake-and-checkpoint.md`, `handoff-consumption.md`, and `validation-and-closeout.md`.

- [ ] **Step 3: Create debug references**

Create these files:

```text
templates/command-references/debug/INDEX.md
templates/command-references/debug/intake-and-debug-checkpoint.md
templates/command-references/debug/reproduction-and-evidence.md
templates/command-references/debug/hypothesis-and-root-cause.md
templates/command-references/debug/fix-gate.md
templates/command-references/debug/regression-validation-and-closeout.md
templates/command-references/debug/debug-state.md
```

Move detailed debug workflow rules into those files without changing Debug Checkpoint, reproduction-before-fix, root-cause gate, evidence lane, fix gate, state, or validation semantics. The main `templates/commands/debug.md` keeps direct links to `references/INDEX.md`, `intake-and-debug-checkpoint.md`, `reproduction-and-evidence.md`, and `fix-gate.md`.

- [ ] **Step 4: Extend migrated workflow tuple**

In `tests/test_alignment_templates.py`, update:

```python
MIGRATED_COMMAND_REFERENCE_WORKFLOWS = (
    "discussion",
    "specify",
    "plan",
    "tasks",
)
```

to:

```python
MIGRATED_COMMAND_REFERENCE_WORKFLOWS = (
    "discussion",
    "specify",
    "plan",
    "tasks",
    "implement",
    "quick",
    "debug",
)
```

- [ ] **Step 5: Add coverage ledgers**

Create:

```text
tests/fixtures/command-reference-coverage/implement.json
tests/fixtures/command-reference-coverage/quick.json
tests/fixtures/command-reference-coverage/debug.json
```

Each ledger must map moved hard gates, state field groups, JSON key groups, exception branches, review gates, validation gates, and artifact package rules to the main file or a reference file.

- [ ] **Step 6: Run implementation workflow checks**

Run:

```powershell
python -m pytest tests/test_alignment_templates.py::test_command_reference_files_are_reachable_and_have_required_headers tests/test_alignment_templates.py::test_command_reference_coverage_ledgers_target_existing_text tests/integrations/test_integration_base_skills.py::SkillsIntegrationTests::test_generated_reference_sidecars_have_no_unresolved_renderer_tokens tests/integrations/test_integration_base_skills.py::SkillsIntegrationTests::test_generated_reference_sidecars_are_reachable_from_index -q
```

Expected: PASS.

- [ ] **Step 7: Run runtime workflow contract tests**

Run:

```powershell
python -m pytest tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_gemini.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit**

```powershell
git add templates/commands/implement.md templates/commands/quick.md templates/commands/debug.md templates/command-references/implement templates/command-references/quick templates/command-references/debug tests/fixtures/command-reference-coverage/implement.json tests/fixtures/command-reference-coverage/quick.json tests/fixtures/command-reference-coverage/debug.json tests/test_alignment_templates.py
git commit -m "refactor: split execution workflow references"
```

### Task 10: Strengthen All-Integration And Distribution Regression Coverage

**Files:**
- Modify: `tests/integrations/test_integration_base_skills.py`
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Modify: `tests/integrations/test_integration_subcommand.py`
- Modify: `tests/test_alignment_templates.py`

- [ ] **Step 1: Assert every SkillsIntegration gets sidecars for migrated workflows**

In `tests/integrations/test_integration_base_skills.py`, add a top-level test:

```python
def test_all_skills_integrations_generate_migrated_workflow_references(tmp_path):
    for integration_key in INTEGRATION_REGISTRY:
        integration = get_integration(integration_key)
        if not isinstance(integration, SkillsIntegration):
            continue

        project = tmp_path / integration_key
        manifest = IntegrationManifest(integration_key, project)
        integration.setup(project, manifest, script_type="sh")

        for workflow in IntegrationBase.COMMAND_REFERENCE_WORKFLOWS:
            skill_dir = integration.skills_dest(project) / f"sp-{workflow}"
            assert (skill_dir / "SKILL.md").exists(), (integration_key, workflow)
            assert (skill_dir / "references" / "INDEX.md").exists(), (integration_key, workflow)
            assert any((skill_dir / "references").glob("*.md")), (integration_key, workflow)
```

Add `IntegrationBase` to the import from `specify_cli.integrations.base`.

- [ ] **Step 2: Assert manifest owns all generated sidecars**

Add:

```python
def test_all_skills_integrations_manifest_owns_reference_sidecars(tmp_path):
    for integration_key in INTEGRATION_REGISTRY:
        integration = get_integration(integration_key)
        if not isinstance(integration, SkillsIntegration):
            continue

        project = tmp_path / integration_key
        manifest = IntegrationManifest(integration_key, project)
        integration.setup(project, manifest, script_type="sh")

        for reference in integration.skills_dest(project).glob("sp-*/references/**/*.md"):
            rel = reference.relative_to(project).as_posix()
            assert rel in manifest.files, (integration_key, rel)
```

- [ ] **Step 3: Assert Markdown/TOML outputs do not leak sidecar-only references**

In Markdown and TOML mixins, add assertions that generated command output includes `## Reference Contracts` for migrated workflows and no `references/INDEX.md` link is left as the only detail source.

Use this assertion body for Markdown command files:

```python
        if command_path.name in {"sp.discussion.md", "sp.specify.md", "sp.plan.md", "sp.tasks.md", "sp.implement.md", "sp.quick.md", "sp.debug.md"}:
            assert "## Reference Contracts" in content
            assert "Trigger:" in content
            assert "Preserved Contract:" in content
```

Use the same body against parsed TOML `prompt`.

- [ ] **Step 4: Add CLI repair tests now real migrated sidecars exist**

In `tests/integrations/test_integration_subcommand.py`, under `class TestIntegrationRepair`, add:

```python
    def test_repair_restores_missing_manifest_owned_reference_sidecar(self, tmp_path):
        project = _init_project(tmp_path, "claude")

        reference = project / ".claude" / "skills" / "sp-plan" / "references" / "INDEX.md"
        assert reference.exists()
        reference.unlink()

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(
                app,
                ["integration", "repair", "--script", "sh"],
                catch_exceptions=False,
            )
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 0, result.output
        assert reference.exists()
        assert "Plan Reference Index" in reference.read_text(encoding="utf-8")

    def test_repair_preserves_user_modified_reference_sidecar(self, tmp_path):
        project = _init_project(tmp_path, "claude")

        reference = project / ".claude" / "skills" / "sp-plan" / "references" / "INDEX.md"
        original = "# user-modified reference index\n"
        reference.write_text(original, encoding="utf-8")

        old_cwd = os.getcwd()
        try:
            os.chdir(project)
            result = runner.invoke(
                app,
                ["integration", "repair", "--script", "sh"],
                catch_exceptions=False,
            )
        finally:
            os.chdir(old_cwd)

        assert result.exit_code == 0, result.output
        assert reference.read_text(encoding="utf-8") == original
```

- [ ] **Step 5: Run broad integration tests**

Run:

```powershell
python -m pytest tests/integrations -q
```

Expected: PASS.

- [ ] **Step 6: Run alignment template tests**

Run:

```powershell
python -m pytest tests/test_alignment_templates.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit**

```powershell
git add tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_subcommand.py tests/test_alignment_templates.py
git commit -m "test: strengthen workflow reference regressions"
```

### Task 11: Final Verification And Cleanup

**Files:**
- Verify all changed files.

- [ ] **Step 1: Run the focused regression suite**

Run:

```powershell
python -m pytest tests/integrations tests/test_alignment_templates.py -q
```

Expected: PASS.

- [ ] **Step 2: Run full tests if runtime budget allows**

Run:

```powershell
python -m pytest -q
```

Expected: PASS. If the full suite exceeds local runtime budget, record the focused suite as completed and list the full-suite gap in the final handoff.

- [ ] **Step 3: Check whitespace**

Run:

```powershell
git diff --check
```

Expected: no output and exit code 0.

- [ ] **Step 4: Review generated file size reduction**

Run this inline Python script:

```powershell
@'
from pathlib import Path
from specify_cli.integrations import get_integration
from specify_cli.integrations.manifest import IntegrationManifest
project = Path("tmp-skill-size-check")
if project.exists():
    import shutil
    shutil.rmtree(project)
project.mkdir()
integration = get_integration("codex")
manifest = IntegrationManifest("codex", project)
integration.setup(project, manifest, script_type="sh")
for name in ("discussion", "specify", "plan", "tasks", "implement", "quick", "debug"):
    skill = project / ".codex" / "skills" / f"sp-{name}" / "SKILL.md"
    refs = list((skill.parent / "references").glob("*.md"))
    print(name, skill.stat().st_size, len(refs))
'@ | python -
```

Expected: each target workflow prints a `SKILL.md` size and a reference count greater than 1.

- [ ] **Step 5: Remove temporary generated project**

Run:

```powershell
Remove-Item -LiteralPath tmp-skill-size-check -Recurse -Force
```

Expected: `tmp-skill-size-check` is removed.

- [ ] **Step 6: Inspect git status**

Run:

```powershell
git status --short
```

Expected: only intentional source, test, and template changes are present.

- [ ] **Step 7: Final commit if any verification-only fixes were needed**

If Step 6 shows uncommitted intentional fixes, commit them:

```powershell
git add src templates tests pyproject.toml
git commit -m "fix: stabilize workflow reference generation"
```

Expected: commit succeeds only when there are verification fixes. If there are no uncommitted changes, skip this step.

---

## Self-Review Checklist For The Implementer

- Every target workflow has an `INDEX.md` under its exact reference directory, such as `templates/command-references/discussion/INDEX.md`.
- Every generated skills-format workflow has `SKILL.md` plus `references/*.md`.
- Every generated reference sidecar has no `{SCRIPT}`, `{AGENT_SCRIPT}`, `{ARGS}`, `__AGENT__`, or `{{invoke:...}}`.
- Every non-skills migrated command contains `## Reference Contracts`.
- Every hard gate still has a visible summary in the main workflow template.
- Every moved rule has a coverage-ledger entry or is still visible in the main workflow template.
- Repair does not overwrite user-modified `SKILL.md` files or reference sidecars.
- Preset restore safely restores missing generated sidecars for core workflow skills.
- `templates/command-references` is packaged and mirrored into generated projects.
- `git diff --check` passes.
