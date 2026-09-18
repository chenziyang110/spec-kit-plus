"""Read-only diagnostic scans must report unreadable input, not skip or hang.

Probe results are isolated from the scan under test. Configuration loading,
path discovery, file reads, parsing and diagnostic assembly use real owners.
"""
from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

import pytest

from specify_cli import launcher


UNREADABLE = "unreadable-generated-guidance"
MARKER = launcher.SPECIFY_RUNTIME_UNAVAILABLE_MARKER + ":specify-runtime version"


@pytest.fixture
def project(tmp_path, monkeypatch):
    root = tmp_path.resolve() / "project 中文"
    (root / ".specify").mkdir(parents=True)
    (root / ".specify/config.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "empty-personal"))
    return root


def put(root, relative, content=b""):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content if isinstance(content, bytes) else content.encode("utf-8"))
    return path


def snapshot(root):
    result = {}
    for directory, _, names in os.walk(root, followlinks=False):
        for name in names:
            path = Path(directory) / name
            info = path.lstat()
            result[path.relative_to(root).as_posix()] = (
                info.st_mode, info.st_mtime_ns,
                path.read_bytes() if stat.S_ISREG(info.st_mode) else None,
            )
    return result


def unreadable(issues):
    return [item for item in issues if item["code"] == UNREADABLE]


@pytest.mark.parametrize("relative", [
    ".claude/commands/sp-example.md",
    ".gemini/commands/sp-example.toml",
    ".specify/scripts/powershell/common.ps1",
    ".specify/scripts/bash/create-new-feature.sh",
    ".specify/templates/commands/analyze.md",
    "AGENTS.md",
])
def test_invalid_utf8_is_reported_without_aborting_other_diagnostics(project, relative):
    put(project, relative, b"\xff\xfeinvalid")
    before = snapshot(project)
    issues = launcher.diagnose_project_runtime_compatibility(project)
    failed = unreadable(issues)
    assert len(failed) == 1
    assert relative in failed[0]["summary"]
    assert failed[0]["severity"] == "repairable-block"
    assert "missing-specify-runtime-launcher" in {item["code"] for item in issues}
    assert snapshot(project) == before


@pytest.mark.parametrize("relative", [
    ".claude/commands/sp-example.md", ".specify/scripts/powershell/common.ps1",
    ".specify/templates/commands/analyze.md",
])
def test_fifo_guidance_is_reported_without_waiting(project, relative, tmp_path):
    if not hasattr(os, "mkfifo"):
        pytest.skip("FIFO fixture requires POSIX")
    path = project / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    os.mkfifo(path)
    before = path.lstat()
    script = tmp_path / "diagnose.py"
    script.write_text('''import json, pathlib, sys, types
pkg = types.ModuleType("specify_cli")
pkg.__path__ = [sys.argv[1]]
sys.modules["specify_cli"] = pkg
from specify_cli import launcher
print(json.dumps(launcher.diagnose_project_runtime_compatibility(pathlib.Path(sys.argv[2]))))
''', encoding="utf-8")
    try:
        result = subprocess.run(
            [sys.executable, "-I", "-B", str(script), str(Path(launcher.__file__).parent), str(project)],
            capture_output=True, text=True, encoding="utf-8", timeout=3,
            stdin=subprocess.DEVNULL, check=False,
        )
    except subprocess.TimeoutExpired:
        pytest.fail("diagnostic scan waited for a FIFO peer")
    assert result.returncode == 0, result.stderr
    failed = unreadable(json.loads(result.stdout))
    assert len(failed) == 1 and relative in failed[0]["summary"]
    assert os.path.samestat(before, path.lstat())
    assert stat.S_ISFIFO(path.lstat().st_mode)
    assert path.lstat().st_mtime_ns == before.st_mtime_ns


