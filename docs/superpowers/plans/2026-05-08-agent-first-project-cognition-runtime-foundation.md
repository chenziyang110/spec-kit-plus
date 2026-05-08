# Agent-First Project Cognition Runtime Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current handbook-first `map-scan/map-build` runtime contract with the first working graph-native cognition runtime foundation, including a new `map-update` command surface and graph-first validation/gating primitives.

**Architecture:** Implement this as a foundation slice rather than the full end-state in one jump. First, lock the new command and artifact contracts in tests so the legacy handbook-first surface starts failing for the right reasons. Second, add a new project cognition runtime storage layer for evidence, graph nodes, edges, claims, conflicts, slices, and update events. Third, rewire `map-scan`, `map-build`, freshness/gating, integration guidance, and artifact validation to use the graph-native runtime as the primary truth surface while leaving deeper brownfield workflow adoption for later plans.

**Tech Stack:** Python, Typer, Markdown skill templates, JSON graph artifacts, pytest

---

## Scope Check

The approved spec describes multiple independent but related subsystems:

- graph-native storage and schemas
- `map-scan` command redesign
- `map-build` command redesign
- new `map-update` command
- graph-first workflow consumption
- eval and quality harnesses

This plan intentionally covers only the first independently useful implementation slice:

- graph runtime storage contract
- `map-scan` / `map-build` / `map-update` command and template contract rewrite
- artifact validation rewrite
- project-map freshness and command guidance rewrite
- initial integration-layer updates
- regression tests for the new runtime foundation

It does **not** fully implement downstream `sp-specify`, `sp-plan`, `sp-tasks`, `sp-implement`, and `sp-debug` graph-slice execution. That should follow in a separate plan once the runtime foundation is real and testable.

## File Structure

### New runtime storage and schema layer

- Create: `src/specify_cli/cognition/__init__.py`
  - Public exports for graph runtime helpers and schema objects.
- Create: `src/specify_cli/cognition/paths.py`
  - Canonical file and directory layout for cognition runtime artifacts under `.specify/project-cognition/`.
- Create: `src/specify_cli/cognition/schema.py`
  - Typed dataclasses for evidence, observations, nodes, edges, claims, conflicts, update events, and slices.
- Create: `src/specify_cli/cognition/store.py`
  - Read/write helpers for graph-native JSON artifacts.
- Create: `src/specify_cli/cognition/status.py`
  - Runtime baseline status helpers replacing handbook-first freshness assumptions.
- Create: `src/specify_cli/cognition/diff.py`
  - Diff-impact helper primitives for `map-update`.

### Command and runtime CLI surfaces

- Modify: `src/specify_cli/__init__.py`
  - Replace old `map-scan/map-build` descriptions, add `map-update`, and switch `project-map` helpers to cognition-runtime-aware messaging.
- Modify: `src/specify_cli/project_map_status.py`
  - Bridge existing project-map freshness logic to the new cognition runtime baseline and graph artifact presence rules.

### Validation and execution contracts

- Modify: `src/specify_cli/hooks/artifact_validation.py`
  - Replace handbook-required artifacts with graph-runtime-required artifacts and add validation for cognition graph stores and slices.
- Modify: `src/specify_cli/execution/packet_compiler.py`
  - Stop bundling `BUILD-HANDBOOK.md` / `DEBUG-HANDBOOK.md` as the primary context payload for future graph-aware packet compilation.

### Skill and integration surfaces

- Modify: `templates/commands/map-scan.md`
  - Rewrite around full evidence acquisition and provisional graph construction.
- Modify: `templates/commands/map-build.md`
  - Rewrite around graph reconstruction, claim synthesis, conflict creation, and slice publishing.
- Create: `templates/commands/map-update.md`
  - New incremental maintenance workflow contract.
- Modify: `src/specify_cli/integrations/base.py`
  - Replace handbook-first hard gates with cognition-runtime-first hard gates.
