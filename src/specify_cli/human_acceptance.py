"""Durable, context-restoring human acceptance state for completed features."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from copy import deepcopy
from pathlib import Path
from typing import Any

import pathspec

from .atomic_io import atomic_write_text, interprocess_lock


ACCEPTANCE_FILENAME = "human-acceptance.json"
IMPLEMENTATION_SUMMARY_FILENAME = "implementation-summary.md"
ACCEPTANCE_SCHEMA_REF = ".specify/templates/human-acceptance-state-schema.json"
ACCEPTANCE_COMMAND = "sp-accept (Classic) or spx-accept (Advanced)"
ACCEPTANCE_STATUSES = {
    "draft",
    "ready",
    "in_progress",
    "accepted",
    "rejected",
    "blocked",
    "stale",
}
STEP_RESULTS = {"pending", "pass", "fail", "blocked", "not_run"}
SCENARIO_VERDICTS = {"pending", "pass", "fail", "blocked", "not_run"}
OVERALL_VERDICTS = {"pending", "pass", "fail", "blocked"}
FINDING_CLASSIFICATIONS = {
    "product-defect",
    "requirement-gap",
    "environment-or-access",
    "unable-to-verify",
}
FINDING_ROUTES = {
    "sp-implement",
    "sp-debug",
    "sp-clarify",
    "sp-specify",
    "spx-implement",
    "spx-debug",
    "spx-clarify",
    "spx-specify",
    "human-action",
}


def new_human_acceptance_state() -> dict[str, Any]:
    """Return the stable empty state copied by implement closeout."""

    return {
        "version": 1,
        "schema_ref": ACCEPTANCE_SCHEMA_REF,
        "status": "draft",
        "source": {
            "implementation_summary": IMPLEMENTATION_SUMMARY_FILENAME,
            "implementation_summary_sha256": "",
            "prepared_from_sha256": "",
            "current_sha256": "",
        },
        "orientation": {
            "outcome": "",
            "why_it_matters": "",
            "user_visible_changes": [],
            "not_in_scope": [],
            "prerequisites": [],
            "start_here": "",
        },
        "scenarios": [],
        "cursor": {"scenario_id": None, "step_id": None},
        "findings": [],
        "overall": {
            "verdict": "pending",
            "summary": "",
            "next_command": ACCEPTANCE_COMMAND,
        },
    }


def prepare_human_acceptance(project_root: Path, feature_dir: Path) -> dict[str, Any]:
    """Create or freshness-check the post-implementation acceptance state."""

    root = project_root.resolve()
    resolved_feature_dir = _resolve_feature_dir(root, feature_dir)
    state_path = resolved_feature_dir / ACCEPTANCE_FILENAME
    with interprocess_lock(state_path.parent / ".human-acceptance.lock"):
        return _prepare_human_acceptance_locked(root, resolved_feature_dir)


def _prepare_human_acceptance_locked(
    root: Path, resolved_feature_dir: Path
) -> dict[str, Any]:
    summary_path = resolved_feature_dir / IMPLEMENTATION_SUMMARY_FILENAME
    state_path = resolved_feature_dir / ACCEPTANCE_FILENAME
    if not summary_path.is_file():
        return {
            "status": "blocked",
            "state_path": _display_path(state_path, root),
            "errors": [f"missing implementation summary: {summary_path}"],
            "next_command": "sp-implement or spx-implement",
        }

    summary_digest = _sha256(summary_path)
    current_digest = _implementation_snapshot_sha256(
        root, resolved_feature_dir, summary_digest
    )
    if state_path.exists():
        try:
            state = _read_state(state_path)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            return {
                "status": "conflict",
                "state_path": _display_path(state_path, root),
                "errors": [
                    f"existing acceptance state is unreadable and was preserved: {exc}"
                ],
                "next_command": ACCEPTANCE_COMMAND,
            }
        source = state.get("source")
        if not isinstance(source, dict):
            return {
                "status": "conflict",
                "state_path": _display_path(state_path, root),
                "errors": [
                    "existing acceptance state is missing source metadata and was preserved"
                ],
                "next_command": ACCEPTANCE_COMMAND,
            }
        prepared_digest = str(source.get("prepared_from_sha256") or "")
        source["implementation_summary_sha256"] = summary_digest
        source["current_sha256"] = current_digest
        if prepared_digest and prepared_digest != current_digest:
            state["status"] = "stale"
            overall = state.get("overall")
            if isinstance(overall, dict):
                overall["verdict"] = "pending"
                overall["summary"] = (
                    "Implementation evidence changed after this acceptance guide was prepared. "
                    "Rebuild the guide before continuing."
                )
                overall["next_command"] = ACCEPTANCE_COMMAND
            _write_state(state_path, state)
            return {
                "status": "stale",
                "state_path": _display_path(state_path, root),
                "prepared_from_sha256": prepared_digest,
                "current_sha256": current_digest,
                "next_command": ACCEPTANCE_COMMAND,
            }
        if not prepared_digest:
            source["prepared_from_sha256"] = current_digest
        _write_state(state_path, state)
        return {
            "status": str(state.get("status") or "draft"),
            "state_path": _display_path(state_path, root),
            "prepared_from_sha256": str(source.get("prepared_from_sha256") or ""),
            "current_sha256": current_digest,
            "next_command": ACCEPTANCE_COMMAND,
        }

    state = deepcopy(new_human_acceptance_state())
    state["source"]["implementation_summary_sha256"] = summary_digest
    state["source"]["prepared_from_sha256"] = current_digest
    state["source"]["current_sha256"] = current_digest
    _write_state(state_path, state)
    return {
        "status": "draft",
        "state_path": _display_path(state_path, root),
        "prepared_from_sha256": current_digest,
        "current_sha256": current_digest,
        "next_command": ACCEPTANCE_COMMAND,
    }


def validate_human_acceptance(
    project_root: Path,
    feature_dir: Path,
    *,
    require_accepted: bool = False,
) -> dict[str, Any]:
    """Validate acceptance shape, freshness, progress, and final verdict rules."""

    root = project_root.resolve()
    resolved_feature_dir = _resolve_feature_dir(root, feature_dir)
    state_path = resolved_feature_dir / ACCEPTANCE_FILENAME
    summary_path = resolved_feature_dir / IMPLEMENTATION_SUMMARY_FILENAME
    errors: list[str] = []
    if not state_path.is_file():
        errors.append(f"missing {ACCEPTANCE_FILENAME}")
        return _validation_payload(root, state_path, None, errors, stale=False)
    try:
        state = _read_state(state_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(f"invalid {ACCEPTANCE_FILENAME}: {exc}")
        return _validation_payload(root, state_path, None, errors, stale=False)

    status = str(state.get("status") or "")
    if state.get("version") != 1:
        errors.append("version must equal 1")
    if state.get("schema_ref") != ACCEPTANCE_SCHEMA_REF:
        errors.append(f"schema_ref must equal {ACCEPTANCE_SCHEMA_REF}")
    if status not in ACCEPTANCE_STATUSES:
        errors.append(f"unsupported acceptance status: {status or 'missing'}")

    source = _object(state, "source", errors)
    if source.get("implementation_summary") != IMPLEMENTATION_SUMMARY_FILENAME:
        errors.append(
            f"source.implementation_summary must equal {IMPLEMENTATION_SUMMARY_FILENAME}"
        )
    recorded_summary_digest = _required_string(
        source, "implementation_summary_sha256", "source", errors
    )
    prepared_digest = _required_string(source, "prepared_from_sha256", "source", errors)
    recorded_current = _required_string(source, "current_sha256", "source", errors)
    actual_summary_digest = _sha256(summary_path) if summary_path.is_file() else ""
    if not actual_summary_digest:
        errors.append(f"missing {IMPLEMENTATION_SUMMARY_FILENAME}")
    elif recorded_summary_digest != actual_summary_digest:
        errors.append(
            "source.implementation_summary_sha256 does not match the current implementation summary"
        )
    actual_digest = (
        _implementation_snapshot_sha256(
            root, resolved_feature_dir, actual_summary_digest
        )
        if actual_summary_digest
        else ""
    )
    stale = bool(actual_digest and prepared_digest and prepared_digest != actual_digest)
    if actual_digest and recorded_current != actual_digest:
        errors.append(
            "source.current_sha256 does not match the current implementation evidence snapshot"
        )
    if stale and status != "stale":
        errors.append(
            "implementation summary changed; status must be stale until the guide is rebuilt"
        )
    if status == "stale" and not stale:
        errors.append(
            "status is stale but the prepared and current implementation summary digests match"
        )

    orientation = _object(state, "orientation", errors)
    scenarios = state.get("scenarios")
    if not isinstance(scenarios, list):
        errors.append("scenarios must be an array")
        scenarios = []
    findings = state.get("findings")
    if not isinstance(findings, list):
        errors.append("findings must be an array")
        findings = []
    cursor = _object(state, "cursor", errors)
    overall = _object(state, "overall", errors)
    overall_verdict = str(overall.get("verdict") or "")
    if overall_verdict not in OVERALL_VERDICTS:
        errors.append("overall.verdict must be pending, pass, fail, or blocked")

    if status not in {"draft", "stale"}:
        for key in ("outcome", "why_it_matters", "start_here"):
            _required_string(orientation, key, "orientation", errors)
        _nonempty_string_list(
            orientation, "user_visible_changes", "orientation", errors
        )
        if not scenarios:
            errors.append(
                "at least one acceptance scenario is required outside draft/stale state"
            )

    scenario_ids: set[str] = set()
    step_ids: set[str] = set()
    required_verdicts: list[str] = []
    any_failed = False
    any_blocked = False
    for index, raw_scenario in enumerate(scenarios):
        prefix = f"scenarios[{index}]"
        if not isinstance(raw_scenario, dict):
            errors.append(f"{prefix} must be an object")
            continue
        scenario_id = _required_string(raw_scenario, "id", prefix, errors)
        if scenario_id in scenario_ids:
            errors.append(f"duplicate scenario id: {scenario_id}")
        scenario_ids.add(scenario_id)
        for key in ("title", "user_value", "start_state"):
            _required_string(raw_scenario, key, prefix, errors)
        required = raw_scenario.get("required")
        if not isinstance(required, bool):
            errors.append(f"{prefix}.required must be a boolean")
            required = False
        verdict = str(raw_scenario.get("verdict") or "")
        if verdict not in SCENARIO_VERDICTS:
            errors.append(f"{prefix}.verdict is invalid")
        if required:
            required_verdicts.append(verdict)
        any_failed = any_failed or verdict == "fail"
        any_blocked = any_blocked or verdict == "blocked"
        steps = raw_scenario.get("steps")
        if not isinstance(steps, list) or not steps:
            errors.append(f"{prefix}.steps must contain at least one step")
            continue
        scenario_step_results: list[str] = []
        for step_index, raw_step in enumerate(steps):
            step_prefix = f"{prefix}.steps[{step_index}]"
            if not isinstance(raw_step, dict):
                errors.append(f"{step_prefix} must be an object")
                continue
            step_id = _required_string(raw_step, "id", step_prefix, errors)
            if step_id in step_ids:
                errors.append(f"duplicate step id: {step_id}")
            step_ids.add(step_id)
            for key in ("action", "expected_result", "if_failed", "response_prompt"):
                _required_string(raw_step, key, step_prefix, errors)
            result = str(raw_step.get("result") or "")
            scenario_step_results.append(result)
            if result not in STEP_RESULTS:
                errors.append(f"{step_prefix}.result is invalid")
            any_failed = any_failed or result == "fail"
            any_blocked = any_blocked or result == "blocked"
            evidence = raw_step.get("evidence")
            if not isinstance(evidence, list):
                errors.append(f"{step_prefix}.evidence must be an array")
        if verdict == "pass" and any(
            result != "pass" for result in scenario_step_results
        ):
            errors.append(f"{prefix}.verdict=pass requires every step to pass")

    open_finding_ids: list[str] = []
    for index, raw_finding in enumerate(findings):
        prefix = f"findings[{index}]"
        if not isinstance(raw_finding, dict):
            errors.append(f"{prefix} must be an object")
            continue
        finding_id = _required_string(raw_finding, "id", prefix, errors)
        for key in ("scenario_id", "step_id", "expected", "observed"):
            _required_string(raw_finding, key, prefix, errors)
        if raw_finding.get("scenario_id") not in scenario_ids:
            errors.append(f"{prefix}.scenario_id must reference an existing scenario")
        if raw_finding.get("step_id") not in step_ids:
            errors.append(f"{prefix}.step_id must reference an existing step")
        if raw_finding.get("classification") not in FINDING_CLASSIFICATIONS:
            errors.append(f"{prefix}.classification is invalid")
        if raw_finding.get("route") not in FINDING_ROUTES:
            errors.append(f"{prefix}.route is invalid")
        finding_status = raw_finding.get("status")
        if finding_status not in {"open", "resolved"}:
            errors.append(f"{prefix}.status must be open or resolved")
        elif finding_status == "open":
            open_finding_ids.append(finding_id or prefix)
        evidence = raw_finding.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            errors.append(f"{prefix}.evidence must be a non-empty array")

    cursor_scenario = cursor.get("scenario_id")
    cursor_step = cursor.get("step_id")
    if status == "in_progress":
        if cursor_scenario not in scenario_ids:
            errors.append(
                "in_progress state requires cursor.scenario_id to name a scenario"
            )
        if cursor_step not in step_ids:
            errors.append("in_progress state requires cursor.step_id to name a step")
    elif cursor_scenario is not None or cursor_step is not None:
        if cursor_scenario not in scenario_ids or cursor_step not in step_ids:
            errors.append(
                "cursor must be null or reference an existing scenario and step"
            )

    if status == "accepted":
        if not required_verdicts or any(
            verdict != "pass" for verdict in required_verdicts
        ):
            errors.append("accepted status requires every required scenario to pass")
        if overall_verdict != "pass":
            errors.append("accepted status requires overall.verdict=pass")
        if open_finding_ids:
            errors.append(
                "accepted status requires every finding to be resolved; "
                f"open findings: {', '.join(open_finding_ids)}"
            )
    if status == "rejected" and not any_failed:
        errors.append("rejected status requires a failed step or scenario")
    if status == "rejected" and overall_verdict != "fail":
        errors.append("rejected status requires overall.verdict=fail")
    if status == "rejected" and not findings:
        errors.append("rejected status requires a routed acceptance finding")
    if status == "blocked" and not any_blocked and not findings:
        errors.append("blocked status requires a blocked step/scenario or a finding")
    if status == "blocked" and overall_verdict != "blocked":
        errors.append("blocked status requires overall.verdict=blocked")
    if status == "blocked" and not findings:
        errors.append("blocked status requires a routed acceptance finding")
    if require_accepted and status != "accepted":
        errors.append("human acceptance closeout requires status=accepted")

    return _validation_payload(root, state_path, state, errors, stale=stale)


def acceptance_closeout_blockers(
    feature_dir: Path,
    *,
    acceptance_errors: list[str] | None = None,
    hook_errors: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Build canonical blockers for prepare/validate/closeout CLI stops."""

    blockers: list[dict[str, Any]] = []
    closeout_argv = [
        "specify",
        "accept",
        "closeout",
        "--feature-dir",
        str(feature_dir),
        "--format",
        "json",
    ]
    errors = [
        str(item).strip() for item in (acceptance_errors or []) if str(item).strip()
    ]
    if errors:
        needs_human = any(
            "status=accepted" in item or "human acceptance" in item.casefold()
            for item in errors
        )
        blockers.append(
            _acceptance_blocker(
                blocker_id="ACCEPTANCE-NOT-CLOSED",
                category="human-review" if needs_human else "artifact-or-state",
                owner="user" if needs_human else "agent",
                summary=(
                    "Human product acceptance has not reached an accepted verdict."
                    if needs_human
                    else "The human acceptance artifact is incomplete or invalid."
                ),
                evidence=errors,
                exact_next_action=(
                    "Run sp-accept or spx-accept and guide the human through every required scenario before retrying closeout."
                    if needs_human
                    else "Repair or rebuild human-acceptance.json, then validate it before retrying closeout."
                ),
                unblock_criteria="human-acceptance.json is fresh, schema-valid, and records status=accepted with every required scenario passing.",
                resume_argv=closeout_argv,
                human_action_required=needs_human,
            )
        )
    hook_evidence = [
        str(item).strip() for item in (hook_errors or []) if str(item).strip()
    ]
    if hook_evidence:
        blockers.append(
            _acceptance_blocker(
                blocker_id="ACCEPTANCE-WORKFLOW-STATE",
                category="artifact-or-state",
                owner="agent",
                summary="Acceptance workflow state is not valid for closeout.",
                evidence=hook_evidence,
                exact_next_action="Repair the acceptance workflow state and rerun its deterministic validator.",
                unblock_criteria="The acceptance artifact and workflow-state validators both pass.",
                resume_argv=closeout_argv,
                human_action_required=False,
            )
        )
    return blockers


