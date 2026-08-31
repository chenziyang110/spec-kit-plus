"""Child environments for direct execution without retired Run authority."""

from __future__ import annotations

import os
from typing import Mapping


_RETIRED_ENV_KEYS = frozenset(
    {
        "SPECIFY_ACTIVITY_ID",
        "SPECIFY_ATTEMPT_ID",
        "SPECIFY_ATTEMPT_FENCE",
        "SPECIFY_WORKSPACE_ID",
        "SPECIFY_WORKSPACE_GENERATION",
        "SPECIFY_WORKSPACE_ROOT",
        "SPECIFY_REPO_COMMON_DIR",
        "SPECIFY_PRIVATE_REF",
    }
)


def _is_retired_environment_key(key: str) -> bool:
    normalized = key.upper()
    return normalized.startswith("SPECIFY_RUN_") or normalized in _RETIRED_ENV_KEYS


def build_child_environment(env: Mapping[str, str] | None = None) -> dict[str, str]:
    """Remove obsolete authority while preserving caller-owned Board/packet bindings."""

    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    merged_env = {
        key: value
        for key, value in merged_env.items()
        if not _is_retired_environment_key(key)
    }
    for key in list(merged_env):
        if key.upper() == "WSLENV":
            merged_env[key] = ":".join(
                entry
                for entry in merged_env[key].split(":")
                if entry and not _is_retired_environment_key(entry.split("/", 1)[0])
            )
    return merged_env
