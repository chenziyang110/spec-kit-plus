import os
import re
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any
import yaml
from .schema import FeatureContext

class ContextLoader:
    def __init__(self, root_dir: Optional[Path] = None):
        self.root_dir = root_dir or Path.cwd()

    def find_active_feature(self) -> Optional[Path]:
        """Find feature dir in specs/* with newest tasks.md."""
        specs_dir = self.root_dir / "specs"
        if not specs_dir.exists():
            return None
        
        newest_task_file = None
        newest_mtime = 0
        
        for task_file in specs_dir.glob("*/tasks.md"):
            mtime = task_file.stat().st_mtime
            if mtime > newest_mtime:
                newest_mtime = mtime
                newest_task_file = task_file
        
        return newest_task_file.parent if newest_task_file else None

    def load_feature_context(self, feature_dir: Path) -> FeatureContext:
        """Map standard paths and parse metadata."""
        context = FeatureContext(
            feature_id=feature_dir.name,
            spec_path=(feature_dir / "spec.md").relative_to(self.root_dir).as_posix() if (feature_dir / "spec.md").exists() else None,
            plan_path=(feature_dir / "plan.md").relative_to(self.root_dir).as_posix() if (feature_dir / "plan.md").exists() else None,
            tasks_path=(feature_dir / "tasks.md").relative_to(self.root_dir).as_posix() if (feature_dir / "tasks.md").exists() else None,
            constitution_path=".specify/memory/constitution.md",
            roadmap_path=".planning/ROADMAP.md"
        )
        
        # Load feature name from spec.md
        if context.spec_path:
            spec_content = (self.root_dir / context.spec_path).read_text(encoding="utf-8")
            match = re.search(r"^#\s+(.+)$", spec_content, re.MULTILINE)
            if match:
                context.feature_name = match.group(1).strip()
        
        # Identify phase from ROADMAP.md
        roadmap_file = self.root_dir / context.roadmap_path
        if roadmap_file.exists():
            roadmap_content = roadmap_file.read_text(encoding="utf-8")
            # Simple heuristic: find the last phase header before any mention of the feature_id
            phases = re.split(r"^###\s+Phase\s+", roadmap_content, flags=re.MULTILINE)
            for phase_block in phases[1:]:
                header = phase_block.split("\n", 1)[0].strip()
                if context.feature_id in phase_block or (context.feature_name and context.feature_name in phase_block):
                    context.feature_phase = f"Phase {header}"
                    break
        
        # Parse plan.md for modified_files
        if context.plan_path:
            plan_file = self.root_dir / context.plan_path
            plan_content = plan_file.read_text(encoding="utf-8")
            # Extract frontmatter
            match = re.search(r"^---\s*\n(.*?)\n---\s*\n", plan_content, re.DOTALL)
            if match:
                try:
                    frontmatter = yaml.safe_load(match.group(1))
                    if frontmatter and "files_modified" in frontmatter:
                        context.modified_files = frontmatter["files_modified"]
                except Exception:
                    pass
        
        return context

    def get_recent_git_changes(self, limit: int = 10) -> List[str]:
        """Get list of files changed in last N commits."""
        try:
            output = subprocess.check_output(
                ["git", "log", f"-n{limit}", "--name-only", "--pretty=format:"],
                cwd=self.root_dir,
                stderr=subprocess.STDOUT,
                text=True
            )
            files = []
            for line in output.splitlines():
                line = line.strip()
                if line and line not in files:
                    files.append(line)
            return files
        except (subprocess.CalledProcessError, FileNotFoundError):
            return []

    def cross_reference_changes(self, git_files: List[str], plan_files: List[str]) -> List[str]:
        """Identify which git-changed files overlap with the plan's modified_files."""
        plan_set = set(plan_files)
        return [f for f in git_files if f in plan_set]