def _acceptance_blocker(
    *,
    blocker_id: str,
    category: str,
    owner: str,
    summary: str,
    evidence: list[str],
    exact_next_action: str,
    unblock_criteria: str,
    resume_argv: list[str],
    human_action_required: bool,
) -> dict[str, Any]:
    resume_command = subprocess.list2cmdline(resume_argv)
    blocker: dict[str, Any] = {
        "version": 1,
        "blocker_id": blocker_id,
        "code": "human-acceptance-blocked",
        "workflow": "sp-accept|spx-accept",
        "stage": "human acceptance closeout",
        "category": category,
        "owner": owner,
        "summary": summary,
        "details": "The feature cannot close until a fresh, explicit human product verdict satisfies the acceptance contract.",
        "evidence": evidence,
        "attempted_recovery": [
            {
                "action": "Validate the acceptance artifact and workflow state.",
                "result": "One or more closeout requirements remain unsatisfied.",
            }
        ],
        "exact_next_action": exact_next_action,
        "unblock_criteria": unblock_criteria,
        "affected_scope": ["human product acceptance", "feature closeout"],
        "can_continue": False,
        "human_action_required": human_action_required,
        "human_action_guide": None,
        "resume": {
            "instruction": f"After the acceptance state is repaired, run: {resume_command}",
            "command": resume_command,
            "argv": resume_argv,
        },
    }
    if human_action_required:
        blocker["human_action_guide"] = {
            "goal": "Decide whether the implemented feature works for a real user and explicitly accept or reject it.",
            "why_human": "Automated checks can prove technical conditions, but only a human can make the required product-acceptance judgment.",
            "prerequisites": [
                "Ask the agent to run sp-accept or spx-accept for this feature.",
                "Access to the real application entry point and any test account or data named by the guide.",
                "The generated implementation-summary.md and human-acceptance.json.",
            ],
            "safety_notes": [
                "Do not paste passwords, tokens, cookies, private keys, or unredacted personal data into chat.",
                "Do not approve from automated test output alone; observe each required user-facing result.",
                "If the app, account, environment, or expected behavior is unclear, record blocked instead of guessing.",
            ],
            "steps": [
                {
                    "order": 1,
                    "title": "Let the agent restore context",
                    "action": "Run sp-accept or spx-accept and read the short explanation of what changed, why it matters, and where to start.",
                    "command": None,
                    "expected_result": "You understand the feature outcome, prerequisites, and first real entry point without rereading the implementation history.",
                    "if_failed": "Ask the agent to repair the acceptance guide; do not continue with an unclear target.",
                },
                {
                    "order": 2,
                    "title": "Follow one observable step at a time",
                    "action": "For each required scenario, perform exactly the action the agent presents and report what you actually observe.",
                    "command": None,
                    "expected_result": "Every step receives pass, fail, or blocked plus evidence when requested.",
                    "if_failed": "Describe the observed result and let the agent record and route the finding; do not silently retry or reinterpret it.",
                },
                {
                    "order": 3,
                    "title": "Review the final verdict",
                    "action": "Accept only when every required scenario passes; otherwise reject or block and confirm the routed findings.",
                    "command": None,
                    "expected_result": "human-acceptance.json records one explicit, evidence-backed overall verdict.",
                    "if_failed": "Leave the verdict pending and name the unresolved scenario or decision.",
                },
                {
                    "order": 4,
                    "title": "Close the feature",
                    "action": f"After an accepted verdict, ask the agent to run `{resume_command}`.",
                    "command": resume_command,
                    "expected_result": "The closeout command succeeds without an acceptance or workflow-state blocker.",
                    "if_failed": "Return the complete blocker JSON to the agent and follow its exact resume instructions.",
                },
            ],
            "verification": [
                "Every required scenario and step passed",
                "The overall verdict is pass and status is accepted",
                "No open acceptance finding remains unresolved",
            ],
            "evidence_to_return": [
                "PASS, REJECT, or BLOCKED for each required scenario",
                "Any requested screenshots, output, or IDs with secrets redacted",
                "The final overall acceptance decision",
            ],
            "resume_instruction": f"Return the verdict and evidence to the agent, then resume with `{resume_command}`.",
        }
    return blocker


