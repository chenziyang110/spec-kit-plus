import importlib.util
import sys
from pathlib import Path

import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "tools"
    / "workflow-quality"
    / "measure_workflow_costs.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location(
        "measure_workflow_costs", MODULE_PATH
    )
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_importlib_loader_without_sys_modules_registration():
    prior_module = sys.modules.pop("measure_workflow_costs", None)
    try:
        assert "measure_workflow_costs" not in sys.modules
        module = load_module()
        assert "measure_workflow_costs" not in sys.modules
        assert module.count_words("sp-discussion Truth Pass 质量") == 6
    finally:
        if prior_module is not None:
            sys.modules["measure_workflow_costs"] = prior_module
        else:
            sys.modules.pop("measure_workflow_costs", None)


def test_measure_file_counts_path_kind_lines_words_and_bytes(tmp_path):
    module = load_module()
    target = tmp_path / "nested" / "sample.txt"
    content = "hello world\nsecond line\n"
    target.parent.mkdir()
    target.write_text(content, encoding="utf-8")

    metric = module.measure_file(tmp_path, target, "prompt")

    assert metric.path == "nested/sample.txt"
    assert metric.kind == "prompt"
    assert metric.lines == 2
    assert metric.words == 4
    assert metric.bytes == len(content.encode("utf-8"))


def test_summarize_groups_metrics_by_kind_and_sorts_files():
    module = load_module()
    metrics = [
        module.FileMetric("z.md", "prompt", 3, 5, 7),
        module.FileMetric("a.md", "prompt", 2, 4, 6),
        module.FileMetric("artifact.json", "artifact", 1, 2, 3),
    ]

    summary = module.summarize(metrics)

    assert summary["totals"] == {
        "prompt": {"files": 2, "lines": 5, "words": 9, "bytes": 13},
        "artifact": {"files": 1, "lines": 1, "words": 2, "bytes": 3},
    }
    assert [item["path"] for item in summary["files"]] == [
        "a.md",
        "artifact.json",
        "z.md",
    ]


def test_render_markdown_includes_title_and_prompt_row():
    module = load_module()
    summary = {
        "totals": {
            "prompt": {"files": 1, "lines": 2, "words": 3, "bytes": 4}
        },
        "files": [],
    }

    markdown = module.render_markdown(summary)

    assert markdown.startswith("# Workflow Cost Metrics")
    assert "| prompt | 1 | 2 | 3 | 4 |" in markdown


def test_main_invalid_root_exits_nonzero_with_clear_message(monkeypatch, tmp_path):
    module = load_module()
    missing_root = tmp_path / "missing-root"
    assert not missing_root.exists()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "measure_workflow_costs.py",
            "--root",
            str(missing_root),
            "--format",
            "json",
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        module.main()

    assert exc_info.value.code
    assert "root is not a directory" in str(exc_info.value)
