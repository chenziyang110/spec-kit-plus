"""Helpers for CLI stdout rendering."""

from __future__ import annotations

import codecs
import json
from pathlib import Path
import sys
from typing import Any, TextIO


def render_json_for_stdout(
    payload: Any,
    *,
    indent: int | None = None,
    default: Any | None = None,
    stream: TextIO | None = None,
) -> str:
    """Render JSON that is safe for the active stdout encoding."""

    target = stream or sys.stdout
    encoding = getattr(target, "encoding", None)
    if not encoding:
        return json.dumps(payload, ensure_ascii=False, indent=indent, default=default)
    try:
        normalized_encoding = codecs.lookup(encoding).name
    except LookupError:
        return json.dumps(payload, ensure_ascii=True, indent=indent, default=default)
    if normalized_encoding != "utf-8":
        return json.dumps(payload, ensure_ascii=True, indent=indent, default=default)
    return json.dumps(payload, ensure_ascii=False, indent=indent, default=default)


def print_json(
    payload: Any,
    *,
    indent: int | None = None,
    default: Any | None = None,
    stream: TextIO | None = None,
) -> None:
    """Write JSON plus a trailing newline to stdout safely."""

    target = stream or sys.stdout
    from .launcher import bind_project_launcher_payload

    bound_payload = bind_project_launcher_payload(payload, Path.cwd())
    target.write(
        render_json_for_stdout(
            bound_payload,
            indent=indent,
            default=default,
            stream=target,
        )
    )
    target.write("\n")