@pytest.mark.parametrize("kind", ["file", "dangling", "root", "nested-directory"])
def test_linked_guidance_is_reported_without_reading_or_traversing_target(project, tmp_path, monkeypatch, kind):
    outside = tmp_path / "external"
    outside.mkdir()
    victim = put(outside, "sp-marker.md", MARKER)
    if kind == "root":
        alias, target = project / ".claude/commands", outside
    elif kind == "nested-directory":
        alias, target = project / ".claude/commands/nested", outside
    else:
        alias = project / ".claude/commands/sp-linked.md"
        target = victim if kind == "file" else outside / "missing.md"
    alias.parent.mkdir(parents=True, exist_ok=True)
    try:
        alias.symlink_to(target, target_is_directory=kind in {"root", "nested-directory"})
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"symlinks unavailable: {exc}")
    original_scandir = os.scandir
    visited = []

    def inspect(path):
        visited.append(Path(path))
        return original_scandir(path)

    monkeypatch.setattr(launcher.os, "scandir", inspect)
    before = snapshot(outside)
    visited.clear()
    issues = launcher.diagnose_project_runtime_compatibility(project)
    assert not any(p == alias or alias in p.parents or p == outside or outside in p.parents for p in visited)
    failed = unreadable(issues)
    assert len(failed) == 1 and alias.relative_to(project).as_posix() in failed[0]["summary"]
    assert "unrebound-specify-runtime-launcher" not in {item["code"] for item in issues}
    assert snapshot(outside) == before


def test_read_permission_error_is_reported_once_and_other_files_still_scanned(project, monkeypatch):
    denied = put(project, ".claude/commands/a-denied.md", "private contents")
    put(project, ".claude/commands/b-good.md", MARKER)
    original = launcher.read_local_state_text
    calls = Counter()

    def read(path, **kwargs):
        calls[Path(path)] += 1
        if Path(path) == denied:
            raise PermissionError("sensitive external path must not be echoed")
        return original(path, **kwargs)

    monkeypatch.setattr(launcher, "read_local_state_text", read)
    issues = launcher.diagnose_project_runtime_compatibility(project)
    assert len(unreadable(issues)) == 1
    assert calls[denied] == 1
    assert "unrebound-specify-runtime-launcher" in {item["code"] for item in issues}
    assert "sensitive external" not in json.dumps(issues)


@pytest.mark.parametrize("nested", [False, True])
def test_discovery_error_is_not_silently_skipped(project, monkeypatch, nested):
    root = project / ".claude/commands"
    denied = root / "nested" if nested else root
    denied.mkdir(parents=True)
    original = os.scandir

    def scan(path):
        if Path(path) == denied:
            raise PermissionError(13, "controlled scan failure", str(denied))
        return original(path)

    monkeypatch.setattr(launcher.os, "scandir", scan)
    issues = launcher.diagnose_project_runtime_compatibility(project)
    failed = unreadable(issues)
    assert len(failed) == 1 and denied.relative_to(project).as_posix() in failed[0]["summary"]


def test_nondirectory_guidance_root_is_reported(project):
    put(project, ".claude/commands", b"not a directory")
    failed = unreadable(launcher.diagnose_project_runtime_compatibility(project))
    assert len(failed) == 1 and ".claude/commands" in failed[0]["summary"]


def test_fixed_guidance_path_that_is_a_directory_is_reported(project):
    (project / "AGENTS.md").mkdir()
    failed = unreadable(launcher.diagnose_project_runtime_compatibility(project))
    assert len(failed) == 1 and "AGENTS.md" in failed[0]["summary"]


def bind_for_scan(project, monkeypatch):
    # Avoid executing uvx/a native runtime: this suite tests scan ownership, not compatibility probes.
    argv = ("uvx", "--from", launcher.SPECIFY_SOURCE_REPOSITORY + "@" + "a" * 40, "specify")
    spec = launcher._source_bound_specify_launcher_spec(argv)
    assert spec is not None
    launcher.write_project_specify_launcher_config(project, spec)
    monkeypatch.setattr(launcher, "project_specify_launcher_is_available", lambda *args: True)
    monkeypatch.setattr(launcher, "runtime_launcher_is_compatible", lambda *args: True)


