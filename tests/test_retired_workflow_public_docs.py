from __future__ import annotations

import re
from pathlib import Path

from .agent_guidance_utils import agent_guidance_reference_paths


ROOT = Path(__file__).resolve().parents[1]

RETIRED_WORKFLOW_TOKEN = re.compile(
    r"(?<![A-Za-z0-9-])(?:sp-prd|spx-prd|sp-research|spx-research)(?!-[A-Za-z0-9])"
)
RETIRED_ALIAS_GUIDANCE = re.compile(
    r"(?:`prd` remains[^\n]*compatibility|If `prd` is present[^\n]*deprecated|"
    r"`research` (?:is|remains|is accepted)[^\n]*compatibility alias|"
    r"treat `research` as a compatibility alias)",
    re.IGNORECASE,
)


def test_active_public_guidance_no_longer_advertises_retired_workflow_aliases() -> None:
    active_guidance = (
        "AGENTS.md",
        "README.md",
        "PROJECT-HANDBOOK.md",
        "templates/project-handbook-template.md",
        "templates/project-map/WORKFLOWS.md",
        "templates/project-map/root/WORKFLOWS.md",
        "docs/quickstart.md",
        "docs/installation.md",
        *(
            path.relative_to(ROOT.resolve()).as_posix()
            for path in agent_guidance_reference_paths()
        ),
    )

    violations: list[str] = []
    for relative in active_guidance:
        content = (ROOT / relative).read_text(encoding="utf-8")
        for pattern in (RETIRED_WORKFLOW_TOKEN, RETIRED_ALIAS_GUIDANCE):
            if match := pattern.search(content):
                line = content.count("\n", 0, match.start()) + 1
                violations.append(f"{relative}:{line}: {match.group(0)}")

    assert violations == []


def test_profile_documentation_uses_post_retirement_catalog_sizes() -> None:
    agents = " ".join((ROOT / "AGENTS.md").read_text(encoding="utf-8").split())

    assert "29 one-to-one Classic command counterparts plus `spx-map-rebuild`" in agents
    assert "current topology is 30 SPX skills" in agents


def test_public_guidance_keeps_canonical_replacements() -> None:
    handbook = (ROOT / "PROJECT-HANDBOOK.md").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    for content in (handbook, readme):
        assert "sp-prd-scan" in content
        assert "sp-prd-build" in content
        assert "deep-research" in content
    assert "$spx-review" in readme


def test_readme_advanced_skill_listing_matches_the_live_catalog() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    listing = readme.split(
        "After an advanced-profile init, use independent, discoverable SPX skills:",
        1,
    )[1].split("Advanced installs also include", 1)[0]
    documented = set(re.findall(r"\$((?:spx)-[a-z0-9-]+)", listing))
    installed = {
        path.name
        for path in (ROOT / "templates" / "advanced-skills").glob("spx-*")
        if (path / "SKILL.md").is_file()
    }

    assert documented == installed
