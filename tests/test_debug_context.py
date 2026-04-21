import os
from pathlib import Path
import pytest
from specify_cli.debug.context import ContextLoader

def test_find_active_feature(tmp_path):
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    
    feat1 = specs_dir / "001-feat"
    feat1.mkdir()
    (feat1 / "tasks.md").write_text("tasks 1")
    
    feat2 = specs_dir / "002-feat"
    feat2.mkdir()
    task2 = feat2 / "tasks.md"
    task2.write_text("tasks 2")
    
    # Set older time for task1
    os.utime(feat1 / "tasks.md", (100, 100))
    # Set newer time for task2
    os.utime(task2, (200, 200))
    
    loader = ContextLoader(root_dir=tmp_path)
    active = loader.find_active_feature()
    assert active.name == "002-feat"

def test_load_feature_context(tmp_path):
    (tmp_path / ".planning").mkdir()
    roadmap = tmp_path / ".planning" / "ROADMAP.md"
    roadmap.write_text("""
### Phase 1: Foundation
- Some plan
### Phase 2: Context
- 002-feat
""")
    
    specs_dir = tmp_path / "specs"
    specs_dir.mkdir()
    feat2 = specs_dir / "002-feat"
    feat2.mkdir()
    (feat2 / "spec.md").write_text("# Feature: Super Cool\nDetails")
    (feat2 / "plan.md").write_text("""---
files_modified:
  - src/app.py
  - tests/test_app.py
---
Plan content""")
    (feat2 / "tasks.md").write_text("tasks")
    
    loader = ContextLoader(root_dir=tmp_path)
    context = loader.load_feature_context(feat2)
    
    assert context.feature_id == "002-feat"
    assert context.feature_name == "Feature: Super Cool"
    assert "Phase 2" in context.feature_phase
    assert "src/app.py" in context.modified_files
    assert context.spec_path == "specs/002-feat/spec.md"

def test_cross_reference(tmp_path):
    loader = ContextLoader(root_dir=tmp_path)
    git_files = ["src/app.py", "README.md"]
    plan_files = ["src/app.py", "tests/test_app.py"]
    overlap = loader.cross_reference_changes(git_files, plan_files)
    assert overlap == ["src/app.py"]
