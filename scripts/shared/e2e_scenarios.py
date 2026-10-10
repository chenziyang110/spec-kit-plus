#!/usr/bin/env python3
"""Derive/check E2E scenario obligations and audit visual or mixed execution.

Stateless, standard-library-only test-asset helper; never drives a UI, executes
input, writes workflow state, or certifies discovery/assertion correctness.
Exit 0 = requested check satisfied, 1 = gaps, 2 = invalid/stale input.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
from typing import Any

DIMENSIONS = {
    "happy_path": "What observable user goal and durable outcome must succeed?",
    "input_partitions": "Which valid/invalid classes, encodings and equivalent names behave differently?",
    "input_boundaries": "What is each actual limit, its unit, and the values just below/at/above it?",
    "object_lifecycle": "What if the object is absent, moved, replaced, open, locked or already changed?",
    "external_mutation": "Which assumptions can another actor invalidate while the operation is open?",
    "event_order": "What changes before entry, before commit, while pending, and after commit?",
    "permissions": "What if role, ownership, tenant or permission changes before the effect?",
    "conflict_concurrency": "What if the destination exists or two actors race for the same resource?",
    "repeat_cancel_retry": "What do duplicate activation, cancel, retry and undo do to the same intent?",
    "interruption_recovery": "What survives disconnect, crash, restart or a partial operation?",
    "persistence_consistency": "Do independent readback, other views and related state agree without data loss?",
    "environment_compatibility": "Which supported OS, filesystem, device, locale or dependency rules differ?",
    "visual_interaction": "Are feedback, focus, selection, IME, keyboard, layout and pending states correct?",
    "cross_feature": "Which search, recent-item, open-document or other consumer journeys can regress?",
}
CHANNELS = {"visual", "filesystem", "api", "cli", "database", "log", "accessibility", "human"}
STATUSES = {"passed", "failed", "blocked", "skipped", "not_run"}
MAX_RECORDS = 10000


class ScenarioError(ValueError):
    """The supplied data cannot support the requested claim."""


def need(ok: bool, message: str) -> None:
    if not ok:
        raise ScenarioError(message)


def obj(value: Any, fields: str, label: str) -> dict:
    need(isinstance(value, dict), f"{label}: object required")
    need(set(value) <= set(fields.split()), f"{label}: unknown fields {sorted(set(value) - set(fields.split()))}")
    return value


def text(value: Any, label: str) -> str:
    need(isinstance(value, str) and bool(value.strip()), f"{label}: nonempty string required")
    return value


def rows(value: Any, label: str, nonempty: bool = True) -> list:
    need(isinstance(value, list), f"{label}: array required")
    need((not nonempty or bool(value)) and len(value) <= MAX_RECORDS, f"{label}: empty or excessive array")
    return value


def strings(value: Any, label: str) -> list[str]:
    values = rows(value, label)
    for item in values:
        text(item, label)
    need(len(set(values)) == len(values), f"{label}: duplicate value")
    return values


def indexed(value: Any, label: str, nonempty: bool = True) -> dict[str, dict]:
    result = {}
    for item in rows(value, label, nonempty):
        need(isinstance(item, dict), f"{label}: object required")
        identity = text(item.get("id"), f"{label}.id")
        need(identity not in result, f"{label}: duplicate id {identity}")
        result[identity] = item
    return result


def sha(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def file_hash(root: Path, name: str) -> str:
    text(name, "path")
    path = PurePosixPath(name)
    need(not path.is_absolute() and ".." not in path.parts and "\\" not in name
         and ":" not in name and path.as_posix() == name, f"unsafe/noncanonical path: {name}")
    resolved = (root / name).resolve()
    need(resolved.is_relative_to(root.resolve()) and resolved.is_file(), f"missing/escaping file: {name}")
    return hashlib.sha256(resolved.read_bytes()).hexdigest()


def files(value: Any, root: Path) -> set[str]:
    found = set()
    for row in rows(value, "sources"):
        obj(row, "path sha256", "source")
        name = text(row.get("path"), "source.path")
        need(name not in found, f"duplicate source: {name}")
        need(row.get("sha256") == file_hash(root, name), f"stale source: {name}")
        found.add(name)
    return found


def refs(value: Any, allowed: Any, label: str) -> list[str]:
    values = strings(value, label)
    need(set(values) <= set(allowed), f"{label}: unknown reference")
    return values


def stamp(value: Any) -> datetime:
    result = datetime.fromisoformat(text(value, "timestamp").replace("Z", "+00:00"))
    need(result.tzinfo is not None, "timestamps must include a timezone")
    return result


def structure(book: dict, root: Path) -> tuple[dict, dict, dict, list]:
    need(isinstance(book, dict), "book: object required")
    version = book.get("schema_version")
    need(type(version) is int and version in {1, 2}, "book: schema_version must be 1 or 2")
    obj(book, "schema_version scope source_revision sources requirements operations scenarios discovery_gaps exclusions"
        + (" conditions" if version == 2 else ""), "book")
    text(book.get("scope"), "scope")
    text(book.get("source_revision"), "source_revision")
    source_paths = files(book.get("sources"), root)
    requirements = indexed(book.get("requirements"), "requirements")
    for requirement in requirements.values():
        obj(requirement, "id source_ref assertion", "requirement")
        need(requirement.get("source_ref") in source_paths, "requirement: unbound source_ref")
        text(requirement.get("assertion"), "requirement.assertion")
    operations = indexed(book.get("operations"), "operations")
    obligations = []
    timing_by_operation = {}
    for identity, operation in operations.items():
        obj(operation, "id title entrypoint source_refs assumptions side_effects dimensions checkpoints events", identity)
        for key in ("title", "entrypoint"):
            text(operation.get(key), f"{identity}.{key}")
        refs(operation.get("source_refs"), source_paths, f"{identity}.source_refs")
        strings(operation.get("assumptions"), f"{identity}.assumptions")
        need(type(operation.get("side_effects")) is bool, f"{identity}: side_effects must be boolean")
        dimensions = operation.get("dimensions")
        need(isinstance(dimensions, dict) and set(DIMENSIONS) <= set(dimensions), f"{identity}: missing dimension decisions")
        for dimension, decision in dimensions.items():
            text(dimension, "dimension")
            obj(decision, "disposition reason source_refs", f"{identity}.{dimension}")
            need(decision.get("disposition") in {"applicable", "not_applicable"}, "invalid dimension disposition")
            text(decision.get("reason"), "dimension.reason")
            refs(decision.get("source_refs"), source_paths, "dimension.source_refs")
        need(dimensions["happy_path"]["disposition"] == "applicable", "happy_path cannot be not_applicable")
        if operation["side_effects"]:
            need(dimensions["persistence_consistency"]["disposition"] == "applicable", "side effects require persistence_consistency")
        checkpoints = indexed(operation.get("checkpoints"), "checkpoints", False)
        for checkpoint in checkpoints.values():
            obj(checkpoint, "id observation", "checkpoint")
            text(checkpoint.get("observation"), "checkpoint.observation")
        events = indexed(operation.get("events"), "events", False)
        allowed_timing = timing_by_operation[identity] = set()
        if dimensions["external_mutation"]["disposition"] == "applicable":
            need(bool(events), f"{identity}: external_mutation requires events")
        for event_id, event in events.items():
            obj(event, "id change checkpoints", "event")
            text(event.get("change"), "event.change")
            need(all(dimensions[d]["disposition"] == "applicable" for d in ("external_mutation", "event_order")),
                 "events require applicable external_mutation and event_order")
            for checkpoint in refs(event.get("checkpoints"), checkpoints, "event.checkpoints"):
                key = [identity, event_id, checkpoint]
                allowed_timing.add((event_id, checkpoint))
                obligations.append({"id": "TIME-" + sha(key)[:24], "operation": identity,
                                    "event": event_id, "checkpoint": checkpoint})
                need(len(obligations) <= MAX_RECORDS, "timing obligation budget exceeded; split scope explicitly")
    scenarios = indexed(book.get("scenarios"), "scenarios", False)
    for identity, scenario in scenarios.items():
        obj(scenario, "id operation title dimensions requirements technique priority preconditions steps perturbations oracles execution cleanup safety"
            + (" condition_bindings" if version == 2 else ""), identity)
        operation_id = text(scenario.get("operation"), f"{identity}.operation")
        need(operation_id in operations, f"{identity}: unknown operation")
        operation = operations[operation_id]
        text(scenario.get("title"), f"{identity}.title")
        dimensions = refs(scenario.get("dimensions"), operation["dimensions"], f"{identity}.dimensions")
        need(all(operation["dimensions"][d]["disposition"] == "applicable" for d in dimensions), "scenario contradicts not_applicable decision")
        refs(scenario.get("requirements"), requirements, f"{identity}.requirements")
        strings(scenario.get("technique"), f"{identity}.technique")
        need(scenario.get("priority") in {"critical", "high", "normal"}, "invalid priority")
        need(scenario.get("execution") in {"visual", "runner", "hybrid", "human"}, "invalid execution route")
        for key in ("preconditions", "cleanup", "safety"):
            strings(scenario.get(key), f"{identity}.{key}")
        steps = indexed(scenario.get("steps"), f"{identity}.steps")
        for step in steps.values():
            obj(step, "id actor action observe", "step")
            need(step.get("actor") in {"user", "visual-model", "fixture", "system", "runner", "human"}, "invalid step actor")
            text(step.get("action"), "step.action")
            text(step.get("observe"), "step.observe")
        timing_keys = set()
        perturbation_steps = set()
        allowed = timing_by_operation[operation_id]
        for perturbation in rows(scenario.get("perturbations"), "perturbations", False):
            obj(perturbation, "event checkpoint step_id", "perturbation")
            key = (text(perturbation.get("event"), "event"), text(perturbation.get("checkpoint"), "checkpoint"))
            need(key in allowed and key not in timing_keys, "unknown/duplicate timing obligation")
            need(perturbation.get("step_id") in steps, "perturbation needs an explicit setup/change/proof step")
            need({"external_mutation", "event_order"} <= set(dimensions), "perturbation missing timing dimensions")
            need(perturbation["step_id"] not in perturbation_steps, "each timing obligation needs its own perturbation step")
            timing_keys.add(key)
            perturbation_steps.add(perturbation["step_id"])
        oracles = indexed(scenario.get("oracles"), f"{identity}.oracles")
        for oracle in oracles.values():
            obj(oracle, "id channel assertion check", "oracle")
            need(oracle.get("channel") in CHANNELS, "invalid oracle channel")
            text(oracle.get("assertion"), "oracle.assertion")
            text(oracle.get("check"), "oracle.check")
        if scenario["execution"] == "visual":
            need(any(o["channel"] == "visual" for o in oracles.values()), "visual route needs visual oracle")
        if operation["side_effects"]:
            need(any(o["channel"] not in {"visual", "accessibility", "human"} for o in oracles.values()),
                 "side effects require an independent readback oracle, not only a screenshot")
    for gap in rows(book.get("discovery_gaps"), "discovery_gaps", False):
        obj(gap, "id description owner next_action", "gap")
        for key in ("id", "description", "owner", "next_action"):
            text(gap.get(key), f"gap.{key}")
    for exclusion in rows(book.get("exclusions"), "exclusions", False):
        obj(exclusion, "scope reason owner", "exclusion")
        for key in ("scope", "reason", "owner"):
            text(exclusion.get(key), f"exclusion.{key}")
    return operations, requirements, scenarios, sorted(obligations, key=lambda o: o["id"])


def condition_coverage(book: dict, operations: dict, scenarios: dict) -> tuple[list, list]:
    """Expand v2 test conditions without inventing semantics or execution evidence.

    Boundary points are discrete quantities in an explicitly named unit. Other
    families enumerate agent-authored partitions, states, rules or sequences.
    IDs are stable under reordering; the full book digest binds changed meaning.
    """
    if book["schema_version"] == 1:
        return [], []
    sources = {row["path"] for row in book["sources"]}
    requirements = {row["id"] for row in book["requirements"]}
    conditions = indexed(book.get("conditions"), "conditions", False)
    obligations = {}
    gaps = []
    family_dimensions = set()
    for identity, condition in conditions.items():
        obj(condition, "id operation dimension kind title source_refs requirements variants boundary", "condition")
        op = text(condition.get("operation"), "condition.operation")
        dimension = text(condition.get("dimension"), "condition.dimension")
        need(op in operations, "condition: unknown operation")
        decisions = operations[op]["dimensions"]
        need(dimension in decisions and decisions[dimension]["disposition"] == "applicable",
             "condition: unknown or not_applicable dimension")
        text(condition.get("title"), "condition.title")
        refs(condition.get("source_refs"), sources, "condition.source_refs")
        required = refs(condition.get("requirements"), requirements, "condition.requirements")
        kind = text(condition.get("kind"), "condition.kind")
        need(kind in {"boundary", "partition", "state", "rule", "sequence", "example"}, "unknown condition kind")
        family_dimensions.add((op, dimension))
        if kind == "boundary":
            need("variants" not in condition, "boundary variants are derived, not supplied")
            boundary = obj(condition.get("boundary"), "limit unit expectations", "boundary")
            limit = boundary.get("limit")
            need(type(limit) is int and abs(limit) <= 10**12, "boundary.limit: bounded integer required")
            unit = text(boundary.get("unit"), "boundary.unit")
            expectations = obj(boundary.get("expectations"), "below at above", "boundary.expectations")
            variants = [{"id": name, "input": f"{limit + offset} {unit}",
                         "expected": text(expectations.get(name), f"boundary.{name}")}
                        for name, offset in (("below", -1), ("at", 0), ("above", 1))]
        else:
            need("boundary" not in condition, "non-boundary conditions cannot supply boundary")
            variants = list(indexed(condition.get("variants"), "condition.variants").values())
        for variant in variants:
            obj(variant, "id input expected", "variant")
            variant_id = text(variant.get("id"), "variant.id")
            stimulus = text(variant.get("input"), "variant.input")
            expected = text(variant.get("expected"), "variant.expected")
            key = (identity, variant_id)
            obligations[key] = {
                "id": "COND-" + sha([op, identity, variant_id])[:24],
                "operation": op, "condition": identity, "dimension": dimension,
                "variant": variant_id, "input": stimulus, "expected": expected,
                "requirements": sorted(required), "scenario_ids": [],
            }
            need(len(obligations) <= MAX_RECORDS, "condition obligation budget exceeded; split scope explicitly")
    for op, operation in operations.items():
        for dimension, decision in operation["dimensions"].items():
            # Event/checkpoint obligations already provide the timing denominator.
            timing_owned = dimension in {"external_mutation", "event_order"} and bool(operation["events"])
            if decision["disposition"] == "applicable" and not timing_owned and (op, dimension) not in family_dimensions:
                gaps.append({"kind": "condition_family", "operation": op, "dimension": dimension})
    for scenario_id, scenario in scenarios.items():
        steps = indexed(scenario["steps"], "steps")
        oracles = indexed(scenario["oracles"], "oracles")
        seen = set()
        used_steps = {}
        used_oracles = {}
        credited_dimensions = set()
        for binding in rows(scenario.get("condition_bindings"), "condition_bindings", False):
            obj(binding, "condition variant step_ids oracle_ids", "condition binding")
            condition_id = text(binding.get("condition"), "binding.condition")
            key = (condition_id, text(binding.get("variant"), "binding.variant"))
            need(key in obligations and key not in seen, "unknown/duplicate condition binding")
            seen.add(key)
            obligation = obligations[key]
            need(obligation["operation"] == scenario["operation"], "cross-operation condition binding")
            need(obligation["dimension"] in scenario["dimensions"], "condition binding needs its dimension")
            need(set(obligation["requirements"]) <= set(scenario["requirements"]), "condition requirements missing from scenario")
            step_ids = refs(binding.get("step_ids"), steps, "binding.step_ids")
            oracle_ids = refs(binding.get("oracle_ids"), oracles, "binding.oracle_ids")
            need(step_ids == [step for step in steps if step in step_ids], "condition step order differs from scenario")
            need(obligation["expected"] in [oracles[o]["assertion"] for o in oracle_ids],
                 "condition expected outcome needs an exact bound oracle assertion")
            # Below/at/above and sibling partitions need distinct stimuli and
            # observations, even when one longer scenario exercises them all.
            for used, selected in ((used_steps, step_ids), (used_oracles, oracle_ids)):
                previous = used.setdefault(condition_id, set())
                need(not previous.intersection(selected), "sibling variants require distinct steps and oracles")
                previous.update(selected)
            credited_dimensions.add(obligation["dimension"])
            obligation["scenario_ids"].append(scenario_id)
        if scenario["perturbations"]:
            credited_dimensions.update({"external_mutation", "event_order"})
        for dimension in sorted(set(scenario["dimensions"]) - credited_dimensions):
            gaps.append({"kind": "unbound_scenario_dimension", "scenario": scenario_id, "dimension": dimension})
    result = sorted(obligations.values(), key=lambda row: row["id"])
    for obligation in result:
        obligation["scenario_ids"].sort()
        if not obligation["scenario_ids"]:
            gaps.append({"kind": "condition", **obligation})
    return result, gaps


def execution_coverage(obligations: list, outcomes: dict) -> dict:
    """Only cleanly passed scenarios satisfy a declared obligation at audit."""
    missing = [dict(row) for row in obligations
               if not any(outcomes.get(identity) == "passed" for identity in row["scenario_ids"])]
    return {"total": len(obligations), "passed": len(obligations) - len(missing), "missing": missing}


def check(book: dict, root: Path) -> dict:
    operations, requirements, scenarios, obligations = structure(book, root)
    gaps = []
    # Build joins once per call. Local event/checkpoint IDs are not globally
    # unique: the operation remains part of every key. Keep reporting order
    # below identical to the frozen inventory/obligations, not index order.
    dimensions_by_operation = {identity: set() for identity in operations}
    timing_scenarios = {}
    mapped = set()
    for scenario in scenarios.values():
        operation_id = scenario["operation"]
        dimensions_by_operation[operation_id].update(scenario["dimensions"])
        mapped.update(scenario["requirements"])
        for perturbation in scenario["perturbations"]:
            key = (operation_id, perturbation["event"], perturbation["checkpoint"])
            timing_scenarios.setdefault(key, []).append(scenario["id"])
    for identity, operation in operations.items():
        covered = dimensions_by_operation[identity]
        for dimension, decision in operation["dimensions"].items():
            if decision["disposition"] == "applicable" and dimension not in covered:
                gaps.append({"kind": "dimension", "operation": identity, "dimension": dimension})
    gaps.extend({"kind": "requirement", "id": r} for r in sorted(set(requirements) - mapped))
    for obligation in obligations:
        key = (obligation["operation"], obligation["event"], obligation["checkpoint"])
        matches = timing_scenarios.get(key, [])
        obligation["scenario_ids"] = sorted(matches)
        if not matches:
            gaps.append({"kind": "timing", **obligation})
    gaps.extend({"kind": "discovery", **gap} for gap in book["discovery_gaps"])
    conditions, condition_gaps = condition_coverage(book, operations, scenarios)
    gaps.extend(condition_gaps)
    extra = {"condition_obligations": conditions} if book["schema_version"] == 2 else {}
    return {**extra, "schema_version": book["schema_version"], "claim": "scenario_design_ready" if not gaps else "design_incomplete",
            "book_sha256": sha(book), "scenario_count": len(scenarios), "timing_obligations": obligations,
            "gaps": gaps, "exclusions": book["exclusions"],
            "qualification": "Declared design accounting only: not executed tests, discovery completeness, semantic oracle correctness, visual acceptance, or release safety."}


def audit(book: dict, trace: dict, root: Path) -> dict:
    design = check(book, root)
    scenarios = indexed(book["scenarios"], "scenarios", False)
    obj(trace, "schema_version book_sha256 source_revision run_id target executor started_at finished_at evidence results", "trace")
    need(type(trace.get("schema_version")) is int and trace["schema_version"] == 1, "trace: invalid schema_version")
    need(trace.get("book_sha256") == design["book_sha256"] and trace.get("source_revision") == book["source_revision"], "stale trace binding")
    for key in ("run_id", "target"):
        text(trace.get(key), key)
    executor = obj(trace.get("executor"), "kind name", "executor")
    need(executor.get("kind") in {"visual-model", "runner", "hybrid", "human"}, "invalid executor")
    text(executor.get("name"), "executor.name")
    started, finished = stamp(trace.get("started_at")), stamp(trace.get("finished_at"))
    need(finished >= started, "finished_at precedes started_at")
    evidence = indexed(trace.get("evidence"), "evidence", False)
    paths = set()
    for item in evidence.values():
        obj(item, "id kind path sha256 captured_at", "evidence")
        need(item.get("kind") in CHANNELS | {"action_log"}, "invalid evidence kind")
        name = text(item.get("path"), "evidence.path")
        need(name not in paths, "duplicate evidence path")
        paths.add(name)
        need(item.get("sha256") == file_hash(root, name), f"stale evidence: {name}")
        need(started <= stamp(item.get("captured_at")) <= finished, "evidence outside run time window")

    def observations(value: Any, expected: dict, label: str, oracle: bool = False) -> None:
        actual = indexed(value, label)
        need(set(actual) == set(expected), f"{label}: missing/unknown observations")
        if not oracle:
            need(list(actual) == list(expected), f"{label}: observed step order differs from the scenario")
        for identity, item in actual.items():
            obj(item, "id observation evidence_ids outcome" if oracle else "id observation evidence_ids", label)
            text(item.get("observation"), f"{label}.observation")
            bound = refs(item.get("evidence_ids"), evidence, f"{label}.evidence_ids")
            if oracle:
                need(item.get("outcome") == "passed", f"{label}: unverified oracle cannot pass")
                need(any(evidence[r]["kind"] == expected[identity]["channel"] for r in bound),
                     f"{label}: oracle requires matching evidence channel")

    outcomes = {}
    for result in rows(trace.get("results"), "results", False):
        obj(result, "id attempts", "result")
        identity = text(result.get("id"), "result.id")
        need(identity in scenarios and identity not in outcomes, "unknown/duplicate scenario result")
        scenario = scenarios[identity]
        statuses = []
        for attempt in rows(result.get("attempts"), "attempts"):
            obj(attempt, "status reason steps oracles cleanup", "attempt")
            status = text(attempt.get("status"), "attempt.status")
            need(status in STATUSES, "invalid attempt status")
            statuses.append(status)
            if status != "passed":
                text(attempt.get("reason"), "nonpass reason")
                continue
            observations(attempt.get("steps"), indexed(scenario["steps"], "steps"), "step observations")
            observations(attempt.get("oracles"), indexed(scenario["oracles"], "oracles"), "oracle observations", True)
            cleanup = obj(attempt.get("cleanup"), "status observation evidence_ids", "cleanup")
            need(cleanup.get("status") == "passed", "cleanup not verified")
            text(cleanup.get("observation"), "cleanup.observation")
            refs(cleanup.get("evidence_ids"), evidence, "cleanup.evidence_ids")
        outcomes[identity] = "flaky" if statuses[-1] == "passed" and any(s != "passed" for s in statuses) else statuses[-1]
    statuses = {s: 0 for s in sorted(STATUSES | {"flaky"})}
    gaps = []
    for identity in scenarios:
        status = outcomes.get(identity, "not_run")
        statuses[status] += 1
        if status != "passed":
            gaps.append({"id": identity, "status": status})
    complete = bool(scenarios) and not design["gaps"] and not gaps
    extra = {}
    if book["schema_version"] == 2:
        extra = {"condition_coverage": execution_coverage(design["condition_obligations"], outcomes),
                 "timing_coverage": execution_coverage(design["timing_obligations"], outcomes)}
    return {**extra, "schema_version": book["schema_version"], "claim": "evidence_complete_against_declared_scenarios" if complete else "incomplete",
            "book_sha256": design["book_sha256"], "run_id": trace["run_id"], "target": trace["target"],
            "executor": executor, "statuses": statuses, "execution_gaps": gaps, "design_gaps": design["gaps"],
            "exclusions": book["exclusions"],
            "qualification": "Local trace/hash consistency only; no attestation of model observation, actual execution, correct assertions, exhaustive discovery, visual acceptance, or release safety."}


def load(path: Path) -> dict:
    def unique(pairs):
        result = {}
        for key, value in pairs:
            need(key not in result, f"duplicate JSON key: {key}")
            result[key] = value
        return result
    with path.open(encoding="utf-8") as handle:
        return json.load(handle, object_pairs_hook=unique,
                         parse_constant=lambda value: need(False, f"invalid JSON constant: {value}"))


def schemas(version: int = 1) -> dict:
    """Publish exact field shapes; cross-links/freshness remain code-owned checks."""
    need(type(version) is int and version in {1, 2}, "schema_version must be 1 or 2")
    string = {"type": "string", "minLength": 1}

    def array_of(item, nonempty=True):
        return {"type": "array", "items": item, "minItems": int(nonempty), "maxItems": MAX_RECORDS}

    def enum(values):
        return {"type": "string", "enum": sorted(values)}

    def record(properties, required=None):
        return {"type": "object", "properties": properties, "additionalProperties": False,
                "required": list(properties) if required is None else required}

    texts = {**array_of(string), "uniqueItems": True}
    source = record({"path": string, "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"}})
    dimension = record({"disposition": enum({"applicable", "not_applicable"}), "reason": string, "source_refs": texts})
    step = record({"id": string, "actor": enum({"user", "visual-model", "fixture", "system", "runner", "human"}),
                   "action": string, "observe": string})
    oracle = record({"id": string, "channel": enum(CHANNELS), "assertion": string, "check": string})
    operation = record({
        "id": string, "title": string, "entrypoint": string, "source_refs": texts, "assumptions": texts,
        "side_effects": {"type": "boolean"},
        "dimensions": {"type": "object", "required": list(DIMENSIONS), "additionalProperties": dimension},
        "checkpoints": array_of(record({"id": string, "observation": string}), False),
        "events": array_of(record({"id": string, "change": string, "checkpoints": texts}), False),
    })
    scenario = record({
        "id": string, "operation": string, "title": string, "dimensions": texts, "requirements": texts,
        "technique": texts, "priority": enum({"critical", "high", "normal"}), "preconditions": texts,
        "steps": array_of(step),
        "perturbations": array_of(record({"event": string, "checkpoint": string, "step_id": string}), False),
        "oracles": array_of(oracle), "execution": enum({"visual", "runner", "hybrid", "human"}),
        "cleanup": texts, "safety": texts,
    })
    book = record({
        "schema_version": {"const": 1, "type": "integer"}, "scope": string, "source_revision": string,
        "sources": array_of(source),
        "requirements": array_of(record({"id": string, "source_ref": string, "assertion": string})),
        "operations": array_of(operation), "scenarios": array_of(scenario, False),
        "discovery_gaps": array_of(record({"id": string, "description": string, "owner": string, "next_action": string}), False),
        "exclusions": array_of(record({"scope": string, "reason": string, "owner": string}), False),
    })
    if version == 2:
        variant = record({"id": string, "input": string, "expected": string})
        boundary = record({"limit": {"type": "integer", "minimum": -(10**12), "maximum": 10**12},
                           "unit": string, "expectations": record({k: string for k in ("below", "at", "above")})})
        common = {"id": string, "operation": string, "dimension": string, "title": string,
                  "source_refs": texts, "requirements": texts}
        condition = {"oneOf": [
            record({**common, "kind": {"const": "boundary"}, "boundary": boundary}),
            record({**common, "kind": enum({"partition", "state", "rule", "sequence", "example"}),
                    "variants": array_of(variant)}),
        ]}
        scenario["properties"]["condition_bindings"] = array_of(record({
            "condition": string, "variant": string, "step_ids": texts, "oracle_ids": texts}), False)
        scenario["required"].append("condition_bindings")
        book["properties"]["schema_version"]["const"] = 2
        book["properties"]["conditions"] = array_of(condition, False)
        book["required"].append("conditions")
    observation = record({"id": string, "observation": string, "evidence_ids": texts})
    observed_oracle = record({"id": string, "observation": string, "evidence_ids": texts,
                              "outcome": enum({"passed", "failed", "unobserved"})})
    cleanup = record({"status": enum(STATUSES), "observation": string, "evidence_ids": texts})
    attempt = record({"status": enum(STATUSES), "reason": string, "steps": array_of(observation),
                      "oracles": array_of(observed_oracle), "cleanup": cleanup}, ["status"])
    attempt["allOf"] = [{"if": {"properties": {"status": {"const": "passed"}}},
                          "then": {"required": ["steps", "oracles", "cleanup"]},
                          "else": {"required": ["reason"]}}]
    trace = record({
        "schema_version": {"const": 1, "type": "integer"}, "book_sha256": string,
        "source_revision": string, "run_id": string, "target": string,
        "executor": record({"kind": enum({"visual-model", "runner", "hybrid", "human"}), "name": string}),
        "started_at": string, "finished_at": string,
        "evidence": array_of(record({"id": string, "kind": enum(CHANNELS | {"action_log"}),
                                     "path": string, "sha256": source["properties"]["sha256"], "captured_at": string}), False),
        "results": array_of(record({"id": string, "attempts": array_of(attempt)}), False),
    })
    for schema in (book, trace):
        schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    return {"claim": "schemas_only", "book": book, "trace": trace}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("catalog", "schema", "derive", "check", "audit"))
    parser.add_argument("book", type=Path, nargs="?")
    parser.add_argument("--trace", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--schema-version", type=int, choices=(1, 2), default=None,
                        help="Schema output only; default 1 preserves existing consumers")
    parser.add_argument("--require-v2", action="store_true",
                        help="Reject legacy books instead of silently omitting condition coverage")
    args = parser.parse_args(argv)
    try:
        need(args.schema_version is None or args.mode == "schema", "--schema-version is only for schema")
        need(not args.require_v2 or args.mode in {"derive", "check", "audit"}, "--require-v2 requires a book")
        need((args.mode in {"catalog", "schema"}) == (args.book is None), "only catalog/schema omit the book")
        need((args.mode == "audit") == (args.trace is not None), "only audit requires --trace")
        if args.mode == "schema":
            report = schemas(args.schema_version or 1)
        elif args.mode == "catalog":
            report = {"claim": "questions_only", "dimensions": DIMENSIONS}
        else:
            root = args.root.resolve()
            book = load(root / args.book)
            need(not args.require_v2 or (isinstance(book, dict) and type(book.get("schema_version")) is int
                 and book["schema_version"] == 2),
                 "condition coverage requires schema_version 2; author conditions and rebind evidence, never relabel old traces")
            if args.mode == "audit":
                report = audit(book, load(root / args.trace), root)
            else:
                report = check(book, root)
                if args.mode == "derive":
                    report["claim"] = "obligations_only"
        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
        return 1 if report["claim"] in {"design_incomplete", "incomplete"} else 0
    except (ScenarioError, OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"claim": "invalid", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
