# Layered Project-Map Atlas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the current handbook plus flat project-map into a layered atlas with machine-readable index files, module-level documentation, module-aware freshness state, and an agent read contract that supports partial refresh and module-directed lookup.

**Architecture:** Implement the change in five slices. First, lock the new contract in tests. Second, extend the Python freshness/status model and canonical path model to support `index/`, `root/`, and `modules/`. Third, update `map-codebase` and passive gate contracts so agents use the new index and module read order. Fourth, add root/module/deep templates. Fifth, pilot the closed loop on one real repository module before broadening generated-surface assertions.

**Tech Stack:** Python, Typer, JSON status/index contracts, Markdown templates, pytest

---

## File Structure

### Core Python state and CLI surfaces

- Modify: `src/specify_cli/project_map_status.py`
  - Add layered atlas path helpers, new status schema, module freshness helpers, and partial-refresh fallout logic.
- Modify: `src/specify_cli/__init__.py`
  - Update user-facing `project-map` command help/output to mention layered state and module scope.
- Modify: `src/specify_cli/hooks/project_map.py`
  - Keep hook surfaces aligned with the new status payload.

### Shared templates and workflow contracts

- Modify: `templates/project-handbook-template.md`
  - Route humans and agents into `index/`, `root/`, and `modules/`.
- Create: `templates/project-map/index/atlas-config.json`
- Create: `templates/project-map/index/atlas-index.json`
- Create: `templates/project-map/index/modules.json`
- Create: `templates/project-map/index/relations.json`
- Create: `templates/project-map/root/ARCHITECTURE.md`
- Create: `templates/project-map/root/STRUCTURE.md`
- Create: `templates/project-map/root/CONVENTIONS.md`
- Create: `templates/project-map/root/INTEGRATIONS.md`
- Create: `templates/project-map/root/WORKFLOWS.md`
- Create: `templates/project-map/root/TESTING.md`
- Create: `templates/project-map/root/OPERATIONS.md`
- Create: `templates/project-map/modules/OVERVIEW.md`
- Create: `templates/project-map/modules/ARCHITECTURE.md`
- Create: `templates/project-map/modules/STRUCTURE.md`
- Create: `templates/project-map/modules/WORKFLOWS.md`
- Create: `templates/project-map/modules/TESTING.md`
- Create: `templates/project-map/modules/deep/capabilities/TEMPLATE.md`
- Create: `templates/project-map/modules/deep/workflows/TEMPLATE.md`
- Create: `templates/project-map/modules/deep/integrations/TEMPLATE.md`
- Create: `templates/project-map/modules/deep/runtime/TEMPLATE.md`
- Create: `templates/project-map/modules/deep/references/TEMPLATE.md`
- Modify: `templates/commands/map-codebase.md`
- Modify: `templates/passive-skills/spec-kit-project-map-gate/SKILL.md`

### Tests

- Modify: `tests/test_project_map_status.py`
- Create: `tests/test_project_map_layered_contract.py`
- Modify: `tests/test_project_handbook_templates.py`
- Modify: `tests/test_map_codebase_template_guidance.py`
- Modify: `tests/test_extension_skills.py`
- Modify: `tests/integrations/test_cli.py`

### Pilot live atlas artifacts in this repository

- Modify: `PROJECT-HANDBOOK.md`
- Create: `.specify/project-map/index/atlas-config.json`
- Create: `.specify/project-map/index/atlas-index.json`
- Create: `.specify/project-map/index/modules.json`
- Create: `.specify/project-map/index/relations.json`
- Modify: `.specify/project-map/index/status.json` or migrate from `.specify/project-map/index/status.json`
- Create: `.specify/project-map/root/ARCHITECTURE.md`
- Create: `.specify/project-map/root/STRUCTURE.md`
- Create: `.specify/project-map/root/CONVENTIONS.md`
- Create: `.specify/project-map/root/INTEGRATIONS.md`
- Create: `.specify/project-map/root/WORKFLOWS.md`
- Create: `.specify/project-map/root/TESTING.md`
- Create: `.specify/project-map/root/OPERATIONS.md`
- Create: `.specify/project-map/modules/specify-cli-core/OVERVIEW.md`
- Create: `.specify/project-map/modules/specify-cli-core/ARCHITECTURE.md`
- Create: `.specify/project-map/modules/specify-cli-core/STRUCTURE.md`
- Create: `.specify/project-map/modules/specify-cli-core/WORKFLOWS.md`
- Create: `.specify/project-map/modules/specify-cli-core/TESTING.md`

