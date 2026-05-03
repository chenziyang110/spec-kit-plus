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
    return subprocess.run(
        [POWERSHELL, "-NoProfile", "-File", str(POWERSHELL_SCRIPT), "-AgentType", agent_type],
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


def _assert_managed_block_has_stable_subagent_routing(content: str) -> None:
    lower = content.lower()

    assert "## workflow activation discipline" in lower
    assert "1% chance" in lower
    assert "before any response or action" in lower
    assert "clarifying question" in lower
    assert "file read" in lower
    assert "## delegated execution defaults" in lower
    assert "native subagents" in lower
    assert "validated `workertaskpacket`" in lower
    assert "raw task text" in lower
    assert "structured handoff" in lower
    assert "`sp-teams` only" in lower


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
    assert "PROJECT-HANDBOOK.md" in content
    assert ".specify/project-map/" in content
    assert "## Active Technologies" in content
    assert "Python 3.13" in content
    assert "Typer" in content
    assert "## Workflow Routing" in content
    assert "sp-fast" in content
    assert "## Artifact Priority" in content
    assert "workflow-state.md" in content
    assert "Planning Handoff" in content
    assert "## Map Maintenance" in content
    assert ".specify/project-map/index/status.json" in content
    _assert_managed_block_has_stable_subagent_routing(content)


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
    assert "PROJECT-HANDBOOK.md" in content
    assert ".specify/project-map/" in content
    assert "## Active Technologies" in content
    assert "Python 3.13 + Typer" in content
    assert "## Workflow Routing" in content
    assert "sp-fast" in content
    assert "## Artifact Priority" in content
    assert "workflow-state.md" in content
    assert "Planning Handoff" in content
    assert "## Map Maintenance" in content
    assert ".specify/project-map/index/status.json" in content
    _assert_managed_block_has_stable_subagent_routing(content)


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
