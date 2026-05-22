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
