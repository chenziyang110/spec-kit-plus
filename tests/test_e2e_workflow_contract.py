"""Prompt stage contracts; runtime behavior is exercised by Go E2E tests."""
from pathlib import Path
import re

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
CLASSIC = ROOT / "templates/commands/e2e.md"
ADVANCED = ROOT / "templates/advanced-skills/spx-e2e/SKILL.md"


@pytest.mark.parametrize("path", [CLASSIC, ADVANCED])
def test_each_of_seven_stages_declares_its_consumption_contract(path):
    """Protect the semantic stage handoffs alongside the shared Go runtime."""
    source = path.read_text(encoding="utf-8")
    headings = list(re.finditer(r"^## ([1-7])\. .+$", source, re.MULTILINE))
    assert [int(match.group(1)) for match in headings] == list(range(1, 8))
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(source)
        stage = source[heading.end():end]
        for required in ("**Inputs:**", "**Outputs:**", "**Acceptance:**"):
            assert required in stage, (path.name, heading.group(0), required)
    assert source.index("e2e_scenarios.py check") < headings[2].start()
    assert headings[2].start() < source.index("e2e_coverage.py plan") < headings[3].start()
    assert headings[3].start() < source.index("e2e_scenarios.py audit") < headings[4].start()


@pytest.mark.parametrize("path", [CLASSIC, ADVANCED])
def test_workflows_preserve_coverage_and_execution_boundaries(path):
    source = path.read_text(encoding="utf-8").lower()
    for required in (
        "e2e_coverage.py plan", "e2e_coverage.py audit", "pairwise", "mandatory",
        "exhaustive", "real", "source_revision", "manifest_sha256", "test_sources",
        "not_run", "flaky", "discovery gaps", "production", "test design",
        "review -> accept", "exact resume point", "evidence",
    ):
        assert required in source, (path.name, required)


def test_classic_workflow_metadata_is_complete():
    meta = yaml.safe_load(CLASSIC.read_text(encoding="utf-8").split("---", 2)[1])
    assert set(meta["workflow_contract"]) == {
        "when_to_use", "primary_objective", "primary_outputs", "default_handoff"
    }
    assert "execution-bootstrap.md" in CLASSIC.read_text(encoding="utf-8")


def test_advanced_is_independent_and_explicitly_invoked():
    source = ADVANCED.read_text(encoding="utf-8")
    meta = yaml.safe_load(source.split("---", 2)[1])
    assert set(meta) == {"name", "description"}
    assert meta["name"] == "spx-e2e"
    assert "advanced" in meta["description"].lower()
    assert "references/project-cognition.md" in source
    assert "references/project-learning.md" in source
    assert "{{spec-kit-include:" not in source
    config = yaml.safe_load((ADVANCED.parent / "agents/openai.yaml").read_text(encoding="utf-8"))
    assert config["policy"]["allow_implicit_invocation"] is False
    assert "$spx-e2e" in config["interface"]["default_prompt"]
