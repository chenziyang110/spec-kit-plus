import os
from pathlib import Path

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


def test_ensure_project_cognition_binary_downloads_release_asset(monkeypatch, tmp_path: Path):
    downloads: list[tuple[str, Path]] = []

    monkeypatch.setattr(project_cognition_runtime, "cache_dir", lambda: tmp_path)
    monkeypatch.setattr(project_cognition_runtime.platform, "system", lambda: "Linux")
    monkeypatch.setattr(project_cognition_runtime.platform, "machine", lambda: "x86_64")
    monkeypatch.setattr(
        project_cognition_runtime,
        "_binary_supports_required_commands",
        lambda binary: True,
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
    assert downloads == [
        (
            "https://github.com/chenziyang110/spec-kit-plus/releases/download/v1.2.3/project-cognition-linux-amd64",
            tmp_path / "project-cognition",
        )
    ]


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

    def fake_supports_required_commands(binary: Path) -> bool:
        return binary.read_text(encoding="utf-8") == "new runtime"

    def fake_urlretrieve(url: str, dest: Path):
        downloads.append((url, dest))
        dest.write_text("new runtime", encoding="utf-8")
        return dest, None

    monkeypatch.setattr(
        project_cognition_runtime,
        "_binary_supports_required_commands",
        fake_supports_required_commands,
        raising=False,
    )
    monkeypatch.setattr(project_cognition_runtime, "urlretrieve", fake_urlretrieve)

    binary = project_cognition_runtime.ensure_binary(version="v1.2.3")

    assert binary == cached_binary
    assert cached_binary.read_text(encoding="utf-8") == "new runtime"
    assert downloads == [
        (
            "https://github.com/chenziyang110/spec-kit-plus/releases/download/v1.2.3/project-cognition-linux-amd64",
            cached_binary,
        )
    ]


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

    def fake_supports_required_commands(binary: Path) -> bool:
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
        "_binary_supports_required_commands",
        fake_supports_required_commands,
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
        "_binary_supports_required_commands",
        lambda binary: binary.read_text(encoding="utf-8") == "built runtime",
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


def test_project_cognition_required_commands_include_init_empty():
    assert "build-from-scan" in project_cognition_runtime.REQUIRED_COMMANDS
    assert "init-empty" in project_cognition_runtime.REQUIRED_COMMANDS


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
    assert f"{binary} lexicon --intent implement" in content


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
                    "pathlib.Path(sys.argv[0]).with_name('calls.txt').write_text(' '.join(sys.argv[1:]), encoding='utf-8')",
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
    assert calls_file.read_text(encoding="utf-8").strip() == "init-empty --format json"
