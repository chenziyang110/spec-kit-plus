import codecs
import os
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
BASH_SCRIPT = REPO_ROOT / "scripts" / "bash" / "update-agent-context.sh"
POWERSHELL_SCRIPT = REPO_ROOT / "scripts" / "powershell" / "update-agent-context.ps1"
BLOCK_START = "<!-- SPEC-KIT:BEGIN -->"
BLOCK_END = "<!-- SPEC-KIT:END -->"
POWERSHELL = shutil.which("pwsh") or shutil.which("powershell")


def _bash_path(path: str | Path) -> str:
    raw = str(Path(path).resolve())
    normalized = raw.replace("\\", "/")
    if os.name != "nt":
        return normalized

    bash = shutil.which("bash")
    if bash is None:
        return normalized

    probe = subprocess.run(
        [
            bash,
            "-lc",
            'if [ -r /proc/version ] && grep -qi microsoft /proc/version; then printf wsl; else printf other; fi',
        ],
        text=True,
        errors="replace",
        capture_output=True,
        check=False,
    )
    if probe.stdout.strip() == "wsl" and len(normalized) >= 2 and normalized[1] == ":":
        return f"/mnt/{normalized[0].lower()}{normalized[2:]}"
    return normalized


def _seed_repo(
    repo: Path,
    *,
    with_template: bool = True,
    language_version: str = "Python 3.13",
    primary_dependencies: str = "Typer",
    storage: str = "N/A",
    project_type: str = "cli",
) -> None:
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo,
        check=True,
        capture_output=True,
    )

    if with_template:
        (repo / ".specify" / "templates").mkdir(parents=True, exist_ok=True)
        (repo / ".specify" / "templates" / "agent-file-template.md").write_text(
            "# [PROJECT NAME]\n\n"
            "Last updated: [DATE]\n\n"
            "## Active Technologies\n\n"
            "[EXTRACTED FROM ALL PLAN.MD FILES]\n\n"
            "## Recent Changes\n\n"
            "[LAST 3 FEATURES AND WHAT THEY ADDED]\n",
            encoding="utf-8",
        )
    else:
        (repo / ".specify").mkdir(parents=True, exist_ok=True)

    spec_dir = repo / "specs" / "001-test-feature"
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "plan.md").write_text(
        f"**Language/Version**: {language_version}\n"
        f"**Primary Dependencies**: {primary_dependencies}\n"
        f"**Storage**: {storage}\n"
        f"**Project Type**: {project_type}\n",
        encoding="utf-8",
    )

    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "checkout", "-b", "001-test-feature"],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _run_bash_update(repo: Path, agent_type: str = "codex") -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", _bash_path(BASH_SCRIPT), agent_type],
        cwd=repo,
        text=True,
        errors="replace",
        capture_output=True,
        check=False,
    )


def _run_powershell_update(
    repo: Path, agent_type: str = "codex"
) -> subprocess.CompletedProcess[str]:
    command = [POWERSHELL, "-NoProfile", "-File", str(POWERSHELL_SCRIPT)]
    if agent_type:
        command.extend(["-AgentType", agent_type])
    return subprocess.run(
        command,
        cwd=repo,
        text=True,
        errors="replace",
        capture_output=True,
        check=False,
    )


def _read_utf8_without_bom(path: Path) -> str:
    raw = path.read_bytes()
    assert not raw.startswith(codecs.BOM_UTF8), "unexpected UTF-8 BOM"
    return raw.decode("utf-8")


