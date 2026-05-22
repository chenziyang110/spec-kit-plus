from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_release_workflow_uploads_project_cognition_binaries():
    content = (ROOT / ".github" / "workflows" / "release.yml").read_text(encoding="utf-8")

    assert 'build_tool "project-cognition" "tools/project-cognition"' in content
    assert '-o "../../dist/release-tools/${tool}-${goos}-${goarch}${ext}" .' in content
    assert "dist/release-tools/*" in content
    assert "gh release create" in content
    assert r"standalone \`project-cognition\` binary" in content
    assert r"prefer \`PROJECT_COGNITION_BIN\`" in content


def test_project_cognition_attach_workflow_remains_fallback_only():
    content = (ROOT / ".github" / "workflows" / "release-project-cognition.yml").read_text(encoding="utf-8")

    assert "release:" in content
    assert "types: [published]" in content
    assert "tools/project-cognition/bin/*" in content
