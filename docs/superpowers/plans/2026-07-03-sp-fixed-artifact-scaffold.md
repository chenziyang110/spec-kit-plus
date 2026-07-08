# SP Fixed Artifact Scaffold Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a registry-driven `specify artifact` surface that audits fixed `sp-*` artifact cost and creates path-safe fixed scaffolds for the first two low-risk artifacts.

**Architecture:** Add a focused `specify_cli.artifacts` package for registry, audit, path safety, and scaffold writing. Wire it into the existing Typer CLI as a new `artifact` subcommand group, package fixed scaffold templates under `templates/artifacts/`, and update only `sp-quick` and `sp-plan` guidance for the first rollout.

**Tech Stack:** Python 3.11, Typer, pytest, packaged template assets through Hatch `force-include`, existing Markdown command templates.

---

## Scope Check

This plan implements the first rollout from the approved design, not the full multi-workflow conversion. It produces working, testable software for:

- deterministic artifact registry and fixed-cost audit
- create-only scaffold writing with path safety
- first scaffold kinds: `quick-status` and `plan-contract`
- CLI surface: `specify artifact audit-fixed-cost` and `specify artifact scaffold`
- workflow guidance updates for `sp-quick` and `sp-plan`

The plan does not implement `sp-discussion`, `sp-specify`, `sp-debug`, or `sp-tasks` scaffolds. Those should be added only after the audit output proves clear savings and low quality risk.

## File Structure

- Create `src/specify_cli/artifacts/__init__.py`
  - Public exports for registry, audit, and scaffold helpers.
- Create `src/specify_cli/artifacts/registry.py`
  - Owns scaffold registry dataclasses, first two registry entries, fixed-cost audit calculation, and registry validation.
- Create `src/specify_cli/artifacts/scaffold.py`
  - Owns project-relative path safety, template rendering, create-only writes, and compact scaffold result payloads.
- Create `templates/artifacts/quick-status.md`
  - Fixed Markdown skeleton for `.planning/quick/<id>-<slug>/STATUS.md` with stable `agent-fill:*` anchors.
- Modify `templates/plan-contract-template.json`
  - Keep the existing safe JSON skeleton. Do not duplicate it under `templates/artifacts/` in this rollout.
- Modify `src/specify_cli/__init__.py`
  - Add `artifact_app` Typer group and two commands.
- Modify `pyproject.toml`
  - Add `templates/artifacts` to wheel `force-include`.
- Modify `templates/commands/quick.md`
  - Replace the long inline `STATUS.md` fixed template block with scaffold guidance and a compact field list.
- Modify `templates/commands/plan.md`
  - Tell agents to scaffold `plan-contract.json` with a project-relative `--out`, especially when prerequisite helpers emit absolute `FEATURE_DIR`.
- Create `tests/test_artifact_scaffold.py`
  - Unit tests for registry, audit, path safety, scaffold writes, overwrite protection, and readiness rejection.
- Create `tests/test_artifact_cli.py`
  - CLI tests for help, audit JSON, scaffold JSON, project gating, and unsafe paths.
- Modify `tests/test_packaging_assets.py`
  - Assert `templates/artifacts` is force-included and installed by shared infra.
- Modify `tests/test_quick_template_guidance.py`
  - Assert quick guidance uses scaffold instead of embedding the full fixed status template.
- Modify `tests/test_plan_research_contract.py`
  - Assert plan guidance uses project-relative scaffold output for `plan-contract.json`.

## Task 1: Add Registry And Audit Model

**Files:**
- Create: `src/specify_cli/artifacts/__init__.py`
- Create: `src/specify_cli/artifacts/registry.py`
- Test: `tests/test_artifact_scaffold.py`

- [ ] **Step 1: Write failing registry and audit tests**

Add this initial test file:

```python
from pathlib import Path

from specify_cli.artifacts.registry import (
    ARTIFACT_REGISTRY,
    audit_fixed_cost,
    get_artifact_kind,
    validate_registry,
)


def test_registry_contains_first_rollout_kinds() -> None:
    assert {"quick-status", "plan-contract"} <= set(ARTIFACT_REGISTRY)
    quick = get_artifact_kind("quick-status")
    assert quick.workflow == "sp-quick"
    assert quick.allowed_output_paths == (".planning/quick/*/STATUS.md",)
    assert "current_focus" in quick.agent_fill_required
    assert quick.fill_targets["current_focus"]["anchor"] == "agent-fill:current_focus"

    plan = get_artifact_kind("plan-contract")
    assert plan.workflow == "sp-plan"
    assert plan.allowed_output_paths == ("specs/*/plan-contract.json", ".specify/features/*/plan-contract.json")
    assert plan.validator == "json"


def test_validate_registry_reports_no_errors_for_first_rollout() -> None:
    assert validate_registry() == []


def test_audit_reports_fixed_savings_and_registry_metadata() -> None:
    payload = audit_fixed_cost()

    assert payload["status"] == "ok"
    assert payload["candidate_count"] == 2
    by_kind = {candidate["kind"]: candidate for candidate in payload["candidates"]}

    quick = by_kind["quick-status"]
    assert quick["workflow"] == "sp-quick"
    assert quick["recommendation"] == "scaffold"
    assert quick["fixed_bytes"] > 1000
    assert quick["estimated_token_savings"] == quick["fixed_bytes"] // 4
    assert quick["quality_risk"] == "low"
    assert quick["fill_targets"]["current_focus"]["type"] == "markdown_anchor"

    plan = by_kind["plan-contract"]
    assert plan["workflow"] == "sp-plan"
    assert plan["recommendation"] == "builder"
    assert plan["fixed_bytes"] > 500
    assert plan["downstream_consumers"] == ["sp-tasks", "sp-analyze"]
```

- [ ] **Step 2: Run the tests and verify the expected import failure**

Run:

```bash
pytest tests/test_artifact_scaffold.py -q
```

Expected: fails with `ModuleNotFoundError: No module named 'specify_cli.artifacts'`.

- [ ] **Step 3: Create the artifact package exports**

Create `src/specify_cli/artifacts/__init__.py`:

