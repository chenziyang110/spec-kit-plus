"""Guard the E2E workflow's shared registrations without weakening catalog tests."""
import ast
import json
from pathlib import Path
import tomllib

from specify_cli.extensions import CORE_COMMAND_NAMES, _FALLBACK_CORE_COMMAND_NAMES
from specify_cli.integrations.claude import ARGUMENT_HINTS
from specify_cli.learnings import KNOWN_COMMANDS
from specify_cli.orchestration.models import should_attempt_one_subagent

ROOT = Path(__file__).resolve().parents[1]


def test_e2e_runtime_identity_and_python_consumers():
    policies = json.loads((ROOT / 'templates/artifacts/project-cognition-workflow-registry.json').read_text(encoding="utf-8"))['workflows']
    assert policies['e2e']['mode'] == 'mutation_closeout'
    assert policies['e2e']['canonical_workflow'] == 'sp-e2e'
    assert policies['test-design']['mode'] == 'no_closeout'
    assert policies['accept']['mode'] == 'no_closeout'
    assert 'sp-e2e' in KNOWN_COMMANDS
    assert 'e2e' in CORE_COMMAND_NAMES
    assert 'e2e' in _FALLBACK_CORE_COMMAND_NAMES
    assert should_attempt_one_subagent('e2e')
    assert ARGUMENT_HINTS['e2e']


def test_e2e_advanced_catalog_preserves_independent_expected_set():
    root = ROOT / 'templates/advanced-skills'
    mapping = json.loads((root / '_shared/surface-map.json').read_text(encoding="utf-8"))
    entry = mapping['skills']['spx-e2e']
    assert entry['absorbs'] == ['e2e']
    assert entry['references'] == ['spx-e2e/references/scenario-design.md']
    assert (root / entry['references'][0]).is_file()
    assert set(mapping['classic_companion_skills']) == {'sp-map-scan', 'sp-map-build', 'sp-map-update'}
    tree = ast.parse((ROOT / 'tests/test_spx_skill.py').read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.Assign) and any(
        isinstance(t, ast.Name) and t.id == 'SPX_SKILLS' for t in n.targets))
    expected = ast.literal_eval(node.value)
    assert 'spx-e2e' in expected
    assert expected == set(mapping['skills'])
    assert expected == {p.name for p in root.iterdir() if (p / 'SKILL.md').is_file()}


def test_e2e_helpers_remain_part_of_wheel_source_contract():
    # Package inclusion is necessary but not a substitute for wheel installation.
    config = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding="utf-8"))
    included = config['tool']['hatch']['build']['targets']['wheel']['force-include']
    assert included['scripts/shared'] == 'specify_cli/core_pack/scripts/shared'
    assert included['templates/advanced-skills'] == 'specify_cli/core_pack/advanced-skills'
    for name in ('e2e_scenarios.py', 'e2e_coverage.py', 'e2e_runner.py', 'e2e_pytest_reporter.py'):
        assert (ROOT / 'scripts/shared' / name).is_file()


def test_e2e_mutation_gate_is_reachable_without_an_invented_stage():
    classic = (ROOT / 'templates/commands/e2e.md').read_text(encoding="utf-8")
    advanced = (ROOT / 'templates/advanced-skills/spx-e2e/SKILL.md').read_text(encoding="utf-8")
    assert '../command-partials/common/inline-project-cognition-update.md' in classic
    assert '../command-partials/common/learning-layer.md' in classic
    assert 'canonical workflow `sp-e2e`' in advanced
    assert 'references/project-cognition.md' in advanced
    for body in (classic, advanced):
        assert 'other' in body.lower() and 'Work Board' in body
        assert 'test-only' in body.lower()


def test_e2e_init_guidance_uses_the_existing_native_display_mapper():
    source = (ROOT / "src/specify_cli/__init__.py").read_text(encoding="utf-8")
    assert "_display_cmd('e2e')" in source
    assert "scenario-first E2E" in source
