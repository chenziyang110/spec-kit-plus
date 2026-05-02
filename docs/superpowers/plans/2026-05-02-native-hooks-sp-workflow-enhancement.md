# Native Hook and `sp-*` Workflow Enhancement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a shared workflow policy and compaction layer for `sp-*` workflows, then wire it into Claude, Codex, and Gemini native hooks with balanced hard-block and advisory behavior.

**Architecture:** Extend the shared `specify hook ...` engine first so it can produce normalized workflow-policy outcomes and structured compaction artifacts. Then keep native adapters thin by translating those shared outcomes into Claude, Codex, and Gemini hook responses according to each integration's lifecycle depth.

**Tech Stack:** Python, Typer, pytest, project-local Claude and Gemini hook adapters, OMX Codex runtime TypeScript, Node test runner

---

## File Structure

### Shared Python Hook Core

- Modify: `src/specify_cli/hooks/types.py`
  - Extend `HookResult` so shared hooks can express workflow-policy and compaction metadata without breaking existing consumers.
- Modify: `src/specify_cli/hooks/events.py`
  - Register any new canonical events needed for workflow policy and compaction.
- Modify: `src/specify_cli/hooks/engine.py`
  - Wire new hook implementations into the shared registry.
- Create: `src/specify_cli/hooks/workflow_policy.py`
  - Central workflow-policy classification helpers and normalized outcome builders.
- Create: `src/specify_cli/hooks/compaction.py`
  - Structured compaction artifact generation, staleness checks, and resume-cue shaping.
- Modify: `src/specify_cli/hooks/checkpoint.py`
  - Reuse checkpoint data when building compaction artifacts instead of inventing a parallel source of truth.
- Modify: `src/specify_cli/hooks/context_monitor.py`
  - Add compaction refresh recommendations and machine-readable refresh triggers.
- Modify: `src/specify_cli/hooks/session_state.py`
  - Feed richer workflow-policy outcomes and recovery guidance for implement, quick, and debug.
- Modify: `src/specify_cli/hooks/statusline.py`
  - Keep the bounded session-start payload compact while exposing resume metadata needed by native adapters.
- Modify: `src/specify_cli/__init__.py`
  - Expose any new `specify hook ...` CLI commands or payload switches needed by the shared core.

### Claude and Gemini Adapters

- Modify: `src/specify_cli/integrations/claude/hooks/claude-hook-dispatch.py`
  - Translate shared workflow-policy and compaction outcomes into Claude-native responses.
- Modify: `src/specify_cli/integrations/claude/hooks/README.md`
  - Document the expanded managed Claude hook behavior.
- Modify: `src/specify_cli/integrations/gemini/hooks/gemini-hook-dispatch.py`
  - Translate shared workflow-policy and bounded compaction guidance into Gemini responses.
- Modify: `src/specify_cli/integrations/gemini/hooks/README.md`
  - Document Gemini's ingress-only lifecycle and compaction limitations.

### Codex Native Runtime

- Modify: `extensions/agent-teams/engine/src/hooks/specify-quality-adapter.ts`
  - Add shared workflow-policy and compaction invocation helpers for OMX.
- Modify: `extensions/agent-teams/engine/src/scripts/codex-native-pre-post.ts`
  - Extend shared pre/post tool evaluation to understand the new workflow-policy contract.
- Modify: `extensions/agent-teams/engine/src/scripts/codex-native-hook.ts`
  - Add SessionStart, UserPromptSubmit, PostToolUse, and Stop compaction and workflow-policy behavior.
- Modify: `extensions/agent-teams/engine/docs/codex-native-hooks.md`
  - Document new Codex behavior and bounded compaction injection rules.

### Tests

- Create: `tests/hooks/test_workflow_policy_hooks.py`
  - Python tests for workflow-policy classification and repairable-block decisions.
- Create: `tests/hooks/test_compaction_hooks.py`
  - Python tests for compaction generation, staleness checks, and resume-cue output.
- Modify: `tests/contract/test_hook_cli_surface.py`
  - Preserve JSON compatibility while asserting the new fields and hook commands.
