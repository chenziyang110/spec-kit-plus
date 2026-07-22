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

import importlib
import inspect
import json
import re
import shutil
from abc import ABC
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

from specify_cli.orchestration import CapabilitySnapshot, describe_delegation_surface

if TYPE_CHECKING:
    from .manifest import IntegrationManifest


EPISTEMIC_CONTRACT_GUIDANCE = (
    "Read and carry `epistemic_contract`; require `graph_role=route_candidate_only`, "
    "`fact_source_of_truth=live_repository`, `live_verification_required=true`, "
    "`graph_only_claims_allowed=false`, and `unverified_claim_action=withhold`. "
    "The contract cannot authorize source changes and cannot prove current behavior; "
    "contradictory live evidence overrides the route candidate. Graph claims are indexed assertions; "
    "even `verified_in_graph_generation` is only an active graph-generation state, not current repository truth. "
    "Graph claims cannot authorize source changes and cannot set workflow `claim_ready=true`; bounded live evidence "
    "and the separate workflow final-claim gate remain required."
)


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

    question_tool_config: dict[str, Any] | None = None
    """Optional structured-question-tool metadata for the integration."""

    MAP_SUBAGENT_DISCOVERY_COMMANDS = frozenset({"map-scan", "map-build", "map-update"})
    ADVANCED_CLASSIC_COMPANION_COMMANDS = frozenset(
        {"map-scan", "map-build", "map-update"}
    )
    RUNTIME_SUBAGENT_CONTRACT_COMMANDS = frozenset(
        {"implement", "review", "debug", "quick"}
    )
    SUBAGENT_DISCOVERY_EXCLUDED_COMMANDS = frozenset({"fast"})
    PROJECT_COGNITION_WORKFLOW_TOKEN = "{{project-cognition-workflow}}"
    PROJECT_COGNITION_WORKFLOW_REGISTRY = (
        "project-cognition-workflow-registry.json"
    )
    PROJECT_COGNITION_WORKFLOW_MODES = frozenset(
        {
            "mutation_closeout",
            "map_maintenance",
            "baseline_maintenance",
            "no_closeout",
        }
    )
    SUBAGENT_DISCOVERY_TRIGGERS = (
        "## mandatory subagent execution",
        "choose_subagent_dispatch",
        "choose_evidence_lane_dispatch",
        "choose_ui_reference_lane_dispatch",
        "execution_model: subagent-mandatory",
        "execution model: `subagents-first`",
        "dispatch_shape: one-subagent",
        "dispatch `one-subagent`",
        "parallel-subagents",
        "subagent-assisted",
        "native-subagents",
        "spawn_agent",
        "task tool",
    )
    COMMAND_REFERENCE_WORKFLOWS = frozenset(
        {
            "analyze",
            "checklist",
            "clarify",
            "debug",
            "deep-research",
            "design",
            "discussion",
            "fast",
            "implement",
            "implement-teams",
            "map-build",
            "map-scan",
            "map-update",
            "plan",
            "prd-scan",
            "quick",
            "review",
            "specify",
            "tasks",
        }
    )
    UNRESOLVED_RENDERER_TOKEN_RE = re.compile(
        r"\{SCRIPT\}|\{AGENT_SCRIPT\}|\{ARGS\}|__AGENT__|"
        r"\{\{invoke:[^}]+}}|\{\{spec-kit-include:|"
        r"\{\{project-cognition-workflow}}"
    )

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

    def shared_command_references_dir(self) -> Path | None:
        """Return path to the shared command reference templates directory."""
        import inspect

        pkg_dir = Path(inspect.getfile(IntegrationBase)).resolve().parent.parent
        for candidate in [
            pkg_dir / "core_pack" / "command-references",
            pkg_dir.parent.parent / "templates" / "command-references",
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

    @classmethod
    def project_cognition_workflow_registry(cls) -> dict[str, Any]:
        """Load and validate the shared workflow closeout registry."""

        pkg_dir = Path(inspect.getfile(IntegrationBase)).resolve().parent.parent
        candidates = (
            pkg_dir
            / "core_pack"
            / "templates"
            / "artifacts"
            / cls.PROJECT_COGNITION_WORKFLOW_REGISTRY,
            pkg_dir.parent.parent
            / "templates"
            / "artifacts"
            / cls.PROJECT_COGNITION_WORKFLOW_REGISTRY,
        )
        registry_path = next((path for path in candidates if path.is_file()), None)
        if registry_path is None:
            raise FileNotFoundError(
                "Project cognition workflow registry is unavailable; checked: "
                + ", ".join(str(path) for path in candidates)
            )

        try:
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(
                f"Invalid project cognition workflow registry: {registry_path}"
            ) from exc
        cls._validate_project_cognition_workflow_registry(registry)
        return registry

    @classmethod
    def _validate_project_cognition_workflow_registry(
        cls,
        registry: Any,
    ) -> None:
        """Validate the stable subset consumed by prompt renderers."""

        if not isinstance(registry, dict):
            raise ValueError("Project cognition workflow registry must be an object")
        if registry.get("$schema") != "project-cognition-workflow-registry.schema.json":
            raise ValueError("Project cognition workflow registry has an unknown schema")
        if registry.get("schema_version") != 1:
            raise ValueError("Project cognition workflow registry must use schema_version 1")
        workflows = registry.get("workflows")
        if not isinstance(workflows, dict) or not workflows:
            raise ValueError("Project cognition workflow registry requires workflows")

        for command_name, policy in workflows.items():
            if not isinstance(command_name, str) or not re.fullmatch(
                r"[a-z0-9]+(?:-[a-z0-9]+)*", command_name
            ):
                raise ValueError(f"Invalid workflow command name: {command_name!r}")
            if not isinstance(policy, dict):
                raise ValueError(f"Workflow policy for {command_name!r} must be an object")
            if set(policy) != {"mode", "canonical_workflow", "reason"}:
                raise ValueError(
                    f"Workflow policy for {command_name!r} has invalid fields"
                )
            mode = policy.get("mode")
            if mode not in cls.PROJECT_COGNITION_WORKFLOW_MODES:
                raise ValueError(
                    f"Workflow policy for {command_name!r} has invalid mode {mode!r}"
                )
            canonical = policy.get("canonical_workflow")
            requires_canonical = mode in {"mutation_closeout", "map_maintenance"}
            if requires_canonical:
                if not isinstance(canonical, str) or not re.fullmatch(
                    r"sp-[a-z0-9]+(?:-[a-z0-9]+)*", canonical
                ):
                    raise ValueError(
                        f"Workflow policy for {command_name!r} requires a canonical sp-* workflow"
                    )
            elif canonical is not None:
                raise ValueError(
                    f"Workflow policy for {command_name!r} must not define a canonical workflow"
                )
            if not isinstance(policy.get("reason"), str) or not policy["reason"].strip():
                raise ValueError(
                    f"Workflow policy for {command_name!r} requires a reason"
                )

    @classmethod
    def project_cognition_workflow_policy(
        cls,
        command_name: str,
    ) -> dict[str, Any]:
        """Return one validated closeout policy by Classic command name."""

        workflows = cls.project_cognition_workflow_registry()["workflows"]
        try:
            return workflows[command_name]
        except KeyError as exc:
            raise ValueError(
                f"No project cognition workflow policy for {command_name!r}"
            ) from exc

    @staticmethod
    def _command_name_for_template(template_path: Path | None) -> str | None:
        if template_path is None:
            return None
        parts = template_path.parts
        topology_directories = {
            "commands",
            "command-references",
            "command-partials",
        }
        topology_indices = [
            index
            for index, part in enumerate(parts)
            if part in topology_directories
        ]
        if not topology_indices:
            return None

        # Source checkouts use templates/<surface>/..., while wheels use
        # core_pack/<surface>/.... Prefer those known roots over an unrelated
        # ancestor that happens to share a surface directory name. Fixtures may
        # provide only <surface>/..., so retain the nearest-match fallback.
        rooted_indices = [
            index
            for index in topology_indices
            if index > 0 and parts[index - 1] in {"templates", "core_pack"}
        ]
        index = max(rooted_indices or topology_indices)
        if index + 1 >= len(parts):
            return None

        directory = parts[index]
        owner = parts[index + 1]
        if directory == "commands":
            return Path(owner).stem
        if owner == "common":
            return None
        return owner

    @classmethod
    def render_project_cognition_workflow_token(
        cls,
        content: str,
        template_path: Path | None,
    ) -> str:
        """Render the closeout workflow token to a registry-owned literal ID."""

        if cls.PROJECT_COGNITION_WORKFLOW_TOKEN not in content:
            return content
        command_name = cls._command_name_for_template(template_path)
        if command_name is None:
            raise ValueError(
                "Cannot render project cognition workflow without an owning command"
            )
        policy = cls.project_cognition_workflow_policy(command_name)
        canonical = policy.get("canonical_workflow")
        if policy.get("mode") != "mutation_closeout" or not canonical:
            raise ValueError(
                f"Workflow {command_name!r} does not own mutation closeout"
            )
        return content.replace(cls.PROJECT_COGNITION_WORKFLOW_TOKEN, canonical)

    def list_command_templates(self) -> list[Path]:
        """Return sorted list of command template files from the shared directory."""
        cmd_dir = self.shared_commands_dir()
        if not cmd_dir or not cmd_dir.is_dir():
            return []
        excluded_templates = {"team.md", "implement-teams.md"}
        return sorted(
            f
            for f in cmd_dir.iterdir()
            if f.is_file() and f.suffix == ".md" and f.name not in excluded_templates
        )

    def list_command_reference_templates(self, command_name: str) -> list[Path]:
        """Return sorted reference template files for *command_name*."""
        references_dir = self.shared_command_references_dir()
        if not references_dir or not references_dir.is_dir():
            return []
        if (
            not command_name
            or ".." in command_name
            or "/" in command_name
            or "\\" in command_name
        ):
            return []

        references_root = references_dir.resolve()
        workflow_dir = (references_root / command_name).resolve()
        try:
            workflow_dir.relative_to(references_root)
        except ValueError:
            return []
        if not workflow_dir.is_dir():
            return []

        return sorted(
            (path for path in workflow_dir.rglob("*") if path.is_file()),
            key=lambda path: path.relative_to(workflow_dir).as_posix(),
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

    @classmethod
    def validate_no_unresolved_renderer_tokens(
        cls,
        content: str,
        source_path: Path,
    ) -> None:
        """Raise if rendered *content* still contains renderer-only tokens."""
        match = cls.UNRESOLVED_RENDERER_TOKEN_RE.search(content)
        if match:
            raise ValueError(
                f"{source_path} contains unresolved renderer token {match.group(0)!r}"
            )

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
        *,
        preserve_modified: bool = False,
        skipped_modified: list[str] | None = None,
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
        modified = set(manifest.check_modified()) if preserve_modified else set()
        scripts_dest = project_root / ".specify" / "integrations" / self.key / "scripts"
        scripts_dest.mkdir(parents=True, exist_ok=True)

        for src_script in sorted(scripts_src.iterdir()):
            if not src_script.is_file():
                continue
            dst_script = scripts_dest / src_script.name
            relative = dst_script.relative_to(project_root).as_posix()
            if preserve_modified and (dst_script.exists() or dst_script.is_symlink()):
                if relative not in manifest.files or relative in modified:
                    if skipped_modified is not None:
                        skipped_modified.append(relative)
                    continue
            shutil.copy2(src_script, dst_script)
            if dst_script.suffix == ".sh":
                dst_script.chmod(dst_script.stat().st_mode | 0o111)
            self.record_file_in_manifest(dst_script, project_root, manifest)
            created.append(dst_script)

        return created

    def _question_tool_use_cases(self, command_name: str) -> list[str]:
        use_cases = {
            "specify": [
                "planning-critical clarification",
                "capability split confirmation",
                "user-owned semantic delta before planning readiness",
            ],
            "discussion": [
                "one high-impact product or technical clarification",
                "resume selection when multiple incomplete discussions exist",
                "explicit handoff request and boundary confirmation before drafting agent-only `handoff-to-specify.json`",
                "user confirmation before marking the handoff ready for `sp-specify`",
            ],
            "clarify": [
                "high-impact gap confirmation",
                "scope or constraint confirmation when enhancement changes planning readiness",
            ],
            "deep-research": [
                "whether the feasibility question is actually a requirement gap",
                "minimum research tracks needed before planning",
                "manual confirmation before force-proceeding with unresolved feasibility risk",
            ],
            "checklist": [
                "initial contextual clarifying questions (`Q1`-`Q3`)",
                "optional targeted follow-ups (`Q4`-`Q5`) when high-value gaps remain",
            ],
            "quick": [
                "lightweight clarification when `--discuss` is active",
                "resume selection when multiple unfinished quick tasks exist",
            ],
            "debug": [
                "missing-information questions during map-backed intake",
                "deep Stage 1A/1B fallback when project cognition is insufficient",
            ],
        }
        return use_cases.get(command_name, [])

    def _question_tool_fallback_hint(self, command_name: str) -> str:
        fallback_hints = {
            "specify": "If the native tool is unavailable in the current runtime or the tool call fails, fall back to the shared open question block structure already defined in this template.",
            "discussion": "If the native tool is unavailable in the current runtime or the tool call fails, ask one concise plain-text product or technical question and continue with the discussion state update.",
            "clarify": "If the native tool is unavailable in the current runtime or the tool call fails, ask one concise plain-text confirmation question and continue with the existing enhancement flow.",
            "deep-research": "If the native tool is unavailable in the current runtime or the tool call fails, ask one concise plain-text question about the missing feasibility or research-track decision, then continue with the existing research workflow.",
            "checklist": "If the native tool is unavailable in the current runtime or the tool call fails, keep the template's existing `Q1`/`Q2`/`Q3` (and optional `Q4`/`Q5`) textual question format.",
            "quick": "If the native tool is unavailable in the current runtime or the tool call fails, use the template's existing concise plain-text clarification or quick-task selection wording.",
            "debug": "If the native tool is unavailable in the current runtime or the tool call fails, ask one concise missing-information question in plain text during observer framing before entering reproduction work.",
        }
        return fallback_hints.get(
            command_name,
            "If the native tool is unavailable in the current runtime or the tool call fails, fall back to the template's existing textual question format.",
        )

    def _append_question_tool_preference(
        self,
        *,
        content: str,
        agent_name: str,
        command_name: str,
    ) -> str:
        question_driven_commands = {"specify", "discussion", "clarify", "deep-research", "checklist", "quick", "debug"}
        if command_name not in question_driven_commands:
            return content

        marker = f"## {agent_name} Structured Question Preference"
        if marker in content:
            return content

        config = self.question_tool_config or {}
        tool_name = config.get("tool_name")
        availability_note = config.get("availability_note")
        question_limit = config.get("question_limit")
        option_limit = config.get("option_limit")
        question_fields = config.get("question_fields") or []
        option_fields = config.get("option_fields") or []
        extra_notes = config.get("extra_notes") or []

        lines = [
            "",
            f"## {agent_name} Structured Question Preference",
            "",
            "- If this command was routed by `sp-auto` with `auto_default_recommendation: true`, evaluate the automatic recommended/default continuation gate before any question path.",
            "- When that gate has one safe recommended/default answer, you must auto-resolve the question or confirmation, record the accepted recommendation in the workflow state or summary, continue the workflow, and do not invoke the native structured question tool only to ask for that approval.",
            "- If the automatic gate is not safe, write the blocker and self-unblock recommendation before using the normal question path.",
            "- If the runtime's native structured question tool is available for the current turn and the `sp-auto` automatic gate did not resolve the question, you must use it.",
            "- Do not render the textual fallback block when the native tool is available.",
            "- Do not self-authorize textual fallback because the question seems simple, short, or easy to phrase manually.",
            "- Treat the template's textual question format as fallback-only guidance; use it to shape the question content, but do not render the textual block unless the native tool is unavailable in the current runtime or the tool call fails.",
            "- Keep native-tool availability, runtime mode, and fallback mechanics backstage. Do not tell the user that a structured question tool is unavailable, that the current runtime/mode lacks a tool, or that a fallback is being used; ask the user-facing question directly when a question is genuinely required.",
            "- Ask only the minimum number of questions required by this workflow's existing contract.",
            "- Keep the user-visible question text in the user's current language and keep option labels short.",
            "- Do not emit both a native tool question and the textual fallback block in the same turn. The user should see the active question exactly once.",
            f"- {self._question_tool_fallback_hint(command_name)}",
        ]

        use_cases = self._question_tool_use_cases(command_name)
        if use_cases:
            lines.append(f"- In `{command_name}`, use this preference for:")
            for use_case in use_cases:
                lines.append(f"  - {use_case}")

        if tool_name:
            tool_intro = f"- Native tool target: `{tool_name}`"
            if availability_note:
                tool_intro += f" {availability_note}"
            lines.append(tool_intro)
            if not availability_note:
                lines.append(
                    "- When this native tool target is listed for the integration and the runtime does not signal otherwise, assume it is available by default in normal interactive sessions."
                )
        if question_limit:
            lines.append(f"- Question count: {question_limit}")
        if option_limit:
            lines.append(f"- Option count: {option_limit}")
        if question_fields:
            lines.append(
                "- Required question fields: "
                + ", ".join(f"`{field}`" for field in question_fields)
            )
        if option_fields:
            lines.append(
                "- Option fields: "
                + ", ".join(f"`{field}`" for field in option_fields)
            )
        for note in extra_notes:
            lines.append(f"- {note}")

        return content + "\n".join(lines) + "\n"

    def _append_specify_semantic_traceability_guidance(
        self,
        *,
        content: str,
    ) -> str:
        """Append simplified `sp-specify` semantic-traceability guidance when absent."""

        marker = "## Semantic Traceability Guidance"
        if marker in content:
            return content

        addendum = (
            "\n"
            "## Semantic Traceability Guidance\n\n"
            "- Preserve the concise `sp-specify` flow: explore project context, ask one high-impact question at a time, compare two or three approaches, write artifacts, self-review, and ask for user review.\n"
            "- When `sp-specify` comes from `sp-discussion`, compile canonical `spec-contract.json` from the confirmed requirement contract and preserve its decision digest by reference.\n"
            "- Read supporting discussion files only when a named evidence reference is stale, missing, or contradictory; record only the refs actually needed in the compact context capsule.\n"
            "- Compute `semantic_delta`; when it is empty and deterministic review passes, do not repeat upstream questions or user confirmation.\n"
            "- Decompose semantic terms before narrowing scope and keep unconfirmed narrowing out of planning-ready state.\n"
            "- Downstream stages must reopen upstream intent explicitly instead of silently reinterpreting it.\n"
        )
        return content + addendum

    def _append_specify_pre_analysis_protocol(
        self,
        *,
        content: str,
    ) -> str:
        """Keep skills-based specify prompts explicit when includes are trimmed."""

        marker = "## Pre-Analysis Protocol"
        if marker in content:
            return content

        addendum = (
            "\n"
            f"{marker}\n\n"
            "- Before drafting or asking clarification questions, identify the target need, scope boundary, key constraints, acceptance proof, known unknowns, and safest next step.\n"
            "- Keep guided requirement discovery concise and avoid reviving the deprecated fixed heavy discovery lifecycle.\n"
            "- Treat `final-handoff-decision` as a compatibility readiness check name only; do not restore the legacy staged handoff flow.\n"
            "- In compile mode, reuse the confirmed discussion contract's context capsule and decision digest. Run one bounded `{{specify-subcmd:specify-runtime cognition compass --intent plan --query=\"$ARGUMENTS\" --format json}}` intake only when a planning facet is absent or outdated; preserve `{{specify-subcmd:specify-runtime cognition query --intent plan --query-plan \"<query_plan_json>\" --format json}}` as a precision escalation for an explicit unresolved concept.\n"
            "- Read top-level `minimal_live_reads` first and open live files only for the named gap. Do not build a second broad repository summary or infer final scope from first-pass paths.\n"
            "- After `FEATURE_DIR` is known, use `{{specify-subcmd:specify-runtime workflow show --feature-dir <feature-dir> --format json}}`; when state is missing, run `{{specify-subcmd:specify-runtime workflow enter --command specify --feature-dir <feature-dir> --format json}}`. The deterministic workflow runtime owns `workflow.json` as required-stage state; do not author or advance it manually. Rich `workflow-state.md` remains specification evidence and resume state inside the fixed workflow artifact boundary: read it only through `{{specify-subcmd:specify-runtime artifact show --path <project-relative-workflow-state-path> --view summary}}`; write it only through an authorized `{{specify-subcmd:specify-runtime artifact prepare --path <project-relative-workflow-state-path>}}` then `{{specify-subcmd:specify-runtime artifact submit --lease <lease-id> --content-file <temporary-file>}}` lease. Never use rich state to skip runtime stages. Do not implement code, edit source files, edit tests, or run implementation-oriented fix loops from `sp-specify`.\n"
            "- Write canonical `spec-contract.json` first. Render `spec.md`; write `alignment.md`, `context.md`, `references.md`, or diagnostics only when the triggered content has independent project-review value and cannot be represented by a stable ref.\n"
            "- Clarify only planning-critical ambiguity. Recommend `/sp.clarify` or `/sp.deep-research` only when the unresolved item belongs there.\n"
            "- Preserve this as an internal understand-before-acting pass; do not replace the one-question-at-a-time requirement discovery flow with a broad analysis report.\n"
        )
        return content + addendum

    def _append_planning_skill_cognition_refresh_guidance(
        self,
        *,
        content: str,
        command_name: str,
    ) -> str:
        """Keep planning navigation visible without granting mutation closeout."""

        if command_name not in {"specify", "plan", "tasks"}:
            return content

        marker = "## Project Cognition Navigation (Planning Only)"
        if marker in content:
            return content

        addendum = (
            "\n"
            f"{marker}\n\n"
            "- Use `.specify/project-cognition/status.json` to assess "
            "Git-baseline freshness and "
            "`.specify/project-cognition/project-cognition.db` only as advisory "
            "navigation; prove planning facts from bounded live repository "
            "evidence.\n"
            "- This planning-only section does not grant source-mutation authority "
            "or mutation-closeout execution. The current workflow remains "
            "artifact-only.\n"
            "- Planning artifact writes do not run `specify-runtime cognition "
            "complete-refresh`. Any manual override/fallback belongs to an explicit "
            "map-maintenance recovery path, not specification closeout.\n"
            "- Recommend `/sp-map-update` for ordinary existing-baseline gaps; run "
            "`/sp-map-scan` followed by `/sp-map-build` only for a missing or "
            "unusable baseline or an explicit rebuild condition.\n"
        )
        return content + addendum

    def _append_checklist_project_cognition_guidance(
        self,
        *,
        content: str,
    ) -> str:
        """Keep checklist skills explicit about brownfield navigation inputs."""

        marker = "## Checklist Project Cognition Intake"
        if marker in content:
            return content

        addendum = (
            "\n"
            f"{marker}\n\n"
            "- Run `{{specify-subcmd:specify-runtime cognition compass --intent plan --query=\"$ARGUMENTS\" --format json}}` before shaping the checklist. Read top-level `minimal_live_reads` first, then use lane-level `first_pass_paths` reasons, `verification_hints`, `followup_surfaces`, and `before_fix_claim`; treat `coverage_diagnostics` as confidence and closeout signals and `expansion_ref` as a continuation path only when coverage state or live evidence requires it.\n"
            "- Preserve the advanced `lexicon -> semantic_intake -> query` path with `{{specify-subcmd:specify-runtime cognition query --intent plan --query-plan \"<query_plan_json>\" --format json}}` when explicit concept decisions are needed; include `query_plan`, `semantic_intake`, `concept_decisions`, `covered_facets`, `missing_facets`, `match_sources`, `lexicon_generation_id`, and `repository_search_terms` there.\n"
        )
        return content + addendum

    def _append_delegation_surface_contract(
        self,
        *,
        content: str,
        agent_name: str,
        command_name: str,
        snapshot: CapabilitySnapshot,
        heading: str,
    ) -> str:
        """Append a normalized subagent dispatch contract section when absent."""

        marker = f"## {agent_name} {heading}"
        if marker in content:
            return content

        descriptor = describe_delegation_surface(
            command_name=command_name,
            snapshot=snapshot,
        )
        managed_team_hint = descriptor.managed_team_hint
        execution_model = "adaptive" if command_name == "implement" else "subagents-first"
        local_route = (
            "- Leader-direct route: valid for a small or tightly coupled task when it independently passes the workflow safety gate; record the selected route in the current lifecycle record.\n"
            if command_name == "implement"
            else "- Leader-inline fallback: record the reason before local execution.\n"
        )
        addendum = (
            "\n"
            f"## {agent_name} {heading}\n\n"
            f"- Execution model: `{execution_model}`\n"
            "- Dispatch shape: `one-subagent`, `parallel-subagents`, or `subagent-blocked`\n"
            "- Execution surface: `native-subagents`, `managed-team`, or `leader-inline`\n"
            "- Delegation surface contract: preserve the native dispatch, fallback, worker result contract, and handoff path below.\n"
            f"- Native subagent capability discovery: {descriptor.native_discovery_hint}\n"
            "- Do not record `subagent-blocked` until this capability discovery step is complete and the exact unavailable or unsafe surface is recorded.\n"
            f"- Native subagent dispatch: {descriptor.native_dispatch_hint}\n"
            f"- Join behavior: {descriptor.native_join_hint}\n"
            f"- Managed-team fallback: {managed_team_hint}\n"
            f"{local_route}"
            f"- Worker result contract: {descriptor.result_contract_hint}\n"
            f"- Result contract: {descriptor.result_contract_hint}\n"
            f"- Result handoff path: {descriptor.result_handoff_hint}\n"
        )
        return content + addendum

    def _append_runtime_project_cognition_gate(
        self,
        *,
        content: str,
        agent_name: str,
        command_name: str,
    ) -> str:
        """Append a hard project cognition read gate for runtime-facing commands when absent."""

        policy = self.project_cognition_workflow_policy(command_name)
        if policy["mode"] != "mutation_closeout":
            return content

        if command_name not in self.RUNTIME_SUBAGENT_CONTRACT_COMMANDS:
            return content

        marker = f"## {agent_name} Project Cognition Advisory Gate"
        if marker in content:
            return content

        command_step = {
            "implement": "before any implementation actions",
            "review": "before any system review, repair, or revalidation actions",
            "debug": "before any investigation or fixes",
            "quick": "before repository analysis or implementation",
        }[command_name]
        query_gate = self._project_cognition_query_gate_line(command_name=command_name, command_step=command_step)
        carry_forward = {
            "implement": "- Carry forward only the current task's selected capability, minimal live reads, boundary constraints, required references, validation route, and evidence gaps into its lifecycle record or just-in-time `WorkerTaskPacket`.\n",
            "review": "- Carry forward the selected user journeys, official entrypoints, affected runtime surfaces, minimal live reads, validation routes, and evidence gaps into `review-state.json` or the just-in-time review packet.\n",
            "debug": "- Carry forward the selected capability or symptom, evidence routes, minimal reads, competing truths, and unresolved coverage gaps into debug session state before root-cause claims.\n",
            "quick": "- Carry forward the selected capability, minimal reads, validation route, and known risk into quick-task `STATUS.md` before implementation proceeds.\n",
        }[command_name]

        addendum = (
            "\n"
            f"## {agent_name} Project Cognition Advisory Gate\n\n"
            f"{query_gate}\n"
            f"- {EPISTEMIC_CONTRACT_GUIDANCE}\n"
            "- Route every Compass packet by `recommended_next_action.action_id`, never by readiness alone. `query_ready` reads top-level `minimal_live_reads` first and then lane-level `first_pass_paths`; `review` permits only returned `minimal_live_reads` plus `coverage_diagnostics`; `needs_rebuild` may carry a resumable non-rebuild action such as `complete_scan_packets`, which must be preserved. Only `action_id=project_cognition.rebuild` may consume `rebuild_reasons[]` and the canonical Classic steps in `recommended_next_action.workflow_routes.classic.steps`; `action_id=project_cognition.repair_status` must run its returned `argv`. `blocked` reports the runtime issue as advisory map state and continues with live repository evidence unless the user's request is to repair cognition; `unsupported_runtime` continues with live evidence and records that compass intake was unavailable. If `baseline_kind=greenfield_empty`, continue with workflow artifacts and live requirements instead of inferring rebuild from absent graph paths.\n"
            "- Use `map-update` for ordinary existing-baseline gaps. If `baseline_kind=greenfield_empty`, do not recommend map-scan -> map-build solely because the graph has no paths; continue with workflow artifacts and live requirements. Use `map-scan -> map-build` only for brownfield first/missing/unusable baseline, schema failure, schema v1 or old broad-schema rebuild-required readiness, zero active-generation `path_index` rows outside `greenfield_empty`, missing or invalid `alias_index`, `explicit_rebuild_requested`, or `baseline_identity_invalid`.\n"
            "- Treat the project cognition compass packet as advisory navigation for brownfield context; do not fall back to chat memory or ad hoc repository instincts when compass-backed runtime coverage should guide the route.\n"
            "- Treat this as advisory navigation, not a hard gate; continue with live repository evidence when the bundle is weak, stale, or missing, and use map maintenance only when it is actually useful.\n"
            "- Mutation closeout is separate from entry routing. Its single semantic owner is the shared inline closeout contract rendered in the owning command or triggered closeout reference; this advisory gate does not restate or execute closeout.\n"
            "- `sp-map-update` is for manual/external maintenance and follow-up repair after user edits, interrupted workflows, or explicit operator map-maintenance requests. It is not routine cleanup for changes this workflow just made.\n"
            "- A specify-runtime cognition compass intake is not complete when it returns JSON. It is complete only when readiness drives routing, `minimal_live_reads` constrains inspection, lane-level `first_pass_paths` reasons are considered, and relevant facts are carried into the next workflow artifact or execution state.\n"
            f"{carry_forward}"
        )

        insert_before = None
        if "## Orchestration Model" in content:
            insert_before = "## Orchestration Model"
        elif "## Outline" in content:
            insert_before = "## Outline"
        elif "## Process" in content:
            insert_before = "## Process"
        elif "## Session Lifecycle" in content:
            insert_before = "## Session Lifecycle"

        if insert_before:
            return content.replace(insert_before, addendum + f"\n{insert_before}", 1)
        return content + addendum

    def _project_cognition_query_gate_line(self, *, command_name: str, command_step: str) -> str:
        intent = {
            "debug": "debug",
            "implement": "implement",
            "review": "implement",
            "quick": "implement",
        }.get(command_name, "implement")
        if command_name == "implement":
            return (
                "**Current-Task Navigation Repair**: Reuse the current task's required refs and live touched-area evidence. "
                "Only when a required ref is stale, missing, or contradicted by live code, run at most one "
                "`{{specify-subcmd:specify-runtime cognition compass --intent implement --query=\"$ARGUMENTS\" --format json}}` "
                f"{command_step}. {EPISTEMIC_CONTRACT_GUIDANCE} Use `compass_state`, `minimal_live_reads`, `first_pass_paths`, `coverage_diagnostics`, "
                "and `expansion_ref` only to repair current-task context; they do not replace live proof or authorize "
                "broader implementation scope."
            )
        return (
            "**Crucial First Step**: You MUST use project cognition compass first: "
            f"run `{{{{specify-subcmd:specify-runtime cognition compass --intent {intent} --query=\"$ARGUMENTS\" --format json}}}}` "
            f"{command_step}. {EPISTEMIC_CONTRACT_GUIDANCE} Read top-level `minimal_live_reads` first, then use lane-level `first_pass_paths` reasons, "
            "`verification_hints`, `followup_surfaces`, and `before_fix_claim`; treat `coverage_diagnostics` as confidence "
            "and closeout signals, never as route candidates. Treat `expansion_ref` as a normal continuation path and run "
            "`{{specify-subcmd:specify-runtime cognition expand --id <id> --section <section> --format json}}` only when coverage state or live evidence "
            "requires more map detail. Do not infer final edit scope from `minimal_live_reads` or `first_pass_paths`. "
            "Readiness values are `query_ready`, `review`, `needs_rebuild`, `blocked`, and `unsupported_runtime`. "
            "When `compass_state=needs_semantic_intake`, write `semantic_intake` from project vocabulary and rerun compass "
            "with `--semantic-intake-file`, or use the advanced `lexicon -> semantic_intake -> query` path when explicit "
            "concept decisions are needed. Preserve advanced routing through "
            f"`{{{{specify-subcmd:specify-runtime cognition query --intent {intent} --query-plan \"<query_plan_json>\" --format json}}}}` "
            "for precision cases."
        )

    def _append_toml_debug_runtime_bridge(
        self,
        *,
        content: str,
        agent_name: str,
    ) -> str:
        """Append TOML-only debug compatibility wording without polluting markdown bases."""

        marker = f"## {agent_name} Debug Compatibility Bridge"
        if marker in content:
            return content

        handbook = "DEBUG" + "-HANDBOOK.md"
        contract = "debug" + "-workflow-contract"
        bridge_label = "Runtime " + "handbook contract"
        addendum = (
            "\n"
            f"## {agent_name} Debug Compatibility Bridge\n\n"
            f"- {bridge_label}: read `{handbook}` only when a compatibility/export debug view is needed alongside the query-backed runtime.\n"
            "- Fixed chapter IDs required for debug remain compatibility identifiers layered on top of the query-backed runtime, not a replacement brownfield truth source.\n"
            f"- Compatibility tag: `{contract}`.\n"
        )

        if "## Investigation Protocol" in content:
            return content.replace("## Investigation Protocol", addendum + "\n## Investigation Protocol", 1)
        if "## Session Lifecycle" in content:
            return content.replace("## Session Lifecycle", addendum + "\n## Session Lifecycle", 1)
        return content + addendum

    def runtime_capability_snapshot(self) -> CapabilitySnapshot:
        """Return the best available capability snapshot for this integration."""

        local_snapshot = getattr(self, "_runtime_capability_snapshot", None)
        if callable(local_snapshot):
            return local_snapshot()

        class_module = type(self).__module__
        package_name = class_module.rsplit(".", 1)[0]
        module_names = []
        for module_name in (f"{class_module}.multi_agent", f"{package_name}.multi_agent"):
            if module_name not in module_names:
                module_names.append(module_name)

        for module_name in module_names:
            try:
                module = importlib.import_module(module_name)
            except ImportError:
                continue
            for _, value in inspect.getmembers(module, inspect.isclass):
                if getattr(value, "integration_key", None) != self.key:
                    continue
                detect_capabilities = getattr(value(), "detect_capabilities", None)
                if callable(detect_capabilities):
                    return detect_capabilities()

        from specify_cli.orchestration.adapters import build_capability_snapshot

        return build_capability_snapshot(
            integration_key=self.key,
            native_subagents=False,
            managed_team_supported=False,
            structured_results=False,
            durable_coordination=False,
            native_worker_surface="unknown",
            delegation_confidence="low",
            model_family=self.key,
            notes=[
                "No integration-specific capability adapter was registered; using the conservative shared subagent dispatch contract.",
            ],
        )

    def _append_subagent_capability_discovery(
        self,
        *,
        content: str,
        agent_name: str,
        command_name: str,
        snapshot: CapabilitySnapshot,
    ) -> str:
        """Append subagent discovery guidance to generated workflows that dispatch lanes."""

        if command_name in self.SUBAGENT_DISCOVERY_EXCLUDED_COMMANDS:
            return content

        if "Native subagent capability discovery" in content:
            return content

        lowered = content.lower()
        if not any(trigger in lowered for trigger in self.SUBAGENT_DISCOVERY_TRIGGERS):
            return content

        section_name = (
            "Map Subagent Capability Discovery"
            if command_name in self.MAP_SUBAGENT_DISCOVERY_COMMANDS
            else "Subagent Capability Discovery"
        )
        marker = f"## {agent_name} {section_name}"
        if marker in content:
            return content

        descriptor = describe_delegation_surface(
            command_name=command_name,
            snapshot=snapshot,
        )
        schema_note = (
            "- Keep map packet/result schemas from this workflow authoritative; do not substitute implementation `WorkerTaskResult` fields for map scan/build/update packet contracts.\n"
            if command_name in self.MAP_SUBAGENT_DISCOVERY_COMMANDS
            else "- Preserve this workflow's existing packet, handoff, artifact, and result schema; this section only governs capability discovery before dispatch or blocked-state recording.\n"
        )
        addendum = (
            "\n"
            f"## {agent_name} {section_name}\n\n"
            "- Execution model: preserve the workflow's existing `subagent-mandatory`, `subagents-first`, `adaptive`, or `subagent-assisted` policy.\n"
            "- Dispatch shape: preserve the workflow's existing dispatch shape; use `subagent-blocked` only after the discovery step below fails or is unsafe.\n"
            "- Execution surface: prefer `native-subagents` when the current runtime supports it; use `none` only after recording the unavailable or unsafe surface.\n"
            f"- Native subagent capability discovery: {descriptor.native_discovery_hint}\n"
            "- Do not record `subagent-blocked` until this capability discovery step is complete and the exact unavailable or unsafe surface is recorded.\n"
            f"- Native subagent dispatch: {descriptor.native_dispatch_hint}\n"
            f"- Join behavior: {descriptor.native_join_hint}\n"
            f"{schema_note}"
        )
        return content + addendum

    def _append_map_subagent_capability_discovery(
        self,
        *,
        content: str,
        agent_name: str,
        command_name: str,
        snapshot: CapabilitySnapshot,
    ) -> str:
        """Compatibility wrapper for older integration-specific setup loops."""

        return self._append_subagent_capability_discovery(
            content=content,
            agent_name=agent_name,
            command_name=command_name,
            snapshot=snapshot,
        )

    def _append_implement_leader_gate(
        self,
        *,
        content: str,
        agent_name: str,
    ) -> str:
        """Append the shared implement leader-gate contract when absent."""

        if "## Orchestration Model" in content:
            return content

        gate_marker = f"## {agent_name} Leader Gate"
        if gate_marker in content:
            return content

        gate_addendum = (
            "\n"
            f"## {agent_name} Leader Gate\n\n"
            f"When running `sp-implement` in {agent_name}, you are the leader and own route selection, execution-state truth, acceptance, and recovery.\n"
            "\n"
            f"{self._project_cognition_query_gate_line(command_name='implement', command_step='before any implementation actions')}\n"
            "\n"
            "Before implementation actions:\n"
            "- Read canonical `task-index.json` or the light direct task list, compact execution state, and the current task's required refs.\n"
            "- **Resume Audit**: If the tracker is `resolved`, all tasks appear checked, or the previous session exit is unknown, run `{{specify-subcmd:implement resume-audit --feature-dir \"$FEATURE_DIR\" --format json}}` before trusting completion.\n"
            "- Treat completed task markers as claims until changed paths, validation, required consumer evidence, review status, and mutation closeout prove them.\n"
            "- Choose `leader-direct` for a small or tightly coupled ready task when delegation adds no quality or critical-path benefit and no high-risk trigger calls for an independent lane.\n"
            "- Choose `one-subagent` for one independent bounded task and `parallel-subagents` only for validated lanes with isolated write sets and an explicit join point.\n"
            "- Compile and validate a `WorkerTaskPacket` just in time only for delegated work; leader-direct work does not require one.\n"
            "- If dispatch fails, record the event and re-evaluate route safety. Use leader-direct only if the task independently qualifies; otherwise repair the packet/surface or block truthfully.\n"
            "- Wait for every subagent's structured handoff before accepting the join point, closing the batch, or declaring completion.\n"
            "- Do not treat an idle subagent as done work; idle without a consumed handoff means the result channel is still unresolved.\n"
            "- Require consumer evidence when a worker creates a reusable UI, route, provider, registry, factory, config, API, or test surface; a created but not wired file is not complete.\n"
            "- When a packet requires `real_entrypoint_evidence`, require `consumer_evidence` with `kind: real_entrypoint`, `entrypoint`, `producer`, `transformer`, `consumer`, `boundary_or_executor`, and `validation`; synthetic-only component, reducer, helper, or hand-built state evidence is not enough.\n"
            "- The leader must not edit a delegated lane's write scope while that subagent is active.\n"
            "- On technical blockers, attempt the smallest safe autonomous recovery or specialist lane before asking for manual intervention.\n"
        )

        if "## Outline" in content:
            return content.replace("## Outline", gate_addendum + "\n## Outline", 1)
        return content + gate_addendum

    def _append_runtime_worker_result_contract(
        self,
        *,
        content: str,
        agent_name: str,
        command_name: str,
        snapshot: CapabilitySnapshot,
    ) -> str:
        """Append the runtime worker-result contract when absent."""

        marker = f"## {agent_name} Subagent Result Contract"
        if marker in content:
            return content

        descriptor = describe_delegation_surface(
            command_name=command_name,
            snapshot=snapshot,
        )
        if "<request-id>" in descriptor.result_handoff_hint:
            result_cli_guidance = (
                "- Runtime-managed result paths require a dispatch request id; compute the path with "
                f"`{{{{specify-subcmd:result path --command {command_name} --request-id <request-id>}}}}` and report final completion "
                "through the active runtime-managed result channel for that request id.\n"
                "- `{{specify-subcmd:result path --help}}` documents a JSON-only command; do not append `--format`.\n"
            )
        else:
            result_cli_guidance = (
                "- For filesystem handoffs, use `{{specify-subcmd:result path --help}}` with the concrete workflow identifiers "
                "such as `--feature-dir`/`--task-id`, `--workspace`/`--lane-id`, or `--session-slug`/`--lane-id`.\n"
                "- The result-path command emits JSON and does not accept `--format`; do not append `--format`.\n"
            )
        addendum = (
            "\n"
            f"## {agent_name} Subagent Result Contract\n\n"
            "- Worker result contract: preserve the shared `WorkerTaskResult` semantics even when the runtime calls lanes subagents.\n"
            f"- Preferred result contract: {descriptor.result_contract_hint}\n"
            f"- Result file handoff path: {descriptor.result_handoff_hint}\n"
            f"{result_cli_guidance}"
            "- Normalize subagent-reported statuses like `DONE`, `DONE_WITH_CONCERNS`, `BLOCKED`, and `NEEDS_CONTEXT` into the shared `WorkerTaskResult` contract before the leader accepts the handoff.\n"
            "- Keep `reported_status` when normalization occurs so runtime-specific subagent language can be reconciled with canonical orchestration state.\n"
            "- Wait for every subagent's structured handoff before accepting the join point, closing the batch, or declaring completion.\n"
            "- Do not treat an idle subagent as done work; idle without a consumed handoff means the result channel is still unresolved.\n"
            "- Do not interrupt or shut down subagent work before the handoff has been written or explicitly reported as `BLOCKED` or `NEEDS_CONTEXT`.\n"
            "- Treat `DONE_WITH_CONCERNS` as completed work plus follow-up concerns, not as silent success.\n"
            "- Treat `NEEDS_CONTEXT` as a blocked handoff that must carry the missing context or failed assumption explicitly.\n"
        )
        return content + addendum

    def _append_debug_leader_gate(
        self,
        *,
        content: str,
        agent_name: str,
    ) -> str:
        """Append the shared debug leader-gate contract when absent."""

        gate_marker = f"## {agent_name} Leader Gate"
        if gate_marker in content:
            return content

        gate_addendum = (
            "\n"
            f"## {agent_name} Leader Gate\n\n"
            f"When running `sp-debug` in {agent_name}, you are the **leader**, not a freeform debugger.\n"
            "\n"
            f"{self._project_cognition_query_gate_line(command_name='debug', command_step='before any investigation or fixes')}\n"
            "\n"
            "Before applying fixes or running investigation actions:\n"
            "- Read the current debug session state and choose `execution_model: leader-inline | subagent-assisted | blocked` from the investigation shape.\n"
            "- Use `leader-inline` for a small focused investigation with one short evidence chain.\n"
            "- Use `subagent-assisted` when there are two or more independent evidence-gathering lanes, broad surface area, or meaningful parallelism.\n"
            "- If the next step is unsafe, unavailable, or unpacketizable, record `subagent-blocked`, `execution_surface: none`, and a concrete `blocked_reason` before stopping.\n"
            "- Rejoin only at the current investigation join point, then integrate returned results on the leader path.\n"
            "\n"
            "**Hard rule:** During `investigating`, the leader must not let subagents mutate the debug file, declare the root cause final, or advance the session state.\n"
        )

        if "## Session Lifecycle" in content:
            return content.replace("## Session Lifecycle", gate_addendum + "\n## Session Lifecycle", 1)
        return content + gate_addendum

    def _append_debug_routing_contract(
        self,
        *,
        content: str,
        agent_name: str,
        snapshot: CapabilitySnapshot,
    ) -> str:
        """Append the shared debug routing contract when absent."""

        marker = f"## {agent_name} Investigation Routing Contract"
        if marker in content:
            return content

        descriptor = describe_delegation_surface(
            command_name="debug",
            snapshot=snapshot,
        )
        managed_team_hint = descriptor.managed_team_hint
        addendum = (
            "\n"
            f"## {agent_name} Investigation Routing Contract\n\n"
            f"When running `sp-debug` in {agent_name}, treat `investigating` as a complexity-based leader decision.\n"
            "- Execution model: `leader-inline | subagent-assisted | blocked`.\n"
            "- Dispatch shape: `leader-inline`, `one-subagent`, `parallel-subagents`, or `subagent-blocked`.\n"
            "- Execution surface: `leader-inline`, `native-subagents`, or `none`.\n"
            f"- Subagent dispatch: {descriptor.native_dispatch_hint}\n"
            f"- Integration-native join point: {descriptor.native_join_hint}\n"
            f"- Fallback path: {managed_team_hint}\n"
            "- Small focused investigation -> `leader-inline`.\n"
            "- One safe isolated evidence lane -> `one-subagent` when the current runtime supports it safely.\n"
            "- Two or more independent evidence lanes -> `parallel-subagents` when the current runtime supports it safely.\n"
            "- Unsafe, unavailable, or unpacketizable next step -> `subagent-blocked` with `execution_surface: none` and `blocked_reason`.\n"
            "- Suitable subagent tasks include running targeted tests or repro commands, collecting logs and exit codes, searching for error text, tracing isolated code paths, and gathering evidence after diagnostic logging has been added.\n"
            "- Read `diagnostic_profile` from the debug session before choosing subagent lanes.\n"
            "- Subagents must return facts, command results, and observations; they must not update the debug file, declare the root cause final, or transition the session state.\n"
            "- Keep fixing, verification, `awaiting_human_verify`, and final session resolution on the leader path.\n"
        )
        return content + addendum

    def _append_quick_leader_gate(
        self,
        *,
        content: str,
        agent_name: str,
    ) -> str:
        """Append the shared quick leader-gate contract when absent."""

        gate_marker = f"## {agent_name} Leader Gate"
        if gate_marker in content:
            return content

        gate_addendum = (
            "\n"
            f"## {agent_name} Leader Gate\n\n"
            f"When running `sp-quick` in {agent_name}, you are the **leader**, not the concrete implementer.\n"
            "\n"
            f"{self._project_cognition_query_gate_line(command_name='quick', command_step='before repository analysis or implementation')}\n"
            "\n"
            "Before code edits, test edits, or implementation commands:\n"
            "- Read `.specify/memory/constitution.md` first if it exists.\n"
            "- Read `STATUS.md` for the active quick-task workspace, or create it if this quick task is new.\n"
            "- If `understanding_confirmed` is not `true`, present the Understanding Checkpoint and wait for user confirmation before implementation work.\n"
            "- The user-facing checkpoint must use the fixed Quick Checkpoint Markdown table with `| Decision to confirm | Current understanding |` and rows for `Request and outcome`, `User-visible result`, `Scope`, `Recommended approach`, `Assumptions and risks`, `Completion evidence`, and `Reconfirmation trigger`; technical execution stays agent-owned, and prose bullets or partial field lists are not sufficient. For applicable UI work, append the independent UI Confirmation card and ask once for both decisions.\n"
            "- Do not proceed to code edits, broad repository analysis, delegation, or validation commands until `understanding_confirmed: true` is recorded in `STATUS.md`.\n"
            "- Before choosing the next lane, read `STATUS.md` and any quick-task summary artifacts so resume truth comes from durable state instead of chat narration.\n"
            "- After understanding is confirmed, define the smallest safe delegated lane or ready batch, and choose the dispatch shape for that batch.\n"
            "- Dispatch `one-subagent` when one validated `WorkerTaskPacket` or equivalent execution contract preserves quality.\n"
            "- Dispatch `parallel-subagents` when two or more safe subagent lanes would materially improve throughput.\n"
            "- Use the current runtime's `native-subagents` path before considering any fallback path.\n"
            "- If that bar is not met, keep the lane on the leader path until the missing context, constraints, validation target, or handoff expectations are explicit.\n"
            "- Use the current integration's join point to integrate returned results before choosing the next action.\n"
            "- Wait for every subagent's structured handoff before accepting the join point, closing the batch, or declaring completion.\n"
            "- Do not treat an idle subagent as done work; idle without a consumed handoff means the result channel is still unresolved.\n"
            "- Do not interrupt or shut down subagent work before the handoff has been written or explicitly reported as `BLOCKED` or `NEEDS_CONTEXT`.\n"
            "- Use `managed-team` only when durable team state is needed beyond one in-session subagent burst.\n"
            "- Use `subagent-blocked` only when subagent dispatch and the managed team workflow are both unavailable or unsafe.\n"
            "- When `subagent-blocked` is used, you **MUST** write the concrete blocker reason into `STATUS.md` before escalating or stopping locally.\n"
            "\n"
            "**Hard rule:** The leader must keep scope control, strategy selection, join-point handling, validation, summary ownership, and `STATUS.md` accuracy while subagent execution is active.\n"
        )

        if "## Process" in content:
            return content.replace("## Process", gate_addendum + "\n## Process", 1)
        return content + gate_addendum

    def _append_quick_routing_contract(
        self,
        *,
        content: str,
        agent_name: str,
        snapshot: CapabilitySnapshot,
    ) -> str:
        """Append the shared quick routing contract when absent."""

        marker = f"## {agent_name} Quick Execution Routing"
        if marker in content:
            return content

        descriptor = describe_delegation_surface(
            command_name="quick",
            snapshot=snapshot,
        )
        managed_team_hint = descriptor.managed_team_hint
        addendum = (
            "\n"
            f"## {agent_name} Quick Execution Routing\n\n"
            f"When running `sp-quick` in {agent_name}, do not start execution routing until `STATUS.md` exists and `understanding_confirmed: true` is recorded.\n"
            "- Dispatch shape: `one-subagent`, `parallel-subagents`, or `subagent-blocked`.\n"
            "- Execution surface: `native-subagents`, `managed-team`, or `leader-inline`.\n"
            "- Understanding checkpoint: before dispatch, render the fixed Quick Checkpoint Markdown table with `| Decision to confirm | Current understanding |` and user-owned rows for request/outcome, visible result, scope, recommended approach, assumptions/risks, completion evidence, and reconfirmation trigger. Append the UI Confirmation proposal when applicable and use one combined confirmation.\n"
            f"- Subagent dispatch: {descriptor.native_dispatch_hint}\n"
            f"- Integration-native join point: {descriptor.native_join_hint}\n"
            f"- Fallback path: {managed_team_hint}\n"
            "- Once the first lane is chosen, dispatch it before continuing any leader-inline deep-dive analysis of the repository.\n"
            "- If multiple safe subagent lanes exist and they materially improve throughput, dispatch them in parallel.\n"
            "- Keep `.planning/quick/<id>-<slug>/STATUS.md` as the leader-owned source of truth.\n"
            "- Before compaction-risk transitions or join points, update `STATUS.md` and any summary artifacts needed for clean resume.\n"
            "- Subagents may return evidence, patches, and verification output, but they must not become the authority for resume state; the leader updates `STATUS.md` before and after each join point.\n"
            f"- Decision order for {agent_name} `sp-quick`: safe packetized subagents -> `managed-team` when durable state is needed -> `subagent-blocked` with reason.\n"
            "- Prefer subagent execution only when a validated `WorkerTaskPacket` or equivalent execution contract preserves quality.\n"
            "- Re-check strategy after every join point and continue automatically until the quick task is complete or blocked.\n"
        )
        return content + addendum

    @staticmethod
    def resolve_template_includes(
        content: str,
        base_dir: Path | None,
        *,
        _stack: tuple[Path, ...] = (),
    ) -> str:
        """Resolve narrow include directives inside shared prompt templates."""

        if not isinstance(content, str) or not content or base_dir is None:
            return content

        include_pattern = re.compile(
            r"(?m)^[ \t]*\{\{spec-kit-include:\s*(?P<path>[^}]+?)\s*\}\}[ \t]*(?:\r?\n)?"
        )

        def _replace(match: re.Match[str]) -> str:
            rel_path = match.group("path").strip()
            include_path = (base_dir / rel_path).resolve()

            if include_path in _stack:
                chain = " -> ".join(str(path) for path in (*_stack, include_path))
                raise ValueError(f"Template include cycle detected: {chain}")
            if not include_path.is_file():
                raise FileNotFoundError(
                    f"Template include not found: {include_path}"
                )

            included = include_path.read_text(encoding="utf-8")
            return IntegrationBase.resolve_template_includes(
                included,
                include_path.parent,
                _stack=(*_stack, include_path),
            )

        return include_pattern.sub(_replace, content)

    @staticmethod
    def _split_frontmatter(content: str) -> tuple[str, str]:
        """Split YAML frontmatter from the remaining content.

        Returns ``("", content)`` when no complete frontmatter block is
        present. The body is preserved exactly as written so later
        rendering stages keep their intended formatting.
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
    def _parse_frontmatter_mapping(frontmatter_text: str) -> dict[str, Any]:
        """Parse YAML frontmatter into a mapping, returning ``{}`` on failure."""
        import yaml

        if not frontmatter_text:
            return {}

        try:
            frontmatter = yaml.safe_load(frontmatter_text) or {}
        except yaml.YAMLError:
            return {}

        if not isinstance(frontmatter, dict):
            return {}

        return frontmatter

    @staticmethod
    def _render_workflow_contract_summary(frontmatter: dict[str, Any]) -> str:
        """Render the shared workflow contract summary from frontmatter."""
        workflow_contract = frontmatter.get("workflow_contract")
        if not isinstance(workflow_contract, dict):
            return ""

        fields = (
            ("When to use", "when_to_use"),
            ("Primary objective", "primary_objective"),
            ("Primary outputs", "primary_outputs"),
            ("Default handoff", "default_handoff"),
        )

        rendered_lines = ["## Workflow Contract Summary", ""]
        for label, key in fields:
            value = workflow_contract.get(key)
            if not isinstance(value, str) or not value.strip():
                return ""
            rendered_lines.append(f"- **{label}**: {value.strip()}")

        rendered_lines.append(
            "- **Execution note**: This summary is routing metadata only. "
            "Follow the full contract below end-to-end rather than inferring "
            "behavior from the description alone."
        )
        return "\n".join(rendered_lines) + "\n\n"

    @staticmethod
    def render_template_content(
        content: str,
        template_path: Path | None = None,
    ) -> str:
        """Resolve shared template structure before agent-specific processing.

        This expands ``{{spec-kit-include: ...}}`` directives and renders
        the shared workflow-contract summary from frontmatter when present.
        """
        content = IntegrationBase.resolve_template_includes(
            content,
            template_path.parent if template_path is not None else None,
        )

        if template_path is not None and template_path.parent.name == "commands":
            blocker_contract_path = (
                template_path.parent.parent
                / "command-partials"
                / "common"
                / "blocker-resolution.md"
            )
            if (
                blocker_contract_path.is_file()
                and "## Blocked Exit Contract" not in content
            ):
                blocker_contract = blocker_contract_path.read_text(encoding="utf-8").strip()
                frontmatter_text, body = IntegrationBase._split_frontmatter(content)
                if frontmatter_text:
                    rendered_body = body.lstrip("\r\n")
                    content = (
                        f"---\n{frontmatter_text}---\n\n"
                        f"{blocker_contract}\n\n{rendered_body}"
                    )
                else:
                    content = f"{blocker_contract}\n\n{content.lstrip()}"

            runtime_boundary_path = (
                template_path.parent.parent
                / "command-partials"
                / "common"
                / "runtime-artifact-boundary.md"
            )
            if (
                runtime_boundary_path.is_file()
                and "## Fixed Workflow Artifact Boundary" not in content
            ):
                runtime_boundary = runtime_boundary_path.read_text(
                    encoding="utf-8"
                ).strip()
                frontmatter_text, body = IntegrationBase._split_frontmatter(content)
                if frontmatter_text:
                    rendered_body = body.lstrip("\r\n")
                    content = (
                        f"---\n{frontmatter_text}---\n\n"
                        f"{runtime_boundary}\n\n{rendered_body}"
                    )
                else:
                    content = f"{runtime_boundary}\n\n{content.lstrip()}"

        frontmatter_text, body = IntegrationBase._split_frontmatter(content)
        if not frontmatter_text or "## Workflow Contract Summary" in body:
            return content

        summary = IntegrationBase._render_workflow_contract_summary(
            IntegrationBase._parse_frontmatter_mapping(frontmatter_text)
        )
        if not summary:
            return content

        rendered_body = body.lstrip("\r\n")
        return f"---\n{frontmatter_text}---\n\n{summary}{rendered_body}"

    @staticmethod
    def _renderer_context_frontmatter(frontmatter_text: str) -> str:
        """Return only frontmatter sections needed for renderer substitutions."""
        renderer_sections = {"scripts:", "agent_scripts:"}
        output_lines: list[str] = []
        in_renderer_section = False

        for line in frontmatter_text.splitlines(keepends=True):
            stripped = line.strip()
            if stripped in renderer_sections:
                output_lines.append(line)
                in_renderer_section = True
                continue

            if in_renderer_section:
                if line and line[0].isspace():
                    output_lines.append(line)
                    continue
                in_renderer_section = False

        return "".join(output_lines)

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
        """Render a command reference template using its owner command context."""
        _ = owner_template_path
        owner_frontmatter, _ = cls._split_frontmatter(owner_template_raw)
        render_input = raw_reference
        renderer_context = cls._renderer_context_frontmatter(owner_frontmatter)
        if renderer_context:
            render_input = f"---\n{renderer_context}---\n\n{raw_reference}"

        processed = cls.process_template(
            render_input,
            agent_name,
            script_type,
            arg_placeholder,
            template_path=reference_path,
            project_root=project_root,
        )
        _, body = cls._split_frontmatter(processed)

        if apply_invocation_conventions:
            from specify_cli.agents import CommandRegistrar

            body = CommandRegistrar.apply_skill_invocation_conventions(
                agent_name,
                body,
            )

        cls.validate_no_unresolved_renderer_tokens(body, reference_path)
        return body.lstrip("\r\n")

    def render_inline_command_references(
        self,
        *,
        command_name: str,
        owner_template_raw: str,
        owner_template_path: Path,
        agent_name: str | None = None,
        script_type: str,
        arg_placeholder: str,
        project_root: Path | None = None,
    ) -> str:
        """Render command references as an inline section for single-file commands."""
        reference_files = self.list_command_reference_templates(command_name)
        if not reference_files:
            return ""

        references_dir = self.shared_command_references_dir()
        workflow_dir = (references_dir / command_name).resolve() if references_dir else None
        display_root = (
            workflow_dir
            if workflow_dir is not None and workflow_dir.is_dir()
            else reference_files[0].parent.resolve()
        )

        lines = ["", "## Reference Contracts", ""]
        for reference_path in reference_files:
            try:
                relative_reference = reference_path.resolve().relative_to(display_root)
            except ValueError:
                relative_reference = Path(reference_path.name)
            display_path = f"references/{relative_reference.as_posix()}"
            rendered_body = self.render_command_reference_content(
                reference_path.read_text(encoding="utf-8"),
                owner_template_raw=owner_template_raw,
                owner_template_path=owner_template_path,
                reference_path=reference_path,
                agent_name=agent_name or self.key,
                script_type=script_type,
                arg_placeholder=arg_placeholder,
                project_root=project_root,
            ).rstrip()

            lines.extend([f"### {display_path}", ""])
            if rendered_body:
                lines.extend([rendered_body, ""])

        section = "\n".join(lines).rstrip() + "\n"
        self.validate_no_unresolved_renderer_tokens(section, owner_template_path)
        return section

    @staticmethod
    def rewrite_command_reference_links(content: str, command_name: str) -> str:
        """Point a single-file command at its namespaced reference sidecars."""
        if not command_name or "references/" not in content:
            return content
        return re.sub(
            r"references/(?=[A-Za-z0-9_.-]+\.md\b)",
            f"references/{command_name}/",
            content,
        )

    def install_command_reference_sidecars(
        self,
        *,
        command_name: str,
        owner_template_raw: str,
        owner_template_path: Path,
        commands_destination: Path,
        project_root: Path,
        manifest: IntegrationManifest,
        script_type: str,
        arg_placeholder: str,
    ) -> list[Path]:
        """Render references beside a single-file command under a stable namespace."""
        reference_files = self.list_command_reference_templates(command_name)
        references_dir = self.shared_command_references_dir()
        if not reference_files or not references_dir:
            return []

        references_root = (references_dir / command_name).resolve()
        references_destination = commands_destination / "references" / command_name
        created: list[Path] = []
        for source in reference_files:
            try:
                relative = source.resolve().relative_to(references_root)
            except ValueError:
                relative = Path(source.name)
            rendered = self.render_command_reference_content(
                source.read_text(encoding="utf-8"),
                owner_template_raw=owner_template_raw,
                owner_template_path=owner_template_path,
                reference_path=source,
                agent_name=self.key,
                script_type=script_type,
                arg_placeholder=arg_placeholder,
                project_root=project_root,
            )
            created.append(
                self.write_file_and_record(
                    rendered,
                    references_destination / relative,
                    project_root,
                    manifest,
                )
            )
        return created

    @staticmethod
    def process_template(
        content: str,
        agent_name: str,
        script_type: str,
        arg_placeholder: str = "$ARGUMENTS",
        template_path: Path | None = None,
        project_root: Path | None = None,
    ) -> str:
        """Process a raw command template into agent-ready content.

        Performs the same transformations as the release script:
        1. Resolve ``{{spec-kit-include: ...}}`` directives
        2. Extract ``scripts.<script_type>`` value from YAML frontmatter
        3. Replace ``{SCRIPT}`` with the extracted script command
        4. Extract ``agent_scripts.<script_type>`` and replace ``{AGENT_SCRIPT}``
        5. Strip ``scripts:`` and ``agent_scripts:`` sections from frontmatter
        6. Replace ``{ARGS}`` with *arg_placeholder*
        7. Replace ``__AGENT__`` with *agent_name*
        8. Rewrite paths: ``scripts/`` → ``.specify/scripts/`` etc.
        """
        content = IntegrationBase.render_template_content(
            content,
            template_path=template_path,
        )
        content = IntegrationBase.render_project_cognition_workflow_token(
            content,
            template_path,
        )

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
        from specify_cli.launcher import render_project_launcher_placeholders
        content = CommandRegistrar.rewrite_project_relative_paths(content)
        content = CommandRegistrar.render_invocation_placeholders(agent_name, content)
        if project_root is not None:
            content = render_project_launcher_placeholders(project_root, content)

        for unresolved in (
            "{{spec-kit-include:",
            IntegrationBase.PROJECT_COGNITION_WORKFLOW_TOKEN,
        ):
            if unresolved in content:
                raise ValueError(
                    f"{template_path or '<template>'} contains unresolved renderer token "
                    f"{unresolved!r}"
                )

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

    def repair_runtime_assets(
        self,
        project_root: Path,
        manifest: IntegrationManifest,
        **opts: Any,
    ) -> list[Path]:
        """Refresh runtime-managed integration assets without rewriting workflow content."""
        skipped: list[str] = []
        cognition_skipped: list[str] = []
        created = self.install_scripts(
            project_root,
            manifest,
            preserve_modified=True,
            skipped_modified=skipped,
        )
        created.extend(
            self.rebind_unavailable_specify_runtime_commands(
                project_root,
                manifest,
                skipped_modified=cognition_skipped,
            )
        )
        skipped.extend(cognition_skipped)
        rebound, guidance_skipped = self.rebind_manifest_owned_specify_guidance(
            project_root,
            manifest,
        )
        created.extend(rebound)
        skipped.extend(guidance_skipped)
        self._last_repair_skipped_modified = tuple(sorted(set(skipped)))
        self._last_repair_unresolved_cognition_markers = tuple(
            sorted(set(cognition_skipped))
        )
        self._last_repair_unresolved_cognition_calls = tuple(
            sorted(set(cognition_skipped))
        )
        return created

    def rebind_unavailable_specify_runtime_commands(
        self,
        project_root: Path,
        manifest: IntegrationManifest,
        *,
        skipped_modified: list[str] | None = None,
    ) -> list[Path]:
        """Rebind unmodified generated guidance after unified runtime recovery."""

        from specify_cli.launcher import (
            SPECIFY_RUNTIME_UNAVAILABLE_MARKER,
            load_runtime_launcher,
            rebind_unavailable_specify_runtime_commands,
            rebind_unbound_unified_runtime_calls,
        )

        project_root_resolved = project_root.resolve()
        runtime_launcher = load_runtime_launcher(project_root)
        modified = set(manifest.check_modified())
        rebound: list[Path] = []
        for relative in sorted(manifest.files):
            lexical_path = project_root_resolved / relative
            if lexical_path.is_symlink():
                if relative in modified and skipped_modified is not None:
                    skipped_modified.append(relative)
                continue
            path = lexical_path.resolve()
            try:
                path.relative_to(project_root_resolved)
            except ValueError:
                if skipped_modified is not None:
                    skipped_modified.append(relative)
                continue
            if not path.is_file() or path.suffix.lower() not in {".md", ".toml"}:
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                if skipped_modified is not None:
                    skipped_modified.append(relative)
                continue
            marker_present = (
                f"{SPECIFY_RUNTIME_UNAVAILABLE_MARKER}:specify-runtime"
                in content
            )
            _, bare_count = rebind_unbound_unified_runtime_calls(
                content,
                "__SPEC_KIT_BOUND_SPECIFY_RUNTIME__",
            )
            if not marker_present and bare_count == 0:
                continue
            if relative in modified:
                if skipped_modified is not None:
                    skipped_modified.append(relative)
                continue
            if runtime_launcher is None:
                if skipped_modified is not None:
                    skipped_modified.append(relative)
                continue
            command_renderer = None
            if path.suffix.lower() == ".toml":
                render_toml_string = getattr(self, "_render_toml_string", None)
                if not callable(render_toml_string):
                    if skipped_modified is not None:
                        skipped_modified.append(relative)
                    continue

                def command_renderer(command: str) -> str:
                    rendered = render_toml_string(command)
                    return rendered[1:-1]

            repaired = rebind_unavailable_specify_runtime_commands(
                project_root,
                content,
                command_renderer=command_renderer,
            )
            repaired, _ = rebind_unbound_unified_runtime_calls(
                repaired,
                runtime_launcher.command,
                command_renderer=command_renderer,
            )
            if repaired == content:
                if skipped_modified is not None:
                    skipped_modified.append(relative)
                continue
            rebound.append(
                self.write_file_and_record(
                    repaired,
                    path,
                    project_root,
                    manifest,
                )
            )
        return rebound

    def rebind_manifest_owned_specify_guidance(
        self,
        project_root: Path,
        manifest: IntegrationManifest,
    ) -> tuple[list[Path], list[str]]:
        """Rebind safe generated guidance while preserving every user edit."""

        from specify_cli.launcher import (
            SPEC_KIT_MANAGED_BLOCK_RE,
            load_project_specify_launcher,
            rebind_source_bound_specify_launchers,
            rebind_unbound_specify_runtime_calls,
        )

        launcher = load_project_specify_launcher(project_root)
        if launcher is None:
            return [], []
        project_root_resolved = project_root.resolve()
        modified = set(manifest.check_modified())
        context_relative = (
            Path(self.context_file).as_posix()
            if self.context_file
            else None
        )
        rebound: list[Path] = []
        skipped: list[str] = []
        for relative in sorted(manifest.files):
            lexical_path = project_root_resolved / Path(relative)
            if lexical_path.is_symlink():
                skipped.append(relative)
                continue
            path = lexical_path.resolve()
            try:
                path.relative_to(project_root_resolved)
            except ValueError:
                skipped.append(relative)
                continue
            if not path.is_file() or path.suffix.lower() not in {".md", ".toml"}:
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except OSError:
                skipped.append(relative)
                continue
            command_renderer = None
            if path.suffix.lower() == ".toml":
                render_toml_string = getattr(self, "_render_toml_string", None)
                if not callable(render_toml_string):
                    continue

                def command_renderer(command: str) -> str:
                    rendered = render_toml_string(command)
                    return rendered[1:-1]

            updated, source_count = rebind_source_bound_specify_launchers(
                content,
                launcher,
                command_renderer=command_renderer,
            )
            updated, bare_count = rebind_unbound_specify_runtime_calls(
                updated,
                launcher.command,
                command_renderer=command_renderer,
            )
            if source_count + bare_count == 0 or updated == content:
                continue
            if relative in modified:
                if relative == context_relative:
                    def rebind_managed_block(match: re.Match[str]) -> str:
                        block, _ = rebind_source_bound_specify_launchers(
                            match.group(0),
                            launcher,
                        )
                        block, _ = rebind_unbound_specify_runtime_calls(
                            block,
                            launcher.command,
                        )
                        return block

                    managed_updated = SPEC_KIT_MANAGED_BLOCK_RE.sub(
                        rebind_managed_block,
                        content,
                    )
                    if managed_updated != content:
                        path.write_bytes(managed_updated.encode("utf-8"))
                        rebound.append(path)
                    if managed_updated != updated:
                        skipped.append(relative)
                    continue
                skipped.append(relative)
                continue
            rebound.append(
                self.write_file_and_record(
                    updated,
                    path,
                    project_root,
                    manifest,
                )
            )
        return rebound, sorted(set(skipped))

    def post_init_bootstrap(
        self,
        project_root: Path,
        manifest: IntegrationManifest,
    ) -> list[Path]:
        """Optional post-init adjustments after context/bootstrap assets exist."""
        return []


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
        runtime_snapshot = self.runtime_capability_snapshot()
        created: list[Path] = []

        for src_file in templates:
            raw = src_file.read_text(encoding="utf-8")
            processed = self.process_template(
                raw,
                self.key,
                script_type,
                arg_placeholder,
                template_path=src_file,
                project_root=project_root,
            )
            processed = self.rewrite_command_reference_links(
                processed,
                src_file.stem,
            )
            agent_name = self.config.get("name", self.key.capitalize()) if self.config else self.key.capitalize()
            processed = self._append_runtime_project_cognition_gate(
                content=processed,
                agent_name=agent_name.replace(" CLI", ""),
                command_name=src_file.stem,
            )
            if src_file.stem == "implement":
                processed = self._append_implement_leader_gate(
                    content=processed,
                    agent_name=agent_name.replace(" CLI", ""),
                )
            if src_file.stem == "debug":
                processed = self._append_debug_leader_gate(
                    content=processed,
                    agent_name=agent_name.replace(" CLI", ""),
                )
                processed = self._append_debug_routing_contract(
                    content=processed,
                    agent_name=agent_name.replace(" CLI", ""),
                    snapshot=runtime_snapshot,
                )
            if src_file.stem == "quick":
                processed = self._append_quick_leader_gate(
                    content=processed,
                    agent_name=agent_name.replace(" CLI", ""),
                )
                processed = self._append_quick_routing_contract(
                    content=processed,
                    agent_name=agent_name.replace(" CLI", ""),
                    snapshot=runtime_snapshot,
                )
            if src_file.stem in self.RUNTIME_SUBAGENT_CONTRACT_COMMANDS:
                processed = self._append_delegation_surface_contract(
                    content=processed,
                    agent_name=agent_name.replace(" CLI", ""),
                    command_name=src_file.stem,
                    snapshot=runtime_snapshot,
                    heading="Subagent Dispatch Contract",
                )
                processed = self._append_runtime_worker_result_contract(
                    content=processed,
                    agent_name=agent_name.replace(" CLI", ""),
                    command_name=src_file.stem,
                    snapshot=runtime_snapshot,
                )
            processed = self._append_map_subagent_capability_discovery(
                content=processed,
                agent_name=agent_name.replace(" CLI", ""),
                command_name=src_file.stem,
                snapshot=runtime_snapshot,
            )
            processed = self._append_question_tool_preference(
                content=processed,
                agent_name=agent_name.replace(" CLI", ""),
                command_name=src_file.stem,
            )
            from specify_cli.launcher import render_project_launcher_placeholders
            processed = render_project_launcher_placeholders(project_root, processed)
            dst_name = self.command_filename(src_file.stem)
            dst_file = self.write_file_and_record(
                processed, dest / dst_name, project_root, manifest
            )
            created.append(dst_file)
            created.extend(
                self.install_command_reference_sidecars(
                    command_name=src_file.stem,
                    owner_template_raw=raw,
                    owner_template_path=src_file,
                    commands_destination=dest,
                    project_root=project_root,
                    manifest=manifest,
                    script_type=script_type,
                    arg_placeholder=arg_placeholder,
                )
            )

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
        frontmatter_text, _ = IntegrationBase._split_frontmatter(content)
        frontmatter = IntegrationBase._parse_frontmatter_mapping(frontmatter_text)
        if not frontmatter:
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
        return IntegrationBase._split_frontmatter(content)

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
        runtime_snapshot = self.runtime_capability_snapshot()
        created: list[Path] = []

        for src_file in templates:
            raw = src_file.read_text(encoding="utf-8")
            description = self._extract_description(raw)
            processed = self.process_template(
                raw,
                self.key,
                script_type,
                arg_placeholder,
                template_path=src_file,
                project_root=project_root,
            )
            processed = self.rewrite_command_reference_links(
                processed,
                src_file.stem,
            )
            agent_name = self.config.get("name", self.key.capitalize()) if self.config else self.key.capitalize()
            processed = self._append_runtime_project_cognition_gate(
                content=processed,
                agent_name=agent_name.replace(" CLI", ""),
                command_name=src_file.stem,
            )
            if src_file.stem == "implement":
                processed = self._append_implement_leader_gate(
                    content=processed,
                    agent_name=agent_name.replace(" CLI", ""),
                )
            if src_file.stem == "debug":
                processed = self._append_debug_leader_gate(
                    content=processed,
                    agent_name=agent_name.replace(" CLI", ""),
                )
                processed = self._append_toml_debug_runtime_bridge(
                    content=processed,
                    agent_name=agent_name.replace(" CLI", ""),
                )
                processed = self._append_debug_routing_contract(
                    content=processed,
                    agent_name=agent_name.replace(" CLI", ""),
                    snapshot=runtime_snapshot,
                )
            if src_file.stem == "quick":
                processed = self._append_quick_leader_gate(
                    content=processed,
                    agent_name=agent_name.replace(" CLI", ""),
                )
                processed = self._append_quick_routing_contract(
                    content=processed,
                    agent_name=agent_name.replace(" CLI", ""),
                    snapshot=runtime_snapshot,
                )
            if src_file.stem in self.RUNTIME_SUBAGENT_CONTRACT_COMMANDS:
                processed = self._append_delegation_surface_contract(
                    content=processed,
                    agent_name=agent_name.replace(" CLI", ""),
                    command_name=src_file.stem,
                    snapshot=runtime_snapshot,
                    heading="Subagent Dispatch Contract",
                )
                processed = self._append_runtime_worker_result_contract(
                    content=processed,
                    agent_name=agent_name.replace(" CLI", ""),
                    command_name=src_file.stem,
                    snapshot=runtime_snapshot,
                )
            processed = self._append_map_subagent_capability_discovery(
                content=processed,
                agent_name=agent_name.replace(" CLI", ""),
                command_name=src_file.stem,
                snapshot=runtime_snapshot,
            )
            processed = self._append_question_tool_preference(
                content=processed,
                agent_name=agent_name.replace(" CLI", ""),
                command_name=src_file.stem,
            )
            from specify_cli.launcher import render_project_launcher_placeholders
            processed = render_project_launcher_placeholders(project_root, processed)
            _, body = self._split_frontmatter(processed)
            toml_content = self._render_toml(description, body)
            dst_name = self.command_filename(src_file.stem)
            dst_file = self.write_file_and_record(
                toml_content, dest / dst_name, project_root, manifest
            )
            created.append(dst_file)
            created.extend(
                self.install_command_reference_sidecars(
                    command_name=src_file.stem,
                    owner_template_raw=raw,
                    owner_template_path=src_file,
                    commands_destination=dest,
                    project_root=project_root,
                    manifest=manifest,
                    script_type=script_type,
                    arg_placeholder=arg_placeholder,
                )
            )

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
    ``sp-<name>/SKILL.md`` file with skills-oriented frontmatter, and
    may also install passive repository skills from
    ``templates/passive-skills/<name>/SKILL.md``.
    """

    WORKFLOW_PROFILES = frozenset({"classic", "advanced"})

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

    def shared_passive_skills_dir(self) -> Path | None:
        """Return path to the shared passive skill template directory."""
        import inspect

        pkg_dir = Path(inspect.getfile(IntegrationBase)).resolve().parent.parent
        for candidate in [
            pkg_dir / "core_pack" / "passive-skills",
            pkg_dir.parent.parent / "templates" / "passive-skills",
        ]:
            if candidate.is_dir():
                return candidate
        return None

    def list_passive_skill_templates(self) -> list[Path]:
        """Return sorted passive skill directories containing ``SKILL.md``."""
        passive_dir = self.shared_passive_skills_dir()
        if not passive_dir or not passive_dir.is_dir():
            return []
        return sorted(
            path
            for path in passive_dir.iterdir()
            if path.is_dir() and (path / "SKILL.md").is_file()
        )

    def shared_advanced_skills_dir(self) -> Path | None:
        """Return the opt-in advanced-model skill template directory."""
        import inspect

        pkg_dir = Path(inspect.getfile(IntegrationBase)).resolve().parent.parent
        for candidate in [
            pkg_dir / "core_pack" / "advanced-skills",
            pkg_dir.parent.parent / "templates" / "advanced-skills",
        ]:
            if candidate.is_dir():
                return candidate
        return None

    def list_advanced_skill_templates(self) -> list[Path]:
        """Return sorted explicit skills for the advanced prompt profile."""
        advanced_dir = self.shared_advanced_skills_dir()
        if not advanced_dir or not advanced_dir.is_dir():
            return []
        return sorted(
            path
            for path in advanced_dir.iterdir()
            if path.is_dir()
            and path.name.startswith("spx-")
            and (path / "SKILL.md").is_file()
        )

    @classmethod
    def workflow_profile(
        cls,
        parsed_options: dict[str, Any] | None,
    ) -> str:
        """Resolve and validate the prompt profile for one install pass."""
        profile = str((parsed_options or {}).get("workflow_profile") or "classic")
        if profile not in cls.WORKFLOW_PROFILES:
            choices = ", ".join(sorted(cls.WORKFLOW_PROFILES))
            raise ValueError(
                f"Unknown workflow profile {profile!r}; choose from: {choices}"
            )
        return profile

    def render_advanced_invocations(self, content: str) -> str:
        """Project canonical ``$spx-*`` handoffs to this skill integration."""
        if self.key in {"codex", "agy", "trae", "zcode"}:
            return content
        if self.key == "kimi":
            replacement = r"/skill:spx-\1"
        else:
            replacement = r"/spx-\1"
        return re.sub(r"\$spx-([a-z0-9][a-z0-9-]*)", replacement, content)

    @staticmethod
    def _can_augment_generated_file(skill_path: Path, project_root: Path) -> bool:
        """Return True when an integration post-processing target is safe to edit."""

        if not skill_path.is_file():
            return False
        try:
            skill_path.resolve().relative_to(project_root.resolve())
        except ValueError:
            return False
        return True

    @staticmethod
    def _parse_skill_frontmatter(raw: str) -> dict[str, Any]:
        """Parse YAML frontmatter from a skill template."""
        frontmatter_text, _ = IntegrationBase._split_frontmatter(raw)
        return IntegrationBase._parse_frontmatter_mapping(frontmatter_text)

    @staticmethod
    def _quote_skill_value(value: str) -> str:
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'

    def _render_skill_content(
        self,
        *,
        raw: str,
        skill_name: str,
        description: str,
        source: str,
        project_root: Path,
        script_type: str,
        arg_placeholder: str,
        apply_invocation_conventions: bool = False,
        template_path: Path | None = None,
    ) -> str:
        """Render a command or passive skill template into normalized ``SKILL.md``."""
        processed_body = self.process_template(
            raw,
            self.key,
            script_type,
            arg_placeholder,
            template_path=template_path,
            project_root=project_root,
        )
        if processed_body.startswith("---"):
            parts = processed_body.split("---", 2)
            if len(parts) >= 3:
                processed_body = parts[2]

        from specify_cli.agents import CommandRegistrar

        if apply_invocation_conventions:
            processed_body = CommandRegistrar.apply_skill_invocation_conventions(
                self.key,
                processed_body,
            )

        compatibility = "Requires spec-kit project structure with .specify/ directory"
        return (
            f"---\n"
            f"name: {self._quote_skill_value(skill_name)}\n"
            f"description: {self._quote_skill_value(description)}\n"
            f"compatibility: {self._quote_skill_value(compatibility)}\n"
            f"metadata:\n"
            f"  author: {self._quote_skill_value('github-spec-kit')}\n"
            f"  source: {self._quote_skill_value(source)}\n"
            f"---\n"
            f"{processed_body}"
        )

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
        """Render command references into a skill's ``references/`` directory."""
        reference_files = self.list_command_reference_templates(command_name)
        if not reference_files:
            return []

        references_dir = self.shared_command_references_dir()
        if not references_dir:
            return []
        references_root = (references_dir / command_name).resolve()
        references_dest = destination_dir / "references"

        created: list[Path] = []
        for src_file in reference_files:
            try:
                relative = src_file.resolve().relative_to(references_root)
            except ValueError:
                relative = Path(src_file.name)
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

        references_dir = self.shared_command_references_dir()
        if not references_dir:
            return restored

        project_root_resolved = project_root.resolve()
        for src_file in self.list_command_templates():
            command_name = src_file.stem
            reference_files = self.list_command_reference_templates(command_name)
            if not reference_files:
                continue
            skill_name = (
                "sp-teams"
                if command_name == "team"
                else f"sp-{command_name.replace('.', '-')}"
            )
            skill_dir = skills_dir / skill_name
            if not (skill_dir / "SKILL.md").is_file():
                continue

            owner_raw = src_file.read_text(encoding="utf-8")
            references_root = (references_dir / command_name).resolve()
            for reference_src in reference_files:
                try:
                    relative = reference_src.resolve().relative_to(references_root)
                except ValueError:
                    relative = Path(reference_src.name)
                destination = skill_dir / "references" / relative
                rel_manifest_path = destination.resolve().relative_to(
                    project_root_resolved
                ).as_posix()
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
        created.extend(
            self.repair_missing_advanced_skill_files(
                project_root,
                manifest,
                script_type=opts.get("script_type", "sh"),
            )
        )
        return created

    def repair_missing_advanced_skill_files(
        self,
        project_root: Path,
        manifest: IntegrationManifest,
        *,
        script_type: str,
    ) -> list[Path]:
        """Restore/rebind manifest-owned SPX support files without overwriting edits."""
        advanced_dir = self.shared_advanced_skills_dir()
        if not advanced_dir:
            return []

        skills_dir = self.skills_dest(project_root).resolve()
        project_root_resolved = project_root.resolve()
        arg_placeholder = (
            self.registrar_config.get("args", "$ARGUMENTS")
            if self.registrar_config
            else "$ARGUMENTS"
        )
        restored: list[Path] = []

        def restore_file(source: Path, destination: Path, *, render: bool) -> None:
            relative = destination.resolve().relative_to(
                project_root_resolved
            ).as_posix()
            if relative not in manifest.files or destination.exists():
                return
            destination.parent.mkdir(parents=True, exist_ok=True)
            if render:
                content = self.process_template(
                    source.read_text(encoding="utf-8"),
                    self.key,
                    script_type,
                    arg_placeholder,
                    template_path=source,
                    project_root=project_root,
                )
                content = self.render_advanced_invocations(content)
                restored.append(
                    self.write_file_and_record(
                        content,
                        destination,
                        project_root,
                        manifest,
                    )
                )
                return
            shutil.copy2(source, destination)
            self.record_file_in_manifest(destination, project_root, manifest)
            restored.append(destination)

        shared_references = sorted((advanced_dir / "_shared").glob("*.md"))
        for template_dir in self.list_advanced_skill_templates():
            skill_dir = skills_dir / template_dir.name
            if not (skill_dir / "SKILL.md").is_file():
                continue
            for source in sorted(template_dir.rglob("*")):
                if source.is_file() and source.name != "SKILL.md":
                    relative = source.relative_to(template_dir)
                    restore_file(
                        source,
                        skill_dir / relative,
                        render=(
                            relative.parts[0] == "references"
                            and source.suffix.lower() == ".md"
                        ),
                    )
            for source in shared_references:
                destination = skill_dir / "references" / source.name
                restore_file(source, destination, render=True)
        return restored

    def _copy_supporting_passive_files(
        self,
        *,
        template_dir: Path,
        destination_dir: Path,
        project_root: Path,
        manifest: IntegrationManifest,
    ) -> list[Path]:
        """Copy non-``SKILL.md`` support files for a passive skill."""
        created: list[Path] = []
        pending = [template_dir]
        files: list[Path] = []
        while pending:
            current = pending.pop()
            for child in current.iterdir():
                if child.is_dir():
                    pending.append(child)
                elif child.is_file():
                    files.append(child)

        for src_file in sorted(files):
            if src_file.name == "SKILL.md":
                continue
            relative = src_file.relative_to(template_dir)
            dst_file = destination_dir / relative
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)
            self.record_file_in_manifest(dst_file, project_root, manifest)
            created.append(dst_file)
        return created

    def _install_advanced_skills(
        self,
        *,
        project_root: Path,
        manifest: IntegrationManifest,
        script_type: str,
        arg_placeholder: str,
    ) -> list[Path]:
        """Install the advanced prompt profile without classic augmentation."""
        skills_dir = self.skills_dest(project_root).resolve()
        project_root_resolved = project_root.resolve()
        skills_prefix = (
            skills_dir.relative_to(project_root_resolved).as_posix().rstrip("/")
            + "/spx-"
        )
        previous_spx_files = {
            relative
            for relative in manifest.files
            if relative.startswith(skills_prefix)
        }
        advanced_dir = self.shared_advanced_skills_dir()
        shared_references = (
            sorted((advanced_dir / "_shared").glob("*.md"))
            if advanced_dir
            else []
        )
        created: list[Path] = []
        for template_dir in self.list_advanced_skill_templates():
            source_path = template_dir / "SKILL.md"
            raw = source_path.read_text(encoding="utf-8")
            skill_name = template_dir.name
            frontmatter = self._parse_skill_frontmatter(raw)
            description = frontmatter.get("description", "")
            if not description:
                description = f"Spec Kit advanced workflow: {skill_name}"

            skill_content = self._render_skill_content(
                raw=raw,
                skill_name=skill_name,
                description=description,
                source=f"templates/advanced-skills/{skill_name}/SKILL.md",
                project_root=project_root,
                script_type=script_type,
                arg_placeholder=arg_placeholder,
                apply_invocation_conventions=False,
                template_path=source_path,
            )
            skill_content = self.render_advanced_invocations(skill_content)
            if "## Fixed Workflow Artifact Boundary" not in skill_content:
                frontmatter_text, body = self._split_frontmatter(skill_content)
                boundary = (
                    "## Fixed Workflow Artifact Boundary\n\n"
                    "Before any canonical workflow artifact access, use "
                    "`specify-runtime artifact show`; authorized writes use "
                    "`specify-runtime artifact prepare` followed by "
                    "`specify-runtime artifact submit`. Read "
                    "`references/runtime-artifact-boundary.md` for the exact contract.\n\n"
                )
                if frontmatter_text:
                    rendered_body = body.lstrip("\r\n")
                    skill_content = (
                        f"---\n{frontmatter_text}---\n\n"
                        f"{boundary}{rendered_body}"
                    )
                else:
                    skill_content = boundary + skill_content.lstrip()
            skill_dir = skills_dir / skill_name
            created.append(
                self.write_file_and_record(
                    skill_content,
                    skill_dir / "SKILL.md",
                    project_root,
                    manifest,
                )
            )
            for support_file in sorted(template_dir.rglob("*")):
                if not support_file.is_file() or support_file.name == "SKILL.md":
                    continue
                relative = support_file.relative_to(template_dir)
                destination = skill_dir / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                if (
                    relative.parts[0] == "references"
                    and support_file.suffix.lower() == ".md"
                ):
                    support_content = self.process_template(
                        support_file.read_text(encoding="utf-8"),
                        self.key,
                        script_type,
                        arg_placeholder,
                        template_path=support_file,
                        project_root=project_root,
                    )
                    support_content = self.render_advanced_invocations(
                        support_content
                    )
                    created.append(
                        self.write_file_and_record(
                            support_content,
                            destination,
                            project_root,
                            manifest,
                        )
                    )
                    continue
                shutil.copy2(support_file, destination)
                self.record_file_in_manifest(destination, project_root, manifest)
                created.append(destination)
            for shared_reference in shared_references:
                reference_content = self.process_template(
                    shared_reference.read_text(encoding="utf-8"),
                    self.key,
                    script_type,
                    arg_placeholder,
                    template_path=shared_reference,
                    project_root=project_root,
                )
                reference_content = self.render_advanced_invocations(
                    reference_content
                )
                created.append(
                    self.write_file_and_record(
                        reference_content,
                        skill_dir / "references" / shared_reference.name,
                        project_root,
                        manifest,
                    )
                )
        expected_spx_files = {
            path.resolve().relative_to(project_root_resolved).as_posix()
            for path in created
        }
        for relative in sorted(previous_spx_files - expected_spx_files):
            manifest.remove_file_if_unmodified(relative)
        return created

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
        profile = self.workflow_profile(parsed_options)
        templates = self.list_command_templates()
        passive_templates = self.list_passive_skill_templates()
        advanced_templates = self.list_advanced_skill_templates()
        if profile == "advanced":
            templates = [
                template
                for template in templates
                if template.stem in self.ADVANCED_CLASSIC_COMPANION_COMMANDS
            ]
            passive_templates = []
        if not templates and not passive_templates:
            if profile != "advanced" or not advanced_templates:
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
        runtime_snapshot = self.runtime_capability_snapshot()
        created: list[Path] = []

        if profile == "advanced":
            created.extend(
                self._install_advanced_skills(
                    project_root=project_root,
                    manifest=manifest,
                    script_type=script_type,
                    arg_placeholder=arg_placeholder,
                )
            )

        for src_file in templates:
            raw = src_file.read_text(encoding="utf-8")

            # Derive the skill name from the template stem
            command_name = src_file.stem  # e.g. "plan"
            skill_name = "sp-teams" if command_name == "team" else f"sp-{command_name.replace('.', '-')}"

            # Parse frontmatter for description
            frontmatter = self._parse_skill_frontmatter(raw)

            # Keep the original template description for ZIP parity.
            description = frontmatter.get("description", "")
            if not description:
                description = f"Spec Kit: {command_name} workflow"

            skill_content = self._render_skill_content(
                raw=raw,
                skill_name=skill_name,
                description=description,
                source=f"templates/commands/{src_file.name}",
                project_root=project_root,
                script_type=script_type,
                arg_placeholder=arg_placeholder,
                apply_invocation_conventions=True,
                template_path=src_file,
            )
            agent_name = self.config.get("name", self.key.capitalize()) if self.config else self.key.capitalize()
            skill_content = self._append_runtime_project_cognition_gate(
                content=skill_content,
                agent_name=agent_name.replace(" CLI", ""),
                command_name=command_name,
            )
            if command_name == "implement":
                skill_content = self._append_implement_leader_gate(
                    content=skill_content,
                    agent_name=agent_name.replace(" CLI", ""),
                )
            if command_name == "debug":
                skill_content = self._append_debug_leader_gate(
                    content=skill_content,
                    agent_name=agent_name.replace(" CLI", ""),
                )
                skill_content = self._append_debug_routing_contract(
                    content=skill_content,
                    agent_name=agent_name.replace(" CLI", ""),
                    snapshot=runtime_snapshot,
                )
            if command_name == "quick":
                skill_content = self._append_quick_leader_gate(
                    content=skill_content,
                    agent_name=agent_name.replace(" CLI", ""),
                )
                skill_content = self._append_quick_routing_contract(
                    content=skill_content,
                    agent_name=agent_name.replace(" CLI", ""),
                    snapshot=runtime_snapshot,
                )
            if command_name in self.RUNTIME_SUBAGENT_CONTRACT_COMMANDS:
                skill_content = self._append_delegation_surface_contract(
                    content=skill_content,
                    agent_name=agent_name.replace(" CLI", ""),
                    command_name=command_name,
                    snapshot=runtime_snapshot,
                    heading="Subagent Dispatch Contract",
                )
                skill_content = self._append_runtime_worker_result_contract(
                    content=skill_content,
                    agent_name=agent_name.replace(" CLI", ""),
                    command_name=command_name,
                    snapshot=runtime_snapshot,
                )
            skill_content = self._append_map_subagent_capability_discovery(
                content=skill_content,
                agent_name=agent_name.replace(" CLI", ""),
                command_name=command_name,
                snapshot=runtime_snapshot,
            )
            skill_content = self._append_question_tool_preference(
                content=skill_content,
                agent_name=agent_name.replace(" CLI", ""),
                command_name=command_name,
            )
            if command_name == "specify":
                skill_content = self._append_specify_pre_analysis_protocol(
                    content=skill_content,
                )
                skill_content = self._append_specify_semantic_traceability_guidance(
                    content=skill_content,
                )
            if command_name == "checklist":
                skill_content = self._append_checklist_project_cognition_guidance(
                    content=skill_content,
                )
            skill_content = self._append_planning_skill_cognition_refresh_guidance(
                content=skill_content,
                command_name=command_name,
            )
            from specify_cli.launcher import render_project_launcher_placeholders
            skill_content = render_project_launcher_placeholders(project_root, skill_content)

            # Write sp-<name>/SKILL.md
            skill_dir = skills_dir / skill_name
            skill_file = skill_dir / "SKILL.md"
            dst = self.write_file_and_record(
                skill_content, skill_file, project_root, manifest
            )
            created.append(dst)
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

        for template_dir in passive_templates:
            raw = (template_dir / "SKILL.md").read_text(encoding="utf-8")
            skill_name = template_dir.name
            frontmatter = self._parse_skill_frontmatter(raw)
            description = frontmatter.get("description", "")
            if not description:
                description = f"Spec Kit passive skill: {skill_name}"

            skill_content = self._render_skill_content(
                raw=raw,
                skill_name=skill_name,
                description=description,
                source=f"templates/passive-skills/{skill_name}/SKILL.md",
                project_root=project_root,
                script_type=script_type,
                arg_placeholder=arg_placeholder,
                apply_invocation_conventions=False,
                template_path=template_dir / "SKILL.md",
            )
            skill_dir = skills_dir / skill_name
            skill_file = skill_dir / "SKILL.md"
            dst = self.write_file_and_record(
                skill_content, skill_file, project_root, manifest
            )
            created.append(dst)
            created.extend(
                self._copy_supporting_passive_files(
                    template_dir=template_dir,
                    destination_dir=skill_dir,
                    project_root=project_root,
                    manifest=manifest,
                )
            )

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
        if not self._can_augment_generated_file(skill_path, project_root):
            return
        content = skill_path.read_text(encoding="utf-8")
        if marker in content:
            return
        self._write_augmented_skill(content + addendum, skill_path, project_root, manifest)

    def _write_augmented_skill(
        self,
        content: str,
        skill_path: Path,
        project_root: Path,
        manifest: IntegrationManifest,
    ) -> None:
        """Write a post-processed skill after resolving launcher placeholders."""

        from specify_cli.launcher import render_project_launcher_placeholders

        rendered = render_project_launcher_placeholders(project_root, content)
        self.write_file_and_record(rendered, skill_path, project_root, manifest)

    def _augment_implement_skill(
        self,
        created: list[Path],
        project_root: Path,
        manifest: IntegrationManifest,
        implement_skill: Path,
        snapshot: CapabilitySnapshot | None = None,
    ) -> None:
        """Inject the adaptive leader/worker routing contract into the implement skill."""
        if not self._can_augment_generated_file(implement_skill, project_root):
            return

        content = implement_skill.read_text(encoding="utf-8")
        agent_name_full = self.config.get("name", self.key.capitalize())
        agent_name = agent_name_full.replace(" CLI", "")

        content = self._append_runtime_project_cognition_gate(
            content=content,
            agent_name=agent_name,
            command_name="implement",
        )

        content = self._append_implement_leader_gate(
            content=content,
            agent_name=agent_name,
        )

        marker = f"## {agent_name} Adaptive Execution"
        if marker not in content:
            addendum = (
                "\n"
                f"## {agent_name} Adaptive Execution\n\n"
                f"When running `sp-implement` in {agent_name}, choose the lightest safe route for the current ready task.\n"
                "\n"
                "**Route Scenarios**:\n"
                "1. **Leader-direct**: one small or tightly coupled task, no useful parallel lane, bounded write scope, and no high-risk review trigger.\n"
                "2. **One delegated lane**: one independent bounded task whose specialist focus or context isolation materially improves quality. Compile one packet just in time, then use `one-subagent`.\n"
                "3. **Parallel delegated lanes**: multiple ready tasks with exact isolated write sets and a defined join validation. Compile only the selected packets, then use `parallel-subagents`.\n"
                "4. **Durable team state**: use `managed-team` only when coordination must outlive one in-session wave.\n"
                "5. **Blocked**: if the selected safe route is unavailable and leader-direct is not independently safe, record the blocker and recovery instead of forcing execution.\n"
                "\n"
                "For delegated waves:\n"
                f"- Use {agent_name}'s `native-subagents` lifecycle when available.\n"
                "- Fixed runtime budget: `max_parallel_subagents = 4`.\n"
                f"- Use `spawn_agent` for at most four validated isolated lanes, `wait_agent` at the explicit join, and `close_agent` after results are integrated.\n"
                "- Launch the selected parallel wave before waiting; never merge lanes with overlapping writes merely to fill capacity.\n"
                "- Re-check route safety after drift, dispatch failure, and every join. Run event-triggered review when the recorded review triggers fire.\n"
                "- Continue automatically from the smallest ready task until the confirmed scope is complete or genuinely blocked.\n"
            )
            content += addendum

        if snapshot is not None:
            content = self._append_delegation_surface_contract(
                content=content,
                agent_name=agent_name,
                command_name="implement",
                snapshot=snapshot,
                heading="Subagent Dispatch Contract",
            )

        self._write_augmented_skill(content, implement_skill, project_root, manifest)

    def _augment_debug_skill(
        self,
        created: list[Path],
        project_root: Path,
        manifest: IntegrationManifest,
        debug_skill: Path,
        snapshot: CapabilitySnapshot | None = None,
    ) -> None:
        """Inject Leader Gate, Think Subagent Dispatch, and evidence collection guidance into the debug skill."""
        if not self._can_augment_generated_file(debug_skill, project_root):
            return

        content = debug_skill.read_text(encoding="utf-8")
        agent_name_full = self.config.get("name", self.key.capitalize())
        agent_name = agent_name_full.replace(" CLI", "")

        content = self._append_runtime_project_cognition_gate(
            content=content,
            agent_name=agent_name,
            command_name="debug",
        )

        gate_marker = f"## {agent_name} Leader Gate"
        if gate_marker not in content:
            gate_addendum = (
                "\n"
                f"## {agent_name} Leader Gate\n\n"
                f"When running `sp-debug` in {agent_name}, you are the **leader**, not a freeform debugger.\n"
                "\n"
                f"{self._project_cognition_query_gate_line(command_name='debug', command_step='before any investigation or fixes')}\n"
                "\n"
                "Before applying fixes or running investigation actions:\n"
                "- Read the current debug session state and choose `execution_model: leader-inline | subagent-assisted | blocked` from the investigation shape.\n"
                "- Use `leader-inline` for a small focused investigation with one short evidence chain.\n"
                "- Use `subagent-assisted` when there are two or more independent evidence-gathering lanes, broad surface area, or meaningful parallelism.\n"
                "- If the next step is unsafe, unavailable, or unpacketizable, record `subagent-blocked`, `execution_surface: none`, and a concrete `blocked_reason` before stopping.\n"
                f"- Use `wait_agent` at the investigation join point, integrate returned results, and call `close_agent` for completed subagents.\n"
                "\n"
                "**Hard rule:** During `investigating`, the leader must not let subagents mutate the debug file, declare the root cause final, or advance the session state.\n"
            )
            if "## Session Lifecycle" in content:
                content = content.replace("## Session Lifecycle", gate_addendum + "\n## Session Lifecycle", 1)
            else:
                content += gate_addendum

        think_gate_marker = f"## {agent_name} Deep Debug Intake Dispatch"
        if think_gate_marker not in content:
            think_addendum = (
                "\n"
                f"## {agent_name} Deep Debug Intake Dispatch\n\n"
                f"When running `sp-debug` in {agent_name}, use the project cognition compass packet as the default "
                "intake source. If the **Gathering** stage can build `map-backed-minimum-intake`, continue directly "
                "into evidence investigation with the primary candidate, contrarian candidate, transition memo, "
                "and log plan already recorded.\n"
                "\n"
                "If project cognition is missing, ambiguous, stale, or insufficient for the failing area, Gathering "
                "may return an `await_input` containing a `think_subagent_prompt`. This prompt is a self-contained "
                "deep fallback reasoning task for a fresh subagent.\n"
                "\n"
                "**When you receive a think_subagent_prompt:**\n"
                "- Spawn a subagent with the exact prompt text via `spawn_agent`.\n"
                "- The think subagent does NOT read source code and does NOT run commands — it is a pure reasoning agent.\n"
                "- Use `wait_agent` to wait for the think subagent's result.\n"
                "- The result is hybrid: free-text analysis followed by `---` and a YAML block.\n"
                "- Parse the YAML block after `---` and populate these fields in the debug state:\n"
                "  - `causal_map` (symptom_anchor, closed_loop_path, break_edges, bypass_paths, family_coverage, candidates, adjacent_risk_targets, dimension_scan, candidate_board)\n"
                "- Ensure Stage 1A covers at least 3 families and every family includes a falsifier.\n"
                "- These Stage 1A candidates are still the observer-framing alternative cause candidates; do not collapse them into one family too early.\n"
                "- Set `causal_map_completed` to `True`.\n"
                "- Then continue the debug session — the next GatheringNode run will request the contract planner stage.\n"
                "- If Gathering returns `contract_subagent_prompt`, use it for the contract-planner subagent and feed its result back into `observer_framing`, `transition_memo`, `investigation_contract`, and top-level `log_investigation_plan`.\n"
                "- Treat the causal-map output as Stage 1A and the contract-planner output as Stage 1B. Investigation starts only after both stages are complete, unless map-backed minimum intake already completed those fields.\n"
                "- Stage 1B must still produce a primary suspected loop, a contrarian candidate, and a recommended first probe before investigation begins.\n"
                "- Do NOT skip the think subagent once the runtime requested deep fallback. Context isolation is the purpose of that step.\n"
            )
            content = content.replace(
                "**Hard rule:** During `investigating`",
                think_addendum + "\n**Hard rule:** During `investigating`",
                1,
            )

        marker = f"## {agent_name} Subagent Evidence Collection"
        if marker in content:
            return

        addendum = (
            "\n"
            f"## {agent_name} Subagent Evidence Collection\n\n"
            f"When running `sp-debug` in {agent_name}, choose leader-inline or subagent-assisted evidence collection from the investigation shape.\n"
            "- Execution model: `leader-inline | subagent-assisted | blocked`.\n"
            "- Dispatch shape: `leader-inline`, `one-subagent`, `parallel-subagents`, or `subagent-blocked`.\n"
            "- Execution surface: `leader-inline`, `native-subagents`, or `none`.\n"
            "- Small focused investigation -> `leader-inline`.\n"
            "- One safe isolated evidence lane -> `one-subagent` when the current runtime supports it safely.\n"
            "- Two or more independent evidence lanes -> `parallel-subagents` when the current runtime supports it safely.\n"
            "- Unsafe, unavailable, or unpacketizable next step -> `subagent-blocked` with `execution_surface: none` and `blocked_reason`.\n"
            f"- If there are two or more independent evidence-gathering lanes, dispatch subagents through `spawn_agent` instead of doing manual sequential investigation.\n"
            "- Suitable subagent tasks include running targeted tests or repro commands, collecting logs and exit codes, searching for error text, tracing isolated code paths, and gathering evidence after diagnostic logging has been added.\n"
            "- Read `diagnostic_profile` from the debug session before choosing subagent lanes.\n"
            "- The leader **MUST** update the debug file's `Current Focus` before dispatching subagents and treat subagent work as evidence collection for the current hypothesis.\n"
            "- The think-subagent output is an investigation contract, not advisory prose.\n"
            "- The investigating stage must consume the candidate queue and primary candidate before freeform fixes begin.\n"
            "- After two automated verification failures, switch the session into root-cause mode and stop layering point fixes.\n"
            "- Do not close the session until nearest-neighbor related risk targets have been reviewed.\n"
            "- Subagents must return facts, command results, and observations; they must not update the debug file, declare the root cause final, or transition the session state.\n"
            "- Wait for every subagent's structured handoff before accepting the join point or changing the investigation stage.\n"
            "- Wait for every delegated lane's structured handoff before accepting the join point or changing the investigation stage.\n"
            "- Do not treat an idle subagent as done work; idle without a consumed handoff means the evidence lane is still unresolved.\n"
            "- Do not interrupt or shut down subagent work before the handoff has been written or explicitly reported as `BLOCKED` or `NEEDS_CONTEXT`.\n"
            f"- Use `wait_agent` only after the current investigation fan-out reaches its join point.\n"
            f"- Use `close_agent` after integrating finished subagent results.\n"
            "- Do not resolve the session directly from successful automated verification. Successful automated verification must hand off into formal human verification.\n"
            "- If human feedback reports another problem, classify it as `same_issue`, `derived_issue`, or `unrelated_issue`.\n"
            "- Default to `same_issue` unless strong evidence proves the other classes.\n"
            "- Keep fixing, agent verification, `awaiting_human_verify`, and final session resolution on the leader path.\n"
        )

        content = content + addendum
        if snapshot is not None:
            content = self._append_delegation_surface_contract(
                content=content,
                agent_name=agent_name,
                command_name="debug",
                snapshot=snapshot,
                heading="Subagent Dispatch Contract",
            )

        self._write_augmented_skill(content, debug_skill, project_root, manifest)

    def _augment_quick_skill(
        self,
        created: list[Path],
        project_root: Path,
        manifest: IntegrationManifest,
        quick_skill: Path,
        snapshot: CapabilitySnapshot | None = None,
    ) -> None:
        """Inject Leader Gate and delegation guidance into the quick-task skill."""
        if not self._can_augment_generated_file(quick_skill, project_root):
            return

        content = quick_skill.read_text(encoding="utf-8")
        agent_name_full = self.config.get("name", self.key.capitalize())
        agent_name = agent_name_full.replace(" CLI", "")

        content = self._append_runtime_project_cognition_gate(
            content=content,
            agent_name=agent_name,
            command_name="quick",
        )

        gate_marker = f"## {agent_name} Leader Gate"
        if gate_marker not in content:
            gate_addendum = (
                "\n"
                f"## {agent_name} Leader Gate\n\n"
                f"When running `sp-quick` in {agent_name}, you are the **leader**, not the concrete implementer.\n"
                "\n"
                f"{self._project_cognition_query_gate_line(command_name='quick', command_step='before repository analysis or implementation')}\n"
                "\n"
                "Before code edits, test edits, or implementation commands:\n"
                "- Read `.specify/memory/constitution.md` first if it exists.\n"
                "- Read `STATUS.md` for the active quick-task workspace, or create it if this quick task is new.\n"
                "- If `understanding_confirmed` is not `true`, present the Understanding Checkpoint and wait for user confirmation before implementation work.\n"
                "- The user-facing checkpoint must use the fixed Quick Checkpoint Markdown table with `| Decision to confirm | Current understanding |` and rows for `Request and outcome`, `User-visible result`, `Scope`, `Recommended approach`, `Assumptions and risks`, `Completion evidence`, and `Reconfirmation trigger`; technical execution stays agent-owned, and prose bullets or partial field lists are not sufficient. For applicable UI work, append the independent UI Confirmation card and ask once for both decisions.\n"
                "- Do not proceed to code edits, broad repository analysis, delegation, or validation commands until `understanding_confirmed: true` is recorded in `STATUS.md`.\n"
                "- After understanding is confirmed, define the smallest safe delegated lane or ready batch, and choose the dispatch shape for that batch.\n"
                "- Dispatch `one-subagent` when one validated `WorkerTaskPacket` or equivalent execution contract preserves quality.\n"
                "- Dispatch `parallel-subagents` when two or more safe subagent lanes would materially improve throughput.\n"
                f"- Use `native-subagents` through `spawn_agent` before considering any fallback path.\n"
                "- If that bar is not met, keep the lane on the leader path until the missing context, constraints, validation target, or handoff expectations are explicit.\n"
                f"- Use `wait_agent` only at the current join point, integrate returned results, and call `close_agent` for completed subagents.\n"
                "- Wait for every subagent's structured handoff before accepting the join point, closing the batch, or declaring completion.\n"
                "- Do not treat an idle subagent as done work; idle without a consumed handoff means the result channel is still unresolved.\n"
                "- Do not interrupt or shut down subagent work before the handoff has been written or explicitly reported as `BLOCKED` or `NEEDS_CONTEXT`.\n"
                "- Use `managed-team` only when durable team state is needed beyond one in-session subagent burst.\n"
                "- Use `subagent-blocked` only when subagent dispatch and `sp-teams` are both unavailable or unsafe.\n"
                "- When `subagent-blocked` is used, you **MUST** write the concrete blocker reason into `STATUS.md` before escalating or stopping locally.\n"
                "\n"
                "**Hard rule:** The leader must keep scope control, strategy selection, join-point handling, validation, summary ownership, and `STATUS.md` accuracy while subagent execution is active.\n"
            )
            if "## Process" in content:
                content = content.replace("## Process", gate_addendum + "\n## Process", 1)
            else:
                content += gate_addendum

        marker = f"## {agent_name} Quick-Task Subagent Execution"
        if marker in content:
            if snapshot is not None:
                content = self._append_delegation_surface_contract(
                    content=content,
                    agent_name=agent_name,
                    command_name="quick",
                    snapshot=snapshot,
                    heading="Subagent Dispatch Contract",
                )
            self._write_augmented_skill(content, quick_skill, project_root, manifest)
            return

        addendum = (
            "\n"
            f"## {agent_name} Quick-Task Subagent Execution\n\n"
            f"When running `sp-quick` in {agent_name}, start execution routing only after `STATUS.md` exists and `understanding_confirmed: true` is recorded.\n"
            "- Understanding checkpoint: before dispatch, render the fixed Quick Checkpoint Markdown table with `| Decision to confirm | Current understanding |` and user-owned rows for request/outcome, visible result, scope, recommended approach, assumptions/risks, completion evidence, and reconfirmation trigger. Append the UI Confirmation proposal when applicable and use one combined confirmation.\n"
            "- Dispatch `one-subagent` or `parallel-subagents` only after the Understanding Checkpoint is confirmed.\n"
            "- Use `subagent-blocked` only after native subagents and the managed-team path are unavailable or unsafe, and record the blocker reason in `STATUS.md`.\n"
            f"- Use `spawn_agent` for bounded lanes such as focused repository analysis, targeted implementation, regression test updates, or validation command runs.\n"
            "- Once the first lane is chosen, dispatch it before continuing any leader-inline deep-dive analysis of the repository.\n"
            "- If multiple safe subagent lanes exist and they materially improve throughput, dispatch them in parallel.\n"
            f"- Use `wait_agent` only at the documented join point for the current quick-task batch.\n"
            f"- Use `close_agent` after integrating finished subagent results.\n"
            "- Keep `.planning/quick/<id>-<slug>/STATUS.md` as the leader-owned source of truth.\n"
            "- Subagents may return evidence, patches, and verification output, but they must not become the authority for resume state; the leader updates `STATUS.md` before and after each join point.\n"
            f"- Decision order for {agent_name} `sp-quick`: safe packetized subagents -> `managed-team` when durable state is needed -> `subagent-blocked` with reason.\n"
            "- Prefer subagent execution only when a validated `WorkerTaskPacket` or equivalent execution contract preserves quality.\n"
            "- Re-check strategy after every join point and continue automatically until the quick task is complete or blocked.\n"
        )

        content = content + addendum
        if snapshot is not None:
            content = self._append_delegation_surface_contract(
                content=content,
                agent_name=agent_name,
                command_name="quick",
                snapshot=snapshot,
                heading="Subagent Dispatch Contract",
            )

        self._write_augmented_skill(content, quick_skill, project_root, manifest)

    def _augment_implement_teams_result_contract(
        self,
        created: list[Path],
        project_root: Path,
        manifest: IntegrationManifest,
        implement_teams_skill: Path,
        snapshot: CapabilitySnapshot,
    ) -> None:
        """Append the shared implement result contract to a teams-backed skill."""
        if not self._can_augment_generated_file(implement_teams_skill, project_root):
            return

        content = implement_teams_skill.read_text(encoding="utf-8")
        agent_name_full = self.config.get("name", self.key.capitalize())
        agent_name = agent_name_full.replace(" CLI", "")
        content = self._append_runtime_worker_result_contract(
            content=content,
            agent_name=agent_name,
            command_name="implement",
            snapshot=snapshot,
        )
        self._write_augmented_skill(content, implement_teams_skill, project_root, manifest)

    def _augment_implement_teams_shared_contract(
        self,
        created: list[Path],
        project_root: Path,
        manifest: IntegrationManifest,
        implement_teams_skill: Path,
        *,
        canonical_command: str,
        teams_command: str,
        backend_label: str,
    ) -> None:
        """Append the shared sp-implement contract to a teams-backed skill."""
        if not self._can_augment_generated_file(implement_teams_skill, project_root):
            return

        content = implement_teams_skill.read_text(encoding="utf-8")
        marker = f"## Shared Contract With `{canonical_command}`"
        if marker in content:
            return

        addendum = (
            "\n"
            f"## Shared Contract With `{canonical_command}`\n\n"
            f"`{canonical_command}` remains the canonical implementation workflow. "
            f"`{teams_command}` is the same execution contract with the concrete team-managed work pinned to {backend_label}.\n\n"
            f"When you use `{teams_command}`, keep the same leader-owned execution semantics that `{canonical_command}` requires:\n\n"
            "1. keep canonical task status, compact execution state, and one lifecycle record per executed task aligned\n"
            "2. compile and validate a `WorkerTaskPacket` just in time before assigning each team-managed execution task\n"
            "3. for implementation-oriented teams flows, preserve the user-visible fields `execution_model`, `dispatch_shape`, and `execution_surface`\n"
            "4. preserve explicit join behavior, blocker/recovery reporting, event-triggered review, and completion checks\n"
            "5. preserve the team result contract and canonical result file handoff path\n"
            "6. preserve final-completion truthfulness: do not describe `core implementation complete`, `implementation complete`, or `ready for integration testing` as overall feature completion while required E2E, Polish, documentation, quickstart, or validation work remains\n\n"
            "Every team-managed task in the teams-backed flow must still behave like an explicit execution packet, not a chat-only summary. Preserve these fields whenever the backend exposes task records, mailbox messages, or equivalent runtime-managed assignments:\n\n"
            "1. task id and subject\n"
            "2. write set and shared surfaces\n"
            "3. required references and forbidden drift\n"
            "4. explicit verification command or acceptance check\n"
            "5. canonical result handoff path or runtime-managed result channel expectation\n"
            "6. completion-handoff protocol covering start, blocker, and final completion evidence\n"
            "7. platform guardrails such as supported platforms, conditional compilation requirements, or other environment-sensitive constraints\n\n"
            f"Before {backend_label} starts concrete work, ensure the current ready batch is prepared the same way `{canonical_command}` would prepare it:\n\n"
            "1. the current batch is recorded in canonical task and compact execution state\n"
            "2. each team-managed task has a validated `WorkerTaskPacket`\n"
            "3. join point expectations and result handoff expectations are explicit\n"
            "4. the team-managed lane cannot be treated as complete from a status flip alone; the leader still needs the promised completion handoff or result evidence\n\n"
            "Before assigning team-managed work, preserve the same project cognition compass contract that `sp-implement` uses:\n\n"
            "1. run `{{specify-subcmd:specify-runtime cognition compass --intent implement --query=\"$ARGUMENTS\" --format json}}` and include the compass packet in the execution context bundle\n"
            f"2. {EPISTEMIC_CONTRACT_GUIDANCE} Carry `epistemic_contract` in every teammate context packet.\n"
            "3. read top-level `minimal_live_reads` first, then use lane-level `first_pass_paths` reasons, evidence hints, `verification_hints`, `followup_surfaces`, and `before_fix_claim` checks\n"
            "4. preserve `coverage_diagnostics` as confidence and closeout signals, not route candidates\n"
            "5. treat `expansion_ref` as a normal continuation path and run `{{specify-subcmd:specify-runtime cognition expand --id <id> --section <section> --format json}}` only when coverage state or live evidence requires more map detail\n"
            "6. do not infer final edit scope from `minimal_live_reads` or `first_pass_paths`; carry them as advisory first-pass evidence routes in every teammate context packet\n"
            "7. use the advanced `lexicon -> semantic_intake -> query` path only when explicit concept decisions are needed or coverage cannot be resolved from the default compass packet\n"
            "8. in that precision escalation, normalize user input and write a `semantic_intake` object with `workflow_intent`, `normalized_query`, `intent_facets`, `negative_constraints`, `alias_interpretations`, and `open_semantic_questions`\n"
            "9. treat `agent_normalization.required=true` as a non-intelligent CLI reminder to write `semantic_intake` from the alias catalog (raw lexicon ranking is only a bootstrap; action: write_semantic_intake_from_alias_catalog); if `agent_normalization` is omitted, treat it as `required=false`, not as proof that raw lexical ranking is authoritative\n"
            "10. keep CJK or mixed CJK/ASCII input in agent-owned normalization even when positive raw lexical matches exist because embedded project tokens do not translate the surrounding user language; the agent still owns translation and `agent_normalization` is advisory guidance, not a route decision\n"
            "11. keep `alias_interpretations` object-shaped, for example `{\"alias\": \"<user term>\", \"meaning\": \"<project term>\", \"confidence\": \"medium\"}`, never as a string array\n"
            "12. build a `query_plan` with `selected_concepts`, `rejected_concepts`, `concept_decisions`, `covered_facets`, `missing_facets`, `match_sources`, `lexicon_generation_id`, `expanded_queries`, `repository_search_terms`, and justified `paths`\n"
            "13. derive project-language search terms from the alias catalog before source search; do not search only the raw user words; include component names, state names, file names, command names, UI labels, and route names from candidates, aliases, matched terms, returned paths, `normalized_query`, and `expanded_queries`\n"
            "14. run `{{specify-subcmd:specify-runtime cognition query --intent implement --query-plan \"<query_plan_json>\" --format json}}` only for that precision escalation, and preserve returned readiness, `minimal_live_reads`, `first_pass_paths`, and the task-local bundle in every teammate context packet\n"
            "15. if the query reports diagnostics, preserve `warnings`, `repair_hints`, normalized `query_plan`, structured `errors`, and `expected_shape` so the leader can repair the plan instead of losing the diagnostics in team chat\n\n"
            "The only intended difference is the dispatch path:\n\n"
            f"1. `{canonical_command}` may route the current ready batch through subagents first\n"
            f"2. `{teams_command}` forces the concrete team-managed execution through {backend_label} for the same batch and join-point semantics\n"
            f"3. {backend_label} must not weaken the tracker, packet, validation, or completion contract\n"
        )

        if "## Execution Contract" in content:
            content = content.replace("## Execution Contract", addendum + "\n## Execution Contract", 1)
        else:
            content += addendum
        self._write_augmented_skill(content, implement_teams_skill, project_root, manifest)
