# Sp Specify Lossless State Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add lossless, stage-backed `sp-specify` state so long specification runs can survive context compaction, resume from disk, and compile final artifacts from durable structured inputs instead of chat memory.

**Architecture:** Implement this as a product-surface change across templates, scaffolding scripts, validation hooks, and tests. The durable model is an append-only `brainstorming/journal.ndjson`, a `brainstorming/stage-manifest.json` recovery index, per-stage JSON landing points, and compiled final artifacts that cite the structured state package.

**Tech Stack:** Python 3.11, Typer hook runtime, Markdown command templates, JSON templates, bash and PowerShell scaffolding scripts, pytest

---

## File Structure

- Create: `templates/brainstorming-stage-manifest-template.json`
  - Recovery index template for journal pointer, checkpoint event ID, stage artifact metadata, and canonical stage keys.
- Create: `templates/brainstorming-domains-template.json`
  - Structured domain clarification state for domain closure, question/answer IDs, reopen history, and `compiled_from`.
- Create: `templates/brainstorming-evidence-index-template.json`
  - Index of evidence IDs, paths, hashes, source kinds, and accepted-use links.
- Create: `templates/brainstorming-evidence-record-template.json`
  - Per-evidence record shape for bounded raw snippets and source hashes.
- Modify: `templates/brainstorming-facts-template.json`
- Modify: `templates/brainstorming-route-template.json`
- Modify: `templates/brainstorming-intent-template.json`
- Modify: `templates/brainstorming-complexity-template.json`
- Modify: `templates/brainstorming-handoff-specify-template.json`
  - Add `compiled_from`, event IDs, evidence IDs, canonical stage references, and first-release payload contract hints.
- Modify: `templates/workflow-state-template.md`
  - Replace old `sp-specify` compatibility stage list with canonical stage enum and add checkpoint/journal pointers.
- Modify: `templates/specify-draft-template.md`
  - Keep human-readable ledger role but mark it as companion, not trusted recovery source.
- Modify: `templates/spec-template.md`
- Modify: `templates/alignment-template.md`
- Modify: `templates/context-template.md`
- Modify: `templates/references-template.md`
- Modify: `templates/checklist-template.md`
  - Add source-map guidance to final compiled artifacts.
- Modify: `templates/commands/specify.md`
- Modify: `templates/command-partials/specify/shell.md`
  - Require journal events, stage checkpoints, resume validation, and compile from structured state.
- Modify: `scripts/bash/create-new-feature.sh`
- Modify: `scripts/powershell/create-new-feature.ps1`
- Modify: `scripts/bash/common.sh`
- Modify: `scripts/powershell/common.ps1`
  - Scaffold and expose the new lossless state paths.
- Modify: `src/specify_cli/hooks/artifact_validation.py`
  - Validate journal, manifest, stage enum consistency, `compiled_from`, checkpoint pointers, and legacy warnings.
- Modify: `pyproject.toml`
  - Bundle new templates into the wheel/core pack.
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/test_specify_guidance_docs.py`
- Modify: `tests/hooks/test_artifact_hooks.py`
- Modify: `tests/contract/test_hook_cli_surface.py`
- Modify: `tests/integrations/test_cli.py`
  - Lock scaffolding, packaging, template guidance, and validation behavior.

---

### Task 1: Lock New Template And Packaging Contract In Tests

**Files:**
- Modify: `tests/test_alignment_templates.py`
- Modify: `tests/integrations/test_cli.py`
- Modify: `tests/test_packaging_assets.py`

- [ ] **Step 1: Add failing template packaging assertions**

Append this test to `tests/test_alignment_templates.py` near `test_feature_scaffolding_and_packaging_include_brainstorming_truth_templates`:

```python
def test_lossless_specify_state_templates_are_packaged_and_scaffolded() -> None:
    pyproject = _read("pyproject.toml")
    sh_create = _read("scripts/bash/create-new-feature.sh")
    ps_create = _read("scripts/powershell/create-new-feature.ps1")
    sh_common = _read("scripts/bash/common.sh")
    ps_common = _read("scripts/powershell/common.ps1")

    for path in (
        "templates/brainstorming-stage-manifest-template.json",
        "templates/brainstorming-domains-template.json",
        "templates/brainstorming-evidence-index-template.json",
        "templates/brainstorming-evidence-record-template.json",
    ):
        assert path in pyproject

    for token in (
        "BRAINSTORMING_JOURNAL",
        "BRAINSTORMING_STAGE_MANIFEST",
        "BRAINSTORMING_DOMAINS",
        "BRAINSTORMING_EVIDENCE_INDEX",
        "BRAINSTORMING_EVIDENCE_DIR",
    ):
        assert token in sh_common
        assert token in ps_common
        assert token in sh_create
        assert token in ps_create

    assert "brainstorming-stage-manifest-template" in sh_create
    assert "brainstorming-domains-template" in sh_create
    assert "brainstorming-evidence-index-template" in sh_create
    assert "brainstorming-evidence-record-template" in sh_create
    assert "brainstorming-stage-manifest-template" in ps_create
    assert "brainstorming-domains-template" in ps_create
    assert "brainstorming-evidence-index-template" in ps_create
    assert "brainstorming-evidence-record-template" in ps_create