- Modify: `src/specify_cli/integrations/codex/__init__.py`
  - Update Codex-specific guidance for the rewritten commands and new `sp-map-update`.

### Tests

- Create: `tests/test_project_cognition_runtime.py`
  - Runtime path and storage contract tests.
- Create: `tests/test_map_runtime_template_guidance.py`
  - Template contract tests for `map-scan`, `map-build`, and `map-update`.
- Modify: `tests/test_runtime_handbook_contract.py`
  - Replace handbook-first assumptions with cognition-runtime contract assertions.
- Modify: `tests/test_project_map_status.py`
  - Update freshness expectations around the new baseline artifacts.
- Modify: `tests/test_alignment_templates.py`
  - Replace command-text expectations for the map workflows.
- Modify: `tests/contract/test_hook_cli_surface.py`
  - Rebuild artifact validation tests for graph-native map artifacts.
- Modify: `tests/integrations/test_cli.py`
  - Add `map-update` CLI coverage and update generated-asset assertions.
- Modify: `tests/integrations/test_integration_codex.py`
  - Ensure Codex skills include `sp-map-update` and new graph-native guidance.
- Modify: `tests/integrations/test_integration_base_markdown.py`
  - Update generated command assertions.
- Modify: `tests/integrations/test_integration_base_toml.py`
  - Update generated command assertions.
- Modify: `tests/integrations/test_integration_base_skills.py`
  - Update generated skill assertions.

## Task 1: Lock the graph-native cognition runtime contract in tests

**Files:**
- Create: `tests/test_project_cognition_runtime.py`
- Create: `tests/test_map_runtime_template_guidance.py`
- Modify: `tests/test_runtime_handbook_contract.py`
- Modify: `tests/test_alignment_templates.py`

- [ ] **Step 1: Add a dedicated runtime path contract test**

Create `tests/test_project_cognition_runtime.py` with failing tests like:

```python
from pathlib import Path

from specify_cli.cognition.paths import (
    cognition_dir,
    cognition_status_path,
    graph_nodes_path,
    graph_edges_path,
    graph_claims_path,
    graph_conflicts_path,
    graph_slices_dir,
)


def test_cognition_runtime_paths_live_under_project_cognition(tmp_path: Path) -> None:
    assert cognition_dir(tmp_path) == tmp_path / ".specify" / "project-cognition"
    assert cognition_status_path(tmp_path) == tmp_path / ".specify" / "project-cognition" / "status.json"
    assert graph_nodes_path(tmp_path) == tmp_path / ".specify" / "project-cognition" / "graph" / "nodes.json"
    assert graph_edges_path(tmp_path) == tmp_path / ".specify" / "project-cognition" / "graph" / "edges.json"
    assert graph_claims_path(tmp_path) == tmp_path / ".specify" / "project-cognition" / "graph" / "claims.json"
    assert graph_conflicts_path(tmp_path) == tmp_path / ".specify" / "project-cognition" / "graph" / "conflicts.json"
    assert graph_slices_dir(tmp_path) == tmp_path / ".specify" / "project-cognition" / "slices"
```

- [ ] **Step 2: Add template-guidance tests for the new command contract**

Create `tests/test_map_runtime_template_guidance.py` with assertions like:

```python
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_map_scan_template_targets_graph_native_runtime():
    content = _read("templates/commands/map-scan.md")
    assert ".specify/project-cognition/" in content
    assert "evidence" in content.lower()
    assert "provisional nodes" in content.lower()
    assert "candidate edges" in content.lower()
    assert "must not publish final cognition truth" in content.lower()


def test_map_build_template_targets_graph_reconstruction():
    content = _read("templates/commands/map-build.md")
    assert ".specify/project-cognition/graph/nodes.json" in content
    assert ".specify/project-cognition/graph/claims.json" in content
    assert ".specify/project-cognition/slices/" in content
    assert "conflict" in content.lower()
    assert "claim" in content.lower()


def test_map_update_template_exists_and_is_incremental():
    content = _read("templates/commands/map-update.md")
    assert "map-update" in content
    assert "diff" in content.lower()
    assert "user supplement" in content.lower()
    assert "incremental" in content.lower()
```