---

### Task 1: Lock the layered atlas contract in tests

**Files:**
- Create: `tests/test_project_map_layered_contract.py`
- Modify: `tests/test_project_map_status.py`
- Modify: `tests/test_project_handbook_templates.py`

- [ ] **Step 1: Write failing tests for the new canonical atlas paths**

Create `tests/test_project_map_layered_contract.py` with assertions like:

```python
from pathlib import Path

from specify_cli.project_map_status import canonical_project_map_paths


def test_canonical_project_map_paths_include_index_root_and_module_entry(tmp_path: Path):
    paths = [str(path).replace("\\", "/") for path in canonical_project_map_paths(tmp_path)]
    assert f"{tmp_path.as_posix()}/PROJECT-HANDBOOK.md" in paths
    assert f"{tmp_path.as_posix()}/.specify/project-map/index/atlas-index.json" in paths
    assert f"{tmp_path.as_posix()}/.specify/project-map/index/modules.json" in paths
    assert f"{tmp_path.as_posix()}/.specify/project-map/index/relations.json" in paths
    assert f"{tmp_path.as_posix()}/.specify/project-map/index/status.json" in paths
    assert f"{tmp_path.as_posix()}/.specify/project-map/root/ARCHITECTURE.md" in paths
```

- [ ] **Step 2: Add failing status-schema expectations for module and deep state**

Extend `tests/test_project_map_status.py` with an assertion like:

```python
def test_project_map_status_round_trip_preserves_global_and_module_state(tmp_path):
    mod = _load_module()

    status = mod.ProjectMapStatus(
        version=2,
        global_freshness="possibly_stale",
        global_last_refresh_commit="abc123",
        global_stale_reasons=["module_changed"],
        global_affected_root_docs=["WORKFLOWS.md"],
        modules={
            "specify-cli-core": {
                "freshness": "stale",
                "deep_status": "deep_stale",
                "last_refresh_commit": "abc123",
                "coverage_fingerprint": "sha256:test",
                "stale_reasons": ["src_changed"],
                "affected_docs": ["WORKFLOWS.md"],
            }
        },
    )

    written = mod.write_project_map_status(tmp_path, status)
    loaded = mod.read_project_map_status(tmp_path)

    assert written == tmp_path / ".specify" / "project-map" / "index" / "status.json"
    assert loaded.modules["specify-cli-core"]["deep_status"] == "deep_stale"
```

- [ ] **Step 3: Add failing template assertions for `index/`, `root/`, and `modules/`**

Extend `tests/test_project_handbook_templates.py` with expectations like:

```python
assert "`.specify/project-map/index/atlas-index.json`" in handbook
assert "`.specify/project-map/root/ARCHITECTURE.md`" in handbook
assert "`.specify/project-map/modules/<module-id>/OVERVIEW.md`" in handbook
```

and:

```python
for rel_path in [
    "templates/project-map/index/atlas-config.json",
    "templates/project-map/index/atlas-index.json",
    "templates/project-map/index/modules.json",
    "templates/project-map/index/relations.json",
]:
    assert (PROJECT_ROOT / rel_path).exists()
```

- [ ] **Step 4: Run the targeted contract tests and confirm red**

Run:

```powershell
pytest tests/test_project_map_layered_contract.py tests/test_project_map_status.py tests/test_project_handbook_templates.py -q
```

Expected:

- path-contract tests fail because `index/`, `root/`, and module contract files do not exist yet
- status tests fail because the current schema is still global-only

- [ ] **Step 5: Commit the failing contract slice**

```bash
git add tests/test_project_map_layered_contract.py tests/test_project_map_status.py tests/test_project_handbook_templates.py
git commit -m "test: lock layered project-map atlas contract"
```

### Task 2: Implement the layered status and path model

**Files:**
- Modify: `src/specify_cli/project_map_status.py`
- Modify: `src/specify_cli/hooks/project_map.py`
- Modify: `src/specify_cli/__init__.py`

- [ ] **Step 1: Add layered path helpers**

