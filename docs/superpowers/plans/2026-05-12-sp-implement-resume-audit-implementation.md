# sp-implement Resume Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `sp-implement` resume after crashes audit terminal-looking state before trusting `[X]` tasks or `status: resolved`.

**Architecture:** Add a small resume-audit runtime module that reads `tasks.md`, `implement-tracker.md`, and `worker-results/` evidence, then exposes the result through `specify implement resume-audit` and `validate-session-state`. Keep the audit intentionally conservative and stack-agnostic: it does not infer full reachability automatically, but it rejects terminal state without validation, worker-result, open-gap, and consumer-evidence receipts where those are required by packets/results. Update templates and packet/result contracts so future work carries the evidence needed to avoid “created but not wired” false completion.

**Tech Stack:** Python dataclasses/Typer/pytest for CLI runtime; Markdown templates under `templates/`; existing `WorkerTaskPacket` and `WorkerTaskResult` JSON contracts.

---

## File Structure

- Create `src/specify_cli/implement_audit.py`: pure audit logic for feature directories. It parses task checkboxes, tracker state, worker-result JSON, open gaps, and evidence fields, returning a structured payload.
- Modify `src/specify_cli/__init__.py`: add `specify implement resume-audit` command and call the audit from `implement closeout`.
- Modify `src/specify_cli/hooks/events.py`, `src/specify_cli/hooks/engine.py`, and `src/specify_cli/hooks/session_state.py`: register/use a workflow resume-audit event and surface terminal-audit findings through `validate-session-state`.
- Modify `src/specify_cli/execution/packet_schema.py`, `src/specify_cli/execution/result_schema.py`, and `src/specify_cli/execution/result_validator.py`: add optional acceptance/consumer/manual evidence fields and validate populated evidence requirements.
- Modify `templates/commands/implement.md`, `templates/command-partials/implement/shell.md`, `templates/worker-prompts/implementer.md`, and `src/specify_cli/integrations/base.py`: generated workflow guidance must run resume audit before trusting terminal state and ask workers for consumer evidence.
- Tests:
  - `tests/execution/test_implement_resume_audit.py`
  - `tests/execution/test_result_validator.py`
  - `tests/contract/test_hook_cli_surface.py`
  - `tests/test_alignment_templates.py`
  - targeted integration template tests if existing assertions require generated Codex/Claude guidance.

## Task 1: Add Failing Resume Audit Tests

**Files:**
- Create: `tests/execution/test_implement_resume_audit.py`

- [ ] **Step 1: Add tests for false terminal state**

Create `tests/execution/test_implement_resume_audit.py`:

