from pathlib import Path
import re
from typing import Any
from datetime import datetime
import yaml
from .schema import (
    DebugGraphState,
)
from .dispatch import build_codex_dispatch_plan, build_codex_spawn_plan


def build_handoff_report(state: DebugGraphState) -> str:
    root_cause = state.resolution.root_cause.display_text() if state.resolution.root_cause else "Not confirmed"
    lines = [
        "## Awaiting Human Review",
        "",
        f"- Trigger: {state.trigger}",
        f"- Diagnostic profile: {state.diagnostic_profile or 'Not classified'}",
        f"- Root cause: {root_cause}",
        f"- Attempted fix: {state.resolution.fix or 'No fix recorded'}",
        f"- Verification status: {state.resolution.verification or 'unknown'}",
        f"- Failed verification attempts: {state.resolution.fail_count}",
        "",
        "### Eliminated Hypotheses",
    ]

    if state.eliminated:
        for entry in state.eliminated:
            lines.append(f"- {entry.hypothesis}: {entry.evidence}")
    else:
        lines.append("- None recorded")

    lines.extend(["", "### Key Evidence"])
    if state.evidence:
        for entry in state.evidence:
            lines.append(
                f"- {entry.checked}: {entry.found} -> {entry.implication}"
            )
    else:
        lines.append("- None recorded")

    lines.extend(["", "### Truth Ownership"])
    if state.truth_ownership:
        for entry in state.truth_ownership:
            owner_line = f"- {entry.layer}: {entry.owns}"
            if entry.evidence:
                owner_line += f" ({entry.evidence})"
            lines.append(owner_line)
    else:
        lines.append("- Not recorded")

    lines.extend(["", "### Decisive Signals"])
    if state.resolution.decisive_signals:
        for signal in state.resolution.decisive_signals:
            lines.append(f"- {signal}")
    else:
        lines.append("- Not recorded")

    lines.extend(["", "### Suggested Evidence Lanes"])
    if state.suggested_evidence_lanes:
        for lane in state.suggested_evidence_lanes:
            lines.append(f"- {lane.name}: {lane.focus}")
            for item in lane.evidence_to_collect:
                lines.append(f"  - {item}")
            if lane.join_goal:
                lines.append(f"  - join goal: {lane.join_goal}")
    else:
        lines.append("- Not recorded")

    dispatch_plan = build_codex_dispatch_plan(state)
    lines.extend(["", "### Suggested Codex Dispatch"])
    if dispatch_plan:
        for task in dispatch_plan:
            lines.append(f"- {task.lane_name}: {task.task_summary}")
            lines.append(f"  - role: {task.agent_role}")
            lines.append(f"  - prompt: {task.prompt.strip()}")
    else:
        lines.append("- Not recorded")

    spawn_plan = build_codex_spawn_plan(state)
    lines.extend(["", "### Suggested Codex Spawn Payloads"])
    if spawn_plan:
        for task in spawn_plan:
            lines.append(f"- {task.lane_name}: {task.agent_type} ({task.reasoning_effort})")
            lines.append(f"  - message: {task.message.strip()}")
    else:
        lines.append("- Not recorded")

    lines.extend(["", "### Root Cause Structure"])
    if state.resolution.root_cause:
        if state.resolution.root_cause.owning_layer:
            lines.append(f"- Owning layer: {state.resolution.root_cause.owning_layer}")
        if state.resolution.root_cause.broken_control_state:
            lines.append(f"- Broken control state: {state.resolution.root_cause.broken_control_state}")
        if state.resolution.root_cause.failure_mechanism:
            lines.append(f"- Failure mechanism: {state.resolution.root_cause.failure_mechanism}")
        if state.resolution.root_cause.loop_break:
            lines.append(f"- Closed-loop break: {state.resolution.root_cause.loop_break}")
        if state.resolution.root_cause.decisive_signal:
            lines.append(f"- Primary decisive signal: {state.resolution.root_cause.decisive_signal}")
    else:
        lines.append("- Not recorded")

    lines.extend(
        [
            "",
            "### Next Step",
            "Continue the investigation manually from the persisted session file.",
        ]
    )
    return "\n".join(lines)

