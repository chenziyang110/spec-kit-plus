import yaml
from pathlib import Path
import re
from typing import Dict, Any, List
from datetime import datetime
from .schema import (
    DebugGraphState, 
    DebugStatus, 
    Focus, 
    Symptoms, 
    EliminatedEntry, 
    EvidenceEntry, 
    Resolution
)

class MarkdownPersistenceHandler:
    def __init__(self, debug_dir: Path):
        self.debug_dir = debug_dir
        self.debug_dir.mkdir(parents=True, exist_ok=True)

    def save(self, state: DebugGraphState):
        file_path = self.debug_dir / f"{state.slug}.md"
        
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
        content += yaml.dump(frontmatter, sort_keys=False)
        content += "---\n\n"
        
        # Current Focus
        content += "## Current Focus\n"
        content += "<!-- OVERWRITE on each update - always reflects NOW -->\n\n"
        content += f"hypothesis: {state.current_focus.hypothesis or ''}\n"
        content += f"test: {state.current_focus.test or ''}\n"
        content += f"expecting: {state.current_focus.expecting or ''}\n"
        content += f"next_action: {state.current_focus.next_action or ''}\n\n"
        
        # Symptoms
        content += "## Symptoms\n"
        content += "<!-- Written during gathering, then immutable -->\n\n"
        content += f"expected: {state.symptoms.expected or ''}\n"
        content += f"actual: {state.symptoms.actual or ''}\n"
        content += f"errors: {state.symptoms.errors or ''}\n"
        content += f"reproduction: {state.symptoms.reproduction or ''}\n"
        content += f"started: {state.symptoms.started or ''}\n\n"
        
        # Eliminated
        content += "## Eliminated\n"
        content += "<!-- APPEND only - prevents re-investigating after context reset -->\n\n"
        for entry in state.eliminated:
            content += f"- hypothesis: {entry.hypothesis}\n"
            content += f"  evidence: {entry.evidence}\n"
            content += f"  timestamp: {entry.timestamp.isoformat()}\n"
        content += "\n"
        
        # Evidence
        content += "## Evidence\n"
        content += "<!-- APPEND only - facts discovered during investigation -->\n\n"
        for entry in state.evidence:
            content += f"- timestamp: {entry.timestamp.isoformat()}\n"
            content += f"  checked: {entry.checked}\n"
            content += f"  found: {entry.found}\n"
            content += f"  implication: {entry.implication}\n"
        content += "\n"
        
        # Resolution
        content += "## Resolution\n"
        content += "<!-- OVERWRITE as understanding evolves -->\n\n"
        content += f"root_cause: {state.resolution.root_cause or ''}\n"
        content += f"fix: {state.resolution.fix or ''}\n"
        content += f"verification: {state.resolution.verification or ''}\n"
        content += f"files_changed: {state.resolution.files_changed or []}\n"
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

    def load(self, path: Path) -> DebugGraphState:
        if not path.exists():
            raise FileNotFoundError(f"Debug session file not found: {path}")
            
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Parse YAML frontmatter
        parts = content.split("---", 2)
        if len(parts) < 3:
            raise ValueError("Invalid debug session file format: Missing YAML frontmatter")
            
        frontmatter = yaml.safe_load(parts[1])
        body = parts[2]
        
        # Extract sections using regex
        sections = {}
        section_names = ["Current Focus", "Symptoms", "Eliminated", "Evidence", "Resolution"]
        
        current_section = None
        current_content = []
        
        for line in body.splitlines():
            match = re.match(r"^##\s+(.*)", line)
            if match:
                if current_section:
                    sections[current_section] = "\n".join(current_content).strip()
                current_section = match.group(1).strip()
                current_content = []
            elif current_section:
                current_content.append(line)
        
        if current_section:
            sections[current_section] = "\n".join(current_content).strip()
            
        # Parse sections into models
        def parse_fields(text: str) -> Dict[str, str]:
            fields = {}
            for line in text.splitlines():
                if ":" in line and not line.strip().startswith("-"):
                    key, val = line.split(":", 1)
                    fields[key.strip()] = val.strip()
            return fields

        focus_fields = parse_fields(sections.get("Current Focus", ""))
        symptoms_fields = parse_fields(sections.get("Symptoms", ""))
        resolution_fields = parse_fields(sections.get("Resolution", ""))
        
        # Parse Eliminated (list of entries)
        eliminated = []
        eliminated_text = sections.get("Eliminated", "")
        # Remove comment
        eliminated_text = re.sub(r"<!--.*?-->", "", eliminated_text).strip()
        if eliminated_text:
            # Basic bullet point parsing
            entries = re.split(r"^- ", eliminated_text, flags=re.MULTILINE)
            for entry in entries:
                if not entry.strip(): continue
                fields = parse_fields(entry)
                if "hypothesis" in fields and "evidence" in fields:
                    eliminated.append(EliminatedEntry(
                        hypothesis=fields["hypothesis"],
                        evidence=fields["evidence"],
                        timestamp=datetime.fromisoformat(fields["timestamp"]) if "timestamp" in fields else datetime.now()
                    ))

        # Parse Evidence (list of entries)
        evidence = []
        evidence_text = sections.get("Evidence", "")
        evidence_text = re.sub(r"<!--.*?-->", "", evidence_text).strip()
        if evidence_text:
            entries = re.split(r"^- ", evidence_text, flags=re.MULTILINE)
            for entry in entries:
                if not entry.strip(): continue
                fields = parse_fields(entry)
                if all(k in fields for k in ["checked", "found", "implication"]):
                    evidence.append(EvidenceEntry(
                        timestamp=datetime.fromisoformat(fields["timestamp"]) if "timestamp" in fields else datetime.now(),
                        checked=fields["checked"],
                        found=fields["found"],
                        implication=fields["implication"]
                    ))

        # Re-inflate state
        state = DebugGraphState(
            slug=frontmatter["slug"],
            status=DebugStatus(frontmatter["status"]),
            trigger=frontmatter["trigger"],
            current_node_id=frontmatter.get("current_node_id"),
            created=datetime.fromisoformat(frontmatter["created"]),
            updated=datetime.fromisoformat(frontmatter["updated"]),
            current_focus=Focus(**focus_fields),
            symptoms=Symptoms(**symptoms_fields),
            eliminated=eliminated,
            evidence=evidence,
            resolution=Resolution(
                root_cause=resolution_fields.get("root_cause"),
                fix=resolution_fields.get("fix"),
                verification=resolution_fields.get("verification"),
                files_changed=eval(resolution_fields.get("files_changed", "[]"))
            )
        )
        
        return state

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