- [ ] **Step 3: Convert runtime-handbook contract tests into cognition-runtime contract tests**

Replace the old expectations in `tests/test_runtime_handbook_contract.py` with assertions like:

```python
assert ".specify/project-cognition/status.json" in content
assert ".specify/project-cognition/graph/nodes.json" in content
assert ".specify/project-cognition/graph/edges.json" in content
assert ".specify/project-cognition/graph/claims.json" in content
assert ".specify/project-cognition/graph/conflicts.json" in content
```

and remove assertions that require `DEBUG-HANDBOOK.md` or `BUILD-HANDBOOK.md` as the canonical runtime output.

- [ ] **Step 4: Rewrite alignment-template expectations for the new lifecycle**

Update `tests/test_alignment_templates.py` so map workflow assertions require:

```python
assert "map-update" in content
assert "graph-native" in content.lower()
assert "project-cognition" in content
assert 'choose_subagent_dispatch(command_name="map-scan"' in content
assert 'choose_subagent_dispatch(command_name="map-build"' in content
```

and remove legacy expectations around refreshing `DEBUG-HANDBOOK.md` and `BUILD-HANDBOOK.md`.

- [ ] **Step 5: Run the new contract test subset and confirm red**

Run:

```powershell
pytest tests/test_project_cognition_runtime.py `
  tests/test_map_runtime_template_guidance.py `
  tests/test_runtime_handbook_contract.py `
  tests/test_alignment_templates.py -q
```

Expected: failures because the cognition runtime module and the new map command contracts do not exist yet.

- [ ] **Step 6: Commit the red contract**

```bash
git add tests/test_project_cognition_runtime.py tests/test_map_runtime_template_guidance.py tests/test_runtime_handbook_contract.py tests/test_alignment_templates.py
git commit -m "test: lock graph-native cognition runtime contract"
```

## Task 2: Add the graph-native cognition runtime storage foundation

**Files:**
- Create: `src/specify_cli/cognition/__init__.py`
- Create: `src/specify_cli/cognition/paths.py`
- Create: `src/specify_cli/cognition/schema.py`
- Create: `src/specify_cli/cognition/store.py`
- Create: `src/specify_cli/cognition/status.py`
- Create: `src/specify_cli/cognition/diff.py`
- Modify: `tests/test_project_cognition_runtime.py`

- [ ] **Step 1: Define the runtime path helpers**

Create `src/specify_cli/cognition/paths.py` with concrete helpers like:

```python
from pathlib import Path


def cognition_dir(project_root: Path) -> Path:
    return project_root / ".specify" / "project-cognition"


def cognition_status_path(project_root: Path) -> Path:
    return cognition_dir(project_root) / "status.json"


def graph_dir(project_root: Path) -> Path:
    return cognition_dir(project_root) / "graph"


def graph_nodes_path(project_root: Path) -> Path:
    return graph_dir(project_root) / "nodes.json"


def graph_edges_path(project_root: Path) -> Path:
    return graph_dir(project_root) / "edges.json"


def graph_claims_path(project_root: Path) -> Path:
    return graph_dir(project_root) / "claims.json"


def graph_conflicts_path(project_root: Path) -> Path:
    return graph_dir(project_root) / "conflicts.json"


def graph_updates_path(project_root: Path) -> Path:
    return graph_dir(project_root) / "updates.json"


def evidence_dir(project_root: Path) -> Path:
    return cognition_dir(project_root) / "evidence"


def graph_slices_dir(project_root: Path) -> Path:
    return cognition_dir(project_root) / "slices"