```python
"""Fixed artifact scaffold registry and writers."""

from .registry import (
    ARTIFACT_REGISTRY,
    ArtifactKind,
    audit_fixed_cost,
    get_artifact_kind,
    validate_registry,
)
from .scaffold import ArtifactScaffoldError, scaffold_artifact

__all__ = [
    "ARTIFACT_REGISTRY",
    "ArtifactKind",
    "ArtifactScaffoldError",
    "audit_fixed_cost",
    "get_artifact_kind",
    "scaffold_artifact",
    "validate_registry",
]
```

This imports `scaffold.py`, which does not exist yet. Task 2 will create it. If the import blocks this task, keep the export line and create a temporary empty `scaffold.py` in Step 4 of this task with only the exception class and function stub shown below.

- [ ] **Step 4: Create registry implementation**

Create `src/specify_cli/artifacts/registry.py`:

```python
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ArtifactKind:
    kind: str
    workflow: str
    artifact: str
    source_template: str
    prompt_refs: tuple[str, ...]
    allowed_output_paths: tuple[str, ...]
    fixed_anchors: tuple[str, ...]
    agent_fill_required: tuple[str, ...]
    fill_targets: dict[str, dict[str, str]]
    validator: str
    downstream_consumers: list[str]
    package_targets: tuple[str, ...]
    scriptability: str
    quality_risk: str
    recommendation: str
    fixed_bytes_estimate: int
    semantic_bytes_estimate: int

    def audit_record(self) -> dict[str, Any]:
        fixed_bytes = self.fixed_bytes_estimate
        semantic_bytes = self.semantic_bytes_estimate
        total = fixed_bytes + semantic_bytes
        fixed_ratio = round(fixed_bytes / total, 2) if total else 0.0
        return {
            "kind": self.kind,
            "workflow": self.workflow,
            "artifact": self.artifact,
            "source_template": self.source_template,
            "prompt_refs": list(self.prompt_refs),
            "allowed_output_paths": list(self.allowed_output_paths),
            "fixed_anchors": list(self.fixed_anchors),
            "fixed_bytes": fixed_bytes,
            "semantic_bytes": semantic_bytes,
            "fixed_ratio": fixed_ratio,
            "estimated_token_savings": fixed_bytes // 4,
            "scriptability": self.scriptability,
            "quality_risk": self.quality_risk,
            "recommendation": self.recommendation,
            "agent_fill_required": list(self.agent_fill_required),
            "fill_targets": self.fill_targets,
            "validator": self.validator,
            "downstream_consumers": self.downstream_consumers,
            "package_targets": list(self.package_targets),
        }


ARTIFACT_REGISTRY: dict[str, ArtifactKind] = {
    "quick-status": ArtifactKind(
        kind="quick-status",
        workflow="sp-quick",
        artifact="STATUS.md",
        source_template="templates/artifacts/quick-status.md",
        prompt_refs=("templates/commands/quick.md",),
        allowed_output_paths=(".planning/quick/*/STATUS.md",),
        fixed_anchors=(
            "agent-fill:discussion_handoff_source",
            "agent-fill:current_focus",
            "agent-fill:execution_intent",
            "agent-fill:understanding_checkpoint",
            "agent-fill:execution",
            "agent-fill:validation",
            "agent-fill:summary_pointer",
            "agent-fill:senior_consequence_analysis",
        ),
        agent_fill_required=(
            "discussion_handoff_source",
            "current_focus",
            "execution_intent",
            "understanding_checkpoint",
            "execution",
            "validation",
            "summary_pointer",
            "senior_consequence_analysis",
        ),
        fill_targets={
            "discussion_handoff_source": {"type": "markdown_anchor", "anchor": "agent-fill:discussion_handoff_source"},
            "current_focus": {"type": "markdown_anchor", "anchor": "agent-fill:current_focus"},
            "execution_intent": {"type": "markdown_anchor", "anchor": "agent-fill:execution_intent"},
            "understanding_checkpoint": {"type": "markdown_anchor", "anchor": "agent-fill:understanding_checkpoint"},
            "execution": {"type": "markdown_anchor", "anchor": "agent-fill:execution"},
            "validation": {"type": "markdown_anchor", "anchor": "agent-fill:validation"},
            "summary_pointer": {"type": "markdown_anchor", "anchor": "agent-fill:summary_pointer"},
            "senior_consequence_analysis": {"type": "markdown_anchor", "anchor": "agent-fill:senior_consequence_analysis"},
        },
        validator="markdown-anchors",
        downstream_consumers=["sp-quick", "specify quick"],
        package_targets=("templates/artifacts",),
        scriptability="high",
        quality_risk="low",
        recommendation="scaffold",
        fixed_bytes_estimate=7600,
        semantic_bytes_estimate=2400,
    ),
    "plan-contract": ArtifactKind(
        kind="plan-contract",
        workflow="sp-plan",
        artifact="plan-contract.json",
        source_template="templates/plan-contract-template.json",
        prompt_refs=("templates/commands/plan.md",),
        allowed_output_paths=("specs/*/plan-contract.json", ".specify/features/*/plan-contract.json"),
        fixed_anchors=(
            "/version",
            "/status",
            "/route",
            "/intent",
            "/complexity_level",
            "/capability_preservation",
            "/consequence_gate",
            "/consequence_analysis",
        ),
        agent_fill_required=(
            "/route",
            "/intent",
            "/complexity_level",
            "/must_preserve",
            "/acceptance_obligations",
        ),
        fill_targets={
            "route": {"type": "json_pointer", "pointer": "/route"},
            "intent": {"type": "json_pointer", "pointer": "/intent"},
            "complexity_level": {"type": "json_pointer", "pointer": "/complexity_level"},
            "must_preserve": {"type": "json_pointer", "pointer": "/must_preserve"},
            "acceptance_obligations": {"type": "json_pointer", "pointer": "/acceptance_obligations"},
        },
        validator="json",
        downstream_consumers=["sp-tasks", "sp-analyze"],
        package_targets=("templates/plan-contract-template.json",),
        scriptability="high",
        quality_risk="low",
        recommendation="builder",
        fixed_bytes_estimate=2100,
        semantic_bytes_estimate=1600,
    ),
}


def get_artifact_kind(kind: str) -> ArtifactKind:
    try:
        return ARTIFACT_REGISTRY[kind]
    except KeyError as exc:
        raise ValueError(f"unknown artifact scaffold kind: {kind}") from exc


def validate_registry() -> list[str]:
    errors: list[str] = []
    seen = set()
    for kind, entry in ARTIFACT_REGISTRY.items():
        if kind != entry.kind:
            errors.append(f"{kind}: key must match entry.kind")
        if entry.kind in seen:
            errors.append(f"{kind}: duplicate kind")
        seen.add(entry.kind)
        if not entry.source_template:
            errors.append(f"{kind}: source_template is required")
        if not entry.allowed_output_paths:
            errors.append(f"{kind}: allowed_output_paths is required")
        if not entry.fill_targets:
            errors.append(f"{kind}: fill_targets is required")
        for name in entry.agent_fill_required:
            if name not in entry.fill_targets and not name.startswith("/"):
                errors.append(f"{kind}: missing fill target for {name}")
        if entry.recommendation not in {"scaffold", "builder", "skip_low_savings", "skip_semantic", "defer_risk"}:
            errors.append(f"{kind}: invalid recommendation {entry.recommendation}")
    return errors


def audit_fixed_cost() -> dict[str, Any]:
    errors = validate_registry()
    candidates = [entry.audit_record() for entry in ARTIFACT_REGISTRY.values()]
    return {
        "status": "blocked" if errors else "ok",
        "candidate_count": len(candidates),
        "errors": errors,
        "candidates": candidates,
    }
```

