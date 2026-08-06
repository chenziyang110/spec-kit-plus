"""Deterministic authoring control plane for task-index.json and tasks.md."""

from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping

from .atomic_io import read_local_state_text, safe_local_state_path
from .workflow_transaction import (
    WorkflowTransactionError,
    apply_workflow_transaction,
)


class TaskAuthoringError(RuntimeError):
    """Raised when a task package mutation is invalid or unsafe."""


_TASK_ID_RE = re.compile(r"^T\d+$")
_TERMINAL_STATUSES = {"accepted", "deferred"}
_AUTHORING_MUTABLE_STATUSES = {"pending", "ready", "blocked", "failed"}
_PROTECTED_ROOT_FIELDS = {"version", "status", "tasks", "transition"}
_PROTECTED_TASK_FIELDS = {"status", "lifecycle_ref", "packet_ref", "result_ref"}
_AUTHORED_TASK_FIELDS = {
    "id",
    "task_id",
    "story_id",
    "phase",
    "objective",
    "title",  # alias for objective; normalized away
    "description",
    "dependencies",
    "depends_on",
    "parallel",
    "batch",
    "batch_id",
    "join_point",
    "join_point_id",
    "owner",
    "execution_mode",
    "task_kind",
    "priority",
    "risk",
    "risk_level",
    "expected_write_scope",
    "write_scope",
    "read_scope",
    "required_refs",
    "authoritative_refs",
    "policy_refs",
    "forbidden_drift",
    "hard_rules",
    "acceptance",
    "done_condition",  # alias for acceptance; normalized away
    "acceptance_refs",
    "verification",
    "required_validation",
    "task_checks",
    "consumer_surfaces",
    "required_consumer_evidence",
    "required_evidence",
    "must_preserve_ids",
    "must_preserve_refs",
    "consequence_obligation_ids",
    "consequence_obligation_refs",
    "capability_operations",
    "capability_operation_refs",
    "fidelity_refs",
    "user_confirmed_deferral_refs",
    "implementation_target_ref",
    "stop_and_reopen_conditions",
    "recovery",
    "ui_contract",
    "no_new_test_rationale",
    "replacement_validation",
    "residual_risk",
    "skills",
    "notes",
}
_OBSOLETE_TASK_FIELDS = {
    "ui_contract_version",
    "ui_fidelity_requirements",
    "ui_fidelity_evidence",
}


def _json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _project_feature(
    project_root: Path, feature_dir: Path | str
) -> tuple[Path, Path]:
    root = safe_local_state_path(Path(project_root))
    candidate = Path(feature_dir)
    if not candidate.is_absolute():
        candidate = root / candidate
    feature = safe_local_state_path(candidate, root=root)
    if not feature.is_dir():
        raise TaskAuthoringError(f"feature directory does not exist: {feature}")
    return root, feature