```

- [ ] **Step 2: Add minimal typed schema objects**

Create `src/specify_cli/cognition/schema.py` with dataclasses for:

```python
@dataclass(slots=True)
class EvidenceRecord:
    evidence_id: str
    source_kind: str
    source_path: str
    commit_sha: str = ""
    commit_range: str = ""
    span: str = ""
    extractor: str = ""
    captured_at: str = ""
    content_hash: str = ""
    project_internal: bool = True


@dataclass(slots=True)
class GraphNode:
    node_id: str
    node_type: str
    title: str
    backing_evidence_ids: list[str] = field(default_factory=list)
    attributes: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class GraphEdge:
    edge_id: str
    edge_type: str
    source_node_id: str
    target_node_id: str
    backing_evidence_ids: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ClaimRecord:
    claim_id: str
    subject_ref: str
    predicate: str
    object_value: str = ""
    object_ref: str = ""
    truth_layer: str = "inferred_synthesis"
    confidence: str = "weak"
    backing_evidence_ids: list[str] = field(default_factory=list)
    falsification_reads: list[str] = field(default_factory=list)
```

Also define `ConflictRecord`, `UpdateEventRecord`, and `SliceRecord`.

- [ ] **Step 3: Add JSON store helpers**

Create `src/specify_cli/cognition/store.py` with functions like:

```python
def ensure_cognition_runtime_dirs(project_root: Path) -> None: ...
def write_json_artifact(path: Path, payload: dict[str, object]) -> Path: ...
def read_json_artifact(path: Path) -> dict[str, object]: ...
def write_graph_nodes(project_root: Path, nodes: list[GraphNode]) -> Path: ...
def write_graph_edges(project_root: Path, edges: list[GraphEdge]) -> Path: ...
def write_graph_claims(project_root: Path, claims: list[ClaimRecord]) -> Path: ...
def write_graph_conflicts(project_root: Path, conflicts: list[ConflictRecord]) -> Path: ...
```

Use `asdict()` and UTF-8 JSON output with `indent=2`.

- [ ] **Step 4: Add status and diff primitives**

Create `src/specify_cli/cognition/status.py` with a minimal `CognitionStatus` dataclass:

```python
@dataclass(slots=True)
class CognitionStatus:
    version: int = 1
    baseline_state: str = "missing"
    baseline_commit: str = ""
    baseline_branch: str = ""
    baseline_built_at: str = ""
    last_update_id: str = ""
    graph_ready: bool = False
    stale_paths: list[str] = field(default_factory=list)
    stale_reasons: list[str] = field(default_factory=list)
```

Create `src/specify_cli/cognition/diff.py` with stubs that compile and return deterministic shapes:

```python
def build_diff_impact_payload(*, changed_paths: list[str]) -> dict[str, object]:
    return {
        "changed_paths": changed_paths,
        "affected_nodes": [],
        "affected_claims": [],
        "requires_full_rescan": False,
    }
```

- [ ] **Step 5: Export the public API**

Create `src/specify_cli/cognition/__init__.py` exporting the path helpers, schema objects, status object, and store helpers that the rest of the code will import.

- [ ] **Step 6: Run the runtime-path and schema tests and make them green**

Run:

```powershell
pytest tests/test_project_cognition_runtime.py -q
```

Expected: the new cognition runtime contract tests pass.

- [ ] **Step 7: Commit the runtime foundation**

```bash
git add src/specify_cli/cognition tests/test_project_cognition_runtime.py
git commit -m "feat: add project cognition runtime foundation"
```

## Task 3: Rewrite map command templates and CLI descriptions for the new runtime

**Files:**
- Modify: `templates/commands/map-scan.md`
- Modify: `templates/commands/map-build.md`
- Create: `templates/commands/map-update.md`
- Modify: `src/specify_cli/__init__.py`
- Modify: `tests/test_map_runtime_template_guidance.py`
- Modify: `tests/test_alignment_templates.py`

- [ ] **Step 1: Rewrite `map-scan` around evidence acquisition**

Replace the frontmatter and body in `templates/commands/map-scan.md` so the primary outputs become graph-runtime scan artifacts such as:

```yaml
primary_outputs: '`.specify/project-cognition/evidence/`, `.specify/project-cognition/provisional/nodes.json`, `.specify/project-cognition/provisional/edges.json`, `.specify/project-cognition/provisional/observations.json`, `.specify/project-cognition/coverage.json`, and `.specify/project-cognition/status.json`.'
```

and use command language like:

```markdown
- `sp-map-scan` must not publish final cognition truth.
- `sp-map-scan` must enumerate all project-relevant in-repo evidence.
- `sp-map-scan` must produce provisional nodes, candidate edges, uncertainty, and coverage diagnostics.
```

- [ ] **Step 2: Rewrite `map-build` around graph reconstruction**

Replace the current handbook-first output contract in `templates/commands/map-build.md` with graph-native outputs like:

```markdown
The only canonical runtime outputs for this command are:

- `.specify/project-cognition/graph/nodes.json`
- `.specify/project-cognition/graph/edges.json`
- `.specify/project-cognition/graph/claims.json`
- `.specify/project-cognition/graph/conflicts.json`
- `.specify/project-cognition/graph/updates.json`
- `.specify/project-cognition/slices/change.json`
- `.specify/project-cognition/slices/debug.json`
- `.specify/project-cognition/slices/capabilities/`
- `.specify/project-cognition/status.json`
```

Also add explicit requirements for `truth_layer`, `confidence`, and `conflict` synthesis.

- [ ] **Step 3: Add the new `map-update` command template**

Create `templates/commands/map-update.md` with frontmatter like:

```yaml
description: Use when a project cognition baseline already exists and you need to apply diff-based evidence refresh or user-supplied operational corrections without rebuilding from scratch.
workflow_contract:
  when_to_use: A graph-native cognition baseline exists and repository changes or user supplements must be merged into it.
  primary_objective: Compute impact closure, refresh affected evidence, update claims/conflicts, and rebuild only affected graph slices.
  primary_outputs: '`.specify/project-cognition/graph/updates.json`, refreshed graph artifacts, refreshed slices, and updated `.specify/project-cognition/status.json`.'
  default_handoff: Return to the blocked brownfield workflow once the affected slices are green or yellow.
```

and body rules like:

```markdown
- `sp-map-update` is the normal maintenance entrypoint after baseline build.
- It must accept both diff-driven and user-supplement-driven updates.
- It must not silently escalate to full rescan without recording why.
```

- [ ] **Step 4: Update CLI descriptions and help text**

In `src/specify_cli/__init__.py`, replace:

```python
"map-scan": "Use when runtime handbook/project-map coverage is missing, stale, or insufficient ..."
"map-build": "Use when map-scan has produced complete coverage ledgers ..."
```

with graph-native descriptions and add:

```python
"map-update": "Use when a graph-native project cognition baseline exists and diff-based evidence refresh or user-supplied corrections must update the cognition runtime incrementally."
```

Also update the onboarding/help text around `map-scan -> map-build` versus `map-update`.

- [ ] **Step 5: Run the template and CLI guidance subset**

Run:

```powershell
pytest tests/test_map_runtime_template_guidance.py `
  tests/test_alignment_templates.py `
  tests/integrations/test_cli.py -q
