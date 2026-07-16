# Superpowers 6 SDD Artifact Review Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add durable task brief, review package, task review, ledger, branch review, and UI fidelity review contracts to the existing `sp-plan -> sp-tasks -> sp-implement` workflow.

**Architecture:** Extend the current `.specify` feature-dir implementation model instead of introducing a new executor or global scratch tree. The runtime additions live beside the existing packet/result and embedded review helpers, while command templates and passive skills teach agents to use the new artifact path by default.

**Tech Stack:** Python dataclasses and JSON helpers in `src/specify_cli`, Markdown command and prompt templates under `templates/`, Pytest for runtime and packaging coverage.

---

## Scope Check

This is one coherent workflow contract change. It spans runtime schema, audit helpers, generated templates, worker prompts, and packaging tests, but all pieces serve the same packetized implementation review path and can be verified together.

Out of scope for this plan:

- replacing `FEATURE_DIR`, `.specify`, `WorkerTaskPacket`, or `WorkerTaskResult`
- deleting legacy `spec-reviewer.md` or `code-quality-reviewer.md`
- adding a new public `sp-review` command
- requiring visual diff tooling for all UI changes

## File Structure

Runtime review contract:

- Modify `src/specify_cli/execution/implementation_review.py`: add task brief, review package, task review, ledger, and branch review path helpers plus schema validation helpers.
- Modify `tests/execution/test_implementation_review.py`: cover the new helper paths, accepted review rules, concerns disposition, ledger round trip, and branch review path.

Packet and result contract:

- Modify `src/specify_cli/execution/packet_schema.py`: add `PacketInterfaces` and `UiFidelityRequirements`, plus new optional packet fields.
- Modify `src/specify_cli/execution/packet_compiler.py`: compile new fields from `plan.md` and enriched `tasks.md` task detail tables.
- Modify `src/specify_cli/execution/packet_validator.py`: reject malformed UI fidelity levels and controller check fields when present.
- Modify `src/specify_cli/execution/result_schema.py`: add `ui_fidelity_evidence`.
- Modify `src/specify_cli/execution/result_normalizer.py`: normalize `ui_fidelity_evidence` and camel-case aliases.
- Modify `src/specify_cli/execution/result_validator.py`: require UI fidelity evidence when packet fields ask for it.
- Modify `tests/execution/test_packet_schema.py`, `tests/execution/test_packet_compiler.py`, `tests/execution/test_packet_validator.py`, `tests/execution/test_result_normalizer.py`, and `tests/execution/test_result_validator.py`.

Resume and closeout:

- Modify `src/specify_cli/implement_audit.py`: treat packetized checked tasks without accepted task reviews as incomplete, and require branch review before terminal trust.
- Modify `src/specify_cli/implementation_summary.py`: include review artifact paths, ledger state, human-needed checks, and unresolved review gaps.
- Modify `tests/execution/test_implement_resume_audit.py` and `tests/contract/test_hook_cli_surface.py`.

Hook and artifact validation:

- Modify `src/specify_cli/hooks/artifact_validation.py`: add conservative implement review artifact validation for packetized terminal state.
- Modify `src/specify_cli/hooks/state_validation.py`: add review artifact paths to implement state validation data where available.
- Modify `tests/contract/test_hook_cli_surface.py`.

Generated workflow templates:

- Modify `templates/commands/plan.md`, `templates/commands/tasks.md`, and `templates/commands/implement.md`.
- Modify `templates/plan-contract-template.json`, `templates/tasks-template.md`, and `templates/workflow-state-template.md`.
- Modify `templates/worker-prompts/implementer.md`.
- Create `templates/worker-prompts/task-reviewer.md`.
- Modify `templates/worker-prompts/spec-reviewer.md` and `templates/worker-prompts/code-quality-reviewer.md` only to mark them as legacy compatibility prompts.
- Modify `templates/passive-skills/subagent-driven-development/SKILL.md` and `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`.

Packaging and alignment:

- Modify `tests/test_alignment_templates.py`.
- Modify `tests/integrations/test_cli.py`.
- Modify `tests/test_packaging_assets.py`.
- Modify integration renderer tests under `tests/integrations/` when rendered command output snapshots assert the old two-reviewer wording.

## Task 1: Add Task Review Artifact Helpers

**Files:**

- Modify: `src/specify_cli/execution/implementation_review.py`
- Modify: `tests/execution/test_implementation_review.py`

- [ ] **Step 1: Write failing path and ledger tests**

Append these tests to `tests/execution/test_implementation_review.py`:

```python
from specify_cli.execution.implementation_review import (
    AcceptedResidualRisk,
    ControllerCheck,
    FollowUpWork,
    TaskLedgerEntry,
    TaskReviewFinding,
    TaskReviewRecord,
    branch_review_path,
    load_task_ledger,
    task_brief_path,
    task_review_acceptance_errors,
    task_review_is_accepted,
    task_review_path,
    review_package_path,
    write_task_ledger,
    write_task_review_record,
)


def test_task_review_artifact_paths_live_under_implementation_review(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"

    assert task_brief_path(feature_dir, "T001") == feature_dir / "implementation-review" / "task-briefs" / "T001.md"
    assert review_package_path(feature_dir, "T001") == feature_dir / "implementation-review" / "review-packages" / "T001.md"
    assert task_review_path(feature_dir, "T001") == feature_dir / "implementation-review" / "task-reviews" / "T001.json"
    assert branch_review_path(feature_dir) == feature_dir / "implementation-review" / "branch-review.md"


def test_task_review_accepts_passed_spec_and_quality(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    record = TaskReviewRecord(
        task_id="T001",
        spec_verdict="pass",
        quality_verdict="pass",
        ui_fidelity_result="not_applicable",
        final_assessment="accepted",
    )

    path = write_task_review_record(feature_dir, record)

    assert path == feature_dir / "implementation-review" / "task-reviews" / "T001.json"
    assert task_review_acceptance_errors(record) == []
    assert task_review_is_accepted(record) is True
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["task_id"] == "T001"
    assert payload["final_assessment"] == "accepted"


def test_task_review_concerns_require_auditable_disposition() -> None:
    record = TaskReviewRecord(
        task_id="T002",
        spec_verdict="pass",
        quality_verdict="concerns",
        findings=[
            TaskReviewFinding(
                severity="medium",
                category="quality",
                file="src/demo.py",
                line=12,
                summary="Existing function remains oversized",
                required_fix="Track a bounded follow-up refactor",
                disposition="follow_up",
            )
        ],
        follow_up_work=[
            FollowUpWork(
                finding_index=0,
                description="Split the function after the feature lands",
                target="backlog",
            )
        ],
        ui_fidelity_result="not_applicable",
        final_assessment="accepted",
    )

    assert task_review_acceptance_errors(record) == []
    assert task_review_is_accepted(record) is True


def test_task_review_blocks_open_findings_and_open_controller_checks() -> None:
    record = TaskReviewRecord(
        task_id="T003",
        spec_verdict="cannot_verify_from_diff",
        quality_verdict="concerns",
        findings=[
            TaskReviewFinding(
                severity="high",
                category="evidence",
                file="",
                line=0,
                summary="Real entrypoint evidence is missing",
                required_fix="Run the real entrypoint check",
                disposition="open",
            )
        ],
        controller_checks=[
            ControllerCheck(
                check="Run the generated CLI from the installed script",
                reason="Diff cannot prove generated command behavior",
                evidence_required="Command output path",
            )
        ],
        ui_fidelity_result="needs_visual_or_human_review",
        final_assessment="accepted",
    )

    errors = task_review_acceptance_errors(record)

    assert any("open finding" in error for error in errors)
    assert any("controller check" in error for error in errors)
    assert any("visual or human review" in error for error in errors)
    assert task_review_is_accepted(record) is False


def test_task_ledger_round_trips_compact_entries(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    entries = [
        TaskLedgerEntry(
            task_id="T001",
            status="accepted",
            task_brief="implementation-review/task-briefs/T001.md",
            worker_result="worker-results/T001.json",
            review_package="implementation-review/review-packages/T001.md",
            task_review="implementation-review/task-reviews/T001.json",
            controller_checks_open=[],
            controller_checks_closed=["real entrypoint inspected"],
            last_evidence=["worker-results/T001.json"],
        )
    ]

    path = write_task_ledger(feature_dir, entries)
    restored = load_task_ledger(feature_dir)

    assert path == feature_dir / "implementation-review" / "ledger.json"
    assert restored[0].task_id == "T001"
    assert restored[0].status == "accepted"
    assert restored[0].controller_checks_closed == ["real entrypoint inspected"]
```

- [ ] **Step 2: Run tests and confirm the missing symbols fail**

Run:

```powershell
pytest tests/execution/test_implementation_review.py -q
```

Expected: failure with import errors for the new task review classes and helper functions.

- [ ] **Step 3: Add schema classes and path helpers**

Add these imports, literals, dataclasses, and helpers to `src/specify_cli/execution/implementation_review.py`:

```python
TaskReviewSpecVerdict = Literal["pass", "fail", "cannot_verify_from_diff"]
TaskReviewQualityVerdict = Literal["pass", "fail", "concerns"]
TaskReviewFindingCategory = Literal["spec", "quality", "evidence", "ui_fidelity", "plan_mandated_defect"]
TaskReviewFindingDisposition = Literal["open", "fixed", "accepted_residual_risk", "follow_up"]
TaskReviewUiFidelityResult = Literal["not_applicable", "pass", "fail", "needs_visual_or_human_review"]
TaskReviewFinalAssessment = Literal["accepted", "fixes_required", "controller_check_required"]
TaskLedgerStatus = Literal[
    "pending",
    "brief_written",
    "worker_done",
    "review_package_written",
    "review_pending",
    "fixes_required",
    "controller_check_required",
    "accepted",
    "blocked",
]


@dataclass(slots=True)
class TaskReviewFinding:
    severity: ReviewSeverity
    category: TaskReviewFindingCategory
    file: str
    line: int
    summary: str
    required_fix: str
    disposition: TaskReviewFindingDisposition = "open"


@dataclass(slots=True)
class ControllerCheck:
    check: str
    reason: str
    evidence_required: str


@dataclass(slots=True)
class AcceptedResidualRisk:
    finding_index: int
    reason: str
    owner: str


@dataclass(slots=True)
class FollowUpWork:
    finding_index: int
    description: str
    target: str


@dataclass(slots=True)
class TaskReviewRecord:
    task_id: str
    spec_verdict: TaskReviewSpecVerdict
    quality_verdict: TaskReviewQualityVerdict
    findings: list[TaskReviewFinding] = field(default_factory=list)
    controller_checks: list[ControllerCheck] = field(default_factory=list)
    plan_mandated_defects: list[dict[str, str]] = field(default_factory=list)
    accepted_residual_risks: list[AcceptedResidualRisk] = field(default_factory=list)
    follow_up_work: list[FollowUpWork] = field(default_factory=list)
    ui_fidelity_result: TaskReviewUiFidelityResult = "not_applicable"
    final_assessment: TaskReviewFinalAssessment = "fixes_required"
    created_at: str = field(default_factory=_utc_now)


@dataclass(slots=True)
class TaskLedgerEntry:
    task_id: str
    status: TaskLedgerStatus
    task_brief: str = ""
    worker_result: str = ""
    review_package: str = ""
    task_review: str = ""
    controller_checks_open: list[str] = field(default_factory=list)
    controller_checks_closed: list[str] = field(default_factory=list)
    last_evidence: list[str] = field(default_factory=list)


def task_briefs_dir(feature_dir: Path) -> Path:
    return implementation_review_root(feature_dir) / "task-briefs"


def review_packages_dir(feature_dir: Path) -> Path:
    return implementation_review_root(feature_dir) / "review-packages"


def task_reviews_dir(feature_dir: Path) -> Path:
    return implementation_review_root(feature_dir) / "task-reviews"


def task_brief_path(feature_dir: Path, task_id: str) -> Path:
    return task_briefs_dir(feature_dir) / f"{task_id}.md"


def review_package_path(feature_dir: Path, task_id: str) -> Path:
    return review_packages_dir(feature_dir) / f"{task_id}.md"


def task_review_path(feature_dir: Path, task_id: str) -> Path:
    return task_reviews_dir(feature_dir) / f"{task_id}.json"


def ledger_path(feature_dir: Path) -> Path:
    return implementation_review_root(feature_dir) / "ledger.json"


def branch_review_path(feature_dir: Path) -> Path:
    return implementation_review_root(feature_dir) / "branch-review.md"
```

- [ ] **Step 4: Add task review validation and ledger IO**

Add these functions to `src/specify_cli/execution/implementation_review.py`:

```python
def task_review_record_payload(record: TaskReviewRecord) -> dict[str, object]:
    return asdict(record)


def task_review_acceptance_errors(record: TaskReviewRecord) -> list[str]:
    errors: list[str] = []
    if record.spec_verdict == "fail":
        errors.append("spec verdict failed")
    if record.quality_verdict == "fail":
        errors.append("quality verdict failed")
    if record.quality_verdict == "concerns" and not record.findings:
        errors.append("concerns verdict requires findings")

    residual_indexes = {item.finding_index for item in record.accepted_residual_risks}
    follow_up_indexes = {item.finding_index for item in record.follow_up_work}
    for index, finding in enumerate(record.findings):
        if finding.disposition == "open":
            errors.append(f"open finding at index {index}")
        if finding.disposition == "accepted_residual_risk" and index not in residual_indexes:
            errors.append(f"accepted residual risk missing for finding index {index}")
        if finding.disposition == "follow_up" and index not in follow_up_indexes:
            errors.append(f"follow-up work missing for finding index {index}")

    if record.spec_verdict == "cannot_verify_from_diff" and record.controller_checks:
        if record.final_assessment == "accepted":
            errors.append("controller check must be closed before acceptance")
    if record.ui_fidelity_result == "needs_visual_or_human_review":
        if record.final_assessment == "accepted":
            errors.append("visual or human review must be complete before acceptance")
    if record.ui_fidelity_result == "fail":
        errors.append("ui fidelity failed")
    if record.final_assessment == "accepted" and record.controller_checks:
        errors.append("accepted review cannot contain open controller checks")
    return errors


def task_review_is_accepted(record: TaskReviewRecord) -> bool:
    return record.final_assessment == "accepted" and not task_review_acceptance_errors(record)


def write_task_review_record(feature_dir: Path, record: TaskReviewRecord) -> Path:
    path = task_review_path(feature_dir, record.task_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(task_review_record_payload(record), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def task_ledger_payload(entries: list[TaskLedgerEntry]) -> dict[str, object]:
    return {"tasks": [asdict(entry) for entry in entries]}


def write_task_ledger(feature_dir: Path, entries: list[TaskLedgerEntry]) -> Path:
    path = ledger_path(feature_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(task_ledger_payload(entries), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


def load_task_ledger(feature_dir: Path) -> list[TaskLedgerEntry]:
    path = ledger_path(feature_dir)
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_entries = payload.get("tasks", []) if isinstance(payload, dict) else []
    entries: list[TaskLedgerEntry] = []
    for item in raw_entries:
        if isinstance(item, dict):
            entries.append(TaskLedgerEntry(**_filter_task_ledger_entry_payload(item)))
    return entries


def _filter_task_ledger_entry_payload(payload: dict[str, object]) -> dict[str, object]:
    allowed = {item.name for item in fields(TaskLedgerEntry)}
    return {key: value for key, value in payload.items() if key in allowed}
```

Also extend the top imports:

```python
from dataclasses import asdict, dataclass, field, fields
```

- [ ] **Step 5: Run focused tests**

Run:

```powershell
pytest tests/execution/test_implementation_review.py -q
```

Expected: all tests in this file pass.

- [ ] **Step 6: Commit**

Run:

```powershell
git add src/specify_cli/execution/implementation_review.py tests/execution/test_implementation_review.py
git commit -m "feat: add implementation task review artifacts"
```

Expected: commit succeeds with only these two files staged.

## Task 2: Extend Packet and Result Contracts

**Files:**

- Modify: `src/specify_cli/execution/packet_schema.py`
- Modify: `src/specify_cli/execution/packet_validator.py`
- Modify: `src/specify_cli/execution/result_schema.py`
- Modify: `src/specify_cli/execution/result_normalizer.py`
- Modify: `src/specify_cli/execution/result_validator.py`
- Modify: `tests/execution/test_packet_schema.py`
- Modify: `tests/execution/test_packet_validator.py`
- Modify: `tests/execution/test_result_normalizer.py`
- Modify: `tests/execution/test_result_validator.py`

- [ ] **Step 1: Write failing packet schema tests**

Add this test to `tests/execution/test_packet_schema.py`:

```python
def test_worker_task_packet_round_trips_review_and_ui_contract_fields() -> None:
    packet = WorkerTaskPacket(
        feature_id="001-feature",
        task_id="T021",
        story_id="US1",
        objective="Implement settings panel",
        intent=ExecutionIntent(
            outcome="Implement settings panel",
            constraints=["Use DESIGN.md tokens"],
            success_signals=["settings panel renders in route"],
        ),
        scope=PacketScope(
            write_scope=["apps/web/src/settings/SettingsPanel.tsx"],
            read_scope=["DESIGN.md", ".specify/features/001-feature/ui-brief.md"],
        ),
        context_bundle=[
            ContextBundleItem(
                path="DESIGN.md",
                kind="task_reference",
                purpose="Project visual system",
                required_for=["ui_fidelity"],
                read_order=1,
                must_read=True,
                selection_reason="UI work must follow project design style",
            )
        ],
        required_references=[PacketReference(path="DESIGN.md", reason="visual contract")],
        hard_rules=["Follow the visual token contract"],
        forbidden_drift=["Do not introduce a new visual language"],
        validation_gates=["npm test -- settings"],
        done_criteria=["settings panel renders"],
        handoff_requirements=["return changed files"],
        global_constraints=["Use project spacing and typography tokens"],
        interfaces=PacketInterfaces(
            consumes=["SettingsRoute registration"],
            produces=["SettingsPanel component"],
        ),
        review_inputs=["ui-brief.md", "ui-target.html"],
        review_risks=["visual comparison may require browser screenshot"],
        ui_fidelity_requirements=UiFidelityRequirements(
            applicable=True,
            level="high",
            design_inputs=["DESIGN.md", "ui-brief.md", "ui-target.html"],
            required_evidence=["screenshot_evidence", "visual_comparison_evidence"],
        ),
        controller_checks_required=["human visual review if agent comparison is unavailable"],
    )

    restored = worker_task_packet_from_json(json.dumps(worker_task_packet_payload(packet)))

    assert restored.global_constraints == ["Use project spacing and typography tokens"]
    assert restored.interfaces.consumes == ["SettingsRoute registration"]
    assert restored.interfaces.produces == ["SettingsPanel component"]
    assert restored.review_inputs == ["ui-brief.md", "ui-target.html"]
    assert restored.review_risks == ["visual comparison may require browser screenshot"]
    assert restored.ui_fidelity_requirements.applicable is True
    assert restored.ui_fidelity_requirements.level == "high"
    assert restored.controller_checks_required == ["human visual review if agent comparison is unavailable"]
```

Update the imports in that test file to include:

```python
    PacketInterfaces,
    UiFidelityRequirements,
```

- [ ] **Step 2: Write failing result evidence tests**

Add this test to `tests/execution/test_result_normalizer.py`:

```python
def test_normalize_worker_task_result_payload_preserves_ui_fidelity_evidence() -> None:
    result = normalize_worker_task_result_payload(
        {
            "task_id": "T021",
            "status": "success",
            "summary": "implemented settings panel",
            "uiFidelityEvidence": [
                {
                    "kind": "visual_comparison",
                    "viewport": "desktop",
                    "evidence": "artifacts/screens/settings-desktop.png",
                }
            ],
        }
    )

    assert result.ui_fidelity_evidence == [
        {
            "kind": "visual_comparison",
            "viewport": "desktop",
            "evidence": "artifacts/screens/settings-desktop.png",
        }
    ]
```

Add this test to `tests/execution/test_result_validator.py`:

```python
def test_validate_worker_task_result_requires_ui_fidelity_evidence(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.ui_fidelity_requirements = UiFidelityRequirements(
        applicable=True,
        level="high",
        design_inputs=["DESIGN.md", "ui-brief.md"],
        required_evidence=["visual_comparison_evidence"],
    )
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
        summary="Implemented UI-facing behavior",
        rule_acknowledgement=RuleAcknowledgement(
            required_references_read=True,
            forbidden_drift_respected=True,
            context_bundle_read=True,
            paths_read=[
                ".specify/project-cognition/status.json",
                ".specify/project-cognition/project-cognition.db",
            ],
        ),
    )

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_result(result, sample_packet)

    assert exc.value.code == "DP3"
    assert "UI fidelity evidence" in exc.value.message
```

Update the imports in `tests/execution/test_result_validator.py` to include `UiFidelityRequirements`.

- [ ] **Step 3: Run focused tests and confirm missing fields fail**

Run:

```powershell
pytest tests/execution/test_packet_schema.py tests/execution/test_result_normalizer.py tests/execution/test_result_validator.py -q
```

Expected: failures mention missing `PacketInterfaces`, `UiFidelityRequirements`, or `ui_fidelity_evidence`.

- [ ] **Step 4: Add packet dataclasses and fields**

In `src/specify_cli/execution/packet_schema.py`, add:

```python
UiFidelityLevel = Literal["none", "approximate", "high"]


@dataclass(slots=True)
class PacketInterfaces:
    consumes: list[str] = field(default_factory=list)
    produces: list[str] = field(default_factory=list)


@dataclass(slots=True)
class UiFidelityRequirements:
    applicable: bool = False
    level: UiFidelityLevel = "none"
    design_inputs: list[str] = field(default_factory=list)
    required_evidence: list[str] = field(default_factory=list)
```

Add these fields to `WorkerTaskPacket` while keeping `packet_version` at `2`:

```python
    global_constraints: list[str] = field(default_factory=list)
    interfaces: PacketInterfaces = field(default_factory=PacketInterfaces)
    review_inputs: list[str] = field(default_factory=list)
    review_risks: list[str] = field(default_factory=list)
    ui_fidelity_requirements: UiFidelityRequirements = field(default_factory=UiFidelityRequirements)
    controller_checks_required: list[str] = field(default_factory=list)
```

In `worker_task_packet_from_json()`, add:

```python
    interfaces = PacketInterfaces(
        **_filter_dataclass_payload(PacketInterfaces, payload.get("interfaces", {}))
    )
    ui_fidelity_requirements = UiFidelityRequirements(
        **_filter_dataclass_payload(
            UiFidelityRequirements,
            payload.get("ui_fidelity_requirements", {}),
        )
    )
```

Then add these assignments before returning `WorkerTaskPacket`:

```python
    packet_payload["interfaces"] = interfaces
    packet_payload["ui_fidelity_requirements"] = ui_fidelity_requirements
```

- [ ] **Step 5: Validate packet field values**

In `src/specify_cli/execution/packet_validator.py`, add:

```python
VALID_UI_FIDELITY_LEVELS = {"none", "approximate", "high"}
```

Inside `validate_worker_task_packet()`, after the platform guardrail check, add:

```python
    ui_contract = packet.ui_fidelity_requirements
    if ui_contract.level not in VALID_UI_FIDELITY_LEVELS:
        raise PacketValidationError("DP2", "ui fidelity level must be none, approximate, or high")
    if ui_contract.applicable:
        if ui_contract.level == "none":
            raise PacketValidationError("DP2", "applicable ui fidelity requires approximate or high level")
        if not ui_contract.design_inputs:
            raise PacketValidationError("DP2", "applicable ui fidelity requires design inputs")
        if not ui_contract.required_evidence:
            raise PacketValidationError("DP2", "applicable ui fidelity requires evidence terms")
    if packet.controller_checks_required and not all(item.strip() for item in packet.controller_checks_required):
        raise PacketValidationError("DP2", "controller checks cannot contain blank entries")
```

Add this test to `tests/execution/test_packet_validator.py`:

```python
def test_validate_worker_task_packet_rejects_incomplete_ui_fidelity_contract(
    sample_packet: WorkerTaskPacket,
) -> None:
    sample_packet.ui_fidelity_requirements = UiFidelityRequirements(applicable=True, level="none")

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_packet(sample_packet)

    assert exc.value.code == "DP2"
    assert "ui fidelity" in exc.value.message
```

- [ ] **Step 6: Add UI fidelity evidence to result schema and normalizer**

In `src/specify_cli/execution/result_schema.py`, add this field to `WorkerTaskResult`:

```python
    ui_fidelity_evidence: list[dict[str, str]] = field(default_factory=list)
```

In `worker_task_result_from_json()`, add:

```python
    result_payload["ui_fidelity_evidence"] = _normalize_evidence_items(
        result_payload.get("ui_fidelity_evidence", [])
    )
```

In `src/specify_cli/execution/result_normalizer.py`, add to the `WorkerTaskResult(...)` constructor:

```python
        ui_fidelity_evidence=_normalize_evidence_items(
            _pick(payload, "ui_fidelity_evidence", "uiFidelityEvidence")
        ),
```

- [ ] **Step 7: Require UI fidelity evidence when packet asks for it**

In `src/specify_cli/execution/result_validator.py`, inside the `result.status == "success"` block, add:

```python
        ui_contract = packet.ui_fidelity_requirements
        if ui_contract.applicable:
            if not result.ui_fidelity_evidence:
                raise PacketValidationError("DP3", "worker result is missing UI fidelity evidence")
            evidence_kinds = {
                normalize_evidence_label(str(item.get("kind", "")))
                for item in result.ui_fidelity_evidence
                if isinstance(item, dict)
            }
            required_ui_evidence = {
                normalize_evidence_label(item)
                for item in ui_contract.required_evidence
                if item.strip()
            }
            if "visual_comparison_evidence" in required_ui_evidence and "visual_comparison" not in evidence_kinds:
                raise PacketValidationError(
                    "DP3",
                    "worker result is missing visual comparison UI fidelity evidence",
                )
```

- [ ] **Step 8: Run focused tests**

Run:

```powershell
pytest tests/execution/test_packet_schema.py tests/execution/test_packet_validator.py tests/execution/test_result_normalizer.py tests/execution/test_result_validator.py -q
```

Expected: all selected tests pass.

- [ ] **Step 9: Commit**

Run:

```powershell
git add src/specify_cli/execution/packet_schema.py src/specify_cli/execution/packet_validator.py src/specify_cli/execution/result_schema.py src/specify_cli/execution/result_normalizer.py src/specify_cli/execution/result_validator.py tests/execution/test_packet_schema.py tests/execution/test_packet_validator.py tests/execution/test_result_normalizer.py tests/execution/test_result_validator.py
git commit -m "feat: carry review and ui fidelity task packet fields"
```

Expected: commit succeeds with only these files staged.

## Task 3: Compile New Packet Fields From Plan and Tasks

**Files:**

- Modify: `src/specify_cli/execution/packet_compiler.py`
- Modify: `tests/execution/test_packet_compiler.py`

- [ ] **Step 1: Write failing compiler test**

Add this test to `tests/execution/test_packet_compiler.py`:

```python
def test_compile_worker_task_packet_reads_review_and_ui_contract_fields(
    tmp_path: Path,
) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)
    (project_root / ".specify" / "memory").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition").mkdir(parents=True)
    (project_root / ".specify" / "project-cognition" / "status.json").write_text(
        '{"version": 1, "graph_ready": true}\n',
        encoding="utf-8",
    )
    (project_root / ".specify" / "project-cognition" / "project-cognition.db").write_bytes(
        b"SQLite test database marker"
    )
    (project_root / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n\n- MUST add tests for public behavior\n",
        encoding="utf-8",
    )
    (feature_dir / "plan.md").write_text(
        "\n".join(
            [
                "## Required Implementation References",
                "",
                "- `DESIGN.md`",
                "",
                "## Forbidden Implementation Drift",
                "",
                "- Do not introduce a second visual system",
                "",
                "## Global Constraints",
                "",
                "- Use DESIGN.md color, typography, spacing, radius, and shadow tokens",
                "- Do not add UI dependencies unless plan.md names them",
                "",
                "## Review-Risk Notes",
                "",
                "- Visual comparison may require a browser screenshot",
            ]
        ),
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "\n".join(
            [
                "## Validation Gates",
                "",
                "- npm test -- settings",
                "",
                "## T021: Build settings panel",
                "",
                "### Scope Boundaries",
                "| Field | Value |",
                "|-------|-------|",
                "| write_scope | [apps/web/src/settings/SettingsPanel.tsx] |",
                "| read_scope | [DESIGN.md, ui-brief.md] |",
                "| consumes | [SettingsRoute registration] |",
                "| produces | [SettingsPanel component] |",
                "| review_inputs | [DESIGN.md, ui-brief.md, ui-target.html] |",
                "| review_risks | [high fidelity requires visual comparison] |",
                "| ui_fidelity_level | [high] |",
                "| design_inputs | [DESIGN.md, ui-brief.md, ui-target.html] |",
                "| ui_required_evidence | [screenshot_evidence, visual_comparison_evidence] |",
                "| controller_checks_required | [human review if agent visual comparison is unavailable] |",
                "",
                "- [ ] T021 [US1] Build settings panel in apps/web/src/settings/SettingsPanel.tsx",
            ]
        ),
        encoding="utf-8",
    )

    packet = compile_worker_task_packet(
        project_root=project_root,
        feature_dir=feature_dir,
        task_id="T021",
    )

    assert packet.global_constraints == [
        "Use DESIGN.md color, typography, spacing, radius, and shadow tokens",
        "Do not add UI dependencies unless plan.md names them",
    ]
    assert packet.interfaces.consumes == ["SettingsRoute registration"]
    assert packet.interfaces.produces == ["SettingsPanel component"]
    assert packet.review_inputs == ["DESIGN.md", "ui-brief.md", "ui-target.html"]
    assert "high fidelity requires visual comparison" in packet.review_risks
    assert "Visual comparison may require a browser screenshot" in packet.review_risks
    assert packet.ui_fidelity_requirements.applicable is True
    assert packet.ui_fidelity_requirements.level == "high"
    assert packet.ui_fidelity_requirements.required_evidence == [
        "screenshot_evidence",
        "visual_comparison_evidence",
    ]
    assert packet.controller_checks_required == [
        "human review if agent visual comparison is unavailable"
    ]
```

- [ ] **Step 2: Run compiler test and confirm fields are empty**

Run:

```powershell
pytest tests/execution/test_packet_compiler.py::test_compile_worker_task_packet_reads_review_and_ui_contract_fields -q
```

Expected: failure showing the new fields are not populated.

- [ ] **Step 3: Import the new packet dataclasses**

In `src/specify_cli/execution/packet_compiler.py`, extend the import block from `.packet_schema`:

```python
    PacketInterfaces,
    UiFidelityRequirements,
```

- [ ] **Step 4: Add compiler helpers**

Add these helpers near the existing task contract helpers:

```python
def _first_task_detail_value(task_detail: str, field_name: str) -> str:
    values = _task_detail_table_field_values(task_detail, "Scope Boundaries", field_name)
    return values[0] if values else ""


def _global_constraints_for_task(plan_text: str, task_detail: str) -> list[str]:
    return _unique(
        _section_or_subsection_values(
            plan_text,
            "Global Constraints",
            "Profile-Driven Implementation Constraints",
        )
        + _task_detail_table_field_values(task_detail, "Scope Boundaries", "global_constraints")
    )


def _review_risks_for_task(plan_text: str, task_detail: str) -> list[str]:
    return _unique(
        _section_or_subsection_values(plan_text, "Review-Risk Notes")
        + _task_detail_table_field_values(task_detail, "Scope Boundaries", "review_risks")
    )


def _ui_fidelity_requirements_for_task(task_detail: str) -> UiFidelityRequirements:
    raw_level = _first_task_detail_value(task_detail, "ui_fidelity_level").lower()
    level = raw_level if raw_level in {"none", "approximate", "high"} else "none"
    design_inputs = _task_detail_table_field_values(task_detail, "Scope Boundaries", "design_inputs")
    required_evidence = _task_detail_table_field_values(task_detail, "Scope Boundaries", "ui_required_evidence")
    applicable = level != "none" or bool(design_inputs or required_evidence)
    if applicable and level == "none":
        level = "approximate"
    return UiFidelityRequirements(
        applicable=applicable,
        level=level,
        design_inputs=design_inputs,
        required_evidence=required_evidence,
    )
```

- [ ] **Step 5: Populate fields in `WorkerTaskPacket(...)`**

Inside `compile_worker_task_packet()`, add these keyword arguments to the `WorkerTaskPacket` constructor:

```python
        global_constraints=_global_constraints_for_task(plan_text, task_detail),
        interfaces=PacketInterfaces(
            consumes=_task_detail_table_field_values(task_detail, "Scope Boundaries", "consumes"),
            produces=_task_detail_table_field_values(task_detail, "Scope Boundaries", "produces"),
        ),
        review_inputs=_task_detail_table_field_values(task_detail, "Scope Boundaries", "review_inputs"),
        review_risks=_review_risks_for_task(plan_text, task_detail),
        ui_fidelity_requirements=_ui_fidelity_requirements_for_task(task_detail),
        controller_checks_required=_task_detail_table_field_values(
            task_detail,
            "Scope Boundaries",
            "controller_checks_required",
        ),
```

- [ ] **Step 6: Run focused compiler tests**

Run:

```powershell
pytest tests/execution/test_packet_compiler.py -q
```

Expected: all compiler tests pass.

- [ ] **Step 7: Commit**

Run:

```powershell
git add src/specify_cli/execution/packet_compiler.py tests/execution/test_packet_compiler.py
git commit -m "feat: compile review packet fields from task contracts"
```

Expected: commit succeeds with only these two files staged.

## Task 4: Enforce Ledger and Branch Review in Resume and Closeout

**Files:**

- Modify: `src/specify_cli/implement_audit.py`
- Modify: `src/specify_cli/implementation_summary.py`
- Modify: `tests/execution/test_implement_resume_audit.py`
- Modify: `tests/contract/test_hook_cli_surface.py`

- [ ] **Step 1: Write failing resume audit tests**

Add this helper and tests to `tests/execution/test_implement_resume_audit.py`:

