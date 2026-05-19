"""Cursor IDE integration."""

from __future__ import annotations

from pathlib import Path

from ..base import IntegrationOption, SkillsIntegration
from ..manifest import IntegrationManifest
from ...orchestration import CapabilitySnapshot, describe_delegation_surface


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
        return content

    def _cursor_capability_snapshot(self) -> CapabilitySnapshot:
        return CapabilitySnapshot(
            integration_key=self.key,
            native_subagents=True,
            managed_team_supported=True,
            structured_results=True,
            durable_coordination=False,
            native_worker_surface="native-cli",
            delegation_confidence="medium",
            model_family="cursor",
            runtime_probe_succeeded=True,
        )

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
        for stem in ("implement", "debug", "quick"):
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
        if "## Cursor Project Cognition Gate" in content:
            return None

        addendum = (
            "\n"
            "## Cursor Project Cognition Gate\n\n"
            "**Crucial First Step**: Before repository analysis or implementation, query the current project cognition runtime and treat the result as advisory for whether `sp-map-scan` or `sp-map-build` may be helpful.\n"
            "- Use `.specify/project-cognition/` as the graph-native project cognition source when present.\n"
            "- If the runtime is missing, stale, or too incomplete for the requested work, recommend `sp-map-scan` before relying on local assumptions.\n"
            "- If scan evidence exists but the graph artifacts are missing or stale, recommend `sp-map-build` before accepting the map as current.\n"
            "- Continue with live repository evidence; treat the project cognition state as guidance unless a concrete blocker is recorded.\n"
        )

        if "## Orchestration Model" in content:
            updated = content.replace("## Orchestration Model", addendum + "\n## Orchestration Model", 1)
        elif "## Cursor Leader Gate" in content:
            updated = content.replace("## Cursor Leader Gate", addendum + "\n## Cursor Leader Gate", 1)
        else:
            updated = content + addendum

        self.write_file_and_record(updated, path, project_root, manifest)
        return path

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
        path.write_text(updated, encoding="utf-8")
        self.record_file_in_manifest(path, project_root, manifest)
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
                "- Read `.specify/memory/constitution.md` first if it exists. This gate comes before `STATUS.md`, clarification, lane selection, delegation, or any repository analysis.\n"
                "- Read `STATUS.md` for the active quick-task workspace, or create `.planning/quick/<slug>/STATUS.md` if this quick task is new.\n"
                "- Do **not** perform broad repository analysis, implementation design, or local deep-dive debugging before `STATUS.md` exists and the first subagent lane is selected.\n"
                "- Define the smallest safe delegated lane or ready batch.\n"
                "- Dispatch `one-subagent` or `parallel-subagents` before broad leader-inline repository analysis.\n"
                "- Use Cursor's native subagent path when available.\n"
                "- If two or more safe subagent lanes would materially improve throughput, launch them in parallel instead of serializing them without a concrete coordination reason.\n"
                "- After the first lane is defined, the next concrete action must be dispatch, not additional leader-inline repo exploration.\n"
                "- If a subagent lane is active, use the current join point to integrate results back into `STATUS.md` before selecting the next action.\n"
                "- Use `leader-inline-fallback` only after native subagents and the managed-team path are unavailable or unsafe, and record the fallback reason in `STATUS.md`.\n"
                "\n"
                "**Hard rule:** The leader must keep scope control, dispatch-shape selection, join-point handling, validation, summary ownership, and `STATUS.md` accuracy while subagent execution is active. Local execution is the last fallback.\n"
            )
            if "## Process" in content:
                content = content.replace("## Process", gate_addendum + "\n## Process", 1)
            else:
                content += gate_addendum

        marker = "## Cursor Subagent Execution"
        if marker in content:
            self.write_file_and_record(content, quick_skill, project_root, manifest)
            return

        addendum = (
            "\n"
            "## Cursor Subagent Execution\n\n"
            "When running `sp-quick` in Cursor, use subagents-first execution after `STATUS.md` exists.\n"
            "- Define the smallest safe delegated lane or ready batch.\n"
            "- Dispatch `one-subagent` or `parallel-subagents` before broad leader-inline repository analysis.\n"
            "- Do **not** perform broad repository analysis, implementation design, or local deep-dive debugging before `STATUS.md` exists and the first subagent lane is selected.\n"
            f"- Use Cursor's native subagent path for bounded lanes when available. {descriptor.native_dispatch_hint}\n"
            "- After the first lane is defined, the next concrete action must be dispatch, not additional leader-inline repo exploration.\n"
            "- Once the first lane is chosen, dispatch it before continuing any leader-inline deep-dive analysis of the repository.\n"
            "- If multiple safe subagent lanes exist and they materially improve throughput, dispatch them in parallel instead of defaulting to serial execution.\n"
            "- Keep `.planning/quick/<slug>/STATUS.md` as the leader-owned source of truth with current focus, `dispatch_shape`, active lane or batch, join point, next action, and blockers.\n"
            "- Subagents may return evidence, patches, and verification output, but they must not become the authority for resume state; the leader updates `STATUS.md` before and after each join point.\n"
            f"- Join subagent lanes through the integration-native join point: {descriptor.native_join_hint}\n"
            "- Use `leader-inline-fallback` only after native subagents and the managed-team path are unavailable or unsafe, and record the fallback reason in `STATUS.md`.\n"
            f"- Result contract: {descriptor.result_contract_hint}\n"
            f"- Result file handoff path: {descriptor.result_handoff_hint}\n"
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

        self.write_file_and_record(content, quick_skill, project_root, manifest)
