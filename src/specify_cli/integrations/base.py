"""Base classes for AI-assistant integrations.

Provides:
- ``IntegrationOption`` — declares a CLI option an integration accepts.
- ``IntegrationBase`` — abstract base every integration must implement.
- ``MarkdownIntegration`` — concrete base for standard Markdown-format
  integrations (the common case — subclass, set three class attrs, done).
- ``TomlIntegration`` — concrete base for TOML-format integrations
  (Gemini, Tabnine — subclass, set three class attrs, done).
- ``SkillsIntegration`` — concrete base for integrations that install
  commands as agent skills (``sp-<name>/SKILL.md`` layout).
"""

from __future__ import annotations

import re
import shutil
from abc import ABC
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from specify_cli.orchestration import CapabilitySnapshot, describe_delegation_surface

if TYPE_CHECKING:
    from .manifest import IntegrationManifest


# ---------------------------------------------------------------------------
# IntegrationOption
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IntegrationOption:
    """Declares an option that an integration accepts via ``--integration-options``.

    Attributes:
        name:      The flag name (e.g. ``"--commands-dir"``).
        is_flag:   ``True`` for boolean flags (``--skills``).
        required:  ``True`` if the option must be supplied.
        default:   Default value when not supplied (``None`` → no default).
        help:      One-line description shown in ``specify integrate info``.
    """

    name: str
    is_flag: bool = False
    required: bool = False
    default: Any = None
    help: str = ""


# ---------------------------------------------------------------------------
# IntegrationBase — abstract base class
# ---------------------------------------------------------------------------

