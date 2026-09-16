from pathlib import Path
import json

from tools.workflow_quality import quick_eval_runner


def test_report_keeps_unknown_quality_unknown(tmp_path: Path):
    source = tmp_path / "records.jsonl"
    output = tmp_path / "report.json"
    source.write_text(
        json.dumps({
            "mode": "direct-compact",
            "input_tokens": 100,
            "output_tokens": 20,
            "duration_ms": 50,
            "accepted": None,
            "human_intervention": False,
        }) + "\n",
        encoding="utf-8",
    )

    quick_eval_runner.main = lambda: 0
    report = quick_eval_runner.summarize(quick_eval_runner.load_records(source))

    assert report["groups"]["direct-compact"]["unknown_quality"] == 1
    assert report["rules"]["quality_from_tokens"] is False


def test_report_groups_all_supported_modes():
    report = quick_eval_runner.summarize([
        {"mode": "worker-full", "input_tokens": 10, "output_tokens": 5, "accepted": True},
        {"mode": "worker-compact", "input_tokens": 5, "output_tokens": 2, "accepted": False},
        {"mode": "direct-full", "input_tokens": 8, "output_tokens": 3, "accepted": True},
        {"mode": "direct-compact", "input_tokens": 4, "output_tokens": 1, "accepted": None},
    ])

    assert set(report["groups"]) == {
        "worker-full",
        "worker-compact",
        "direct-full",
        "direct-compact",
    }
