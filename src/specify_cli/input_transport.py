"""Bounded inline, project-file, and stdin transport for agent-authored input."""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path
from typing import Any, TextIO


MAX_AGENT_INPUT_BYTES = 16 * 1024 * 1024


def _is_link_or_reparse(info: os.stat_result) -> bool:
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0)
    file_attributes = getattr(info, "st_file_attributes", 0)
    return stat.S_ISLNK(info.st_mode) or bool(file_attributes & reparse_flag)


def _contained_input_path(project_root: Path, raw_path: str, *, label: str) -> tuple[Path, Path]:
    root = Path(project_root).resolve(strict=True)
    candidate = Path(raw_path)
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = Path(os.path.abspath(candidate))
    try:
        relative = candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"{label} @path must stay inside the project root") from exc
    if relative == Path("."):
        raise ValueError(f"{label} @path must be a regular file")
    return root, candidate


def _inspect_contained_regular_file(root: Path, candidate: Path, *, label: str) -> os.stat_result:
    relative = candidate.relative_to(root)
    current = root
    final_info: os.stat_result | None = None
    for index, part in enumerate(relative.parts):
        current /= part
        try:
            info = os.lstat(current)
        except OSError as exc:
            raise ValueError(f"{label} @path could not be inspected: {exc}") from exc
        if _is_link_or_reparse(info):
            raise ValueError(f"{label} @path must not use symlinks or reparse points")
        if index < len(relative.parts) - 1 and not stat.S_ISDIR(info.st_mode):
            raise ValueError(f"{label} @path parent must be a directory")
        final_info = info
    if final_info is None or not stat.S_ISREG(final_info.st_mode):
        raise ValueError(f"{label} @path must be a regular file")
    return final_info


def _read_project_file(
    project_root: Path,
    raw_path: str,
    *,
    label: str,
    max_bytes: int,
) -> str:
    root, candidate = _contained_input_path(project_root, raw_path, label=label)
    initial_info = _inspect_contained_regular_file(root, candidate, label=label)
    if initial_info.st_size > max_bytes:
        raise ValueError(f"{label} exceeds the {max_bytes}-byte input limit")

    try:
        with candidate.open("rb") as source:
            opened_info = os.fstat(source.fileno())
            current_info = _inspect_contained_regular_file(root, candidate, label=label)
            if not stat.S_ISREG(opened_info.st_mode):
                raise ValueError(f"{label} @path must be a regular file")
            if not os.path.samestat(opened_info, current_info):
                raise ValueError(f"{label} @path changed during validation")
            if opened_info.st_size > max_bytes or current_info.st_size > max_bytes:
                raise ValueError(f"{label} exceeds the {max_bytes}-byte input limit")
            data = source.read(max_bytes + 1)
    except ValueError:
        raise
    except OSError as exc:
        raise ValueError(f"{label} @path could not be read: {exc}") from exc

    if len(data) > max_bytes:
        raise ValueError(f"{label} exceeds the {max_bytes}-byte input limit")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} @path must contain UTF-8 text: {exc}") from exc


def _read_bounded_stdin(source: TextIO, *, label: str, max_bytes: int) -> str:
    binary_source = getattr(source, "buffer", None)
    if binary_source is not None:
        data = binary_source.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise ValueError(f"{label} exceeds the {max_bytes}-byte input limit")
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError(f"{label} stdin must contain UTF-8 text: {exc}") from exc

    chunks: list[str] = []
    total_bytes = 0
    while True:
        remaining = max_bytes - total_bytes
        # A Python character occupies at most four UTF-8 bytes. Keep text-only
        # streams bounded without first materializing an oversized string.
        read_size = min(64 * 1024, max(1, (remaining + 3) // 4))
        chunk = source.read(read_size)
        if not chunk:
            break
        try:
            chunk_bytes = chunk.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError(f"{label} stdin must contain UTF-8 text: {exc}") from exc
        total_bytes += len(chunk_bytes)
        if total_bytes > max_bytes:
            raise ValueError(f"{label} exceeds the {max_bytes}-byte input limit")
        chunks.append(chunk)
    return "".join(chunks)


def resolve_agent_text_input(
    raw: str,
    *,
    project_root: Path,
    label: str,
    stdin: TextIO | None = None,
    max_bytes: int = MAX_AGENT_INPUT_BYTES,
) -> str:
    """Resolve one bounded ``inline|@path|-`` text input at invocation time."""

    raw_text = raw or ""
    text = raw_text.strip()
    if not text:
        raise ValueError(
            f"{label} is required (inline text, @path, or - for stdin; "
            "on Windows prefer @path or stdin for large existing payloads)"
        )
    if raw_text == "-":
        source = stdin if stdin is not None else sys.stdin
        return _read_bounded_stdin(source, label=label, max_bytes=max_bytes)
    if raw_text.startswith("@@"):
        payload = raw_text[1:]
    elif raw_text.startswith("@"):
        path_text = raw_text[1:].strip()
        if not path_text:
            raise ValueError(f"{label} @path requires a non-empty path")
        return _read_project_file(
            project_root,
            path_text,
            label=label,
            max_bytes=max_bytes,
        )
    else:
        payload = raw

    if len(payload.encode("utf-8")) > max_bytes:
        raise ValueError(f"{label} exceeds the {max_bytes}-byte input limit")
    return payload


def resolve_agent_json_object(
    raw: str,
    *,
    project_root: Path,
    label: str,
    stdin: TextIO | None = None,
    max_bytes: int = MAX_AGENT_INPUT_BYTES,
) -> dict[str, Any]:
    """Resolve and decode one bounded JSON object from ``inline|@path|-``."""

    payload_text = resolve_agent_text_input(
        raw,
        project_root=project_root,
        label=label,
        stdin=stdin,
        max_bytes=max_bytes,
    )
    try:
        payload = json.loads(payload_text)
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{label} must be valid JSON: {exc}; "
            "on Windows PowerShell prefer @payload.json or stdin -"
        ) from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return payload


__all__ = [
    "MAX_AGENT_INPUT_BYTES",
    "resolve_agent_json_object",
    "resolve_agent_text_input",
]
