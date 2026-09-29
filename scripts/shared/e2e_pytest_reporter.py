"""Opt-in pytest reporter for e2e_runner.py; not loaded by ordinary pytest runs."""
from __future__ import annotations

import json
import os
from pathlib import Path

_EVENTS: list[dict] = []
_COLLECTION: list[str] = []
_ERRORS: list[str] = []


def pytest_sessionstart(session):
    _EVENTS.clear()
    _COLLECTION.clear()
    _ERRORS.clear()


def pytest_collection_finish(session):
    _COLLECTION.extend(item.nodeid for item in session.items)


def pytest_collectreport(report):
    if report.failed:
        _ERRORS.append(report.nodeid)


def pytest_internalerror(excrepr, excinfo):
    _ERRORS.append("pytest internal error; see runner.log")


def pytest_runtest_logreport(report):
    # Keep every phase and every retry. A final passing call cannot erase a
    # failed setup, teardown, xfail/xpass, or earlier attempt.
    _EVENTS.append({
        "nodeid": report.nodeid,
        "file": report.location[0],
        "phase": report.when,
        "outcome": report.outcome,
        "wasxfail": hasattr(report, "wasxfail"),
    })


def pytest_sessionfinish(session, exitstatus):
    output = os.environ.get("SPECIFY_E2E_REPORT")
    run_id = os.environ.get("SPECIFY_E2E_RUN_ID")
    if not output or not run_id:
        raise RuntimeError("E2E reporter must be launched by e2e_runner.py")
    report = {
        "schema_version": 1,
        "runner": "pytest",
        "run_id": run_id,
        "exit_code": int(exitstatus),
        "collected": _COLLECTION,
        "events": _EVENTS,
        "errors": _ERRORS,
    }
    # Exclusive creation prevents a prior report from becoming this run's proof.
    with Path(output).open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, allow_nan=False)
        handle.write("\n")