```python
from pathlib import Path

from specify_cli.implement_audit import audit_implement_resume


def _write_basic_feature(feature_dir: Path, *, tracker_status: str = "resolved") -> None:
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State",
                "",
                "## Next Command",
                "",
                "- `/sp.implement`",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "implement-tracker.md").write_text(
        "\n".join(
            [
                "---",
                f"status: {tracker_status}",
                "feature: 001-demo",
                "resume_decision: resolved",
                "---",
                "",
                "## Current Focus",
                "current_batch: final validation",
                "goal: finish implementation",
                "next_action: report completion",
                "",
                "## Execution State",
                "completed_tasks:",
                "  - T001",
                "in_progress_tasks:",
                "failed_tasks:",
                "retry_attempts: 0",
                "",
                "## Open Gaps",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "\n".join(
            [
                "# Tasks",
                "",
                "- [X] T001 [US1] Create provider form in apps/web/src/features/providers/forms/ClaudeForm.tsx",
            ]
        ),
        encoding="utf-8",
    )


def test_resolved_tracker_with_checked_task_but_no_worker_result_requires_audit_recovery(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_basic_feature(feature_dir)

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert payload["resume_classification"] == "terminal-audit-required"
    assert payload["trusted_terminal_state"] is False
    assert payload["recommended_tracker_status"] == "validating"
    assert any("missing worker result" in finding["missing_evidence"] for finding in payload["task_findings"])


def test_checked_component_task_with_result_but_no_consumer_evidence_is_gap(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_basic_feature(feature_dir)
    result_dir = feature_dir / "worker-results"
    result_dir.mkdir()
    (result_dir / "T001.json").write_text(
        """
{
  "task_id": "T001",
  "status": "success",
  "changed_files": ["apps/web/src/features/providers/forms/ClaudeForm.tsx"],
  "validation_results": [{"command": "npm test -- providers", "status": "passed", "output": "PASS"}],
  "summary": "Created ClaudeForm component",
  "rule_acknowledgement": {
    "required_references_read": true,
    "forbidden_drift_respected": true,
    "context_bundle_read": true,
    "paths_read": []
  }
}
""".strip(),
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert payload["recommended_tracker_status"] == "validating"
    assert any("missing consumer evidence" in finding["missing_evidence"] for finding in payload["task_findings"])


def test_resolved_tracker_with_worker_result_and_consumer_evidence_passes(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_basic_feature(feature_dir)
    result_dir = feature_dir / "worker-results"
    result_dir.mkdir()
    (result_dir / "T001.json").write_text(
        """
{
  "task_id": "T001",
  "status": "success",
  "changed_files": [
    "apps/web/src/features/providers/forms/ClaudeForm.tsx",
    "apps/web/src/features/providers/DeviceProviderFormModal.tsx"
  ],
  "validation_results": [{"command": "npm test -- providers", "status": "passed", "output": "PASS"}],
  "consumer_evidence": [
    {
      "surface": "DeviceProviderFormModal",
      "evidence": "FormFactory renders ClaudeForm for cliToolType=claude",
      "method": "focused test"
    }
  ],
  "summary": "Created and wired ClaudeForm component",
  "rule_acknowledgement": {
    "required_references_read": true,
    "forbidden_drift_respected": true,
    "context_bundle_read": true,
    "paths_read": []
  }
}
""".strip(),
        encoding="utf-8",
    )

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "pass"
    assert payload["trusted_terminal_state"] is True
    assert payload["recommended_tracker_status"] == "resolved"
```

- [ ] **Step 2: Run failing tests**

Run:

```powershell
uv run --extra test pytest tests/execution/test_implement_resume_audit.py -q
```

Expected: fails with `ModuleNotFoundError: No module named 'specify_cli.implement_audit'`.

## Task 2: Implement Pure Resume Audit Logic

**Files:**
- Create: `src/specify_cli/implement_audit.py`
- Modify if needed: `src/specify_cli/execution/result_schema.py`

- [ ] **Step 1: Create audit module**

Add `src/specify_cli/implement_audit.py`:

```python
"""Resume-audit helpers for sp-implement terminal-state validation."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from specify_cli.hooks.checkpoint_serializers import serialize_implement_tracker


TASK_RE = re.compile(r"(?m)^\s*-\s\[(?P<checked>[ xX])\]\s+(?P<task_id>T\d+)\b(?P<body>.*)$")
CONSUMER_KEYWORDS = (
    "component",
    "form",
    "page",
    "route",
    "router",
    "provider",
    "factory",
    "registry",
    "panel",
    "modal",
    "endpoint",
    "api",
    "client",
    "config",
    "schema",
    "test",
)


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _parse_tasks(tasks_path: Path) -> list[dict[str, Any]]:
    text = _read_text(tasks_path)
    tasks: list[dict[str, Any]] = []
    for match in TASK_RE.finditer(text):
        body = match.group("body").strip()
        tasks.append(
            {
                "task_id": match.group("task_id"),
                "checked": match.group("checked").lower() == "x",
                "body": body,
                "consumer_facing": _looks_consumer_facing(body),
            }
        )
    return tasks


def _looks_consumer_facing(task_body: str) -> bool:
    lowered = task_body.lower()
    return any(keyword in lowered for keyword in CONSUMER_KEYWORDS)


def _load_worker_result(feature_dir: Path, task_id: str) -> dict[str, Any] | None:
    for candidate in (
        feature_dir / "worker-results" / f"{task_id}.json",
        feature_dir / "worker-results" / f"{task_id.lower()}.json",
    ):
        if not candidate.exists():
            continue
        try:
            payload = json.loads(candidate.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"task_id": task_id, "status": "invalid-json", "path": str(candidate)}
        payload["path"] = str(candidate)
        return payload
    return None


def _result_has_passed_validation(result: dict[str, Any]) -> bool:
    validations = result.get("validation_results") or result.get("validationResults") or []
    if not isinstance(validations, list) or not validations:
        return False
    return all(str(item.get("status", "")).lower() == "passed" for item in validations if isinstance(item, dict))


def _result_has_consumer_evidence(result: dict[str, Any]) -> bool:
    evidence = result.get("consumer_evidence") or result.get("consumerEvidence") or []
    return isinstance(evidence, list) and any(bool(item) for item in evidence)


def _tracker_has_open_gaps(feature_dir: Path) -> bool:
    text = _read_text(feature_dir / "implement-tracker.md")
    marker = "## Open Gaps"
    if marker not in text:
        return False
    body = text.split(marker, 1)[1]
    next_section = re.split(r"(?m)^##\s+", body, maxsplit=1)[0]
    meaningful = [
        line.strip()
        for line in next_section.splitlines()
        if line.strip() and line.strip() not in {"- none", "none", "[]"}
    ]
    return any(line.startswith("-") or line.startswith("type:") for line in meaningful)


def audit_implement_resume(project_root: Path, feature_dir: Path) -> dict[str, Any]:
    """Return a conservative resume audit payload for an implement feature dir."""

    resolved_feature_dir = feature_dir if feature_dir.is_absolute() else (project_root / feature_dir).resolve()
    tracker_path = resolved_feature_dir / "implement-tracker.md"
    tasks_path = resolved_feature_dir / "tasks.md"

    if not tracker_path.exists():
        return _payload(
            status="conflict",
            feature_dir=resolved_feature_dir,
            classification="state-conflict",
            trusted=False,
            recommended_status="blocked",
            next_action="Recreate or recover implement-tracker.md before resuming implementation.",
            task_findings=[],
            open_gaps=["implement-tracker.md is missing"],
        )

    tracker = serialize_implement_tracker(tracker_path)
    tracker_status = str(tracker.get("status") or "").strip().lower()
    tasks = _parse_tasks(tasks_path)
    checked_tasks = [task for task in tasks if task["checked"]]
    all_checked = bool(tasks) and len(checked_tasks) == len(tasks)
    terminal = tracker_status == "resolved" or all_checked
    classification = "terminal-audit-required" if terminal else "clean-active"

    task_findings: list[dict[str, Any]] = []
    evidence_gaps: list[str] = []
    for task in checked_tasks:
        missing: list[str] = []
        result = _load_worker_result(resolved_feature_dir, str(task["task_id"]))
        if result is None:
            missing.append("missing worker result")
        elif str(result.get("status", "")).lower() not in {"success", "done", "done_with_concerns"}:
            missing.append("worker result is not successful")
        else:
            if not _result_has_passed_validation(result):
                missing.append("missing passed validation evidence")
            if task["consumer_facing"] and not _result_has_consumer_evidence(result):
                missing.append("missing consumer evidence")

        if missing:
            evidence_gaps.append(f"{task['task_id']}: {', '.join(missing)}")
        task_findings.append(
            {
                "task_id": task["task_id"],
                "checked": task["checked"],
                "consumer_facing": task["consumer_facing"],
                "result_path": result.get("path", "") if isinstance(result, dict) else "",
                "missing_evidence": "; ".join(missing),
            }
        )

    if _tracker_has_open_gaps(resolved_feature_dir):
        evidence_gaps.append("implement-tracker.md has unresolved open_gaps")

    audit_passed = terminal and not evidence_gaps
    if audit_passed:
        return _payload(
            status="pass",
            feature_dir=resolved_feature_dir,
            classification=classification,
            trusted=True,
            recommended_status="resolved",
            next_action="Terminal implement state has closeout-quality evidence.",
            task_findings=task_findings,
            open_gaps=[],
        )

    if terminal:
        return _payload(
            status="fail",
            feature_dir=resolved_feature_dir,
            classification=classification,
            trusted=False,
            recommended_status="validating",
            next_action="Resume sp-implement in validation/recovery mode and close the evidence gaps before reporting completion.",
            task_findings=task_findings,
            open_gaps=evidence_gaps,
        )

    return _payload(
        status="pass",
        feature_dir=resolved_feature_dir,
        classification=classification,
        trusted=False,
        recommended_status=tracker_status or "executing",
        next_action=str(tracker.get("next_action") or "Resume the recorded implementation batch."),
        task_findings=task_findings,
        open_gaps=evidence_gaps,
    )


def _payload(
    *,
    status: str,
    feature_dir: Path,
    classification: str,
    trusted: bool,
    recommended_status: str,
    next_action: str,
    task_findings: list[dict[str, Any]],
    open_gaps: list[str],
) -> dict[str, Any]:
    return {
        "status": status,
        "feature_dir": str(feature_dir),
        "resume_classification": classification,
        "trusted_terminal_state": trusted,
        "task_findings": task_findings,
        "join_point_findings": [],
        "open_gaps": open_gaps,
        "recommended_tracker_status": recommended_status,
        "recommended_next_action": next_action,
    }
```