class IntegrationBase(ABC):
    """Abstract base class every integration must implement.

    Subclasses must set the following class-level attributes:

    * ``key``              — unique identifier, matches actual CLI tool name
    * ``config``           — dict compatible with ``AGENT_CONFIG`` entries
    * ``registrar_config`` — dict compatible with ``CommandRegistrar.AGENT_CONFIGS``

    And may optionally set:

    * ``context_file``     — path (relative to project root) of the agent
                             context/instructions file (e.g. ``"CLAUDE.md"``)
    """

    # -- Must be set by every subclass ------------------------------------

    key: str = ""
    """Unique integration key — should match the actual CLI tool name."""

    config: dict[str, Any] | None = None
    """Metadata dict matching the ``AGENT_CONFIG`` shape."""

    registrar_config: dict[str, Any] | None = None
    """Registration dict matching ``CommandRegistrar.AGENT_CONFIGS`` shape."""

    # -- Optional ---------------------------------------------------------

    context_file: str | None = None
    """Relative path to the agent context file (e.g. ``CLAUDE.md``)."""

    # -- Public API -------------------------------------------------------

    @classmethod
    def options(cls) -> list[IntegrationOption]:
        """Return options this integration accepts. Default: none."""
        return []

    # -- Primitives — building blocks for setup() -------------------------

    def shared_commands_dir(self) -> Path | None:
        """Return path to the shared command templates directory.

        Checks ``core_pack/commands/`` (wheel install) first, then
        ``templates/commands/`` (source checkout).  Returns ``None``
        if neither exists.
        """
        import inspect

        pkg_dir = Path(inspect.getfile(IntegrationBase)).resolve().parent.parent
        for candidate in [
            pkg_dir / "core_pack" / "commands",
            pkg_dir.parent.parent / "templates" / "commands",
        ]:
            if candidate.is_dir():
                return candidate
        return None

    def shared_templates_dir(self) -> Path | None:
        """Return path to the shared page templates directory.

        Contains ``vscode-settings.json``, ``spec-template.md``, etc.
        Checks ``core_pack/templates/`` then ``templates/``.
        """
        import inspect

        pkg_dir = Path(inspect.getfile(IntegrationBase)).resolve().parent.parent
        for candidate in [
            pkg_dir / "core_pack" / "templates",
            pkg_dir.parent.parent / "templates",
        ]:
            if candidate.is_dir():
                return candidate
        return None

    def list_command_templates(self) -> list[Path]:
        """Return sorted list of command template files from the shared directory."""
        cmd_dir = self.shared_commands_dir()
        if not cmd_dir or not cmd_dir.is_dir():
            return []
        return sorted(
            f
            for f in cmd_dir.iterdir()
            if f.is_file() and f.suffix == ".md" and f.name != "team.md"
        )

    def command_filename(self, template_name: str) -> str:
        """Return the destination filename for a command template.

        *template_name* is the stem of the source file (e.g. ``"plan"``).
        Default: ``sp.{template_name}.md``.  Subclasses override
        to change the extension or naming convention.
        """
        return f"sp.{template_name}.md"

    def commands_dest(self, project_root: Path) -> Path:
        """Return the absolute path to the commands output directory.

        Derived from ``config["folder"]`` and ``config["commands_subdir"]``.
        Raises ``ValueError`` if ``config`` or ``folder`` is missing.
        """
        if not self.config:
            raise ValueError(
                f"{type(self).__name__}.config is not set; integration "
                "subclasses must define a non-empty 'config' mapping."
            )
        folder = self.config.get("folder")
        if not folder:
            raise ValueError(
                f"{type(self).__name__}.config is missing required 'folder' entry."
            )
        subdir = self.config.get("commands_subdir", "commands")
        return project_root / folder / subdir

    # -- File operations — granular primitives for setup() ----------------

    @staticmethod
    def copy_command_to_directory(
        src: Path,
        dest_dir: Path,
        filename: str,
    ) -> Path:
        """Copy a command template to *dest_dir* with the given *filename*.

        Creates *dest_dir* if needed.  Returns the absolute path of the
        written file.  The caller can post-process the file before
        recording it in the manifest.
        """
        dest_dir.mkdir(parents=True, exist_ok=True)
        dst = dest_dir / filename
        shutil.copy2(src, dst)
        return dst

    @staticmethod
    def record_file_in_manifest(
        file_path: Path,
        project_root: Path,
        manifest: IntegrationManifest,
    ) -> None:
        """Hash *file_path* and record it in *manifest*.

        *file_path* must be inside *project_root*.
        """
        rel = file_path.resolve().relative_to(project_root.resolve())
        manifest.record_existing(rel)

    @staticmethod
    def write_file_and_record(
        content: str,
        dest: Path,
        project_root: Path,
        manifest: IntegrationManifest,
    ) -> Path:
        """Write *content* to *dest*, hash it, and record in *manifest*.

        Creates parent directories as needed.  Writes bytes directly to
        avoid platform newline translation (CRLF on Windows).  Any
        ``\r\n`` sequences in *content* are normalised to ``\n`` before
        writing.  Returns *dest*.
        """
        dest.parent.mkdir(parents=True, exist_ok=True)
        normalized = content.replace("\r\n", "\n")
        dest.write_bytes(normalized.encode("utf-8"))
        rel = dest.resolve().relative_to(project_root.resolve())
        manifest.record_existing(rel)
        return dest

    def integration_scripts_dir(self) -> Path | None:
        """Return path to this integration's bundled ``scripts/`` directory.

        Looks for a ``scripts/`` sibling of the module that defines the
        concrete subclass (not ``IntegrationBase`` itself).
        Returns ``None`` if the directory doesn't exist.
        """
        import inspect

        cls_file = inspect.getfile(type(self))
        scripts = Path(cls_file).resolve().parent / "scripts"
        return scripts if scripts.is_dir() else None

    def install_scripts(
        self,
        project_root: Path,
        manifest: IntegrationManifest,
    ) -> list[Path]:
        """Copy integration-specific scripts into the project.

        Copies files from this integration's ``scripts/`` directory to
        ``.specify/integrations/<key>/scripts/`` in the project.  Shell
        scripts are made executable.  All copied files are recorded in
        *manifest*.

        Returns the list of files created.
        """
        scripts_src = self.integration_scripts_dir()
        if not scripts_src:
            return []

        created: list[Path] = []
        scripts_dest = project_root / ".specify" / "integrations" / self.key / "scripts"
        scripts_dest.mkdir(parents=True, exist_ok=True)

        for src_script in sorted(scripts_src.iterdir()):
            if not src_script.is_file():
                continue
            dst_script = scripts_dest / src_script.name
            shutil.copy2(src_script, dst_script)
            if dst_script.suffix == ".sh":
                dst_script.chmod(dst_script.stat().st_mode | 0o111)
            self.record_file_in_manifest(dst_script, project_root, manifest)
            created.append(dst_script)

        return created

    def _append_delegation_surface_contract(
        self,
        *,
        content: str,
        agent_name: str,
        command_name: str,
        snapshot: CapabilitySnapshot,
        heading: str,
    ) -> str:
        """Append a normalized delegation-surface contract section when absent."""

        marker = f"## {agent_name} {heading}"
        if marker in content:
            return content

        descriptor = describe_delegation_surface(
            command_name=command_name,
            snapshot=snapshot,
        )
        addendum = (
            "\n"
            f"## {agent_name} {heading}\n\n"
            f"- Native dispatch surface: {descriptor.native_dispatch_hint}\n"
            f"- Join behavior: {descriptor.native_join_hint}\n"
            f"- Sidecar fallback: {descriptor.sidecar_surface_hint}\n"
            f"- Result contract: {descriptor.result_contract_hint}\n"
            f"- Result handoff path: {descriptor.result_handoff_hint}\n"
        )
        return content + addendum

    @staticmethod
    def process_template(
        content: str,
        agent_name: str,
        script_type: str,
        arg_placeholder: str = "$ARGUMENTS",
    ) -> str:
        """Process a raw command template into agent-ready content.

        Performs the same transformations as the release script:
        1. Extract ``scripts.<script_type>`` value from YAML frontmatter
        2. Replace ``{SCRIPT}`` with the extracted script command
        3. Extract ``agent_scripts.<script_type>`` and replace ``{AGENT_SCRIPT}``
        4. Strip ``scripts:`` and ``agent_scripts:`` sections from frontmatter
        5. Replace ``{ARGS}`` with *arg_placeholder*
        6. Replace ``__AGENT__`` with *agent_name*
        7. Rewrite paths: ``scripts/`` → ``.specify/scripts/`` etc.
        """
        # 1. Extract script command from frontmatter
        script_command = ""
        script_pattern = re.compile(
            rf"^\s*{re.escape(script_type)}:\s*(.+)$", re.MULTILINE
        )
        # Find the scripts: block
        in_scripts = False
        for line in content.splitlines():
            if line.strip() == "scripts:":
                in_scripts = True
                continue
            if in_scripts and line and not line[0].isspace():
                in_scripts = False
            if in_scripts:
                m = script_pattern.match(line)
                if m:
                    script_command = m.group(1).strip()
                    break

        # 2. Replace {SCRIPT}
        if script_command:
            content = content.replace("{SCRIPT}", script_command)

        # 3. Extract agent_script command
        agent_script_command = ""
        in_agent_scripts = False
        for line in content.splitlines():
            if line.strip() == "agent_scripts:":
                in_agent_scripts = True
                continue
            if in_agent_scripts and line and not line[0].isspace():
                in_agent_scripts = False
            if in_agent_scripts:
                m = script_pattern.match(line)
                if m:
                    agent_script_command = m.group(1).strip()
                    break

        if agent_script_command:
            content = content.replace("{AGENT_SCRIPT}", agent_script_command)

        # 4. Strip scripts: and agent_scripts: sections from frontmatter
        lines = content.splitlines(keepends=True)
        output_lines: list[str] = []
        in_frontmatter = False
        skip_section = False
        dash_count = 0
        for line in lines:
            stripped = line.rstrip("\n\r")
            if stripped == "---":
                dash_count += 1
                if dash_count == 1:
                    in_frontmatter = True
                else:
                    in_frontmatter = False
                skip_section = False
                output_lines.append(line)
                continue
            if in_frontmatter:
                if stripped in ("scripts:", "agent_scripts:"):
                    skip_section = True
                    continue
                if skip_section:
                    if line[0:1].isspace():
                        continue  # skip indented content under scripts/agent_scripts
                    skip_section = False
            output_lines.append(line)
        content = "".join(output_lines)

        # 5. Replace {ARGS}
        content = content.replace("{ARGS}", arg_placeholder)

        # 6. Replace __AGENT__
        content = content.replace("__AGENT__", agent_name)

        # 7. Rewrite paths — delegate to the shared implementation in
        #    CommandRegistrar so extension-local paths are preserved and
        #    boundary rules stay consistent across the codebase.
        from specify_cli.agents import CommandRegistrar
        content = CommandRegistrar.rewrite_project_relative_paths(content)

        return content

    def setup(
        self,
        project_root: Path,
        manifest: IntegrationManifest,
        parsed_options: dict[str, Any] | None = None,
        **opts: Any,
    ) -> list[Path]:
        """Install integration command files into *project_root*.

        Returns the list of files created.  Copies raw templates without
        processing.  Integrations that need placeholder replacement
        (e.g. ``{SCRIPT}``, ``__AGENT__``) should override ``setup()``
        and call ``process_template()`` in their own loop — see
        ``CopilotIntegration`` for an example.
        """
        templates = self.list_command_templates()
        if not templates:
            return []

        project_root_resolved = project_root.resolve()
        if manifest.project_root != project_root_resolved:
            raise ValueError(
                f"manifest.project_root ({manifest.project_root}) does not match "
                f"project_root ({project_root_resolved})"
            )

        dest = self.commands_dest(project_root).resolve()
        try:
            dest.relative_to(project_root_resolved)
        except ValueError as exc:
            raise ValueError(
                f"Integration destination {dest} escapes "
                f"project root {project_root_resolved}"
            ) from exc

        created: list[Path] = []

        for src_file in templates:
            dst_name = self.command_filename(src_file.stem)
            dst_file = self.copy_command_to_directory(src_file, dest, dst_name)
            self.record_file_in_manifest(dst_file, project_root, manifest)
            created.append(dst_file)

        return created

    def teardown(
        self,
        project_root: Path,
        manifest: IntegrationManifest,
        *,
        force: bool = False,
    ) -> tuple[list[Path], list[Path]]:
        """Uninstall integration files from *project_root*.

        Delegates to ``manifest.uninstall()`` which only removes files
        whose hash still matches the recorded value (unless *force*).

        Returns ``(removed, skipped)`` file lists.
        """
        return manifest.uninstall(project_root, force=force)

    # -- Convenience helpers for subclasses -------------------------------

    def install(
        self,
        project_root: Path,
        manifest: IntegrationManifest,
        parsed_options: dict[str, Any] | None = None,
        **opts: Any,
    ) -> list[Path]:
        """High-level install — calls ``setup()`` and returns created files."""
        return self.setup(
            project_root, manifest, parsed_options=parsed_options, **opts
        )

    def uninstall(
        self,
        project_root: Path,
        manifest: IntegrationManifest,
        *,
        force: bool = False,
    ) -> tuple[list[Path], list[Path]]:
        """High-level uninstall — calls ``teardown()``."""
        return self.teardown(project_root, manifest, force=force)


