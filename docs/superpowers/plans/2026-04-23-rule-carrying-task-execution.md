# Rule-Carrying Task Execution Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a shared hard-fail rule-carrying execution contract so delegated workers execute from compiled task packets instead of raw task text, then wire that contract through templates, Codex guidance, and sidecar runtime state.

**Architecture:** Implement this in five layers. First, lock the packet contract in focused tests and template assertions. Second, add a new shared `src/specify_cli/execution/` package for packet and result schemas, compilation, validation, and rendering. Third, extend Codex sidecar/runtime records so dispatched work can persist compiled packets and completion evidence. Fourth, rewrite `plan`, `tasks`, `implement`, and `analyze` templates plus Codex skill augmentation so native delegation and sidecar fallback both require validated packets. Fifth, update docs and run a focused regression suite.

**Tech Stack:** Python, dataclasses, Markdown templates, Typer-generated integration surfaces, JSON runtime state, pytest

---

## File Structure

### New shared execution package

- Create: `src/specify_cli/execution/__init__.py`
  - Public exports for packet compilation and validation helpers.
- Create: `src/specify_cli/execution/packet_schema.py`
  - Canonical `WorkerTaskPacket` dataclasses plus nested rule/reference/result types.
- Create: `src/specify_cli/execution/packet_compiler.py`
  - Shared compiler that reads `constitution.md`, `plan.md`, and `tasks.md` to build packets.
- Create: `src/specify_cli/execution/packet_validator.py`
  - Hard-fail validation for packet completeness and rule-carry guarantees.
- Create: `src/specify_cli/execution/packet_renderer.py`
  - Integration-neutral rendering helpers for prompt-safe packet formatting.
- Create: `src/specify_cli/execution/result_schema.py`
  - Canonical delegated worker result dataclasses.
- Create: `src/specify_cli/execution/result_validator.py`
  - Join-point verification against packet expectations.

### Existing runtime and integration surfaces

- Modify: `src/specify_cli/codex_team/manifests.py`
  - Persist packet metadata or packet artifact references alongside task and batch records.
- Modify: `src/specify_cli/codex_team/runtime_state.py`
  - Extend dispatch records to carry packet/result artifacts.
- Modify: `src/specify_cli/codex_team/worker_bootstrap.py`
  - Include packet-backed execution contract fields in bootstrap instructions.
- Modify: `src/specify_cli/codex_team/auto_dispatch.py`
  - Require packet compilation before sidecar worker launch.
- Modify: `src/specify_cli/integrations/codex/__init__.py`
  - Teach generated Codex skills to compile, validate, and dispatch from packets rather than raw task text.

### Shared planning templates and docs

- Modify: `templates/plan-template.md`
  - Add `Dispatch Compilation Hints`.
- Modify: `templates/tasks-template.md`
  - Add task-level guardrail mapping guidance and packet-friendly metadata expectations.
- Modify: `templates/commands/plan.md`
  - Require planners to populate compilation hints and task-relevant quality floor data.
- Modify: `templates/commands/tasks.md`
  - Require a guardrail registry or equivalent packet-compilation anchor.
- Modify: `templates/commands/implement.md`
  - Require validated packet compilation before dispatch.
- Modify: `templates/commands/analyze.md`
  - Add `DP1`, `DP2`, and `DP3` checks.
- Modify: `README.md`
  - Document packet-based delegated execution.
- Modify: `docs/quickstart.md`
  - Update the workflow guidance to mention compiled worker packets.

### Tests

- Create: `tests/execution/test_packet_schema.py`
- Create: `tests/execution/test_packet_validator.py`
- Create: `tests/execution/test_packet_compiler.py`
- Create: `tests/execution/test_result_validator.py`
- Create: `tests/codex_team/test_worker_bootstrap.py`
- Modify: `tests/codex_team/test_auto_dispatch.py`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_extension_skills.py`
- Modify: `tests/integrations/test_integration_codex.py`
- Modify: `tests/test_specify_guidance_docs.py`

---

### Task 1: Lock the rule-carrying packet contract in tests

**Files:**
- Create: `tests/execution/test_packet_schema.py`
- Create: `tests/execution/test_packet_validator.py`
- Create: `tests/execution/test_packet_compiler.py`
- Create: `tests/execution/test_result_validator.py`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_extension_skills.py`
- Modify: `tests/integrations/test_integration_codex.py`

