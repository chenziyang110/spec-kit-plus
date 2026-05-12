# Cross-Project Project Cognition Reference Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a shared helper surface that discovers nested downstream projects by locating `.specify/`, admits only `fresh` external project cognition as reference context, and lets workflows explicitly read minimal foreign `project-cognition` artifacts without restoring `.specify/project-map/*` as the primary truth path.

**Architecture:** Implement this as a bounded runtime helper, not a new `sp-*` workflow. First lock the contract with failing tests for discovery, admission, CLI surface, and prompt guidance. Then add shared cognition discovery and reference-read helpers under `src/specify_cli/cognition/`, expose them through a new `cognition` Typer group, and update the relevant templates and docs so workflows can opt into explicit external cognition while keeping current-project cognition authoritative. Finish with focused regression runs that prove external cognition stays supplemental, explicit, and `fresh`-gated.

**Tech Stack:** Python 3.13, Typer CLI, Markdown workflow templates, pytest

---

## Scope Check

This plan stays in one execution lane because the approved design is one
shared-runtime capability with one trust model:

- nested downstream project discovery
- external cognition admission gating
- minimal foreign cognition reads
- CLI helper exposure
- workflow guidance updates
- regression coverage

Splitting discovery, CLI, and prompt guidance into separate plans would create
a partially shipped feature where some surfaces teach a capability that the
runtime cannot actually enforce.

## File Structure

```text
MODIFY: cognition runtime public API and helper modules
  src/specify_cli/cognition/__init__.py
    Purpose: export the new discovery and reference-read helpers from the public cognition API.
  src/specify_cli/cognition/status.py
    Purpose: keep status parsing authoritative and extend it only if lightweight freshness access helpers are needed by reference admission logic.
  src/specify_cli/cognition/store.py
    Purpose: provide existing JSON artifact reads used by the new helper code; extend only if a tiny shared reader helper reduces duplication.

CREATE: shared cross-project cognition helpers
  src/specify_cli/cognition/discovery.py
    Purpose: recursively scan a supplied root, identify nested downstream project candidates by `.specify/`, prune obvious heavyweight directories, and surface lightweight candidate metadata without deep reads.
  src/specify_cli/cognition/reference_read.py
    Purpose: validate explicit project selection, enforce `fresh`-only admission, read the requested slice, optionally read targeted graph artifacts, and preserve provenance in a stable payload.

MODIFY: CLI command surface and rendering
  src/specify_cli/__init__.py
    Purpose: add a `cognition` Typer group, wire `discover` and `read` commands, render human output, and support JSON output without inventing a new workflow surface.

MODIFY: shared freshness and handbook/runtime docs only where cross-project behavior must be explained
  README.md
    Purpose: document the new helper surface and its explicit-only, `fresh`-only, supplemental-only contract.
  PROJECT-HANDBOOK.md
    Purpose: record that cross-project cognition reference is a shared helper surface under the graph-native runtime, not a new workflow and not a project-map regression.
  AGENTS.md
    Purpose: note in the repository maintenance guidance that cross-project cognition reference is a shared runtime helper surface when future workflow or product changes touch it.

MODIFY: workflow templates and passive skill guidance
  templates/commands/explain.md
    Purpose: let `explain` use the helper when the user explicitly requests another downstream project as reference context.
  templates/commands/clarify.md
    Purpose: teach clarification-time external cognition reference as an explicit helper path only.
  templates/commands/deep-research.md
    Purpose: allow deep research to cite external downstream cognition as supplemental evidence when the user explicitly requests it.
  templates/commands/plan.md
    Purpose: teach planning-time reference cognition as explicit supplemental context and preserve current-project truth ownership.
  templates/commands/debug.md
    Purpose: allow debug-time foreign cognition only when explicitly requested and only through the helper gate.
  templates/passive-skills/spec-kit-project-map-gate/SKILL.md
    Purpose: extend the brownfield hard gate wording so it distinguishes current-project mandatory cognition from explicit foreign-project supplemental cognition.

MODIFY: CLI and cognition regression tests
  tests/test_project_cognition_runtime.py
    Purpose: lock the new helper payloads, nested discovery rules, admission rules, and provenance behavior at the runtime layer.
  tests/test_project_map_status.py
    Purpose: ensure the new capability does not redefine freshness semantics and, if needed, lock any shared helper expectations reused by the admission gate.
  tests/integrations/test_cli.py
    Purpose: verify `specify cognition discover` and `specify cognition read` behavior and JSON payload shape through the public CLI.
  tests/test_alignment_templates.py
    Purpose: lock template wording for explicit-only, supplemental-only, `fresh`-only foreign cognition reference and guard against reintroducing project-map exports as the primary source.
  tests/test_project_handbook_templates.py
    Purpose: lock documentation-oriented generated guidance so runtime truth still starts from project cognition and external reference remains helper-scoped.

READ-ONLY: approved design input
  docs/superpowers/specs/2026-05-11-cross-project-project-cognition-reference-design.md
    Purpose: approved product contract; implementation must not drift from its explicit-only, supplemental-only, and `fresh`-only decisions.
```

