from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_release_workflow_uploads_project_cognition_binaries():
    content = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert "workflow_dispatch:" in content
    assert "ref: ${{ github.event_name == 'workflow_dispatch' && inputs.tag || github.ref }}" in content
    assert 'build_tool "project-cognition" "tools/project-cognition"' in content
    assert '-o "../../dist/release-tools/${tool}-${goos}-${goarch}${ext}" .' in content
    assert "dist/release-tools/*" in content
    assert "gh release create" in content
    assert r"standalone \`project-cognition\` binary" in content
    assert r"prefer \`PROJECT_COGNITION_BIN\`" in content


def test_release_trigger_has_token_fallback_and_dispatches_release_workflow():
    content = (ROOT / ".github" / "workflows" / "release-trigger.yml").read_text(encoding="utf-8")

    assert "actions: write" in content
    assert "${{ secrets.RELEASE_PAT || secrets.GITHUB_TOKEN }}" in content
    assert 'gh workflow run release.yml --ref main -f tag="${{ steps.version.outputs.tag }}"' in content


def test_project_cognition_attach_workflow_remains_fallback_only():
    content = (ROOT / ".github" / "workflows" / "release-project-cognition.yml").read_text(encoding="utf-8")

    assert "release:" in content
    assert "types: [published]" in content
    assert "tools/project-cognition/bin/*" in content