# ---------------------------------------------------------------------------
# MarkdownIntegration — covers ~20 standard agents
# ---------------------------------------------------------------------------

class MarkdownIntegration(IntegrationBase):
    """Concrete base for integrations that use standard Markdown commands.

    Subclasses only need to set ``key``, ``config``, ``registrar_config``
    (and optionally ``context_file``).  Everything else is inherited.

    ``setup()`` processes command templates (replacing ``{SCRIPT}``,
    ``{ARGS}``, ``__AGENT__``, rewriting paths) and installs
    integration-specific scripts (``update-context.sh`` / ``.ps1``).
    """

    def setup(
        self,
        project_root: Path,
        manifest: IntegrationManifest,
        parsed_options: dict[str, Any] | None = None,
        **opts: Any,
    ) -> list[Path]:
        templates = self.list_command_templates()
        if not templates:
            return []

        project_root_resolved = project_root.resolve()
        if manifest.project_root != project_root_resolved:
            raise ValueError(
                f"manifest.project_root ({manifest.project_root}) does not match "
                f"project_root ({project_root_resolved})"
            )

        dest = self.commands_dest(project_root).resolve()
        try:
            dest.relative_to(project_root_resolved)
        except ValueError as exc:
            raise ValueError(
                f"Integration destination {dest} escapes "
                f"project root {project_root_resolved}"
            ) from exc
        dest.mkdir(parents=True, exist_ok=True)

        script_type = opts.get("script_type", "sh")
        arg_placeholder = self.registrar_config.get("args", "$ARGUMENTS") if self.registrar_config else "$ARGUMENTS"
        created: list[Path] = []

        for src_file in templates:
            raw = src_file.read_text(encoding="utf-8")
            processed = self.process_template(raw, self.key, script_type, arg_placeholder)
            dst_name = self.command_filename(src_file.stem)
            dst_file = self.write_file_and_record(
                processed, dest / dst_name, project_root, manifest
            )
            created.append(dst_file)

        created.extend(self.install_scripts(project_root, manifest))
        return created