```

Expected: new map command contract tests and CLI description checks pass.

- [ ] **Step 6: Commit the command-contract rewrite**

```bash
git add templates/commands/map-scan.md templates/commands/map-build.md templates/commands/map-update.md src/specify_cli/__init__.py tests/test_map_runtime_template_guidance.py tests/test_alignment_templates.py tests/integrations/test_cli.py
git commit -m "feat: rewrite map commands for graph-native cognition runtime"
```

## Task 4: Replace handbook-first artifact validation with cognition-runtime validation

**Files:**
- Modify: `src/specify_cli/hooks/artifact_validation.py`
- Modify: `tests/contract/test_hook_cli_surface.py`

- [ ] **Step 1: Replace map workflow required artifact sets**

Change the `FILE_REQUIRED_ARTIFACTS`, `DIRECTORY_REQUIRED_ARTIFACTS`, and `REQUIRED_ARTIFACTS` entries so:

```python
"map-scan": (
    "status.json",
    "coverage.json",
    "provisional/nodes.json",
    "provisional/edges.json",
    "provisional/observations.json",
)
```

under the `.specify/project-cognition/` feature dir model, and:

```python
"map-build": (
    "status.json",
    "graph/nodes.json",
    "graph/edges.json",
    "graph/claims.json",
    "graph/conflicts.json",
    "graph/updates.json",
    "slices",
)
```

Add a new `map-update` entry requiring graph runtime artifacts plus updated slices.

- [ ] **Step 2: Remove handbook-section validation and add graph-shape validation**

Delete the map-build-specific runtime-handbook section checks and replace them with validation helpers like:

```python
def _validate_graph_nodes(feature_dir: Path) -> list[str]: ...
def _validate_graph_edges(feature_dir: Path) -> list[str]: ...
def _validate_graph_claims(feature_dir: Path) -> list[str]: ...
def _validate_graph_conflicts(feature_dir: Path) -> list[str]: ...
def _validate_graph_slices(feature_dir: Path) -> list[str]: ...
```

Each should at minimum confirm that the JSON is an object with the expected top-level array, for example:

```python
if not isinstance(payload.get("nodes"), list):
    return ["graph/nodes.json must define a top-level nodes array"]
```

- [ ] **Step 3: Add `map-update` artifact validation**

In `validate_artifacts_hook()`, add:

```python
if command_name == "map-update":
    validation_errors.extend(_validate_map_update_artifacts(feature_dir))
```

where `_validate_map_update_artifacts()` checks for:

- graph runtime existence
- updates log existence
- slices directory existence
- non-empty changed scope metadata in status or updates payload

- [ ] **Step 4: Rewrite the hook CLI surface tests**

Update `tests/contract/test_hook_cli_surface.py` so failing fixtures look like:

```python
{
    "status.json": "{\"version\": 1, \"graph_ready\": false}\n",
    "coverage.json": "{\"version\": 1, \"rows\": []}\n",
    "provisional/nodes.json": "{\"nodes\": []}\n",
}
```

and success/failure assertions check for messages like:

```python
assert any("graph/nodes.json" in message for message in payload["errors"])
assert any("graph/conflicts.json" in message for message in payload["errors"])
assert any("slices" in message for message in payload["errors"])
```

- [ ] **Step 5: Run hook validation tests and make them green**

Run:

```powershell
pytest tests/contract/test_hook_cli_surface.py -q
```

Expected: the graph-native validation path passes and legacy handbook-specific assertions are gone.

- [ ] **Step 6: Commit the validation rewrite**

```bash
git add src/specify_cli/hooks/artifact_validation.py tests/contract/test_hook_cli_surface.py
git commit -m "feat: validate graph-native cognition runtime artifacts"
```

## Task 5: Rewire freshness, gating, and packet compilation to the cognition runtime baseline

**Files:**
- Modify: `src/specify_cli/project_map_status.py`
- Modify: `src/specify_cli/execution/packet_compiler.py`
- Modify: `tests/test_project_map_status.py`
- Modify: `tests/hooks/test_preflight_hooks.py`
- Modify: `tests/hooks/test_delegation_hooks.py`

- [ ] **Step 1: Add cognition-runtime canonical path helpers**

In `src/specify_cli/project_map_status.py`, add helper functions such as:

```python
def canonical_cognition_runtime_paths(project_root: Path) -> list[Path]:
    return [
        cognition_status_path(project_root),
        graph_nodes_path(project_root),
        graph_edges_path(project_root),
        graph_claims_path(project_root),
        graph_conflicts_path(project_root),
        graph_slices_dir(project_root),
    ]
