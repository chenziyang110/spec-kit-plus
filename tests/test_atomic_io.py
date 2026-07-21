from pathlib import Path
from threading import Event, Thread

import pytest

from specify_cli.atomic_io import atomic_write_text, interprocess_lock


def test_interprocess_lock_waits_for_competing_holder(tmp_path: Path) -> None:
    lock_path = tmp_path / "state.lock"
    first_entered = Event()
    release_first = Event()
    second_entered = Event()

    def hold_first() -> None:
        with interprocess_lock(lock_path):
            first_entered.set()
            assert release_first.wait(5)

    def enter_second() -> None:
        assert first_entered.wait(5)
        with interprocess_lock(lock_path):
            second_entered.set()

    first = Thread(target=hold_first)
    second = Thread(target=enter_second)
    first.start()
    second.start()
    assert first_entered.wait(5)
    assert not second_entered.wait(0.2)
    release_first.set()
    first.join(5)
    second.join(5)

    assert not first.is_alive()
    assert not second.is_alive()
    assert second_entered.is_set()


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
