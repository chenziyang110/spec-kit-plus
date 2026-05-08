"""Diff impact helpers for project cognition runtime updates."""

from __future__ import annotations


def build_diff_impact_payload(*, changed_paths: list[str]) -> dict[str, object]:
    return {
        "changed_paths": list(changed_paths),
        "affected_nodes": [],
        "affected_claims": [],
        "requires_full_rescan": False,
    }