Extend `src/specify_cli/project_map_status.py` with helpers like:

```python
INDEX_DIRNAME = "index"
ROOT_DIRNAME = "root"
MODULES_DIRNAME = "modules"


def project_map_index_dir(project_root: Path) -> Path:
    return project_map_dir(project_root) / INDEX_DIRNAME


def project_map_root_dir(project_root: Path) -> Path:
    return project_map_dir(project_root) / ROOT_DIRNAME


def project_map_modules_dir(project_root: Path) -> Path:
    return project_map_dir(project_root) / MODULES_DIRNAME


def project_map_status_path(project_root: Path) -> Path:
    return project_map_index_dir(project_root) / STATUS_FILENAME
```

- [ ] **Step 2: Replace the status dataclass with global and module state**

Refactor the current dataclass into a schema that can preserve module detail:

```python
@dataclass(slots=True)
class ProjectMapStatus:
    version: int = 2
    global_freshness: str = "missing"
    global_last_refresh_commit: str = ""
    global_last_refresh_at: str = ""
    global_stale_reasons: list[str] | None = None
    global_affected_root_docs: list[str] | None = None
    modules: dict[str, dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "global": {
                "freshness": self.global_freshness,
                "last_refresh_commit": self.global_last_refresh_commit,
                "last_refresh_at": self.global_last_refresh_at,
                "stale_reasons": list(self.global_stale_reasons or []),
                "affected_root_docs": list(self.global_affected_root_docs or []),
            },
            "modules": dict(self.modules or {}),
        }
```

Keep backward compatibility in `from_dict()` by detecting the old flat status
shape and mapping it into the new structure.

- [ ] **Step 3: Add module fingerprint and deep-staleness helpers**

Add helpers that operate on module registry entries:

```python
def module_status_payload(
    *,
    freshness: str,
    deep_status: str,
    last_refresh_commit: str,
    coverage_fingerprint: str,
    stale_reasons: list[str],
    affected_docs: list[str],
) -> dict[str, Any]:
    return {
        "freshness": freshness,
        "deep_status": deep_status,
        "last_refresh_commit": last_refresh_commit,
        "coverage_fingerprint": coverage_fingerprint,
        "stale_reasons": stale_reasons,
        "affected_docs": affected_docs,
    }
```

and a fingerprint helper that hashes only matched module coverage inputs:

```python
def coverage_fingerprint(paths: list[str]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        digest.update(path.encode("utf-8"))
    return f"sha256:{digest.hexdigest()}"
```

- [ ] **Step 4: Update CLI/hook payloads to point at `index/status.json`**

Adjust:

```python
payload["status_path"] = str(project_root / ".specify" / "project-map" / "index" / "status.json")
```

in `src/specify_cli/__init__.py` and `src/specify_cli/hooks/project_map.py`, and
change user-facing help text from:

```python
".specify/project-map/index/status.json"
```

to:

```python
".specify/project-map/index/status.json"
```

- [ ] **Step 5: Run the state and CLI tests to make them green**

Run:

```powershell
pytest tests/test_project_map_layered_contract.py tests/test_project_map_status.py tests/integrations/test_cli.py -q
```

Expected:

- layered path and status tests pass
- `project-map status/check` render the new status path without regressions

- [ ] **Step 6: Commit the layered state-model slice**

```bash
git add src/specify_cli/project_map_status.py src/specify_cli/hooks/project_map.py src/specify_cli/__init__.py tests/test_project_map_layered_contract.py tests/test_project_map_status.py tests/integrations/test_cli.py
git commit -m "feat: add layered project-map status model"
```

### Task 3: Add index, root, module, and deep templates