- Modify: `tests/integrations/test_integration_claude.py`
  - Verify Claude adapter behavior for compaction and workflow-policy outputs.
- Create: `tests/integrations/test_integration_gemini.py`
  - Verify Gemini ingress-only behavior with the shared policy contract.
- Modify: `extensions/agent-teams/engine/src/hooks/__tests__/specify-quality-adapter.test.ts`
  - Verify Codex shared adapter helpers preserve existing block output semantics.
- Modify: `extensions/agent-teams/engine/src/scripts/__tests__/codex-native-hook.test.ts`
  - Verify Codex lifecycle behavior for SessionStart, UserPromptSubmit, PostToolUse, and Stop.

### Template and Documentation Follow-Through

- Modify: `README.md`
  - Update native hook capability documentation once behavior changes land.
- Modify: `tests/test_hook_template_guidance.py`
  - Ensure generated workflow guidance stays aligned with the new hook and compaction contract.
- Modify: `templates/commands/*.md` as needed in later tasks
  - Add explicit portable checkpoint and compaction references only after the shared and native core is stable.

## Task 1: Add Shared Workflow-Policy Types and Events

**Files:**
- Modify: `src/specify_cli/hooks/types.py`
- Modify: `src/specify_cli/hooks/events.py`
- Test: `tests/hooks/test_workflow_policy_hooks.py`

- [ ] **Step 1: Write the failing workflow-policy type tests**

```python
from specify_cli.hooks.types import HookResult


def test_hook_result_supports_repairable_block_status():
    result = HookResult(
        event="workflow.policy.evaluate",
        status="repairable-block",
        severity="warning",
    )
    payload = result.to_dict()
    assert payload["status"] == "repairable-block"


def test_hook_result_round_trips_policy_metadata():
    result = HookResult(
        event="workflow.policy.evaluate",
        status="warn",
        severity="warning",
        data={
            "policy": {
                "classification": "soft-enforced",
                "repairable": True,
                "compaction": {"stale": False},
            }
        },
    )
    payload = result.to_dict()
    assert payload["data"]["policy"]["classification"] == "soft-enforced"
    assert payload["data"]["policy"]["repairable"] is True
    assert payload["data"]["policy"]["compaction"]["stale"] is False
```

- [ ] **Step 2: Run the focused Python tests to verify they fail**

Run: `pytest tests/hooks/test_workflow_policy_hooks.py -q`
Expected: FAIL because `repairable-block` is not a valid `HookStatus` and the new test file does not exist yet

- [ ] **Step 3: Add the new hook status and policy-friendly data compatibility**

```python
HookStatus = Literal["ok", "warn", "blocked", "repaired", "repairable-block"]
```

Keep `HookResult.to_dict()` append-only so callers that only read existing keys continue to work.

- [ ] **Step 4: Add canonical events for workflow policy and compaction**

```python
WORKFLOW_POLICY_EVALUATE = "workflow.policy.evaluate"
WORKFLOW_COMPACTION_BUILD = "workflow.compaction.build"
WORKFLOW_COMPACTION_READ = "workflow.compaction.read"
```

Add these constants to `CANONICAL_HOOK_EVENTS` without removing existing events.

- [ ] **Step 5: Re-run the focused Python tests**

Run: `pytest tests/hooks/test_workflow_policy_hooks.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/specify_cli/hooks/types.py src/specify_cli/hooks/events.py tests/hooks/test_workflow_policy_hooks.py
git commit -m "feat: add workflow policy hook result types"
```

## Task 2: Implement the Shared Workflow-Policy Core

**Files:**
- Create: `src/specify_cli/hooks/workflow_policy.py`
- Modify: `src/specify_cli/hooks/engine.py`
- Test: `tests/hooks/test_workflow_policy_hooks.py`

- [ ] **Step 1: Write failing workflow-policy engine tests**