- [ ] **Step 5: Add temporary scaffold stub if needed**

If `tests/test_artifact_scaffold.py` still fails on `specify_cli.artifacts.scaffold`, create `src/specify_cli/artifacts/scaffold.py` with:

```python
class ArtifactScaffoldError(ValueError):
    """Raised when a fixed artifact scaffold cannot be written safely."""


def scaffold_artifact(*args, **kwargs):
    raise ArtifactScaffoldError("artifact scaffold writer is not implemented")
```

- [ ] **Step 6: Run registry tests**

Run:

```bash
pytest tests/test_artifact_scaffold.py::test_registry_contains_first_rollout_kinds tests/test_artifact_scaffold.py::test_validate_registry_reports_no_errors_for_first_rollout tests/test_artifact_scaffold.py::test_audit_reports_fixed_savings_and_registry_metadata -q
```

Expected: PASS.

- [ ] **Step 7: Commit registry and audit model**

Run:

```bash
git add src/specify_cli/artifacts tests/test_artifact_scaffold.py
git commit -m "feat: add artifact scaffold registry"
```

## Task 2: Add Path-Safe Scaffold Writer

**Files:**
- Modify: `src/specify_cli/artifacts/scaffold.py`
- Modify: `tests/test_artifact_scaffold.py`

- [ ] **Step 1: Add failing path safety and scaffold tests**

Append these tests to `tests/test_artifact_scaffold.py`:

```python
import json
import os

import pytest

from specify_cli.artifacts.scaffold import ArtifactScaffoldError, scaffold_artifact


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    (project / ".specify").mkdir(parents=True)
    return project


def test_scaffold_rejects_absolute_output_path(tmp_path: Path) -> None:
    project = _project(tmp_path)
    absolute_out = project / ".planning" / "quick" / "001-demo" / "STATUS.md"

    with pytest.raises(ArtifactScaffoldError, match="unsafe_path"):
        scaffold_artifact(
            project,
            kind="quick-status",
            out_path=str(absolute_out),
            variables={"id": "001", "slug": "demo", "title": "Demo", "trigger": "demo"},
        )


def test_scaffold_rejects_traversal_output_path(tmp_path: Path) -> None:
    project = _project(tmp_path)

    with pytest.raises(ArtifactScaffoldError, match="unsafe_path"):
        scaffold_artifact(
            project,
            kind="quick-status",
            out_path=".planning/quick/001-demo/../../escape.md",
            variables={"id": "001", "slug": "demo", "title": "Demo", "trigger": "demo"},
        )


def test_scaffold_rejects_disallowed_kind_path(tmp_path: Path) -> None:
    project = _project(tmp_path)

    with pytest.raises(ArtifactScaffoldError, match="unsafe_path"):
        scaffold_artifact(
            project,
            kind="quick-status",
            out_path="specs/001-demo/STATUS.md",
            variables={"id": "001", "slug": "demo", "title": "Demo", "trigger": "demo"},
        )


def test_scaffold_rejects_symlink_escape(tmp_path: Path) -> None:
    if os.name == "nt":
        pytest.skip("symlink creation is not consistently available on Windows test hosts")
    project = _project(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    quick_root = project / ".planning" / "quick"
    quick_root.mkdir(parents=True)
    (quick_root / "001-demo").symlink_to(outside, target_is_directory=True)

    with pytest.raises(ArtifactScaffoldError, match="unsafe_path"):
        scaffold_artifact(
            project,
            kind="quick-status",
            out_path=".planning/quick/001-demo/STATUS.md",
            variables={"id": "001", "slug": "demo", "title": "Demo", "trigger": "demo"},
        )


def test_quick_status_scaffold_writes_create_only_file_with_fill_targets(tmp_path: Path) -> None:
    project = _project(tmp_path)

    payload = scaffold_artifact(
        project,
        kind="quick-status",
        out_path=".planning/quick/001-demo/STATUS.md",
        variables={"id": "001", "slug": "demo", "title": "Demo", "trigger": "Fix demo"},
    )

    status_path = project / ".planning" / "quick" / "001-demo" / "STATUS.md"
    text = status_path.read_text(encoding="utf-8")
    assert payload["status"] == "created"
    assert payload["path"] == ".planning/quick/001-demo/STATUS.md"
    assert payload["agent_fill_required"]
    assert payload["fill_targets"]["current_focus"]["anchor"] == "agent-fill:current_focus"
    assert "understanding_confirmed: false" in text
    assert "status: gathering" in text
    assert "<!-- agent-fill:current_focus -->" in text

    with pytest.raises(ArtifactScaffoldError, match="blocked_existing_file"):
        scaffold_artifact(
            project,
            kind="quick-status",
            out_path=".planning/quick/001-demo/STATUS.md",
            variables={"id": "001", "slug": "demo", "title": "Demo", "trigger": "Fix demo"},
        )


def test_plan_contract_scaffold_rejects_unsafe_ready_status(tmp_path: Path) -> None:
    project = _project(tmp_path)

    with pytest.raises(ArtifactScaffoldError, match="unsafe_status"):
        scaffold_artifact(
            project,
            kind="plan-contract",
            out_path="specs/001-demo/plan-contract.json",
            variables={"status": "ready"},
        )


def test_plan_contract_scaffold_writes_safe_json_skeleton(tmp_path: Path) -> None:
    project = _project(tmp_path)
    (project / "specs" / "001-demo").mkdir(parents=True)

    payload = scaffold_artifact(
        project,
        kind="plan-contract",
        out_path="specs/001-demo/plan-contract.json",
        variables={},
    )

    path = project / "specs" / "001-demo" / "plan-contract.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert payload["status"] == "created"
    assert payload["path"] == "specs/001-demo/plan-contract.json"
    assert payload["fill_targets"]["route"]["pointer"] == "/route"
    assert data["status"] == "pending"
    assert data["handoff_to_tasks_ready"] is False
```