**Files:**
- Modify: `templates/project-handbook-template.md`
- Create: `templates/project-map/index/atlas-config.json`
- Create: `templates/project-map/index/atlas-index.json`
- Create: `templates/project-map/index/modules.json`
- Create: `templates/project-map/index/relations.json`
- Create: `templates/project-map/root/ARCHITECTURE.md`
- Create: `templates/project-map/root/STRUCTURE.md`
- Create: `templates/project-map/root/CONVENTIONS.md`
- Create: `templates/project-map/root/INTEGRATIONS.md`
- Create: `templates/project-map/root/WORKFLOWS.md`
- Create: `templates/project-map/root/TESTING.md`
- Create: `templates/project-map/root/OPERATIONS.md`
- Create: `templates/project-map/modules/OVERVIEW.md`
- Create: `templates/project-map/modules/ARCHITECTURE.md`
- Create: `templates/project-map/modules/STRUCTURE.md`
- Create: `templates/project-map/modules/WORKFLOWS.md`
- Create: `templates/project-map/modules/TESTING.md`
- Create: `templates/project-map/modules/deep/capabilities/TEMPLATE.md`
- Create: `templates/project-map/modules/deep/workflows/TEMPLATE.md`
- Create: `templates/project-map/modules/deep/integrations/TEMPLATE.md`
- Create: `templates/project-map/modules/deep/runtime/TEMPLATE.md`
- Create: `templates/project-map/modules/deep/references/TEMPLATE.md`

- [ ] **Step 1: Rewrite the handbook template to route into the new layers**

Update `templates/project-handbook-template.md` so `Topic Map` becomes:

```markdown
## Topic Map

- `.specify/project-map/index/atlas-index.json` - atlas entry summary
- `.specify/project-map/index/modules.json` - module registry and module document paths
- `.specify/project-map/index/relations.json` - cross-module dependencies and handoffs
- `.specify/project-map/index/status.json` - atlas freshness and module stale state
- `.specify/project-map/root/ARCHITECTURE.md` - global layers, truth ownership, shared seams
- `.specify/project-map/root/WORKFLOWS.md` - global workflow contracts and cross-module flows
- `.specify/project-map/modules/<module-id>/OVERVIEW.md` - module-local routing and ownership
```

- [ ] **Step 2: Add minimal JSON templates for index files**

Create `templates/project-map/index/atlas-index.json` with:

```json
{
  "version": 1,
  "generated_at": "YYYY-MM-DDTHH:MM:SSZ",
  "modules_count": 0,
  "last_full_refresh_commit": "",
  "global_freshness": "missing",
  "module_registry_path": ".specify/project-map/index/modules.json",
  "relations_path": ".specify/project-map/index/relations.json",
  "status_path": ".specify/project-map/index/status.json"
}
```

Create `atlas-config.json`, `modules.json`, and `relations.json` with empty but
contract-valid starter shapes.

- [ ] **Step 3: Move global topical templates under `root/`**

Create root topical templates using the same content model as the current flat
templates, but under:

```text
templates/project-map/root/
```

with headings such as:

```markdown
# Architecture
**Coverage Scope:** repository-wide conceptual architecture
```

- [ ] **Step 4: Add module and deep templates**

Create `templates/project-map/modules/OVERVIEW.md` with a structure like:

```markdown
# Module Overview

**Module ID:** <module-id>
**Owned Roots:** <root_paths>
**Related Root Topics:** <owner_topics>

## Purpose
## Why This Module Exists
## Shared Surfaces
## Risky Coordination Points
## Where To Read Next
```

and deep templates with the required fields:

```markdown
# Capability Detail

## Scope
## Why This Exists
## Truth Lives
## Inputs / Outputs
## Update Triggers
## Minimum Verification
## Confidence
```

- [ ] **Step 5: Run template tests and make them green**

Run:

```powershell
pytest tests/test_project_handbook_templates.py tests/test_project_map_layered_contract.py -q
```

Expected:

- handbook template routes into index/root/modules
- new template files exist and satisfy the contract

- [ ] **Step 6: Commit the layered template slice**

```bash
git add templates/project-handbook-template.md templates/project-map
git commit -m "feat: add layered project-map atlas templates"
```

### Task 4: Update `map-codebase` and passive gate contracts

**Files:**
- Modify: `templates/commands/map-codebase.md`
- Modify: `templates/passive-skills/spec-kit-project-map-gate/SKILL.md`
- Modify: `tests/test_map_codebase_template_guidance.py`
- Modify: `tests/test_extension_skills.py`

- [ ] **Step 1: Rewrite `map-codebase` output contract around layered outputs**

Change the canonical outputs section in `templates/commands/map-codebase.md` to
list:

