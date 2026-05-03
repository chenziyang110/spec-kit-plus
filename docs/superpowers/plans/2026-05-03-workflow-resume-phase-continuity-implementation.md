# Workflow Resume Phase Continuity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a shared workflow recovery contract and `redirect-first` phase-continuity enforcement so active `sp-*` workflows survive compaction and resume without drifting into downstream phases.

**Architecture:** Extend the shared Python hook engine first so every resumable workflow surface can serialize into one recovery contract and compaction artifact. Then wire that contract into workflow policy, hook CLI output, and native Claude/Gemini/Codex adapters so `SessionStart`, `UserPromptSubmit`, `PostToolUse`, and `Stop` all enforce the same recovery semantics.

**Tech Stack:** Python 3.13+, Typer, pytest, project-local Claude and Gemini hook adapters, OMX Codex runtime TypeScript, Node test runner, Markdown templates

---

## File Structure

### Shared Recovery Contract and Serialization

- Modify: `src/specify_cli/hooks/checkpoint_serializers.py`
  - Extend the existing serializers so `workflow-state.md`, `implement-tracker.md`, `STATUS.md`, and debug sessions expose full recovery-contract fields instead of only minimal checkpoint data.
- Modify: `src/specify_cli/hooks/checkpoint.py`
  - Ensure checkpoint payloads carry all recovery-critical fields and lane metadata needed by compaction and native adapters.
- Modify: `src/specify_cli/hooks/compaction.py`
  - Build structured recovery summaries from checkpoint data and preserve them in JSON and Markdown artifacts.
- Modify: `src/specify_cli/hooks/statusline.py`
  - Keep the short statusline while exposing richer checkpoint data for `SessionStart`.

### Shared Policy and Hook CLI

- Modify: `src/specify_cli/hooks/workflow_policy.py`
  - Upgrade policy outcomes from simple allow/block logic into `allow | redirect | repairable-block | blocked`.
- Modify: `src/specify_cli/hooks/context_monitor.py`
  - Preserve compaction refresh guidance and include the richer checkpoint payload whenever checkpointing is recommended.
- Modify: `src/specify_cli/hooks/state_validation.py`
  - Tighten recovery-critical field validation for active resumable workflows.
- Modify: `src/specify_cli/hooks/session_state.py`
  - Surface workflow-state vs tracker contradictions as repairable state drift instead of silent warnings.
- Modify: `src/specify_cli/hooks/types.py`
  - Preserve JSON-compatible hook result serialization if new policy metadata fields are added.
- Modify: `src/specify_cli/__init__.py`
  - Extend `specify hook` CLI subcommands so workflow-policy, compaction, and statusline responses can return the richer recovery contract cleanly.

### Native Hook Adapters

- Modify: `src/specify_cli/integrations/claude/hooks/claude-hook-dispatch.py`
  - Render the structured recovery summary on `SessionStart`, return redirects on first drift, and preserve advisory `PostToolUse` behavior.
- Modify: `src/specify_cli/integrations/gemini/hooks/gemini-hook-dispatch.py`
  - Reuse the same shared recovery contract for `SessionStart` and prompt-entry policy outcomes.
- Modify: `extensions/agent-teams/engine/src/hooks/specify-quality-adapter.ts`
  - Preserve shared payload compatibility and append the richer recovery summary text.
- Modify: `extensions/agent-teams/engine/src/scripts/codex-native-hook.ts`
  - Inject shared recovery summaries and redirect-first behavior into Codex `SessionStart`, `UserPromptSubmit`, `PostToolUse`, and `Stop`.

### Workflow Templates and Docs

- Modify: `templates/workflow-state-template.md`
  - Make recovery-contract fields explicit and complete.
- Modify: `templates/commands/specify.md`
  - Reinforce planning-only recovery behavior and explicit re-entry from `workflow-state.md`.
- Modify: `templates/commands/plan.md`
  - Reinforce design-only recovery behavior and no implicit permission to execute.
- Modify: `templates/commands/implement.md`
  - Reinforce execution-state recovery, cross-file truth, and redirect behavior.
- Modify: `docs/quickstart.md`
  - Document structured recovery summaries and redirect-first behavior across native-hook surfaces.
- Modify: `src/specify_cli/integrations/claude/hooks/README.md`
  - Describe the new Claude recovery summary and redirect behavior.
- Modify: `src/specify_cli/integrations/gemini/hooks/README.md`
  - Describe Gemini’s recovery summary and ingress-only enforcement depth.

### Tests

- Modify: `tests/hooks/test_hook_engine.py`
  - Extend checkpoint expectations to cover the richer recovery-contract fields.
- Modify: `tests/hooks/test_state_hooks.py`
  - Add recovery-critical field validation failures and success cases.
- Modify: `tests/hooks/test_workflow_policy_hooks.py`
  - Add redirect-first, repeated-drift, and explicit phase-jump coverage.
- Modify: `tests/hooks/test_compaction_hooks.py`
  - Verify structured recovery summaries in compaction artifacts.
- Modify: `tests/hooks/test_statusline_hooks.py`
  - Verify checkpoint data remains available even when the short statusline stays compact.
- Modify: `tests/contract/test_hook_cli_surface.py`
  - Verify `specify hook` CLI JSON payloads include the new recovery fields without breaking existing shape.
