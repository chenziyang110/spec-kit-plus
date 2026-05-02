#!/usr/bin/env pwsh
param(
    [string]$ProjectRoot = ".",
    [ValidateSet("init", "status")]
    [string]$Mode = "status",
    [string]$RunSlug = ""
)

$pythonScript = @'
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


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
        "capability_triage": (run_dir / "capability-triage.md").is_file(),
        "depth_policy": (run_dir / "depth-policy.md").is_file(),
        "quality_check": (run_dir / "quality-check.md").is_file(),
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
    write_file_if_missing(
        run_dir / "capability-triage.md",
        "\n".join(
            [
                "# Capability Triage",
                "",
                "## Core Value Proposition",
                "",
                "- [Describe the repository-backed product-defining value before broad synthesis.]",
                "",
                "## Capability Tiers",
                "",
                "| Capability ID | Display Name | Tier | Why It Matters | Evidence Sources | Required Depth |",
                "| --- | --- | --- | --- | --- | --- |",
                "| [CAP-001] | [CAPABILITY] | [critical | high | standard | auxiliary] | [WHY_THIS_CAPABILITY_MATTERS] | [PATHS] | [surface | depth-qualified] |",
                "",
            ]
        ),
    )
    write_file_if_missing(
        run_dir / "depth-policy.md",
        "\n".join(
            [
                "# Depth Policy",
                "",
                "## Tier Expectations",
                "",
                "- `critical`: implementation mechanisms, traceability, edge cases, and format/protocol details when applicable.",
                "- `high`: mechanism summary, key rules, and main failure paths.",
                "- `standard`: flow-level reconstruction and main surfaces.",
                "- `auxiliary`: surface inventory unless stronger evidence demands more detail.",
                "",
            ]
        ),
    )
    write_file_if_missing(
        run_dir / "quality-check.md",
        "\n".join(
            [
                "# Quality Check",
                "",
                "## Gates",
                "",
                "| Gate | Status | Evidence | Notes |",
                "| --- | --- | --- | --- |",
                "| Capability Triage Gate | pending |  |  |",
                "| Critical Depth Gate | pending |  |  |",
                "| Traceability Gate | pending |  |  |",
                "| Export Integrity Gate | pending |  |  |",
                "| Unknown Visibility Gate | pending |  |  |",
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
'@

$pythonScript | python - $ProjectRoot $Mode $RunSlug
exit $LASTEXITCODE
