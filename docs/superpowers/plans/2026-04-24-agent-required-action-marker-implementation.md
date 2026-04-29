# Agent-Required Action Marker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** add a first-class `[AGENT]` required-action marker, preserve user `AGENTS.md` files through a Spec Kit managed block, and roll the new hard-action carrier across `sp-fast`, `sp-quick`, `sp-map-codebase`, and the rest of the shared `sp-*` workflow surface without changing existing `[P]` semantics.

**Architecture:** keep the current `[P] + batch + strategy` execution model intact, add a separate marker-parsing layer for `[AGENT]`, update shared command templates so hard gates are rendered as explicit `[AGENT]` lines, and teach the shared `update-agent-context` scripts to upsert a bounded `<!-- SPEC-KIT:BEGIN --> ... <!-- SPEC-KIT:END -->` block inside existing `AGENTS.md` files instead of mutating the whole file. Deliver the change in three slices: managed-block support, marker semantics plus first-wave templates, then the remaining shared workflows and documentation/tests.

**Tech Stack:** Python 3.13, Typer CLI, Markdown templates, Bash and PowerShell update scripts, pytest, Typer `CliRunner`

---

## File Structure

### Existing files to modify

- `scripts/bash/update-agent-context.sh`
  - Add managed-block constants and upsert helpers for root `AGENTS.md` targets while preserving current `.mdc` frontmatter behavior.
- `scripts/powershell/update-agent-context.ps1`
  - Mirror the managed-block logic from the bash script for Windows flows.
- `templates/commands/fast.md`
  - Mark fast-path hard gates as `[AGENT]`, including `learning start`, project-map sufficiency checks, and post-run capture.
- `templates/commands/quick.md`
  - Mark quick-task hard gates as `[AGENT]`, including `STATUS.md` recovery, learning start, project-map loading, strategy choice, and capture.
- `templates/commands/map-codebase.md`
  - Mark map refresh decisions and live-file scouting gates as `[AGENT]`.
- `templates/commands/specify.md`
  - Mark learning start, workflow-state recovery, project-map load, and strategy selection as `[AGENT]`.
- `templates/commands/plan.md`
  - Mark learning start, workflow-state recovery, project-map load, strategy selection, and constitution preservation steps as `[AGENT]`.
- `templates/commands/tasks.md`
  - Mark learning start, workflow-state recovery, project-map load, strategy selection, `Task Guardrail Index`, and join-point generation as `[AGENT]`.
- `templates/commands/implement.md`
  - Mark learning start, tracker recovery, project-map load, per-batch strategy choice, packet compile/validate, and result consumption as `[AGENT]`.
- `templates/commands/debug.md`
  - Mark learning start, debug-state recovery, project-map load, strategy choice, and blocker-evidence gathering as `[AGENT]`.
- `templates/tasks-template.md`
  - Document that `[AGENT]` is a valid task or guardrail marker independent from `[P]`.
- `src/specify_cli/codex_team/auto_dispatch.py`
  - Parse `[AGENT]` as an independent marker without changing current `[P]` handling.
- `AGENTS.md`
  - Document the new marker semantics and managed-block policy in the repository’s own operator guidance.
- `README.md`
  - Teach `[AGENT]`, the managed `AGENTS.md` block, and the first-wave command coverage.
- `docs/quickstart.md`
  - Reflect the same marker semantics and rollout coverage in the shorter workflow docs.
- `tests/test_cursor_frontmatter.py`
  - Keep the `.mdc` behavior covered while adding script-level coverage for managed-block updates.
- `tests/test_agent_config_consistency.py`
  - Extend script-consistency checks so managed-block markers and supported agent cases stay aligned.
- `tests/test_fast_template_guidance.py`
  - Add assertions for `[AGENT]` hard gates in `sp-fast`.
- `tests/test_quick_template_guidance.py`
  - Add assertions for `[AGENT]` hard gates in `sp-quick`.