# ---------------------------------------------------------------------------
# TomlIntegration — TOML-format agents (Gemini, Tabnine)
# ---------------------------------------------------------------------------

class TomlIntegration(IntegrationBase):
    """Concrete base for integrations that use TOML command format.

    Mirrors ``MarkdownIntegration`` closely: subclasses only need to set
    ``key``, ``config``, ``registrar_config`` (and optionally
    ``context_file``).  Everything else is inherited.

    ``setup()`` processes command templates through the same placeholder
    pipeline as ``MarkdownIntegration``, then converts the result to
    TOML format (``description`` key + ``prompt`` multiline string).
    """

    def command_filename(self, template_name: str) -> str:
        """TOML commands use ``.toml`` extension."""
        return f"sp.{template_name}.toml"

    @staticmethod
    def _extract_description(content: str) -> str:
        """Extract the ``description`` value from YAML frontmatter.

        Parses the YAML frontmatter so block scalar descriptions (``|``
        and ``>``) keep their YAML semantics instead of being treated as
        raw text.
        """
        import yaml

        frontmatter_text, _ = TomlIntegration._split_frontmatter(content)
        if not frontmatter_text:
            return ""
        try:
            frontmatter = yaml.safe_load(frontmatter_text) or {}
        except yaml.YAMLError:
            return ""

        if not isinstance(frontmatter, dict):
            return ""

        description = frontmatter.get("description", "")
        if isinstance(description, str):
            return description
        return ""

    @staticmethod
    def _split_frontmatter(content: str) -> tuple[str, str]:
        """Split YAML frontmatter from the remaining content.

        Returns ``("", content)`` when no complete frontmatter block is
        present. The body is preserved exactly as written so prompt text
        keeps its intended formatting.
        """
        if not content.startswith("---"):
            return "", content

        lines = content.splitlines(keepends=True)
        if not lines or lines[0].rstrip("\r\n") != "---":
            return "", content

        frontmatter_end = -1
        for i, line in enumerate(lines[1:], start=1):
            if line.rstrip("\r\n") == "---":
                frontmatter_end = i
                break

        if frontmatter_end == -1:
            return "", content

        frontmatter = "".join(lines[1:frontmatter_end])
        body = "".join(lines[frontmatter_end + 1 :])
        return frontmatter, body

    @staticmethod
    def _render_toml_string(value: str) -> str:
        """Render *value* as a TOML string literal.

        Uses a basic string for single-line values. Multiline values are
        emitted as multiline basic strings with explicit escaping and
        leading/trailing line trimming so the parsed value matches the
        original exactly while keeping the closing delimiter on its own
        line for parser compatibility.
        """
        if "\n" not in value and "\r" not in value:
            escaped = (
                value.replace("\\", "\\\\")
                .replace('"', '\\"')
                .replace("\r", "\\r")
                .replace("\t", "\\t")
            )
            return f'"{escaped}"'

        escaped = (
            value.replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\r", "\\r")
            .replace("\t", "\\t")
        )
        return '"""\\\n' + escaped + '\\\n"""'

    @staticmethod
    def _render_toml(description: str, body: str) -> str:
        """Render a TOML command file from description and body.

        The body is ``rstrip("\\n")``'d before rendering, so the TOML
        value preserves content without forcing a trailing newline.
        """
        toml_lines: list[str] = []

        if description:
            toml_lines.append(f"description = {TomlIntegration._render_toml_string(description)}")
            toml_lines.append("")

        body = body.rstrip("\n")
        toml_lines.append(f"prompt = {TomlIntegration._render_toml_string(body)}")

        return "\n".join(toml_lines) + "\n"

    def setup(
        self,
        project_root: Path,
        manifest: IntegrationManifest,
        parsed_options: dict[str, Any] | None = None,
        **opts: Any,
    ) -> list[Path]:
        templates = self.list_command_templates()
        if not templates:
            return []

        project_root_resolved = project_root.resolve()
        if manifest.project_root != project_root_resolved:
            raise ValueError(
                f"manifest.project_root ({manifest.project_root}) does not match "
                f"project_root ({project_root_resolved})"
            )

        dest = self.commands_dest(project_root).resolve()
        try:
            dest.relative_to(project_root_resolved)
        except ValueError as exc:
            raise ValueError(
                f"Integration destination {dest} escapes "
                f"project root {project_root_resolved}"
            ) from exc
        dest.mkdir(parents=True, exist_ok=True)

        script_type = opts.get("script_type", "sh")
        arg_placeholder = self.registrar_config.get("args", "{{args}}") if self.registrar_config else "{{args}}"
        created: list[Path] = []

        for src_file in templates:
            raw = src_file.read_text(encoding="utf-8")
            description = self._extract_description(raw)
            processed = self.process_template(raw, self.key, script_type, arg_placeholder)
            _, body = self._split_frontmatter(processed)
            toml_content = self._render_toml(description, body)
            dst_name = self.command_filename(src_file.stem)
            dst_file = self.write_file_and_record(
                toml_content, dest / dst_name, project_root, manifest
            )
            created.append(dst_file)

        created.extend(self.install_scripts(project_root, manifest))
        return created