def test_one_discovery_and_one_read_per_guidance_file_for_both_launchers(project, monkeypatch):
    bind_for_scan(project, monkeypatch)
    path = put(project, ".claude/commands/sp-two.md", "Run `specify version` and `specify-runtime version`.\n")
    helper = put(project, ".specify/scripts/powershell/common.ps1", "old helper")
    scans, reads = [], Counter()
    original_discovery = launcher._generated_guidance_files
    original_read = launcher.read_local_state_text

    def discover(*args, **kwargs):
        scans.append(1)
        return original_discovery(*args, **kwargs)

    def read(path, **kwargs):
        reads[Path(path)] += 1
        return original_read(path, **kwargs)

    monkeypatch.setattr(launcher, "_generated_guidance_files", discover)
    monkeypatch.setattr(launcher, "read_local_state_text", read)
    before = snapshot(project)
    issues = launcher.diagnose_project_runtime_compatibility(project)
    assert len(scans) == 1
    assert reads[path] == reads[helper] == 1
    assert {"unbound-generated-specify-launcher", "unbound-generated-specify-runtime-launcher"} <= {i["code"] for i in issues}
    assert snapshot(project) == before


def test_cache_is_per_call_and_does_not_hide_later_file_changes(project):
    path = put(project, ".claude/commands/sp-change.md", MARKER)
    first = launcher.diagnose_project_runtime_compatibility(project)
    path.write_text("# No runtime commands\n", encoding="utf-8")
    second = launcher.diagnose_project_runtime_compatibility(project)
    assert "unrebound-specify-runtime-launcher" in {i["code"] for i in first}
    assert "unrebound-specify-runtime-launcher" not in {i["code"] for i in second}


def test_discovery_is_sorted_and_deduplicated(project, monkeypatch):
    paths = [put(project, f".claude/commands/{name}.md", "text") for name in ("z", "b", "a")]
    monkeypatch.setattr(launcher, "GENERATED_GUIDANCE_ROOTS", (".claude/commands", ".claude/commands"))
    monkeypatch.setattr(launcher, "GENERATED_CONTEXT_FILES", (".claude/commands/a.md",))
    assert launcher._generated_guidance_files(project) == sorted(paths)


def test_missing_optional_assets_are_not_failures(project):
    issues = launcher.diagnose_project_runtime_compatibility(project)
    assert unreadable(issues) == []
    assert "missing-learning-index" in {i["code"] for i in issues}


@pytest.mark.parametrize("relative,body,detected", [
    ("AGENTS.md", MARKER, False),
    ("AGENTS.md", "<!-- SPEC-KIT:BEGIN -->\n" + MARKER + "\n<!-- SPEC-KIT:END -->", True),
    (".claude/commands/sp-front.md", "---\nnote: " + MARKER + "\n---\nBody", False),
    (".claude/commands/sp-body.md", "---\nname: demo\n---\n" + MARKER, True),
])
def test_existing_managed_block_and_frontmatter_scope_is_preserved(project, relative, body, detected):
    put(project, relative, body)
    issues = launcher.diagnose_project_runtime_compatibility(project)
    assert ("unrebound-specify-runtime-launcher" in {i["code"] for i in issues}) is detected
    assert unreadable(issues) == []


def test_file_disappearing_after_discovery_is_reported_as_incomplete(project, monkeypatch):
    path = put(project, ".claude/commands/sp-disappears.md", MARKER)
    original = launcher._generated_guidance_files

    def discover(*args, **kwargs):
        files = original(*args, **kwargs)
        path.unlink()
        return files

    monkeypatch.setattr(launcher, "_generated_guidance_files", discover)
    failed = unreadable(launcher.diagnose_project_runtime_compatibility(project))
    assert len(failed) == 1 and "sp-disappears.md" in failed[0]["summary"]