```python
from pathlib import Path

from specify_cli.hooks.engine import run_quality_hook


def test_workflow_policy_marks_missing_state_as_repairable_block(tmp_path: Path):
    project = tmp_path / "policy-project"
    project.mkdir()
    (project / ".specify").mkdir()
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)

    result = run_quality_hook(
        project,
        "workflow.policy.evaluate",
        {"command_name": "implement", "feature_dir": str(feature_dir), "trigger": "pre_tool"},
    )

    assert result.status == "repairable-block"
    assert any("workflow-state.md" in action for action in result.actions)


def test_workflow_policy_denies_explicit_phase_jump(tmp_path: Path):
    project = tmp_path / "policy-project"
    project.mkdir()
    (project / ".specify").mkdir()
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    (feature_dir / "workflow-state.md").write_text(
        "\n".join(
            [
                "# Workflow State: Demo",
                "",
                "## Current Command",
                "",
                "- active_command: `sp-specify`",
                "- status: `active`",
                "",
                "## Phase Mode",
                "",
                "- phase_mode: `design-only`",
                "- summary: demo",
                "",
                "## Next Command",
                "",
                "- `/sp.plan`",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.policy.evaluate",
        {
            "command_name": "specify",
            "feature_dir": str(feature_dir),
            "trigger": "prompt",
            "requested_action": "jump_to_implement",
        },
    )

    assert result.status == "blocked"
    assert any("phase" in error.lower() for error in result.errors)
```

- [ ] **Step 2: Run the focused tests**

Run: `pytest tests/hooks/test_workflow_policy_hooks.py -q`
Expected: FAIL because `workflow.policy.evaluate` is not implemented yet

- [ ] **Step 3: Create the shared workflow-policy module**

Implement `src/specify_cli/hooks/workflow_policy.py` with:

```python
from __future__ import annotations

from pathlib import Path

from .events import WORKFLOW_POLICY_EVALUATE
from .session_state import session_state_hook
from .state_validation import validate_state_hook
from .types import HookResult, QualityHookError


def workflow_policy_hook(project_root: Path, payload: dict[str, object]) -> HookResult:
    command_name = str(payload.get("command_name") or "").strip().lower()
    trigger = str(payload.get("trigger") or "unknown").strip().lower()
    requested_action = str(payload.get("requested_action") or "").strip().lower()

    if not command_name:
        raise QualityHookError("command_name is required")

    if command_name in {"implement", "quick", "debug"}:
        state_result = session_state_hook(project_root, payload)
        if state_result.status == "blocked":
            return HookResult(
                event=WORKFLOW_POLICY_EVALUATE,
                status="repairable-block",
                severity="warning",
                actions=[*state_result.errors, "repair the resumable workflow state before continuing"],
                data={
                    "policy": {
                        "classification": "soft-enforced",
                        "trigger": trigger,
                        "repairable": True,
                    }
                },
            )

    if "jump" in requested_action and command_name in {"specify", "plan", "tasks", "analyze"}:
        return HookResult(
            event=WORKFLOW_POLICY_EVALUATE,
            status="blocked",
            severity="critical",
            errors=["requested action attempts to skip required workflow phases"],
            data={
                "policy": {
                    "classification": "hard-blockable",
                    "trigger": trigger,
                    "repairable": False,
                }
            },
        )

    state_result = validate_state_hook(project_root, payload)
    if state_result.status == "blocked":
        return HookResult(
            event=WORKFLOW_POLICY_EVALUATE,
            status="repairable-block",
            severity="warning",
            actions=[*state_result.errors, "rebuild or resume the required workflow-state artifact before continuing"],
            data={
                "policy": {
                    "classification": "soft-enforced",
                    "trigger": trigger,
                    "repairable": True,
                }
            },
        )

    return HookResult(
        event=WORKFLOW_POLICY_EVALUATE,
        status="ok",
        severity="info",
        data={
            "policy": {
                "classification": "allow",
                "trigger": trigger,
                "repairable": False,
            }
        },
    )
```

Minimum behavior for the first pass:

- normalize the command name and trigger
- call existing state/session validators where appropriate
- emit `repairable-block` when required workflow state is missing but recoverable
- emit `blocked` only for explicit high-risk jumps or unrepairable contradictions
- return structured `data["policy"]` with classification and repair hints

