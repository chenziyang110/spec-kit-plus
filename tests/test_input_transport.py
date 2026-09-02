from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from specify_cli.input_transport import (
    resolve_agent_json_object,
    resolve_agent_text_input,
)


def test_agent_input_transport_reads_project_file_and_stdin(tmp_path: Path) -> None:
    source = tmp_path / "payload.json"
    source.write_text('{"source":"file"}', encoding="utf-8")

    assert resolve_agent_json_object(
        "@payload.json", project_root=tmp_path, label="payload"
    ) == {"source": "file"}
    assert resolve_agent_json_object(
        "-",
        project_root=tmp_path,
        label="payload",
        stdin=io.StringIO('{"source":"stdin"}'),
    ) == {"source": "stdin"}


def test_agent_input_transport_rejects_file_outside_project(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="inside the project root"):
        resolve_agent_text_input(
            f"@{outside}", project_root=project, label="payload"
        )


def test_agent_input_transport_rejects_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target.json"
    target.write_text(json.dumps({"safe": True}), encoding="utf-8")
    link = tmp_path / "linked.json"
    try:
        link.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symlink creation is unavailable: {exc}")

    with pytest.raises(ValueError, match="symlinks or reparse points"):
        resolve_agent_text_input(
            "@linked.json", project_root=tmp_path, label="payload"
        )


def test_agent_input_transport_keeps_whitespace_prefixed_at_literal(
    tmp_path: Path,
) -> None:
    (tmp_path / "payload.json").write_text("unexpected", encoding="utf-8")

    assert (
        resolve_agent_text_input(
            "  @payload.json", project_root=tmp_path, label="payload"
        )
        == "  @payload.json"
    )
    assert (
        resolve_agent_text_input(
            "@@operator", project_root=tmp_path, label="payload"
        )
        == "@operator"
    )


def test_agent_input_transport_bounds_text_stdin_by_utf8_bytes(
    tmp_path: Path,
) -> None:
    class RecordingTextStream(io.StringIO):
        requested_sizes: list[int]

        def __init__(self, value: str) -> None:
            super().__init__(value)
            self.requested_sizes = []

        def read(self, size: int = -1) -> str:
            self.requested_sizes.append(size)
            return super().read(size)

    source = RecordingTextStream("😀😀😀")
    with pytest.raises(ValueError, match="8-byte input limit"):
        resolve_agent_text_input(
            "-",
            project_root=tmp_path,
            label="payload",
            stdin=source,
            max_bytes=8,
        )
    assert max(source.requested_sizes) <= 2
