"""Prepare repeatable Quick fixtures and run frozen functional checks.

This is not an Agent launcher, security sandbox or human acceptance authority.
Only a new external directory may be prepared; existing work is never replaced.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "evals" / "quick" / "fixtures.json"


def case_data(case_id: str) -> tuple[dict[str, Any], str]:
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    if bundle.get("schema") != "quick-fixtures-v1" or case_id not in bundle["cases"]:
        raise ValueError(f"unknown fixture: {case_id}")
    case = bundle["cases"][case_id]
    for name in case["files"]:
        path = PurePosixPath(name)
        if (path.is_absolute() or ".." in path.parts or str(path) != name
                or any(c in name for c in "\\:\x00") or not path.parts):
            raise ValueError("fixture contains a noncanonical path")
    encoded = json.dumps(case, sort_keys=True, separators=(",", ":")).encode()
    return case, hashlib.sha256(encoded).hexdigest()


def prepare(case_id: str, destination: Path) -> dict[str, Any]:
    case, digest = case_data(case_id)
    target = destination.resolve()
    if target.is_relative_to(ROOT):
        raise ValueError("prepare outside the source checkout")
    target.mkdir(parents=False, exist_ok=False)
    project = target / "project"
    project.mkdir()
    for name, content in case["files"].items():
        path = project / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8", newline="\n")
    metadata = {"case_id": case_id, "snapshot_digest": digest, "schema": "quick-case-v1"}
    (target / "case.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    (target / "TASK.md").write_text(case["task"] + "\n", encoding="utf-8")
    return metadata


def _project(case_id: str, target: Path, case: dict[str, Any], digest: str) -> Path:
    metadata = json.loads((target / "case.json").read_text(encoding="utf-8"))
    expected = {"case_id": case_id, "snapshot_digest": digest, "schema": "quick-case-v1"}
    if metadata != expected or (target / "TASK.md").read_text(encoding="utf-8") != case["task"] + "\n":
        raise ValueError("fixture binding changed; prepare a new run instead of retargeting")
    project = target / "project"
    if project.is_symlink() or not project.is_dir():
        raise ValueError("fixture project must be a real directory")
    allowed = set(case["files"])
    for path in project.rglob("*"):
        if path.is_symlink():
            raise ValueError("fixture symlinks are not supported")
        if path.is_file() and path.relative_to(project).as_posix() not in allowed:
            raise ValueError(f"out-of-scope fixture file: {path.relative_to(project).as_posix()}")
    return project


def verify(case_id: str, destination: Path) -> dict[str, Any]:
    case, digest = case_data(case_id)
    target = destination.resolve()
    project = _project(case_id, target, case, digest)
    # The frozen oracle lives outside the editable project. -I/-B reduce ambient
    # interpreter interference; they are NOT a security sandbox for project code.
    marker = f"SPEC_KIT_FIXTURE_COMPLETED:{digest}"
    script = (
        "import sys\nfrom pathlib import Path\n"
        "sys.path.insert(0, sys.argv[1])\n" + case["verify"] +
        "\nprint(" + repr(marker) + ")\n"
    )
    with tempfile.TemporaryDirectory(prefix="quick-oracle-") as temporary:
        oracle = Path(temporary) / "verify.py"
        oracle.write_text(script, encoding="utf-8", newline="\n")
        result = subprocess.run(
            [sys.executable, "-I", "-B", str(oracle), str(project)],
            cwd=project, capture_output=True, text=True, timeout=15,
        )
    if case_data(case_id)[1] != digest:
        raise ValueError("frozen fixture changed during verification")
    _project(case_id, target, case, digest)
    passed = result.returncode == 0 and result.stdout.rstrip().endswith(marker)
    return {
        "case_id": case_id, "snapshot_digest": digest,
        "verification_status": "passed" if passed else "failed",
        "exit_code": result.returncode, "oracle_completed": result.stdout.rstrip().endswith(marker),
        "accepted": None, "agent_executed": None, "agent_launched_by_helper": False,
        "input_tokens": None, "output_tokens": None,
        "stderr_tail": result.stderr[-4096:],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "verify"])
    parser.add_argument("case_id")
    parser.add_argument("directory", type=Path)
    args = parser.parse_args(argv)
    try:
        result = prepare(args.case_id, args.directory) if args.action == "prepare" else verify(args.case_id, args.directory)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        print(f"quick-case: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, allow_nan=False))
    return 1 if result.get("verification_status") == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
