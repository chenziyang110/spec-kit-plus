"""Helpers for CLI stdout rendering."""

from __future__ import annotations

import json
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
    rendered = json.dumps(payload, ensure_ascii=False, indent=indent, default=default)
    encoding = getattr(target, "encoding", None)
    if not encoding:
        return rendered
    try:
        rendered.encode(encoding)
    except (LookupError, UnicodeEncodeError):
        return json.dumps(payload, ensure_ascii=True, indent=indent, default=default)
    return rendered


def print_json(
    payload: Any,
    *,
    indent: int | None = None,
    default: Any | None = None,
    stream: TextIO | None = None,
) -> None:
    """Write JSON plus a trailing newline to stdout safely."""

    target = stream or sys.stdout
    target.write(render_json_for_stdout(payload, indent=indent, default=default, stream=target))
    target.write("\n")