- Modify: `tests/integrations/test_integration_claude.py`
  - Verify Claude hook dispatch emits recovery summaries and redirect-first outputs.
- Modify: `tests/integrations/test_integration_gemini.py`
  - Verify Gemini hook dispatch emits recovery summaries and prompt-entry redirects.
- Modify: `extensions/agent-teams/engine/src/hooks/__tests__/specify-quality-adapter.test.ts`
  - Verify shared payload context appending preserves recovery-summary text.
- Modify: `extensions/agent-teams/engine/src/scripts/__tests__/codex-native-hook.test.ts`
  - Verify Codex native hook lifecycle behavior for recovery summary and redirect-first handling.

---

### Task 1: Extend serializer output into a full recovery contract

**Files:**
- Modify: `src/specify_cli/hooks/checkpoint_serializers.py`
- Test: `tests/hooks/test_hook_engine.py`
- Test: `tests/hooks/test_state_hooks.py`

- [ ] **Step 1: Add the failing checkpoint serializer assertions**

Add these assertions to `test_workflow_checkpoint_returns_resume_payload_for_workflow_state` in `tests/hooks/test_hook_engine.py`:

```python
    assert checkpoint["summary"] == "demo"
    assert checkpoint["allowed_artifact_writes"] == ["spec.md"]
    assert checkpoint["forbidden_actions"] == ["edit source code"]
    assert checkpoint["authoritative_files"] == ["spec.md"]
```

Add this new test to `tests/hooks/test_state_hooks.py`:

```python
def test_validate_state_blocks_when_recovery_fields_are_missing(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
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
                "- phase_mode: `planning-only`",
                "- summary: demo",
                "",
                "## Next Action",
                "",
                "- refine scope",
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
        "workflow.state.validate",
        {"command_name": "specify", "feature_dir": str(feature_dir)},
    )

    assert result.status == "blocked"
    assert any("allowed_artifact_writes" in message for message in result.errors)
    assert any("forbidden_actions" in message for message in result.errors)
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
uv run pytest tests/hooks/test_hook_engine.py::test_workflow_checkpoint_returns_resume_payload_for_workflow_state tests/hooks/test_state_hooks.py::test_validate_state_blocks_when_recovery_fields_are_missing -q
```

Expected: FAIL because `serialize_workflow_state()` does not yet expose `summary`, `allowed_artifact_writes`, or `forbidden_actions`, and state validation does not require them.

- [ ] **Step 3: Extend `serialize_workflow_state()` to capture recovery-contract fields**

Update `src/specify_cli/hooks/checkpoint_serializers.py` inside `serialize_workflow_state()` so it also reads:

```python
    allowed_artifact_writes = section_body(text, "Allowed Artifact Writes")
    forbidden_actions = section_body(text, "Forbidden Actions")
    lane_context = section_body(text, "Lane Context")
```

and returns:

```python
        "summary": extract_field(phase_mode, "summary"),
        "allowed_artifact_writes": extract_bullets(allowed_artifact_writes),
        "forbidden_actions": extract_bullets(forbidden_actions),
        "recovery_state": extract_field(lane_context, "recovery_state"),
        "last_stable_checkpoint": extract_field(lane_context, "last_stable_checkpoint"),
```

Do not remove existing fields such as `route_reason`, `blocked_reason`, or `authoritative_files`.

- [ ] **Step 4: Tighten workflow-state validation around recovery-critical fields**

In `src/specify_cli/hooks/state_validation.py`, after the existing `active_command` and `phase_mode` checks for `EXPECTED_WORKFLOW_STATE`, add:

```python
        if not checkpoint["allowed_artifact_writes"]:
            errors.append("allowed_artifact_writes is missing from workflow-state")
        if not checkpoint["forbidden_actions"]:
            errors.append("forbidden_actions is missing from workflow-state")
        if not checkpoint["authoritative_files"]:
            errors.append("authoritative_files is missing from workflow-state")
        if not checkpoint["next_command"]:
            errors.append("next_command is missing from workflow-state")
```

- [ ] **Step 5: Re-run the focused hook tests**

Run:

```bash
uv run pytest tests/hooks/test_hook_engine.py::test_workflow_checkpoint_returns_resume_payload_for_workflow_state tests/hooks/test_state_hooks.py -q
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/specify_cli/hooks/checkpoint_serializers.py src/specify_cli/hooks/state_validation.py tests/hooks/test_hook_engine.py tests/hooks/test_state_hooks.py
git commit -m "feat: extend workflow recovery serialization"
```

---

### Task 2: Extend checkpoint and compaction artifacts with structured recovery summaries

**Files:**
- Modify: `src/specify_cli/hooks/checkpoint.py`
- Modify: `src/specify_cli/hooks/compaction.py`
- Modify: `tests/hooks/test_compaction_hooks.py`
- Modify: `tests/contract/test_hook_cli_surface.py`

- [ ] **Step 1: Add the failing compaction summary assertions**

Extend `test_compaction_build_writes_json_and_markdown` in `tests/hooks/test_compaction_hooks.py` with:

```python
    assert payload["artifact"]["recovery_summary"]["next_action"] == "integrate results"
    assert payload["artifact"]["recovery_summary"]["authoritative_sources"] == [str(workspace / "STATUS.md")]
```

Add this new test to `tests/contract/test_hook_cli_surface.py`:

