from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_release_workflow_uploads_unified_runtime_binaries():
    content = (ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )

    assert "workflow_dispatch:" in content
    assert (
        "ref: ${{ github.event_name == 'workflow_dispatch' && inputs.tag || github.ref }}"
        in content
    )
    assert 'build_tool "specify-runtime" "tools/specify-runtime"' in content
    assert '-o "../../dist/release-tools/${tool}-${goos}-${goarch}${ext}" .' in content
    assert "dist/release-tools/*" in content
    assert "Smoke-test specify-runtime release binary" in content
    assert 'SOURCE_REVISION="$(git rev-parse HEAD)"' in content
    assert (
        "tools/specify-runtime/internal/buildinfo.SourceRevision=${SOURCE_REVISION}"
        in content
    )
    assert "tools/specify-runtime/internal/buildinfo.BuildDirty=false" in content
    assert (
        "tools/specify-runtime/internal/buildinfo.ReleaseIdentity=${identity_marker}"
        in content
    )
    assert (
        './dist/release-tools/specify-runtime-linux-amd64 --help | grep -q "cognition"'
        in content
    )
    assert (
        './dist/release-tools/specify-runtime-linux-amd64 --help | grep -q "artifact"'
        in content
    )
    assert (
        './dist/release-tools/specify-runtime-linux-amd64 --help | grep -q "workflow"'
        in content
    )
    assert (
        './dist/release-tools/specify-runtime-linux-amd64 --help | grep -q "validate"'
        in content
    )
    assert (
        'version_json="$(./dist/release-tools/specify-runtime-linux-amd64 version --format json)"'
        in content
    )
    assert ".data.cli_version == $version" in content
    assert ".data.source_revision == $revision" in content
    assert ".data.dirty == false" in content
    assert (
        "./dist/release-tools/specify-runtime-linux-amd64 artifact catalog --format json | grep -q '\"quick-status\"'"
        in content
    )
    assert (
        "./dist/release-tools/specify-runtime-linux-amd64 artifact catalog --format json | grep -q '\"plan-contract\"'"
        in content
    )
    assert "workflow --help 2>&1" in content
    assert (
        "show enter next complete-stage transition reopen block resolve closeout"
        in content
    )
    assert 'cognition scan-prepare --help 2>&1 | grep -q -- "-force"' in content
    assert (
        'cognition scan-lease --help 2>&1 | grep -q -- "-worker-capacity-tokens"'
        in content
    )
    assert 'cognition scan-accept --help 2>&1 | grep -q -- "-packet-id"' in content
    assert 'semantic_audit_resume_status":"fresh' in content
    assert 'semantic_audit_resume_status":"needs-rerun' in content
    assert "SPECIFY_RUNTIME_VERSION=${VERSION}" in content
    assert r'\$env:SPECIFY_RUNTIME_VERSION="${VERSION}"' in content
    assert "gh release create" in content
    assert 'gh release upload "$VERSION" dist/release-tools/* --clobber' in content
    assert "--json isDraft,assets" in content
    assert ".size > 0" in content
    assert "--pattern 'specify-runtime-*'" in content
    assert (
        'expected_identity_marker="specify-runtime.release.v1,version=${VERSION},revision=${expected_revision},dirty=false"'
        in content
    )
    assert 'grep -aF -- "$expected_identity_marker" "$asset_path"' in content
    assert (
        'IDENTITY_MARKER="specify-runtime.release.v1,version=${VERSION},revision=${SOURCE_REVISION},dirty=false"'
        in content
    )
    assert 'grep -aF -- "$IDENTITY_MARKER" "$asset"' in content
    assert 'grep -aF -- "specify-runtime.v1" "$asset_path"' in content
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
    content = (
        ROOT / ".github" / "workflows" / "release-specify-runtime.yml"
    ).read_text(encoding="utf-8")

    assert "actions/checkout@v7" in content
    assert 'bin/specify-runtime-linux-amd64 --help | grep -q "cognition"' in content
    assert "ref: ${{ github.event.release.tag_name }}" in content
    assert "fetch-depth: 1" in content
    assert 'expected_revision="$(git rev-parse HEAD)"' in content
    assert 'SOURCE_REVISION="$(git rev-parse HEAD)"' in content
    assert "--pattern 'specify-runtime-*'" in content
    assert (
        'expected_identity_marker="specify-runtime.release.v1,version=${RELEASE_TAG},revision=${expected_revision},dirty=false"'
        in content
    )
    assert 'grep -aF -- "$expected_identity_marker" "$asset_path"' in content
    assert 'grep -aF -- "specify-runtime.v1" "$asset_path"' in content
    assert (
        "tools/specify-runtime/internal/buildinfo.SourceRevision=${SOURCE_REVISION}"
        in content
    )
    assert "tools/specify-runtime/internal/buildinfo.BuildDirty=false" in content
    assert (
        "tools/specify-runtime/internal/buildinfo.ReleaseIdentity=${IDENTITY_MARKER}"
        in content
    )
    assert (
        'bin/specify-runtime-linux-amd64 cognition scan-prepare --help 2>&1 | grep -q -- "-force"'
        in content
    )
    assert (
        'bin/specify-runtime-linux-amd64 cognition scan-lease --help 2>&1 | grep -q -- "-worker-capacity-tokens"'
        in content
    )
    assert (
        'bin/specify-runtime-linux-amd64 cognition scan-accept --help 2>&1 | grep -q -- "-packet-id"'
        in content
    )
    assert (
        'version_json="$(bin/specify-runtime-linux-amd64 version --format json)"'
        in content
    )
    assert ".data.cli_version == $version" in content
    assert ".data.source_revision == $revision" in content
    assert ".data.dirty == false" in content
    assert ".data.source_revision == $revision and .data.dirty == false" in content
    assert (
        'IDENTITY_MARKER="specify-runtime.release.v1,version=${VERSION},revision=${SOURCE_REVISION},dirty=false"'
        in content
    )
    assert 'grep -aF -- "$IDENTITY_MARKER" "$asset"' in content
    assert 'grep -aF -- "specify-runtime.v1" "$asset"' in content
    assert (
        "bin/specify-runtime-linux-amd64 artifact catalog --format json | grep -q '\"quick-status\"'"
        in content
    )
    assert (
        "bin/specify-runtime-linux-amd64 artifact catalog --format json | grep -q '\"plan-contract\"'"
        in content
    )
    assert "workflow --help 2>&1" in content
    assert (
        "show enter next complete-stage transition reopen block resolve closeout"
        in content
    )


