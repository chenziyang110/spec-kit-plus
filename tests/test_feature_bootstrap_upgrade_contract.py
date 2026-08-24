"""Regression coverage for version-coupled feature bootstrap upgrades."""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.integrations.manifest import IntegrationManifest
from specify_cli.launcher import diagnose_project_runtime_compatibility

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BOOTSTRAP_CONTRACT = "spec-kit-feature-bootstrap-v1"


def test_manifest_treats_crlf_translation_as_unmodified(tmp_path: Path) -> None:
    relative = Path(".specify/scripts/powershell/create-new-feature.ps1")
    script = tmp_path / relative
    script.parent.mkdir(parents=True)
    script.write_bytes(b"first\nsecond\n")
    manifest = IntegrationManifest("speckit", tmp_path)
    manifest.record_existing(relative)

    script.write_bytes(b"first\r\nsecond\r\n")

    assert relative.as_posix() not in manifest.check_modified()


def test_manifest_still_detects_real_content_changes_with_crlf(tmp_path: Path) -> None:
    relative = Path(".specify/scripts/powershell/create-new-feature.ps1")
    script = tmp_path / relative
    script.parent.mkdir(parents=True)
    script.write_bytes(b"first\nsecond\n")
    manifest = IntegrationManifest("speckit", tmp_path)
    manifest.record_existing(relative)

    script.write_bytes(b"first\r\nchanged\r\n")

    assert relative.as_posix() in manifest.check_modified()


def test_manifest_treats_lf_translation_as_unmodified_when_recorded_crlf(
    tmp_path: Path,
) -> None:
    relative = Path(".specify/scripts/powershell/create-new-feature.ps1")
    script = tmp_path / relative
    script.parent.mkdir(parents=True)
    script.write_bytes(b"first\r\nsecond\r\n")
    manifest = IntegrationManifest("speckit", tmp_path)
    manifest.record_existing(relative)

    script.write_bytes(b"first\nsecond\n")

    assert relative.as_posix() not in manifest.check_modified()


def test_manifest_uninstall_accepts_eol_only_translation(tmp_path: Path) -> None:
    relative = Path(".specify/scripts/powershell/create-new-feature.ps1")
    script = tmp_path / relative
    script.parent.mkdir(parents=True)
    script.write_bytes(b"first\nsecond\n")
    manifest = IntegrationManifest("speckit", tmp_path)
    manifest.record_existing(relative)

    script.write_bytes(b"first\r\nsecond\r\n")

    removed, skipped = manifest.uninstall()
    assert removed == [script]
    assert skipped == []


@pytest.mark.parametrize(
    ("relative", "stale_content"),
    (
        (
            ".specify/scripts/powershell/create-new-feature.ps1",
            (
                "param([switch]$DryRun, [switch]$Json, "
                "[switch]$KeepCurrentBranch, [string]$ResolvedFeatureId)\n"
            ),
        ),
        (
            ".specify/scripts/bash/create-new-feature.sh",
            (
                "case \"$1\" in\n"
                "  --dry-run) ;;\n"
                "  --keep-current-branch) ;;\n"
                "  --resolved-feature-id) shift ;;\n"
                "esac\n"
            ),
        ),
    ),
)
def test_diagnose_blocks_stale_feature_bootstrap_contract(
    tmp_path: Path,
    relative: str,
    stale_content: str,
) -> None:
    script = tmp_path / relative
    script.parent.mkdir(parents=True)
    script.write_text(stale_content, encoding="utf-8")

    issues = diagnose_project_runtime_compatibility(tmp_path)

    issue = next(item for item in issues if item["code"] == "stale-feature-bootstrap-contract")
    assert issue["severity"] == "repairable-block"
    assert relative in issue["summary"]
    assert "integration repair" in issue["repair"]


@pytest.mark.parametrize(
    ("relative", "source_relative"),
    (
        (
            ".specify/scripts/powershell/create-new-feature.ps1",
            "scripts/powershell/create-new-feature.ps1",
        ),
        (
            ".specify/scripts/bash/create-new-feature.sh",
            "scripts/bash/create-new-feature.sh",
        ),
    ),
)
def test_diagnose_accepts_current_feature_bootstrap_contract(
    tmp_path: Path,
    relative: str,
    source_relative: str,
) -> None:
    script = tmp_path / relative
    script.parent.mkdir(parents=True)
    script.write_text(
        (PROJECT_ROOT / source_relative).read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    issues = diagnose_project_runtime_compatibility(tmp_path)

    assert not any(
        item["code"] == "stale-feature-bootstrap-contract" for item in issues
    )
    assert BOOTSTRAP_CONTRACT in script.read_text(encoding="utf-8")
