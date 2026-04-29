from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from specify_cli.evals import EvalCase, load_eval_cases, now_iso, sync_eval_index, write_eval_case
from specify_cli.verification import default_verification_runner


def _resolve_target(project_root: Path, target: str) -> Path:
    return (project_root / target).resolve()


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def run_eval_case(project_root: Path, case: EvalCase) -> EvalCase:
    updated = EvalCase.from_payload(case.to_payload())

    if case.verification_method == "file-check":
        target = _resolve_target(project_root, case.target)
        exists = target.exists()
        updated.last_result = "pass" if ((case.expect == "exists" and exists) or (case.expect == "missing" and not exists)) else "fail"
    elif case.verification_method == "rule-check":
        target = _resolve_target(project_root, case.target)
        if not target.exists():
            updated.last_result = "skip"
        else:
            content = _read_text(target)
            present = case.contains in content
            updated.last_result = "pass" if ((case.expect == "found" and present) or (case.expect == "not_found" and not present)) else "fail"
    elif case.verification_method == "grep-check":
        matches = []
        for matched_path in project_root.glob(case.target):
            if matched_path.is_file():
                matches.append(bool(re.search(case.pattern, _read_text(matched_path), flags=re.MULTILINE)))
        if not matches:
            updated.last_result = "skip"
        else:
            found = any(matches)
            updated.last_result = "pass" if ((case.expect == "found" and found) or (case.expect == "not_found" and not found)) else "fail"
    elif case.verification_method == "command-check":
        exit_code, _output = default_verification_runner(case.command)
        passed = exit_code == 0
        updated.last_result = "pass" if ((case.expect == "pass" and passed) or (case.expect == "fail" and not passed)) else "fail"
    else:
        raise ValueError(f"unsupported verification_method '{case.verification_method}'")

    updated.last_run = now_iso()
    return updated


def run_eval_suite(project_root: Path, *, recurrence_key: str | None = None) -> dict[str, Any]:
    cases = load_eval_cases(project_root)
    selected = [case for case in cases if recurrence_key is None or case.recurrence_key == recurrence_key]
    updated_cases: list[EvalCase] = []
    for case in selected:
        updated = run_eval_case(project_root, case)
        write_eval_case(project_root, updated)
        updated_cases.append(updated)
    sync_eval_index(project_root)
    return {
        "counts": {
            "total": len(updated_cases),
            "passed": sum(1 for case in updated_cases if case.last_result == "pass"),
            "failed": sum(1 for case in updated_cases if case.last_result == "fail"),
            "skipped": sum(1 for case in updated_cases if case.last_result == "skip"),
        },
        "cases": [case.to_payload() for case in updated_cases],
    }
