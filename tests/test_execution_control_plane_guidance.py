from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8").lower()


def test_shared_workflow_bootstraps_use_the_execution_control_lifecycle() -> None:
    for path in (
        "templates/command-partials/common/execution-bootstrap.md",
        "templates/advanced-skills/_shared/execution-bootstrap.md",
    ):
        content = read(path)
        assert "specify-runtime execution announce" in content, path
        assert "specify-runtime execution guard" in content, path
        assert "expected-overview-revision" in content, path
        assert "expected-overview-sha256" in content, path
        assert "specify-runtime execution complete" in content, path
        assert "actual changed" in content, path
        assert "semantic resource" in content, path
        assert "product and canonical workflow git delta" in content, path
        assert "not an audit exemption" in content, path
        assert ".specify" in content and ".planning" in content, path
        assert "fast|debug|implement|quick" in content, path
        assert "artifact leases" in content and "state owners" in content, path


def test_handbooks_define_one_activity_lifecycle_and_atomic_boundaries() -> None:
    for path in ("PROJECT-HANDBOOK.md", "templates/project-handbook-template.md"):
        content = read(path)
        assert "announced -> selected -> claimed -> executing -> validating -> completed" in content, path
        assert "execution guard" in content, path
        assert "execution complete" in content, path
        assert "task state and work ownership" in content, path
        assert "changed paths" in content, path
        assert "fresh passing validation" in content, path
        assert "terminal workflow task state" in content, path
        assert "product and canonical workflow git delta" in content, path
        assert "without a second owner" in content, path


def test_python_launcher_requires_the_execution_control_capability() -> None:
    content = read("src/specify_cli/specify_runtime.py")
    assert '"execution.control"' in content