```python
def test_hook_build_compaction_outputs_recovery_summary(tmp_path: Path):
    project = _create_project(tmp_path)
    workspace = project / ".planning" / "quick" / "260427-001-demo-quick-task"
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "STATUS.md").write_text(
        "\n".join(
            [
                "---",
                'id: "260427-001"',
                'slug: "demo-quick-task"',
                'title: "Demo quick task"',
                'status: "executing"',
                "---",
                "",
                "## Current Focus",
                "",
                "next_action: finish validation",
                "",
                "## Execution",
                "",
                "active_lane: worker-a",
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
            "before_stop",
        ],
    )

    payload = json.loads(result.output.strip())
    summary = payload["data"]["artifact"]["recovery_summary"]
    assert summary["next_action"] == "finish validation"
    assert summary["resume_decision"] == "resume here"
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
uv run pytest tests/hooks/test_compaction_hooks.py::test_compaction_build_writes_json_and_markdown tests/contract/test_hook_cli_surface.py::test_hook_build_compaction_outputs_recovery_summary -q
```

Expected: FAIL because compaction artifacts do not yet include `recovery_summary`.

- [ ] **Step 3: Add a structured recovery summary to compaction artifacts**

In `src/specify_cli/hooks/compaction.py`, add this helper:

```python
def _recovery_summary(project_root: Path, checkpoint: dict[str, Any]) -> dict[str, Any]:
    checkpoint_path = str(checkpoint.get("path") or "").strip()
    authoritative_sources: list[str] = []
    if checkpoint_path:
        authoritative_sources.append(str(Path(checkpoint_path).resolve()))
    for item in checkpoint.get("authoritative_files", []):
        text = str(item or "").strip()
        if text:
            authoritative_sources.append(text)
    return {
        "command_name": str(checkpoint.get("active_command") or ""),
        "phase_mode": str(checkpoint.get("phase_mode") or ""),
        "status": str(checkpoint.get("status") or ""),
        "summary": str(checkpoint.get("summary") or ""),
        "allowed_actions": list(checkpoint.get("allowed_artifact_writes") or []),
        "forbidden_actions": list(checkpoint.get("forbidden_actions") or []),
        "authoritative_sources": authoritative_sources,
        "next_action": str(checkpoint.get("next_action") or ""),
        "next_command": str(checkpoint.get("next_command") or ""),
        "route_reason": str(checkpoint.get("route_reason") or ""),
        "blocked_reason": str(checkpoint.get("blocked_reason") or ""),
        "resume_decision": str(checkpoint.get("resume_decision") or ""),
    }
```

Then include it in the `artifact` payload:

```python
        "recovery_summary": _recovery_summary(project_root, checkpoint),
```

Keep `resume_cue` for backward compatibility.

- [ ] **Step 4: Surface the recovery summary in Markdown output**

In `_artifact_markdown()`, add:

```python
    recovery_summary = artifact["recovery_summary"]
```

and a new section:

```python
        "## Recovery Summary",
        "",
        f"- phase_mode: `{recovery_summary.get('phase_mode', '')}`",
        f"- next_action: `{recovery_summary.get('next_action', '')}`",
        f"- next_command: `{recovery_summary.get('next_command', '')}`",
```

Do not remove the existing `Resume Cue` section.

- [ ] **Step 5: Re-run the focused tests**

Run:

```bash
uv run pytest tests/hooks/test_compaction_hooks.py tests/contract/test_hook_cli_surface.py -q
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/specify_cli/hooks/checkpoint.py src/specify_cli/hooks/compaction.py tests/hooks/test_compaction_hooks.py tests/contract/test_hook_cli_surface.py
git commit -m "feat: add structured workflow recovery summaries"
```

---

### Task 3: Upgrade workflow policy to support redirect-first semantics

**Files:**
- Modify: `src/specify_cli/hooks/workflow_policy.py`
- Modify: `tests/hooks/test_workflow_policy_hooks.py`

- [ ] **Step 1: Add failing redirect-first workflow-policy tests**

Add these tests to `tests/hooks/test_workflow_policy_hooks.py`:

```python
def test_workflow_policy_redirects_first_phase_drift(tmp_path: Path):
    project = _create_project(tmp_path)
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
                "- phase_mode: `planning-only`",
                "- summary: refine scope",
                "",
                "## Allowed Artifact Writes",
                "",
                "- spec.md",
                "",
                "## Forbidden Actions",
                "",
                "- edit source code",
                "",
                "## Authoritative Files",
                "",
                "- spec.md",
                "",
                "## Next Action",
                "",
                "- refine scope",
                "",
                "## Next Command",
                "",
                "- `/sp.plan`",
                "",
                "## Learning Signals",
                "",
                "- route_reason: `spec not yet approved for planning`",
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
            "requested_action": "start_editing_code",
        },
    )

    assert result.status == "warn"
    assert result.data["policy"]["classification"] == "redirect"
    assert result.data["policy"]["recovery_summary"]["next_command"] == "/sp.plan"
```

