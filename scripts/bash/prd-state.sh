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
    "scan_packets": "scan-packets",
    "worker_results": "worker-results",
    "master": "master",
    "exports": "exports",
    "workflow_state": "workflow-state.md",
    "prd_scan": "prd-scan.md",
    "coverage_ledger": "coverage-ledger.md",
    "coverage_ledger_json": "coverage-ledger.json",
    "capability_ledger_json": "capability-ledger.json",
    "artifact_contracts_json": "artifact-contracts.json",
    "reconstruction_checklist_json": "reconstruction-checklist.json",
    "master_pack": "master/master-pack.md",
    "prd_export": "exports/prd.md",
    "reconstruction_appendix": "exports/reconstruction-appendix.md",
    "data_model": "exports/data-model.md",
    "integration_contracts": "exports/integration-contracts.md",
    "runtime_behaviors": "exports/runtime-behaviors.md",
}

SCAN_SURFACE_KEYS = (
    "workspace",
    "evidence",
    "scan_packets",
    "worker_results",
    "master",
    "exports",
    "workflow_state",
    "prd_scan",
    "coverage_ledger",
    "coverage_ledger_json",
    "capability_ledger_json",
    "artifact_contracts_json",
    "reconstruction_checklist_json",
)

BUILD_SURFACE_KEYS = (
    "workspace",
    "master",
    "exports",
    "workflow_state",
    "master_pack",
    "prd_export",
    "reconstruction_appendix",
    "data_model",
    "integration_contracts",
    "runtime_behaviors",
)


def run_date() -> str:
    return datetime.now(timezone.utc).strftime("%y%m%d")


def now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    slug = slug.strip("-")
    return slug or "prd-run"


def canonical_mode(mode: str) -> tuple[str, str]:
    normalized = mode.strip().lower()
    aliases = {
        "init": ("init-scan", "init"),
        "status": ("status-scan", "status"),
        "init-scan": ("init-scan", "init-scan"),
        "status-scan": ("status-scan", "status-scan"),
        "status-build": ("status-build", "status-build"),
    }
    if normalized not in aliases:
        raise ValueError(f"unknown mode: {mode}")
    return aliases[normalized]


def surface_status(run_dir: Path) -> dict[str, bool]:
    statuses: dict[str, bool] = {}
    for key, relative in EXPECTED_SURFACES.items():
        path = run_dir if relative == "." else run_dir / relative
        statuses[key] = path.is_dir() if "." not in Path(relative).name and Path(relative).suffix == "" and relative != "." else path.exists()
        if relative == ".":
            statuses[key] = run_dir.is_dir()
        elif Path(relative).suffix:
            statuses[key] = path.is_file()
        else:
            statuses[key] = path.is_dir()
    return statuses


def write_file_if_missing(path: Path, content: str) -> None:
    if not path.exists():
        path.write_text(content, encoding="utf-8")


def scan_workflow_state(workspace: str, slug: str, active_command: str) -> str:
    return "\n".join(
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
            f"- active_command: `{active_command}`",
            "- status: `active`",
            "",
            "## Phase Mode",
            "",
            "- phase_mode: `analysis-only`",
            "- summary: reconstruction scan package initialization",
            "",
            "## Allowed Artifact Writes",
            "",
            f"- `.specify/prd-runs/{workspace}/workflow-state.md`",
            f"- `.specify/prd-runs/{workspace}/prd-scan.md`",
            f"- `.specify/prd-runs/{workspace}/coverage-ledger.md`",
            f"- `.specify/prd-runs/{workspace}/coverage-ledger.json`",
            f"- `.specify/prd-runs/{workspace}/capability-ledger.json`",
            f"- `.specify/prd-runs/{workspace}/artifact-contracts.json`",
            f"- `.specify/prd-runs/{workspace}/reconstruction-checklist.json`",
            f"- `.specify/prd-runs/{workspace}/scan-packets/`",
            f"- `.specify/prd-runs/{workspace}/worker-results/`",
            f"- `.specify/prd-runs/{workspace}/evidence/`",
            "",
            "## Forbidden Actions",
            "",
            "- edit source code",
            "- implement product changes",
            "- write final PRD exports",
            "",
            "## Next Action",
            "",
            "- initialize reconstruction evidence harvest",
            "",
            "## Next Command",
            "",
            "- `/sp.prd-build`",
            "",
            "## Authoritative Files",
            "",
            f"- `.specify/prd-runs/{workspace}/workflow-state.md`",
            f"- `.specify/prd-runs/{workspace}/prd-scan.md`",
            f"- `.specify/prd-runs/{workspace}/coverage-ledger.json`",
            f"- `.specify/prd-runs/{workspace}/artifact-contracts.json`",
            f"- `.specify/prd-runs/{workspace}/reconstruction-checklist.json`",
            "",
            "## Open Unknowns",
            "",
            "- None recorded yet.",
            "",
        ]
    )


