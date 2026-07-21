import json
import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import time

from typer.testing import CliRunner

import specify_cli
import specify_cli.lint as specify_lint
from specify_cli import project_cognition_runtime
from specify_cli.launcher import (
    load_project_cognition_launcher,
    render_project_launcher_placeholders,
)


def test_project_cognition_binary_name_matches_platform(monkeypatch):
    monkeypatch.setattr(project_cognition_runtime.platform, "system", lambda: "Windows")
    monkeypatch.setattr(project_cognition_runtime.platform, "machine", lambda: "AMD64")

    assert project_cognition_runtime.binary_filename() == "project-cognition-windows-amd64.exe"


def test_project_cognition_runtime_info_uses_machine_readable_version_command(
    monkeypatch, tmp_path: Path
):
    binary = tmp_path / "project-cognition"
    binary.write_text("binary", encoding="utf-8")
    calls: list[list[str]] = []

    class Result:
        returncode = 0
        stdout = json.dumps(
            {
                "version": "v1.2.3",
                "runtime_protocol": "project-cognition.v2",
                "schema_version": 5,
                "source_revision": "abc123",
                "dirty": False,
            }
        )
        stderr = ""

    def fake_run(command, **kwargs):
        calls.append([str(part) for part in command])
        return Result()

    monkeypatch.setattr(project_cognition_runtime.subprocess, "run", fake_run)

    assert project_cognition_runtime._runtime_info((str(binary),)) == {
        "version": "v1.2.3",
        "runtime_protocol": "project-cognition.v2",
        "schema_version": 5,
        "source_revision": "abc123",
        "dirty": False,
    }
    assert calls == [[str(binary), "version", "--format", "json"]]


def test_project_cognition_runtime_compatibility_checks_protocol_schema_and_dirty(
    monkeypatch, tmp_path: Path
):
    binary = tmp_path / "project-cognition"
    binary.write_text("binary", encoding="utf-8")
    monkeypatch.setattr(
        project_cognition_runtime,
        "_binary_supports_required_commands",
        lambda candidate: True,
    )

    compatible = {
        "version": "v1.2.3",
        "runtime_protocol": "project-cognition.v2",
        "schema_version": 5,
        "source_revision": "abc123",
        "dirty": False,
    }
    monkeypatch.setattr(project_cognition_runtime, "_runtime_info", lambda argv: compatible)
    assert project_cognition_runtime._binary_is_compatible(binary) is True

    incompatible_protocol = {**compatible, "runtime_protocol": "project-cognition.v1"}
    monkeypatch.setattr(
        project_cognition_runtime, "_runtime_info", lambda argv: incompatible_protocol
    )
    assert project_cognition_runtime._binary_is_compatible(binary) is False

    incompatible_schema = {**compatible, "schema_version": 4}
    monkeypatch.setattr(
        project_cognition_runtime, "_runtime_info", lambda argv: incompatible_schema
    )
    assert project_cognition_runtime._binary_is_compatible(binary) is False

    dirty = {**compatible, "dirty": True}
    monkeypatch.setattr(project_cognition_runtime, "_runtime_info", lambda argv: dirty)
    assert project_cognition_runtime._binary_is_compatible(binary) is False
    assert project_cognition_runtime._binary_is_compatible(binary, allow_dirty=True) is True


def test_project_cognition_runtime_info_rejects_malformed_or_failed_output(
    monkeypatch, tmp_path: Path
):
    binary = tmp_path / "project-cognition"
    binary.write_text("binary", encoding="utf-8")

    class Result:
        returncode = 0
        stdout = "not-json"
        stderr = ""

    monkeypatch.setattr(
        project_cognition_runtime.subprocess, "run", lambda *args, **kwargs: Result()
    )
    assert project_cognition_runtime._runtime_info((str(binary),)) is None

    Result.returncode = 2
    Result.stdout = "{}"
    assert project_cognition_runtime._runtime_info((str(binary),)) is None


def test_project_cognition_source_build_replaces_empty_candidate_before_go_build(
    monkeypatch, tmp_path: Path
):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    candidate = tmp_path / ".project-cognition.candidate"
    candidate.write_text("", encoding="utf-8")

    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(command, **kwargs):
        assert not candidate.exists(), "go build must not receive the mkstemp placeholder"
        candidate.write_text("built runtime", encoding="utf-8")
        return Result()

    monkeypatch.setattr(project_cognition_runtime.shutil, "which", lambda command: "go")
    monkeypatch.setattr(project_cognition_runtime.subprocess, "run", fake_run)
    monkeypatch.setattr(project_cognition_runtime.platform, "system", lambda: "Windows")

    assert project_cognition_runtime._build_from_source(source_dir, candidate) == candidate
    assert candidate.read_text(encoding="utf-8") == "built runtime"


