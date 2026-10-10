"""Install actual Debug prompts in native formats; do not mock the renderer.

These assertions prove delivery and repair of the prompt contract, not that an
LLM executed it, or that any particular product defect has been fixed.
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path

import pytest


@pytest.fixture(scope="module", params=[
    ("codex", "classic", "sh"), ("codex", "advanced", "sh"),
    ("claude", "classic", "sh"), ("claude", "advanced", "sh"),
    ("gemini", "classic", "sh"),
    ("codex", "classic", "ps"), ("codex", "advanced", "ps"),
], ids=lambda values: "-".join(values))
def installed_debug(request: pytest.FixtureRequest, tmp_path_factory: pytest.TempPathFactory):
    # Keep graph-unit tests runnable without pretending an installer exists.
    # Installer-dependent tests still fail at setup when the real package is absent.
    from specify_cli import _install_shared_infra
    from specify_cli.integrations import get_integration
    from specify_cli.integrations.base import SkillsIntegration
    from specify_cli.integrations.manifest import IntegrationManifest

    agent, profile, script_type = request.param
    project = tmp_path_factory.mktemp(f"debug-loop-{agent}-{profile}-{script_type}")
    integration = get_integration(agent)
    assert integration is not None
    assert _install_shared_infra(project, script_type) is True
    manifest = IntegrationManifest(agent, project)
    created = integration.setup(project, manifest,
        parsed_options={"workflow_profile": profile}, script_type=script_type)
    if isinstance(integration, SkillsIntegration):
        prefix = "spx" if profile == "advanced" else "sp"
        entry = integration.skills_dest(project) / f"{prefix}-debug/SKILL.md"
    else:
        matches = [path for path in created if path.name == integration.command_filename("debug")]
        assert len(matches) == 1
        entry = matches[0]
    assert entry.is_file()
    return project, integration, manifest, profile, script_type, entry


def _navigation_prose(content: str) -> str:
    """Extract instruction prose, excluding frontmatter, comments and fences.

    Parse fences before comments: an HTML opener used as a code specimen must
    not swallow real instructions after the closing fence. This is a bounded
    helper for native prompt references, not a complete Markdown parser.
    """
    raw_lines = content.splitlines()
    if raw_lines and raw_lines[0].strip() == "---":
        end = next((i for i, line in enumerate(raw_lines[1:], 1)
                    if line.strip() in {"---", "..."}), None)
        if end is not None:
            raw_lines = raw_lines[end + 1:]
    lines: list[str] = []
    fence_char = ""
    fence_length = 0
    in_comment = False
    for line in raw_lines:
        if fence_char:
            marker = re.match(r"^\s{0,3}(`{3,}|~{3,})(.*)$", line)
            if marker:
                run, tail = marker.groups()
                if run[0] == fence_char and len(run) >= fence_length and not tail.strip():
                    fence_char = ""
            continue
        visible: list[str] = []
        rest = line
        while rest:
            if in_comment:
                end = rest.find("-->")
                if end == -1:
                    break
                rest = rest[end + 3:]
                in_comment = False
            else:
                start = rest.find("<!--")
                if start == -1:
                    visible.append(rest)
                    break
                visible.append(rest[:start])
                visible.append(" ")
                rest = rest[start + 4:]
                in_comment = True
        prose = "".join(visible)
        marker = re.match(r"^\s{0,3}(`{3,}|~{3,})(.*)$", prose)
        if marker:
            run, _ = marker.groups()
            fence_char, fence_length = run[0], len(run)
        else:
            lines.append(prose)
    return "\n".join(lines)


def _reference_paths(content: str, source: Path, root: Path) -> list[Path]:
    """Resolve documented skill-root references and reference-relative links."""
    from urllib.parse import unquote, urlsplit

    prose = _navigation_prose(content)
    inline = [
        token for token in re.findall(r"`([^`\n]+)`", prose)
        if token.replace("\\", "/").startswith("references/")
    ]
    links = re.findall(
        r'\[[^\]\n]*\]\(([^)\s]+\.md(?:#[^)\s]*)?)(?:\s+"[^"]*")?\)', prose
    )
    resolved: list[Path] = []
    for token in dict.fromkeys(inline + links):
        target = unquote(token).replace("\\", "/")
        if urlsplit(target).scheme or target.startswith(("/", "#")):
            continue
        # These are project artifact contracts, not packaged skill sidecars.
        if target.startswith((".specify/", ".planning/")):
            continue
        target = target.split("#", 1)[0]
        if not target.endswith(".md") or any(c in target for c in "<>[]*"):
            continue
        base = root if target.startswith("references/") else source.parent
        path = (base / target).resolve()
        assert path.is_relative_to(root), f"Reference escapes skill root: {source}: {token}"
        assert path.is_file(), f"Missing reference: {source}: {token}"
        resolved.append(path)
    return resolved


def _effective_text(entry: Path, *, prose_only: bool = False) -> str:
    """Read only reachable references, not every file that happened to install.

    This checks possible delivery, not whether an LLM followed conditional read
    triggers. Prose-only checks cannot pass on examples or metadata, while the
    raw view remains available for unresolved renderer-token checks. TOML commands
    carry their reference contracts inside the prompt.
    """
    content = entry.read_text(encoding="utf-8")
    if entry.suffix == ".toml":
        prompt = tomllib.loads(content).get("prompt")
        assert isinstance(prompt, str), f"Expected text prompt in {entry}"
        body = _navigation_prose(prompt) if prose_only else prompt
        return re.sub(r"\s+", " ", body).lower()

    root = entry.parent.resolve()
    pending = [entry.resolve()]
    visited: set[Path] = set()
    parts: list[str] = []
    while pending:
        source = pending.pop()
        assert source.is_relative_to(root), f"Reference escapes skill root: {source}"
        if source in visited:
            continue
        visited.add(source)
        body = source.read_text(encoding="utf-8")
        parts.append(_navigation_prose(body) if prose_only else body)
        pending.extend(reversed(_reference_paths(body, source, root)))
    return re.sub(r"\s+", " ", "\n".join(parts)).lower()


def test_installed_debug_reaches_full_loop_and_worker_contract(installed_debug) -> None:
    project, _, _, profile, _, entry = installed_debug
    content = _effective_text(entry, prose_only=True)
    raw_content = _effective_text(entry)
    for required in (
        "recency alone", "earliest", "do not impose deep-only fields",
        "red must match the target", "lease conflict", "newer evidence",
        "input revision", "wrong-session", "final integrated revision",
        "awaiting_human_verify", "explicit human confirmation", "same invocation",
        "diagnosis-only delivery", "not defect resolution",
        "navigation hints are not read authorization",
        "before any source, test, harness, configuration, or instrumentation write",
        "contradictory observations are valid evidence",
        "without waiting for a missing handoff", "cancellation is not task acceptance",
        "installation metadata", "historical dispatch failure",
    ):
        assert required in content, (entry, required)
    for forbidden in (
        "the graph engine (gatheringnode) will return", "gathering returns an `await_input`",
        "explicit human confirmation or an evidence-backed classification",
        "if that expands beyond the debug fix lane, route it through",
        "{{spec-kit-include:", "execute_command: debug",
        "before closing the join point, declaring completion, requesting shutdown, or interrupting",
    ):
        assert forbidden not in raw_content, (entry, forbidden)
    worker = (entry.parent / "references/investigator-worker.md" if profile == "advanced"
              else project / ".specify/templates/worker-prompts/debug-investigator.md")
    worker_text = re.sub(r"\s+", " ", _navigation_prose(worker.read_text(encoding="utf-8"))).lower()
    assert "session/lane identity" in worker_text
    assert "a claim awaiting acceptance" in worker_text
    assert "a disconfirming observation is not a failed assignment" in worker_text
    assert "partial evidence" in worker_text


def test_missing_debug_reference_repair_preserves_user_edits(installed_debug) -> None:
    from specify_cli.integrations.base import SkillsIntegration

    project, integration, manifest, profile, script_type, entry = installed_debug
    if not isinstance(integration, SkillsIntegration):
        pytest.skip("The TOML entrypoint embeds its references rather than owning skill sidecars")
    filename = "investigation-contract.md" if profile == "advanced" else "debug-state.md"
    reference = entry.parent / "references" / filename
    assert reference.is_file()
    expected = reference.read_bytes()
    original_entry = entry.read_bytes()
    user_content = original_entry + b"\n<!-- user-owned debug note -->\n"
    try:
        entry.write_bytes(user_content)
        reference.unlink()
        if profile == "advanced":
            integration.repair_missing_advanced_skill_files(project, manifest, script_type=script_type)
        else:
            integration.repair_missing_command_reference_sidecars(project, manifest, script_type=script_type)
        assert reference.read_bytes() == expected
        assert entry.read_bytes() == user_content
    finally:
        entry.write_bytes(original_entry)
        # Test-only cleanup, after assertions: even a wrongly restored reference
        # must not poison subsequent cases that share this fixture.
        reference.write_bytes(expected)


# These synthetic files test reference delivery, not agent execution.
def _graph_fixture(tmp_path: Path, entry_text: str) -> Path:
    entry = tmp_path / "sp-debug" / "SKILL.md"
    entry.parent.mkdir()
    (entry.parent / "references").mkdir()
    entry.write_text(entry_text, encoding="utf-8")
    return entry


def test_reference_graph_excludes_unreachable_sidecars(tmp_path: Path) -> None:
    entry = _graph_fixture(tmp_path, "No recovery reference is loaded.\n")
    (entry.parent / "references/orphan.md").write_text(
        "mandatory repair then resume", encoding="utf-8"
    )
    assert "mandatory repair then resume" not in _effective_text(entry)


def test_reference_graph_detects_a_removed_entry_trigger(tmp_path: Path) -> None:
    entry = _graph_fixture(tmp_path, "Read `references/recovery.md` before exiting.\n")
    reference = entry.parent / "references/recovery.md"
    reference.write_text("mandatory repair then resume", encoding="utf-8")
    assert "mandatory repair then resume" in _effective_text(entry)
    entry.write_text("Recovery trigger accidentally removed.\n", encoding="utf-8")
    assert "mandatory repair then resume" not in _effective_text(entry)


def test_reference_graph_requires_linked_file(tmp_path: Path) -> None:
    entry = _graph_fixture(tmp_path, "Read `references/missing.md`.\n")
    with pytest.raises(AssertionError, match="Missing reference"):
        _effective_text(entry)


def test_reference_graph_follows_index_and_nested_links(tmp_path: Path) -> None:
    entry = _graph_fixture(tmp_path, "Read [Reference index](references/INDEX.md).\n")
    refs = entry.parent / "references"
    (refs / "INDEX.md").write_text(
        "[Probe](nested/probe.md#signals)", encoding="utf-8"
    )
    (refs / "nested").mkdir()
    (refs / "nested/probe.md").write_text(
        "nested evidence contract\nRead `references/shared.md`.", encoding="utf-8"
    )
    (refs / "shared.md").write_text("shared evidence contract", encoding="utf-8")
    content = _effective_text(entry)
    assert "nested evidence contract" in content
    assert "shared evidence contract" in content


def test_reference_graph_deduplicates_cycles(tmp_path: Path) -> None:
    entry = _graph_fixture(tmp_path, "Read `references/a.md` and `references/b.md`.\n")
    refs = entry.parent / "references"
    (refs / "a.md").write_text(
        "unique-a-contract\nRead [B](b.md).", encoding="utf-8"
    )
    (refs / "b.md").write_text(
        "unique-b-contract\nRead [A](a.md).", encoding="utf-8"
    )
    content = _effective_text(entry)
    assert content.count("unique-a-contract") == 1
    assert content.count("unique-b-contract") == 1


@pytest.mark.parametrize("example", [
    "<!-- Read `references/example.md`. -->",
    "```markdown\nRead `references/example.md`.\n```",
    "~~~text\nRead [example](references/example.md).\n~~~",
    "````markdown\n```\nRead `references/example.md`.\n```\n````",
])
def test_reference_graph_does_not_load_examples(tmp_path: Path, example: str) -> None:
    entry = _graph_fixture(tmp_path, example)
    (entry.parent / "references/example.md").write_text(
        "example-only-policy", encoding="utf-8"
    )
    assert "example-only-policy" not in _effective_text(entry)


@pytest.mark.parametrize("target", [
    "references/../../outside.md",
    "references/%2e%2e/%2e%2e/outside.md",
    r"references\..\..\outside.md",
])
def test_reference_graph_rejects_escape(tmp_path: Path, target: str) -> None:
    entry = _graph_fixture(tmp_path, f"Read `{target}`.\n")
    (tmp_path / "outside.md").write_text("outside-secret", encoding="utf-8")
    with pytest.raises(AssertionError, match="escapes"):
        _effective_text(entry)


def test_reference_graph_rejects_symlink_escape(tmp_path: Path) -> None:
    entry = _graph_fixture(tmp_path, "Read `references/outside.md`.\n")
    outside = tmp_path / "outside.md"
    outside.write_text("outside-secret", encoding="utf-8")
    try:
        (entry.parent / "references/outside.md").symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"Host does not permit creating symlinks: {exc}")
    with pytest.raises(AssertionError, match="escapes"):
        _effective_text(entry)


def test_reference_graph_toml_uses_only_embedded_prompt(tmp_path: Path) -> None:
    entry = tmp_path / "sp.debug.toml"
    entry.write_text('description = "metadata"\nprompt = "embedded-contract"\n', encoding="utf-8")
    (tmp_path / "references").mkdir()
    (tmp_path / "references/orphan.md").write_text("orphan-contract", encoding="utf-8")
    content = _effective_text(entry)
    assert "embedded-contract" in content
    assert "orphan-contract" not in content


@pytest.mark.parametrize("toml", ['description = "no prompt"', "prompt = 123"])
def test_reference_graph_requires_text_toml_prompt(tmp_path: Path, toml: str) -> None:
    entry = tmp_path / "sp.debug.toml"
    entry.write_text(toml, encoding="utf-8")
    with pytest.raises(AssertionError, match="text prompt"):
        _effective_text(entry)


@pytest.mark.parametrize("example", [
    "<!-- required-real-policy -->",
    "```text\nrequired-real-policy\n```",
    "---\ndescription: required-real-policy\n---\nNormal body.",
])
def test_policy_view_excludes_non_instruction_text(tmp_path: Path, example: str) -> None:
    entry = _graph_fixture(tmp_path, example)
    assert "required-real-policy" not in _effective_text(entry, prose_only=True)
    assert "required-real-policy" in _effective_text(entry)


def test_comment_delimiter_in_code_does_not_hide_following_live_reference(tmp_path: Path) -> None:
    entry = _graph_fixture(
        tmp_path,
        "```html\n<!-- sample opening delimiter\n```\nRead `references/live.md`.\n",
    )
    (entry.parent / "references/live.md").write_text("actual-live-policy", encoding="utf-8")
    assert "actual-live-policy" in _effective_text(entry, prose_only=True)


def test_reachable_comment_cannot_supply_a_policy_requirement(tmp_path: Path) -> None:
    entry = _graph_fixture(tmp_path, "Read `references/live.md`.\n")
    (entry.parent / "references/live.md").write_text(
        "<!-- required-real-policy -->\nActual body.\n", encoding="utf-8"
    )
    assert "required-real-policy" not in _effective_text(entry, prose_only=True)
    assert "actual body" in _effective_text(entry, prose_only=True)


def test_toml_policy_view_checks_instructions_not_embedded_examples(tmp_path: Path) -> None:
    entry = tmp_path / "sp.debug.toml"
    entry.write_text(
        'prompt = """\nActual policy.\n```text\nexample-only-policy\n```\n"""\n',
        encoding="utf-8",
    )
    assert "actual policy" in _effective_text(entry, prose_only=True)
    assert "example-only-policy" not in _effective_text(entry, prose_only=True)
    assert "example-only-policy" in _effective_text(entry)


def test_raw_view_retains_unresolved_tokens_for_render_validation(tmp_path: Path) -> None:
    entry = _graph_fixture(tmp_path, "```text\n{{spec-kit-include: example.md}}\n```\n")
    assert "{{spec-kit-include:" in _effective_text(entry)
    assert "{{spec-kit-include:" not in _effective_text(entry, prose_only=True)


def test_multiline_comment_hides_only_comment_and_not_later_reference(tmp_path: Path) -> None:
    entry = _graph_fixture(tmp_path, "<!--\nRead `references/missing.md`.\n-->\nRead `references/live.md`.\n")
    (entry.parent / "references/live.md").write_text("actual-live-policy", encoding="utf-8")
    assert "actual-live-policy" in _effective_text(entry, prose_only=True)