```

and switch `canonical_project_map_paths()` / `atlas_minimum_read_set()` to use the cognition runtime baseline instead of the two handbook files.

- [ ] **Step 2: Replace handbook-first freshness messaging**

Rewrite user-facing error text in `src/specify_cli/project_map_status.py` and any call sites so messages say:

```text
Run /sp-map-scan, then /sp-map-build to create the initial cognition baseline.
After that, use /sp-map-update when the graph runtime is stale or too weak for the touched area.
```

Remove wording that treats `DEBUG-HANDBOOK.md` and `BUILD-HANDBOOK.md` as the runtime truth.

- [ ] **Step 3: Stop packet compilation from assuming handbook context**

In `src/specify_cli/execution/packet_compiler.py`, replace the current project-doc bundle entries that inject:

```python
"DEBUG-HANDBOOK.md"
"BUILD-HANDBOOK.md"
```

with cognition-runtime entries like:

```python
(".specify/project-cognition/status.json", "project_cognition_status", ...)
(".specify/project-cognition/slices/change.json", "project_cognition_slice", ...)
(".specify/project-cognition/slices/debug.json", "project_cognition_slice", ...)
```

Use neutral `kind` labels that compile with the existing dataclass if needed, such as `task_reference`, until packet schema expansion happens in a later plan.

- [ ] **Step 4: Rewrite status and hook tests**

Update `tests/test_project_map_status.py`, `tests/hooks/test_preflight_hooks.py`, and `tests/hooks/test_delegation_hooks.py` so fixture read scopes reference the cognition baseline, for example:

```python
read_scope=[".specify/project-cognition/status.json"]
```

and expected messages reference the cognition runtime baseline rather than handbook refresh.

- [ ] **Step 5: Run the status and hook subset**

Run:

```powershell
pytest tests/test_project_map_status.py `
  tests/hooks/test_preflight_hooks.py `
  tests/hooks/test_delegation_hooks.py -q
```

Expected: freshness, packet, and hook tests pass against the graph-native baseline assumptions.

- [ ] **Step 6: Commit the gating rewrite**

```bash
git add src/specify_cli/project_map_status.py src/specify_cli/execution/packet_compiler.py tests/test_project_map_status.py tests/hooks/test_preflight_hooks.py tests/hooks/test_delegation_hooks.py
git commit -m "feat: make brownfield gating cognition-runtime first"
```

## Task 6: Update integration guidance and generated skill surfaces for `map-update`

**Files:**
- Modify: `src/specify_cli/integrations/base.py`
- Modify: `src/specify_cli/integrations/codex/__init__.py`
- Modify: `tests/integrations/test_integration_codex.py`
- Modify: `tests/integrations/test_integration_base_markdown.py`
- Modify: `tests/integrations/test_integration_base_toml.py`
- Modify: `tests/integrations/test_integration_base_skills.py`

- [ ] **Step 1: Replace handbook-first hard-gate text in the shared integration base**

In `src/specify_cli/integrations/base.py`, replace guidance like:

```python
"You MUST pass the runtime handbook contract first by reading `BUILD-HANDBOOK.md`..."
```

with graph-first text such as:

```python
"You MUST pass the project cognition contract first by reading the required `.specify/project-cognition/` status and slice artifacts for this workflow before repository analysis or implementation."
```

Also update the stale routing instruction to mention `map-update` after baseline creation.

- [ ] **Step 2: Add Codex augmentation support for `sp-map-update`**

In `src/specify_cli/integrations/codex/__init__.py`, add a new `_augment_shared_skill()` call targeting:

```python
skills_dir / "sp-map-update" / "SKILL.md"
```

with injected text like:

```python
f"When running `sp-map-update` in {agent_name}, use the subagents-first dispatch model.\n"
"- Suggested bounded update lanes include diff impact closure, affected claim refresh, user supplement normalization, and conflict reconciliation.\n"
"- Use `wait_agent` only at the documented join points before updating graph claims, conflicts, and slices.\n"
```

- [ ] **Step 3: Rewrite generated integration assertions**

Update integration tests so they assert:

```python
assert "map-update" in content
assert ".specify/project-cognition/" in content
assert "graph" in content.lower()
assert "slice" in content.lower()
```

and remove checks that require refreshing `DEBUG-HANDBOOK.md` / `BUILD-HANDBOOK.md`.

- [ ] **Step 4: Run the integration guidance subset**

Run:

```powershell
pytest tests/integrations/test_integration_codex.py `
  tests/integrations/test_integration_base_markdown.py `
  tests/integrations/test_integration_base_toml.py `
  tests/integrations/test_integration_base_skills.py -q
```