# ---------------------------------------------------------------------------
# SkillsIntegration — skills-format agents (Codex, Kimi, Agy)
# ---------------------------------------------------------------------------


class SkillsIntegration(IntegrationBase):
    """Concrete base for integrations that install commands as agent skills.

    Skills use the ``sp-<name>/SKILL.md`` directory layout following
    the `agentskills.io <https://agentskills.io/specification>`_ spec.

    Subclasses set ``key``, ``config``, ``registrar_config`` (and
    optionally ``context_file``) like any integration.  They may also
    override ``options()`` to declare additional CLI flags (e.g.
    ``--skills``, ``--migrate-legacy``).

    ``setup()`` processes each shared command template into a
    ``sp-<name>/SKILL.md`` file with skills-oriented frontmatter.
    """

    def skills_dest(self, project_root: Path) -> Path:
        """Return the absolute path to the skills output directory.

        Derived from ``config["folder"]`` and the configured
        ``commands_subdir`` (defaults to ``"skills"``).

        Raises ``ValueError`` when ``config`` or ``folder`` is missing.
        """
        if not self.config:
            raise ValueError(
                f"{type(self).__name__}.config is not set."
            )
        folder = self.config.get("folder")
        if not folder:
            raise ValueError(
                f"{type(self).__name__}.config is missing required 'folder' entry."
            )
        subdir = self.config.get("commands_subdir", "skills")
        return project_root / folder / subdir

    def setup(
        self,
        project_root: Path,
        manifest: IntegrationManifest,
        parsed_options: dict[str, Any] | None = None,
        **opts: Any,
    ) -> list[Path]:
        """Install command templates as agent skills.

        Creates ``sp-<name>/SKILL.md`` for each shared command
        template.  Each SKILL.md has normalised frontmatter containing
        ``name``, ``description``, ``compatibility``, and ``metadata``.
        """
        import yaml

        templates = self.list_command_templates()
        if not templates:
            return []

        project_root_resolved = project_root.resolve()
        if manifest.project_root != project_root_resolved:
            raise ValueError(
                f"manifest.project_root ({manifest.project_root}) does not match "
                f"project_root ({project_root_resolved})"
            )

        skills_dir = self.skills_dest(project_root).resolve()
        try:
            skills_dir.relative_to(project_root_resolved)
        except ValueError as exc:
            raise ValueError(
                f"Skills destination {skills_dir} escapes "
                f"project root {project_root_resolved}"
            ) from exc

        script_type = opts.get("script_type", "sh")
        arg_placeholder = (
            self.registrar_config.get("args", "$ARGUMENTS")
            if self.registrar_config
            else "$ARGUMENTS"
        )
        created: list[Path] = []

        for src_file in templates:
            raw = src_file.read_text(encoding="utf-8")

            # Derive the skill name from the template stem
            command_name = src_file.stem  # e.g. "plan"
            skill_name = f"sp-{command_name.replace('.', '-')}"

            # Parse frontmatter for description
            frontmatter: dict[str, Any] = {}
            if raw.startswith("---"):
                parts = raw.split("---", 2)
                if len(parts) >= 3:
                    try:
                        fm = yaml.safe_load(parts[1])
                        if isinstance(fm, dict):
                            frontmatter = fm
                    except yaml.YAMLError:
                        pass

            # Process body through the standard template pipeline
            processed_body = self.process_template(
                raw, self.key, script_type, arg_placeholder
            )
            # Strip the processed frontmatter — we rebuild it for skills.
            # Preserve leading whitespace in the body to match release ZIP
            # output byte-for-byte (the template body starts with \n after
            # the closing ---).
            if processed_body.startswith("---"):
                parts = processed_body.split("---", 2)
                if len(parts) >= 3:
                    processed_body = parts[2]

            # Select description — use the original template description
            # to stay byte-for-byte identical with release ZIP output.
            description = frontmatter.get("description", "")
            if not description:
                description = f"Spec Kit: {command_name} workflow"

            # Build SKILL.md with manually formatted frontmatter to match
            # the release packaging script output exactly (double-quoted
            # values, no yaml.safe_dump quoting differences).
            def _quote(v: str) -> str:
                escaped = v.replace("\\", "\\\\").replace('"', '\\"')
                return f'"{escaped}"'

            skill_content = (
                f"---\n"
                f"name: {_quote(skill_name)}\n"
                f"description: {_quote(description)}\n"
                f"compatibility: {_quote('Requires spec-kit project structure with .specify/ directory')}\n"
                f"metadata:\n"
                f"  author: {_quote('github-spec-kit')}\n"
                f"  source: {_quote('templates/commands/' + src_file.name)}\n"
                f"---\n"
                f"{processed_body}"
            )

            # Write sp-<name>/SKILL.md
            skill_dir = skills_dir / skill_name
            skill_file = skill_dir / "SKILL.md"
            dst = self.write_file_and_record(
                skill_content, skill_file, project_root, manifest
            )
            created.append(dst)

        self.augment_generated_skills(
            created,
            project_root,
            manifest,
            skills_dir,
        )

        created.extend(self.install_scripts(project_root, manifest))
        return created

    def augment_generated_skills(
        self,
        created: list[Path],
        project_root: Path,
        manifest: IntegrationManifest,
        skills_dir: Path,
    ) -> None:
        """Hook for integration-specific post-processing of generated skills."""
        return None

    def _augment_shared_skill(
        self,
        created: list[Path],
        project_root: Path,
        manifest: IntegrationManifest,
        skill_path: Path,
        marker: str,
        addendum: str,
    ) -> None:
        """Append an integration-specific addendum to a shared skill if it matches the marker."""
        if skill_path not in created or not skill_path.is_file():
            return
        content = skill_path.read_text(encoding="utf-8")
        if marker in content:
            return
        self.write_file_and_record(content + addendum, skill_path, project_root, manifest)

    def _augment_implement_skill(
        self,
        created: list[Path],
        project_root: Path,
        manifest: IntegrationManifest,
        implement_skill: Path,
        snapshot: CapabilitySnapshot | None = None,
    ) -> None:
        """Inject Leader Gate and Auto-Parallel guidance into the implement skill."""
        if implement_skill not in created or not implement_skill.is_file():
            return

        content = implement_skill.read_text(encoding="utf-8")
        agent_name_full = self.config.get("name", self.key.capitalize())
        agent_name = agent_name_full.replace(" CLI", "")

        gate_marker = f"## {agent_name} Leader Gate"
        if gate_marker not in content:
            gate_addendum = (
                "\n"
                f"## {agent_name} Leader Gate\n\n"
                f"When running `sp-implement` in {agent_name}, you are the **leader**, not the concrete implementer.\n"
                "\n"
                "**Crucial First Step**: You MUST read `PROJECT-HANDBOOK.md` and relevant `.specify/project-map/*.md` files to understand the architectural boundaries and conventions before any implementation actions.\n"
                "\n"
                "**Autonomous Blocker Recovery (Hard Rule)**:\n"
                "- If technical blockers arise (e.g. build errors, missing toolchain components like Win32/x86, environment mismatches), you **MUST** attempt autonomous escalation to a specialist sub-agent (e.g. `cpp-build-resolver`) **BEFORE** asking the user for intervention.\n"
                "- Only stop and ask the user if the specialist agent confirms that manual human action (like physical installer execution) is the ONLY remaining path.\n"
                "\n"
                "Before any code edits, test edits, build commands, or implementation actions:\n"
                "- Read `FEATURE_DIR/implement-tracker.md` first if it exists, and resume from its recorded blocker, recovery, replanning, or validation state before choosing a new batch.\n"
                "- **Audit Missed Dispatches**: If you find tasks in the tracker that you performed yourself but could have been delegated, record them under a `missed_agent_dispatch` field in the tracker as a recovery debt.\n"
                "- If `$ARGUMENTS` is non-empty, extract the important execution constraints or recovery hints from it and persist them under `## User Execution Notes` in `FEATURE_DIR/implement-tracker.md` before dispatching work.\n"
                "- Read `tasks.md`, identify the current ready batch, and choose the execution strategy for that batch.\n"
                "- Before any delegated implementation work starts, compile and validate the packet for the current task or batch item.\n"
                "- If the selected strategy is `native-multi-agent`, you **MUST** delegate the concrete work through `spawn_agent` worker lanes before considering any fallback path.\n"
                "- If the selected strategy is `sidecar-runtime`, or if native worker delegation proves concretely unavailable for the current batch, you **MUST** call **`specify team auto-dispatch --feature-dir \"<FEATURE_DIR>\"`** before doing any concrete implementation work yourself.\n"
                "- Do **not** fall through from worker delegation or sidecar fallback into local self-execution just because the implementation looks feasible.\n"
                "- `single-agent` still means one delegated worker lane, not leader self-execution.\n"
                "- Dispatch only from validated `WorkerTaskPacket`.\n"
                "\n"
                "**Hard rule:** The leader must not edit implementation files directly while worker delegation is active or while `sidecar-runtime` is selected.\n"
            )
            if "## Outline" in content:
                content = content.replace("## Outline", gate_addendum + "\n## Outline", 1)
            else:
                content += gate_addendum

        marker = f"## {agent_name} Auto-Parallel Execution"
        if marker not in content:
            addendum = (
                "\n"
                f"## {agent_name} Auto-Parallel Execution\n\n"
                f"When running `sp-implement` in {agent_name}, treat Step 6's unified execution strategy selection as a runtime-aware escalation.\n"
                "\n"
                "**Standard Dispatch Scenarios**:\n"
                "1. **Parallel Creation**: If current batch has [P] markers or creates >3 new files -> Use `native-multi-agent`.\n"
                "2. **Build/Compile Failures**: If commands return non-zero exit codes -> Dispatch `cpp-build-resolver` or specialist agent.\n"
                "3. **Testing Tasks**: If paths involve `tests/` or `*_test.*` -> Dispatch `tdd-guide` or build specialist.\n"
                "4. **Cross-module Dependency**: If task affects >2 different directories -> Use `single-agent` workers per module.\n"
                "\n"
                "For each ready parallel batch:\n"
                "- The invoking runtime acts as the leader: it reads the current planning artifacts, selects the next executable phase and ready batch, and dispatches work instead of performing concrete implementation directly.\n"
                f"- Keep the shared strategy names and workload-safety checks, but for {agent_name} `sp-implement` prefer `native-multi-agent` whenever `snapshot.native_multi_agent` is true.\n"
                f"- Use `spawn_agent` to delegate disjoint worker lanes for the current batch, `wait_agent` to join them, and `close_agent` after integrating results.\n"
                "- Interpret `single-agent` as one delegated worker lane, not leader self-execution.\n"
                "- Interpret `native-multi-agent` as the native subagents path.\n"
                "- Interpret `sidecar-runtime` as escalation via **`specify team`** only after native worker delegation is unavailable or unsuitable for the current batch.\n"
                f"- Decision order for {agent_name} `sp-implement` must stay fixed: `no-safe-batch` -> `native-preferred` -> `sidecar-fallback` -> `fallback`.\n"
                "- Only fall back to `specify team` after a concrete blocker shows that the current batch cannot proceed through native worker delegation.\n"
                "- Re-check the strategy after every join point instead of assuming the first choice still applies.\n"
                "- The leader delegates execution through these worker paths rather than executing the implementation itself.\n"
                "- After each completed batch, the leader re-evaluates milestone state, selects the next executable phase and ready batch in roadmap order, and continues automatically until the milestone is complete or blocked.\n"
            )
            content += addendum

        if snapshot is not None:
            content = self._append_delegation_surface_contract(
                content=content,
                agent_name=agent_name,
                command_name="implement",
                snapshot=snapshot,
                heading="Delegation Surface Contract",
            )

        self.write_file_and_record(content, implement_skill, project_root, manifest)

    def _augment_debug_skill(
        self,
        created: list[Path],
        project_root: Path,
        manifest: IntegrationManifest,
        debug_skill: Path,
        snapshot: CapabilitySnapshot | None = None,
    ) -> None:
        """Inject Leader Gate and evidence collection guidance into the debug skill."""
        if debug_skill not in created or not debug_skill.is_file():
            return

        content = debug_skill.read_text(encoding="utf-8")
        agent_name_full = self.config.get("name", self.key.capitalize())
        agent_name = agent_name_full.replace(" CLI", "")

        gate_marker = f"## {agent_name} Leader Gate"
        if gate_marker not in content:
            gate_addendum = (
                "\n"
                f"## {agent_name} Leader Gate\n\n"
                f"When running `sp-debug` in {agent_name}, you are the **leader**, not a freeform debugger.\n"
                "\n"
                "**Crucial First Step**: You MUST read `PROJECT-HANDBOOK.md` and relevant `.specify/project-map/*.md` files to understand the architectural boundaries and conventions before any investigation or fixes.\n"
                "\n"
                "Before applying fixes or running multiple independent investigation actions yourself:\n"
                "- Read the current debug session state and identify whether the investigation has two or more independent evidence-gathering lanes.\n"
                f"- If the current stage is `investigating` and there are two or more bounded evidence-gathering lanes, you **MUST** delegate them through `spawn_agent` before continuing with more sequential evidence collection yourself.\n"
                f"- Use `wait_agent` at the investigation join point, integrate returned results, and call `close_agent` for completed child agents.\n"
                "- Do **not** skip delegation just because the evidence tasks look easy; use the lighter `single-agent` path only when the current investigation does not have safe parallel lanes.\n"
                "\n"
                "**Hard rule:** During `investigating`, the leader must not let child agents mutate the debug file, declare the root cause final, or advance the session state.\n"
            )
            if "## Session Lifecycle" in content:
                content = content.replace("## Session Lifecycle", gate_addendum + "\n## Session Lifecycle", 1)
            else:
                content += gate_addendum

        marker = f"## {agent_name} Native Multi-Agent Investigation"
        if marker in content:
            return

        addendum = (
            "\n"
            f"## {agent_name} Native Multi-Agent Investigation\n\n"
            f"When running `sp-debug` in {agent_name}, treat the `investigating` stage as a leader-led routing decision between `single-agent` and native delegated evidence collection.\n"
            f"- If there are two or more independent evidence-gathering lanes, prefer native delegation through `spawn_agent` over manual sequential investigation.\n"
            "- Suitable child tasks include running targeted tests or repro commands, collecting logs and exit codes, searching for error text, tracing isolated code paths, and gathering evidence after diagnostic logging has been added.\n"
            "- Read `diagnostic_profile` from the debug session before choosing child lanes.\n"
            "- The leader **MUST** update the debug file's `Current Focus` before delegating and treat child work as evidence collection for the current hypothesis.\n"
            "- Child agents must return facts, command results, and observations; they must not update the debug file, declare the root cause final, or transition the session state.\n"
            f"- Use `wait_agent` only after the current investigation fan-out reaches its join point.\n"
            f"- Use `close_agent` after integrating finished child results.\n"
            "- Keep fixing, verification, `awaiting_human_verify`, and final session resolution on the leader path.\n"
        )

        content = content + addendum
        if snapshot is not None:
            content = self._append_delegation_surface_contract(
                content=content,
                agent_name=agent_name,
                command_name="debug",
                snapshot=snapshot,
                heading="Delegation Surface Contract",
            )

        self.write_file_and_record(content, debug_skill, project_root, manifest)

    def _augment_quick_skill(
        self,
        created: list[Path],
        project_root: Path,
        manifest: IntegrationManifest,
        quick_skill: Path,
        snapshot: CapabilitySnapshot | None = None,
    ) -> None:
        """Inject Leader Gate and delegation guidance into the quick-task skill."""
        if quick_skill not in created or not quick_skill.is_file():
            return

        content = quick_skill.read_text(encoding="utf-8")
        agent_name_full = self.config.get("name", self.key.capitalize())
        agent_name = agent_name_full.replace(" CLI", "")

        gate_marker = f"## {agent_name} Leader Gate"
        if gate_marker not in content:
            gate_addendum = (
                "\n"
                f"## {agent_name} Leader Gate\n\n"
                f"When running `sp-quick` in {agent_name}, you are the **leader**, not the concrete implementer.\n"
                "\n"
                "**Crucial First Step**: You MUST read `PROJECT-HANDBOOK.md` and relevant `.specify/project-map/*.md` files to understand the architectural boundaries and conventions before repository analysis or implementation.\n"
                "\n"
                "Before code edits, test edits, or implementation commands:\n"
                "- Read `.specify/memory/constitution.md` first if it exists.\n"
                "- Read `STATUS.md` for the active quick-task workspace, or create it if this quick task is new.\n"
                "- Define the smallest safe execution lane or ready batch, and choose the execution strategy for that batch.\n"
                "- `single-agent` still means one delegated worker lane. Do **not** reinterpret it as leader self-execution.\n"
                f"- If the selected strategy is `native-multi-agent`, you **MUST** delegate the concrete work through `spawn_agent` worker lanes before considering any fallback path.\n"
                "- If the selected strategy is `single-agent`, you **MUST** dispatch exactly one delegated worker lane before considering any leader-local fallback.\n"
                "- If two or more safe delegated lanes would materially improve throughput, you **MUST** prefer launching them in parallel.\n"
                f"- Use `wait_agent` only at the current join point, integrate returned results, and call `close_agent` for completed workers.\n"
                f"- If the selected strategy is `sidecar-runtime`, or if native worker delegation proves concretely unavailable for the current batch, you **MUST** call **`specify team auto-dispatch`** for the quick-task workload before doing concrete implementation work yourself.\n"
                "- Leader-local execution is allowed only when native worker delegation is concretely unavailable and the sidecar runtime path is also unavailable.\n"
                "- When leader-local fallback is used, you **MUST** write the concrete fallback reason into `STATUS.md` before executing locally.\n"
                "\n"
                "**Hard rule:** The leader must keep scope control, strategy selection, join-point handling, validation, summary ownership, and `STATUS.md` accuracy while delegated execution is active.\n"
            )
            if "## Process" in content:
                content = content.replace("## Process", gate_addendum + "\n## Process", 1)
            else:
                content += gate_addendum

        marker = f"## {agent_name} Native Multi-Agent Execution"
        if marker in content:
            if snapshot is not None:
                content = self._append_delegation_surface_contract(
                    content=content,
                    agent_name=agent_name,
                    command_name="quick",
                    snapshot=snapshot,
                    heading="Delegation Surface Contract",
                )
            self.write_file_and_record(content, quick_skill, project_root, manifest)
            return

        addendum = (
            "\n"
            f"## {agent_name} Native Multi-Agent Execution\n\n"
            f"When running `sp-quick` in {agent_name}, prefer native worker delegation whenever the selected quick-task strategy is `native-multi-agent`.\n"
            f"- Use `spawn_agent` (or native handoffs) for bounded lanes such as focused repository analysis, targeted implementation, regression test updates, or validation command runs.\n"
            "- Once the first lane is chosen, dispatch it before continuing any leader-local deep-dive analysis of the repository.\n"
            "- If multiple safe worker lanes exist and they materially improve throughput, dispatch them in parallel.\n"
            f"- Use `wait_agent` only at the documented join point for the current quick-task batch.\n"
            f"- Use `close_agent` after integrating finished worker results.\n"
            "- Keep `.planning/quick/<id>-<slug>/STATUS.md` as the leader-owned source of truth.\n"
            "- Child agents may return evidence, patches, and verification output, but they must not become the authority for resume state; the leader updates `STATUS.md` before and after each join point.\n"
            f"- Decision order for {agent_name} `sp-quick`: `no-safe-batch` -> `native-preferred` -> `sidecar-fallback` -> `fallback`.\n"
            "- Interpret `single-agent` as one delegated worker lane, not leader self-execution.\n"
            "- Interpret `native-multi-agent` as the native subagents path.\n"
            "- Interpret `sidecar-runtime` as escalation via **`specify team`** only after native worker delegation is unavailable or unsuitable.\n"
            "- Re-check strategy after every join point and continue automatically until the quick task is complete or blocked.\n"
        )

        content = content + addendum
        if snapshot is not None:
            content = self._append_delegation_surface_contract(
                content=content,
                agent_name=agent_name,
                command_name="quick",
                snapshot=snapshot,
                heading="Delegation Surface Contract",
            )

        self.write_file_and_record(content, quick_skill, project_root, manifest)
