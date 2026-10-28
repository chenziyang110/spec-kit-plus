"""Score complete work-to-cognition episodes against independently frozen facts.

This consumes evidence and never executes or authenticates an Agent. Mechanism
replay, actual work, Learning ablation, and installed-entry coverage stay separate.
The older navigation evaluator and its 120 observations are not this denominator.
"""
from __future__ import annotations

import argparse
import math
import statistics
import sys
from pathlib import Path
from typing import Any

from cognition_eval import artifact, binding, digest, load, write_new

SCHEMA = "cognition-loop-evaluation.v1"
PROFILES = ("classic", "advanced")
KINDS = ("mechanism_replay", "actual_agent_work", "learning_ablation")
LEARNING_ARMS = ("empty", "captured_candidate", "explicitly_promoted")
LEARNING_CONDITIONS = ("new_session_repeat", "unseen_variant", "source_changed")
STAGES = ("intake", "work", "verification", "classification", "semantic", "closeout", "recovery", "consumer")
FACT_KINDS = ("owner", "consumer", "interface", "state_contract", "generated_chain", "verification", "old_fact")
CLASSIC = (
    "accept", "analyze", "ask", "auto", "checklist", "constitution", "debug",
    "deep-research", "design", "discussion", "do", "e2e", "explain", "fast",
    "implement", "implement-teams", "map-build", "map-scan", "map-update",
    "plan", "prd-build", "prd-scan", "quick", "review", "specify", "tasks",
    "taskstoissues", "team", "test-design",
)
CASES = (
    ("L01", "no_mutation", "read_only", "ask"),
    ("L02", "no_mutation", "build_output_only", "do"),
    ("L03", "path_changes", "repair", "quick"),
    ("L04", "path_changes", "add_component", "implement"),
    ("L05", "path_changes", "delete_component", "quick"),
    ("L06", "path_changes", "rename_both_endpoints", "quick"),
    ("L07", "propagation", "cross_component_interface", "implement"),
    ("L08", "propagation", "shared_config", "quick"),
    ("L09", "propagation", "generated_template", "implement"),
    ("L10", "propagation", "dependency", "quick"),
    ("L11", "workflow_owners", "implement_submission", "implement"),
    ("L12", "workflow_owners", "quick_submission", "quick"),
    ("L13", "workflow_owners", "debug_repair", "debug"),
    ("L14", "workflow_owners", "review_repair", "review"),
    ("L15", "workflow_owners", "do_retained_source", "do"),
    ("L16", "workflow_owners", "e2e_retained_assets", "e2e"),
    ("L17", "version_binding", "edit_after_verification", "quick"),
    ("L18", "version_binding", "foreign_receipt", "implement"),
    ("L19", "version_binding", "accepted_output_changed", "implement"),
    ("L20", "multiple_workers", "serial_same_file", "implement"),
    ("L21", "multiple_workers", "shared_claim", "implement"),
    ("L22", "multiple_workers", "disjoint_scopes", "implement"),
    ("L23", "interruption", "prepare_boundary", "quick"),
    ("L24", "interruption", "update_boundary", "quick"),
    ("L25", "interruption", "reconcile_boundary", "implement"),
    ("L26", "interruption", "validate_boundary", "quick"),
    ("L27", "interruption", "receipt_boundary", "quick"),
    ("L28", "scope_debt", "unrelated_global_debt", "quick"),
    ("L29", "scope_debt", "related_read_debt", "implement"),
    ("L30", "scope_debt", "unknown_relevance", "quick"),
    ("L31", "external_baseline", "external_edit", "map-update"),
    ("L32", "external_baseline", "unknown_format", "map-update"),
    ("L33", "external_baseline", "missing_baseline", "map-scan"),
    ("L34", "external_baseline", "legacy_baseline", "map-build"),
    ("L35", "persistent_reuse", "new_session_repeat", "debug"),
    ("L36", "persistent_reuse", "unseen_variant", "debug"),
    ("L37", "persistent_reuse", "source_changed", "debug"),
    ("L38", "persistent_reuse", "wrong_component_lesson", "debug"),
    ("L39", "persistent_reuse", "old_version_lesson", "debug"),
    ("L40", "persistent_reuse", "contradictory_lesson", "debug"),
)
ACTUAL_CASES = ("L01", "L03", "L07", "L11", "L17", "L21", "L23", "L28", "L31", "L35")


def case_rows() -> list[dict[str, str]]:
    return [dict(zip(("id", "family", "condition", "workflow"), row, strict=True)) for row in CASES]


def slots(kind: str) -> list[str]:
    if kind == "mechanism_replay":
        return [f"{profile}/{case[0]}" for profile in PROFILES for case in CASES]
    if kind == "actual_agent_work":
        return [f"{profile}/{case}" for profile in PROFILES for case in ACTUAL_CASES]
    if kind == "learning_ablation":
        return [f"{profile}/{arm}/{condition}" for profile in PROFILES for arm in LEARNING_ARMS for condition in LEARNING_CONDITIONS]
    raise ValueError("unknown observation kind")


def case_for_slot(kind: str, slot: str) -> str:
    parts = slot.split("/")
    if kind == "learning_ablation":
        return dict(zip(LEARNING_CONDITIONS, ("L35", "L36", "L37"), strict=True))[parts[2]]
    return parts[1]


