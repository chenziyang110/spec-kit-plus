#!/usr/bin/env python3
"""Plan constrained E2E combinations and audit real-run coverage (stdlib only).

This is a stateless test-asset helper, not a workflow-state writer or test runner.
It never executes commands from input. JSON reports go to stdout; exit codes:
0 = plan generated / complete audited run, 1 = incomplete run, 2 = invalid input.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import heapq
import itertools
import json
import math
from pathlib import Path
import sys
from typing import Any, Iterator

SCHEMA_VERSION = 1
MAX_CANDIDATES = 10000
MAX_INTERACTIONS = 100000
MAX_TOTAL_CANDIDATES = 50000
STATUSES = {"passed", "failed", "skipped", "blocked", "not_run", "flaky"}


class CoverageError(ValueError):
    """An input cannot support a defensible coverage claim."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CoverageError(message)


def known_fields(value: dict, allowed: str, label: str) -> None:
    unknown = set(value) - set(allowed.split())
    require(not unknown, f"{label}: unknown fields {sorted(unknown)}")


def text(value: Any, label: str) -> str:
    require(isinstance(value, str) and bool(value.strip()), f"{label}: non-empty string required")
    return value


def array(value: Any, label: str, *, nonempty: bool = True) -> list:
    require(isinstance(value, list), f"{label}: array required")
    require(not nonempty or bool(value), f"{label}: empty array")
    return value


def unique_strings(value: Any, label: str) -> list[str]:
    values = array(value, label)
    for item in values:
        text(item, label)
    require(len(set(values)) == len(values), f"{label}: duplicate value")
    return values