def _read_state(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("top-level JSON must be an object")
    return payload


def _write_state(path: Path, state: dict[str, Any]) -> None:
    atomic_write_text(
        path,
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
    )


def _resolve_feature_dir(project_root: Path, feature_dir: Path) -> Path:
    resolved = (
        feature_dir.resolve(strict=False)
        if feature_dir.is_absolute()
        else (project_root / feature_dir).resolve(strict=False)
    )
    try:
        relative = resolved.relative_to(project_root.resolve(strict=False))
    except ValueError as exc:
        raise ValueError("feature_dir must stay inside the current project") from exc
    if not relative.parts:
        raise ValueError("feature_dir must identify a directory below the project root")
    return resolved


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _implementation_snapshot_sha256(
    project_root: Path, feature_dir: Path, summary_digest: str
) -> str:
    """Bind acceptance to summary plus current implementation working-tree evidence."""

    digest = hashlib.sha256()
    digest.update(f"summary:{summary_digest}\n".encode("utf-8"))
    try:
        feature_relative = feature_dir.resolve().relative_to(project_root.resolve())
        feature_pathspec = feature_relative.as_posix().rstrip("/") + "/**"
    except ValueError:
        feature_relative = None
        feature_pathspec = ""
    exclusions = [
        ":(exclude).specify/runtime/**",
        ":(exclude).planning/**",
    ]
    if feature_pathspec:
        exclusions.append(f":(exclude){feature_pathspec}")

    head = _run_git_bytes(project_root, ["rev-parse", "HEAD"])
    if head is None:
        _update_no_git_snapshot(digest, project_root, feature_relative)
        return digest.hexdigest()
    digest.update(b"head:")
    digest.update(head.strip())
    digest.update(b"\n")

    diff = _run_git_bytes(
        project_root, ["diff", "--binary", "HEAD", "--", ".", *exclusions]
    )
    if diff is not None:
        digest.update(b"diff:\n")
        digest.update(diff)

    untracked = _run_git_bytes(
        project_root,
        [
            "ls-files",
            "--others",
            "--exclude-standard",
            "-z",
            "--",
            ".",
            *exclusions,
        ],
    )
    if untracked:
        for raw_path in sorted(path for path in untracked.split(b"\0") if path):
            relative = raw_path.decode("utf-8", errors="surrogateescape")
            digest.update(b"untracked:")
            digest.update(raw_path)
            digest.update(b"\0")
            target = project_root / relative
            if target.is_file():
                digest.update(target.read_bytes())
            digest.update(b"\0")
    return digest.hexdigest()


def _update_no_git_snapshot(
    digest: Any,
    project_root: Path,
    feature_relative: Path | None,
) -> None:
    """Hash a deterministic project tree when Git cannot provide a snapshot."""

    root = project_root.resolve(strict=False)
    ignore_spec = _root_gitignore_spec(root)
    digest.update(b"tree-fallback:v1\n")
    pending = [root]
    while pending:
        directory = pending.pop()
        with os.scandir(directory) as iterator:
            entries = sorted(iterator, key=lambda entry: entry.name)
        child_directories: list[Path] = []
        for entry in entries:
            entry_path = Path(entry.path)
            relative = entry_path.relative_to(root)
            is_junction = getattr(entry_path, "is_junction", None)
            is_link = entry.is_symlink() or (
                callable(is_junction) and bool(is_junction())
            )
            is_directory = not is_link and entry.is_dir(follow_symlinks=False)
            if _no_git_snapshot_excluded(
                relative,
                feature_relative,
                ignore_spec=ignore_spec,
                is_directory=is_directory,
            ):
                continue
            if is_link:
                _update_no_git_snapshot_record(
                    digest,
                    "link",
                    relative,
                    os.readlink(entry_path),
                )
            elif is_directory:
                child_directories.append(entry_path)
            elif entry.is_file(follow_symlinks=False):
                _update_no_git_snapshot_record(
                    digest,
                    "file",
                    relative,
                    _sha256(entry_path),
                )
            else:
                _update_no_git_snapshot_record(digest, "other", relative, "")
        pending.extend(reversed(child_directories))


def _no_git_snapshot_excluded(
    relative: Path,
    feature_relative: Path | None,
    *,
    ignore_spec: pathspec.GitIgnoreSpec | None,
    is_directory: bool,
) -> bool:
    if feature_relative is not None and (
        relative == feature_relative or feature_relative in relative.parents
    ):
        return True
    parts = relative.parts
    if not parts:
        return False
    if parts[0] in {".git", ".planning"}:
        return True
    if len(parts) >= 2 and parts[:2] == (".specify", "runtime"):
        return True
    if ignore_spec is None:
        return False
    normalized = relative.as_posix() + ("/" if is_directory else "")
    return ignore_spec.match_file(normalized)


def _root_gitignore_spec(project_root: Path) -> pathspec.GitIgnoreSpec | None:
    ignore_path = project_root / ".gitignore"
    try:
        lines = ignore_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return None
    if not lines:
        return None
    return pathspec.GitIgnoreSpec.from_lines(lines)


def _update_no_git_snapshot_record(
    digest: Any,
    kind: str,
    relative: Path,
    value: str,
) -> None:
    record = json.dumps(
        [kind, relative.as_posix(), value],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    digest.update(record.encode("utf-8", errors="surrogateescape"))
    digest.update(b"\n")


def _run_git_bytes(project_root: Path, args: list[str]) -> bytes | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=project_root,
            capture_output=True,
            check=False,
        )
    except (OSError, ValueError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _object(payload: dict[str, Any], key: str, errors: list[str]) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        errors.append(f"{key} must be an object")
        return {}
    return value


def _required_string(
    payload: dict[str, Any], key: str, prefix: str, errors: list[str]
) -> str:
    value = str(payload.get(key) or "").strip()
    if not value:
        errors.append(f"{prefix}.{key} must be a non-empty string")
    return value


def _nonempty_string_list(
    payload: dict[str, Any], key: str, prefix: str, errors: list[str]
) -> None:
    value = payload.get(key)
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item.strip() for item in value)
    ):
        errors.append(f"{prefix}.{key} must be a non-empty string array")


def _validation_payload(
    project_root: Path,
    state_path: Path,
    state: dict[str, Any] | None,
    errors: list[str],
    *,
    stale: bool,
) -> dict[str, Any]:
    overall = (state or {}).get("overall")
    next_command_value = (
        overall.get("next_command") if isinstance(overall, dict) else None
    )
    return {
        "status": str((state or {}).get("status") or "missing"),
        "valid": not errors,
        "accepted": not errors and (state or {}).get("status") == "accepted",
        "stale": stale,
        "state_path": _display_path(state_path, project_root),
        "errors": errors,
        "next_command": str(next_command_value).strip()
        if next_command_value
        else ACCEPTANCE_COMMAND,
    }


def _display_path(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()