## Verification Commands

Minimum trustworthy verification for this rollout:

```bash
uv run pytest tests/test_project_cognition_runtime.py tests/test_project_map_status.py -q
uv run pytest tests/integrations/test_cli.py -q -k "cognition"
uv run pytest tests/test_alignment_templates.py tests/test_project_handbook_templates.py -q -k "cognition or project_map"
```

If CLI command registration or prompt coverage broadens:

```bash
uv run pytest tests/integrations -q
```

If cognition runtime helpers or freshness interplay broadens:

```bash
uv run pytest tests/test_project_cognition_runtime.py tests/test_project_map_status.py tests/hooks/test_preflight_hooks.py -q
```

---

### Task 1: Lock discovery, admission, and CLI contracts in failing tests

**Files:**
- Modify: `tests/test_project_cognition_runtime.py`
- Modify: `tests/integrations/test_cli.py`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_project_handbook_templates.py`

- [ ] **Step 1: Add failing runtime tests for nested project discovery**

Add the following tests to `tests/test_project_cognition_runtime.py`:

```python
from pathlib import Path

from specify_cli.cognition.discovery import discover_reference_projects
from specify_cli.cognition.status import CognitionStatus, write_cognition_status
from specify_cli.cognition.store import ensure_cognition_runtime_dirs, write_json_artifact


def _seed_reference_project(project_root: Path, *, freshness: str = "fresh", include_change: bool = True, include_debug: bool = True) -> None:
    ensure_cognition_runtime_dirs(project_root)
    (project_root / ".specify").mkdir(parents=True, exist_ok=True)
    write_cognition_status(
        project_root,
        CognitionStatus(
            version=1,
            baseline_state=freshness,
            graph_ready=(freshness == "fresh"),
        ),
    )
    if include_change:
        write_json_artifact(
            project_root / ".specify" / "project-cognition" / "slices" / "change.json",
            {"slice": {"slice_id": "change"}},
        )
    if include_debug:
        write_json_artifact(
            project_root / ".specify" / "project-cognition" / "slices" / "debug.json",
            {"slice": {"slice_id": "debug"}},
        )