- [ ] **Step 1: Add failing unit tests for packet and result schemas**

Create `tests/execution/test_packet_schema.py` with exact assertions like:

```python
from specify_cli.execution.packet_schema import (
    DispatchPolicy,
    PacketReference,
    PacketScope,
    WorkerTaskPacket,
)
from specify_cli.execution.result_schema import ValidationResult, WorkerTaskResult


def test_worker_task_packet_captures_required_execution_contract() -> None:
    packet = WorkerTaskPacket(
        feature_id="001-feature",
        task_id="T017",
        story_id="US1",
        objective="Implement auth flow",
        scope=PacketScope(
            write_scope=["src/services/auth_service.py"],
            read_scope=["src/contracts/auth.py"],
        ),
        required_references=[
            PacketReference(
                path="src/contracts/auth.py",
                reason="public contract compatibility must be preserved",
            )
        ],
        hard_rules=["Every public function changed must have tests"],
        forbidden_drift=["Do not create a parallel auth stack"],
        validation_gates=["pytest tests/unit/test_auth_service.py -q"],
        done_criteria=["login/logout behavior implemented"],
        handoff_requirements=["return changed files"],
        dispatch_policy=DispatchPolicy(mode="hard_fail", must_acknowledge_rules=True),
    )

    assert packet.packet_version == 1
    assert packet.scope.write_scope == ["src/services/auth_service.py"]
    assert packet.dispatch_policy.mode == "hard_fail"


def test_worker_task_result_requires_validation_records() -> None:
    result = WorkerTaskResult(
        task_id="T017",
        status="success",
        changed_files=["src/services/auth_service.py"],
        validation_results=[
            ValidationResult(
                command="pytest tests/unit/test_auth_service.py -q",
                status="passed",
            )
        ],
        summary="Implemented auth flow",
    )

    assert result.status == "success"
    assert result.validation_results[0].status == "passed"
```

- [ ] **Step 2: Add failing validator and compiler tests**

Create `tests/execution/test_packet_validator.py` and `tests/execution/test_packet_compiler.py` with coverage like:

```python
import pytest

from specify_cli.execution.packet_compiler import compile_worker_task_packet
from specify_cli.execution.packet_validator import PacketValidationError, validate_worker_task_packet


def test_validate_worker_task_packet_rejects_missing_required_references(sample_packet) -> None:
    sample_packet.required_references = []

    with pytest.raises(PacketValidationError) as exc:
        validate_worker_task_packet(sample_packet)

    assert exc.value.code == "DP2"


def test_compile_worker_task_packet_merges_constitution_plan_and_task_sources(tmp_path) -> None:
    project_root = tmp_path / "project"
    feature_dir = project_root / "specs" / "001-test-feature"
    feature_dir.mkdir(parents=True)
    (project_root / ".specify" / "memory").mkdir(parents=True)
    (project_root / ".specify" / "memory" / "constitution.md").write_text(
        "# Constitution\n\n- MUST add tests for public behavior\n",
        encoding="utf-8",
    )
    (feature_dir / "plan.md").write_text(
        "## Implementation Constitution\n\n### Required Implementation References\n\n- `src/contracts/auth.py`\n\n### Forbidden Implementation Drift\n\n- Do not create a parallel auth stack\n",
        encoding="utf-8",
    )
    (feature_dir / "tasks.md").write_text(
        "- [ ] T017 [US1] Implement auth flow in src/services/auth_service.py\n",
        encoding="utf-8",
    )

    packet = compile_worker_task_packet(
        project_root=project_root,
        feature_dir=feature_dir,
        task_id="T017",
    )

    assert packet.task_id == "T017"
    assert "src/contracts/auth.py" in [ref.path for ref in packet.required_references]
    assert any("public behavior" in rule.lower() for rule in packet.hard_rules)
```

- [ ] **Step 3: Add failing template and generated-skill assertions**

Update `tests/test_alignment_templates.py`, `tests/test_extension_skills.py`, and `tests/integrations/test_integration_codex.py` so they assert:

```python
assert "Dispatch Compilation Hints" in plan_template
assert "Task Guardrail Index" in tasks_template
assert "dispatch only from validated `WorkerTaskPacket`" in implement_template
assert "DP1" in analyze_template
assert "DP2" in analyze_template
assert "DP3" in analyze_template
assert "compile and validate the packet before any delegated work begins" in implement_skill
assert "must not dispatch from raw task text alone" in implement_skill.lower()
```

- [ ] **Step 4: Run the focused red suite**

Run:

```powershell
pytest tests/execution/test_packet_schema.py `
  tests/execution/test_packet_validator.py `
  tests/execution/test_packet_compiler.py `
  tests/execution/test_result_validator.py `
  tests/test_alignment_templates.py `
  tests/test_extension_skills.py `
  tests/integrations/test_integration_codex.py -q
```

Expected:

- import failures for the new `specify_cli.execution` package
- template assertion failures for missing packet language
- Codex integration test failures for missing packet guidance

- [ ] **Step 5: Commit the red contract**

```bash
git add tests/execution/test_packet_schema.py tests/execution/test_packet_validator.py tests/execution/test_packet_compiler.py tests/execution/test_result_validator.py tests/test_alignment_templates.py tests/test_extension_skills.py tests/integrations/test_integration_codex.py
git commit -m "test: lock rule-carrying packet contract"
```

### Task 2: Add the shared execution packet and result modules

**Files:**
- Create: `src/specify_cli/execution/__init__.py`
- Create: `src/specify_cli/execution/packet_schema.py`
- Create: `src/specify_cli/execution/packet_validator.py`
- Create: `src/specify_cli/execution/result_schema.py`
- Create: `src/specify_cli/execution/result_validator.py`
- Create: `tests/execution/test_packet_schema.py`
- Create: `tests/execution/test_packet_validator.py`
- Create: `tests/execution/test_result_validator.py`

- [ ] **Step 1: Implement the packet dataclasses**

Create `src/specify_cli/execution/packet_schema.py` around these exact shapes:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


PacketMode = Literal["hard_fail"]


@dataclass(slots=True)
class PacketReference:
    path: str
    reason: str


@dataclass(slots=True)
class PacketScope:
    write_scope: list[str] = field(default_factory=list)
    read_scope: list[str] = field(default_factory=list)


@dataclass(slots=True)
class DispatchPolicy:
    mode: PacketMode = "hard_fail"
    must_acknowledge_rules: bool = True


@dataclass(slots=True)
class WorkerTaskPacket:
    feature_id: str
    task_id: str
    story_id: str
    objective: str
    scope: PacketScope
    required_references: list[PacketReference]
    hard_rules: list[str]
    forbidden_drift: list[str]
    validation_gates: list[str]
    done_criteria: list[str]
    handoff_requirements: list[str]
    dispatch_policy: DispatchPolicy = field(default_factory=DispatchPolicy)
    packet_version: int = 1
```

- [ ] **Step 2: Implement the result dataclasses**

Create `src/specify_cli/execution/result_schema.py` like:

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


WorkerStatus = Literal["success", "blocked", "failed"]
ValidationStatus = Literal["passed", "failed", "skipped"]


@dataclass(slots=True)
class ValidationResult:
    command: str
    status: ValidationStatus
    output: str = ""


@dataclass(slots=True)
class RuleAcknowledgement:
    required_references_read: bool = False
    forbidden_drift_respected: bool = False


@dataclass(slots=True)
class WorkerTaskResult:
    task_id: str
    status: WorkerStatus
    changed_files: list[str] = field(default_factory=list)
    validation_results: list[ValidationResult] = field(default_factory=list)
    summary: str = ""
    blockers: list[str] = field(default_factory=list)
    rule_acknowledgement: RuleAcknowledgement = field(default_factory=RuleAcknowledgement)
```

- [ ] **Step 3: Implement hard-fail validators**

Create `src/specify_cli/execution/packet_validator.py` and `src/specify_cli/execution/result_validator.py` with code like:

```python
from dataclasses import dataclass

from .packet_schema import WorkerTaskPacket
from .result_schema import WorkerTaskResult


@dataclass(slots=True)
class PacketValidationError(ValueError):
    code: str
    message: str

    def __post_init__(self) -> None:
        super().__init__(self.message)


def validate_worker_task_packet(packet: WorkerTaskPacket) -> WorkerTaskPacket:
    if not packet.scope.write_scope:
        raise PacketValidationError("DP1", "write_scope is required for delegated execution")
    if not packet.required_references:
        raise PacketValidationError("DP2", "required_references must be compiled into the packet")
    if not packet.hard_rules:
        raise PacketValidationError("DP1", "hard_rules must be present in the packet")
    if not packet.validation_gates:
        raise PacketValidationError("DP1", "validation_gates must be present in the packet")
    if not packet.done_criteria:
        raise PacketValidationError("DP1", "done_criteria must be present in the packet")
    return packet


def validate_worker_task_result(result: WorkerTaskResult, packet: WorkerTaskPacket) -> WorkerTaskResult:
    if packet.dispatch_policy.must_acknowledge_rules:
        if not result.rule_acknowledgement.required_references_read:
            raise PacketValidationError("DP3", "worker did not acknowledge required references")
        if not result.rule_acknowledgement.forbidden_drift_respected:
            raise PacketValidationError("DP3", "worker did not acknowledge forbidden drift")
    if packet.validation_gates and not result.validation_results:
        raise PacketValidationError("DP3", "worker result is missing validation evidence")
    return result
```

- [ ] **Step 4: Export the public API and make the tests green**

Set `src/specify_cli/execution/__init__.py` to export the packet and validator helpers:

```python
from .packet_schema import DispatchPolicy, PacketReference, PacketScope, WorkerTaskPacket
from .packet_validator import PacketValidationError, validate_worker_task_packet
from .result_schema import RuleAcknowledgement, ValidationResult, WorkerTaskResult
from .result_validator import validate_worker_task_result

__all__ = [
    "DispatchPolicy",
    "PacketReference",
    "PacketScope",
    "PacketValidationError",
    "RuleAcknowledgement",
    "ValidationResult",
    "WorkerTaskPacket",
    "WorkerTaskResult",
    "validate_worker_task_packet",
    "validate_worker_task_result",
]
```

Run:

```powershell
pytest tests/execution/test_packet_schema.py tests/execution/test_packet_validator.py tests/execution/test_result_validator.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/execution/__init__.py src/specify_cli/execution/packet_schema.py src/specify_cli/execution/packet_validator.py src/specify_cli/execution/result_schema.py src/specify_cli/execution/result_validator.py tests/execution/test_packet_schema.py tests/execution/test_packet_validator.py tests/execution/test_result_validator.py
git commit -m "feat: add shared worker packet and result contracts"
```

### Task 3: Implement packet compilation from constitution, plan, and tasks

**Files:**
- Create: `src/specify_cli/execution/packet_compiler.py`
- Modify: `src/specify_cli/execution/__init__.py`
- Create: `tests/execution/test_packet_compiler.py`

- [ ] **Step 1: Implement section and bullet extraction helpers**

Create `src/specify_cli/execution/packet_compiler.py` with parsers built around exact helper shapes like:

```python
from __future__ import annotations

import re
from pathlib import Path

from .packet_schema import DispatchPolicy, PacketReference, PacketScope, WorkerTaskPacket
from .packet_validator import validate_worker_task_packet


SECTION_RE = re.compile(r"(?ms)^##? (?P<title>.+?)\n(?P<body>.*?)(?=^##? |\Z)")
BULLET_RE = re.compile(r"(?m)^\s*-\s+`?(?P<value>.+?)`?\s*$")
TASK_RE = re.compile(r"(?m)^\s*-\s\[[ xX]\]\s(?P<task_id>T\d+)(?P<body>.+)$")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def _section_body(text: str, title: str) -> str:
    for match in SECTION_RE.finditer(text):
        if match.group("title").strip().lower() == title.strip().lower():
            return match.group("body").strip()
    return ""


def _bullet_values(text: str) -> list[str]:
    return [match.group("value").strip() for match in BULLET_RE.finditer(text)]
```

- [ ] **Step 2: Compile packet fields from the three canonical sources**

Add a compiler entrypoint like:

```python
def compile_worker_task_packet(*, project_root: Path, feature_dir: Path, task_id: str) -> WorkerTaskPacket:
    constitution_text = _read(project_root / ".specify" / "memory" / "constitution.md")
    plan_text = _read(feature_dir / "plan.md")
    tasks_text = _read(feature_dir / "tasks.md")

    task_match = next(match for match in TASK_RE.finditer(tasks_text) if match.group("task_id") == task_id)
    task_body = task_match.group("body").strip()
    objective = task_body

    required_references = [
        PacketReference(path=value, reason="compiled from Required Implementation References")
        for value in _bullet_values(_section_body(plan_text, "Required Implementation References"))
    ]
    forbidden_drift = _bullet_values(_section_body(plan_text, "Forbidden Implementation Drift"))
    hard_rules = _bullet_values(constitution_text) + _bullet_values(_section_body(tasks_text, "Planning Inputs"))
    validation_gates = _bullet_values(_section_body(tasks_text, "Validation Gates"))
    if not validation_gates:
        validation_gates = [f"pytest -q -k {task_id.lower()}"]

    packet = WorkerTaskPacket(
        feature_id=feature_dir.name,
        task_id=task_id,
        story_id=_story_id_from_task_body(task_body),
        objective=objective,
        scope=PacketScope(write_scope=_paths_from_task_body(task_body), read_scope=[ref.path for ref in required_references]),
        required_references=required_references,
        hard_rules=hard_rules,
        forbidden_drift=forbidden_drift,
        validation_gates=validation_gates,
        done_criteria=[objective],
        handoff_requirements=["return changed files", "return validation results", "return blockers"],
        dispatch_policy=DispatchPolicy(mode="hard_fail", must_acknowledge_rules=True),
    )
    return validate_worker_task_packet(packet)
```

Use exact helpers for `_story_id_from_task_body()` and `_paths_from_task_body()`:

```python
def _story_id_from_task_body(task_body: str) -> str:
    match = re.search(r"\[(US\d+)\]", task_body)
    return match.group(1) if match else "UNASSIGNED"


def _paths_from_task_body(task_body: str) -> list[str]:
    return re.findall(r"(?:^| )(?:[A-Za-z0-9_./-]+/[A-Za-z0-9_./-]+)", task_body)
```

- [ ] **Step 3: Make compiler tests green**

Run:

```powershell
pytest tests/execution/test_packet_compiler.py -q
```

Expected: PASS.

- [ ] **Step 4: Export the compiler**

Update `src/specify_cli/execution/__init__.py`:

```python
from .packet_compiler import compile_worker_task_packet
```

and add it to `__all__`.

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/execution/__init__.py src/specify_cli/execution/packet_compiler.py tests/execution/test_packet_compiler.py
git commit -m "feat: compile worker packets from planning artifacts"
```

### Task 4: Carry packet artifacts through Codex sidecar/runtime state

**Files:**
- Modify: `src/specify_cli/codex_team/runtime_state.py`
- Modify: `src/specify_cli/codex_team/manifests.py`
- Modify: `src/specify_cli/codex_team/worker_bootstrap.py`
- Modify: `src/specify_cli/codex_team/auto_dispatch.py`
- Create: `tests/codex_team/test_worker_bootstrap.py`
- Modify: `tests/codex_team/test_auto_dispatch.py`

- [ ] **Step 1: Extend dispatch and batch records to carry packet artifacts**

Update `src/specify_cli/codex_team/runtime_state.py` so `DispatchRecord` includes:

```python
@dataclass(slots=True)
class DispatchRecord:
    request_id: str
    target_worker: str
    status: str = "pending"
    reason: str = ""
    failure_class: str = ""
    retry_count: int = 0
    retry_budget: int = 0
    packet_path: str = ""
    packet_summary: dict[str, object] | None = None
    result_path: str = ""
    created_at: str = ""
    updated_at: str = ""
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        now = _utc_now()
        if self.packet_summary is None:
            self.packet_summary = {}
        if not self.created_at:
            self.created_at = now
        if not self.updated_at:
            self.updated_at = now
