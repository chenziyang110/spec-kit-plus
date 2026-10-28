"""The visual probe freezes intent before UI execution and never creates passes."""
import importlib.util
from pathlib import Path

import pytest


def test_visual_probe_freezes_reproducible_source_bound_book(tmp_path):
    source = Path(__file__).parent / 'e2e_samples/e2e_visual_probe.py'
    spec = importlib.util.spec_from_file_location('e2e_visual_probe', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    first = module.prepare(tmp_path / 'first')
    second = module.prepare(tmp_path / 'second')
    assert first == second
    assert first['scenario_count'] == 3
    assert first['condition_count'] == 9
    assert first['timing_count'] == 1
    assert not (tmp_path / 'first/trace.json').exists()
    assert not (tmp_path / 'first/evidence').exists()
    with pytest.raises(FileExistsError):
        module.prepare(tmp_path / 'first')