```python
def test_workflow_policy_blocks_repeated_phase_drift(tmp_path: Path):
    project = _create_project(tmp_path)
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
                "- phase_mode: `planning-only`",
                "- summary: refine scope",
                "",
                "## Allowed Artifact Writes",
                "",
                "- spec.md",
                "",
                "## Forbidden Actions",
                "",
                "- edit source code",
                "",
                "## Authoritative Files",
                "",
                "- spec.md",
                "",
                "## Next Action",
                "",
                "- refine scope",
                "",
                "## Next Command",
                "",
                "- `/sp.plan`",
                "",
                "## Learning Signals",
                "",
                "- route_reason: `spec not yet approved for planning`",
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
            "requested_action": "start_editing_code",
            "prior_redirect_count": 1,
        },
    )

    assert result.status == "blocked"
    assert any("phase" in error.lower() for error in result.errors)
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
uv run pytest tests/hooks/test_workflow_policy_hooks.py -q
```

Expected: FAIL because `workflow_policy_hook()` only supports allow, warn, repairable-block, and explicit hard phase jumps.

- [ ] **Step 3: Implement redirect-first classification in `workflow_policy_hook()`**

In `src/specify_cli/hooks/workflow_policy.py`, add:

```python
SOFT_REDIRECT_ACTIONS = {
    "start_editing_code",
    "start_implementation",
    "run_fix_loop",
    "jump_to_testing",
}
```

Then, after `validate_state_hook()` returns `ok`, if `requested_action` is one of those and `command_name` is one of `{"constitution", "specify", "deep-research", "plan", "tasks", "analyze", "prd"}`, build:

```python
        checkpoint = state_result.data.get("checkpoint", {})
        recovery_summary = {
            "phase_mode": checkpoint.get("phase_mode", ""),
            "summary": checkpoint.get("summary", ""),
            "forbidden_actions": checkpoint.get("forbidden_actions", []),
            "authoritative_files": checkpoint.get("authoritative_files", []),
            "next_action": checkpoint.get("next_action", ""),
            "next_command": checkpoint.get("next_command", ""),
            "route_reason": checkpoint.get("route_reason", ""),
        }
```

If `prior_redirect_count` is `0` or missing, return:

```python
        return HookResult(
            event=WORKFLOW_POLICY_EVALUATE,
            status="warn",
            severity="warning",
            warnings=["requested action conflicts with the active workflow phase; redirect before continuing"],
            actions=["re-read the authoritative workflow state and continue from the recorded next action"],
            data={
                "policy": {
                    "classification": "redirect",
                    "trigger": trigger,
                    "command_name": command_name,
                    "repairable": False,
                    "requested_action": requested_action,
                    "recovery_summary": recovery_summary,
                }
            },
        )
```

If `prior_redirect_count >= 1`, return `blocked` with the same `recovery_summary` under `data["policy"]`.

- [ ] **Step 4: Re-run the workflow-policy tests**

Run:

```bash
uv run pytest tests/hooks/test_workflow_policy_hooks.py -q
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/hooks/workflow_policy.py tests/hooks/test_workflow_policy_hooks.py
git commit -m "feat: add redirect-first workflow policy"
```

---

### Task 4: Surface recovery summaries through the hook CLI and shared adapter

**Files:**
- Modify: `src/specify_cli/__init__.py`
- Modify: `extensions/agent-teams/engine/src/hooks/specify-quality-adapter.ts`
- Modify: `extensions/agent-teams/engine/src/hooks/__tests__/specify-quality-adapter.test.ts`
- Modify: `tests/contract/test_hook_cli_surface.py`

- [ ] **Step 1: Add failing shared-adapter tests for recovery-summary text**

Add this test to `extensions/agent-teams/engine/src/hooks/__tests__/specify-quality-adapter.test.ts`:

```ts
  it("appends structured recovery-summary text to existing context", () => {
    const merged = appendSharedHookContext("Base context.", {
      event: "workflow.compaction.build",
      status: "ok",
      data: {
        artifact: {
          recovery_summary: {
            phase_mode: "planning-only",
            next_action: "refine scope",
            next_command: "/sp.plan",
            route_reason: "spec not yet approved for implementation",
          },
        },
      },
    });

    assert.match(merged ?? "", /planning-only/);
    assert.match(merged ?? "", /refine scope/);
    assert.match(merged ?? "", /\/sp\.plan/);
  });
```

Add this test to `tests/contract/test_hook_cli_surface.py`:

```python
def test_hook_workflow_policy_outputs_redirect_payload(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
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
                "- phase_mode: `planning-only`",
                "- summary: demo",
                "",
                "## Allowed Artifact Writes",
                "",
                "- spec.md",
                "",
                "## Forbidden Actions",
                "",
                "- edit source code",
                "",
                "## Authoritative Files",
                "",
                "- spec.md",
                "",
                "## Next Action",
                "",
                "- refine scope",
                "",
                "## Next Command",
                "",
                "- `/sp.plan`",
                "",
                "## Learning Signals",
                "",
                "- route_reason: `spec not yet approved for planning`",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        [
            "hook",
            "workflow-policy",
            "--command",
            "specify",
            "--feature-dir",
            str(feature_dir),
            "--trigger",
            "prompt",
            "--requested-action",
            "start_editing_code",
        ],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "warn"
    assert payload["data"]["policy"]["classification"] == "redirect"
    assert payload["data"]["policy"]["recovery_summary"]["next_command"] == "/sp.plan"
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
uv run pytest tests/contract/test_hook_cli_surface.py::test_hook_workflow_policy_outputs_redirect_payload -q
npm --prefix extensions/agent-teams/engine test -- specify-quality-adapter.test.ts
```