- [ ] **Step 2: Run the tests and verify writer failures**

Run:

```bash
pytest tests/test_artifact_scaffold.py -q
```

Expected: fails because `scaffold_artifact` is still a stub or lacks path/template behavior.

- [ ] **Step 3: Implement path safety and scaffold writing**

Replace `src/specify_cli/artifacts/scaffold.py` with:

```python
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .registry import get_artifact_kind


class ArtifactScaffoldError(ValueError):
    """Raised when a fixed artifact scaffold cannot be written safely."""


UNSAFE_READY_VALUES = {"ready", "approved", "user_confirmed", "user-confirmed", True}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _template_source(project_root: Path, source_template: str) -> Path:
    project_candidate = project_root / ".specify" / source_template
    if project_candidate.is_file():
        return project_candidate
    core_candidate = Path(__file__).resolve().parents[1] / "core_pack" / source_template
    if core_candidate.is_file():
        return core_candidate
    repo_candidate = _repo_root() / source_template
    if repo_candidate.is_file():
        return repo_candidate
    raise ArtifactScaffoldError(f"template_not_found: {source_template}")


def _matches_allowed_pattern(relative_path: str, patterns: tuple[str, ...]) -> bool:
    for pattern in patterns:
        regex = "^" + re.escape(pattern).replace("\\*", "[^/]+") + "$"
        if re.match(regex, relative_path):
            return True
    return False


def _allowed_root(pattern: str) -> str:
    if "*" not in pattern:
        parent = str(Path(pattern).parent).replace("\\", "/")
        return "" if parent == "." else parent
    prefix = pattern.split("*", 1)[0].rstrip("/")
    return prefix.rstrip("/")


def _resolve_safe_output_path(project_root: Path, kind: str, out_path: str) -> tuple[Path, str]:
    entry = get_artifact_kind(kind)
    raw = Path(out_path)
    if raw.is_absolute():
        raise ArtifactScaffoldError("unsafe_path: absolute output paths are not accepted")
    raw_parts = raw.parts
    if any(part == ".." for part in raw_parts):
        raise ArtifactScaffoldError("unsafe_path: traversal segments are not accepted")

    normalized = raw.as_posix().lstrip("./")
    if not _matches_allowed_pattern(normalized, entry.allowed_output_paths):
        raise ArtifactScaffoldError(f"unsafe_path: {normalized} is not allowed for {kind}")

    project_resolved = project_root.resolve()
    target = (project_resolved / normalized)
    target_parent = target.parent
    existing_parent = target_parent
    while not existing_parent.exists() and existing_parent != project_resolved:
        existing_parent = existing_parent.parent
    resolved_existing_parent = existing_parent.resolve()
    if project_resolved not in (resolved_existing_parent, *resolved_existing_parent.parents):
        raise ArtifactScaffoldError("unsafe_path: parent resolves outside project root")

    allowed = False
    for pattern in entry.allowed_output_paths:
        root_rel = _allowed_root(pattern)
        allowed_root = (project_resolved / root_rel).resolve() if root_rel else project_resolved
        if allowed_root in (resolved_existing_parent, *resolved_existing_parent.parents):
            allowed = True
            break
    if not allowed:
        raise ArtifactScaffoldError("unsafe_path: parent resolves outside allowed kind root")

    return target, normalized


def _render_markdown_template(text: str, variables: dict[str, Any]) -> str:
    rendered = text
    safe_vars = {
        "id": str(variables.get("id") or ""),
        "slug": str(variables.get("slug") or ""),
        "title": str(variables.get("title") or ""),
        "trigger": str(variables.get("trigger") or ""),
    }
    for key, value in safe_vars.items():
        rendered = rendered.replace("{{" + key + "}}", value)
    return rendered


def _guard_safe_variables(variables: dict[str, Any]) -> None:
    for key, value in variables.items():
        if key.lower() in {"status", "ready", "approved", "user_confirmed", "user-confirmed"}:
            if value in UNSAFE_READY_VALUES or str(value).strip().lower() in {"ready", "approved", "user_confirmed", "user-confirmed", "true"}:
                raise ArtifactScaffoldError("unsafe_status: scaffold cannot create approved or ready state")


def _render_payload(project_root: Path, kind: str, variables: dict[str, Any]) -> str:
    entry = get_artifact_kind(kind)
    source = _template_source(project_root, entry.source_template)
    text = source.read_text(encoding="utf-8")
    if entry.validator == "json":
        payload = json.loads(text)
        for key, value in variables.items():
            if key in payload:
                payload[key] = value
        return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    return _render_markdown_template(text, variables)


def scaffold_artifact(
    project_root: Path,
    *,
    kind: str,
    out_path: str,
    variables: dict[str, Any] | None = None,
) -> dict[str, Any]:
    variables = dict(variables or {})
    _guard_safe_variables(variables)
    entry = get_artifact_kind(kind)
    target, relative = _resolve_safe_output_path(project_root, kind, out_path)
    if target.exists():
        raise ArtifactScaffoldError("blocked_existing_file: scaffold target already exists")

    content = _render_payload(project_root, kind, variables)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    record = entry.audit_record()
    return {
        "status": "created",
        "kind": kind,
        "path": relative,
        "estimated_token_savings": record["estimated_token_savings"],
        "agent_fill_required": record["agent_fill_required"],
        "fill_targets": record["fill_targets"],
    }
```