```python
def _write_packetized_review_state(feature_dir: Path, *, branch_review: bool = True) -> None:
    (feature_dir / "task-packets").mkdir(exist_ok=True)
    (feature_dir / "task-packets" / "T001.json").write_text('{"task_id": "T001"}\n', encoding="utf-8")
    review_dir = feature_dir / "implementation-review"
    (review_dir / "task-briefs").mkdir(parents=True, exist_ok=True)
    (review_dir / "review-packages").mkdir(parents=True, exist_ok=True)
    (review_dir / "task-reviews").mkdir(parents=True, exist_ok=True)
    (review_dir / "task-briefs" / "T001.md").write_text("# T001 Brief\n", encoding="utf-8")
    (review_dir / "review-packages" / "T001.md").write_text("# T001 Review Package\n", encoding="utf-8")
    (review_dir / "task-reviews" / "T001.json").write_text(
        """
{
  "task_id": "T001",
  "spec_verdict": "pass",
  "quality_verdict": "pass",
  "findings": [],
  "controller_checks": [],
  "plan_mandated_defects": [],
  "accepted_residual_risks": [],
  "follow_up_work": [],
  "ui_fidelity_result": "not_applicable",
  "final_assessment": "accepted"
}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    (review_dir / "ledger.json").write_text(
        """
{
  "tasks": [
    {
      "task_id": "T001",
      "status": "accepted",
      "task_brief": "implementation-review/task-briefs/T001.md",
      "worker_result": "worker-results/T001.json",
      "review_package": "implementation-review/review-packages/T001.md",
      "task_review": "implementation-review/task-reviews/T001.json",
      "controller_checks_open": [],
      "controller_checks_closed": [],
      "last_evidence": ["worker-results/T001.json"]
    }
  ]
}
""".strip()
        + "\n",
        encoding="utf-8",
    )
    if branch_review:
        (review_dir / "branch-review.md").write_text("# Branch Review\n\n- final_assessment: accepted\n", encoding="utf-8")


def test_packetized_checked_task_without_ledger_is_not_trusted(tmp_path: Path) -> None:
    feature_dir = tmp_path / "specs" / "001-demo"
    _write_basic_feature(feature_dir)
    (feature_dir / "task-packets").mkdir()
    (feature_dir / "task-packets" / "T001.json").write_text('{"task_id": "T001"}\n', encoding="utf-8")

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any("missing implementation-review/ledger.json" in gap for gap in payload["open_gaps"])


def test_packetized_checked_task_without_branch_review_is_not_terminal(tmp_path: Path) -> None:
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
  "consumer_evidence": [
    {
      "kind": "real_entrypoint",
      "entrypoint": "DeviceProviderPage",
      "producer": "provider catalog fixture",
      "transformer": "FormFactory cliToolType routing",
      "consumer": "DeviceProviderFormModal renders ClaudeForm",
      "boundary_or_executor": "React render test",
      "validation": "npm test -- providers"
    }
  ],
  "summary": "Created and wired ClaudeForm component"
}
""".strip(),
        encoding="utf-8",
    )
    _write_packetized_review_state(feature_dir, branch_review=False)

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "fail"
    assert any("branch-review.md" in gap for gap in payload["open_gaps"])


def test_packetized_checked_task_with_accepted_review_and_branch_review_passes(tmp_path: Path) -> None:
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
  "consumer_evidence": [
    {
      "kind": "real_entrypoint",
      "entrypoint": "DeviceProviderPage",
      "producer": "provider catalog fixture",
      "transformer": "FormFactory cliToolType routing",
      "consumer": "DeviceProviderFormModal renders ClaudeForm",
      "boundary_or_executor": "React render test",
      "validation": "npm test -- providers"
    }
  ],
  "summary": "Created and wired ClaudeForm component"
}
""".strip(),
        encoding="utf-8",
    )
    _write_packetized_review_state(feature_dir, branch_review=True)

    payload = audit_implement_resume(tmp_path, feature_dir)

    assert payload["status"] == "pass"
    assert payload["trusted_terminal_state"] is True
```

- [ ] **Step 2: Write failing summary assertion**

Extend `test_implementation_summary_records_completed_work_changes_and_verification()` after writing the worker result:

```python
    _write_packetized_review_state(feature_dir, branch_review=True)
```

Add these assertions after `payload = build_implementation_summary(project, feature_dir)`:

```python
    assert payload["review_artifacts"]["ledger"] == ".specify/features/001-demo/implementation-review/ledger.json"
    assert payload["review_artifacts"]["branch_review"] == ".specify/features/001-demo/implementation-review/branch-review.md"
    assert payload["completed_work"][0]["task_review"] == ".specify/features/001-demo/implementation-review/task-reviews/T001.json"
```

Add report assertions:

```python
    assert "## Review Artifacts" in report
    assert "implementation-review/ledger.json" in report
    assert "implementation-review/branch-review.md" in report
```

- [ ] **Step 3: Run focused audit tests and confirm review gaps are missing**

Run:

```powershell
pytest tests/execution/test_implement_resume_audit.py -q
```

Expected: failures show resume audit and summary do not yet read review artifacts.

- [ ] **Step 4: Add ledger loading and packetized detection**

In `src/specify_cli/implement_audit.py`, add:

```python
def _is_packetized_implementation(feature_dir: Path) -> bool:
    packet_dir = feature_dir / "task-packets"
    return packet_dir.is_dir() and any(packet_dir.glob("*.json"))


def _load_task_ledger(feature_dir: Path) -> dict[str, dict[str, Any]]:
    path = feature_dir / "implementation-review" / "ledger.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"__invalid__": {"status": "invalid-json", "path": str(path)}}
    raw_tasks = payload.get("tasks", []) if isinstance(payload, dict) else []
    entries: dict[str, dict[str, Any]] = {}
    for item in raw_tasks:
        if not isinstance(item, dict):
            continue
        task_id = str(item.get("task_id") or "").upper()
        if task_id:
            entries[task_id] = item
    return entries


def _review_path_exists(feature_dir: Path, relative_path: object) -> bool:
    if not isinstance(relative_path, str) or not relative_path.strip():
        return False
    path = feature_dir / relative_path
    return path.exists() and path.is_file()
```

- [ ] **Step 5: Require accepted ledger entries for packetized checked tasks**

Inside `audit_implement_resume()`, after `tasks = _parse_tasks(tasks_path)`, add:

```python
    packetized = _is_packetized_implementation(resolved_feature_dir)
    ledger_entries = _load_task_ledger(resolved_feature_dir) if packetized else {}
    ledger_path = resolved_feature_dir / "implementation-review" / "ledger.json"
    if packetized and checked_tasks and not ledger_path.exists():
        evidence_gaps.append("missing implementation-review/ledger.json for packetized implementation")
```

Inside the checked task loop, after worker result validation, add:

```python
        if packetized:
            ledger_entry = ledger_entries.get(str(task["task_id"]).upper())
            if not ledger_entry:
                missing.append("missing implementation review ledger entry")
            elif str(ledger_entry.get("status") or "").lower() != "accepted":
                missing.append("implementation review ledger entry is not accepted")
            elif not _review_path_exists(resolved_feature_dir, ledger_entry.get("task_review")):
                missing.append("missing accepted task review artifact")
```

Before `audit_passed = terminal and not evidence_gaps`, add:

```python
    if packetized and terminal and checked_tasks:
        branch_review = resolved_feature_dir / "implementation-review" / "branch-review.md"
        if not branch_review.exists():
            evidence_gaps.append("implementation-review/branch-review.md is missing")
```

- [ ] **Step 6: Add review artifacts to implementation summary**

In `src/specify_cli/implementation_summary.py`, add helpers:

```python
def _load_review_ledger(feature_dir: Path, project_root: Path) -> dict[str, dict[str, str]]:
    path = feature_dir / "implementation-review" / "ledger.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    raw_tasks = payload.get("tasks", []) if isinstance(payload, dict) else []
    entries: dict[str, dict[str, str]] = {}
    for item in raw_tasks:
        if not isinstance(item, dict):
            continue
        task_id = str(item.get("task_id") or "").upper()
        if not task_id:
            continue
        entries[task_id] = {
            "status": str(item.get("status") or ""),
            "task_brief": _display_path(feature_dir / str(item.get("task_brief") or ""), project_root),
            "review_package": _display_path(feature_dir / str(item.get("review_package") or ""), project_root),
            "task_review": _display_path(feature_dir / str(item.get("task_review") or ""), project_root),
        }
    return entries


def _review_artifacts(feature_dir: Path, project_root: Path) -> dict[str, str]:
    review_dir = feature_dir / "implementation-review"
    ledger = review_dir / "ledger.json"
    branch_review = review_dir / "branch-review.md"
    return {
        "ledger": _display_path(ledger, project_root) if ledger.exists() else "",
        "branch_review": _display_path(branch_review, project_root) if branch_review.exists() else "",
    }
```

Update `build_implementation_summary()`:

```python
    review_ledger = _load_review_ledger(resolved_feature_dir, root)
    completed_work = _completed_work(tasks, worker_results, root, review_ledger)
```

Change `_completed_work()` signature and append review fields:

```python
def _completed_work(
    tasks: list[dict[str, Any]],
    worker_results: list[dict[str, Any]],
    project_root: Path,
    review_ledger: dict[str, dict[str, str]],
) -> list[dict[str, Any]]:
```

Inside each completed item:

```python
        review_entry = review_ledger.get(task_id, {})
```

Add keys:

```python
                "task_brief": review_entry.get("task_brief", ""),
                "review_package": review_entry.get("review_package", ""),
                "task_review": review_entry.get("task_review", ""),
                "review_status": review_entry.get("status", ""),
```

Add this payload key:

```python
        "review_artifacts": _review_artifacts(resolved_feature_dir, root),
```

In `_render_markdown()`, after the version comparison block and before remaining gaps, add:

```python
    lines.extend(["", "## Review Artifacts", ""])
    review_artifacts = payload.get("review_artifacts") or {}
    if review_artifacts.get("ledger"):
        lines.append(f"- Ledger: `{review_artifacts['ledger']}`")
    else:
        lines.append("- Ledger: none recorded.")
    if review_artifacts.get("branch_review"):
        lines.append(f"- Branch review: `{review_artifacts['branch_review']}`")
    else:
        lines.append("- Branch review: none recorded.")
```

Also in the completed-work loop, add:

```python
            if item.get("task_review"):
                lines.append(f"  - Task review: `{item['task_review']}`")
```

- [ ] **Step 7: Run audit and closeout tests**

Run:

```powershell
pytest tests/execution/test_implement_resume_audit.py tests/contract/test_hook_cli_surface.py::test_implement_closeout_writes_user_facing_summary -q
```

Expected: selected tests pass.

- [ ] **Step 8: Commit**

Run:

```powershell
git add src/specify_cli/implement_audit.py src/specify_cli/implementation_summary.py tests/execution/test_implement_resume_audit.py tests/contract/test_hook_cli_surface.py
git commit -m "feat: audit accepted task reviews before implement closeout"
```

Expected: commit succeeds with only these files staged.

## Task 5: Add Hook Validation for Packetized Implement Review Artifacts

**Files:**

- Modify: `src/specify_cli/hooks/artifact_validation.py`
- Modify: `src/specify_cli/hooks/state_validation.py`
- Modify: `tests/contract/test_hook_cli_surface.py`

- [ ] **Step 1: Write failing artifact validation test**

Add this test to `tests/contract/test_hook_cli_surface.py` near the existing hook artifact tests:

```python
def test_hook_validate_artifacts_blocks_packetized_implement_missing_review_ledger(tmp_path: Path):
    feature_dir = tmp_path / ".specify" / "features" / "001-demo"
    feature_dir.mkdir(parents=True)
    (feature_dir / "implement-tracker.md").write_text(
        "---\nstatus: resolved\n---\n\n## Current Focus\nnext_action: report completion\n",
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text("- [X] T001 [US1] Build UI in src/app.tsx\n", encoding="utf-8")
    (feature_dir / "task-packets").mkdir()
    (feature_dir / "task-packets" / "T001.json").write_text('{"task_id":"T001"}\n', encoding="utf-8")

    result = run_cli(
        [
            "hook",
            "validate-artifacts",
            "--command",
            "implement",
            "--feature-dir",
            str(feature_dir),
            "--format",
            "json",
        ],
        cwd=tmp_path,
    )

    assert result.returncode != 0
    payload = json.loads(result.stdout)
    assert any("implementation-review/ledger.json" in message for message in payload["errors"])
```

- [ ] **Step 2: Run the test and confirm unsupported command failure**

Run:

```powershell
pytest tests/contract/test_hook_cli_surface.py::test_hook_validate_artifacts_blocks_packetized_implement_missing_review_ledger -q
```

Expected: failure because artifact validation does not support `implement`.

- [ ] **Step 3: Add conservative implement artifact validation**

In `src/specify_cli/hooks/artifact_validation.py`, add `"implement"` to the artifact maps:

```python
    "implement": ("implement-tracker.md",),
```

Add this helper near other command-specific validators:

```python
def _tasks_checked_ids(feature_dir: Path) -> list[str]:
    tasks_path = feature_dir / "tasks.md"
    if not tasks_path.exists():
        return []
    content = tasks_path.read_text(encoding="utf-8", errors="replace")
    return [
        match.group(1).upper()
        for match in re.finditer(r"(?m)^\s*-\s*\[[xX]\]\s+(T\d+)\b", content)
    ]


def _validate_implement_review_artifacts(feature_dir: Path) -> list[str]:
    errors: list[str] = []
    checked_ids = _tasks_checked_ids(feature_dir)
    packet_dir = feature_dir / "task-packets"
    packetized = packet_dir.is_dir() and any(packet_dir.glob("*.json"))
    if not packetized or not checked_ids:
        return errors

    review_dir = feature_dir / "implementation-review"
    ledger_file = review_dir / "ledger.json"
    if not ledger_file.exists():
        return ["missing required artifact: implementation-review/ledger.json"]
    payload, read_errors = _read_json_artifact(ledger_file, "implementation-review/ledger.json")
    if read_errors:
        return read_errors
    if not isinstance(payload, dict) or not isinstance(payload.get("tasks"), list):
        return ["implementation-review/ledger.json must contain a top-level tasks array"]

    by_task = {
        str(item.get("task_id") or "").upper(): item
        for item in payload["tasks"]
        if isinstance(item, dict)
    }
    for task_id in checked_ids:
        entry = by_task.get(task_id)
        if not entry:
            errors.append(f"implementation-review/ledger.json is missing checked task {task_id}")
            continue
        if str(entry.get("status") or "").lower() != "accepted":
            errors.append(f"implementation-review/ledger.json task {task_id} is not accepted")
        review_path = feature_dir / str(entry.get("task_review") or "")
        if not review_path.exists():
            errors.append(f"missing required artifact: implementation-review/task-reviews/{task_id}.json")

    if checked_ids and not (review_dir / "branch-review.md").exists():
        errors.append("missing required artifact: implementation-review/branch-review.md")
    return errors
```

In `validate_artifacts_hook()`, add:

```python
    if command_name == "implement":
        validation_errors.extend(_validate_implement_review_artifacts(feature_dir))
```

- [ ] **Step 4: Add implement state validation context**

In `src/specify_cli/hooks/state_validation.py`, inside the `command_name == "implement"` return data, add:

```python
        review_dir = feature_dir / "implementation-review"
```

Then include:

```python
                "implementation_review": {
                    "ledger": str((review_dir / "ledger.json").resolve()),
                    "branch_review": str((review_dir / "branch-review.md").resolve()),
                },
```

- [ ] **Step 5: Run focused hook tests**

Run:

```powershell
pytest tests/contract/test_hook_cli_surface.py::test_hook_validate_artifacts_blocks_packetized_implement_missing_review_ledger tests/contract/test_hook_cli_surface.py::test_hook_preflight_blocks_implement_and_returns_json -q
```

Expected: both tests pass.

- [ ] **Step 6: Commit**

Run:

```powershell
git add src/specify_cli/hooks/artifact_validation.py src/specify_cli/hooks/state_validation.py tests/contract/test_hook_cli_surface.py
git commit -m "feat: validate packetized implement review artifacts"
```

Expected: commit succeeds with only these files staged.

## Task 6: Update Generated Workflow Templates and Prompts

**Files:**

- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/commands/implement.md`
- Modify: `templates/plan-contract-template.json`
- Modify: `templates/tasks-template.md`
- Modify: `templates/workflow-state-template.md`
- Modify: `templates/worker-prompts/implementer.md`
- Create: `templates/worker-prompts/task-reviewer.md`
- Modify: `templates/worker-prompts/spec-reviewer.md`
- Modify: `templates/worker-prompts/code-quality-reviewer.md`
- Modify: `templates/passive-skills/subagent-driven-development/SKILL.md`
- Modify: `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`

- [ ] **Step 1: Write failing alignment tests for new guidance**

In `tests/test_alignment_templates.py`, update worker prompt lists to include:

```python
        "templates/worker-prompts/task-reviewer.md",
```

Add this test near the existing worker prompt assertions:

```python
def test_implement_uses_single_task_reviewer_by_default() -> None:
    content = _read("templates/commands/implement.md")

    assert ".specify/templates/worker-prompts/task-reviewer.md" in content
    assert "spec_verdict" in content
    assert "quality_verdict" in content
    assert "implementation-review/task-briefs/" in content
    assert "implementation-review/review-packages/" in content
    assert "implementation-review/task-reviews/" in content
    assert "implementation-review/ledger.json" in content
    assert "implementation-review/branch-review.md" in content
    assert "pair post-implementation reviews with `.specify/templates/worker-prompts/spec-reviewer.md`" not in content
```

Add this test:

```python
def test_task_reviewer_prompt_defines_dual_verdict_schema() -> None:
    content = _read("templates/worker-prompts/task-reviewer.md")

    assert "spec_verdict" in content
    assert "quality_verdict" in content
    assert "ui_fidelity_result" in content
    assert "final_assessment" in content
    assert "accepted_residual_risks" in content
    assert "follow_up_work" in content
```

Add this test:

```python
def test_plan_tasks_and_workflow_state_carry_review_artifact_contract() -> None:
    combined = "\n".join(
        [
            _read("templates/commands/plan.md"),
            _read("templates/commands/tasks.md"),
            _read("templates/tasks-template.md"),
            _read("templates/workflow-state-template.md"),
            _read("templates/plan-contract-template.json"),
        ]
    )

    assert "Global Constraints" in combined
    assert "Task Interface Map" in combined
    assert "Review-Risk Notes" in combined
    assert "ui_fidelity_requirements" in combined
    assert "controller_checks_required" in combined
    assert "task-briefs" in combined
    assert "review-packages" in combined
    assert "task-reviews" in combined
    assert "branch-review.md" in combined