def test_runtime_installers_require_artifact_and_workflow_capabilities() -> None:
    shell = (ROOT / "tools" / "specify-runtime" / "install.sh").read_text(
        encoding="utf-8"
    )
    powershell = (ROOT / "tools" / "specify-runtime" / "install.ps1").read_text(
        encoding="utf-8"
    )

    for capability in (
        "artifact.checklist",
        "artifact.delete",
        "artifact.list",
        "artifact.patch",
        "artifact.restore",
        "artifact.scaffold",
        "artifact.submit",
        "cognition.archive-incompatible-store",
        "cognition.run",
        "cognition.scan-packet",
        "implement.task-reopen",
        "workflow.show",
        "workflow.enter",
        "workflow.next",
        "workflow.complete-stage",
        "workflow.transition",
        "workflow.reopen",
        "workflow.block",
        "workflow.resolve",
        "workflow.closeout",
    ):
        assert capability in shell
        assert capability.replace(".", r"\.") in powershell

    assert "Downloaded binary version" in shell
    assert "Downloaded latest binary has no concrete release version" in shell
    assert "Downloaded binary reports inconsistent release provenance" in shell
    assert "Downloaded binary has invalid release provenance" in shell
    assert "Downloaded binary version" in powershell
    assert "Downloaded latest binary has no concrete release version" in powershell
    assert "Downloaded binary reports inconsistent release provenance" in powershell
    assert "Downloaded binary has invalid release provenance" in powershell


def test_release_trigger_has_token_fallback_and_dispatches_release_workflow():
    content = (ROOT / ".github" / "workflows" / "release-trigger.yml").read_text(
        encoding="utf-8"
    )

    assert "actions: write" in content
    assert "${{ secrets.RELEASE_PAT || secrets.GITHUB_TOKEN }}" in content
    assert "continue-on-error: true" in content
    assert (
        'gh workflow run release.yml --ref main -f tag="${{ steps.version.outputs.tag }}"'
        in content
    )
    assert "release artifacts are being built" in content
    assert "Release workflow is building artifacts from the tag" in content
    assert "release completed" not in content.lower()
    assert "Create a PR manually from ${{ env.branch }} to main" in content


def test_runtime_attach_workflow_remains_fallback_only():
    content = (
        ROOT / ".github" / "workflows" / "release-specify-runtime.yml"
    ).read_text(encoding="utf-8")

    assert "release:" in content
    assert "types: [published]" in content
    assert "tools/specify-runtime/bin/*" in content
    assert "Check whether runtime assets are missing or invalid" in content
    assert "steps.assets.outputs.missing == 'true'" in content
    assert "gh release view" in content
    assert 'gh release download "$RELEASE_TAG"' in content
    assert (
        'gh release upload "$RELEASE_TAG" tools/specify-runtime/bin/* --clobber'
        in content
    )
