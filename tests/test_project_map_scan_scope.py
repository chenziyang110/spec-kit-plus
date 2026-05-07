from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODULE_PATH = PROJECT_ROOT / "src" / "specify_cli" / "project_map_status.py"


def _load_module():
    spec = spec_from_file_location("project_map_status_scope", MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_project_map_scope_classifies_runtime_atlas_and_workbench_distinctly():
    mod = _load_module()

    assert mod.classify_scan_scope_path("src/specify_cli/project_map_status.py") == "live_surface"
    assert mod.classify_scan_scope_path("templates/commands/map-scan.md") == "live_surface"
    assert mod.classify_scan_scope_path(".specify/memory/project-rules.md") == "live_surface"
    assert mod.classify_scan_scope_path(".specify/templates/project-map/ARCHITECTURE.md") == "live_surface"
    assert mod.classify_scan_scope_path("PROJECT-HANDBOOK.md") == "reference_only"
    assert mod.classify_scan_scope_path(".specify/project-map/root/ARCHITECTURE.md") == "reference_only"
    assert mod.classify_scan_scope_path(".specify/project-map/index/capabilities.json") == "reference_only"
    assert mod.classify_scan_scope_path(".specify/project-map/scan-packets/SCAN-core.md") == "reference_only"
    assert mod.classify_scan_scope_path(".specify/project-map/worker-results/SCAN-core.json") == "reference_only"
    assert mod.classify_scan_scope_path(".pytest_cache/v/cache/nodeids") == "hard_excluded"


def test_project_map_scope_filter_drops_reference_only_and_keeps_live_candidates():
    mod = _load_module()

    filtered = mod.filter_scan_scope_candidates(
        [
            "src/specify_cli/project_map_status.py",
            ".specify/project-map/index/status.json",
            "PROJECT-HANDBOOK.md",
            ".specify/templates/project-map/ARCHITECTURE.md",
            ".pytest_cache/v/cache/nodeids",
        ]
    )

    assert filtered["live_candidates"] == [
        "src/specify_cli/project_map_status.py",
        ".specify/templates/project-map/ARCHITECTURE.md",
    ]
    assert filtered["reference_only"] == [
        ".specify/project-map/index/status.json",
        "PROJECT-HANDBOOK.md",
    ]
    assert filtered["hard_excluded"] == [".pytest_cache/v/cache/nodeids"]
