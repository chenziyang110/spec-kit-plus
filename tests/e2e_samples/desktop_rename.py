"""Disposable Tk client used to exercise E2E scenario design, not a file manager.

Only operate on a fresh sandbox created by ``create_sandbox``. The 32-code-point
name policy is this sample's explicit contract, not an OS/filesystem rule.
External mutations in the tests occur at observable pre-confirm checkpoints.
This sample does not claim atomic correctness against hostile syscall races.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import tkinter as tk
from tkinter import ttk

LIMIT = 32
MARKER = ".spec-kit-e2e-sandbox"
MARKER_BYTES = b"spec-kit-plus disposable desktop rename sample v1\n"
SENTINEL = b"original file: preserve these bytes\n"
OCCUPIED = b"existing destination: never overwrite\n"


class RenameRejected(ValueError):
    """A sample contract rejects an operation without modifying user data."""


@dataclass(frozen=True)
class Selection:
    name: str
    device: int
    inode: int
    digest: str


def create_sandbox(path: Path) -> Path:
    """Create, never reuse, a private directory with disposable sample files."""
    path.mkdir(mode=0o700, parents=False, exist_ok=False)
    (path / MARKER).write_bytes(MARKER_BYTES)
    (path / "A.txt").write_bytes(SENTINEL)
    (path / "taken.txt").write_bytes(OCCUPIED)
    return path


class Store:
    def __init__(self, root: Path):
        if root.is_symlink() or not root.is_dir():
            raise RenameRejected("A real disposable sandbox is required")
        self.root = root.resolve()
        marker = self.root / MARKER
        if marker.is_symlink() or not marker.is_file() or marker.read_bytes() != MARKER_BYTES:
            raise RenameRejected("Refusing to use an unmarked directory")

    @staticmethod
    def validate_name(name: str) -> None:
        # Explicit sample policy. Do not copy this list into a product contract.
        if not name or not name.strip():
            raise RenameRejected("Name must not be empty or whitespace")
        if name in {".", "..", MARKER}:
            raise RenameRejected("Name is reserved by this sample")
        if any(ord(c) < 32 or c in '<>:"/\\|?*' for c in name):
            raise RenameRejected("Name contains a disallowed character")
        if len(name) > LIMIT:
            raise RenameRejected(f"Name exceeds {LIMIT} Unicode code points")

    def select(self, name: str) -> Selection:
        self.validate_name(name)
        source = self.root / name
        try:
            metadata = source.lstat()
            if not stat.S_ISREG(metadata.st_mode):
                raise RenameRejected("Selection must be a regular non-symlink file")
            data = source.read_bytes()
        except FileNotFoundError as exc:
            raise RenameRejected("Original file no longer exists") from exc
        return Selection(name, metadata.st_dev, metadata.st_ino, hashlib.sha256(data).hexdigest())

    def rename(self, selection: Selection, name: str) -> str:
        self.validate_name(name)
        current = self.select(selection.name)
        if current != selection:
            raise RenameRejected("Original file changed or was replaced")
        if name == selection.name:
            return "Name unchanged"
        source, target = self.root / selection.name, self.root / name
        # link() gives an exclusive destination: it never overwrites an existing
        # file or symlink. All files live on the same disposable filesystem.
        try:
            os.link(source, target, follow_symlinks=False)
        except FileExistsError as exc:
            raise RenameRejected("Destination already exists") from exc
        try:
            # Guard the controlled sample against a changed pre-confirm object.
            if self.select(selection.name) != selection:
                raise RenameRejected("Original file changed during rename")
            source.unlink()
        except BaseException:
            # Remove only the link this invocation created, not an unrelated
            # replacement installed at the destination in the meantime.
            try:
                linked = self.select(name)
                if (linked.device, linked.inode, linked.digest) == (
                    selection.device, selection.inode, selection.digest
                ):
                    target.unlink()
            except (OSError, RenameRejected):
                pass
            raise
        return f"Renamed to {name}"

    def readback(self) -> dict[str, str]:
        return {
            p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(self.root.iterdir())
            if p.name != MARKER and p.is_file() and not p.is_symlink()
        }


class RenameClient:
    def __init__(self, root: tk.Tk, store: Store):
        self.root, self.store = root, store
        self.dialog: tk.Toplevel | None = None
        self.selection: Selection | None = None
        root.title("Spec Kit E2E — disposable desktop client")
        root.geometry("720x470+80+70")
        root.resizable(False, False)
        body = ttk.Frame(root, padding=22)
        body.pack(fill="both", expand=True)
        ttk.Label(body, text="Desktop rename scenario", font=("TkDefaultFont", 18, "bold")).pack(anchor="w")
        ttk.Label(body, text="Isolated sample data only · visual feedback and filesystem readback are separate").pack(anchor="w", pady=(6, 16))
        self.listbox = tk.Listbox(body, height=8, exportselection=False, font=("TkDefaultFont", 13))
        self.listbox.pack(fill="x")
        actions = ttk.Frame(body)
        actions.pack(fill="x", pady=12)
        self.rename_button = ttk.Button(actions, text="Rename selected file", command=self.open_dialog)
        self.rename_button.pack(side="left")
        self.refresh_button = ttk.Button(actions, text="Refresh", command=self.refresh)
        self.refresh_button.pack(side="left", padx=10)
        self.status = tk.StringVar(value="Ready. Select A.txt and open Rename.")
        self.status_label = ttk.Label(body, textvariable=self.status, wraplength=665)
        self.status_label.pack(anchor="w", pady=6)
        self.refresh()

    def refresh(self) -> None:
        self.listbox.delete(0, "end")
        for name in self.store.readback():
            self.listbox.insert("end", name)
        if self.listbox.size():
            self.listbox.selection_set(0)

    def open_dialog(self) -> None:
        if self.dialog is not None:
            self.dialog.lift()
            return
        selected = self.listbox.curselection()
        if not selected:
            self.status.set("Select a file first")
            return
        try:
            self.selection = self.store.select(self.listbox.get(selected[0]))
        except (OSError, RenameRejected) as exc:
            self.status.set(str(exc))
            return
        dialog = self.dialog = tk.Toplevel(self.root)
        dialog.title("Rename selected file")
        dialog.geometry("530x225+175+155")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.protocol("WM_DELETE_WINDOW", self.cancel)
        dialog.grab_set()
        frame = ttk.Frame(dialog, padding=22)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text=f"New name for {self.selection.name} (max {LIMIT} code points)").pack(anchor="w")
        self.name = tk.StringVar(value=self.selection.name)
        self.entry = ttk.Entry(frame, textvariable=self.name, font=("TkDefaultFont", 13))
        self.entry.pack(fill="x", pady=12)
        self.error = tk.StringVar()
        ttk.Label(frame, textvariable=self.error, wraplength=470).pack(anchor="w")
        buttons = ttk.Frame(frame)
        buttons.pack(anchor="e", pady=14)
        self.confirm_button = ttk.Button(buttons, text="Confirm rename", command=self.confirm)
        self.confirm_button.pack(side="left", padx=8)
        self.cancel_button = ttk.Button(buttons, text="Cancel", command=self.cancel)
        self.cancel_button.pack(side="left")
        self.entry.bind("<Return>", lambda event: self.confirm())
        self.entry.bind("<Escape>", lambda event: self.cancel())
        self.entry.focus_force()
        self.entry.selection_range(0, "end")

    def confirm(self) -> None:
        # Queued double activation after closing the dialog is a no-op.
        if self.dialog is None or self.selection is None:
            return
        try:
            outcome = self.store.rename(self.selection, self.name.get())
        except (OSError, RenameRejected) as exc:
            self.error.set(str(exc))
            self.status.set(f"Not renamed: {exc}")
            return
        self.cancel()
        self.status.set(outcome)
        self.refresh()

    def cancel(self) -> None:
        if self.dialog is not None:
            self.dialog.grab_release()
            self.dialog.destroy()
            self.dialog = None
        self.selection = None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, help="A NEW sandbox path; existing directories are rejected")
    args = parser.parse_args()
    # A newly allocated parent keeps the sandbox create-only.
    parent = None
    if args.workspace is None:
        parent = tempfile.TemporaryDirectory(prefix="spec-kit-e2e-")
        workspace = Path(parent.name) / "sandbox"
    else:
        workspace = args.workspace.absolute()
    try:
        store = Store(create_sandbox(workspace))
        print(json.dumps({"workspace": str(workspace), "contract": "sample-only", "limit": LIMIT}), flush=True)
        root = tk.Tk()
        RenameClient(root, store)
        root.mainloop()
    finally:
        if parent is not None:
            parent.cleanup()


if __name__ == "__main__":
    main()