```

- [ ] **Step 2: Add failing integration asset assertions**

In `tests/integrations/test_cli.py`, extend the test that checks generated template assets around the existing `brainstorming-*-template.json` assertions:

```python
assert (templates_dir / "brainstorming-stage-manifest-template.json").exists()
assert (templates_dir / "brainstorming-domains-template.json").exists()
assert (templates_dir / "brainstorming-evidence-index-template.json").exists()
assert (templates_dir / "brainstorming-evidence-record-template.json").exists()
```

- [ ] **Step 3: Add failing packaging assertions**

In `tests/test_packaging_assets.py`, add assertions that the `pyproject.toml` force-includes the four new template files:

```python
def test_lossless_specify_state_templates_are_force_included() -> None:
    pyproject = (PROJECT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    for template in (
        "templates/brainstorming-stage-manifest-template.json",
        "templates/brainstorming-domains-template.json",
        "templates/brainstorming-evidence-index-template.json",
        "templates/brainstorming-evidence-record-template.json",
    ):
        assert f'"{template}" = ' in pyproject
```

- [ ] **Step 4: Run focused red tests**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_lossless_specify_state_templates_are_packaged_and_scaffolded tests/test_packaging_assets.py::test_lossless_specify_state_templates_are_force_included -q
```

Expected: both tests fail because the new templates and script variables do not exist yet.

- [ ] **Step 5: Commit the failing tests**

```powershell
git add tests/test_alignment_templates.py tests/integrations/test_cli.py tests/test_packaging_assets.py
git commit -m "test: lock lossless specify scaffolding contract"
```

### Task 2: Add Lossless State Templates And Package Them

**Files:**
- Create: `templates/brainstorming-stage-manifest-template.json`
- Create: `templates/brainstorming-domains-template.json`
- Create: `templates/brainstorming-evidence-index-template.json`
- Create: `templates/brainstorming-evidence-record-template.json`
- Modify: `templates/brainstorming-facts-template.json`
- Modify: `templates/brainstorming-route-template.json`
- Modify: `templates/brainstorming-intent-template.json`
- Modify: `templates/brainstorming-complexity-template.json`
- Modify: `templates/brainstorming-handoff-specify-template.json`
- Modify: `pyproject.toml`

- [ ] **Step 1: Create the stage manifest template**

Create `templates/brainstorming-stage-manifest-template.json`:

```json
{
  "version": 1,
  "status": "active",
  "canonical_stage_enum": [
    "intake",
    "evidence-intake",
    "facts-lock",
    "route-lock",
    "intent-lock",
    "complexity-lock",
    "domain-clarification",
    "consequence-risk",
    "specify-compile",
    "release-decision"
  ],
  "journal": {
    "path": "brainstorming/journal.ndjson",
    "last_event_id": null,
    "last_checkpoint_id": null
  },
  "stages": {
    "intake": {
      "artifact": "workflow-state.md",
      "status": "pending",
      "event_range": [],
      "artifact_hash": null,
      "last_compiled_event_id": null,
      "recoverable": false
    },
    "evidence-intake": {
      "artifact": "brainstorming/evidence-index.json",
      "status": "pending",
      "event_range": [],
      "artifact_hash": null,
      "last_compiled_event_id": null,
      "recoverable": false
    },
    "facts-lock": {
      "artifact": "brainstorming/facts.json",
      "status": "pending",
      "event_range": [],
      "artifact_hash": null,
      "last_compiled_event_id": null,
      "recoverable": false
    },
    "route-lock": {
      "artifact": "brainstorming/route.json",
      "status": "pending",
      "event_range": [],
      "artifact_hash": null,
      "last_compiled_event_id": null,
      "recoverable": false
    },
    "intent-lock": {
      "artifact": "brainstorming/intent.json",
      "status": "pending",
      "event_range": [],
      "artifact_hash": null,
      "last_compiled_event_id": null,
      "recoverable": false
    },
    "complexity-lock": {
      "artifact": "brainstorming/complexity.json",
      "status": "pending",
      "event_range": [],
      "artifact_hash": null,
      "last_compiled_event_id": null,
      "recoverable": false
    },
    "domain-clarification": {
      "artifact": "brainstorming/domains.json",
      "status": "pending",
      "event_range": [],
      "artifact_hash": null,
      "last_compiled_event_id": null,
      "recoverable": false
    },
    "consequence-risk": {
      "artifact": "brainstorming/handoff-to-specify.json",
      "status": "pending",
      "event_range": [],
      "artifact_hash": null,
      "last_compiled_event_id": null,
      "recoverable": false
    },
    "specify-compile": {
      "artifact": "spec.md",
      "status": "pending",
      "event_range": [],
      "artifact_hash": null,
      "last_compiled_event_id": null,
      "recoverable": false
    },
    "release-decision": {
      "artifact": "workflow-state.md",
      "status": "pending",
      "event_range": [],
      "artifact_hash": null,
      "last_compiled_event_id": null,
      "recoverable": false
    }
  }
}
```

- [ ] **Step 2: Create the domains template**

Create `templates/brainstorming-domains-template.json`:

```json
{
  "version": 1,
  "status": "pending",
  "stage": "domain-clarification",
  "domains": {
    "goal-and-users": {
      "status": "not-started",
      "question_ids": [],
      "answer_event_ids": [],
      "evidence_ids": [],
      "reopen_event_ids": []
    },
    "triggers-and-primary-flow": {
      "status": "not-started",
      "question_ids": [],
      "answer_event_ids": [],
      "evidence_ids": [],
      "reopen_event_ids": []
    },
    "boundaries-and-non-goals": {
      "status": "not-started",
      "question_ids": [],
      "answer_event_ids": [],
      "evidence_ids": [],
      "reopen_event_ids": []
    },
    "failure-paths-exceptions-and-permissions": {
      "status": "not-started",
      "question_ids": [],
      "answer_event_ids": [],
      "evidence_ids": [],
      "reopen_event_ids": []
    },
    "dependencies-constraints-and-upstream-downstream-impact": {
      "status": "not-started",
      "question_ids": [],
      "answer_event_ids": [],
      "evidence_ids": [],
      "reopen_event_ids": []
    },
    "acceptance-and-completeness-gap-closure": {
      "status": "not-started",
      "question_ids": [],
      "answer_event_ids": [],
      "evidence_ids": [],
      "reopen_event_ids": []
    }
  },
  "questions": [],
  "reopens": [],
  "compiled_from": {
    "journal": "brainstorming/journal.ndjson",
    "event_range": [],
    "key_events": [],
    "evidence_ids": [],
    "compiled_at": null
  }
}
```

- [ ] **Step 3: Create evidence templates**

Create `templates/brainstorming-evidence-index-template.json`:

```json
{
  "version": 1,
  "status": "pending",
  "stage": "evidence-intake",
  "evidence": [],
  "accepted_use": [],
  "compiled_from": {
    "journal": "brainstorming/journal.ndjson",
    "event_range": [],
    "key_events": [],
    "evidence_ids": [],
    "compiled_at": null
  }
}
```

Create `templates/brainstorming-evidence-record-template.json`:

```json
{
  "version": 1,
  "evidence_id": "EVD-000",
  "source_kind": "repo",
  "source": null,
  "source_path": null,
  "source_url": null,
  "excerpt": "",
  "content_hash": null,
  "captured_event_id": null,
  "stage": "evidence-intake",
  "domain": null,
  "relevance": "",
  "accepted_use": []
}
```

- [ ] **Step 4: Add `compiled_from` to existing brainstorming templates**

For each existing brainstorming JSON template, add this top-level object without removing current fields:

```json
"compiled_from": {
  "journal": "brainstorming/journal.ndjson",
  "event_range": [],
  "key_events": [],
  "evidence_ids": [],
  "compiled_at": null
}
```

Also add a top-level `"stage"` value:

```json
"stage": "facts-lock"
```

Use these stage values:

- `facts.json`: `facts-lock`
- `route.json`: `route-lock`
- `intent.json`: `intent-lock`
- `complexity.json`: `complexity-lock`
- `handoff-to-specify.json`: `consequence-risk`

- [ ] **Step 5: Add template force-includes**

Add these lines under `[tool.hatch.build.targets.wheel.force-include]` in `pyproject.toml`:

```toml
"templates/brainstorming-stage-manifest-template.json" = "specify_cli/core_pack/templates/brainstorming-stage-manifest-template.json"
"templates/brainstorming-domains-template.json" = "specify_cli/core_pack/templates/brainstorming-domains-template.json"
"templates/brainstorming-evidence-index-template.json" = "specify_cli/core_pack/templates/brainstorming-evidence-index-template.json"
"templates/brainstorming-evidence-record-template.json" = "specify_cli/core_pack/templates/brainstorming-evidence-record-template.json"
```

- [ ] **Step 6: Run packaging/template tests**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_lossless_specify_state_templates_are_packaged_and_scaffolded tests/test_packaging_assets.py::test_lossless_specify_state_templates_are_force_included -q
```

Expected: tests still fail only on script/common variables; template and pyproject assertions pass.

- [ ] **Step 7: Commit templates**

```powershell
git add templates pyproject.toml
git commit -m "feat: add lossless specify state templates"
```

### Task 3: Scaffold Lossless State Files In Bash And PowerShell

**Files:**
- Modify: `scripts/bash/create-new-feature.sh`
- Modify: `scripts/powershell/create-new-feature.ps1`
- Modify: `scripts/bash/common.sh`
- Modify: `scripts/powershell/common.ps1`
- Modify: `tests/test_alignment_templates.py`

- [ ] **Step 1: Add bash path variables**

In `scripts/bash/create-new-feature.sh`, add path variables next to the existing brainstorming paths:

```bash
BRAINSTORMING_JOURNAL_FILE="$FEATURE_DIR/brainstorming/journal.ndjson"
BRAINSTORMING_STAGE_MANIFEST_FILE="$FEATURE_DIR/brainstorming/stage-manifest.json"
BRAINSTORMING_DOMAINS_FILE="$FEATURE_DIR/brainstorming/domains.json"
BRAINSTORMING_EVIDENCE_INDEX_FILE="$FEATURE_DIR/brainstorming/evidence-index.json"
BRAINSTORMING_EVIDENCE_DIR="$FEATURE_DIR/brainstorming/evidence"
BRAINSTORMING_EVIDENCE_RECORD_TEMPLATE_FILE="$FEATURE_DIR/brainstorming/evidence/EVD-000-template.json"
```

- [ ] **Step 2: Scaffold bash files**

Change the directory creation line to:

```bash
mkdir -p "$FEATURE_DIR" "$BRAINSTORMING_DIR" "$BRAINSTORMING_EVIDENCE_DIR"
```

Add scaffold calls after existing brainstorming template calls:

```bash
scaffold_template_file "brainstorming-stage-manifest-template" "$BRAINSTORMING_STAGE_MANIFEST_FILE"
scaffold_template_file "brainstorming-domains-template" "$BRAINSTORMING_DOMAINS_FILE"
scaffold_template_file "brainstorming-evidence-index-template" "$BRAINSTORMING_EVIDENCE_INDEX_FILE"
scaffold_template_file "brainstorming-evidence-record-template" "$BRAINSTORMING_EVIDENCE_RECORD_TEMPLATE_FILE"
if [ ! -f "$BRAINSTORMING_JOURNAL_FILE" ]; then
    : > "$BRAINSTORMING_JOURNAL_FILE"
fi
```

- [ ] **Step 3: Add PowerShell path variables**

In `scripts/powershell/create-new-feature.ps1`, add variables next to existing brainstorming paths:

```powershell
$brainstormingJournalFile = Join-Path $brainstormingDir 'journal.ndjson'
$brainstormingStageManifestFile = Join-Path $brainstormingDir 'stage-manifest.json'
$brainstormingDomainsFile = Join-Path $brainstormingDir 'domains.json'
$brainstormingEvidenceIndexFile = Join-Path $brainstormingDir 'evidence-index.json'
$brainstormingEvidenceDir = Join-Path $brainstormingDir 'evidence'
$brainstormingEvidenceRecordTemplateFile = Join-Path $brainstormingEvidenceDir 'EVD-000-template.json'
```

- [ ] **Step 4: Scaffold PowerShell files**

Add:

```powershell
New-Item -ItemType Directory -Path $brainstormingEvidenceDir -Force | Out-Null
```

Add these entries to the `Copy-OrCreateTemplateFile` array:

```powershell
@{ Template = 'brainstorming-stage-manifest-template'; Destination = $brainstormingStageManifestFile }
@{ Template = 'brainstorming-domains-template'; Destination = $brainstormingDomainsFile }
@{ Template = 'brainstorming-evidence-index-template'; Destination = $brainstormingEvidenceIndexFile }
@{ Template = 'brainstorming-evidence-record-template'; Destination = $brainstormingEvidenceRecordTemplateFile }
```

Then add:

```powershell
if (-not (Test-Path -PathType Leaf $brainstormingJournalFile)) {
    New-Item -ItemType File -Path $brainstormingJournalFile -Force | Out-Null
}
```

- [ ] **Step 5: Expose common helper paths**

In `scripts/bash/common.sh`, add these `printf` lines next to existing brainstorming outputs:

```bash
printf 'BRAINSTORMING_JOURNAL=%q\n' "$feature_dir/brainstorming/journal.ndjson"
printf 'BRAINSTORMING_STAGE_MANIFEST=%q\n' "$feature_dir/brainstorming/stage-manifest.json"
printf 'BRAINSTORMING_DOMAINS=%q\n' "$feature_dir/brainstorming/domains.json"
printf 'BRAINSTORMING_EVIDENCE_INDEX=%q\n' "$feature_dir/brainstorming/evidence-index.json"
printf 'BRAINSTORMING_EVIDENCE_DIR=%q\n' "$feature_dir/brainstorming/evidence"
```

In `scripts/powershell/common.ps1`, add these object properties:

```powershell
BRAINSTORMING_JOURNAL = Join-Path $featureDir 'brainstorming/journal.ndjson'
BRAINSTORMING_STAGE_MANIFEST = Join-Path $featureDir 'brainstorming/stage-manifest.json'
BRAINSTORMING_DOMAINS = Join-Path $featureDir 'brainstorming/domains.json'
BRAINSTORMING_EVIDENCE_INDEX = Join-Path $featureDir 'brainstorming/evidence-index.json'
BRAINSTORMING_EVIDENCE_DIR = Join-Path $featureDir 'brainstorming/evidence'
```

- [ ] **Step 6: Run focused tests**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_lossless_specify_state_templates_are_packaged_and_scaffolded -q
```

Expected: PASS.

- [ ] **Step 7: Commit scaffolding**

```powershell
git add scripts/bash/create-new-feature.sh scripts/powershell/create-new-feature.ps1 scripts/bash/common.sh scripts/powershell/common.ps1 tests/test_alignment_templates.py
git commit -m "feat: scaffold lossless specify state"
```

### Task 4: Lock Workflow Template Guidance For Journal, Checkpoints, And Compile

**Files:**
- Modify: `tests/test_alignment_templates.py`
- Modify: `templates/commands/specify.md`
- Modify: `templates/command-partials/specify/shell.md`
- Modify: `templates/workflow-state-template.md`
- Modify: `templates/specify-draft-template.md`

- [ ] **Step 1: Add failing workflow guidance test**

Append this test to `tests/test_alignment_templates.py` near the existing `sp-specify` template tests:

```python
def test_specify_template_requires_lossless_journal_stage_manifest_and_checkpoints() -> None:
    specify = _read("templates/commands/specify.md")
    shell = _read("templates/command-partials/specify/shell.md")
    workflow_state = _read("templates/workflow-state-template.md")
    draft = _read("templates/specify-draft-template.md")

    combined = "\n".join([specify, shell, workflow_state, draft])
    for expected in (
        "brainstorming/journal.ndjson",
        "brainstorming/stage-manifest.json",
        "brainstorming/domains.json",
        "brainstorming/evidence-index.json",
        "checkpoint_written",
        "compiled_from",
        "last_checkpoint_id",
        "last_event_id",
        "journal replay wins",
        "Markdown is not a trusted recovery source",
    ):
        assert expected in combined

    for stage in (
        "intake",
        "evidence-intake",
        "facts-lock",
        "route-lock",
        "intent-lock",
        "complexity-lock",
        "domain-clarification",
        "consequence-risk",
        "specify-compile",
        "release-decision",
    ):
        assert stage in workflow_state
        assert stage in specify
```

- [ ] **Step 2: Run the red test**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_specify_template_requires_lossless_journal_stage_manifest_and_checkpoints -q
```

Expected: FAIL because workflow templates do not yet mention the lossless contract.

- [ ] **Step 3: Update workflow-state template**

Modify `templates/workflow-state-template.md`:

- Change the `current_stage` allowed value list to:

```markdown
- current_stage: [intake | evidence-intake | facts-lock | route-lock | intent-lock | complexity-lock | domain-clarification | consequence-risk | specify-compile | release-decision | plan-design | task-generation | analysis | implementation | research]
```

- Add a new section after `## Fixed Lifecycle State`:

```markdown
## Lossless Resume State

- journal_file: [brainstorming/journal.ndjson | none]
- stage_manifest: [brainstorming/stage-manifest.json | none]
- last_event_id: [EVT-###### | none]
- last_checkpoint_id: [EVT-###### | none]
- resume_validation: [not-run | valid | repaired-from-journal | blocked]
```

- [ ] **Step 4: Update `sp-specify` template and shell partial**

In `templates/commands/specify.md` and `templates/command-partials/specify/shell.md`, add explicit requirements:

- create or resume `BRAINSTORMING_JOURNAL_FILE`
- create or resume `BRAINSTORMING_STAGE_MANIFEST_FILE`
- append journal events for user input, evidence, questions, answers, decisions, reopens, artifact compilation, and checkpoints
- write `checkpoint_written` before compaction-risk transitions
- treat `checkpoint_written.event_id` as `last_checkpoint_id`
- validate stage artifacts against `stage-manifest.json`
- if journal and stage artifacts disagree, journal replay wins
- compile final artifacts from stage artifacts plus cited journal/evidence events

Use this exact sentence somewhere in the template:

```markdown
Markdown is not a trusted recovery source; JSON stage artifacts plus `brainstorming/journal.ndjson` are the trusted recovery and compile contract.
```

Use this exact sentence somewhere in the template:

```markdown
If journal replay and a compiled stage artifact disagree, journal replay wins and the stage artifact must be regenerated before continuing.
```

- [ ] **Step 5: Update specify-draft template**

In `templates/specify-draft-template.md`, add a short section:

```markdown
## Lossless State Companion

- Trusted recovery source: JSON stage artifacts plus `brainstorming/journal.ndjson`
- Human-readable companion: this file
- Markdown is not a trusted recovery source.
- If this file disagrees with structured stage artifacts, regenerate or repair this file from the structured state.
```

- [ ] **Step 6: Run focused template tests**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_specify_template_requires_lossless_journal_stage_manifest_and_checkpoints tests/test_alignment_templates.py::test_specify_template_requires_brainstorming_lock_flow_and_handoff_chain -q
```

Expected: PASS.

- [ ] **Step 7: Commit workflow guidance**

```powershell
git add tests/test_alignment_templates.py templates/commands/specify.md templates/command-partials/specify/shell.md templates/workflow-state-template.md templates/specify-draft-template.md
git commit -m "feat: require lossless specify workflow state"
```

### Task 5: Add Final Artifact Source-Map Guidance

**Files:**
- Modify: `tests/test_alignment_templates.py`
- Modify: `templates/spec-template.md`
- Modify: `templates/alignment-template.md`
- Modify: `templates/context-template.md`
- Modify: `templates/references-template.md`
- Modify: `templates/checklist-template.md`

- [ ] **Step 1: Add failing source-map template test**

Append this test to `tests/test_alignment_templates.py` near `test_compiled_artifact_templates_preserve_route_and_complexity_truth`:

```python
def test_final_artifact_templates_preserve_lossless_source_map_guidance() -> None:
    spec = _read("templates/spec-template.md")
    alignment = _read("templates/alignment-template.md")
    context = _read("templates/context-template.md")
    references = _read("templates/references-template.md")
    checklist = _read("templates/checklist-template.md")

    for content in (spec, alignment, context, references):
        assert "Source Map" in content
        assert "brainstorming/journal.ndjson" in content
        assert "brainstorming/stage-manifest.json" in content
        assert "EVT-" in content
        assert "EVD-" in content

    assert "lossless source map" in checklist.lower()
    assert "compiled_from" in checklist
```

- [ ] **Step 2: Run the red test**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_final_artifact_templates_preserve_lossless_source_map_guidance -q
```

Expected: FAIL because final artifact templates do not yet carry the new source-map guidance.

- [ ] **Step 3: Update final artifact templates**

Add a compact source-map section to `templates/spec-template.md`, `templates/alignment-template.md`, `templates/context-template.md`, and `templates/references-template.md`:

```markdown
## Lossless Source Map

- Journal: `brainstorming/journal.ndjson`
- Stage Manifest: `brainstorming/stage-manifest.json`
- Source Event IDs:
  - EVT-###: [Decision, evidence, answer, or checkpoint used]
- Evidence IDs:
  - EVD-###: [Evidence record used]
- Compiled From:
  - `compiled_from`: [journal range and stage artifact inputs]
```

In `templates/checklist-template.md`, add validation items:

```markdown
- [ ] Final artifacts include a lossless source map for planning-critical claims
- [ ] `compiled_from` references are present for structured stage artifacts
- [ ] Major claims trace to `EVT-###` or `EVD-###` identifiers
```

- [ ] **Step 4: Run focused tests**

Run:

```powershell
pytest tests/test_alignment_templates.py::test_final_artifact_templates_preserve_lossless_source_map_guidance tests/test_alignment_templates.py::test_compiled_artifact_templates_preserve_route_and_complexity_truth -q
```

Expected: PASS.

- [ ] **Step 5: Commit source-map template updates**

```powershell
git add tests/test_alignment_templates.py templates/spec-template.md templates/alignment-template.md templates/context-template.md templates/references-template.md templates/checklist-template.md
git commit -m "feat: add lossless source maps to specify artifacts"
```

### Task 6: Add Artifact Validation For Journal, Manifest, Stage Enum, And Checkpoints

**Files:**
- Modify: `tests/hooks/test_artifact_hooks.py`
- Modify: `src/specify_cli/hooks/artifact_validation.py`

- [ ] **Step 1: Add valid lossless helper fixtures**

Update `_write_valid_brainstorming_truth_files(feature_dir: Path)` in `tests/hooks/test_artifact_hooks.py` so it writes lossless files:

```python
    journal_event = {
        "event_id": "EVT-000001",
        "schema_version": 1,
        "created_at": "2026-05-16T00:00:00Z",
        "stage": "facts-lock",
        "domain": "goal-and-users",
        "type": "checkpoint_written",
        "source": {"kind": "agent", "excerpt": "checkpoint", "content_hash": "sha256:checkpoint"},
        "payload": {
            "checkpoint_event_id": "EVT-000001",
            "current_stage": "facts-lock",
            "current_domain": "goal-and-users",
            "manifest_hash": "sha256:manifest",
            "workflow_state_hash": "sha256:workflow",
            "next_action": "continue"
        },
        "writes": [],
        "supersedes_event_id": None
    }
    (brainstorming_dir / "journal.ndjson").write_text(json.dumps(journal_event) + "\n", encoding="utf-8")
    (brainstorming_dir / "stage-manifest.json").write_text(
        json.dumps(
            {
                "version": 1,
                "status": "active",
                "canonical_stage_enum": [
                    "intake",
                    "evidence-intake",
                    "facts-lock",
                    "route-lock",
                    "intent-lock",
                    "complexity-lock",
                    "domain-clarification",
                    "consequence-risk",
                    "specify-compile",
                    "release-decision"
                ],
                "journal": {
                    "path": "brainstorming/journal.ndjson",
                    "last_event_id": "EVT-000001",
                    "last_checkpoint_id": "EVT-000001"
                },
                "stages": {
                    "facts-lock": {
                        "artifact": "brainstorming/facts.json",
                        "status": "closed",
                        "event_range": ["EVT-000001", "EVT-000001"],
                        "artifact_hash": None,
                        "last_compiled_event_id": "EVT-000001",
                        "recoverable": True
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    (brainstorming_dir / "domains.json").write_text(
        '{"version":1,"status":"active","stage":"domain-clarification","domains":{},"questions":[],"reopens":[],"compiled_from":{"journal":"brainstorming/journal.ndjson","event_range":["EVT-000001","EVT-000001"],"key_events":["EVT-000001"],"evidence_ids":[],"compiled_at":"2026-05-16T00:00:00Z"}}',
        encoding="utf-8",
    )
    (brainstorming_dir / "evidence-index.json").write_text(
        '{"version":1,"status":"active","stage":"evidence-intake","evidence":[],"accepted_use":[],"compiled_from":{"journal":"brainstorming/journal.ndjson","event_range":["EVT-000001","EVT-000001"],"key_events":["EVT-000001"],"evidence_ids":[],"compiled_at":"2026-05-16T00:00:00Z"}}',
        encoding="utf-8",
    )
    (brainstorming_dir / "evidence").mkdir(exist_ok=True)
```

Also add `compiled_from` blocks and `"stage"` to the existing JSON strings the helper writes.

- [ ] **Step 2: Add failing validation tests**

Add these tests to `tests/hooks/test_artifact_hooks.py`:

```python
def test_validate_artifacts_blocks_specify_when_lossless_journal_is_missing(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "brainstorming" / "journal.ndjson").unlink()

    result = run_quality_hook(project, "workflow.artifacts.validate", {"command_name": "specify", "feature_dir": str(feature_dir)})

    assert result.status == "blocked"
    assert any("brainstorming/journal.ndjson" in message for message in result.errors)


def test_validate_artifacts_blocks_specify_when_checkpoint_pointer_is_not_in_journal(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    manifest = json.loads((feature_dir / "brainstorming" / "stage-manifest.json").read_text(encoding="utf-8"))
    manifest["journal"]["last_checkpoint_id"] = "EVT-999999"
    (feature_dir / "brainstorming" / "stage-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    result = run_quality_hook(project, "workflow.artifacts.validate", {"command_name": "specify", "feature_dir": str(feature_dir)})

    assert result.status == "blocked"
    assert any("last_checkpoint_id" in message and "EVT-999999" in message for message in result.errors)


def test_validate_artifacts_blocks_specify_when_stage_enum_drifts(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    manifest = json.loads((feature_dir / "brainstorming" / "stage-manifest.json").read_text(encoding="utf-8"))
    manifest["stages"]["question-batch"] = manifest["stages"].pop("facts-lock")
    (feature_dir / "brainstorming" / "stage-manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    result = run_quality_hook(project, "workflow.artifacts.validate", {"command_name": "specify", "feature_dir": str(feature_dir)})

    assert result.status == "blocked"
    assert any("canonical stage" in message.lower() or "question-batch" in message for message in result.errors)


def test_validate_artifacts_blocks_specify_when_closed_stage_lacks_compiled_from(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    facts = json.loads((feature_dir / "brainstorming" / "facts.json").read_text(encoding="utf-8"))
    facts.pop("compiled_from", None)
    (feature_dir / "brainstorming" / "facts.json").write_text(json.dumps(facts), encoding="utf-8")

    result = run_quality_hook(project, "workflow.artifacts.validate", {"command_name": "specify", "feature_dir": str(feature_dir)})

    assert result.status == "blocked"
    assert any("compiled_from" in message and "brainstorming/facts.json" in message for message in result.errors)
```

- [ ] **Step 3: Run red validation tests**

Run:

```powershell
pytest tests/hooks/test_artifact_hooks.py::test_validate_artifacts_blocks_specify_when_lossless_journal_is_missing tests/hooks/test_artifact_hooks.py::test_validate_artifacts_blocks_specify_when_checkpoint_pointer_is_not_in_journal tests/hooks/test_artifact_hooks.py::test_validate_artifacts_blocks_specify_when_stage_enum_drifts tests/hooks/test_artifact_hooks.py::test_validate_artifacts_blocks_specify_when_closed_stage_lacks_compiled_from -q
```

Expected: FAIL until validation is implemented.

- [ ] **Step 4: Extend required artifacts**

In `src/specify_cli/hooks/artifact_validation.py`, add these entries to `FILE_REQUIRED_ARTIFACTS["specify"]` and `REQUIRED_ARTIFACTS["specify"]`:

```python
"brainstorming/journal.ndjson",
"brainstorming/stage-manifest.json",
"brainstorming/domains.json",
"brainstorming/evidence-index.json",
```

Add `"brainstorming/evidence"` to `DIRECTORY_REQUIRED_ARTIFACTS["specify"]` and `REQUIRED_ARTIFACTS["specify"]`.

- [ ] **Step 5: Add validation helper functions**

Add constants near the top of `artifact_validation.py`:

```python
LOSSLESS_SPECIFY_STAGES = {
    "intake",
    "evidence-intake",
    "facts-lock",
    "route-lock",
    "intent-lock",
    "complexity-lock",
    "domain-clarification",
    "consequence-risk",
    "specify-compile",
    "release-decision",
}
```

Add helper functions:

```python
def _read_journal_events(feature_dir: Path) -> tuple[list[dict[str, Any]], list[str]]:
    journal_path = feature_dir / "brainstorming" / "journal.ndjson"
    events: list[dict[str, Any]] = []
    errors: list[str] = []
    for index, line in enumerate(journal_path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"brainstorming/journal.ndjson line {index} is invalid JSON: {exc.msg}")
            continue
        if not isinstance(event, dict):
            errors.append(f"brainstorming/journal.ndjson line {index} must be an object")
            continue
        event_id = str(event.get("event_id") or "").strip()
        event_type = str(event.get("type") or "").strip()
        stage = str(event.get("stage") or "").strip()
        if not event_id:
            errors.append(f"brainstorming/journal.ndjson line {index} missing event_id")
        if not event_type:
            errors.append(f"brainstorming/journal.ndjson line {index} missing type")
        if stage and stage not in LOSSLESS_SPECIFY_STAGES:
            errors.append(f"brainstorming/journal.ndjson line {index} uses non-canonical stage: {stage}")
        events.append(event)
    return events, errors


def _validate_compiled_from(payload: dict[str, Any], label: str) -> list[str]:
    compiled_from = payload.get("compiled_from")
    if not isinstance(compiled_from, dict):
        return [f"{label} missing compiled_from"]
    if str(compiled_from.get("journal") or "").strip() != "brainstorming/journal.ndjson":
        return [f"{label} compiled_from.journal must be brainstorming/journal.ndjson"]
    event_range = compiled_from.get("event_range")
    key_events = compiled_from.get("key_events")
    evidence_ids = compiled_from.get("evidence_ids")
    errors: list[str] = []
    if not isinstance(event_range, list):
        errors.append(f"{label} compiled_from.event_range must be a list")
    if not isinstance(key_events, list):
        errors.append(f"{label} compiled_from.key_events must be a list")
    if not isinstance(evidence_ids, list):
        errors.append(f"{label} compiled_from.evidence_ids must be a list")
    return errors
```

- [ ] **Step 6: Implement manifest validation**

Add `_validate_lossless_specify_state(feature_dir: Path) -> list[str]`:

```python
def _validate_lossless_specify_state(feature_dir: Path) -> list[str]:
    errors: list[str] = []
    events, journal_errors = _read_journal_events(feature_dir)
    errors.extend(journal_errors)
    event_ids = {str(event.get("event_id") or "").strip() for event in events if isinstance(event, dict)}
    checkpoint_ids = {
        str(event.get("event_id") or "").strip()
        for event in events
        if isinstance(event, dict) and str(event.get("type") or "").strip() == "checkpoint_written"
    }

    manifest, manifest_errors = _read_json_artifact(
        feature_dir / "brainstorming" / "stage-manifest.json",
        "brainstorming/stage-manifest.json",
    )
    errors.extend(manifest_errors)
    if manifest_errors:
        return errors
    if not isinstance(manifest, dict):
        return ["brainstorming/stage-manifest.json must contain a top-level object"]

    stages = manifest.get("stages")
    if not isinstance(stages, dict):
        errors.append("brainstorming/stage-manifest.json stages must be an object")
        stages = {}
    for stage in stages:
        if stage not in LOSSLESS_SPECIFY_STAGES:
            errors.append(f"brainstorming/stage-manifest.json uses non-canonical stage: {stage}")

    canonical = manifest.get("canonical_stage_enum")
    if isinstance(canonical, list):
        missing = sorted(LOSSLESS_SPECIFY_STAGES - {str(item) for item in canonical})
        extra = sorted({str(item) for item in canonical} - LOSSLESS_SPECIFY_STAGES)
        if missing:
            errors.append(f"brainstorming/stage-manifest.json canonical_stage_enum missing: {', '.join(missing)}")
        if extra:
            errors.append(f"brainstorming/stage-manifest.json canonical_stage_enum has unknown stages: {', '.join(extra)}")

    journal = manifest.get("journal")
    if not isinstance(journal, dict):
        errors.append("brainstorming/stage-manifest.json journal must be an object")
    else:
        last_event_id = str(journal.get("last_event_id") or "").strip()
        last_checkpoint_id = str(journal.get("last_checkpoint_id") or "").strip()
        if last_event_id and last_event_id not in event_ids:
            errors.append(f"brainstorming/stage-manifest.json last_event_id not found in journal: {last_event_id}")
        if last_checkpoint_id and last_checkpoint_id not in checkpoint_ids:
            errors.append(f"brainstorming/stage-manifest.json last_checkpoint_id not found as checkpoint_written event in journal: {last_checkpoint_id}")

    for relative_path in (
        "brainstorming/facts.json",
        "brainstorming/route.json",
        "brainstorming/intent.json",
        "brainstorming/complexity.json",
        "brainstorming/domains.json",
        "brainstorming/evidence-index.json",
        "brainstorming/handoff-to-specify.json",
    ):
        payload, payload_errors = _read_json_artifact(feature_dir / relative_path, relative_path)
        errors.extend(payload_errors)
        if not payload_errors and isinstance(payload, dict):
            stage = str(payload.get("stage") or "").strip()
            if stage and stage not in LOSSLESS_SPECIFY_STAGES:
                errors.append(f"{relative_path} uses non-canonical stage: {stage}")
            errors.extend(_validate_compiled_from(payload, relative_path))
    return errors
```

Then call it inside `_validate_specify_draft_artifacts(feature_dir)` before returning:

```python
errors.extend(_validate_lossless_specify_state(feature_dir))
```

- [ ] **Step 7: Run validation tests**

Run:

```powershell
pytest tests/hooks/test_artifact_hooks.py::test_validate_artifacts_blocks_specify_when_lossless_journal_is_missing tests/hooks/test_artifact_hooks.py::test_validate_artifacts_blocks_specify_when_checkpoint_pointer_is_not_in_journal tests/hooks/test_artifact_hooks.py::test_validate_artifacts_blocks_specify_when_stage_enum_drifts tests/hooks/test_artifact_hooks.py::test_validate_artifacts_blocks_specify_when_closed_stage_lacks_compiled_from tests/hooks/test_artifact_hooks.py::test_validate_artifacts_accepts_fixed_lifecycle_state_and_draft_contract -q
```

Expected: PASS. If older positive fixtures fail, update only the fixture helper to include the required lossless artifacts; do not loosen validation for non-legacy positive paths.

- [ ] **Step 8: Commit validation**

```powershell
git add tests/hooks/test_artifact_hooks.py src/specify_cli/hooks/artifact_validation.py
git commit -m "feat: validate lossless specify artifacts"
```

### Task 7: Add Legacy Warning Behavior

**Files:**
- Modify: `tests/hooks/test_artifact_hooks.py`
- Modify: `src/specify_cli/hooks/artifact_validation.py`

- [ ] **Step 1: Add a legacy warning test**

Add this test to `tests/hooks/test_artifact_hooks.py`:

```python
def test_validate_artifacts_warns_for_legacy_specify_package_without_lossless_files(tmp_path: Path):
    project = _create_project(tmp_path)
    feature_dir = project / "specs" / "001-demo"
    feature_dir.mkdir(parents=True)
    _write_valid_specify_semantic_artifacts(feature_dir)
    _write_valid_specify_workflow_state(feature_dir)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    for relative in (
        "journal.ndjson",
        "stage-manifest.json",
        "domains.json",
        "evidence-index.json",
    ):
        path = feature_dir / "brainstorming" / relative
        if path.exists():
            path.unlink()
    legacy_marker = feature_dir / "brainstorming" / "legacy-state.json"
    legacy_marker.write_text('{"version":1,"lossless_state":"legacy-unavailable"}', encoding="utf-8")

    result = run_quality_hook(project, "workflow.artifacts.validate", {"command_name": "specify", "feature_dir": str(feature_dir)})

    assert result.status == "warn"
    assert any("legacy" in message.lower() and "lossless" in message.lower() for message in result.warnings)
```

- [ ] **Step 2: Run the red legacy test**

Run:

```powershell
pytest tests/hooks/test_artifact_hooks.py::test_validate_artifacts_warns_for_legacy_specify_package_without_lossless_files -q
```

Expected: FAIL because missing required artifacts currently block.

- [ ] **Step 3: Implement explicit legacy marker handling**

In `validate_artifacts_hook`, before returning on missing required artifacts for `command_name == "specify"`, detect:

```python
legacy_marker = feature_dir / "brainstorming" / "legacy-state.json"
lossless_missing = [name for name in missing if name.startswith("brainstorming/") and name in {
    "brainstorming/journal.ndjson",
    "brainstorming/stage-manifest.json",
    "brainstorming/domains.json",
    "brainstorming/evidence-index.json",
    "brainstorming/evidence",
}]
```

If the legacy marker exists and all missing artifacts are from this lossless set, return:

```python
return HookResult(
    event=WORKFLOW_ARTIFACTS_VALIDATE,
    status="warn",
    severity="warning",
    warnings=[
        "legacy sp-specify package lacks lossless state artifacts; do not treat this package as lossless unless it is repaired with legacy_state_imported"
    ],
    data={"feature_dir": str(feature_dir), "legacy_lossless_state": False},
)
```

Do not allow legacy mode if non-lossless required artifacts such as `spec.md` or `workflow-state.md` are missing.

- [ ] **Step 4: Run focused legacy and missing-artifact tests**

Run:

```powershell
pytest tests/hooks/test_artifact_hooks.py::test_validate_artifacts_warns_for_legacy_specify_package_without_lossless_files tests/hooks/test_artifact_hooks.py::test_validate_artifacts_blocks_specify_when_lossless_journal_is_missing tests/hooks/test_artifact_hooks.py::test_validate_artifacts_blocks_specify_when_draft_artifact_is_missing -q
```

Expected: PASS.

- [ ] **Step 5: Commit legacy warning behavior**

```powershell
git add tests/hooks/test_artifact_hooks.py src/specify_cli/hooks/artifact_validation.py
git commit -m "feat: warn on legacy specify state"
```

### Task 8: Update Guidance Docs And Generated Workflow Docs

**Files:**
- Modify: `README.md`
- Modify: `PROJECT-HANDBOOK.md`
- Modify: `templates/project-handbook-template.md`
- Modify: `docs/quickstart.md`
- Modify: `docs/installation.md`
- Modify: `tests/test_specify_guidance_docs.py`

- [ ] **Step 1: Add failing docs assertions**

Add this test to `tests/test_specify_guidance_docs.py`:

```python
def test_guidance_docs_explain_lossless_specify_state() -> None:
    readme = _read("README.md")
    handbook = _read("PROJECT-HANDBOOK.md")
    quickstart = _read("docs/quickstart.md")

    for content in (readme, handbook, quickstart):
        lowered = content.lower()
        assert "journal.ndjson" in content
        assert "stage-manifest.json" in content
        assert "lossless" in lowered
        assert "compiled_from" in content
        assert "markdown is not a trusted recovery source" in lowered
```

- [ ] **Step 2: Run red docs test**

Run:

```powershell
pytest tests/test_specify_guidance_docs.py::test_guidance_docs_explain_lossless_specify_state -q
```

Expected: FAIL.

- [ ] **Step 3: Update docs**

Add concise guidance to `README.md`, `PROJECT-HANDBOOK.md`, `templates/project-handbook-template.md`, `docs/quickstart.md`, and `docs/installation.md`:

```markdown
`sp-specify` is lossless-state backed for new feature packages. The trusted recovery source is `brainstorming/journal.ndjson` plus JSON stage artifacts indexed by `brainstorming/stage-manifest.json`; Markdown is not a trusted recovery source. Final artifacts carry `compiled_from` / source-map references so planning can trace major claims to event IDs or evidence IDs.
```

- [ ] **Step 4: Run docs test**

Run:

```powershell
pytest tests/test_specify_guidance_docs.py::test_guidance_docs_explain_lossless_specify_state -q
```

Expected: PASS.

- [ ] **Step 5: Commit docs**

```powershell
git add README.md PROJECT-HANDBOOK.md templates/project-handbook-template.md docs/quickstart.md docs/installation.md tests/test_specify_guidance_docs.py
git commit -m "docs: explain lossless specify state"
```

### Task 9: Run Focused Regression And Final Review

**Files:**
- Modify only if verification exposes drift.

- [ ] **Step 1: Run focused template/scaffolding tests**

```powershell
pytest tests/test_alignment_templates.py tests/test_packaging_assets.py tests/integrations/test_cli.py -q
```

Expected: PASS.

- [ ] **Step 2: Run focused hook tests**

```powershell
pytest tests/hooks/test_artifact_hooks.py tests/contract/test_hook_cli_surface.py -q
```

Expected: PASS. If legacy `current_stage` tests fail because they use old compatibility stage names, update the test fixtures to canonical stages only where they are modeling `sp-specify` lossless state. Do not weaken the canonical stage enum.

- [ ] **Step 3: Run guidance docs tests**

```powershell
pytest tests/test_specify_guidance_docs.py -q
```

Expected: PASS.

- [ ] **Step 4: Inspect diff for scope creep**

Run:

```powershell
git diff --stat HEAD~8..HEAD
git diff --check
```

Expected:

- Changes stay within templates, scripts, docs, hooks, packaging, and tests named in this plan.
- `git diff --check` exits 0.

- [ ] **Step 5: Manual scaffold smoke test**

Run a dry or temp-directory scaffold check from the repo root:

```powershell
$tmp = New-Item -ItemType Directory -Path ([System.IO.Path]::Combine([System.IO.Path]::GetTempPath(), "specify-lossless-smoke-" + [System.Guid]::NewGuid().ToString("N")))
Push-Location $tmp
git init | Out-Null
$env:PYTHONPATH = "F:\github\spec-kit-plus\src"
python -m specify_cli init --ai codex --ai-skills --here --ignore-agent-tools
Pop-Location
```

Expected:

- Generated project includes `.specify/templates/brainstorming-stage-manifest-template.json`.
- Running the generated create-feature script creates `brainstorming/journal.ndjson`, `brainstorming/stage-manifest.json`, `brainstorming/domains.json`, `brainstorming/evidence-index.json`, and `brainstorming/evidence/EVD-000-template.json`.

- [ ] **Step 6: Handle verification fixes without hiding them**

If Step 1-5 required fixes, do not use a catch-all commit command. Add a short
follow-up task naming the exact files and tests affected, then commit that
follow-up task with its exact paths. If no fixes were needed, leave this task
with no commit.

```powershell
git status --short
```

---

## Verification Notes

Run these before claiming implementation complete:

```powershell
pytest tests/test_alignment_templates.py tests/test_packaging_assets.py tests/integrations/test_cli.py -q
pytest tests/hooks/test_artifact_hooks.py tests/contract/test_hook_cli_surface.py -q
pytest tests/test_specify_guidance_docs.py -q
git diff --check
```

The implementation is complete only when new `sp-specify` packages have lossless state files, templates require journal-backed checkpoints and source maps, validation blocks inconsistent non-legacy state, and legacy packages are explicitly marked as non-lossless instead of silently upgraded.