```

- [ ] **Step 2: Run alignment tests and confirm template gaps**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_implement_uses_single_task_reviewer_by_default tests/test_alignment_templates.py::test_task_reviewer_prompt_defines_dual_verdict_schema tests/test_alignment_templates.py::test_plan_tasks_and_workflow_state_carry_review_artifact_contract -q
```

Expected: failures mention missing `task-reviewer.md` and missing artifact contract terms.

- [ ] **Step 3: Create `task-reviewer.md`**

Create `templates/worker-prompts/task-reviewer.md` with:

```markdown
# Task Reviewer Worker Prompt

Use this template when the leader reviews one completed `sp-implement` task.

## Role

You are a read-only task reviewer. Review the task brief, review package, worker result, diff, touched files, and evidence. Do not edit files.

## Required Inputs

- `FEATURE_DIR/implementation-review/task-briefs/<task-id>.md`
- `FEATURE_DIR/implementation-review/review-packages/<task-id>.md`
- `FEATURE_DIR/worker-results/<task-id>.json`
- The relevant diff or changed-file list named by the review package
- Any UI, reference, real-entrypoint, or human-review evidence named by the review package

Treat worker summaries as claims, not proof.

## Verdicts

Return one JSON object with:

```json
{
  "task_id": "T001",
  "spec_verdict": "pass | fail | cannot_verify_from_diff",
  "quality_verdict": "pass | fail | concerns",
  "findings": [
    {
      "severity": "critical | high | medium | low",
      "category": "spec | quality | evidence | ui_fidelity | plan_mandated_defect",
      "file": "path/to/file",
      "line": 1,
      "summary": "Concrete issue summary",
      "required_fix": "Concrete fix or escalation",
      "disposition": "open | fixed | accepted_residual_risk | follow_up"
    }
  ],
  "controller_checks": [
    {
      "check": "Run or inspect the real entrypoint",
      "reason": "Requirement cannot be verified from the diff",
      "evidence_required": "Screenshot or command output path"
    }
  ],
  "plan_mandated_defects": [],
  "accepted_residual_risks": [
    {
      "finding_index": 0,
      "reason": "Why accepting this concern is safe for this release",
      "owner": "leader | user | maintainer"
    }
  ],
  "follow_up_work": [
    {
      "finding_index": 0,
      "description": "Concrete follow-up work",
      "target": "task | issue | upstream-workflow | backlog"
    }
  ],
  "ui_fidelity_result": "not_applicable | pass | fail | needs_visual_or_human_review",
  "final_assessment": "accepted | fixes_required | controller_check_required"
}
```

## Acceptance Rules

- `spec_verdict=fail` blocks task acceptance.
- `quality_verdict=fail` blocks task acceptance.
- `quality_verdict=concerns` may pass only when every concern has a disposition and appears in `accepted_residual_risks` or `follow_up_work` when relevant.
- `spec_verdict=cannot_verify_from_diff` requires explicit controller checks before acceptance.
- `ui_fidelity_result=needs_visual_or_human_review` requires agent visual comparison first when available, otherwise human review as a controller check.
- `final_assessment=accepted` is valid only when blocking findings and required controller checks are closed.

## Review Focus

- Verify the implementation satisfies the task brief and upstream plan constraints.
- Verify changed files stay within the allowed write scope.
- Verify validation evidence is real, current, and covers the named gate.
- Verify UI and reference fidelity evidence when the task brief requires it.
- Flag plan-mandated defects separately from avoidable implementation defects.
- Identify any controller check that cannot be proven from the diff.
```

- [ ] **Step 4: Update implementer prompt for file-based handoff**

In `templates/worker-prompts/implementer.md`, add this under `## Controller Requirements`:

```markdown
- Provide the task brief path under `FEATURE_DIR/implementation-review/task-briefs/<task-id>.md` when the runtime has written one.
- Tell the worker that the task brief and packet are the authoritative contract for the lane.
```

Add this under `## Minimum Return Payload`:

```markdown
- UI fidelity evidence when the packet's `ui_fidelity_requirements.applicable` is true.
- Evidence paths that the leader can cite from `implementation-review/review-packages/<task-id>.md`.
```

- [ ] **Step 5: Update implement command default review path**

In `templates/commands/implement.md`, replace the old required reviewer line with:

```markdown
   - **REQUIRED FOR SUBAGENT EXECUTION**: Use `.specify/templates/worker-prompts/implementer.md` as the default implementer subagent contract and use `.specify/templates/worker-prompts/task-reviewer.md` for ordinary post-task review. Legacy `.specify/templates/worker-prompts/spec-reviewer.md` and `.specify/templates/worker-prompts/code-quality-reviewer.md` remain installed for older downstream workflows and special migration/debug scenarios; do not run both legacy prompts and the new task reviewer for the same ordinary task review.
```

In the Audit Artifacts section, add:

```markdown
For every packetized implementation task accepted by `sp-implement`, maintain:

- `FEATURE_DIR/implementation-review/task-briefs/<task-id>.md`
- `FEATURE_DIR/implementation-review/review-packages/<task-id>.md`
- `FEATURE_DIR/implementation-review/task-reviews/<task-id>.json`
- `FEATURE_DIR/implementation-review/ledger.json`

After all tasks are accepted and before closeout, write `FEATURE_DIR/implementation-review/branch-review.md`.
```

Add task acceptance guidance:

```markdown
Task acceptance requires an accepted task review. A checked task is a claim; a ledger entry with `status: accepted` plus `task-reviews/<task-id>.json` is reviewed execution evidence.
```

- [ ] **Step 6: Update plan and task templates**

In `templates/commands/plan.md`, add guidance under implementation constitution or planning outputs:

```markdown
- Add `Global Constraints` when constraints materially affect implementation or review.
- Add `Task Interface Map` when task-level consumes/produces expectations are already known.
- Add `Review-Risk Notes` for plan-approved risks, manual checks, UI/reference fidelity risks, or quality tradeoffs that reviewers must not reconstruct from chat memory.
```

In `templates/plan-contract-template.json`, add these top-level keys:

```json
  "global_constraints": [],
  "task_interface_map": [],
  "review_risk_notes": [],
  "ui_design_inputs": []
```

Keep valid JSON by adding a comma after the previous property.

In `templates/tasks-template.md`, extend the enriched task example `Scope Boundaries` table with:

```markdown
| global_constraints | [Use project design tokens] |
| consumes | [SettingsRoute registration] |
| produces | [SettingsPanel component] |
| review_inputs | [DESIGN.md, ui-brief.md, ui-target.html] |
| review_risks | [visual comparison may require browser screenshot] |
| ui_fidelity_level | [high] |
| design_inputs | [DESIGN.md, ui-brief.md, ui-target.html] |
| ui_required_evidence | [screenshot_evidence, visual_comparison_evidence] |
| controller_checks_required | [human review if agent visual comparison is unavailable] |
```

In `templates/commands/tasks.md`, add the same packet field names to task-generation output guidance:

```markdown
- Carry `global_constraints`, `interfaces.consumes`, `interfaces.produces`, `review_inputs`, `review_risks`, `ui_fidelity_requirements`, and `controller_checks_required` into task packets when relevant.
```

- [ ] **Step 7: Update workflow state template**

In `templates/workflow-state-template.md`, under `implementation_review`, add:

```markdown
  - task_briefs: [implementation-review/task-briefs/]
  - review_packages: [implementation-review/review-packages/]
  - task_reviews: [implementation-review/task-reviews/]
  - ledger: [implementation-review/ledger.json]
  - branch_review: [implementation-review/branch-review.md]
```

- [ ] **Step 8: Mark legacy reviewer prompts**

At the top of both `templates/worker-prompts/spec-reviewer.md` and `templates/worker-prompts/code-quality-reviewer.md`, add:

```markdown
> Legacy compatibility prompt. New `sp-implement` ordinary task reviews use `.specify/templates/worker-prompts/task-reviewer.md`, which returns both `spec_verdict` and `quality_verdict` in one result.
```

- [ ] **Step 9: Update passive skill guidance**

In `templates/passive-skills/subagent-driven-development/SKILL.md`, replace the two-reviewer Process step with:

```markdown
5. **Review accepted work**: For ordinary `sp-implement` task review, use the single task reviewer. It returns `spec_verdict`, `quality_verdict`, controller checks, UI fidelity result, and final assessment. Legacy separate spec and quality reviewer prompts are compatibility assets, not the default path.
```

In `templates/passive-skills/spec-kit-workflow-routing/SKILL.md`, add routing guidance:

```markdown
- Route planned implementation to `sp-implement`; task review is embedded through task briefs, review packages, task reviews, ledger state, and branch review. Do not route to a separate public review command.
```

