#!/usr/bin/env python3
"""Stable entrypoint for project-local native hook dispatch."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


NATIVE_HOOK_DISPATCH_TIMEOUT_SECONDS = 30.0


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _dispatch_script(project_root: Path, integration_key: str) -> Path:
    if integration_key == "claude":
        return project_root / ".claude" / "hooks" / "claude-hook-dispatch.py"
    if integration_key == "gemini":
        return project_root / ".gemini" / "hooks" / "gemini-hook-dispatch.py"
    raise ValueError(f"Unsupported integration '{integration_key}'")


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: specify-hook.py <integration> <route>", file=sys.stderr)
        return 2

    integration_key, route = sys.argv[1], sys.argv[2]
    project_root = _project_root()
    dispatch_script = _dispatch_script(project_root, integration_key)
    if not dispatch_script.exists():
        print(
            f"Missing native hook dispatch script for '{integration_key}'. Run 'specify integration repair'.",
            file=sys.stderr,
        )
        return 2

    try:
        result = subprocess.run(
            [sys.executable, str(dispatch_script), route],
            cwd=project_root,
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
            check=False,
            env=os.environ.copy(),
            timeout=NATIVE_HOOK_DISPATCH_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        print(
            f"Native hook dispatch for '{integration_key}:{route}' timed out after "
            f"{NATIVE_HOOK_DISPATCH_TIMEOUT_SECONDS:g}s; continuing without hook output.",
            file=sys.stderr,
        )
        return 0
    return int(result.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