- [ ] **Step 2: Run audit tests**

Run:

```powershell
uv run --extra test pytest tests/execution/test_implement_resume_audit.py -q
```

Expected: all tests pass.

## Task 3: Expose Audit Through CLI and Session Hook

**Files:**
- Modify: `src/specify_cli/__init__.py`
- Modify: `src/specify_cli/hooks/events.py`
- Modify: `src/specify_cli/hooks/engine.py`
- Modify: `src/specify_cli/hooks/session_state.py`
- Test: `tests/contract/test_hook_cli_surface.py`

- [ ] **Step 1: Add failing CLI/hook tests**

Append to `tests/contract/test_hook_cli_surface.py`:

```python
def test_implement_resume_audit_cli_blocks_false_resolved_state(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n\n## Next Command\n\n- `/sp.implement`\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text("- [X] T001 [US1] Create provider form in apps/web/src/Form.tsx\n", encoding="utf-8")
    (feature_dir / "implement-tracker.md").write_text(
        "\n".join(
            [
                "---",
                "status: resolved",
                "feature: 001-demo",
                "resume_decision: resolved",
                "---",
                "",
                "## Current Focus",
                "current_batch: final",
                "next_action: report completion",
                "",
                "## Open Gaps",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["implement", "resume-audit", "--feature-dir", str(feature_dir), "--format", "json"],
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["status"] == "fail"
    assert payload["recommended_tracker_status"] == "validating"


def test_validate_session_state_surfaces_terminal_audit_required(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n\n## Next Command\n\n- `/sp.implement`\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text("- [X] T001 [US1] Create provider form in apps/web/src/Form.tsx\n", encoding="utf-8")
    (feature_dir / "implement-tracker.md").write_text(
        "\n".join(
            [
                "---",
                "status: resolved",
                "feature: 001-demo",
                "resume_decision: resolved",
                "---",
                "",
                "## Current Focus",
                "current_batch: final",
                "next_action: report completion",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["hook", "validate-session-state", "--command", "implement", "--feature-dir", str(feature_dir)],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["status"] == "warn"
    audit = payload["data"]["resume_audit"]
    assert audit["resume_classification"] == "terminal-audit-required"
    assert audit["trusted_terminal_state"] is False
```

- [ ] **Step 2: Run failing tests**

Run:

```powershell
uv run --extra test pytest tests/contract/test_hook_cli_surface.py::test_implement_resume_audit_cli_blocks_false_resolved_state tests/contract/test_hook_cli_surface.py::test_validate_session_state_surfaces_terminal_audit_required -q
```

