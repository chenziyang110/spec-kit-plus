from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_release_workflow_uploads_unified_runtime_binaries():
    content = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )

    assert "workflow_dispatch:" in content
    assert "ref: ${{ github.event_name == 'workflow_dispatch' && inputs.tag || github.ref }}" in content
    assert 'build_tool "specify-runtime" "tools/specify-runtime"' in content
    assert '-o "../../dist/release-tools/${tool}-${goos}-${goarch}${ext}" .' in content
    assert "dist/release-tools/*" in content
    assert "Smoke-test specify-runtime release binary" in content
    assert 'SOURCE_REVISION="$(git rev-parse HEAD)"' in content
    assert "tools/specify-runtime/internal/buildinfo.SourceRevision=${SOURCE_REVISION}" in content
    assert "tools/specify-runtime/internal/buildinfo.BuildDirty=false" in content
    assert './dist/release-tools/specify-runtime-linux-amd64 --help | grep -q "cognition"' in content
    assert './dist/release-tools/specify-runtime-linux-amd64 --help | grep -q "artifact"' in content
    assert './dist/release-tools/specify-runtime-linux-amd64 --help | grep -q "workflow"' in content
    assert './dist/release-tools/specify-runtime-linux-amd64 --help | grep -q "validate"' in content
    assert './dist/release-tools/specify-runtime-linux-amd64 version --format json | grep -q \'"protocol_version":"specify-runtime.v1"\'' in content
    assert './dist/release-tools/specify-runtime-linux-amd64 artifact catalog --format json | grep -q \'"quick-status"\'' in content
    assert './dist/release-tools/specify-runtime-linux-amd64 artifact catalog --format json | grep -q \'"plan-contract"\'' in content
    assert "cognition scan-prepare --help 2>&1 | grep -q -- \"-force\"" in content
    assert "cognition scan-lease --help 2>&1 | grep -q -- \"-worker-capacity-tokens\"" in content
    assert "cognition scan-accept --help 2>&1 | grep -q -- \"-packet-id\"" in content
    assert "semantic_audit_resume_status\":\"fresh" in content
    assert "semantic_audit_resume_status\":\"needs-rerun" in content
    assert "SPECIFY_RUNTIME_VERSION=${VERSION}" in content
    assert r'\$env:SPECIFY_RUNTIME_VERSION="${VERSION}"' in content
    assert "gh release create" in content
    assert 'gh release upload "$VERSION" dist/release-tools/* --clobber' in content
    assert "--json isDraft,assets" in content
    assert ".size > 0" in content
    assert 'gh release edit "$VERSION" --draft=false' in content
    assert r"project-pinned \`specify-runtime\` binary" in content
    assert r"\`runtime_launcher\`" in content
    assert r"\`SPECIFY_RUNTIME_BIN\`" in content
    assert 'build_tool "project-cognition"' not in content
    assert 'build_tool "spec-lint"' not in content


def test_project_handbook_runtime_regression_includes_install_suite():
    content = (ROOT / "PROJECT-HANDBOOK.md").read_text(encoding="utf-8")

    assert "tests/test_project_cognition_runtime_install.py" in content
    assert "tests/test_specify_runtime.py" in content


def test_runtime_fallback_release_smokes_namespaced_cognition_commands():
    content = (ROOT / ".github" / "workflows" / "release-specify-runtime.yml").read_text(
        encoding="utf-8"
    )

    assert 'bin/specify-runtime-linux-amd64 --help | grep -q "cognition"' in content
    assert 'SOURCE_REVISION="$(git rev-parse HEAD)"' in content
    assert "tools/specify-runtime/internal/buildinfo.SourceRevision=${SOURCE_REVISION}" in content
    assert "tools/specify-runtime/internal/buildinfo.BuildDirty=false" in content
    assert 'bin/specify-runtime-linux-amd64 cognition scan-prepare --help 2>&1 | grep -q -- "-force"' in content
    assert 'bin/specify-runtime-linux-amd64 cognition scan-lease --help 2>&1 | grep -q -- "-worker-capacity-tokens"' in content
    assert 'bin/specify-runtime-linux-amd64 cognition scan-accept --help 2>&1 | grep -q -- "-packet-id"' in content
    assert 'bin/specify-runtime-linux-amd64 version --format json | grep -q \'"protocol_version":"specify-runtime.v1"\'' in content
    assert 'bin/specify-runtime-linux-amd64 artifact catalog --format json | grep -q \'"quick-status"\'' in content
    assert 'bin/specify-runtime-linux-amd64 artifact catalog --format json | grep -q \'"plan-contract"\'' in content


def test_runtime_installers_require_artifact_and_workflow_capabilities() -> None:
    shell = (ROOT / "tools" / "specify-runtime" / "install.sh").read_text(
        encoding="utf-8"
    )
    powershell = (ROOT / "tools" / "specify-runtime" / "install.ps1").read_text(
        encoding="utf-8"
    )

    for capability in ("artifact.scaffold", "artifact.submit", "workflow.transition"):
        assert capability in shell
        assert capability.replace(".", r"\.") in powershell


def test_release_trigger_has_token_fallback_and_dispatches_release_workflow():
    content = (ROOT / ".github" / "workflows" / "release-trigger.yml").read_text(encoding="utf-8")

    assert "actions: write" in content
    assert "${{ secrets.RELEASE_PAT || secrets.GITHUB_TOKEN }}" in content
    assert "continue-on-error: true" in content
    assert 'gh workflow run release.yml --ref main -f tag="${{ steps.version.outputs.tag }}"' in content
    assert "release artifacts are being built" in content
    assert "Release workflow is building artifacts from the tag" in content
    assert "release completed" not in content.lower()
    assert "Create a PR manually from ${{ env.branch }} to main" in content


def test_runtime_attach_workflow_remains_fallback_only():
    content = (ROOT / ".github" / "workflows" / "release-specify-runtime.yml").read_text(
        encoding="utf-8"
    )

    assert "release:" in content
    assert "types: [published]" in content
    assert "tools/specify-runtime/bin/*" in content