```markdown
- `PROJECT-HANDBOOK.md`
- `.specify/project-map/index/atlas-index.json`
- `.specify/project-map/index/modules.json`
- `.specify/project-map/index/relations.json`
- `.specify/project-map/index/status.json`
- `.specify/project-map/root/*.md`
- `.specify/project-map/modules/<module-id>/*.md`
```

and add explicit rules:

```markdown
- `atlas-index.json` is the entry summary, not the truth source.
- `modules.json` is the module registry.
- `relations.json` is the cross-module routing source.
- `status.json` must track both global and module freshness.
- deep module content may be marked `deep_stale` instead of auto-rewritten.
```

- [ ] **Step 2: Rewrite the passive gate read contract**

Update `templates/passive-skills/spec-kit-project-map-gate/SKILL.md` from:

```markdown
- Read the relevant `.specify/project-map/*.md` files for the touched subsystem
```

to:

```markdown
- Read `.specify/project-map/index/atlas-index.json` and `.specify/project-map/index/status.json`.
- Read `PROJECT-HANDBOOK.md`.
- Resolve the primary touched module from `.specify/project-map/index/modules.json`.
- Read that module's `OVERVIEW.md` and the smallest relevant module docs.
- Expand into related modules only when `.specify/project-map/index/relations.json` says the touched area crosses module boundaries.
```

- [ ] **Step 3: Update guidance tests**

Extend `tests/test_map_codebase_template_guidance.py` and
`tests/test_extension_skills.py` with expectations like:

```python
assert ".specify/project-map/index/modules.json" in content
assert ".specify/project-map/modules/<module-id>/overview.md" in content.lower()
assert "deep_stale" in content
```

- [ ] **Step 4: Run the contract/gate subset**

Run:

```powershell
pytest tests/test_map_codebase_template_guidance.py tests/test_extension_skills.py -q
```

Expected:

- `map-codebase` and passive gate both teach the layered atlas read order

- [ ] **Step 5: Commit the contract rewrite**

```bash
git add templates/commands/map-codebase.md templates/passive-skills/spec-kit-project-map-gate/SKILL.md tests/test_map_codebase_template_guidance.py tests/test_extension_skills.py
git commit -m "feat: route map-codebase and project-map gate through layered atlas"
```

### Task 5: Pilot a real module and validate the closed loop

**Files:**
- Modify: `PROJECT-HANDBOOK.md`
- Create: `.specify/project-map/index/atlas-config.json`
- Create: `.specify/project-map/index/atlas-index.json`
- Create: `.specify/project-map/index/modules.json`
- Create: `.specify/project-map/index/relations.json`
- Modify: `.specify/project-map/index/status.json`
- Create: `.specify/project-map/root/ARCHITECTURE.md`
- Create: `.specify/project-map/root/STRUCTURE.md`
- Create: `.specify/project-map/root/CONVENTIONS.md`
- Create: `.specify/project-map/root/INTEGRATIONS.md`
- Create: `.specify/project-map/root/WORKFLOWS.md`
- Create: `.specify/project-map/root/TESTING.md`
- Create: `.specify/project-map/root/OPERATIONS.md`
- Create: `.specify/project-map/modules/specify-cli-core/OVERVIEW.md`
- Create: `.specify/project-map/modules/specify-cli-core/ARCHITECTURE.md`
- Create: `.specify/project-map/modules/specify-cli-core/STRUCTURE.md`
- Create: `.specify/project-map/modules/specify-cli-core/WORKFLOWS.md`
- Create: `.specify/project-map/modules/specify-cli-core/TESTING.md`

- [ ] **Step 1: Seed one real module in `modules.json`**

Create a pilot module registry entry like:

```json
{
  "modules": [
    {
      "module_id": "specify-cli-core",
      "display_name": "Specify CLI Core",
      "root_paths": ["src/specify_cli"],
      "include_globs": ["tests/**/specify*", "templates/commands/**"],
      "exclude_globs": ["**/__pycache__/**"],
      "tags": ["cli", "workflow", "atlas"],
      "owner_topics": ["ARCHITECTURE.md", "WORKFLOWS.md", "TESTING.md"],
      "doc_paths": {
        "overview": ".specify/project-map/modules/specify-cli-core/OVERVIEW.md",
        "architecture": ".specify/project-map/modules/specify-cli-core/ARCHITECTURE.md",
        "structure": ".specify/project-map/modules/specify-cli-core/STRUCTURE.md",
        "workflows": ".specify/project-map/modules/specify-cli-core/WORKFLOWS.md",
        "testing": ".specify/project-map/modules/specify-cli-core/TESTING.md"
      }
    }
  ]
}
```

- [ ] **Step 2: Populate the pilot module docs**

Write `OVERVIEW.md` with real facts like:

```markdown
## Purpose

Own the `specify` Typer CLI surface, workflow command registration, init flow,
and the root runtime glue that connects generated assets, project-map state,
and downstream integration installers.
```

and make `WORKFLOWS.md` explicitly cover `specify`, `project-map`, `learning`,
and command-registration boundaries in `src/specify_cli/__init__.py`.

- [ ] **Step 3: Mark deep content intentionally stale for the pilot**

Write the pilot module status entry with:

```json
"specify-cli-core": {
  "freshness": "fresh",
  "deep_status": "deep_stale",
  "last_refresh_commit": "HEAD",
  "coverage_fingerprint": "sha256:pilot",
  "stale_reasons": [],
  "affected_docs": []
}
```

This proves that the atlas can represent a module whose core docs are fresh
while deep docs still require later enrichment.

- [ ] **Step 4: Run the pilot closed loop**

Run:

```powershell
pytest tests/test_project_map_status.py tests/test_map_codebase_template_guidance.py tests/integrations/test_cli.py -q
```

Then manually verify the read path:

```text
1. Read PROJECT-HANDBOOK.md
2. Read .specify/project-map/index/modules.json
3. Open .specify/project-map/modules/specify-cli-core/OVERVIEW.md
4. Confirm the next docs to read are module-local, not global-only
```

Expected:

- tests stay green
- the atlas supports a real module lookup and explicit module-doc routing

- [ ] **Step 5: Commit the pilot atlas**

```bash
git add PROJECT-HANDBOOK.md .specify/project-map/index .specify/project-map/root .specify/project-map/modules/specify-cli-core
git commit -m "docs: pilot layered project-map atlas on specify-cli-core"
```

### Task 6: Run the focused verification sweep

**Files:**
- No new files in this task

- [ ] **Step 1: Run the layered-atlas regression suite**

Run:

```powershell
pytest tests/test_project_map_layered_contract.py tests/test_project_map_status.py tests/test_project_handbook_templates.py tests/test_map_codebase_template_guidance.py tests/test_extension_skills.py tests/integrations/test_cli.py -q
```

Expected:

- layered path contract passes
- layered status contract passes
- template and guidance surfaces all teach the new read order

- [ ] **Step 2: Run a project-map CLI smoke subset**

Run:

```powershell
python -m specify_cli project-map status --format json
python -m specify_cli project-map check --format json
python -m specify_cli hook complete-refresh
```

Expected:

- the CLI points to `.specify/project-map/index/status.json`
- no crash from the layered path migration

- [ ] **Step 3: Fix any contract drift before widening scope**

If failures mention old flat paths such as:

```text
.specify/project-map/index/status.json
```

or old read contracts such as:

```text
read the relevant `.specify/project-map/*.md` files
```

update the failing template, helper, or assertion before broadening the rollout
to more integrations or more pilot modules.

- [ ] **Step 4: Commit the verification pass**

```bash
git add -A
git commit -m "test: verify layered project-map atlas rollout"
```

## Spec Coverage Check

- Machine index layer: covered by Tasks 1, 2, and 3.
- Root and module split: covered by Tasks 3 and 5.
- Module discovery and stable IDs: covered by Task 5.
- Global plus module freshness with `deep_stale`: covered by Task 2 and Task 5.
- Agent read-order contract: covered by Task 4.
- Partial refresh and single-module pilot: covered by Task 5.
- Focused regression and CLI proof: covered by Task 6.

## Placeholder Scan

- No `TODO`, `TBD`, or deferred placeholders remain.
- Every task names exact files.
- Every verification step includes exact commands.
- Every schema or content step includes concrete starter content.

## Type and Naming Consistency Check

- Root entrypoint stays `PROJECT-HANDBOOK.md`.
- Machine index directory is `.specify/project-map/index/`.
- Root topical directory is `.specify/project-map/root/`.
- Module directory is `.specify/project-map/modules/<module-id>/`.
- Canonical deep stale value is `deep_stale`.
- The pilot module ID is `specify-cli-core`.