def number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        raise ValueError(f"{label}: expected finite non-negative number")
    return float(value)


def integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label}: expected integer")
    return value


def source_manifest(reference: Any, label: str) -> list[dict[str, Any]]:
    ref = artifact(reference, label)
    rows = load(Path(ref["path"]))
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"{label}: source denominator is empty")
    names: set[str] = set()
    for row in rows:
        name = row.get("source_path")
        if not isinstance(name, str) or not name or name.startswith("/") or "\\" in name or Path(name).is_absolute() or ".." in Path(name).parts or ":" in name:
            raise ValueError(f"{label}: non-relative source path")
        if name in names:
            raise ValueError(f"{label}: duplicate source path")
        names.add(name)
        if row.get("state", "present") == "deleted":
            if row.get("sha256") is not None or row.get("bytes") != 0:
                raise ValueError(f"{label}: deleted source must have null digest and zero bytes")
        else:
            artifact(row, f"{label} {name}")
    return rows


def validate_tasks(tasks: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(tasks, dict) or tasks.get("schema") != "cognition-loop-tasks.v1" or not tasks.get("author"):
        raise ValueError("tasks require explicit author and schema")
    rows = tasks.get("cases", [])
    if len(rows) != 40 or {row.get("id") for row in rows} != {row[0] for row in CASES}:
        raise ValueError("original forty case denominator must be retained")
    expected = {row["id"]: row for row in case_rows()}
    for row in rows:
        for key, value in expected[row["id"]].items():
            if row.get(key) != value:
                raise ValueError(f"{row['id']}: original {key} changed")
        if not row.get("request") or not row.get("business_acceptance"):
            raise ValueError(f"{row['id']}: original request and business acceptance required")
        if not isinstance(row.get("owned_paths"), list):
            raise ValueError("task-owned paths must be explicit, including empty read-only scope")
        facts = row.get("fact_contract", [])
        required = {f"{row['id']}-{kind}": kind for kind in FACT_KINDS}
        if len(facts) != len(required) or {fact.get("id"): fact.get("kind") for fact in facts} != required:
            raise ValueError("original task requires its exact seven fact IDs and distinct kinds")
        for fact in facts:
            if not fact.get("criterion") or fact.get("expected_state") not in ("accepted", "retired", "withheld"):
                raise ValueError("original task fact criterion and disposition must be frozen")
    return {row["id"]: row for row in rows}


def validate_gold(gold: Any, tasks_path: Path) -> dict[str, dict[str, Any]]:
    tasks = load(tasks_path)
    original_tasks = validate_tasks(tasks)
    if not isinstance(gold, dict) or gold.get("schema") != "cognition-loop-gold.v1" or gold.get("status") != "accepted":
        raise ValueError("independent source-bound gold must be accepted")
    if not gold.get("reviewer") or gold["reviewer"] == tasks["author"] or gold.get("tasks_sha256") != digest(tasks_path):
        raise ValueError("gold requires a separate reviewer and exact original tasks")
    rows = gold.get("cases", [])
    if len(rows) != 40 or {row.get("id") for row in rows} != {row[0] for row in CASES}:
        raise ValueError("gold cannot reduce forty cases")
    for row in rows:
        before_rows = source_manifest(row.get("source_before"), "gold original sources")
        source_manifest(row.get("source_expected"), "gold expected final sources")
        unchanged = {item["source_path"] for item in before_rows} - set(original_tasks[row["id"]]["owned_paths"])
        if set(row.get("unchanged_required_paths", [])) != unchanged:
            raise ValueError("gold unchanged-source boundary differs from original task ownership")
        if row.get("source_policy", "exact_bytes") not in ("exact_bytes", "independent_semantic"):
            raise ValueError("gold source equivalence policy is invalid")
        if row.get("source_policy") == "independent_semantic" and not row.get("source_equivalence_criteria"):
            raise ValueError("semantic source equivalence requires original explicit criteria")
        facts = row.get("facts", [])
        original = original_tasks[row["id"]]["fact_contract"]
        contract_fields = ("id", "kind", "criterion", "expected_state")
        expected_contract = {fact["id"]: {key: fact[key] for key in contract_fields} for fact in original}
        observed_contract = {fact.get("id"): {key: fact.get(key) for key in contract_fields} for fact in facts}
        if len(facts) != len(original) or observed_contract != expected_contract:
            raise ValueError("gold changed original task fact denominator or contract")
        for fact in facts:
            if fact.get("kind") not in FACT_KINDS or fact.get("expected_state") not in ("accepted", "retired", "withheld") or not fact.get("criterion"):
                raise ValueError("fact type, expected disposition and original criterion required")
            if not fact.get("evidence"):
                raise ValueError("gold fact requires independently inspected source evidence")
            for ref in fact["evidence"]:
                artifact(ref, "gold fact evidence")
    return {row["id"]: row for row in rows}


def validate_surfaces(surface: Any) -> None:
    if not isinstance(surface, dict) or surface.get("schema") != "cognition-loop-surfaces.v1":
        raise ValueError("installed entry inventory required")
    expected = {(profile, name) for profile in PROFILES for name in CLASSIC}
    expected.add(("advanced", "map-rebuild"))
    rows = surface.get("entries", [])
    if len(rows) != 59 or {(row.get("profile"), row.get("command")) for row in rows} != expected:
        raise ValueError("entry coverage must retain 29 Classic and 30 Advanced")
    for row in rows:
        if not row.get("invocation") or row.get("classification") not in ("consume_only", "planning_artifact", "mutation_closeout", "map_maintenance", "delegate"):
            raise ValueError("each actual installed entry needs invocation and effect classification")
        artifact(row.get("installed_entry"), "installed entry")
        if not row.get("triggered_contracts"):
            raise ValueError("installed entry has no effective contract evidence")
        for ref in row["triggered_contracts"]:
            artifact(ref, "triggered installed contract")
    companions = surface.get("classic_map_companions", [])
    if len(companions) != 3 or {row.get("command") for row in companions} != {"map-scan", "map-build", "map-update"}:
        raise ValueError("three Classic map companion rows required")
    for row in companions:
        first = artifact(row.get("classic"), "Classic companion")
        second = artifact(row.get("advanced"), "Advanced installed Classic companion")
        if first["sha256"] != second["sha256"] or first["bytes"] != second["bytes"]:
            raise ValueError("Classic map companions must remain byte-equivalent")


def freeze(tasks_path: Path, gold_path: Path, environment_path: Path, surfaces_path: Path,
           baseline_path: Path, baseline_acceptance_path: Path, runtime_path: Path) -> dict[str, Any]:
    validate_gold(load(gold_path), tasks_path)
    validate_surfaces(load(surfaces_path))
    source = load(baseline_path)
    acceptance = load(baseline_acceptance_path)
    if source.get("schema") != "cognition-loop-source-baseline.v1" or acceptance.get("status") != "accepted" or acceptance.get("manifest") != binding(baseline_path):
        raise ValueError("source baseline is not independently accepted at this exact revision")
    frozen = Path(source["frozen_root"])
    for row in source.get("files", []):
        candidate = frozen / row["path"]
        if not candidate.is_file() or digest(candidate) != row["sha256"] or candidate.stat().st_size != row["bytes"]:
            raise ValueError(f"frozen baseline changed: {row['path']}")
    environment = load(environment_path)
    for key in ("platform", "python", "model", "permissions", "cold_warm_policy", "clock"):
        if key not in environment:
            raise ValueError(f"environment missing {key}")
    return {
        "schema": "cognition-loop-plan.v1", "phase": "before", "tasks": binding(tasks_path),
        "gold": binding(gold_path), "environment": binding(environment_path),
        "surfaces": binding(surfaces_path), "source_baseline": binding(baseline_path),
        "source_baseline_acceptance": binding(baseline_acceptance_path), "runtime": binding(runtime_path),
        "required_slots": {kind: slots(kind) for kind in KINDS},
        "required_entries": {"classic": 29, "advanced": 30, "classic_map_companions": 3},
        "boundaries": ["Native replay does not count as actual Agent work", "IDs and digests establish consistency, not process authentication or semantic truth", "All failures and recovery remain in the original episode", "Learning, graph freshness, and Playbook applicability have different owners", "First means task-session cold; OS caches are not cleared", "Previous 120 navigation observations are separate regression evidence", "Model tokens, memory, I/O and lock timing require actual telemetry or remain unavailable"],
    }


def validate_plan(path: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    plan = load(path)
    if plan.get("schema") != "cognition-loop-plan.v1" or plan.get("phase") not in ("before", "after") or plan.get("required_slots") != {kind: slots(kind) for kind in KINDS}:
        raise ValueError("plan cannot shrink or rewrite the fixed matrices")
    for key in ("tasks", "gold", "environment", "surfaces", "source_baseline", "source_baseline_acceptance", "runtime"):
        artifact(plan.get(key), f"plan {key}")
    validate_surfaces(load(Path(plan["surfaces"]["path"])))
    gold = validate_gold(load(Path(plan["gold"]["path"])), Path(plan["tasks"]["path"]))
    return plan, gold


def freeze_after(before_path: Path, runtime_path: Path, surfaces_path: Path,
                 candidate_source_path: Path, prerequisites_path: Path, budget_path: Path) -> dict[str, Any]:
    before, _ = validate_plan(before_path)
    if before["phase"] != "before":
        raise ValueError("before contract required")
    validate_surfaces(load(surfaces_path))
    prerequisites = load(prerequisites_path)
    rows = prerequisites.get("items", [])
    if prerequisites.get("status") != "accepted" or len(rows) != 8 or {row.get("id") for row in rows} != {f"R{i}" for i in range(8)}:
        raise ValueError("AFTER requires all eight independently accepted R0-R7 outputs")
    for row in rows:
        acceptance = artifact(row.get("acceptance"), "prerequisite acceptance")
        receipt = load(Path(acceptance["path"]))
        if receipt.get("status") != "accepted" or not receipt.get("validator") or receipt.get("validator") == row.get("author"):
            raise ValueError("prerequisite acceptance is not independent")
        if receipt.get("item") != row["id"] or not row.get("outputs") or receipt.get("accepted_outputs") != row["outputs"]:
            raise ValueError("prerequisite acceptance does not bind this item and exact accepted outputs")
        for ref in row.get("outputs", []):
            artifact(ref, "accepted prerequisite output")
    budget = load(budget_path)
    if budget.get("schema") != "cognition-loop-budget.v1" or budget.get("before_plan_sha256") != digest(before_path) or budget.get("status") != "accepted":
        raise ValueError("performance budget must be fixed from the accepted BEFORE plan before candidate observation")
    if set(budget.get("profiles", {})) != set(PROFILES):
        raise ValueError("each profile requires its own complete-cost budget")
    for profile in PROFILES:
        number(budget["profiles"][profile]["max_median_total_ratio"], "profile budget")
    source_manifest(binding(candidate_source_path), "candidate source freeze")
    return {**before, "phase": "after", "before_plan": binding(before_path),
            "runtime": binding(runtime_path), "surfaces": binding(surfaces_path),
            "candidate_source": binding(candidate_source_path),
            "prerequisites": binding(prerequisites_path), "budget": binding(budget_path)}


def identity(value: Any, label: str) -> dict[str, Any]:
    ref = artifact(value, label)
    result = load(Path(ref["path"]))
    if not isinstance(result, dict) or not all(result.get(key) for key in ("task_id", "turn_id", "model", "origin")) or result["origin"] != "native_collaboration":
        raise ValueError(f"{label}: actual native task/turn/model provenance required")
    return result


def certificate(value: Any, label: str, record: dict[str, Any], task: dict[str, Any],
                schema: str, recorded_calls: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Check inspectable native proof bindings; this does not authenticate actors.

    A random hashed artifact cannot substitute for a version-bound business or
    closeout proof. Actual independent reviewers still establish semantic truth.
    """
    result = load(Path(artifact(value, label)["path"]))
    if not isinstance(result, dict) or result.get("schema") != schema:
        raise ValueError(f"{label}: typed native evidence certificate required")
    for key in ("run_id", "slot", "phase", "case_id", "project_root", "plan_sha256", "installed_entry", "source_after"):
        if result.get(key) != record.get(key):
            raise ValueError(f"{label}: foreign episode, entry or final source version ({key})")
    if result.get("profile") != record["slot"].split("/")[0] or result.get("business_acceptance") != task["business_acceptance"]:
        raise ValueError(f"{label}: changed original business criteria or profile")
    if not result.get("native_owner") or not result.get("native_calls"):
        raise ValueError(f"{label}: actual native owner and calls required")
    for call in result["native_calls"]:
        if call.get("cwd") != record["project_root"] or not isinstance(call.get("argv"), list) or not call["argv"]:
            raise ValueError(f"{label}: native command or target missing")
        integer(call.get("exit_code"), "certificate native exit")
        if integer(call.get("started_at_ns"), "certificate native start") > integer(call.get("ended_at_ns"), "certificate native end"):
            raise ValueError(f"{label}: native timing reversed")
        artifact(call.get("stdout"), "certificate native stdout")
        artifact(call.get("stderr"), "certificate native stderr")
        if recorded_calls is not None and call not in recorded_calls:
            raise ValueError(f"{label}: call is absent from original episode trace")
    if schema == "cognition-loop-business-proof.v1":
        criteria = result.get("criteria", [])
        required = {f"B{index + 1:02d}": criterion for index, criterion in enumerate(task["business_acceptance"])}
        if len(criteria) != len(required) or {row.get("id"): row.get("criterion") for row in criteria} != required:
            raise ValueError(f"{label}: dropped original business criteria")
        for row in criteria:
            if not row.get("evidence") or not row.get("reason") or row.get("status") not in ("passed", "failed", "unsupported"):
                raise ValueError(f"{label}: each business criterion needs inspectable proof and reasoning")
            for ref in row["evidence"]:
                artifact(ref, "business criterion evidence")
    return result


def validate_record(record: Any, plan_path: Path, plan: dict[str, Any], gold: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(record, dict) or record.get("schema") != "cognition-loop-observation.v1":
        raise ValueError("invalid loop observation schema")
    kind, slot = record.get("kind"), record.get("slot")
    if kind not in KINDS or slot not in slots(kind) or not record.get("run_id"):
        raise ValueError("invalid fixed slot or missing run ID")
    if record.get("plan_sha256") != digest(plan_path) or record.get("phase") != plan["phase"]:
        raise ValueError("observation belongs to another phase or frozen plan")
    packet_ref = artifact(record.get("packet"), "episode packet")
    packet = load(Path(packet_ref["path"]))
    fields = ("slot", "kind", "phase", "case_id", "project_root", "runtime", "source_before", "installed_entry", "plan_sha256", "owned_paths", "producer_id")
    for key in fields:
        if record.get(key) != packet.get(key):
            raise ValueError(f"observation changed packet {key}")
    if packet.get("schema") != "cognition-loop-packet.v1" or record.get("runtime") != plan["runtime"]:
        raise ValueError("packet or runtime identity changed")
    if record.get("case_id") not in gold or record["case_id"] != case_for_slot(kind, slot):
        raise ValueError("case is outside original facts")
    source_manifest(record.get("source_before"), "actual initial source snapshot")
    root = Path(record["project_root"])
    if not root.is_dir() or str(root.resolve()) != record["project_root"]:
        raise ValueError("missing or redirected episode target")
    artifact(record.get("installed_entry"), "actual installed entry used")
    profile = slot.split("/")[0]
    task = validate_tasks(load(Path(plan["tasks"]["path"])))[record["case_id"]]
    surface_rows = load(Path(plan["surfaces"]["path"]))["entries"]
    expected_command = next(row["workflow"] for row in case_rows() if row["id"] == record["case_id"])
    eligible_entries = [row["installed_entry"] for row in surface_rows if row["profile"] == profile and row["command"] == expected_command]
    if not any(record["installed_entry"]["sha256"] == ref["sha256"] and record["installed_entry"]["bytes"] == ref["bytes"] for ref in eligible_entries):
        raise ValueError("episode did not consume this profile's installed entry")
    actual_initial = {row["source_path"]: (row.get("sha256"), row["bytes"]) for row in source_manifest(record["source_before"], "episode original")}
    expected_initial = {row["source_path"]: (row.get("sha256"), row["bytes"]) for row in source_manifest(gold[record["case_id"]]["source_before"], "gold original")}
    if actual_initial != expected_initial:
        raise ValueError("episode original source differs from frozen fixture")
    start = integer(record.get("started_at_ns"), "episode start")
    end = integer(record.get("ended_at_ns"), "episode end")
    if end < start:
        raise ValueError("episode timing moved backwards")
    total_ms = (end - start) / 1e6
    if abs(number(record.get("total_ms"), "complete episode time") - total_ms) > 0.001:
        raise ValueError("reported time omits failures or differs from full original episode")
    attempts = record.get("attempts", [])
    if not attempts or len({row.get("id") for row in attempts}) != len(attempts):
        raise ValueError("attempt history must remain nonempty and distinct")
    calls = []
    for attempt in attempts:
        attempt_start = integer(attempt.get("started_at_ns"), "attempt start")
        attempt_end = integer(attempt.get("ended_at_ns"), "attempt end")
        if not start <= attempt_start <= attempt_end <= end or attempt.get("stage") not in STAGES or attempt.get("result") not in ("passed", "failed", "blocked", "unsupported", "interrupted"):
            raise ValueError("attempt stage/result/timing is invalid")
        for ref in attempt.get("evidence", []):
            artifact(ref, "attempt evidence")
        for call in attempt.get("calls", []):
            if not isinstance(call.get("argv"), list) or not call["argv"] or call.get("cwd") != record["project_root"]:
                raise ValueError("native call argv/target missing or foreign")
            integer(call.get("exit_code"), "native exit")
            call_start = integer(call.get("started_at_ns"), "native start")
            call_end = integer(call.get("ended_at_ns"), "native end")
            if not attempt_start <= call_start <= call_end <= attempt_end:
                raise ValueError("native call clock falls outside its attempt")
            artifact(call.get("stdout"), "native stdout")
            artifact(call.get("stderr"), "native stderr")
            calls.append(call)
    if record.get("model_tokens", {}).get("status") != "unavailable":
        if kind == "mechanism_replay":
            raise ValueError("mechanism replay cannot supply model tokens")
        artifact(record["model_tokens"].get("evidence"), "actual model token telemetry")
    for name in ("memory", "io", "lock_wait"):
        telemetry = record.get(name, {"status": "unavailable"})
        if telemetry.get("status") != "unavailable":
            if telemetry.get("status") != "native_telemetry":
                raise ValueError(f"{name} cannot be inferred from stdout or configuration")
            artifact(telemetry.get("evidence"), f"actual {name} telemetry")
    explicit_read_bytes = 0
    for read in record.get("source_reads", []):
        ref = artifact(read.get("evidence"), "instrumented source read")
        if read.get("source_path") not in set(task.get("read_paths", [])) | set(task["owned_paths"]) or read.get("source_sha256") != ref["sha256"]:
            raise ValueError("source-read byte evidence is foreign or inconsistent")
        explicit_read_bytes += ref["bytes"]
    explicit_write_bytes = 0
    for edit in record.get("source_edits", []):
        artifact(edit, "instrumented source edit")
        change = load(Path(edit["path"]))
        if change.get("source_path") not in record["owned_paths"] or (change.get("rename_to") and change["rename_to"] not in record["owned_paths"]):
            raise ValueError("instrumented edit escaped original ownership")
        written = integer(change.get("source_write_bytes"), "instrumented source write bytes")
        number(written, "instrumented source write bytes")
        explicit_write_bytes += written
    actor = None
    if kind != "mechanism_replay":
        actor = identity(record.get("actor"), "actual work actor")
    facts = gold[record["case_id"]]["facts"]
    expected = {fact["id"]: fact for fact in facts}
    decisions = record.get("fact_decisions", [])
    if len({row.get("id") for row in decisions}) != len(decisions):
        raise ValueError("duplicate fact decisions inflate coverage")
    by_id = {row["id"]: row for row in decisions}
    for row in decisions:
        if row.get("state") not in ("accepted", "retired", "withheld", "unknown"):
            raise ValueError("fact disposition is invalid")
        if row["state"] in ("accepted", "retired") and not row.get("evidence"):
            raise ValueError("accepted or retired fact lacks inspectable evidence")
        for ref in row.get("evidence", []):
            artifact(ref, "observed fact evidence")
    missing = sorted(set(expected) - set(by_id))
    incorrect = sorted(key for key in set(expected) & set(by_id) if expected[key]["expected_state"] != by_id[key]["state"])
    unexpected = sorted(key for key in by_id if key not in expected and by_id[key]["state"] == "accepted")
    false_accepts = sorted(key for key in incorrect if by_id[key]["state"] == "accepted") + unexpected
    missed_invalidation = sorted(key for key in expected if expected[key]["expected_state"] == "retired" and by_id.get(key, {}).get("state") != "retired")
    independently_accepted = False
    if record.get("semantic_review"):
        ref = artifact(record["semantic_review"], "independent semantic review")
        review = load(Path(ref["path"]))
        if review.get("gold_sha256") != plan["gold"]["sha256"] or review.get("case_id") != record["case_id"] or review.get("decisions_sha256") != digest(Path(artifact(record.get("decisions_artifact"), "original decisions")["path"])):
            raise ValueError("semantic review is not bound to original case, facts and actual decisions")
        original_decisions = load(Path(record["decisions_artifact"]["path"]))
        if original_decisions != decisions:
            raise ValueError("record rewrote the original decision artifact")
        if not review.get("validator") or review["validator"] in (record.get("producer_id"), (actor or {}).get("task_id")) or review.get("source_after") != record.get("source_after"):
            raise ValueError("semantic reviewer is not separate or changed final source version")
        review_rows = review.get("rows", [])
        if len(review_rows) != len(facts) or {row.get("id") for row in review_rows} != set(expected):
            raise ValueError("independent semantic review dropped original fact rows")
        for row in review_rows:
            if row.get("criterion") != expected[row["id"]]["criterion"] or not row.get("reason") or not row.get("evidence"):
                raise ValueError("each semantic fact row requires original criterion, reasoning and inspectable source/native evidence")
            for ref in row["evidence"]:
                artifact(ref, "independent fact source/native evidence")
        independently_accepted = review.get("status") == "accepted" and all(row.get("status") == "accepted" for row in review_rows)
    expected_final = {row["source_path"]: (row.get("sha256"), row["bytes"]) for row in source_manifest(gold[record["case_id"]]["source_expected"], "expected final source")}
    actual_final = {}
    if record.get("source_after"):
        actual_final = {row["source_path"]: (row.get("sha256"), row["bytes"]) for row in source_manifest(record["source_after"], "actual final source")}
    if gold[record["case_id"]].get("source_policy", "exact_bytes") == "independent_semantic":
        source_gaps = sorted(key for key in set(expected_final) | set(actual_final)
                             if key not in expected_final or key not in actual_final or
                             (expected_final[key][0] is None) != (actual_final[key][0] is None))
    else:
        source_gaps = sorted(key for key in set(expected_final) | set(actual_final) if expected_final.get(key) != actual_final.get(key))
    source_gaps = sorted(set(source_gaps) | {key for key in gold[record["case_id"]].get("unchanged_required_paths", []) if actual_final.get(key) != expected_initial.get(key)})
    consumer = record.get("consumer")
    consumer_passed = False
    consumer_ms = None
    if consumer:
        decision_ref = artifact(consumer.get("decision"), "new consumer original decision")
        decision = load(Path(decision_ref["path"]))
        if kind != "mechanism_replay":
            consumer_identity = identity(consumer.get("identity"), "new-session consumer")
            if consumer_identity["task_id"] == actor["task_id"]:
                raise ValueError("consumer must run in a different native Agent session")
        if decision.get("source_after") != record.get("source_after") or decision.get("case_id") != record["case_id"]:
            raise ValueError("consumer decision belongs to another final source or task")
        proof = certificate(decision.get("verification"), "new consumer business verification", record, task, "cognition-loop-business-proof.v1")
        consumer_ms = number(consumer.get("total_ms"), "separate consumer episode")
        consumer_passed = decision.get("business_result") == "passed" and decision.get("old_fact_used") is False and all(row["status"] == "passed" for row in proof["criteria"])
    if kind == "learning_ablation":
        arm, condition = slot.split("/")[1:]
        learning = record.get("learning", {})
        if learning.get("arm") != arm or learning.get("condition") != condition:
            raise ValueError("Learning arm/condition differs from fixed slot")
        for ref in learning.get("evidence", []):
            artifact(ref, "actual Learning owner evidence")
        if arm != "empty" and not learning.get("capture_evidence"):
            raise ValueError("nonempty Learning arm lacks actual capture evidence")
        if arm != "empty":
            artifact(learning["capture_evidence"], "real lesson capture")
        if arm == "explicitly_promoted":
            artifact(learning.get("promote_evidence"), "explicit fixture promotion")
        if arm != "explicitly_promoted" and learning.get("promote_evidence"):
            raise ValueError("candidate/empty arm cannot be silently promoted")
    correct = not missing and not incorrect and not unexpected and not source_gaps
    closeout = record.get("closeout", {})
    closeout_passed = closeout.get("scope_result") in ("scope_ready", "ready", "no_op", "no_cognition_change")
    if closeout_passed:
        proof = certificate(closeout.get("evidence"), "actual closeout/no-change owner result", record, task, "cognition-loop-closeout-proof.v1", calls)
        expected_scope = {"project_root": record["project_root"], "owned_paths": record["owned_paths"], "source_after": record["source_after"]}
        if proof.get("scope_result") != closeout["scope_result"] or proof.get("scope_binding") != expected_scope or not proof.get("native_result"):
            raise ValueError("closeout proof lacks exact scope/result owner evidence")
        artifact(proof["native_result"], "native closeout owner result")
    business_passed = False
    if record.get("business_result") == "passed":
        proof = certificate(record.get("business_verification"), "original business verification", record, task, "cognition-loop-business-proof.v1", calls)
        business_passed = all(row["status"] == "passed" for row in proof["criteria"])
    complete = correct and independently_accepted and consumer_passed and closeout_passed and business_passed
    return {"kind": kind, "phase": record["phase"], "slot": slot, "case_id": record["case_id"],
            "run_id": record["run_id"], "loop_acceptance": "pass" if complete else "fail",
            "fact_required": len(facts), "fact_correct": sum(key in by_id and expected[key]["expected_state"] == by_id[key]["state"] for key in expected),
            "missing_facts": missing, "incorrect_facts": incorrect, "unexpected_accepted_facts": unexpected,
            "false_accepted_facts": false_accepts, "missed_invalidation": missed_invalidation,
            "source_version_gaps": source_gaps, "independent_semantic_acceptance": independently_accepted,
            "new_session_consumer_passed": consumer_passed, "business_passed": business_passed,
            "closeout_passed": closeout_passed, "first_attempt_success": complete and not any(row["result"] != "passed" for row in attempts),
            "metrics": {"complete_total_ms": total_ms, "consumer_total_ms": consumer_ms,
                        "attempts": len(attempts), "failed_or_blocked_attempts": sum(row["result"] != "passed" for row in attempts),
                        "native_calls": len(calls), "native_elapsed_ms_sum": sum((row["ended_at_ns"] - row["started_at_ns"]) / 1e6 for row in calls),
                        "stdout_bytes": sum(row["stdout"]["bytes"] for row in calls), "stderr_bytes": sum(row["stderr"]["bytes"] for row in calls),
                        "instrumented_source_read_bytes": explicit_read_bytes, "instrumented_source_write_bytes": explicit_write_bytes,
                        "source_io_scope": "probe read/edit calls only; native process, snapshots and uninstrumented reads are unavailable",
                        "model_tokens": record.get("model_tokens", {"status": "unavailable"}),
                        "memory": record.get("memory", {"status": "unavailable"}), "io": record.get("io", {"status": "unavailable"}),
                        "lock_wait": record.get("lock_wait", {"status": "unavailable"})}}


def evaluate(plan_path: Path, records: list[dict[str, Any]]) -> dict[str, Any]:
    plan, gold = validate_plan(plan_path)
    observed, run_ids = [], set()
    seen: set[tuple[str, str]] = set()
    for record in records:
        row = validate_record(record, plan_path, plan, gold)
        key = row["kind"], row["slot"]
        if key in seen or row["run_id"] in run_ids:
            raise ValueError("duplicate observation slot or run ID")
        seen.add(key)
        run_ids.add(row["run_id"])
        observed.append(row)
    matrices = []
    for kind in KINDS:
        rows = [row for row in observed if row["kind"] == kind]
        found = {row["slot"] for row in rows}
        per_profile = {}
        for profile in PROFILES:
            subset = [row for row in rows if row["slot"].startswith(profile + "/")]
            per_profile[profile] = {"required": len(slots(kind)) // 2, "observed": len(subset),
                                    "passed": sum(row["loop_acceptance"] == "pass" for row in subset),
                                    "median_complete_total_ms": statistics.median(row["metrics"]["complete_total_ms"] for row in subset) if subset else None}
        matrices.append({"kind": kind, "required": len(slots(kind)), "observed": len(rows),
                         "passed": sum(row["loop_acceptance"] == "pass" for row in rows),
                         "unexecuted_slots": [slot for slot in slots(kind) if slot not in found], "per_profile": per_profile,
                         "fact_required_total": sum(len(gold[case_for_slot(kind, slot)]["facts"]) for slot in slots(kind)),
                         "fact_required_observed": sum(row["fact_required"] for row in rows), "fact_correct": sum(row["fact_correct"] for row in rows),
                         "false_accepted_facts": sum(len(row["false_accepted_facts"]) for row in rows),
                         "missed_invalidation": sum(len(row["missed_invalidation"]) for row in rows)})
    done = all(matrix["observed"] == matrix["required"] for matrix in matrices)
    quality = all(matrix["passed"] == matrix["required"] for matrix in matrices)
    return {"schema": SCHEMA, "phase": plan["phase"], "plan": binding(plan_path),
            "status": "observed_complete_matrix" if done else "pending_complete_loop_evidence",
            "quality_status": "pass" if quality else "fail" if done else "pending",
            "matrices": matrices, "observations": observed, "installed_entry_coverage": plan["required_entries"],
            "limits": plan["boundaries"] + ["This scorer's acceptance is not independent product acceptance", "Small fixed cases do not establish P95 or universal zero-error reliability", "Parallel episode intervals are not summed into model-work time"]}


def compare(before_path: Path, after_path: Path, before_records: list[dict[str, Any]], after_records: list[dict[str, Any]]) -> dict[str, Any]:
    before, _ = validate_plan(before_path)
    after, _ = validate_plan(after_path)
    if before["phase"] != "before" or after["phase"] != "after" or after.get("before_plan") != binding(before_path):
        raise ValueError("phase pairing is not bound to original BEFORE")
    for key in ("tasks", "gold", "environment", "required_slots"):
        if before[key] != after[key]:
            raise ValueError(f"pairing changed original {key}")
    artifact(after.get("prerequisites"), "current accepted candidate prerequisites")
    artifact(after.get("budget"), "fixed profile budgets")
    first, second = evaluate(before_path, before_records), evaluate(after_path, after_records)
    indexed = [{(row["kind"], row["slot"]): row for row in result["observations"]} for result in (first, second)]
    pairs = []
    budgets = load(Path(after["budget"]["path"]))["profiles"]
    for kind in KINDS:
        for profile in PROFILES:
            required = [slot for slot in slots(kind) if slot.startswith(profile + "/")]
            available = [slot for slot in required if (kind, slot) in indexed[0] and (kind, slot) in indexed[1]]
            successful = [slot for slot in available if all(index[kind, slot]["loop_acceptance"] == "pass" for index in indexed)]
            before_times = [indexed[0][kind, slot]["metrics"]["complete_total_ms"] for slot in successful]
            after_times = [indexed[1][kind, slot]["metrics"]["complete_total_ms"] for slot in successful]
            ratio = statistics.median(after_times) / statistics.median(before_times) if before_times and statistics.median(before_times) > 0 else None
            pairs.append({"kind": kind, "profile": profile, "required_pairs": len(required), "available_pairs": len(available),
                          "matched_successful_pairs": len(successful), "ineligible_failed_pairs": [slot for slot in available if slot not in successful],
                          "before_passed": sum(indexed[0][kind, slot]["loop_acceptance"] == "pass" for slot in available),
                          "after_passed": sum(indexed[1][kind, slot]["loop_acceptance"] == "pass" for slot in available),
                          "median_complete_ms_before": statistics.median(before_times) if before_times else None,
                          "median_complete_ms_after": statistics.median(after_times) if after_times else None,
                          "median_complete_ratio": ratio, "fixed_max_ratio": budgets[profile]["max_median_total_ratio"],
                          "all_observed_cost_before_ms": sum(indexed[0][kind, slot]["metrics"]["complete_total_ms"] for slot in required if (kind, slot) in indexed[0]),
                          "all_observed_cost_after_ms": sum(indexed[1][kind, slot]["metrics"]["complete_total_ms"] for slot in required if (kind, slot) in indexed[1]),
                          "budget_status": "pending" if len(successful) != len(required) or ratio is None else "pass" if ratio <= budgets[profile]["max_median_total_ratio"] else "fail",
                          "claim": "matched_successful_sample_only" if successful else "no_matched_successful_endpoint"})
    return {"schema": "cognition-loop-comparison.v1", "before": first, "after": second, "pairs": pairs,
            "limits": ["Profiles and evidence kinds have separate acceptance", "No complete-loop benefit follows from the older navigation benchmark", "All actual failed attempts remain in complete episode timing", "No causal Learning benefit without matched native actor outcomes in all three arms"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    count = sub.add_parser("contract")
    count.add_argument("--output", type=Path)
    freeze_parser = sub.add_parser("freeze")
    for name in ("tasks", "gold", "environment", "surfaces", "baseline", "baseline-acceptance", "runtime", "output"):
        freeze_parser.add_argument("--" + name, type=Path, required=True)
    after_parser = sub.add_parser("freeze-after")
    for name in ("before", "runtime", "surfaces", "candidate-source", "prerequisites", "budget", "output"):
        after_parser.add_argument("--" + name, type=Path, required=True)
    score_parser = sub.add_parser("evaluate")
    for name in ("plan", "records", "output"):
        score_parser.add_argument("--" + name, type=Path, required=True)
    compare_parser = sub.add_parser("compare")
    for name in ("before", "after", "before-records", "after-records", "output"):
        compare_parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.operation == "contract":
            result = {"schema": "cognition-loop-denominator.v1", "cases": case_rows(), "required_slots": {kind: slots(kind) for kind in KINDS}, "entry_counts": {"classic": 29, "advanced": 30, "classic_map_companions": 3}}
        elif args.operation == "freeze":
            result = freeze(args.tasks, args.gold, args.environment, args.surfaces, args.baseline, args.baseline_acceptance, args.runtime)
        elif args.operation == "freeze-after":
            result = freeze_after(args.before, args.runtime, args.surfaces, args.candidate_source, args.prerequisites, args.budget)
        elif args.operation == "evaluate":
            result = evaluate(args.plan, load(args.records))
        else:
            result = compare(args.before, args.after, load(args.before_records), load(args.after_records))
        if args.output:
            write_new(args.output, result)
            print(binding(args.output))
        else:
            import json
            print(json.dumps(result, ensure_ascii=False, allow_nan=False))
    except (OSError, UnicodeError, ValueError, KeyError, TypeError) as exc:
        print(f"cognition-loop-eval: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
