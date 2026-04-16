"""Cursor IDE integration."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..base import MarkdownIntegration


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

        gate_marker = "## Cursor Leader Gate"
        if gate_marker not in content:
            gate_addendum = (
                "\n"
                "## Cursor Leader Gate\n\n"
                "When running `sp-quick` in Cursor, you are the **leader**, not the concrete implementer.\n"
                "\n"
                "Before code edits, test edits, or implementation commands:\n"
                "- Read `STATUS.md` for the active quick-task workspace, or create `.planning/quick/<slug>/STATUS.md` if this quick task is new.\n"
                "- Define the smallest safe execution lane or ready batch, and choose the execution strategy for that batch.\n"
                "- `single-agent` still means one delegated worker lane. Do **not** reinterpret it as leader self-execution.\n"
                "- If Cursor's native delegated worker path is available for the current batch, you **MUST** use it before considering any leader-local fallback.\n"
                "- If a delegated lane is active, use the current join point to integrate results back into `STATUS.md` before selecting the next action.\n"
                "- If native delegated execution is concretely unavailable for the current batch, escalate to the coordinated runtime surface before doing concrete implementation work yourself.\n"
                "- Leader-local execution is allowed only when native delegated execution is unavailable for the current batch and the coordinated runtime path is also unavailable or unsuitable.\n"
                "- When leader-local fallback is used, you **MUST** write the concrete fallback reason into `STATUS.md` before executing locally.\n"
                "\n"
                "**Hard rule:** The leader must keep scope control, strategy selection, join-point handling, validation, summary ownership, and `STATUS.md` accuracy while delegated execution is active. Local execution is the last fallback, not the default reading of `single-agent`.\n"
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
            "When running `sp-quick` in Cursor, prefer delegated worker execution whenever the selected quick-task strategy is `single-agent` or `native-multi-agent`.\n"
            "- Treat `single-agent` as one delegated worker lane by default. The leader should coordinate that lane rather than execute the work directly.\n"
            "- Use Cursor's native delegated worker path for bounded lanes such as focused repository analysis, targeted implementation, regression test updates, validation command runs, or summary artifact drafting when those lanes do not share a write surface.\n"
            "- Keep `.planning/quick/<slug>/STATUS.md` as the leader-owned source of truth with current focus, execution strategy, active lane or batch, join point, next action, and blockers.\n"
            "- Child or delegated worker paths may return evidence, patches, and verification output, but they must not become the authority for resume state; the leader updates `STATUS.md` before and after each join point.\n"
            "- Interpret `native-multi-agent` as Cursor's delegated multi-lane path when available.\n"
            "- Interpret `sidecar-runtime` as escalation to the coordinated runtime surface only after native delegated execution is unavailable or unsuitable for the current quick-task batch.\n"
            "- Use leader-local execution only after both worker paths are concretely unavailable for the current batch, and record that fallback explicitly in `STATUS.md`.\n"
            "- Re-check strategy after every join point and continue automatically until the quick task is complete or blocked.\n"
            "- Keep validation and final quick-task summary on the leader path even when execution fan-out is delegated.\n"
        )

        self.write_file_and_record(content + addendum, quick_command, project_root, manifest)
