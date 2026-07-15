from pathlib import Path

import pytest

from specify_cli.atomic_io import atomic_write_text


@pytest.mark.parametrize("escape_kind", ["final", "parent"])
def test_atomic_write_rejects_symlink_escape_without_mutating_victim(
    tmp_path: Path,
    escape_kind: str,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    victim = outside / "state.txt"
    victim.write_text("original\n", encoding="utf-8")

    try:
        if escape_kind == "final":
            destination = workspace / "state.txt"
            destination.symlink_to(victim)
        else:
            linked_parent = workspace / "linked-parent"
            linked_parent.symlink_to(outside, target_is_directory=True)
            destination = linked_parent / "state.txt"
    except (NotImplementedError, OSError) as exc:
        pytest.skip(f"symbolic links are unavailable: {exc}")

    assert destination.resolve() == victim.resolve()
    with pytest.raises(ValueError, match="(?i)symlink|escape|outside"):
        atomic_write_text(destination, "replacement\n")
    assert victim.read_text(encoding="utf-8") == "original\n"
