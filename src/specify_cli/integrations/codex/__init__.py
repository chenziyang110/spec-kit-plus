"""Codex CLI integration — skills-based agent.

Codex uses the ``.codex/skills/sp-<name>/SKILL.md`` layout.
Commands are deprecated; ``--skills`` defaults to ``True``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..base import IntegrationOption, SkillsIntegration
from .multi_agent import CodexMultiAgentAdapter


class CodexIntegration(SkillsIntegration):
    """Integration for OpenAI Codex CLI."""

    key = "codex"
    config = {
        "name": "Codex CLI",
        "folder": ".codex/",
        "commands_subdir": "skills",
        "install_url": "https://github.com/openai/codex",
        "requires_cli": True,
    }
    registrar_config = {
        "dir": ".codex/skills",
        "format": "markdown",
        "args": "$ARGUMENTS",
        "extension": "/SKILL.md",
    }
    context_file = "AGENTS.md"

    @classmethod
    def options(cls) -> list[IntegrationOption]:
        return [
            IntegrationOption(
                "--skills",
                is_flag=True,
                default=True,
                help="Install as agent skills (default for Codex)",
            ),
        ]

    def list_command_templates(self) -> list[Path]:
        """Return the shared skills plus the Codex-only team skill."""
        templates = list(super().list_command_templates())
        commands_dir = self.shared_commands_dir()
        if not commands_dir:
            return templates

        team_template = commands_dir / "team.md"
        if team_template.exists():
            templates.append(team_template)
        return sorted(templates, key=lambda path: path.name)

    def setup(
        self,
        project_root: Path,
        manifest,
        parsed_options: dict[str, Any] | None = None,
        **opts: Any,
    ) -> list[Path]:
        created = super().setup(
            project_root,
            manifest,
            parsed_options=parsed_options,
            **opts,
        )

        skills_dir = self.skills_dest(project_root)
        self._augment_shared_skill(
            created,
            project_root,
            manifest,
            skills_dir / "sp-specify" / "SKILL.md",
            "## Codex Native Multi-Agent Execution",
            (
                "\n"
                "## Codex Native Multi-Agent Execution\n\n"
                "When running `sp-specify` in Codex, prefer native worker delegation whenever the selected strategy is `native-multi-agent`.\n"
                "- Use `spawn_agent` for bounded lanes such as repository and local context analysis, references analysis, and ambiguity/risk analysis.\n"
                "- Use `wait_agent` only at the documented join points before capability decomposition and before writing `spec.md`, `alignment.md`, and `context.md`.\n"
                "- Use `close_agent` after integrating finished worker results.\n"
                "- Keep the shared workflow language integration-neutral in user-visible output; this Codex addendum is the only place that should mention `spawn_agent`.\n"
            ),
        )
        self._augment_shared_skill(
            created,
            project_root,
            manifest,
            skills_dir / "sp-plan" / "SKILL.md",
            "## Codex Native Multi-Agent Execution",
            (
                "\n"
                "## Codex Native Multi-Agent Execution\n\n"
                "When running `sp-plan` in Codex, prefer native worker delegation whenever the selected strategy is `native-multi-agent`.\n"
                "- Use `spawn_agent` for bounded lanes such as research, data model design, contracts drafting, and quickstart or validation scenario generation.\n"
                "- Use `wait_agent` only at the documented join points before the final constitution and risk re-check and before writing the consolidated implementation plan.\n"
                "- Use `close_agent` after integrating finished worker results.\n"
                "- Keep the shared workflow language integration-neutral in user-visible output; this Codex addendum is the only place that should mention `spawn_agent`.\n"
            ),
        )
        self._augment_shared_skill(
            created,
            project_root,
            manifest,
            skills_dir / "sp-tasks" / "SKILL.md",
            "## Codex Native Multi-Agent Execution",
            (
                "\n"
                "## Codex Native Multi-Agent Execution\n\n"
                "When running `sp-tasks` in Codex, prefer native worker delegation whenever the selected strategy is `native-multi-agent`.\n"
                "- Use `spawn_agent` for bounded lanes such as story and phase decomposition, dependency graph analysis, and write-set or parallel-safety analysis.\n"
                "- Use `wait_agent` only at the documented join points before writing `tasks.md` and before emitting canonical parallel batches and join points.\n"
                "- Use `close_agent` after integrating finished worker results.\n"
                "- Keep the shared workflow language integration-neutral in user-visible output; this Codex addendum is the only place that should mention `spawn_agent`.\n"
            ),
        )
        self._augment_implement_skill(
            created,
            project_root,
            manifest,
            skills_dir / "sp-implement" / "SKILL.md",
        )
        self._augment_debug_skill(
            created,
            project_root,
            manifest,
            skills_dir / "sp-debug" / "SKILL.md",
        )
        self._augment_quick_skill(
            created,
            project_root,
            manifest,
            skills_dir / "sp-quick" / "SKILL.md",
        )

        return created

    def _augment_shared_skill(
        self,
        created: list[Path],
        project_root: Path,
        manifest,
        skill_path: Path,
        marker: str,
        addendum: str,
    ) -> None:
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
        manifest,
        implement_skill: Path,
    ) -> None:
        if implement_skill not in created or not implement_skill.is_file():
            return

        content = implement_skill.read_text(encoding="utf-8")

        gate_marker = "## Codex Leader Gate"
        if gate_marker not in content:
            gate_addendum = (
                "\n"
                "## Codex Leader Gate\n\n"
                "When running `sp-implement` in Codex, you are the **leader**, not the concrete implementer.\n"
                "\n"
                "Before any code edits, test edits, build commands, or implementation actions:\n"
                "- Read `tasks.md`, identify the current ready batch, and choose the execution strategy for that batch.\n"
                "- If the selected strategy is `native-multi-agent`, you **MUST** delegate the concrete work through `spawn_agent` worker lanes before considering any fallback path.\n"
                "- Use `wait_agent` only at the join point for the current ready batch, then integrate results and call `close_agent` for completed workers.\n"
                "- If the selected strategy is `sidecar-runtime`, or if native worker delegation proves concretely unavailable for the current batch, you **MUST** call **`specify team auto-dispatch --feature-dir \"<FEATURE_DIR>\"`** before doing any concrete implementation work yourself.\n"
                "- Do **not** fall through from worker delegation or sidecar fallback into local self-execution just because the implementation looks feasible.\n"
                "- `single-agent` still means one delegated worker lane, not leader self-execution.\n"
                "\n"
                "**Hard rule:** The leader must not edit implementation files directly while worker delegation is active or while `sidecar-runtime` is selected.\n"
            )
            if "## Outline" in content:
                content = content.replace("## Outline", gate_addendum + "\n## Outline", 1)
            else:
                content += gate_addendum

        marker = "## Codex Auto-Parallel Execution"
        if marker not in content:
            addendum = (
                "\n"
                "## Codex Auto-Parallel Execution\n\n"
                "When running `sp-implement` in Codex, treat Step 6's unified execution strategy selection as a runtime-aware escalation with a Codex-specific native-worker preference.\n"
                "For each ready parallel batch:\n"
                "- The invoking runtime acts as the leader: it reads the current planning artifacts, selects the next executable phase and ready batch, and dispatches work instead of performing concrete implementation directly.\n"
                "- The shared implement template is the primary source of truth for this leader-only milestone scheduler contract, and Codex-specific guidance must preserve the same semantics.\n"
                "- Keep the shared strategy names and workload-safety checks, but for Codex `sp-implement` prefer `native-multi-agent` whenever `snapshot.native_multi_agent` is true for the current ready batch.\n"
                "- Use `spawn_agent` to delegate disjoint worker lanes for the current batch, `wait_agent` to join them, and `close_agent` after integrating results.\n"
                "- single-agent still means one delegated worker lane, not leader self-execution.\n"
                "- Interpret `single-agent` as solo execution through that delegated single-worker sequential path.\n"
                "- Interpret `native-multi-agent` as the native subagents path.\n"
                "- Interpret `sidecar-runtime` as escalation via **`specify team`** only after native worker delegation is unavailable or unsuitable for the current batch.\n"
                "- Decision order for Codex `sp-implement` must stay fixed: `no-safe-batch` -> `native-preferred` -> `sidecar-fallback` -> `fallback`.\n"
                "- Only fall back to `specify team` after a concrete blocker shows that the current batch cannot proceed through native worker delegation.\n"
                "- Re-check the strategy after every join point instead of assuming the first choice still applies.\n"
                "- The leader delegates execution through these worker paths rather than executing the implementation itself.\n"
                "- Surface join points, retry-pending work, and blocker state truthfully instead of leaving those runtime transitions implicit.\n"
                "- After each completed batch, the leader re-evaluates milestone state, selects the next executable phase and ready batch in roadmap order, and continues automatically until the milestone is complete or blocked.\n"
            )
            content += addendum

        self.write_file_and_record(content, implement_skill, project_root, manifest)

    def _augment_debug_skill(
        self,
        created: list[Path],
        project_root: Path,
        manifest,
        debug_skill: Path,
    ) -> None:
        if debug_skill not in created or not debug_skill.is_file():
            return

        content = debug_skill.read_text(encoding="utf-8")
        gate_marker = "## Codex Leader Gate"
        if gate_marker not in content:
            gate_addendum = (
                "\n"
                "## Codex Leader Gate\n\n"
                "When running `sp-debug` in Codex, you are the **leader**, not a freeform debugger.\n"
                "\n"
                "Before applying fixes or running multiple independent investigation actions yourself:\n"
                "- Read the current debug session state and identify whether the investigation has two or more independent evidence-gathering lanes.\n"
                "- If the current stage is `investigating` and there are two or more bounded evidence-gathering lanes, you **MUST** delegate them through `spawn_agent` before continuing with more sequential evidence collection yourself.\n"
                "- Use `wait_agent` at the investigation join point, integrate the returned facts into `Evidence` or `Eliminated`, and call `close_agent` for completed child agents.\n"
                "- Do **not** skip delegation just because the evidence tasks look easy; use the lighter `single-agent` path only when the current investigation does not have safe parallel lanes.\n"
                "\n"
                "**Hard rule:** During `investigating`, the leader must not let child agents mutate the debug file, declare the root cause final, or advance the session state.\n"
            )
            if "## Session Lifecycle" in content:
                content = content.replace("## Session Lifecycle", gate_addendum + "\n## Session Lifecycle", 1)
            else:
                content += gate_addendum

        marker = "## Codex Native Multi-Agent Investigation"
        if marker in content:
            return

        addendum = (
            "\n"
            "## Codex Native Multi-Agent Investigation\n\n"
            "When running `sp-debug` in Codex, treat the `investigating` stage as a leader-led routing decision between `single-agent` and native delegated evidence collection.\n"
            "- If there are two or more independent evidence-gathering lanes, prefer native delegation through `spawn_agent` over manual sequential investigation.\n"
            "- Suitable child tasks include running targeted tests or repro commands, collecting logs and exit codes, searching for error text, tracing isolated code paths, comparing independent modules or configurations, judging whether existing logs are detailed enough, and gathering evidence after diagnostic logging has been added.\n"
            "- Read `diagnostic_profile` from the debug session before choosing child lanes. Treat it as the default evidence-routing hint unless fresh evidence clearly invalidates it.\n"
            "- If `suggested_evidence_lanes` is populated, use it as the default fan-out plan for child-agent evidence collection and join-point planning.\n"
            "- Prefer child tasks that gather decisive control-plane signals such as ownership sets, queue contents, resource counters, running collections, and decision-boundary traces.\n"
            "- Bias delegated evidence collection by profile when possible:\n"
            "  - `scheduler-admission`: gather queue contents, running/admitted sets, slot counters, and promotion handoff traces in parallel.\n"
            "  - `cache-snapshot`: gather authoritative control state, cached or snapshot state, invalidation timing, and refresh-path traces in parallel.\n"
            "  - `ui-projection`: gather source-of-truth state, publish-boundary state, transformed view-model state, and rendered or polled output in parallel.\n"
            "  - `general`: gather the owning decision-layer state, the observable projection state, and the boundary trace between them.\n"
            "- The leader **MUST** update the debug file's `Current Focus` before delegating and treat child work as evidence collection for the current hypothesis, not as parallel hypothesis formation.\n"
            "- Child agents must return facts, command results, and observations; they must not update the debug file, declare the root cause final, transition the session state, or archive the session.\n"
            "- Use `wait_agent` only after the current investigation fan-out reaches its join point, then integrate the returned evidence into `Evidence` or `Eliminated` yourself.\n"
            "- Use `close_agent` after integrating finished child results.\n"
            "- Keep fixing, verification, `awaiting_human_verify`, and final session resolution on the leader path unless a single explicitly scoped repair task is delegated after the root cause is already established.\n"
        )

        self.write_file_and_record(content + addendum, debug_skill, project_root, manifest)

    def _augment_quick_skill(
        self,
        created: list[Path],
        project_root: Path,
        manifest,
        quick_skill: Path,
    ) -> None:
        if quick_skill not in created or not quick_skill.is_file():
            return

        content = quick_skill.read_text(encoding="utf-8")

        gate_marker = "## Codex Leader Gate"
        if gate_marker not in content:
            gate_addendum = (
                "\n"
                "## Codex Leader Gate\n\n"
                "When running `sp-quick` in Codex, you are the **leader**, not the concrete implementer.\n"
                "\n"
                "Before code edits, test edits, or implementation commands:\n"
                "- Read `STATUS.md` for the active quick-task workspace, or create `.planning/quick/<slug>/STATUS.md` if this quick task is new.\n"
                "- Define the smallest safe execution lane or ready batch, and choose the execution strategy for that batch.\n"
                "- If the selected strategy is `native-multi-agent`, you **MUST** delegate the concrete work through `spawn_agent` worker lanes before considering any fallback path.\n"
                "- Use `wait_agent` only at the current join point, integrate the returned results, and call `close_agent` for completed workers.\n"
                "- If the selected strategy is `sidecar-runtime`, or if native worker delegation proves concretely unavailable for the current batch, you **MUST** call **`specify team auto-dispatch`** for the quick-task workload before doing concrete implementation work yourself.\n"
                "- Do **not** fall through into leader self-execution just because the task looks small; `single-agent` still means one delegated worker lane.\n"
                "\n"
                "**Hard rule:** The leader must keep scope control, strategy selection, join-point handling, validation, summary ownership, and `STATUS.md` accuracy while delegated execution is active.\n"
            )
            if "## Process" in content:
                content = content.replace("## Process", gate_addendum + "\n## Process", 1)
            else:
                content += gate_addendum

        marker = "## Codex Native Multi-Agent Execution"
        if marker in content:
            self.write_file_and_record(content, quick_skill, project_root, manifest)
            return

        addendum = (
            "\n"
            "## Codex Native Multi-Agent Execution\n\n"
            "When running `sp-quick` in Codex, prefer native worker delegation whenever the selected quick-task strategy is `native-multi-agent`.\n"
            "- Use `spawn_agent` for bounded lanes such as focused repository analysis, targeted implementation, regression test updates, validation command runs, or summary artifact drafting when those lanes do not share a write surface.\n"
            "- Use `wait_agent` only at the documented join point for the current quick-task batch.\n"
            "- Use `close_agent` after integrating finished worker results.\n"
            "- Keep `.planning/quick/<slug>/STATUS.md` as the leader-owned source of truth with current focus, execution strategy, active lane or batch, join point, next action, and blockers.\n"
            "- Child agents may return evidence, patches, and verification output, but they must not become the authority for resume state; the leader updates `STATUS.md` before and after each join point.\n"
            "- Keep the decision order fixed: `no-safe-batch` -> `native-preferred` -> `sidecar-fallback` -> `fallback`.\n"
            "- Interpret `single-agent` as one delegated worker lane, not leader self-execution.\n"
            "- In plain terms: single-agent still means one delegated worker lane.\n"
            "- Interpret `native-multi-agent` as the native subagents path.\n"
            "- Interpret `sidecar-runtime` as escalation via **`specify team`** only after native worker delegation is unavailable or unsuitable for the current quick-task batch.\n"
            "- Re-check strategy after every join point and continue automatically until the quick task is complete or blocked.\n"
            "- Keep validation and final quick-task summary on the leader path even when execution fan-out is delegated.\n"
            "- When the quick task reaches a terminal state, make resume semantics obvious in `STATUS.md` and point to `SUMMARY.md`; archive under `.planning/quick/resolved/` when the local convention expects resolved quick-task workspaces to move out of the active queue.\n"
        )

        self.write_file_and_record(content + addendum, quick_skill, project_root, manifest)


__all__ = ["CodexIntegration", "CodexMultiAgentAdapter"]