def init_scan_artifacts(run_dir: Path) -> None:
    for dirname in ("evidence", "scan-packets", "worker-results", "master", "exports"):
        (run_dir / dirname).mkdir(exist_ok=True)

    write_file_if_missing(
        run_dir / "prd-scan.md",
        "\n".join(
            [
                "# PRD Scan",
                "",
                "## Reconstruction Summary",
                "",
                "- Status: initialized",
                "",
            ]
        ),
    )
    write_file_if_missing(
        run_dir / "coverage-ledger.md",
        "\n".join(
            [
                "# Coverage Ledger",
                "",
                "| Surface | Status | Evidence | Notes |",
                "| --- | --- | --- | --- |",
                "| Repository overview | pending |  |  |",
                "",
            ]
        ),
    )
    write_file_if_missing(
        run_dir / "coverage-ledger.json",
        json.dumps({"version": 1, "rows": []}, indent=2) + "\n",
    )
    write_file_if_missing(
        run_dir / "capability-ledger.json",
        json.dumps({"capabilities": []}, indent=2) + "\n",
    )
    write_file_if_missing(
        run_dir / "artifact-contracts.json",
        json.dumps({"artifacts": []}, indent=2) + "\n",
    )
    write_file_if_missing(
        run_dir / "reconstruction-checklist.json",
        json.dumps({"checks": []}, indent=2) + "\n",
    )


def init_run(project_root: Path, requested_slug: str, active_command: str, payload_mode: str) -> dict[str, object]:
    date_value = run_date()
    slug = slugify(requested_slug)
    workspace = f"{date_value}-{slug}"
    run_dir = project_root / ".specify" / "prd-runs" / workspace
    run_dir.mkdir(parents=True, exist_ok=True)

    write_file_if_missing(run_dir / "workflow-state.md", scan_workflow_state(workspace, slug, active_command))
    init_scan_artifacts(run_dir)

    surfaces = surface_status(run_dir)
    return {
        "mode": payload_mode,
        "date": date_value,
        "slug": slug,
        "workspace": workspace,
        "workspace_path": str(run_dir.resolve()),
        "surfaces": surfaces,
        "complete": all(surfaces[key] for key in SCAN_SURFACE_KEYS),
    }


def resolve_run_dir(project_root: Path, run_id: str) -> Path:
    if not run_id.strip():
        raise ValueError("run id is required")
    candidate = Path(run_id)
    if candidate.is_absolute():
        return candidate
    return project_root / ".specify" / "prd-runs" / run_id


def status_run(project_root: Path, run_id: str, payload_mode: str, surface_keys: tuple[str, ...]) -> dict[str, object]:
    run_dir = resolve_run_dir(project_root, run_id)
    surfaces = surface_status(run_dir)
    return {
        "mode": payload_mode,
        "workspace": run_dir.name,
        "workspace_path": str(run_dir.resolve()),
        "surfaces": surfaces,
        "complete": all(surfaces[key] for key in surface_keys),
    }


def main() -> int:
    project_root = Path(sys.argv[1]).resolve()
    requested_mode = sys.argv[2] if len(sys.argv) > 2 else "status"
    run_slug = sys.argv[3] if len(sys.argv) > 3 else ""
    mode, payload_mode = canonical_mode(requested_mode)

    if mode == "init-scan":
        active_command = "sp-prd" if payload_mode == "init" else "sp-prd-scan"
        print(json.dumps(init_run(project_root, run_slug, active_command, payload_mode)))
        return 0
    if mode == "status-scan":
        print(json.dumps(status_run(project_root, run_slug, payload_mode, SCAN_SURFACE_KEYS)))
        return 0
    if mode == "status-build":
        print(json.dumps(status_run(project_root, run_slug, payload_mode, BUILD_SURFACE_KEYS)))
        return 0

    raise ValueError(f"unknown mode: {requested_mode}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(str(exc), file=sys.stderr)
        raise SystemExit(1)
PY
