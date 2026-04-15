from __future__ import annotations

from .schema import DebugGraphState, SuggestedDispatchTask, SuggestedSpawnTask


def build_codex_dispatch_plan(state: DebugGraphState) -> list[SuggestedDispatchTask]:
    profile = state.diagnostic_profile or "general"
    root_cause = (
        state.resolution.root_cause.display_text()
        if state.resolution.root_cause
        else "Current hypothesis"
    )
    current_focus = state.current_focus.hypothesis or state.current_focus.next_action or "Collect bounded evidence."

    tasks: list[SuggestedDispatchTask] = []
    for lane in state.suggested_evidence_lanes:
        evidence_lines = ", ".join(lane.evidence_to_collect) if lane.evidence_to_collect else "bounded evidence for this lane"
        prompt = (
            f"Investigate lane `{lane.name}` for debug session `{state.slug}`.\n"
            f"- Diagnostic profile: {profile}\n"
            f"- Lane focus: {lane.focus}\n"
            f"- Current root-cause draft: {root_cause}\n"
            f"- Current focus: {current_focus}\n"
            f"- Collect: {evidence_lines}\n"
            f"- Join goal: {lane.join_goal or 'Return facts that help the leader decide the next hypothesis.'}\n"
            "- Return facts, command results, and observations only.\n"
            "- Do not mutate the debug session file.\n"
            "- Do not declare the root cause final.\n"
        )
        tasks.append(
            SuggestedDispatchTask(
                lane_name=lane.name,
                agent_role="evidence-collector",
                task_summary=f"{lane.focus} [{profile}]",
                prompt=prompt,
            )
        )
    return tasks


def format_dispatch_plan(tasks: list[SuggestedDispatchTask]) -> str:
    if not tasks:
        return "No suggested child-agent fan-out is available."

    lines = ["### Suggested Codex Dispatch"]
    for task in tasks:
        lines.append(f"- {task.lane_name}: {task.task_summary}")
        lines.append(f"  - role: {task.agent_role}")
        lines.append(f"  - prompt: {task.prompt.strip()}")
    return "\n".join(lines)


def build_codex_spawn_plan(state: DebugGraphState) -> list[SuggestedSpawnTask]:
    tasks = build_codex_dispatch_plan(state)
    spawn_tasks: list[SuggestedSpawnTask] = []
    for task in tasks:
        spawn_tasks.append(
            SuggestedSpawnTask(
                lane_name=task.lane_name,
                agent_type="explorer",
                reasoning_effort="medium",
                message=task.prompt,
            )
        )
    return spawn_tasks


def format_spawn_plan(tasks: list[SuggestedSpawnTask]) -> str:
    if not tasks:
        return "No spawn-ready Codex payloads are available."

    lines = ["### Suggested Codex Spawn Payloads"]
    for task in tasks:
        lines.append(f"- {task.lane_name}: {task.agent_type} ({task.reasoning_effort})")
        lines.append(f"  - message: {task.message.strip()}")
    return "\n".join(lines)