- [ ] **Step 4: Run path safety and scaffold tests**

Run:

```bash
pytest tests/test_artifact_scaffold.py -q
```

Expected: tests still fail for `quick-status` because the template file does not exist. Other failures should be template-not-found, not path-safety logic.

- [ ] **Step 5: Commit path-safety implementation after templates are added**

Do not commit yet. Task 3 adds the required template, then commit the writer and template together.

## Task 3: Add First Scaffold Templates

**Files:**
- Create: `templates/artifacts/quick-status.md`
- Reuse: `templates/plan-contract-template.json`
- Modify: `tests/test_packaging_assets.py`

- [ ] **Step 1: Create quick status scaffold template**

Create `templates/artifacts/quick-status.md`:

```markdown
---
id: "{{id}}"
slug: "{{slug}}"
title: "{{title}}"
status: gathering
trigger: "{{trigger}}"
understanding_confirmed: false
execution_model: subagent-mandatory
dispatch_shape: one-subagent | parallel-subagents
execution_surface: native-subagents
created: ""
updated: ""
---

## Discussion Handoff Source
<!-- agent-fill:discussion_handoff_source -->

handoff_consumer: none
source_discussion_slug: none
source_handoff_md: none
source_handoff_json: none
source_files_read: []
locked_direction: []
must_preserve: []
reopen_conditions: []
quick_task_candidate:
  bounded_scope: []
  excluded_scope: []
  validation_route: []

## Current Focus
<!-- agent-fill:current_focus -->

goal: ""
current_focus: ""
next_action: ""

## Execution Intent
<!-- agent-fill:execution_intent -->

intent_outcome: ""
intent_constraints: []
success_evidence: []
cognition_facts:
  selected_capability: unknown
  minimal_reads: []
  validation_route: unknown
  known_risk: none

## Understanding Checkpoint
<!-- agent-fill:understanding_checkpoint -->

checkpoint:
  issue: ""
  issue_detail: ""
  expected_or_target: ""
  known_facts: []
  unknowns_or_risks: []
  will_change: []
  will_not_change: []
  in_scope: []
  out_of_scope: []
  affected_surfaces: []
  execution_approach: ""
  implementation_plan: []
  next_action: ""
  validation_evidence: []
  stop_condition: ""
  done_or_progress_signal: ""
  user_corrections: []

## Execution
<!-- agent-fill:execution -->

blocked_dispatch:
  status: none
  reason: ""
lanes: []
retry_attempts: 0
recovery_action: none

## Validation
<!-- agent-fill:validation -->

validation_evidence: []
unverified_surfaces: []
terminal_status: gathering

## Summary Pointer
<!-- agent-fill:summary_pointer -->

summary_path: ""
changed_code_paths: []
changed_behavior_surfaces: []
project_cognition_refresh:
  status: not-needed
  evidence: []

## Senior Consequence Analysis
<!-- agent-fill:senior_consequence_analysis -->

affected_objects: []
state_behavior_matrix: []
dependency_impact: []
recovery_and_validation: []
project_cognition_evidence: []
coverage_gaps: []
escalation_decision: none
```

- [ ] **Step 2: Add packaging assertions**

Append this test to `tests/test_packaging_assets.py`:

```python
def test_wheel_force_include_bundles_artifact_scaffold_templates() -> None:
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert '"templates/artifacts" = "specify_cli/core_pack/templates/artifacts"' in pyproject
    assert (REPO_ROOT / "templates" / "artifacts" / "quick-status.md").exists()
```

- [ ] **Step 3: Run tests and verify packaging failure**

Run:

```bash
pytest tests/test_artifact_scaffold.py tests/test_packaging_assets.py::test_wheel_force_include_bundles_artifact_scaffold_templates -q
```

Expected: artifact scaffold tests pass or fail only on package assertion. Packaging assertion fails because `pyproject.toml` is not updated yet.

- [ ] **Step 4: Add artifact templates to package data**

Modify `pyproject.toml` under `[tool.hatch.build.targets.wheel.force-include]` near the existing template entries:

```toml
"templates/artifacts" = "specify_cli/core_pack/templates/artifacts"
```

- [ ] **Step 5: Add install-shared-infra assertion for artifact templates**

In `tests/test_packaging_assets.py::test_install_shared_infra_copies_split_core_pack_template_dirs`, add these setup lines after the `core_pack / "templates"` setup:

```python
    (core_pack / "templates" / "artifacts").mkdir(parents=True)
    (core_pack / "templates" / "artifacts" / "quick-status.md").write_text(
        "# Quick Status\n",
        encoding="utf-8",
    )
```

Add this assertion near the other `.specify/templates` assertions:

```python
    assert (project_root / ".specify" / "templates" / "artifacts" / "quick-status.md").exists()
```

Use the local variable name already present in that test. In the current file it is `project_root`.

- [ ] **Step 6: Run scaffold and packaging tests**

Run:

```bash
pytest tests/test_artifact_scaffold.py tests/test_packaging_assets.py::test_wheel_force_include_bundles_artifact_scaffold_templates tests/test_packaging_assets.py::test_install_shared_infra_copies_split_core_pack_template_dirs -q
```

Expected: PASS.

- [ ] **Step 7: Commit scaffold writer and templates**

Run:

```bash
git add src/specify_cli/artifacts/scaffold.py templates/artifacts/quick-status.md pyproject.toml tests/test_artifact_scaffold.py tests/test_packaging_assets.py
git commit -m "feat: scaffold fixed workflow artifacts"
```

## Task 4: Wire Artifact CLI Commands

**Files:**
- Modify: `src/specify_cli/__init__.py`
- Create: `tests/test_artifact_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Create `tests/test_artifact_cli.py`:

```python
import json
import os
from pathlib import Path

from typer.testing import CliRunner

from specify_cli import app


runner = CliRunner()


