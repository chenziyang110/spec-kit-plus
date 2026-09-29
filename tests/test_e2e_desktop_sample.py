"""Real Tk event-loop + filesystem integration tests for the disposable sample.

These tests are widget-driven, not evidence of a model's visual perception.
Set SPECIFY_E2E_REQUIRE_DESKTOP=1 under Xvfb to make absent display/Tk a failure.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import sys

import pytest

SAMPLE = Path(__file__).parent / "e2e_samples" / "desktop_rename.py"
_spec = importlib.util.spec_from_file_location("e2e_desktop_sample", SAMPLE)
assert _spec is not None and _spec.loader is not None
sample = importlib.util.module_from_spec(_spec)
sys.modules[_spec.name] = sample
try:
    _spec.loader.exec_module(sample)
except ModuleNotFoundError as exc:
    if exc.name not in {"tkinter", "_tkinter"}:
        raise
    if os.environ.get("SPECIFY_E2E_REQUIRE_DESKTOP") == "1":
        raise
    pytest.skip(f"Optional desktop sample requires Tk: {exc}", allow_module_level=True)


@pytest.fixture
def store(tmp_path):
    return sample.Store(sample.create_sandbox(tmp_path / "sandbox"))


@pytest.fixture
def client(store):
    try:
        root = sample.tk.Tk()
    except sample.tk.TclError as exc:
        if os.environ.get("SPECIFY_E2E_REQUIRE_DESKTOP") == "1":
            pytest.fail(f"Desktop checks were required but no Tk display is available: {exc}")
        pytest.skip(f"Optional Tk display unavailable: {exc}")
    app = sample.RenameClient(root, store)
    root.update()
    yield app
    app.cancel()
    root.destroy()


def click(app, widget):
    app.root.update()
    widget.event_generate("<Enter>")
    widget.event_generate("<ButtonPress-1>", x=8, y=8)
    app.root.update()
    widget.event_generate("<ButtonRelease-1>", x=8, y=8)
    app.root.update()


def enter_name(app, value):
    app.entry.delete(0, "end")
    app.entry.insert(0, value)
    app.root.update()


def readback(root):
    # Do not use the sample's Store.readback as the independent test oracle.
    return {p.name: p.read_bytes() for p in root.iterdir() if p.name != sample.MARKER}


@pytest.mark.parametrize("name,error", [
    ("", "empty"), ("   ", "whitespace"), (".", "reserved"), ("..", "reserved"),
    (sample.MARKER, "reserved"), ("a/b", "disallowed"), ("a\\b", "disallowed"),
    ("a:b", "disallowed"), ("a?b", "disallowed"), ('a"b', "disallowed"),
    ("a\x00b", "disallowed"), ("a\nb", "disallowed"),
    ("x" * (sample.LIMIT + 1), "exceeds"), ("文" * (sample.LIMIT + 1), "exceeds"),
])
def test_invalid_names_leave_both_files_unchanged(store, name, error):
    before = readback(store.root)
    with pytest.raises(sample.RenameRejected, match=error):
        store.rename(store.select("A.txt"), name)
    assert readback(store.root) == before


@pytest.mark.parametrize("name", ["B.txt", "文档.txt", "x" * (sample.LIMIT - 1), "x" * sample.LIMIT, "文" * sample.LIMIT])
def test_valid_boundary_names_through_real_tk(client, name):
    click(client, client.rename_button)
    assert client.dialog is not None
    enter_name(client, name)
    click(client, client.confirm_button)
    assert client.dialog is None
    assert client.status.get() == f"Renamed to {name}"
    assert readback(client.store.root) == {name: sample.SENTINEL, "taken.txt": sample.OCCUPIED}
    assert name in client.listbox.get(0, "end")


@pytest.mark.parametrize("event", ["delete", "rename", "replace", "modify"])
@pytest.mark.parametrize("checkpoint", ["dialog_open", "before_confirm"])
def test_external_mutation_at_distinct_checkpoints(client, event, checkpoint):
    click(client, client.rename_button)
    assert client.dialog is not None
    if checkpoint == "before_confirm":
        enter_name(client, "B.txt")
    source = client.store.root / "A.txt"
    if event == "delete":
        source.unlink()
    elif event == "rename":
        source.rename(source.with_name("externally-renamed.txt"))
    elif event == "replace":
        # Retain original inode, then create a distinct object at its stale path.
        source.rename(source.with_name("original-kept.txt"))
        source.write_bytes(b"replacement object: must not be renamed\n")
    else:
        source.write_bytes(b"content changed while dialog was open\n")
    # The independent read proves the perturbation has completed before Confirm.
    after_event = readback(client.store.root)
    if checkpoint == "dialog_open":
        enter_name(client, "B.txt")
    click(client, client.confirm_button)
    assert client.dialog is not None
    assert "Not renamed:" in client.status.get()
    expected_error = "no longer exists" if event in {"delete", "rename"} else "changed"
    assert expected_error in client.error.get()
    assert readback(client.store.root) == after_event
    assert not (client.store.root / "B.txt").exists()
    click(client, client.cancel_button)
    click(client, client.refresh_button)
    assert set(client.listbox.get(0, "end")) == set(after_event)


def test_destination_created_after_dialog_opens_is_not_overwritten(client):
    click(client, client.rename_button)
    enter_name(client, "B.txt")
    (client.store.root / "B.txt").write_bytes(b"other actor owns this destination")
    before = readback(client.store.root)
    click(client, client.confirm_button)
    assert "Destination already exists" in client.error.get()
    assert readback(client.store.root) == before


def test_original_deleted_before_entry_is_not_a_dialog_time_test(client):
    (client.store.root / "A.txt").unlink()
    click(client, client.rename_button)
    assert client.dialog is None
    assert "no longer exists" in client.status.get()
    assert readback(client.store.root) == {"taken.txt": sample.OCCUPIED}


def test_error_recovery_cancel_reopen_and_duplicate_confirmation(client):
    click(client, client.rename_button)
    enter_name(client, "x" * (sample.LIMIT + 1))
    click(client, client.confirm_button)
    assert "exceeds" in client.error.get()
    assert (client.store.root / "A.txt").read_bytes() == sample.SENTINEL
    click(client, client.cancel_button)
    assert client.dialog is None
    click(client, client.rename_button)
    enter_name(client, "B.txt")
    click(client, client.confirm_button)
    # A queued duplicate event after successful completion must have no effect.
    client.root.after_idle(client.confirm)
    client.root.update()
    assert readback(client.store.root) == {"B.txt": sample.SENTINEL, "taken.txt": sample.OCCUPIED}


def test_same_name_is_noop(client):
    before = readback(client.store.root)
    click(client, client.rename_button)
    click(client, client.confirm_button)
    assert client.status.get() == "Name unchanged"
    assert readback(client.store.root) == before


def test_symlink_selection_and_destination_are_rejected(store, tmp_path):
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"outside data")
    try:
        (store.root / "link.txt").symlink_to(outside)
    except (OSError, NotImplementedError):
        pytest.skip("This host does not permit symlink creation")
    with pytest.raises(sample.RenameRejected, match="non-symlink"):
        store.select("link.txt")
    with pytest.raises(sample.RenameRejected, match="Destination already exists"):
        store.rename(store.select("A.txt"), "link.txt")
    assert outside.read_bytes() == b"outside data"
    assert (store.root / "A.txt").read_bytes() == sample.SENTINEL


def test_sandbox_is_create_only_and_requires_marker(tmp_path):
    root = sample.create_sandbox(tmp_path / "sandbox")
    before = readback(root)
    with pytest.raises(FileExistsError):
        sample.create_sandbox(root)
    assert readback(root) == before
    (root / sample.MARKER).unlink()
    with pytest.raises(sample.RenameRejected, match="unmarked"):
        sample.Store(root)


def test_status_and_dialog_controls_are_within_visible_client_area(client):
    # Regression found by inspecting actual pixels, not the StringVar assertions.
    client.root.update()
    status_bottom = client.status_label.winfo_rooty() + client.status_label.winfo_height()
    assert client.status_label.winfo_height() > 1
    assert status_bottom < client.root.winfo_rooty() + client.root.winfo_height()
    click(client, client.rename_button)
    assert client.dialog is not None
    for widget in (client.entry, client.confirm_button, client.cancel_button):
        assert widget.winfo_ismapped()
        assert widget.winfo_rooty() + widget.winfo_height() < client.dialog.winfo_rooty() + client.dialog.winfo_height()
