from pathlib import Path
import json


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_quick_nav_behaves_like_dictionary_entry_surface() -> None:
    content = (PROJECT_ROOT / "templates" / "project-map" / "QUICK-NAV.md").read_text(encoding="utf-8").lower()

    assert "## by symptom" in content
    assert "shared-surface hotspots" in content
    assert "verification routes" in content
    assert "propagation-risk routes" in content
    assert "which module most likely owns the touched area" in content


def test_atlas_index_exposes_query_oriented_entry_metadata() -> None:
    payload = json.loads((PROJECT_ROOT / "templates" / "project-map" / "index" / "atlas-index.json").read_text(encoding="utf-8"))

    assert "entrypoints" in payload
    assert "root_topics" in payload
    assert "module_registry_path" in payload
    assert "relations_path" in payload
    assert "status_path" in payload
    assert "entry_contract" in payload
    assert "recommended_minimum_read_set" in payload