def digest(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def records(value: Any, label: str) -> dict[str, dict]:
    result: dict[str, dict] = {}
    for item in array(value, label):
        require(isinstance(item, dict), f"{label}: object required")
        identity = text(item.get("id"), f"{label}.id")
        require(identity not in result, f"{label}: duplicate id {identity}")
        result[identity] = item
    return result


def safe_file(root: Path, value: Any) -> Path:
    name = text(value, "file path")
    path = Path(name)
    require(not path.is_absolute() and ".." not in path.parts, f"unsafe path: {name}")
    resolved = (root / path).resolve()
    require(resolved.is_relative_to(root.resolve()), f"path escapes root: {name}")
    require(resolved.is_file(), f"missing file: {name}")
    return resolved


def _file_entries(value: Any, label: str) -> Iterator[tuple[str, str]]:
    """Validate every declaration, even when its bytes were checked earlier."""
    paths: set[str] = set()
    for entry in array(value, label):
        require(isinstance(entry, dict), f"{label}: object required")
        known_fields(entry, "path sha256", label)
        name = text(entry.get("path"), f"{label}.path")
        require(name not in paths, f"{label}: duplicate path {name}")
        expected = text(entry.get("sha256"), f"{label}.sha256")
        require(len(expected) == 64 and all(c in "0123456789abcdef" for c in expected),
                f"{label}: invalid sha256 for {name}")
        paths.add(name)
        yield name, expected


def _file_sha256(path: Path) -> str:
    # Python 3.11+; bounded-memory hashing even for large native logs/reports.
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def verify_files(root: Path, value: Any, label: str) -> set[str]:
    paths: set[str] = set()
    for name, expected in _file_entries(value, label):
        actual = _file_sha256(safe_file(root, name))
        require(actual == expected, f"stale or changed {label}: {name}")
        paths.add(name)
    return paths


class _AuditEvidence:
    """Deduplicate evidence I/O only inside one audit, then recheck all bytes.

    Repeated declarations still undergo schema, digest and path validation.
    This is not a persistent cache, a filesystem lock, or runner attestation.
    Evidence must stay immutable; closeout never trusts the earlier digest alone.
    """

    def __init__(self, root: Path):
        self.root = root
        self.checked: dict[str, str] = {}

    def verify(self, value: Any, label: str) -> None:
        for name, expected in _file_entries(value, label):
            path = safe_file(self.root, name)
            actual = self.checked.get(name)
            if actual is None:
                actual = _file_sha256(path)
                self.checked[name] = actual
            require(actual == expected, f"stale or changed {label}: {name}")

    def recheck(self) -> None:
        verify_files(self.root, [{"path": name, "sha256": sha}
                                 for name, sha in self.checked.items()], "post-audit evidence")


def pattern(value: Any, factors: dict[str, list[str]], label: str) -> dict[str, str]:
    require(isinstance(value, dict) and bool(value), f"{label}: non-empty object required")
    for key, chosen in value.items():
        require(key in factors and isinstance(chosen, str) and chosen in factors[key],
                f"{label}: unknown factor/value {key}={chosen!r}")
    return value


def matches(row: dict[str, str], partial: dict[str, str]) -> bool:
    return all(row[key] == value for key, value in partial.items())


def interactions(row: dict[str, str], strength: int) -> frozenset[tuple]:
    return frozenset(itertools.combinations(sorted(row.items()), strength))


def prepare(model: dict, root: Path | None = None) -> dict:
    """Validate a frozen inventory and derive feasible, not theoretical, tuples."""
    require(isinstance(model, dict), "manifest: object required")
    known_fields(model, "schema_version scope source_revision sources exclusions requirements journeys", "manifest")
    require(type(model.get("schema_version")) is int and model["schema_version"] == SCHEMA_VERSION,
            "manifest: unsupported schema_version")
    text(model.get("scope"), "scope")
    text(model.get("source_revision"), "source_revision")
    array(model.get("sources"), "sources")
    for excluded in array(model.get("exclusions", []), "exclusions", nonempty=False):
        require(isinstance(excluded, dict), "exclusions: object required")
        known_fields(excluded, "scope reason owner", "exclusion")
        text(excluded.get("scope"), "exclusion.scope")
        text(excluded.get("reason"), "exclusion.reason")
    if root is not None:
        verify_files(root, model["sources"], "sources")
    requirements = records(model.get("requirements"), "requirements")
    for requirement in requirements.values():
        known_fields(requirement, "id source assertion", "requirement")
        text(requirement.get("source"), "requirement.source")
        text(requirement.get("assertion"), "requirement.assertion")
    journeys = records(model.get("journeys"), "journeys")
    mapped: set[str] = set()
    prepared: dict[str, dict] = {}
    total_candidates = 0
    for identity, journey in sorted(journeys.items()):
        known_fields(journey, "id requirements steps factors strength exclude mandatory", identity)
        refs = unique_strings(journey.get("requirements"), f"{identity}.requirements")
        require(set(refs) <= requirements.keys(), f"{identity}: unknown requirement")
        mapped.update(refs)
        for step in array(journey.get("steps"), f"{identity}.steps"):
            text(step, f"{identity}.step")
        factors = journey.get("factors")
        require(isinstance(factors, dict) and bool(factors), f"{identity}: non-empty factors required")
        for key, values in factors.items():
            text(key, f"{identity}.factor")
            unique_strings(values, f"{identity}.{key}")
        strength = journey.get("strength", min(2, len(factors)))
        if strength == "exhaustive":
            strength = len(factors)
        require(type(strength) is int and 1 <= strength <= len(factors),
                f"{identity}: strength must be 1..factor count or exhaustive")
        count = math.prod(len(values) for values in factors.values())
        require(count <= MAX_CANDIDATES,
                f"{identity}: {count} candidates exceed {MAX_CANDIDATES}; split scope, never silently sample")
        total_candidates += count
        require(total_candidates <= MAX_TOTAL_CANDIDATES, "total candidate budget exceeded; split the manifest")
        require(count * math.comb(len(factors), strength) <= MAX_INTERACTIONS,
                f"{identity}: interaction budget exceeded; split scope")
        forbidden = []
        for constraint in array(journey.get("exclude", []), f"{identity}.exclude", nonempty=False):
            require(isinstance(constraint, dict), f"{identity}.exclude: object required")
            known_fields(constraint, "when reason", f"{identity}.exclude")
            text(constraint.get("reason"), f"{identity}.exclude.reason")
            forbidden.append(pattern(constraint.get("when"), factors, f"{identity}.exclude.when"))
        keys = sorted(factors)
        candidates = [dict(zip(keys, values)) for values in itertools.product(*(sorted(factors[k]) for k in keys))]
        candidates = [row for row in candidates if not any(matches(row, banned) for banned in forbidden)]
        require(bool(candidates), f"{identity}: constraints eliminate every combination")
        for key, values in factors.items():
            require({row[key] for row in candidates} == set(values),
                    f"{identity}: constraints make a declared {key} value unreachable")
        mandatory = [pattern(item, factors, f"{identity}.mandatory") for item in
                     array(journey.get("mandatory", []), f"{identity}.mandatory", nonempty=False)]
        for item in mandatory:
            require(any(matches(row, item) for row in candidates), f"{identity}: infeasible mandatory combination {item}")
        tuples = [interactions(row, strength) for row in candidates]
        universe = set().union(*tuples)
        prepared[identity] = dict(requirements=sorted(refs), candidates=candidates, tuples=tuples,
                                  universe=universe, mandatory=mandatory, strength=strength)
    require(mapped == requirements.keys(), f"unmapped requirements: {sorted(requirements.keys() - mapped)}")
    return prepared


def _greedy_indices(data: dict, identity: str, budget: int, max_cases: int) -> list[int]:
    """Keep the historical score/tie order using monotone, indexed scores.

    Heap entries are upper bounds until refreshed. Scores only decrease, so a
    current top entry is exactly the next row the full-rescan algorithm chose.
    Candidate index breaks ties; neither set nor hash iteration order can do so.
    """
    candidates = data["candidates"]
    budget_error = f"case budget {max_cases} exceeded; raise the budget or explicitly revise scope/strength"
    if data["strength"] == len(candidates[0]):
        require(len(candidates) <= budget, budget_error)
        return list(range(len(candidates)))

    interaction_owners: dict[tuple, list[int]] = {}
    for index, tuples in enumerate(data["tuples"]):
        for item in tuples:
            interaction_owners.setdefault(item, []).append(index)
    # Factor postings avoid storing a potentially dense candidate x mandatory
    # matrix. Recompute a pattern's intersection only when its score is removed.
    factor_owners: dict[tuple[str, str], set[int]] = {}
    if data["mandatory"]:
        for index, row in enumerate(candidates):
            for item in row.items():
                factor_owners.setdefault(item, set()).add(index)

    def matching_indices(partial: dict) -> set[int]:
        groups = sorted((factor_owners[item] for item in partial.items()), key=len)
        indices = groups[0].copy()
        for group in groups[1:]:
            indices.intersection_update(group)
        return indices

    mandatory = list(data["mandatory"])
    mandatory_scores = [0] * len(candidates)
    for partial in mandatory:
        for index in matching_indices(partial):
            mandatory_scores[index] += 1
    interaction_scores = [len(items) for items in data["tuples"]]
    queue = [(-mandatory_scores[i], -interaction_scores[i], i) for i in range(len(candidates))]
    heapq.heapify(queue)
    uncovered = set(data["universe"])
    chosen: list[int] = []
    while uncovered or mandatory:
        require(bool(queue), f"{identity}: cannot cover remaining obligations")
        previous = heapq.heappop(queue)
        best = previous[2]
        current = (-mandatory_scores[best], -interaction_scores[best], best)
        if current != previous:
            heapq.heappush(queue, current)
            continue
        require(current[:2] != (0, 0), f"{identity}: cannot cover remaining obligations")
        chosen.append(best)
        require(len(chosen) <= budget, budget_error)
        for item in data["tuples"][best] & uncovered:
            for index in interaction_owners[item]:
                interaction_scores[index] -= 1
        uncovered.difference_update(data["tuples"][best])
        remaining = []
        for partial in mandatory:
            if matches(candidates[best], partial):
                for index in matching_indices(partial):
                    mandatory_scores[index] -= 1
            else:
                remaining.append(partial)
        mandatory = remaining
    return chosen


def _plan_prepared(model: dict, prepared: dict, max_cases: int) -> dict:
    """Use only this invocation's validated model, never a cross-run cache."""
    cases = []
    summary = []
    for identity, data in prepared.items():
        chosen = _greedy_indices(data, identity, max_cases - len(cases), max_cases)
        for index in chosen:
            row = data["candidates"][index]
            case_id = "E2E-" + digest({"journey": identity, "parameters": row})[:24]
            cases.append(dict(id=case_id, journey=identity, parameters=row, requirements=data["requirements"]))
        summary.append(dict(journey=identity, strength=data["strength"], feasible_combinations=len(data["candidates"]),
                            required_interactions=len(data["universe"]), planned_cases=len(chosen),
                            mandatory_combinations=len(data["mandatory"])))
    return dict(schema_version=SCHEMA_VERSION, manifest_sha256=digest(model),
                claim="planned_only", cases=cases, journeys=summary,
                exclusions=model.get("exclusions", []))


def plan(model: dict, root: Path | None = None, max_cases: int = 1000) -> dict:
    """Deterministic greedy covering array; not guaranteed to minimize test count."""
    require(type(max_cases) is int and max_cases > 0, "max_cases must be positive")
    return _plan_prepared(model, prepare(model, root), max_cases)


def audit(model: dict, results: dict, root: Path, max_cases: int = 1000) -> dict:
    """Require every generated case, fresh source/test bytes, and hashed run evidence."""
    require(type(max_cases) is int and max_cases > 0, "max_cases must be positive")
    prepared = prepare(model, root)
    planned = _plan_prepared(model, prepared, max_cases)
    require(isinstance(results, dict), "results: object required")
    known_fields(results, "schema_version manifest_sha256 source_revision run_id target started_at finished_at command exit_code test_sources evidence cases", "results")
    require(type(results.get("schema_version")) is int and results["schema_version"] == SCHEMA_VERSION,
            "results: unsupported schema_version")
    require(results.get("manifest_sha256") == planned["manifest_sha256"], "stale results: manifest digest mismatch")
    require(results.get("source_revision") == model["source_revision"], "stale results: source revision mismatch")
    for key in ("run_id", "target", "started_at", "finished_at"):
        text(results.get(key), f"results.{key}")
    try:
        started = datetime.fromisoformat(results["started_at"].replace("Z", "+00:00"))
        finished = datetime.fromisoformat(results["finished_at"].replace("Z", "+00:00"))
    except ValueError as exc:
        raise CoverageError("results: invalid ISO-8601 timestamps") from exc
    require(started.tzinfo is not None and finished.tzinfo is not None, "results: timestamps need timezones")
    require(finished >= started, "results: finished_at precedes started_at")
    for arg in array(results.get("command"), "results.command"):
        text(arg, "results.command argument")
    require(type(results.get("exit_code")) is int, "results.exit_code: integer required")
    test_sources = verify_files(root, results.get("test_sources"), "test_sources")
    evidence = _AuditEvidence(root)
    evidence.verify(results.get("evidence"), "run evidence")
    actual: dict[str, dict] = {}
    expected = {case["id"]: case for case in planned["cases"]}
    for result in array(results.get("cases"), "results.cases", nonempty=False):
        require(isinstance(result, dict), "results.cases: object required")
        known_fields(result, "id status test_ref asserted_requirements evidence", "result")
        identity = text(result.get("id"), "result.id")
        require(identity in expected, f"unexpected case id: {identity}")
        require(identity not in actual, f"duplicate result: {identity}; preserve retries as flaky in one final record")
        status = result.get("status")
        require(isinstance(status, str) and status in STATUSES, f"{identity}: invalid status")
        actual[identity] = result
        if status == "passed":
            assertions = unique_strings(result.get("asserted_requirements"), f"{identity}.asserted_requirements")
            require(set(assertions) == set(expected[identity]["requirements"]),
                    f"{identity}: missing or unrelated requirement assertions")
            require(result.get("test_ref") in test_sources, f"{identity}: test_ref not bound to test_sources")
            evidence.verify(result.get("evidence"), f"{identity} evidence")
    counts = {status: 0 for status in sorted(STATUSES)}
    passed = []
    gaps = []
    for identity, case in expected.items():
        status = actual.get(identity, {}).get("status", "not_run")
        counts[status] += 1
        if status == "passed":
            passed.append(case)
        else:
            gaps.append(dict(id=identity, journey=case["journey"], status=status))
    covered_requirements = {ref for case in passed for ref in case["requirements"]}
    all_requirements = {item["id"] for item in model["requirements"]}
    journey_reports = []
    for identity, data in prepared.items():
        rows = [case["parameters"] for case in passed if case["journey"] == identity]
        covered = set().union(*(interactions(row, data["strength"]) for row in rows))
        missing = sorted(data["universe"] - covered)
        missing_mandatory = [item for item in data["mandatory"] if not any(matches(row, item) for row in rows)]
        journey_reports.append(dict(journey=identity, strength=data["strength"],
                                    required_interactions=len(data["universe"]),
                                    passed_interactions=len(covered),
                                    missing_interactions=[dict(item) for item in missing],
                                    missing_mandatory=missing_mandatory))
    # A late change must invalidate even an incomplete report, not become its
    # accepted input basis. Re-read bytes; size/mtime or a cached digest is not proof.
    verify_files(root, model["sources"], "post-audit sources")
    verify_files(root, results["test_sources"], "post-audit tests")
    evidence.recheck()
    complete = not gaps and results["exit_code"] == 0
    return dict(schema_version=SCHEMA_VERSION,
                claim="complete_against_frozen_scope" if complete else "incomplete",
                manifest_sha256=planned["manifest_sha256"], run_id=results["run_id"],
                source_revision=results["source_revision"], target=results["target"],
                planned_cases=len(expected), statuses=counts, gaps=gaps,
                requirements=dict(total=len(all_requirements), passed=len(covered_requirements),
                                  missing=sorted(all_requirements - covered_requirements)),
                journeys=journey_reports, runner_exit_code=results["exit_code"],
                exclusions=model.get("exclusions", []),
                qualification="Bounded model and evidence consistency only; not proof of discovery completeness, truthful runner output, visual acceptance, or release safety.")


def load(path: Path) -> dict:
    def reject_duplicates(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f"duplicate JSON key: {key}")
            result[key] = value
        return result
    with path.open(encoding="utf-8") as handle:
        return json.load(handle, object_pairs_hook=reject_duplicates,
                         parse_constant=lambda value: require(False, f"invalid JSON constant: {value}"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("plan", "audit"))
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--results", type=Path)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--max-cases", type=int, default=1000)
    args = parser.parse_args(argv)
    try:
        require(args.mode != "audit" or args.results is not None, "audit requires --results")
        require(args.mode != "plan" or args.results is None, "plan does not accept --results")
        model = load(args.manifest)
        report = (plan(model, args.root, args.max_cases) if args.mode == "plan" else
                  audit(model, load(args.results), args.root, args.max_cases))
        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False))
        return 1 if report["claim"] == "incomplete" else 0
    except (CoverageError, OSError, ValueError, TypeError) as exc:
        print(json.dumps({"claim": "invalid", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