def test_ensure_project_cognition_binary_downloads_release_asset(monkeypatch, tmp_path: Path):
    downloads: list[tuple[str, Path]] = []

    monkeypatch.setattr(project_cognition_runtime, "cache_dir", lambda: tmp_path)
    monkeypatch.setattr(project_cognition_runtime.platform, "system", lambda: "Linux")
    monkeypatch.setattr(project_cognition_runtime.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(
        project_cognition_runtime,
        "_binary_is_compatible",
        lambda binary, allow_dirty=False: True,
        raising=False,
    )

    def fake_urlretrieve(url: str, dest: Path):
        downloads.append((url, dest))
        dest.write_text("binary", encoding="utf-8")
        return dest, None

    monkeypatch.setattr(project_cognition_runtime, "urlretrieve", fake_urlretrieve)
    monkeypatch.setattr(project_cognition_runtime.os, "chmod", lambda path, mode: None)

    binary = project_cognition_runtime.ensure_binary(version="v1.2.3")

    assert binary == tmp_path / "project-cognition"
    assert len(downloads) == 1
    assert downloads[0][0] == (
        "https://github.com/chenziyang110/spec-kit-plus/releases/download/v1.2.3/"
        "project-cognition-linux-amd64"
    )
    assert downloads[0][1].parent == tmp_path
    assert downloads[0][1].name.startswith(".project-cognition.")


def test_ensure_project_cognition_binary_serializes_concurrent_cache_publication(
    monkeypatch, tmp_path: Path
):
    downloads: list[Path] = []
    monkeypatch.setattr(project_cognition_runtime, "cache_dir", lambda: tmp_path)
    monkeypatch.setattr(project_cognition_runtime.platform, "system", lambda: "Linux")
    monkeypatch.setattr(project_cognition_runtime.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(project_cognition_runtime.os, "chmod", lambda path, mode: None)

    def fake_is_compatible(binary: Path, *, allow_dirty: bool = False) -> bool:
        return binary.exists() and binary.read_text(encoding="utf-8") == "binary"

    def fake_urlretrieve(url: str, dest: Path):
        downloads.append(dest)
        time.sleep(0.1)
        dest.write_text("binary", encoding="utf-8")
        return dest, None

    monkeypatch.setattr(project_cognition_runtime, "_binary_is_compatible", fake_is_compatible)
    monkeypatch.setattr(project_cognition_runtime, "urlretrieve", fake_urlretrieve)

    with ThreadPoolExecutor(max_workers=4) as pool:
        binaries = list(pool.map(lambda _: project_cognition_runtime.ensure_binary("v1.2.3"), range(4)))

    assert binaries == [tmp_path / "project-cognition"] * 4
    assert len(downloads) == 1


def test_ensure_project_cognition_binary_reuses_hash_bound_dirty_source_build(
    monkeypatch, tmp_path: Path
):
    source_dir = tmp_path / "source" / "project-cognition"
    source_dir.mkdir(parents=True)
    source_file = source_dir / "main.go"
    source_file.write_text("package main\n", encoding="utf-8")
    builds: list[Path] = []
    downloads: list[Path] = []

    monkeypatch.setattr(project_cognition_runtime, "cache_dir", lambda: tmp_path / "cache")
    monkeypatch.setattr(project_cognition_runtime.platform, "system", lambda: "Linux")
    monkeypatch.setattr(project_cognition_runtime.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(project_cognition_runtime.os, "chmod", lambda path, mode: None)
    monkeypatch.setattr(
        project_cognition_runtime,
        "_bundled_project_cognition_source",
        lambda: source_dir,
    )

    def fake_is_compatible(binary: Path, *, allow_dirty: bool = False) -> bool:
        return (
            binary.exists()
            and binary.read_text(encoding="utf-8") == "dirty source runtime"
            and allow_dirty
        )

    def fake_urlretrieve(url: str, dest: Path):
        downloads.append(dest)
        dest.write_text("incompatible release runtime", encoding="utf-8")
        return dest, None

    def fake_build_from_source(source: Path, dest: Path) -> Path:
        builds.append(source)
        dest.write_text("dirty source runtime", encoding="utf-8")
        return dest

    monkeypatch.setattr(project_cognition_runtime, "_binary_is_compatible", fake_is_compatible)
    monkeypatch.setattr(project_cognition_runtime, "urlretrieve", fake_urlretrieve)
    monkeypatch.setattr(project_cognition_runtime, "_build_from_source", fake_build_from_source)

    first = project_cognition_runtime.ensure_binary(version="v1.2.3")
    second = project_cognition_runtime.ensure_binary(version="v1.2.3")

    assert first == second == tmp_path / "cache" / "project-cognition"
    assert builds == [source_dir]
    assert len(downloads) == 1
    assert project_cognition_runtime._source_build_marker(first).is_file()

    monkeypatch.setattr(
        project_cognition_runtime,
        "REQUIRED_COMMANDS",
        (*project_cognition_runtime.REQUIRED_COMMANDS, "future-command"),
    )
    project_cognition_runtime.ensure_binary(version="v1.2.3")

    assert builds == [source_dir, source_dir]
    assert len(downloads) == 2

    first.write_text("tampered runtime", encoding="utf-8")
    project_cognition_runtime.ensure_binary(version="v1.2.3")

    assert builds == [source_dir, source_dir, source_dir]
    assert len(downloads) == 3

    source_file.write_text("package main\n// changed\n", encoding="utf-8")
    project_cognition_runtime.ensure_binary(version="v1.2.3")

    assert builds == [source_dir, source_dir, source_dir, source_dir]
    assert len(downloads) == 4


def test_ensure_project_cognition_binary_refreshes_cached_binary_without_required_commands(
    monkeypatch, tmp_path: Path
):
    downloads: list[tuple[str, Path]] = []

    monkeypatch.setattr(project_cognition_runtime, "cache_dir", lambda: tmp_path)
    monkeypatch.setattr(project_cognition_runtime.platform, "system", lambda: "Linux")
    monkeypatch.setattr(project_cognition_runtime.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(project_cognition_runtime.os, "chmod", lambda path, mode: None)

    cached_binary = tmp_path / "project-cognition"
    cached_binary.write_text("old runtime", encoding="utf-8")

    def fake_is_compatible(binary: Path, *, allow_dirty: bool = False) -> bool:
        return binary.read_text(encoding="utf-8") == "new runtime"

    def fake_urlretrieve(url: str, dest: Path):
        downloads.append((url, dest))
        dest.write_text("new runtime", encoding="utf-8")
        return dest, None

    monkeypatch.setattr(
        project_cognition_runtime,
        "_binary_is_compatible",
        fake_is_compatible,
        raising=False,
    )
    monkeypatch.setattr(project_cognition_runtime, "urlretrieve", fake_urlretrieve)

    binary = project_cognition_runtime.ensure_binary(version="v1.2.3")

    assert binary == cached_binary
    assert cached_binary.read_text(encoding="utf-8") == "new runtime"
    assert len(downloads) == 1
    assert downloads[0][0] == (
        "https://github.com/chenziyang110/spec-kit-plus/releases/download/v1.2.3/"
        "project-cognition-linux-amd64"
    )
    assert downloads[0][1] != cached_binary


def test_ensure_project_cognition_binary_preserves_cached_binary_when_refresh_fails(
    monkeypatch, tmp_path: Path
):
    cached_binary = tmp_path / "project-cognition"
    cached_binary.write_text("old runtime", encoding="utf-8")

    monkeypatch.setattr(project_cognition_runtime, "cache_dir", lambda: tmp_path)
    monkeypatch.setattr(project_cognition_runtime.platform, "system", lambda: "Linux")
    monkeypatch.setattr(project_cognition_runtime.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(
        project_cognition_runtime,
        "_binary_supports_required_commands",
        lambda binary: False,
    )
    monkeypatch.setattr(
        project_cognition_runtime,
        "urlretrieve",
        lambda url, dest: (_ for _ in ()).throw(OSError("release unavailable")),
    )
    monkeypatch.setattr(
        project_cognition_runtime,
        "_bundled_project_cognition_source",
        lambda: None,
    )

    try:
        project_cognition_runtime.ensure_binary(version="v1.2.3")
    except RuntimeError:
        pass
    else:
        raise AssertionError("ensure_binary unexpectedly succeeded")

    assert cached_binary.read_text(encoding="utf-8") == "old runtime"
    assert not list(tmp_path.glob(".project-cognition.*.candidate"))


def test_ensure_project_cognition_binary_builds_bundled_source_when_release_lacks_required_commands(
    monkeypatch, tmp_path: Path
):
    built: list[Path] = []
    source_dir = tmp_path / "source" / "project-cognition"
    source_dir.mkdir(parents=True)

    monkeypatch.setattr(project_cognition_runtime, "cache_dir", lambda: tmp_path)
    monkeypatch.setattr(project_cognition_runtime.platform, "system", lambda: "Linux")
    monkeypatch.setattr(project_cognition_runtime.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(project_cognition_runtime.os, "chmod", lambda path, mode: None)
    monkeypatch.setattr(
        project_cognition_runtime,
        "_bundled_project_cognition_source",
        lambda: source_dir,
        raising=False,
    )

    def fake_is_compatible(binary: Path, *, allow_dirty: bool = False) -> bool:
        return binary.read_text(encoding="utf-8") == "built runtime"

    def fake_urlretrieve(url: str, dest: Path):
        dest.write_text("release runtime", encoding="utf-8")
        return dest, None

    def fake_build_from_source(source: Path, dest: Path) -> Path:
        built.append(source)
        dest.write_text("built runtime", encoding="utf-8")
        return dest

    monkeypatch.setattr(
        project_cognition_runtime,
        "_binary_is_compatible",
        fake_is_compatible,
        raising=False,
    )
    monkeypatch.setattr(project_cognition_runtime, "urlretrieve", fake_urlretrieve)
    monkeypatch.setattr(
        project_cognition_runtime,
        "_build_from_source",
        fake_build_from_source,
        raising=False,
    )

    binary = project_cognition_runtime.ensure_binary(version="v1.2.3")

    assert binary == tmp_path / "project-cognition"
    assert binary.read_text(encoding="utf-8") == "built runtime"
    assert built == [source_dir]


def test_ensure_project_cognition_binary_builds_bundled_source_when_download_fails(
    monkeypatch, tmp_path: Path
):
    source_dir = tmp_path / "source" / "project-cognition"
    source_dir.mkdir(parents=True)

    monkeypatch.setattr(project_cognition_runtime, "cache_dir", lambda: tmp_path)
    monkeypatch.setattr(project_cognition_runtime.platform, "system", lambda: "Linux")
    monkeypatch.setattr(project_cognition_runtime.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(project_cognition_runtime.os, "chmod", lambda path, mode: None)
    monkeypatch.setattr(
        project_cognition_runtime,
        "_bundled_project_cognition_source",
        lambda: source_dir,
        raising=False,
    )
    monkeypatch.setattr(
        project_cognition_runtime,
        "_binary_is_compatible",
        lambda binary, allow_dirty=False: binary.read_text(encoding="utf-8")
        == "built runtime",
        raising=False,
    )

    def fake_urlretrieve(url: str, dest: Path):
        raise OSError("release unavailable")

    def fake_build_from_source(source: Path, dest: Path) -> Path:
        dest.write_text("built runtime", encoding="utf-8")
        return dest

    monkeypatch.setattr(project_cognition_runtime, "urlretrieve", fake_urlretrieve)
    monkeypatch.setattr(
        project_cognition_runtime,
        "_build_from_source",
        fake_build_from_source,
        raising=False,
    )

    binary = project_cognition_runtime.ensure_binary(version="v1.2.3")

    assert binary == tmp_path / "project-cognition"
    assert binary.read_text(encoding="utf-8") == "built runtime"


def test_ensure_project_cognition_binary_validates_project_cognition_bin_override(
    monkeypatch, tmp_path: Path
):
    binary = tmp_path / "old-project-cognition"
    binary.write_text("old runtime", encoding="utf-8")

    monkeypatch.setenv("PROJECT_COGNITION_BIN", str(binary))
    monkeypatch.setattr(
        project_cognition_runtime,
        "_binary_supports_required_commands",
        lambda candidate: False,
        raising=False,
    )

    try:
        project_cognition_runtime.ensure_binary(version="v1.2.3")
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError("ensure_binary accepted unsupported PROJECT_COGNITION_BIN")

    assert "PROJECT_COGNITION_BIN" in message
    assert "lexicon --mode" in message


def test_write_project_cognition_launcher_records_downloaded_binary(tmp_path: Path):
    binary = tmp_path / ".specify" / "bin" / "project-cognition"
    binary.parent.mkdir(parents=True)
    binary.write_text("binary", encoding="utf-8")

    config_path = project_cognition_runtime.write_project_launcher_config(tmp_path, binary)

    assert config_path == tmp_path / ".specify" / "config.json"
    launcher = load_project_cognition_launcher(tmp_path)
    assert launcher is not None
    assert launcher.argv == (str(binary),)


def test_project_cognition_placeholder_uses_persisted_binary(tmp_path: Path):
    binary = tmp_path / ".specify" / "bin" / "project-cognition"
    binary.parent.mkdir(parents=True)
    binary.write_text("binary", encoding="utf-8")
    project_cognition_runtime.write_project_launcher_config(tmp_path, binary)

    rendered = render_project_launcher_placeholders(
        tmp_path,
        "{{specify-subcmd:project-cognition status --format json}}",
    )

    assert rendered == f"{binary} status --format json"


def test_project_cognition_required_commands_include_compass_and_expand():
    assert "build-from-scan" in project_cognition_runtime.REQUIRED_COMMANDS
    assert "init-empty" in project_cognition_runtime.REQUIRED_COMMANDS
    assert "repair-status" in project_cognition_runtime.REQUIRED_COMMANDS
    assert "generate-ignore" in project_cognition_runtime.REQUIRED_COMMANDS
    assert "scan-set" in project_cognition_runtime.REQUIRED_COMMANDS
    assert "scan-prepare" in project_cognition_runtime.REQUIRED_COMMANDS
    assert "scan-lease" in project_cognition_runtime.REQUIRED_COMMANDS
    assert "scan-checkpoint" in project_cognition_runtime.REQUIRED_COMMANDS
    assert "scan-yield" in project_cognition_runtime.REQUIRED_COMMANDS
    assert "scan-requeue" in project_cognition_runtime.REQUIRED_COMMANDS
    assert "scan-status" in project_cognition_runtime.REQUIRED_COMMANDS
    assert "scan-accept" in project_cognition_runtime.REQUIRED_COMMANDS
    assert "changes" in project_cognition_runtime.REQUIRED_COMMANDS
    assert "closeout-plan" in project_cognition_runtime.REQUIRED_COMMANDS
    assert "semantic-intake --input" in project_cognition_runtime.REQUIRED_COMMANDS
    assert "semantic-audit-resume --input" in project_cognition_runtime.REQUIRED_COMMANDS
    assert "lexicon --mode" in project_cognition_runtime.REQUIRED_COMMANDS
    assert (
        "compass --semantic-intake-file --query-plan-file"
        in project_cognition_runtime.REQUIRED_COMMANDS
    )
    assert "expand --section" in project_cognition_runtime.REQUIRED_COMMANDS
    assert "update --payload-file --verification" in project_cognition_runtime.REQUIRED_COMMANDS
    assert "delta append --verification --generated-surface" in project_cognition_runtime.REQUIRED_COMMANDS


def test_project_cognition_install_scripts_verify_closeout_plan_flags():
    shell_script = Path("tools/project-cognition/install.sh").read_text(encoding="utf-8")
    powershell_script = Path("tools/project-cognition/install.ps1").read_text(encoding="utf-8")

    assert "closeout-plan --help" in shell_script
    assert "-workflow" in shell_script
    assert "-delta-session" in shell_script
    assert "semantic-intake --help" in shell_script
    assert "semantic-intake binary is missing required input flag" in shell_script
    assert "semantic-audit-resume --help" in shell_script
    assert "semantic-audit-resume binary is missing required input flag" in shell_script
    assert "required_command in repair-status scan-set scan-prepare scan-lease scan-checkpoint scan-yield scan-requeue scan-status scan-accept" in shell_script
    assert "scan-prepare --help" in shell_script
    for flag in (
        "-force",
        "-scan-set",
        "-max-paths",
        "-max-bytes",
        "-worker-budget-tokens",
        "-context-window-tokens",
        "-inherited-context-tokens",
        "-system-skill-tokens",
        "-reserved-output-tokens",
        "-reserved-tool-tokens",
        "-reserved-reasoning-tokens",
        "-safety-percent",
    ):
        assert flag in shell_script
    assert "scan-lease --help" in shell_script
    assert '"-worker-capacity-tokens"' in shell_script
    assert "scan-checkpoint --help" in shell_script
    assert "scan-yield --help" in shell_script
    assert "scan-requeue --help" in shell_script
    assert "scan-accept --help" in shell_script
    assert "-packet-id" in shell_script
    assert "-attempt-id" in shell_script
    assert "project-cognition --help" in shell_script
    assert 'version --format json' in shell_script
    assert 'project-cognition.v2' in shell_script
    assert '"schema_version":5' in shell_script
    assert '@("closeout-plan", "--help")' in powershell_script
    assert "-workflow" in powershell_script
    assert "-delta-session" in powershell_script
    assert '@("semantic-intake", "--help")' in powershell_script
    assert "semantic-intake binary is missing required input flag" in powershell_script
    assert '@("semantic-audit-resume", "--help")' in powershell_script
    assert "semantic-audit-resume binary is missing required input flag" in powershell_script
    assert '"repair-status", "scan-set", "scan-prepare", "scan-lease", "scan-checkpoint", "scan-yield", "scan-requeue", "scan-status", "scan-accept"' in powershell_script
    assert '@("scan-prepare", "--help")' in powershell_script
    for flag in (
        "-force",
        "-scan-set",
        "-max-paths",
        "-max-bytes",
        "-worker-budget-tokens",
        "-context-window-tokens",
        "-inherited-context-tokens",
        "-system-skill-tokens",
        "-reserved-output-tokens",
        "-reserved-tool-tokens",
        "-reserved-reasoning-tokens",
        "-safety-percent",
    ):
        assert flag in powershell_script
    assert '@("scan-lease", "--help")' in powershell_script
    assert "'-worker-capacity-tokens'" in powershell_script
    assert '@("scan-checkpoint", "--help")' in powershell_script
    assert '@("scan-yield", "--help")' in powershell_script
    assert '@("scan-requeue", "--help")' in powershell_script
    assert '@("scan-accept", "--help")' in powershell_script
    assert '@("--help")' in powershell_script
    assert '@("version", "--format", "json")' in powershell_script
    assert 'project-cognition.v2' in powershell_script
    assert '"schema_version":5' in powershell_script


def test_project_cognition_binary_support_requires_compass_and_expand(
    monkeypatch, tmp_path: Path
):
    binary = tmp_path / "project-cognition"
    binary.write_text("binary", encoding="utf-8")

    class RootHelpResult:
        stdout = (
            "Commands: status, build-from-scan, init-empty, repair-status, generate-ignore, scan-set, scan-prepare, scan-accept, changes, "
            "update, lexicon, delta\n"
        )
        stderr = ""

    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append([str(part) for part in command])
        if command[1:] == ["--help"]:
            return RootHelpResult()
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(project_cognition_runtime.subprocess, "run", fake_run)

    assert project_cognition_runtime._binary_supports_required_commands(binary) is False
    assert calls == [[str(binary), "--help"]]


def test_project_cognition_binary_support_requires_changes(monkeypatch, tmp_path: Path):
    binary = tmp_path / "project-cognition"
    binary.write_text("binary", encoding="utf-8")

    class RootHelpResult:
        stdout = (
            "Commands: status, build-from-scan, init-empty, repair-status, generate-ignore, scan-set, scan-prepare, scan-accept, update, lexicon, compass, "
            "expand, delta, closeout-plan\n"
        )
        stderr = ""

    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append([str(part) for part in command])
        if command[1:] == ["--help"]:
            return RootHelpResult()
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(project_cognition_runtime.subprocess, "run", fake_run)

    assert project_cognition_runtime._binary_supports_required_commands(binary) is False
    assert calls == [[str(binary), "--help"]]


def test_project_cognition_binary_support_requires_repair_status(
    monkeypatch, tmp_path: Path
):
    binary = tmp_path / "project-cognition"
    binary.write_text("binary", encoding="utf-8")

    class RootHelpResult:
        stdout = (
            "Commands: status, build-from-scan, init-empty, generate-ignore, "
            "scan-set, scan-prepare, scan-accept, changes, update, semantic-intake, "
            "semantic-audit-resume, lexicon, compass, expand, delta, closeout-plan\n"
        )
        stderr = ""

    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append([str(part) for part in command])
        if command[1:] == ["--help"]:
            return RootHelpResult()
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(project_cognition_runtime.subprocess, "run", fake_run)

    assert project_cognition_runtime._binary_supports_required_commands(binary) is False
    assert calls == [[str(binary), "--help"]]


def test_project_cognition_binary_support_requires_update_payload_file(monkeypatch, tmp_path: Path):
    binary = tmp_path / "project-cognition"
    binary.write_text("binary", encoding="utf-8")

    class RootHelpResult:
        stdout = (
            "Commands: status, build-from-scan, init-empty, repair-status, generate-ignore, scan-set, scan-prepare, scan-lease, scan-checkpoint, scan-yield, scan-requeue, scan-status, scan-accept, changes, update, semantic-intake, semantic-audit-resume, lexicon, compass, "
            "expand, delta, closeout-plan\n"
        )
        stderr = ""

    class UpdateHelpResult:
        stdout = "Usage of update:\n  -changed-path value\n"
        stderr = ""

    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append([str(part) for part in command])
        if command[1:] == ["--help"]:
            return RootHelpResult()
        if command[1:] == ["update", "--help"]:
            return UpdateHelpResult()
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(project_cognition_runtime.subprocess, "run", fake_run)

    assert project_cognition_runtime._binary_supports_required_commands(binary) is False
    assert calls == [[str(binary), "--help"], [str(binary), "update", "--help"]]


def test_project_cognition_binary_support_requires_closeout_plan_root_command(
    monkeypatch, tmp_path: Path
):
    binary = tmp_path / "project-cognition"
    binary.write_text("binary", encoding="utf-8")

    class RootHelpResult:
        stdout = (
            "Commands: status, build-from-scan, init-empty, repair-status, generate-ignore, scan-set, scan-prepare, scan-accept, changes, update, semantic-intake, semantic-audit-resume, lexicon, compass, "
            "expand, delta\n"
        )
        stderr = ""

    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append([str(part) for part in command])
        if command[1:] == ["--help"]:
            return RootHelpResult()
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(project_cognition_runtime.subprocess, "run", fake_run)

    assert project_cognition_runtime._binary_supports_required_commands(binary) is False
    assert calls == [[str(binary), "--help"]]


def test_project_cognition_binary_support_requires_update_verification_flag(
    monkeypatch, tmp_path: Path
):
    binary = tmp_path / "project-cognition"
    binary.write_text("binary", encoding="utf-8")

    class RootHelpResult:
        stdout = (
            "Commands: status, build-from-scan, init-empty, repair-status, generate-ignore, scan-set, scan-prepare, scan-accept, changes, update, semantic-intake, semantic-audit-resume, lexicon, compass, "
            "expand, delta, closeout-plan\n"
        )
        stderr = ""

    class UpdateHelpResult:
        stdout = "Usage of update:\n  -payload-file string\n"
        stderr = ""

    def fake_run(command, **kwargs):
        if command[1:] == ["--help"]:
            return RootHelpResult()
        if command[1:] == ["update", "--help"]:
            return UpdateHelpResult()
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(project_cognition_runtime.subprocess, "run", fake_run)

    assert project_cognition_runtime._binary_supports_required_commands(binary) is False


def test_project_cognition_binary_support_requires_lexicon_catalog_mode(
    monkeypatch, tmp_path: Path
):
    binary = tmp_path / "project-cognition"
    binary.write_text("binary", encoding="utf-8")

    class RootHelpResult:
        stdout = (
            "Commands: status, build-from-scan, init-empty, repair-status, generate-ignore, scan-set, scan-prepare, scan-accept, changes, update, semantic-intake, semantic-audit-resume, lexicon, compass, "
            "expand, delta, closeout-plan\n"
        )
        stderr = ""

    class UpdateHelpResult:
        stdout = "Usage of update:\n  -payload-file string\n  -verification value\n"
        stderr = ""

    class SemanticIntakeHelpResult:
        stdout = "Usage of semantic-intake:\n  -input string\n"
        stderr = ""

    class SemanticAuditResumeHelpResult:
        stdout = "Usage of semantic-audit-resume:\n  -input string\n"
        stderr = ""

    class LexiconHelpResult:
        stdout = "Usage of lexicon:\n  -query string\n"
        stderr = ""

    def fake_run(command, **kwargs):
        if command[1:] == ["--help"]:
            return RootHelpResult()
        if command[1:] == ["update", "--help"]:
            return UpdateHelpResult()
        if command[1:] == ["semantic-intake", "--help"]:
            return SemanticIntakeHelpResult()
        if command[1:] == ["semantic-audit-resume", "--help"]:
            return SemanticAuditResumeHelpResult()
        if command[1:] == ["lexicon", "--help"]:
            return LexiconHelpResult()
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(project_cognition_runtime.subprocess, "run", fake_run)

    assert project_cognition_runtime._binary_supports_required_commands(binary) is False


def test_project_cognition_binary_support_requires_semantic_intake_input_flag(
    monkeypatch, tmp_path: Path
):
    binary = tmp_path / "project-cognition"
    binary.write_text("binary", encoding="utf-8")

    class RootHelpResult:
        stdout = (
            "Commands: status, build-from-scan, init-empty, repair-status, generate-ignore, scan-set, scan-prepare, scan-lease, scan-checkpoint, scan-yield, scan-requeue, scan-status, scan-accept, changes, update, "
            "semantic-intake, semantic-audit-resume, lexicon, compass, expand, delta, closeout-plan\n"
        )
        stderr = ""

    class UpdateHelpResult:
        stdout = "Usage of update:\n  -payload-file string\n  -verification value\n"
        stderr = ""

    class SemanticIntakeHelpResult:
        stdout = "Usage of semantic-intake:\n  -format string\n"
        stderr = ""

    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append([str(part) for part in command])
        if command[1:] == ["--help"]:
            return RootHelpResult()
        if command[1:] == ["update", "--help"]:
            return UpdateHelpResult()
        if command[1:] == ["semantic-intake", "--help"]:
            return SemanticIntakeHelpResult()
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(project_cognition_runtime.subprocess, "run", fake_run)

    assert project_cognition_runtime._binary_supports_required_commands(binary) is False
    assert calls == [
        [str(binary), "--help"],
        [str(binary), "update", "--help"],
        [str(binary), "semantic-intake", "--help"],
    ]


def test_project_cognition_binary_support_requires_compass_precision_flags(
    monkeypatch, tmp_path: Path
):
    binary = tmp_path / "project-cognition"
    binary.write_text("binary", encoding="utf-8")

    class RootHelpResult:
        stdout = (
            "Commands: status, build-from-scan, init-empty, repair-status, generate-ignore, scan-set, scan-prepare, scan-lease, scan-checkpoint, scan-yield, scan-requeue, scan-status, scan-accept, changes, update, semantic-intake, semantic-audit-resume, lexicon, compass, "
            "expand, delta, closeout-plan\n"
        )
        stderr = ""

    class UpdateHelpResult:
        stdout = "Usage of update:\n  -payload-file string\n  -verification value\n"
        stderr = ""

    class SemanticIntakeHelpResult:
        stdout = "Usage of semantic-intake:\n  -input string\n"
        stderr = ""

    class SemanticAuditResumeHelpResult:
        stdout = "Usage of semantic-audit-resume:\n  -input string\n"
        stderr = ""

    class LexiconHelpResult:
        stdout = "Usage of lexicon:\n  -mode string\n"
        stderr = ""

    class CompassHelpResult:
        stdout = "Usage of compass:\n  -semantic-intake-file string\n"
        stderr = ""

    def fake_run(command, **kwargs):
        if command[1:] == ["--help"]:
            return RootHelpResult()
        if command[1:] == ["update", "--help"]:
            return UpdateHelpResult()
        if command[1:] == ["semantic-intake", "--help"]:
            return SemanticIntakeHelpResult()
        if command[1:] == ["semantic-audit-resume", "--help"]:
            return SemanticAuditResumeHelpResult()
        if command[1:] == ["lexicon", "--help"]:
            return LexiconHelpResult()
        if command[1:] == ["compass", "--help"]:
            return CompassHelpResult()
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(project_cognition_runtime.subprocess, "run", fake_run)

    assert project_cognition_runtime._binary_supports_required_commands(binary) is False


def test_project_cognition_binary_support_requires_expand_section_flag(
    monkeypatch, tmp_path: Path
):
    binary = tmp_path / "project-cognition"
    binary.write_text("binary", encoding="utf-8")

    class RootHelpResult:
        stdout = (
            "Commands: status, build-from-scan, init-empty, repair-status, generate-ignore, scan-set, scan-prepare, scan-accept, changes, update, semantic-intake, semantic-audit-resume, lexicon, compass, "
            "expand, delta, closeout-plan\n"
        )
        stderr = ""

    class UpdateHelpResult:
        stdout = "Usage of update:\n  -payload-file string\n  -verification value\n"
        stderr = ""

    class SemanticIntakeHelpResult:
        stdout = "Usage of semantic-intake:\n  -input string\n"
        stderr = ""

    class SemanticAuditResumeHelpResult:
        stdout = "Usage of semantic-audit-resume:\n  -input string\n"
        stderr = ""

    class LexiconHelpResult:
        stdout = "Usage of lexicon:\n  -mode string\n"
        stderr = ""

    class CompassHelpResult:
        stdout = (
            "Usage of compass:\n  -semantic-intake-file string\n  -query-plan-file string\n"
        )
        stderr = ""

    class ExpandHelpResult:
        stdout = "Usage of expand:\n  -id string\n"
        stderr = ""

    def fake_run(command, **kwargs):
        if command[1:] == ["--help"]:
            return RootHelpResult()
        if command[1:] == ["update", "--help"]:
            return UpdateHelpResult()
        if command[1:] == ["semantic-intake", "--help"]:
            return SemanticIntakeHelpResult()
        if command[1:] == ["semantic-audit-resume", "--help"]:
            return SemanticAuditResumeHelpResult()
        if command[1:] == ["lexicon", "--help"]:
            return LexiconHelpResult()
        if command[1:] == ["compass", "--help"]:
            return CompassHelpResult()
        if command[1:] == ["expand", "--help"]:
            return ExpandHelpResult()
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(project_cognition_runtime.subprocess, "run", fake_run)

    assert project_cognition_runtime._binary_supports_required_commands(binary) is False


def test_project_cognition_binary_support_requires_delta_append_verification_flag(
    monkeypatch, tmp_path: Path
):
    binary = tmp_path / "project-cognition"
    binary.write_text("binary", encoding="utf-8")

    class RootHelpResult:
        stdout = (
            "Commands: status, build-from-scan, init-empty, repair-status, generate-ignore, scan-set, scan-prepare, scan-accept, changes, update, semantic-intake, semantic-audit-resume, lexicon, compass, "
            "expand, delta, closeout-plan\n"
        )
        stderr = ""

    class UpdateHelpResult:
        stdout = "Usage of update:\n  -payload-file string\n  -verification value\n"
        stderr = ""

    class SemanticIntakeHelpResult:
        stdout = "Usage of semantic-intake:\n  -input string\n"
        stderr = ""

    class SemanticAuditResumeHelpResult:
        stdout = "Usage of semantic-audit-resume:\n  -input string\n"
        stderr = ""

    class LexiconHelpResult:
        stdout = "Usage of lexicon:\n  -mode string\n"
        stderr = ""

    class CompassHelpResult:
        stdout = (
            "Usage of compass:\n  -semantic-intake-file string\n  -query-plan-file string\n"
        )
        stderr = ""

    class ExpandHelpResult:
        stdout = "Usage of expand:\n  -section string\n"
        stderr = ""

    class DeltaAppendHelpResult:
        stdout = "Usage of delta append:\n  -changed-path value\n  -generated-surface value\n"
        stderr = ""

    def fake_run(command, **kwargs):
        if command[1:] == ["--help"]:
            return RootHelpResult()
        if command[1:] == ["update", "--help"]:
            return UpdateHelpResult()
        if command[1:] == ["semantic-intake", "--help"]:
            return SemanticIntakeHelpResult()
        if command[1:] == ["semantic-audit-resume", "--help"]:
            return SemanticAuditResumeHelpResult()
        if command[1:] == ["lexicon", "--help"]:
            return LexiconHelpResult()
        if command[1:] == ["compass", "--help"]:
            return CompassHelpResult()
        if command[1:] == ["expand", "--help"]:
            return ExpandHelpResult()
        if command[1:] == ["delta", "append", "--help"]:
            return DeltaAppendHelpResult()
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(project_cognition_runtime.subprocess, "run", fake_run)

    assert project_cognition_runtime._binary_supports_required_commands(binary) is False


def test_project_cognition_binary_support_requires_closeout_plan_delta_session_flag(
    monkeypatch, tmp_path: Path
):
    binary = tmp_path / "project-cognition"
    binary.write_text("binary", encoding="utf-8")

    class RootHelpResult:
        stdout = (
            "Commands: status, build-from-scan, init-empty, repair-status, generate-ignore, scan-set, scan-prepare, scan-lease, scan-checkpoint, scan-yield, scan-requeue, scan-status, scan-accept, changes, update, semantic-intake, semantic-audit-resume, lexicon, compass, "
            "expand, delta, closeout-plan\n"
        )
        stderr = ""

    class UpdateHelpResult:
        stdout = "Usage of update:\n  -payload-file string\n  -verification value\n"
        stderr = ""

    class SemanticIntakeHelpResult:
        stdout = "Usage of semantic-intake:\n  -input string\n"
        stderr = ""

    class SemanticAuditResumeHelpResult:
        stdout = "Usage of semantic-audit-resume:\n  -input string\n"
        stderr = ""

    class LexiconHelpResult:
        stdout = "Usage of lexicon:\n  -mode string\n"
        stderr = ""

    class CompassHelpResult:
        stdout = (
            "Usage of compass:\n  -semantic-intake-file string\n  -query-plan-file string\n"
        )
        stderr = ""

    class ExpandHelpResult:
        stdout = "Usage of expand:\n  -section string\n"
        stderr = ""

    class DeltaAppendHelpResult:
        stdout = (
            "Usage of delta append:\n  -verification value\n  -generated-surface value\n"
        )
        stderr = ""

    class CloseoutPlanHelpResult:
        stdout = "Usage of closeout-plan:\n  -workflow string\n"
        stderr = ""

    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append([str(part) for part in command])
        if command[1:] == ["--help"]:
            return RootHelpResult()
        if command[1:] == ["update", "--help"]:
            return UpdateHelpResult()
        if command[1:] == ["semantic-intake", "--help"]:
            return SemanticIntakeHelpResult()
        if command[1:] == ["semantic-audit-resume", "--help"]:
            return SemanticAuditResumeHelpResult()
        if command[1:] == ["lexicon", "--help"]:
            return LexiconHelpResult()
        if command[1:] == ["compass", "--help"]:
            return CompassHelpResult()
        if command[1:] == ["expand", "--help"]:
            return ExpandHelpResult()
        if command[1:] == ["delta", "append", "--help"]:
            return DeltaAppendHelpResult()
        if command[1:] == ["closeout-plan", "--help"]:
            return CloseoutPlanHelpResult()
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(project_cognition_runtime.subprocess, "run", fake_run)

    assert project_cognition_runtime._binary_supports_required_commands(binary) is False
    assert calls == [
        [str(binary), "--help"],
        [str(binary), "update", "--help"],
        [str(binary), "semantic-intake", "--help"],
        [str(binary), "semantic-audit-resume", "--help"],
        [str(binary), "lexicon", "--help"],
        [str(binary), "compass", "--help"],
        [str(binary), "expand", "--help"],
        [str(binary), "delta", "append", "--help"],
        [str(binary), "closeout-plan", "--help"],
    ]


def test_project_cognition_binary_support_requires_scan_workbench_flags(
    monkeypatch, tmp_path: Path
):
    binary = tmp_path / "project-cognition"
    binary.write_text("binary", encoding="utf-8")

    outputs = {
        ("--help",): (
            "build-from-scan init-empty repair-status generate-ignore scan-set scan-prepare "
            "scan-lease scan-checkpoint scan-yield scan-requeue scan-status scan-accept "
            "changes closeout-plan semantic-intake semantic-audit-resume lexicon compass "
            "expand update delta"
        ),
        ("update", "--help"): "-payload-file -verification",
        ("semantic-intake", "--help"): "-input",
        ("semantic-audit-resume", "--help"): "-input",
        ("lexicon", "--help"): "-mode",
        ("compass", "--help"): "-semantic-intake-file -query-plan-file",
        ("expand", "--help"): "-section",
        ("delta", "append", "--help"): "-verification -generated-surface",
        ("closeout-plan", "--help"): "-workflow -delta-session",
        ("scan-prepare", "--help"): "-force",
    }

    class Result:
        stderr = ""

        def __init__(self, stdout: str):
            self.stdout = stdout

    def fake_run(command, **kwargs):
        args = tuple(str(part) for part in command[1:])
        if args not in outputs:
            raise AssertionError(f"unexpected command: {command}")
        return Result(outputs[args])

    monkeypatch.setattr(project_cognition_runtime.subprocess, "run", fake_run)

    assert project_cognition_runtime._binary_supports_required_commands(binary) is False


def test_project_cognition_binary_support_requires_resumable_scan_flags(
    monkeypatch, tmp_path: Path
):
    binary = tmp_path / "project-cognition"
    binary.write_text("binary", encoding="utf-8")

    outputs = {
        ("--help",): (
            "build-from-scan init-empty repair-status generate-ignore scan-set scan-prepare "
            "scan-lease scan-checkpoint scan-yield scan-requeue scan-status scan-accept "
            "changes closeout-plan semantic-intake semantic-audit-resume lexicon compass "
            "expand update delta"
        ),
        ("update", "--help"): "-payload-file -verification",
        ("semantic-intake", "--help"): "-input",
        ("semantic-audit-resume", "--help"): "-input",
        ("lexicon", "--help"): "-mode",
        ("compass", "--help"): "-semantic-intake-file -query-plan-file",
        ("expand", "--help"): "-section",
        ("delta", "append", "--help"): "-verification -generated-surface",
        ("closeout-plan", "--help"): "-workflow -delta-session",
        ("scan-prepare", "--help"): (
            "-force -scan-set -worker-budget-tokens -context-window-tokens -max-paths"
        ),
        ("scan-lease", "--help"): "-packet-id -worker-id -worker-capacity-tokens",
        # Missing -result must keep this runtime incompatible.
        ("scan-checkpoint", "--help"): "-packet-id -attempt-id",
    }

    class Result:
        stderr = ""

        def __init__(self, stdout: str):
            self.stdout = stdout

    def fake_run(command, **kwargs):
        args = tuple(str(part) for part in command[1:])
        if args not in outputs:
            raise AssertionError(f"unexpected command: {command}")
        return Result(outputs[args])

    monkeypatch.setattr(project_cognition_runtime.subprocess, "run", fake_run)

    assert project_cognition_runtime._binary_supports_required_commands(binary) is False


def test_project_cognition_binary_support_requires_complete_scan_budget_protocol(
    monkeypatch, tmp_path: Path
):
    binary = tmp_path / "project-cognition"
    binary.write_text("binary", encoding="utf-8")

    outputs = {
        ("--help",): (
            "build-from-scan init-empty repair-status generate-ignore scan-set scan-prepare "
            "scan-lease scan-checkpoint scan-yield scan-requeue scan-status scan-accept "
            "changes closeout-plan semantic-intake semantic-audit-resume lexicon compass "
            "expand update delta"
        ),
        ("update", "--help"): "-payload-file -verification",
        ("semantic-intake", "--help"): "-input",
        ("semantic-audit-resume", "--help"): "-input",
        ("lexicon", "--help"): "-mode",
        ("compass", "--help"): "-semantic-intake-file -query-plan-file",
        ("expand", "--help"): "-section",
        ("delta", "append", "--help"): "-verification -generated-surface",
        ("closeout-plan", "--help"): "-workflow -delta-session",
        # Everything except -safety-percent: this older runtime must be rejected.
        ("scan-prepare", "--help"): (
            "-force -scan-set -max-paths -max-bytes -worker-budget-tokens "
            "-context-window-tokens -inherited-context-tokens -system-skill-tokens "
            "-reserved-output-tokens -reserved-tool-tokens -reserved-reasoning-tokens"
        ),
        ("scan-lease", "--help"): "-packet-id -worker-id -worker-capacity-tokens",
        ("scan-checkpoint", "--help"): "-packet-id -attempt-id -result",
        ("scan-yield", "--help"): "-packet-id -attempt-id",
        ("scan-requeue", "--help"): "-packet-id -attempt-id",
        ("scan-accept", "--help"): "-packet-id -attempt-id -result",
    }

    class Result:
        stderr = ""

        def __init__(self, stdout: str):
            self.stdout = stdout

    def fake_run(command, **kwargs):
        return Result(outputs[tuple(str(part) for part in command[1:])])

    monkeypatch.setattr(project_cognition_runtime.subprocess, "run", fake_run)

    assert project_cognition_runtime._binary_supports_required_commands(binary) is False


def test_project_cognition_init_empty_declined_zero_exit_is_not_greenfield(
    monkeypatch, tmp_path: Path
):
    class FakeResult:
        returncode = 0
        stdout = (
            '{"status":"declined","warnings":["project contains non-scaffold files"],'
            '"readiness":"uninitialized"}'
        )
        stderr = ""

    monkeypatch.setattr(specify_cli.subprocess, "run", lambda *args, **kwargs: FakeResult())

    init_ok, init_detail = specify_cli._run_project_cognition_init_empty(
        tmp_path, tmp_path / "project-cognition"
    )

    assert init_ok is False
    assert init_detail == "project contains non-scaffold files"


def test_project_cognition_init_empty_already_initialized_zero_exit(monkeypatch, tmp_path: Path):
    class FakeResult:
        returncode = 0
        stdout = '{"status":"ok","already_initialized":true}'
        stderr = ""

    monkeypatch.setattr(specify_cli.subprocess, "run", lambda *args, **kwargs: FakeResult())

    init_ok, init_detail = specify_cli._run_project_cognition_init_empty(
        tmp_path, tmp_path / "project-cognition"
    )

    assert init_ok is True
    assert init_detail == "already initialized"


def test_init_prefetches_project_cognition_runtime(monkeypatch, tmp_path: Path):
    binary = tmp_path / "cache" / "project-cognition"
    calls: list[str] = []

    def fake_ensure_binary():
        calls.append("ensure")
        binary.parent.mkdir(parents=True)
        binary.write_text("binary", encoding="utf-8")
        return binary

    monkeypatch.setattr(specify_lint, "ensure_binary", lambda: tmp_path / "spec-lint")
    monkeypatch.setattr("specify_cli.project_cognition_runtime.ensure_binary", fake_ensure_binary)
    monkeypatch.setattr(specify_cli, "check_tool", lambda tool, tracker=None: True)

    runner = CliRunner()
    result = runner.invoke(
        specify_cli.app,
        ["init", str(tmp_path / "project"), "--ai", "claude", "--no-git"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    assert calls == ["ensure"]
    assert load_project_cognition_launcher(tmp_path / "project").argv == (str(binary),)
    implement_skill = tmp_path / "project" / ".claude" / "skills" / "sp-implement" / "SKILL.md"
    content = implement_skill.read_text(encoding="utf-8")
    assert f"{binary} compass --intent implement" in content
    assert f"{binary} lexicon --intent implement" not in content


def test_init_runs_project_cognition_init_empty(monkeypatch, tmp_path: Path):
    binary = tmp_path / "cache" / "project-cognition"
    calls_file = tmp_path / "calls.txt"
    binary.parent.mkdir(parents=True)
    if os.name == "nt":
        binary = binary.with_suffix(".cmd")
        binary.write_text(
            "\n".join(
                [
                    "@echo off",
                    r'if not exist ".specify\config.json" exit /b 7',
                    f'echo %*>"{calls_file}"',
                    "echo {\"status\":\"ok\",\"readiness\":\"query_ready\",\"baseline_kind\":\"greenfield_empty\"}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
    else:
        binary.write_text(
            "\n".join(
                [
                    "#!/usr/bin/env python3",
                    "import json, pathlib, sys",
                    "if not (pathlib.Path.cwd() / '.specify' / 'config.json').is_file(): sys.exit(7)",
                    f"pathlib.Path({str(calls_file)!r}).write_text(' '.join(sys.argv[1:]), encoding='utf-8')",
                    "print(json.dumps({'status':'ok','readiness':'query_ready','baseline_kind':'greenfield_empty'}))",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        binary.chmod(0o755)

    def fake_ensure_binary():
        return binary

    monkeypatch.setattr(specify_lint, "ensure_binary", lambda: tmp_path / "spec-lint")
    monkeypatch.setattr("specify_cli.project_cognition_runtime.ensure_binary", fake_ensure_binary)
    monkeypatch.setattr(specify_cli, "check_tool", lambda tool, tracker=None: True)

    runner = CliRunner()
    result = runner.invoke(
        specify_cli.app,
        ["init", str(tmp_path / "project"), "--ai", "claude", "--no-git"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    assert load_project_cognition_launcher(tmp_path / "project").argv == (str(binary),)
    assert calls_file.read_text(encoding="utf-8").strip() == "init-empty --format json"


def test_init_declined_project_cognition_empty_baseline_warning(monkeypatch, tmp_path: Path):
    binary = tmp_path / "cache" / "project-cognition"
    binary.parent.mkdir(parents=True)
    if os.name == "nt":
        binary = binary.with_suffix(".cmd")
        binary.write_text(
            "\n".join(
                [
                    "@echo off",
                    'echo {"status":"declined","warnings":["project contains non-scaffold files"]}',
                ]
            )
            + "\n",
            encoding="utf-8",
        )
    else:
        binary.write_text(
            "\n".join(
                [
                    "#!/usr/bin/env python3",
                    "import json",
                    "print(json.dumps({'status':'declined','warnings':['project contains non-scaffold files']}))",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        binary.chmod(0o755)

    monkeypatch.setattr(specify_lint, "ensure_binary", lambda: tmp_path / "spec-lint")
    monkeypatch.setattr("specify_cli.project_cognition_runtime.ensure_binary", lambda: binary)
    monkeypatch.setattr(specify_cli, "check_tool", lambda tool, tracker=None: True)

    runner = CliRunner()
    result = runner.invoke(
        specify_cli.app,
        ["init", str(tmp_path / "project"), "--ai", "claude", "--no-git"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    assert "available; empty baseline skipped" in result.output
    assert "project contains non-scaffold files" in result.output
    assert "could not be auto-installed" not in result.output
    assert "Install the prebuilt release binary manually" not in result.output
    assert "install.sh | bash" not in result.output
    assert "install.ps1 | iex" not in result.output