def _read_object(path: Path, *, root: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(read_local_state_text(path, root=root))
    except FileNotFoundError as exc:
        raise TaskAuthoringError(f"{label} is missing: {path}") from exc
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TaskAuthoringError(f"{label} is invalid: {exc}") from exc
    if not isinstance(payload, dict):
        raise TaskAuthoringError(f"{label} must contain a JSON object")
    return payload


def _load_template(root: Path) -> dict[str, Any]:
    return _read_object(
        root / ".specify" / "templates" / "task-index-template.json",
        root=root,
        label="task-index template",
    )


def _normalize_task_id(value: object) -> str:
    task_id = str(value or "").strip().upper()
    if not _TASK_ID_RE.fullmatch(task_id):
        raise TaskAuthoringError(f"task id must match T<digits>: {value!r}")
    return task_id


def _string_list(value: object, *, label: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise TaskAuthoringError(f"{label} must be an array")
    result: list[str] = []
    for item in value:
        text = str(item).strip()
        if not text:
            raise TaskAuthoringError(f"{label} must contain non-empty strings")
        if text not in result:
            result.append(text)
    return result


def _normalize_task(
    raw_task: object, *, allow_runtime_fields: bool
) -> dict[str, Any]:
    if not isinstance(raw_task, Mapping):
        raise TaskAuthoringError("each task must be a JSON object")
    task = deepcopy(dict(raw_task))
    title = str(task.get("title") or "").strip()
    if title and not str(task.get("objective") or "").strip():
        task["objective"] = title
    task.pop("title", None)
    if "acceptance" not in task and "done_condition" in task:
        task["acceptance"] = task["done_condition"]
    task.pop("done_condition", None)
    obsolete = sorted(_OBSOLETE_TASK_FIELDS & task.keys())
    if obsolete:
        raise TaskAuthoringError(
            "task contains obsolete fields: " + ", ".join(obsolete)
        )
    protected = sorted(_PROTECTED_TASK_FIELDS & task.keys())
    if protected and not allow_runtime_fields:
        raise TaskAuthoringError(
            "task contains CLI-owned fields: " + ", ".join(protected)
        )
    unknown = sorted(set(task) - _AUTHORED_TASK_FIELDS - _PROTECTED_TASK_FIELDS)
    if unknown and not allow_runtime_fields:
        raise TaskAuthoringError(
            "task contains unsupported fields: "
            + ", ".join(unknown)
            + "; accepted fields include objective (alias: title), acceptance (alias: done_condition)"
        )
    task_id = _normalize_task_id(task.get("id", task.get("task_id")))
    objective = str(task.get("objective") or "").strip()
    if not objective:
        raise TaskAuthoringError(
            f"{task_id} objective is required (title is accepted as an alias)"
        )
    task.pop("task_id", None)
    task["id"] = task_id
    task["objective"] = objective
    task["dependencies"] = [
        _normalize_task_id(item)
        for item in _string_list(
            task.get("dependencies", task.get("depends_on", [])),
            label=f"{task_id} dependencies",
        )
    ]
    task.pop("depends_on", None)
    task["expected_write_scope"] = _string_list(
        task.get("expected_write_scope", task.get("write_scope", [])),
        label=f"{task_id} expected_write_scope",
    )
    task.pop("write_scope", None)
    for key in (
        "read_scope",
        "required_refs",
        "authoritative_refs",
        "policy_refs",
        "forbidden_drift",
        "hard_rules",
        "acceptance",
        "verification",
        "required_validation",
        "task_checks",
        "consumer_surfaces",
        "required_consumer_evidence",
        "required_evidence",
        "must_preserve_ids",
        "must_preserve_refs",
        "consequence_obligation_ids",
        "consequence_obligation_refs",
        "capability_operations",
        "capability_operation_refs",
        "fidelity_refs",
        "acceptance_refs",
        "user_confirmed_deferral_refs",
        "stop_and_reopen_conditions",
        "skills",
    ):
        if key in task:
            task[key] = _string_list(task[key], label=f"{task_id} {key}")
    status = str(task.get("status") or "pending").strip().lower()
    if status not in {
        "pending",
        "ready",
        "in_progress",
        "implemented",
        "accepted",
        "blocked",
        "failed",
        "deferred",
    }:
        raise TaskAuthoringError(f"{task_id} status is invalid: {status}")
    task["status"] = status
    return task


def _normalize_tasks(
    raw_tasks: object, *, allow_runtime_fields: bool
) -> list[dict[str, Any]]:
    if not isinstance(raw_tasks, list):
        raise TaskAuthoringError("tasks must be an array")
    tasks = [
        _normalize_task(item, allow_runtime_fields=allow_runtime_fields)
        for item in raw_tasks
    ]
    seen: set[str] = set()
    for task in tasks:
        task_id = task["id"]
        if task_id in seen:
            raise TaskAuthoringError(f"duplicate task id: {task_id}")
        seen.add(task_id)
    return tasks


def _expand_ui_contracts(
    root: Path, tasks: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    defaults: dict[str, Any] | None = None
    for task in tasks:
        if "ui_contract" not in task or task["ui_contract"] is None:
            continue
        ui_contract = task["ui_contract"]
        if not isinstance(ui_contract, Mapping):
            raise TaskAuthoringError(
                f"{task['id']} ui_contract must be a JSON object"
            )
        if not ui_contract:
            continue
        if defaults is None:
            packet_template = _read_object(
                root / ".specify" / "templates" / "task-packet-template.json",
                root=root,
                label="task-packet template",
            )
            raw_defaults = packet_template.get("ui_contract")
            if not isinstance(raw_defaults, dict) or not raw_defaults:
                raise TaskAuthoringError(
                    "task-packet template ui_contract must be a non-empty JSON object"
                )
            defaults = raw_defaults
        unknown = sorted(set(ui_contract) - set(defaults))
        if unknown:
            raise TaskAuthoringError(
                f"{task['id']} ui_contract contains unsupported fields: "
                + ", ".join(unknown)
            )
        expanded = deepcopy(defaults)
        expanded.update(deepcopy(dict(ui_contract)))
        task["ui_contract"] = expanded
    return tasks


def _overlay_definition(
    root: Path, template: dict[str, Any], definition: Mapping[str, Any]
) -> tuple[dict[str, Any], str]:
    allowed = set(template) | {"title"}
    unknown = sorted(set(definition) - allowed)
    if unknown:
        raise TaskAuthoringError(
            "task definition contains unsupported root fields: " + ", ".join(unknown)
        )
    payload = deepcopy(template)
    title = str(definition.get("title") or "Feature implementation").strip()
    for key, value in definition.items():
        if key == "title":
            continue
        if key in {"version", "status", "transition"}:
            raise TaskAuthoringError(f"{key} is CLI-owned and cannot be authored")
        payload[key] = deepcopy(value)
    payload["version"] = 2
    payload["status"] = "draft"
    payload["tasks"] = _expand_ui_contracts(
        root,
        _normalize_tasks(payload.get("tasks"), allow_runtime_fields=False),
    )
    transition = payload.get("transition")
    if not isinstance(transition, dict):
        transition = {}
        payload["transition"] = transition
    transition.update(
        {
            "version": 1,
            "status": "blocked",
            "source_ref": "task-index.json",
            "blockers": ["task package has not been finalized"],
            "next_action": "Run `specify-runtime tasks finalize` after task review.",
        }
    )
    return payload, title or "Feature implementation"


def _render_list(values: object) -> str:
    if not isinstance(values, list) or not values:
        return "none"
    return ", ".join(f"`{str(value)}`" for value in values)


def _render_tasks_markdown(task_index: Mapping[str, Any], *, title: str) -> str:
    tasks = task_index.get("tasks")
    if not isinstance(tasks, list):
        raise TaskAuthoringError("task-index tasks must be an array")
    lines = [
        f"# Tasks: {title}",
        "",
        "> Generated by `specify-runtime tasks`; `task-index.json` is canonical.",
        "",
        "## Task List",
        "",
    ]
    for raw_task in tasks:
        task = dict(raw_task)
        checked = "x" if task.get("status") in _TERMINAL_STATUSES else " "
        markers: list[str] = []
        if task.get("parallel") is True:
            markers.append("[P]")
        story_id = str(task.get("story_id") or "").strip()
        if story_id:
            markers.append(f"[{story_id}]")
        marker_text = (" " + " ".join(markers)) if markers else ""
        lines.append(
            f"- [{checked}] {task['id']}{marker_text} {task['objective']}"
        )

    lines.extend(
        [
            "",
            "## Consequence Obligation Mapping",
            "",
            "| Obligation ID | Task IDs |",
            "| --- | --- |",
        ]
    )
    consequence_map: dict[str, list[str]] = {}
    for raw_task in tasks:
        task = dict(raw_task)
        for obligation_id in task.get("consequence_obligation_ids", []):
            consequence_map.setdefault(str(obligation_id), []).append(str(task["id"]))
    if consequence_map:
        for obligation_id, task_ids in consequence_map.items():
            lines.append(f"| {obligation_id} | {', '.join(task_ids)} |")
    else:
        lines.append("| None | None |")

    for raw_task in tasks:
        task = dict(raw_task)
        task_id = str(task["id"])
        lines.extend(
            [
                "",
                f"## {task_id} — {task['objective']}",
                "",
                "### Scope Boundaries",
                "",
                "| Field | Value |",
                "| --- | --- |",
                f"| read_scope | {_render_list(task.get('read_scope'))} |",
                f"| write_scope | {_render_list(task.get('expected_write_scope'))} |",
                f"| required_refs | {_render_list(task.get('required_refs'))} |",
                f"| dependencies | {_render_list(task.get('dependencies'))} |",
                "",
                "### Acceptance and Verification",
                "",
                f"- Acceptance: {_render_list(task.get('acceptance'))}",
                f"- Verification: {_render_list(task.get('verification'))}",
            ]
        )
        ui_contract = task.get("ui_contract")
        if isinstance(ui_contract, dict) and any(ui_contract.values()):
            lines.extend(
                [
                    "",
                    "### UI Implementation Contract",
                    "",
                    "| Field | Value |",
                    "| --- | --- |",
                    f"| ui_contract_ref | task-index.json#/tasks/{task_id}/ui_contract |",
                    f"| fidelity_level | {ui_contract.get('fidelity_level', 'none')} |",
                    f"| required_states | {_render_list(ui_contract.get('required_states'))} |",
                    f"| required_evidence | {_render_list(ui_contract.get('required_evidence'))} |",
                ]
            )
    return "\n".join(lines).rstrip() + "\n"


def _receipt(
    *,
    status: str,
    task_index: Mapping[str, Any],
    task_index_bytes: bytes,
    markdown_bytes: bytes,
    transaction: object,
) -> dict[str, Any]:
    transaction_payload = transaction.to_dict()
    return {
        "status": "ok",
        "package_status": status,
        **transaction_payload,
        "task_count": len(task_index.get("tasks", [])),
        "task_index_ref": next(
            path
            for path in transaction_payload["changed_paths"]
            if path.endswith("/task-index.json")
        ),
        "tasks_ref": next(
            path
            for path in transaction_payload["changed_paths"]
            if path.endswith("/tasks.md")
        ),
        "task_index_sha256": _sha256(task_index_bytes),
        "tasks_sha256": _sha256(markdown_bytes),
    }


def _commit(
    root: Path,
    feature: Path,
    task_index: dict[str, Any],
    *,
    title: str,
    kind: str,
) -> dict[str, Any]:
    task_index_bytes = _json_bytes(task_index)
    markdown_bytes = _render_tasks_markdown(task_index, title=title).encode("utf-8")
    try:
        transaction = apply_workflow_transaction(
            root,
            kind=kind,
            updates={
                feature / "task-index.json": task_index_bytes,
                feature / "tasks.md": markdown_bytes,
            },
        )
    except WorkflowTransactionError as exc:
        raise TaskAuthoringError(str(exc)) from exc
    return _receipt(
        status=str(task_index["status"]),
        task_index=task_index,
        task_index_bytes=task_index_bytes,
        markdown_bytes=markdown_bytes,
        transaction=transaction,
    )


def build_task_package(
    project_root: Path,
    feature_dir: Path | str,
    definition: Mapping[str, Any],
) -> dict[str, Any]:
    root, feature = _project_feature(project_root, feature_dir)
    if (feature / "task-index.json").exists() or (feature / "tasks.md").exists():
        raise TaskAuthoringError(
            "task package already exists; use tasks upsert, set-root, or remove"
        )
    task_index, title = _overlay_definition(root, _load_template(root), definition)
    return _commit(
        root,
        feature,
        task_index,
        title=title,
        kind="tasks.build",
    )


def _load_task_package(
    project_root: Path, feature_dir: Path | str
) -> tuple[Path, Path, dict[str, Any], str]:
    root, feature = _project_feature(project_root, feature_dir)
    task_index = _read_object(
        feature / "task-index.json", root=root, label="task-index.json"
    )
    if task_index.get("version") != 2:
        raise TaskAuthoringError("task-index.json must use version 2")
    tasks = _expand_ui_contracts(
        root,
        _normalize_tasks(task_index.get("tasks"), allow_runtime_fields=True),
    )
    task_index["tasks"] = tasks
    title = feature.name
    tasks_path = feature / "tasks.md"
    if tasks_path.is_file():
        try:
            first_line = read_local_state_text(tasks_path, root=root).splitlines()[0]
            if first_line.startswith("# Tasks:"):
                title = first_line.partition(":")[2].strip() or title
        except (OSError, UnicodeError, IndexError):
            pass
    return root, feature, task_index, title


def upsert_task(
    project_root: Path,
    feature_dir: Path | str,
    task: Mapping[str, Any],
) -> dict[str, Any]:
    root, feature, task_index, title = _load_task_package(
        project_root, feature_dir
    )
    normalized = _expand_ui_contracts(
        root,
        [_normalize_task(task, allow_runtime_fields=False)],
    )[0]
    tasks = task_index["tasks"]
    for index, existing in enumerate(tasks):
        if existing["id"] != normalized["id"]:
            continue
        existing_status = str(existing.get("status") or "pending")
        if existing_status not in _AUTHORING_MUTABLE_STATUSES:
            raise TaskAuthoringError(
                f"{normalized['id']} has runtime status {existing_status} and cannot "
                "be replaced through task authoring"
            )
        tasks[index] = normalized
        break
    else:
        tasks.append(normalized)
    task_index["status"] = "draft"
    transition = task_index.get("transition")
    if isinstance(transition, dict):
        transition["status"] = "blocked"
        transition["blockers"] = ["task package changed after its last finalize"]
        transition["next_action"] = "Run `specify-runtime tasks finalize`."
    return _commit(
        root,
        feature,
        task_index,
        title=title,
        kind="tasks.upsert",
    )


def remove_task(
    project_root: Path, feature_dir: Path | str, task_id: str
) -> dict[str, Any]:
    root, feature, task_index, title = _load_task_package(
        project_root, feature_dir
    )
    normalized_id = _normalize_task_id(task_id)
    tasks = task_index["tasks"]
    existing = next((task for task in tasks if task["id"] == normalized_id), None)
    if existing is None:
        raise TaskAuthoringError(f"unknown task: {normalized_id}")
    existing_status = str(existing.get("status") or "pending")
    if existing_status not in _AUTHORING_MUTABLE_STATUSES:
        raise TaskAuthoringError(
            f"{normalized_id} has runtime status {existing_status} and cannot be "
            "removed through task authoring"
        )
    task_index["tasks"] = [task for task in tasks if task["id"] != normalized_id]
    for task in task_index["tasks"]:
        if normalized_id in task.get("dependencies", []):
            raise TaskAuthoringError(
                f"{normalized_id} is still required by {task['id']}; update that task first"
            )
    task_index["status"] = "draft"
    transition = task_index.get("transition")
    if isinstance(transition, dict):
        transition["status"] = "blocked"
        transition["blockers"] = ["task package changed after its last finalize"]
        transition["next_action"] = "Run `specify-runtime tasks finalize`."
    return _commit(
        root,
        feature,
        task_index,
        title=title,
        kind="tasks.remove",
    )


def set_task_root_fields(
    project_root: Path,
    feature_dir: Path | str,
    patch: Mapping[str, Any],
) -> dict[str, Any]:
    root, feature, task_index, title = _load_task_package(
        project_root, feature_dir
    )
    template = _load_template(root)
    unknown = sorted(set(patch) - set(template))
    protected = sorted(set(patch) & _PROTECTED_ROOT_FIELDS)
    if unknown:
        raise TaskAuthoringError(
            "root patch contains unsupported fields: " + ", ".join(unknown)
        )
    if protected:
        detail = ", ".join(protected)
        if "transition" in protected:
            raise TaskAuthoringError(
                "root patch contains CLI-owned fields: "
                + detail
                + "; transition is written only by tasks finalize/handoff "
                "(do not set next_action/status via set-root)"
            )
        raise TaskAuthoringError(
            "root patch contains CLI-owned fields: " + detail
        )
    for key, value in patch.items():
        task_index[key] = deepcopy(value)
    task_index["status"] = "draft"
    return _commit(
        root,
        feature,
        task_index,
        title=title,
        kind="tasks.set-root",
    )


def _validate_dependency_graph(tasks: list[dict[str, Any]]) -> None:
    ids = {task["id"] for task in tasks}
    for task in tasks:
        for dependency in task["dependencies"]:
            if dependency not in ids:
                raise TaskAuthoringError(
                    f"{task['id']} references unknown dependency {dependency}"
                )
            if dependency == task["id"]:
                raise TaskAuthoringError(f"{task['id']} cannot depend on itself")

    visiting: set[str] = set()
    visited: set[str] = set()
    by_id = {task["id"]: task for task in tasks}

    def visit(task_id: str) -> None:
        if task_id in visited:
            return
        if task_id in visiting:
            raise TaskAuthoringError(f"task dependency cycle contains {task_id}")
        visiting.add(task_id)
        for dependency in by_id[task_id]["dependencies"]:
            visit(dependency)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in by_id:
        visit(task_id)


def _validate_acceptance_projection(feature: Path, task_index: dict[str, Any]) -> None:
    plan_path = feature / "plan-contract.json"
    if not plan_path.is_file():
        nested = feature / "plan" / "plan-contract.json"
        plan_path = nested if nested.is_file() else plan_path
    if not plan_path.is_file():
        return
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TaskAuthoringError(f"plan-contract.json is invalid: {exc}") from exc
    if not isinstance(plan, dict):
        raise TaskAuthoringError("plan-contract.json must contain an object")
    expected = plan.get("acceptance_refs", [])
    if not isinstance(expected, list):
        raise TaskAuthoringError("plan-contract acceptance_refs must be an array")
    task_index["acceptance_refs"] = _normalize_task_index_acceptance_refs(
        task_index.get("acceptance_refs"),
        expected,
        plan_label="plan-contract.json",
    )
    _rewrite_acceptance_source_refs(
        task_index,
        expected,
        plan_label="plan-contract.json",
    )
    if expected:
        for field in (
            "official_entrypoints",
            "system_review_scenarios",
            "review_obligations",
            "human_acceptance_obligations",
            "human_acceptance_scenarios",
        ):
            if not isinstance(task_index.get(field), list) or not task_index[field]:
                raise TaskAuthoringError(
                    f"task-index {field} is required when acceptance_refs are present"
                )


def _parse_plan_acceptance_pointer(value: str, plan_label: str) -> int | None:
    text = str(value or "").strip()
    for prefix in (
        f"{plan_label}#/acceptance_refs/",
        "plan-contract.json#/acceptance_refs/",
        "#/acceptance_refs/",
    ):
        if not text.startswith(prefix):
            continue
        suffix = text[len(prefix) :]
        if not suffix.isdigit():
            return None
        return int(suffix)
    return None


def _normalize_task_index_acceptance_refs(
    actual: object,
    expected: list[Any],
    *,
    plan_label: str,
) -> list[Any]:
    if actual is None:
        if not expected:
            return []
        preview = ", ".join(str(item) for item in expected) or "[]"
        raise TaskAuthoringError(
            "task-index acceptance_refs must exactly copy "
            "plan-contract.acceptance_refs values in order "
            f"(example values: [{preview}]); pointer form "
            f"{plan_label}#/acceptance_refs/N is also accepted and rewritten"
        )
    if not isinstance(actual, list):
        raise TaskAuthoringError("task-index acceptance_refs must be an array")
    if actual == expected:
        return deepcopy(expected)
    expanded: list[Any] = []
    for item in actual:
        text = str(item).strip()
        if not text:
            raise TaskAuthoringError(
                "task-index acceptance_refs must contain non-empty strings"
            )
        index = _parse_plan_acceptance_pointer(text, plan_label)
        if index is not None:
            if index < 0 or index >= len(expected):
                raise TaskAuthoringError(
                    f"task-index acceptance_refs pointer {text!r} is out of range "
                    f"for {plan_label} ({len(expected)} refs)"
                )
            expanded.append(expected[index])
            continue
        expanded.append(text)
    if expanded != expected:
        expected_preview = ", ".join(str(item) for item in expected)
        actual_preview = ", ".join(str(item) for item in expanded)
        raise TaskAuthoringError(
            "task-index acceptance_refs must exactly preserve "
            "plan-contract.acceptance_refs values and order; "
            f"expected [{expected_preview}], got [{actual_preview}] "
            f"(pointer form {plan_label}#/acceptance_refs/N is accepted and rewritten)"
        )
    return deepcopy(expected)


def _rewrite_acceptance_source_refs(
    task_index: dict[str, Any],
    expected: list[Any],
    *,
    plan_label: str,
) -> None:
    pointer_to_value: dict[str, Any] = {}
    for index, value in enumerate(expected):
        pointer_to_value[f"{plan_label}#/acceptance_refs/{index}"] = value
        pointer_to_value[f"plan-contract.json#/acceptance_refs/{index}"] = value
        pointer_to_value[f"#/acceptance_refs/{index}"] = value
    for field in ("human_acceptance_obligations", "review_obligations"):
        rows = task_index.get(field)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            source = str(row.get("source_ref") or "").strip()
            if source in pointer_to_value:
                row["source_ref"] = pointer_to_value[source]
    for field in ("system_review_scenarios", "human_acceptance_scenarios"):
        rows = task_index.get(field)
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict) or "acceptance_refs" not in row:
                continue
            refs = row.get("acceptance_refs")
            if not isinstance(refs, list):
                continue
            row["acceptance_refs"] = [
                pointer_to_value.get(str(item).strip(), item) for item in refs
            ]


def finalize_task_package(
    project_root: Path, feature_dir: Path | str
) -> dict[str, Any]:
    root, feature, task_index, title = _load_task_package(
        project_root, feature_dir
    )
    tasks = task_index["tasks"]
    if not tasks:
        raise TaskAuthoringError("task package must contain at least one task")
    _validate_dependency_graph(tasks)
    _validate_acceptance_projection(feature, task_index)
    task_index["status"] = "ready"
    transition = task_index.get("transition")
    if not isinstance(transition, dict):
        transition = {}
        task_index["transition"] = transition
    transition.update(
        {
            "version": 1,
            "status": "ready",
            "source_ref": "task-index.json",
            "required_refs": list(task_index.get("acceptance_refs", [])),
            "blockers": [],
            "next_action": "Run sp-implement or spx-implement.",
            "recovery": None,
        }
    )
    return _commit(
        root,
        feature,
        task_index,
        title=title,
        kind="tasks.finalize",
    )


def write_task_handoff(
    project_root: Path,
    feature_dir: Path | str,
    *,
    target: str,
) -> dict[str, Any]:
    normalized_target = target.strip().lower()
    if normalized_target not in {"tasks", "implement"}:
        raise TaskAuthoringError("target must be tasks or implement")
    root, feature, task_index, _ = _load_task_package(project_root, feature_dir)
    transition = task_index.get("transition")
    if (
        task_index.get("status") != "ready"
        or not isinstance(transition, dict)
        or transition.get("status") != "ready"
    ):
        raise TaskAuthoringError(
            "task package must be finalized before creating a handoff"
        )

    task_index_bytes = (feature / "task-index.json").read_bytes()
    handoff = {
        "version": 1,
        "status": "ready",
        "target": normalized_target,
        "task_index_ref": "task-index.json",
        "tasks_ref": "tasks.md",
        "task_index_sha256": _sha256(task_index_bytes),
        "source_revision": deepcopy(task_index.get("source_revision")),
        "task_count": len(task_index["tasks"]),
    }
    raw = _json_bytes(handoff)
    name = f"handoff-to-{normalized_target}.json"
    try:
        transaction = apply_workflow_transaction(
            root,
            kind="tasks.handoff",
            updates={feature / name: raw},
        )
    except WorkflowTransactionError as exc:
        raise TaskAuthoringError(str(exc)) from exc
    transaction_payload = transaction.to_dict()
    handoff_ref = next(
        path
        for path in transaction_payload["changed_paths"]
        if path.endswith(f"/{name}") or path == name
    )
    return {
        "status": "ok",
        **transaction_payload,
        "target": normalized_target,
        "handoff_ref": handoff_ref,
        "handoff_sha256": _sha256(raw),
        "task_count": len(task_index["tasks"]),
    }


__all__ = [
    "TaskAuthoringError",
    "build_task_package",
    "finalize_task_package",
    "remove_task",
    "set_task_root_fields",
    "upsert_task",
    "write_task_handoff",
]
