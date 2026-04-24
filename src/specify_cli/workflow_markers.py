from __future__ import annotations

import re


AGENT_MARKER = "[AGENT]"
PARALLEL_MARKER = "[P]"
_SUPPORTED_MARKERS = (AGENT_MARKER, PARALLEL_MARKER)
_ACTIONABLE_PREFIX_RE = re.compile(
    r"^(?P<leading_ws>\s*)"
    r"(?:(?P<action_prefix>- \[[ xX]\] T\d+\s+|-\s+|\d+\.\s+))?"
    r"(?P<body>.*)$"
)


def _split_actionable_prefix(text: str) -> tuple[str, str]:
    match = _ACTIONABLE_PREFIX_RE.match(text)
    if match is None:
        return "", text.lstrip()

    action_prefix = match.group("action_prefix")
    if action_prefix:
        prefix = f"{match.group('leading_ws')}{action_prefix}"
        return prefix, match.group("body")

    return "", match.group("body")


def _consume_leading_markers(text: str) -> tuple[str, tuple[str, ...], str]:
    prefix, remainder = _split_actionable_prefix(text)
    found: list[str] = []

    while True:
        candidate = remainder.lstrip()
        consumed_marker = False

        for marker in _SUPPORTED_MARKERS:
            if not candidate.startswith(marker):
                continue

            marker_end = len(marker)
            if len(candidate) > marker_end and not candidate[marker_end].isspace():
                continue

            found.append(marker)
            remainder = candidate[marker_end:]
            consumed_marker = True
            break

        if not consumed_marker:
            break

    return prefix, tuple(found), remainder


def has_agent_marker(text: str) -> bool:
    return AGENT_MARKER in _consume_leading_markers(text)[1]


def has_parallel_marker(text: str) -> bool:
    return PARALLEL_MARKER in _consume_leading_markers(text)[1]


def strip_known_markers(text: str) -> str:
    prefix, _, remainder = _consume_leading_markers(text)
    cleaned = remainder.strip()

    if prefix:
        return f"{prefix.rstrip()} {cleaned}".rstrip()

    return cleaned