class MarkdownPersistenceHandler:
    def __init__(self, debug_dir: Path):
        self.debug_dir = debug_dir
        self.debug_dir.mkdir(parents=True, exist_ok=True)

    def _session_path(self, slug: str) -> Path:
        if not slug or Path(slug).name != slug or any(sep in slug for sep in ("/", "\\")):
            raise ValueError("Invalid debug session slug")

        file_path = (self.debug_dir / f"{slug}.md").resolve()
        debug_root = self.debug_dir.resolve()
        if file_path.parent != debug_root:
            raise ValueError("Debug session path escapes debug directory")

        return file_path

    def save(self, state: DebugGraphState):
        file_path = self._session_path(state.slug)
        
        # Frontmatter
        frontmatter = {
            "slug": state.slug,
            "status": state.status.value,
            "trigger": state.trigger,
            "diagnostic_profile": state.diagnostic_profile,
            "current_node_id": state.current_node_id,
            "created": state.created.isoformat(),
            "updated": datetime.now().isoformat()
        }
        
        content = "---\n"
        content += yaml.safe_dump(frontmatter, sort_keys=False)
        content += "---\n\n"

        sections = [
            ("Current Focus", state.current_focus.model_dump(mode="json")),
            ("Symptoms", state.symptoms.model_dump(mode="json")),
            ("Suggested Evidence Lanes", [lane.model_dump(mode="json") for lane in state.suggested_evidence_lanes]),
            ("Truth Ownership", [entry.model_dump(mode="json") for entry in state.truth_ownership]),
            ("Control State", state.control_state),
            ("Observation State", state.observation_state),
            ("Closed Loop", state.closed_loop.model_dump(mode="json")),
            ("Context", state.context.model_dump(mode="json")),
            ("Recently Modified", state.recently_modified),
            ("Eliminated", [entry.model_dump(mode="json") for entry in state.eliminated]),
            ("Evidence", [entry.model_dump(mode="json") for entry in state.evidence]),
            ("Resolution", state.resolution.model_dump(mode="json")),
        ]

        for title, payload in sections:
            content += f"## {title}\n"
            content += yaml.safe_dump(payload, sort_keys=False).rstrip()
            content += "\n\n"
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    def build_handoff_report(self, state: DebugGraphState) -> str:
        return build_handoff_report(state)

    def load(self, path: Path) -> DebugGraphState:
        if not path.exists():
            raise FileNotFoundError(f"Debug session file not found: {path}")
            
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Parse YAML frontmatter without being confused by `---` inside values.
        lines = content.splitlines()
        if not lines or lines[0] != "---":
            raise ValueError("Invalid debug session file format: Missing YAML frontmatter")

        try:
            frontmatter_end = lines[1:].index("---") + 1
        except ValueError as exc:
            raise ValueError("Invalid debug session file format: Unterminated YAML frontmatter") from exc

        frontmatter = yaml.safe_load("\n".join(lines[1:frontmatter_end]))
        body = "\n".join(lines[frontmatter_end + 1 :])
        
        # Extract sections using markdown headings and decode each as YAML.
        sections: dict[str, Any] = {}
        
        current_section = None
        current_content = []
        
        for line in body.splitlines():
            match = re.match(r"^##\s+(.*)", line)
            if match:
                if current_section:
                    section_text = "\n".join(current_content).strip()
                    sections[current_section] = yaml.safe_load(section_text) if section_text else None
                current_section = match.group(1).strip()
                current_content = []
            elif current_section:
                current_content.append(line)
        
        if current_section:
            section_text = "\n".join(current_content).strip()
            sections[current_section] = yaml.safe_load(section_text) if section_text else None

        return DebugGraphState.model_validate(
            {
                "slug": frontmatter["slug"],
                "status": frontmatter["status"],
                "trigger": frontmatter["trigger"],
                "diagnostic_profile": frontmatter.get("diagnostic_profile"),
                "current_node_id": frontmatter.get("current_node_id"),
                "created": frontmatter["created"],
                "updated": frontmatter["updated"],
                "current_focus": sections.get("Current Focus") or {},
                "symptoms": sections.get("Symptoms") or {},
                "suggested_evidence_lanes": sections.get("Suggested Evidence Lanes") or [],
                "truth_ownership": sections.get("Truth Ownership") or [],
                "control_state": sections.get("Control State") or [],
                "observation_state": sections.get("Observation State") or [],
                "closed_loop": sections.get("Closed Loop") or {},
                "context": sections.get("Context") or {},
                "recently_modified": sections.get("Recently Modified") or [],
                "eliminated": sections.get("Eliminated") or [],
                "evidence": sections.get("Evidence") or [],
                "resolution": sections.get("Resolution") or {},
            }
        )

    def load_most_recent_session(self) -> DebugGraphState | None:
        """
        Finds and loads the most recently updated debug session from the debug directory.
        """
        if not self.debug_dir.exists():
            return None
            
        sessions = list(self.debug_dir.glob("*.md"))
        if not sessions:
            return None
            
        # Sort by modification time, newest first
        sessions.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Try to load the most recent one. If it's corrupted, try the next one.
        for session_path in sessions:
            try:
                return self.load(session_path)
            except Exception:
                continue
                
        return None
