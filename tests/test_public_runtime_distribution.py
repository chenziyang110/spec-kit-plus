"""The public artifact repository is separate from private CLI source."""

from pathlib import Path

import pytest

from specify_cli import launcher, specify_runtime as runtime


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_REPO = "chenziyang110/spec-kit-plus-releases"


@pytest.mark.parametrize("version,path", [("latest", "latest/download"), ("v0.6.24", "download/v0.6.24")])
def test_runtime_downloads_use_public_repository(monkeypatch, version, path):
    monkeypatch.setattr(runtime, "binary_filename", lambda: "specify-runtime-windows-amd64.exe")
    monkeypatch.delenv("SPECIFY_RUNTIME_DOWNLOAD_MIRRORS", raising=False)
    expected = f"https://github.com/{PUBLIC_REPO}/releases/{path}/specify-runtime-windows-amd64.exe"
    assert runtime.github_download_url(version) == expected
    assert runtime.download_urls(version) == [expected]


def test_cli_source_repository_is_not_retargeted_to_binary_distribution():
    assert launcher.SPECIFY_SOURCE_REPOSITORY == "git+https://github.com/chenziyang110/spec-kit-plus.git"
    assert runtime.REPO == PUBLIC_REPO


@pytest.mark.parametrize("name", ["install.sh", "install.ps1"])
def test_standalone_installers_share_public_origin_without_implicit_mirrors(name):
    script = (ROOT / "tools/specify-runtime" / name).read_text(encoding="utf-8")
    assert PUBLIC_REPO in script
    assert "SPECIFY_RUNTIME_REPO" in script
    assert "SPECIFY_RUNTIME_DOWNLOAD_MIRRORS" in script
    assert "mirror.ghproxy.com" not in script
    assert "ghproxy.net" not in script
    assert "gh-proxy.com" not in script
    assert "gitdl.cn" not in script


def test_public_readme_is_a_distribution_document_not_a_source_export():
    readme = (ROOT / "templates/runtime-distribution/README.md").read_text(encoding="utf-8")
    assert PUBLIC_REPO in readme
    assert "SHA256SUMS" in readme
    assert "source code" in readme.lower()
    assert "git+" not in readme
    assert "raw.githubusercontent.com/chenziyang110/spec-kit-plus/" not in readme