def _normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _assert_managed_block_is_compact_always_on_context(content: str) -> None:
    lower = content.lower()

    assert "## always-on context" in lower
    assert "project cognition and project memory are always available" in lower
    assert "even without an active `sp-*` workflow" in lower
    assert "when existing-system truth matters" in lower
    assert "before broad source inspection" in lower
    assert "narrow live reads" in lower
    assert ".specify/memory/project-rules.md" in content
    assert ".specify/memory/learnings/INDEX.md" in content
    assert "## workflow recommendations" in lower
    assert "do not auto-enter an `sp-*` workflow" in lower
    assert "unless the user invokes it" in lower
    assert "recommend `sp-discussion`" in lower
    assert "`sp-specify` for formal alignment" in lower
    assert "`sp-deep-research` for feasibility proof" in lower
    assert "`sp-debug` for root-cause diagnosis" in lower
    assert "## command surface rules" in lower
    assert "specify --help" in lower
    assert "specify create-feature" in lower
    assert "generated create-feature script" in lower
    assert "## durable state" in lower
    assert "prefer durable workflow state and explicit feature paths" in lower
    assert "frontstage-only deferred persistence" in lower
    assert "do not write discussion files, counters, dirty markers, receipts, or status summaries for every user reply" in lower
    assert "semantic checkpoints, user-triggered checkpoints/saves, compaction risk, or lifecycle transitions" in lower
    assert "suggest `checkpoint, continue`" in lower
    assert "prompt does not write files by itself" in lower
    assert "project cognition freshness truthful" in lower
    assert "store reusable lessons in project memory" in lower

    assert "## workflow activation discipline" not in lower
    assert "1% chance" not in lower
    assert "before any response or action" not in lower
    assert "## workflow routing" not in lower
    assert "## artifact priority" not in lower
    assert "## brownfield context gate" not in lower
    assert "## project cognition usage" not in lower
    assert "## map maintenance" not in lower
    assert "## delegated execution defaults" not in lower
    assert "sp-fast" not in lower
    assert "sp-quick" not in lower
    assert "sp-test-scan" not in lower
    assert "sp-test-build" not in lower
    assert ".specify/project-map/" not in lower
    assert "project-map complete-refresh" not in lower
    assert "project-map mark-dirty" not in lower
    assert "known-stale handbook state" not in lower
    assert "map-level truth" not in lower


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash is not installed")
def test_bash_script_inserts_managed_block_without_overwriting_user_content(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_repo(repo)

    agents = repo / "AGENTS.md"
    initial = "# User Notes\n\nKeep this line.\n\n"
    agents.write_text(initial, encoding="utf-8")

    result = _run_bash_update(repo)

    assert result.returncode == 0, result.stderr
    content = agents.read_text(encoding="utf-8")
    assert content[: content.index(BLOCK_START)] == initial
    assert BLOCK_START in content
    assert BLOCK_END in content


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash is not installed")
def test_bash_script_updates_existing_agents_without_template(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_repo(repo, with_template=False)

    agents = repo / "AGENTS.md"
    initial = "# User Notes\n\nKeep this line.\n\n"
    agents.write_text(initial, encoding="utf-8")

    result = _run_bash_update(repo)

    assert result.returncode == 0, result.stderr
    content = agents.read_text(encoding="utf-8")
    assert content[: content.index(BLOCK_START)] == initial
    assert BLOCK_START in content
    assert BLOCK_END in content


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash is not installed")
def test_bash_script_replaces_existing_block_without_touching_surrounding_content(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_repo(repo)

    prefix = "# User Notes\n\nalpha\n\n"
    suffix = "\n\nomega"
    agents = repo / "AGENTS.md"
    agents.write_text(
        prefix + BLOCK_START + "\nold block\n" + BLOCK_END + suffix,
        encoding="utf-8",
    )

    result = _run_bash_update(repo)

    assert result.returncode == 0, result.stderr
    content = agents.read_text(encoding="utf-8")
    start = content.index(BLOCK_START)
    end = content.index(BLOCK_END) + len(BLOCK_END)
    assert content[:start] == prefix
    assert content[end:] == suffix
    assert "old block" not in content
    assert not content.endswith("\n")


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash is not installed")
def test_bash_script_does_not_pair_stale_begin_with_later_end_and_is_repeat_safe(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_repo(repo)

    initial = (
        "# User Notes\n\n"
        + BLOCK_START
        + "\nuser draft stays here\n\n"
        + BLOCK_START
        + "\nold block\n"
        + BLOCK_END
        + "\n\nomega"
    )
    agents = repo / "AGENTS.md"
    agents.write_text(initial, encoding="utf-8")

    result1 = _run_bash_update(repo)
    assert result1.returncode == 0, result1.stderr
    content1 = agents.read_text(encoding="utf-8")
    assert content1.startswith(initial)
    assert content1.count(BLOCK_START) == 3
    assert content1.count(BLOCK_END) == 2
    assert content1.endswith(BLOCK_END)

    result2 = _run_bash_update(repo)
    assert result2.returncode == 0, result2.stderr
    content2 = agents.read_text(encoding="utf-8")
    assert content2 == content1


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash is not installed")
def test_bash_script_uses_literal_duplicate_matching_for_plan_values() -> None:
    content = BASH_SCRIPT.read_text(encoding="utf-8")
    assert 'grep -Fq -- "$tech_stack" "$target_file"' in content
    assert 'grep -Fq -- "$NEW_DB" "$target_file"' in content


def test_powershell_script_replaces_existing_managed_block_only_and_preserves_surroundings(
    tmp_path: Path,
) -> None:
    if POWERSHELL is None:
        pytest.skip("PowerShell is not installed")

    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_repo(repo)

    agents = repo / "AGENTS.md"
    prefix = "# User Notes\r\n\r\nalpha\r\n\r\n"
    suffix = "\r\n\r\nomega\r\n\r\n"
    agents.write_bytes(
        (
            prefix
            + BLOCK_START
            + "\r\nold block\r\n"
            + BLOCK_END
            + suffix
        ).encode("utf-8")
    )

    result = _run_powershell_update(repo)

    assert result.returncode == 0, result.stderr
    content = _read_utf8_without_bom(agents)
    start = content.index(BLOCK_START)
    end = content.index(BLOCK_END) + len(BLOCK_END)
    assert content[:start] == prefix
    assert content[end:] == suffix
    assert content.count(BLOCK_START) == 1
    assert content.count(BLOCK_END) == 1
    assert "old block" not in content


def test_powershell_script_does_not_pair_stale_begin_with_later_end_and_is_repeat_safe(
    tmp_path: Path,
) -> None:
    if POWERSHELL is None:
        pytest.skip("PowerShell is not installed")

    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_repo(repo)

    initial = (
        "# User Notes\r\n\r\n"
        + BLOCK_START
        + "\r\nuser draft stays here\r\n\r\n"
        + BLOCK_START
        + "\r\nold block\r\n"
        + BLOCK_END
        + "\r\n\r\nomega"
    )
    agents = repo / "AGENTS.md"
    agents.write_bytes(initial.encode("utf-8"))

    result1 = _run_powershell_update(repo)
    assert result1.returncode == 0, result1.stderr
    content1 = _read_utf8_without_bom(agents)
    assert content1.startswith(initial)
    assert content1.count(BLOCK_START) == 3
    assert content1.count(BLOCK_END) == 2
    assert content1.endswith(BLOCK_END)

    result2 = _run_powershell_update(repo)
    assert result2.returncode == 0, result2.stderr
    content2 = _read_utf8_without_bom(agents)
    assert content2 == content1


def test_powershell_script_updates_existing_agents_without_template(
    tmp_path: Path,
) -> None:
    if POWERSHELL is None:
        pytest.skip("PowerShell is not installed")

    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_repo(repo, with_template=False)

    agents = repo / "AGENTS.md"
    initial = "# User Notes\r\n\r\nKeep this line.\r\n\r\n"
    agents.write_bytes(initial.encode("utf-8"))

    result = _run_powershell_update(repo)

    assert result.returncode == 0, result.stderr
    content = _read_utf8_without_bom(agents)
    assert content[: content.index(BLOCK_START)] == initial
    assert BLOCK_START in content
    assert BLOCK_END in content


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash is not installed")
def test_bash_script_updates_existing_non_agents_file_with_managed_guidance(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_repo(repo)

    claude = repo / "CLAUDE.md"
    initial = "# User CLAUDE\n\nCustom note.\n"
    claude.write_text(initial, encoding="utf-8")

    result = _run_bash_update(repo, "claude")

    assert result.returncode == 0, result.stderr
    content = claude.read_text(encoding="utf-8")
    assert content.startswith(initial)
    assert BLOCK_START in content
    assert "## Active Technologies" in content
    assert "Python 3.13" in content
    assert "Typer" in content
    _assert_managed_block_is_compact_always_on_context(content)


def test_powershell_script_updates_existing_non_agents_file_with_managed_guidance(
    tmp_path: Path,
) -> None:
    if POWERSHELL is None:
        pytest.skip("PowerShell is not installed")

    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_repo(repo)

    claude = repo / "CLAUDE.md"
    initial = "# User CLAUDE\r\n\r\nCustom note.\r\n"
    claude.write_bytes(initial.encode("utf-8"))

    result = _run_powershell_update(repo, "claude")

    assert result.returncode == 0, result.stderr
    content = _read_utf8_without_bom(claude)
    assert _normalize_newlines(content).startswith(_normalize_newlines(initial))
    assert BLOCK_START in content
    assert "## Active Technologies" in content
    assert "Python 3.13 + Typer" in content
    _assert_managed_block_is_compact_always_on_context(content)


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash is not installed")
def test_bash_script_updates_agy_root_agents_file(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_repo(repo)

    result = _run_bash_update(repo, "agy")

    assert result.returncode == 0, result.stderr
    assert (repo / "AGENTS.md").exists()
    assert not (repo / ".agent" / "rules" / "specify-rules.md").exists()


def test_powershell_script_updates_agy_root_agents_file(
    tmp_path: Path,
) -> None:
    if POWERSHELL is None:
        pytest.skip("PowerShell is not installed")

    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_repo(repo)

    result = _run_powershell_update(repo, "agy")

    assert result.returncode == 0, result.stderr
    assert (repo / "AGENTS.md").exists()
    assert not (repo / ".agent" / "rules" / "specify-rules.md").exists()


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash is not installed")
def test_bash_script_updates_vibe_root_agents_file(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_repo(repo)

    result = _run_bash_update(repo, "vibe")

    assert result.returncode == 0, result.stderr
    assert (repo / "AGENTS.md").exists()
    assert BLOCK_START in (repo / "AGENTS.md").read_text(encoding="utf-8")
    assert not (repo / ".vibe" / "agents" / "specify-agents.md").exists()


def test_powershell_script_updates_vibe_root_agents_file(
    tmp_path: Path,
) -> None:
    if POWERSHELL is None:
        pytest.skip("PowerShell is not installed")

    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_repo(repo)

    result = _run_powershell_update(repo, "vibe")

    assert result.returncode == 0, result.stderr
    assert (repo / "AGENTS.md").exists()
    assert BLOCK_START in _read_utf8_without_bom(repo / "AGENTS.md")
    assert not (repo / ".vibe" / "agents" / "specify-agents.md").exists()


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash is not installed")
def test_bash_update_all_migrates_legacy_vibe_file_to_root_agents(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_repo(repo)

    legacy_vibe = repo / ".vibe" / "agents" / "specify-agents.md"
    legacy_vibe.parent.mkdir(parents=True)
    legacy_content = "# Legacy Vibe\n\nKeep this file.\n"
    legacy_vibe.write_text(legacy_content, encoding="utf-8")

    result = _run_bash_update(repo, "")

    assert result.returncode == 0, result.stderr
    agents = repo / "AGENTS.md"
    assert agents.exists()
    assert BLOCK_START in agents.read_text(encoding="utf-8")
    assert not (repo / "CLAUDE.md").exists()
    assert legacy_vibe.read_text(encoding="utf-8") == legacy_content


def test_powershell_update_all_migrates_legacy_vibe_file_to_root_agents(
    tmp_path: Path,
) -> None:
    if POWERSHELL is None:
        pytest.skip("PowerShell is not installed")

    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_repo(repo)

    legacy_vibe = repo / ".vibe" / "agents" / "specify-agents.md"
    legacy_vibe.parent.mkdir(parents=True)
    legacy_content = "# Legacy Vibe\r\n\r\nKeep this file.\r\n"
    legacy_vibe.write_bytes(legacy_content.encode("utf-8"))

    result = _run_powershell_update(repo, "")

    assert result.returncode == 0, result.stderr
    agents = repo / "AGENTS.md"
    assert agents.exists()
    assert BLOCK_START in _read_utf8_without_bom(agents)
    assert not (repo / "CLAUDE.md").exists()
    assert _read_utf8_without_bom(legacy_vibe) == legacy_content


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash is not installed")
def test_bash_script_updates_trae_project_rules_file(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_repo(repo)

    result = _run_bash_update(repo, "trae")

    assert result.returncode == 0, result.stderr
    trae_rules = repo / ".trae" / "rules" / "project_rules.md"
    assert trae_rules.exists()
    assert BLOCK_START in trae_rules.read_text(encoding="utf-8")
    assert not (repo / ".trae" / "rules" / "AGENTS.md").exists()


def test_powershell_script_updates_trae_project_rules_file(
    tmp_path: Path,
) -> None:
    if POWERSHELL is None:
        pytest.skip("PowerShell is not installed")

    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_repo(repo)

    result = _run_powershell_update(repo, "trae")

    assert result.returncode == 0, result.stderr
    trae_rules = repo / ".trae" / "rules" / "project_rules.md"
    assert trae_rules.exists()
    assert BLOCK_START in _read_utf8_without_bom(trae_rules)
    assert not (repo / ".trae" / "rules" / "AGENTS.md").exists()
