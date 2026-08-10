from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "scripts" / "release-note-commits.sh"
WORKFLOW_PATHS = [
    ROOT / ".github" / "workflows" / "release-trigger.yml",
    ROOT / ".github" / "workflows" / "release.yml",
]


def _bash_executable() -> str:
    """Prefer Git Bash over the Windows WSL launcher when running locally."""

    if os.name != "nt":
        return shutil.which("bash") or "bash"

    git = shutil.which("git")
    if git:
        git_dir = Path(git).resolve().parent
        for candidate in (
            git_dir / "bash.exe",
            git_dir.parent / "bin" / "bash.exe",
            git_dir.parent / "usr" / "bin" / "bash.exe",
        ):
            if candidate.is_file():
                return str(candidate)

    return shutil.which("bash") or "bash"


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _commit(repo: Path, filename: str, content: str, message: str) -> None:
    path = repo / filename
    path.write_text(content, encoding="utf-8")
    _git(repo, "add", filename)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "Test User",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test User",
        "GIT_COMMITTER_EMAIL": "test@example.com",
    }
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )


def _init_release_history(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "branch", "-M", "main")

    _commit(repo, "history.txt", "base\n", "docs: seed history")
    _git(repo, "tag", "v0.6.16")

    _commit(repo, "history.txt", "feature\n", "feat: add release-note filtering")
    _commit(repo, "version.txt", "0.6.17\n", "chore: bump version to 0.6.17")
    _commit(repo, "fix.txt", "fix\n", "fix: keep real product fixes in release notes")
    _commit(
        repo,
        "dev-version.txt",
        "0.6.18.dev0\n",
        "chore: begin 0.6.18.dev0 development",
    )
    _commit(repo, "release-pr.txt", "merge\n", "chore: release v0.6.17 (#96)")
    _commit(
        repo,
        "release-pr-no-v.txt",
        "merge without v prefix\n",
        "chore: release 0.6.17, begin 0.6.18.dev0 development (#97)",
    )

    return repo


def test_release_note_helper_filters_release_bookkeeping_commits(
    tmp_path: Path,
) -> None:
    assert HELPER.exists(), (
        "Missing scripts/release-note-commits.sh. "
        "Add a shared helper so release-trigger.yml and release.yml can filter "
        "bookkeeping commits consistently."
    )

    repo = _init_release_history(tmp_path)
    result = subprocess.run(
        [_bash_executable(), str(HELPER), "v0.6.16..HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        encoding="utf-8",
    )
    commits = [line.strip() for line in result.stdout.splitlines() if line.strip()]

    assert commits == [
        "- fix: keep real product fixes in release notes",
        "- feat: add release-note filtering",
    ]


def test_release_workflows_call_shared_release_note_helper() -> None:
    assert HELPER.exists(), (
        "Missing scripts/release-note-commits.sh. "
        "Both release workflows should shell out to one shared helper to avoid "
        "release-note filtering drift."
    )

    expected = "scripts/release-note-commits.sh"
    for path in WORKFLOW_PATHS:
        content = path.read_text(encoding="utf-8")
        assert expected in content, f"{path} does not call {expected}"