- [ ] **Step 4: Register the new hook in the shared engine**

Add the workflow-policy hook to `_HOOK_REGISTRY` in `src/specify_cli/hooks/engine.py`.

- [ ] **Step 5: Re-run the focused workflow-policy tests**

Run: `pytest tests/hooks/test_workflow_policy_hooks.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/specify_cli/hooks/workflow_policy.py src/specify_cli/hooks/engine.py tests/hooks/test_workflow_policy_hooks.py
git commit -m "feat: add shared workflow policy hook"
```

## Task 3: Add Structured Compaction Artifacts

**Files:**
- Create: `src/specify_cli/hooks/compaction.py`
- Modify: `src/specify_cli/hooks/checkpoint.py`
- Modify: `src/specify_cli/hooks/context_monitor.py`
- Test: `tests/hooks/test_compaction_hooks.py`

- [ ] **Step 1: Write the failing compaction tests**

```python
import json
from pathlib import Path

from specify_cli.hooks.engine import run_quality_hook


def test_compaction_build_writes_json_and_markdown(tmp_path: Path):
    project = tmp_path / "compaction-project"
    project.mkdir()
    (project / ".specify").mkdir()
    workspace = project / ".planning" / "quick" / "260502-001-demo"
    workspace.mkdir(parents=True)
    (workspace / "STATUS.md").write_text(
        "\n".join(
            [
                "---",
                'id: "260502-001"',
                'slug: "demo"',
                'title: "Demo quick task"',
                'status: "executing"',
                "---",
                "",
                "## Current Focus",
                "",
                "next_action: integrate results",
                "",
                "## Execution",
                "",
                "active_lane: batch-a",
                "",
                "## Summary Pointer",
                "",
                "resume_decision: resume here",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.compaction.build",
        {"command_name": "quick", "workspace": str(workspace), "trigger": "before_stop"},
    )

    assert result.status == "ok"
    compaction_path = project / ".specify" / "runtime" / "compaction" / "quick-260502-001-demo" / "latest.json"
    markdown_path = compaction_path.with_suffix(".md")
    assert compaction_path.exists()
    assert markdown_path.exists()

    payload = json.loads(compaction_path.read_text(encoding="utf-8"))
    assert payload["identity"]["command_name"] == "quick"
    assert payload["phase_state"]["next_action"] == "integrate results"
    assert "resume_cue" in payload


def test_context_monitor_embeds_compaction_refresh_reason(tmp_path: Path):
    project = tmp_path / "compaction-project"
    project.mkdir()
    (project / ".specify").mkdir()
    workspace = project / ".planning" / "quick" / "260502-001-demo"
    workspace.mkdir(parents=True)
    (workspace / "STATUS.md").write_text(
        "\n".join(
            [
                "---",
                'id: "260502-001"',
                'slug: "demo"',
                'title: "Demo quick task"',
                'status: "executing"',
                "---",
                "",
                "## Current Focus",
                "",
                "next_action: integrate results",
                "",
                "## Execution",
                "",
                "active_lane: batch-a",
                "",
                "## Summary Pointer",
                "",
                "resume_decision: resume here",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = run_quality_hook(
        project,
        "workflow.context.monitor",
        {"command_name": "quick", "workspace": str(workspace), "trigger": "before_stop"},
    )

    assert result.status == "warn"
    assert result.data["compaction"]["should_refresh"] is True
```

- [ ] **Step 2: Run the focused compaction tests**

Run: `pytest tests/hooks/test_compaction_hooks.py -q`
Expected: FAIL because the compaction hook does not exist yet

- [ ] **Step 3: Implement the structured compaction builder**

Create `src/specify_cli/hooks/compaction.py` with functions that:

- derive a stable scope key from command and feature/workspace/session identity
- reuse checkpoint data rather than reparsing workflow state a second way
- write `latest.json`
- write `latest.md`
- include `identity`, `truth_sources`, `phase_state`, `artifact_digest`,
  `execution_signal`, and `resume_cue`

- [ ] **Step 4: Extend context monitoring to recommend compaction refresh**