Expected: FAIL because the shared adapter does not yet append `recovery_summary` text.

- [ ] **Step 3: Extend `appendSharedHookContext()` for structured recovery summaries**

In `extensions/agent-teams/engine/src/hooks/specify-quality-adapter.ts`, inside `appendSharedHookContext()`, after the existing `artifact.phase_state` handling, add:

```ts
  const recoverySummary = artifact["recovery_summary"] as Record<string, unknown> | undefined;
  if (recoverySummary && typeof recoverySummary === "object") {
    const phaseMode = typeof recoverySummary["phase_mode"] === "string"
      ? String(recoverySummary["phase_mode"])
      : "";
    const nextAction = typeof recoverySummary["next_action"] === "string"
      ? String(recoverySummary["next_action"])
      : "";
    const nextCommand = typeof recoverySummary["next_command"] === "string"
      ? String(recoverySummary["next_command"])
      : "";
    const routeReason = typeof recoverySummary["route_reason"] === "string"
      ? String(recoverySummary["route_reason"])
      : "";
    if (phaseMode || nextAction || nextCommand || routeReason) {
      lines.push(
        [
          phaseMode ? `Phase: ${phaseMode}.` : "",
          nextAction ? `Next action: ${nextAction}.` : "",
          nextCommand ? `Next command: ${nextCommand}.` : "",
          routeReason ? `Reason: ${routeReason}.` : "",
        ].filter(Boolean).join(" "),
      );
    }
  }
```

- [ ] **Step 4: Re-run the focused tests**

Run:

```bash
uv run pytest tests/contract/test_hook_cli_surface.py::test_hook_workflow_policy_outputs_redirect_payload -q
npm --prefix extensions/agent-teams/engine test -- specify-quality-adapter.test.ts
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/specify_cli/__init__.py tests/contract/test_hook_cli_surface.py extensions/agent-teams/engine/src/hooks/specify-quality-adapter.ts extensions/agent-teams/engine/src/hooks/__tests__/specify-quality-adapter.test.ts
git commit -m "feat: expose recovery summaries through hook adapters"
```

---

### Task 5: Wire Claude and Gemini native hooks to emit recovery summaries and redirects

**Files:**
- Modify: `src/specify_cli/integrations/claude/hooks/claude-hook-dispatch.py`
- Modify: `src/specify_cli/integrations/gemini/hooks/gemini-hook-dispatch.py`
- Modify: `tests/integrations/test_integration_claude.py`
- Modify: `tests/integrations/test_integration_gemini.py`

- [ ] **Step 1: Add failing Claude and Gemini integration tests**

Add this Claude test to `tests/integrations/test_integration_claude.py`:

```python
    def test_claude_hook_session_start_appends_recovery_summary(self, tmp_path):
        integration = get_integration("claude")
        manifest = IntegrationManifest("claude", tmp_path)
        integration.setup(tmp_path, manifest, script_type="sh")

        feature_dir = tmp_path / "specs" / "001-demo"
        feature_dir.mkdir(parents=True, exist_ok=True)
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
                    "- phase_mode: `planning-only`",
                    "- summary: refine scope",
                    "",
                    "## Allowed Artifact Writes",
                    "",
                    "- spec.md",
                    "",
                    "## Forbidden Actions",
                    "",
                    "- edit source code",
                    "",
                    "## Authoritative Files",
                    "",
                    "- spec.md",
                    "",
                    "## Next Action",
                    "",
                    "- refine scope",
                    "",
                    "## Next Command",
                    "",
                    "- `/sp.plan`",
                    "",
                    "## Learning Signals",
                    "",
                    "- route_reason: `spec not yet approved for planning`",
                ]
            ),
            encoding="utf-8",
        )

        env = os.environ.copy()
        env["CLAUDE_PROJECT_DIR"] = str(tmp_path)
        repo_root = Path(__file__).resolve().parents[2]
        env["PYTHONPATH"] = str(repo_root / "src")

        hook_script = tmp_path / ".claude" / "hooks" / "claude-hook-dispatch.py"
        result = subprocess.run(
            [sys.executable, str(hook_script), "session-start"],
            input=json.dumps({"hook_event_name": "SessionStart"}),
            text=True,
            capture_output=True,
            check=False,
            env=env,
            cwd=tmp_path,
        )

        payload = json.loads(result.stdout.strip())
        context = payload["hookSpecificOutput"]["additionalContext"]
        assert "planning-only" in context
        assert "/sp.plan" in context
```

Add this Gemini test to `tests/integrations/test_integration_gemini.py`:

```python
    def test_gemini_hook_before_agent_returns_redirect_for_phase_drift(self, tmp_path):
        integration = get_integration("gemini")
        manifest = IntegrationManifest("gemini", tmp_path)
        integration.setup(tmp_path, manifest, script_type="sh")

        feature_dir = tmp_path / "specs" / "001-demo"
        feature_dir.mkdir(parents=True, exist_ok=True)
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
                    "- phase_mode: `planning-only`",
                    "- summary: refine scope",
                    "",
                    "## Allowed Artifact Writes",
                    "",
                    "- spec.md",
                    "",
                    "## Forbidden Actions",
                    "",
                    "- edit source code",
                    "",
                    "## Authoritative Files",
                    "",
                    "- spec.md",
                    "",
                    "## Next Action",
                    "",
                    "- refine scope",
                    "",
                    "## Next Command",
                    "",
                    "- `/sp.plan`",
                    "",
                    "## Learning Signals",
                    "",
                    "- route_reason: `spec not yet approved for planning`",
                ]
            ),
            encoding="utf-8",
        )

        env = os.environ.copy()
        env["GEMINI_PROJECT_DIR"] = str(tmp_path)
        repo_root = Path(__file__).resolve().parents[2]
        env["PYTHONPATH"] = str(repo_root / "src")

        hook_script = tmp_path / ".gemini" / "hooks" / "gemini-hook-dispatch.py"
        result = subprocess.run(
            [sys.executable, str(hook_script), "before-agent"],
            input=json.dumps(
                {
                    "llm_request": {
                        "messages": [
                            {
                                "role": "user",
                                "parts": [{"text": "start editing code now"}],
                            }
                        ]
                    }
                }
            ),
            text=True,
            capture_output=True,
            check=False,
            env=env,
            cwd=tmp_path,
        )

        payload = json.loads(result.stdout.strip())
        assert payload["decision"] == "deny"
        assert "/sp.plan" in payload.get("systemMessage", "")
```

- [ ] **Step 2: Run the focused integration tests to verify they fail**

Run:

```bash
uv run pytest tests/integrations/test_integration_claude.py::TestClaudeIntegration::test_claude_hook_session_start_appends_recovery_summary tests/integrations/test_integration_gemini.py::TestGeminiIntegration::test_gemini_hook_before_agent_returns_redirect_for_phase_drift -q
```

Expected: FAIL because native hook outputs do not yet include the structured recovery summary or redirect system message.

- [ ] **Step 3: Extend Claude `SessionStart` and prompt handling**

In `src/specify_cli/integrations/claude/hooks/claude-hook-dispatch.py`, inside `_compaction_resume_context()`, prefer `artifact["recovery_summary"]` before falling back to `phase_state` and `resume_cue`:

```python
    recovery_summary = artifact.get("recovery_summary", {})
    if isinstance(recovery_summary, dict):
        phase_mode = str(recovery_summary.get("phase_mode") or "").strip()
        next_action = str(recovery_summary.get("next_action") or "").strip()
        next_command = str(recovery_summary.get("next_command") or "").strip()
        route_reason = str(recovery_summary.get("route_reason") or "").strip()
        parts = [
            f"Phase: {phase_mode}." if phase_mode else "",
            f"Next action: {next_action}." if next_action else "",
            f"Next command: {next_command}." if next_command else "",
            f"Reason: {route_reason}." if route_reason else "",
        ]
        summary = " ".join(part for part in parts if part).strip()
        if summary:
            return summary
```

Then in `_handle_user_prompt_submit()`, if `policy_output` is a block with a `systemMessage`, preserve it exactly instead of collapsing to only the reason.

- [ ] **Step 4: Extend Gemini recovery and prompt-entry behavior**

In `src/specify_cli/integrations/gemini/hooks/gemini-hook-dispatch.py`, mirror the same `recovery_summary` handling in its compaction/resume helper. Then, in the prompt-entry handler, if `workflow-policy` returns `warn` with `classification == "redirect"`, return:

```python
    return {
        "decision": "deny",
        "reason": "requested action conflicts with the active workflow phase",
        "systemMessage": redirect_message,
    }
```

where `redirect_message` is assembled from `recovery_summary["phase_mode"]`, `next_action`, `next_command`, and `route_reason`.

- [ ] **Step 5: Re-run the focused integration tests**

Run:

```bash
uv run pytest tests/integrations/test_integration_claude.py::TestClaudeIntegration::test_claude_hook_session_start_appends_recovery_summary tests/integrations/test_integration_gemini.py::TestGeminiIntegration::test_gemini_hook_before_agent_returns_redirect_for_phase_drift -q
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/specify_cli/integrations/claude/hooks/claude-hook-dispatch.py src/specify_cli/integrations/gemini/hooks/gemini-hook-dispatch.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_gemini.py
git commit -m "feat: surface workflow recovery in native hook adapters"
```

---

### Task 6: Wire Codex native hooks to the same recovery-summary and redirect-first contract

**Files:**
- Modify: `extensions/agent-teams/engine/src/scripts/codex-native-hook.ts`
- Modify: `extensions/agent-teams/engine/src/scripts/__tests__/codex-native-hook.test.ts`

- [ ] **Step 1: Add the failing Codex native-hook tests**

Add this test to `extensions/agent-teams/engine/src/scripts/__tests__/codex-native-hook.test.ts`:

```ts
  it("adds the shared recovery summary to SessionStart output", async () => {
    const cwd = await mkdtemp(join(tmpdir(), "codex-native-hook-"));
    tempDirs.push(cwd);
    await mkdir(join(cwd, ".specify"), { recursive: true });
    const featureDir = join(cwd, "specs", "001-demo");
    await mkdir(featureDir, { recursive: true });
    await writeFile(
      join(featureDir, "workflow-state.md"),
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
        "- phase_mode: `planning-only`",
        "- summary: refine scope",
        "",
        "## Allowed Artifact Writes",
        "",
        "- spec.md",
        "",
        "## Forbidden Actions",
        "",
        "- edit source code",
        "",
        "## Authoritative Files",
        "",
        "- spec.md",
        "",
        "## Next Action",
        "",
        "- refine scope",
        "",
        "## Next Command",
        "",
        "- `/sp.plan`",
        "",
        "## Learning Signals",
        "",
        "- route_reason: `spec not yet approved for planning`",
        "",
      ].join("\n"),
      "utf-8",
    );

    const result = await dispatchCodexNativeHook(
      JSON.stringify({ hookEventName: "SessionStart" }),
      { cwd },
    );

    assert.match(JSON.stringify(result.outputJson ?? {}), /planning-only/);
    assert.match(JSON.stringify(result.outputJson ?? {}), /\/sp\.plan/);
  });
```

Add this second test:

```ts
  it("returns a block output for repeated shared phase drift", async () => {
    const cwd = await mkdtemp(join(tmpdir(), "codex-native-hook-"));
    tempDirs.push(cwd);
    await mkdir(join(cwd, ".specify"), { recursive: true });
    const featureDir = join(cwd, "specs", "001-demo");
    await mkdir(featureDir, { recursive: true });
    await writeFile(
      join(featureDir, "workflow-state.md"),
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
        "- phase_mode: `planning-only`",
        "- summary: refine scope",
        "",
        "## Allowed Artifact Writes",
        "",
        "- spec.md",
        "",
        "## Forbidden Actions",
        "",
        "- edit source code",
        "",
        "## Authoritative Files",
        "",
        "- spec.md",
        "",
        "## Next Action",
        "",
        "- refine scope",
        "",
        "## Next Command",
        "",
        "- `/sp.plan`",
        "",
        "## Learning Signals",
        "",
        "- route_reason: `spec not yet approved for planning`",
        "",
      ].join("\n"),
      "utf-8",
    );

    const result = await dispatchCodexNativeHook(
      JSON.stringify({
        hookEventName: "UserPromptSubmit",
        prompt: "start editing code now",
        activeContext: { prior_redirect_count: 1 },
      }),
      { cwd },
    );

    assert.equal(result.outputJson?.decision, "block");
  });
```

- [ ] **Step 2: Run the focused Node tests to verify they fail**

Run:

```bash
npm --prefix extensions/agent-teams/engine test -- codex-native-hook.test.ts
```

Expected: FAIL because `dispatchCodexNativeHook()` does not yet append structured recovery summaries or pass repeated-drift information through to shared policy evaluation.

- [ ] **Step 3: Append recovery summaries in `codex-native-hook.ts`**

In `extensions/agent-teams/engine/src/scripts/codex-native-hook.ts`, after the existing `appendSharedHookContext()` usage for `SessionStart` and `Stop`, make sure the shared payload from `build-compaction` or `read-compaction` is passed through unchanged so the new `recovery_summary` text reaches the final output. Do not create Codex-only wording.

Also, when building workflow-policy hook args for prompt submission, include:

```ts
  if (typeof activeContext["prior_redirect_count"] === "number") {
    args.push("--prior-redirect-count", String(activeContext["prior_redirect_count"]));
  }
```

and add the matching CLI option in Python in Task 7 below.

- [ ] **Step 4: Re-run the focused Node tests**

Run:

```bash
npm --prefix extensions/agent-teams/engine test -- codex-native-hook.test.ts
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add extensions/agent-teams/engine/src/scripts/codex-native-hook.ts extensions/agent-teams/engine/src/scripts/__tests__/codex-native-hook.test.ts
git commit -m "feat: align codex native hooks with recovery contract"
```

---

### Task 7: Add CLI support for repeated-drift escalation and update workflow docs

**Files:**
- Modify: `src/specify_cli/__init__.py`
- Modify: `templates/workflow-state-template.md`
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/implement.md`
- Modify: `docs/quickstart.md`
- Modify: `src/specify_cli/integrations/claude/hooks/README.md`
- Modify: `src/specify_cli/integrations/gemini/hooks/README.md`
- Modify: `tests/test_alignment_templates.py`

- [ ] **Step 1: Add failing template and CLI surface tests**

Add this assertion to the workflow-state template guidance test block in `tests/test_alignment_templates.py`:

```python
    assert "Allowed Artifact Writes" in content
    assert "Forbidden Actions" in content
    assert "Authoritative Files" in content
    assert "Re-read this file first after compaction or session recovery." in content
```

Add this CLI surface test to `tests/contract/test_hook_cli_surface.py`:

```python
def test_hook_workflow_policy_accepts_prior_redirect_count(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True, exist_ok=True)
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
                "- phase_mode: `planning-only`",
                "- summary: demo",
                "",
                "## Allowed Artifact Writes",
                "",
                "- spec.md",
                "",
                "## Forbidden Actions",
                "",
                "- edit source code",
                "",
                "## Authoritative Files",
                "",
                "- spec.md",
                "",
                "## Next Action",
                "",
                "- refine scope",
                "",
                "## Next Command",
                "",
                "- `/sp.plan`",
                "",
                "## Learning Signals",
                "",
                "- route_reason: `spec not yet approved for planning`",
            ]
        ),
        encoding="utf-8",
    )

    result = _invoke_in_project(
        project,
        [
            "hook",
            "workflow-policy",
            "--command",
            "specify",
            "--feature-dir",
            str(feature_dir),
            "--trigger",
            "prompt",
            "--requested-action",
            "start_editing_code",
            "--prior-redirect-count",
            "1",
        ],
    )

    payload = json.loads(result.output.strip())
    assert payload["status"] == "blocked"
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run:

```bash
uv run pytest tests/test_alignment_templates.py tests/contract/test_hook_cli_surface.py::test_hook_workflow_policy_accepts_prior_redirect_count -q
```

Expected: FAIL because the CLI does not yet accept `--prior-redirect-count`.

- [ ] **Step 3: Add the CLI option and pass it through**

In `src/specify_cli/__init__.py`, update `hook_workflow_policy_command()` with:

```python
    prior_redirect_count: int = typer.Option(0, "--prior-redirect-count", help="Number of prior redirect outcomes for this active workflow"),
```

and pass it through:

```python
            "prior_redirect_count": prior_redirect_count,
```

- [ ] **Step 4: Update template and documentation wording**

Make these exact documentation additions:

In `templates/workflow-state-template.md`, keep the current sections and ensure the file clearly preserves:

```markdown
- Re-read this file first after compaction or session recovery.
- Re-read the authoritative files before taking the next step.
- If the next action conflicts with the current `phase_mode`, stop and repair the workflow state instead of improvising.
```

In `docs/quickstart.md`, add one short paragraph under the native-hook guidance explaining that active `sp-*` workflows now surface a structured recovery summary on resume and use redirect-first enforcement before hard-blocking repeated phase jumps.

In the Claude and Gemini hook READMEs, add bullets documenting:

- `SessionStart` recovery summary injection
- prompt-entry redirect-first handling for active workflows
- repeated or explicit phase jumps being blocked by shared workflow policy

- [ ] **Step 5: Re-run the focused documentation and CLI tests**

Run:

```bash
uv run pytest tests/test_alignment_templates.py tests/contract/test_hook_cli_surface.py::test_hook_workflow_policy_accepts_prior_redirect_count -q
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add src/specify_cli/__init__.py templates/workflow-state-template.md templates/commands/specify.md templates/commands/plan.md templates/commands/implement.md docs/quickstart.md src/specify_cli/integrations/claude/hooks/README.md src/specify_cli/integrations/gemini/hooks/README.md tests/test_alignment_templates.py tests/contract/test_hook_cli_surface.py
git commit -m "docs: document workflow recovery phase continuity"
```

---

### Task 8: Run the full verification suite for the recovery-contract change set

**Files:**
- Modify: none
- Test: `tests/hooks/test_hook_engine.py`
- Test: `tests/hooks/test_state_hooks.py`
- Test: `tests/hooks/test_workflow_policy_hooks.py`
- Test: `tests/hooks/test_compaction_hooks.py`
- Test: `tests/hooks/test_statusline_hooks.py`
- Test: `tests/contract/test_hook_cli_surface.py`
- Test: `tests/integrations/test_integration_claude.py`
- Test: `tests/integrations/test_integration_gemini.py`
- Test: `extensions/agent-teams/engine/src/hooks/__tests__/specify-quality-adapter.test.ts`
- Test: `extensions/agent-teams/engine/src/scripts/__tests__/codex-native-hook.test.ts`

- [ ] **Step 1: Run the full Python verification slice**

Run:

```bash
uv run pytest tests/hooks/test_hook_engine.py tests/hooks/test_state_hooks.py tests/hooks/test_workflow_policy_hooks.py tests/hooks/test_compaction_hooks.py tests/hooks/test_statusline_hooks.py tests/contract/test_hook_cli_surface.py tests/integrations/test_integration_claude.py tests/integrations/test_integration_gemini.py -q
```

Expected: PASS

- [ ] **Step 2: Run the focused Node verification slice**

Run:

```bash
npm --prefix extensions/agent-teams/engine test -- specify-quality-adapter.test.ts codex-native-hook.test.ts
```

Expected: PASS

- [ ] **Step 3: Review the final diff**

Run:

```bash
git diff --stat HEAD~7..HEAD
```

Expected: shows only the shared recovery-contract, native hook, template, doc, and test files planned above

- [ ] **Step 4: Commit the verification checkpoint**

```bash
git commit --allow-empty -m "chore: verify workflow recovery phase continuity"
```

---

## Self-Review

### Spec coverage

- Unified recovery contract: covered by Tasks 1 and 2.
- Existing state files remain canonical: covered by Tasks 1, 2, and 3.
- Structured recovery summary on resume-class events: covered by Tasks 2, 4, 5, and 6.
- Redirect-first enforcement and repeated-drift blocking: covered by Tasks 3, 5, 6, and 7.
- Template and doc alignment: covered by Task 7.
- Verification and rollout readiness: covered by Task 8.

### Placeholder scan

- No `TODO`, `TBD`, or “similar to previous task” placeholders remain.
- Every code-changing step includes exact file paths and concrete code snippets.
- Every verification step includes exact commands and expected results.

### Type consistency

- Shared policy outcome names are consistently `allow`, `redirect`, `repairable-block`, and `blocked`.
- Recovery-contract field names remain consistent across Python, adapter, and test tasks:
  - `allowed_artifact_writes`
  - `forbidden_actions`
  - `authoritative_files`
  - `recovery_summary`
  - `prior_redirect_count`

