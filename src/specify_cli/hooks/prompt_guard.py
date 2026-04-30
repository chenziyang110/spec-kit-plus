"""Shared prompt-level workflow bypass detection."""

from __future__ import annotations

import re

from .events import WORKFLOW_PROMPT_GUARD_VALIDATE
from .types import HookResult, QualityHookError


BLOCK_PATTERNS = [
    re.compile(r"ignore\s+analyze", re.IGNORECASE),
    re.compile(r"implement\s+directly", re.IGNORECASE),
    re.compile(r"do\s+not\s+write\s+workflow-state", re.IGNORECASE),
    re.compile(r"skip\s+tests?", re.IGNORECASE),
    re.compile(r"bypass\s+(?:the\s+)?(?:workflow|guardrails?|checks?)", re.IGNORECASE),
]

WARN_PATTERNS = [
    re.compile(r"ignore\s+previous\s+instructions", re.IGNORECASE),
    re.compile(r"just\s+do\s+what\s+i\s+say", re.IGNORECASE),
    re.compile(r"no\s+workflow", re.IGNORECASE),
    re.compile(r"no\s+(?:subagents?|spawned\s+agents?)", re.IGNORECASE),
    re.compile(r"do\s+not\s+(?:dispatch|spawn|use)\s+(?:native\s+)?(?:subagents?|agents?)", re.IGNORECASE),
]


def prompt_guard_hook(_project_root, payload: dict[str, object]) -> HookResult:
    prompt_text = str(payload.get("prompt_text") or "").strip()
    if not prompt_text:
        raise QualityHookError("prompt_text is required for workflow.prompt_guard.validate")

    lower = prompt_text.lower()
    block_hits = [pattern.pattern for pattern in BLOCK_PATTERNS if pattern.search(lower)]
    if block_hits:
        return HookResult(
            event=WORKFLOW_PROMPT_GUARD_VALIDATE,
            status="blocked",
            severity="critical",
            errors=[
                "prompt attempts to ignore or skip required workflow guardrails or execution discipline"
            ],
            data={"matched_rules": block_hits},
        )

    warn_hits = [pattern.pattern for pattern in WARN_PATTERNS if pattern.search(lower)]
    if warn_hits:
        return HookResult(
            event=WORKFLOW_PROMPT_GUARD_VALIDATE,
            status="warn",
            severity="warning",
            warnings=[
                "prompt contains instruction-override or subagent-suppression language; review before routing automatically"
            ],
            data={"matched_rules": warn_hits},
        )

    return HookResult(
        event=WORKFLOW_PROMPT_GUARD_VALIDATE,
        status="ok",
        severity="info",
        data={"matched_rules": []},
    )