Expected: generated integration guidance is graph-native and includes `map-update`.

- [ ] **Step 5: Commit the integration-surface rewrite**

```bash
git add src/specify_cli/integrations/base.py src/specify_cli/integrations/codex/__init__.py tests/integrations/test_integration_codex.py tests/integrations/test_integration_base_markdown.py tests/integrations/test_integration_base_toml.py tests/integrations/test_integration_base_skills.py
git commit -m "feat: align integration guidance with cognition runtime"
```

## Task 7: Run the focused foundation verification sweep

**Files:**
- No new files in this task

- [ ] **Step 1: Run the focused graph-runtime regression suite**

Run:

```powershell
pytest tests/test_project_cognition_runtime.py `
  tests/test_map_runtime_template_guidance.py `
  tests/test_runtime_handbook_contract.py `
  tests/test_alignment_templates.py `
  tests/test_project_map_status.py `
  tests/hooks/test_preflight_hooks.py `
  tests/hooks/test_delegation_hooks.py `
  tests/contract/test_hook_cli_surface.py `
  tests/integrations/test_cli.py `
  tests/integrations/test_integration_codex.py `
  tests/integrations/test_integration_base_markdown.py `
  tests/integrations/test_integration_base_toml.py `
  tests/integrations/test_integration_base_skills.py -q
```

Expected:

- the graph-native runtime foundation contract passes
- map command guidance is rewritten
- artifact validation is graph-native
- integration surfaces mention `map-update`

- [ ] **Step 2: Run a narrow CLI smoke check**

Run:

```powershell
python -m specify_cli --help
python -m specify_cli map-scan --help
python -m specify_cli map-build --help
python -m specify_cli map-update --help
python -m specify_cli project-map status --help
```

Expected:

- all command help renders
- `map-update` is present
- no import crash from the new cognition runtime module

- [ ] **Step 3: Commit the verification sweep**

```bash
git add -A
git commit -m "test: verify cognition runtime foundation rollout"
```

## Spec Coverage Check

- Graph-first runtime instead of handbook-first runtime: covered by Tasks 1 through 4.
- New evidence/graph/claim/conflict/update storage layer: covered by Task 2.
- Rewritten `map-scan` and `map-build` command contracts: covered by Task 3.
- New `map-update` lifecycle entrypoint: covered by Tasks 3 and 6.
- Graph-first gating and baseline freshness: covered by Task 5.
- Agent-first integration guidance and generated surfaces: covered by Task 6.
- Foundation-level verification gates: covered by Task 7.

## Placeholder Scan

- No `TODO`, `TBD`, or "implement later" placeholders remain.
- Every task names exact files and exact commands.
- Code steps include concrete snippets instead of abstract prose.

## Type and Naming Consistency Check

- Canonical baseline root: `.specify/project-cognition/`
- Canonical graph directory: `.specify/project-cognition/graph/`
- Canonical daily maintenance command: `map-update`
- Canonical truth artifacts in this phase: `nodes.json`, `edges.json`, `claims.json`, `conflicts.json`, `updates.json`, `status.json`, and `slices/`
- Legacy `DEBUG-HANDBOOK.md` / `BUILD-HANDBOOK.md` assumptions are intentionally removed from the runtime foundation path in this plan
