from pathlib import Path


def test_sync_ecc_to_codex_shell_wrapper_exists_and_routes_to_omx_setup():
    script = Path("scripts/sync-ecc-to-codex.sh")
    assert script.exists()

    content = script.read_text(encoding="utf-8")
    assert "omx setup" in content
    assert "dist/cli/index.js" in content
    assert "--dry-run" in content


def test_sync_ecc_to_codex_powershell_wrapper_exists_and_routes_to_omx_setup():
    script = Path("scripts/powershell/sync-ecc-to-codex.ps1")
    assert script.exists()

    content = script.read_text(encoding="utf-8")
    assert "omx setup" in content
    assert "dist\\cli\\index.js" in content or "dist/cli/index.js" in content
    assert "-DryRun" in content


def test_readme_documents_how_to_refresh_codex_config_after_mcp_install():
    readme = Path("README.md").read_text(encoding="utf-8")

    assert 'pip install "specify-cli[mcp]"' in readme
    assert "scripts/sync-ecc-to-codex.sh" in readme
    assert "scripts/powershell/sync-ecc-to-codex.ps1" in readme