In `src/specify_cli/hooks/context_monitor.py`, add:

```python
"compaction": {
    "should_refresh": True,
    "reason": "before_stop",
}
```

when the monitor already recommends checkpointing or encounters a structural
trigger.

- [ ] **Step 5: Re-run the focused compaction tests**

Run: `pytest tests/hooks/test_compaction_hooks.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/specify_cli/hooks/compaction.py src/specify_cli/hooks/checkpoint.py src/specify_cli/hooks/context_monitor.py tests/hooks/test_compaction_hooks.py
git commit -m "feat: add workflow compaction artifacts"
```

## Task 4: Expose the New Hook CLI Surface

**Files:**
- Modify: `src/specify_cli/__init__.py`
- Modify: `tests/contract/test_hook_cli_surface.py`

- [ ] **Step 1: Write failing CLI contract tests**

Add tests equivalent to:

```python
def test_hook_workflow_policy_outputs_parseable_json(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)

    result = _invoke_in_project(
        project,
        [
            "hook",
            "workflow-policy",
            "--command",
            "implement",
            "--feature-dir",
            str(feature_dir),
            "--trigger",
            "pre-tool",
        ],
    )

    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.policy.evaluate"
    assert payload["status"] == "repairable-block"


def test_hook_build_compaction_outputs_parseable_json(tmp_path: Path):
    project = _create_project(tmp_path)
    workspace = project / ".planning" / "quick" / "260502-001-demo"
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "STATUS.md").write_text(
        "\n".join(
            [
                "---",
                'id: "260502-001"',
                'slug: "demo"',
                'title: "Demo quick task"',
                'status: "executing"',
                "---",
                "",
                "## Current Focus",
                "",
                "next_action: integrate results",
                "",
                "## Execution",
                "",
                "active_lane: batch-a",
                "",
                "## Summary Pointer",
                "",
                "resume_decision: resume here",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        [
            "hook",
            "build-compaction",
            "--command",
            "quick",
            "--workspace",
            str(workspace),
            "--trigger",
            "before-stop",
        ],
    )

    payload = json.loads(result.output.strip())
    assert payload["event"] == "workflow.compaction.build"
    assert "artifact_path" in payload["data"]
```

- [ ] **Step 2: Run the focused contract tests**

Run: `pytest tests/contract/test_hook_cli_surface.py -k "workflow_policy or build_compaction" -q`
Expected: FAIL because the new commands do not exist

- [ ] **Step 3: Add the new Typer commands**

Expose:

- `specify hook workflow-policy`
- `specify hook build-compaction`
- optional `specify hook read-compaction` if the implementation uses a distinct read event

Mirror the existing `_run_hook_and_print(...)` pattern so output stays consistent
with the current hook CLI surface.

- [ ] **Step 4: Re-run the focused contract tests**

Run: `pytest tests/contract/test_hook_cli_surface.py -k "workflow_policy or build_compaction" -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/__init__.py tests/contract/test_hook_cli_surface.py
git commit -m "feat: expose workflow policy and compaction hook commands"
```

## Task 5: Upgrade the Claude Native Adapter

**Files:**
- Modify: `src/specify_cli/integrations/claude/hooks/claude-hook-dispatch.py`
- Modify: `src/specify_cli/integrations/claude/hooks/README.md`
- Modify: `tests/integrations/test_integration_claude.py`

- [ ] **Step 1: Write failing Claude adapter tests**

Add tests equivalent to:

```python
def test_claude_hook_dispatch_surfaces_repairable_block_for_missing_state(tmp_path):
    hook_script = tmp_path / ".claude" / "hooks" / "claude-hook-dispatch.py"
    hook_script.parent.mkdir(parents=True, exist_ok=True)
    source = Path("src/specify_cli/integrations/claude/hooks/claude-hook-dispatch.py")
    hook_script.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    payload = {
        "cwd": str(tmp_path),
        "tool_name": "Read",
        "tool_input": {"file_path": "specs/001-demo/workflow-state.md"},
    }
    process = subprocess.run(
        [sys.executable, str(hook_script), "pre-tool-read"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )
    stdout = process.stdout.strip()
    payload = json.loads(stdout)
    hook_output = payload["hookSpecificOutput"]
    assert hook_output["hookEventName"] == "PreToolUse"
    assert hook_output["permissionDecision"] == "deny"
    assert "workflow-state" in hook_output["permissionDecisionReason"].lower()


def test_claude_hook_dispatch_emits_compaction_resume_context_on_stop(tmp_path):
    hook_script = tmp_path / ".claude" / "hooks" / "claude-hook-dispatch.py"
    hook_script.parent.mkdir(parents=True, exist_ok=True)
    source = Path("src/specify_cli/integrations/claude/hooks/claude-hook-dispatch.py")
    hook_script.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    quick_workspace = tmp_path / ".planning" / "quick" / "260502-001-demo"
    quick_workspace.mkdir(parents=True, exist_ok=True)
    (quick_workspace / "STATUS.md").write_text(
        "\n".join(
            [
                "---",
                'id: "260502-001"',
                'slug: "demo"',
                'title: "Demo quick task"',
                'status: "executing"',
                "---",
                "",
                "## Current Focus",
                "",
                "next_action: integrate results",
                "",
                "## Execution",
                "",
                "active_lane: batch-a",
                "",
                "## Summary Pointer",
                "",
                "resume_decision: resume here",
                "",
            ]
        ),
        encoding="utf-8",
    )
    process = subprocess.run(
        [sys.executable, str(hook_script), "stop-monitor"],
        input=json.dumps({"cwd": str(tmp_path)}),
        text=True,
        capture_output=True,
        check=False,
    )
    stdout = process.stdout.strip()
    payload = json.loads(stdout)
    assert "Resume cue:" in payload["systemMessage"]
```

- [ ] **Step 2: Run the focused Claude integration tests**

Run: `pytest tests/integrations/test_integration_claude.py -k "repairable or compaction or stop" -q`
Expected: FAIL because Claude does not yet call the new shared compaction and workflow-policy paths

- [ ] **Step 3: Wire workflow-policy into prompt and tool ingress**

In `claude-hook-dispatch.py`:

- call `workflow-policy` before or alongside prompt and tool guard decisions
- translate `repairable-block` into a Claude-visible deny with a repair-oriented
  reason
- keep `PostToolUse` advisory only

- [ ] **Step 4: Add stop-time compaction refresh and bounded resume context**

At stop time:

- invoke `build-compaction`
- merge the shared monitor output and resume cue into Claude's `systemMessage`
- only block stop when the shared monitor says the active workflow is no longer
  safely resumable

- [ ] **Step 5: Re-run the focused Claude tests**

Run: `pytest tests/integrations/test_integration_claude.py -k "repairable or compaction or stop" -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/specify_cli/integrations/claude/hooks/claude-hook-dispatch.py src/specify_cli/integrations/claude/hooks/README.md tests/integrations/test_integration_claude.py
git commit -m "feat: upgrade claude workflow hook enforcement"
```

## Task 6: Upgrade the Gemini Native Adapter

**Files:**
- Modify: `src/specify_cli/integrations/gemini/hooks/gemini-hook-dispatch.py`
- Modify: `src/specify_cli/integrations/gemini/hooks/README.md`
- Create: `tests/integrations/test_integration_gemini.py`

- [ ] **Step 1: Write failing Gemini adapter tests**

