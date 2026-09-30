#!/usr/bin/env python3
"""Verify E2E wheel payloads against their source bytes and wheel RECORD.

Read-only and stdlib-only. This is packaging evidence, not an installed-project,
GUI, discovery-completeness or product-acceptance claim. No archive is extracted.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import stat
import sys
import zipfile
from typing import BinaryIO

HELPERS = ("e2e_scenarios.py", "e2e_coverage.py", "e2e_runner.py", "e2e_pytest_reporter.py")
ASSET_TREES = {
    "templates/command-partials": "specify_cli/core_pack/command-partials",
    "templates/advanced-skills/spx-e2e": "specify_cli/core_pack/advanced-skills/spx-e2e",
    "templates/advanced-skills/_shared": "specify_cli/core_pack/advanced-skills/_shared",
}
ASSET_FILES = {
    "src/specify_cli/__init__.py": "specify_cli/__init__.py",
    "templates/commands/e2e.md": "specify_cli/core_pack/commands/e2e.md",
    "templates/artifacts/project-cognition-workflow-registry.json":
        "specify_cli/core_pack/templates/artifacts/project-cognition-workflow-registry.json",
}


class WheelError(ValueError):
    """The wheel does not establish the requested packaging claim."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise WheelError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_assets(root: Path) -> dict[str, bytes]:
    """Enumerate the real owners; missing source trees must not reduce coverage."""
    root = root.resolve()
    mapping = dict(ASSET_FILES)
    mapping.update({f"scripts/shared/{name}": f"specify_cli/core_pack/scripts/shared/{name}"
                    for name in HELPERS})
    for source, target in ASSET_TREES.items():
        directory = root / source
        require(directory.is_dir(), f"missing source tree: {source}")
        require(directory.resolve().is_relative_to(root), f"escaping source tree: {source}")
        members = sorted(path for path in directory.rglob("*") if path.is_file()
                         and "__pycache__" not in path.parts and path.suffix != ".pyc")
        require(bool(members), f"empty source tree: {source}")
        for path in members:
            mapping[path.relative_to(root).as_posix()] = target + "/" + path.relative_to(directory).as_posix()
    assets = {}
    for source, target in sorted(mapping.items()):
        path = root / source
        require(path.resolve().is_relative_to(root) and path.is_file(), f"missing/escaping source: {source}")
        assets[target] = path.read_bytes()
    return assets


def read_record(archive: zipfile.ZipFile) -> dict[str, tuple[str, str]]:
    records = [name for name in archive.namelist() if name.endswith(".dist-info/RECORD")]
    require(len(records) == 1, "wheel must contain exactly one RECORD")
    result = {}
    for row in csv.reader(io.StringIO(archive.read(records[0]).decode("utf-8"))):
        require(len(row) == 3 and bool(row[0]), "malformed RECORD row")
        require(row[0] not in result, f"duplicate RECORD row: {row[0]}")
        result[row[0]] = (row[1], row[2])
    return result


def _file_signature(value: os.stat_result) -> tuple[int, ...]:
    return (value.st_dev, value.st_ino, value.st_mode, value.st_size,
            value.st_mtime_ns, value.st_ctime_ns)


def _check_wheel_snapshot(wheel: Path, stream: BinaryIO, expected: os.stat_result) -> None:
    """Check both the opened descriptor and the current named file."""
    for current in (os.fstat(stream.fileno()), wheel.stat()):
        require(stat.S_ISREG(current.st_mode), "wheel must be a regular file")
        require(_file_signature(current) == _file_signature(expected),
                "wheel changed during verification; rebuild or retry on a stable file")


def _stream_sha256(stream: BinaryIO) -> str:
    """Hash the checked descriptor in bounded chunks, never reopen its path."""
    stream.seek(0)
    result = hashlib.sha256()
    for chunk in iter(lambda: stream.read(65536), b""):
        result.update(chunk)
    stream.seek(0)
    return result.hexdigest()


def verify_wheel(wheel: Path, root: Path) -> dict:
    expected = source_assets(root)
    checked = []
    before = wheel.stat()
    require(stat.S_ISREG(before.st_mode), "wheel must be a regular file")
    # Nonblocking open prevents an observed regular file swapped for a FIFO
    # from hanging on POSIX. O_BINARY keeps archive bytes unchanged on Windows.
    flags = os.O_RDONLY | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_BINARY", 0)
    with os.fdopen(os.open(wheel, flags), "rb") as stream:
        _check_wheel_snapshot(wheel, stream, before)
        wheel_digest = _stream_sha256(stream)
        with zipfile.ZipFile(stream) as archive:
            names = archive.namelist()
            require(len(names) == len(set(names)), "duplicate ZIP member")
            for name in names:
                clean = name.rstrip("/")
                path = PurePosixPath(clean)
                require(bool(clean) and not path.is_absolute() and ".." not in path.parts
                        and "\\" not in name and ":" not in name and path.as_posix() == clean,
                        f"noncanonical ZIP member: {name}")
            record = read_record(archive)
            for name, wanted in sorted(expected.items()):
                require(name in names, f"missing wheel asset: {name}")
                info = archive.getinfo(name)
                require(info.file_size == len(wanted), f"wheel asset size mismatch: {name}")
                actual = archive.read(name)
                require(actual == wanted, f"wheel asset bytes mismatch: {name}")
                encoded = base64.urlsafe_b64encode(hashlib.sha256(actual).digest()).rstrip(b"=").decode("ascii")
                require(record.get(name) == ("sha256=" + encoded, str(len(actual))),
                        f"RECORD hash/size mismatch: {name}")
                checked.append({"path": name, "sha256": sha256(actual), "size": len(actual)})
        _check_wheel_snapshot(wheel, stream, before)
        require(_stream_sha256(stream) == wheel_digest,
                "wheel bytes changed during verification")
        # Re-enumeration also catches newly added/removed required references;
        # rechecking only the old file list could silently shrink the boundary.
        require(source_assets(root) == expected,
                "source assets changed during verification; rebuild the wheel")
        _check_wheel_snapshot(wheel, stream, before)
    return {
        "claim": "wheel_e2e_assets_verified", "wheel_sha256": wheel_digest,
        "asset_count": len(checked), "assets": checked,
        "qualification": "Source/archive/RECORD consistency only; not installation, execution or product acceptance. "
                         "Observed stability checks are not an atomic snapshot or a hostile-writer sandbox.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wheel", required=True, type=Path)
    parser.add_argument("--source-root", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = verify_wheel(args.wheel, args.source_root)
    except (OSError, ValueError, KeyError, UnicodeError, csv.Error, zipfile.BadZipFile) as exc:
        print(json.dumps({"claim": "invalid", "error": str(exc)}), file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