```

Update `src/specify_cli/codex_team/manifests.py` so `TaskRecord.metadata` defaults can persist:

```python
metadata={
    "packet": {
        "task_id": task_id,
        "feature_id": feature_id,
        "required_references": [ref.path for ref in packet.required_references],
        "validation_gates": packet.validation_gates,
    }
}
```

- [ ] **Step 2: Add bootstrap instructions that expose packet-backed constraints**

Update `src/specify_cli/codex_team/worker_bootstrap.py` so `build_worker_bootstrap_payload()` appends lines like:

```python
if additional_metadata:
    packet_summary = additional_metadata.get("packet_summary", "")
    required_refs = additional_metadata.get("required_references", "")
    forbidden_drift = additional_metadata.get("forbidden_drift", "")
    validation_gates = additional_metadata.get("validation_gates", "")
    instructions_parts.extend(
        [
            f"packet_summary: {packet_summary}",
            f"required_references: {required_refs}",
            f"forbidden_drift: {forbidden_drift}",
            f"validation_gates: {validation_gates}",
            "hard rule: do not execute from raw task text alone",
        ]
    )
```

Create `tests/codex_team/test_worker_bootstrap.py` to assert those lines appear.

- [ ] **Step 3: Require packet compilation before sidecar worker launch**

Modify `src/specify_cli/codex_team/auto_dispatch.py` to compile the packet inside `route_ready_parallel_batch()` and persist it before `launch_dispatched_worker()`:

```python
from specify_cli.execution import compile_worker_task_packet


packet = compile_worker_task_packet(
    project_root=project_root,
    feature_dir=feature_dir,
    task_id=task_id,
)
packet_path = codex_team_state_root(project_root) / "packets" / f"{request_id}.json"
write_json(packet_path, asdict(packet))
dispatch_runtime_task(
    project_root,
    session_id=session_id,
    request_id=request_id,
    target_worker=task_id.lower(),
    reason="parallel-batch-dispatch",
    packet_path=str(packet_path),
    packet_summary={
        "task_id": packet.task_id,
        "objective": packet.objective,
        "write_scope": packet.scope.write_scope,
    },
)
```

Update `tests/codex_team/test_auto_dispatch.py` to assert:

```python
dispatch_payload = json.loads(dispatch_record_path(project_root, request_id).read_text(encoding="utf-8"))
assert dispatch_payload["packet_path"]
assert dispatch_payload["packet_summary"]["task_id"] == "T002"
```

- [ ] **Step 4: Run the focused Codex team tests**

Run:

```powershell
pytest tests/codex_team/test_worker_bootstrap.py tests/codex_team/test_auto_dispatch.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/codex_team/runtime_state.py src/specify_cli/codex_team/manifests.py src/specify_cli/codex_team/worker_bootstrap.py src/specify_cli/codex_team/auto_dispatch.py tests/codex_team/test_worker_bootstrap.py tests/codex_team/test_auto_dispatch.py
git commit -m "feat: carry worker packets through codex runtime dispatch"
```

### Task 5: Rewrite templates and Codex skill generation around validated packets

**Files:**
- Modify: `templates/plan-template.md`
- Modify: `templates/tasks-template.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/commands/implement.md`
- Modify: `templates/commands/analyze.md`
- Modify: `src/specify_cli/integrations/codex/__init__.py`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_extension_skills.py`
- Modify: `tests/integrations/test_integration_codex.py`

- [ ] **Step 1: Add packet-compilation sections to the shared templates**

Update `templates/plan-template.md` to include:

```markdown
## Dispatch Compilation Hints

### Boundary Owner

- [Truth-owning module, service, boundary, or adapter]

### Required Packet References

- [File every delegated worker must inspect before changing this area]

### Packet Validation Gates

- [Command that must run before the worker can claim completion]

### Task-Level Quality Floor

- [Feature-specific quality rule that every delegated worker must inherit]
```

Update `templates/tasks-template.md` to add a `Task Guardrail Index` section:

```markdown
## Task Guardrail Index

- `T000` -> `G-READ-REFERENCES`, `G-BOUNDARY-CONFIRM`
- `T017` -> `G-PRESERVE-BOUNDARY`, `G-VALIDATE-AUTH`, `G-NO-PARALLEL-STACK`
```

- [ ] **Step 2: Rewrite the command templates to require packet compilation**

Update `templates/commands/plan.md` with exact guidance like:

```markdown
- Add `Dispatch Compilation Hints` whenever delegated execution would be unsafe without explicit boundary owner, required references, validation gates, or quality-floor rules.
```

Update `templates/commands/tasks.md` with exact guidance like:

```markdown
- Generate a `Task Guardrail Index` or equivalent task-to-guardrail mapping so delegated execution can compile task-local hard rules without copying the full constitution into every task body.
```