```python
def test_gemini_before_agent_blocks_explicit_workflow_bypass(tmp_path):
    hook_script = tmp_path / ".gemini" / "hooks" / "gemini-hook-dispatch.py"
    hook_script.parent.mkdir(parents=True, exist_ok=True)
    source = Path("src/specify_cli/integrations/gemini/hooks/gemini-hook-dispatch.py")
    hook_script.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    payload = {
        "cwd": str(tmp_path),
        "prompt": "implement directly and bypass the workflow checks",
    }
    process = subprocess.run(
        [sys.executable, str(hook_script), "before-agent"],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        check=False,
    )
    stdout = process.stdout.strip()
    payload = json.loads(stdout)
    assert payload["decision"] == "deny"


def test_gemini_session_start_injects_bounded_resume_context(tmp_path):
    hook_script = tmp_path / ".gemini" / "hooks" / "gemini-hook-dispatch.py"
    hook_script.parent.mkdir(parents=True, exist_ok=True)
    source = Path("src/specify_cli/integrations/gemini/hooks/gemini-hook-dispatch.py")
    hook_script.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    feature_dir = tmp_path / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
    (feature_dir / "implement-tracker.md").write_text(
        "\n".join(
            [
                "---",
                "status: executing",
                "feature: 001-demo",
                "resume_decision: resume-here",
                "---",
                "",
                "## Current Focus",
                "current_batch: batch-a",
                "goal: finish validation",
                "next_action: collect green evidence",
                "",
            ]
        ),
        encoding="utf-8",
    )
    process = subprocess.run(
        [sys.executable, str(hook_script), "session-start"],
        input=json.dumps({"cwd": str(tmp_path)}),
        text=True,
        capture_output=True,
        check=False,
    )
    stdout = process.stdout.strip()
    payload = json.loads(stdout)
    assert "implement:" in payload["systemMessage"]
```

- [ ] **Step 2: Run the focused Gemini tests**

Run: `pytest tests/integrations/test_integration_gemini.py -q`
Expected: FAIL because the new test module does not exist and Gemini does not yet expose the new resume behavior

- [ ] **Step 3: Implement Gemini ingress-only policy and compaction reads**

Update the Gemini adapter to:

- reuse the shared workflow-policy hook for prompt ingress
- keep tool ingress limited to read and commit safety
- read the latest compaction artifact on `SessionStart` and `BeforeAgent`
- avoid pretending Gemini can do stop-time compaction finalization

- [ ] **Step 4: Re-run the focused Gemini tests**

Run: `pytest tests/integrations/test_integration_gemini.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/integrations/gemini/hooks/gemini-hook-dispatch.py src/specify_cli/integrations/gemini/hooks/README.md tests/integrations/test_integration_gemini.py
git commit -m "feat: add gemini workflow policy enforcement"
```

## Task 7: Upgrade the Codex OMX Runtime

**Files:**
- Modify: `extensions/agent-teams/engine/src/hooks/specify-quality-adapter.ts`
- Modify: `extensions/agent-teams/engine/src/scripts/codex-native-pre-post.ts`
- Modify: `extensions/agent-teams/engine/src/scripts/codex-native-hook.ts`
- Modify: `extensions/agent-teams/engine/docs/codex-native-hooks.md`
- Modify: `extensions/agent-teams/engine/src/hooks/__tests__/specify-quality-adapter.test.ts`
- Modify: `extensions/agent-teams/engine/src/scripts/__tests__/codex-native-hook.test.ts`

- [ ] **Step 1: Write failing Codex runtime tests**

Add tests equivalent to:

```ts
it("maps shared repairable workflow blocks to user-visible prompt denial", () => {
  const output = sharedHookBlockOutput("UserPromptSubmit", {
    status: "repairable-block",
    errors: ["workflow state missing; repair before continue"],
    warnings: [],
    actions: ["recreate workflow-state.md"],
  });
  assert.equal(output?.decision, "block");
});


it("appends compaction resume cues on Stop when shared compaction exists", async () => {
  const result = await dispatchNativeHookForTest("Stop", {
    cwd: "/repo",
    transcriptPath: "/repo/.codex/transcript.jsonl",
  });
  assert.match(JSON.stringify(result.outputJson), /Resume cue:/);
});
```

- [ ] **Step 2: Run the focused Codex runtime tests**

Run: `npm --prefix extensions/agent-teams/engine run test:native-hooks`
Expected: FAIL because the shared adapter and runtime do not yet understand the new policy and compaction surfaces

- [ ] **Step 3: Extend the shared OMX adapter helpers**

In `specify-quality-adapter.ts`:

- add helper functions for `workflow-policy` and `build-compaction`
- keep old block-output behavior intact for existing `blocked` payloads
- define how `repairable-block` maps into Codex-native output