def _run_in_project(project: Path, args: list[str]):
    old_cwd = os.getcwd()
    try:
        os.chdir(project)
        return runner.invoke(app, args, catch_exceptions=False)
    finally:
        os.chdir(old_cwd)


def test_artifact_help_surface_is_registered() -> None:
    result = runner.invoke(app, ["artifact", "--help"], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    assert "audit-fixed-cost" in result.output
    assert "scaffold" in result.output


def test_artifact_audit_requires_specify_project(tmp_path: Path) -> None:
    result = _run_in_project(tmp_path, ["artifact", "audit-fixed-cost", "--format", "json"])

    assert result.exit_code != 0
    assert "Not a Spec Kit Plus project" in result.output


def test_artifact_audit_emits_compact_json(tmp_path: Path) -> None:
    project = tmp_path / "project"
    (project / ".specify").mkdir(parents=True)

    result = _run_in_project(project, ["artifact", "audit-fixed-cost", "--format", "json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "ok"
    assert payload["candidate_count"] == 2


def test_artifact_scaffold_writes_quick_status(tmp_path: Path) -> None:
    project = tmp_path / "project"
    (project / ".specify").mkdir(parents=True)

    result = _run_in_project(
        project,
        [
            "artifact",
            "scaffold",
            "--kind",
            "quick-status",
            "--out",
            ".planning/quick/001-demo/STATUS.md",
            "--vars",
            '{"id":"001","slug":"demo","title":"Demo","trigger":"Fix demo"}',
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["status"] == "created"
    assert payload["path"] == ".planning/quick/001-demo/STATUS.md"
    assert (project / ".planning" / "quick" / "001-demo" / "STATUS.md").exists()


def test_artifact_scaffold_rejects_absolute_out_path(tmp_path: Path) -> None:
    project = tmp_path / "project"
    (project / ".specify").mkdir(parents=True)
    absolute_out = project / ".planning" / "quick" / "001-demo" / "STATUS.md"

    result = _run_in_project(
        project,
        [
            "artifact",
            "scaffold",
            "--kind",
            "quick-status",
            "--out",
            str(absolute_out),
            "--vars",
            '{"id":"001","slug":"demo","title":"Demo","trigger":"Fix demo"}',
            "--format",
            "json",
        ],
    )

    assert result.exit_code != 0
    assert "unsafe_path" in result.output
```

- [ ] **Step 2: Run CLI tests and verify missing command**

Run:

```bash
pytest tests/test_artifact_cli.py -q
```

Expected: fails because `artifact` command is not registered.

- [ ] **Step 3: Add Typer app registration**

In `src/specify_cli/__init__.py`, near the existing `result_app`, add:

```python
artifact_app = typer.Typer(
    name="artifact",
    help="Audit and scaffold fixed workflow artifacts",
    add_completion=False,
)
app.add_typer(artifact_app, name="artifact")
```

- [ ] **Step 4: Add CLI command functions**

Add these command functions near the `result_app` command functions:

```python
@artifact_app.command("audit-fixed-cost")
def artifact_audit_fixed_cost_command(
    output_format: str = typer.Option("json", "--format", help="Output format: json"),
):
    """Report fixed artifact scaffold candidates and estimated token savings."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    if output_format.lower() != "json":
        console.print("[red]Error:[/red] only --format json is supported for artifact audit")
        raise typer.Exit(1)
    from specify_cli.artifacts import audit_fixed_cost

    print_json(audit_fixed_cost())


@artifact_app.command("scaffold")
def artifact_scaffold_command(
    kind: str = typer.Option(..., "--kind", help="Artifact scaffold kind"),
    out_path: str = typer.Option(..., "--out", help="Project-relative artifact output path"),
    vars_json: str = typer.Option("{}", "--vars", help="Compact JSON variables for the scaffold"),
    output_format: str = typer.Option("json", "--format", help="Output format: json"),
):
    """Create a fixed workflow artifact scaffold at a safe project-relative path."""
    project_root = Path.cwd()
    _require_spec_kit_plus_project(project_root)
    if output_format.lower() != "json":
        console.print("[red]Error:[/red] only --format json is supported for artifact scaffold")
        raise typer.Exit(1)
    try:
        variables = json.loads(vars_json)
    except json.JSONDecodeError as exc:
        console.print(f"[red]Error:[/red] invalid --vars JSON: {exc}")
        raise typer.Exit(1) from exc
    if not isinstance(variables, dict):
        console.print("[red]Error:[/red] --vars must decode to a JSON object")
        raise typer.Exit(1)

    from specify_cli.artifacts import ArtifactScaffoldError, scaffold_artifact

    try:
        payload = scaffold_artifact(project_root, kind=kind, out_path=out_path, variables=variables)
    except ArtifactScaffoldError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    print_json(payload)
```

- [ ] **Step 5: Run CLI tests**

Run:

```bash
pytest tests/test_artifact_cli.py -q
```

Expected: PASS.

- [ ] **Step 6: Run focused artifact test set**

Run:

```bash
pytest tests/test_artifact_scaffold.py tests/test_artifact_cli.py -q
```

Expected: PASS.

- [ ] **Step 7: Commit CLI wiring**

Run:

```bash
git add src/specify_cli/__init__.py tests/test_artifact_cli.py
git commit -m "feat: expose artifact scaffold cli"
```

## Task 5: Update Workflow Guidance To Use Scaffolds

**Files:**
- Modify: `templates/commands/quick.md`
- Modify: `templates/commands/plan.md`
- Modify: `tests/test_quick_template_guidance.py`
- Modify: `tests/test_plan_research_contract.py`

- [ ] **Step 1: Update quick guidance tests first**

Modify `tests/test_quick_template_guidance.py::test_quick_template_includes_concrete_status_template` into:

```python
def test_quick_template_uses_fixed_status_scaffold() -> None:
    content = read_template("templates/commands/quick.md").lower()

    assert "## status.md scaffold" in content
    assert "artifact scaffold --kind quick-status" in content
    assert "--out \".planning/quick/<id>-<slug>/status.md\"" in content
    assert "--vars" in content
    assert "project-relative" in content
    assert "do not pass an absolute path" in content
    assert "agent_fill_required" in content
    assert "fill_targets" in content
    assert "understanding_confirmed: false" in content
    assert "## current focus" not in content
    assert "task-specific ordered step" not in content
```

Keep the surrounding quick-template tests unchanged unless they explicitly assert the removed inline template body.

- [ ] **Step 2: Update plan guidance tests first**

Add this test to `tests/test_plan_research_contract.py`:

```python
def test_plan_command_scaffolds_plan_contract_with_project_relative_path() -> None:
    content = _read("templates/commands/plan.md").lower()

    assert "artifact scaffold --kind plan-contract" in content
    assert "project-relative" in content
    assert "do not pass absolute `feature_dir`" in content
    assert "convert it to a project-relative output path" in content
    assert "plan-contract.json" in content
```

- [ ] **Step 3: Run guidance tests and verify failures**

Run:

```bash
pytest tests/test_quick_template_guidance.py::test_quick_template_uses_fixed_status_scaffold tests/test_plan_research_contract.py::test_plan_command_scaffolds_plan_contract_with_project_relative_path -q
```

Expected: FAIL because templates still contain the old inline quick template and no plan-contract scaffold command.

- [ ] **Step 4: Replace quick inline status template with scaffold guidance**

In `templates/commands/quick.md`, replace the section starting at `## STATUS.md Template` through the end of that fenced Markdown status template with this shorter section:

```markdown
## STATUS.md Scaffold

Use the fixed artifact scaffold instead of writing the fixed `STATUS.md` skeleton by hand.

Command shape:

```text
{{specify-subcmd:artifact scaffold --kind quick-status --out ".planning/quick/<id>-<slug>/STATUS.md" --vars "<compact-json>" --format json}}
```

`--out` must be project-relative. Do not pass an absolute path. The scaffold is create-only and returns `agent_fill_required` plus `fill_targets`; write semantic quick-task content only at those returned anchors.

The compact JSON variables are:

- `id`: quick-task id
- `slug`: quick-task slug
- `title`: short quick-task title
- `trigger`: verbatim user input

The generated scaffold initializes `understanding_confirmed: false`, `status: gathering`, `execution_model: subagent-mandatory`, `dispatch_shape: one-subagent | parallel-subagents`, and `execution_surface: native-subagents`. It also creates fixed sections for discussion handoff source, current focus, execution intent, understanding checkpoint, execution, validation, summary pointer, and senior consequence analysis. The agent must fill the semantic values through the returned `fill_targets` and keep `STATUS.md` compact.
```

Make sure the outer file fencing remains valid. If the section is inside ordinary Markdown, use a fenced `text` block exactly as above.

- [ ] **Step 5: Add plan-contract scaffold guidance**

In `templates/commands/plan.md`, near the existing instructions that write `plan-contract.json`, add:

```markdown
Before writing semantic planning fields into `plan-contract.json`, create the fixed JSON envelope with:

```text
{{specify-subcmd:artifact scaffold --kind plan-contract --out "<project-relative-feature-dir>/plan-contract.json" --vars "{}" --format json}}
```

`--out` must be project-relative. Prerequisite helpers may emit `FEATURE_DIR` as an absolute path; do not pass absolute `FEATURE_DIR` to `artifact scaffold`. Convert it to a project-relative output path first, then write semantic planning values through the returned JSON Pointer `fill_targets`.
```

- [ ] **Step 6: Run guidance tests**

Run:

```bash
pytest tests/test_quick_template_guidance.py::test_quick_template_uses_fixed_status_scaffold tests/test_plan_research_contract.py::test_plan_command_scaffolds_plan_contract_with_project_relative_path -q
```

Expected: PASS.

- [ ] **Step 7: Run command-surface regression tests affected by template changes**

Run:

```bash
pytest tests/test_quick_template_guidance.py tests/test_plan_research_contract.py tests/test_alignment_templates.py tests/test_command_surface_semantics.py -q
```

Expected: PASS, or failures only where assertions still require the removed inline fixed quick status template. Update those assertions to check scaffold guidance, not the old fixed block.

- [ ] **Step 8: Commit workflow guidance changes**

Run:

```bash
git add templates/commands/quick.md templates/commands/plan.md tests/test_quick_template_guidance.py tests/test_plan_research_contract.py tests/test_alignment_templates.py tests/test_command_surface_semantics.py
git commit -m "docs: route fixed artifacts through scaffold cli"
```

Only include `tests/test_alignment_templates.py` or `tests/test_command_surface_semantics.py` if they were actually changed.

## Task 6: Verify Init Packaging And End-To-End Scaffold Flow

**Files:**
- Modify only if tests reveal drift: `tests/test_packaging_assets.py`, `tests/integrations/test_cli.py`

- [ ] **Step 1: Add init integration assertion for artifact template installation**

If `tests/test_packaging_assets.py::test_install_shared_infra_copies_split_core_pack_template_dirs` already covers `.specify/templates/artifacts/quick-status.md`, skip this step. Otherwise add this test to `tests/integrations/test_cli.py`:

```python
def test_init_installs_artifact_scaffold_templates(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    project = tmp_path / "artifact-scaffold-install"
    result = CliRunner().invoke(
        app,
        ["init", str(project), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"],
        catch_exceptions=False,
    )

    assert result.exit_code == 0, result.output
    assert (project / ".specify" / "templates" / "artifacts" / "quick-status.md").exists()
```

- [ ] **Step 2: Run packaging and init tests**

Run:

```bash
pytest tests/test_packaging_assets.py::test_wheel_force_include_bundles_artifact_scaffold_templates tests/test_packaging_assets.py::test_install_shared_infra_copies_split_core_pack_template_dirs -q
```

If the init integration test was added, also run:

```bash
pytest tests/integrations/test_cli.py::test_init_installs_artifact_scaffold_templates -q
```

Expected: PASS.

- [ ] **Step 3: Run a real CLI scaffold smoke test in a temporary project**

Run:

```bash
tmpdir="$(mktemp -d)"
python -m specify_cli init "$tmpdir/demo" --ai codex --no-git --ignore-agent-tools --script sh
cd "$tmpdir/demo"
python -m specify_cli artifact audit-fixed-cost --format json
python -m specify_cli artifact scaffold --kind quick-status --out ".planning/quick/001-demo/STATUS.md" --vars '{"id":"001","slug":"demo","title":"Demo","trigger":"Fix demo"}' --format json
test -f ".planning/quick/001-demo/STATUS.md"
```

Expected: every command exits 0 and the final `test -f` succeeds. On Windows PowerShell, run the equivalent manually:

```powershell
$tmp = New-Item -ItemType Directory -Path ([System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "artifact-scaffold-demo-" + [guid]::NewGuid()))
python -m specify_cli init "$($tmp.FullName)\demo" --ai codex --no-git --ignore-agent-tools --script ps
Set-Location "$($tmp.FullName)\demo"
python -m specify_cli artifact audit-fixed-cost --format json
python -m specify_cli artifact scaffold --kind quick-status --out ".planning/quick/001-demo/STATUS.md" --vars '{"id":"001","slug":"demo","title":"Demo","trigger":"Fix demo"}' --format json
Test-Path ".planning/quick/001-demo/STATUS.md"
```

- [ ] **Step 4: Run full focused verification**

Run:

```bash
pytest tests/test_artifact_scaffold.py tests/test_artifact_cli.py tests/test_packaging_assets.py tests/test_quick_template_guidance.py tests/test_plan_research_contract.py tests/test_alignment_templates.py tests/test_command_surface_semantics.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit verification-only fixes if any were needed**

If Step 4 required test or packaging fixes, commit them:

```bash
git add tests src templates pyproject.toml
git commit -m "test: cover artifact scaffold rollout"
```

If no files changed, do not create an empty commit.

## Task 7: Final Review And Cost Evidence

**Files:**
- Modify: `docs/superpowers/specs/2026-07-03-sp-fixed-artifact-scaffold-design.md` only if measured evidence should be recorded there
- Create or modify: `docs/workflow-quality/` evaluation record only if the team wants a formal quality record for this rollout

- [ ] **Step 1: Capture audit output**

Run:

```bash
python -m specify_cli artifact audit-fixed-cost --format json
```

Expected: JSON contains `quick-status` and `plan-contract`, non-zero `estimated_token_savings`, `fill_targets`, allowed output paths, and low quality risk.

- [ ] **Step 2: Inspect final diff**

Run:

```bash
git diff --stat HEAD
git diff HEAD -- src/specify_cli/artifacts src/specify_cli/__init__.py templates/artifacts templates/commands/quick.md templates/commands/plan.md pyproject.toml tests/test_artifact_scaffold.py tests/test_artifact_cli.py tests/test_packaging_assets.py tests/test_quick_template_guidance.py tests/test_plan_research_contract.py
```

Expected: changes are limited to artifact scaffold implementation, first rollout templates, workflow guidance, package data, and tests.

- [ ] **Step 3: Run final targeted tests**

Run:

```bash
pytest tests/test_artifact_scaffold.py tests/test_artifact_cli.py tests/test_packaging_assets.py tests/test_quick_template_guidance.py tests/test_plan_research_contract.py tests/test_alignment_templates.py tests/test_command_surface_semantics.py -q
```

Expected: PASS.

- [ ] **Step 4: Commit any remaining implementation changes**

If `git status --short` shows staged implementation changes, commit them:

```bash
git add src/specify_cli/artifacts src/specify_cli/__init__.py templates/artifacts templates/commands/quick.md templates/commands/plan.md pyproject.toml tests/test_artifact_scaffold.py tests/test_artifact_cli.py tests/test_packaging_assets.py tests/test_quick_template_guidance.py tests/test_plan_research_contract.py tests/test_alignment_templates.py tests/test_command_surface_semantics.py
git commit -m "feat: scaffold fixed workflow artifacts"
```

If all prior task commits already captured the work, skip this step.

- [ ] **Step 5: Write final implementation summary**

Use this exact summary shape in the final response:

```text
Implemented fixed artifact scaffolding for the first rollout.

Changed:
- Added registry-driven artifact audit and create-only scaffold writer.
- Added path-safe `specify artifact audit-fixed-cost` and `specify artifact scaffold`.
- Added `quick-status` and `plan-contract` scaffold kinds.
- Updated `sp-quick` and `sp-plan` guidance to use project-relative scaffold outputs.

Verification:
- pytest tests/test_artifact_scaffold.py tests/test_artifact_cli.py tests/test_packaging_assets.py tests/test_quick_template_guidance.py tests/test_plan_research_contract.py tests/test_alignment_templates.py tests/test_command_surface_semantics.py -q

Cost evidence:
- quick-status estimated savings: 1900 tokens
- plan-contract estimated savings: 525 tokens
```

If Task 1's registry estimates change during implementation, use the actual numeric values from Step 1's audit JSON instead of the example values above.

## Self-Review

Spec coverage:

- Fixed content only: Tasks 1-3 implement registry and scaffolds that generate only fixed skeletons and safe defaults.
- Token savings assessment: Tasks 1 and 7 expose audit output and required cost evidence.
- Path safety: Task 2 adds project-relative enforcement, allowlist checks, traversal rejection, and symlink escape tests.
- Create-only overwrite protection: Task 2 rejects existing targets and Task 4 surfaces errors through CLI.
- Deterministic registry: Task 1 creates the registry with prompt refs, output patterns, anchors, consumers, package targets, and risk metadata.
- Fill targets: Tasks 1-3 return anchors and JSON Pointers.
- Approval-source proof: Task 2 rejects unsafe readiness and approval values in the first rollout.
- Packaging and generated-project availability: Tasks 3 and 6 cover force-includes and `.specify/templates/artifacts`.
- Workflow behavior: Task 5 updates `sp-quick` and `sp-plan` only.

Incomplete-marker scan:

- No incomplete marker strings or incomplete task descriptions remain in this plan.
- The registry field name `semantic_placeholders` from the spec is intentionally avoided in implementation code for this rollout; implementation uses `agent_fill_required` and `fill_targets`.

Type consistency:

- The registry uses `ArtifactKind`, `ARTIFACT_REGISTRY`, `get_artifact_kind`, `validate_registry`, and `audit_fixed_cost`.
- The writer exposes `ArtifactScaffoldError` and `scaffold_artifact`.
- CLI commands call `audit_fixed_cost` and `scaffold_artifact`.
- Tests refer to the same function and field names used in implementation tasks.
