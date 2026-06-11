"""Resume-audit helpers for sp-implement terminal-state validation."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from specify_cli.execution.evidence import (
    has_any_evidence,
    has_real_entrypoint_consumer_evidence,
    normalize_evidence_label,
)
from specify_cli.hooks.checkpoint_serializers import serialize_implement_tracker


TASK_RE = re.compile(r"(?m)^\s*-\s\[(?P<checked>[ xX])\]\s+(?P<task_id>T\d+)\b(?P<body>.*)$")
TASK_DETAIL_RE = re.compile(r"(?ms)^##\s+(?P<task_id>T\d+)\b[^\n]*\n(?P<body>.*?)(?=^##\s+|\Z)")
CONSUMER_KEYWORDS = (
    "component",
    "form",
    "page",
    "route",
    "router",
    "provider",
    "factory",
    "registry",
    "panel",
    "modal",
    "endpoint",
    "api",
    "client",
    "config",
    "schema",
    "test",
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _parse_tasks(tasks_path: Path) -> list[dict[str, Any]]:
    text = _read_text(tasks_path)
    tasks: list[dict[str, Any]] = []
    for match in TASK_RE.finditer(text):
        task_id = match.group("task_id")
        body = match.group("body").strip()
        detail = _task_detail_body(text, task_id)
        tasks.append(
            {
                "task_id": task_id,
                "checked": match.group("checked").lower() == "x",
                "body": body,
                "consumer_facing": _looks_consumer_facing(body),
                "requires_real_entrypoint": _requires_real_entrypoint_evidence(body, detail),
            }
        )
    return tasks


def _task_detail_body(tasks_text: str, task_id: str) -> str:
    for match in TASK_DETAIL_RE.finditer(tasks_text):
        if match.group("task_id") == task_id:
            return match.group("body").strip()
    return ""


def _requires_real_entrypoint_evidence(*texts: str) -> bool:
    normalized = normalize_evidence_label(" ".join(text for text in texts if text))
    return "real_entrypoint_evidence" in normalized


def _looks_consumer_facing(task_body: str) -> bool:
    lowered = task_body.lower()
    return any(keyword in lowered for keyword in CONSUMER_KEYWORDS)


def _load_worker_result(feature_dir: Path, task_id: str) -> dict[str, Any] | None:
    for candidate in (
        feature_dir / "worker-results" / f"{task_id}.json",
        feature_dir / "worker-results" / f"{task_id.lower()}.json",
    ):
        if not candidate.exists():
            continue
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"task_id": task_id, "status": "invalid-json", "path": str(candidate)}
        payload["path"] = str(candidate)
        return payload
    return None


def _result_has_passed_validation(result: dict[str, Any]) -> bool:
    validations = result.get("validation_results") or result.get("validationResults") or []
    if not isinstance(validations, list) or not validations:
        return False
    statuses = [
        str(item.get("status", "")).lower()
        for item in validations
        if isinstance(item, dict)
    ]
    return bool(statuses) and all(status == "passed" for status in statuses)


def _result_has_consumer_evidence(result: dict[str, Any]) -> bool:
    evidence = result.get("consumer_evidence") or result.get("consumerEvidence") or []
    return has_any_evidence(evidence)


def _result_has_real_entrypoint_consumer_evidence(result: dict[str, Any]) -> bool:
    evidence = result.get("consumer_evidence") or result.get("consumerEvidence") or []
    return has_real_entrypoint_consumer_evidence(evidence)


def _tracker_has_open_gaps(feature_dir: Path) -> bool:
    text = _read_text(feature_dir / "implement-tracker.md")
    marker = "## Open Gaps"
    if marker not in text:
        return False
    body = text.split(marker, 1)[1]
    next_section = re.split(r"(?m)^##\s+", body, maxsplit=1)[0]
    meaningful = [
        line.strip()
        for line in next_section.splitlines()
        if line.strip() and line.strip().lower() not in {"- none", "none", "[]"}
    ]
    return any(line.startswith("-") or line.startswith("type:") for line in meaningful)


def audit_implement_resume(project_root: Path, feature_dir: Path) -> dict[str, Any]:
    """Return a conservative resume audit payload for an implement feature dir."""

    resolved_feature_dir = feature_dir if feature_dir.is_absolute() else (project_root / feature_dir).resolve()
    tracker_path = resolved_feature_dir / "implement-tracker.md"
    tasks_path = resolved_feature_dir / "tasks.md"

    if not tracker_path.exists():
        return _payload(
            status="conflict",
            feature_dir=resolved_feature_dir,
            classification="state-conflict",
            trusted=False,
            recommended_status="blocked",
            next_action="Recreate or recover implement-tracker.md before resuming implementation.",
            task_findings=[],
            open_gaps=["implement-tracker.md is missing"],
        )

    tracker = serialize_implement_tracker(tracker_path)
    tracker_status = str(tracker.get("status") or "").strip().lower()
    tasks = _parse_tasks(tasks_path)
    checked_tasks = [task for task in tasks if task["checked"]]
    all_checked = bool(tasks) and len(checked_tasks) == len(tasks)
    terminal = tracker_status == "resolved" or all_checked
    classification = "terminal-audit-required" if terminal else "clean-active"

    task_findings: list[dict[str, Any]] = []
    evidence_gaps: list[str] = []
    if terminal and not tasks:
        evidence_gaps.append("tasks.md has no task checklist evidence")
    for task in checked_tasks:
        missing: list[str] = []
        result = _load_worker_result(resolved_feature_dir, str(task["task_id"]))
        if result is None:
            missing.append("missing worker result")
        elif str(result.get("status", "")).lower() not in {"success", "done", "done_with_concerns"}:
            missing.append("worker result is not successful")
        else:
            if not _result_has_passed_validation(result):
                missing.append("missing passed validation evidence")
            if task["requires_real_entrypoint"] and not _result_has_consumer_evidence(result):
                missing.append("missing consumer evidence")
            elif task["requires_real_entrypoint"] and not _result_has_real_entrypoint_consumer_evidence(result):
                missing.append("missing real-entrypoint consumer evidence")
            elif task["consumer_facing"] and not _result_has_consumer_evidence(result):
                missing.append("missing consumer evidence")

        if missing:
            evidence_gaps.append(f"{task['task_id']}: {', '.join(missing)}")
        task_findings.append(
            {
                "task_id": task["task_id"],
                "checked": task["checked"],
                "consumer_facing": task["consumer_facing"],
                "result_path": result.get("path", "") if isinstance(result, dict) else "",
                "missing_evidence": "; ".join(missing),
            }
        )

    if _tracker_has_open_gaps(resolved_feature_dir):
        evidence_gaps.append("implement-tracker.md has unresolved open_gaps")

    audit_passed = terminal and not evidence_gaps
    if audit_passed:
        return _payload(
            status="pass",
            feature_dir=resolved_feature_dir,
            classification=classification,
            trusted=True,
            recommended_status="resolved",
            next_action="Terminal implement state has closeout-quality evidence.",
            task_findings=task_findings,
            open_gaps=[],
        )

    if terminal:
        return _payload(
            status="fail",
            feature_dir=resolved_feature_dir,
            classification=classification,
            trusted=False,
            recommended_status="validating",
            next_action="Resume sp-implement in validation/recovery mode and close the evidence gaps before reporting completion.",
            task_findings=task_findings,
            open_gaps=evidence_gaps,
        )

    return _payload(
        status="pass",
        feature_dir=resolved_feature_dir,
        classification=classification,
        trusted=False,
        recommended_status=tracker_status or "executing",
        next_action=str(tracker.get("next_action") or "Resume the recorded implementation batch."),
        task_findings=task_findings,
        open_gaps=evidence_gaps,
    )


def _payload(
    *,
    status: str,
    feature_dir: Path,
    classification: str,
    trusted: bool,
    recommended_status: str,
    next_action: str,
    task_findings: list[dict[str, Any]],
    open_gaps: list[str],
) -> dict[str, Any]:
    return {
        "status": status,
        "feature_dir": str(feature_dir),
        "resume_classification": classification,
        "trusted_terminal_state": trusted,
        "task_findings": task_findings,
        "join_point_findings": [],
        "open_gaps": open_gaps,
        "recommended_tracker_status": recommended_status,
        "recommended_next_action": next_action,
    }
