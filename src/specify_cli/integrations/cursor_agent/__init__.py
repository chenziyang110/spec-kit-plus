"""Cursor IDE integration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..base import MarkdownIntegration
from ...orchestration import CapabilitySnapshot, describe_delegation_surface


class CursorAgentIntegration(MarkdownIntegration):
    key = "cursor-agent"
    config = {
        "name": "Cursor",
        "folder": ".cursor/",
        "commands_subdir": "commands",
        "install_url": None,
        "requires_cli": False,
    }
    registrar_config = {
        "dir": ".cursor/commands",
        "format": "markdown",
        "args": "$ARGUMENTS",
        "extension": ".md",
    }
    context_file = ".cursor/rules/specify-rules.mdc"

    def _cursor_capability_snapshot(self) -> CapabilitySnapshot:
        return CapabilitySnapshot(
            integration_key=self.key,
            native_multi_agent=True,
            sidecar_runtime_supported=True,
            structured_results=True,
            durable_coordination=False,
            native_worker_surface="native-cli",
            delegation_confidence="medium",
            model_family="cursor",
            runtime_probe_succeeded=True,
        )

    def _runtime_capability_snapshot(self) -> CapabilitySnapshot:
        return self._cursor_capability_snapshot()

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

        commands_dir = self.commands_dest(project_root)
        self._augment_quick_command(
            created,
            project_root,
            manifest,
            commands_dir / "sp.quick.md",
        )

        return created

    def _augment_quick_command(
        self,
        created: list[Path],
        project_root: Path,
        manifest,
        quick_command: Path,
    ) -> None:
        if quick_command not in created or not quick_command.is_file():
            return

        content = quick_command.read_text(encoding="utf-8")
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
                "- Read `.specify/memory/constitution.md` first if it exists. This gate comes before `STATUS.md`, clarification, lane selection, delegation, or any repository analysis.\n"
                "- Read `STATUS.md` for the active quick-task workspace, or create `.planning/quick/<slug>/STATUS.md` if this quick task is new.\n"
                "- Do **not** perform broad repository analysis, implementation design, or local deep-dive debugging before `STATUS.md` exists and the first worker lane is selected.\n"
                "- Define the smallest safe execution lane or ready batch, and choose the execution strategy for that batch.\n"
                "- `single-lane` still means one delegated worker lane. Do **not** reinterpret it as leader self-execution.\n"
                "- If Cursor's native delegated worker path is available for the current batch, you **MUST** use it before considering any leader-local fallback.\n"
                "- If two or more safe delegated lanes would materially improve throughput, you **MUST** prefer launching them in parallel instead of serializing them without a concrete coordination reason.\n"
                "- After the first lane is defined, the next concrete action must be dispatch, not additional leader-local repo exploration.\n"
                "- If a delegated lane is active, use the current join point to integrate results back into `STATUS.md` before selecting the next action.\n"
                "- If native delegated execution is concretely unavailable for the current batch, escalate to the coordinated runtime surface before doing concrete implementation work yourself.\n"
                "- Leader-local execution is allowed only when native delegated execution is unavailable for the current batch and the coordinated runtime path is also unavailable or unsuitable.\n"
                "- When leader-local fallback is used, you **MUST** write the concrete fallback reason into `STATUS.md` before executing locally.\n"
                "\n"
                "**Hard rule:** The leader must keep scope control, strategy selection, join-point handling, validation, summary ownership, and `STATUS.md` accuracy while delegated execution is active. Local execution is the last fallback, not the default reading of `single-lane`.\n"
            )
            if "## Process" in content:
                content = content.replace("## Process", gate_addendum + "\n## Process", 1)
            else:
                content += gate_addendum

        marker = "## Cursor Delegated Execution"
        if marker in content:
            self.write_file_and_record(content, quick_command, project_root, manifest)
            return

        addendum = (
            "\n"
            "## Cursor Delegated Execution\n\n"
            "When running `sp-quick` in Cursor, prefer delegated worker execution whenever the selected quick-task strategy is `single-lane` or `native-multi-agent`.\n"
            "- Treat `single-lane` as one delegated worker lane by default. The leader should coordinate that lane rather than execute the work directly.\n"
            "- Do **not** perform broad repository analysis, implementation design, or local deep-dive debugging before `STATUS.md` exists and the first worker lane is selected.\n"
            "- If Cursor's native delegated worker path is available for the current batch, you **MUST** use it before considering any leader-local fallback.\n"
            f"- Use Cursor's native delegated worker path for bounded lanes when available. {descriptor.native_dispatch_hint}\n"
            "- After the first lane is defined, the next concrete action must be dispatch, not additional leader-local repo exploration.\n"
            "- Once the first lane is chosen, dispatch it before continuing any leader-local deep-dive analysis of the repository.\n"
            "- If multiple safe worker lanes exist and they materially improve throughput, dispatch them in parallel instead of defaulting to serial delegation.\n"
            "- Keep `.planning/quick/<slug>/STATUS.md` as the leader-owned source of truth with current focus, execution strategy, active lane or batch, join point, next action, and blockers.\n"
            "- Child or delegated worker paths may return evidence, patches, and verification output, but they must not become the authority for resume state; the leader updates `STATUS.md` before and after each join point.\n"
            f"- Join delegated lanes through the integration-native join point: {descriptor.native_join_hint}\n"
            "- Interpret `native-multi-agent` as Cursor's delegated multi-lane path when available.\n"
            "- Interpret `sidecar-runtime` as escalation to the coordinated runtime surface only after native delegated execution is unavailable or unsuitable for the current quick-task batch.\n"
            "- If native delegated execution is concretely unavailable for the current batch, escalate to the coordinated runtime surface before doing concrete implementation work yourself.\n"
            f"- Result contract: {descriptor.result_contract_hint}\n"
            f"- Result file handoff path: {descriptor.result_handoff_hint}\n"
            "- Use leader-local execution only after both worker paths are concretely unavailable for the current batch, and record that fallback explicitly in `STATUS.md`.\n"
            "- Re-check strategy after every join point and continue automatically until the quick task is complete or blocked.\n"
            "- Keep validation and final quick-task summary on the leader path even when execution fan-out is delegated.\n"
        )
        content = content + addendum
        content = self._append_delegation_surface_contract(
            content=content,
            agent_name="Cursor",
            command_name="quick",
            snapshot=cursor_snapshot,
            heading="Delegation Surface Contract",
        )
        if "## Cursor Worker Result Contract" not in content:
            content += (
                "\n"
                "## Cursor Worker Result Contract\n\n"
                f"- Preferred result contract: {descriptor.result_contract_hint}\n"
                f"- Result file handoff path: {descriptor.result_handoff_hint}\n"
                "- Normalize worker-reported statuses like `DONE`, `DONE_WITH_CONCERNS`, `BLOCKED`, and `NEEDS_CONTEXT` into the shared `WorkerTaskResult` contract before the leader accepts the handoff.\n"
                "- Keep `reported_status` when normalization occurs so Cursor lane output can be reconciled with canonical orchestration state.\n"
                "- Treat `DONE_WITH_CONCERNS` as completed work plus follow-up concerns, not as silent success.\n"
                "- Treat `NEEDS_CONTEXT` as a blocked handoff that must carry the missing context or failed assumption explicitly.\n"
            )

        self.write_file_and_record(content, quick_command, project_root, manifest)