Expected: first test fails because CLI command does not exist; second fails because hook does not include `resume_audit`.

- [ ] **Step 3: Implement CLI and hook integration**

Add `@implement_app.command("resume-audit")` next to `implement_closeout` in `src/specify_cli/__init__.py`. Import and call `audit_implement_resume`; print JSON for `--format json`; exit with code 1 when status is `fail` or `conflict`.

In `src/specify_cli/hooks/session_state.py`, after serializing tracker for implement, call `audit_implement_resume(project_root, feature_dir)` when tracker status is `resolved` or audit classification is terminal. Add it to `data["resume_audit"]`; add a warning when audit status is not `pass`.

Do not create a separate hook event unless the implementation needs it after this step. Keep the first version simple by mirroring the audit inside the existing session-state hook.

- [ ] **Step 4: Run tests**

Run:

```powershell
uv run --extra test pytest tests/contract/test_hook_cli_surface.py::test_implement_resume_audit_cli_blocks_false_resolved_state tests/contract/test_hook_cli_surface.py::test_validate_session_state_surfaces_terminal_audit_required -q
```

Expected: both pass.

## Task 4: Add Packet/Result Evidence Fields and Validation

**Files:**
- Modify: `src/specify_cli/execution/packet_schema.py`
- Modify: `src/specify_cli/execution/result_schema.py`
- Modify: `src/specify_cli/execution/result_validator.py`
- Modify: `tests/execution/test_result_validator.py`

- [ ] **Step 1: Add failing validator test**

Append to `tests/execution/test_result_validator.py`:

```python
def test_validate_worker_task_result_rejects_missing_required_consumer_evidence(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.consumer_surfaces = ["DeviceProviderPage renders ClaudeForm"]
    sample_packet.required_evidence = ["consumer_evidence"]
    result = WorkerTaskResult(
        task_id="T017",
        status="success",
        changed_files=["src/services/auth_service.py"],
        validation_results=[
            ValidationResult(
                command="pytest tests/unit/test_auth_service.py -q",
                status="passed",
                output="1 passed",
            )
        ],
        summary="Implemented auth flow",
        rule_acknowledgement=RuleAcknowledgement(
            required_references_read=True,
            forbidden_drift_respected=True,
            context_bundle_read=True,
            paths_read=[
                ".specify/project-cognition/status.json",
                ".specify/project-cognition/slices/change.json",
            ],
        ),
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "consumer evidence" in exc.value.message
```

- [ ] **Step 2: Run failing test**

Run:

```powershell
uv run --extra test pytest tests/execution/test_result_validator.py::test_validate_worker_task_result_rejects_missing_required_consumer_evidence -q
```

Expected: fails because packet/result fields are missing.

- [ ] **Step 3: Add optional dataclass fields**

In `WorkerTaskPacket`, add:

```python
acceptance_criteria: list[str] = field(default_factory=list)
consumer_surfaces: list[str] = field(default_factory=list)
required_evidence: list[str] = field(default_factory=list)
```

In `WorkerTaskResult`, add:

```python
acceptance_evidence: list[dict[str, str]] = field(default_factory=list)
consumer_evidence: list[dict[str, str]] = field(default_factory=list)
manual_evidence: list[dict[str, str]] = field(default_factory=list)
```

Normalize these fields in `worker_task_result_from_json` the same way `paths_read` is normalized: keep only dict items and stringify keys/values.

- [ ] **Step 4: Validate populated evidence requirements**

In `validate_worker_task_result`, after validation gate checks for success:

```python
required = {item.strip().lower() for item in packet.required_evidence}
if packet.consumer_surfaces or "consumer_evidence" in required:
    if not result.consumer_evidence:
        raise PacketValidationError("DP3", "worker result is missing consumer evidence")
if "acceptance_evidence" in required and not result.acceptance_evidence:
    raise PacketValidationError("DP3", "worker result is missing acceptance evidence")
if "manual_evidence" in required and not result.manual_evidence:
    raise PacketValidationError("DP3", "worker result is missing manual evidence")
```