- `tests/test_alignment_templates.py`
  - Extend shared template assertions for `[AGENT]` marker presence across `specify`, `plan`, `tasks`, `implement`, and `debug`.
- `tests/test_specify_guidance_docs.py`
  - Assert that repo docs explain `[AGENT]`, managed blocks, and `sp-fast` / `sp-quick` / `sp-map-codebase` coverage.
- `tests/integrations/test_integration_codex.py`
  - Verify generated Codex skills preserve the new `[AGENT]` lines and managed-block aware guidance.
- `tests/integrations/test_integration_claude.py`
  - Verify the shared-skills path preserves the same `[AGENT]` lines for non-Codex skills consumers.
- `tests/codex_team/test_auto_dispatch.py`
  - Assert `[AGENT]` parsing is independent from `[P]` routing.

### New files to create

- `src/specify_cli/workflow_markers.py`
  - Own canonical parsing helpers for `[AGENT]` and future workflow markers.
- `tests/test_workflow_markers.py`
  - Own pure unit tests for marker parsing, including `[AGENT]`/`[P]` independence.
- `tests/test_agent_context_managed_block.py`
  - Own focused managed-block tests for `update-agent-context.sh` and `update-agent-context.ps1`.
- `tests/test_map_codebase_template_guidance.py`
  - Own focused assertions for `[AGENT]` hard gates in `sp-map-codebase`.

### Design boundaries

- Do not overwrite user-authored content outside the managed `AGENTS.md` block.
- Do not reinterpret `[AGENT]` as parallelism, subagent routing, or delegation.
- Do not change the current `[P]` routing semantics in `auto_dispatch`.
- Do not block this work on a full runtime-enforcement engine; first deliver the marker carrier, managed block, parser semantics, and template/test coverage.
- Preserve existing uncommitted edits in modified files by making surgical additions rather than broad rewrites.

## Task 1: Add Managed `AGENTS.md` Block Support To The Shared Update Scripts

**Files:**
- Modify: `scripts/bash/update-agent-context.sh`
- Modify: `scripts/powershell/update-agent-context.ps1`
- Create: `tests/test_agent_context_managed_block.py`
- Modify: `tests/test_cursor_frontmatter.py`

- [ ] **Step 1: Write failing managed-block tests for bash and PowerShell**

Create `tests/test_agent_context_managed_block.py`:

```python
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
BASH_SCRIPT = REPO_ROOT / "scripts" / "bash" / "update-agent-context.sh"
POWERSHELL_SCRIPT = REPO_ROOT / "scripts" / "powershell" / "update-agent-context.ps1"
BLOCK_START = "<!-- SPEC-KIT:BEGIN -->"
BLOCK_END = "<!-- SPEC-KIT:END -->"


def _seed_repo(repo: Path) -> None:
    subprocess.run(["git", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True, capture_output=True)
    (repo / ".specify" / "templates").mkdir(parents=True, exist_ok=True)
    (repo / ".specify" / "templates" / "agent-file-template.md").write_text(
        "# [PROJECT NAME]\n\nLast updated: [DATE]\n\n## Active Technologies\n\n[EXTRACTED FROM ALL PLAN.MD FILES]\n\n## Recent Changes\n\n[LAST 3 FEATURES AND WHAT THEY ADDED]\n",
        encoding="utf-8",
    )
    spec_dir = repo / "specs" / "001-test-feature"
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "plan.md").write_text(
        "**Language/Version**: Python 3.13\n**Primary Dependencies**: Typer\n**Storage**: N/A\n**Project Type**: cli\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)
    subprocess.run(["git", "checkout", "-b", "001-test-feature"], cwd=repo, check=True, capture_output=True)


@pytest.mark.skipif(shutil.which("bash") is None, reason="bash is not installed")
def test_bash_script_inserts_managed_block_without_overwriting_user_content(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_repo(repo)
    agents = repo / "AGENTS.md"
    agents.write_text("# User Notes\n\nKeep this line.\n", encoding="utf-8")

    result = subprocess.run(
        ["bash", str(BASH_SCRIPT), "codex"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    content = agents.read_text(encoding="utf-8")
    assert "# User Notes" in content
    assert "Keep this line." in content
    assert BLOCK_START in content
    assert BLOCK_END in content


def test_powershell_script_replaces_existing_managed_block_only(tmp_path: Path) -> None:
    if shutil.which("pwsh") is None:
        pytest.skip("pwsh is not installed")
    repo = tmp_path / "repo"
    repo.mkdir()
    _seed_repo(repo)
    agents = repo / "AGENTS.md"
    agents.write_text(
        "# User Notes\n\nalpha\n\n<!-- SPEC-KIT:BEGIN -->\nold block\n<!-- SPEC-KIT:END -->\n\nomega\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        ["pwsh", "-File", str(POWERSHELL_SCRIPT), "-AgentType", "codex"],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    content = agents.read_text(encoding="utf-8")
    assert content.count(BLOCK_START) == 1
    assert content.count(BLOCK_END) == 1
    assert "old block" not in content
    assert "alpha" in content
    assert "omega" in content
```

