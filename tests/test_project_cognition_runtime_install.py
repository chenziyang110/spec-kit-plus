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
    assert "generate-ignore" in project_cognition_runtime.REQUIRED_COMMANDS
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
    assert '@("closeout-plan", "--help")' in powershell_script
    assert "-workflow" in powershell_script
    assert "-delta-session" in powershell_script
    assert '@("semantic-intake", "--help")' in powershell_script
    assert "semantic-intake binary is missing required input flag" in powershell_script
    assert '@("semantic-audit-resume", "--help")' in powershell_script
    assert "semantic-audit-resume binary is missing required input flag" in powershell_script


def test_project_cognition_binary_support_requires_compass_and_expand(
    monkeypatch, tmp_path: Path
):
    binary = tmp_path / "project-cognition"
    binary.write_text("binary", encoding="utf-8")

    class RootHelpResult:
        stdout = (
            "Commands: status, build-from-scan, init-empty, generate-ignore, changes, "
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
            "Commands: status, build-from-scan, init-empty, generate-ignore, update, lexicon, compass, "
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


def test_project_cognition_binary_support_requires_update_payload_file(monkeypatch, tmp_path: Path):
    binary = tmp_path / "project-cognition"
    binary.write_text("binary", encoding="utf-8")

    class RootHelpResult:
        stdout = (
            "Commands: status, build-from-scan, init-empty, generate-ignore, changes, update, semantic-intake, semantic-audit-resume, lexicon, compass, "
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
            "Commands: status, build-from-scan, init-empty, generate-ignore, changes, update, semantic-intake, semantic-audit-resume, lexicon, compass, "
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
            "Commands: status, build-from-scan, init-empty, generate-ignore, changes, update, semantic-intake, semantic-audit-resume, lexicon, compass, "
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
            "Commands: status, build-from-scan, init-empty, generate-ignore, changes, update, semantic-intake, semantic-audit-resume, lexicon, compass, "
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
            "Commands: status, build-from-scan, init-empty, generate-ignore, changes, update, "
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
            "Commands: status, build-from-scan, init-empty, generate-ignore, changes, update, semantic-intake, semantic-audit-resume, lexicon, compass, "
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
            "Commands: status, build-from-scan, init-empty, generate-ignore, changes, update, semantic-intake, semantic-audit-resume, lexicon, compass, "
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
            "Commands: status, build-from-scan, init-empty, generate-ignore, changes, update, semantic-intake, semantic-audit-resume, lexicon, compass, "
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
            "Commands: status, build-from-scan, init-empty, generate-ignore, changes, update, semantic-intake, semantic-audit-resume, lexicon, compass, "
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