- [ ] **Step 5: Run tests**

Run:

```powershell
uv run --extra test pytest tests/execution/test_result_validator.py tests/execution/test_result_normalizer.py -q
```

Expected: pass.

## Task 5: Harden Templates and Alignment Tests

**Files:**
- Modify: `templates/commands/implement.md`
- Modify: `templates/command-partials/implement/shell.md`
- Modify: `templates/worker-prompts/implementer.md`
- Modify: `src/specify_cli/integrations/base.py`
- Modify: `tests/test_alignment_templates.py`
- Modify targeted integration tests if they assert generated implement guidance.

- [ ] **Step 1: Add failing template assertions**

Add assertions near existing implement template tests in `tests/test_alignment_templates.py`:

```python
def test_implement_template_requires_resume_audit_before_trusting_terminal_state():
    content = _read("templates/commands/implement.md")
    lowered = content.lower()
    assert "resume audit" in lowered
    assert "terminal-audit-required" in lowered
    assert "checked tasks as claims" in lowered
    assert "consumer evidence" in lowered
    assert "do not preserve `resolved`" in lowered
```

Add worker prompt assertion:

```python
def test_implementer_prompt_requires_consumer_evidence_for_created_surfaces():
    content = _read("templates/worker-prompts/implementer.md").lower()
    assert "consumer evidence" in content
    assert "created but not wired" in content
```

- [ ] **Step 2: Run failing template tests**

Run:

```powershell
uv run --extra test pytest tests/test_alignment_templates.py::test_implement_template_requires_resume_audit_before_trusting_terminal_state tests/test_alignment_templates.py::test_implementer_prompt_requires_consumer_evidence_for_created_surfaces -q
```

Expected: fail until templates are updated.

- [ ] **Step 3: Update templates**

In `templates/commands/implement.md`, add a “Resume Audit Gate” subsection before batch selection:

```markdown
### Resume Audit Gate

- On every resume, treat checked tasks as claims that need evidence, not evidence themselves.
- If `implement-tracker.md` is `resolved`, all tasks appear checked, or the previous session exit is unknown, run `{{specify-subcmd:implement resume-audit --feature-dir "$FEATURE_DIR" --format json}}` before final reporting or new closeout.
- Treat `terminal-audit-required` as validation/recovery work, not completion.
- Require consumer evidence for tasks that create UI components, routes, providers, registries, factories, configs, tests, API handlers, or other reusable surfaces.
- Do not preserve `resolved` when the audit finds missing wiring, missing validation evidence, stale subagent handoff, unresolved `open_gaps`, or unexecuted planned validation tasks.
```

In `templates/command-partials/implement/shell.md`, add one concise bullet under Process:

```markdown
- On resume, audit terminal-looking tracker/task state before trusting completion; checked tasks are claims until validation, handoff, join point, and consumer evidence prove them.
```

In `templates/worker-prompts/implementer.md`, add:

```markdown
- For any task that creates a reusable surface such as a UI component, route, provider, registry entry, factory branch, config field, API handler, or test file, return consumer evidence showing where that surface is imported, registered, rendered, executed, or included. A created but not wired file is not complete.
```

In `src/specify_cli/integrations/base.py`, update the generated implement skill/addendum text to mention `resume-audit`, checked tasks as claims, and consumer evidence. Search for the existing implement tracker guidance around `FEATURE_DIR/implement-tracker.md`.

- [ ] **Step 4: Run template/integration tests**

Run:

```powershell
uv run --extra test pytest tests/test_alignment_templates.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py -q
```

Expected: pass or reveal exact generated guidance assertions to update.

## Task 6: Wire Closeout to Audit and Run Focused Regression

**Files:**
- Modify: `src/specify_cli/__init__.py`
- Test: `tests/contract/test_hook_cli_surface.py`

- [ ] **Step 1: Update `implement closeout`**

In `implement_closeout`, call `audit_implement_resume` after `workflow.session_state.validate`. If audit status is `fail` or `conflict`, return JSON payload:

```python
{"status": "blocked", "resume_audit": audit_payload, ...}
```

and exit 1. For text mode, print the recommended next action and evidence gaps.

- [ ] **Step 2: Add closeout regression test**

Add to `tests/contract/test_hook_cli_surface.py`:

```python
def test_implement_closeout_blocks_false_resolved_state(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    (feature_dir / "workflow-state.md").write_text("# Workflow State\n\n## Next Command\n\n- `/sp.implement`\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text("- [X] T001 [US1] Create provider form in apps/web/src/Form.tsx\n", encoding="utf-8")
    (feature_dir / "implement-tracker.md").write_text(
        "---\nstatus: resolved\nfeature: 001-demo\nresume_decision: resolved\n---\n\n## Current Focus\nnext_action: report completion\n",
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        ["implement", "closeout", "--feature-dir", str(feature_dir), "--format", "json"],
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["status"] == "blocked"
    assert payload["resume_audit"]["trusted_terminal_state"] is False
```

- [ ] **Step 3: Run focused regression**

Run:

```powershell
uv run --extra test pytest tests/execution/test_implement_resume_audit.py tests/execution/test_result_validator.py tests/contract/test_hook_cli_surface.py::test_implement_resume_audit_cli_blocks_false_resolved_state tests/contract/test_hook_cli_surface.py::test_validate_session_state_surfaces_terminal_audit_required tests/contract/test_hook_cli_surface.py::test_implement_closeout_blocks_false_resolved_state tests/test_alignment_templates.py::test_implement_template_requires_resume_audit_before_trusting_terminal_state tests/test_alignment_templates.py::test_implementer_prompt_requires_consumer_evidence_for_created_surfaces -q
```

Expected: all pass.

## Task 7: Final Verification and Commit

**Files:**
- Review all changed files.

- [ ] **Step 1: Run broader relevant tests**

Run:

```powershell
uv run --extra test pytest tests/execution tests/contract/test_hook_cli_surface.py tests/test_alignment_templates.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py -q
```

Expected: pass. If unrelated failures appear from pre-existing worktree changes, capture the failing test names and evidence before narrowing.

- [ ] **Step 2: Inspect diff**

Run:

```powershell
git diff -- src/specify_cli/implement_audit.py src/specify_cli/__init__.py src/specify_cli/hooks/session_state.py src/specify_cli/execution/packet_schema.py src/specify_cli/execution/result_schema.py src/specify_cli/execution/result_validator.py templates/commands/implement.md templates/command-partials/implement/shell.md templates/worker-prompts/implementer.md src/specify_cli/integrations/base.py tests/execution/test_implement_resume_audit.py tests/execution/test_result_validator.py tests/contract/test_hook_cli_surface.py tests/test_alignment_templates.py
```

Expected: only resume-audit/evidence-contract changes.

- [ ] **Step 3: Commit only files from this plan**

Run:

```powershell
git add -- src/specify_cli/implement_audit.py src/specify_cli/__init__.py src/specify_cli/hooks/session_state.py src/specify_cli/execution/packet_schema.py src/specify_cli/execution/result_schema.py src/specify_cli/execution/result_validator.py templates/commands/implement.md templates/command-partials/implement/shell.md templates/worker-prompts/implementer.md src/specify_cli/integrations/base.py tests/execution/test_implement_resume_audit.py tests/execution/test_result_validator.py tests/contract/test_hook_cli_surface.py tests/test_alignment_templates.py docs/superpowers/plans/2026-05-12-sp-implement-resume-audit-implementation.md
git commit -m "fix: audit sp-implement resume completion evidence"
```

Expected: commit succeeds without staging unrelated existing worktree changes.

## Self-Review Notes

- Spec coverage: resume audit gate, evidence model, hook/CLI behavior, tracker/closeout semantics, packet/result evidence, templates, and tests are covered.
- Scope: one runtime helper plus existing CLI/hooks/templates. No task database rewrite.
- TDD: each implementation task starts with a failing test or assertion.
