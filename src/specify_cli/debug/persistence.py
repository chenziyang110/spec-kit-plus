from pathlib import Path
import re
from typing import Any
from datetime import datetime
import yaml
from .schema import (
    DebugGraphState,
)


def build_handoff_report(state: DebugGraphState) -> str:
    lines = [
        "## Awaiting Human Review",
        "",
        f"- Trigger: {state.trigger}",
        f"- Root cause: {state.resolution.root_cause or 'Not confirmed'}",
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
                "current_node_id": frontmatter.get("current_node_id"),
                "created": frontmatter["created"],
                "updated": frontmatter["updated"],
                "current_focus": sections.get("Current Focus") or {},
                "symptoms": sections.get("Symptoms") or {},
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
