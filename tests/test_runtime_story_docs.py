from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_readme_describes_sp_implement_as_leader_worker_runtime() -> None:
    content = (PROJECT_ROOT / "README.md").read_text(encoding="utf-8").lower()

    assert "sp-implement" in content
    assert "leader" in content
    assert "delegates" in content or "delegated" in content
    assert "join point" in content
    assert "blocker" in content
    assert "retry" in content
