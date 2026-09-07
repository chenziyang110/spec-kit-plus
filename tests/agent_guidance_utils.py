"""Read repository guidance through the entrypoint's explicit reference links."""

from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GUIDANCE_ROOT = PROJECT_ROOT / "docs" / "agent-guidance"


def agent_guidance_reference_paths() -> tuple[Path, ...]:
    entry = (PROJECT_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    targets = re.findall(
        r"\[[^\]\n]+\]\((docs/agent-guidance/[^)\s#]+)(?:#[^)\s]+)?\)",
        entry,
    )
    references = []
    for target in dict.fromkeys(targets):
        path = (PROJECT_ROOT / target).resolve()
        assert path.is_relative_to(GUIDANCE_ROOT.resolve()), target
        assert path.suffix == ".md" and path.is_file(), target
        references.append(path)
    return tuple(references)


def read_agents_with_references() -> str:
    paths = (PROJECT_ROOT / "AGENTS.md", *agent_guidance_reference_paths())
    return "\n\n".join(path.read_text(encoding="utf-8") for path in paths)
