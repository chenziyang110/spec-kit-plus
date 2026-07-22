import json
import os
import shlex
import shutil
import subprocess
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
BASH_DIR = PROJECT_ROOT / "scripts" / "bash"
POWERSHELL_DIR = PROJECT_ROOT / "scripts" / "powershell"


@pytest.fixture
def script_repo(tmp_path: Path) -> Path:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)

    for source_dir, name in ((BASH_DIR, "bash"), (POWERSHELL_DIR, "powershell")):
        target_dir = tmp_path / "scripts" / name
        target_dir.mkdir(parents=True)
        for filename in ("common.sh", "project-cognition-freshness.sh", "setup-plan.sh") if name == "bash" else (
            "common.ps1",
            "project-cognition-freshness.ps1",
            "setup-plan.ps1",
        ):
            shutil.copy(source_dir / filename, target_dir / filename)

    templates_dir = tmp_path / ".specify" / "templates"
    templates_dir.mkdir(parents=True)
    (templates_dir / "plan-template.md").write_text("# Template plan\n", encoding="utf-8")
    return tmp_path


def _bash() -> str:
    executable = shutil.which("bash")
    if not executable:
        pytest.skip("bash is not available")
    return executable


def _pwsh() -> str:
    executable = shutil.which("pwsh") or shutil.which("powershell")
    if not executable:
        pytest.skip("PowerShell is not available")
    return executable


def _run_bash_cognition(repo: Path, dirty_scope_paths_json: str) -> subprocess.CompletedProcess[str]:
    fake = repo / ".specify" / "bin" / "project-cognition-fake.sh"
    fake.parent.mkdir(parents=True, exist_ok=True)
    fake.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "printf '%s\\n' \"$@\" > .specify/captured-args.txt\n"
        "printf '{}\\n'\n",
        encoding="utf-8",
        newline="\n",
    )
    fake.chmod(fake.stat().st_mode | 0o111)
    command = "SPECIFY_RUNTIME_BIN=.specify/bin/project-cognition-fake.sh " + shlex.join(
        [
            "scripts/bash/project-cognition-freshness.sh",
            ".",
            "mark-dirty",
            "workflow changed",
            "implement",
            ".specify/features/001-safe",
            "lane-001",
            dirty_scope_paths_json,
        ]
    )
    return subprocess.run(
        [_bash(), "-lc", command],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=os.environ,
    )


def _run_powershell_cognition(repo: Path, dirty_scope_paths_json: str) -> subprocess.CompletedProcess[str]:
    fake = repo / ".specify" / "bin" / "project-cognition-fake.ps1"
    fake.parent.mkdir(parents=True, exist_ok=True)
    fake.write_text(
        "param([Parameter(ValueFromRemainingArguments=$true)][string[]]$Args)\n"
        "$payload = ConvertTo-Json -InputObject @($Args) -Compress\n"
        "Set-Content -LiteralPath '.specify/captured-args.json' -Value $payload -Encoding utf8\n"
        "Write-Output '{}'\n",
        encoding="utf-8",
        newline="\n",
    )
    return subprocess.run(
        [
            _pwsh(),
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "scripts/powershell/project-cognition-freshness.ps1",
            "-RepoRoot",
            str(repo),
            "-Command",
            "mark-dirty",
            "-Reason",
            "workflow changed",
            "-OriginCommand",
            "implement",
            "-OriginFeatureDir",
            ".specify/features/001-safe",
            "-OriginLaneId",
            "lane-001",
            "-DirtyScopePathsJson",
            dirty_scope_paths_json,
        ],
        cwd=repo,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "SPECIFY_RUNTIME_BIN": str(fake)},
    )


@pytest.mark.parametrize(
    ("runner", "capture_name"),
    [
        (_run_bash_cognition, "captured-args.txt"),
        (_run_powershell_cognition, "captured-args.json"),
    ],
)
def test_project_cognition_wrapper_expands_dirty_scope_json(
    script_repo: Path,
    runner,
    capture_name: str,
):
    result = runner(script_repo, json.dumps(["src/a.py", "docs/with space.md"]))

    assert result.returncode == 0, result.stderr
    capture = script_repo / ".specify" / capture_name
    args = (
        json.loads(capture.read_text(encoding="utf-8-sig"))
        if capture.suffix == ".json"
        else capture.read_text(encoding="utf-8").splitlines()
    )
    assert args == [
        "cognition",
        "mark-dirty",
        "--reason",
        "workflow changed",
        "--origin-command",
        "implement",
        "--origin-feature-dir",
        ".specify/features/001-safe",
        "--origin-lane-id",
        "lane-001",
        "--scope",
        "src/a.py",
        "--scope",
        "docs/with space.md",
        "--format",
        "json",
    ]


@pytest.mark.parametrize("runner", [_run_bash_cognition, _run_powershell_cognition])
@pytest.mark.parametrize("payload", ["not-json", '{"src":"a.py"}', '["src/a.py", 7]'])
def test_project_cognition_wrapper_rejects_invalid_dirty_scope_json(
    script_repo: Path,
    runner,
    payload: str,
):
    result = runner(script_repo, payload)

    assert result.returncode != 0
    assert "dirty scope paths json" in (result.stderr + result.stdout).lower()
    assert not (script_repo / ".specify" / "captured-args.txt").exists()
    assert not (script_repo / ".specify" / "captured-args.json").exists()


def test_bash_setup_plan_creates_once_then_preserves_existing_plan(script_repo: Path):
    feature_dir = script_repo / ".specify" / "features" / "001-safe"
    first = subprocess.run(
        [
            _bash(),
            "scripts/bash/setup-plan.sh",
            "--json",
            "--feature-dir",
            ".specify/features/001-safe",
        ],
        cwd=script_repo,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert first.returncode == 0, first.stderr
    assert json.loads(first.stdout)["STATUS"] == "created"
    assert (feature_dir / "plan.md").read_text(encoding="utf-8") == "# Template plan\n"

    (feature_dir / "plan.md").write_text("# Human plan\n", encoding="utf-8")
    second = subprocess.run(
        [
            _bash(),
            "scripts/bash/setup-plan.sh",
            "--json",
            "--feature-dir",
            ".specify/features/001-safe",
        ],
        cwd=script_repo,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert second.returncode == 0, second.stderr
    assert json.loads(second.stdout)["STATUS"] == "noop"
    assert (feature_dir / "plan.md").read_text(encoding="utf-8") == "# Human plan\n"


def test_powershell_setup_plan_creates_once_then_preserves_existing_plan(script_repo: Path):
    feature_dir = script_repo / ".specify" / "features" / "001-safe"
    command = [
        _pwsh(),
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        "scripts/powershell/setup-plan.ps1",
        "-Json",
        "-FeatureDir",
        ".specify/features/001-safe",
    ]
    first = subprocess.run(command, cwd=script_repo, check=False, capture_output=True, text=True)
    assert first.returncode == 0, first.stderr
    assert json.loads(first.stdout)["STATUS"] == "created"
    assert (feature_dir / "plan.md").read_text(encoding="utf-8") == "# Template plan\n"

    (feature_dir / "plan.md").write_text("# Human plan\n", encoding="utf-8")
    second = subprocess.run(command, cwd=script_repo, check=False, capture_output=True, text=True)
    assert second.returncode == 0, second.stderr
    assert json.loads(second.stdout)["STATUS"] == "noop"
    assert (feature_dir / "plan.md").read_text(encoding="utf-8") == "# Human plan\n"