- [ ] **Step 2: Run the managed-block tests and verify they fail**

Run:

```powershell
python -m pytest tests/test_agent_context_managed_block.py -q
```

Expected:

```text
AssertionError: '<!-- SPEC-KIT:BEGIN -->' not found in AGENTS.md
```

- [ ] **Step 3: Add managed-block helpers to the bash update script**

Modify `scripts/bash/update-agent-context.sh` by adding helpers near the utility section:

```bash
SPEC_KIT_BLOCK_START="<!-- SPEC-KIT:BEGIN -->"
SPEC_KIT_BLOCK_END="<!-- SPEC-KIT:END -->"

render_speckit_managed_block() {
    cat <<'EOF'
<!-- SPEC-KIT:BEGIN -->
## Spec Kit Plus Managed Rules

- `[AGENT]` marks an action the AI must explicitly execute.
- `[AGENT]` is independent from `[P]`.
- Preserve content outside this managed block.
<!-- SPEC-KIT:END -->
EOF
}

upsert_speckit_managed_block() {
    local target_file="$1"
    local rendered_block
    rendered_block="$(render_speckit_managed_block)"
    if grep -q "$SPEC_KIT_BLOCK_START" "$target_file" && grep -q "$SPEC_KIT_BLOCK_END" "$target_file"; then
        python - "$target_file" "$SPEC_KIT_BLOCK_START" "$SPEC_KIT_BLOCK_END" "$rendered_block" <<'PY'
from pathlib import Path
import sys
path = Path(sys.argv[1])
start = sys.argv[2]
end = sys.argv[3]
block = sys.argv[4]
content = path.read_text(encoding="utf-8")
before, rest = content.split(start, 1)
_old, after = rest.split(end, 1)
path.write_text(before.rstrip() + "\n\n" + block + after, encoding="utf-8")
PY
    else
        printf "%s\n\n%s\n" "$(cat "$target_file")" "$rendered_block" > "$target_file"
    fi
}
```

Then call the helper inside the `AGENTS.md` path of both create and update flows:

```bash
if [[ "$(basename "$target_file")" == "AGENTS.md" ]]; then
    upsert_speckit_managed_block "$target_file"
fi
```

- [ ] **Step 4: Mirror the same managed-block behavior in PowerShell**

Modify `scripts/powershell/update-agent-context.ps1` by adding:

