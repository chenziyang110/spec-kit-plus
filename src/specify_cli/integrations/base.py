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

    question_tool_config: dict[str, Any] | None = None
    """Optional structured-question-tool metadata for the integration."""

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
        excluded_templates = {"team.md", "implement-teams.md"}
        return sorted(
            f
            for f in cmd_dir.iterdir()
            if f.is_file() and f.suffix == ".md" and f.name not in excluded_templates
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

    def _question_tool_use_cases(self, command_name: str) -> list[str]:
        use_cases = {
            "specify": [
                "planning-critical clarification",
                "capability split confirmation",
                "current-understanding confirmation before `Aligned: ready for plan`",
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
                "missing-information questions during observer framing",
                "compressed observer framing when the user already supplied strong low-level evidence",
            ],
        }
        return use_cases.get(command_name, [])

    def _question_tool_fallback_hint(self, command_name: str) -> str:
        fallback_hints = {
            "specify": "If the native tool is unavailable in the current runtime or the tool call fails, fall back to the shared open question block structure already defined in this template.",
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
        question_driven_commands = {"specify", "clarify", "deep-research", "checklist", "quick", "debug"}
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
            "- If the runtime's native structured question tool is available for the current turn, you must use it.",
            "- Do not render the textual fallback block when the native tool is available.",
            "- Do not self-authorize textual fallback because the question seems simple, short, or easy to phrase manually.",
            "- Treat the template's textual question format as fallback-only guidance; use it to shape the question content, but do not render the textual block unless the native tool is unavailable in the current runtime or the tool call fails.",
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
        addendum = (
            "\n"
            f"## {agent_name} {heading}\n\n"
            "- Execution model: `subagents-first`\n"
            "- Dispatch shape: `one-subagent`, `parallel-subagents`, or `leader-inline-fallback`\n"
            "- Execution surface: `native-subagents`, `managed-team`, or `leader-inline`\n"
            "- Delegation surface contract: preserve the native dispatch, fallback, worker result contract, and handoff path below.\n"
            f"- Native subagent dispatch: {descriptor.native_dispatch_hint}\n"
            f"- Join behavior: {descriptor.native_join_hint}\n"
            f"- Managed-team fallback: {managed_team_hint}\n"
            "- Leader-inline fallback: record the reason before local execution.\n"
            f"- Worker result contract: {descriptor.result_contract_hint}\n"
            f"- Result contract: {descriptor.result_contract_hint}\n"
            f"- Result handoff path: {descriptor.result_handoff_hint}\n"
        )
        return content + addendum

    def _append_runtime_project_map_gate(
        self,
        *,
        content: str,
        agent_name: str,
        command_name: str,
    ) -> str:
        """Append a hard project-map read gate for runtime-facing commands when absent."""

        if command_name not in {"implement", "debug", "quick"}:
            return content

        marker = f"## {agent_name} Project-Map Hard Gate"
        if marker in content:
            return content

        command_step = {
            "implement": "before any implementation actions",
            "debug": "before any investigation or fixes",
            "quick": "before repository analysis or implementation",
        }[command_name]

        addendum = (
            "\n"
            f"## {agent_name} Project-Map Hard Gate\n\n"
            f"**Crucial First Step**: You MUST read `PROJECT-HANDBOOK.md` and relevant `.specify/project-map/*.md` files {command_step}.\n"
            "- If the handbook or required topical documents are missing, stale, or too broad for the touched area, run `/sp-map-scan` followed by `/sp-map-build` before continuing.\n"
            "- Treat this as a hard gate, not a best-effort reminder; do not continue on chat memory or local instincts when the project map should be the source of truth.\n"
        )

        insert_before = None
        if "## Outline" in content:
            insert_before = "## Outline"
        elif "## Process" in content:
            insert_before = "## Process"
        elif "## Session Lifecycle" in content:
            insert_before = "## Session Lifecycle"

        if insert_before:
            return content.replace(insert_before, addendum + f"\n{insert_before}", 1)
        return content + addendum

    def runtime_capability_snapshot(self) -> CapabilitySnapshot:
        """Return the best available capability snapshot for this integration."""

        local_snapshot = getattr(self, "_runtime_capability_snapshot", None)
        if callable(local_snapshot):
            return local_snapshot()

        package_name = type(self).__module__.rsplit(".", 1)[0]
        try:
            module = importlib.import_module(f"{package_name}.multi_agent")
        except ImportError:
            module = None

        if module is not None:
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
            f"When running `sp-implement` in {agent_name}, you are the **leader**, not the concrete implementer.\n"
            "\n"
            "**Crucial First Step**: You MUST read `PROJECT-HANDBOOK.md` and relevant `.specify/project-map/*.md` files to understand the architectural boundaries and conventions before any implementation actions.\n"
            "\n"
            "**Autonomous Blocker Recovery (Hard Rule)**:\n"
            "- If technical blockers arise (e.g. build errors, missing toolchain components like Win32/x86, environment mismatches), you **MUST** attempt autonomous escalation to a specialist subagent (for example a build/toolchain specialist) **BEFORE** asking the user for intervention.\n"
            "- Only stop and ask the user if the specialist lane confirms that manual human action (like physical installer execution) is the ONLY remaining path.\n"
            "\n"
            "Before any code edits, test edits, build commands, or implementation actions:\n"
            "- Read `FEATURE_DIR/implement-tracker.md` first if it exists, and resume from its recorded blocker, recovery, replanning, or validation state before choosing a new batch.\n"
            "- When the local CLI is available, use `specify hook validate-state --command implement --feature-dir \"$FEATURE_DIR\"` and `specify hook validate-session-state --command implement --feature-dir \"$FEATURE_DIR\"` before choosing the next batch so shared product checks verify the execution state.\n"
            "- **Audit Missed Dispatches**: If you find tasks in the tracker that you performed yourself but could have been delegated, record them under a `missed_agent_dispatch` field in the tracker as a recovery debt.\n"
            "- If `$ARGUMENTS` is non-empty, extract the important execution constraints or recovery hints from it and persist them under `## User Execution Notes` in `FEATURE_DIR/implement-tracker.md` before dispatching work.\n"
            "- Read `tasks.md`, identify the current ready batch, and choose the `subagents-first` dispatch shape for that batch.\n"
            "- Use subagents by default when the current batch can be delegated safely.\n"
            "- Dispatch `one-subagent` when one validated `WorkerTaskPacket` is ready.\n"
            "- Dispatch `parallel-subagents` when multiple validated packets have isolated write sets.\n"
            "- Use the current runtime's `native-subagents` path first when `delegation_confidence` makes subagent execution safe.\n"
            "- Use `leader-inline-fallback` only after recording why delegation is unavailable, unsafe, or not packetized in `FEATURE_DIR/implement-tracker.md`.\n"
            "- Before any subagent implementation work starts, compile and validate the packet for the current task or batch item.\n"
            "- Before subagent dispatch, prefer `specify hook validate-packet --packet-file <packet-json>` when the current runtime has written the packet to disk.\n"
            "- Do **not** fall through from subagent dispatch into local self-execution just because the implementation looks feasible.\n"
            "- If the subagent-readiness bar is not met, use `leader-inline-fallback` until the missing context, hard rules, validation gates, or handoff requirements are compiled. Do not dispatch a low-context subagent just to satisfy a routing preference.\n"
            "- Wait for every subagent's structured handoff before accepting the join point, closing the batch, or declaring completion.\n"
            "- Do not treat an idle subagent as done work; idle without a consumed handoff means the result channel is still unresolved.\n"
            "- Do not interrupt or shut down subagent work before the handoff has been written or explicitly reported as `BLOCKED` or `NEEDS_CONTEXT`.\n"
            "- Dispatch only from validated `WorkerTaskPacket`.\n"
            "\n"
            "**Hard rule:** The leader must not edit implementation files directly while subagent execution is active.\n"
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
        addendum = (
            "\n"
            f"## {agent_name} Subagent Result Contract\n\n"
            "- Worker result contract: preserve the shared `WorkerTaskResult` semantics even when the runtime calls lanes subagents.\n"
            f"- Preferred result contract: {descriptor.result_contract_hint}\n"
            f"- Result file handoff path: {descriptor.result_handoff_hint}\n"
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
            "**Crucial First Step**: You MUST read `PROJECT-HANDBOOK.md` and relevant `.specify/project-map/*.md` files to understand the architectural boundaries and conventions before any investigation or fixes.\n"
            "\n"
            "Before applying fixes or running multiple independent investigation actions yourself:\n"
            "- Read the current debug session state and identify whether the investigation has two or more independent evidence-gathering lanes.\n"
            "- If the current stage is `investigating` and there are two or more bounded evidence-gathering lanes, you **MUST** dispatch subagents before continuing with more sequential evidence collection yourself.\n"
            "- Rejoin only at the current investigation join point, then integrate returned results on the leader path.\n"
            "- If subagent evidence collection is unavailable or unsuitable, record `leader-inline-fallback` and use the managed team workflow before widening leader-inline investigation work.\n"
            "- Do **not** skip subagents just because the evidence tasks look easy; use `leader-inline-fallback` only when the current investigation does not have safe parallel lanes.\n"
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
            f"When running `sp-debug` in {agent_name}, treat the `investigating` stage as a leader-led `subagents-first` routing decision.\n"
            "- Dispatch shape: `parallel-subagents` for independent evidence lanes, or `leader-inline-fallback` with a recorded reason when delegation is unavailable or unsafe.\n"
            "- Execution surface: `native-subagents` first, `managed-team` only when durable team state is needed, and `leader-inline` only as fallback.\n"
            f"- Subagent dispatch: {descriptor.native_dispatch_hint}\n"
            f"- Integration-native join point: {descriptor.native_join_hint}\n"
            f"- Fallback path: {managed_team_hint}\n"
            "- If there are two or more independent evidence-gathering lanes, dispatch subagents whenever the current runtime can support it safely.\n"
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
            "**Crucial First Step**: You MUST read `PROJECT-HANDBOOK.md` and relevant `.specify/project-map/*.md` files to understand the architectural boundaries and conventions before repository analysis or implementation.\n"
            "\n"
            "Before code edits, test edits, or implementation commands:\n"
            "- Read `.specify/memory/constitution.md` first if it exists.\n"
            "- Read `STATUS.md` for the active quick-task workspace, or create it if this quick task is new.\n"
            "- When the local CLI is available, use `specify hook validate-state --command quick --workspace <quick-workspace>` and `specify hook validate-session-state --command quick --workspace <quick-workspace>` before choosing the next lane so shared product checks verify quick-task resume truth.\n"
            "- Define the smallest safe delegated lane or ready batch, and choose the `subagents-first` dispatch shape for that batch.\n"
            "- Dispatch `one-subagent` when one validated `WorkerTaskPacket` or equivalent execution contract preserves quality.\n"
            "- Dispatch `parallel-subagents` when two or more safe subagent lanes would materially improve throughput.\n"
            "- Use the current runtime's `native-subagents` path before considering any fallback path.\n"
            "- If that bar is not met, keep the lane on the leader path until the missing context, constraints, validation target, or handoff expectations are explicit.\n"
            "- Use the current integration's join point to integrate returned results before choosing the next action.\n"
            "- Wait for every subagent's structured handoff before accepting the join point, closing the batch, or declaring completion.\n"
            "- Do not treat an idle subagent as done work; idle without a consumed handoff means the result channel is still unresolved.\n"
            "- Do not interrupt or shut down subagent work before the handoff has been written or explicitly reported as `BLOCKED` or `NEEDS_CONTEXT`.\n"
            "- Use `managed-team` only when durable team state is needed beyond one in-session subagent burst.\n"
            "- Use `leader-inline-fallback` only when subagent dispatch and the managed team workflow are both unavailable or unsafe.\n"
            "- When `leader-inline-fallback` is used, you **MUST** write the concrete fallback reason into `STATUS.md` before executing locally.\n"
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
            f"When running `sp-quick` in {agent_name}, use `subagents-first` execution after `STATUS.md` exists.\n"
            "- Dispatch shape: `one-subagent`, `parallel-subagents`, or `leader-inline-fallback`.\n"
            "- Execution surface: `native-subagents`, `managed-team`, or `leader-inline`.\n"
            f"- Subagent dispatch: {descriptor.native_dispatch_hint}\n"
            f"- Integration-native join point: {descriptor.native_join_hint}\n"
            f"- Fallback path: {managed_team_hint}\n"
            "- Once the first lane is chosen, dispatch it before continuing any leader-inline deep-dive analysis of the repository.\n"
            "- If multiple safe subagent lanes exist and they materially improve throughput, dispatch them in parallel.\n"
            "- Keep `.planning/quick/<id>-<slug>/STATUS.md` as the leader-owned source of truth.\n"
            "- Before compaction-risk transitions or join points, prefer `specify hook monitor-context --command quick --workspace <quick-workspace>` and follow checkpoint recommendations with `specify hook checkpoint --command quick --workspace <quick-workspace>`.\n"
            "- Subagents may return evidence, patches, and verification output, but they must not become the authority for resume state; the leader updates `STATUS.md` before and after each join point.\n"
            f"- Decision order for {agent_name} `sp-quick`: safe packetized subagents -> `managed-team` when durable state is needed -> `leader-inline-fallback` with reason.\n"
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
    def process_template(
        content: str,
        agent_name: str,
        script_type: str,
        arg_placeholder: str = "$ARGUMENTS",
        template_path: Path | None = None,
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
            )
            agent_name = self.config.get("name", self.key.capitalize()) if self.config else self.key.capitalize()
            processed = self._append_runtime_project_map_gate(
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
            if src_file.stem in {"implement", "debug", "quick", "test-scan", "test-build"}:
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
            processed = self._append_question_tool_preference(
                content=processed,
                agent_name=agent_name.replace(" CLI", ""),
                command_name=src_file.stem,
            )
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
            )
            agent_name = self.config.get("name", self.key.capitalize()) if self.config else self.key.capitalize()
            processed = self._append_runtime_project_map_gate(
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
            if src_file.stem in {"implement", "debug", "quick", "test-scan", "test-build"}:
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
            processed = self._append_question_tool_preference(
                content=processed,
                agent_name=agent_name.replace(" CLI", ""),
                command_name=src_file.stem,
            )
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
    ``sp-<name>/SKILL.md`` file with skills-oriented frontmatter, and
    may also install passive repository skills from
    ``templates/passive-skills/<name>/SKILL.md``.
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
        script_type: str,
        arg_placeholder: str,
        template_path: Path | None = None,
    ) -> str:
        """Render a command or passive skill template into normalized ``SKILL.md``."""
        processed_body = self.process_template(
            raw,
            self.key,
            script_type,
            arg_placeholder,
            template_path=template_path,
        )
        if processed_body.startswith("---"):
            parts = processed_body.split("---", 2)
            if len(parts) >= 3:
                processed_body = parts[2]

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
        templates = self.list_command_templates()
        passive_templates = self.list_passive_skill_templates()
        if not templates and not passive_templates:
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
                script_type=script_type,
                arg_placeholder=arg_placeholder,
                template_path=src_file,
            )
            agent_name = self.config.get("name", self.key.capitalize()) if self.config else self.key.capitalize()
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
            if command_name in {"implement", "debug", "quick", "test-scan", "test-build"}:
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
            skill_content = self._append_question_tool_preference(
                content=skill_content,
                agent_name=agent_name.replace(" CLI", ""),
                command_name=command_name,
            )

            # Write sp-<name>/SKILL.md
            skill_dir = skills_dir / skill_name
            skill_file = skill_dir / "SKILL.md"
            dst = self.write_file_and_record(
                skill_content, skill_file, project_root, manifest
            )
            created.append(dst)

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
                script_type=script_type,
                arg_placeholder=arg_placeholder,
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
        self.write_file_and_record(content + addendum, skill_path, project_root, manifest)

    def _augment_implement_skill(
        self,
        created: list[Path],
        project_root: Path,
        manifest: IntegrationManifest,
        implement_skill: Path,
        snapshot: CapabilitySnapshot | None = None,
    ) -> None:
        """Inject Leader Gate and subagents-first guidance into the implement skill."""
        if not self._can_augment_generated_file(implement_skill, project_root):
            return

        content = implement_skill.read_text(encoding="utf-8")
        agent_name_full = self.config.get("name", self.key.capitalize())
        agent_name = agent_name_full.replace(" CLI", "")

        content = self._append_implement_leader_gate(
            content=content,
            agent_name=agent_name,
        )

        marker = f"## {agent_name} Subagents-First Execution"
        if marker not in content:
            addendum = (
                "\n"
                f"## {agent_name} Subagents-First Execution\n\n"
                f"When running `sp-implement` in {agent_name}, use the `subagents-first` dispatch model.\n"
                "\n"
                "**Standard Dispatch Scenarios**:\n"
                "1. **One Ready Lane**: If one validated `WorkerTaskPacket` is ready -> dispatch `one-subagent` on `native-subagents`.\n"
                "2. **Parallel Creation**: If multiple packetized lanes have isolated write sets -> dispatch `parallel-subagents` on `native-subagents`.\n"
                "3. **Durable Team State**: If durable coordination is required beyond one in-session wave -> use `managed-team`.\n"
                "4. **Fallback**: If delegation is unavailable, unsafe, or not packetized -> record `leader-inline-fallback` and execute on `leader-inline`.\n"
                "5. **Build/Compile Failures**: If commands return non-zero exit codes -> dispatch `cpp-build-resolver` or specialist agent.\n"
                "6. **Testing Tasks**: If paths involve `tests/` or `*_test.*` -> dispatch `tdd-guide` or build specialist.\n"
                "7. **Cross-module Dependency**: If task affects >2 different directories -> dispatch one subagent per module when packet context is ready.\n"
                "\n"
                "For each ready parallel batch:\n"
                "- The invoking runtime acts as the leader: it reads the current planning artifacts, selects the next executable phase and ready batch, and dispatches work instead of performing concrete implementation directly.\n"
                f"- Keep the shared workload-safety checks, but for {agent_name} `sp-implement` prefer `execution_surface: native-subagents` whenever `snapshot.native_subagents` is true.\n"
                f"- Use `spawn_agent` to dispatch disjoint subagents for the current batch, `wait_agent` to join them, and `close_agent` after integrating results.\n"
                "- Prefer subagent execution only when the lane already has a validated `WorkerTaskPacket` and enough context to preserve or improve on leader-inline quality.\n"
                f"- Decision order for {agent_name} `sp-implement` must stay fixed: safe packetized subagents -> `managed-team` only when durable team state is required -> `leader-inline-fallback` with reason.\n"
                "- If subagent dispatch is unavailable or low-confidence for the current batch, use `leader-inline-fallback`, record the fallback reason, and preserve the same join-point discipline locally.\n"
                "- Re-check the strategy after every join point instead of assuming the first choice still applies.\n"
                "- The leader dispatches subagents rather than executing the implementation itself when the batch is ready for subagent work.\n"
                "- Once one safe lane clears the subagent-readiness bar, do **not** ask the user whether it should switch to subagent execution; dispatch the subagent by default and only discuss fallback after dispatch concretely fails.\n"
                "- After each completed batch, the leader re-evaluates milestone state, selects the next executable phase and ready batch in roadmap order, and continues automatically until the milestone is complete or blocked.\n"
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
        if not self._can_augment_generated_file(debug_skill, project_root):
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
                f"- If the current stage is `investigating` and there are two or more bounded evidence-gathering lanes, you **MUST** dispatch subagents through `spawn_agent` before continuing with more sequential evidence collection yourself.\n"
                f"- Use `wait_agent` at the investigation join point, integrate returned results, and call `close_agent` for completed subagents.\n"
                "- Do **not** skip subagents just because the evidence tasks look easy; use `leader-inline-fallback` only when the current investigation does not have safe parallel lanes.\n"
                "\n"
                "**Hard rule:** During `investigating`, the leader must not let subagents mutate the debug file, declare the root cause final, or advance the session state.\n"
            )
            if "## Session Lifecycle" in content:
                content = content.replace("## Session Lifecycle", gate_addendum + "\n## Session Lifecycle", 1)
            else:
                content += gate_addendum

        think_gate_marker = f"## {agent_name} Think Subagent Dispatch"
        if think_gate_marker not in content:
            think_addendum = (
                "\n"
                f"## {agent_name} Think Subagent Dispatch\n\n"
                f"When running `sp-debug` in {agent_name}, the **Gathering** stage may return an `await_input` "
                "containing a `think_subagent_prompt`. This prompt is a self-contained reasoning task for a "
                "fresh subagent.\n"
                "\n"
                "**When you receive a think_subagent_prompt:**\n"
                "- Spawn a subagent with the exact prompt text via `spawn_agent`.\n"
                "- The think subagent does NOT read source code and does NOT run commands — it is a pure reasoning agent.\n"
                "- Use `wait_agent` to wait for the think subagent's result.\n"
                "- The result is hybrid: free-text analysis followed by `---` and a YAML block.\n"
                "- Parse the YAML block after `---` and populate these fields in the debug state:\n"
                "  - `observer_framing` (summary, primary_suspected_loop, suspected_owning_layer, etc.)\n"
                "  - `transition_memo` (first_candidate_to_test, why_first, carry_forward_notes)\n"
                "  - `alternative_cause_candidates` (list of candidate objects)\n"
                "- Set `observer_framing_completed` to `True`.\n"
                "- Then continue the debug session — the next GatheringNode run will skip observer framing "
                "and proceed to gate checks.\n"
                "- Do NOT skip the think subagent. Context isolation is the purpose of this step.\n"
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
            f"When running `sp-debug` in {agent_name}, treat the `investigating` stage as leader-led `subagents-first` evidence collection.\n"
            "- Use `parallel-subagents` on `native-subagents` when there are two or more independent evidence-gathering lanes.\n"
            "- Use `leader-inline-fallback` only after recording why evidence delegation is unavailable, unsafe, or not packetized.\n"
            f"- If there are two or more independent evidence-gathering lanes, dispatch subagents through `spawn_agent` instead of doing manual sequential investigation.\n"
            "- Suitable subagent tasks include running targeted tests or repro commands, collecting logs and exit codes, searching for error text, tracing isolated code paths, and gathering evidence after diagnostic logging has been added.\n"
            "- Read `diagnostic_profile` from the debug session before choosing subagent lanes.\n"
            "- The leader **MUST** update the debug file's `Current Focus` before dispatching subagents and treat subagent work as evidence collection for the current hypothesis.\n"
            "- Subagents must return facts, command results, and observations; they must not update the debug file, declare the root cause final, or transition the session state.\n"
            "- Wait for every subagent's structured handoff before accepting the join point or changing the investigation stage.\n"
            "- Wait for every delegated lane's structured handoff before accepting the join point or changing the investigation stage.\n"
            "- Do not treat an idle subagent as done work; idle without a consumed handoff means the evidence lane is still unresolved.\n"
            "- Do not interrupt or shut down subagent work before the handoff has been written or explicitly reported as `BLOCKED` or `NEEDS_CONTEXT`.\n"
            f"- Use `wait_agent` only after the current investigation fan-out reaches its join point.\n"
            f"- Use `close_agent` after integrating finished subagent results.\n"
            "- Keep fixing, verification, `awaiting_human_verify`, and final session resolution on the leader path.\n"
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
        if not self._can_augment_generated_file(quick_skill, project_root):
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
                "- Define the smallest safe delegated lane or ready batch, and choose the `subagents-first` dispatch shape for that batch.\n"
                "- Dispatch `one-subagent` when one validated `WorkerTaskPacket` or equivalent execution contract preserves quality.\n"
                "- Dispatch `parallel-subagents` when two or more safe subagent lanes would materially improve throughput.\n"
                f"- Use `native-subagents` through `spawn_agent` before considering any fallback path.\n"
                "- If that bar is not met, keep the lane on the leader path until the missing context, constraints, validation target, or handoff expectations are explicit.\n"
                f"- Use `wait_agent` only at the current join point, integrate returned results, and call `close_agent` for completed subagents.\n"
                "- Wait for every subagent's structured handoff before accepting the join point, closing the batch, or declaring completion.\n"
                "- Do not treat an idle subagent as done work; idle without a consumed handoff means the result channel is still unresolved.\n"
                "- Do not interrupt or shut down subagent work before the handoff has been written or explicitly reported as `BLOCKED` or `NEEDS_CONTEXT`.\n"
                "- Use `managed-team` only when durable team state is needed beyond one in-session subagent burst.\n"
                "- Use `leader-inline-fallback` only when subagent dispatch and `sp-teams` are both unavailable or unsafe.\n"
                "- When `leader-inline-fallback` is used, you **MUST** write the concrete fallback reason into `STATUS.md` before executing locally.\n"
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
            self.write_file_and_record(content, quick_skill, project_root, manifest)
            return

        addendum = (
            "\n"
            f"## {agent_name} Quick-Task Subagent Execution\n\n"
            f"When running `sp-quick` in {agent_name}, use `subagents-first` execution after `STATUS.md` exists.\n"
            "- Dispatch `one-subagent` or `parallel-subagents` before broad leader-inline repository analysis.\n"
            "- Use `leader-inline-fallback` only after native subagents and the managed-team path are unavailable or unsafe, and record the fallback reason in `STATUS.md`.\n"
            f"- Use `spawn_agent` for bounded lanes such as focused repository analysis, targeted implementation, regression test updates, or validation command runs.\n"
            "- Once the first lane is chosen, dispatch it before continuing any leader-inline deep-dive analysis of the repository.\n"
            "- If multiple safe subagent lanes exist and they materially improve throughput, dispatch them in parallel.\n"
            f"- Use `wait_agent` only at the documented join point for the current quick-task batch.\n"
            f"- Use `close_agent` after integrating finished subagent results.\n"
            "- Keep `.planning/quick/<id>-<slug>/STATUS.md` as the leader-owned source of truth.\n"
            "- Subagents may return evidence, patches, and verification output, but they must not become the authority for resume state; the leader updates `STATUS.md` before and after each join point.\n"
            f"- Decision order for {agent_name} `sp-quick`: safe packetized subagents -> `managed-team` when durable state is needed -> `leader-inline-fallback` with reason.\n"
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

        self.write_file_and_record(content, quick_skill, project_root, manifest)

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
        self.write_file_and_record(content, implement_teams_skill, project_root, manifest)

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
            "1. keep `FEATURE_DIR/implement-tracker.md` as the execution-state source of truth\n"
            "2. compile and validate a `WorkerTaskPacket` before assigning each team-managed execution task\n"
            "3. for implementation-oriented teams flows, preserve the user-visible fields `execution_model`, `dispatch_shape`, and `execution_surface`\n"
            "4. preserve explicit join point behavior, blocker reporting, retry-pending state, and completion checks\n"
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
            "1. the current batch is recorded in `implement-tracker.md`\n"
            "2. each team-managed task has a validated `WorkerTaskPacket`\n"
            "3. join point expectations and result handoff expectations are explicit\n"
            "4. the team-managed lane cannot be treated as complete from a status flip alone; the leader still needs the promised completion handoff or result evidence\n\n"
            "The only intended difference is the dispatch path:\n\n"
            f"1. `{canonical_command}` may route the current ready batch through subagents first\n"
            f"2. `{teams_command}` forces the concrete team-managed execution through {backend_label} for the same batch and join-point semantics\n"
            f"3. {backend_label} must not weaken the tracker, packet, validation, or completion contract\n"
        )

        if "## Execution Contract" in content:
            content = content.replace("## Execution Contract", addendum + "\n## Execution Contract", 1)
        else:
            content += addendum
        self.write_file_and_record(content, implement_teams_skill, project_root, manifest)