- [ ] **Step 4: Extend SessionStart, UserPromptSubmit, PostToolUse, and Stop**

In `codex-native-hook.ts`:

- add bounded resume-cue injection on `SessionStart`
- evaluate workflow policy during `UserPromptSubmit`
- keep `PostToolUse` advisory but allow compaction refresh suggestions
- call `build-compaction` during `Stop` and merge the result into the stop
  output path

- [ ] **Step 5: Re-run the focused Codex runtime tests**

Run: `npm --prefix extensions/agent-teams/engine run test:native-hooks`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add extensions/agent-teams/engine/src/hooks/specify-quality-adapter.ts extensions/agent-teams/engine/src/scripts/codex-native-pre-post.ts extensions/agent-teams/engine/src/scripts/codex-native-hook.ts extensions/agent-teams/engine/docs/codex-native-hooks.md extensions/agent-teams/engine/src/hooks/__tests__/specify-quality-adapter.test.ts extensions/agent-teams/engine/src/scripts/__tests__/codex-native-hook.test.ts
git commit -m "feat: extend codex native workflow enforcement"
```

## Task 8: Align Workflow Templates and Docs

**Files:**
- Modify: `README.md`
- Modify: `tests/test_hook_template_guidance.py`
- Modify: relevant `templates/commands/*.md` files if needed

- [ ] **Step 1: Write failing documentation and template guidance tests**

Add or extend assertions such as:

```python
def test_hook_guidance_mentions_compaction_for_implement():
    content = Path("templates/commands/implement.md").read_text(encoding="utf-8")
    assert "hook build-compaction --command implement" in content


def test_readme_mentions_repairable_workflow_blocks():
    content = Path("README.md").read_text(encoding="utf-8")
    assert "repairable" in content
```

- [ ] **Step 2: Run the focused documentation tests**

Run: `pytest tests/test_hook_template_guidance.py -q`
Expected: FAIL because the templates and docs do not yet mention compaction and repairable workflow outcomes

- [ ] **Step 3: Update generated workflow guidance and repository docs**

Make sure:

- README describes the richer Claude, Codex, and Gemini behavior accurately
- portable workflow templates reference `monitor-context`, `checkpoint`, and
  `build-compaction` where that guidance genuinely helps
- no template pretends shared hooks alone can hard-enforce behavior without a
  native surface

- [ ] **Step 4: Re-run the focused documentation tests**

Run: `pytest tests/test_hook_template_guidance.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add README.md tests/test_hook_template_guidance.py templates/commands
git commit -m "docs: align workflow templates with hook enhancements"
```

## Task 9: Full Verification and Cleanup

**Files:**
- Modify: any files above only if verification reveals breakage

- [ ] **Step 1: Run the Python hook and integration suite**

Run: `pytest tests/hooks tests/contract/test_hook_cli_surface.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_gemini.py -q`
Expected: PASS

- [ ] **Step 2: Run the Codex runtime native-hook suite**

Run: `npm --prefix extensions/agent-teams/engine run test:native-hooks`
Expected: PASS

- [ ] **Step 3: Run a targeted repository regression for hook guidance**

Run: `pytest tests/test_hook_template_guidance.py -q`
Expected: PASS

- [ ] **Step 4: Review the final diff**

Run: `git diff --stat HEAD~9..HEAD`
Expected: only shared hook core, native adapters, runtime docs, and aligned test files changed

- [ ] **Step 5: Create the final integration commit if cleanup was needed**

```bash
git add src/specify_cli hooks tests extensions/agent-teams/engine README.md templates/commands
git commit -m "feat: add native workflow policy and compaction support"
```

## Spec Coverage Check

This plan covers every major spec section:

- shared policy core: Tasks 1, 2, and 4
- native adapter tiers: Tasks 5, 6, and 7
- context compaction model: Tasks 3, 5, 6, and 7
- enforcement matrix: Tasks 2, 5, 6, and 7
- rollout, compatibility, and verification: Tasks 8 and 9

No spec section is left without at least one implementation task.