```powershell
$script:SpecKitBlockStart = '<!-- SPEC-KIT:BEGIN -->'
$script:SpecKitBlockEnd = '<!-- SPEC-KIT:END -->'

function Get-SpecKitManagedBlock {
@"
<!-- SPEC-KIT:BEGIN -->
## Spec Kit Plus Managed Rules

- `[AGENT]` marks an action the AI must explicitly execute.
- `[AGENT]` is independent from `[P]`.
- Preserve content outside this managed block.
<!-- SPEC-KIT:END -->
"@
}

function Update-SpecKitManagedBlock {
    param([string]$TargetFile)
    $content = if (Test-Path $TargetFile) { Get-Content -LiteralPath $TargetFile -Raw -Encoding utf8 } else { '' }
    $block = Get-SpecKitManagedBlock
    if ($content.Contains($script:SpecKitBlockStart) -and $content.Contains($script:SpecKitBlockEnd)) {
        $pattern = "(?s)$([regex]::Escape($script:SpecKitBlockStart)).*?$([regex]::Escape($script:SpecKitBlockEnd))"
        $content = [regex]::Replace($content, $pattern, $block)
    }
    elseif ([string]::IsNullOrWhiteSpace($content)) {
        $content = $block
    }
    else {
        $content = $content.TrimEnd() + [Environment]::NewLine + [Environment]::NewLine + $block + [Environment]::NewLine
    }
    Set-Content -LiteralPath $TargetFile -Value $content -Encoding utf8
}
```

Then call `Update-SpecKitManagedBlock` in the `AGENTS.md` create/update path after file content is generated.

- [ ] **Step 5: Re-run the managed-block and cursor-frontmatter tests**

Run:

```powershell
python -m pytest tests/test_agent_context_managed_block.py tests/test_cursor_frontmatter.py -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 6: Commit**

```powershell
git add scripts/bash/update-agent-context.sh scripts/powershell/update-agent-context.ps1 tests/test_agent_context_managed_block.py tests/test_cursor_frontmatter.py
git commit -m "feat: manage spec-kit rules in AGENTS blocks"
```

## Task 2: Add Canonical `[AGENT]` Marker Parsing Without Changing `[P]` Behavior

**Files:**
- Create: `src/specify_cli/workflow_markers.py`
- Modify: `src/specify_cli/codex_team/auto_dispatch.py`
- Create: `tests/test_workflow_markers.py`
- Modify: `tests/codex_team/test_auto_dispatch.py`

- [ ] **Step 1: Write failing marker-semantic tests**

Create `tests/test_workflow_markers.py`:

```python
from specify_cli.workflow_markers import has_agent_marker, has_parallel_marker, strip_known_markers


def test_agent_marker_is_independent_from_parallel_marker() -> None:
    assert has_agent_marker("- [ ] T017 [AGENT] Read PROJECT-HANDBOOK.md") is True
    assert has_parallel_marker("- [ ] T017 [AGENT] Read PROJECT-HANDBOOK.md") is False
    assert has_agent_marker("- [ ] T018 [P] Build batch") is False
    assert has_parallel_marker("- [ ] T018 [P] Build batch") is True


def test_strip_known_markers_preserves_human_summary() -> None:
    cleaned = strip_known_markers(" [P] [AGENT] Re-evaluate strategy after join point ")
    assert cleaned == "Re-evaluate strategy after join point"
```

Append to `tests/codex_team/test_auto_dispatch.py`:

```python
def test_parse_tasks_markdown_captures_agent_required_without_redefining_parallel(codex_team_project_root: Path):
    feature_dir = _write_feature_tasks(
        codex_team_project_root,
        \"\"\"# Tasks

- [X] T001 Setup
- [ ] T002 [AGENT] Read handbook
- [ ] T003 [P] [AGENT] Worker lane
\"\"\",
    )

    parsed = parse_tasks_markdown(feature_dir / "tasks.md")

    assert parsed.tasks[1].agent_required is True
    assert parsed.tasks[1].parallel is False
    assert parsed.tasks[2].agent_required is True
    assert parsed.tasks[2].parallel is True
```

- [ ] **Step 2: Run the marker tests and verify they fail**

Run:

```powershell
python -m pytest tests/test_workflow_markers.py tests/codex_team/test_auto_dispatch.py -q
```

Expected:

```text
E   ModuleNotFoundError: No module named 'specify_cli.workflow_markers'
```

- [ ] **Step 3: Add the shared marker helper module**

Create `src/specify_cli/workflow_markers.py`:

```python
from __future__ import annotations

