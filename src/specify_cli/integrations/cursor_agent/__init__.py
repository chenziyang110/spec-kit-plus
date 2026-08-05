"""Cursor IDE integration."""

from __future__ import annotations

from pathlib import Path

from ..base import IntegrationOption, SkillsIntegration
from ..manifest import IntegrationManifest
from ...orchestration import CapabilitySnapshot, describe_delegation_surface
from .multi_agent import CursorMultiAgentAdapter


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
    CLOSEOUT_ADVISORY_HEADING = "## Cursor Project Cognition Closeout Advisory"

    @classmethod
    def options(cls) -> list[IntegrationOption]:
        return [
            IntegrationOption(
                "--skills",
                is_flag=True,
                default=True,
                help="Install as agent skills (default for Cursor)",
            ),
        ]

    @staticmethod
    def _append_runtime_handbook_compatibility(
        *,
        content: str,
        command_name: str,
    ) -> str:
        _ = command_name
        if CursorAgentIntegration._has_exact_heading(
            content,
            CursorAgentIntegration.CLOSEOUT_ADVISORY_HEADING,
        ):
            return content
        addendum = CursorAgentIntegration._cursor_project_cognition_advisory_addendum()
        if "## Orchestration Model" in content:
            return content.replace(
                "## Orchestration Model", addendum + "\n## Orchestration Model", 1
            )
        if "## Cursor Leader Gate" in content:
            return content.replace(
                "## Cursor Leader Gate", addendum + "\n## Cursor Leader Gate", 1
            )
        return content + addendum

    @staticmethod
    def _cursor_project_cognition_advisory_addendum() -> str:
        return (
            "\n"
            f"{CursorAgentIntegration.CLOSEOUT_ADVISORY_HEADING}\n\n"
            "**Advisory First Pass**: Before repository analysis or implementation, query project cognition when available and use it to choose likely live reads.\n"
            "- Query the graph-native project cognition source only through `specify-runtime cognition status|compass|query`; never inspect its storage directory.\n"
            "- If the runtime is missing, stale, blocked, or too incomplete for the requested work, continue with live repository inspection instead of stopping for map maintenance.\n"
            "- If `baseline_kind=greenfield_empty`, do not recommend map-scan -> map-build solely because the graph has no paths; continue with workflow artifacts and live requirements.\n"
            "- Use map-update for ordinary existing-baseline gaps. Use map-scan -> map-build only for brownfield first/missing/unusable baseline, schema failure, schema v1 or old broad-schema rebuild-required readiness, zero active-generation path_index rows outside greenfield_empty, missing or invalid alias_index, explicit_rebuild_requested, or baseline_identity_invalid.\n"
            "- Entry advisory is not closeout ownership: stale or weak cognition at entry may remain advisory, but workflow-owned mutation closeout must run inline project cognition update for changes this workflow made.\n"
            "- Follow the rendered planner-first closeout contract for the active mutation skill: use its registry-owned literal `sp-*` workflow ID, pass explicit workflow-owned paths, fill only planner-returned agent fields, and execute structured `update_argv`. Never construct a direct delta append or update command.\n"
            "- `sp-map-update` is for manual/external maintenance and follow-up repair, not routine cleanup for changes this workflow just made.\n"
            "- Do not treat map output as evidence by itself; verify technical claims from live code, tests, scripts, configuration, or authoritative docs.\n"
        )

    def _cursor_capability_snapshot(self) -> CapabilitySnapshot:
        return CursorMultiAgentAdapter().detect_capabilities()

    def _runtime_capability_snapshot(self) -> CapabilitySnapshot:
        return self._cursor_capability_snapshot()

    def augment_generated_skills(
        self,
        created: list[Path],
        project_root: Path,
        manifest: IntegrationManifest,
        skills_dir: Path,
    ) -> None:
        runtime_skills = {
            "implement": skills_dir / "sp-implement" / "SKILL.md",
            "review": skills_dir / "sp-review" / "SKILL.md",
            "debug": skills_dir / "sp-debug" / "SKILL.md",
            "quick": skills_dir / "sp-quick" / "SKILL.md",
        }
        for command_name, path in runtime_skills.items():
            self._append_runtime_handbook_compatibility_to_file(
                project_root=project_root,
                manifest=manifest,
                path=path,
                command_name=command_name,
            )

        self._augment_implement_skill(
            created,
            project_root,
            manifest,
            runtime_skills["implement"],
            snapshot=self._cursor_capability_snapshot(),
        )
        self._augment_quick_skill(
            created,
            project_root,
            manifest,
            runtime_skills["quick"],
        )

    def post_init_bootstrap(
        self,
        project_root: Path,
        manifest: IntegrationManifest,
    ) -> list[Path]:
        updated_files: list[Path] = []
        skills_dir = self.skills_dest(project_root)
        for stem in ("implement", "review", "debug", "quick"):
            path = skills_dir / f"sp-{stem}" / "SKILL.md"
            updated = self._append_runtime_handbook_compatibility_to_file(
                project_root=project_root,
                manifest=manifest,
                path=path,
                command_name=stem,
            )
            if updated is None:
                continue
            updated_files.append(updated)
        return updated_files

    def _append_project_cognition_gate_to_file(
        self,
        *,
        project_root: Path,
        manifest: IntegrationManifest,
        path: Path,
    ) -> Path | None:
        if not path.exists():
            return None

        content = path.read_text(encoding="utf-8")
        if self._has_exact_heading(content, self.CLOSEOUT_ADVISORY_HEADING):
            return None

        addendum = self._cursor_project_cognition_advisory_addendum()

        if "## Orchestration Model" in content:
            updated = content.replace(
                "## Orchestration Model", addendum + "\n## Orchestration Model", 1
            )
        elif "## Cursor Leader Gate" in content:
            updated = content.replace(
                "## Cursor Leader Gate", addendum + "\n## Cursor Leader Gate", 1
            )
        else:
            updated = content + addendum

        self._write_augmented_skill(
            updated,
            path,
            project_root,
            manifest,
        )
        return path

    @staticmethod
    def _has_exact_heading(content: str, heading: str) -> bool:
        return any(line.strip() == heading for line in content.splitlines())

    def _append_runtime_handbook_compatibility_to_file(
        self,
        *,
        project_root: Path,
        manifest: IntegrationManifest,
        path: Path,
        command_name: str,
    ) -> Path | None:
        if not path.exists():
            return None
        content = path.read_text(encoding="utf-8")
        updated = self._append_runtime_handbook_compatibility(
            content=content,
            command_name=command_name,
        )
        if updated == content:
            return None
        self._write_augmented_skill(
            updated,
            path,
            project_root,
            manifest,
        )
        return path

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
        cursor_snapshot = self._cursor_capability_snapshot()
        descriptor = describe_delegation_surface(
            command_name="quick",
            snapshot=cursor_snapshot,
        )

        gate_marker = "## Cursor Leader Gate"
        if gate_marker not in content:
            gate_addendum = (
                "\n"
                "## Cursor Leader Gate\n\n"
                "When running `sp-quick` in Cursor, you are the **leader**, not the concrete implementer.\n"
                "\n"
                "Before code edits, test edits, or implementation commands:\n"
                "- Query `.specify/memory/constitution.md` first through `specify-runtime artifact show` if it exists. This gate comes before `STATUS.md`, clarification, lane selection, delegation, or any repository analysis.\n"
                "- Create a new quick-task `STATUS.md` only through `specify-runtime artifact scaffold --kind quick-status`, or resume it through targeted `artifact show` calls.\n"
                "- If `understanding_confirmed` is not `true`, stage the runtime Decision Checkpoint with `specify-runtime quick checkpoint-stage`, show `--view decision` and `--view delivery`, and wait for user confirmation (or inherit a discussion digest with no semantic delta) before implementation work.\n"
                "- The user-facing surface is the runtime Decision Checkpoint plus Delivery Map/Pulse, not a freeform two-column approval table. Confirm only user-owned goal, visible result, scope, stable Q1/Q2 deliverables, product-level dependencies, per-item acceptance, risks, and reconfirmation trigger. Delivery Map waves, subagents, file splits, and test order stay agent-owned and never enter `confirmation_digest`. For applicable UI work, include `ui_confirmation` and ask once for both decisions.\n"
                "- Do not proceed to code edits, broad repository analysis, delegation, or validation commands until `understanding_confirmed: true` has been set by `quick checkpoint-confirm` / inherited stage (or an equivalent leased frontmatter patch).\n"
                "- Compile and gate Q items with `quick packet-compile --item Qn`, `quick item-start --item Qn`, and `quick item-accept --item Qn --evidence ...`. Runtime rejects dependent starts before prerequisites are accepted.\n"
                "- Do **not** perform broad repository analysis, implementation design, or local deep-dive debugging before targeted `specify-runtime artifact show` reports CLI-owned `STATUS.md` has `understanding_confirmed: true` and the first subagent lane is selected.\n"
                "- After understanding is confirmed, define the smallest safe delegated lane or ready batch.\n"
                "- Dispatch `one-subagent` or `parallel-subagents` only after the Decision Checkpoint is confirmed or inherited.\n"
                "- Use Cursor's native subagent path when available.\n"
                "- If two or more safe subagent lanes would materially improve throughput, launch them in parallel instead of serializing them without a concrete coordination reason.\n"
                "- After understanding is confirmed and the first lane is defined, the next concrete action must be dispatch, not additional leader-inline repo exploration.\n"
                "- If a subagent lane is active, use the current join point to integrate results back into `STATUS.md` before selecting the next action.\n"
                "- Use `leader-inline-fallback` only when the selected native lane cannot proceed and local execution is independently safe; do not require or invoke `managed-team`/`sp-teams` unless durable execution was explicitly selected. Patch the fallback reason into `STATUS.md` through a fresh `specify-runtime artifact patch` lease.\n"
                "\n"
                "**Hard rule:** The leader must keep scope control, dispatch-shape selection, join-point handling, validation, summary ownership, and `STATUS.md` accuracy while subagent execution is active. Local execution is the last fallback.\n"
            )
            if "## Process" in content:
                content = content.replace(
                    "## Process", gate_addendum + "\n## Process", 1
                )
            else:
                content += gate_addendum

        marker = "## Cursor Subagent Execution"
        if marker in content:
            self._write_augmented_skill(
                content,
                quick_skill,
                project_root,
                manifest,
            )
            return

        addendum = (
            "\n"
            "## Cursor Subagent Execution\n\n"
            "When running `sp-quick` in Cursor, start execution routing only after targeted `specify-runtime artifact show` reports that CLI-owned `STATUS.md` has `understanding_confirmed: true`.\n"
            "- Decision Checkpoint: before dispatch, stage/show the runtime Decision Checkpoint and Delivery Map (`quick checkpoint-stage` / `checkpoint-show`). Confirm only user-owned Q1/Q2 deliverables, dependencies, and acceptance; never ask users to approve subagent/batch/file choreography. Prefer `packet-compile` + `item-start`/`item-accept` for DAG-gated execution.\n"
            "- After understanding is confirmed, define the smallest safe delegated lane or ready batch.\n"
            "- Dispatch `one-subagent` or `parallel-subagents` only after the Decision Checkpoint is confirmed or inherited.\n"
            "- Do **not** perform broad repository analysis, implementation design, or local deep-dive debugging before targeted `specify-runtime artifact show` reports CLI-owned `STATUS.md` has `understanding_confirmed: true` and the first subagent lane is selected.\n"
            f"- Use Cursor's native subagent path for bounded lanes when available. {descriptor.native_dispatch_hint}\n"
            "- After understanding is confirmed and the first lane is defined, the next concrete action must be dispatch, not additional leader-inline repo exploration.\n"
            "- Once the first lane is chosen after confirmation, dispatch it before continuing any leader-inline deep-dive analysis of the repository.\n"
            "- If multiple safe subagent lanes exist and they materially improve throughput, dispatch them in parallel instead of defaulting to serial execution.\n"
            "- Keep `.planning/quick/<id>-<slug>/STATUS.md` as the leader-owned source of truth with current focus, `dispatch_shape`, active lane or batch, join point, next action, and blockers.\n"
            "- Subagents may return evidence, patches, and verification output, but they must not become the authority for resume state; the leader patches `STATUS.md` through fresh `specify-runtime artifact patch` leases before and after each join point.\n"
            f"- Join subagent lanes through the integration-native join point: {descriptor.native_join_hint}\n"
            "- Use `leader-inline-fallback` only when the selected native lane cannot proceed and local execution is independently safe; do not require or invoke `managed-team`/`sp-teams` unless durable execution was explicitly selected. Patch the fallback reason into `STATUS.md` through a fresh `specify-runtime artifact patch` lease.\n"
            f"- Result contract: {descriptor.result_contract_hint}\n"
            f"- Inline result submission: {descriptor.result_submit_hint}\n"
            f"- Runtime-owned compatibility path: `{descriptor.result_handoff_hint}`. The runtime derives and writes it; never create a result file or use `--result-file`.\n"
            "- Re-check strategy after every join point and continue automatically until the quick task is complete or blocked.\n"
            "- Keep validation and final quick-task summary on the leader path even when execution fan-out is delegated.\n"
        )
        content = content + addendum
        content = self._append_delegation_surface_contract(
            content=content,
            agent_name="Cursor",
            command_name="quick",
            snapshot=cursor_snapshot,
            heading="Subagent Dispatch Contract",
        )
        if "## Cursor Worker Status Deltas" not in content:
            content += (
                "\n"
                "## Cursor Worker Status Deltas\n\n"
                "- Normalize worker-reported statuses like `DONE`, `DONE_WITH_CONCERNS`, `BLOCKED`, and `NEEDS_CONTEXT` into the shared `WorkerTaskResult` contract before the leader accepts the handoff.\n"
                "- Keep `reported_status` when normalization occurs so Cursor lane output can be reconciled with canonical orchestration state.\n"
                "- Treat `DONE_WITH_CONCERNS` as completed work plus follow-up concerns, not as silent success.\n"
                "- Treat `NEEDS_CONTEXT` as a blocked handoff that must carry the missing context or failed assumption explicitly.\n"
            )

        self._write_augmented_skill(
            content,
            quick_skill,
            project_root,
            manifest,
        )


__all__ = ["CursorAgentIntegration", "CursorMultiAgentAdapter"]
