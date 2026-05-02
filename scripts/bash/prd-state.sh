#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-.}"
MODE="${2:-status}"
RUN_SLUG="${3:-}"

python - "$PROJECT_ROOT" "$MODE" "$RUN_SLUG" <<'PY'
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


EXPECTED_SURFACES = {
    "workspace": ".",
    "evidence": "evidence",
    "master": "master",
    "exports": "exports",
    "master_exports": "master/exports",
    "workflow_state": "workflow-state.md",
    "coverage_matrix": "coverage-matrix.md",
}


def run_date() -> str:
    return datetime.now(timezone.utc).strftime("%y%m%d")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    slug = slug.strip("-")
    return slug or "prd-run"


def surface_status(run_dir: Path) -> dict[str, bool]:
    return {
        "workspace": run_dir.is_dir(),
        "evidence": (run_dir / "evidence").is_dir(),
        "master": (run_dir / "master").is_dir(),
        "exports": (run_dir / "exports").is_dir(),
        "master_exports": (run_dir / "master" / "exports").is_dir(),
        "workflow_state": (run_dir / "workflow-state.md").is_file(),
        "coverage_matrix": (run_dir / "coverage-matrix.md").is_file(),
    }


def write_file_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def init_run(project_root: Path, requested_slug: str) -> dict[str, object]:
    date_value = run_date()
    slug = slugify(requested_slug)
    workspace = f"{date_value}-{slug}"
    run_dir = project_root / ".specify" / "prd-runs" / workspace
    run_dir.mkdir(parents=True, exist_ok=True)
    for dirname in ("evidence", "master", "exports", "master/exports"):
        (run_dir / dirname).mkdir(exist_ok=True)

    write_file_if_missing(
        run_dir / "workflow-state.md",
        "\n".join(
            [
                "---",
                f'id: "{workspace}"',
                f'slug: "{slug}"',
                'status: "initialized"',
                f'created_at: "{now_utc()}"',
                "---",
                "# PRD Workflow State",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-prd`",
                "- status: `active`",
                "",
                "## Phase Mode",
                "",
                "- phase_mode: `analysis-only`",
                "- summary: existing-project reverse PRD extraction",
                "",
                "## Next Action",
                "",
                "- initialize repository evidence harvest",
                "",
                "## Next Command",
                "",
                "- `/sp.prd`",
                "",
                "## Authoritative Files",
                "",
                f"- `.specify/prd-runs/{workspace}/workflow-state.md`",
                f"- `.specify/prd-runs/{workspace}/coverage-matrix.md`",
                f"- `.specify/prd-runs/{workspace}/master/master-pack.md`",
                f"- `.specify/prd-runs/{workspace}/exports/prd.md`",
                "",
                "## Open Unknowns",
                "",
                "- None recorded yet.",
                "",
            ]
        ),
    )
    write_file_if_missing(
        run_dir / "coverage-matrix.md",
        "\n".join(
            [
                "# PRD Coverage Matrix",
                "",
                "| Surface | Status | Evidence | Notes |",
                "| --- | --- | --- | --- |",
                "| Repository overview | pending |  |  |",
                "",
            ]
        ),
    )

    surfaces = surface_status(run_dir)
    return {
        "mode": "init",
        "date": date_value,
        "slug": slug,
        "workspace": workspace,
        "workspace_path": str(run_dir.resolve()),
        "surfaces": surfaces,
        "complete": all(surfaces.values()),
    }


def resolve_run_dir(project_root: Path, run_id: str) -> Path:
    if not run_id.strip():
        raise ValueError("run id is required")
    candidate = Path(run_id)
    if candidate.is_absolute():
        return candidate
    return project_root / ".specify" / "prd-runs" / run_id


def status_run(project_root: Path, run_id: str) -> dict[str, object]:
    run_dir = resolve_run_dir(project_root, run_id)
    surfaces = surface_status(run_dir)
    return {
        "mode": "status",
        "workspace": run_dir.name,
        "workspace_path": str(run_dir.resolve()),
        "surfaces": surfaces,
        "complete": all(surfaces.values()),
    }


def main() -> int:
    project_root = Path(sys.argv[1]).resolve()
    mode = (sys.argv[2] if len(sys.argv) > 2 else "status").strip().lower()
    run_slug = sys.argv[3] if len(sys.argv) > 3 else ""

    if mode == "init":
        print(json.dumps(init_run(project_root, run_slug)))
        return 0
    if mode == "status":
        print(json.dumps(status_run(project_root, run_slug)))
        return 0

    raise ValueError(f"unknown mode: {mode}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
PY