import re


AGENT_MARKER = "[AGENT]"
PARALLEL_MARKER = "[P]"
_KNOWN_MARKER_RE = re.compile(r"\[(?:AGENT|P)\]")


def has_agent_marker(text: str) -> bool:
    return AGENT_MARKER in text


def has_parallel_marker(text: str) -> bool:
    return PARALLEL_MARKER in text


def strip_known_markers(text: str) -> str:
    return " ".join(_KNOWN_MARKER_RE.sub(" ", text).split())
```

- [ ] **Step 4: Extend `auto_dispatch.py` to parse `agent_required` separately**

Modify `src/specify_cli/codex_team/auto_dispatch.py`:

```python
from specify_cli.workflow_markers import has_agent_marker, has_parallel_marker


@dataclass(slots=True)
class ParsedTask:
    task_id: str
    completed: bool
    parallel: bool
    agent_required: bool
    summary: str
    order_index: int
```

Then update task construction:

```python
tasks.append(
    ParsedTask(
        task_id=task_match.group("task_id"),
        completed=task_match.group("mark").lower() == "x",
        parallel=has_parallel_marker(rest),
        agent_required=has_agent_marker(rest),
        summary=rest.strip(),
        order_index=len(tasks),
    )
)
```

- [ ] **Step 5: Re-run the marker tests**

Run:

```powershell
python -m pytest tests/test_workflow_markers.py tests/codex_team/test_auto_dispatch.py -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 6: Commit**

```powershell
git add src/specify_cli/workflow_markers.py src/specify_cli/codex_team/auto_dispatch.py tests/test_workflow_markers.py tests/codex_team/test_auto_dispatch.py
git commit -m "feat: add independent agent-required marker parsing"
```

## Task 3: Roll `[AGENT]` Through `sp-fast`, `sp-quick`, And `sp-map-codebase`

**Files:**
- Modify: `templates/commands/fast.md`
- Modify: `templates/commands/quick.md`
- Modify: `templates/commands/map-codebase.md`
- Modify: `tests/test_fast_template_guidance.py`
- Modify: `tests/test_quick_template_guidance.py`
- Create: `tests/test_map_codebase_template_guidance.py`

- [ ] **Step 1: Add failing template assertions for `[AGENT]` hard gates**

Append to `tests/test_fast_template_guidance.py`:

```python
def test_fast_template_marks_learning_and_routing_hard_gates_with_agent_marker() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "fast.md").read_text(encoding="utf-8")

    assert "[AGENT] Run `specify learning start --command fast --format json`" in content
    assert "[AGENT] Read `PROJECT-HANDBOOK.md`." in content or "[AGENT] Read `PROJECT-HANDBOOK.md`" in content
    assert "[AGENT] If `PROJECT-HANDBOOK.md` or `.specify/project-map/` is missing, stop and redirect to `/sp-quick`" in content
    assert "[AGENT] Before the final report, capture any new `pitfall`, `workflow_gap`, or `project_constraint` learning" in content
```

Append to `tests/test_quick_template_guidance.py`:

```python
def test_quick_template_marks_learning_status_and_strategy_gates_with_agent_marker() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "quick.md").read_text(encoding="utf-8")

    assert "[AGENT] Run `specify learning start --command quick --format json`" in content
    assert "[AGENT] Create or resume `STATUS.md`." in content or "[AGENT] Create or resume `STATUS.md`" in content
    assert "[AGENT] Read `PROJECT-HANDBOOK.md`." in content or "[AGENT] Read `PROJECT-HANDBOOK.md`" in content
    assert "[AGENT] Use the shared policy function before execution begins and again at each join point" in content
    assert "[AGENT] Before the final summary, capture any new `pitfall`, `recovery_path`, or `project_constraint` learning" in content
```

