#!/usr/bin/env python3
"""Prepare and inspect ordinary E2E assets without writing files or runtime state.

Risk discovery and semantic review remain human/model work. This helper binds
declared risks to an existing v2 book and delegates execution accounting to its
original auditor. Exit 0 is the requested bounded check, 1 is gaps, 2 invalid
input. No command executes scenarios, authors risk semantics, or creates passes.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path, PurePosixPath
import sys
from typing import Any

import e2e_scenarios as scenarios

MAX_BYTES = 4 * 1024 * 1024
MAX_ROWS = 10000
MAX_TEXT = 8192
MAX_BUNDLE_BOOKS = 1000
QUALIFICATION = (
    "Declared risk/byte/reference accounting only; not complete discovery, "
    "semantic sufficiency, authentic observations, agent/time attestation, "
    "product acceptance or release safety. Runtime acceptance must bind this "
    "ordinary asset and the original intent; hashes do not authenticate authors."
)


class AssetError(ValueError):
    """An ordinary asset cannot support the requested bounded claim."""


def need(ok: bool, message: str) -> None:
    if not ok:
        raise AssetError(message)


def shape(value: Any, fields: str, label: str) -> dict:
    need(isinstance(value, dict), f"{label}: object required")
    need(set(value) == set(fields.split()), f"{label}: missing/unknown fields")
    return value


def text(value: Any, label: str) -> str:
    need(isinstance(value, str) and bool(value.strip()) and len(value) <= MAX_TEXT,
         f"{label}: bounded nonempty string required")
    return value


def rows(value: Any, label: str, nonempty: bool = False) -> list:
    need(isinstance(value, list) and len(value) <= MAX_ROWS and (bool(value) or not nonempty),
         f"{label}: bounded array required")
    return value


def references(value: Any, allowed: Any, label: str, nonempty: bool = True) -> list[str]:
    result = rows(value, label, nonempty)
    for item in result:
        text(item, label)
    need(len(set(result)) == len(result), f"{label}: duplicate reference")
    need(set(result) <= set(allowed), f"{label}: unknown reference")
    return result


def indexed(value: Any, label: str, nonempty: bool = False) -> dict:
    result = {}
    for row in rows(value, label, nonempty):
        need(isinstance(row, dict), f"{label}: object row required")
        identity = text(row.get("id"), f"{label}.id")
        need(identity not in result, f"{label}: duplicate ID")
        result[identity] = row
    return result


def canonical_path(name: str) -> PurePosixPath:
    text(name, "path")
    path = PurePosixPath(name)
    need(not path.is_absolute() and path.parts and ".." not in path.parts
         and "\\" not in name and ":" not in name and path.as_posix() == name,
         f"unsafe/noncanonical path: {name}")
    return path


def safe_file(root: Path, name: str) -> Path:
    path = canonical_path(name)
    root = root.resolve(strict=True)
    candidate = root
    for part in path.parts:
        candidate /= part
        need(not candidate.is_symlink() and not getattr(candidate, "is_junction", lambda: False)(),
             f"linked path is not an immutable input: {name}")
    need(candidate.resolve().is_relative_to(root) and candidate.is_file(),
         f"missing/escaping file: {name}")
    return candidate


def read_bytes(root: Path, name: str) -> bytes:
    path = safe_file(root, name)
    with path.open("rb") as handle:
        value = handle.read(MAX_BYTES + 1)
    need(len(value) <= MAX_BYTES, f"input exceeds {MAX_BYTES} byte budget: {name}")
    return value


def digest_file(root: Path, name: str) -> str:
    # Large source/evidence files are hashed without loading them into memory.
    with safe_file(root, name).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def decode(value: bytes) -> dict:
    def pairs(items):
        result = {}
        for key, item in items:
            need(key not in result, f"duplicate JSON key: {key}")
            result[key] = item
        return result

    def constant(value):
        raise AssetError(f"non-finite JSON number: {value}")

    result = json.loads(value.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    need(isinstance(result, dict), "JSON root must be an object")
    return result


def load(root: Path, name: str) -> dict:
    return decode(read_bytes(root, name))


def strength_prepare(intent_path: str, book_path: str, root: Path) -> dict:
    """Freeze supplied semantics; never infer risks or produce observations."""
    root = root.resolve(strict=True)
    intent_bytes = read_bytes(root, intent_path)
    intent, book = decode(intent_bytes), load(root, book_path)
    shape(intent, "schema_version scope risks gaps exclusions", "strength intent")
    need(type(intent["schema_version"]) is int and intent["schema_version"] == 1,
         "unsupported strength intent version")
    text(intent["scope"], "scope")
    need(type(book.get("schema_version")) is int and book["schema_version"] == 2, "v2 book required")
    design = scenarios.check(book, root)
    sources = {row["path"]: row["sha256"] for row in book["sources"]}
    for path, expected in sources.items():
        need(digest_file(root, path) == expected, f"stale source: {path}")
    operations = {row["id"]: row for row in book["operations"]}
    requirements = {row["id"]: row for row in book["requirements"]}
    conditions = {(row["condition"], row["variant"]): row for row in design["condition_obligations"]}
    condition_sources = {row["id"]: row["source_refs"] for row in book["conditions"]}
    timing = {(row["operation"], row["event"], row["checkpoint"]): row for row in design["timing_obligations"]}
    cards = {row["id"]: row for row in book["scenarios"]}
    risks = indexed(intent["risks"], "risks", True)
    gaps = [{"kind": "book", "detail": row} for row in design["gaps"]]
    interactions = []
    work = 0
    for risk_id, risk in risks.items():
        shape(risk, "id operation requirements source_refs rationale interactions", "risk")
        op = text(risk["operation"], "risk.operation")
        need(op in operations, "risk: unknown operation")
        text(risk["rationale"], "risk.rationale")
        required = references(risk["requirements"], requirements, "risk.requirements")
        source_refs = references(risk["source_refs"], sources, "risk.source_refs")
        need({requirements[r]["source_ref"] for r in required} <= set(source_refs),
             "risk must bind its requirement sources")
        for interaction_id, interaction in indexed(risk["interactions"], "interactions", True).items():
            shape(interaction, "id conditions timing bindings", "interaction")
            work += 1
            need(work <= MAX_ROWS, "interaction/binding budget exceeded")
            condition_keys, timing_keys = set(), set()
            for ref in rows(interaction["conditions"], "interaction.conditions"):
                shape(ref, "condition variant", "condition reference")
                key = (text(ref["condition"], "condition"), text(ref["variant"], "variant"))
                need(key in conditions and key not in condition_keys, "unknown/duplicate condition variant")
                condition = conditions[key]
                need(condition["operation"] == op and set(condition["requirements"]) <= set(required),
                     "condition operation/requirements differ from risk")
                need(set(condition_sources[key[0]]) <= set(source_refs), "condition sources missing from risk")
                condition_keys.add(key)
            for ref in rows(interaction["timing"], "interaction.timing"):
                shape(ref, "event checkpoint", "timing reference")
                key = (op, text(ref["event"], "event"), text(ref["checkpoint"], "checkpoint"))
                need(key in timing and key not in timing_keys, "unknown/duplicate timing pair")
                timing_keys.add(key)
            if timing_keys:
                need(set(operations[op]["source_refs"]) <= set(source_refs), "timing operation sources missing from risk")
            need(len(condition_keys) + 2 * len(timing_keys) >= 2,
                 "interaction needs two conditions or an explicit event/checkpoint pair")
            binding_ids = set()
            for binding in rows(interaction["bindings"], "interaction.bindings"):
                work += 1
                need(work <= MAX_ROWS, "interaction/binding budget exceeded")
                shape(binding, "scenario step_ids oracle_ids", "risk binding")
                identity = text(binding["scenario"], "binding.scenario")
                need(identity in cards and identity not in binding_ids, "unknown/duplicate bound scenario")
                binding_ids.add(identity)
                card = cards[identity]
                need(card["operation"] == op and set(required) <= set(card["requirements"]),
                     "scenario operation/requirements differ from risk")
                steps = references(binding["step_ids"], [s["id"] for s in card["steps"]], "binding.step_ids")
                need(steps == [s["id"] for s in card["steps"] if s["id"] in steps], "risk step order differs from book")
                oracles = {o["id"]: o for o in card["oracles"]}
                selected = references(binding["oracle_ids"], oracles, "binding.oracle_ids")
                bound_conditions = {(c["condition"], c["variant"]): c for c in card["condition_bindings"]}
                need(condition_keys <= set(bound_conditions), "scenario does not exercise complete interaction")
                for key in condition_keys:
                    bound = bound_conditions[key]
                    need(set(bound["step_ids"]) <= set(steps) and set(bound["oracle_ids"]) <= set(selected),
                         "risk binding omits condition stimulus/oracle")
                bound_timing = {(op, p["event"], p["checkpoint"]): p for p in card["perturbations"]}
                need(timing_keys <= set(bound_timing), "scenario does not exercise timing pair")
                need(all(bound_timing[key]["step_id"] in steps for key in timing_keys), "timing stimulus missing")
                if operations[op]["side_effects"]:
                    need(any(oracles[o]["channel"] not in {"visual", "accessibility", "human"} for o in selected),
                         "risk binding needs independent effect oracle")
            pair = {"risk": risk_id, "interaction": interaction_id}
            interactions.append(pair)
            if not binding_ids:
                gaps.append({"kind": "unbound_interaction", **pair})
    declared_gaps = indexed(intent["gaps"], "gaps")
    for row in declared_gaps.values():
        shape(row, "id reason owner next_action", "gap")
        for key, value in row.items():
            text(value, "gap." + key)
        gaps.append({"kind": "declared", **row})
    exclusions = indexed(intent["exclusions"], "exclusions")
    need(not (set(risks) & set(exclusions)), "risk cannot also be excluded")
    for row in exclusions.values():
        shape(row, "id reason source_refs", "exclusion")
        text(row["reason"], "exclusion.reason")
        references(row["source_refs"], sources, "exclusion.source_refs")
    # Check named inputs again: never silently freeze a changed intent/book.
    need(read_bytes(root, intent_path) == intent_bytes, "intent changed during preparation")
    need(scenarios.sha(load(root, book_path)) == design["book_sha256"], "book changed during preparation")
    for path, expected in sources.items():
        need(digest_file(root, path) == expected, f"source changed during preparation: {path}")
    return {"schema_version": 1, "kind": "e2e-strength",
            "intent_ref": {"path": intent_path, "sha256": hashlib.sha256(intent_bytes).hexdigest()},
            "intent_sha256": scenarios.sha(intent), "intent": intent,
            "book": {"path": book_path, "sha256": design["book_sha256"]},
            "source_revision": book["source_revision"], "sources": book["sources"],
            "denominator": {"risk_ids": sorted(risks), "interactions": interactions,
                            "gap_ids": sorted(declared_gaps), "exclusion_ids": sorted(exclusions)},
            "claim": "strength_incomplete" if gaps else "declared_strength_ready", "gaps": gaps,
            "qualification": QUALIFICATION}


def strength_audit(asset_path: str, root: Path, trace_path: str | None = None) -> dict:
    root = root.resolve(strict=True)
    asset = load(root, asset_path)
    shape(asset, "schema_version kind intent_ref intent_sha256 intent book source_revision sources denominator claim gaps qualification", "strength asset")
    shape(asset["intent_ref"], "path sha256", "intent_ref")
    shape(asset["book"], "path sha256", "book")
    expected = strength_prepare(asset["intent_ref"]["path"], asset["book"]["path"], root)
    need(scenarios.sha(asset) == scenarios.sha(expected),
         "stale/changed strength asset or original intent; prepare and independently review a new asset")
    report = {"schema_version": 1, "claim": "strength_incomplete" if asset["gaps"] else "declared_strength_checked",
              "strength_sha256": scenarios.sha(asset), "intent_sha256": asset["intent_sha256"],
              "book_sha256": asset["book"]["sha256"], "denominator": asset["denominator"],
              "design_gaps": asset["gaps"], "execution": "unrequested", "qualification": QUALIFICATION}
    if trace_path is not None:
        trace = load(root, trace_path)
        book = load(root, asset["book"]["path"])
        # Existing audit is authoritative for every declared case, including
        # cases outside risk bindings. A passing overlap cannot erase a failure.
        execution = scenarios.audit(book, trace, root)
        missing = {row["id"]: row["status"] for row in execution["execution_gaps"]}
        observations = []
        for risk in asset["intent"]["risks"]:
            for interaction in risk["interactions"]:
                observations.append({"risk": risk["id"], "interaction": interaction["id"],
                                     "scenarios": [{"id": b["scenario"], "status": missing.get(b["scenario"], "passed")}
                                                   for b in interaction["bindings"]]})
        report.update(execution="observed", scenario_audit=execution, risk_observations=observations,
                      trace={"path": trace_path, "sha256": scenarios.sha(trace)})
        if execution["claim"] != "evidence_complete_against_declared_scenarios":
            report["claim"] = "strength_incomplete"
        need(scenarios.sha(load(root, asset_path)) == scenarios.sha(asset)
             and scenarios.sha(strength_prepare(asset["intent_ref"]["path"], asset["book"]["path"], root)) == scenarios.sha(asset),
             "strength inputs changed during audit")
        need(load(root, trace_path) == trace, "trace changed during audit")
        for evidence in trace["evidence"]:
            need(digest_file(root, evidence["path"]) == evidence["sha256"], "trace evidence changed during audit")
    return report


def strength_schemas() -> dict:
    string = {"type": "string", "minLength": 1, "maxLength": MAX_TEXT}

    def array(item, minimum=0):
        return {"type": "array", "items": item, "minItems": minimum, "maxItems": MAX_ROWS}

    def obj(properties):
        return {"type": "object", "additionalProperties": False, "properties": properties, "required": list(properties)}

    refs = {**array(string, 1), "uniqueItems": True}
    interaction = obj({"id": string, "conditions": array(obj({"condition": string, "variant": string})),
                       "timing": array(obj({"event": string, "checkpoint": string})),
                       "bindings": array(obj({"scenario": string, "step_ids": refs, "oracle_ids": refs}))})
    intent = obj({"schema_version": {"const": 1, "type": "integer"}, "scope": string,
                  "risks": array(obj({"id": string, "operation": string, "requirements": refs, "source_refs": refs,
                                      "rationale": string, "interactions": array(interaction, 1)}), 1),
                  "gaps": array(obj({"id": string, "reason": string, "owner": string, "next_action": string})),
                  "exclusions": array(obj({"id": string, "reason": string, "source_refs": refs}))})
    binding = obj({"path": string, "sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"}})
    asset = obj({"schema_version": {"const": 1, "type": "integer"}, "kind": {"const": "e2e-strength"},
                 "intent_ref": binding, "intent_sha256": binding["properties"]["sha256"], "intent": intent,
                 "book": binding, "source_revision": string, "sources": array(binding, 1),
                 "denominator": obj({"risk_ids": refs,
                                     "interactions": array(obj({"risk": string, "interaction": string}), 1),
                                     "gap_ids": array(string), "exclusion_ids": array(string)}),
                 "claim": {"enum": ["declared_strength_ready", "strength_incomplete"]},
                 "gaps": array({"type": "object"}), "qualification": {"const": QUALIFICATION}})
    return {"claim": "schemas_only", "intent": {"$schema": "https://json-schema.org/draft/2020-12/schema", **intent},
            "asset": {"$schema": "https://json-schema.org/draft/2020-12/schema", **asset},
            "qualification": "Schemas do not author risk semantics; semantic cross-links require prepare/audit."}


BUNDLE_QUALIFICATION = (
    "Preparation reuse and preservation of original run evidence only; never a new-run pass. "
    "Stage 2 must independently accept the original parent, intent and exact bundle bytes; "
    "Stage 3/4 runtime packets must consume that accepted bundle digest before execution. "
    "This stateless helper checks consistency, not approval, chronology, agent identity, "
    "complete dependency discovery or the authenticity of the executed build."
)


def file_bindings(value: Any, root: Path, label: str, *, nonempty: bool = False, verify: bool = True) -> list:
    seen = set()
    for row in rows(value, label, nonempty):
        shape(row, "path sha256", label + " binding")
        name = text(row["path"], label + ".path")
        canonical_path(name)
        digest = digest_value(row["sha256"])
        need(name not in seen, f"{label}: duplicate file binding")
        seen.add(name)
        if verify:
            need(digest_file(root, name) == digest, f"stale {label}: {name}")
    return value


def digest_value(value: Any) -> str:
    digest = text(value, "sha256")
    need(len(digest) == 64 and all(c in "0123456789abcdef" for c in digest), "SHA-256 must be lowercase hex")
    return digest


def dependency_closure(graph: dict[str, list[str]], label: str) -> dict[str, set[str]]:
    """Bounded iterative DAG expansion avoids recursive-stack limits."""
    need(len(graph) <= MAX_BUNDLE_BOOKS, f"{label}: dependency budget exceeded")
    closure = {}
    for identity, dependencies in graph.items():
        references(dependencies, graph, label + ".depends_on", False)
        need(identity not in dependencies, f"{label}: self dependency")
    pending = set(graph)
    while pending:
        ready = sorted(identity for identity in pending if set(graph[identity]) <= set(closure))
        need(bool(ready), f"{label}: cyclic dependency graph")
        for identity in ready:
            closure[identity] = set(graph[identity])
            for dependency in graph[identity]:
                closure[identity].update(closure[dependency])
            pending.remove(identity)
    return closure


def parent_scope(value: dict, root: Path, *, verify: bool = True) -> tuple[dict, dict]:
    shape(value, "schema_version scope request_sources obligations gaps exclusions", "parent scope")
    need(type(value["schema_version"]) is int and value["schema_version"] == 1, "unsupported parent version")
    text(value["scope"], "parent.scope")
    files = file_bindings(value["request_sources"], root, "parent request", nonempty=True, verify=verify)
    source_paths = {row["path"] for row in files}
    obligations = indexed(value["obligations"], "parent obligations", True)
    need(len(obligations) <= MAX_BUNDLE_BOOKS, "parent obligation budget exceeded")
    for row in obligations.values():
        shape(row, "id kind description source_refs depends_on", "parent obligation")
        need(row["kind"] in {"operation", "cross_feature"}, "unknown parent obligation kind")
        text(row["description"], "obligation.description")
        references(row["source_refs"], source_paths, "obligation.source_refs")
        if row["kind"] == "cross_feature":
            need(len(rows(row["depends_on"], "cross-feature dependencies")) >= 2,
                 "cross-feature obligation must retain at least two upstream scopes")
    graph = {identity: row["depends_on"] for identity, row in obligations.items()}
    closure = dependency_closure(graph, "parent")
    for row in indexed(value["gaps"], "parent gaps").values():
        shape(row, "id reason owner next_action", "parent gap")
        for key, item in row.items():
            text(item, "gap." + key)
    exclusions = indexed(value["exclusions"], "parent exclusions")
    need(not set(exclusions).intersection(obligations), "required obligation cannot be relabelled excluded")
    for row in exclusions.values():
        shape(row, "id reason source_refs", "parent exclusion")
        text(row["reason"], "exclusion.reason")
        references(row["source_refs"], source_paths, "exclusion.source_refs")
    return obligations, closure


def bundle_intent(value: dict, root: Path, *, verify: bool = True) -> tuple[dict, dict]:
    shape(value, "schema_version books", "bundle intent")
    need(type(value["schema_version"]) is int and value["schema_version"] == 1, "unsupported bundle intent version")
    books = indexed(value["books"], "bundle books", True)
    need(len(books) <= MAX_BUNDLE_BOOKS, "bundle book budget exceeded")
    paths = set()
    for row in books.values():
        shape(row, "id path scope_bindings depends_on fixtures target strength_refs", "book intent")
        name = text(row["path"], "book.path")
        canonical_path(name)
        unique = safe_file(root, name) if verify else name
        need(unique not in paths, "duplicate book path; cannot split one book after execution")
        paths.add(unique)
        shape(row["target"], "id bindings", "target")
        text(row["target"]["id"], "target.id")
        file_bindings(row["target"]["bindings"], root, "target", nonempty=True, verify=verify)
        file_bindings(row["fixtures"], root, "fixtures", verify=verify)
        file_bindings(row["strength_refs"], root, "strength refs", nonempty=True, verify=verify)
        scopes = set()
        for binding in rows(row["scope_bindings"], "scope bindings", True):
            shape(binding, "scope_id operation_ids scenario_ids", "scope binding")
            identity = text(binding["scope_id"], "scope_id")
            need(identity not in scopes, "duplicate scope binding")
            scopes.add(identity)
            for field in ("operation_ids", "scenario_ids"):
                references(binding[field], binding[field], field)
    closure = dependency_closure({identity: row["depends_on"] for identity, row in books.items()}, "books")
    return books, closure


def bundle_prepare(intent_path: str, parent_path: str, root: Path) -> dict:
    root = root.resolve(strict=True)
    parent_bytes, intent_bytes = read_bytes(root, parent_path), read_bytes(root, intent_path)
    parent, intent = decode(parent_bytes), decode(intent_bytes)
    obligations, scope_closure = parent_scope(parent, root)
    books, closure = bundle_intent(intent, root)
    snapshots, mapping = [], {identity: set() for identity in obligations}
    gaps = [{"kind": "parent_gap", "detail": gap} for gap in parent["gaps"]]
    for identity, row in books.items():
        book = load(root, row["path"])
        need(type(book.get("schema_version")) is int and book["schema_version"] == 2, "bundle requires v2 books")
        design = scenarios.check(book, root)
        file_bindings(book["sources"], root, "book sources", nonempty=True)
        cards = {card["id"]: card for card in book["scenarios"]}
        operations = {op["id"] for op in book["operations"]}
        bound_scopes, bound_cards, bound_operations = set(), set(), set()
        for binding in rows(row["scope_bindings"], "scope bindings", True):
            shape(binding, "scope_id operation_ids scenario_ids", "scope binding")
            scope = text(binding["scope_id"], "scope_id")
            need(scope in obligations and scope not in bound_scopes, "unknown/duplicate scope binding")
            selected_ops = references(binding["operation_ids"], operations, "scope.operation_ids")
            selected_cards = references(binding["scenario_ids"], cards, "scope.scenario_ids")
            need({cards[c]["operation"] for c in selected_cards} == set(selected_ops), "scope operation/scenario mapping differs")
            if obligations[scope]["kind"] == "cross_feature":
                need(all("cross_feature" in cards[c]["dimensions"] for c in selected_cards),
                     "cross-feature obligation requires explicit cross-feature scenarios")
            mapping[scope].add(identity)
            bound_scopes.add(scope)
            bound_cards.update(selected_cards)
            bound_operations.update(selected_ops)
        need(bound_cards == set(cards) and bound_operations == operations,
             "every book scenario and operation needs a parent-scope mapping")
        gaps.extend({"kind": "book_gap", "book_id": identity, "detail": gap} for gap in design["gaps"])
        for ref in row["strength_refs"]:
            strength = load(root, ref["path"])
            result = strength_audit(ref["path"], root)
            need(strength["book"] == {"path": row["path"], "sha256": design["book_sha256"]},
                 "strength ref is not bound to this exact book")
            if result["claim"] == "strength_incomplete":
                gaps.append({"kind": "strength_gap", "book_id": identity, "path": ref["path"], "detail": result["design_gaps"]})
        snapshot = {"id": identity, "book": {"path": row["path"], "sha256": design["book_sha256"]},
                    "source_revision": book["source_revision"], "sources": book["sources"],
                    "scenario_ids": sorted(cards), "scope_bindings": row["scope_bindings"],
                    "depends_on": row["depends_on"], "fixtures": row["fixtures"], "target": row["target"],
                    "strength_refs": row["strength_refs"], "design_gaps": design["gaps"]}
        snapshot["binding_sha256"] = scenarios.sha(snapshot)
        snapshots.append(snapshot)
    for scope, owner_books in mapping.items():
        if not owner_books:
            gaps.append({"kind": "unmapped_scope", "scope_id": scope})
        for consumer in owner_books:
            for upstream in scope_closure[scope]:
                for producer in mapping[upstream]:
                    need(producer == consumer or producer in closure[consumer],
                         f"missing book dependency for parent obligation: {producer} -> {consumer}")
    # A book explicitly read as another book's source/fixture/build is a real
    # producer input; declaring two unrelated book names cannot erase the edge.
    path_owner = {safe_file(root, row["path"]): identity for identity, row in books.items()}
    for snapshot in snapshots:
        for source in snapshot["sources"] + snapshot["fixtures"] + snapshot["target"]["bindings"]:
            producer = path_owner.get(safe_file(root, source["path"]))
            need(producer is None or producer == snapshot["id"] or producer in closure[snapshot["id"]],
                 "missing producer-book input dependency")
    need(read_bytes(root, parent_path) == parent_bytes and read_bytes(root, intent_path) == intent_bytes,
         "parent/intent changed during bundle preparation")
    parent_scope(parent, root)
    for snapshot in snapshots:
        need(scenarios.sha(load(root, snapshot["book"]["path"])) == snapshot["book"]["sha256"], "book changed during preparation")
        for label, bindings in (("sources", snapshot["sources"]), ("fixtures", snapshot["fixtures"]),
                                ("target", snapshot["target"]["bindings"]), ("strength", snapshot["strength_refs"])):
            file_bindings(bindings, root, label)
    return {"schema_version": 1, "kind": "e2e-bundle", "parent": parent, "intent": intent,
            "parent_ref": {"path": parent_path, "sha256": hashlib.sha256(parent_bytes).hexdigest()},
            "intent_ref": {"path": intent_path, "sha256": hashlib.sha256(intent_bytes).hexdigest()},
            "books": snapshots, "denominator": {"scope_ids": sorted(obligations), "book_ids": sorted(books),
                "gap_ids": sorted(g["id"] for g in parent["gaps"]), "exclusion_ids": sorted(e["id"] for e in parent["exclusions"])},
            "claim": "bundle_incomplete" if gaps else "bundle_preparation_ready", "gaps": gaps,
            "qualification": BUNDLE_QUALIFICATION}


def bundle_impact(asset_path: str, expected_sha256: str, root: Path, runs_path: str | None = None) -> dict:
    root = root.resolve(strict=True)
    original = read_bytes(root, asset_path)
    actual_digest = hashlib.sha256(original).hexdigest()
    need(expected_sha256 == actual_digest, "bundle bytes do not match the externally accepted SHA-256")
    asset = decode(original)
    shape(asset, "schema_version kind parent intent parent_ref intent_ref books denominator claim gaps qualification", "bundle asset")
    need(type(asset["schema_version"]) is int and asset["schema_version"] == 1 and asset["kind"] == "e2e-bundle",
         "unsupported bundle asset")
    need(asset["qualification"] == BUNDLE_QUALIFICATION, "bundle qualification changed")
    need(asset["claim"] in {"bundle_preparation_ready", "bundle_incomplete"}, "unknown bundle claim")
    rows(asset["gaps"], "bundle gaps")
    for name in ("parent", "intent"):
        binding = shape(asset[name + "_ref"], "path sha256", name + "_ref")
        current = read_bytes(root, binding["path"])
        need(hashlib.sha256(current).hexdigest() == binding["sha256"] and scenarios.sha(decode(current)) == scenarios.sha(asset[name]),
             f"original {name} changed; refreeze the complete scope and obtain new independent acceptance, never reuse old run bindings")
    obligations, _ = parent_scope(asset["parent"], root)
    books = indexed(asset["books"], "frozen books", True)
    expected_books, _ = bundle_intent(asset["intent"], root, verify=False)
    need(set(books) == set(expected_books) and scenarios.sha(asset["denominator"]) == scenarios.sha({
        "scope_ids": sorted(obligations), "book_ids": sorted(books),
        "gap_ids": sorted(g["id"] for g in asset["parent"]["gaps"]),
        "exclusion_ids": sorted(e["id"] for e in asset["parent"]["exclusions"])}), "bundle denominator differs from original scope")
    graph = {identity: book["depends_on"] for identity, book in books.items()}
    closure = dependency_closure(graph, "frozen books")
    reasons, live_books = {}, {}
    for identity, snapshot in books.items():
        shape(snapshot, "id book source_revision sources scenario_ids scope_bindings depends_on fixtures target strength_refs design_gaps binding_sha256", "book snapshot")
        unsigned = {k: v for k, v in snapshot.items() if k != "binding_sha256"}
        need(scenarios.sha(unsigned) == snapshot["binding_sha256"], "book binding digest differs")
        file_bindings([snapshot["book"]], root, "book", verify=False)
        text(snapshot["source_revision"], "source_revision")
        references(snapshot["scenario_ids"], snapshot["scenario_ids"], "scenario_ids")
        rows(snapshot["design_gaps"], "book design gaps")
        for key in ("scope_bindings", "depends_on", "fixtures", "target", "strength_refs"):
            need(scenarios.sha(snapshot[key]) == scenarios.sha(expected_books[identity][key]), f"book {key} differs from original intent")
        need(snapshot["book"]["path"] == expected_books[identity]["path"], "book path differs from original intent")
        reasons[identity] = []
        try:
            book = load(root, snapshot["book"]["path"])
            if scenarios.sha(book) != snapshot["book"]["sha256"]:
                reasons[identity].append({"kind": "book_changed", "path": snapshot["book"]["path"]})
            else:
                live_books[identity] = book
        except (AssetError, OSError, ValueError, TypeError, RecursionError) as exc:
            reasons[identity].append({"kind": "book_unavailable", "detail": str(exc)})
        for kind, bindings in (("source", snapshot["sources"]), ("fixture", snapshot["fixtures"]),
                               ("target", snapshot["target"]["bindings"]), ("strength", snapshot["strength_refs"])):
            file_bindings(bindings, root, kind, verify=False)
            for binding in bindings:
                try:
                    fresh = digest_file(root, binding["path"]) == binding["sha256"]
                except (AssetError, OSError, ValueError) as exc:
                    reasons[identity].append({"kind": kind + "_unavailable", "path": binding["path"], "detail": str(exc)})
                else:
                    if not fresh:
                        reasons[identity].append({"kind": kind + "_changed", "path": binding["path"]})
        if not reasons[identity]:
            try:
                design = scenarios.check(live_books[identity], root)
                need(design["book_sha256"] == snapshot["book"]["sha256"], "book drift")
                need(scenarios.sha(live_books[identity]["sources"]) == scenarios.sha(snapshot["sources"])
                     and live_books[identity]["source_revision"] == snapshot["source_revision"]
                     and sorted(s["id"] for s in live_books[identity]["scenarios"]) == snapshot["scenario_ids"],
                     "snapshot differs from its whole book")
                for ref in snapshot["strength_refs"]:
                    strength_audit(ref["path"], root)
            except (AssetError, scenarios.ScenarioError, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
                reasons[identity].append({"kind": "input_invalid", "detail": str(exc)})
    direct = {identity for identity in books if reasons[identity]}
    affected = {identity for identity in books if identity in direct or closure[identity].intersection(direct)}
    for identity in affected - direct:
        reasons[identity].append({"kind": "upstream_changed", "book_ids": sorted(closure[identity].intersection(direct))})
    report = {"schema_version": 1, "claim": "bundle_impact_detected" if affected or asset["gaps"] else "bundle_preparation_reusable",
              "bundle_file_sha256": actual_digest, "denominator": asset["denominator"], "parent_gaps": asset["parent"]["gaps"],
              "scenario_denominator": [{"book_id": identity, "book_sha256": books[identity]["book"]["sha256"],
                                        "scenario_ids": books[identity]["scenario_ids"]} for identity in sorted(books)],
              "exclusions": asset["parent"]["exclusions"], "preparation_gaps": asset["gaps"],
              "directly_changed_books": sorted(direct), "affected_books": sorted(affected),
              "reusable_preparation_books": sorted(set(books) - affected),
              "affected_scope_ids": sorted({s["scope_id"] for b in affected for s in books[b]["scope_bindings"]}),
              "reasons": {identity: reasons[identity] for identity in sorted(affected)},
              "execution": "unrequested", "preserved_old_run_evidence": [], "run_gaps": [],
              "qualification": BUNDLE_QUALIFICATION}
    if runs_path is not None:
        run_bytes = read_bytes(root, runs_path)
        index = decode(run_bytes)
        shape(index, "schema_version bundle_file_sha256 runs", "run evidence index")
        need(type(index["schema_version"]) is int and index["schema_version"] == 1, "unsupported run index")
        need(index["bundle_file_sha256"] == actual_digest, "old runs cannot be rebound to a new/refrozen bundle")
        by_book = {identity: [] for identity in books}
        for row in rows(index["runs"], "runs"):
            shape(row, "book_id bundle_file_sha256 book_binding_sha256 trace execution_binding", "run reference")
            identity = text(row["book_id"], "run.book_id")
            digest_value(row["bundle_file_sha256"])
            digest_value(row["book_binding_sha256"])
            file_bindings([row["trace"]], root, "trace", verify=False)
            file_bindings([row["execution_binding"]], root, "execution binding", verify=False)
            if identity not in books:
                report["run_gaps"].append({"kind": "unknown_book", "book_id": identity})
            else:
                by_book[identity].append(row)
        for identity, bound_runs in by_book.items():
            if len(bound_runs) != 1:
                report["run_gaps"].append({"kind": "missing_run" if not bound_runs else "conflicting_runs", "book_id": identity})
                continue
            row = bound_runs[0]
            if row["bundle_file_sha256"] != actual_digest or row["book_binding_sha256"] != books[identity]["binding_sha256"]:
                report["run_gaps"].append({"kind": "stale_run_binding", "book_id": identity})
                continue
            if identity in affected:
                report["run_gaps"].append({"kind": "affected_book_requires_fresh_execution", "book_id": identity})
                continue
            audit = None
            try:
                file_bindings([row["trace"]], root, "trace", nonempty=True)
                trace = load(root, row["trace"]["path"])
                need(trace["target"] == books[identity]["target"]["id"], "trace target differs from frozen target")
                audit = scenarios.audit(live_books[identity], trace, root)
                need(audit["claim"] == "evidence_complete_against_declared_scenarios", "original trace remains incomplete")
                file_bindings([row["execution_binding"]], root, "execution binding", nonempty=True)
                receipt = load(root, row["execution_binding"]["path"])
                expected = {"schema_version": 1, "bundle_file_sha256": actual_digest,
                            "book_binding_sha256": books[identity]["binding_sha256"], "book_id": identity,
                            "run_id": trace["run_id"], "target": trace["target"]}
                need(scenarios.sha(receipt) == scenarios.sha(expected), "original execution binding differs from this bundle/book/run")
                receipts = []
                for evidence in trace["evidence"]:
                    if evidence["kind"] != "log":
                        continue
                    try:
                        value = decode(read_bytes(root, evidence["path"]))
                    except (AssetError, ValueError, UnicodeError):
                        continue  # Ordinary textual logs are not binding receipts.
                    if "bundle_file_sha256" in value or "book_binding_sha256" in value:
                        receipts.append(evidence)
                need(len(receipts) == 1 and receipts[0]["id"] == "bundle-execution-binding"
                     and receipts[0]["path"] == row["execution_binding"]["path"]
                     and receipts[0]["sha256"] == row["execution_binding"]["sha256"],
                     "execution binding must be the unique bundle-execution-binding log evidence in the original trace; an index alone cannot bind old runs")
                report["preserved_old_run_evidence"].append({"book_id": identity, "original_run_id": trace["run_id"],
                    "trace": row["trace"], "execution_binding": row["execution_binding"],
                    "book_sha256": audit["book_sha256"], "scenario_audit": audit,
                    "claim": "preserve_old_run_evidence"})
            except (AssetError, scenarios.ScenarioError, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
                gap = {"kind": "unverified_run", "book_id": identity, "detail": str(exc)}
                if audit is not None:
                    gap["original_scenario_audit"] = audit
                report["run_gaps"].append(gap)
        for gap in report["run_gaps"]:
            if gap["book_id"] in books:
                gap["scenario_ids"] = books[gap["book_id"]]["scenario_ids"]
        need(read_bytes(root, runs_path) == run_bytes, "run index changed during impact check")
        report["execution"] = "historical_evidence_rechecked"
        if report["run_gaps"]:
            report["claim"] = "bundle_impact_detected"
    # Recheck all inputs for books whose old evidence/preparation is preserved.
    for identity in set(books) - affected:
        snapshot = books[identity]
        need(scenarios.sha(load(root, snapshot["book"]["path"])) == snapshot["book"]["sha256"], "book changed during impact check")
        for bindings in (snapshot["sources"], snapshot["fixtures"], snapshot["target"]["bindings"], snapshot["strength_refs"]):
            file_bindings(bindings, root, "final input")
    for entry in report["preserved_old_run_evidence"]:
        file_bindings([entry["trace"]], root, "final trace")
        trace = load(root, entry["trace"]["path"])
        for evidence in trace["evidence"]:
            need(digest_file(root, evidence["path"]) == evidence["sha256"], "evidence changed during impact check")
    need(read_bytes(root, asset_path) == original, "bundle changed during impact check")
    for name in ("parent", "intent"):
        need(digest_file(root, asset[name + "_ref"]["path"]) == asset[name + "_ref"]["sha256"], "original scope changed during impact check")
    parent_scope(asset["parent"], root)
    return report


def bundle_schemas() -> dict:
    string = {"type": "string", "minLength": 1, "maxLength": MAX_TEXT}
    digest = {"type": "string", "pattern": "^[0-9a-f]{64}$"}

    def array(item, minimum=0, maximum=MAX_ROWS):
        return {"type": "array", "items": item, "minItems": minimum, "maxItems": maximum}

    def obj(properties):
        return {"type": "object", "additionalProperties": False, "properties": properties, "required": list(properties)}

    def refs(minimum=0):
        return {**array(string, minimum), "uniqueItems": True}

    version = {"const": 1, "type": "integer"}
    binding = obj({"path": string, "sha256": digest})
    gap = obj({"id": string, "reason": string, "owner": string, "next_action": string})
    parent = obj({"schema_version": version, "scope": string, "request_sources": array(binding, 1),
                  "obligations": array(obj({"id": string, "kind": {"enum": ["operation", "cross_feature"]},
                                            "description": string, "source_refs": refs(1), "depends_on": refs()}), 1, MAX_BUNDLE_BOOKS),
                  "gaps": array(gap), "exclusions": array(obj({"id": string, "reason": string, "source_refs": refs(1)}))})
    scope_binding = obj({"scope_id": string, "operation_ids": refs(1), "scenario_ids": refs(1)})
    target = obj({"id": string, "bindings": array(binding, 1)})
    shared = {"scope_bindings": array(scope_binding, 1), "depends_on": refs(), "fixtures": array(binding),
              "target": target, "strength_refs": array(binding, 1)}
    intent = obj({"schema_version": version,
                  "books": array(obj({"id": string, "path": string, **shared}), 1, MAX_BUNDLE_BOOKS)})
    snapshot = obj({"id": string, "book": binding, "source_revision": string, "sources": array(binding, 1),
                    "scenario_ids": refs(1), **shared, "design_gaps": array({"type": "object"}), "binding_sha256": digest})
    asset = obj({"schema_version": version, "kind": {"const": "e2e-bundle"}, "parent": parent, "intent": intent,
                 "parent_ref": binding, "intent_ref": binding, "books": array(snapshot, 1, MAX_BUNDLE_BOOKS),
                 "denominator": obj({"scope_ids": refs(1), "book_ids": refs(1), "gap_ids": refs(), "exclusion_ids": refs()}),
                 "claim": {"enum": ["bundle_preparation_ready", "bundle_incomplete"]},
                 "gaps": array({"type": "object"}), "qualification": {"const": BUNDLE_QUALIFICATION}})
    runs = obj({"schema_version": version, "bundle_file_sha256": digest,
                "runs": array(obj({"book_id": string, "bundle_file_sha256": digest,
                                   "book_binding_sha256": digest, "trace": binding, "execution_binding": binding}))})
    receipt = obj({"schema_version": version, "bundle_file_sha256": digest, "book_binding_sha256": digest,
                   "book_id": string, "run_id": string, "target": string})
    return {"claim": "schemas_only", **{name: {"$schema": "https://json-schema.org/draft/2020-12/schema", **value}
            for name, value in (("parent", parent), ("intent", intent), ("asset", asset), ("runs", runs), ("execution_binding", receipt))},
            "qualification": BUNDLE_QUALIFICATION}


CROSSWALK_QUALIFICATION = (
    "Declared many-to-many evidence accounting only; not discovery, semantic equivalence, "
    "authentic execution, visual acceptance or a new-run pass. Original scenario/coverage "
    "auditors and native adapters own outcomes. Stage 2/3/4 acceptance and input/output "
    "bindings remain with the existing runtime and independent review."
)


def native_modules():
    # Q1/S1 remain independently usable with only the scenario helper installed.
    import e2e_coverage
    import e2e_runner
    return e2e_coverage, e2e_runner


def lane_root(root: Path, name: str) -> Path:
    if name == ".":
        return root
    path = canonical_path(name)
    current = root
    for part in path.parts:
        current /= part
        need(not current.is_symlink() and not getattr(current, "is_junction", lambda: False)(), "linked native root")
    need(current.is_dir() and current.resolve().is_relative_to(root), "native root escapes project or is missing")
    return current.resolve()


def project_bindings(root: Path, native_root: Path, bindings: list) -> list:
    file_bindings(bindings, native_root, "native input", nonempty=True)
    return [{"path": safe_file(native_root, b["path"]).relative_to(root).as_posix(), "sha256": b["sha256"]} for b in bindings]


def crosswalk_prepare(intent_path: str, bundle_path: str, expected_bundle: str, root: Path) -> dict:
    root = root.resolve(strict=True)
    coverage, runner = native_modules()
    impact = bundle_impact(bundle_path, expected_bundle, root)
    need(not impact["affected_books"], "crosswalk requires current frozen books and inputs")
    bundle = load(root, bundle_path)
    snapshots = indexed(bundle["books"], "books", True)
    intent_bytes = read_bytes(root, intent_path)
    intent = decode(intent_bytes)
    shape(intent, "schema_version native_lanes mappings", "crosswalk intent")
    need(type(intent["schema_version"]) is int and intent["schema_version"] == 1, "unsupported crosswalk version")
    lanes = indexed(intent["native_lanes"], "native lanes", True)
    need(len(lanes) <= MAX_BUNDLE_BOOKS, "native lane budget exceeded")
    books, obligations, native, gaps = {}, {}, {}, list(impact["preparation_gaps"])
    native_selectors = set()
    for identity, snapshot in snapshots.items():
        book = load(root, snapshot["book"]["path"])
        design = scenarios.check(book, root)
        books[identity] = book
        for card in book["scenarios"]:
            obligations[(identity, "scenario", card["id"])] = [card["id"]]
        for kind, field in (("condition", "condition_obligations"), ("timing", "timing_obligations")):
            for row in design[field]:
                obligations[(identity, kind, row["id"])] = row["scenario_ids"]
        need(len(obligations) <= MAX_ROWS, "crosswalk obligation budget exceeded")
    for identity, lane in lanes.items():
        shape(lane, "id root manifest bindings runner target book_ids", "native lane")
        native_root = lane_root(root, lane["root"])
        file_bindings([lane["manifest"], lane["bindings"]], root, "native declarations", nonempty=True)
        need(lane["runner"] in {"pytest", "playwright"}, "unknown native runner")
        text(lane["target"], "native target")
        related = references(lane["book_ids"], snapshots, "native book_ids")
        need(all(snapshots[b]["target"]["id"] == lane["target"] for b in related), "native target differs from book target")
        model, binding = load(root, lane["manifest"]["path"]), load(root, lane["bindings"]["path"])
        plan = coverage.plan(model, native_root)
        runner.validate_bindings(binding, plan, native_root, lane["runner"])
        for case in binding["cases"]:
            selector = (lane["runner"], lane["target"], safe_file(native_root, case["test_ref"]), case["selector"], case.get("project", ""))
            need(selector not in native_selectors, "duplicate native selector credit across lanes")
            native_selectors.add(selector)
        inputs = project_bindings(root, native_root, model["sources"]) + project_bindings(root, native_root, binding["test_sources"])
        inputs = list({r["path"]: r for r in inputs}.values())
        for book_id in related:
            snapshot = snapshots[book_id]
            bound = {(safe_file(root, r["path"]), r["sha256"]) for r in
                     snapshot["sources"] + snapshot["fixtures"] + snapshot["target"]["bindings"]}
            need(all((safe_file(root, r["path"]), r["sha256"]) in bound for r in inputs),
                 "native source/test inputs must already be bound by every related S1 book")
        native[identity] = {**lane, "manifest_sha256": coverage.digest(model), "bindings_sha256": coverage.digest(binding),
                            "input_bindings": inputs, "plan": plan}
        need(sum(len(value["plan"]["cases"]) for value in native.values()) <= MAX_ROWS,
             "crosswalk total native case budget exceeded")
    mapped_obligations, mapped_cases, edges = set(), set(), set()
    mappings = indexed(intent["mappings"], "crosswalk mappings")
    for mapping in mappings.values():
        shape(mapping, "id rationale scenario_refs obligations native_cases requirement_links", "mapping")
        text(mapping["rationale"], "mapping rationale")
        selected, selected_requirements = set(), set()
        for ref in rows(mapping["scenario_refs"], "scenario refs", True):
            shape(ref, "book_id scenario_id step_ids oracle_ids", "scenario ref")
            key = (text(ref["book_id"], "book_id"), text(ref["scenario_id"], "scenario_id"))
            need(key[0] in books and key not in selected, "unknown/duplicate scenario book ref")
            cards = {c["id"]: c for c in books[key[0]]["scenarios"]}
            need(key[1] in cards, "unknown scenario ref")
            card = cards[key[1]]
            need(ref["step_ids"] == [s["id"] for s in card["steps"]], "mapping must retain complete ordered scenario steps")
            references(ref["oracle_ids"], [o["id"] for o in card["oracles"]], "mapping oracles")
            need(set(ref["oracle_ids"]) == {o["id"] for o in card["oracles"]}, "mapping must retain all scenario oracles")
            selected.add(key)
            selected_requirements.update((key[0], r) for r in card["requirements"])
        selected_obligations = set()
        for ref in rows(mapping["obligations"], "mapped obligations", True):
            shape(ref, "book_id kind id", "obligation ref")
            key = tuple(text(ref[k], k) for k in ("book_id", "kind", "id"))
            need(key in obligations and key not in selected_obligations, "unknown/duplicate obligation ref")
            need(any((key[0], s) in selected for s in obligations[key]), "obligation not exercised by selected scenarios")
            selected_obligations.add(key)
        need(all(any(key[0] == b and s in obligations[key] for key in selected_obligations) for b, s in selected),
             "scenario ref has no mapped obligation")
        selected_cases, native_requirements = set(), set()
        for ref in rows(mapping["native_cases"], "mapped native cases", True):
            shape(ref, "lane_id case_id journey parameters", "native case ref")
            key = (text(ref["lane_id"], "lane_id"), text(ref["case_id"], "case_id"))
            need(key[0] in native and key not in selected_cases, "unknown/duplicate native case ref")
            cases = {c["id"]: c for c in native[key[0]]["plan"]["cases"]}
            need(key[1] in cases, "unknown native case")
            case = cases[key[1]]
            need(ref["journey"] == case["journey"] and scenarios.sha(ref["parameters"]) == scenarios.sha(case["parameters"]),
                 "native case combination differs from frozen plan")
            need({b for b, _ in selected} <= set(native[key[0]]["book_ids"]), "mapping uses unrelated native lane/book")
            selected_cases.add(key)
            native_requirements.update((key[0], r) for r in case["requirements"])
        links = set()
        for link in rows(mapping["requirement_links"], "requirement links", True):
            shape(link, "book_id requirement_id lane_id native_requirement_id", "requirement link")
            key = tuple(text(link[k], k) for k in ("book_id", "requirement_id", "lane_id", "native_requirement_id"))
            need(key not in links and key[:2] in selected_requirements and key[2:] in native_requirements,
                 "unknown/duplicate requirement link")
            links.add(key)
        need({k[:2] for k in links} == selected_requirements and {k[2:] for k in links} == native_requirements,
             "requirement link denominator is incomplete")
        for obligation in selected_obligations:
            for case in selected_cases:
                relevant_requirements = {r for card in books[obligation[0]]["scenarios"]
                    if card["id"] in obligations[obligation] and (obligation[0], card["id"]) in selected
                    for r in card["requirements"]}
                case_requirements = next(c["requirements"] for c in native[case[0]]["plan"]["cases"] if c["id"] == case[1])
                need(any((obligation[0], req, case[0], native_req) in links
                         for req in relevant_requirements for native_req in case_requirements),
                     "crosswalk edge has no exact requirement link")
                edge = obligation + case
                need(edge not in edges, "duplicate crosswalk credit edge")
                edges.add(edge)
                need(len(edges) <= MAX_ROWS, "crosswalk edge budget exceeded")
        mapped_obligations.update(selected_obligations)
        mapped_cases.update(selected_cases)
    all_cases = {(lane, case["id"]) for lane, value in native.items() for case in value["plan"]["cases"]}
    for book, kind, identity in sorted(set(obligations) - mapped_obligations):
        gaps.append({"kind": "unmapped_obligation", "book_id": book, "obligation_kind": kind, "id": identity})
    for lane, case in sorted(all_cases - mapped_cases):
        gaps.append({"kind": "unmapped_native_case", "lane_id": lane, "case_id": case})
    need(read_bytes(root, intent_path) == intent_bytes, "crosswalk intent changed during preparation")
    need(digest_file(root, bundle_path) == expected_bundle, "bundle changed during crosswalk preparation")
    for lane in native.values():
        file_bindings([lane["manifest"], lane["bindings"]] + lane["input_bindings"], root, "final native input")
    need(scenarios.sha(bundle_impact(bundle_path, expected_bundle, root)) == scenarios.sha(impact), "bundle inputs changed during crosswalk preparation")
    return {"schema_version": 1, "kind": "e2e-crosswalk", "bundle_ref": {"path": bundle_path, "sha256": expected_bundle},
            "intent_ref": {"path": intent_path, "sha256": hashlib.sha256(intent_bytes).hexdigest()}, "intent": intent,
            "native_lanes": list(native.values()), "denominator": {"parent": bundle["denominator"],
                "obligations": [{"book_id": b, "kind": k, "id": i, "scenario_ids": obligations[(b, k, i)]} for b, k, i in sorted(obligations)],
                "native_cases": [{"lane_id": lane, "cases": value["plan"]["cases"]} for lane, value in native.items()],
                "edge_count": len(edges)}, "gaps": gaps, "claim": "crosswalk_incomplete" if gaps else "crosswalk_mapping_ready",
            "qualification": CROSSWALK_QUALIFICATION}


def crosswalk_audit(asset_path: str, expected_crosswalk: str, expected_bundle: str, scenario_runs: str,
                    native_runs: str, root: Path) -> dict:
    root = root.resolve(strict=True)
    coverage, runner = native_modules()
    raw = read_bytes(root, asset_path)
    need(hashlib.sha256(raw).hexdigest() == expected_crosswalk, "crosswalk differs from accepted file digest")
    asset = decode(raw)
    shape(asset, "schema_version kind bundle_ref intent_ref intent native_lanes denominator gaps claim qualification", "crosswalk asset")
    need(asset["bundle_ref"]["sha256"] == expected_bundle, "crosswalk bundle differs from accepted bundle digest")
    fresh = crosswalk_prepare(asset["intent_ref"]["path"], asset["bundle_ref"]["path"], expected_bundle, root)
    need(scenarios.sha(asset) == scenarios.sha(fresh), "crosswalk intent or frozen inputs changed")
    bundle_audit = bundle_impact(asset["bundle_ref"]["path"], expected_bundle, root, scenario_runs)
    # S1 delegates to the scenario auditor over EVERY book and original trace.
    report = {"schema_version": 1, "claim": "crosswalk_accounting_complete", "crosswalk_file_sha256": expected_crosswalk,
              "denominator": asset["denominator"], "mapping_gaps": asset["gaps"], "bundle_audit": bundle_audit,
              "native_audits": [], "execution_gaps": [], "qualification": CROSSWALK_QUALIFICATION}
    if asset["gaps"] or bundle_audit["claim"] != "bundle_preparation_reusable":
        report["claim"] = "crosswalk_incomplete"
    raw_index = read_bytes(root, native_runs)
    index = decode(raw_index)
    shape(index, "schema_version crosswalk_file_sha256 runs", "native runs")
    need(type(index["schema_version"]) is int and index["schema_version"] == 1, "unsupported native index")
    need(index["crosswalk_file_sha256"] == expected_crosswalk, "native index belongs to another crosswalk")
    lanes = indexed(asset["native_lanes"], "native lanes", True)
    indexed_runs = {identity: [] for identity in lanes}
    for row in rows(index["runs"], "native runs"):
        shape(row, "lane_id results native_report execution", "native run reference")
        identity = text(row["lane_id"], "lane_id")
        file_bindings([row["native_report"], row["execution"]] + ([] if row["results"] is None else [row["results"]]), root, "native run", verify=False)
        if identity not in lanes:
            report["execution_gaps"].append({"kind": "unknown_native_lane", "lane_id": identity})
        else:
            indexed_runs[identity].append(row)
    old_runs = {entry["book_id"]: entry for entry in bundle_audit["preserved_old_run_evidence"]}
    verified_files = []
    for identity, lane in lanes.items():
        entries = indexed_runs[identity]
        if len(entries) != 1:
            report["execution_gaps"].append({"kind": "missing_native_run" if not entries else "conflicting_native_runs", "lane_id": identity})
            continue
        row = entries[0]
        result = {"lane_id": identity, "references": row, "native_audit": None, "reconciliation": "unverified"}
        report["native_audits"].append(result)
        try:
            bindings = [row["native_report"], row["execution"]] + ([] if row["results"] is None else [row["results"]])
            file_bindings(bindings, root, "native run")
            verified_files.extend(bindings)
            native_root = lane_root(root, lane["root"])
            native_report, execution = load(root, row["native_report"]["path"]), load(root, row["execution"]["path"])
            result["execution_record"] = execution  # Preserve owner error/receipt including empty-run failures.
            need(row["results"] is not None, "native owner has no results; raw report/error retained, no fabricated audit")
            values = load(root, row["results"]["path"])
            model, binding = load(root, lane["manifest"]["path"]), load(root, lane["bindings"]["path"])
            file_bindings(values["test_sources"], native_root, "native test sources", nonempty=True)
            file_bindings(values["evidence"], native_root, "native evidence", nonempty=True)
            result["native_audit"] = coverage.audit(model, values, native_root)
            need(scenarios.sha(values["test_sources"]) == scenarios.sha(binding["test_sources"]), "native test source binding changed")
            need(values["target"] == lane["target"] and execution["target"] == lane["target"], "native target mismatch")
            for key in ("run_id", "command", "started_at", "finished_at", "exit_code", "manifest_sha256"):
                need(scenarios.sha(values[key]) == scenarios.sha(execution[key]), "native execution/result mismatch: " + key)
            need(execution["runner"] == lane["runner"] and execution["bindings_sha256"] == lane["bindings_sha256"], "native execution bindings mismatch")
            need(type(execution.get("schema_version")) is int and execution["schema_version"] == 1,
                 "unsupported native execution receipt")
            expected_native = {"path": safe_file(root, row["native_report"]["path"]).relative_to(native_root).as_posix(),
                               "sha256": row["native_report"]["sha256"]}
            need(execution["native_report"] == expected_native, "native execution report reference differs")
            for native_ref in (row["native_report"], row["execution"]):
                local = {"path": safe_file(root, native_ref["path"]).relative_to(native_root).as_posix(), "sha256": native_ref["sha256"]}
                need(local in values["evidence"], "original native result lacks report/execution evidence")
            validated = runner.validate_bindings(binding, lane["plan"], native_root, lane["runner"])
            if lane["runner"] == "playwright":
                # The native owner's execute() checks this binding before its
                # pure outcome adapter. Recheck the same bounds when auditing
                # retained reports; declared times still do not attest reality.
                stats = native_report.get("stats")
                need(isinstance(stats, dict), "missing Playwright run timestamps")
                native_started = datetime.fromisoformat(text(stats.get("startTime"), "Playwright startTime").replace("Z", "+00:00"))
                need(native_started.tzinfo is not None, "Playwright timestamp needs timezone")
                started = datetime.fromisoformat(values["started_at"].replace("Z", "+00:00"))
                finished = datetime.fromisoformat(values["finished_at"].replace("Z", "+00:00"))
                elapsed, wall = (native_started - started).total_seconds(), (finished - started).total_seconds()
                duration = stats.get("duration")
                need(-2 <= elapsed <= wall + 2, "Playwright report is stale or from a future run")
                need(type(duration) in (int, float) and math.isfinite(duration) and 0 <= duration <= (wall + 4) * 1000,
                     "invalid Playwright run duration")
            outcomes = (runner.pytest_outcomes(native_report, validated, values["run_id"], values["exit_code"])
                        if lane["runner"] == "pytest" else runner.playwright_outcomes(native_report, validated, native_root))
            actual = {c["id"]: c["status"] for c in values["cases"]}
            need(outcomes == actual, "native raw outcomes conflict with normalized results (including retries/skip/missing)")
            result["reconciliation"] = "original_native_adapter_matched"
            # A late index or mapping must not retarget an old trace. Both its
            # S1 receipt and this crosswalk receipt are original trace evidence.
            for book_id in lane["book_ids"]:
                need(book_id in old_runs, "related scenario run was not independently auditable under S1 bindings")
                trace = load(root, old_runs[book_id]["trace"]["path"])
                references_by_id = {e["id"]: e for e in trace["evidence"]}
                need("crosswalk-execution-binding" in references_by_id, "original scenario trace has no crosswalk execution binding")
                receipt_ref = references_by_id["crosswalk-execution-binding"]
                need(receipt_ref["kind"] == "log", "crosswalk execution binding must be log evidence")
                receipt = load(root, receipt_ref["path"])
                expected = {"schema_version": 1, "crosswalk_file_sha256": expected_crosswalk, "book_id": book_id,
                            "run_id": trace["run_id"], "target": trace["target"]}
                need(scenarios.sha(receipt) == scenarios.sha(expected), "original trace crosswalk binding mismatch")
                candidates = []
                for evidence in trace["evidence"]:
                    if evidence["kind"] == "log":
                        try:
                            value = decode(read_bytes(root, evidence["path"]))
                        except (AssetError, ValueError, UnicodeError):
                            continue
                        if "crosswalk_file_sha256" in value:
                            candidates.append(evidence["id"])
                need(candidates == ["crosswalk-execution-binding"], "duplicate/conflicting crosswalk execution bindings")
                for native_ref in bindings:
                    need(any(e["path"] == native_ref["path"] and e["sha256"] == native_ref["sha256"] for e in trace["evidence"]),
                         "original scenario trace lacks selected native evidence")
            if result["native_audit"]["claim"] != "complete_against_frozen_scope":
                report["execution_gaps"].append({"kind": "native_audit_incomplete", "lane_id": identity})
        except (AssetError, ValueError, OSError, TypeError, KeyError, RecursionError) as exc:
            report["execution_gaps"].append({"kind": "unverified_native_lane", "lane_id": identity, "detail": str(exc)})
    if report["execution_gaps"]:
        report["claim"] = "crosswalk_incomplete"
    file_bindings(verified_files, root, "final native run")
    need(read_bytes(root, native_runs) == raw_index and read_bytes(root, asset_path) == raw, "crosswalk/run index changed during audit")
    need(scenarios.sha(crosswalk_prepare(asset["intent_ref"]["path"], asset["bundle_ref"]["path"], expected_bundle, root)) == scenarios.sha(asset),
         "crosswalk inputs changed during audit")
    # Preserve and re-audit all original trace/evidence bytes after native reads.
    need(scenarios.sha(bundle_impact(asset["bundle_ref"]["path"], expected_bundle, root, scenario_runs)) == scenarios.sha(bundle_audit),
         "scenario evidence changed during crosswalk audit")
    return report


def crosswalk_schemas() -> dict:
    string = {"type": "string", "minLength": 1, "maxLength": MAX_TEXT}
    digest = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
    version = {"type": "integer", "const": 1}

    def array(item, minimum=0):
        return {"type": "array", "items": item, "minItems": minimum, "maxItems": MAX_ROWS}

    def obj(properties):
        return {"type": "object", "additionalProperties": False, "properties": properties, "required": list(properties)}

    def refs(minimum=0):
        return {**array(string, minimum), "uniqueItems": True}

    binding = obj({"path": string, "sha256": digest})
    lane = {"id": string, "root": string, "manifest": binding, "bindings": binding,
            "runner": {"enum": ["pytest", "playwright"]}, "target": string, "book_ids": refs(1)}
    obligation = {"book_id": string, "kind": {"enum": ["scenario", "condition", "timing"]}, "id": string}
    parameters = {"type": "object", "additionalProperties": string, "minProperties": 1, "maxProperties": MAX_ROWS}
    case = obj({"id": string, "journey": string, "parameters": parameters, "requirements": refs(1)})
    mapping = obj({"id": string, "rationale": string,
        "scenario_refs": array(obj({"book_id": string, "scenario_id": string, "step_ids": refs(1), "oracle_ids": refs(1)}), 1),
        "obligations": array(obj(obligation), 1),
        "native_cases": array(obj({"lane_id": string, "case_id": string, "journey": string, "parameters": parameters}), 1),
        "requirement_links": array(obj({"book_id": string, "requirement_id": string, "lane_id": string, "native_requirement_id": string}), 1)})
    intent = obj({"schema_version": version, "native_lanes": array(obj(lane), 1), "mappings": array(mapping)})
    snapshot = obj({**lane, "manifest_sha256": digest, "bindings_sha256": digest,
                    "input_bindings": array(binding, 1), "plan": {"type": "object"}})
    asset = obj({"schema_version": version, "kind": {"const": "e2e-crosswalk"}, "bundle_ref": binding,
        "intent_ref": binding, "intent": intent, "native_lanes": array(snapshot, 1),
        "denominator": obj({"parent": bundle_schemas()["asset"]["properties"]["denominator"],
            "obligations": array(obj({**obligation, "scenario_ids": refs()}), 1),
            "native_cases": array(obj({"lane_id": string, "cases": array(case, 1)}), 1), "edge_count": {"type": "integer", "minimum": 0, "maximum": MAX_ROWS}}),
        "gaps": array({"type": "object"}), "claim": {"enum": ["crosswalk_mapping_ready", "crosswalk_incomplete"]},
        "qualification": {"const": CROSSWALK_QUALIFICATION}})
    native_runs = obj({"schema_version": version, "crosswalk_file_sha256": digest,
        "runs": array(obj({"lane_id": string, "results": {"anyOf": [binding, {"type": "null"}]},
                           "native_report": binding, "execution": binding}))})
    receipt = obj({"schema_version": version, "crosswalk_file_sha256": digest, "book_id": string, "run_id": string, "target": string})
    return {"claim": "schemas_only", **{name: {"$schema": "https://json-schema.org/draft/2020-12/schema", **value}
            for name, value in (("intent", intent), ("asset", asset), ("native_runs", native_runs), ("execution_binding", receipt))},
            "qualification": CROSSWALK_QUALIFICATION}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    schema = commands.add_parser("schema", help="Print schemas, never authored risk content")
    schema.add_argument("asset", choices=("strength", "bundle", "crosswalk"))
    prepare = commands.add_parser("strength-prepare", help="Print a frozen ordinary asset from supplied risk intent")
    prepare.add_argument("intent")
    prepare.add_argument("--book", required=True)
    prepare.add_argument("--root", type=Path, default=Path.cwd())
    audit = commands.add_parser("strength-audit", help="Recheck frozen intent/book and optional actual trace")
    audit.add_argument("asset")
    audit.add_argument("--root", type=Path, default=Path.cwd())
    audit.add_argument("--trace")
    freeze = commands.add_parser("bundle-prepare", help="Print a complete pre-execution parent/book bundle")
    freeze.add_argument("intent")
    freeze.add_argument("--parent", required=True)
    freeze.add_argument("--root", type=Path, default=Path.cwd())
    impact = commands.add_parser("bundle-impact", help="Check frozen inputs and optional historical run evidence")
    impact.add_argument("asset")
    impact.add_argument("--expected-bundle-sha256", required=True, help="Raw bundle file digest accepted externally in Stage 2")
    impact.add_argument("--runs", help="Complete run reference index; old runs keep their original identities")
    impact.add_argument("--root", type=Path, default=Path.cwd())
    cross_prepare = commands.add_parser("crosswalk-prepare", help="Freeze declared many-to-many scenario/native mappings")
    cross_prepare.add_argument("intent")
    cross_prepare.add_argument("--bundle", required=True)
    cross_prepare.add_argument("--expected-bundle-sha256", required=True)
    cross_prepare.add_argument("--root", type=Path, default=Path.cwd())
    cross_audit = commands.add_parser("crosswalk-audit", help="Delegate full evidence checks to original auditors/adapters")
    cross_audit.add_argument("asset")
    cross_audit.add_argument("--expected-crosswalk-sha256", required=True)
    cross_audit.add_argument("--expected-bundle-sha256", required=True)
    cross_audit.add_argument("--scenario-runs", required=True)
    cross_audit.add_argument("--native-runs", required=True)
    cross_audit.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    try:
        if args.command == "schema":
            report = {"strength": strength_schemas, "bundle": bundle_schemas, "crosswalk": crosswalk_schemas}[args.asset]()
        elif args.command == "strength-prepare":
            report = strength_prepare(args.intent, args.book, args.root)
        elif args.command == "strength-audit":
            report = strength_audit(args.asset, args.root, args.trace)
        elif args.command == "bundle-prepare":
            report = bundle_prepare(args.intent, args.parent, args.root)
        elif args.command == "bundle-impact":
            report = bundle_impact(args.asset, args.expected_bundle_sha256, args.root, args.runs)
        elif args.command == "crosswalk-prepare":
            report = crosswalk_prepare(args.intent, args.bundle, args.expected_bundle_sha256, args.root)
        else:
            report = crosswalk_audit(args.asset, args.expected_crosswalk_sha256, args.expected_bundle_sha256,
                                     args.scenario_runs, args.native_runs, args.root)
        # ASCII JSON remains lossless on Windows pipes whose encoding differs
        # from UTF-8 (including isolated -E interpreters); consumers decode JSON.
        print(json.dumps(report, ensure_ascii=True, indent=2, allow_nan=False))
        return 1 if report["claim"] in {"strength_incomplete", "bundle_incomplete", "bundle_impact_detected", "crosswalk_incomplete"} else 0
    except (AssetError, scenarios.ScenarioError, OSError, ValueError, TypeError, KeyError, RecursionError) as exc:
        print(json.dumps({"claim": "invalid", "error": str(exc)}, ensure_ascii=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
