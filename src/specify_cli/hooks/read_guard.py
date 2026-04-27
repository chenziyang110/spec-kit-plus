"""Shared path-level read boundary guards."""

from __future__ import annotations

from pathlib import Path

from .events import WORKFLOW_READ_GUARD_VALIDATE
from .types import HookResult, QualityHookError


SENSITIVE_FILE_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
    ".git/config",
    "id_rsa",
    "id_ed25519",
    "known_hosts",
}
SENSITIVE_PARTS = {".ssh", ".aws", ".gnupg"}


def read_guard_hook(project_root: Path, payload: dict[str, object]) -> HookResult:
    raw_target = str(payload.get("target_path") or "").strip()
    if not raw_target:
        raise QualityHookError("target_path is required for workflow.read_guard.validate")

    target = Path(raw_target)
    if not target.is_absolute():
        target = (project_root / target).resolve()
    else:
        target = target.resolve()

    try:
        target.relative_to(project_root.resolve())
    except ValueError:
        return HookResult(
            event=WORKFLOW_READ_GUARD_VALIDATE,
            status="blocked",
            severity="critical",
            errors=[f"read target is outside project root: {target}"],
            data={"target_path": str(target)},
        )

    normalized = str(target.relative_to(project_root.resolve())).replace("\\", "/")
    if normalized in SENSITIVE_FILE_NAMES or target.name in SENSITIVE_FILE_NAMES:
        return HookResult(
            event=WORKFLOW_READ_GUARD_VALIDATE,
            status="blocked",
            severity="critical",
            errors=[f"sensitive file read blocked: {normalized}"],
            data={"target_path": str(target)},
        )

    if any(part in SENSITIVE_PARTS for part in target.parts):
        return HookResult(
            event=WORKFLOW_READ_GUARD_VALIDATE,
            status="blocked",
            severity="critical",
            errors=[f"sensitive path read blocked: {target}"],
            data={"target_path": str(target)},
        )

    return HookResult(
        event=WORKFLOW_READ_GUARD_VALIDATE,
        status="ok",
        severity="info",
        data={"target_path": str(target)},
    )