Create `tests/test_map_codebase_template_guidance.py`:

```python
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_map_codebase_template_marks_refresh_and_strategy_gates_with_agent_marker() -> None:
    content = (PROJECT_ROOT / "templates" / "commands" / "map-codebase.md").read_text(encoding="utf-8")

    assert "[AGENT] Read `.specify/project-map/index/status.json`" in content
    assert "[AGENT] Read `PROJECT-HANDBOOK.md` and all existing `.specify/project-map/*.md` files if present." in content
    assert "[AGENT] Before broad scouting begins, assess workload shape" in content
    assert "[AGENT] Read only the live files needed to establish current facts" in content
```

- [ ] **Step 2: Run the template guidance tests and verify they fail**

Run:

```powershell
python -m pytest tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_map_codebase_template_guidance.py -q
```

Expected:

```text
AssertionError: '[AGENT]' not found in one or more templates
```

- [ ] **Step 3: Add `[AGENT]` lines to `fast.md`, `quick.md`, and `map-codebase.md`**

Insert representative blocks:

```md
- [AGENT] Run `specify learning start --command fast --format json` when available.
- [AGENT] Read `PROJECT-HANDBOOK.md`.
- [AGENT] If `PROJECT-HANDBOOK.md` or `.specify/project-map/` is missing, stop and redirect to `/sp-quick`.
```

```md
- [AGENT] Run `specify learning start --command quick --format json` when available.
- [AGENT] Create or resume `STATUS.md`.
- [AGENT] Read `PROJECT-HANDBOOK.md`.
- [AGENT] Use `choose_execution_strategy(command_name="quick", snapshot, workload_shape)` before execution begins and again at each join point.
```

```md
- [AGENT] Read `.specify/project-map/index/status.json` if present.
- [AGENT] Read `PROJECT-HANDBOOK.md` and all existing `.specify/project-map/*.md` files if present.
- [AGENT] Before broad scouting begins, assess workload shape and run `choose_execution_strategy(command_name="map-codebase", snapshot, workload_shape)`.
- [AGENT] Read only the live files needed to establish current facts.
```

- [ ] **Step 4: Re-run the template guidance tests**

Run:

```powershell
python -m pytest tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_map_codebase_template_guidance.py -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 5: Commit**

```powershell
git add templates/commands/fast.md templates/commands/quick.md templates/commands/map-codebase.md tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_map_codebase_template_guidance.py
git commit -m "feat: mark fast quick and map hard gates with agent actions"
```

## Task 4: Roll `[AGENT]` Through The Remaining Shared Workflows And Shared Docs

**Files:**
- Modify: `templates/commands/specify.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/tasks.md`
- Modify: `templates/commands/implement.md`
- Modify: `templates/commands/debug.md`
- Modify: `templates/tasks-template.md`
- Modify: `AGENTS.md`
- Modify: `README.md`
- Modify: `docs/quickstart.md`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_specify_guidance_docs.py`
- Modify: `tests/integrations/test_integration_codex.py`
- Modify: `tests/integrations/test_integration_claude.py`

- [ ] **Step 1: Add failing assertions for shared-workflow `[AGENT]` coverage**

Append to `tests/test_alignment_templates.py`:

```python
def test_shared_workflow_templates_mark_hard_gates_with_agent_marker() -> None:
    paths = {
        "specify": Path("templates/commands/specify.md"),
        "plan": Path("templates/commands/plan.md"),
        "tasks": Path("templates/commands/tasks.md"),
        "implement": Path("templates/commands/implement.md"),
        "debug": Path("templates/commands/debug.md"),
    }

    for name, path in paths.items():
        content = path.read_text(encoding="utf-8")
        assert "[AGENT]" in content, f"{name} template missing [AGENT] marker"
```

Append to `tests/test_specify_guidance_docs.py`:

```python
def test_guidance_docs_explain_agent_marker_and_managed_agents_block() -> None:
    readme = _read("README.md")
    quickstart = _read("docs/quickstart.md")
    agents = _read("AGENTS.md")

    for content in (readme, quickstart, agents):
        assert "[AGENT]" in content
        assert "independent from `[P]`" in content

    assert "<!-- SPEC-KIT:BEGIN -->" in agents
    assert "<!-- SPEC-KIT:END -->" in agents
```

Append to `tests/integrations/test_integration_codex.py`:

```python
def test_codex_generated_skills_preserve_agent_required_marker_lines(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "codex-agent-marker"
    result = runner.invoke(app, ["init", str(target), "--ai", "codex", "--no-git", "--ignore-agent-tools", "--script", "sh"])
    assert result.exit_code == 0, result.output

    for skill_name in ("sp-fast", "sp-quick", "sp-map-codebase", "sp-implement"):
        content = (target / ".codex" / "skills" / skill_name / "SKILL.md").read_text(encoding="utf-8")
        assert "[AGENT]" in content
```

Append to `tests/integrations/test_integration_claude.py`:

```python
def test_claude_generated_skills_preserve_agent_required_marker_lines(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    runner = CliRunner()
    target = tmp_path / "claude-agent-marker"
    result = runner.invoke(app, ["init", str(target), "--ai", "claude", "--no-git", "--ignore-agent-tools", "--script", "sh"])
    assert result.exit_code == 0, result.output

    for skill_name in ("sp-fast", "sp-quick", "sp-map-codebase", "sp-implement"):
        content = (target / ".claude" / "skills" / skill_name / "SKILL.md").read_text(encoding="utf-8")
        assert "[AGENT]" in content
```

- [ ] **Step 2: Run the shared-template and integration tests and verify they fail**

Run:

```powershell
python -m pytest tests/test_alignment_templates.py tests/test_specify_guidance_docs.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py -q
```

Expected:

```text
AssertionError: one or more templates or generated skills are missing [AGENT] coverage
```

- [ ] **Step 3: Add `[AGENT]` lines to the remaining workflow templates and tasks template**

Use these representative insertions:

```md
- [AGENT] Run `specify learning start --command specify --format json` when available.
- [AGENT] Create or resume `WORKFLOW_STATE_FILE`.
- [AGENT] Read `PROJECT-HANDBOOK.md`.
- [AGENT] Run `choose_execution_strategy(command_name="specify", snapshot, workload_shape)`.
```

```md
- [AGENT] Run `specify learning start --command implement --format json` when available.
- [AGENT] Create or resume `FEATURE_DIR/implement-tracker.md`.
- [AGENT] Read `PROJECT-HANDBOOK.md`.
- [AGENT] Compile and validate the packet before any delegated work begins.
- [AGENT] Wait for and consume the structured handoff before closing the join point.
```

And in `templates/tasks-template.md` add:

```md
- **[AGENT]**: Marks a task or guardrail action the AI must explicitly execute; it is independent from `[P]`
```

- [ ] **Step 4: Add the managed block and marker explanation to shared docs**

Add this managed block to `AGENTS.md` near the top-level execution guidance:

```md
<!-- SPEC-KIT:BEGIN -->
## Spec Kit Plus Managed Rules

- `[AGENT]` marks an action the AI must explicitly execute.
- `[AGENT]` is independent from `[P]`.
- `sp-fast`, `sp-quick`, and `sp-map-codebase` are first-wave `[AGENT]` workflows and must participate in the passive learning lifecycle.
<!-- SPEC-KIT:END -->
```

Then add concise explanations to `README.md` and `docs/quickstart.md`:

```md
- `[AGENT]` marks a required AI action and is independent from `[P]`.
- Existing `AGENTS.md` files are extended through a managed `SPEC-KIT` block instead of full-file append or replacement.
```

- [ ] **Step 5: Re-run the shared-template and integration tests**

Run:

```powershell
python -m pytest tests/test_alignment_templates.py tests/test_specify_guidance_docs.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 6: Commit**

```powershell
git add templates/commands/specify.md templates/commands/plan.md templates/commands/tasks.md templates/commands/implement.md templates/commands/debug.md templates/tasks-template.md AGENTS.md README.md docs/quickstart.md tests/test_alignment_templates.py tests/test_specify_guidance_docs.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py
git commit -m "feat: propagate agent-required markers across shared workflows"
```

## Task 5: Run The Full Feature Verification Pass And Capture Follow-Up Notes

**Files:**
- Modify: `docs/superpowers/specs/2026-04-24-agent-required-action-marker-design.md`
- Modify: `docs/superpowers/plans/2026-04-24-agent-required-action-marker-implementation.md`

- [ ] **Step 1: Run the complete targeted verification suite**

Run:

```powershell
python -m pytest tests/test_agent_context_managed_block.py tests/test_workflow_markers.py tests/codex_team/test_auto_dispatch.py tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_map_codebase_template_guidance.py tests/test_alignment_templates.py tests/test_specify_guidance_docs.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 2: Run the broader regression set for template and integration stability**

Run:

```powershell
python -m pytest tests/test_agent_config_consistency.py tests/test_extension_skills.py tests/test_cursor_frontmatter.py tests/integrations -q
```

Expected:

```text
all tests passed
```

- [ ] **Step 3: Review the diff for scope drift and preserve unrelated edits**

Run:

```powershell
git status --short
git diff -- scripts/bash/update-agent-context.sh scripts/powershell/update-agent-context.ps1 src/specify_cli/workflow_markers.py src/specify_cli/codex_team/auto_dispatch.py templates/commands/fast.md templates/commands/quick.md templates/commands/map-codebase.md templates/commands/specify.md templates/commands/plan.md templates/commands/tasks.md templates/commands/implement.md templates/commands/debug.md templates/tasks-template.md AGENTS.md README.md docs/quickstart.md tests/test_agent_context_managed_block.py tests/test_workflow_markers.py tests/codex_team/test_auto_dispatch.py tests/test_fast_template_guidance.py tests/test_quick_template_guidance.py tests/test_map_codebase_template_guidance.py tests/test_alignment_templates.py tests/test_specify_guidance_docs.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_claude.py
```

Expected:

```text
only the planned marker, managed-block, documentation, and test changes are present; unrelated user edits remain untouched
```

- [ ] **Step 4: Update the spec or plan only if verification exposed a real gap**

If verification reveals a needed scope correction, amend the design or plan documents with a short note before implementation continues:

```md
## Verification Follow-Up

- [date]: [observed gap] -> [scope adjustment]
```

- [ ] **Step 5: Commit**

```powershell
git add docs/superpowers/specs/2026-04-24-agent-required-action-marker-design.md docs/superpowers/plans/2026-04-24-agent-required-action-marker-implementation.md
git commit -m "chore: verify agent-required marker rollout"
```

## Self-Review

### Spec Coverage

- Managed `AGENTS.md` block: covered in Task 1
- Independent `[AGENT]` semantics: covered in Task 2
- `sp-fast`, `sp-quick`, `sp-map-codebase` first-wave rollout: covered in Task 3
- Remaining shared workflows and docs: covered in Task 4
- Verification and drift review: covered in Task 5

### Placeholder Scan

- No `TODO`, `TBD`, or “similar to Task N” references remain.
- All file paths are explicit.
- All verification steps include exact commands and expected outcomes.

### Type Consistency

- Marker names stay consistent:
  - `[AGENT]`
  - `[P]`
  - `SPEC-KIT:BEGIN`
  - `SPEC-KIT:END`
- Helper names stay consistent:
  - `has_agent_marker`
  - `has_parallel_marker`
  - `strip_known_markers`

Plan complete and saved to `docs/superpowers/plans/2026-04-24-agent-required-action-marker-implementation.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