- [ ] **Step 10: Run focused alignment tests**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_implement_uses_single_task_reviewer_by_default tests/test_alignment_templates.py::test_task_reviewer_prompt_defines_dual_verdict_schema tests/test_alignment_templates.py::test_plan_tasks_and_workflow_state_carry_review_artifact_contract -q
```

Expected: selected tests pass.

- [ ] **Step 11: Commit**

Run:

```powershell
git add templates/commands/plan.md templates/commands/tasks.md templates/commands/implement.md templates/plan-contract-template.json templates/tasks-template.md templates/workflow-state-template.md templates/worker-prompts/implementer.md templates/worker-prompts/task-reviewer.md templates/worker-prompts/spec-reviewer.md templates/worker-prompts/code-quality-reviewer.md templates/passive-skills/subagent-driven-development/SKILL.md templates/passive-skills/spec-kit-workflow-routing/SKILL.md tests/test_alignment_templates.py
git commit -m "feat: teach generated workflows task review artifacts"
```

Expected: commit succeeds with only these files staged.

## Task 7: Update Packaging and Install Coverage

**Files:**

- Modify: `tests/integrations/test_cli.py`
- Modify: `tests/test_packaging_assets.py`
- Modify: `tests/test_alignment_templates.py`
- Modify: integration renderer tests under `tests/integrations/` only where they assert old review wording.

- [ ] **Step 1: Update CLI install test**

In `tests/integrations/test_cli.py`, near the existing worker prompt assertions around `prompt_dir`, add:

```python
        assert (prompt_dir / "task-reviewer.md").exists()
```

- [ ] **Step 2: Update packaging asset test**

In `tests/test_packaging_assets.py`, inside `test_install_shared_infra_copies_split_core_pack_template_dirs()`, add this setup line after the implementer prompt write:

```python
    (core_pack / "worker-prompts" / "task-reviewer.md").write_text("# Task Reviewer\n", encoding="utf-8")
```

Add this assertion near the implementer assertion:

```python
    assert (project_root / ".specify" / "templates" / "worker-prompts" / "task-reviewer.md").exists()
```

- [ ] **Step 3: Run install and packaging tests**

Run:

```powershell
pytest tests/integrations/test_cli.py::test_init_installs_shared_worker_prompts tests/test_packaging_assets.py::test_install_shared_infra_copies_split_core_pack_template_dirs -q
```

Expected: selected tests pass. If the exact integration test name differs, run `rg -n "worker-prompts" tests/integrations/test_cli.py` and use the test that contains the prompt-dir assertions.

- [ ] **Step 4: Update rendered integration assertions if needed**

Run:

```powershell
pytest tests/integrations -q
```

Expected: failures, if any, identify rendered command text that still expects the legacy reviewer pair. For each failure, update the assertion to expect `task-reviewer.md`, `spec_verdict`, and `quality_verdict`, while still asserting the legacy prompt files are installed.

- [ ] **Step 5: Commit**

Run:

```powershell
git add tests/integrations/test_cli.py tests/test_packaging_assets.py tests/test_alignment_templates.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_skills.py tests/integrations/test_integration_base_toml.py
git commit -m "test: assert task reviewer prompt packaging"
```

Expected: commit succeeds. If `tests/integrations` has no changes after Step 4, Git stages only the files changed in Steps 1 and 2.

## Task 8: Full Validation and Contract Sweep

**Files:**

- Read-only validation across source, templates, and tests.
- Modify only files with failures directly tied to this plan.

- [ ] **Step 1: Run the targeted execution suite**

Run:

```powershell
pytest tests/execution/test_implementation_review.py tests/execution/test_packet_schema.py tests/execution/test_packet_compiler.py tests/execution/test_packet_validator.py tests/execution/test_result_normalizer.py tests/execution/test_result_validator.py tests/execution/test_implement_resume_audit.py -q
```

Expected: all selected tests pass.

- [ ] **Step 2: Run template and packaging coverage**

Run:

```powershell
pytest tests/test_alignment_templates.py tests/test_packaging_assets.py tests/integrations/test_cli.py -q
```

Expected: all selected tests pass.

- [ ] **Step 3: Run hook and CLI contract coverage**

Run:

```powershell
pytest tests/contract/test_hook_cli_surface.py -q
```

Expected: all hook CLI contract tests pass.

- [ ] **Step 4: Run diff hygiene**

Run:

```powershell
git diff --check
```

Expected: no output and exit code `0`.

- [ ] **Step 5: Search for stale default reviewer wording**

Run:

```powershell
rg -n "pair post-implementation reviews|Skipping spec compliance review|Running code quality review before spec compliance|task-reviewer.md|spec_verdict|quality_verdict" templates tests src
```

Expected:

- No generated default guidance says ordinary task review pairs `spec-reviewer.md` and `code-quality-reviewer.md`.
- `task-reviewer.md`, `spec_verdict`, and `quality_verdict` appear in runtime or template guidance.
- Legacy prompt mentions appear only as compatibility guidance or install assertions.

- [ ] **Step 6: Review changed files**

Run:

```powershell
git status --short
git diff --stat HEAD
git diff --name-status HEAD
```

Expected: changed files are limited to the runtime, template, prompt, and test surfaces named in this plan.

- [ ] **Step 7: Commit final validation fixes if any**

If Step 1 through Step 6 required fixes, run:

```powershell
git add src/specify_cli/execution/implementation_review.py src/specify_cli/execution/packet_schema.py src/specify_cli/execution/packet_compiler.py src/specify_cli/execution/packet_validator.py src/specify_cli/execution/result_schema.py src/specify_cli/execution/result_normalizer.py src/specify_cli/execution/result_validator.py src/specify_cli/implement_audit.py src/specify_cli/implementation_summary.py src/specify_cli/hooks/artifact_validation.py src/specify_cli/hooks/state_validation.py templates/commands/plan.md templates/commands/tasks.md templates/commands/implement.md templates/plan-contract-template.json templates/tasks-template.md templates/workflow-state-template.md templates/worker-prompts/implementer.md templates/worker-prompts/task-reviewer.md templates/worker-prompts/spec-reviewer.md templates/worker-prompts/code-quality-reviewer.md templates/passive-skills/subagent-driven-development/SKILL.md templates/passive-skills/spec-kit-workflow-routing/SKILL.md tests/execution/test_implementation_review.py tests/execution/test_packet_schema.py tests/execution/test_packet_compiler.py tests/execution/test_packet_validator.py tests/execution/test_result_normalizer.py tests/execution/test_result_validator.py tests/execution/test_implement_resume_audit.py tests/contract/test_hook_cli_surface.py tests/test_alignment_templates.py tests/integrations/test_cli.py tests/test_packaging_assets.py
git commit -m "test: validate sdd artifact review contract"
```

Expected: commit succeeds when there were validation fixes. If there were no fixes, skip this commit.

## Execution Order

1. Task 1 locks the artifact paths, task review schema, acceptance rules, and ledger helpers.
2. Task 2 extends packet and result contracts without changing the public workflow command chain.
3. Task 3 makes `sp-tasks` packet compilation populate the new fields.
4. Task 4 makes resume audit and closeout trust accepted reviews rather than checked boxes alone.
5. Task 5 adds hook-level validation for packetized terminal state.
6. Task 6 updates generated command, prompt, passive skill, and state templates.
7. Task 7 verifies packaged install behavior across generated projects.
8. Task 8 runs the cross-surface validation sweep.

## Self-Review

Spec coverage:

- Artifact layout is covered by Task 1, Task 4, Task 5, and Task 6.
- Single task reviewer and dual verdicts are covered by Task 1 and Task 6.
- Packet fields for global constraints, interfaces, review inputs, review risks, UI fidelity, and controller checks are covered by Task 2 and Task 3.
- Resume and closeout behavior are covered by Task 4 and Task 5.
- Legacy reviewer compatibility is covered by Task 6 and Task 7.
- Packaging and cross-integration installation are covered by Task 7.
- UI fidelity evidence is covered by Task 2, Task 3, Task 4, and Task 6.

Type consistency:

- `TaskReviewRecord`, `TaskReviewFinding`, `TaskLedgerEntry`, `PacketInterfaces`, and `UiFidelityRequirements` are introduced before later tasks use them.
- The packet remains `packet_version=2` for compatibility because the new fields are optional and ignored by older consumers.
- Review artifact paths consistently live under `FEATURE_DIR/implementation-review/`.

Validation commands:

- Runtime: `pytest tests/execution/test_implementation_review.py tests/execution/test_packet_schema.py tests/execution/test_packet_compiler.py tests/execution/test_packet_validator.py tests/execution/test_result_normalizer.py tests/execution/test_result_validator.py tests/execution/test_implement_resume_audit.py -q`
- Templates and packaging: `pytest tests/test_alignment_templates.py tests/test_packaging_assets.py tests/integrations/test_cli.py -q`
- Hooks: `pytest tests/contract/test_hook_cli_surface.py -q`
- Hygiene: `git diff --check`