def test_discover_reference_projects_finds_nested_downstream_projects(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    first = workspace / "apps" / "alpha"
    second = workspace / "libs" / "beta" / "demo"
    _seed_reference_project(first)
    _seed_reference_project(second)

    payload = discover_reference_projects(workspace)

    roots = [item["project_root"].replace("\\", "/") for item in payload["projects"]]
    assert first.as_posix() in roots
    assert second.as_posix() in roots
    assert len(payload["projects"]) == 2


def test_discover_reference_projects_reports_candidate_without_cognition_runtime(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    candidate = workspace / "apps" / "gamma"
    (candidate / ".specify").mkdir(parents=True, exist_ok=True)

    payload = discover_reference_projects(workspace)

    assert payload["projects"][0]["has_specify"] is True
    assert payload["projects"][0]["has_cognition"] is False
    assert payload["projects"][0]["freshness"] == "missing"
```

- [ ] **Step 2: Add failing runtime tests for `fresh`-only admission and minimal read order**

Extend `tests/test_project_cognition_runtime.py` with:

```python
from specify_cli.cognition.reference_read import read_reference_project_cognition, ReferenceProjectReadError


def test_read_reference_project_cognition_requires_fresh_status(tmp_path: Path) -> None:
    project_root = tmp_path / "stale-project"
    _seed_reference_project(project_root, freshness="stale")

    try:
        read_reference_project_cognition(project_root, slice_name="change")
    except ReferenceProjectReadError as exc:
        assert exc.code == "reference_not_fresh"
        assert "fresh" in str(exc).lower()
    else:
        raise AssertionError("expected non-fresh reference cognition to be rejected")


def test_read_reference_project_cognition_reads_status_and_requested_slice_only_by_default(tmp_path: Path) -> None:
    project_root = tmp_path / "fresh-project"
    _seed_reference_project(project_root, freshness="fresh")
    write_json_artifact(project_root / ".specify" / "project-cognition" / "graph" / "claims.json", {"claims": []})

    payload = read_reference_project_cognition(project_root, slice_name="change")

    assert payload["admission"]["allowed"] is True
    assert payload["slice"]["path"].replace("\\", "/").endswith("/.specify/project-cognition/slices/change.json")
    assert payload["graph"] == {}
    assert payload["provenance"] == [
        ".specify/project-cognition/status.json",
        ".specify/project-cognition/slices/change.json",
    ]
```

- [ ] **Step 3: Add failing CLI tests for `cognition discover` and `cognition read`**

Extend `tests/integrations/test_cli.py` with:

```python
def test_cognition_discover_lists_nested_candidates_as_json(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    workspace = tmp_path / "workspace"
    alpha = workspace / "apps" / "alpha"
    beta = workspace / "libs" / "beta"
    _seed_reference_project(alpha)
    _seed_reference_project(beta)

    runner = CliRunner()
    result = runner.invoke(app, ["cognition", "discover", "--root", str(workspace), "--format", "json"], catch_exceptions=False)

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    roots = [item["project_root"].replace("\\", "/") for item in payload["projects"]]
    assert alpha.as_posix() in roots
    assert beta.as_posix() in roots


def test_cognition_read_rejects_non_fresh_reference_project(tmp_path):
    from typer.testing import CliRunner
    from specify_cli import app

    project_root = tmp_path / "reference-project"
    _seed_reference_project(project_root, freshness="possibly_stale")

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["cognition", "read", "--project", str(project_root), "--slice", "change", "--format", "json"],
        catch_exceptions=False,
    )

    assert result.exit_code != 0
    assert "non-fresh external project cognition" in result.output.lower() or "fresh" in result.output.lower()
```

- [ ] **Step 4: Add failing template and handbook guidance assertions**

Extend `tests/test_alignment_templates.py` with:

```python
def test_templates_treat_external_cognition_as_explicit_supplemental_and_fresh_only() -> None:
    for relative in (
        "templates/commands/explain.md",
        "templates/commands/clarify.md",
        "templates/commands/deep-research.md",
        "templates/commands/plan.md",
        "templates/commands/debug.md",
        "templates/passive-skills/spec-kit-project-map-gate/SKILL.md",
    ):
        content = _read(relative).lower()
        assert "explicit" in content
        assert "supplemental" in content
        assert "fresh" in content
        assert "project-map" in content
```

Extend `tests/test_project_handbook_templates.py` with:

```python
def test_project_handbook_template_keeps_external_cognition_as_helper_surface() -> None:
    content = _read("templates/project-handbook-template.md").lower()
    assert "project-cognition" in content
    assert "compatibility/export" in content
    assert "external" in content or "reference project" in content
```

- [ ] **Step 5: Run the focused red suite**

Run:

```bash
uv run pytest tests/test_project_cognition_runtime.py tests/integrations/test_cli.py tests/test_alignment_templates.py tests/test_project_handbook_templates.py -q -k "cognition or reference"
```

Expected: FAIL because discovery and reference-read helpers and CLI commands do not exist yet.

- [ ] **Step 6: Commit the red tests**

Run:

```bash
git add tests/test_project_cognition_runtime.py tests/integrations/test_cli.py tests/test_alignment_templates.py tests/test_project_handbook_templates.py
git commit -m "test: lock cross-project cognition reference contract"
```

### Task 2: Build shared cognition discovery and reference-read helpers

**Files:**
- Create: `src/specify_cli/cognition/discovery.py`
- Create: `src/specify_cli/cognition/reference_read.py`
- Modify: `src/specify_cli/cognition/__init__.py`
- Modify: `src/specify_cli/cognition/status.py`
- Modify: `src/specify_cli/cognition/store.py`

- [ ] **Step 1: Implement candidate discovery helpers**

Create `src/specify_cli/cognition/discovery.py` with:

```python
from __future__ import annotations

from pathlib import Path
from typing import Any

from .paths import cognition_dir, cognition_status_path, graph_slices_dir
from .status import read_cognition_status


PRUNED_DIR_NAMES = {
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
}


def _available_slices(project_root: Path) -> list[str]:
    slices_root = graph_slices_dir(project_root)
    if not slices_root.exists():
        return []
    names: list[str] = []
    change_path = slices_root / "change.json"
    debug_path = slices_root / "debug.json"
    if change_path.exists():
        names.append("change")
    if debug_path.exists():
        names.append("debug")
    return names


def _candidate_payload(project_root: Path, *, discovery_root: Path) -> dict[str, Any]:
    has_cognition = cognition_dir(project_root).exists()
    status = read_cognition_status(project_root) if has_cognition else None
    freshness = "missing"
    graph_ready = False
    if status is not None:
        baseline_state = str(status.baseline_state or "").strip().lower()
        freshness = "fresh" if baseline_state == "ready" and status.graph_ready else baseline_state or "missing"
        graph_ready = bool(status.graph_ready)
    return {
        "project_root": project_root.as_posix(),
        "relative_path": project_root.relative_to(discovery_root).as_posix(),
        "has_specify": True,
        "has_cognition": has_cognition,
        "freshness": freshness,
        "graph_ready": graph_ready,
        "available_slices": _available_slices(project_root),
    }


def discover_reference_projects(root: Path) -> dict[str, Any]:
    discovery_root = root.resolve()
    if not discovery_root.exists():
        raise FileNotFoundError(f"discovery root does not exist: {discovery_root}")
    projects: list[dict[str, Any]] = []
    for current, dirnames, _filenames in __import__("os").walk(discovery_root, topdown=True):
        dirnames[:] = [name for name in dirnames if name not in PRUNED_DIR_NAMES]
        current_path = Path(current)
        if (current_path / ".specify").is_dir():
            projects.append(_candidate_payload(current_path, discovery_root=discovery_root))
    projects.sort(key=lambda item: item["relative_path"])
    return {
        "root": discovery_root.as_posix(),
        "projects": projects,
    }
```

- [ ] **Step 2: Implement explicit admission and reference-read helpers**

Create `src/specify_cli/cognition/reference_read.py` with:

```python
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .paths import cognition_status_path, graph_claims_path, graph_conflicts_path, graph_edges_path, graph_nodes_path, graph_slices_dir
from .status import read_cognition_status
from .store import read_json_artifact


GRAPH_PATHS = {
    "nodes": graph_nodes_path,
    "edges": graph_edges_path,
    "claims": graph_claims_path,
    "conflicts": graph_conflicts_path,
}


@dataclass(slots=True)
class ReferenceProjectReadError(RuntimeError):
    code: str
    message: str

    def __str__(self) -> str:
        return self.message


def _admit_reference_project(project_root: Path) -> dict[str, Any]:
    if not (project_root / ".specify").is_dir():
        raise ReferenceProjectReadError("not_downstream_project", f"{project_root} does not contain .specify/")
    status_path = cognition_status_path(project_root)
    if not status_path.exists():
        raise ReferenceProjectReadError("missing_cognition_runtime", f"{project_root} is missing .specify/project-cognition/status.json")
    status = read_cognition_status(project_root)
    freshness = str(status.baseline_state or "").strip().lower()
    is_fresh = freshness == "ready" and bool(status.graph_ready)
    if not is_fresh:
        raise ReferenceProjectReadError(
            "reference_not_fresh",
            f"Non-fresh external project cognition cannot be used as reference context: {project_root}",
        )
    return {
        "allowed": True,
        "reason": "reference project cognition is fresh",
        "freshness": "fresh",
    }


def read_reference_project_cognition(
    project_root: Path,
    *,
    slice_name: str,
    include_graph: list[str] | None = None,
) -> dict[str, Any]:
    resolved_root = project_root.resolve()
    admission = _admit_reference_project(resolved_root)
    slice_path = graph_slices_dir(resolved_root) / f"{slice_name}.json"
    if not slice_path.exists():
        raise ReferenceProjectReadError("missing_slice", f"reference cognition slice is missing: {slice_path}")
    provenance = [
        ".specify/project-cognition/status.json",
        f".specify/project-cognition/slices/{slice_name}.json",
    ]
    graph_payload: dict[str, Any] = {}
    for key in include_graph or []:
        if key not in GRAPH_PATHS:
            raise ReferenceProjectReadError("unsupported_graph_artifact", f"unsupported graph artifact: {key}")
        artifact_path = GRAPH_PATHS[key](resolved_root)
        if not artifact_path.exists():
            raise ReferenceProjectReadError("missing_graph_artifact", f"reference graph artifact is missing: {artifact_path}")
        graph_payload[key] = {
            "path": artifact_path.as_posix(),
            "payload": read_json_artifact(artifact_path),
        }
        provenance.append(f".specify/project-cognition/graph/{artifact_path.name}")
    return {
        "reference_project": resolved_root.as_posix(),
        "admission": admission,
        "status": {
            "path": cognition_status_path(resolved_root).as_posix(),
            "payload": read_json_artifact(cognition_status_path(resolved_root)),
        },
        "slice": {
            "path": slice_path.as_posix(),
            "payload": read_json_artifact(slice_path),
        },
        "graph": graph_payload,
        "provenance": provenance,
    }
```

- [ ] **Step 3: Export the new helpers through the cognition package**

Update `src/specify_cli/cognition/__init__.py` to export:

```python
from .discovery import discover_reference_projects
from .reference_read import ReferenceProjectReadError, read_reference_project_cognition
```

And add them to `__all__`:

```python
    "ReferenceProjectReadError",
    "discover_reference_projects",
    "read_reference_project_cognition",
```

- [ ] **Step 4: Make any tiny shared status/store changes required by the new helpers**

If the new helpers need a small convenience function, keep it tiny and local.
For example, if repeated JSON reads become noisy, add to `src/specify_cli/cognition/store.py`:

```python
def artifact_exists(path: Path) -> bool:
    return path.exists() and path.is_file()
```

Do not broaden `status.py` or `store.py` into a second abstraction layer.
Keep the shared changes minimal.

- [ ] **Step 5: Run the focused runtime suite**

Run:

```bash
uv run pytest tests/test_project_cognition_runtime.py tests/test_project_map_status.py -q
```

Expected: PASS for the new runtime tests without breaking existing project-map freshness behavior.

- [ ] **Step 6: Commit the runtime helper implementation**

Run:

```bash
git add src/specify_cli/cognition/__init__.py src/specify_cli/cognition/discovery.py src/specify_cli/cognition/reference_read.py src/specify_cli/cognition/status.py src/specify_cli/cognition/store.py tests/test_project_cognition_runtime.py tests/test_project_map_status.py
git commit -m "feat: add cross-project cognition reference helpers"
```

### Task 3: Expose the helper through the public CLI

**Files:**
- Modify: `src/specify_cli/__init__.py`
- Modify: `tests/integrations/test_cli.py`

- [ ] **Step 1: Register a new `cognition` Typer group**

In `src/specify_cli/__init__.py`, near the other helper groups, add:

```python
cognition_app = typer.Typer(
    name="cognition",
    help="Discover and read explicit cross-project project cognition reference context",
    add_completion=False,
)
app.add_typer(cognition_app, name="cognition")
```

- [ ] **Step 2: Add a small shared renderer for discover and read payloads**

Add to `src/specify_cli/__init__.py`:

```python
def _render_cognition_discovery(result: dict[str, Any]) -> None:
    rows = [
        ("Root", f"[dim]{result['root']}[/dim]"),
        ("Candidates", str(len(result.get("projects", [])))),
    ]
    console.print(_cli_panel(_labeled_grid(rows), title="Cognition Discovery", border_style="cyan"))
    for item in result.get("projects", []):
        console.print(
            f"- {item['relative_path']} "
            f"(freshness={item['freshness']}, slices={','.join(item.get('available_slices', [])) or 'none'})"
        )


def _render_cognition_reference_read(result: dict[str, Any]) -> None:
    rows = [
        ("Project", f"[dim]{result['reference_project']}[/dim]"),
        ("Admission", f"[cyan]{result['admission']['allowed']}[/cyan]"),
        ("Slice", f"[cyan]{Path(result['slice']['path']).name}[/cyan]"),
    ]
    console.print(_cli_panel(_labeled_grid(rows), title="Cognition Reference", border_style="cyan"))
    console.print("[bold]Provenance[/bold]")
    for path in result.get("provenance", []):
        console.print(f"- {path}")
```

- [ ] **Step 3: Implement `cognition discover`**

Add:

```python
@cognition_app.command("discover")
def cognition_discover_command(
    root: str = typer.Option(..., "--root", help="Root directory to scan for nested downstream projects"),
    format: str = typer.Option("text", "--format", help="Output format: text or json"),
) -> None:
    payload = discover_reference_projects(Path(root))
    if format == "json":
        console.print(json.dumps(payload, ensure_ascii=False))
        return
    _render_cognition_discovery(payload)
```

- [ ] **Step 4: Implement `cognition read` with clear refusal behavior**

Add:

```python
@cognition_app.command("read")
def cognition_read_command(
    project: str = typer.Option(..., "--project", help="Explicit downstream project root to read"),
    slice_name: str = typer.Option(..., "--slice", help="Requested slice: change or debug"),
    include_graph: list[str] | None = typer.Option(None, "--include-graph", help="Optional graph artifacts: nodes, edges, claims, conflicts"),
    format: str = typer.Option("text", "--format", help="Output format: text or json"),
) -> None:
    try:
        payload = read_reference_project_cognition(
            Path(project),
            slice_name=slice_name,
            include_graph=include_graph,
        )
    except ReferenceProjectReadError as exc:
        raise typer.Exit(code=1) from _raise_cli_error(str(exc))
    if format == "json":
        console.print(json.dumps(payload, ensure_ascii=False))
        return
    _render_cognition_reference_read(payload)
```

Add a tiny local helper if needed:

```python
def _raise_cli_error(message: str) -> RuntimeError:
    console.print(f"[red]Error:[/red] {message}")
    return RuntimeError(message)
```

If the repo already has a better CLI error pattern nearby, use that instead of introducing a new one.

- [ ] **Step 5: Make the CLI tests pass**

Run:

```bash
uv run pytest tests/integrations/test_cli.py -q -k "cognition"
```

Expected: PASS for the new command-surface tests.

- [ ] **Step 6: Commit the CLI surface**

Run:

```bash
git add src/specify_cli/__init__.py tests/integrations/test_cli.py
git commit -m "feat: add cognition discovery and read commands"
```

### Task 4: Update templates and docs so workflows use the helper correctly

**Files:**
- Modify: `templates/commands/explain.md`
- Modify: `templates/commands/clarify.md`
- Modify: `templates/commands/deep-research.md`
- Modify: `templates/commands/plan.md`
- Modify: `templates/commands/debug.md`
- Modify: `templates/passive-skills/spec-kit-project-map-gate/SKILL.md`
- Modify: `templates/project-handbook-template.md`
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `AGENTS.md`
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_project_handbook_templates.py`

- [ ] **Step 1: Teach workflow templates the explicit foreign-cognition helper path**

Add wording to each listed workflow template that follows this pattern:

```md
- If the user explicitly requests another `spec-kit-plus` downstream project as reference context, use the `cognition` helper surface to discover candidates and read only the named reference project's project cognition runtime.
- Treat external project cognition as supplemental evidence only; it does not replace the current project's own runtime truth.
- Admit external project cognition only when that reference project's `.specify/project-cognition/status.json` is `fresh`.
- Do not treat `.specify/project-map/*` or handbook exports as the primary cross-project truth source.
```

Keep the wording adapted to each workflow, but preserve all four constraints.

- [ ] **Step 2: Extend the passive brownfield gate with the external-reference rule**

Update `templates/passive-skills/spec-kit-project-map-gate/SKILL.md` with a bounded addendum like:

```md
- When the user explicitly asks to reference a different downstream project, that foreign project is not part of the default hard gate. Load it only through the cross-project cognition helper surface.
- Foreign cognition remains supplemental to the active project's own runtime truth and must be `fresh` before it can be used.
```

- [ ] **Step 3: Document the helper in shared docs**

Update `README.md`, `PROJECT-HANDBOOK.md`, and `AGENTS.md` so they clearly state:

```md
- Cross-project project cognition reference is a shared helper surface, not a new `sp-*` workflow.
- Discovery may be automatic, but deep reads of foreign cognition require explicit user intent.
- Only `fresh` external project cognition is admissible.
- Compatibility/export atlas files remain non-primary for this purpose.
```

Update `templates/project-handbook-template.md` with matching generated-project guidance.

- [ ] **Step 4: Run the focused doc and template suite**

Run:

```bash
uv run pytest tests/test_alignment_templates.py tests/test_project_handbook_templates.py -q -k "cognition or project_map"
```

Expected: PASS with the new wording locked.

- [ ] **Step 5: Commit the guidance updates**

Run:

```bash
git add templates/commands/explain.md templates/commands/clarify.md templates/commands/deep-research.md templates/commands/plan.md templates/commands/debug.md templates/passive-skills/spec-kit-project-map-gate/SKILL.md templates/project-handbook-template.md README.md PROJECT-HANDBOOK.md AGENTS.md tests/test_alignment_templates.py tests/test_project_handbook_templates.py
git commit -m "docs: teach explicit cross-project cognition reference"
```

### Task 5: Run full focused verification and record final handoff notes

**Files:**
- Modify: `docs/superpowers/plans/2026-05-11-cross-project-project-cognition-reference-implementation.md`

- [ ] **Step 1: Run the combined verification set**

Run:

```bash
uv run pytest tests/test_project_cognition_runtime.py tests/test_project_map_status.py tests/integrations/test_cli.py tests/test_alignment_templates.py tests/test_project_handbook_templates.py -q
```

Expected: PASS.

- [ ] **Step 2: Run a broader integration safety check if command registration touched adjacent surfaces**

Run:

```bash
uv run pytest tests/integrations -q
```

Expected: PASS, or if too expensive in the current environment, record exactly which focused suite was run and why the broader suite was skipped.

- [ ] **Step 3: Update this plan with implementation notes if execution revealed any bounded deviations**

Append a short completion note at the bottom of this plan only if needed:

```md
## Implementation Notes

- [date] Adjusted helper payload key names from `summary` to `repository` to match actual status metadata.
- [date] Kept AGENTS-level doc update brief to avoid duplicating handbook wording.
```

If there were no deviations, do not add this section.

- [ ] **Step 4: Commit any final verification-only adjustments**

Run:

```bash
git add docs/superpowers/plans/2026-05-11-cross-project-project-cognition-reference-implementation.md
git commit -m "chore: finalize cross-project cognition reference verification"
```

## Self-Review

Spec coverage:

- discovery by locating `.specify/` is covered in Task 1 and Task 2
- nested-project support is covered in Task 1 and Task 2
- explicit-only deep read is covered in Task 3 and Task 4
- `fresh`-only admission is covered in Task 1 and Task 2
- minimal read order (`status.json`, requested slice, optional graph) is covered in Task 1 and Task 2
- CLI helper surface instead of new workflow is covered in Task 3 and Task 4
- prompt and doc updates are covered in Task 4
- regression proof is covered in Task 5

Placeholder scan:

- no `TODO`, `TBD`, or generic "add tests" placeholders remain
- each task names exact files and exact commands
- code-bearing steps include concrete code

Type consistency:

- helper names are consistent across tasks: `discover_reference_projects`, `read_reference_project_cognition`, `ReferenceProjectReadError`
- CLI group name is consistently `cognition`
- admission terms are consistent: explicit-only, supplemental-only, `fresh`-only

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-11-cross-project-project-cognition-reference-implementation.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