Update `templates/commands/implement.md` with:

```markdown
- Before dispatching a concrete implementation batch, compile a `WorkerTaskPacket` for each delegated task.
- Validate each packet before dispatch.
- Dispatch only from validated `WorkerTaskPacket`.
- Do not dispatch from raw task text alone.
```

Update `templates/commands/analyze.md` to add:

```markdown
- `DP1`: dispatch payload missing compiled hard rules
- `DP2`: dispatch payload missing required references or forbidden drift
- `DP3`: child completion missing required validation evidence
```

- [ ] **Step 3: Rewrite Codex integration addenda so native delegation uses packets**

Update `src/specify_cli/integrations/codex/__init__.py` so the generated `sp-implement` skill includes exact lines like:

```python
"- Before any delegated implementation work starts, compile a `WorkerTaskPacket` for the current task or batch item and validate it.\n"
"- `spawn_agent` lanes must receive the compiled packet summary, required references, forbidden drift, validation gates, and done criteria.\n"
"- Do not dispatch native workers from raw task text alone.\n"
"- If packet compilation fails, stop and repair the planning artifacts instead of improvising.\n"
```

Also update the generated `sp-plan`, `sp-tasks`, and `sp-analyze` skills so the new packet sections appear in generated outputs.

- [ ] **Step 4: Run template and integration tests**

Run:

```powershell
pytest tests/test_alignment_templates.py `
  tests/test_extension_skills.py `
  tests/integrations/test_integration_codex.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add templates/plan-template.md templates/tasks-template.md templates/commands/plan.md templates/commands/tasks.md templates/commands/implement.md templates/commands/analyze.md src/specify_cli/integrations/codex/__init__.py tests/test_alignment_templates.py tests/test_extension_skills.py tests/integrations/test_integration_codex.py
git commit -m "feat: require validated worker packets in templates and codex guidance"
```

### Task 6: Update docs, run the focused regression suite, and close the slice

**Files:**
- Modify: `README.md`
- Modify: `docs/quickstart.md`
- Modify: `docs/superpowers/specs/2026-04-23-rule-carrying-task-execution-design.md`
- Modify: `docs/superpowers/plans/2026-04-23-rule-carrying-task-execution.md`

- [ ] **Step 1: Update user-facing docs**

Update `README.md` and `docs/quickstart.md` to include exact copy like:

```markdown
- Delegated execution should no longer rely on raw task text when architecture or quality rules matter.
- `plan` should provide `Dispatch Compilation Hints`.
- `tasks` should preserve a `Task Guardrail Index` or equivalent task-to-rule mapping.
- `implement` should compile and validate a `WorkerTaskPacket` before dispatching native workers or sidecar workers.
- `analyze` now also reports `DP1`, `DP2`, and `DP3` when rule-carrying execution breaks down.
```

- [ ] **Step 2: Run the focused end-to-end regression suite**

Run:

```powershell
pytest tests/execution/test_packet_schema.py `
  tests/execution/test_packet_validator.py `
  tests/execution/test_packet_compiler.py `
  tests/execution/test_result_validator.py `
  tests/codex_team/test_worker_bootstrap.py `
  tests/codex_team/test_auto_dispatch.py `
  tests/test_alignment_templates.py `
  tests/test_extension_skills.py `
  tests/integrations/test_integration_codex.py `
  tests/test_specify_guidance_docs.py -q
```

Expected:

- all packet-contract tests pass
- runtime dispatch tests pass
- generated-skill and template tests pass
- docs guidance tests pass

- [ ] **Step 3: Run one higher-level integration smoke check**

Run:

```powershell
pytest tests/integrations/test_cli.py -q
```

Expected: PASS or, if unrelated local changes are already breaking it, isolate and document the unrelated failure before continuing.

- [ ] **Step 4: Commit the docs and verification closeout**

```bash
git add README.md docs/quickstart.md
git commit -m "docs: describe rule-carrying delegated execution"
```

- [ ] **Step 5: Produce a final implementation summary**

Record in the final summary:

```markdown
- packet schema files added
- packet compiler and validators added
- Codex sidecar dispatch now persists packet artifacts
- templates now require validated `WorkerTaskPacket` dispatch
- docs updated with `DP1`/`DP2`/`DP3`
- focused pytest suites run and passed
```
