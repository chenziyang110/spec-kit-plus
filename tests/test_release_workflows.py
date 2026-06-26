from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_release_workflow_uploads_project_cognition_binaries():
    content = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert "workflow_dispatch:" in content
    assert "ref: ${{ github.event_name == 'workflow_dispatch' && inputs.tag || github.ref }}" in content
    assert 'build_tool "project-cognition" "tools/project-cognition"' in content
    assert '-o "../../dist/release-tools/${tool}-${goos}-${goarch}${ext}" .' in content
    assert "dist/release-tools/*" in content
    assert "Smoke-test project-cognition release binary" in content
    assert "./dist/release-tools/project-cognition-linux-amd64 semantic-intake --help" in content
    assert "./dist/release-tools/project-cognition-linux-amd64 semantic-audit-resume --help" in content
    assert "templates/examples/semantic-audit-resume" in content
    assert "./dist/release-tools/project-cognition-linux-amd64 semantic-audit-resume --input" in content
    assert "resume-validation-route-changed.json" in content
    assert "grep -q '\"semantic_audit_resume_status\": \"fresh\"'" in content
    assert "grep -q '\"semantic_audit_resume_status\": \"needs-rerun\"'" in content
    assert "grep -q -- \"-input\"" in content
    assert "PROJECT_COGNITION_VERSION=${VERSION}" in content
    assert "gh release create" in content
    assert r"standalone \`project-cognition\` binary" in content
    assert r"prefer \`PROJECT_COGNITION_BIN\`" in content
    assert r"\`semantic-audit-resume\`" in content
    assert "semantic-audit-resume example matrix" in content


def test_project_handbook_project_cognition_regression_includes_runtime_install_suite():
    content = (ROOT / "PROJECT-HANDBOOK.md").read_text(encoding="utf-8")

    assert "Focused project cognition regression:" in content
    assert "tests/test_project_cognition_runtime_install.py" in content


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


def test_project_cognition_attach_workflow_remains_fallback_only():
    content = (ROOT / ".github" / "workflows" / "release-project-cognition.yml").read_text(encoding="utf-8")

    assert "release:" in content
    assert "types: [published]" in content
    assert "tools/project-cognition/bin/*" in content
